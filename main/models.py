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
    logo = models.ImageField(
        upload_to='station_logos/', null=True, blank=True, verbose_name='Логотип СТО'
    )
    edrpou = models.CharField(
        max_length=20, blank=True, null=True, verbose_name='ЄДРПОУ / ІПН'
    )
    bank_details = models.TextField(
        blank=True, null=True, verbose_name='Банківські реквізити (IBAN/Банк)'
    )
    legal_address = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Юридична адреса'
    )
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

    def get_or_create_schedules(self):
        """Ініціалізація розкладу для всіх 7 днів тижня, якщо вони ще не створені."""
        existing = {s.day_of_week: s for s in self.schedules.all()}
        schedules = []
        for day in range(7):
            if day in existing:
                schedules.append(existing[day])
            else:
                # Типове налаштування: Пн-Пт 09:00-18:00, Сб 10:00-16:00, Нд — Вихідний
                is_work = day < 6
                open_t = '10:00' if day == 5 else '09:00'
                close_t = '16:00' if day == 5 else '18:00'
                sch = StationSchedule.objects.create(
                    station=self,
                    day_of_week=day,
                    is_working=is_work,
                    opening_time=open_t,
                    closing_time=close_t
                )
                schedules.append(sch)
        return sorted(schedules, key=lambda x: x.day_of_week)

    def is_open_now(self):
        """Перевірка чи автосервіс відчинений у поточну хвилину."""
        from django.utils import timezone
        now = timezone.localtime()
        current_day = now.weekday()
        current_time = now.time()

        sch = self.schedules.filter(day_of_week=current_day).first()
        if not sch or not sch.is_working:
            return False

        if sch.opening_time <= current_time <= sch.closing_time:
            if sch.break_start and sch.break_end:
                if sch.break_start <= current_time <= sch.break_end:
                    return False
            return True
        return False

    def get_day_schedule(self, day_num):
        """Отримання розкладу для конкретного дня тижня (0=Пн .. 6=Нд)."""
        sch = self.schedules.filter(day_of_week=day_num).first()
        if not sch:
            self.get_or_create_schedules()
            sch = self.schedules.filter(day_of_week=day_num).first()
        return sch


class StationSchedule(models.Model):
    """
    Графік роботи СТО по днях тижня (0 = Понеділок .. 6 = Неділя).
    """
    DAY_CHOICES = (
        (0, 'Понеділок'),
        (1, 'Вівторок'),
        (2, 'Середа'),
        (3, 'Четвер'),
        (4, "П'ятниця"),
        (5, 'Субота'),
        (6, 'Неділя'),
    )

    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='СТО'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name='День тижня')
    is_working = models.BooleanField(default=True, verbose_name='Робочий день')
    opening_time = models.TimeField(default='09:00', verbose_name='Час відкриття')
    closing_time = models.TimeField(default='18:00', verbose_name='Час закриття')
    break_start = models.TimeField(null=True, blank=True, verbose_name='Початок обіду')
    break_end = models.TimeField(null=True, blank=True, verbose_name='Кінець обіду')

    class Meta:
        db_table = 'station_schedule'
        verbose_name = 'Графік роботи СТО'
        verbose_name_plural = 'Графіки роботи СТО'
        unique_together = ('station', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, str(self.day_of_week))
        station_name = self.station.name if hasattr(self, 'station') and self.station else 'СТО'
        if not self.is_working:
            return f'{station_name} — {day_name}: Вихідний'
        break_str = f' (Обід {self.break_start.strftime("%H:%M")}-{self.break_end.strftime("%H:%M")})' if self.break_start and self.break_end else ''
        open_str = self.opening_time.strftime("%H:%M") if self.opening_time else "09:00"
        close_str = self.closing_time.strftime("%H:%M") if self.closing_time else "18:00"
        return f'{station_name} — {day_name}: {open_str}-{close_str}{break_str}'

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

    @property
    def approved_chat_costs(self):
        """Сума всіх додаткових робіт/деталей, підтверджених клієнтом у чаті."""
        from django.db.models import Sum
        result = self.chat_messages.filter(is_approved=True).aggregate(total=Sum('proposed_cost'))
        return result.get('total') or 0


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


class CarHistory(models.Model):
    """
    Історія обслуговування та ремонту автомобіля.
    Створюється автоматично після успішного завершення заявки.
    """
    history_id = models.AutoField(primary_key=True)
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='history_records',
        verbose_name='Автомобіль'
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='car_history_records',
        verbose_name='Заявка'
    )
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='car_history_records',
        verbose_name='СТО'
    )
    date = models.DateField(default=datetime.date.today, verbose_name='Дата обслуговування')
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name='Пробіг (км)')
    work_list = models.TextField(verbose_name='Перелік виконаних робіт')
    spare_parts = models.TextField(null=True, blank=True, verbose_name='Використані запчастини')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Підсумкова вартість (грн)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата запису')

    class Meta:
        db_table = 'car_history'
        verbose_name = 'Запис історії обслуговування'
        verbose_name_plural = 'Історія обслуговування'
        ordering = ['-date', '-created_at']

    def __str__(self):
        station_name = self.station.name if self.station else 'СТО'
        car_str = str(self.car) if self.car else 'Автомобіль'
        return f'{car_str} — {self.date} ({station_name}): {self.price} грн'


class BookingChatMessage(models.Model):
    """
    Повідомлення чату всередині замовлення.
    Дозволяє механіку та клієнту обмінюватися текстом, фотографіями несправностей
    та оперативно узгоджувати додаткові роботи чи суму деталей.
    """
    message_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Заявка'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages',
        verbose_name='Відправник'
    )
    text = models.TextField(blank=True, null=True, verbose_name='Текст повідомлення')
    image = models.ImageField(
        upload_to='chat_photos/',
        null=True,
        blank=True,
        verbose_name='Фото несправності'
    )
    proposed_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Запропонована додаткова вартість (грн)'
    )
    is_approved = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Статус узгодження клієнтом'
    )
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')

    class Meta:
        db_table = 'booking_chat_message'
        verbose_name = 'Повідомлення чату'
        verbose_name_plural = 'Повідомлення чату'
        ordering = ['created_at']

    def __str__(self):
        return f'Чат #{self.booking_id} — {self.sender.full_name} ({self.created_at.strftime("%d.%m %H:%M")})'