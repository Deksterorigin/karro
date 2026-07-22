from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from main.models import User, ServiceStation, Car, Booking, CarHistory
from .models import Employee, SalaryBalance, Transaction, SparePart, UsedSparePart
import datetime
from decimal import Decimal

class AccountingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Створюємо власника СТО з хешованим паролем
        self.owner = User.objects.create(
            full_name='Олексій Власник',
            phone='+380671111111',
            email='owner@test.com',
            password=make_password('testpassword123'),
            role='station'
        )
        
        # Створюємо клієнта з хешованим паролем
        self.client_user = User.objects.create(
            full_name='Дмитро Клієнт',
            phone='+380672222222',
            email='client@test.com',
            password=make_password('testpassword123'),
            role='client'
        )

        # Створюємо СТО
        self.station = ServiceStation.objects.create(
            name='Карро Сервіс',
            address='вул. Лесі Українки, 10',
            phone='+380673333333',
            user=self.owner,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )
        
        # Додаємо тестовий автомобіль
        self.car = Car.objects.create(
            vin_code='ZPI21TESTVIN12345',
            brand='BMW',
            model='X5',
            year=2021,
            user=self.client_user
        )

    def login_as_owner(self):
        self.client.force_login(self.owner)

    def test_employee_creation_and_balance_signal(self):
        # Додаємо нового працівника
        employee = Employee.objects.create(
            station=self.station,
            full_name='Іван Механік',
            phone='+380674444444',
            position='Механік',
            base_salary=Decimal('1000.00'),
            commission_percent=Decimal('10.00')
        )
        
        # Перевіряємо успішність створення працівника
        self.assertEqual(employee.full_name, 'Іван Механік')
        self.assertEqual(employee.position, 'Механік')
        
        # Перевіряємо, чи автоматично через Django signal створився SalaryBalance
        self.assertTrue(SalaryBalance.objects.filter(employee=employee).exists())
        balance = employee.salary_balance
        self.assertEqual(balance.total_earned, Decimal('0.00'))
        self.assertEqual(balance.total_paid, Decimal('0.00'))
        self.assertEqual(balance.current_balance, Decimal('0.00'))

    def test_manual_transaction_logging(self):
        self.login_as_owner()
        
        # Створюємо вручну витрату на оренду приміщення
        response = self.client.post('/accounting/transaction/add/', {
            'station_id': self.station.pk,
            'type': 'expense',
            'category': 'rent',
            'amount': '5000.00',
            'description': 'Оренда приміщення за липень',
            'date': '2026-07-01'
        })
        
        # Перевіряємо редирект
        self.assertEqual(response.status_code, 302)
        
        # Перевіряємо, чи з'явилася транзакція в базі даних
        tx = Transaction.objects.filter(station=self.station, category='rent').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.type, 'expense')
        self.assertEqual(tx.amount, Decimal('5000.00'))
        self.assertEqual(tx.description, 'Оренда приміщення за липень')

    def test_booking_completion_with_commission(self):
        self.login_as_owner()
        
        # Створюємо працівника
        employee = Employee.objects.create(
            station=self.station,
            full_name='Василь Електрик',
            position='Електрик',
            base_salary=Decimal('1200.00'),
            commission_percent=Decimal('15.00') # 15% комісії від вартості ремонту
        )
        
        # Створюємо запис на ремонт (заявку)
        booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Діагностика електрики',
            description='Світиться чек двигуна',
            status='pending',
            scheduled_time=timezone.make_aware(datetime.datetime(2026, 7, 10, 10, 0))
        )
        
        # Завершуємо ремонт через контролер
        response = self.client.post('/accounting/booking/complete/', {
            'booking_id': booking.id,
            'actual_price': '2000.00',
            'employee_id': employee.pk
        })
        
        # Перевіряємо успішність завершення
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        
        # Перевіряємо запис про надходження коштів у доходах СТО
        tx = Transaction.objects.filter(booking=booking).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.type, 'income')
        self.assertEqual(tx.amount, Decimal('2000.00'))
        self.assertEqual(tx.employee, employee)
        
        # Перевіряємо нарахування відсотку майстру (15% від 2000 = 300 грн)
        balance = employee.salary_balance
        balance.refresh_from_db()
        self.assertEqual(balance.total_earned, Decimal('300.00'))
        self.assertEqual(balance.current_balance, Decimal('300.00'))

    def test_salary_payout_logic(self):
        self.login_as_owner()
        
        # Створюємо працівника
        employee = Employee.objects.create(
            station=self.station,
            full_name='Сергій Приймальник',
            position='Приймальник',
            base_salary=Decimal('800.00'),
            commission_percent=Decimal('5.00')
        )
        
        # Безпосередньо записуємо йому накопичений заробіток у базу
        balance = employee.salary_balance
        balance.total_earned = Decimal('1500.00')
        balance.save()
        
        # Проводимо виплату зарплати на суму 1000 грн
        response = self.client.post('/accounting/employee/pay/', {
            'employee_id': employee.pk,
            'amount': '1000.00'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Перевіряємо оновлення поточного балансу
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('1000.00'))
        self.assertEqual(balance.current_balance, Decimal('500.00'))
        
        # Перевіряємо створення транзакції з виплати зарплати в журналі витрат
        tx = Transaction.objects.filter(employee=employee, category='salary').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.type, 'expense')
        self.assertEqual(tx.amount, Decimal('1000.00'))
        
        # Намагаємося виплатити більше, ніж є на балансі (операція має відхилитися)
        response_fail = self.client.post('/accounting/employee/pay/', {
            'employee_id': employee.pk,
            'amount': '600.00'
        })
        
        # Перевіряємо, що баланс не змінився
        balance.refresh_from_db()
        self.assertEqual(balance.total_paid, Decimal('1000.00'))

    def test_complete_already_completed_booking(self):
        """Перевірка, що повторне завершення вже завершеної заявки не створює дублікати."""
        self.login_as_owner()
        
        booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Заміна масла',
            description='Стандартна заміна',
            status='completed',
            scheduled_time=timezone.make_aware(datetime.datetime(2026, 8, 1, 10, 0))
        )
        
        response = self.client.post('/accounting/booking/complete/', {
            'booking_id': booking.id,
            'actual_price': '500.00',
        })
        
        self.assertEqual(response.status_code, 302)
        # Не має бути створено жодної транзакції
        self.assertEqual(Transaction.objects.filter(booking=booking).count(), 0)

    def test_invalid_transaction_category(self):
        """Перевірка валідації категорії транзакції."""
        self.login_as_owner()
        
        response = self.client.post('/accounting/transaction/add/', {
            'station_id': self.station.pk,
            'type': 'expense',
            'category': 'invalid_category',
            'amount': '100.00',
            'description': 'Тестова операція',
            'date': '2026-07-01'
        })
        
        self.assertEqual(response.status_code, 302)
        # Транзакція не має бути створена
        self.assertEqual(Transaction.objects.filter(station=self.station, description='Тестова операція').count(), 0)

    def test_negative_amount_transaction(self):
        """Перевірка, що від'ємна сума транзакції відхиляється."""
        self.login_as_owner()
        
        response = self.client.post('/accounting/transaction/add/', {
            'station_id': self.station.pk,
            'type': 'expense',
            'category': 'rent',
            'amount': '-500.00',
            'description': 'Мінусова операція',
            'date': '2026-07-01'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.filter(station=self.station, description='Мінусова операція').count(), 0)

    def test_complete_booking_creates_car_history(self):
        """Перевірка, що завершення заявки створює відповідний запис в історії обслуговування авто."""
        self.login_as_owner()
        
        booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Діагностика ходової',
            description='Стук спереду',
            status='pending',
            scheduled_time=timezone.make_aware(datetime.datetime(2026, 8, 5, 12, 0))
        )
        
        response = self.client.post('/accounting/booking/complete/', {
            'booking_id': booking.id,
            'actual_price': '1500.00',
            'mileage': '125000',
            'work_list': 'Заміна важелів підвіски, розвал-сходження',
            'spare_parts': 'Важіль передній 2шт'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Перевіряємо статус заявки
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        
        # Перевіряємо запис в історії авто
        history = CarHistory.objects.filter(booking=booking).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.car, self.car)
        self.assertEqual(history.mileage, 125000)
        self.assertEqual(history.price, Decimal('1500.00'))
        self.assertEqual(history.work_list, 'Заміна важелів підвіски, розвал-сходження')
        self.assertEqual(history.spare_parts, 'Важіль передній 2шт')

    def test_inventory_crud_operations(self):
        """Перевірка додавання, редагування та видалення запчастини на складі."""
        self.login_as_owner()

        # 1. Додавання запчастини
        response = self.client.post('/accounting/inventory/add/', {
            'station_id': self.station.pk,
            'name': 'Фільтр масляний Mann',
            'sku': 'W712-95',
            'quantity': '15',
            'cost_price': '180.00',
            'selling_price': '320.00',
            'min_quantity': '4'
        })
        self.assertEqual(response.status_code, 302)

        part = SparePart.objects.filter(station=self.station, sku='W712-95').first()
        self.assertIsNotNone(part)
        self.assertEqual(part.quantity, 15)
        self.assertEqual(part.cost_price, Decimal('180.00'))
        self.assertEqual(part.selling_price, Decimal('320.00'))

        # 2. Редагування запчастини
        response_edit = self.client.post('/accounting/inventory/edit/', {
            'part_id': part.pk,
            'name': 'Фільтр масляний Mann Premium',
            'sku': 'W712-95',
            'quantity': '20',
            'cost_price': '190.00',
            'selling_price': '350.00',
            'min_quantity': '5'
        })
        self.assertEqual(response_edit.status_code, 302)
        part.refresh_from_db()
        self.assertEqual(part.name, 'Фільтр масляний Mann Premium')
        self.assertEqual(part.quantity, 20)

        # 3. Видалення запчастини
        response_del = self.client.post('/accounting/inventory/delete/', {
            'part_id': part.pk
        })
        self.assertEqual(response_del.status_code, 302)
        self.assertFalse(SparePart.objects.filter(pk=part.pk).exists())

    def test_complete_booking_deducts_inventory_and_records_cost(self):
        """Перевірка автоматичного списання деталей зі складу та фіксації собівартості у витратах СТО."""
        self.login_as_owner()

        # Створюємо запчастини на складі
        oil = SparePart.objects.create(
            station=self.station,
            name='Мастило Shell 5W-30',
            sku='SHELL-5W30',
            quantity=10,
            cost_price=Decimal('250.00'),
            selling_price=Decimal('400.00'),
            min_quantity=2
        )

        booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Заміна мастила',
            description='Планове ТО',
            status='pending',
            scheduled_time=timezone.make_aware(datetime.datetime(2026, 8, 10, 11, 0))
        )

        import json
        used_parts_json = json.dumps([
            {'part_id': oil.pk, 'qty': 4}
        ])

        response = self.client.post('/accounting/booking/complete/', {
            'booking_id': booking.id,
            'actual_price': '2200.00',
            'mileage': '150000',
            'work_list': 'Заміна мастила та масляного фільтра',
            'spare_parts': 'Комплект ТО',
            'used_parts_json': used_parts_json
        })

        self.assertEqual(response.status_code, 302)

        # 1. Перевіряємо списання залишку: було 10, списано 4 -> залишилося 6
        oil.refresh_from_db()
        self.assertEqual(oil.quantity, 6)

        # 2. Перевіряємо створення UsedSparePart
        used = UsedSparePart.objects.filter(booking=booking, spare_part=oil).first()
        self.assertIsNotNone(used)
        self.assertEqual(used.quantity, 4)
        self.assertEqual(used.cost_price, Decimal('250.00'))

        # 3. Перевіряємо створення витратної транзакції собівартості (4 * 250 = 1000 грн)
        tx_cost = Transaction.objects.filter(booking=booking, category='spare_parts', type='expense').first()
        self.assertIsNotNone(tx_cost)
        self.assertEqual(tx_cost.amount, Decimal('1000.00'))


