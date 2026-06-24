import json
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth
from .models import User, ServiceStation, Review, Booking

def dashboard_callback(request, context):
    """
    Панель аналітики для Django Unfold.
    Збирає показники KPI та дані для побудови графіків Chart.js.
    """
    today = timezone.now().date()
    
    # Розрахунок показників KPI
    total_users = User.objects.count()
    active_stations = ServiceStation.objects.filter(is_verified=True).count()
    pending_stations = ServiceStation.objects.filter(is_verified=False).count()
    new_reviews_today = Review.objects.filter(date=today).count()
    active_bookings = Booking.objects.filter(status='pending').count()

    context.update({
        "kpi": [
            {
                "title": "Всього користувачів",
                "metric": str(total_users),
                "footer": "Зареєстровано на платформі",
            },
            {
                "title": "Активні СТО",
                "metric": str(active_stations),
                "footer": f"Очікують на перевірку: {pending_stations}",
            },
            {
                "title": "Нові відгуки",
                "metric": str(new_reviews_today),
                "footer": "Залишено за сьогодні",
            },
            {
                "title": "Активні заявки",
                "metric": str(active_bookings),
                "footer": "Нових заявок в очікуванні",
            },
        ],
    })

    # Структура даних для графіків
    chart_data = {
        'line': {'labels': [], 'users': [], 'stations': []},
        'donut': {'labels': [], 'data': []},
        'bar': {'data': [0, 0, 0, 0, 0]}
    }

    # Реєстрації по місяцях (лінійний графік)
    users_by_month = User.objects.annotate(month=TruncMonth('date_joined')).values('month').annotate(c=Count('user_id')).order_by('month')
    stations_by_month = ServiceStation.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(c=Count('station_id')).order_by('month')
    
    months_set = set()
    user_dict = {}
    station_dict = {}

    for u in users_by_month:
        if u['month']:
            m_str = u['month'].strftime("%b %Y")
            months_set.add(m_str)
            user_dict[m_str] = u['c']

    for s in stations_by_month:
        if s['month']:
            m_str = s['month'].strftime("%b %Y")
            months_set.add(m_str)
            station_dict[m_str] = s['c']

    sorted_months = sorted(list(months_set))
    chart_data['line']['labels'] = sorted_months
    chart_data['line']['users'] = [user_dict.get(m, 0) for m in sorted_months]
    chart_data['line']['stations'] = [station_dict.get(m, 0) for m in sorted_months]

    # СТО по містах (кругова діаграма, топ 5)
    cities = ServiceStation.objects.exclude(city='').values('city').annotate(c=Count('station_id')).order_by('-c')[:5]
    for c in cities:
        chart_data['donut']['labels'].append(c['city'])
        chart_data['donut']['data'].append(c['c'])

    # Розподіл відгуків за оцінками (стовпчатий графік)
    reviews = Review.objects.values('rating').annotate(c=Count('review_id'))
    for r in reviews:
        idx = r['rating'] - 1
        if 0 <= idx < 5:
            chart_data['bar']['data'][idx] = r['c']

    context["chart_data"] = json.dumps(chart_data)
    
    return context
