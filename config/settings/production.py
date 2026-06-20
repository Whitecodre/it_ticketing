import os
import dj_database_url
from .base import *

# Allow DEBUG to be controlled via environment variable
DEBUG = env.bool('DEBUG', default=False)

# Use * for now to ensure host is accepted; we'll lock it down later
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Security – redirect HTTP to HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Required for correct protocol detection behind Render’s proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Database – fallback to SQLite for build, Render will override with DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default='sqlite:///db.sqlite3')
    )
}

# Static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Brevo SMTP Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('GMAIL_SMTP_USER')      # e.g., 'your-gmail-address-name@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('GMAIL_SMTP_PASSWORD')  # Your Gmail APP Password
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply.gemzticketingsoftware@gmail.com')
EMAIL_TIMEOUT = 10  # seconds



# Cloudinary file storage
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['https://*.onrender.com'])