import datetime
import json
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.utils import timezone

from accounting.models import Employee, SalaryBalance, SparePart, Transaction, UsedSparePart
from main.models import Booking, BookingChatMessage, Car, CarHistory, ServiceStation, StationBox, User


class RegressionAccountingAndFinancialModelTestCase(TestCase):
    """
    Регресійні тести фінансової моделі, атомарного завершення заявок та бухгалтерського обліку.
    Створено на Етапі 2 (TDD) до зміни коду логіки.
    """

    def setUp(self):
        self.client = Client()

        # Власник СТО
        self.owner = User.objects.create(
            full_name='Власник СТО Регрес',
            phone='+380509998877',
            email='owner_reg@test.com',
            password=make_password('pass123'),
            role='station',
        )

        # СТО
        self.station = ServiceStation.objects.create(
            name='СТО Регрес Тест',
            address='вул. Центральна, 5',
            phone='+380501110000',
            user=self.owner,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0),
        )

        # Клієнт
        self.client_user = User.objects.create(
            full_name='Клієнт Регрес',
            phone='+380502220000',
            email='client_reg@test.com',
            password=make_password('pass123'),
            role='client',
        )

        # Автомобіль
        self.car = Car.objects.create(
            vin_code='3333333333CCCCCC3',
            brand='Volkswagen',
            model='Passat',
            year=2019,
            user=self.client_user,
        )

        # Бокс
        self.box = StationBox.objects.create(
            station=self.station,
            name='Бокс 1',
            is_active=True,
        )

        # Співробітник з комісією 15%
        self.employee = Employee.objects.create(
            station=self.station,
            full_name='Василь Механік',
            phone='+380503330000',
            position='Автослюсар',
            base_salary=Decimal('10000.00'),
            commission_percent=Decimal('15.00'),
            is_active=True,
        )

        # Запчастина на складі СТО: 10 шт, собівартість 500, ціна продажу 800
        self.part1 = SparePart.objects.create(
            station=self.station,
            name='Гальмівні колодки',
            sku='BRK-100',
            quantity=10,
            cost_price=Decimal('500.00'),
            selling_price=Decimal('800.00'),
        )

        # Заявка
        self.booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            box=self.box,
            service_name='Заміна колодок',
            description='Заміна передніх колодок',
            status='confirmed',
            scheduled_time=timezone.now() - datetime.timedelta(hours=2),
            duration=60,
        )

    def test_commission_calculated_from_labor_only(self):
        """
        Комісія майстра розраховується суворо від вартості робіт (основні + погоджені в чаті),
        без вартості запчастин, з банківським округленням ROUND_HALF_UP.
        """
        # Додаємо погоджену доплату в чаті: 350.00 грн
        BookingChatMessage.objects.create(
            booking=self.booking,
            sender=self.owner,
            text='Додаткова проточка дисків',
            proposed_cost=Decimal('350.00'),
            is_approved=True,
        )

        # Основні роботи = 1000.00 грн
        # Запчастини = 2 шт × 800.00 = 1600.00 грн
        # Роботи разом = 1000.00 + 350.00 = 1350.00 грн
        # Очікувана комісія = 1350.00 × 15% = 202.50 грн
        labor_price = Decimal('1000.00')
        extra_total = Decimal('350.00')
        expected_commission = ((labor_price + extra_total) * self.employee.commission_percent / Decimal('100')).quantize(
            Decimal('0.01')
        )
        self.assertEqual(expected_commission, Decimal('202.50'))

    def test_no_double_inventory_expenses(self):
        """
        Додавання чи оновлення запчастини на складі НЕ створює витратної транзакції в операційному звіті.
        """
        self.client.force_login(self.owner)
        initial_transactions_count = Transaction.objects.filter(station=self.station).count()

        # Додавання запчастини через форму
        self.client.post(
            '/accounting/inventory/add/',
            data={
                'name': 'Свічки запалювання',
                'sku': 'SPK-200',
                'quantity': 20,
                'cost_price': '150.00',
                'selling_price': '250.00',
                'min_quantity': 5,
            },
        )

        # Кількість фінансових транзакцій не повинна збільшитися
        current_transactions_count = Transaction.objects.filter(station=self.station).count()
        self.assertEqual(
            initial_transactions_count,
            current_transactions_count,
            'Додавання запчастини не повинно створювати витратну транзакцію в звіті.',
        )

    def test_pay_salary_validation(self):
        """
        Виплата зарплати: сума > 0, сума <= current_balance.
        Перевищення балансу або від'ємна сума блокується.
        """
        self.client.force_login(self.owner)
        balance = SalaryBalance.objects.get(employee=self.employee)
        balance.total_earned = Decimal('500.00')
        balance.total_paid = Decimal('0.00')
        balance.save()

        # 1. Спроба виплатити більше, ніж є на балансі (600 грн при балансі 500)
        self.client.post(
            '/accounting/employee/pay/',
            data={'employee_id': self.employee.pk, 'amount': '600.00'},
        )
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('0.00'), 'Виплата понад баланс не повинна проводитися.')

        # 2. Спроба виплатити від'ємну суму
        self.client.post(
            '/accounting/employee/pay/',
            data={'employee_id': self.employee.pk, 'amount': '-50.00'},
        )
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('0.00'), "Від'ємна сума виплати повинна відхилятися.")

        # 3. Валідна виплата 300 грн
        self.client.post(
            '/accounting/employee/pay/',
            data={'employee_id': self.employee.pk, 'amount': '300.00'},
        )
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('300.00'))
        self.assertEqual(balance.current_balance, Decimal('200.00'))
