"""
Local development settings for kmm_web_backend project.

Settings ini digunakan untuk development lokal.
- DEBUG = True
- PostgreSQL (jika DATABASE_URL ada) atau SQLite (default)
- Console email backend
- Relaxed security settings
- Verbose logging

Untuk menggunakan: Jangan set DJANGO_ENV atau set DJANGO_ENV=local
"""

import dj_database_url

from .base import *

# ============================================================================
# DEBUG & DEVELOPMENT
# ============================================================================

DEBUG = True

# Development hosts - allow semua untuk kemudahan development
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]

# Development SECRET_KEY - aman untuk development saja.
# Perlakukan SECRET_KEY kosong di .env sama seperti tidak diset, supaya
# tetap jatuh ke default dev (mencegah "SECRET_KEY must not be empty").
SECRET_KEY = (
    os.environ.get("SECRET_KEY")
    or "dev-secret-key-that-is-long-enough-and-secure-for-development-use-only-change-in-production-50-chars-minimum"
)

# ============================================================================
# DEVELOPMENT APPS & MIDDLEWARE
# ============================================================================

# Tambahkan development-only apps
INSTALLED_APPS += [
    "django_browser_reload",  # Auto-reload browser saat code berubah
]

# Tambahkan development middleware
MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

# ============================================================================
# DATABASE - PostgreSQL (jika DATABASE_URL ada) atau SQLite (default)
# ============================================================================

# Cek apakah DATABASE_URL ada di environment (misal dari Docker Compose)
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Gunakan PostgreSQL via DATABASE_URL (dari Docker Compose)
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback ke SQLite untuk development tanpa Docker
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ============================================================================
# CACHE - Dummy cache untuk development (tidak benar-benar cache)
# ============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ============================================================================
# EMAIL - Console backend (print ke terminal)
# ============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ============================================================================
# SECURITY - Relaxed untuk development
# ============================================================================

# Disable HTTPS requirements
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# ============================================================================
# STATIC FILES - Simple storage untuk development
# ============================================================================

# Hanya override ke storage lokal bila R2 TIDAK aktif. Bila USE_R2=True dengan
# kredensial lengkap, biarkan konfigurasi R2 dari base.storage tetap dipakai.
if not R2_ENABLED:
    STORAGES["default"]["BACKEND"] = "django.core.files.storage.FileSystemStorage"
    STORAGES["staticfiles"][
        "BACKEND"
    ] = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ============================================================================
# LOGGING - Verbose untuk development
# ============================================================================

# Console logging dengan level DEBUG untuk lihat semua detail
LOGGING["handlers"]["console"]["formatter"] = "verbose"
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["root"]["level"] = "DEBUG"

# ============================================================================
# VITE - Hot reload via Vite dev server (respect env var, default False)
# ============================================================================

VITE_DEV_MODE = os.environ.get("VITE_DEV_MODE", "False").lower() in ("true", "1", "yes")

# ============================================================================
# DJANGO DEBUG TOOLBAR (Optional)
# Uncomment jika ingin pakai Django Debug Toolbar
# ============================================================================

# if 'django_debug_toolbar' in INSTALLED_APPS:
#     MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
#     INTERNAL_IPS = ['127.0.0.1']
