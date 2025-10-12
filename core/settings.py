import os
import sys
import platform
from decouple import config
from unipath import Path
from datetime import timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).parent
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Agrega esta línea:
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="S#perS3crEt_1122")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

# 365 días de retención (ajustable)
BITACORA_RETENCION_DIAS = 365

TIME_ZONE = 'America/Caracas'  # Ajusta a tu zona
USE_TZ = True

# load production server from .env
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.0.103", "192.168.250.3", "192.168.250.2", "192.168.250.1", "192.168.250.5", "10.52.13.73", '192.168.0.1', '192.168.0.106', '192.168.0.107', '192.168.0.105', '0.0.0.0', config("SERVER", default="127.0.0.1")]

# SECURE_SSL_REDIRECT = True  # Redirige HTTP → HTTPS
# SESSION_COOKIE_SECURE = True  # Cookies solo por HTTPS

SESSION_COOKIE_HTTPONLY = True  # Protege cookies de JavaScript
CSRF_COOKIE_SECURE = False  # Si no estás usando HTTPS

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"  # Combina caché + DB

# Application definition

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 'debug_toolbar', # para ver los tiempos de respuesta de las pantallas
    "apps.api",  # La app donde estan las rutas y vistas
    "rest_framework",  # Django Rest Framework
    "rest_framework_simplejwt", #JWT para autenticacion
    "corsheaders",  # Para permitir conexiones desde el frontend
    "apps.authentication",
    "apps.home",  # Enable the inner home (home)
    'django_extensions',
    "apps.bitacora.apps.BitacoraConfig",  # Habilita la aplicación para gestionar bitacora
    "apps.persona",  # Habilita la aplicación para gestionar personas
    "apps.honorario",  # Habilita la aplicación para gestionar honorario
    "apps.inscripcion",  # Habilita la aplicación para gestionar honorario
    "apps.solicitud",  # Habilita la aplicación para gestionar solicitud
########CONTABILIDAD##########
    "apps.planCuenta",  # Habilita la aplicación para gestionar plan de cuenta  
    "apps.periodoContable.apps.PeriodocontableConfig",  # Importante usar la clase Config
    "apps.empresa",  # Habilita la aplicación para gestionar empresa
    "apps.cuentaBanco",  # Habilita la aplicación para gestionar cuenta bancaria
    "apps.asientoContable",  # Habilita la aplicación para gestionar asiento contable
    "apps.factura",  # Habilita la aplicación para gestionar factura contable
    "apps.saldoContable",  # Habilita la aplicación para gestionar saldo contable
    'apps.requisitoCliente',  # Habilita la aplicación para gestionar requisitos de cliente
    'apps.librosContables',  # Habilita la aplicación para gestionar requisitos de cliente

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.bitacora.middleware.AuditMiddleware",
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",  # IP local del PC donde corre Django
]


# Direcciones IP donde se mostrará la toolbar (normalmente localhost)
INTERNAL_IPS = [
    '127.0.0.1',
]

ROOT_URLCONF = "core.urls"

TEMPLATE_DIR = os.path.join(CORE_DIR, "apps/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # Ruta a tu carpeta static

#Media
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="fundacion2"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="wil123"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        'OPTIONS': {
            'client_encoding': 'UTF8',
            'options': '-c search_path=public'
        }
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Autenticación JWT
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',  # Todos los usuarios autenticados pueden acceder
    ),
}

SIMPLE_JWT = {
    # duraciones opcionales:
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),

    # aquí indicamos a SimpleJWT que el campo PK de tu usuario es idUsuario
    'USER_ID_FIELD': 'idUsuario',
    # y cómo lo nombrará dentro del payload del token
    'USER_ID_CLAIM': 'user_id',
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Ajustes específicos para Windows
if platform.system() == "Windows":
    DATABASES["default"]["OPTIONS"]["client_encoding"] = "UTF8"


# Configuración de autenticación
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

AUTH_USER_MODEL = 'home.Usuarios'

AUTHENTICATION_BACKENDS = [
    'apps.home.backends.CedulaBackend',  # Asegúrate de crear este archivo
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

IME_ZONE = 'America/Caracas'

USE_I18N = True

USE_L10N = True

USE_TZ = True

#############################################################
# SRC: https://devcenter.heroku.com/articles/django-assets

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}
#############################################################
#############################################################
