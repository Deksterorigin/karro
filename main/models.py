from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

class User(models.Model):
    """
    Користувач системи (клієнт або власник СТО).
    Не наслідує AbstractBaseUser; автентифікація реалізована через кастомну сесійну логіку.
    """
    ROLE_CHOICES = [
        ('client',  'Клієнт'),
        ('station', 'Адміністратор СТО'),
    ]

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100, verbose_name='Повне ім\'я')
    phone = models.CharField(max_length=20, unique=True, verbose_name='Телефон')
    email = models.EmailField(max_length=100, unique=True, verbose_name='Email')
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name='Роль')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата реєстрації')

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
    Профіль станції технічного обслуговування.
    Прив'язаний до користувача з роллю 'station'.
    """
    station_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='Назва СТО')
    city = models.CharField(max_length=100, blank=True, default='', verbose_name='Місто')
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')

    class Meta:
        db_table = 'service_station'
        verbose_name = 'Станція ТО'
        verbose_name_plural = 'Станції ТО'
        ordering = ['name']

    def __str__(self):
        return self.name

    def avg_rating(self):
        """Обчислює середній рейтинг СТО."""
        from django.db.models import Avg
        result = Review.objects.filter(station=self).aggregate(avg=Avg('rating'))
        avg = result.get('avg')
        return round(avg, 1) if avg is not None else None

    def review_count(self):
        """Повертає кількість відгуків СТО."""
        return Review.objects.filter(station=self).count()

class Car(models.Model):
    """
    Автомобіль клієнта з валідацією VIN за стандартом ISO 3779.
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
        validators=[MinValueValidator(1900), MaxValueValidator(2030)],
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
    Послуга, що надається конкретною СТО.
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
    Відгук клієнта про роботу СТО.
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