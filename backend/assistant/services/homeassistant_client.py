import requests
from typing import Dict, Any, Optional
from django.contrib.auth.models import User
from ..models import HomeAssistantConfig


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

