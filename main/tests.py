# pyrefly: ignore [missing-import]
import json
import datetime
from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from main.models import User, ServiceStation, Car, Booking, Notification

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
        session = self.client.session
        session['user_id'] = self.client_user.user_id
        session['user_name'] = self.client_user.full_name
        session.save()

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
        self.assertIn('СТО працює з 09:00 до 18:00', response.json()['message'])

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
        session = self.client.session
        session['user_id'] = self.client_user.user_id
        session['user_name'] = self.client_user.full_name
        session.save()

    def login_owner(self):
        session = self.client.session
        session['user_id'] = self.station_user.user_id
        session['user_name'] = self.station_user.full_name
        session.save()

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
