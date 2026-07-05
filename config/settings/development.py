# config/settings/development.py

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Rate limiting settings for development
RATELIMIT_ENABLED = False  # Set to True to test, False to disable in dev

#  Add Channels Layer (Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='it_ticketing_dev'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='postgres'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

TEST_PUSH=True
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

if env('EMAIL_HOST', default=None):
    # ✅ Always use Gmail SMTP in development
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_PORT = env('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')   
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
    EMAIL_TIMEOUT = 10  # seconds
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ================================================================
# DEVELOPMENT - Redis cache fallback (optional, for testing rate limiting)
# ================================================================
# If you have Redis running locally, you can enable it:

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}