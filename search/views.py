import logging
import math

from django.core.paginator import Paginator
from django.db import OperationalError
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from main.models import Service, ServiceStation
from main.textnorm import escape_like, fold_text

logger = logging.getLogger(__name__)

PAGE_SIZE = 12
MAX_QUERY_LENGTH = 100
MAX_SUGGEST_LIMIT = 20
MAX_SCAN_ROWS = 1000

LAT_RANGE = (-90.0, 90.0)
LNG_RANGE = (-180.0, 180.0)
RADIUS_RANGE = (0.1, 2000.0)
RATING_RANGE = (0.0, 5.0)


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    a = min(1.0, max(0.0, a))
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _parse_number(raw, lo=None, hi=None):
    if raw is None:
        return None
    text = str(raw).strip().replace(',', '.')[:32]
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    if lo is not None and hi is not None and not (lo <= value <= hi):
        return None
    return value


def _clean_text(raw, max_len=MAX_QUERY_LENGTH):
    return fold_text(str(raw)[:max_len])


def _apply_tokens(queryset, field, folded_query):
    tokens = [token for token in folded_query.split(' ') if token]
    for token in tokens:
        queryset = queryset.filter(**{f'{field}__icontains': escape_like(token)})
    return queryset, bool(tokens)


@require_GET
def search_stations(request):
    city_query = _clean_text(request.GET.get('city', ''))
    service_query = _clean_text(request.GET.get('service', ''))
    min_rating = _parse_number(request.GET.get('rating', ''))
    if min_rating is not None and not (RATING_RANGE[0] < min_rating <= RATING_RANGE[1]):
        min_rating = None

    user_lat = _parse_number(request.GET.get('lat'), *LAT_RANGE)
    user_lng = _parse_number(request.GET.get('lng'), *LNG_RANGE)
    radius_km = _parse_number(request.GET.get('radius'), *RADIUS_RANGE)
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

        stations, city_active = _apply_tokens(stations, 'city_norm', city_query)
        stations, service_active = _apply_tokens(stations, 'service__service_name_norm', service_query)
        if city_active or service_active:
            stations = stations.distinct()

        if min_rating is not None:
            stations = stations.filter(avg_rating_val__gte=min_rating)

        rows = list(stations[:MAX_SCAN_ROWS])
    except OperationalError:
        logger.exception('Search query failed')
        db_error = True

    station_data = []
    for s in rows:
        dist_km = None
        if has_coords and s.latitude is not None and s.longitude is not None:
            dist_km = round(
                haversine_distance(user_lat, user_lng, float(s.latitude), float(s.longitude)),
                1,
            )

        if has_coords and radius_km is not None:
            if dist_km is None or dist_km > radius_km:
                continue

        station_data.append({
            'station': s,
            'avg_rating': round(s.avg_rating_val, 1) if s.avg_rating_val else None,
            'review_count': s.review_count_val,
            'services': s.service_set.all(),
            'distance_km': dist_km,
        })

    if has_coords:
        station_data.sort(key=lambda item: (
            item['distance_km'] if item['distance_km'] is not None else math.inf,
            item['station'].pk,
        ))

    paginator = Paginator(station_data, PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    return render(request, 'search/search.html', {
        'station_data': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
        'querystring': querystring,
        'db_error': db_error,
        'selected_city': str(request.GET.get('city', '')).strip()[:MAX_QUERY_LENGTH],
        'selected_service': str(request.GET.get('service', '')).strip()[:MAX_QUERY_LENGTH],
        'selected_rating': str(request.GET.get('rating', '')).strip()[:10],
        'selected_radius': int(radius_km) if radius_km else '',
        'user_lat': user_lat,
        'user_lng': user_lng,
    })


@require_GET
def suggest(request):
    query = _clean_text(request.GET.get('q', ''), max_len=60)
    limit = _parse_number(request.GET.get('limit', ''))
    limit = max(1, min(int(limit) if limit is not None else 10, MAX_SUGGEST_LIMIT))

    cities = []
    services = []
    if query:
        prefix = escape_like(query)
        try:
            cities = list(
                ServiceStation.objects
                .exclude(city_norm='')
                .filter(city_norm__istartswith=prefix)
                .values_list('city', flat=True)
                .distinct()
                .order_by('city')[:limit]
            )
            services = list(
                Service.objects
                .exclude(service_name_norm='')
                .filter(service_name_norm__istartswith=prefix)
                .values_list('service_name', flat=True)
                .distinct()
                .order_by('service_name')[:limit]
            )
        except OperationalError:
            logger.exception('Suggest query failed')

    return JsonResponse({'query': query, 'cities': cities, 'services': services})
