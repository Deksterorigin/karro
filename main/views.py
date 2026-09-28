import datetime
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import logging
import re
from urllib.parse import urlencode

import requests
from django import forms
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Prefetch, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .decorators import login_required_session
from .models import (
    Booking,
    BookingChatMessage,
    Car,
    CarHistory,
    Notification,
    Review,
    Service,
    ServiceStation,
    StationBox,
    User,
)
from .pdf_utils import generate_act_pdf
from .vin_decoder import decode_vin


logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
from .forms import CarForm, ProfileForm, RegistrationForm, ServiceForm, StationForm
from .image_utils import (
    ALLOWED_IMAGE_FORMATS,
    MAX_IMAGE_SIZE_BYTES,
    _save_file,
    _validate_image_upload,
    optimize_image,
    save_optimized_file,
    validate_image_upload,
)


def _show_form_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


def _safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _login_cache_key(ip):
    return f'login_attempts:{ip}'


def _check_login_rate_limit(identifier):
    return cache.get(_login_cache_key(identifier), 0) >= MAX_LOGIN_ATTEMPTS


def _record_failed_login(identifier):
    key = _login_cache_key(identifier)
    if not cache.add(key, 1, LOGIN_LOCKOUT_SECONDS):
        cache.incr(key)


def get_current_user(request):
    return request.user if request.user.is_authenticated else None


def is_valid_vin(vin):
    return bool(re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', (vin or '').upper()))



def _redirect_to_profile(**query_params):
    url = reverse('profile')
    return redirect(f'{url}?{urlencode(query_params)}' if query_params else url)


def geocode_address(city, address):
    """Шукає координати адреси через OpenStreetMap."""
    if not city and not address:
        return None, None

    clean_address = re.sub(
        r'\b(вул\.|вулиця|просп\.|проспект|б-р|бульвар|пл\.|площа|пров\.|провулок|буд\.|будинок)\b',
        '', address, flags=re.IGNORECASE,
    ).strip()

    queries = [
        f'{address}, {city}, Україна' if city else f'{address}, Україна',
        f'{clean_address}, {city}, Україна' if city and clean_address else None,
        f'{city}, Україна' if city else None,
    ]
    headers = {'User-Agent': 'Karro-STO-App/1.0', 'Accept-Language': 'uk,en'}

    for query in queries:
        if not query:
            continue
        try:
            response = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers=headers, timeout=4,
            )
            response.raise_for_status()
            results = response.json()
            if results:
                return float(results[0]['lat']), float(results[0]['lon'])
        except (requests.RequestException, ValueError, KeyError, IndexError) as error:
            logger.warning('Не вдалося знайти координати для "%s": %s', query, error)

    return None, None


def home(request):
    return render(request, 'main/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', '')
        if _check_login_rate_limit(ip):
            messages.error(request, 'Забагато спроб входу. Зачекайте кілька хвилин.')
            return render(request, 'main/login.html')

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            cache.delete(_login_cache_key(ip))
            login(request, user)
            return redirect('profile')

        _record_failed_login(ip)
        messages.error(request, 'Невірний email або пароль.')

    return render(request, 'main/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password'])
                    user.save()
            except IntegrityError:
                messages.error(request, 'Цей email або телефон уже використовується.')
            else:
                login(request, user)
                messages.success(request, 'Реєстрація успішна!')
                return redirect('profile')
        else:
            _show_form_errors(request, form)

    return render(request, 'main/login.html', {'show_register': True})


@login_required_session
@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')


def _handle_update_profile(request, user):
    form = ProfileForm(request.POST, instance=user)
    if not form.is_valid():
        _show_form_errors(request, form)
        return
    try:
        form.save()
    except IntegrityError:
        messages.error(request, 'Цей номер телефону вже зайнятий.')
    else:
        messages.success(request, 'Особисті дані оновлено.')


def _handle_change_password(request, user):
    old_password = request.POST.get('old_password', '')
    new_password = request.POST.get('new_password', '')

    if not user.check_password(old_password):
        messages.error(request, 'Старий пароль введено невірно.')
        return
    if new_password != request.POST.get('new_password2', ''):
        messages.error(request, 'Нові паролі не збігаються.')
        return

    try:
        validate_password(new_password, user)
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)
        return

    user.set_password(new_password)
    user.save(update_fields=['password'])
    update_session_auth_hash(request, user)
    messages.success(request, 'Пароль змінено.')


def _handle_schedule_save(request, station):
    if station is None:
        messages.error(request, 'Спочатку створіть СТО.')
        return

    schedules = station.get_or_create_schedules()
    time_field = forms.TimeField()
    changes = []

    for schedule in schedules:
        day = schedule.day_of_week
        try:
            opening = time_field.clean(request.POST.get(f'opening_time_{day}') or '09:00')
            closing = time_field.clean(request.POST.get(f'closing_time_{day}') or '18:00')
            break_start = forms.TimeField(required=False).clean(request.POST.get(f'break_start_{day}'))
            break_end = forms.TimeField(required=False).clean(request.POST.get(f'break_end_{day}'))
        except forms.ValidationError:
            messages.error(request, f'Перевірте час у графіку за {schedule.get_day_of_week_display().lower()}.')
            return

        is_working = request.POST.get(f'is_working_{day}') == 'on'
        if is_working and opening >= closing:
            messages.error(request, 'Час закриття має бути пізніше часу відкриття.')
            return
        if (break_start is None) != (break_end is None):
            messages.error(request, 'Для перерви вкажіть її початок і кінець.')
            return
        if break_start and not (opening <= break_start < break_end <= closing):
            messages.error(request, 'Перерва має бути в межах робочого часу.')
            return

        changes.append((schedule, is_working, opening, closing, break_start, break_end))

    with transaction.atomic():
        for schedule, is_working, opening, closing, break_start, break_end in changes:
            schedule.is_working = is_working
            schedule.opening_time = opening
            schedule.closing_time = closing
            schedule.break_start = break_start
            schedule.break_end = break_end
            schedule.save()

    messages.success(request, 'Графік роботи збережено.')


def _handle_car_action(request, user, action):
    if not user.is_client:
        messages.error(request, 'Дія доступна лише клієнтам.')
        return

    vin = request.POST.get('vin_code', '').strip().upper()
    if action == 'add_car':
        data = request.POST.copy()
        data['vin_code'] = vin
        form = CarForm(data, instance=Car(user=user))
        if not form.is_valid():
            _show_form_errors(request, form)
            return

        car = form.save(commit=False)
        car.user = user
        try:
            car.save(force_insert=True)
            messages.success(request, f'Автомобіль {car.brand} {car.model} додано до гаража.')
        except IntegrityError:
            messages.error(request, 'Авто з таким VIN-кодом уже є в системі.')
        return

    car = get_object_or_404(Car, vin_code=vin, user=user)
    if action == 'delete_car':
        car.delete()
        messages.success(request, 'Автомобіль видалено.')
    elif action == 'upload_car_photo':
        uploaded_file = request.FILES.get('car_photo')
        valid, error = _validate_image_upload(uploaded_file)
        if not valid:
            messages.error(request, error)
            return
        _save_file(car, 'photo', uploaded_file)
        messages.success(request, 'Фото авто оновлено.')


def _owned_station(request, user, *, allow_first=False):
    station_id = request.POST.get('station_id')
    if station_id:
        return get_object_or_404(ServiceStation, pk=_safe_int(station_id), user=user)
    return ServiceStation.objects.filter(user=user).first() if allow_first else None


def _handle_station_update(request, user):
    if not user.is_station:
        messages.error(request, 'Дія доступна тільки власникам СТО.')
        return None

    station = _owned_station(request, user)
    data = request.POST.copy()
    data['name'] = request.POST.get('station_name', '').strip()
    data['city'] = request.POST.get('station_city', '').strip()
    data['address'] = request.POST.get('station_address', '').strip()
    data['phone'] = request.POST.get('station_phone', '').strip()

    form = StationForm(data, instance=station)
    if not form.is_valid():
        _show_form_errors(request, form)
        return None

    station = form.save(commit=False)
    station.user = user

    if station.latitude is None and station.longitude is None:
        latitude, longitude = geocode_address(station.city, station.address)
        station.latitude = latitude
        station.longitude = longitude

    station.save()
    if request.POST.get('station_id'):
        messages.success(request, 'Інформацію про СТО збережено.')
    else:
        messages.success(request, 'СТО успішно зареєстровано.')

    return _redirect_to_profile(edit_station=station.pk, tab='station')


def _handle_service_action(request, user, action):
    if not user.is_station:
        messages.error(request, 'Дія доступна тільки власникам СТО.')
        return None

    if action == 'delete_service':
        service = get_object_or_404(Service, pk=_safe_int(request.POST.get('service_id')), station__user=user)
        station_id = service.station_id
        service.delete()
        messages.success(request, 'Послугу видалено.')
        return _redirect_to_profile(edit_station=station_id, tab='station')

    station = _owned_station(request, user, allow_first=True)
    if station is None:
        messages.error(request, 'Спочатку збережіть інформацію про СТО.')
        return None

    form = ServiceForm(request.POST, instance=Service(station=station))
    if not form.is_valid():
        _show_form_errors(request, form)
        return None

    service = form.save(commit=False)
    service.station = station
    service.save()
    messages.success(request, f'Послугу "{service.service_name}" додано.')
    return _redirect_to_profile(edit_station=station.pk, tab='station')


def _handle_box_action(request, user, action):
    if not user.is_station:
        messages.error(request, 'Дія доступна тільки власникам СТО.')
        return None

    if action == 'add_box':
        station = get_object_or_404(ServiceStation, pk=_safe_int(request.POST.get('station_id')), user=user)
        name = request.POST.get('box_name', '').strip()
        if not name or len(name) > 50:
            messages.error(request, 'Вкажіть назву боксу до 50 символів.')
        else:
            StationBox.objects.create(station=station, name=name)
            messages.success(request, 'Бокс успішно додано.')
        return _redirect_to_profile(edit_station=station.pk, tab='station')

    box = get_object_or_404(StationBox, pk=_safe_int(request.POST.get('box_id')), station__user=user)
    station_id = box.station_id

    if action == 'toggle_box':
        box.is_active = not box.is_active
        box.save(update_fields=['is_active'])
        messages.success(request, f'Статус боксу "{box.name}" оновлено.')
    elif action == 'delete_box':
        box.delete()
        messages.success(request, 'Бокс видалено.')

    return _redirect_to_profile(edit_station=station_id, tab='station')


def _handle_booking_status(request, user):
    if not user.is_station:
        messages.error(request, 'Дія доступна тільки власникам СТО.')
        return

    booking = get_object_or_404(Booking, pk=_safe_int(request.POST.get('booking_id')), station__user=user)
    status = request.POST.get('status')
    if status == 'completed':
        messages.warning(request, 'Для завершення заявки скористайтеся формою закриття замовлення.')
        return
    if status not in dict(Booking.STATUS_CHOICES):
        messages.error(request, 'Невірний статус заявки.')
        return

    booking.status = status
    booking.save(update_fields=['status'])
    messages.success(request, f'Статус заявки #{booking.pk} оновлено.')


@login_required_session
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'update_profile':
            _handle_update_profile(request, user)
        elif action == 'change_password':
            _handle_change_password(request, user)
        elif action == 'upload_avatar':
            uploaded_file = request.FILES.get('avatar')
            valid, error = _validate_image_upload(uploaded_file)
            if valid:
                _save_file(user, 'avatar', uploaded_file)
                messages.success(request, 'Аватар оновлено.')
            else:
                messages.error(request, error)
        elif action in ('add_car', 'delete_car', 'upload_car_photo'):
            _handle_car_action(request, user, action)
        elif action == 'update_station':
            response = _handle_station_update(request, user)
            if response:
                return response
        elif action in ('add_service', 'delete_service'):
            response = _handle_service_action(request, user, action)
            if response:
                return response
        elif action in ('add_box', 'toggle_box', 'delete_box'):
            return _handle_box_action(request, user, action)
        elif action == 'save_schedule':
            if not user.is_station:
                messages.error(request, 'Дія доступна тільки власникам СТО.')
            else:
                station_id = request.POST.get('station_id') or request.GET.get('edit_station')
                station = get_object_or_404(ServiceStation, pk=_safe_int(station_id), user=user) if station_id else ServiceStation.objects.filter(user=user).first()
                _handle_schedule_save(request, station)
                if station:
                    return _redirect_to_profile(edit_station=station.pk, tab='station')
        elif action == 'update_booking_status':
            _handle_booking_status(request, user)
            return _redirect_to_profile(tab='bookings')
        else:
            messages.error(request, 'Невідома дія.')

        return redirect('profile')

    context = {'user': user}

    if user.is_client:
        bookings_prefetch = Prefetch(
            'bookings',
            queryset=Booking.objects.filter(client=user).select_related('station').order_by('-scheduled_time', '-created_at'),
            to_attr='bookings_list',
        )
        history_prefetch = Prefetch(
            'history_records',
            queryset=CarHistory.objects.select_related('station').order_by('-date', '-created_at'),
            to_attr='history_list',
        )
        cars = Car.objects.filter(user=user).prefetch_related(bookings_prefetch, history_prefetch)

        context.update({
            'client_cars': cars,
            'cars': cars,
            'other_bookings': Booking.objects.filter(client=user, car__isnull=True).select_related('station').order_by('-created_at'),
            'reviews': Review.objects.filter(user=user).select_related('station'),
        })

    if user.is_station:
        stations = ServiceStation.objects.filter(user=user)
        is_new = request.GET.get('action') == 'new_station'
        edit_id = request.GET.get('edit_station')

        if edit_id:
            station = get_object_or_404(stations, pk=_safe_int(edit_id))
        elif is_new:
            station = None
        else:
            station = stations.first()

        context.update({
            'stations': stations,
            'station': station,
            'is_new_station': is_new or station is None,
            'bookings': Booking.objects.filter(station__user=user).select_related('client', 'station', 'box'),
        })
        from accounting.models import Employee, SparePart

        context['station_employees'] = Employee.objects.filter(station__user=user, is_active=True)
        context['station_spare_parts'] = SparePart.objects.filter(station=station) if station else SparePart.objects.filter(station__user=user)

        if station:
            context['services'] = Service.objects.filter(station=station)
            context['station_boxes'] = StationBox.objects.filter(station=station)
            context['schedules'] = station.get_or_create_schedules()

    return render(request, 'main/profile.html', context)


@login_required_session
def client_profile_view(request, client_id):
    user = request.user
    if not user.is_station:
        messages.error(request, 'Доступ заборонено.')
        return redirect('profile')

    client = User.objects.filter(user_id=client_id, role='client', bookings__station__user=user).distinct().first()
    if client is None:
        messages.error(request, 'Клієнта не знайдено серед заявок ваших СТО.')
        return redirect('profile')

    cars = Car.objects.filter(user=client, bookings__station__user=user).distinct()
    return render(request, 'main/client_detail.html', {'client': client, 'cars': cars})


# Заявки, календар і чат

ACTIVE_BOOKING_STATUSES = ('pending', 'confirmed')
MAX_BOOKING_DURATION = 480


def _api_error(message, status=400):
    return JsonResponse({'status': 'error', 'message': message}, status=status)


def _read_json(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _parse_booking_time(value):
    if not isinstance(value, str):
        return None
    scheduled_time = parse_datetime(value)
    if scheduled_time is None:
        return None
    return timezone.make_aware(scheduled_time) if timezone.is_naive(scheduled_time) else scheduled_time


def _booking_duration(value):
    duration = _safe_int(value)
    return duration if (duration is not None and 15 <= duration <= MAX_BOOKING_DURATION) else None


def _schedule_error(station, start, duration):
    local_start = timezone.localtime(start)
    local_end = timezone.localtime(start + datetime.timedelta(minutes=duration))

    if local_start.date() != local_end.date():
        return 'Запис має завершитися того самого дня.'

    schedule = station.get_day_schedule(local_start.weekday())
    if schedule is None or not schedule.is_working:
        return 'СТО не працює в обраний день.'

    start_time = local_start.time().replace(tzinfo=None)
    end_time = local_end.time().replace(tzinfo=None)

    if start_time < schedule.opening_time or end_time > schedule.closing_time:
        return (
            f'СТО працює з {schedule.opening_time.strftime("%H:%M")} '
            f'до {schedule.closing_time.strftime("%H:%M")}. Будь ласка, оберіть інший час.'
        )

    if schedule.break_start and schedule.break_end and start_time < schedule.break_end and end_time > schedule.break_start:
        return 'Час послуги перетинається з перервою СТО.'

    return None


def _free_box(station, start, duration, preferred_box_id=None, exclude_booking_id=None):
    end = start + datetime.timedelta(minutes=duration)
    boxes = list(station.boxes.filter(is_active=True).order_by('pk'))
    if not boxes:
        return None

    bookings = Booking.objects.filter(
        station=station,
        box__in=boxes,
        status__in=ACTIVE_BOOKING_STATUSES,
        scheduled_time__gte=start - datetime.timedelta(days=1),
        scheduled_time__lt=end,
    ).only('id', 'box_id', 'scheduled_time', 'duration')

    if exclude_booking_id is not None:
        bookings = bookings.exclude(pk=exclude_booking_id)

    occupied = {b.box_id for b in bookings if b.scheduled_time + datetime.timedelta(minutes=b.duration) > start}

    if preferred_box_id is not None:
        for box in boxes:
            if box.pk == preferred_box_id and box.pk not in occupied:
                return box

    return next((box for box in boxes if box.pk not in occupied), None)


def _lock_station(station_id):
    ServiceStation.objects.filter(pk=station_id).update(is_verified=F('is_verified'))
    return ServiceStation.objects.select_for_update().get(pk=station_id)


def _chat_message_data(message, user):
    return {
        'id': message.pk,
        'sender_id': message.sender_id,
        'sender_name': message.sender.full_name,
        'sender_role': message.sender.role,
        'is_me': message.sender_id == user.pk,
        'text': message.text or '',
        'image_url': message.image.url if message.image else None,
        'proposed_cost': str(message.proposed_cost) if message.proposed_cost is not None else None,
        'is_approved': message.is_approved,
        'created_at': timezone.localtime(message.created_at).strftime('%d.%m.%Y %H:%M'),
    }


def _booking_participant(booking, user):
    return booking.client_id == user.pk or (booking.station_id is not None and booking.station.user_id == user.pk)


@require_POST
def create_booking_api(request):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)
    if not request.user.is_client:
        return _api_error('Дія доступна лише клієнтам.', 403)

    data = _read_json(request)
    if data is None:
        return _api_error('Невірний формат даних.')

    station_id = _safe_int(data.get('station_id'))
    car_id = data.get('car_id')
    service_name = data.get('service_name')
    description = data.get('description')

    if (
        station_id is None
        or not isinstance(car_id, str)
        or not isinstance(service_name, str)
        or not isinstance(description, str)
        or not service_name.strip()
        or not description.strip()
    ):
        return _api_error('Заповніть СТО, автомобіль, послугу й опис.')

    service_name = service_name.strip()
    description = description.strip()
    if len(service_name) > 150:
        return _api_error('Назва послуги надто довга.')

    station = ServiceStation.objects.filter(pk=station_id).first()
    if station is None:
        return _api_error('СТО не знайдено.', 404)

    car = Car.objects.filter(vin_code=car_id.strip().upper(), user=request.user).first()
    if car is None:
        return _api_error('Обраний автомобіль не належить вам.')

    start = _parse_booking_time(data.get('scheduled_time'))
    if start is None:
        return _api_error('Невірний формат часу.')

    duration = _booking_duration(data.get('duration', 60))
    if duration is None:
        return _api_error('Тривалість має бути від 15 до 480 хвилин.')

    if start <= timezone.now():
        return _api_error('Неможливо записатися на минулий час.')

    error = _schedule_error(station, start, duration)
    if error:
        return _api_error(error)

    try:
        with transaction.atomic():
            station = _lock_station(station.pk)
            error = _schedule_error(station, start, duration)
            if error:
                return _api_error(error)

            if not station.boxes.exists():
                StationBox.objects.create(station=station, name='Бокс 1', is_active=True)
            elif not station.boxes.filter(is_active=True).exists():
                return _api_error('На цьому СТО наразі немає доступних робочих боксів.')

            box = _free_box(station, start, duration)
            if box is None:
                return _api_error('На цей час усі бокси вже зайняті.')

            booking = Booking.objects.create(
                client=request.user,
                station=station,
                car=car,
                box=box,
                duration=duration,
                service_name=service_name,
                description=description,
                scheduled_time=start,
            )
            Notification.objects.create(
                recipient=station.user,
                booking=booking,
                message=f'Нова заявка #{booking.pk}: {request.user.full_name} на {timezone.localtime(start):%d.%m.%Y %H:%M}',
            )
    except DatabaseError:
        logger.exception('Не вдалося створити заявку')
        return _api_error('Не вдалося зайняти час. Спробуйте ще раз.', 409)

    return JsonResponse({'status': 'success', 'message': 'Заявку успішно створено'})


def get_notifications_api(request):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    data = [
        {
            'id': notification.pk,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': timezone.localtime(notification.created_at).strftime('%d.%m.%Y %H:%M'),
            'booking_id': notification.booking_id,
        }
        for notification in notifications
    ]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'status': 'success', 'unread_count': unread_count, 'notifications': data})


@require_POST
def mark_notification_read_api(request, notification_id):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'status': 'success'})


@require_POST
def mark_all_notifications_read_api(request):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


def get_available_slots_api(request, station_id):
    station = get_object_or_404(ServiceStation, pk=station_id)

    try:
        selected_date = datetime.date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        return _api_error('Передайте дату у форматі РРРР-ММ-ДД.')

    duration = _booking_duration(request.GET.get('duration', 60))
    if duration is None:
        return _api_error('Тривалість має бути від 15 до 480 хвилин.')

    schedule = station.get_day_schedule(selected_date.weekday())
    if schedule is None or not schedule.is_working:
        return JsonResponse({'status': 'success', 'slots': [], 'is_closed': True, 'message': 'Вихідний день.'})

    if not station.boxes.filter(is_active=True).exists():
        return JsonResponse({'status': 'success', 'slots': [], 'is_closed': False})

    current = timezone.make_aware(datetime.datetime.combine(selected_date, schedule.opening_time))
    closing = timezone.make_aware(datetime.datetime.combine(selected_date, schedule.closing_time))
    step = datetime.timedelta(minutes=30)
    visit_length = datetime.timedelta(minutes=duration)
    now = timezone.now()
    slots = []

    while current + visit_length <= closing:
        if (
            current > now
            and _schedule_error(station, current, duration) is None
            and _free_box(station, current, duration) is not None
        ):
            slots.append(timezone.localtime(current).strftime('%H:%M'))
        current += step

    return JsonResponse({'status': 'success', 'slots': slots, 'is_closed': False})


def get_calendar_events_api(request, station_id):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    station = ServiceStation.objects.filter(pk=station_id, user=request.user).first()
    if station is None:
        return _api_error('Немає доступу до календаря.', 403)

    start = _parse_booking_time(request.GET.get('start'))
    end = _parse_booking_time(request.GET.get('end'))
    if start is None or end is None or start >= end:
        return _api_error('Передайте коректний початок і кінець періоду.')

    bookings = Booking.objects.filter(
        station=station,
        scheduled_time__gte=start - datetime.timedelta(days=1),
        scheduled_time__lt=end,
    ).select_related('client', 'car', 'box')

    colors = {'confirmed': '#F59E0B', 'completed': '#10B981', 'cancelled': '#EF4444'}
    events = []

    for booking in bookings:
        booking_end = booking.scheduled_time + datetime.timedelta(minutes=booking.duration)
        if booking_end <= start:
            continue

        car_name = f'{booking.car.brand} {booking.car.model}' if booking.car else ''
        events.append({
            'id': booking.pk,
            'title': f'{booking.client.full_name} ({car_name}) - {booking.service_name or "Діагностика"}',
            'start': booking.scheduled_time.isoformat(),
            'end': booking_end.isoformat(),
            'color': colors.get(booking.status, '#3B82F6'),
            'extendedProps': {
                'clientName': booking.client.full_name,
                'car': car_name or 'Не вказано',
                'description': booking.description,
                'status': booking.get_status_display(),
                'boxName': booking.box.name if booking.box else 'Не визначено',
            },
        })

    return JsonResponse(events, safe=False)


@require_POST
def reschedule_booking_api(request, booking_id):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    booking = Booking.objects.select_related('station').filter(pk=booking_id, station__user=request.user).first()
    if booking is None:
        return _api_error('Заявку не знайдено.', 404)

    data = _read_json(request)
    if data is None:
        return _api_error('Невірний формат даних.')

    start = _parse_booking_time(data.get('scheduled_time'))
    if start is None:
        return _api_error('Невірний формат часу.')
    if start <= timezone.now():
        return _api_error('Час не може бути в минулому.')
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        return _api_error('Цю заявку вже не можна перенести.')

    error = _schedule_error(booking.station, start, booking.duration)
    if error:
        return _api_error(error)

    try:
        with transaction.atomic():
            station = _lock_station(booking.station_id)
            booking = Booking.objects.select_for_update().get(pk=booking.pk, station=station)

            if booking.status not in ACTIVE_BOOKING_STATUSES:
                return _api_error('Цю заявку вже не можна перенести.')

            error = _schedule_error(station, start, booking.duration)
            if error:
                return _api_error(error)

            box = _free_box(station, start, booking.duration, preferred_box_id=booking.box_id, exclude_booking_id=booking.pk)
            if box is None:
                return _api_error('Усі робочі бокси зайняті.')

            booking.scheduled_time = start
            booking.box = box
            booking.save(update_fields=['scheduled_time', 'box'])

            local_start = timezone.localtime(start)
            Notification.objects.create(
                recipient=booking.client,
                booking=booking,
                message=f'Час заявки #{booking.pk} змінено на {local_start:%d.%m.%Y %H:%M} ({box.name})',
            )
    except DatabaseError:
        logger.exception('Не вдалося перенести заявку %s', booking_id)
        return _api_error('Не вдалося зайняти час. Спробуйте ще раз.', 409)

    return JsonResponse({
        'status': 'success',
        'message': f'Перенесено на {local_start:%d.%m.%Y %H:%M}',
        'box_name': box.name,
    })


def booking_chat_api(request, booking_id):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    booking = get_object_or_404(
        Booking.objects.select_related('station'),
        Q(client=request.user) | Q(station__user=request.user),
        pk=booking_id,
    )
    user = request.user

    if request.method == 'GET':
        chat_messages = BookingChatMessage.objects.filter(booking=booking).select_related('sender')
        chat_messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
        return JsonResponse({'status': 'success', 'messages': [_chat_message_data(m, user) for m in chat_messages]})

    if request.method != 'POST':
        return _api_error('Метод не підтримується.', 405)

    if booking.status == 'completed':
        return _api_error('Цю заявку вже завершено. Чат закрито для нових повідомлень.')

    text = request.POST.get('text', '').strip()
    image = request.FILES.get('image')
    cost_text = request.POST.get('proposed_cost', '').strip()

    if image:
        valid, error = _validate_image_upload(image)
        if not valid:
            return _api_error(error)

    proposed_cost = None
    if cost_text:
        if not booking.station_id or booking.station.user_id != user.pk:
            return _api_error('Запропонувати суму може лише власник СТО.', 403)
        try:
            proposed_cost = Decimal(cost_text)
        except InvalidOperation:
            return _api_error('Вкажіть коректну суму.')

        if not proposed_cost.is_finite() or proposed_cost <= 0 or proposed_cost.as_tuple().exponent < -2 or proposed_cost > Decimal('99999999.99'):
            return _api_error('Вкажіть додатну суму з точністю до копійок.')

    if not text and not image and proposed_cost is None:
        return _api_error('Повідомлення не може бути порожнім.')

    if image:
        image = optimize_image(image)

    message = BookingChatMessage.objects.create(
        booking=booking,
        sender=user,
        text=text or None,
        image=image,
        proposed_cost=proposed_cost,
    )

    recipient = booking.station.user if user.pk == booking.client_id and booking.station_id else booking.client
    if recipient.pk != user.pk:
        notification_text = f'Нове повідомлення у чаті замовлення #{booking.pk}'
        if image:
            notification_text += ' (фото)'
        Notification.objects.create(recipient=recipient, booking=booking, message=notification_text)

    return JsonResponse({'status': 'success', 'message': _chat_message_data(message, user)})


@require_POST
def respond_cost_approval_api(request, message_id):
    if not request.user.is_authenticated:
        return _api_error('Увійдіть в акаунт.', 401)

    action = request.POST.get('action')
    if action not in ('approve', 'reject', 'decline'):
        return _api_error('Оберіть підтвердження або відхилення.')

    with transaction.atomic():
        message = get_object_or_404(
            BookingChatMessage.objects.select_for_update().select_related('booking__station'),
            pk=message_id,
            booking__client=request.user,
        )
        booking = message.booking

        if booking.status == 'completed':
            return _api_error('Цю заявку вже завершено.')

        if message.proposed_cost is None:
            return _api_error('У цьому повідомленні немає запропонованої суми.')
        if message.is_approved is not None:
            return _api_error('Відповідь на цю пропозицію вже збережено.')

        message.is_approved = action == 'approve'
        message.save(update_fields=['is_approved'])

        if booking.station_id:
            status_text = 'підтвердив' if message.is_approved else 'відхилив'
            Notification.objects.create(
                recipient=booking.station.user,
                booking=booking,
                message=f'Клієнт {status_text} додаткову суму {message.proposed_cost} грн у чаті #{booking.pk}',
            )

    return JsonResponse({
        'status': 'success',
        'is_approved': message.is_approved,
        'message': 'Суму підтверджено.' if message.is_approved else 'Суму відхилено.',
    })


@login_required_session
def download_act_pdf_view(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('station', 'car', 'client'),
        Q(client=request.user) | Q(station__user=request.user),
        pk=booking_id,
    )

    pdf_bytes = generate_act_pdf(booking)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="act_{booking.pk:05d}.pdf"'
    return response


def decode_vin_api(request):
    result = decode_vin(request.GET.get('vin', ''))
    return JsonResponse(result, status=400 if result['status'] == 'error' else 200)