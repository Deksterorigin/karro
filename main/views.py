import logging
import os
import re
from collections import defaultdict
from datetime import date
from time import time
from urllib.parse import urlencode

import requests
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
# Стандартна перевірка паролів Django
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.http import JsonResponse, HttpResponse
import json
from .decorators import login_required_session
from .models import User, Car, Review, ServiceStation, Service, Booking, Notification, CarHistory, BookingChatMessage
from .pdf_utils import generate_act_pdf

logger = logging.getLogger(__name__)

# Тимчасовий лімітатор спроб входу для захисту від брутфорсу
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300  # 5 хвилин

def _check_login_rate_limit(identifier: str) -> bool:
    """Повертає True якщо IP заблоковано через перевищення кількості спроб."""
    now = time()
    _login_attempts[identifier] = [
        t for t in _login_attempts[identifier]
        if now - t < LOGIN_LOCKOUT_SECONDS
    ]
    if len(_login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        return True
    _login_attempts[identifier].append(now)
    return False

# Дозволені формати та обмеження розміру для зображень
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
}
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024

def get_current_user(request):
    """Повертає поточного авторизованого користувача або None."""
    if request.user.is_authenticated:
        return request.user
    return None

def is_valid_vin(vin: str) -> bool:
    """Перевірка відповідності VIN-коду стандарту ISO 3779."""
    return bool(re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', vin.upper()))

def _validate_image_upload(uploaded_file):
    """Валідація завантаженого файлу зображення."""
    if not uploaded_file:
        return False, 'Оберіть файл для завантаження.'

    content_type = uploaded_file.content_type
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, 'Дозволені лише зображення (JPEG, PNG, WebP, GIF).'

    _, ext = os.path.splitext(uploaded_file.name.lower())
    if ext not in ALLOWED_IMAGE_TYPES[content_type]:
        return False, f'Розширення файлу "{ext}" не відповідає типу "{content_type}".'

    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        max_mb = MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        return False, f'Розмір файлу перевищує {max_mb:.0f} МБ.'

    return True, None

def optimize_image(uploaded_file, max_size=(1920, 1080), quality=85):
    """
    Стискає та оптимізує завантажене зображення (макс 1920x1080) для економії дискового простору.
    """
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
            output,
            'ImageField',
            uploaded_file.name,
            f'image/{fmt.lower()}',
            output.getbuffer().nbytes,
            None
        )
    except Exception as e:
        logger.warning('Image optimization error: %s', e, exc_info=True)
        return uploaded_file

def _save_file(instance, field_name: str, uploaded_file):
    """Видаляє старий файл та зберігає стиснутий новий."""
    old_file = getattr(instance, field_name)
    if old_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass
    optimized = optimize_image(uploaded_file)
    setattr(instance, field_name, optimized)
    instance.save()

# Раніше тут була функція _set_session_data, тепер використовується стандартний сесійний механізм Django.

def _redirect_to_profile(**query_params):
    """Перенаправляє на профіль із передачею параметрів."""
    url = reverse('profile')
    if query_params:
        url += '?' + urlencode(query_params)
    return redirect(url)

def geocode_address(city: str, address: str):
    """
    Визначає геокоординати за адресою через Nominatim (OpenStreetMap API).
    Підтримує адреси українською та англійською мовами.
    """
    if not address and not city:
        return None, None

    clean_addr = re.sub(r'\b(вул\.|вулиця|просп\.|проспект|б-р|бульвар|пл\.|площа|пров\.|провулок|буд\.|будинок)\b', '', address, flags=re.IGNORECASE).strip()

    queries = [
        f"{address}, {city}, Україна" if city else f"{address}, Україна",
        f"{clean_addr}, {city}, Україна" if city and clean_addr else None,
        f"{city}, Україна" if city else None
    ]

    headers = {
        'User-Agent': 'Karro-STO-App/1.0',
        'Accept-Language': 'uk,en'
    }

    for query in queries:
        if not query:
            continue
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers=headers,
                timeout=4,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception as e:
            logger.warning('Geocoding query failed for "%s": %s', query, e)

    return None, None

def home(request):
    """Головна сторінка сервісу."""
    return render(request, 'main/home.html')

def login_view(request):
    """Авторизація користувача за email та паролем."""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        # Обмеження кількості спроб входу
        ip = request.META.get('REMOTE_ADDR', '')
        if _check_login_rate_limit(ip):
            messages.error(
                request,
                'Забагато спроб входу. Спробуйте через 5 хвилин.'
            )
            return render(request, 'main/login.html')

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Ваш акаунт заблоковано.')
            else:
                login(request, user)
                return redirect('profile')
        else:
            messages.error(request, 'Невірний email або пароль.')

    return render(request, 'main/login.html')

def register_view(request):
    """Реєстрація нового користувача в системі."""
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

        # Перевірка пароля вбудованими валідаторами
        try:
            validate_password(password)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
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
            email=email,
            full_name=full_name,
            phone=phone,
            role=role,
            password=password,
        )

        login(request, user)
        messages.success(request, 'Реєстрація успішна! Ласкаво просимо.')
        return redirect('profile')

    return render(request, 'main/login.html', {'show_register': True})

@login_required_session
def profile_view(request):
    """Особистий кабінет з підтримкою кастомних POST-операцій."""
    user = get_current_user(request)
    if user is None:
        return redirect('login')

    context = {'user': user}

    if user.is_client:
        from django.db.models import Prefetch
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

    if user.is_station:
        stations = ServiceStation.objects.filter(user=user)
        context['stations'] = stations

        edit_id = request.GET.get('edit_station')
        station = None
        if edit_id:
            try:
                station = stations.get(pk=edit_id)
            except (ValueError, ServiceStation.DoesNotExist):
                pass

        is_new = request.GET.get('action') == 'new_station'
        if not station and not is_new and stations.exists():
            station = stations.first()

        context['station'] = station
        context['is_new_station'] = is_new or (not station)
        if station:
            context['services'] = Service.objects.filter(station=station)
            from .models import StationBox
            context['station_boxes'] = StationBox.objects.filter(station=station)
            context['schedules'] = station.get_or_create_schedules()
            
        context['bookings'] = Booking.objects.filter(station__user=user).select_related('client', 'station', 'box')
        
        from accounting.models import Employee, SparePart
        context['station_employees'] = Employee.objects.filter(station__user=user, is_active=True)
        if station:
            context['station_spare_parts'] = SparePart.objects.filter(station=station)
        else:
            context['station_spare_parts'] = SparePart.objects.filter(station__user=user)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # Зміна персональних даних
        if action == 'update_profile':
            full_name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            if not full_name:
                messages.error(request, "Ім'я не може бути порожнім.")
            else:
                if User.objects.filter(phone=phone).exclude(user_id=user.user_id).exists():
                    messages.error(request, 'Цей номер телефону вже використовується.')
                else:
                    user.full_name = full_name
                    user.phone = phone
                    user.save(update_fields=['full_name', 'phone'])
                    messages.success(request, 'Дані успішно оновлено.')

        # Оновлення пароля
        elif action == 'change_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            new_password2 = request.POST.get('new_password2', '')

            if not user.check_password(old_password):
                messages.error(request, 'Поточний пароль введено невірно.')
            elif new_password != new_password2:
                messages.error(request, 'Нові паролі не збігаються.')
            else:
                # Валідація нового пароля
                try:
                    validate_password(new_password)
                except ValidationError as e:
                    for error in e.messages:
                        messages.error(request, error)
                    return redirect('profile')

                user.set_password(new_password)
                user.save(update_fields=['password'])
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успішно змінено.')

        # Оновлення графіку роботи СТО
        elif action == 'save_schedule':
            if not user.is_station or not station:
                messages.error(request, 'Спочатку оберіть або створіть СТО.')
            else:
                for day in range(7):
                    sch = station.get_day_schedule(day)
                    sch.is_working = request.POST.get(f'is_working_{day}') == 'on'
                    sch.opening_time = request.POST.get(f'opening_time_{day}', '09:00') or '09:00'
                    sch.closing_time = request.POST.get(f'closing_time_{day}', '18:00') or '18:00'
                    
                    b_start = request.POST.get(f'break_start_{day}', '').strip()
                    b_end = request.POST.get(f'break_end_{day}', '').strip()
                    sch.break_start = b_start if b_start else None
                    sch.break_end = b_end if b_end else None
                    sch.save()

                messages.success(request, 'Графік роботи СТО успішно збережено.')
                return redirect('profile')

        # Оновлення фото профілю
        elif action == 'upload_avatar':
            uploaded = request.FILES.get('avatar')
            valid, error_msg = _validate_image_upload(uploaded)
            if not valid:
                messages.error(request, error_msg)
            else:
                _save_file(user, 'avatar', uploaded)
                messages.success(request, 'Аватар оновлено.')

        # Додавання автомобіля (клієнт)
        elif action == 'add_car':
            if not user.is_client:
                messages.error(request, 'Ця дія доступна тільки клієнтам.')
            else:
                vin = request.POST.get('vin_code', '').strip().upper()
                brand = request.POST.get('brand', '').strip()
                model = request.POST.get('model', '').strip()
                year = request.POST.get('year', '').strip()

                if not is_valid_vin(vin):
                    messages.error(request, 'Невірний VIN-код. Має бути 17 символів (A-Z без I,O,Q та 0-9).')
                elif not brand or not model:
                    messages.error(request, 'Введіть марку та модель автомобіля.')
                elif not year.isdigit() or not (1900 <= int(year) <= date.today().year + 1):
                    messages.error(request, f'Рік має бути між 1900 і {date.today().year + 1}.')
                elif Car.objects.filter(vin_code=vin).exists():
                    messages.error(request, 'Автомобіль з таким VIN вже зареєстровано в системі.')
                else:
                    Car.objects.create(
                        vin_code=vin,
                        brand=brand,
                        model=model,
                        year=int(year),
                        user=user,
                    )
                    messages.success(request, f'Автомобіль {brand} {model} додано.')

        # Видалення автомобіля (клієнт)
        elif action == 'delete_car':
            if not user.is_client:
                messages.error(request, 'Ця дія доступна тільки клієнтам.')
            else:
                vin = request.POST.get('vin_code', '').strip().upper()
                deleted, _ = Car.objects.filter(vin_code=vin, user=user).delete()
                if deleted:
                    messages.success(request, 'Автомобіль видалено.')
                else:
                    messages.error(request, 'Автомобіль не знайдено.')

        # Завантаження фото автомобіля (клієнт)
        elif action == 'upload_car_photo':
            if not user.is_client:
                messages.error(request, 'Ця дія доступна тільки клієнтам.')
            else:
                vin = request.POST.get('vin_code', '').strip().upper()
                uploaded = request.FILES.get('car_photo')
                car = Car.objects.filter(vin_code=vin, user=user).first()

                if not car:
                    messages.error(request, 'Автомобіль не знайдено.')
                else:
                    valid, error_msg = _validate_image_upload(uploaded)
                    if not valid:
                        messages.error(request, error_msg)
                    else:
                        _save_file(car, 'photo', uploaded)
                        messages.success(request, 'Фото автомобіля оновлено.')

        # Оновлення чи створення профілю СТО (власник)
        elif action == 'update_station':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                station_id_str = request.POST.get('station_id', '').strip()
                name = request.POST.get('station_name', '').strip()
                city = request.POST.get('station_city', '').strip()
                address = request.POST.get('station_address', '').strip()
                phone = request.POST.get('station_phone', '').strip()
                if not name or not address:
                    messages.error(request, 'Назва та адреса СТО обов\'язкові.')
                else:
                    lat_str = request.POST.get('latitude', '').strip()
                    lng_str = request.POST.get('longitude', '').strip()

                    latitude, longitude = None, None
                    if lat_str and lng_str:
                        try:
                            latitude = float(lat_str)
                            longitude = float(lng_str)
                        except ValueError:
                            pass

                    if latitude is None or longitude is None:
                        latitude, longitude = geocode_address(city, address)

                    station = None
                    if station_id_str:
                        try:
                            station = ServiceStation.objects.filter(
                                user=user, pk=int(station_id_str)
                            ).first()
                        except ValueError:
                            pass

                    if station:
                        station.name = name
                        station.city = city
                        station.address = address
                        station.phone = phone
                        station.latitude = latitude
                        station.longitude = longitude
                        station.save()
                        messages.success(request, 'Дані СТО оновлено.')
                        return _redirect_to_profile(
                            edit_station=station.pk, tab='station'
                        )
                    else:
                        new_station = ServiceStation.objects.create(
                            user=user,
                            name=name,
                            city=city,
                            address=address,
                            phone=phone,
                            latitude=latitude,
                            longitude=longitude,
                        )
                        messages.success(request, 'Нову СТО успішно створено.')
                        return _redirect_to_profile(
                            edit_station=new_station.pk, tab='station'
                        )

        # Додавання нової послуги (власник)
        elif action == 'add_service':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                station_id_str = request.POST.get('station_id', '').strip()
                station = None
                if station_id_str:
                    try:
                        station = ServiceStation.objects.filter(
                            user=user, pk=int(station_id_str)
                        ).first()
                    except ValueError:
                        pass
                if not station:
                    station = ServiceStation.objects.filter(user=user).first()

                if not station:
                    messages.error(request, 'Спочатку заповніть профіль СТО.')
                else:
                    service_name = request.POST.get('service_name', '').strip()
                    price_str = request.POST.get('price', '').strip()
                    description = request.POST.get('description', '').strip()

                    if not service_name:
                        messages.error(request, 'Введіть назву послуги.')
                    else:
                        try:
                            price = float(price_str)
                            if price <= 0:
                                raise ValueError
                        except ValueError:
                            messages.error(request, 'Ціна має бути числом більше 0.')
                        else:
                            Service.objects.create(
                                service_name=service_name,
                                price=price,
                                description=description,
                                station=station,
                            )
                            messages.success(request, f'Послугу "{service_name}" додано.')
                            return _redirect_to_profile(
                                edit_station=station.pk, tab='station'
                            )

        # Видалення послуги (власник)
        elif action == 'delete_service':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                service_id = request.POST.get('service_id', '')
                service = Service.objects.filter(
                    service_id=service_id, station__user=user
                ).first()
                if service:
                    station_pk = service.station.pk
                    service.delete()
                    messages.success(request, 'Послугу видалено.')
                    return _redirect_to_profile(
                        edit_station=station_pk, tab='station'
                    )
                else:
                    messages.error(request, 'Послугу не знайдено.')

        # Додавання боксу
        elif action == 'add_box':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                station_id = request.POST.get('station_id')
                box_name = request.POST.get('box_name', '').strip()
                station = get_object_or_404(ServiceStation, pk=station_id, user=user)
                if box_name:
                    from .models import StationBox
                    StationBox.objects.create(station=station, name=box_name, is_active=True)
                    messages.success(request, 'Робочий бокс успішно додано.')
                return _redirect_to_profile(edit_station=station.pk, tab='station')

        # Перемикання активності боксу
        elif action == 'toggle_box':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                box_id = request.POST.get('box_id')
                from .models import StationBox
                box = get_object_or_404(StationBox, pk=box_id, station__user=user)
                box.is_active = not box.is_active
                box.save()
                messages.success(request, f'Статус боксу "{box.name}" оновлено.')
                return _redirect_to_profile(edit_station=box.station.pk, tab='station')

        # Видалення боксу
        elif action == 'delete_box':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                box_id = request.POST.get('box_id')
                from .models import StationBox
                box = get_object_or_404(StationBox, pk=box_id, station__user=user)
                station_pk = box.station.pk
                box.delete()
                messages.success(request, 'Робочий бокс видалено.')
                return _redirect_to_profile(edit_station=station_pk, tab='station')

        # Оновлення статусу заявки (власник)
        elif action == 'update_booking_status':
            if not user.is_station:
                messages.error(request, 'Ця дія доступна тільки власникам СТО.')
            else:
                booking_id = request.POST.get('booking_id')
                new_status = request.POST.get('status')
                
                try:
                    booking = Booking.objects.get(id=booking_id, station__user=user)
                    if new_status in dict(Booking.STATUS_CHOICES):
                        booking.status = new_status
                        booking.save(update_fields=['status'])
                        messages.success(request, f'Статус заявки #{booking.id} оновлено.')
                    else:
                        messages.error(request, 'Невірний статус.')
                except Booking.DoesNotExist:
                    messages.error(request, 'Заявку не знайдено.')
                
                return _redirect_to_profile(tab='bookings')

        else:
            messages.warning(request, 'Невідома дія.')

        return redirect('profile')

    return render(request, 'main/profile.html', context)

@login_required_session
@require_POST
def logout_view(request):
    """Вихід з облікового запису."""
    logout(request)
    return redirect('home')

@require_POST
def create_booking_api(request):
    """Створення заявки на ремонт (AJAX)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        station_id = data.get('station_id')
        car_id = data.get('car_id')
        service_name = data.get('service_name', '').strip()
        description = data.get('description', '').strip()
        scheduled_time = data.get('scheduled_time')

        if not station_id or not description or not service_name:
            return JsonResponse({'status': 'error', 'message': 'Будь ласка, заповніть усі обов\'язкові поля'}, status=400)

        if not scheduled_time:
            return JsonResponse({'status': 'error', 'message': 'Бажаний час візиту обов\'язковий'}, status=400)

        client = request.user

        # Тільки клієнти мають право оформлювати заявки
        if client.role != 'client':
            return JsonResponse(
                {'status': 'error', 'message': 'Тільки клієнти можуть створювати заявки'},
                status=403
            )

        # Перевірка чи акаунт активний
        if not client.is_active:
            return JsonResponse(
                {'status': 'error', 'message': 'Ваш акаунт заблоковано'},
                status=403
            )

        station = ServiceStation.objects.get(pk=station_id)

        # Перевірка чи автомобіль належить поточному клієнту
        if not car_id:
            return JsonResponse({'status': 'error', 'message': 'Будь ласка, оберіть автомобіль'}, status=400)
        try:
            car = Car.objects.get(vin_code=car_id, user=client)
        except Car.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Обраний автомобіль не знайдено або він не належить вам'}, status=400)

        # Валідація формату дати/часу та годин роботи СТО
        try:
            import datetime
            scheduled_dt = datetime.datetime.fromisoformat(scheduled_time)
            if django_settings.USE_TZ and timezone.is_naive(scheduled_dt):
                scheduled_dt = timezone.make_aware(scheduled_dt)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Невірний формат часу'}, status=400)

        if scheduled_dt < timezone.now():
            return JsonResponse({'status': 'error', 'message': 'Неможливо записатися на минулий час'}, status=400)

        visit_day = scheduled_dt.weekday()
        sch = station.get_day_schedule(visit_day)
        if not sch or not sch.is_working:
            return JsonResponse({
                'status': 'error',
                'message': 'СТО не працює в обраний день тижня (Вихідний).'
            }, status=400)

        visit_time = scheduled_dt.time()
        if visit_time < sch.opening_time or visit_time > sch.closing_time:
            opening_str = sch.opening_time.strftime('%H:%M')
            closing_str = sch.closing_time.strftime('%H:%M')
            return JsonResponse({
                'status': 'error',
                'message': f'СТО у цей день працює з {opening_str} до {closing_str}. Будь ласка, оберіть інший час.'
            }, status=400)

        if sch.break_start and sch.break_end:
            if sch.break_start <= visit_time < sch.break_end:
                return JsonResponse({
                    'status': 'error',
                    'message': f'У СТО обідня перерва з {sch.break_start.strftime("%H:%M")} до {sch.break_end.strftime("%H:%M")}.'
                }, status=400)

        # Автоматичне знаходження вільного боксу
        from .models import StationBox
        boxes = station.boxes.filter(is_active=True)
        if not boxes.exists():
            StationBox.objects.create(station=station, name="Бокс 1", is_active=True)
            boxes = station.boxes.filter(is_active=True)

        duration = int(data.get('duration', 60))
        slot_start = scheduled_dt
        slot_end = slot_start + datetime.timedelta(minutes=duration)

        # Отримуємо конфліктуючі замовлення (ті, які перекриваються за часом)
        conflicting_bookings = Booking.objects.filter(
            station=station,
            status__in=['pending', 'confirmed', 'completed'],
            scheduled_time__gte=slot_start - datetime.timedelta(days=1),
            scheduled_time__lt=slot_end
        )
        occupied_box_ids = set()
        for b in conflicting_bookings:
            b_end = b.scheduled_time + datetime.timedelta(minutes=b.duration)
            if b_end > slot_start:
                occupied_box_ids.add(b.box_id)

        free_box = None
        for box in boxes:
            if box.pk not in occupied_box_ids:
                free_box = box
                break

        if not free_box:
            return JsonResponse({
                'status': 'error',
                'message': 'Нажаль, на цей час усі бокси вже зайняті. Будь ласка, оберіть інший час.'
            }, status=400)

        booking = Booking.objects.create(
            client=client,
            station=station,
            car=car,
            service_name=service_name,
            description=description,
            scheduled_time=scheduled_dt,
            box=free_box,
            duration=duration
        )
        
        # Створення сповіщення для власника СТО
        Notification.objects.create(
            recipient=station.user,
            booking=booking,
            message=f"Нова заявка #{booking.id}: {client.full_name} на {scheduled_dt.strftime('%d.%m.%Y %H:%M')}"
        )
        return JsonResponse({"status": "success", "message": "Заявку успішно створено"})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Клієнта не знайдено'}, status=404)
    except ServiceStation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'СТО не знайдено'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Невірний формат даних'}, status=400)
    except Exception as e:
        logger.error(f'Booking API Error: {e}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Внутрішня помилка сервера'}, status=500)

@login_required_session
def client_profile_view(request, client_id):
    """Перегляд профілю клієнта власником СТО."""
    user = get_current_user(request)
    if not user.is_station:
        messages.error(request, 'Доступ заборонено.')
        return redirect('profile')
        
    try:
        client = User.objects.get(user_id=client_id, role='client')
    except User.DoesNotExist:
        messages.error(request, 'Клієнта не знайдено.')
        return redirect('profile')
        
    if not Booking.objects.filter(client=client, station__user=user).exists():
        messages.error(request, 'Доступ заборонено: у цього клієнта немає заявок на вашій СТО.')
        return redirect('profile')
        
    cars = Car.objects.filter(user=client)
    
    context = {
        'client': client,
        'cars': cars,
    }
    return render(request, 'main/client_detail.html', context)


@login_required_session
def get_notifications_api(request):
    """Отримання списку останніх сповіщень та кількості непрочитаних для поточного користувача."""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Користувач не авторизований'}, status=401)
        
    notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            'booking_id': n.booking.id if n.booking else None
        })
        
    return JsonResponse({
        'status': 'success',
        'unread_count': unread_count,
        'notifications': data
    })


@require_POST
@login_required_session
def mark_notification_read_api(request, notification_id):
    """Позначення сповіщення як прочитаного."""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Користувач не авторизований'}, status=401)
        
    notification = get_object_or_404(Notification, id=notification_id, recipient=user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    
    return JsonResponse({'status': 'success'})


@require_POST
@login_required_session
def mark_all_notifications_read_api(request):
    """Позначення всіх сповіщень користувача як прочитаних."""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Користувач не авторизований'}, status=401)
        
    Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


def get_available_slots_api(request, station_id):
    """Повертає список доступних часових слотів для СТО на вказану дату."""
    import datetime
    station = get_object_or_404(ServiceStation, pk=station_id)
    date_str = request.GET.get('date')
    duration = int(request.GET.get('duration', 60))

    if not date_str:
        return JsonResponse({'status': 'error', 'message': 'Параметр date обов\'язковий'}, status=400)

    try:
        dt_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Невірний формат дати'}, status=400)

    # Отримуємо активні бокси
    from .models import StationBox
    boxes = station.boxes.filter(is_active=True)
    if not boxes.exists():
        StationBox.objects.create(station=station, name="Бокс 1", is_active=True)
        boxes = station.boxes.filter(is_active=True)

    # Визначаємо початок та кінець дня
    start_dt = timezone.make_aware(datetime.datetime.combine(dt_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(dt_date, datetime.time.max))

    bookings = Booking.objects.filter(
        station=station,
        scheduled_time__range=(start_dt, end_dt),
        status__in=['pending', 'confirmed', 'completed']
    ).select_related('box')

    # Генерація слотів з урахуванням розкладу на даний день тижня
    day_num = dt_date.weekday()
    sch = station.get_day_schedule(day_num)

    if not sch or not sch.is_working:
        return JsonResponse({
            'status': 'success',
            'slots': [],
            'is_closed': True,
            'message': 'СТО не працює у цей день (Вихідний).'
        })

    opening_time = sch.opening_time
    closing_time = sch.closing_time

    current_slot = timezone.make_aware(datetime.datetime.combine(dt_date, opening_time))
    work_end = timezone.make_aware(datetime.datetime.combine(dt_date, closing_time))

    now = timezone.now()
    available_slots = []

    while current_slot <= work_end - datetime.timedelta(minutes=duration):
        if current_slot <= now:
            current_slot += datetime.timedelta(minutes=30)
            continue

        slot_start_time = current_slot.time()
        slot_end_dt = current_slot + datetime.timedelta(minutes=duration)
        slot_end_time = slot_end_dt.time()

        # Враховуємо обідню перерву СТО
        if sch.break_start and sch.break_end:
            if not (slot_end_time <= sch.break_start or slot_start_time >= sch.break_end):
                current_slot += datetime.timedelta(minutes=30)
                continue

        slot_end = slot_end_dt
        free_box_found = False
        for box in boxes:
            conflict = False
            for b in bookings:
                if b.box_id == box.pk:
                    b_start = b.scheduled_time
                    b_end = b_start + datetime.timedelta(minutes=b.duration)
                    if b_start < slot_end and b_end > current_slot:
                        conflict = True
                        break
            if not conflict:
                free_box_found = True
                break

        if free_box_found:
            available_slots.append(current_slot.strftime('%H:%M'))

        current_slot += datetime.timedelta(minutes=30)

    return JsonResponse({
        'status': 'success',
        'slots': available_slots,
        'is_closed': False
    })


@login_required_session
def get_calendar_events_api(request, station_id):
    """Повертає список замовлень для відображення в FullCalendar."""
    import datetime
    station = get_object_or_404(ServiceStation, pk=station_id)
    
    # Тільки власник СТО або його персонал мають доступ до календаря
    if station.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not start_str or not end_str:
        return JsonResponse({'status': 'error', 'message': 'Параметри start та end обов\'язкові'}, status=400)

    try:
        # FullCalendar передає дати у форматі ISO 8601
        start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Невірні часові межі'}, status=400)

    bookings = Booking.objects.filter(
        station=station,
        scheduled_time__range=(start_dt, end_dt)
    ).select_related('client', 'car', 'box')

    events = []
    for b in bookings:
        if not b.scheduled_time:
            continue
        
        b_end = b.scheduled_time + datetime.timedelta(minutes=b.duration)
        
        color = '#3B82F6'  # pending
        if b.status == 'confirmed':
            color = '#F59E0B'
        elif b.status == 'completed':
            color = '#10B981'
        elif b.status == 'cancelled':
            color = '#EF4444'

        events.append({
            'id': b.id,
            'title': f'{b.client.full_name} ({b.car.brand} {b.car.model if b.car else ""}) - {b.service_name or "Діагностика"}',
            'start': b.scheduled_time.isoformat(),
            'end': b_end.isoformat(),
            'color': color,
            'extendedProps': {
                'clientName': b.client.full_name,
                'car': f'{b.car.brand} {b.car.model}' if b.car else 'Не вказано',
                'description': b.description,
                'status': b.get_status_display(),
                'boxName': b.box.name if b.box else 'Не визначено',
            }
        })

    return JsonResponse(events, safe=False)


@require_POST
@login_required_session
def reschedule_booking_api(request, booking_id):
    """Ендпоінт для drag-and-drop зміни часу замовлення в календарі."""
    import datetime
    import json
    booking = get_object_or_404(Booking, pk=booking_id, station__user=request.user)

    try:
        data = json.loads(request.body)
        new_start_str = data.get('scheduled_time')
        if not new_start_str:
            return JsonResponse({'status': 'error', 'message': 'Час не вказано'}, status=400)

        new_start = datetime.datetime.fromisoformat(new_start_str.replace('Z', '+00:00'))
        if timezone.is_naive(new_start):
            new_start = timezone.make_aware(new_start)

        new_end = new_start + datetime.timedelta(minutes=booking.duration)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Невірний формат дати/даних'}, status=400)

    # Перевірка чи новий час не в минулому
    if new_start < timezone.now():
        return JsonResponse({'status': 'error', 'message': 'Неможливо перенести замовлення на минулий час'}, status=400)

    # Робочі години СТО
    visit_time = new_start.time()
    station = booking.station
    if visit_time < station.opening_time or visit_time > station.closing_time:
        opening_str = station.opening_time.strftime('%H:%M')
        closing_str = station.closing_time.strftime('%H:%M')
        return JsonResponse({
            'status': 'error',
            'message': f'СТО працює з {opening_str} до {closing_str}. Оберіть робочий час.'
        }, status=400)

    # Перевірка вільних боксів (виключаючи поточне замовлення)
    from .models import StationBox
    boxes = station.boxes.filter(is_active=True)
    if not boxes.exists():
        StationBox.objects.create(station=station, name="Бокс 1", is_active=True)
        boxes = station.boxes.filter(is_active=True)

    conflicting_bookings = Booking.objects.filter(
        station=station,
        status__in=['pending', 'confirmed', 'completed'],
        scheduled_time__gte=new_start - datetime.timedelta(days=1),
        scheduled_time__lt=new_end
    ).exclude(pk=booking.pk)

    occupied_box_ids = set()
    for b in conflicting_bookings:
        b_end = b.scheduled_time + datetime.timedelta(minutes=b.duration)
        if b_end > new_start:
            occupied_box_ids.add(b.box_id)

    # Намагаємося залишити той самий бокс, якщо він вільний, інакше шукаємо перший вільний
    free_box = None
    if booking.box_id in boxes.values_list('pk', flat=True) and booking.box_id not in occupied_box_ids:
        free_box = booking.box
    else:
        for box in boxes:
            if box.pk not in occupied_box_ids:
                free_box = box
                break

    if not free_box:
        return JsonResponse({'status': 'error', 'message': 'Усі робочі бокси зайняті в цей проміжок часу.'}, status=400)

    booking.scheduled_time = new_start
    booking.box = free_box
    booking.save(update_fields=['scheduled_time', 'box'])

    # Створюємо сповіщення клієнту про перенесення
    from .models import Notification
    Notification.objects.create(
        recipient=booking.client,
        booking=booking,
        message=f"Час вашої заявки #{booking.id} змінено на {new_start.strftime('%d.%m.%Y %H:%M')} (бокс: {free_box.name})"
    )

    return JsonResponse({
        'status': 'success',
        'message': f'Замовлення успішно перенесено на {new_start.strftime("%d.%m.%Y %H:%M")}',
        'box_name': free_box.name
    })


@login_required_session
def booking_chat_api(request, booking_id):
    """
    API для отримання та надсилання повідомлень чату замовлення.
    GET: Повертає список повідомлень чату.
    POST: Надсилає новий текст, фото або пропозицію додаткових робіт/ціни.
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    booking = get_object_or_404(Booking, pk=booking_id)

    # Перевірка прав доступу: тільки клієнт замовлення або власник СТО
    is_client = (booking.client_id == user.user_id)
    is_station_owner = (booking.station and booking.station.user_id == user.user_id)

    if not (is_client or is_station_owner or user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'У вас немає доступу до чату цього замовлення.'}, status=403)

    if request.method == 'GET':
        messages_qs = BookingChatMessage.objects.filter(booking=booking).select_related('sender')
        
        # Відмічаємо чужі повідомлення як прочитані
        unread = messages_qs.filter(is_read=False).exclude(sender=user)
        unread.update(is_read=True)

        data = []
        for msg in messages_qs:
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

        return JsonResponse({'status': 'success', 'messages': data})

    elif request.method == 'POST':
        text = request.POST.get('text', '').strip()
        image_file = request.FILES.get('image')
        if image_file:
            image_file = optimize_image(image_file)
        proposed_cost_str = request.POST.get('proposed_cost', '').strip()

        if not text and not image_file and not proposed_cost_str:
            return JsonResponse({'status': 'error', 'message': 'Повідомлення не може бути порожнім.'}, status=400)

        proposed_cost = None
        if proposed_cost_str:
            try:
                from decimal import Decimal
                proposed_cost = Decimal(proposed_cost_str)
            except Exception:
                pass

        msg = BookingChatMessage.objects.create(
            booking=booking,
            sender=user,
            text=text if text else None,
            image=image_file,
            proposed_cost=proposed_cost
        )

        # Створюємо сповіщення для протилежної сторони
        recipient = booking.client if is_station_owner else (booking.station.user if booking.station else None)
        if recipient and recipient != user:
            notif_text = f"Нове повідомлення у чаті замовлення #{booking.id}"
            if image_file:
                notif_text += " (надіслано фото)"
            Notification.objects.create(
                recipient=recipient,
                booking=booking,
                message=notif_text
            )

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
    """
    API для підтвердження або відхилення додаткової суми клієнтом.
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    msg = get_object_or_404(BookingChatMessage, pk=message_id)
    booking = msg.booking

    # Перевірка що відповідає саме клієнт
    if booking.client_id != user.user_id and not user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Тільки клієнт може підтверджувати суму.'}, status=403)

    action = request.POST.get('action') # 'approve' or 'decline'
    if action == 'approve':
        msg.is_approved = True
        msg.save(update_fields=['is_approved'])
        
        if booking.station and booking.station.user:
            Notification.objects.create(
                recipient=booking.station.user,
                booking=booking,
                message=f"Клієнт підтвердив додаткову суму {msg.proposed_cost} грн у чаті замовлення #{booking.id}"
            )
        return JsonResponse({'status': 'success', 'is_approved': True, 'message': 'Суму підтверджено.'})
    elif action == 'decline':
        msg.is_approved = False
        msg.save(update_fields=['is_approved'])
        
        if booking.station and booking.station.user:
            Notification.objects.create(
                recipient=booking.station.user,
                booking=booking,
                message=f"Клієнт відхилив додаткову суму {msg.proposed_cost} грн у чаті замовлення #{booking.id}"
            )
        return JsonResponse({'status': 'success', 'is_approved': False, 'message': 'Суму відхилено.'})

    return JsonResponse({'status': 'error', 'message': 'Невідома дія.'}, status=400)


@login_required_session
def download_act_pdf_view(request, booking_id):
    """
    Генерує та повертає Акт виконаних робіт (PDF) для конкретного замовлення.
    Доступ дозволено клієнту-власнику замовлення або адміністратору СТО.
    """
    user = get_current_user(request)
    if not user:
        return redirect('login')

    booking = get_object_or_404(Booking, pk=booking_id)

    # Перевірка прав доступу: замовник, власник СТО або персонал
    is_owner = (booking.client_id == user.user_id)
    is_station_admin = (booking.station and booking.station.user_id == user.user_id)

    if not (is_owner or is_station_admin or user.is_staff):
        messages.error(request, 'У вас немає прав для перегляду даного документа.')
        return redirect('profile')

    # Створення байтового масиву PDF
    pdf_bytes = generate_act_pdf(booking)

    filename = f"act_{booking.pk:05d}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')

    # Перевірка режиму перегляду (в браузері чи скачування)
    if request.GET.get('inline') == '1':
        response['Content-Disposition'] = f'inline; filename="{filename}"'
    else:
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response