import requests
from typing import Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_speech(text: str) -> Optional[bytes]:
    """
    Generate speech audio from text using the Piper TTS service.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        Audio data as bytes (WAV format) or None if error
    """
    tts_url = getattr(settings, 'TTS_SERVICE_URL', 'http://192.168.1.73:8010/api/tts/')
    
    if not tts_url:
        logger.warning("TTS service URL not configured")
        return None
    
    try:
        response = requests.post(
            tts_url,
            json={'text': text},
            headers={'Content-Type': 'application/json'},
            timeout=10  # 10 second timeout
        )
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"TTS service returned status {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling TTS service: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in TTS service: {e}")
        return None

