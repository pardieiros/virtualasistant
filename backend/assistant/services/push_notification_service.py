import json
import base64
import logging
from django.conf import settings
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from ..models import PushSubscription

logger = logging.getLogger('assistant.services.push_notification_service')


def _convert_vapid_private_key_to_pem(private_key_b64url: str) -> str:
    """
    Convert VAPID private key from base64url to PEM format.
    The key is stored as base64url-encoded 32-byte private key value.
    """
    try:
        # Decode base64url to bytes
        # Add padding if needed
        padding = '=' * (4 - (len(private_key_b64url) % 4)) % 4
        base64_str = private_key_b64url.replace('-', '+').replace('_', '/') + padding
        private_key_bytes = base64.b64decode(base64_str)
        
        # Create private key from raw bytes
        private_value = int.from_bytes(private_key_bytes, byteorder='big')
        private_key = ec.derive_private_key(private_value, ec.SECP256R1(), default_backend())
        
        # Serialize to PEM format
        pem_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return pem_key.decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting VAPID private key to PEM: {e}", exc_info=True)
        raise ValueError(f"Invalid VAPID private key format: {e}") from e


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
        error_msg = "VAPID keys not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not settings.VAPID_EMAIL:
        error_msg = "VAPID_EMAIL not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
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
        # Convert VAPID private key from base64url to PEM format
        vapid_private_key_pem = _convert_vapid_private_key_to_pem(settings.VAPID_PRIVATE_KEY)
        
        logger.debug(f"Sending push notification to subscription {subscription.id}, endpoint: {subscription.endpoint[:50]}...")
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key_pem,
            vapid_claims={
                "sub": settings.VAPID_EMAIL
            }
        )
        logger.info(f"Push notification sent successfully to subscription {subscription.id}")
    except WebPushException as e:
        error_msg = f"WebPushException: {str(e)}"
        logger.error(error_msg)
        # If subscription is invalid, we might want to delete it
        if e.response and e.response.status_code == 410:
            # Subscription expired or invalid
            logger.warning(f"Subscription {subscription.id} is expired or invalid, deleting...")
            subscription.delete()
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error sending push notification: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e

