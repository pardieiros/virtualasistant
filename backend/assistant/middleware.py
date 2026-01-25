"""
Middleware for JWT authentication in Django Channels WebSocket connections.
"""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """
    Get user from JWT token.
    """
    try:
        # Validate and decode token
        token = AccessToken(token_string)
        user_id = token.payload.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            return user
    except (TokenError, User.DoesNotExist) as e:
        logger.error(f"JWT authentication error: {e}")
    
    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for WebSocket connections.
    Extracts token from query string and authenticates user.
    """
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        logger.info(f"WebSocket connection attempt - query_string: {query_string}")
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            logger.info(f"Token found in query string, authenticating...")
            scope['user'] = await get_user_from_token(token)
            logger.info(f"User authenticated: {scope['user']}")
        else:
            logger.warning("No token found in query string, using AnonymousUser")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


