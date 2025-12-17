"""
Helper functions for sending Web Push notifications.
Uses pywebpush library with VAPID authentication.
"""
import json
import base64
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.contrib.auth.models import User
from .models import PushSubscription

logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_AVAILABLE = True
    
    # Fix for pywebpush bug with newer cryptography versions
    # Bug in pywebpush/__init__.py line 203: uses ec.SECP256R1 instead of ec.SECP256R1()
    try:
        import pywebpush
        from cryptography.hazmat.primitives.asymmetric import ec as ec_module
        from cryptography.hazmat.backends import default_backend
        
        # Patch the WebPusher class to fix the encode method
        if hasattr(pywebpush, 'WebPusher'):
            original_encode = pywebpush.WebPusher.encode
            
            def fixed_encode(self, data, content_encoding="aes128gcm"):
                """Fixed encode method that properly instantiates EC curve"""
                # Import here to avoid circular dependencies
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.backends import default_backend
                import json as json_module
                
                # The original encode method has a bug where it uses ec.SECP256R1 (class)
                # instead of ec.SECP256R1() (instance). We need to patch the internal call.
                # However, the bug is deep in the code, so we'll use a workaround:
                # Monkey patch ec.generate_private_key to handle the bug
                original_generate = ec_module.generate_private_key
                
                def patched_generate_private_key(curve, backend):
                    # If curve is passed as a class instead of instance, instantiate it
                    if isinstance(curve, type) and issubclass(curve, ec_module.EllipticCurve):
                        curve = curve()
                    return original_generate(curve, backend)
                
                # Temporarily patch generate_private_key
                ec_module.generate_private_key = patched_generate_private_key
                try:
                    result = original_encode(self, data, content_encoding)
                finally:
                    # Restore original
                    ec_module.generate_private_key = original_generate
                
                return result
            
            # Apply the patch
            pywebpush.WebPusher.encode = fixed_encode
            logger.debug("Applied monkey patch to fix pywebpush EC curve bug")
            
    except Exception as patch_error:
        logger.warning(f"Could not apply pywebpush compatibility fix: {patch_error}. "
                      f"Push notifications may fail with 'curve must be an EllipticCurve instance' error.")
        
except ImportError:
    PYWEBPUSH_AVAILABLE = False
    logger.warning("pywebpush not installed. Push notifications will not work. Install with: pip install pywebpush")

try:
    from py_vapid import Vapid
    PY_VAPID_AVAILABLE = True
except ImportError:
    PY_VAPID_AVAILABLE = False


def load_vapid_private_key_for_pywebpush() -> Optional[str]:
    """
    Load and convert VAPID private key to the format expected by pywebpush/py_vapid.
    
    Supports multiple input formats:
    1. PEM format (-----BEGIN PRIVATE KEY----- ...)
    2. Base64URL encoded 32-byte scalar (raw private key value)
    3. Base64 encoded DER PKCS8
    
    Returns:
        Base64URL-encoded DER PKCS8 string (format expected by py_vapid.Vapid.from_string)
        None if key cannot be loaded or converted
    
    Raises:
        Exception: If key conversion fails (logged with exc_info)
    """
    # Get key from settings (support both WEBPUSH_* and VAPID_* names)
    vapid_private_key_raw = (
        getattr(settings, 'WEBPUSH_VAPID_PRIVATE_KEY', None) or 
        getattr(settings, 'VAPID_PRIVATE_KEY', None)
    )
    
    if not vapid_private_key_raw:
        logger.error("WEBPUSH_VAPID_PRIVATE_KEY or VAPID_PRIVATE_KEY not configured in settings")
        return None
    
    if not isinstance(vapid_private_key_raw, str):
        logger.error(f"VAPID private key must be a string, got {type(vapid_private_key_raw)}")
        return None
    
    vapid_private_key_raw = vapid_private_key_raw.strip()
    
    if not vapid_private_key_raw:
        logger.error("VAPID private key is empty")
        return None
    
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        private_key_obj = None
        detected_format = None
        
        # Try format 1: PEM format
        if vapid_private_key_raw.startswith('-----BEGIN'):
            try:
                logger.debug("Attempting to load VAPID key as PEM format")
                private_key_obj = serialization.load_pem_private_key(
                    vapid_private_key_raw.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                detected_format = "PEM"
                logger.debug("Successfully loaded VAPID key as PEM format")
            except Exception as pem_error:
                logger.debug(f"Failed to load as PEM: {pem_error}")
                # Continue to try other formats
        
        # Try format 2: Base64URL encoded 32-byte scalar (raw private key)
        if private_key_obj is None:
            try:
                logger.debug("Attempting to load VAPID key as Base64URL scalar")
                # Add padding if needed
                padding_length = (4 - (len(vapid_private_key_raw) % 4)) % 4
                padding = '=' * padding_length
                base64_str = vapid_private_key_raw.replace('-', '+').replace('_', '/') + padding
                
                # Decode base64url to bytes
                private_key_bytes = base64.urlsafe_b64decode(base64_str)
                
                # Check if it's 32 bytes (scalar) or longer (might be DER)
                if len(private_key_bytes) == 32:
                    # This is a raw scalar, create EC private key from it
                    private_value = int.from_bytes(private_key_bytes, byteorder='big')
                    private_key_obj = ec.derive_private_key(
                        private_value, 
                        ec.SECP256R1(), 
                        default_backend()
                    )
                    detected_format = "Base64URL scalar (32 bytes)"
                    logger.debug(f"Successfully loaded VAPID key as Base64URL scalar (32 bytes)")
                else:
                    # Might be DER, try loading it
                    logger.debug(f"Base64URL decode resulted in {len(private_key_bytes)} bytes, trying as DER")
                    try:
                        private_key_obj = serialization.load_der_private_key(
                            private_key_bytes,
                            password=None,
                            backend=default_backend()
                        )
                        detected_format = "Base64URL encoded DER"
                        logger.debug("Successfully loaded VAPID key as DER from Base64URL")
                    except Exception:
                        # Not DER either, continue to format 3
                        pass
            except Exception as scalar_error:
                logger.debug(f"Failed to load as Base64URL scalar: {scalar_error}")
        
        # Try format 3: Base64 encoded DER PKCS8
        if private_key_obj is None:
            try:
                logger.debug("Attempting to load VAPID key as Base64 encoded DER")
                # Try standard base64 (not url-safe)
                der_bytes = base64.b64decode(vapid_private_key_raw)
                private_key_obj = serialization.load_der_private_key(
                    der_bytes,
                    password=None,
                    backend=default_backend()
                )
                detected_format = "Base64 encoded DER"
                logger.debug("Successfully loaded VAPID key as Base64 encoded DER")
            except Exception as der_error:
                logger.debug(f"Failed to load as Base64 DER: {der_error}")
        
        # If we still don't have a key object, we failed
        if private_key_obj is None:
            error_msg = (
                f"Could not parse VAPID private key. Tried PEM, Base64URL scalar, and DER formats. "
                f"Key length: {len(vapid_private_key_raw)} chars, "
                f"starts with: {vapid_private_key_raw[:20]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Verify it's an EC private key
        if not isinstance(private_key_obj, ec.EllipticCurvePrivateKey):
            error_msg = f"Key is not an EllipticCurvePrivateKey, got {type(private_key_obj)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Convert to DER PKCS8 format (what py_vapid expects)
        der_bytes = private_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Encode to base64 URL-safe without padding (format expected by py_vapid.Vapid.from_string)
        vapid_private_key_str = base64.urlsafe_b64encode(der_bytes).decode('ascii').rstrip('=')
        
        logger.debug(
            f"Loaded VAPID key as EC private key (detected format: {detected_format}). "
            f"Converted to DER+Base64URL for pywebpush (DER length={len(der_bytes)} bytes, "
            f"b64url length={len(vapid_private_key_str)} chars)."
        )
        
        # Return Base64URL-encoded DER PKCS8 string - this is what py_vapid expects
        return vapid_private_key_str
        
    except Exception as e:
        logger.error(f"Error loading VAPID private key: {e}", exc_info=True)
        return None


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
    
    # Load VAPID private key in the format expected by pywebpush
    vapid_private_key = load_vapid_private_key_for_pywebpush()
    if not vapid_private_key:
        logger.error("Failed to load VAPID private key. Cannot send push notifications.")
        return []
    
    # Get VAPID email/sub
    vapid_email = (
        getattr(settings, 'WEBPUSH_VAPID_SUB', None) or 
        getattr(settings, 'VAPID_EMAIL', 'mailto:admin@example.com')
    )
    
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
    
    results = []
    
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
            # e.response is a requests.Response object, not a dict
            error_code = None
            if hasattr(e, 'response') and e.response is not None:
                error_code = getattr(e.response, 'status_code', None)
            
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
                # Other errors (e.g., 400 Bad Request, 429 Too Many Requests, 413 Payload Too Large)
                error_msg = str(e)
                if error_code:
                    error_msg = f"{error_code} - {error_msg}"
                
                # Check for VapidPkHashMismatch - indicates public/private key mismatch
                if 'VapidPkHashMismatch' in error_msg or 'vapid' in error_msg.lower():
                    logger.error(
                        f"VAPID key mismatch error for subscription {subscription.id}: {error_msg}. "
                        f"This usually means the VAPID public key used during subscription doesn't match "
                        f"the private key configured in the backend. Please ensure WEBPUSH_VAPID_PUBLIC_KEY "
                        f"and WEBPUSH_VAPID_PRIVATE_KEY are a valid key pair."
                    )
                else:
                    logger.error(f"Error sending push to subscription {subscription.id}: {error_msg}")
                
                results.append({
                    'subscription_id': subscription.id,
                    'success': False,
                    'error': error_msg,
                })
                
        except Exception as e:
            logger.error(f"Unexpected error sending push to subscription {subscription.id}: {str(e)}", exc_info=True)
            results.append({
                'subscription_id': subscription.id,
                'success': False,
                'error': str(e),
            })
    
    return results
