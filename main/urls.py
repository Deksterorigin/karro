from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('api/bookings/create/', views.create_booking_api, name='create_booking_api'),
    path('client/<int:client_id>/', views.client_profile_view, name='client_profile'),
    path('api/notifications/', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/mark-read/<int:notification_id>/', views.mark_notification_read_api, name='mark_notification_read_api'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read_api, name='mark_all_notifications_read_api'),
    path('api/stations/<int:station_id>/available-slots/', views.get_available_slots_api, name='get_available_slots_api'),
    path('api/stations/<int:station_id>/calendar-events/', views.get_calendar_events_api, name='get_calendar_events_api'),
    path('api/bookings/<int:booking_id>/reschedule/', views.reschedule_booking_api, name='reschedule_booking_api'),
    path('api/bookings/<int:booking_id>/chat/', views.booking_chat_api, name='booking_chat_api'),
    path('api/chat-message/<int:message_id>/approval/', views.respond_cost_approval_api, name='respond_cost_approval_api'),
    path('booking/<int:booking_id>/act/pdf/', views.download_act_pdf_view, name='download_act_pdf'),
]