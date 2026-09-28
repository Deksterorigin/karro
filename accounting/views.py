import calendar
import datetime
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Case, DecimalField, Sum, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from main.decorators import login_required_session, role_required
from main.models import Booking, CarHistory, ServiceStation

from .models import Employee, SalaryBalance, SparePart, Transaction, UsedSparePart
from .supplier_api import CATALOG_DATABASE, search_supplier_parts


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['full_name', 'phone', 'email', 'position', 'base_salary', 'commission_percent', 'is_active']


class SparePartForm(forms.ModelForm):
    class Meta:
        model = SparePart
        fields = ['name', 'sku', 'quantity', 'cost_price', 'selling_price', 'min_quantity']


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'category', 'amount', 'description', 'date']

    def clean(self):
        data = super().clean()
        cat, t_type, amount = data.get('category'), data.get('type'), data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Сума має бути більшою за нуль.')
        incomes = {'service', 'other_income'}
        expenses = {'salary', 'spare_parts', 'rent', 'utilities', 'other_expense'}
        if (t_type == 'income' and cat not in incomes) or (t_type == 'expense' and cat not in expenses):
            raise forms.ValidationError('Категорія не відповідає типу операції.')
        return data


def _show_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


def _owned_station(request, *, required=True):
    station_id = request.POST.get('station_id') or request.GET.get('station_id')
    stations = ServiceStation.objects.filter(user=request.user)
    if station_id:
        return get_object_or_404(stations, pk=station_id)
    return get_object_or_404(stations.order_by('pk')) if required else stations.order_by('pk').first()


def _money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not amount.is_finite() or amount <= 0 or amount > Decimal('99999999.99') or amount.as_tuple().exponent < -2:
        return None
    return amount


def _positive_int(value):
    try:
        num = int(value)
        return num if num > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_date_range(request):
    today = datetime.date.today()
    first_day = today.replace(day=1)
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)
    start_date, end_date = first_day, last_day

    if start_str := request.GET.get('start_date'):
        try:
            start_date = datetime.date.fromisoformat(start_str)
        except ValueError:
            pass
    if end_str := request.GET.get('end_date'):
        try:
            end_date = datetime.date.fromisoformat(end_str)
        except ValueError:
            pass
    return start_date, end_date


def _build_daily_chart(period_transactions, start_date, end_date):
    daily_data = {}
    curr_d = start_date
    while curr_d <= end_date:
        daily_data[curr_d.strftime('%d.%m')] = {'income': Decimal('0.00'), 'expense': Decimal('0.00')}
        curr_d += datetime.timedelta(days=1)

    for record in period_transactions:
        day_key = record.date.strftime('%d.%m')
        if day_key in daily_data:
            if record.type == 'income':
                daily_data[day_key]['income'] += record.amount
            else:
                daily_data[day_key]['expense'] += record.amount

    dates = list(daily_data.keys())
    return dates, [float(daily_data[d]['income']) for d in dates], [float(daily_data[d]['expense']) for d in dates]


def _build_expense_categories(period_transactions, total_expense):
    categories = {}
    for cat_code, cat_name in Transaction.TRANSACTION_CATEGORIES:
        if cat_code in ['salary', 'spare_parts', 'rent', 'utilities', 'other_expense']:
            categories[cat_code] = {'label': cat_name.split(' (')[0], 'amount': Decimal('0.00'), 'percent': 0}

    for record in period_transactions:
        if record.type == 'expense':
            cat_key = record.category if record.category in categories else 'other_expense'
            if cat_key in categories:
                categories[cat_key]['amount'] += record.amount

    labels, values = [], []
    for cat_code, data in categories.items():
        if total_expense > 0:
            data['percent'] = round(float((data['amount'] / total_expense) * 100), 1)
        if data['amount'] > 0:
            labels.append(data['label'])
            values.append(float(data['amount']))

    return categories, labels, values


def _posted_parts(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise ValueError('Не вдалося прочитати список запчастин.')
    if not isinstance(data, list):
        raise ValueError('Список запчастин має бути масивом.')

    quantities = Counter()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Перевірте дані запчастин.')
        part_id = _positive_int(item.get('part_id', item.get('spare_part_id')))
        quantity = _positive_int(item.get('quantity', item.get('qty')))
        if part_id is None or quantity is None:
            raise ValueError('Вкажіть запчастину та додатну кількість.')
        quantities[part_id] += quantity
    return quantities


def _lock_station(station_id):
    ServiceStation.objects.filter(pk=station_id).update(is_verified=models.F('is_verified'))


@login_required_session
@role_required('station')
def dashboard_view(request):
    stations = ServiceStation.objects.filter(user=request.user)
    if not stations.exists():
        messages.warning(request, 'Будь ласка, спочатку створіть СТО в профілі.')
        return redirect('profile')

    station_id = request.GET.get('station_id')
    selected_station = stations.filter(pk=station_id).first() if station_id else stations.first()

    start_date, end_date = _parse_date_range(request)
    transaction_type = request.GET.get('type', '')
    category = request.GET.get('category', '')
    employee_id_filter = request.GET.get('employee_id', '')

    all_transactions = Transaction.objects.filter(station=selected_station).select_related('employee', 'booking')
    period_transactions = all_transactions.filter(date__range=[start_date, end_date])

    totals = period_transactions.aggregate(
        income=Sum(Case(When(type='income', then='amount'), default=Value(Decimal('0.00')), output_field=DecimalField())),
        expense=Sum(Case(When(type='expense', then='amount'), default=Value(Decimal('0.00')), output_field=DecimalField())),
    )
    total_income = totals['income'] or Decimal('0.00')
    total_expense = totals['expense'] or Decimal('0.00')
    net_profit = total_income - total_expense

    chart_dates, chart_incomes, chart_expenses = _build_daily_chart(period_transactions, start_date, end_date)
    expense_categories, cat_labels, cat_values = _build_expense_categories(period_transactions, total_expense)

    filtered_transactions = period_transactions
    if transaction_type in ('income', 'expense'):
        filtered_transactions = filtered_transactions.filter(type=transaction_type)
    if category and category != 'all':
        filtered_transactions = filtered_transactions.filter(category=category)
    if employee_id_filter and employee_id_filter != 'all':
        try:
            filtered_transactions = filtered_transactions.filter(employee_id=int(employee_id_filter))
        except (ValueError, TypeError):
            pass

    salary_payouts = all_transactions.filter(category='salary', date__range=[start_date, end_date])
    if employee_id_filter and employee_id_filter != 'all':
        try:
            salary_payouts = salary_payouts.filter(employee_id=int(employee_id_filter))
        except (ValueError, TypeError):
            pass

    unpaid_salaries = sum(
        sb.current_balance for sb in SalaryBalance.objects.filter(
            employee__station=selected_station, employee__is_active=True
        )
    )

    return render(request, 'accounting/dashboard.html', {
        'user': request.user,
        'stations': stations,
        'selected_station': selected_station,
        'employees': Employee.objects.filter(station=selected_station).select_related('salary_balance'),
        'transactions': filtered_transactions[:100],
        'salary_payouts': salary_payouts[:100],
        'spare_parts': SparePart.objects.filter(station=selected_station),
        'bookings': Booking.objects.filter(station=selected_station, status__in=['pending', 'confirmed']).select_related('client', 'car'),
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'unpaid_salaries': unpaid_salaries,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'categories_choices': Transaction.TRANSACTION_CATEGORIES,
        'expense_categories': expense_categories.values(),
        'selected_type': transaction_type,
        'selected_category': category,
        'selected_employee_id': employee_id_filter,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_incomes_json': json.dumps(chart_incomes),
        'chart_expenses_json': json.dumps(chart_expenses),
        'category_labels_json': json.dumps(cat_labels),
        'category_values_json': json.dumps(cat_values),
    })


@role_required('station')
@require_POST
def add_employee_view(request):
    station = _owned_station(request)
    form = EmployeeForm(request.POST)
    if form.is_valid():
        employee = form.save(commit=False)
        employee.station = station
        employee.save()
        messages.success(request, 'Співробітника додано.')
    else:
        _show_errors(request, form)
    return redirect(reverse('accounting:dashboard') + f'?station_id={station.pk}')


@role_required('station')
@require_POST
def edit_employee_view(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id, station__user=request.user)
    form = EmployeeForm(request.POST, instance=employee)
    if form.is_valid():
        form.save()
        messages.success(request, 'Дані співробітника оновлено.')
    else:
        _show_errors(request, form)
    return redirect(reverse('accounting:dashboard') + f'?station_id={employee.station_id}')


@role_required('station')
@require_POST
def fire_employee_view(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id, station__user=request.user)
    employee.is_active = False
    employee.save(update_fields=['is_active'])
    messages.success(request, 'Співробітника позначено як звільненого.')
    return redirect(reverse('accounting:dashboard') + f'?station_id={employee.station_id}')


@role_required('station')
@require_POST
def pay_salary_view(request, employee_id=None):
    emp_id = employee_id or request.POST.get('employee_id')
    employee = get_object_or_404(Employee, pk=emp_id, station__user=request.user)
    amount = _money(request.POST.get('amount'))

    if amount is None:
        messages.error(request, 'Вкажіть додатну суму виплати.')
        return redirect(reverse('accounting:dashboard') + f'?station_id={employee.station_id}')

    with transaction.atomic():
        _lock_station(employee.station_id)
        balance, _ = SalaryBalance.objects.select_for_update().get_or_create(employee=employee)

        if amount > balance.current_balance:
            messages.error(request, 'Сума перевищує доступний баланс зарплати.')
            return redirect(reverse('accounting:dashboard') + f'?station_id={employee.station_id}')

        balance.total_paid += amount
        balance.save(update_fields=['total_paid', 'updated_at'])
        Transaction.objects.create(
            station=employee.station,
            employee=employee,
            type='expense',
            category='salary',
            amount=amount,
            description=f'Виплата зарплати: {employee.full_name}',
        )

    messages.success(request, 'Виплату проведено.')
    return redirect(reverse('accounting:dashboard') + f'?station_id={employee.station_id}')


@role_required('station')
@require_POST
def add_transaction_view(request):
    station = _owned_station(request)
    form = TransactionForm(request.POST)
    if form.is_valid():
        record = form.save(commit=False)
        record.station = station
        record.save()
        messages.success(request, 'Операцію додано.')
    else:
        _show_errors(request, form)
    return redirect(reverse('accounting:dashboard') + f'?station_id={station.pk}')


@role_required('station')
@require_POST
def complete_booking_view(request, booking_id=None):
    b_id = booking_id or request.POST.get('booking_id')
    booking = get_object_or_404(Booking.objects.select_related('station', 'car'), pk=b_id, station__user=request.user)

    amount = _money(request.POST.get('actual_price') or request.POST.get('total_price') or request.POST.get('amount'))
    if amount is None:
        messages.error(request, 'Вкажіть коректну загальну вартість робіт.')
        return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')

    employee_id = request.POST.get('employee_id')
    employee = None
    if employee_id:
        employee = Employee.objects.filter(pk=employee_id, station=booking.station, is_active=True).first()
        if employee is None:
            messages.error(request, 'Майстер не належить цьому СТО.')
            return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')

    mileage_text = request.POST.get('mileage', '').strip()
    mileage = None
    if mileage_text:
        try:
            mileage = int(mileage_text)
        except ValueError:
            mileage = -1
        if mileage < 0:
            messages.error(request, 'Пробіг має бути невід’ємним числом.')
            return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')

    try:
        quantities = _posted_parts(request.POST.get('used_parts_json'))
    except ValueError as error:
        messages.error(request, str(error))
        return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')

    try:
        with transaction.atomic():
            _lock_station(booking.station_id)
            booking = Booking.objects.select_for_update().get(pk=booking.pk)

            if booking.status == 'completed':
                return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')
            if booking.status == 'cancelled':
                raise ValueError('Скасовану заявку не можна завершити.')

            parts = {part.pk: part for part in SparePart.objects.select_for_update().filter(pk__in=quantities, station_id=booking.station_id)}
            if len(parts) != len(quantities):
                raise ValueError('Одна із запчастин не належить цьому СТО.')

            for part_id, quantity in quantities.items():
                if parts[part_id].quantity < quantity:
                    raise ValueError(f'Недостатньо запчастини «{parts[part_id].name}» на складі.')

            work_list = request.POST.get('work_list', '').strip() or booking.description
            spare_parts_field = request.POST.get('spare_parts', '').strip()
            used_names, parts_cost = [], Decimal('0.00')

            for part_id, quantity in quantities.items():
                part = parts[part_id]
                part.quantity -= quantity
                part.save(update_fields=['quantity', 'updated_at'])

                UsedSparePart.objects.create(
                    booking=booking, spare_part=part, part_name=part.name,
                    quantity=quantity, cost_price=part.cost_price, selling_price=part.selling_price,
                )
                parts_cost += part.cost_price * quantity
                used_names.append(f'{part.name} × {quantity}')

            Transaction.objects.create(
                station=booking.station, booking=booking, employee=employee,
                type='income', category='service', amount=amount,
                description=f'Виконання заявки #{booking.pk}',
            )

            if parts_cost:
                Transaction.objects.create(
                    station=booking.station, booking=booking, type='expense',
                    category='spare_parts', amount=parts_cost,
                    description=f'Собівартість запчастин для заявки #{booking.pk}',
                )

            if employee is not None:
                commission = (amount * employee.commission_percent / Decimal('100')).quantize(Decimal('0.01'))
                if commission:
                    balance, _ = SalaryBalance.objects.select_for_update().get_or_create(employee=employee)
                    balance.total_earned += commission
                    balance.save(update_fields=['total_earned', 'updated_at'])

            if booking.car_id:
                history_parts = spare_parts_field or (', '.join(used_names) if used_names else None)
                CarHistory.objects.create(
                    car=booking.car, booking=booking, station=booking.station,
                    date=timezone.localdate(), mileage=mileage, work_list=work_list,
                    spare_parts=history_parts, price=amount,
                )

            booking.status = 'completed'
            booking.save(update_fields=['status'])
    except ValueError as error:
        messages.error(request, str(error))
        return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')

    messages.success(request, 'Заявку завершено, фінанси та склад оновлено.')
    return redirect(reverse('accounting:dashboard') + f'?station_id={booking.station_id}')


@role_required('station')
@require_POST
def add_spare_part_view(request):
    station = _owned_station(request)
    form = SparePartForm(request.POST)
    if form.is_valid():
        part = form.save(commit=False)
        part.station = station
        part.save()
        messages.success(request, 'Запчастину додано на склад.')
    else:
        _show_errors(request, form)
    return redirect(reverse('accounting:dashboard') + f'?station_id={station.pk}')


@role_required('station')
@require_POST
def edit_spare_part_view(request, part_id=None):
    p_id = part_id or request.POST.get('part_id')
    part = get_object_or_404(SparePart, pk=p_id, station__user=request.user)
    form = SparePartForm(request.POST, instance=part)
    if form.is_valid():
        form.save()
        messages.success(request, 'Запчастину оновлено.')
    else:
        _show_errors(request, form)
    return redirect(reverse('accounting:dashboard') + f'?station_id={part.station_id}')


@role_required('station')
@require_POST
def delete_spare_part_view(request, part_id=None):
    p_id = part_id or request.POST.get('part_id')
    part = get_object_or_404(SparePart, pk=p_id, station__user=request.user)
    station_id = part.station_id
    part.delete()
    messages.success(request, 'Запчастину видалено зі складу.')
    return redirect(reverse('accounting:dashboard') + f'?station_id={station_id}')


def _report_transactions(request):
    station = _owned_station(request)
    queryset = Transaction.objects.filter(station=station).select_related('employee', 'booking')
    start_text, end_text = request.GET.get('start_date', ''), request.GET.get('end_date', '')

    try:
        start_date = datetime.date.fromisoformat(start_text) if start_text else None
        end_date = datetime.date.fromisoformat(end_text) if end_text else None
    except ValueError:
        return station, None

    if start_date and end_date and start_date > end_date:
        return station, None
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    t_type = request.GET.get('type')
    if t_type in ('income', 'expense'):
        queryset = queryset.filter(type=t_type)

    category = request.GET.get('category')
    if category and category != 'all':
        queryset = queryset.filter(category=category)

    employee_id = request.GET.get('employee_id')
    if employee_id and employee_id != 'all':
        try:
            queryset = queryset.filter(employee_id=int(employee_id))
        except (ValueError, TypeError):
            pass

    return station, queryset.order_by('-date', '-created_at')


@role_required('station')
@require_GET
def export_transactions_xlsx(request):
    station, transactions = _report_transactions(request)
    if transactions is None:
        messages.error(request, 'Перевірте дати звіту.')
        return redirect('accounting:dashboard')

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Операції'
    sheet.append(['Дата', 'Тип', 'Категорія', 'Сума, грн', 'Опис', 'Заявка', 'Співробітник'])
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for record in transactions:
        sheet.append([
            record.date.strftime('%d.%m.%Y'),
            record.get_type_display(),
            record.get_category_display(),
            float(record.amount),
            record.description or '',
            record.booking_id or '',
            record.employee.full_name if record.employee else '',
        ])

    for cell in sheet['D'][1:]:
        cell.number_format = '#,##0.00'

    widths = {'A': 16, 'B': 15, 'C': 22, 'D': 18, 'E': 55, 'F': 14, 'G': 30}
    for col, width in widths.items():
        sheet.column_dimensions[col].width = width

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="transactions_{station.pk}.xlsx"'
    return response


def _pdf_font():
    font_name = 'KarroDejaVu'
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    candidates = [
        Path(settings.BASE_DIR) / 'static' / 'fonts' / 'DejaVuSans.ttf',
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'),
    ]
    for path in candidates:
        if path.is_file():
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
    return 'Helvetica'


@role_required('station')
@require_GET
def export_financial_report_pdf(request):
    station, transactions = _report_transactions(request)
    if transactions is None:
        messages.error(request, 'Перевірте дати звіту.')
        return redirect('accounting:dashboard')

    font_name = _pdf_font()
    income = transactions.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    expense = transactions.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    page_width, page_height = A4

    def page_header():
        pdf.setFont(font_name, 15)
        pdf.drawString(40, page_height - 48, f'Фінансовий звіт: {station.name}')
        pdf.setFont(font_name, 10)
        pdf.drawString(40, page_height - 68, f'Сформовано: {timezone.localdate():%d.%m.%Y}')
        pdf.drawString(40, page_height - 88, f'Дохід: {income:.2f} грн')
        pdf.drawString(220, page_height - 88, f'Витрати: {expense:.2f} грн')
        pdf.drawString(410, page_height - 88, f'Результат: {income - expense:.2f} грн')
        pdf.line(40, page_height - 100, page_width - 40, page_height - 100)

    page_header()
    y = page_height - 125

    for record in transactions:
        if y < 55:
            pdf.showPage()
            page_header()
            y = page_height - 125

        pdf.setFont(font_name, 9)
        pdf.drawString(40, y, record.date.strftime('%d.%m.%Y'))
        pdf.drawString(110, y, record.get_type_display())
        pdf.drawString(200, y, record.get_category_display())
        pdf.drawRightString(page_width - 40, y, f'{record.amount:.2f} грн')
        y -= 15

        if record.description:
            pdf.setFont(font_name, 8)
            pdf.drawString(110, y, record.description[:75])
            y -= 17

    pdf.save()
    output.seek(0)

    disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'{disposition}; filename="financial_report_{station.pk}.pdf"'
    return response


@role_required('station')
@require_GET
def search_supplier_parts_api(request):
    query = request.GET.get('query') or request.GET.get('q', '')
    supplier = request.GET.get('supplier') or request.GET.get('supplier_code', 'all')
    return JsonResponse(search_supplier_parts(query=query[:100], supplier_code=supplier))


@role_required('station')
@require_POST
def import_supplier_part_view(request):
    station = _owned_station(request)
    sku = request.POST.get('sku', '').strip()
    part_name = request.POST.get('part_name', '').strip()
    quantity = _positive_int(request.POST.get('quantity', 1)) or 1

    item = next((part for part in CATALOG_DATABASE if part['sku'] == sku), None)
    if item:
        name = item['part_name']
        cost = Decimal(str(item['cost_price']))
        selling = Decimal(str(item['suggested_retail_price']))
        supplier_name = item.get('supplier_name', 'Постачальник')
    else:
        name = part_name or sku or 'Запчастина'
        cost = _money(request.POST.get('cost_price')) or Decimal('0.00')
        selling = _money(request.POST.get('selling_price')) or Decimal('0.00')
        supplier_name = 'Постачальник'

    with transaction.atomic():
        _lock_station(station.pk)
        part = SparePart.objects.select_for_update().filter(station=station, sku=sku).first()

        if part is None:
            SparePart.objects.create(
                station=station, name=name, sku=sku,
                quantity=quantity, cost_price=cost, selling_price=selling,
            )
        else:
            part.quantity += quantity
            part.cost_price = cost
            part.selling_price = selling
            part.save(update_fields=['quantity', 'cost_price', 'selling_price', 'updated_at'])

        if cost > 0:
            Transaction.objects.create(
                station=station, type='expense', category='spare_parts',
                amount=cost * quantity,
                description=f'Закупівля: {name} × {quantity}, {supplier_name}',
            )

    messages.success(request, 'Запчастину додано на склад, закупівлю записано у витрати.')
    return redirect(reverse('accounting:dashboard') + f'?station_id={station.pk}')
