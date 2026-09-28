import logging
import math

from django.core.paginator import Paginator
from django.db import OperationalError
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from main.models import Service, ServiceStation
from main.textnorm import fold_text, tokenize


logger = logging.getLogger(__name__)

PAGE_SIZE = 12
MAX_QUERY_LENGTH = 100
MAX_SUGGEST_LIMIT = 20


def haversine_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0
    latitude_difference = math.radians(lat2 - lat1)
    longitude_difference = math.radians(lon2 - lon1)

    value = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(longitude_difference / 2) ** 2
    )
    value = min(1.0, max(0.0, value))

    return earth_radius * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )


def _parse_number(raw, minimum=None, maximum=None):
    if raw is None:
        return None

    text = str(raw).strip().replace(',', '.')[:32]
    if not text:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None

    return number


def _clean_text(raw, max_length=MAX_QUERY_LENGTH):
    return fold_text(str(raw)[:max_length])


@require_GET
def search_stations(request):
    city_query = _clean_text(request.GET.get('city', ''))
    service_query = _clean_text(request.GET.get('service', ''))
    min_rating = _parse_number(request.GET.get('rating'), 0.0, 5.0)

    if min_rating == 0:
        min_rating = None

    user_lat = _parse_number(request.GET.get('lat'), -90.0, 90.0)
    user_lng = _parse_number(request.GET.get('lng'), -180.0, 180.0)
    radius_km = _parse_number(request.GET.get('radius'), 0.1, 2000.0)
    has_coords = user_lat is not None and user_lng is not None

    try:
        page_number = int(str(request.GET.get('page', '1'))[:10])
    except (TypeError, ValueError):
        page_number = 1
    page_number = max(1, page_number)

    rows = []
    db_error = False

    try:
        stations = (
            ServiceStation.objects
            .annotate(
                avg_rating_val=Avg('review__rating'),
                review_count_val=Count('review', distinct=True),
            )
            .prefetch_related('service_set')
            .order_by('name', 'pk')
        )

        for token in tokenize(city_query):
            stations = stations.filter(city_norm__icontains=token)

        service_tokens = tokenize(service_query)
        if service_tokens:
            matching_services = Service.objects.all()
            for token in service_tokens:
                matching_services = matching_services.filter(
                    service_name_norm__icontains=token
                )

            stations = stations.filter(
                pk__in=matching_services.values('station_id')
            )

        if min_rating is not None:
            stations = stations.filter(avg_rating_val__gte=min_rating)

        rows = list(stations)
    except OperationalError:
        logger.exception('Не вдалося виконати пошук СТО')
        db_error = True

    station_data = []

    for station in rows:
        distance = None

        if (
            has_coords
            and station.latitude is not None
            and station.longitude is not None
        ):
            distance = haversine_distance(
                user_lat,
                user_lng,
                float(station.latitude),
                float(station.longitude),
            )

        dist_km = round(distance, 1) if distance is not None else None

        if has_coords and radius_km is not None:
            if dist_km is None or dist_km > radius_km:
                continue

        station_data.append({
            'station': station,
            'avg_rating': (
                round(station.avg_rating_val, 1)
                if station.avg_rating_val is not None else None
            ),
            'review_count': station.review_count_val,
            'services': station.service_set.all(),
            'distance_km': dist_km,
        })

    if has_coords:
        station_data.sort(
            key=lambda item: (
                item['distance_km']
                if item['distance_km'] is not None else math.inf,
                item['station'].pk,
            )
        )

    paginator = Paginator(station_data, PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'search/search.html', {
        'station_data': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
        'querystring': params.urlencode(),
        'db_error': db_error,
        'selected_city': str(request.GET.get('city', '')).strip()[:MAX_QUERY_LENGTH],
        'selected_service': str(request.GET.get('service', '')).strip()[:MAX_QUERY_LENGTH],
        'selected_rating': str(request.GET.get('rating', '')).strip()[:10],
        'selected_radius': int(radius_km) if radius_km is not None else '',
        'user_lat': user_lat,
        'user_lng': user_lng,
    })


@require_GET
def suggest(request):
    query = _clean_text(request.GET.get('q', ''), max_length=60)
    requested_limit = _parse_number(request.GET.get('limit'))

    limit = (
        max(1, min(int(requested_limit), MAX_SUGGEST_LIMIT))
        if requested_limit is not None else 10
    )

    cities = []
    services = []

    if query:
        try:
            cities = list(
                ServiceStation.objects
                .exclude(city_norm='')
                .filter(city_norm__istartswith=query)
                .values_list('city', flat=True)
                .distinct()
                .order_by('city')[:limit]
            )
            services = list(
                Service.objects
                .exclude(service_name_norm='')
                .filter(service_name_norm__istartswith=query)
                .values_list('service_name', flat=True)
                .distinct()
                .order_by('service_name')[:limit]
            )
        except OperationalError:
            logger.exception('Не вдалося завантажити підказки пошуку')
            cities = []
            services = []

    return JsonResponse({
        'query': query,
        'cities': cities,
        'services': services,
    })
