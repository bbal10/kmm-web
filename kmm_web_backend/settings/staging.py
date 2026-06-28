"""
Staging settings for kmm_web_backend project.

Settings ini digunakan untuk staging/testing environment.
- DEBUG = True (untuk debugging)
- PostgreSQL database (via DATABASE_URL, sama seperti production)
- Console email backend (agar mudah testing)
- Relaxed security settings (mirip local)
- Verbose logging

Untuk menggunakan: Set DJANGO_ENV=staging

Environment variables yang HARUS diset:
- SECRET_KEY
- DATABASE_URL (PostgreSQL connection string)

Environment variables opsional:
- ALLOWED_HOSTS (comma-separated domain list)
- REDIS_URL (untuk cache)
"""

import dj_database_url

from .base import *

# ============================================================================
# DEBUG & SECURITY
# ============================================================================

DEBUG = True

# Secret key HARUS diset (minimal 50 karakter)
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError(
        "SECRET_KEY must be set and be at least 50 characters long in staging. "
        "Generate one using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# ============================================================================
# ALLOWED HOSTS
# ============================================================================

# Ambil dari environment variable, jika tidak ada gunakan '*'
ALLOWED_HOSTS_ENV = os.environ.get("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(",")]

# ============================================================================
# DATABASE - PostgreSQL via DATABASE_URL (sama seperti production)
# ============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Validasi database URL harus diset
if not DATABASES["default"]:
    raise ValueError(
        "DATABASE_URL must be set in staging environment. "
        "Format: postgresql://user:password@host:port/dbname"
    )

# ============================================================================
# CACHE - LocMem untuk staging (atau Redis jika tersedia)
# ============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ============================================================================
# SECURITY - Relaxed untuk staging (mirip local)
# ============================================================================

# Disable HTTPS requirements untuk memudahkan testing
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# ============================================================================
# EMAIL - Console backend untuk testing (atau SMTP jika diperlukan)
# ============================================================================

# Gunakan console backend untuk testing, atau uncomment SMTP jika diperlukan
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Uncomment jika ingin pakai SMTP di staging:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# ============================================================================
# STATIC FILES - Whitenoise untuk serving static files (sama seperti production)
# ============================================================================

# Hanya berlaku bila R2 TIDAK aktif; bila USE_R2=True, static di-serve dari R2.
if not R2_ENABLED:
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedStaticFilesStorage"

# ============================================================================
# VITE CONFIGURATION - Production mode (use built assets)
# ============================================================================

VITE_DEV_MODE = False

# ============================================================================
# LOGGING - Verbose untuk debugging (mirip local)
# ============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "data_management": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# ============================================================================
# PERFORMANCE TUNING - Disabled untuk staging (mirip local)
# ============================================================================

# Template caching disabled untuk memudahkan debugging
# (uncomment jika ingin test template caching di staging)
# TEMPLATES[0]['APP_DIRS'] = False
# TEMPLATES[0]['OPTIONS']['loaders'] = [
#     ('django.template.loaders.cached.Loader', [
#         'django.template.loaders.filesystem.Loader',
#         'django.template.loaders.app_directories.Loader',
#     ]),
# ]
