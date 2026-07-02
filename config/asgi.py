# config/asgi.py
import os
from django.core.asgi import get_asgi_application

# Use environment variable if set, fallback to development
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
    os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.development'))

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from apps.common.consumers import NotificationConsumer

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/notifications/', NotificationConsumer.as_asgi()),
        ])
    ),
})