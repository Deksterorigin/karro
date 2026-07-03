from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('employee/add/', views.add_employee_view, name='add_employee'),
    path('employee/edit/<int:employee_id>/', views.edit_employee_view, name='edit_employee'),
    path('employee/fire/<int:employee_id>/', views.fire_employee_view, name='fire_employee'),
    path('employee/pay/', views.pay_salary_view, name='pay_salary'),
    path('transaction/add/', views.add_transaction_view, name='add_transaction'),
    path('booking/complete/', views.complete_booking_view, name='complete_booking'),
]
