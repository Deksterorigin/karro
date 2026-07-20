from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import datetime

def get_current_year_plus_one():
    return datetime.date.today().year + 1


class UserManager(BaseUserManager):
    """
    Менеджер користувачів для кастомної моделі.
    """
    def create_user(self, email, full_name, phone, role, password=None, **extra_fields):
        if not email:
            raise ValueError('Email є обов\'язковим')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, phone=phone, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, phone, role='station', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, full_name, phone, role, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('client',  'Клієнт'),
        ('station', 'Адміністратор СТО'),
    ]

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100, verbose_name='Повне ім\'я')
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
    """
    Профіль СТО, пов'язаний з користувачем-власником.
    """
    station_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='Назва СТО')
    city = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name='Місто')
    address = models.CharField(max_length=200, verbose_name='Адреса')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='user_id', verbose_name='Власник'
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Широта'
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Довгота'
    )
    is_verified = models.BooleanField(default=False, verbose_name='Верифікована')
    opening_time = models.TimeField(default='09:00', verbose_name='Час відкриття')
    closing_time = models.TimeField(default='18:00', verbose_name='Час закриття')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')

    class Meta:
        db_table = 'service_station'
        verbose_name = 'Станція ТО'
        verbose_name_plural = 'Станції ТО'
        ordering = ['name']

    def __str__(self):
        return self.name

    def avg_rating(self):
        """Середній рейтинг на основі відгуків."""
        from django.db.models import Avg
        result = Review.objects.filter(station=self).aggregate(avg=Avg('rating'))
        avg = result.get('avg')
        return round(avg, 1) if avg is not None else None

    def review_count(self):
        """Кількість залишених відгуків."""
        return Review.objects.filter(station=self).count()

class Car(models.Model):
    """
    Автомобіль клієнта (з перевіркою VIN-коду).
    """
    vin_validator = RegexValidator(
        regex=r'^[A-HJ-NPR-Z0-9]{17}$',
        message='VIN має містити 17 символів (латинські літери A-Z без I, O, Q та цифри).'
    )

    vin_code = models.CharField(
        max_length=17, primary_key=True,
        validators=[vin_validator],
        verbose_name='VIN-код'
    )
    brand = models.CharField(max_length=50, verbose_name='Марка')
    model = models.CharField(max_length=50, verbose_name='Модель')
    year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(get_current_year_plus_one)],
        verbose_name='Рік випуску'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='user_id', verbose_name='Власник'
    )
    photo = models.ImageField(
        upload_to='cars/', null=True, blank=True, verbose_name='Фото'
    )

    class Meta:
        db_table = 'car'
        verbose_name = 'Автомобіль'
        verbose_name_plural = 'Автомобілі'
        ordering = ['-year']

    def __str__(self):
        return f'{self.brand} {self.model} ({self.year})'

class Service(models.Model):
    """
    Послуги, які надає СТО.
    """
    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=100, verbose_name='Назва послуги')
    description = models.TextField(blank=True, null=True, verbose_name='Опис')
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Ціна (грн)'
    )
    station = models.ForeignKey(
        ServiceStation, on_delete=models.CASCADE,
        db_column='station_id', verbose_name='СТО'
    )

    class Meta:
        db_table = 'service'
        verbose_name = 'Послуга'
        verbose_name_plural = 'Послуги'
        ordering = ['service_name']

    def __str__(self):
        return f'{self.service_name} — {self.price} грн'

class Review(models.Model):
    """
    Відгук клієнта про обслуговування.
    """
    review_id = models.AutoField(primary_key=True)
    text = models.TextField(verbose_name='Текст відгуку')
    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оцінка (1–5)'
    )
    date = models.DateField(auto_now_add=True, verbose_name='Дата')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='user_id', verbose_name='Автор'
    )
    station = models.ForeignKey(
        ServiceStation, on_delete=models.CASCADE,
        db_column='station_id', verbose_name='СТО'
    )

    class Meta:
        db_table = 'review'
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'
        ordering = ['-date']

    def __str__(self):
        return f'Відгук від {self.user.full_name} — оцінка {self.rating}/5'


class StationBox(models.Model):
    """
    Робочий пост/бокс на СТО.
    """
    box_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        ServiceStation, on_delete=models.CASCADE,
        related_name='boxes', db_column='station_id', verbose_name='СТО'
    )
    name = models.CharField(max_length=50, verbose_name='Назва боксу')
    is_active = models.BooleanField(default=True, verbose_name='Активний')

    class Meta:
        db_table = 'station_box'
        verbose_name = 'Робочий бокс'
        verbose_name_plural = 'Робочі бокси'
        ordering = ['name']

    def __str__(self):
        return f'{self.station.name} — {self.name}'


class Booking(models.Model):
    """
    Запис на ремонт або обслуговування автомобіля.
    """

    STATUS_CHOICES = [
        ('pending', 'Очікує'),
        ('confirmed', 'Підтверджено'),
        ('completed', 'Виконано'),
        ('cancelled', 'Скасовано'),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
        db_column='client_id',
        verbose_name='Клієнт',
    )
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bookings',
        db_column='station_id',
        verbose_name='СТО',
    )
    box = models.ForeignKey(
        StationBox,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
        db_column='box_id',
        verbose_name='Робочий бокс',
    )
    duration = models.PositiveIntegerField(
        default=60,
        verbose_name='Тривалість (хвилин)',
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name='Автомобіль',
    )
    service_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Назва послуги',
    )
    description = models.TextField(verbose_name='Опис проблеми')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус',
    )
    scheduled_time = models.DateTimeField(
        null=True, blank=True,
        db_index=True,
        verbose_name='Бажаний час візиту',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Створено',
    )

    class Meta:
        db_table = 'booking'
        verbose_name = 'Заявка на ремонт'
        verbose_name_plural = 'Заявки на ремонт'
        ordering = ['-created_at']

    def __str__(self):
        station_name = self.station.name if self.station else 'Видалена СТО'
        return f'Заявка #{self.pk} — {self.client.full_name} → {station_name} ({self.get_status_display()})'


class Notification(models.Model):
    """
    Сповіщення для користувачів про нові записи або зміну статусів.
    """
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_column='recipient_id',
        verbose_name='Отримувач'
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_column='booking_id',
        verbose_name='Заявка'
    )
    message = models.TextField(verbose_name='Повідомлення')
    is_read = models.BooleanField(default=False, db_index=True, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        db_table = 'notification'
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'
        ordering = ['-created_at']

    def __str__(self):
        return f'Сповіщення для {self.recipient.full_name}: {self.message[:30]}'