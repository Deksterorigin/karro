"""
Django settings for sto project (Karro).

Конфигурация читается из .env через python-decouple.
Включает hardening для production-развёртывания.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/
"""

from pathlib import Path
import os
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────
# 🔐 БЕЗПЕКА
# Значення читаються з файлу .env
# ─────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# ─────────────────────────────────────────────
# 🛡️ SECURITY HEADERS & COOKIES
# Захист сесій, cookie та HTTP-заголовків.
# Ці налаштування критичні для production.
# ─────────────────────────────────────────────

# --- Сесії ---
# Час життя сесії: 24 години (в секундах)
SESSION_COOKIE_AGE = 86400
# Сесія знищується при закритті браузера
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Cookie сесії недоступна з JavaScript (захист від XSS)
SESSION_COOKIE_HTTPONLY = True
# Cookie передається тільки через HTTPS (вмикати в production)
SESSION_COOKIE_SECURE = not DEBUG
# SameSite=Lax блокує cross-site запити з cookie
SESSION_COOKIE_SAMESITE = 'Lax'

# --- CSRF ---
# CSRF cookie також захищена від JS-доступу
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# --- HTTPS / HSTS (тільки в production) ---
if not DEBUG:
    # Перенаправляє HTTP → HTTPS
    SECURE_SSL_REDIRECT = True
    # HSTS: браузер запам'ятовує що сайт тільки HTTPS (1 рік)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Забороняє браузеру "вгадувати" MIME-тип
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Обмеження розміру завантаження (захист від DoS) ---
# Максимум 5 МБ для тіла запиту
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# Максимум 5 МБ для файлів
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Аутентифікація ---
LOGIN_URL = '/login/'


# ─────────────────────────────────────────────
# 📦 ВСТАНОВЛЕНІ ЗАСТОСУНКИ
# ─────────────────────────────────────────────
INSTALLED_APPS = [
    'station',
    'search',
    'main',
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


# ─────────────────────────────────────────────
# 🗄️ БАЗА ДАНИХ
# Параметри читаються з .env
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# 🔑 ВАЛІДАТОРИ ПАРОЛІВ
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# 🌍 ІНТЕРНАЦІОНАЛІЗАЦІЯ
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'uk'

TIME_ZONE = 'Europe/Kyiv'

USE_I18N = True

USE_TZ = True


# ─────────────────────────────────────────────
# 📁 СТАТИЧНІ ТА МЕДІА ФАЙЛИ
# ─────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# Каталог для collectstatic (production)
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ─────────────────────────────────────────────
# 📋 ЛОГУВАННЯ
# Логуємо помилки безпеки та серверні помилки
# у файл та в консоль для діагностики атак.
# ─────────────────────────────────────────────
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
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console', 'file'],
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


# ─────────────────────────────────────────────
# 🔧 ІНШЕ
# ─────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'