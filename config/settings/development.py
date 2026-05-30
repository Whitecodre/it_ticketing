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

# Email (print to console for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'