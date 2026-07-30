import json
import datetime
from django.test import TestCase, Client

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from decimal import Decimal
from main.models import User, ServiceStation, Car, Booking, Notification, StationBox, BookingChatMessage

class BookingAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Створюємо користувачів з хешованими паролями
        self.client_user = User.objects.create(
            full_name='Test Client',
            phone='+380501111111',
            email='client@test.com',
            password=make_password('testpassword'),
            role='client'
        )
        self.station_user = User.objects.create(
            full_name='Test Station Admin',
            phone='+380502222222',
            email='station@test.com',
            password=make_password('testpassword'),
            role='station'
        )
        # Створюємо СТО
        self.station = ServiceStation.objects.create(
            name='Super Auto Service',
            address='Shevchenka St, 1',
            phone='+380503333333',
            user=self.station_user,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )
        # Створюємо автомобіль
        self.car = Car.objects.create(
            vin_code='1234567890ABCDEFG',
            brand='Audi',
            model='A6',
            year=2020,
            user=self.client_user
        )

    def _future_time(self, hour=12):
        """Генерує дату/час у майбутньому з заданою годиною."""
        future_date = timezone.now().date() + datetime.timedelta(days=7)
        return f'{future_date.isoformat()}T{hour:02d}:00:00'

    def login_client(self):
        self.client.force_login(self.client_user)

    def test_unauthorized_access(self):
        # Перевірка неавторизованого доступу (має повернути 401)
        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station.pk,
                'car_id': self.car.vin_code,
                'service_name': 'Заміна мастила',
                'description': 'Заміна масла в двигуні',
                'scheduled_time': self._future_time(10)
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_successful_booking(self):
        # Успішне створення запису в робочі години
        self.login_client()
        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station.pk,
                'car_id': self.car.vin_code,
                'service_name': 'Заміна мастила',
                'description': 'Заміна масла в двигуні',
                'scheduled_time': self._future_time(12)
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(Booking.objects.filter(client=self.client_user, service_name='Заміна мастила').exists())

    def test_off_hours_booking(self):
        # Запис у неробочі години (має повернути 400)
        self.login_client()
        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station.pk,
                'car_id': self.car.vin_code,
                'service_name': 'Заміна мастила',
                'description': 'Заміна масла в двигуні',
                'scheduled_time': self._future_time(22)
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('працює з 09:00 до 18:00', response.json()['message'])

    def test_invalid_car_ownership(self):
        # Запис для іншого автомобіля (має повернути 400)
        other_user = User.objects.create(
            full_name='Other Client',
            phone='+380504444444',
            email='other@test.com',
            password=make_password('testpassword'),
            role='client'
        )
        other_car = Car.objects.create(
            vin_code='ABC123XYZ78901234',
            brand='BMW',
            model='M5',
            year=2021,
            user=other_user
        )
        self.login_client()
        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station.pk,
                'car_id': other_car.vin_code,
                'service_name': 'Заміна мастила',
                'description': 'Заміна масла в двигуні',
                'scheduled_time': self._future_time(12)
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('не належить вам', response.json()['message'])


class NotificationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create(
            full_name='Test Client',
            phone='+380501111111',
            email='client@test.com',
            password=make_password('testpassword'),
            role='client'
        )
        self.station_user = User.objects.create(
            full_name='Test Station Admin',
            phone='+380502222222',
            email='station@test.com',
            password=make_password('testpassword'),
            role='station'
        )
        self.station = ServiceStation.objects.create(
            name='Super Auto Service',
            address='Shevchenka St, 1',
            phone='+380503333333',
            user=self.station_user,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )
        self.car = Car.objects.create(
            vin_code='1234567890ABCDEFG',
            brand='Audi',
            model='A6',
            year=2020,
            user=self.client_user
        )

    def login_client(self):
        self.client.force_login(self.client_user)

    def login_owner(self):
        self.client.force_login(self.station_user)

    def test_notification_workflow(self):
        # 1. Створюємо заявку від імені клієнта
        self.login_client()
        future_date = timezone.now().date() + datetime.timedelta(days=7)
        scheduled_time = f'{future_date.isoformat()}T12:00:00'
        
        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station.pk,
                'car_id': self.car.vin_code,
                'service_name': 'Діагностика',
                'description': 'Діагностика підвіски',
                'scheduled_time': scheduled_time
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Перевіряємо, що сповіщення для власника СТО було створено в БД
        self.assertTrue(Notification.objects.filter(recipient=self.station_user).exists())
        notification = Notification.objects.get(recipient=self.station_user)
        self.assertEqual(notification.is_read, False)
        self.assertIn('Нова заявка', notification.message)
        
        # 2. Отримуємо список сповіщень власником
        self.login_owner()
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['unread_count'], 1)
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['id'], notification.id)
        self.assertEqual(data['notifications'][0]['is_read'], False)
        
        # 3. Позначаємо сповіщення як прочитане
        response = self.client.post(f'/api/notifications/mark-read/{notification.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Перевіряємо оновлення в БД
        notification.refresh_from_db()
        self.assertEqual(notification.is_read, True)
        
        # Отримуємо список знову і перевіряємо unread_count
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.json()['unread_count'], 0)
        
        # 4. Позначаємо всі як прочитані (для перевірки масового API)
        # Створимо ще одне непрочитане сповіщення вручну
        booking_mock = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Інше',
            description='Опис',
            scheduled_time=timezone.now()
        )
        Notification.objects.create(
            recipient=self.station_user,
            booking=booking_mock,
            message='Ще одне сповіщення'
        )
        
        # Перевіряємо unread_count = 1
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.json()['unread_count'], 1)
        
        # Позначаємо все як прочитане
        response = self.client.post('/api/notifications/mark-all-read/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Перевіряємо unread_count = 0
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.json()['unread_count'], 0)


class BookingCalendarTests(TestCase):
    """
    Тести для інтерактивного календаря, робочих боксів та тайм-слотів.
    """
    def setUp(self):
        # Створюємо користувачів
        self.owner = User.objects.create_user(
            email='owner@test.com',
            full_name='Власник СТО',
            phone='+380991111111',
            role='station',
            password='password123'
        )
        self.client_user = User.objects.create_user(
            email='client@test.com',
            full_name='Клієнт Тест',
            phone='+380992222222',
            role='client',
            password='password123'
        )
        
        # Створюємо СТО
        self.station = ServiceStation.objects.create(
            name='Тестова СТО Календар',
            city='Київ',
            address='вулиця Тестова, 1',
            phone='+380441112233',
            user=self.owner,
            opening_time='09:00',
            closing_time='18:00'
        )
        
        # Створюємо бокси (2 активних бокси)
        self.box1 = StationBox.objects.create(station=self.station, name='Бокс 1', is_active=True)
        self.box2 = StationBox.objects.create(station=self.station, name='Бокс 2', is_active=True)
        
        # Створюємо автомобіль
        self.car = Car.objects.create(
            vin_code='12345678901234567',
            brand='Audi',
            model='A6',
            year=2020,
            user=self.client_user
        )

    def test_get_available_slots(self):
        """Перевірка отримання списку вільних часових слотів."""
        self.client.force_login(self.client_user)
        
        # Запит на завтрашній день
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        tomorrow_str = tomorrow.isoformat()
        
        response = self.client.get(f'/api/stations/{self.station.pk}/available-slots/?date={tomorrow_str}&duration=60')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('09:00', data['slots'])
        self.assertIn('10:00', data['slots'])

    def test_booking_box_auto_assignment_and_overbooking(self):
        """Перевірка автоматичного призначення боксів та запобігання овербукінгу."""
        self.client.force_login(self.client_user)
        
        # Завтра о 10:00
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        scheduled_time = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 0)))
        scheduled_time_str = scheduled_time.strftime('%Y-%m-%dT%H:%M')
        
        # 1. Записуємо першу машину
        data = {
            'station_id': self.station.pk,
            'car_id': self.car.vin_code,
            'service_name': 'Заміна олії',
            'description': 'Планове ТО',
            'scheduled_time': scheduled_time_str,
            'duration': 60
        }
        response = self.client.post('/api/bookings/create/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Перевіряємо, що перша заявка отримала якийсь бокс
        b1 = Booking.objects.get(description='Планове ТО')
        self.assertIsNotNone(b1.box)
        
        # 2. Записуємо другу машину на той самий час (має зайняти другий бокс)
        car2 = Car.objects.create(
            vin_code='76543210987654321',
            brand='BMW',
            model='X5',
            year=2021,
            user=self.client_user
        )
        data['car_id'] = car2.vin_code
        data['description'] = 'Ремонт підвіски'
        response = self.client.post('/api/bookings/create/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        b2 = Booking.objects.get(description='Ремонт підвіски')
        self.assertIsNotNone(b2.box)
        self.assertNotEqual(b1.box, b2.box)  # Вони мають бути на різних боксах
        
        # 3. Спроба записати третю машину на той самий час (має повернути помилку, бо всього 2 бокси)
        car3 = Car.objects.create(
            vin_code='11111111111111111',
            brand='Opel',
            model='Astra',
            year=2015,
            user=self.client_user
        )
        data['car_id'] = car3.vin_code
        data['description'] = 'Комп\'ютерна діагностика'
        response = self.client.post('/api/bookings/create/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('усі бокси вже зайняті', response.json()['message'])

    def test_reschedule_booking(self):
        """Перевірка перенесення часу замовлення в календарі (drag-and-drop)."""
        self.client.force_login(self.owner) # Робить власник
        
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        scheduled_time = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 0)))
        
        booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Діагностика',
            description='Стук попереду',
            scheduled_time=scheduled_time,
            duration=60,
            box=self.box1
        )
        
        # Переносимо на 12:00
        new_time = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(12, 0)))
        data = {
            'scheduled_time': new_time.isoformat()
        }
        
        response = self.client.post(f'/api/bookings/{booking.pk}/reschedule/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        booking.refresh_from_db()
        self.assertEqual(booking.scheduled_time, new_time)


class BookingChatTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create(
            full_name='Іван Клієнт',
            phone='+380509998877',
            email='client@test.com',
            password=make_password('password123'),
            role='client'
        )
        self.station_user = User.objects.create(
            full_name='Петро Механік',
            phone='+380679998877',
            email='station@test.com',
            password=make_password('password123'),
            role='station'
        )
        self.station = ServiceStation.objects.create(
            user=self.station_user,
            name='Тестове СТО',
            city='Київ',
            address='вул. Центральна, 1'
        )
        self.car = Car.objects.create(
            user=self.client_user,
            vin_code='1HGBH41JXMN109999',
            brand='Honda',
            model='Civic',
            year=2019
        )
        self.booking = Booking.objects.create(
            client=self.client_user,
            station=self.station,
            car=self.car,
            service_name='Діагностика гальмівної системи',
            description='Скрип при гальмуванні',
            status='confirmed',
            scheduled_time=timezone.now()
        )

    def login_client(self):
        self.client.force_login(self.client_user)

    def login_station(self):
        self.client.force_login(self.station_user)

    def test_send_and_get_chat_messages(self):
        """Перевірка надсилання та отримання повідомлень у чаті замовлення."""
        # 1. Механік надсилає повідомлення про зношені колодки з пропозицією додаткової суми
        self.login_station()
        response = self.client.post(f'/api/bookings/{self.booking.pk}/chat/', {
            'text': 'Знайшли проблему: колодки зношені на 90%, потрібно міняти.',
            'proposed_cost': '850.00'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

        # Перевіряємо що у базі створилося повідомлення
        msg = BookingChatMessage.objects.filter(booking=self.booking).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.sender, self.station_user)
        self.assertEqual(msg.proposed_cost, Decimal('850.00'))

        # Перевіряємо що клієнту відправилося сповіщення Notification
        notif = Notification.objects.filter(recipient=self.client_user, booking=self.booking).first()
        self.assertIsNotNone(notif)
        self.assertIn('Нове повідомлення', notif.message)

        # 2. Клієнт отримує список повідомлень через GET API
        self.login_client()
        response_get = self.client.get(f'/api/bookings/{self.booking.pk}/chat/')
        self.assertEqual(response_get.status_code, 200)
        data = response_get.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['text'], 'Знайшли проблему: колодки зношені на 90%, потрібно міняти.')
        self.assertFalse(data['messages'][0]['is_me'])

    def test_client_approve_proposed_cost(self):
        """Перевірка підтвердження клієнтом додаткових робіт / вартості."""
        msg = BookingChatMessage.objects.create(
            booking=self.booking,
            sender=self.station_user,
            text='Заміна додаткових пильовиків',
            proposed_cost=Decimal('450.00')
        )

        self.login_client()
        response = self.client.post(f'/api/chat-message/{msg.pk}/approval/', {
            'action': 'approve'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_approved'])

        msg.refresh_from_db()
        self.assertTrue(msg.is_approved)

        # Перевіряємо сповіщення СТО
        notif = Notification.objects.filter(recipient=self.station_user, booking=self.booking).first()
        self.assertIsNotNone(notif)
        self.assertIn('підтвердив', notif.message)

