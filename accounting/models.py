from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from main.models import ServiceStation, Booking
import datetime


class Employee(models.Model):
    """Модель працівника СТО (механік, майстер-приймальник тощо)."""

    employee_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        ServiceStation, on_delete=models.CASCADE, verbose_name="СТО", related_name="employees"
    )
    full_name = models.CharField(max_length=100, verbose_name="Повне ім'я")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Email")
    position = models.CharField(max_length=100, verbose_name="Посада")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Ставка (грн)")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Комісія (%)")
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employee'
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.position})"


class SalaryBalance(models.Model):
    """Баланс нарахованої та виплаченої заробітної плати працівника."""

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="salary_balance")
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Всього зароблено")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Всього виплачено")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salary_balance'
        verbose_name = 'Баланс зарплати'
        verbose_name_plural = 'Баланси зарплат'

    @property
    def current_balance(self):
        return self.total_earned - self.total_paid

    def __str__(self):
        return f"Баланс: {self.employee.full_name} ({self.current_balance} грн)"


class Transaction(models.Model):
    """Фінансова транзакція (доходи від послуг/запчастин, витрати на оренду/зарплату)."""

    TRANSACTION_TYPES = [
        ('income', 'Дохід'),
        ('expense', 'Витрата'),
    ]

    TRANSACTION_CATEGORIES = [
        ('service', 'Послуги СТО (Дохід)'),
        ('other_income', 'Інші доходи'),
        ('salary', 'Виплата зарплати (Витрата)'),
        ('spare_parts', 'Запчастини (Витрата)'),
        ('rent', 'Оренда (Витрата)'),
        ('utilities', 'Комунальні послуги (Витрата)'),
        ('other_expense', 'Інші витрати'),
    ]

    transaction_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, verbose_name="СТО", related_name="transactions")
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="Тип", db_index=True)
    category = models.CharField(max_length=20, choices=TRANSACTION_CATEGORIES, verbose_name="Категорія")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сума (грн)")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")
    date = models.DateField(default=datetime.date.today, verbose_name="Дата", db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Заявка", related_name="transactions")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Працівник", related_name="transactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction'
        verbose_name = 'Фінансова операція'
        verbose_name_plural = 'Фінансові операції'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_type_display()} — {self.amount} грн ({self.date})"


# Авто-створення балансу зарплати при додаванні працівника
@receiver(post_save, sender=Employee)
def create_employee_balance(sender, instance, created, **kwargs):
    if created:
        SalaryBalance.objects.create(employee=instance)


class SparePart(models.Model):
    """Складський облік запчастин та матеріалів автосервісу."""

    part_id = models.AutoField(primary_key=True)
    station = models.ForeignKey(ServiceStation, on_delete=models.CASCADE, related_name='spare_parts', verbose_name="СТО")
    name = models.CharField(max_length=150, verbose_name="Назва запчастини/матеріалу")
    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name="Артикул / Каталожний номер")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Кількість на складі")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Собівартість (грн)")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Ціна продажу (грн)")
    min_quantity = models.PositiveIntegerField(default=5, verbose_name="Мінімальний залишок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    class Meta:
        db_table = 'spare_part'
        verbose_name = 'Запчастина на складі'
        verbose_name_plural = 'Запчастини на складі'
        ordering = ['name']

    def __str__(self):
        sku_str = f' [{self.sku}]' if self.sku else ''
        return f'{self.name}{sku_str} — {self.quantity} шт (Закупка: {self.cost_price} грн, Продаж: {self.selling_price} грн)'

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


class UsedSparePart(models.Model):
    """Деталі, списані під конкретне замовлення."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='used_parts', verbose_name="Заявка")
    spare_part = models.ForeignKey(SparePart, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_instances', verbose_name="Запчастина")
    part_name = models.CharField(max_length=150, verbose_name="Назва деталі")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Використана кількість")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Собівартість (грн)")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна продажу (грн)")

    class Meta:
        db_table = 'used_spare_part'
        verbose_name = 'Використана запчастина'
        verbose_name_plural = 'Використані запчастини'

    def __str__(self):
        return f'{self.part_name} x{self.quantity} для Заявки #{self.booking_id}'
