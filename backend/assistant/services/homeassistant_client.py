import requests
import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth.models import User
from ..models import HomeAssistantConfig

logger = logging.getLogger('assistant.services.homeassistant_client')


def call_homeassistant_service(
    user: User,
    domain: str,
    service: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call a Home Assistant service.
    
    Args:
        user: The user making the request
        domain: HA service domain (e.g., 'light', 'switch')
        service: Service name (e.g., 'turn_on', 'turn_off')
        data: Optional service data
    
    Returns:
        Result dict
    """
    try:
        config = HomeAssistantConfig.objects.filter(user=user, enabled=True).first()
        
        if not config or not config.base_url or not config.long_lived_token:
            return {
                'success': False,
                'message': 'Home Assistant not configured or not enabled'
            }
        
        url = f"{config.base_url.rstrip('/')}/api/services/{domain}/{service}"
        headers = {
            'Authorization': f'Bearer {config.long_lived_token}',
            'Content-Type': 'application/json',
        }
        
        payload = data or {}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        return {
            'success': True,
            'message': f'Called {domain}.{service} successfully',
            'data': response.json() if response.content else {}
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'Home Assistant API error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def get_homeassistant_headers(config: HomeAssistantConfig) -> Dict[str, str]:
    """Get headers for Home Assistant API requests."""
    return {
        'Authorization': f'Bearer {config.long_lived_token}',
        'Content-Type': 'application/json',
    }


def get_homeassistant_config(user: User) -> Optional[HomeAssistantConfig]:
    """Get enabled Home Assistant config for user."""
    return HomeAssistantConfig.objects.filter(user=user, enabled=True).first()




def get_homeassistant_states(user: User) -> Dict[str, Any]:
    """Get all states from Home Assistant."""
    try:
        config = get_homeassistant_config(user)
        if not config or not config.base_url or not config.long_lived_token:
            logger.warning(f"Home Assistant not configured for user {user.username}")
            return {'success': False, 'message': 'Home Assistant not configured'}
        
        url = f"{config.base_url.rstrip('/')}/api/states"
        headers = get_homeassistant_headers(config)
        
        logger.debug(f"Fetching states from {url}")
        response = requests.get(url, headers=headers, timeout=2)  # Reduced from 10s to 2s
        response.raise_for_status()
        states = response.json()
        
        logger.debug(f"Retrieved {len(states)} states")
        return {
            'success': True,
            'states': states
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting states: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Home Assistant API error: {str(e)}'
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting states: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Error getting states: {str(e)}'
        }


def get_homeassistant_entity_registry(user: User) -> Dict[str, Any]:
    """Get entity registry from Home Assistant (includes area information)."""
    try:
        config = get_homeassistant_config(user)
        if not config or not config.base_url or not config.long_lived_token:
            logger.warning(f"Home Assistant not configured for user {user.username}")
            return {'success': False, 'message': 'Home Assistant not configured'}
        
        url = f"{config.base_url.rstrip('/')}/api/config/entity_registry"
        headers = get_homeassistant_headers(config)
        
        logger.debug(f"Fetching entity registry from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        entities = response.json()
        
        logger.debug(f"Retrieved {len(entities)} entities from registry")
        return {
            'success': True,
            'entities': entities
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting entity registry: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Home Assistant API error: {str(e)}'
        }
    except Exception as e:
        logger.exception(f"Unexpected error getting entity registry: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Error getting entity registry: {str(e)}'
        }

