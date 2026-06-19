# ╔══════════════════════════════════════════════════════════╗
# ║                  search/views.py                        ║
# ║         Пошук та фільтрація СТО                         ║
# ╚══════════════════════════════════════════════════════════╝

import re

from django.db.models import Avg, Count
from django.shortcuts import render

from main.models import ServiceStation


def search_stations(request):
    """
    Пошук СТО з фільтрацією за:
      - містом (city) — тільки латиниця
      - назвою послуги (service_query) — часткове входження
      - мінімальним рейтингом (min_rating)

    Оптимізовано: рейтинг та кількість відгуків обчислюються
    одним SQL-запитом через annotate(), а не в Python-циклі.
    """
    city_query = request.GET.get('city', '').strip()
    service_query = request.GET.get('service', '').strip()
    min_rating = request.GET.get('rating', '').strip()

    # Базовий QuerySet — усі СТО з анотованим рейтингом та кількістю відгуків
    stations = ServiceStation.objects.annotate(
        avg_rating_val=Avg('review__rating'),
        review_count=Count('review'),
    ).prefetch_related('service_set')

    # Фільтр за містом (тільки латиниця — кирилиця відхиляється)
    if city_query:
        if re.search(r'[А-Яа-яЁёІіЇїЄєҐґ]', city_query):
            stations = stations.none()
        else:
            stations = stations.filter(city__icontains=city_query)

    # Фільтр за назвою послуги
    if service_query:
        stations = stations.filter(
            service__service_name__icontains=service_query
        ).distinct()

    # Фільтр за мінімальним рейтингом
    if min_rating:
        try:
            min_val = float(min_rating)
            stations = stations.filter(avg_rating_val__gte=min_val)
        except ValueError:
            pass  # ігноруємо некоректне значення фільтра

    # Формуємо дані для шаблону
    station_data = [
        {
            'station': s,
            'avg_rating': round(s.avg_rating_val, 1) if s.avg_rating_val else None,
            'review_count': s.review_count,
            'services': s.service_set.all(),
        }
        for s in stations
    ]

    context = {
        'station_data': station_data,
        'selected_city': city_query,
        'selected_service': service_query,
        'selected_rating': min_rating,
    }
    return render(request, 'search/search.html', context)