from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_stations, name='search_stations'),
    path('suggest/', views.suggest, name='search_suggest'),
]