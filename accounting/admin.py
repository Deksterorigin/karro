from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Employee, SalaryBalance, Transaction, SparePart, UsedSparePart


@admin.register(SparePart)
class SparePartAdmin(ModelAdmin):
    list_display = ('name', 'sku', 'station', 'quantity', 'cost_price', 'selling_price', 'min_quantity')
    list_filter = ('station',)
    search_fields = ('name', 'sku')


@admin.register(UsedSparePart)
class UsedSparePartAdmin(ModelAdmin):
    list_display = ('part_name', 'sku', 'booking', 'quantity', 'cost_price', 'selling_price')
    search_fields = ('part_name', 'sku', 'booking__id')

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking and obj.booking.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.booking and obj.booking.status == 'completed':
            return False
        return super().has_change_permission(request, obj)


@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('full_name', 'station', 'position', 'base_salary', 'commission_percent', 'is_active')
    list_filter = ('station', 'position', 'is_active')
    search_fields = ('full_name', 'phone', 'email', 'position')


@admin.register(SalaryBalance)
class SalaryBalanceAdmin(ModelAdmin):
    list_display = ('employee', 'total_earned', 'total_paid', 'current_balance_display', 'updated_at')
    list_filter = ('employee__station', 'updated_at')
    search_fields = ('employee__full_name',)

    def current_balance_display(self, obj):
        return f"{obj.current_balance} грн"
    current_balance_display.short_description = "Баланс"


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('transaction_id', 'station', 'type', 'category', 'amount', 'date', 'employee')
    list_filter = ('station', 'type', 'category', 'date')
    search_fields = ('description', 'employee__full_name', 'booking__id')
