import os
from pathlib import Path
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")


# ✅ Explicitly tell dotenv where to find the file
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "aidocumines.com,41.76.109.131,127.0.0.1,localhost,0.0.0.0").split(",")

AUTH_USER_MODEL = "custom_authentication.CustomUser"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_yasg",
    "django_celery_beat",
    "oauth2_provider",
    "corsheaders",
    #"core",
    "core.apps.CoreConfig",
    "file_monitor",
    "document_ocr",
    "document_anonymizer",
    "document_translation",
    "custom_authentication",
    "grid_documents_interrogation",
    "document_operations",
    "file_system",
    "system_settings",
    "document_search",
    "document_structures",
    "file_elasticsearch"
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "custom_authentication.middleware.APICallLoggingMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aiDocuMines.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = "aiDocuMines.wsgi.application"


OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2_provider.Application'
OAUTH2_PROVIDER_ID_TOKEN_MODEL = 'oauth2_provider.IDToken'
OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL = 'oauth2_provider.AccessToken'
OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL = 'oauth2_provider.RefreshToken'


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "aiDocuMines"),
        "USER": os.getenv("POSTGRES_USER", "admin"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "securepassword"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "oauth2_provider.backends.OAuth2Backend",
]

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "SCOPES": {"read": "Read Scope", "write": "Write Scope"},
    "TOKEN_MODEL": "oauth2_provider.models.AccessToken",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "oauth2": {
            "type": "oauth2",
            "tokenUrl": "http://aidocumines.com:8020/o/token/",
            "flow": "application",
            "scopes": {"read": "Read Scope", "write": "Write Scope"},
        }
    },
    "SECURITY": [{"oauth2": ["read", "write"]}],
}

# Elasticsearch DSL config (modern elasticsearch-dsl)
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': 'http://aidocumines_elasticsearch:9200',
        'http_auth': ('elastic', 'changeme'),
    }
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # Console Handler for standard logs
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        # File Handler for Celery logs (optional)
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "celery_logs.log",  # specify the file where Celery logs will be written
        },
    },
    "loggers": {
        # Default Django logger
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        # Celery logger
        "celery": {
            "handlers": ["console", "file"],  # Celery logs go to both console and file
            "level": "INFO",  # Celery logs at INFO level or higher
            "propagate": False,  # Prevent logs from propagating to the root logger
        },
        # Other loggers, e.g., for your application
        "myapp": {
            "handlers": ["console"],
            "level": "DEBUG",  # Or set to INFO depending on your app's needs
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


'''
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
'''

# caching backed by the same Redis you already run for Celery
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),  # use DB-1
        "TIMEOUT": 60 * 60 * 6,      # 6-hour TTL – tune to taste
        "KEY_PREFIX": "ds",          # document-search
    }
}

CORS_ALLOWED_ORIGINS = [
    "http://aidocumines.com",
    "https://aidocumines.aidocumines.com",
    "http://41.76.109.131:8020",
    "http://41.76.109.131:4200",  # ✅ ADD THIS
    "http://localhost:4200",
    "http://127.0.0.1:3000",
    "https://aidocumines-frontend.aidocumines.com",
    "https://ai-docu-mines-frontend.vercel.app"
]

# CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-client-id",
    "x-client-secret",
]
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE"]

FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = 60

