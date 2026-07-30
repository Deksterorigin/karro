import datetime
from datetime import date
from decimal import Decimal
import json
import logging
import os
import re
import time
from collections import defaultdict
from urllib.parse import urlencode

import requests
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import login_required_session
from .models import (
    User, Car, Review, ServiceStation, Service, Booking, Notification,
    CarHistory, BookingChatMessage, StationBox
)
from .pdf_utils import generate_act_pdf
from .vin_decoder import decode_vin

logger = logging.getLogger(__name__)

# Допоміжні конвертери типів
def _safe_int(val, default=None):
    if val is None or val == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _safe_float(val, default=None):
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# Лімітатор спроб авторизації (in-memory)
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

def _check_login_rate_limit(identifier: str) -> bool:
    now = time.time()
    _login_attempts[identifier] = [
        t for t in _login_attempts[identifier]
        if now - t < LOGIN_LOCKOUT_SECONDS
    ]
    if len(_login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        return True
    _login_attempts[identifier].append(now)
    return False

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
}
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024

def get_current_user(request):
    return request.user if request.user.is_authenticated else None

def is_valid_vin(vin: str) -> bool:
    return bool(re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', (vin or '').upper()))

def _validate_image_upload(uploaded_file):
    if not uploaded_file:
        return False, 'Оберіть файл для завантаження.'

    content_type = uploaded_file.content_type
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, 'Дозволені лише зображення (JPEG, PNG, WebP, GIF).'

    _, ext = os.path.splitext(uploaded_file.name.lower())
    if ext not in ALLOWED_IMAGE_TYPES[content_type]:
        return False, f'Розширення "{ext}" не відповідає типу "{content_type}".'

    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        return False, 'Розмір файлу перевищує 3 МБ.'

    return True, None

def optimize_image(uploaded_file, max_size=(1920, 1080), quality=85):
    if not uploaded_file:
        return uploaded_file
    try:
        from PIL import Image, ImageOps
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile

        img = Image.open(uploaded_file)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

        output = BytesIO()
        fmt = img.format if img.format in ['JPEG', 'PNG', 'WEBP'] else 'JPEG'
        if fmt == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        img.save(output, format=fmt, quality=quality, optimize=True)
        output.seek(0)

        return InMemoryUploadedFile(
            output, 'ImageField', uploaded_file.name,
            f'image/{fmt.lower()}', output.getbuffer().nbytes, None
        )
    except Exception as err:
        logger.warning('Image optimization error: %s', err)
        return uploaded_file

def _save_file(instance, field_name: str, uploaded_file):
    old_file = getattr(instance, field_name)
    if old_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass
    setattr(instance, field_name, optimize_image(uploaded_file))
    instance.save()

def _redirect_to_profile(**query_params):
    url = reverse('profile')
    if query_params:
        url += '?' + urlencode(query_params)
    return redirect(url)

def geocode_address(city: str, address: str):
    if not address and not city:
        return None, None

    clean_addr = re.sub(
        r'\b(вул\.|вулиця|просп\.|проспект|б-р|бульвар|пл\.|площа|пров\.|провулок|буд\.|будинок)\b',
        '', address, flags=re.IGNORECASE
    ).strip()

    queries = [
        f"{address}, {city}, Україна" if city else f"{address}, Україна",
        f"{clean_addr}, {city}, Україна" if city and clean_addr else None,
        f"{city}, Україна" if city else None
    ]
    headers = {'User-Agent': 'Karro-STO-App/1.0', 'Accept-Language': 'uk,en'}

    for q in queries:
        if not q:
            continue
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': q, 'format': 'json', 'limit': 1},
                headers=headers, timeout=4
            )
            if resp.status_code == 200 and (data := resp.json()):
                return float(data[0]['lat']), float(data[0]['lon'])
        except Exception as err:
            logger.warning('Geocoding query failed for "%s": %s', q, err)

    return None, None

# --- Основні представлення ---

def home(request):
    return render(request, 'main/home.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', '')
        if _check_login_rate_limit(ip):
            messages.error(request, 'Забагато спроб входу. Спробуйте через 5 хвилин.')
            return render(request, 'main/login.html')

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if user := authenticate(request, email=email, password=password):
            if not user.is_active:
                messages.error(request, 'Ваш акаунт заблоковано.')
            else:
                login(request, user)
                return redirect('profile')
        else:
            messages.error(request, 'Невірний email або пароль.')

    return render(request, 'main/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'client')

        ctx = {'show_register': True}

        if not full_name:
            messages.error(request, "Введіть своє ім'я.")
            return render(request, 'main/login.html', ctx)

        if role not in ('client', 'station'):
            messages.error(request, 'Невірна роль.')
            return render(request, 'main/login.html', ctx)

        try:
            validate_password(password)
        except ValidationError as err:
            for msg in err.messages:
                messages.error(request, msg)
            return render(request, 'main/login.html', ctx)

        if password != password2:
            messages.error(request, 'Паролі не збігаються.')
            return render(request, 'main/login.html', ctx)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Такий email вже зареєстровано.')
            return render(request, 'main/login.html', ctx)

        if User.objects.filter(phone=phone).exists():
            messages.error(request, 'Такий телефон вже використовується.')
            return render(request, 'main/login.html', ctx)

        user = User.objects.create_user(
            email=email, full_name=full_name, phone=phone,
            role=role, password=password
        )
        login(request, user)
        messages.success(request, 'Реєстрація успішна! Ласкаво просимо.')
        return redirect('profile')

    return render(request, 'main/login.html', {'show_register': True})

@login_required_session
@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')

# --- Диспетчери операцій профілю ---

def _handle_update_profile(request, user):
    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    if not full_name:
        messages.error(request, "Ім'я не може бути порожнім.")
    elif User.objects.filter(phone=phone).exclude(user_id=user.user_id).exists():
        messages.error(request, 'Цей номер телефону вже використовується.')
    else:
        user.full_name = full_name
        user.phone = phone
        user.save(update_fields=['full_name', 'phone'])
        messages.success(request, 'Дані успішно оновлено.')

def _handle_change_password(request, user):
    old_pw = request.POST.get('old_password', '')
    new_pw = request.POST.get('new_password', '')
    new_pw2 = request.POST.get('new_password2', '')

    if not user.check_password(old_pw):
        messages.error(request, 'Поточний пароль введено невірно.')
    elif new_pw != new_pw2:
        messages.error(request, 'Нові паролі не збігаються.')
    else:
        try:
            validate_password(new_pw)
        except ValidationError as err:
            for msg in err.messages:
                messages.error(request, msg)
            return
        user.set_password(new_pw)
        user.save(update_fields=['password'])
        update_session_auth_hash(request, user)
        messages.success(request, 'Пароль успішно змінено.')

def _handle_schedule_save(request, station):
    if not station:
        messages.error(request, 'Спочатку оберіть або створіть СТО.')
        return
    for day in range(7):
        sch = station.get_day_schedule(day)
        sch.is_working = request.POST.get(f'is_working_{day}') == 'on'
        sch.opening_time = request.POST.get(f'opening_time_{day}', '09:00') or '09:00'
        sch.closing_time = request.POST.get(f'closing_time_{day}', '18:00') or '18:00'
        sch.break_start = request.POST.get(f'break_start_{day}', '').strip() or None
        sch.break_end = request.POST.get(f'break_end_{day}', '').strip() or None
        sch.save()
    messages.success(request, 'Графік роботи СТО успішно збережено.')

def _handle_car_action(request, user, action):
    if not user.is_client:
        messages.error(request, 'Ця дія доступна тільки клієнтам.')
        return

    vin = request.POST.get('vin_code', '').strip().upper()
    if action == 'add_car':
        brand = request.POST.get('brand', '').strip()
        model = request.POST.get('model', '').strip()
        year_str = request.POST.get('year', '').strip()
        year = _safe_int(year_str)

        if not is_valid_vin(vin):
            messages.error(request, 'Невірний VIN-код. Має бути 17 символів.')
        elif not brand or not model:
            messages.error(request, 'Введіть марку та модель автомобіля.')
        elif not year or not (1900 <= year <= date.today().year + 1):
            messages.error(request, f'Рік має бути між 1900 і {date.today().year + 1}.')
        elif Car.objects.filter(vin_code=vin).exists():
            messages.error(request, 'Автомобіль з таким VIN вже зареєстровано.')
        else:
            Car.objects.create(vin_code=vin, brand=brand, model=model, year=year, user=user)
            messages.success(request, f'Автомобіль {brand} {model} додано.')

    elif action == 'delete_car':
        deleted, _ = Car.objects.filter(vin_code=vin, user=user).delete()
        if deleted:
            messages.success(request, 'Автомобіль видалено.')
        else:
            messages.error(request, 'Автомобіль не знайдено.')

    elif action == 'upload_car_photo':
        car = Car.objects.filter(vin_code=vin, user=user).first()
        if not car:
            messages.error(request, 'Автомобіль не знайдено.')
            return
        valid, error_msg = _validate_image_upload(request.FILES.get('car_photo'))
        if not valid:
            messages.error(request, error_msg)
        else:
            _save_file(car, 'photo', request.FILES.get('car_photo'))
            messages.success(request, 'Фото автомобіля оновлено.')

def _handle_station_update(request, user):
    if not user.is_station:
        messages.error(request, 'Ця дія доступна тільки власникам СТО.')
        return None

    st_id = _safe_int(request.POST.get('station_id'))
    name = request.POST.get('station_name', '').strip()
    city = request.POST.get('station_city', '').strip()
    address = request.POST.get('station_address', '').strip()
    phone = request.POST.get('station_phone', '').strip()

    if not name or not address:
        messages.error(request, "Назва та адреса СТО обов'язкові.")
        return None

    lat = _safe_float(request.POST.get('latitude'))
    lng = _safe_float(request.POST.get('longitude'))
    if lat is None or lng is None:
        lat, lng = geocode_address(city, address)

    station = ServiceStation.objects.filter(user=user, pk=st_id).first() if st_id else None
    if station:
        station.name, station.city, station.address = name, city, address
        station.phone, station.latitude, station.longitude = phone, lat, lng
        station.save()
        messages.success(request, 'Дані СТО оновлено.')
        return _redirect_to_profile(edit_station=station.pk, tab='station')
    else:
        new_st = ServiceStation.objects.create(
            user=user, name=name, city=city, address=address,
            phone=phone, latitude=lat, longitude=lng
        )
        messages.success(request, 'Нову СТО успішно створено.')
        return _redirect_to_profile(edit_station=new_st.pk, tab='station')

def _handle_service_action(request, user, action):
    if not user.is_station:
        messages.error(request, 'Ця дія доступна тільки власникам СТО.')
        return None

    if action == 'add_service':
        st_id = _safe_int(request.POST.get('station_id'))
        station = ServiceStation.objects.filter(user=user, pk=st_id).first() if st_id else ServiceStation.objects.filter(user=user).first()
        if not station:
            messages.error(request, 'Спочатку заповніть профіль СТО.')
            return None

        service_name = request.POST.get('service_name', '').strip()
        price = _safe_float(request.POST.get('price'))
        description = request.POST.get('description', '').strip()

        if not service_name:
            messages.error(request, 'Введіть назву послуги.')
        elif not price or price <= 0:
            messages.error(request, 'Ціна має бути числом більше 0.')
        else:
            Service.objects.create(service_name=service_name, price=price, description=description, station=station)
            messages.success(request, f'Послугу "{service_name}" додано.')
            return _redirect_to_profile(edit_station=station.pk, tab='station')

    elif action == 'delete_service':
        svc_id = request.POST.get('service_id', '')
        service = Service.objects.filter(service_id=svc_id, station__user=user).first()
        if service:
            st_pk = service.station.pk
            service.delete()
            messages.success(request, 'Послугу видалено.')
            return _redirect_to_profile(edit_station=st_pk, tab='station')
        else:
            messages.error(request, 'Послугу не знайдено.')
    return None

def _handle_box_action(request, user, action):
    if not user.is_station:
        messages.error(request, 'Ця дія доступна тільки власникам СТО.')
        return None

    if action == 'add_box':
        st_id = _safe_int(request.POST.get('station_id'))
        box_name = request.POST.get('box_name', '').strip()
        station = get_object_or_404(ServiceStation, pk=st_id, user=user)
        if box_name:
            StationBox.objects.create(station=station, name=box_name, is_active=True)
            messages.success(request, 'Робочий бокс успішно додано.')
        return _redirect_to_profile(edit_station=station.pk, tab='station')

    elif action == 'toggle_box':
        box_id = request.POST.get('box_id')
        box = get_object_or_404(StationBox, pk=box_id, station__user=user)
        box.is_active = not box.is_active
        box.save()
        messages.success(request, f'Статус боксу "{box.name}" оновлено.')
        return _redirect_to_profile(edit_station=box.station.pk, tab='station')

    elif action == 'delete_box':
        box_id = request.POST.get('box_id')
        box = get_object_or_404(StationBox, pk=box_id, station__user=user)
        st_pk = box.station.pk
        box.delete()
        messages.success(request, 'Робочий бокс видалено.')
        return _redirect_to_profile(edit_station=st_pk, tab='station')

    return None

@login_required_session
def profile_view(request):
    user = get_current_user(request)
    if user is None:
        return redirect('login')

    context = {'user': user}

    if user.is_client:
        bookings_prefetch = Prefetch(
            'bookings',
            queryset=Booking.objects.filter(client=user).order_by('-scheduled_time', '-created_at').select_related('station'),
            to_attr='bookings_list'
        )
        history_prefetch = Prefetch(
            'history_records',
            queryset=CarHistory.objects.order_by('-date', '-created_at').select_related('station'),
            to_attr='history_list'
        )
        client_cars = Car.objects.filter(user=user).prefetch_related(bookings_prefetch, history_prefetch)
        context['client_cars'] = client_cars
        context['other_bookings'] = Booking.objects.filter(client=user, car__isnull=True).order_by('-created_at').select_related('station')
        context['cars'] = client_cars
        context['reviews'] = Review.objects.filter(user=user).select_related('station')

    station = None
    if user.is_station:
        stations = ServiceStation.objects.filter(user=user)
        context['stations'] = stations

        edit_id = _safe_int(request.GET.get('edit_station'))
        if edit_id:
            station = stations.filter(pk=edit_id).first()
        is_new = request.GET.get('action') == 'new_station'
        if not station and not is_new and stations.exists():
            station = stations.first()

        context['station'] = station
        context['is_new_station'] = is_new or (not station)
        if station:
            context['services'] = Service.objects.filter(station=station)
            context['station_boxes'] = StationBox.objects.filter(station=station)
            context['schedules'] = station.get_or_create_schedules()

        context['bookings'] = Booking.objects.filter(station__user=user).select_related('client', 'station', 'box')
        from accounting.models import Employee, SparePart
        context['station_employees'] = Employee.objects.filter(station__user=user, is_active=True)
        context['station_spare_parts'] = SparePart.objects.filter(station=station) if station else SparePart.objects.filter(station__user=user)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_profile':
            _handle_update_profile(request, user)
        elif action == 'change_password':
            _handle_change_password(request, user)
        elif action == 'save_schedule':
            _handle_schedule_save(request, station)
            return redirect('profile')
        elif action == 'upload_avatar':
            valid, err = _validate_image_upload(request.FILES.get('avatar'))
            if not valid:
                messages.error(request, err)
            else:
                _save_file(user, 'avatar', request.FILES.get('avatar'))
                messages.success(request, 'Аватар оновлено.')
        elif action in ('add_car', 'delete_car', 'upload_car_photo'):
            _handle_car_action(request, user, action)
        elif action == 'update_station':
            if res := _handle_station_update(request, user):
                return res
        elif action in ('add_service', 'delete_service'):
            if res := _handle_service_action(request, user, action):
                return res
        elif action in ('add_box', 'toggle_box', 'delete_box'):
            if res := _handle_box_action(request, user, action):
                return res
        elif action == 'update_booking_status':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                b_id = request.POST.get('booking_id')
                status = request.POST.get('status')
                booking = Booking.objects.filter(id=b_id, station__user=user).first()
                if booking and status in dict(Booking.STATUS_CHOICES):
                    booking.status = status
                    booking.save(update_fields=['status'])
                    messages.success(request, f'Статус заявки #{booking.id} оновлено.')
                else:
                    messages.error(request, 'Неможливо оновити статус.')
                return _redirect_to_profile(tab='bookings')

        return redirect('profile')

    return render(request, 'main/profile.html', context)

# --- API Заявок та Календаря ---

@require_POST
def create_booking_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
        station_id = data.get('station_id')
        car_id = data.get('car_id')
        service_name = data.get('service_name', '').strip()
        description = data.get('description', '').strip()
        scheduled_time = data.get('scheduled_time')

        if not station_id or not description or not service_name or not scheduled_time:
            return JsonResponse({'status': 'error', 'message': 'Будь ласка, заповніть усі обов\'язкові поля'}, status=400)

        client = request.user
        if client.role != 'client' or not client.is_active:
            return JsonResponse({'status': 'error', 'message': 'Доступ заборонено'}, status=403)

        station = ServiceStation.objects.get(pk=station_id)
        if not car_id:
            return JsonResponse({'status': 'error', 'message': 'Будь ласка, оберіть автомобіль'}, status=400)

        car = Car.objects.filter(vin_code=car_id, user=client).first()
        if not car:
            return JsonResponse({'status': 'error', 'message': 'Обраний автомобіль не знайдено або він не належить вам'}, status=400)

        try:
            scheduled_dt = datetime.datetime.fromisoformat(scheduled_time)
            if django_settings.USE_TZ and timezone.is_naive(scheduled_dt):
                scheduled_dt = timezone.make_aware(scheduled_dt)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Невірний формат часу'}, status=400)

        if scheduled_dt < timezone.now():
            return JsonResponse({'status': 'error', 'message': 'Неможливо записатися на минулий час'}, status=400)

        sch = station.get_day_schedule(scheduled_dt.weekday())
        if not sch or not sch.is_working:
            return JsonResponse({'status': 'error', 'message': 'СТО не працює в обраний день тижня (Вихідний).'}, status=400)

        visit_time = scheduled_dt.time()
        if visit_time < sch.opening_time or visit_time > sch.closing_time:
            return JsonResponse({
                'status': 'error',
                'message': f'СТО у цей день працює з {sch.opening_time.strftime("%H:%M")} до {sch.closing_time.strftime("%H:%M")}. Будь ласка, оберіть інший час.'
            }, status=400)

        if sch.break_start and sch.break_end and (sch.break_start <= visit_time < sch.break_end):
            return JsonResponse({
                'status': 'error',
                'message': f'У СТО обідня перерва з {sch.break_start.strftime("%H:%M")} до {sch.break_end.strftime("%H:%M")}.'
            }, status=400)

        boxes = station.boxes.filter(is_active=True)
        if not boxes.exists():
            StationBox.objects.create(station=station, name="Бокс 1", is_active=True)
            boxes = station.boxes.filter(is_active=True)

        duration = max(15, min(_safe_int(data.get('duration'), 60), 480))
        slot_start = scheduled_dt
        slot_end = slot_start + datetime.timedelta(minutes=duration)

        conflicting = Booking.objects.filter(
            station=station, status__in=['pending', 'confirmed'],
            scheduled_time__gte=slot_start - datetime.timedelta(days=1), scheduled_time__lt=slot_end
        )
        occupied_box_ids = {
            b.box_id for b in conflicting
            if (b.scheduled_time + datetime.timedelta(minutes=b.duration)) > slot_start
        }

        free_box = next((box for box in boxes if box.pk not in occupied_box_ids), None)
        if not free_box:
            return JsonResponse({
                'status': 'error',
                'message': 'Нажаль, на цей час усі бокси вже зайняті. Будь ласка, оберіть інший час.'
            }, status=400)


        booking = Booking.objects.create(
            client=client, station=station, car=car, service_name=service_name,
            description=description, scheduled_time=scheduled_dt, box=free_box, duration=duration
        )
        Notification.objects.create(
            recipient=station.user, booking=booking,
            message=f"Нова заявка #{booking.id}: {client.full_name} на {scheduled_dt.strftime('%d.%m.%Y %H:%M')}"
        )
        return JsonResponse({"status": "success", "message": "Заявку успішно створено"})
    except Exception as err:
        logger.error('Booking API Error: %s', err, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Помилка створення заявки'}, status=500)

@login_required_session
def client_profile_view(request, client_id):
    user = get_current_user(request)
    if not user.is_station:
        messages.error(request, 'Доступ заборонено.')
        return redirect('profile')

    client = User.objects.filter(user_id=client_id, role='client').first()
    if not client:
        messages.error(request, 'Клієнта не знайдено.')
        return redirect('profile')

    if not Booking.objects.filter(client=client, station__user=user).exists():
        messages.error(request, 'Доступ заборонено: у клієнта немає заявок на вашій СТО.')
        return redirect('profile')

    return render(request, 'main/client_detail.html', {
        'client': client,
        'cars': Car.objects.filter(user=client)
    })

@login_required_session
def get_notifications_api(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    notifs = Notification.objects.filter(recipient=user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    data = [{
        'id': n.id,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
        'booking_id': n.booking.id if n.booking else None
    } for n in notifs]

    return JsonResponse({'status': 'success', 'unread_count': unread_count, 'notifications': data})

@require_POST
@login_required_session
def mark_notification_read_api(request, notification_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    notif = get_object_or_404(Notification, id=notification_id, recipient=user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'status': 'success'})

@require_POST
@login_required_session
def mark_all_notifications_read_api(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

def get_available_slots_api(request, station_id):
    station = get_object_or_404(ServiceStation, pk=station_id)
    date_str = request.GET.get('date')
    duration = max(15, min(_safe_int(request.GET.get('duration'), 60), 480))

    if not date_str:
        return JsonResponse({'status': 'error', 'message': 'Параметр date обов\'язковий'}, status=400)

    try:
        dt_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Невірний формат дати'}, status=400)

    boxes = station.boxes.filter(is_active=True)
    if not boxes.exists():
        StationBox.objects.create(station=station, name="Бокс 1", is_active=True)
        boxes = station.boxes.filter(is_active=True)

    start_dt = timezone.make_aware(datetime.datetime.combine(dt_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(dt_date, datetime.time.max))

    bookings = Booking.objects.filter(
        station=station, scheduled_time__range=(start_dt, end_dt),
        status__in=['pending', 'confirmed']
    ).select_related('box')

    sch = station.get_day_schedule(dt_date.weekday())
    if not sch or not sch.is_working:
        return JsonResponse({'status': 'success', 'slots': [], 'is_closed': True, 'message': 'Вихідний день.'})

    current_slot = timezone.make_aware(datetime.datetime.combine(dt_date, sch.opening_time))
    work_end = timezone.make_aware(datetime.datetime.combine(dt_date, sch.closing_time))
    now = timezone.now()
    available_slots = []

    while current_slot <= work_end - datetime.timedelta(minutes=duration):
        if current_slot > now:
            slot_start_time = current_slot.time()
            slot_end_dt = current_slot + datetime.timedelta(minutes=duration)
            slot_end_time = slot_end_dt.time()

            in_break = False
            if sch.break_start and sch.break_end:
                if not (slot_end_time <= sch.break_start or slot_start_time >= sch.break_end):
                    in_break = True

            if not in_break:
                free_box = False
                for box in boxes:
                    has_conflict = any(
                        b.box_id == box.pk and (b.scheduled_time < slot_end_dt and (b.scheduled_time + datetime.timedelta(minutes=b.duration)) > current_slot)
                        for b in bookings
                    )
                    if not has_conflict:
                        free_box = True
                        break

                if free_box:
                    available_slots.append(current_slot.strftime('%H:%M'))

        current_slot += datetime.timedelta(minutes=30)

    return JsonResponse({'status': 'success', 'slots': available_slots, 'is_closed': False})

@login_required_session
def get_calendar_events_api(request, station_id):
    station = get_object_or_404(ServiceStation, pk=station_id)
    if station.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    if not start_str or not end_str:
        return JsonResponse({'status': 'error', 'message': 'Параметри обов\'язкові'}, status=400)

    try:
        start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Невірні дати'}, status=400)

    bookings = Booking.objects.filter(
        station=station, scheduled_time__range=(start_dt, end_dt)
    ).select_related('client', 'car', 'box')

    colors = {'confirmed': '#F59E0B', 'completed': '#10B981', 'cancelled': '#EF4444'}
    events = []

    for b in bookings:
        if not b.scheduled_time:
            continue
        b_end = b.scheduled_time + datetime.timedelta(minutes=b.duration)
        car_name = f"{b.car.brand} {b.car.model}" if b.car else ""

        events.append({
            'id': b.id,
            'title': f'{b.client.full_name} ({car_name}) - {b.service_name or "Діагностика"}',
            'start': b.scheduled_time.isoformat(),
            'end': b_end.isoformat(),
            'color': colors.get(b.status, '#3B82F6'),
            'extendedProps': {
                'clientName': b.client.full_name,
                'car': car_name or 'Не вказано',
                'description': b.description,
                'status': b.get_status_display(),
                'boxName': b.box.name if b.box else 'Не визначено',
            }
        })

    return JsonResponse(events, safe=False)

@require_POST
@login_required_session
def reschedule_booking_api(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, station__user=request.user)
    try:
        data = json.loads(request.body)
        new_start_str = data.get('scheduled_time')
        new_start = datetime.datetime.fromisoformat(new_start_str.replace('Z', '+00:00'))
        if timezone.is_naive(new_start):
            new_start = timezone.make_aware(new_start)
        new_end = new_start + datetime.timedelta(minutes=booking.duration)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Невірний формат даних'}, status=400)

    if new_start < timezone.now():
        return JsonResponse({'status': 'error', 'message': 'Час не може бути в минулому'}, status=400)

    station = booking.station
    sch = station.get_day_schedule(new_start.weekday())
    if not sch or not sch.is_working:
        return JsonResponse({'status': 'error', 'message': 'СТО не працює у цей день.'}, status=400)

    v_time = new_start.time()
    if v_time < sch.opening_time or v_time > sch.closing_time:
        return JsonResponse({'status': 'error', 'message': 'Час поза робочим графіком СТО.'}, status=400)

    if sch.break_start and sch.break_end and (sch.break_start <= v_time < sch.break_end):
        return JsonResponse({'status': 'error', 'message': 'Обідня перерва на СТО.'}, status=400)

    boxes = station.boxes.filter(is_active=True)
    conflicting = Booking.objects.filter(
        station=station, status__in=['pending', 'confirmed'],
        scheduled_time__gte=new_start - datetime.timedelta(days=1), scheduled_time__lt=new_end
    ).exclude(pk=booking.pk)

    occupied = {b.box_id for b in conflicting if (b.scheduled_time + datetime.timedelta(minutes=b.duration)) > new_start}

    free_box = None
    if booking.box_id in boxes.values_list('pk', flat=True) and booking.box_id not in occupied:
        free_box = booking.box
    else:
        free_box = next((box for box in boxes if box.pk not in occupied), None)

    if not free_box:
        return JsonResponse({'status': 'error', 'message': 'Усі робочі бокси зайняті.'}, status=400)

    booking.scheduled_time = new_start
    booking.box = free_box
    booking.save(update_fields=['scheduled_time', 'box'])

    Notification.objects.create(
        recipient=booking.client, booking=booking,
        message=f"Час заявки #{booking.id} змінено на {new_start.strftime('%d.%m.%Y %H:%M')} ({free_box.name})"
    )

    return JsonResponse({
        'status': 'success',
        'message': f'Перенесено на {new_start.strftime("%d.%m.%Y %H:%M")}',
        'box_name': free_box.name
    })

@login_required_session
def booking_chat_api(request, booking_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    booking = get_object_or_404(Booking, pk=booking_id)
    is_client = (booking.client_id == user.user_id)
    is_station_owner = bool(booking.station and booking.station.user_id == user.user_id)

    if not (is_client or is_station_owner or user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'Немає доступу до чату.'}, status=403)

    if request.method == 'GET':
        messages_qs = BookingChatMessage.objects.filter(booking=booking).select_related('sender')
        messages_qs.filter(is_read=False).exclude(sender=user).update(is_read=True)

        data = [{
            'id': msg.pk,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.full_name,
            'sender_role': msg.sender.role,
            'is_me': (msg.sender_id == user.user_id),
            'text': msg.text or '',
            'image_url': msg.image.url if msg.image else None,
            'proposed_cost': str(msg.proposed_cost) if msg.proposed_cost is not None else None,
            'is_approved': msg.is_approved,
            'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M')
        } for msg in messages_qs]

        return JsonResponse({'status': 'success', 'messages': data})

    elif request.method == 'POST':
        text = request.POST.get('text', '').strip()
        image_file = optimize_image(request.FILES.get('image'))
        cost_str = request.POST.get('proposed_cost', '').strip()

        if not text and not image_file and not cost_str:
            return JsonResponse({'status': 'error', 'message': 'Повідомлення не може бути порожнім.'}, status=400)

        proposed_cost = None
        if cost_str:
            try:
                proposed_cost = Decimal(cost_str)
            except Exception:
                pass

        msg = BookingChatMessage.objects.create(
            booking=booking, sender=user, text=text or None,
            image=image_file, proposed_cost=proposed_cost
        )

        recipient = booking.client if is_station_owner else (booking.station.user if booking.station else None)
        if recipient and recipient != user:
            n_text = f"Нове повідомлення у чаті замовлення #{booking.id}"
            if image_file:
                n_text += " (фото)"
            Notification.objects.create(recipient=recipient, booking=booking, message=n_text)

        return JsonResponse({
            'status': 'success',
            'message': {
                'id': msg.pk,
                'sender_id': msg.sender_id,
                'sender_name': msg.sender.full_name,
                'sender_role': msg.sender.role,
                'is_me': True,
                'text': msg.text or '',
                'image_url': msg.image.url if msg.image else None,
                'proposed_cost': str(msg.proposed_cost) if msg.proposed_cost is not None else None,
                'is_approved': msg.is_approved,
                'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M')
            }
        })

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required_session
@require_POST
def respond_cost_approval_api(request, message_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    msg = get_object_or_404(BookingChatMessage, pk=message_id)
    booking = msg.booking

    if booking.client_id != user.user_id and not user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Тільки клієнт може підтверджувати суму.'}, status=403)

    action = request.POST.get('action')
    approved = (action == 'approve')
    msg.is_approved = approved
    msg.save(update_fields=['is_approved'])

    if booking.station and booking.station.user:
        status_txt = "підтвердив" if approved else "відхилив"
        Notification.objects.create(
            recipient=booking.station.user, booking=booking,
            message=f"Клієнт {status_txt} додаткову суму {msg.proposed_cost} грн у чаті #{booking.id}"
        )

    return JsonResponse({
        'status': 'success', 'is_approved': approved,
        'message': f'Суму {"підтверджено" if approved else "відхилено"}.'
    })

@login_required_session
def download_act_pdf_view(request, booking_id):
    user = get_current_user(request)
    if not user:
        return redirect('login')

    booking = get_object_or_404(Booking, pk=booking_id)
    is_owner = (booking.client_id == user.user_id)
    is_station_admin = bool(booking.station and booking.station.user_id == user.user_id)

    if not (is_owner or is_station_admin or user.is_staff):
        messages.error(request, 'У вас немає прав для перегляду документа.')
        return redirect('profile')

    pdf_bytes = generate_act_pdf(booking)
    filename = f"act_{booking.pk:05d}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response

def decode_vin_api(request):
    result = decode_vin(request.GET.get('vin', '').strip())
    status_code = 400 if result.get('status') == 'error' else 200
    return JsonResponse(result, status=status_code)

@login_required_session
def chat_events_sse(request, booking_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    booking = get_object_or_404(Booking, pk=booking_id)
    is_client = (booking.client_id == user.user_id)
    is_station_owner = bool(booking.station and booking.station.user_id == user.user_id)

    if not (is_client or is_station_owner or user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'Доступ заборонено.'}, status=403)

    last_id = _safe_int(request.GET.get('last_id'), 0)

    def event_stream():
        nonlocal last_id
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
        for _ in range(25):
            messages_qs = BookingChatMessage.objects.filter(
                booking=booking, pk__gt=last_id
            ).select_related('sender').order_by('created_at')

            if messages_qs.exists():
                data = []
                for msg in messages_qs:
                    last_id = max(last_id, msg.pk)
                    data.append({
                        'id': msg.pk,
                        'sender_id': msg.sender_id,
                        'sender_name': msg.sender.full_name,
                        'sender_role': msg.sender.role,
                        'is_me': (msg.sender_id == user.user_id),
                        'text': msg.text or '',
                        'image_url': msg.image.url if msg.image else None,
                        'proposed_cost': str(msg.proposed_cost) if msg.proposed_cost is not None else None,
                        'is_approved': msg.is_approved,
                        'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M')
                    })
                yield f"event: message\ndata: {json.dumps({'messages': data, 'last_id': last_id})}\n\n"
            time.sleep(1)

    resp = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'
    return resp

@login_required_session
def notification_events_sse(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    last_id = _safe_int(request.GET.get('last_id'), 0)

    def event_stream():
        nonlocal last_id
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
        for _ in range(25):
            notifs_qs = Notification.objects.filter(recipient=user, pk__gt=last_id).order_by('created_at')
            if notifs_qs.exists():
                data = []
                for n in notifs_qs:
                    last_id = max(last_id, n.pk)
                    data.append({
                        'id': n.pk,
                        'booking_id': n.booking_id,
                        'message': n.message,
                        'is_read': n.is_read,
                        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M')
                    })
                yield f"event: notification\ndata: {json.dumps({'notifications': data, 'last_id': last_id})}\n\n"
            time.sleep(1)

    resp = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'
    return resp