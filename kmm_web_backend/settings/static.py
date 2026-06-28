"""
Konfigurasi static files dan media files.
"""

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = None  # Akan diset dari base.py menggunakan BASE_DIR

# Media files (User uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = None  # Akan diset dari base.py menggunakan BASE_DIR

# File storage configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": None,  # Akan diset ke MEDIA_ROOT
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
