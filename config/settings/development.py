# config/settings/development.py

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

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

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# if env('EMAIL_HOST', default=None):
#     # ✅ Always use Gmail SMTP in development
#     EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#     EMAIL_HOST = env('EMAIL_HOST')
#     EMAIL_PORT = env('EMAIL_PORT', default=587)
#     EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
#     EMAIL_HOST_USER = env('GMAIL_SMTP_USER')
#     EMAIL_HOST_PASSWORD = env('GMAIL_SMTP_PASSWORD')   
#     DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
#     EMAIL_TIMEOUT = 10  # seconds
# else:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'