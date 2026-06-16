# Django Settings - Panduan Penggunaan

## 📁 Struktur Settings

Settings Django diorganisir dalam beberapa file untuk kemudahan pengelolaan:

```
kmm_web_backend/settings/
├── __init__.py          # Auto-import settings berdasarkan DJANGO_ENV
├── base.py              # Settings dasar (paths, i18n, email)
├── apps.py              # Aplikasi, middleware, templates
├── database.py          # Konfigurasi database & cache
├── security.py          # Authentication, password validation, security headers
├── static.py            # Static files dan media files
├── logging.py           # Konfigurasi logging
├── local.py             # Development settings
├── staging.py           # Staging/testing settings
└── production.py        # Production settings
```

## 🎯 Cara Menggunakan

### Development (Default)

Secara default, Django akan menggunakan settings development:

```bash
# Tidak perlu set environment variable
python manage.py runserver

# Atau explicitly set ke local
export DJANGO_ENV=local
python manage.py runserver
```

### Staging (Testing Environment)

Untuk staging/testing sebelum production:

```bash
export DJANGO_ENV=staging
python manage.py runserver
```

### Production

Untuk production, set environment variable `DJANGO_ENV`:

```bash
export DJANGO_ENV=production
python manage.py runserver
```

## 📝 File-file Settings

### 1. `base.py` - Settings Dasar

File utama yang berisi:

- Path configuration (BASE_DIR)
- Secret key
- Core Django settings (ROOT_URLCONF, WSGI_APPLICATION)
- Internationalization (Language, Timezone)
- Email configuration (default)
- Import dari file-file lain
- Post-import configuration (set paths yang butuh BASE_DIR)

### 2. `apps.py` - Aplikasi & Middleware

Berisi konfigurasi:

- **DJANGO_APPS**: Aplikasi Django bawaan
- **THIRD_PARTY_APPS**: Aplikasi pihak ketiga (widget_tweaks, django_htmx, dll)
- **LOCAL_APPS**: Aplikasi custom (data_management, vite)
- **MIDDLEWARE**: Daftar middleware (urutan penting!)
- **TEMPLATES**: Template engine configuration

### 3. `database.py` - Database & Cache

Konfigurasi:

- Database default (SQLite untuk base, override di local/production)
- Cache configuration
- Session settings

### 4. `security.py` - Keamanan

Berisi:

- Password validators
- Authentication URLs (LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL)
- CSRF cookie settings
- Session cookie settings
- Security middleware settings (HSTS, SSL redirect, dll)
- Content security (X-Frame-Options, XSS protection)

### 5. `static.py` - Static Files

Konfigurasi:

- STATIC_URL dan STATIC_ROOT
- MEDIA_URL dan MEDIA_ROOT
- STORAGES configuration (Whitenoise untuk staticfiles)

### 6. `logging.py` - Logging

Konfigurasi logging dengan:

- 3 format: verbose, simple, json
- 4 handler: console, file, error_file, security_file
- Logger untuk berbagai komponen:
    - `django`: General Django logs
    - `django.request`: Request errors
    - `django.security`: Security events
    - `data_management`: App-specific logs
    - `data_management.security`: Security audit logs
    - `data_management.audit`: Audit trail

### 7. `local.py` - Development Settings

Settings untuk development:

- `DEBUG = True`
- SQLite database
- Console email backend
- Relaxed security (no HTTPS required)
- Verbose logging (DEBUG level)
- Django browser reload middleware
- Dummy cache

### 8. `production.py` - Production Settings

Settings untuk production:

- `DEBUG = False`
- PostgreSQL via DATABASE_URL
- Redis cache (optional)
- SMTP email backend
- Strict security (HTTPS required, HSTS, secure cookies)
- WARNING level logging
- Template caching
- Validation untuk SECRET_KEY dan DATABASE_URL

## 🔧 Environment Variables

### Required untuk Production

```bash
# Secret key (minimal 50 karakter)
SECRET_KEY=your-secret-key-here

# Database URL (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Allowed hosts (comma-separated)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Optional

```bash
# Email configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Redis cache (optional, untuk performa lebih baik)
REDIS_URL=redis://localhost:6379/0

# Django environment
DJANGO_ENV=production  # atau 'local' untuk development
```

## 🎨 Menambahkan Settings Baru

### Jika settings umum untuk semua environment:

Tambahkan di `base.py`:

```python
# ============================================================================
# YOUR NEW SETTING CATEGORY
# ============================================================================

YOUR_SETTING = 'value'
```

### Jika settings spesifik untuk kategori tertentu:

Tambahkan di file yang sesuai (`apps.py`, `database.py`, dll):

```python
# Di apps.py untuk aplikasi baru
THIRD_PARTY_APPS = [
    'widget_tweaks',
    'django_htmx',
    'your_new_app',  # Tambahkan di sini
]
```

### Jika settings berbeda untuk development/production:

Tambahkan di `local.py` dan `production.py`:

```python
# Di local.py
YOUR_SETTING = 'development-value'

# Di production.py
YOUR_SETTING = 'production-value'
```

## 🔍 Tips & Best Practices

1. **Jangan hardcode secrets**: Gunakan environment variables
2. **Test dengan production settings**: Jalankan `DJANGO_ENV=production python manage.py check --deploy`
3. **Perhatikan urutan middleware**: Urutan sangat penting!
4. **Review security checklist**: Jalankan `python manage.py check --deploy` secara berkala
5. **Logging**: Gunakan logger yang tepat untuk setiap jenis event
6. **Cache**: Gunakan Redis di production untuk performa optimal

## 🚀 Deployment Checklist

- [ ] Set `DJANGO_ENV=production`
- [ ] Set `SECRET_KEY` (minimal 50 karakter)
- [ ] Set `DATABASE_URL` ke PostgreSQL
- [ ] Set `ALLOWED_HOSTS` dengan domain yang benar
- [ ] Set email configuration jika butuh kirim email
- [ ] (Optional) Set `REDIS_URL` untuk cache
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Run security check: `python manage.py check --deploy`

## ❓ Troubleshooting

### "SECRET_KEY must be set"

Generate secret key baru:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### "DATABASE_URL must be set in production"

Set DATABASE_URL dengan format:

```bash
export DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Logs tidak muncul

Pastikan folder `logs/` ada di root project:

```bash
mkdir -p logs
```

### Import error dari settings

Pastikan semua file settings ada dan tidak ada syntax error. Cek dengan:

```bash
python manage.py check
```

