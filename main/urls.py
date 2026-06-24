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
]