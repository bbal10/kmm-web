"""
Production settings for kmm_web_backend project.

Settings ini digunakan untuk production deployment.
- DEBUG = False
- PostgreSQL database (via DATABASE_URL)
- Security settings yang ketat
- Email backend via SMTP
- Whitenoise untuk static files

Untuk menggunakan: Set DJANGO_ENV=production

Environment variables yang HARUS diset:
- SECRET_KEY (minimal 50 karakter)
- DATABASE_URL (PostgreSQL connection string)
- ALLOWED_HOSTS (comma-separated domain list)

Environment variables opsional:
- EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
- REDIS_URL (untuk cache)
"""

import dj_database_url

from .base import *

# ============================================================================
# DEBUG & SECURITY
# ============================================================================

DEBUG = False

# Secret key HARUS diset di production dan minimal 50 karakter
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError(
        "SECRET_KEY must be set and be at least 50 characters long in production. "
        "Generate one using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# ============================================================================
# ALLOWED HOSTS - HARUS diset dengan domain yang benar
# ============================================================================

# Ambil dari environment variable, jika tidak ada gunakan '*' (tidak disarankan!)
ALLOWED_HOSTS_ENV = os.environ.get("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(",")]

# Warning jika masih menggunakan wildcard
if "*" in ALLOWED_HOSTS:
    import warnings

    warnings.warn(
        "ALLOWED_HOSTS is set to '*' in production. "
        "Please set ALLOWED_HOSTS environment variable with your actual domain(s).",
        RuntimeWarning,
    )

# ============================================================================
# DATABASE - PostgreSQL via DATABASE_URL
# ============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,  # Connection pooling
        conn_health_checks=True,  # Verify connections are healthy
    )
}

# Validasi database URL harus diset
if not DATABASES["default"]:
    raise ValueError(
        "DATABASE_URL must be set in production environment. "
        "Format: postgresql://user:password@host:port/dbname"
    )

# settings.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# HTTPS redirect
# Set SECURE_SSL_REDIRECT=False temporarily in .env if you don't have HTTPS yet
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# CSRF security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 tahun
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True  # Opsional: untuk daftar di browser HSTS preload list

# Proxy headers (untuk deployment di belakang reverse proxy seperti Nginx)

# ============================================================================
# LOGGING - Override untuk containerized environment
# ============================================================================

# Di containerized environment, log ke stdout/stderr daripada file
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
        "console": {"level": "INFO", "class": "logging.StreamHandler", "formatter": "simple"},
        "error_console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["error_console"],
            "level": "WARNING",
            "propagate": False,
        },
        "data_management": {
            "handlers": ["console", "error_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF trusted origins (penting untuk domain + HTTPS)
CSRF_TRUSTED_ORIGINS_ENV = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if CSRF_TRUSTED_ORIGINS_ENV:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip() for origin in CSRF_TRUSTED_ORIGINS_ENV.split(",") if origin.strip()
    ]

# ============================================================================
# EMAIL - SMTP untuk production
# ============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# ============================================================================
# STATIC FILES - Whitenoise untuk serving static files
# ============================================================================

# Override storage backend untuk production - use ManifestStaticFilesStorage
# instead of CompressedManifestStaticFilesStorage to avoid manifest errors.
# Hanya berlaku bila R2 TIDAK aktif; bila USE_R2=True, static & media di-serve
# dari R2 (lihat base.storage).
if not R2_ENABLED:
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedStaticFilesStorage"

# ============================================================================
# VITE CONFIGURATION - Production mode
# ============================================================================

# Disable Vite dev mode in production (use built assets)
VITE_DEV_MODE = False

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Template caching untuk production
TEMPLATES[0]["APP_DIRS"] = False  # Harus False saat pakai custom loaders
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ),
]
