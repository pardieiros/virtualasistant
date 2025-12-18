from typing import Dict, Any, Optional
from django.conf import settings
from pusher import Pusher
import logging
import json

logger = logging.getLogger('assistant.services.pusher_service')

# Pusher has a limit of ~10KB for data payload
# We'll use 8KB as a safe limit to leave some margin
PUSHER_MAX_DATA_SIZE = 8 * 1024  # 8KB

# Global Pusher client instance (lazy initialization)
_pusher_client: Optional[Pusher] = None
_cached_app_id: Optional[str] = None


def _get_pusher_client() -> Optional[Pusher]:
    """
    Get or create Pusher client instance.
    Uses Soketi configuration which is 100% compatible with Pusher protocol.
    Recreates the client if configuration changed.
    """
    global _pusher_client, _cached_app_id
    
    # Read current configuration
    current_app_id = getattr(settings, 'SOCKET_APP_ID', '').strip()
    
    # Recreate client if config changed or doesn't exist
    if _pusher_client is None or _cached_app_id != current_app_id:
        _pusher_client = None  # Clear old client if exists
        _cached_app_id = current_app_id
    else:
        # Client exists and config matches, return cached client
        return _pusher_client
    
    # Create new client - read configuration from settings
    app_id = current_app_id  # Use the app_id we already read
    app_key = getattr(settings, 'SOCKET_APP_KEY', '').strip()
    app_secret = getattr(settings, 'SOCKET_APP_SECRET', '').strip()
    host = getattr(settings, 'SOCKET_HOST', 'localhost')
    port = getattr(settings, 'SOCKET_PORT', '6001')
    use_tls = getattr(settings, 'SOCKET_USE_TLS', False)
    
    # Validate configuration
    if not all([app_id, app_key, app_secret]):
        missing = []
        if not app_id:
            missing.append('SOCKET_APP_ID')
        if not app_key:
            missing.append('SOCKET_APP_KEY')
        if not app_secret:
            missing.append('SOCKET_APP_SECRET')
        logger.warning(f"Soketi configuration incomplete. Missing: {', '.join(missing)}")
        return None
    
    try:
        # Create Pusher client - Soketi is 100% compatible with Pusher protocol
        _pusher_client = Pusher(
            app_id=app_id,
            key=app_key,
            secret=app_secret,
            host=host,
            port=int(port),
            ssl=use_tls,
        )
        
        logger.info(f"Pusher client initialized successfully with app_id={app_id}")
        logger.debug(f"Configuration: host={host}, port={port}, ssl={use_tls}, app_id={app_id}")
        
        return _pusher_client
    except Exception as e:
        logger.error(f"Failed to initialize Pusher client: {e}", exc_info=True)
        return None


def publish_to_user(user_id: int, event: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to a user's private channel using Pusher client.
    The Pusher client handles all authentication automatically.
    Soketi is 100% compatible with Pusher protocol.
    
    Args:
        user_id: The user's ID
        event: Event name
        data: Event payload
    
    Returns:
        True if published successfully, False otherwise
    """
    try:
        # Get Pusher client (will initialize if needed)
        pusher_client = _get_pusher_client()
        if not pusher_client:
            logger.warning(f"Pusher client not available - cannot send {event} to user {user_id}")
            return False
        
        channel = f'private-user-{user_id}'
        logger.info(f"Publishing to channel {channel}, event: {event}, data keys: {list(data.keys())}")
        
        # Check payload size - Pusher has a limit of ~10KB
        # If audio is present and makes payload too large, remove it
        # Frontend will generate audio locally if needed
        data_to_send = data.copy()
        
        # Check if audio is present and causing payload to be too large
        if 'audio' in data_to_send:
            # Estimate JSON size (base64 is ~33% larger than binary)
            payload_json = json.dumps(data_to_send)
            payload_size = len(payload_json.encode('utf-8'))
            
            logger.debug(f"Payload size: {payload_size} bytes (limit: {PUSHER_MAX_DATA_SIZE} bytes)")
            
            if payload_size > PUSHER_MAX_DATA_SIZE:
                logger.warning(f"Payload too large ({payload_size} bytes), removing audio. Frontend will generate audio locally.")
                # Remove audio but keep audio_format as a hint
                audio_format_hint = data_to_send.get('audio_format', 'wav')
                data_to_send.pop('audio', None)
                # Keep audio_format and signal that audio was removed
                data_to_send['audio_format'] = audio_format_hint
                data_to_send['audio_available'] = False  # Signal that audio was removed due to size
                logger.info(f"Payload size after removing audio: {len(json.dumps(data_to_send).encode('utf-8'))} bytes")
        
        # Use Pusher client trigger method - it handles all authentication automatically
        # The client calculates body_md5, string_to_sign, auth_signature, etc.
        try:
            response = pusher_client.trigger(channel, event, data_to_send)
            logger.info(f"Successfully published {event} to user {user_id}")
            logger.debug(f"Pusher response: {response}")
            return True
        except ValueError as trigger_error:
            # Handle "Too much data" error specifically
            if "Too much data" in str(trigger_error):
                logger.error(f"Payload still too large after removing audio. Attempting to send without audio.")
                # Try again without audio - remove all audio-related fields
                data_without_audio = {k: v for k, v in data_to_send.items() if k not in ['audio', 'audio_format']}
                data_without_audio['audio_available'] = False  # Signal that audio was removed due to size
                try:
                    response = pusher_client.trigger(channel, event, data_without_audio)
                    logger.info(f"Successfully published {event} to user {user_id} (without audio)")
                    return True
                except Exception as retry_error:
                    logger.error(f"Error triggering Pusher event even without audio: {retry_error}")
                    return False
            else:
                logger.error(f"Error triggering Pusher event: {trigger_error}", exc_info=True)
                return False
        except Exception as trigger_error:
            logger.error(f"Error triggering Pusher event: {trigger_error}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Error publishing to Pusher: {e}", exc_info=True)
        return False

