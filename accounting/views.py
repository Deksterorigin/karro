from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponse
# FIX (CRIT-01/02/03): Імпорт transaction та F для атомарних операцій
from django.db import transaction
from django.db.models import F
from main.decorators import login_required_session, role_required
from main.models import User, ServiceStation, Booking
from main.views import get_current_user
from .models import Employee, SalaryBalance, Transaction
import datetime
import re
from decimal import Decimal, InvalidOperation
import calendar
import csv
import json



def _redirect_to_dashboard(station_pk):
    """Перенаправлення на дашборд бухгалтерії для конкретної СТО."""
    return redirect(reverse('accounting:dashboard') + f'?station_id={station_pk}')


# FIX (ARCH-08): Спільна utility-функція для парсингу діапазону дат
def _parse_date_range(request):
    """Парсить діапазон дат з GET-параметрів, дефолт — поточний місяць."""
    today = datetime.date.today()
    first_day = today.replace(day=1)
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = first_day
    end_date = last_day

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    return start_date, end_date


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

    # Визначаємо, для якої саме СТО показувати звітність
    station_id = request.GET.get('station_id')
    selected_station = None
    if station_id:
        try:
            selected_station = stations.filter(pk=int(station_id)).first()
        except ValueError:
            pass
    if not selected_station:
        selected_station = stations.first()

    # FIX (ARCH-08): Використовуємо спільну utility-функцію
    start_date, end_date = _parse_date_range(request)

    # Отримуємо фільтри з GET-запиту
    t_type = request.GET.get('type', '')
    category = request.GET.get('category', '')
    employee_id_filter = request.GET.get('employee_id', '')

    # Працівники цієї станції
    employees = Employee.objects.filter(station=selected_station).select_related('salary_balance')

    # Отримуємо всі фінансові записи цієї станції
    all_transactions = Transaction.objects.filter(station=selected_station).select_related('employee', 'booking')
    
    # Фільтруємо транзакції за обраний період часу (базовий список транзакцій для метрик і графіків)
    period_transactions = all_transactions.filter(date__range=[start_date, end_date])

    # Розрахунок загальних фінансових показників для карток метрик
    total_income = sum(
        (t.amount for t in period_transactions if t.type == 'income'),
        Decimal('0.00')
    )
    total_expense = sum(
        (t.amount for t in period_transactions if t.type == 'expense'),
        Decimal('0.00')
    )
    net_profit = total_income - total_expense

    # Формуємо дані для лінійного графіка динаміки фінансів за днями
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

    chart_dates = list(daily_data.keys())
    chart_incomes = [float(daily_data[d]['income']) for d in chart_dates]
    chart_expenses = [float(daily_data[d]['expense']) for d in chart_dates]

    # Групуємо витрати за категоріями для побудови діаграми
    expense_categories = {}
    for cat_code, cat_name in Transaction.TRANSACTION_CATEGORIES:
        if cat_code in ['salary', 'spare_parts', 'rent', 'utilities', 'other_expense']:
            expense_categories[cat_code] = {
                'label': cat_name.split(' (')[0],
                'amount': Decimal('0.00'),
                'percent': 0
            }

    period_expenses = [t for t in period_transactions if t.type == 'expense']
    for t in period_expenses:
        if t.category in expense_categories:
            expense_categories[t.category]['amount'] += t.amount
        else:
            if 'other_expense' in expense_categories:
                expense_categories['other_expense']['amount'] += t.amount

    if total_expense > 0:
        for cat in expense_categories:
            expense_categories[cat]['percent'] = int(
                round((expense_categories[cat]['amount'] / total_expense) * 100)
            )

    # Дані для кругової діаграми
    category_labels = []
    category_values = []
    for cat_code, cat_data in expense_categories.items():
        if cat_data['amount'] > 0:
            category_labels.append(cat_data['label'])
            category_values.append(float(cat_data['amount']))

    # Застосовуємо розширені фільтри до списку транзакцій, що відображається в таблиці
    filtered_transactions = period_transactions
    if t_type and t_type in ['income', 'expense']:
        filtered_transactions = filtered_transactions.filter(type=t_type)
    if category and category != 'all':
        filtered_transactions = filtered_transactions.filter(category=category)
    if employee_id_filter and employee_id_filter != 'all':
        try:
            filtered_transactions = filtered_transactions.filter(employee_id=int(employee_id_filter))
        except ValueError:
            pass

    # Окремий запис для виплати заробітних плат (архів виплат)
    salary_payouts = all_transactions.filter(category='salary', date__range=[start_date, end_date])
    if employee_id_filter and employee_id_filter != 'all':
        try:
            salary_payouts = salary_payouts.filter(employee_id=int(employee_id_filter))
        except ValueError:
            pass

    # Сума невиплачених зарплат активним працівникам
    unpaid_salaries = sum(
        sb.current_balance 
        for sb in SalaryBalance.objects.filter(
            employee__station=selected_station, 
            employee__is_active=True
        )
    )

    categories_choices = Transaction.TRANSACTION_CATEGORIES

    context = {
        'user': user,
        'stations': stations,
        'selected_station': selected_station,
        'employees': employees,
        'transactions': filtered_transactions[:100],  # Показуємо до 100 відфільтрованих записів
        'salary_payouts': salary_payouts[:100],        # До 100 записів архіву виплат
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'unpaid_salaries': unpaid_salaries,
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'categories_choices': categories_choices,
        'expense_categories': expense_categories.values(),
        
        # Параметри фільтрації для збереження стану полів
        'selected_type': t_type,
        'selected_category': category,
        'selected_employee_id': employee_id_filter,
        
        # Дані для передачі у скрипт Chart.js
        'chart_dates_json': json.dumps(chart_dates),
        'chart_incomes_json': json.dumps(chart_incomes),
        'chart_expenses_json': json.dumps(chart_expenses),
        'category_labels_json': json.dumps(category_labels),
        'category_values_json': json.dumps(category_values),
    }

    return render(request, 'accounting/dashboard.html', context)

@login_required_session
@role_required('station')
@require_POST
def add_employee_view(request):
    user = get_current_user(request)
    station_id = request.POST.get('station_id')
    station = get_object_or_404(ServiceStation, pk=station_id, user=user)

    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    position = request.POST.get('position', '').strip()
    base_salary = request.POST.get('base_salary', '0.00')
    commission_percent = request.POST.get('commission_percent', '0.00')

    if not full_name or not position:
        messages.error(request, "Ім'я та посада є обов'язковими.")
        return _redirect_to_dashboard(station.pk)

    try:
        Employee.objects.create(
            station=station,
            full_name=full_name,
            phone=phone if phone else None,
            email=email if email else None,
            position=position,
            base_salary=Decimal(base_salary),
            commission_percent=Decimal(commission_percent)
        )
        messages.success(request, f"Працівника {full_name} успішно додано.")
    except (InvalidOperation, Exception) as e:
        messages.error(request, f"Помилка при додаванні працівника: {e}")

    return _redirect_to_dashboard(station.pk)

@login_required_session
@role_required('station')
@require_POST
def edit_employee_view(request, employee_id):
    user = get_current_user(request)
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)

    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    position = request.POST.get('position', '').strip()
    base_salary = request.POST.get('base_salary', '0.00')
    commission_percent = request.POST.get('commission_percent', '0.00')
    is_active = request.POST.get('is_active') == 'true'

    if not full_name or not position:
        messages.error(request, "Ім'я та посада є обов'язковими.")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        employee.full_name = full_name
        employee.phone = phone if phone else None
        employee.email = email if email else None
        employee.position = position
        employee.base_salary = Decimal(base_salary)
        employee.commission_percent = Decimal(commission_percent)
        employee.is_active = is_active
        employee.save()
        messages.success(request, f"Дані працівника {full_name} успішно оновлено.")
    except (InvalidOperation, Exception) as e:
        messages.error(request, f"Помилка при оновленні: {e}")

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
    """
    FIX (CRIT-01): Виплата зарплати з атомарним блокуванням
    через select_for_update() та F() для запобігання race condition.
    """
    user = get_current_user(request)
    employee_id = request.POST.get('employee_id')
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)

    amount_str = request.POST.get('amount', '0.00')
    try:
        amount = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума виплати.")
        return _redirect_to_dashboard(employee.station.pk)

    if amount <= 0:
        messages.error(request, "Сума виплати має бути більшою за нуль.")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        with transaction.atomic():
            # SELECT ... FOR UPDATE — блокує рядок від конкурентних змін
            balance = SalaryBalance.objects.select_for_update().get(
                employee=employee
            )
            if amount > balance.current_balance:
                messages.error(
                    request,
                    f"Сума виплати ({amount} грн) перевищує "
                    f"доступний баланс ({balance.current_balance} грн)."
                )
                return _redirect_to_dashboard(employee.station.pk)

            # F() — атомарне оновлення у БД без race condition
            balance.total_paid = F('total_paid') + amount
            balance.save(update_fields=['total_paid'])

            Transaction.objects.create(
                station=employee.station,
                type='expense',
                category='salary',
                amount=amount,
                description=(
                    f"Виплата зарплати працівнику: "
                    f"{employee.full_name} ({employee.position})"
                ),
                employee=employee,
                date=datetime.date.today()
            )

        messages.success(
            request,
            f"Виплата {amount} грн працівнику {employee.full_name} "
            f"успішно проведена."
        )
    except Exception as e:
        messages.error(request, f"Помилка при виплаті зарплати: {e}")

    return _redirect_to_dashboard(employee.station.pk)

@login_required_session
@role_required('station')
@require_POST
def add_transaction_view(request):
    user = get_current_user(request)
    station_id = request.POST.get('station_id')
    station = get_object_or_404(ServiceStation, pk=station_id, user=user)

    t_type = request.POST.get('type')
    category = request.POST.get('category')
    amount_str = request.POST.get('amount')
    description = request.POST.get('description', '').strip()
    date_str = request.POST.get('date')

    # Валідація типу
    if t_type not in ['income', 'expense']:
        messages.error(request, "Невірний тип операції.")
        return _redirect_to_dashboard(station.pk)

    # Валідація категорії по списку допустимих значень
    valid_categories = dict(Transaction.TRANSACTION_CATEGORIES)
    if not category or category not in valid_categories:
        messages.error(request, "Невірна категорія операції.")
        return _redirect_to_dashboard(station.pk)

    if not amount_str:
        messages.error(request, "Заповніть суму операції.")
        return _redirect_to_dashboard(station.pk)

    try:
        amount = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума операції.")
        return _redirect_to_dashboard(station.pk)

    if amount <= 0:
        messages.error(request, "Сума має бути більшою за нуль.")
        return _redirect_to_dashboard(station.pk)

    try:
        t_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()

        Transaction.objects.create(
            station=station,
            type=t_type,
            category=category,
            amount=amount,
            description=description,
            date=t_date
        )
        messages.success(request, "Операцію успішно додано.")
    except Exception as e:
        messages.error(request, f"Помилка при додаванні операції: {e}")

    return _redirect_to_dashboard(station.pk)

@login_required_session
@role_required('station')
@require_POST
def complete_booking_view(request):
    """
    FIX (CRIT-02, CRIT-03): Завершення ремонту з атомарним блокуванням.
    select_for_update() для booking та salary_balance.
    """
    user = get_current_user(request)
    booking_id = request.POST.get('booking_id')

    actual_price_str = request.POST.get('actual_price')
    employee_id = request.POST.get('employee_id')

    if not actual_price_str:
        messages.error(
            request,
            "Будь ласка, вкажіть фактичну вартість ремонту."
        )
        return redirect('profile')

    try:
        actual_price = Decimal(actual_price_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума вартості ремонту.")
        return redirect('profile')

    if actual_price <= 0:
        messages.error(
            request,
            "Вартість ремонту повинна бути більшою за нуль."
        )
        return redirect('profile')

    try:
        with transaction.atomic():
            # FIX (CRIT-02): Блокуємо рядок booking від паралельних змін
            booking = Booking.objects.select_for_update().get(
                pk=booking_id, station__user=user
            )

            # Перевірка поточного статусу
            if booking.status == 'completed':
                messages.warning(
                    request,
                    f"Заявка #{booking.pk} вже була завершена раніше."
                )
                return redirect(reverse('profile') + '?tab=bookings')

            if booking.status == 'cancelled':
                messages.error(
                    request,
                    f"Неможливо завершити скасовану заявку #{booking.pk}."
                )
                return redirect(reverse('profile') + '?tab=bookings')

            employee = None
            if employee_id:
                employee = get_object_or_404(
                    Employee, pk=employee_id, station=booking.station
                )

            # 1. Позначаємо ремонт як виконаний
            booking.status = 'completed'
            booking.save(update_fields=['status'])

            # 2. Записуємо вартість робіт у доходи СТО
            desc = (
                f"Завершено ремонт за заявкою #{booking.id} "
                f"({booking.service_name or 'Загальні роботи'})"
            )
            if employee:
                desc += f". Виконавець: {employee.full_name}."

            tx = Transaction.objects.create(
                station=booking.station,
                type='income',
                category='service',
                amount=actual_price,
                description=desc,
                booking=booking,
                employee=employee,
                date=datetime.date.today()
            )

            # 3. Нараховуємо майстру комісію
            if employee and employee.commission_percent > 0:
                commission = actual_price * (
                    employee.commission_percent / Decimal('100.00')
                )
                commission = commission.quantize(Decimal('0.01'))

                # FIX (CRIT-03): Атомарне оновлення балансу
                sb = SalaryBalance.objects.select_for_update().get(
                    employee=employee
                )
                sb.total_earned = F('total_earned') + commission
                sb.save(update_fields=['total_earned'])

                tx.description += f" Нараховано комісію: {commission} грн."
                tx.save(update_fields=['description'])

        messages.success(
            request,
            f"Ремонт за заявкою #{booking.id} успішно завершено. "
            f"Суму {actual_price} грн внесено в дохід СТО."
        )
    except Booking.DoesNotExist:
        messages.error(request, "Заявку не знайдено.")
    except Exception as e:
        messages.error(request, f"Помилка при завершенні ремонту: {e}")

    return redirect(reverse('profile') + '?tab=bookings')


@login_required_session
@role_required('station')
def export_transactions_csv(request):
    """
    FIX (SEC-06, ARCH-08): Експорт CSV з санітизацією імені файлу
    та використанням спільної _parse_date_range.
    """
    user = get_current_user(request)
    if not user:
        return redirect('login')

    station_id = request.GET.get('station_id')
    if not station_id:
        messages.error(request, "Не вказано СТО для експорту.")
        return redirect('profile')

    station = get_object_or_404(ServiceStation, pk=int(station_id), user=user)

    # FIX (ARCH-08): Використовуємо спільну utility
    start_date, end_date = _parse_date_range(request)

    t_type = request.GET.get('type')
    category = request.GET.get('category')
    employee_id_filter = request.GET.get('employee_id')

    transactions = Transaction.objects.filter(
        station=station, date__range=[start_date, end_date]
    ).select_related('employee', 'booking')

    if t_type and t_type in ['income', 'expense']:
        transactions = transactions.filter(type=t_type)
    if category and category != 'all':
        transactions = transactions.filter(category=category)
    if employee_id_filter and employee_id_filter != 'all':
        try:
            transactions = transactions.filter(
                employee_id=int(employee_id_filter)
            )
        except ValueError:
            pass

    # FIX (SEC-06): Санітизація імені файлу
    safe_name = re.sub(r'[^\w\s-]', '', station.name).strip()[:50]
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = (
        f'attachment; filename="{safe_name}_report_'
        f'{start_date}_{end_date}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Дата', 'Тип операції', 'Категорія', 'Сума (грн)',
        'Опис', 'ID Заявки', 'Співробітник'
    ])

    for t in transactions:
        writer.writerow([
            t.date.strftime("%d.%m.%Y"),
            t.get_type_display(),
            t.get_category_display(),
            t.amount,
            t.description or '',
            t.booking.id if t.booking else '',
            t.employee.full_name if t.employee else ''
        ])

    return response

