from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action
from .models import User, ServiceStation, Review, Booking

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('full_name', 'email', 'phone')
    actions = ['block_users']

    @action(description="Заблокувати вибраних користувачів")
    def block_users(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Заблоковано {count} користувачів.")

@admin.register(ServiceStation)
class ServiceStationAdmin(ModelAdmin):
    list_display = ('name', 'city', 'phone', 'is_verified', 'created_at')
    list_filter = ('city', 'is_verified')
    search_fields = ('name', 'address', 'phone')
    actions = ['verify_stations']

    @action(description="Верифікувати вибрані СТО")
    def verify_stations(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"Успішно верифіковано {count} СТО.")

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('user', 'station', 'rating', 'short_text', 'date')
    list_filter = ('rating', 'date')
    search_fields = ('text', 'user__full_name', 'station__name')
    actions = ['delete_spam']

    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = "Текст відгуку"

    @action(description="Видалити як спам")
    def delete_spam(self, request, queryset):
        count, _ = queryset.delete()
        self.message_user(request, f"Видалено {count} відгуків (Спам).")


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('id', 'client', 'station', 'status', 'scheduled_time', 'created_at')
    list_filter = ('status', 'station', 'created_at')
    search_fields = ('client__full_name', 'station__name', 'description')
    list_per_page = 25
    actions = ['confirm_bookings', 'complete_bookings', 'cancel_bookings']

    @action(description="Підтвердити заявки")
    def confirm_bookings(self, request, queryset):
        count = queryset.update(status='confirmed')
        self.message_user(request, f"Підтверджено {count} заявок.")

    @action(description="Відзначити як виконані")
    def complete_bookings(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f"Виконано {count} заявок.")

    @action(description="Скасувати заявки")
    def cancel_bookings(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"Скасовано {count} заявок.")