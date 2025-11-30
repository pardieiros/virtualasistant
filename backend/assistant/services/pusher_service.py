from typing import Dict, Any, Optional
from django.conf import settings
from pusher import Pusher


def get_pusher_client() -> Optional[Pusher]:
    """Get configured Pusher client for Soketi."""
    if not all([
        settings.SOCKET_APP_ID,
        settings.SOCKET_APP_KEY,
        settings.SOCKET_APP_SECRET,
    ]):
        return None
    
    scheme = 'https' if settings.SOCKET_USE_TLS else 'http'
    host = settings.SOCKET_HOST
    port = settings.SOCKET_PORT
    
    return Pusher(
        app_id=settings.SOCKET_APP_ID,
        key=settings.SOCKET_APP_KEY,
        secret=settings.SOCKET_APP_SECRET,
        host=host,
        port=int(port),
        ssl=settings.SOCKET_USE_TLS,
        cluster='',
    )


def publish_to_user(user_id: int, event: str, data: Dict[str, Any]) -> bool:
    """
    Publish an event to a user's private channel.
    
    Args:
        user_id: The user's ID
        event: Event name
        data: Event payload
    
    Returns:
        True if published successfully, False otherwise
    """
    try:
        pusher = get_pusher_client()
        if not pusher:
            return False
        
        channel = f'private-user-{user_id}'
        pusher.trigger(channel, event, data)
        return True
    except Exception as e:
        print(f"Error publishing to Pusher: {e}")
        return False

