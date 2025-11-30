import json
import base64
from django.conf import settings
from pywebpush import webpush, WebPushException
from ..models import PushSubscription


def send_push_notification(subscription: PushSubscription, title: str, body: str, data: dict = None):
    """
    Send a push notification to a subscription.
    
    Args:
        subscription: PushSubscription instance
        title: Notification title
        body: Notification body text
        data: Optional data payload
    """
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        raise ValueError("VAPID keys not configured")
    
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth
        }
    }
    
    payload = {
        "title": title,
        "body": body,
    }
    
    if data:
        payload["data"] = data
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.VAPID_EMAIL
            }
        )
    except WebPushException as e:
        # If subscription is invalid, we might want to delete it
        if e.response and e.response.status_code == 410:
            # Subscription expired or invalid
            subscription.delete()
        raise

