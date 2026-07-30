import calendar
import csv
import datetime
from decimal import Decimal, InvalidOperation
import json
import logging
import re

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Sum, Case, When, Value, DecimalField
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from main.decorators import login_required_session, role_required
from main.models import User, ServiceStation, Booking, CarHistory
from main.pdf_utils import generate_financial_report_pdf
from main.views import get_current_user
from .models import Employee, SalaryBalance, Transaction, SparePart, UsedSparePart
from .supplier_api import search_supplier_parts, SUPPLIERS

logger = logging.getLogger(__name__)

# Допоміжні конвертери типів
def _safe_int(val, default=0):
    if val is None or val == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _safe_decimal(val, default=Decimal('0.00')):
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return default

def _redirect_to_dashboard(station_pk):
    return redirect(reverse('accounting:dashboard') + f'?station_id={station_pk}')

def _parse_date_range(request):
    today = datetime.date.today()
    first_day = today.replace(day=1)
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)

    start_date, end_date = first_day, last_day
    if start_str := request.GET.get('start_date'):
        try:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_str := request.GET.get('end_date'):
        try:
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    return start_date, end_date

def _build_daily_chart(period_transactions, start_date, end_date):
    daily_data = {}
    curr_d = start_date
    while curr_d <= end_date:
        daily_data[curr_d.strftime("%d.%m")] = {'income': Decimal('0.00'), 'expense': Decimal('0.00')}
        curr_d += datetime.timedelta(days=1)

    for t in period_transactions:
        t_date_str = t.date.strftime("%d.%m")
        if t_date_str in daily_data:
            if t.type == 'income':
                daily_data[t_date_str]['income'] += t.amount
            else:
                daily_data[t_date_str]['expense'] += t.amount

    dates = list(daily_data.keys())
    incomes = [float(daily_data[d]['income']) for d in dates]
    expenses = [float(daily_data[d]['expense']) for d in dates]
    return dates, incomes, expenses

def _build_expense_categories(period_transactions, total_expense):
    categories = {}
    for cat_code, cat_name in Transaction.TRANSACTION_CATEGORIES:
        if cat_code in ['salary', 'spare_parts', 'rent', 'utilities', 'other_expense']:
            categories[cat_code] = {
                'label': cat_name.split(' (')[0],
                'amount': Decimal('0.00'),
                'percent': 0
            }

    for t in period_transactions:
        if t.type == 'expense':
            cat = t.category if t.category in categories else 'other_expense'
            if cat in categories:
                categories[cat]['amount'] += t.amount

    if total_expense > 0:
        for cat in categories:
            categories[cat]['percent'] = int(round((categories[cat]['amount'] / total_expense) * 100))

    labels, values = [], []
    for cat_data in categories.values():
        if cat_data['amount'] > 0:
            labels.append(cat_data['label'])
            values.append(float(cat_data['amount']))

    return categories, labels, values

# --- Основний Дашборд ---

@login_required_session
@role_required('station')
def dashboard_view(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')

    stations = ServiceStation.objects.filter(user=user)
    if not stations.exists():
        messages.warning(request, "Будь ласка, спочатку створіть СТО в профілі.")
        return redirect('profile')

    st_id = _safe_int(request.GET.get('station_id'))
    selected_station = stations.filter(pk=st_id).first() if st_id else stations.first()
    start_date, end_date = _parse_date_range(request)

    t_type = request.GET.get('type', '')
    category = request.GET.get('category', '')
    employee_id_filter = request.GET.get('employee_id', '')

    employees = Employee.objects.filter(station=selected_station).select_related('salary_balance')
    all_transactions = Transaction.objects.filter(station=selected_station).select_related('employee', 'booking')
    period_transactions = all_transactions.filter(date__range=[start_date, end_date])

    totals = period_transactions.aggregate(
        total_income=Sum(Case(When(type='income', then='amount'), default=Value(Decimal('0.00')), output_field=DecimalField())),
        total_expense=Sum(Case(When(type='expense', then='amount'), default=Value(Decimal('0.00')), output_field=DecimalField())),
    )
    total_income = totals['total_income'] or Decimal('0.00')
    total_expense = totals['total_expense'] or Decimal('0.00')
    net_profit = total_income - total_expense

    chart_dates, chart_incomes, chart_expenses = _build_daily_chart(period_transactions, start_date, end_date)
    expense_categories, cat_labels, cat_values = _build_expense_categories(period_transactions, total_expense)

    filtered_transactions = period_transactions
    if t_type in ['income', 'expense']:
        filtered_transactions = filtered_transactions.filter(type=t_type)
    if category and category != 'all':
        filtered_transactions = filtered_transactions.filter(category=category)
    if employee_id_filter and employee_id_filter != 'all':
        if emp_id := _safe_int(employee_id_filter):
            filtered_transactions = filtered_transactions.filter(employee_id=emp_id)

    salary_payouts = all_transactions.filter(category='salary', date__range=[start_date, end_date])
    if employee_id_filter and employee_id_filter != 'all':
        if emp_id := _safe_int(employee_id_filter):
            salary_payouts = salary_payouts.filter(employee_id=emp_id)

    unpaid_salaries = sum(
        sb.current_balance for sb in SalaryBalance.objects.filter(
            employee__station=selected_station, employee__is_active=True
        )
    )

    return render(request, 'accounting/dashboard.html', {
        'user': user,
        'stations': stations,
        'selected_station': selected_station,
        'employees': employees,
        'transactions': filtered_transactions[:100],
        'salary_payouts': salary_payouts[:100],
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'unpaid_salaries': unpaid_salaries,
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'categories_choices': Transaction.TRANSACTION_CATEGORIES,
        'expense_categories': expense_categories.values(),
        'selected_type': t_type,
        'selected_category': category,
        'selected_employee_id': employee_id_filter,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_incomes_json': json.dumps(chart_incomes),
        'chart_expenses_json': json.dumps(chart_expenses),
        'category_labels_json': json.dumps(cat_labels),
        'category_values_json': json.dumps(cat_values),
    })

# --- Управління Працівниками та Виплатами ---

@login_required_session
@role_required('station')
@require_POST
def add_employee_view(request):
    user = get_current_user(request)
    station = get_object_or_404(ServiceStation, pk=_safe_int(request.POST.get('station_id')), user=user)

    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip() or None
    email = request.POST.get('email', '').strip() or None
    position = request.POST.get('position', '').strip()
    base_salary = _safe_decimal(request.POST.get('base_salary'))
    commission = _safe_decimal(request.POST.get('commission_percent'))

    if not full_name or not position:
        messages.error(request, "Ім'я та посада є обов'язковими.")
    else:
        Employee.objects.create(
            station=station, full_name=full_name, phone=phone, email=email,
            position=position, base_salary=base_salary, commission_percent=commission
        )
        messages.success(request, f"Працівника {full_name} успішно додано.")
    return _redirect_to_dashboard(station.pk)

@login_required_session
@role_required('station')
@require_POST
def edit_employee_view(request, employee_id):
    user = get_current_user(request)
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)

    full_name = request.POST.get('full_name', '').strip()
    position = request.POST.get('position', '').strip()
    if not full_name or not position:
        messages.error(request, "Ім'я та посада є обов'язковими.")
    else:
        employee.full_name = full_name
        employee.position = position
        employee.phone = request.POST.get('phone', '').strip() or None
        employee.email = request.POST.get('email', '').strip() or None
        employee.base_salary = _safe_decimal(request.POST.get('base_salary'))
        employee.commission_percent = _safe_decimal(request.POST.get('commission_percent'))
        employee.is_active = (request.POST.get('is_active') == 'true')
        employee.save()
        messages.success(request, f"Дані працівника {full_name} оновлено.")
    return _redirect_to_dashboard(employee.station.pk)

@login_required_session
@role_required('station')
@require_POST
def fire_employee_view(request, employee_id):
    user = get_current_user(request)
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)
    employee.is_active = False
    employee.save()
    messages.success(request, f"Працівника {employee.full_name} звільнено.")
    return _redirect_to_dashboard(employee.station.pk)

@login_required_session
@role_required('station')
@require_POST
def pay_salary_view(request):
    user = get_current_user(request)
    employee = get_object_or_404(Employee, pk=_safe_int(request.POST.get('employee_id')), station__user=user)
    amount = _safe_decimal(request.POST.get('amount'))

    if amount <= 0:
        messages.error(request, "Сума виплати має бути більшою за нуль.")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        with transaction.atomic():
            balance = SalaryBalance.objects.select_for_update().get(employee=employee)
            if amount > balance.current_balance:
                messages.error(request, f"Сума виплати ({amount} грн) перевищує баланс ({balance.current_balance} грн).")
                return _redirect_to_dashboard(employee.station.pk)

            balance.total_paid = F('total_paid') + amount
            balance.save(update_fields=['total_paid'])

            Transaction.objects.create(
                station=employee.station, type='expense', category='salary',
                amount=amount, description=f"Виплата зарплати: {employee.full_name} ({employee.position})",
                employee=employee, date=datetime.date.today()
            )
        messages.success(request, f"Виплата {amount} грн працівнику {employee.full_name} проведена.")
    except Exception as err:
        logger.error("Помилка при виплаті зарплати: %s", err, exc_info=True)
        messages.error(request, "Помилка при виплаті зарплати.")

    return _redirect_to_dashboard(employee.station.pk)

@login_required_session
@role_required('station')
@require_POST
def add_transaction_view(request):
    user = get_current_user(request)
    station = get_object_or_404(ServiceStation, pk=_safe_int(request.POST.get('station_id')), user=user)

    t_type = request.POST.get('type')
    category = request.POST.get('category')
    amount = _safe_decimal(request.POST.get('amount'))
    description = request.POST.get('description', '').strip()
    date_str = request.POST.get('date')

    if t_type not in ['income', 'expense']:
        messages.error(request, "Невірний тип операції.")
    elif category not in dict(Transaction.TRANSACTION_CATEGORIES):
        messages.error(request, "Невірна категорія операції.")
    elif amount <= 0:
        messages.error(request, "Сума має бути більшою за нуль.")
    else:
        t_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()
        Transaction.objects.create(
            station=station, type=t_type, category=category,
            amount=amount, description=description, date=t_date
        )
        messages.success(request, "Операцію успішно додано.")
    return _redirect_to_dashboard(station.pk)

@login_required_session
@role_required('station')
@require_POST
def complete_booking_view(request):
    user = get_current_user(request)
    booking_id = request.POST.get('booking_id')
    actual_price = _safe_decimal(request.POST.get('actual_price'))
    employee_id = request.POST.get('employee_id')
    mileage = _safe_int(request.POST.get('mileage')) or None
    work_list = request.POST.get('work_list', '').strip()
    spare_parts = request.POST.get('spare_parts', '').strip()
    used_parts_json = request.POST.get('used_parts_json')

    if actual_price <= 0:
        messages.error(request, "Вартість ремонту повинна бути більшою за нуль.")
        return redirect('profile')

    used_parts_data = []
    if used_parts_json:
        try:
            used_parts_data = json.loads(used_parts_json)
        except Exception:
            pass

    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking_id, station__user=user)

            if booking.status == 'completed':
                messages.warning(request, f"Заявка #{booking.pk} вже була завершена.")
                return redirect(reverse('profile') + '?tab=bookings')
            if booking.status == 'cancelled':
                messages.error(request, f"Неможливо завершити скасовану заявку #{booking.pk}.")
                return redirect(reverse('profile') + '?tab=bookings')

            employee = Employee.objects.filter(pk=employee_id, station=booking.station).first() if employee_id else None

            booking.status = 'completed'
            booking.save(update_fields=['status'])

            desc = f"Завершено ремонт за заявкою #{booking.id} ({booking.service_name or 'Загальні роботи'})"
            if employee:
                desc += f". Виконавець: {employee.full_name}."

            tx = Transaction.objects.create(
                station=booking.station, type='income', category='service',
                amount=actual_price, description=desc, booking=booking,
                employee=employee, date=datetime.date.today()
            )

            if employee and employee.commission_percent > 0:
                commission = (actual_price * (employee.commission_percent / Decimal('100.00'))).quantize(Decimal('0.01'))
                sb = SalaryBalance.objects.select_for_update().get(employee=employee)
                sb.total_earned = F('total_earned') + commission
                sb.save(update_fields=['total_earned'])
                tx.description += f" Нараховано комісію: {commission} грн."
                tx.save(update_fields=['description'])

            total_parts_cost = Decimal('0.00')
            parts_summary = []
            for item in used_parts_data:
                p_id = item.get('part_id')
                p_qty = int(item.get('qty', 0))
                if p_id and p_qty > 0:
                    try:
                        sp = SparePart.objects.select_for_update().get(pk=p_id, station=booking.station)
                        actual_deduct = min(sp.quantity, p_qty) if sp.quantity > 0 else 0
                        if actual_deduct > 0:
                            sp.quantity = F('quantity') - actual_deduct
                            sp.save(update_fields=['quantity'])
                            UsedSparePart.objects.create(
                                booking=booking, spare_part=sp, part_name=sp.name,
                                quantity=actual_deduct, cost_price=sp.cost_price, selling_price=sp.selling_price
                            )
                            line_cost = sp.cost_price * actual_deduct
                            line_sell = sp.selling_price * actual_deduct
                            total_parts_cost += line_cost
                            parts_summary.append(f"{sp.name} x{actual_deduct} ({line_sell} грн)")
                    except SparePart.DoesNotExist:
                        pass

            if total_parts_cost > 0:
                Transaction.objects.create(
                    station=booking.station, type='expense', category='spare_parts',
                    amount=total_parts_cost, description=f"Списання запчастин за заявкою #{booking.id}",
                    booking=booking, employee=employee, date=datetime.date.today()
                )

            if parts_summary:
                auto_parts_str = ", ".join(parts_summary)
                spare_parts = f"{auto_parts_str}\n{spare_parts}" if spare_parts else auto_parts_str

            if booking.car:
                final_works = work_list or (booking.service_name or booking.description or 'Виконано роботи')
                CarHistory.objects.create(
                    car=booking.car, booking=booking, station=booking.station,
                    date=datetime.date.today(), mileage=mileage, work_list=final_works,
                    spare_parts=spare_parts, price=actual_price
                )

        messages.success(request, f"Ремонт за заявкою #{booking.id} успішно завершено.")
    except Booking.DoesNotExist:
        messages.error(request, "Заявку не знайдено.")
    except Exception as err:
        logger.error("Помилка завершення ремонту: %s", err, exc_info=True)
        messages.error(request, "Помилка при завершенні ремонту.")

    return redirect(reverse('profile') + '?tab=bookings')

# --- Управління Складом Запчастин ---

@login_required_session
@role_required('station')
@require_POST
def add_spare_part_view(request):
    user = get_current_user(request)
    station = get_object_or_404(ServiceStation, pk=_safe_int(request.POST.get('station_id')), user=user)
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, "Вкажіть назву запчастини.")
        return _redirect_to_dashboard(station.pk)

    SparePart.objects.create(
        station=station, name=name, sku=request.POST.get('sku', '').strip() or None,
        quantity=max(0, _safe_int(request.POST.get('quantity'))),
        cost_price=max(Decimal('0.00'), _safe_decimal(request.POST.get('cost_price'))),
        selling_price=max(Decimal('0.00'), _safe_decimal(request.POST.get('selling_price'))),
        min_quantity=max(0, _safe_int(request.POST.get('min_quantity'), 5))
    )
    messages.success(request, f"Запчастину '{name}' додано на склад.")
    return redirect(reverse('profile') + '?tab=inventory')

@login_required_session
@role_required('station')
@require_POST
def edit_spare_part_view(request):
    user = get_current_user(request)
    part = get_object_or_404(SparePart, pk=request.POST.get('part_id'), station__user=user)

    if name := request.POST.get('name', '').strip():
        part.name = name
    part.sku = request.POST.get('sku', '').strip() or None

    if (q := request.POST.get('quantity')) is not None and q != '':
        part.quantity = max(0, _safe_int(q))
    if (cp := request.POST.get('cost_price')) is not None and cp != '':
        part.cost_price = max(Decimal('0.00'), _safe_decimal(cp))
    if (sp := request.POST.get('selling_price')) is not None and sp != '':
        part.selling_price = max(Decimal('0.00'), _safe_decimal(sp))
    if (mq := request.POST.get('min_quantity')) is not None and mq != '':
        part.min_quantity = max(0, _safe_int(mq))

    part.save()
    messages.success(request, f"Запчастину '{part.name}' оновлено.")
    return redirect(reverse('profile') + '?tab=inventory')

@login_required_session
@role_required('station')
@require_POST
def delete_spare_part_view(request):
    user = get_current_user(request)
    part = get_object_or_404(SparePart, pk=request.POST.get('part_id'), station__user=user)
    name = part.name
    part.delete()
    messages.success(request, f"Запчастину '{name}' видалено зі складу.")
    return redirect(reverse('profile') + '?tab=inventory')

# --- Експорт Звітів (Excel та PDF) ---

@login_required_session
@role_required('station')
def export_transactions_csv(request):
    user = get_current_user(request)
    if not user or not (st_id := _safe_int(request.GET.get('station_id'))):
        messages.error(request, "Не вказано СТО для експорту.")
        return redirect('profile')

    station = get_object_or_404(ServiceStation, pk=st_id, user=user)
    start_date, end_date = _parse_date_range(request)

    t_type = request.GET.get('type')
    category = request.GET.get('category')
    emp_filter = request.GET.get('employee_id')

    transactions = Transaction.objects.filter(
        station=station, date__range=[start_date, end_date]
    ).select_related('employee', 'booking')

    if t_type in ['income', 'expense']:
        transactions = transactions.filter(type=t_type)
    if category and category != 'all':
        transactions = transactions.filter(category=category)
    if emp_filter and emp_filter != 'all' and (e_id := _safe_int(emp_filter)):
        transactions = transactions.filter(employee_id=e_id)

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', re.sub(r'\s+', '_', station.name)).strip('_')[:50] or 'station'
    filename = f"{safe_name}_report_{start_date}_{end_date}.xlsx"

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Фінансовий звіт"
    ws.views.sheetView[0].showGridLines = True

    ws.merge_cells('A1:G1')
    ws['A1'].value = f"ФІНАНСОВИЙ ЗВІТ СТО: {station.name.upper()}"
    ws['A1'].font = Font(name='Arial', size=14, bold=True, color="FFFFFF")
    ws['A1'].fill = PatternFill(start_color="1E293B", fill_type="solid")
    ws['A1'].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells('A2:G2')
    ws['A2'].value = f"Період: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}"
    ws['A2'].font = Font(name='Arial', size=10, italic=True, color="475569")
    ws['A2'].alignment = Alignment(horizontal="center", vertical="center")

    headers = ['Дата', 'Тип операції', 'Категорія', 'Сума (грн)', 'Опис', 'ID Заявки', 'Співробітник']
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="0284C7", fill_type="solid")
    header_font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
    for col_idx in range(1, 8):
        cell = ws.cell(row=4, column=col_idx)
        cell.fill, cell.font = header_fill, header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    total_inc, total_exp = Decimal('0.00'), Decimal('0.00')
    curr_row = 5
    for t in transactions:
        ws.append([
            t.date.strftime("%d.%m.%Y"), t.get_type_display(), t.get_category_display(),
            float(t.amount), t.description or '', t.booking.id if t.booking else '',
            t.employee.full_name if t.employee else ''
        ])
        fill = PatternFill(start_color="F8FAFC" if curr_row % 2 == 0 else "FFFFFF", fill_type="solid")
        for c_idx in range(1, 8):
            cell = ws.cell(row=curr_row, column=c_idx)
            cell.fill = fill
            cell.font = Font(name='Arial', size=10)
            if c_idx == 4:
                cell.number_format = '#,##0.00 "грн"'
                cell.alignment = Alignment(horizontal="right")
                if t.type == 'income':
                    cell.font = Font(name='Arial', size=10, bold=True, color="16A34A")
                    total_inc += t.amount
                else:
                    cell.font = Font(name='Arial', size=10, bold=True, color="DC2626")
                    total_exp += t.amount
        curr_row += 1

    summary_row = curr_row + 1
    ws.cell(row=summary_row, column=3, value="ЧИСТИЙ ПРИБУТОК:").font = Font(name='Arial', size=11, bold=True)
    net_cell = ws.cell(row=summary_row, column=4, value=float(total_inc - total_exp))
    net_cell.font = Font(name='Arial', size=12, bold=True, color="16A34A" if total_inc >= total_exp else "DC2626")
    net_cell.number_format = '#,##0.00 "грн"'

    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col if cell.row > 2), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 14)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required_session
@role_required('station')
def export_financial_report_pdf(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')

    stations = ServiceStation.objects.filter(user=user)
    if not stations.exists():
        messages.warning(request, "Спочатку створіть СТО.")
        return redirect('profile')

    st_id = _safe_int(request.GET.get('station_id'))
    selected_station = stations.filter(pk=st_id).first() if st_id else stations.first()
    start_date, end_date = _parse_date_range(request)

    period_transactions = list(Transaction.objects.filter(station=selected_station, date__range=[start_date, end_date]).select_related('employee', 'booking'))
    total_income = sum((t.amount for t in period_transactions if t.type == 'income'), Decimal('0.00'))
    total_expense = sum((t.amount for t in period_transactions if t.type == 'expense'), Decimal('0.00'))
    net_profit = total_income - total_expense

    completed_bookings = Booking.objects.filter(station=selected_station, status='completed', created_at__date__range=[start_date, end_date]).count()

    income_cats, expense_cats = {}, {}
    for t in period_transactions:
        c_disp = t.get_category_display()
        if t.type == 'income':
            income_cats[c_disp] = income_cats.get(c_disp, Decimal('0.00')) + t.amount
        else:
            expense_cats[c_disp] = expense_cats.get(c_disp, Decimal('0.00')) + t.amount

    metrics = {
        'total_income': total_income, 'total_expense': total_expense,
        'net_profit': net_profit, 'profit_margin': float((net_profit / total_income) * 100) if total_income > 0 else 0.0,
        'completed_bookings': completed_bookings,
        'income_by_category': income_cats, 'expense_by_category': expense_cats,
    }
    employees = list(Employee.objects.filter(station=selected_station).select_related('salary_balance'))

    pdf_bytes = generate_financial_report_pdf(selected_station, start_date, end_date, period_transactions, metrics, employees)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', re.sub(r'\s+', '_', selected_station.name)).strip('_')[:50] or 'station'
    filename = f"financial_report_{safe_name}_{start_date}_{end_date}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response

# --- Пошук та Імпорт Запчастин від Постачальників ---

def search_supplier_parts_api(request):
    query = request.GET.get('query', '').strip()
    supplier = request.GET.get('supplier', 'all').strip()
    return JsonResponse(search_supplier_parts(query, supplier))

@require_POST
@login_required_session
@role_required('station')
def import_supplier_part_view(request):
    user = get_current_user(request)
    station = get_object_or_404(ServiceStation, pk=_safe_int(request.POST.get('station_id')), user=user)

    sku = request.POST.get('sku', '').strip()
    part_name = request.POST.get('part_name', '').strip()
    brand = request.POST.get('brand', '').strip()
    cost_price = _safe_decimal(request.POST.get('cost_price'))
    selling_price = _safe_decimal(request.POST.get('selling_price'))
    quantity = max(1, _safe_int(request.POST.get('quantity'), 1))

    if not part_name:
        messages.error(request, 'Назва запчастини є обов\'язковою.')
        return _redirect_to_dashboard(station.pk)

    full_name = f"{part_name} ({brand})" if brand else part_name
    existing_part = SparePart.objects.filter(station=station, name=full_name, sku=sku).first()

    if existing_part:
        existing_part.quantity += quantity
        existing_part.cost_price = cost_price
        if selling_price > 0:
            existing_part.selling_price = selling_price
        existing_part.save()
        messages.success(request, f'Кількість запчастини "{full_name}" оновлено (+{quantity} шт).')
    else:
        if selling_price <= 0:
            selling_price = round(cost_price * Decimal('1.35'), 2)
        SparePart.objects.create(
            station=station, name=full_name, sku=sku, quantity=quantity,
            cost_price=cost_price, selling_price=selling_price, min_quantity=3
        )
        messages.success(request, f'Запчастину "{full_name}" додано на склад СТО.')

    return _redirect_to_dashboard(station.pk)
