from django.urls import path
from . import views

app_name = 'station'

urlpatterns = [
    path('<int:station_id>/', views.station_detail, name='station_detail'),
]
