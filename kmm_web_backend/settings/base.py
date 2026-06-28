"""
Django base settings for kmm_web_backend project.

File ini adalah titik awal settings - hanya berisi konfigurasi paling dasar.
Settings spesifik diorganisir dalam file terpisah untuk kemudahan maintenance.

Struktur settings:
- base.py (file ini): Path, secret key, settings dasar
- apps.py: Installed apps, middleware, templates
- database.py: Database dan cache configuration
- security.py: Authentication, password validation, security headers
- static.py: Static files dan media files
- logging.py: Logging configuration
- local.py: Development settings (DEBUG=True)
- production.py: Production settings (DEBUG=False)

Gunakan DJANGO_ENV environment variable untuk switch antara local/production.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# SECRET KEY
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# ============================================================================
# CORE DJANGO SETTINGS
# ============================================================================

ROOT_URLCONF = "kmm_web_backend.urls"
WSGI_APPLICATION = "kmm_web_backend.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = "id"  # Indonesian locale
TIME_ZONE = "Asia/Jakarta"  # Indonesia timezone
USE_I18N = True  # Enable internationalization
USE_TZ = True  # Enable timezone support

# ============================================================================
# EMAIL CONFIGURATION (Default - override di production)
# ============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@kmm-mesir.org")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ============================================================================
# IMPORT SETTINGS DARI FILE TERPISAH
# ============================================================================

# Import aplikasi, middleware, dan templates
from .apps import *

# Import database dan cache config
from .database import *

# Import logging config
from .logging import *

# Import security settings
from .security import *

# Import static files config
from .static import *

# ============================================================================
# POST-IMPORT CONFIGURATION
# Settings yang perlu BASE_DIR harus diset setelah import
# ============================================================================

# Set template directories
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]

# Set database path untuk SQLite
DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"

# Set static dan media paths
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES["default"]["OPTIONS"]["location"] = MEDIA_ROOT

# Set logging file paths
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING["handlers"]["file"]["filename"] = LOG_DIR / "django.log"
LOGGING["handlers"]["error_file"]["filename"] = LOG_DIR / "django_error.log"
LOGGING["handlers"]["security_file"]["filename"] = LOG_DIR / "security.log"

# ============================================================================
# STORAGE - Cloudflare R2 (S3-compatible), opsional via env (USE_R2)
# Harus di-import TERAKHIR agar bisa meng-override STORAGES & MEDIA_ROOT path.
# ============================================================================

from .storage import *  # noqa: E402,F401,F403
