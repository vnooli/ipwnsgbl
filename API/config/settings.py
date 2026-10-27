import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",  # required by DRF's AnonymousUser fallback, even with no auth classes configured
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.forecasts",
    "apps.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# No relational database is used - see README "Data handling and persistence".
# Django still needs a DATABASES entry to boot; sqlite is unused in practice.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.forecasts.exceptions.api_exception_handler",
    # No user accounts/auth in this app (see README) - avoids needing
    # django.contrib.auth in INSTALLED_APPS purely to satisfy DRF defaults.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# --- Application-specific configuration -----------------------------------

ELEXON_API_BASE_URL = os.environ.get(
    "ELEXON_API_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"
)

# Hour (0-23) in Europe/London local time, on D-1, that marks the latest
# forecast publish time usable for a day-ahead procurement decision for
# delivery day D. Documented assumption - see README section "Decision cutoff".
DECISION_CUTOFF_HOUR = int(os.environ.get("DECISION_CUTOFF_HOUR", "11"))

ELEXON_CACHE_TTL_SECONDS = int(os.environ.get("ELEXON_CACHE_TTL_SECONDS", "900"))
