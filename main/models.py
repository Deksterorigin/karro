import datetime

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Avg, Sum
from django.utils import timezone

from .textnorm import fold_text


def get_current_year_plus_one():
    return datetime.date.today().year + 1


class UserManager(BaseUserManager):
    """Створює користувачів з авторизацією за email."""

    def create_user(self, email, full_name, phone, role, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обов'язковий")

        user = self.model(
            email=self.normalize_email(email),
            full_name=full_name,
            phone=phone,
            role=role,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, phone, role='station', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError('Суперкористувач повинен мати is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Суперкористувач повинен мати is_superuser=True.')
        if not password:
            raise ValueError('Для суперкористувача потрібен пароль.')

        return self.create_user(email, full_name, phone, role, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Клієнт або представник СТО."""

    ROLE_CHOICES = [
        ('client', 'Клієнт'),
        ('station', 'Адміністратор СТО'),
    ]

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100, verbose_name="Повне ім'я")
    phone = models.CharField(max_length=20, unique=True, verbose_name='Телефон')
    email = models.EmailField(max_length=100, unique=True, verbose_name='Email')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, db_index=True, verbose_name='Роль')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')
    is_active = models.BooleanField(default=True, verbose_name='Активний')
    is_staff = models.BooleanField(default=False, verbose_name='Персонал')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата реєстрації')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone', 'role']

    class Meta:
        db_table = 'user'
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def is_client(self):
        return self.role == 'client'

    @property
    def is_station(self):
        return self.role == 'station'


class ServiceStation(models.Model):
    """СТО та його контактні дані."""

    station_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='Назва СТО')
    city = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name='Місто')
    name_norm = models.CharField(max_length=150, blank=True, default='', editable=False, db_index=True)
    city_norm = models.CharField(max_length=150, blank=True, default='', editable=False, db_index=True)
    address = models.CharField(max_length=200, verbose_name='Адреса')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', verbose_name='Власник')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Широта')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Довгота')
    is_verified = models.BooleanField(default=False, verbose_name='Верифікована')
    opening_time = models.TimeField(default='09:00', verbose_name='Час відкриття')
    closing_time = models.TimeField(default='18:00', verbose_name='Час закриття')
    logo = models.ImageField(upload_to='station_logos/', null=True, blank=True, verbose_name='Логотип')
    edrpou = models.CharField(max_length=20, blank=True, null=True, verbose_name='ЄДРПОУ')
    bank_details = models.TextField(blank=True, null=True, verbose_name='Банківські реквізити')
    legal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Юридична адреса')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'service_station'
        verbose_name = 'Станція ТО'
        verbose_name_plural = 'Станції ТО'
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name_norm = fold_text(self.name)
        self.city_norm = fold_text(self.city)

        if kwargs.get('update_fields') is not None:
            update_fields = set(kwargs['update_fields'])
            if 'name' in update_fields:
                update_fields.add('name_norm')
            if 'city' in update_fields:
                update_fields.add('city_norm')
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def avg_rating(self):
        average = self.review_set.aggregate(avg=Avg('rating'))['avg']
        return round(average, 1) if average is not None else None

    def review_count(self):
        return self.review_set.count()

    def get_or_create_schedules(self):
        existing = {schedule.day_of_week: schedule for schedule in self.schedules.all()}
        schedules = []

        for day in range(7):
            if day in existing:
                schedules.append(existing[day])
                continue

            schedules.append(
                StationSchedule.objects.create(
                    station=self,
                    day_of_week=day,
                    is_working=day < 6,
                    opening_time='10:00' if day == 5 else '09:00',
                    closing_time='16:00' if day == 5 else '18:00',
                )
            )

        return schedules

    def get_day_schedule(self, day_num):
        sch = self.schedules.filter(day_of_week=day_num).first()
        if not sch:
            self.get_or_create_schedules()
            sch = self.schedules.filter(day_of_week=day_num).first()
        return sch

    def is_open_now(self):
        now = timezone.localtime()
        schedule = self.schedules.filter(day_of_week=now.weekday()).first()

        if not schedule or not schedule.is_working:
            return False

        current_time = now.time()
        if not (schedule.opening_time <= current_time <= schedule.closing_time):
            return False

        if schedule.break_start and schedule.break_end and (schedule.break_start <= current_time <= schedule.break_end):
            return False

        return True


class StationSchedule(models.Model):
    """Тижневий графік роботи СТО."""

    DAY_CHOICES = (
        (0, 'Понеділок'),
        (1, 'Вівторок'),
        (2, 'Середа'),
        (3, 'Четвер'),
        (4, "П'ятниця"),
        (5, 'Субота'),
        (6, 'Неділя'),
    )

    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    is_working = models.BooleanField(default=True)
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='18:00')
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = 'station_schedule'
        unique_together = ('station', 'day_of_week')
        ordering = ['day_of_week']
        verbose_name = 'Графік роботи'
        verbose_name_plural = 'Графіки роботи'

    def __str__(self):
        day_name = self.get_day_of_week_display()
        if not self.is_working:
            return f'{self.station.name} — {day_name}: Вихідний'
        return f'{self.station.name} — {day_name}: {self.opening_time}-{self.closing_time}'


class Car(models.Model):
    """Автомобіль клієнта."""

    vin_validator = RegexValidator(
        regex=r'^[A-HJ-NPR-Z0-9]{17}$',
        message='VIN має містити 17 символів (без літер I, O, Q).',
    )

    vin_code = models.CharField(max_length=17, primary_key=True, validators=[vin_validator])
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField(validators=[MinValueValidator(1900), MaxValueValidator(get_current_year_plus_one)])
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    engine = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to='cars/', null=True, blank=True)

    class Meta:
        db_table = 'car'
        ordering = ['-year']
        verbose_name = 'Автомобіль'
        verbose_name_plural = 'Автомобілі'

    def __str__(self):
        return f'{self.brand} {self.model} ({self.year})'


class Service(models.Model):
    """Послуга автосервісу."""

    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=100)
    service_name_norm = models.CharField(max_length=150, blank=True, default='', editable=False, db_index=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, db_column='station_id')

    class Meta:
        db_table = 'service'
        ordering = ['service_name']
        verbose_name = 'Послуга'
        verbose_name_plural = 'Послуги'

    def save(self, *args, **kwargs):
        self.service_name_norm = fold_text(self.service_name)

        if kwargs.get('update_fields') is not None:
            update_fields = set(kwargs['update_fields'])
            if 'service_name' in update_fields:
                update_fields.add('service_name_norm')
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.service_name} — {self.price} грн'


class Review(models.Model):
    """Відгук про роботу СТО."""

    review_id = models.AutoField(primary_key=True)
    text = models.TextField()
    rating = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    photo = models.ImageField(upload_to='reviews/', null=True, blank=True)
    owner_response = models.TextField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, db_column='station_id')

    class Meta:
        db_table = 'review'
        ordering = ['-date']
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'

    def __str__(self):
        return f'Відгук від {self.user.full_name} — {self.rating}/5'


class StationBox(models.Model):
    """Робочий бокс на СТО."""

    box_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='boxes', db_column='station_id')
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'station_box'
        ordering = ['name']
        verbose_name = 'Робочий бокс'
        verbose_name_plural = 'Робочі бокси'

    def __str__(self):
        return f'{self.station.name} — {self.name}'


class Booking(models.Model):
    """Заявка на обслуговування."""

    STATUS_CHOICES = [
        ('pending', 'Очікує'),
        ('confirmed', 'Підтверджено'),
        ('completed', 'Виконано'),
        ('cancelled', 'Скасовано'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', db_column='client_id')
    station = models.ForeignKey(ServiceStation, on_delete=models.SET_NULL, null=True, related_name='bookings', db_column='station_id')
    box = models.ForeignKey(StationBox, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings', db_column='box_id')
    duration = models.PositiveIntegerField(default=60)
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    service_name = models.CharField(max_length=150, blank=True, null=True)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    scheduled_time = models.DateTimeField(null=True, blank=True, db_index=True)
    base_work_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Вартість робіт')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking'
        ordering = ['-created_at']
        verbose_name = 'Заявка на обслуговування'
        verbose_name_plural = 'Заявки на обслуговування'

    def clean(self):
        super().clean()
        errors = {}

        if self.car_id and self.client_id and self.car.user_id != self.client_id:
            errors['car'] = 'Автомобіль не належить клієнту цієї заявки.'

        if self.box_id and (not self.station_id or self.box.station_id != self.station_id):
            errors['box'] = 'Бокс має належати СТО цієї заявки.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'Заявка #{self.pk} — {self.client.full_name} ({self.get_status_display()})'

    @property
    def approved_chat_costs(self):
        total = self.chat_messages.filter(is_approved=True).aggregate(total=Sum('proposed_cost'))['total']
        return total or 0


class Notification(models.Model):
    """Сповіщення для користувача."""

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_column='recipient_id')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='notifications', db_column='booking_id')
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-created_at']
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'

    def __str__(self):
        return f'Сповіщення для {self.recipient.full_name}: {self.message[:30]}'


class CarHistory(models.Model):
    """Історія виконаних робіт з автомобілем."""

    history_id = models.AutoField(primary_key=True)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='history_records')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='car_history_records')
    station = models.ForeignKey(ServiceStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='car_history_records')
    date = models.DateField(default=datetime.date.today)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    work_list = models.TextField()
    spare_parts = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'car_history'
        ordering = ['-date', '-created_at']
        verbose_name = 'Запис історії авто'
        verbose_name_plural = 'Історія авто'

    def clean(self):
        super().clean()
        errors = {}

        if self.booking_id and self.car_id:
            booking = self.booking
            if booking.car_id and booking.car_id != self.car_id:
                errors['car'] = 'Автомобіль не збігається з автомобілем у заявці.'
            elif booking.client_id != self.car.user_id:
                errors['car'] = 'Автомобіль не належить клієнту заявки.'

            if self.station_id and booking.station_id and self.station_id != booking.station_id:
                errors['station'] = 'СТО не збігається із СТО в заявці.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        station_name = self.station.name if self.station else 'СТО'
        car_str = str(self.car) if self.car else 'Автомобіль'
        return f'{car_str} — {self.date} ({station_name}): {self.price} грн'


class BookingChatMessage(models.Model):
    """Повідомлення в чаті заявки."""

    message_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_messages')
    text = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_photos/', null=True, blank=True)
    proposed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_approved = models.BooleanField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_chat_message'
        ordering = ['created_at']
        verbose_name = 'Повідомлення в чаті'
        verbose_name_plural = 'Повідомлення в чаті'

    def clean(self):
        super().clean()
        if self.booking_id and self.booking.status == 'completed' and not self.pk:
            raise ValidationError('Неможливо додати повідомлення до вже завершеної заявки.')

    def save(self, *args, **kwargs):
        if self.booking_id and self.booking.status == 'completed' and not self.pk:
            raise ValidationError('Неможливо додати повідомлення до вже завершеної заявки.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.booking_id and self.booking.status == 'completed':
            raise ValidationError('Неможливо видалити повідомлення із завершеної заявки.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f'Чат #{self.booking_id} — {self.sender.full_name}'