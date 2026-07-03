# apps/common/context_processors.py
from django.conf import settings

def vapid_keys(request):
    return {
        'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY,
        'VAPID_PRIVATE_KEY': settings.VAPID_PRIVATE_KEY,
        'VAPID_CLAIM_EMAIL': settings.VAPID_CLAIM_EMAIL,
    }