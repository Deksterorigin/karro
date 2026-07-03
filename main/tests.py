# pyrefly: ignore [missing-import]
import json
import datetime
from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from main.models import User, ServiceStation, Car, Booking

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
