import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from main.models import Booking, ServiceStation


class Employee(models.Model):
    """Співробітник автосервісу."""

    employee_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='employees')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employee'
        ordering = ['full_name']
        verbose_name = 'Співробітник'
        verbose_name_plural = 'Співробітники'

    def __str__(self):
        return f'{self.full_name} ({self.position})'


class SalaryBalance(models.Model):
    """Нарахування та виплати співробітнику."""

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary_balance')
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salary_balance'
        verbose_name = 'Баланс заробітної плати'
        verbose_name_plural = 'Баланси заробітної плати'

    @property
    def current_balance(self):
        return self.total_earned - self.total_paid

    def __str__(self):
        return f'Баланс: {self.employee.full_name} ({self.current_balance} грн)'


class Transaction(models.Model):
    """Дохід або витрата СТО."""

    TRANSACTION_TYPES = [
        ('income', 'Дохід'),
        ('expense', 'Витрата'),
    ]
    TRANSACTION_CATEGORIES = [
        ('service', 'Послуги СТО'),
        ('other_income', 'Інші доходи'),
        ('salary', 'Зарплата'),
        ('spare_parts', 'Запчастини'),
        ('rent', 'Оренда'),
        ('utilities', 'Комунальні'),
        ('other_expense', 'Інші витрати'),
    ]

    transaction_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, db_index=True)
    category = models.CharField(max_length=20, choices=TRANSACTION_CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=datetime.date.today, db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction'
        ordering = ['-date', '-created_at']
        verbose_name = 'Фінансова операція'
        verbose_name_plural = 'Фінансові операції'

    def clean(self):
        super().clean()
        errors = {}

        if self.booking_id and self.station_id and self.booking.station_id != self.station_id:
            errors['booking'] = 'Заявка не належить цьому СТО.'

        if self.employee_id and self.station_id and self.employee.station_id != self.station_id:
            errors['employee'] = 'Співробітник не належить цьому СТО.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.get_type_display()} — {self.amount} грн ({self.date})'


@receiver(post_save, sender=Employee)
def create_employee_balance(sender, instance, created, **kwargs):
    if created:
        SalaryBalance.objects.create(employee=instance)


class SparePart(models.Model):
    """Запчастина на складі СТО."""

    part_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='spare_parts')
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    min_quantity = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_part'
        ordering = ['name']
        verbose_name = 'Запчастина на складі'
        verbose_name_plural = 'Запчастини на складі'

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def margin_amount(self):
        return self.selling_price - self.cost_price

    @property
    def margin_percent(self):
        if self.cost_price and self.cost_price > 0:
            margin = ((self.selling_price - self.cost_price) / self.cost_price) * 100
            return round(float(margin), 1)
        return 0.0

    def __str__(self):
        sku_str = f' [{self.sku}]' if self.sku else ''
        return f'{self.name}{sku_str} — {self.quantity} шт'


class UsedSparePart(models.Model):
    """Запчастина, використана під час виконання заявки."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='used_parts')
    spare_part = models.ForeignKey(SparePart, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_instances')
    part_name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name='Артикул')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'used_spare_part'
        verbose_name = 'Використана деталь'
        verbose_name_plural = 'Використані деталі'

    def clean(self):
        super().clean()
        if self.booking_id and self.spare_part_id and self.spare_part.station_id != self.booking.station_id:
            raise ValidationError({'spare_part': 'Запчастина не належить СТО цієї заявки.'})
        if self.booking_id and self.booking.status == 'completed' and not self.pk:
            raise ValidationError('Неможливо додати запчастину до вже завершеної заявки.')

    def save(self, *args, **kwargs):
        if self.booking_id and self.booking.status == 'completed' and not self.pk:
            raise ValidationError('Неможливо додати запчастину до вже завершеної заявки.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.booking_id and self.booking.status == 'completed':
            raise ValidationError('Неможливо видалити запчастину з уже завершеної заявки.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.part_name} x{self.quantity} для Заявки #{self.booking_id}'
