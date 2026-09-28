from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action
from .models import User, ServiceStation, Review, Booking, CarHistory, Car, BookingChatMessage


@admin.register(BookingChatMessage)
class BookingChatMessageAdmin(ModelAdmin):
    list_display = ('message_id', 'booking', 'sender', 'text', 'has_image', 'proposed_cost', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('text', 'sender__full_name', 'booking__id')

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Фото"

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking and obj.booking.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.booking and obj.booking.status == 'completed':
            return False
        return super().has_change_permission(request, obj)


@admin.register(Car)
class CarAdmin(ModelAdmin):
    list_display = ('vin_code', 'brand', 'model', 'year', 'user')
    list_filter = ('brand', 'year')
    search_fields = ('vin_code', 'brand', 'model', 'user__full_name')


@admin.register(CarHistory)
class CarHistoryAdmin(ModelAdmin):
    list_display = ('car', 'station', 'date', 'mileage', 'price', 'created_at')
    list_filter = ('date', 'station')
    search_fields = ('car__vin_code', 'car__brand', 'car__model', 'work_list', 'spare_parts')
    list_per_page = 25


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
    list_display = ('id', 'client', 'station', 'status', 'scheduled_time', 'base_work_price', 'created_at')
    list_filter = ('status', 'station', 'created_at')
    search_fields = ('client__full_name', 'station__name', 'description')
    list_per_page = 25
    actions = ['confirm_bookings', 'cancel_bookings']

    @action(description="Підтвердити заявки")
    def confirm_bookings(self, request, queryset):
        count = queryset.update(status='confirmed')
        self.message_user(request, f"Підтверджено {count} заявок.")

    @action(description="Скасувати заявки")
    def cancel_bookings(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"Скасовано {count} заявок.")