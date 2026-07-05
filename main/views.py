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
from django.contrib.auth.hashers import make_password, check_password
# FIX (ARCH-09): Підключаємо стандартні Django-валідатори паролів
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.http import JsonResponse
import json
from .decorators import login_required_session
from .models import User, Car, Review, ServiceStation, Service, Booking, Notification

logger = logging.getLogger(__name__)

# FIX (SEC-01): Простий in-memory rate limiter для захисту від brute-force
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
    """Повертає об'єкт користувача з сесії або None."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        request.session.flush()
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

def _save_file(instance, field_name: str, uploaded_file):
    """Видаляє старий файл та зберігає новий."""
    old_file = getattr(instance, field_name)
    if old_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass
    setattr(instance, field_name, uploaded_file)
    instance.save()

def _set_session_data(request, user):
    """Записує ідентифікаційні дані користувача в сесію."""
    # FIX (SEC-02): Ротація session ID для захисту від session fixation
    request.session.cycle_key()
    request.session['user_id'] = user.user_id
    request.session['user_name'] = user.full_name
    request.session['user_role'] = user.role

def _redirect_to_profile(**query_params):
    """Перенаправляє на профіль із передачею параметрів."""
    url = reverse('profile')
    if query_params:
        url += '?' + urlencode(query_params)
    return redirect(url)

def geocode_address(city: str, address: str):
    """Визначає геокоординати за адресою через Nominatim API."""
    query = f"{address}, {city}, Україна"
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': query, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'Karro/1.0'},
            timeout=5,
        )
        data = resp.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        logger.warning('Geocoding failed for address: %s', query, exc_info=True)
    return None, None

def home(request):
    """Головна сторінка сервісу."""
    return render(request, 'main/home.html')

def login_view(request):
    """Авторизація користувача за email та паролем."""
    if request.session.get('user_id'):
        return redirect('profile')

    if request.method == 'POST':
        # FIX (SEC-01): Захист від brute-force
        ip = request.META.get('REMOTE_ADDR', '')
        if _check_login_rate_limit(ip):
            messages.error(
                request,
                'Забагато спроб входу. Спробуйте через 5 хвилин.'
            )
            return render(request, 'main/login.html')

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            user = User.objects.get(email=email)
            # FIX (SEC-05): Перевірка is_active перед логіном
            if not user.is_active:
                messages.error(request, 'Ваш акаунт заблоковано.')
            elif check_password(password, user.password):
                _set_session_data(request, user)
                return redirect('profile')
            else:
                messages.error(request, 'Невірний email або пароль.')
        except User.DoesNotExist:
            messages.error(request, 'Невірний email або пароль.')

    return render(request, 'main/login.html')

def register_view(request):
    """Реєстрація нового користувача в системі."""
    if request.session.get('user_id'):
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

        # FIX (ARCH-09): Використовуємо Django password validators
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

        user = User.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,
            password=make_password(password),
            role=role,
        )

        _set_session_data(request, user)
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
        client_cars = Car.objects.filter(user=user).prefetch_related(bookings_prefetch)
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
            
        context['bookings'] = Booking.objects.filter(station__user=user).select_related('client', 'station')
        
        from accounting.models import Employee
        context['station_employees'] = Employee.objects.filter(station__user=user, is_active=True)

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
                    request.session['user_name'] = user.full_name
                    messages.success(request, 'Дані успішно оновлено.')

        # Оновлення пароля
        elif action == 'change_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            new_password2 = request.POST.get('new_password2', '')

            if not check_password(old_password, user.password):
                messages.error(request, 'Поточний пароль введено невірно.')
            elif new_password != new_password2:
                messages.error(request, 'Нові паролі не збігаються.')
            else:
                # FIX (ARCH-09): Використовуємо Django password validators
                try:
                    validate_password(new_password)
                except ValidationError as e:
                    for error in e.messages:
                        messages.error(request, error)
                    return redirect('profile')

                user.password = make_password(new_password)
                user.save(update_fields=['password'])
                messages.success(request, 'Пароль успішно змінено.')

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
                elif re.search(r'[А-Яа-яЁёІіЇїЄєҐґ]', address):
                    messages.error(request, 'Адреса повинна бути тільки англійською мовою.')
                else:
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
    """Вихід з облікового запису та очищення сесії."""
    request.session.flush()
    return redirect('home')

@require_POST
def create_booking_api(request):
    """Створення заявки на ремонт (AJAX)."""
    user_id = request.session.get('user_id')
    if not user_id:
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

        client = User.objects.get(user_id=user_id)

        # FIX (CRIT-05): Перевірка ролі — тільки клієнти можуть створювати заявки
        if client.role != 'client':
            return JsonResponse(
                {'status': 'error', 'message': 'Тільки клієнти можуть створювати заявки'},
                status=403
            )

        # FIX (SEC-05): Перевірка is_active
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

        visit_time = scheduled_dt.time()
        if visit_time < station.opening_time or visit_time > station.closing_time:
            opening_str = station.opening_time.strftime('%H:%M')
            closing_str = station.closing_time.strftime('%H:%M')
            return JsonResponse({
                'status': 'error',
                'message': f'СТО працює з {opening_str} до {closing_str}. Будь ласка, оберіть інший час.'
            }, status=400)

        booking = Booking.objects.create(
            client=client,
            station=station,
            car=car,
            service_name=service_name,
            description=description,
            scheduled_time=scheduled_dt
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