import math
from django.db.models import Avg, Count
from django.shortcuts import render
from main.models import ServiceStation

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Обчислює відстань у кілометрах між двома точками за формулою Гаверсинуса.
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def search_stations(request):
    """
    Пошук та фільтрація СТО за обраним містом, послугою, рейтингом та відстанню від користувача.
    """
    city_query = request.GET.get('city', '').strip()
    service_query = request.GET.get('service', '').strip()
    min_rating = request.GET.get('rating', '').strip()
    user_lat_str = request.GET.get('lat', '').strip()
    user_lng_str = request.GET.get('lng', '').strip()
    radius_str = request.GET.get('radius', '').strip()

    user_lat, user_lng, radius_km = None, None, None
    if user_lat_str and user_lng_str:
        try:
            user_lat = float(user_lat_str)
            user_lng = float(user_lng_str)
        except ValueError:
            pass

    if radius_str:
        try:
            radius_km = float(radius_str)
        except ValueError:
            pass

    stations = ServiceStation.objects.annotate(
        avg_rating_val=Avg('review__rating'),
        review_count_val=Count('review', distinct=True),
    ).prefetch_related('service_set')

    if city_query:
        stations = stations.filter(city__icontains=city_query)

    if service_query:
        stations = stations.filter(
            service__service_name__icontains=service_query
        ).distinct()

    if min_rating:
        try:
            min_val = float(min_rating)
            stations = stations.filter(avg_rating_val__gte=min_val)
        except ValueError:
            pass

    station_list = list(stations)
    station_data = []

    for s in station_list:
        dist_km = None
        if user_lat is not None and user_lng is not None and s.latitude and s.longitude:
            try:
                dist_km = round(haversine_distance(user_lat, user_lng, float(s.latitude), float(s.longitude)), 1)
            except Exception:
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

    context = {
        'station_data': station_data[:50],
        'selected_city': city_query,
        'selected_service': service_query,
        'selected_rating': min_rating,
        'selected_radius': radius_str,
        'user_lat': user_lat,
        'user_lng': user_lng,
    }
    return render(request, 'search/search.html', context)