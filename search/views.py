import math
from django.db.models import Avg, Count
from django.shortcuts import render
from main.models import ServiceStation

def haversine_distance(lat1, lon1, lat2, lon2):
    # Дистанція в км за формулою гаверсинуса
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def _safe_float(val):
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None

def search_stations(request):
    city_query = request.GET.get('city', '').strip()
    service_query = request.GET.get('service', '').strip()
    min_rating = request.GET.get('rating', '').strip()
    
    user_lat = _safe_float(request.GET.get('lat'))
    user_lng = _safe_float(request.GET.get('lng'))
    radius_km = _safe_float(request.GET.get('radius'))

    stations = ServiceStation.objects.annotate(
        avg_rating_val=Avg('review__rating'),
        review_count_val=Count('review', distinct=True),
    ).prefetch_related('service_set')

    if city_query:
        stations = stations.filter(city__icontains=city_query)

    if service_query:
        stations = stations.filter(service__service_name__icontains=service_query).distinct()

    if min_rating and (min_val := _safe_float(min_rating)):
        stations = stations.filter(avg_rating_val__gte=min_val)

    station_data = []
    for s in stations:
        dist_km = None
        if user_lat is not None and user_lng is not None and s.latitude and s.longitude:
            try:
                dist_km = round(haversine_distance(user_lat, user_lng, float(s.latitude), float(s.longitude)), 1)
            except (ValueError, TypeError):
                pass

        if radius_km and user_lat is not None and user_lng is not None:
            if dist_km is None or dist_km > radius_km:
                continue

        station_data.append({
            'station': s,
            'avg_rating': round(s.avg_rating_val, 1) if s.avg_rating_val else None,
            'review_count': getattr(s, 'review_count_val', 0),
            'services': s.service_set.all(),
            'distance_km': dist_km,
        })

    if user_lat is not None and user_lng is not None:
        station_data.sort(key=lambda x: (x['distance_km'] if x['distance_km'] is not None else 999999))

    return render(request, 'search/search.html', {
        'station_data': station_data[:50],
        'selected_city': city_query,
        'selected_service': service_query,
        'selected_rating': min_rating,
        'selected_radius': request.GET.get('radius', ''),
        'user_lat': user_lat,
        'user_lng': user_lng,
    })