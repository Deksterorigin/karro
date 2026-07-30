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
    # Маршрути управління складом запчастин
    path('inventory/add/', views.add_spare_part_view, name='add_spare_part'),
    path('inventory/edit/', views.edit_spare_part_view, name='edit_spare_part'),
    path('inventory/delete/', views.delete_spare_part_view, name='delete_spare_part'),
    # Експорт транзакцій у CSV та звіту в PDF
    path('export/csv/', views.export_transactions_csv, name='export_csv'),
    path('export/pdf/', views.export_financial_report_pdf, name='export_pdf'),
    # Пошук та закупівля запчастин у постачальників (API + Import)
    path('api/suppliers/parts/search/', views.search_supplier_parts_api, name='search_supplier_parts_api'),
    path('inventory/import-supplier-part/', views.import_supplier_part_view, name='import_supplier_part'),
]
