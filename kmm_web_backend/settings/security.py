"""
Konfigurasi keamanan Django.
Settings ini akan di-override untuk production dengan nilai yang lebih ketat.
"""

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Authentication URLs
LOGIN_REDIRECT_URL = "/dashboard/"
LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/"

# CSRF configuration (defaults untuk development)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  # True di production

# Session security (defaults untuk development)
SESSION_COOKIE_SECURE = False  # True di production

# Security middleware settings (defaults untuk development)
SECURE_SSL_REDIRECT = False  # True di production
SECURE_HSTS_SECONDS = 0  # Set di production
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # True di production
SECURE_HSTS_PRELOAD = False  # True di production (opsional)

# Content Security
X_FRAME_OPTIONS = "DENY"  # Proteksi clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True  # Proteksi MIME-type sniffing
SECURE_BROWSER_XSS_FILTER = True  # XSS protection
