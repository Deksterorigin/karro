import datetime
import json
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.utils import timezone

from main.models import (
    Booking,
    BookingChatMessage,
    Car,
    Notification,
    Service,
    ServiceStation,
    StationBox,
    User,
)


class RegressionSecurityAndContractsTestCase(TestCase):
    """
    Регресійні тести безпеки (BOLA/IDOR), контрактів та захисту цілісності даних.
    Створено на Етапі 2 (TDD) до зміни бізнес-коду.
    """

    def setUp(self):
        self.client = Client()

        # Клієнт 1 (власник заявки)
        self.client_a = User.objects.create(
            full_name='Клієнт А',
            phone='+380501112233',
            email='client_a@test.com',
            password=make_password('pass123'),
            role='client',
        )

        # Клієнт 2 (сторонній клієнт)
        self.client_b = User.objects.create(
            full_name='Клієнт Б',
            phone='+380502223344',
            email='client_b@test.com',
            password=make_password('pass123'),
            role='client',
        )

        # Власник СТО 1
        self.owner_a = User.objects.create(
            full_name='Власник СТО А',
            phone='+380503334455',
            email='owner_a@test.com',
            password=make_password('pass123'),
            role='station',
        )

        # Власник СТО 2 (сторонній)
        self.owner_b = User.objects.create(
            full_name='Власник СТО Б',
            phone='+380504445566',
            email='owner_b@test.com',
            password=make_password('pass123'),
            role='station',
        )

        # Станція СТО 1
        self.station_a = ServiceStation.objects.create(
            name='СТО Альфа',
            address='вул. Перша, 1',
            phone='+380505556677',
            user=self.owner_a,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0),
        )

        # Станція СТО 2
        self.station_b = ServiceStation.objects.create(
            name='СТО Бета',
            address='вул. Друга, 2',
            phone='+380506667788',
            user=self.owner_b,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0),
        )

        # Автомобіль Клієнта А
        self.car_a = Car.objects.create(
            vin_code='1111111111AAAAAA1',
            brand='Toyota',
            model='Corolla',
            year=2021,
            user=self.client_a,
        )

        # Автомобіль Клієнта Б
        self.car_b = Car.objects.create(
            vin_code='2222222222BBBBBB2',
            brand='Honda',
            model='Civic',
            year=2022,
            user=self.client_b,
        )

        # Бокс для СТО 1
        self.box_a = StationBox.objects.create(
            station=self.station_a,
            name='Бокс 1',
            is_active=True,
        )

        # Заявка Клієнта А на СТО 1
        self.booking_a = Booking.objects.create(
            client=self.client_a,
            station=self.station_a,
            car=self.car_a,
            box=self.box_a,
            service_name='Діагностика',
            description='Стук у підвісці',
            status='confirmed',
            scheduled_time=timezone.now() + datetime.timedelta(days=2),
            duration=60,
        )

    def test_banned_direct_status_completion(self):
        """
        Заборонено встановлення статусу completed через простий селект статусів.
        Завершення має проходити виключно через бухгалтерську процедуру.
        """
        self.client.force_login(self.owner_a)
        response = self.client.post(
            '/profile/',
            data={
                'action': 'update_booking_status',
                'booking_id': self.booking_a.pk,
                'status': 'completed',
            },
        )
        self.booking_a.refresh_from_db()
        self.assertNotEqual(
            self.booking_a.status,
            'completed',
            'Статус заявки не повинен переходити у completed через звичайний селект статусів.',
        )

    def test_booking_fails_without_active_boxes(self):
        """
        Якщо на СТО немає жодного активного боксу, створення заявки має повертати помилку
        і не повинно створювати 'Бокс 1' на льоту.
        """
        # Деактивуємо всі бокси на СТО А
        self.box_a.is_active = False
        self.box_a.save()

        self.client.force_login(self.client_a)
        future_time = (timezone.now() + datetime.timedelta(days=3)).replace(hour=11, minute=0, second=0).isoformat()

        response = self.client.post(
            '/api/bookings/create/',
            data=json.dumps({
                'station_id': self.station_a.pk,
                'car_id': self.car_a.vin_code,
                'service_name': 'Заміна мастила',
                'description': 'Планове ТО',
                'scheduled_time': future_time,
                'duration': 60,
            }),
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('бокс', data.get('message', '').lower())
        # Переконуємося, що не було створено новий активний бокс
        self.assertEqual(self.station_a.boxes.filter(is_active=True).count(), 0)

    def test_idor_pdf_access_returns_404_for_non_participant(self):
        """
        Сторонній користувач (Клієнт Б) не має доступу до PDF-акта заявки Клієнта А на СТО А.
        Повинен повертатися HTTP 404 (захист BOLA/IDOR на рівні запиту до БД).
        """
        self.client.force_login(self.client_b)
        response = self.client.get(f'/booking/{self.booking_a.pk}/act/pdf/')
        self.assertEqual(
            response.status_code,
            404,
            'Сторонній користувач повинен отримувати 404 при спробі доступу до чужого акта.',
        )

    def test_idor_chat_access_rejected_for_non_participant(self):
        """
        Сторонній користувач (Клієнт Б або Власник СТО Б) не повинен отримувати доступ до чату чужої заявки.
        """
        self.client.force_login(self.client_b)
        response = self.client.get(f'/api/bookings/{self.booking_a.pk}/chat/')
        self.assertIn(response.status_code, [403, 404])

        self.client.force_login(self.owner_b)
        response = self.client.get(f'/api/bookings/{self.booking_a.pk}/chat/')
        self.assertIn(response.status_code, [403, 404])

    def test_chat_cost_approval_only_by_booking_client(self):
        """
        Погоджувати або відхиляти запропоновану доплату має право виключно клієнт цієї заявки.
        Власник СТО або сторонній користувач не можуть погоджувати доплату.
        """
        msg = BookingChatMessage.objects.create(
            booking=self.booking_a,
            sender=self.owner_a,
            text='Потрібно замінити гальмівні шланги',
            proposed_cost=Decimal('450.00'),
        )

        # Спроба стороннього клієнта
        self.client.force_login(self.client_b)
        res = self.client.post(
            f'/api/chat-message/{msg.pk}/approval/',
            data={'action': 'approve'},
        )
        msg.refresh_from_db()
        self.assertIsNone(msg.is_approved, 'Сторонній користувач не може затвердити доплату.')

        # Спроба власника СТО підтвердити власну доплату
        self.client.force_login(self.owner_a)
        res = self.client.post(
            f'/api/chat-message/{msg.pk}/approval/',
            data={'action': 'approve'},
        )
        msg.refresh_from_db()
        self.assertIsNone(msg.is_approved, 'Власник СТО не може сам підтверджувати свої доплати.')

        # Правильний виклик клієнтом заявки з дією reject
        self.client.force_login(self.client_a)
        res = self.client.post(
            f'/api/chat-message/{msg.pk}/approval/',
            data={'action': 'reject'},
        )
        msg.refresh_from_db()
        self.assertFalse(msg.is_approved)

    def test_idor_owner_cannot_modify_other_station_boxes_or_services(self):
        """
        Власник СТО А не може видалити або змінити бокс або послугу, що належить СТО Б.
        """
        box_b = StationBox.objects.create(station=self.station_b, name='Бокс Б1', is_active=True)
        service_b = Service.objects.create(station=self.station_b, service_name='Ремонт КПП', price=Decimal('2000.00'))

        self.client.force_login(self.owner_a)

        # Спроба видалити бокс СТО Б
        self.client.post(
            '/profile/',
            data={'action': 'delete_box', 'box_id': box_b.pk},
        )
        self.assertTrue(StationBox.objects.filter(pk=box_b.pk).exists(), 'Власник СТО А не повинен видаляти бокс СТО Б.')

        # Спроба видалити послугу СТО Б
        self.client.post(
            '/profile/',
            data={'action': 'delete_service', 'service_id': service_b.pk},
        )
        self.assertTrue(Service.objects.filter(pk=service_b.pk).exists(), 'Власник СТО А не повинен видаляти послугу СТО Б.')
