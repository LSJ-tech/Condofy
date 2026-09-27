"""
Django settings for config project (BarrioSeguro).
"""

import datetime
import os
from pathlib import Path

import dj_database_url
from django.contrib import messages
from django.core.management.utils import get_random_secret_key
from django.templatetags.static import static

BASE_DIR = Path(__file__).resolve().parent.parent

# Lo que cambia entre desarrollo y producción se lee de variables de entorno,
# con valores por defecto que mantienen el runserver local funcionando sin
# configurar nada -- mismo patrón que peluqueria_mascota/peluqueria/settings.py.

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or get_random_secret_key()

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]


# Application definition

INSTALLED_APPS = [
    # 'core' antes que 'unfold' para que su propio admin (si se agrega) gane
    # sobre el de Unfold. 'unfold' sigue antes que 'django.contrib.admin' --
    # lo exige el propio paquete.
    'core',
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',

    'alertas',
    'comunicacion',
    'accesos',
    'gastoscomunes',
    'notificaciones',
    'pagos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.marca',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# Sin DATABASE_URL (desarrollo), se usa SQLite. En producción, Render provee
# DATABASE_URL automáticamente al conectar un servicio de Postgres.

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# Static files -- WhiteNoise sirve los estáticos directamente desde la app en
# producción, sin necesitar un servidor web o CDN aparte.

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

PLATFORM_NAME = os.environ.get('PLATFORM_NAME', 'BarrioSeguro')

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'inicio'

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}


# Email -- sin EMAIL_HOST (desarrollo), los correos se imprimen en la consola.

if os.environ.get('EMAIL_HOST'):
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {
                'host': os.environ['EMAIL_HOST'],
                'port': int(os.environ.get('EMAIL_PORT', 587)),
                'username': os.environ.get('EMAIL_HOST_USER', ''),
                'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
                'use_tls': os.environ.get('EMAIL_USE_TLS', 'True') == 'True',
            },
        },
    }
else:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.console.EmailBackend',
        },
    }

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@barrioseguro.local')


# Pago de la suscripción vía Mercado Pago (Checkout Pro). Suscripción SaaS
# (condominio -> DevQuad) -- distinto del pago de gastos comunes, ver
# gastoscomunes/models.py y el plan del proyecto.
MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
PRECIO_PREMIUM_CLP = int(os.environ.get('PRECIO_PREMIUM_CLP', '14990'))
PRECIOS_PLAN = {"premium": PRECIO_PREMIUM_CLP}


# Django REST Framework + JWT (djangorestframework-simplejwt) -- autenticación
# de la app móvil. Access corto + refresh largo revocable (blacklist), más
# apropiado para sesiones móviles persistentes que un token simple sin expirar.

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication además del JWT: permite que el panel web
        # (logueado con sesión de Django) consuma los mismos endpoints de la
        # API para el polling de alertas, sin duplicar vistas.
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'BarrioSeguro API',
    'DESCRIPTION': 'API para la app móvil de residentes (alertas, avisos, gastos comunes, dispositivos push).',
    'VERSION': '1.0.0',
}


# Seguridad en producción (Render termina TLS en su proxy y reenvía por HTTP interno).

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# Tema del admin (django-unfold).
UNFOLD = {
    "SITE_TITLE": "BarrioSeguro · Admin",
    "SITE_HEADER": "BarrioSeguro",
    "SITE_SYMBOL": "shield",
    "SHOW_HISTORY": True,
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
}
