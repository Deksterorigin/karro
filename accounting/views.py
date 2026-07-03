from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from main.decorators import login_required_session, role_required
from main.models import User, ServiceStation, Booking
from main.views import get_current_user
from .models import Employee, SalaryBalance, Transaction
import datetime
from decimal import Decimal, InvalidOperation
import calendar


def _redirect_to_dashboard(station_pk):
    """Перенаправлення на дашборд бухгалтерії для конкретної СТО."""
    return redirect(reverse('accounting:dashboard') + f'?station_id={station_pk}')


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

    # Задаємо діапазон дат. За замовчуванням беремо поточний місяць
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

    # Працівники цієї станції
    employees = Employee.objects.filter(station=selected_station).select_related('salary_balance')

    # Отримуємо всі фінансові записи цієї станції
    all_transactions = Transaction.objects.filter(station=selected_station).select_related('employee', 'booking')
    
    # Фільтруємо транзакції за обраний період часу
    period_transactions = all_transactions.filter(date__range=[start_date, end_date])

    # Розрахунок загальних фінансових показників з правильною ініціалізацією Decimal
    total_income = sum(
        (t.amount for t in period_transactions if t.type == 'income'),
        Decimal('0.00')
    )
    total_expense = sum(
        (t.amount for t in period_transactions if t.type == 'expense'),
        Decimal('0.00')
    )
    net_profit = total_income - total_expense

    # Сума невиплачених зарплат активним працівникам
    unpaid_salaries = sum(
        sb.current_balance 
        for sb in SalaryBalance.objects.filter(
            employee__station=selected_station, 
            employee__is_active=True
        )
    )

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

    categories_choices = Transaction.TRANSACTION_CATEGORIES

    context = {
        'user': user,
        'stations': stations,
        'selected_station': selected_station,
        'employees': employees,
        'transactions': period_transactions[:100],  # Відображаємо останні 100 операцій
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'unpaid_salaries': unpaid_salaries,
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'categories_choices': categories_choices,
        'expense_categories': expense_categories.values(),
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

    balance = employee.salary_balance
    if amount > balance.current_balance:
        messages.error(request, f"Сума виплати ({amount} грн) перевищує доступний баланс ({balance.current_balance} грн).")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        # Збільшуємо загальну суму виплачених коштів
        balance.total_paid += amount
        balance.save()

        # Фіксуємо виплату в журналі витрат СТО
        Transaction.objects.create(
            station=employee.station,
            type='expense',
            category='salary',
            amount=amount,
            description=f"Виплата зарплати працівнику: {employee.full_name} ({employee.position})",
            employee=employee,
            date=datetime.date.today()
        )
        messages.success(request, f"Виплата {amount} грн працівнику {employee.full_name} успішно проведена.")
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
    user = get_current_user(request)
    booking_id = request.POST.get('booking_id')
    booking = get_object_or_404(Booking, pk=booking_id, station__user=user)

    # Перевірка поточного статусу — не дозволяти повторне завершення або завершення скасованих
    if booking.status == 'completed':
        messages.warning(request, f"Заявка #{booking.pk} вже була завершена раніше.")
        return redirect(reverse('profile') + '?tab=bookings')

    if booking.status == 'cancelled':
        messages.error(request, f"Неможливо завершити скасовану заявку #{booking.pk}.")
        return redirect(reverse('profile') + '?tab=bookings')

    actual_price_str = request.POST.get('actual_price')
    employee_id = request.POST.get('employee_id')

    if not actual_price_str:
        messages.error(request, "Будь ласка, вкажіть фактичну вартість ремонту.")
        return redirect('profile')

    try:
        actual_price = Decimal(actual_price_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума вартості ремонту.")
        return redirect('profile')

    if actual_price <= 0:
        messages.error(request, "Вартість ремонту повинна бути більшою за нуль.")
        return redirect('profile')

    try:
        employee = None
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id, station=booking.station)

        # 1. Позначаємо ремонт у заявці як виконаний
        booking.status = 'completed'
        booking.save()

        # 2. Записуємо вартість робіт у доходи СТО
        desc = f"Завершено ремонт за заявкою #{booking.id} ({booking.service_name or 'Загальні роботи'})"
        if employee:
            desc += f". Виконавець: {employee.full_name}."

        transaction = Transaction.objects.create(
            station=booking.station,
            type='income',
            category='service',
            amount=actual_price,
            description=desc,
            booking=booking,
            employee=employee,
            date=datetime.date.today()
        )

        # 3. Нараховуємо майстру його відсоток від вартості виконаних послуг
        if employee and employee.commission_percent > 0:
            commission = actual_price * (employee.commission_percent / Decimal('100.00'))
            commission = commission.quantize(Decimal('0.01'))

            # Додаємо нараховану комісію до зароблених грошей працівника
            sb = employee.salary_balance
            sb.total_earned += commission
            sb.save()

            # Додаємо відомості про нараховану комісію до журналу транзакцій
            transaction.description += f" Нараховано комісію: {commission} грн."
            transaction.save()

        messages.success(request, f"Ремонт за заявкою #{booking.id} успішно завершено. Суму {actual_price} грн внесено в дохід СТО.")
    except Exception as e:
        messages.error(request, f"Помилка при завершенні ремонту: {e}")

    return redirect(reverse('profile') + '?tab=bookings')
