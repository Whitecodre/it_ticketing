# apps/common/utils.py
import json
import base64
from django.conf import settings
from pywebpush import webpush, WebPushException
from .models import PushSubscription

def send_push_notification(notification):
    """
    Send a push notification to all subscribers of the notification recipient.
    Returns a dict with counts: {'sent': int, 'failed': int, 'expired': int}
    """
    subscriptions = PushSubscription.objects.filter(user=notification.recipient)
    if not subscriptions:
        return {'sent': 0, 'failed': 0, 'expired': 0}

    # Prepare the data payload
    payload = json.dumps({
        'title': 'Gemz Software',
        'body': notification.message,
        'url': notification.url or '/',
    })

    # Decode private key if needed (if stored as base64)
    private_key = settings.VAPID_PRIVATE_KEY
    if not private_key.startswith('-----BEGIN'):
        private_key = base64.b64decode(private_key).decode('utf-8')

    sent = 0
    failed = 0
    expired = 0

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'auth': sub.auth_key,
                        'p256dh': sub.p256dh_key,
                    }
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={
                    'sub': f'mailto:{settings.VAPID_CLAIM_EMAIL}'
                }
            )
            sent += 1
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                # Subscription expired – remove it
                sub.delete()
                expired += 1
            else:
                failed += 1
                # Log error (optional)
                print(f"Push failed for {sub.user.email}: {e}")

    return {'sent': sent, 'failed': failed, 'expired': expired}