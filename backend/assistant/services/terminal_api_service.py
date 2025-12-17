"""
Service for calling the Terminal API (Proxmox host management).
"""
import requests
from typing import Dict, Optional
from django.contrib.auth.models import User
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def execute_terminal_command(command: str, user: User) -> Dict:
    """
    Execute a terminal command via the Terminal API.
    
    Args:
        command: The command to execute (e.g., "docker ps", "pct list")
        user: The user making the request
    
    Returns:
        Dict with 'success', 'stdout', 'stderr', 'returncode', and 'allowed' keys
    """
    try:
        # Get user's Terminal API configuration
        try:
            config = user.terminal_api_config
        except Exception as e:
            logger.warning(
                f"Terminal API config not found for user {user.id}: {str(e)}"
            )
            return {
                'success': False,
                'message': 'Terminal API not configured. Please configure it in Settings.',
                'stdout': '',
                'stderr': 'Terminal API not configured',
                'returncode': -1,
                'allowed': False,
            }
        
        if not config.enabled:
            logger.info(
                f"Terminal API is disabled for user {user.id}"
            )
            return {
                'success': False,
                'message': 'Terminal API is disabled. Please enable it in Settings.',
                'stdout': '',
                'stderr': 'Terminal API is disabled',
                'returncode': -1,
                'allowed': False,
            }
        
        if not config.api_url or not config.api_token:
            logger.warning(
                f"Terminal API not fully configured for user {user.id}: "
                f"api_url={'set' if config.api_url else 'missing'}, "
                f"api_token={'set' if config.api_token else 'missing'}"
            )
            return {
                'success': False,
                'message': 'Terminal API URL or token not configured.',
                'stdout': '',
                'stderr': 'Terminal API not fully configured',
                'returncode': -1,
                'allowed': False,
            }
        
        # Call the Terminal API
        url = f"{config.api_url.rstrip('/')}/api/system/terminal/run/"
        headers = {
            'Authorization': f'Bearer {config.api_token}',
            'Content-Type': 'application/json',
        }
        data = {
            'command': command,
        }
        
        logger.info(
            f"Calling Terminal API for user {user.id}: command='{command}', "
            f"url={url}"
        )
        
        response = requests.post(url, json=data, headers=headers, timeout=25)
        
        logger.debug(
            f"Terminal API response for user {user.id}: "
            f"status_code={response.status_code}"
        )
        
        if response.status_code == 401 or response.status_code == 403:
            logger.warning(
                f"Terminal API authentication failed for user {user.id}, "
                f"status_code={response.status_code}"
            )
            return {
                'success': False,
                'message': 'Authentication failed. Please check your Terminal API token.',
                'stdout': '',
                'stderr': 'Authentication failed',
                'returncode': -1,
                'allowed': False,
            }
        
        response.raise_for_status()
        result = response.json()
        
        if not result.get('allowed', False):
            logger.warning(
                f"Terminal API command not allowed for user {user.id}: "
                f"command='{command}', stderr='{result.get('stderr', 'N/A')}'"
            )
            return {
                'success': False,
                'message': result.get('stderr', 'Command not allowed'),
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', 'Command not allowed'),
                'returncode': result.get('returncode', -1),
                'allowed': False,
            }
        
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')
        returncode = result.get('returncode', 0)
        
        logger.info(
            f"Terminal API command executed successfully for user {user.id}: "
            f"command='{command}', returncode={returncode}, "
            f"stdout_length={len(stdout)}, stderr_length={len(stderr)}"
        )
        
        return {
            'success': True,
            'message': 'Command executed successfully',
            'stdout': stdout,
            'stderr': stderr,
            'returncode': returncode,
            'allowed': True,
        }
    
    except requests.exceptions.Timeout:
        logger.error(
            f"Terminal API timeout for user {user.id}: command='{command}', "
            f"url={url if 'url' in locals() else 'N/A'}"
        )
        return {
            'success': False,
            'message': 'Command timed out. The Terminal API may be unavailable.',
            'stdout': '',
            'stderr': 'Command timed out',
            'returncode': -1,
            'allowed': False,
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Terminal API request error for user {user.id}: command='{command}', "
            f"error={str(e)}, error_type={type(e).__name__}"
        )
        return {
            'success': False,
            'message': f'Error connecting to Terminal API: {str(e)}',
            'stdout': '',
            'stderr': f'Connection error: {str(e)}',
            'returncode': -1,
            'allowed': False,
        }
    
    except Exception as e:
        logger.error(
            f"Unexpected error calling Terminal API for user {user.id}: "
            f"command='{command}', error={str(e)}, error_type={type(e).__name__}",
            exc_info=True
        )
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'allowed': False,
        }







