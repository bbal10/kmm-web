"""
Konfigurasi storage Cloudflare R2 (S3-compatible).

R2 dipakai untuk media (upload user) dan static files. Backend di-toggle lewat
environment variable: jika kredensial R2 terisi (USE_R2=True dan bucket/keys ada),
STORAGES diarahkan ke R2; jika tidak, fallback ke konfigurasi default
(FileSystemStorage untuk media, Whitenoise untuk static).

Modul ini di-import dari base.py SETELAH static.py supaya bisa meng-override
STORAGES yang sudah didefinisikan di sana.

Environment variables (semua opsional kecuali USE_R2 diaktifkan):
- USE_R2                : "True" untuk mengaktifkan R2 (default: False)
- R2_ACCESS_KEY_ID      : Access Key ID dari R2 API token
- R2_SECRET_ACCESS_KEY  : Secret Access Key dari R2 API token
- R2_BUCKET_NAME        : Nama bucket R2
- R2_ACCOUNT_ID         : Cloudflare account ID (untuk endpoint default)
- R2_ENDPOINT_URL       : Override endpoint penuh (opsional; default dibangun
                          dari R2_ACCOUNT_ID -> https://<account>.r2.cloudflarestorage.com)
- R2_CUSTOM_DOMAIN      : Domain publik untuk serve file (mis. cdn.example.com).
                          Tanpa ini, file di-serve via presigned URL.
- R2_MEDIA_LOCATION     : Prefix folder untuk media (default: "media")
- R2_STATIC_LOCATION    : Prefix folder untuk static (default: "static")
"""

import os


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("true", "1", "yes")


USE_R2 = _env_bool("USE_R2", False)

# Validasi: R2 hanya aktif jika kredensial inti benar-benar tersedia, supaya
# mengaktifkan USE_R2 tanpa kredensial tidak menyebabkan kegagalan diam-diam.
_R2_REQUIRED = [
    os.environ.get("R2_ACCESS_KEY_ID"),
    os.environ.get("R2_SECRET_ACCESS_KEY"),
    os.environ.get("R2_BUCKET_NAME"),
]
_R2_HAS_ENDPOINT = bool(os.environ.get("R2_ENDPOINT_URL") or os.environ.get("R2_ACCOUNT_ID"))

R2_ENABLED = USE_R2 and all(_R2_REQUIRED) and _R2_HAS_ENDPOINT

if USE_R2 and not R2_ENABLED:
    import warnings

    warnings.warn(
        "USE_R2=True tetapi kredensial R2 tidak lengkap "
        "(butuh R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, dan "
        "R2_ENDPOINT_URL atau R2_ACCOUNT_ID). Storage fallback ke default lokal.",
        RuntimeWarning,
    )

if R2_ENABLED:
    AWS_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
    AWS_STORAGE_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

    AWS_S3_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL") or (
        f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
    )

    # R2 memakai region "auto".
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"

    # R2 tidak mendukung ACL; jangan kirim header ACL.
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True  # presigned URL kecuali ada custom domain
    AWS_S3_FILE_OVERWRITE = False

    # Domain publik opsional (Cloudflare CDN / custom domain) untuk serve file
    # tanpa presigned URL.
    R2_CUSTOM_DOMAIN = os.environ.get("R2_CUSTOM_DOMAIN", "").strip()
    if R2_CUSTOM_DOMAIN:
        AWS_S3_CUSTOM_DOMAIN = R2_CUSTOM_DOMAIN
        AWS_QUERYSTRING_AUTH = False

    _MEDIA_LOCATION = os.environ.get("R2_MEDIA_LOCATION", "media").strip("/")
    _STATIC_LOCATION = os.environ.get("R2_STATIC_LOCATION", "static").strip("/")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "location": _MEDIA_LOCATION,
                # media bersifat private secara default (presigned URL).
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "location": _STATIC_LOCATION,
                # static aman untuk di-cache lama & query-string auth dimatikan
                # bila ada custom domain.
                "querystring_auth": False,
                "default_acl": None,
            },
        },
    }

    # URL publik. Bila ada custom domain, S3Storage akan membangun URL dari sana;
    # MEDIA_URL/STATIC_URL di bawah hanya untuk referensi/template fallback.
    if R2_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{R2_CUSTOM_DOMAIN}/{_MEDIA_LOCATION}/"
        STATIC_URL = f"https://{R2_CUSTOM_DOMAIN}/{_STATIC_LOCATION}/"
