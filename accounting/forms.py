from django import forms

from .models import Employee, SparePart, Transaction


class EmployeeForm(forms.ModelForm):
    """Форма для додавання та редагування співробітника СТО."""

    class Meta:
        model = Employee
        fields = [
            'full_name',
            'phone',
            'email',
            'position',
            'base_salary',
            'commission_percent',
            'is_active',
        ]


class SparePartForm(forms.ModelForm):
    """Форма для складського обліку запчастин."""

    class Meta:
        model = SparePart
        fields = [
            'name',
            'sku',
            'quantity',
            'cost_price',
            'selling_price',
            'min_quantity',
        ]


class TransactionForm(forms.ModelForm):
    """Форма внесення фінансових операцій (доходи та витрати)."""

    class Meta:
        model = Transaction
        fields = ['type', 'category', 'amount', 'description', 'date']

    def clean(self):
        data = super().clean()
        category = data.get('category')
        t_type = data.get('type')
        amount = data.get('amount')

        if amount is not None and amount <= 0:
            raise forms.ValidationError('Сума операції має бути більшою за нуль.')

        valid_incomes = {'service', 'other_income'}
        valid_expenses = {'salary', 'spare_parts', 'rent', 'utilities', 'other_expense'}

        if (t_type == 'income' and category not in valid_incomes) or (t_type == 'expense' and category not in valid_expenses):
            raise forms.ValidationError('Обрана категорія не відповідає типу фінансової операції.')

        return data
