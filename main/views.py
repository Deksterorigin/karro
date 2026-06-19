# ╔══════════════════════════════════════════════════════════╗
# ║                   main/views.py                         ║
# ║         Усі функції-обробники (views) сайту Karro       ║
# ╚══════════════════════════════════════════════════════════╝

import logging
import os
import re
from datetime import date
from urllib.parse import urlencode

import requests
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .decorators import login_required_session
from .models import User, Car, Review, ServiceStation, Service

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 🔧 ДОПОМІЖНІ ФУНКЦІЇ
# ─────────────────────────────────────────────────────────────

# Дозволені MIME-типи та розширення для завантаження зображень.
# Обмеження запобігає завантаженню виконуваних файлів (.exe, .html, .svg)
# під виглядом картинок — потенційний вектор атаки через XSS або RCE.
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
}

# Максимальний розмір файлу (3 МБ) для запобігання DoS.
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024


def get_current_user(request):
    """
    Повертає об'єкт User за ID із сесії, або None якщо не знайдено.
    Очищає сесію якщо запис у БД вже не існує (користувач видалений).
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return None


def is_valid_vin(vin: str) -> bool:
    """
    Перевіряє що VIN-код відповідає стандарту ISO 3779:
    - рівно 17 символів
    - лише латинські літери (без I, O, Q — їх немає в VIN) та цифри
    """
    return bool(re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', vin.upper()))


def _validate_image_upload(uploaded_file):
    """
    Валідує завантажений файл зображення на безпеку.

    Перевіряє:
    - Content-Type (MIME) — тільки дозволені типи зображень
    - Розширення файлу — повинно відповідати MIME-типу
    - Розмір — не більше MAX_IMAGE_SIZE_BYTES

    Повертає:
        (True, None) — якщо файл валідний
        (False, str) — якщо є проблема, другий елемент — повідомлення помилки
    """
    if not uploaded_file:
        return False, 'Оберіть файл для завантаження.'

    # Перевірка MIME-типу (Content-Type заголовок від браузера)
    content_type = uploaded_file.content_type
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, 'Дозволені лише зображення (JPEG, PNG, WebP, GIF).'

    # Перевірка розширення файлу — повинно відповідати MIME-типу.
    # Це запобігає атаці "image.png.exe" з підробленим Content-Type.
    _, ext = os.path.splitext(uploaded_file.name.lower())
    if ext not in ALLOWED_IMAGE_TYPES[content_type]:
        return False, f'Розширення файлу "{ext}" не відповідає типу "{content_type}".'

    # Обмеження розміру для запобігання DoS
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        max_mb = MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        return False, f'Розмір файлу перевищує {max_mb:.0f} МБ.'

    return True, None


def _save_file(instance, field_name: str, uploaded_file):
    """
    Видаляє старий файл з диску та зберігає новий.
    Працює для будь-якого ImageField (аватар, фото авто і т.д.).
    """
    old_file = getattr(instance, field_name)
    if old_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass  # файл вже відсутній або шлях недоступний
    setattr(instance, field_name, uploaded_file)
    instance.save()


def _set_session_data(request, user):
    """
    Зберігає дані користувача в сесію після входу або реєстрації.
    Централізовано — щоб уникнути дублювання та розсинхрону ключів.
    """
    request.session['user_id'] = user.user_id
    request.session['user_name'] = user.full_name
    request.session['user_role'] = user.role


def _redirect_to_profile(**query_params):
    """
    Створює redirect на профіль з GET-параметрами через reverse().
    Безпечна альтернатива хардкоду URL.
    """
    url = reverse('profile')
    if query_params:
        url += '?' + urlencode(query_params)
    return redirect(url)


def geocode_address(city: str, address: str):
    """
    Визначає координати (широта, довгота) за адресою
    через безкоштовний Nominatim API (OpenStreetMap).

    Повертає:
        (latitude, longitude) — при успіху
        (None, None) — при помилці або відсутності результатів
    """
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


# ─────────────────────────────────────────────────────────────
# 🏠 ГОЛОВНА СТОРІНКА
# URL: /
# ─────────────────────────────────────────────────────────────

def home(request):
    """Головна (landing) сторінка проекту Karro."""
    return render(request, 'main/home.html')


# ─────────────────────────────────────────────────────────────
# 🔑 ВХІД (LOGIN)
# GET  → показує форму входу
# POST → перевіряє email + пароль, зберігає сесію
# URL: /login/
# ─────────────────────────────────────────────────────────────

def login_view(request):
    """
    Аутентифікація по email + пароль.
    Повідомлення про помилку однакове при невірному email і паролі —
    щоб не давати зловмиснику підказки про існування акаунту (user enumeration).
    """
    if request.session.get('user_id'):
        return redirect('profile')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                _set_session_data(request, user)
                return redirect('profile')
            else:
                messages.error(request, 'Невірний email або пароль.')
        except User.DoesNotExist:
            # Однакове повідомлення — захист від user enumeration
            messages.error(request, 'Невірний email або пароль.')

    return render(request, 'main/login.html')


# ─────────────────────────────────────────────────────────────
# 📝 РЕЄСТРАЦІЯ (REGISTER)
# GET  → показує форму реєстрації
# POST → валідує, створює користувача, логінить
# URL: /register/
# ─────────────────────────────────────────────────────────────

def register_view(request):
    """
    Реєстрація нового користувача.
    Пароль зберігається як PBKDF2+SHA256 хеш (Django make_password).
    Після створення — автоматичний вхід.
    """
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

        # ── Валідація ──
        if not full_name:
            messages.error(request, "Введіть своє ім'я.")
            return render(request, 'main/login.html', ctx)

        if role not in ('client', 'station'):
            messages.error(request, 'Невірна роль.')
            return render(request, 'main/login.html', ctx)

        if len(password) < 6:
            messages.error(request, 'Пароль має бути не менше 6 символів.')
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

        # ── Створення користувача ──
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


# ─────────────────────────────────────────────────────────────
# 👤 ПРОФІЛЬ КОРИСТУВАЧА
# Обробляє всі дії на сторінці профілю через POST action.
# Різний контент для клієнта і власника СТО.
#
# Дії (action):
#   update_profile    — зміна імені/телефону
#   change_password   — зміна пароля
#   upload_avatar     — завантаження фото профілю
#   add_car           — додати авто [client]
#   delete_car        — видалити авто [client]
#   upload_car_photo  — фото авто [client]
#   update_station    — дані СТО [station]
#   add_service       — додати послугу [station]
#   delete_service    — видалити послугу [station]
#
# URL: /profile/
# ─────────────────────────────────────────────────────────────

@login_required_session
def profile_view(request):
    """Сторінка профілю з обробкою POST-дій для всіх ролей."""
    user = get_current_user(request)
    if user is None:
        return redirect('login')

    # ── Контекст для шаблону ──
    context = {'user': user}

    if user.is_client:
        context['cars'] = Car.objects.filter(user=user)
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

    # ════ ОБРОБКА POST-ЗАПИТІВ ════
    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ── Оновлення особистих даних ──
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

        # ── Зміна пароля ──
        elif action == 'change_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            new_password2 = request.POST.get('new_password2', '')

            if not check_password(old_password, user.password):
                messages.error(request, 'Поточний пароль введено невірно.')
            elif len(new_password) < 6:
                messages.error(request, 'Новий пароль має бути не менше 6 символів.')
            elif new_password != new_password2:
                messages.error(request, 'Нові паролі не збігаються.')
            else:
                user.password = make_password(new_password)
                user.save(update_fields=['password'])
                messages.success(request, 'Пароль успішно змінено.')

        # ── Завантаження аватара ──
        elif action == 'upload_avatar':
            uploaded = request.FILES.get('avatar')
            valid, error_msg = _validate_image_upload(uploaded)
            if not valid:
                messages.error(request, error_msg)
            else:
                _save_file(user, 'avatar', uploaded)
                messages.success(request, 'Аватар оновлено.')

        # ── Додавання авто [тільки клієнт] ──
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

        # ── Видалення авто [тільки клієнт] ──
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

        # ── Завантаження фото авто [тільки клієнт] ──
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

        # ── Оновлення профілю СТО [тільки власник] ──
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

        # ── Додавання послуги [тільки власник] ──
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

        # ── Видалення послуги [тільки власник] ──
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

        else:
            messages.warning(request, 'Невідома дія.')

        # PRG-патерн: після будь-якого POST — redirect
        return redirect('profile')

    return render(request, 'main/profile.html', context)


# ─────────────────────────────────────────────────────────────
# 🚪 ВИХІД (LOGOUT)
# POST-only: захищено від CSRF-атак.
# GET-запити на /logout/ не працюють — це запобігає
# розлогінюванню через <img src="/logout/">.
# URL: /logout/
# ─────────────────────────────────────────────────────────────

@login_required_session
@require_POST
def logout_view(request):
    """Завершує сесію користувача. Тільки POST (CSRF-захист)."""
    request.session.flush()
    return redirect('home')