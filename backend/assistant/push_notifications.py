"""
Helper functions for sending Web Push notifications.
Uses pywebpush library with VAPID authentication.
"""
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import PushSubscription

logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_AVAILABLE = True
except ImportError:
    PYWEBPUSH_AVAILABLE = False
    logger.warning("pywebpush not installed. Push notifications will not work. Install with: pip install pywebpush")


def send_web_push_to_user(
    user: User,
    payload: Dict,
    ttl: int = 86400  # 24 hours default TTL
) -> List[Dict]:
    """
    Send a web push notification to all subscriptions of a user.
    
    Args:
        user: The user to send notifications to
        payload: Dictionary with notification data:
            - title (required): Notification title
            - body (required): Notification body
            - icon (optional): URL to icon
            - badge (optional): URL to badge
            - url (optional): URL to open when clicked
            - tag (optional): Notification tag
            - data (optional): Additional data
        ttl: Time to live in seconds (default: 86400 = 24 hours)
    
    Returns:
        List of results for each subscription attempt:
        [
            {'subscription_id': 1, 'success': True, 'error': None},
            {'subscription_id': 2, 'success': False, 'error': '410 Gone'},
            ...
        ]
    """
    if not PYWEBPUSH_AVAILABLE:
        logger.error("pywebpush not available. Cannot send push notifications.")
        return []
    
    # Get all active subscriptions for the user
    subscriptions = PushSubscription.objects.filter(user=user)
    
    if not subscriptions.exists():
        logger.info(f"No push subscriptions found for user {user.id}")
        return []
    
    results = []
    vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', None)
    vapid_email = getattr(settings, 'VAPID_EMAIL', 'mailto:admin@example.com')
    
    if not vapid_private_key:
        logger.error("VAPID_PRIVATE_KEY not configured in settings")
        return []
    
    # Prepare VAPID claims
    vapid_claims = {
        "sub": vapid_email
    }
    
    # Prepare notification payload
    notification_payload = {
        'title': payload.get('title', 'Personal Assistant'),
        'body': payload.get('body', 'New notification'),
        'icon': payload.get('icon', '/personal_assistance_logo.ico'),
        'badge': payload.get('badge', '/personal_assistance_logo.ico'),
        'tag': payload.get('tag', 'personal-assistant-notification'),
        'data': {
            'url': payload.get('url', '/'),
            **payload.get('data', {}),
        },
    }
    
    # Convert VAPID private key from base64url to PEM format if needed
    # Check if it's already in PEM format
    if not vapid_private_key.startswith('-----BEGIN'):
        # Convert from base64url to PEM
        try:
            import base64
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            # Decode base64url to bytes
            padding = '=' * (4 - (len(vapid_private_key) % 4)) % 4
            base64_str = vapid_private_key.replace('-', '+').replace('_', '/') + padding
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
            
            vapid_private_key = pem_key.decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting VAPID private key: {e}", exc_info=True)
            return []
    
    # Send to each subscription
    for subscription in subscriptions:
        try:
            # Prepare subscription info
            subscription_info = {
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh,
                    'auth': subscription.auth,
                },
            }
            
            # Send push notification
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_payload),
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
                ttl=ttl,
            )
            
            results.append({
                'subscription_id': subscription.id,
                'success': True,
                'error': None,
            })
            logger.info(f"Push notification sent successfully to subscription {subscription.id}")
            
        except WebPushException as e:
            # Handle specific error codes
            error_code = getattr(e, 'response', {}).get('status_code', None)
            
            # 410 Gone or 404 Not Found - subscription is invalid, delete it
            if error_code in [410, 404]:
                logger.warning(f"Subscription {subscription.id} is invalid (status {error_code}), deleting...")
                subscription.delete()
                results.append({
                    'subscription_id': subscription.id,
                    'success': False,
                    'error': f'{error_code} - Subscription invalid, deleted',
                })
            else:
                # Other errors (e.g., 429 Too Many Requests, 413 Payload Too Large)
                logger.error(f"Error sending push to subscription {subscription.id}: {str(e)}")
                results.append({
                    'subscription_id': subscription.id,
                    'success': False,
                    'error': str(e),
                })
                
        except Exception as e:
            logger.error(f"Unexpected error sending push to subscription {subscription.id}: {str(e)}")
            results.append({
                'subscription_id': subscription.id,
                'success': False,
                'error': str(e),
            })
    
    return results

