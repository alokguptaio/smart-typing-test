from pathlib import Path
import os

# ─── BASE DIR ───────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ───────────────────────────────────────
SECRET_KEY = 'django-insecure-aapki-secret-key-yahan-rakho'
DEBUG = True
ALLOWED_HOSTS = ['*']

# ─── INSTALLED APPS ─────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',      # Google login ke liye

    # Third party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Aapki app
    'app',
]

# ─── MIDDLEWARE ──────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # allauth
]

# ─── URL & WSGI ──────────────────────────────────────
ROOT_URLCONF = 'Typing.urls'   # aapka project naam
WSGI_APPLICATION = 'Typing.wsgi.application'

# ─── TEMPLATES ───────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ─── DATABASE — PostgreSQL ───────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'typingdb',
        'USER':     'postgres',
        'PASSWORD': '1234',
        'HOST':     'localhost',
        'PORT':     '5432',
    }
}

# ─── PASSWORD VALIDATION ─────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── LANGUAGE & TIMEZONE ─────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

# ─── STATIC FILES ────────────────────────────────────
STATIC_URL        = '/static/'
STATICFILES_DIRS  = [BASE_DIR / 'static']
STATIC_ROOT       = BASE_DIR / 'staticfiles'

# ─── MEDIA FILES ─────────────────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── DEFAULT PRIMARY KEY ─────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── SESSION ─────────────────────────────────────────
SESSION_ENGINE         = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE     = 86400      # 24 ghante
SESSION_SAVE_EVERY_REQUEST = True

# ═══════════════════════════════════════════════════
#  EMAIL — Gmail SMTP
#  Steps:
#  1. Gmail → Settings → Security
#  2. 2-Step Verification ON karo
#  3. App Passwords → Mail → Generate
#  4. Woh 16 digit password neeche daalo
# ═══════════════════════════════════════════════════
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = 'alokgupta482005@gmail.com'
EMAIL_HOST_PASSWORD = 'hnxz yvnz wqvh fidx'   # ← Gmail App Password 16 digit yahan
DEFAULT_FROM_EMAIL  = 'Smart Typing Test <alokgupta482005@gmail.com>'

# ─── SITE URL ────────────────────────────────────────
SITE_URL = 'http://127.0.0.1:8000'   # Production mein: 'https://aapkadomain.com'

# ═══════════════════════════════════════════════════
#  GOOGLE LOGIN — django-allauth
# ═══════════════════════════════════════════════════
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

LOGIN_REDIRECT_URL  = '/index/'
LOGOUT_REDIRECT_URL = '/login/'

SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = 'none'