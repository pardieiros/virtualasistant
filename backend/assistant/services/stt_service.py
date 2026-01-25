"""
Speech-to-Text (STT) Service for voice transcription.

This service handles audio transcription using the STT API.
"""
import io
import logging
import os
import tempfile
import requests
from typing import Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

# Global model cache for Whisper
_whisper_model_cache = None


def transcribe_audio(audio_data: bytes, language: str = "pt") -> Optional[str]:
    """
    Transcribe audio data to text using the STT API.
    Falls back to Whisper if the external STT API fails.
    
    Args:
        audio_data: Raw audio bytes (WebM/Opus format expected)
        language: Language code (default: "pt" for Portuguese)
        
    Returns:
        Transcribed text or None if error
    """
    # Try external STT API first
    try:
        stt_url = f"{settings.STT_API_URL}/stt/transcribe"
        logger.info(f"Sending audio to STT API at {stt_url}, audio size: {len(audio_data)} bytes, language: {language}")
        
        # Prepare multipart form data
        # The API expects 'file' parameter, not 'audio'
        files = {
            'file': ('audio.webm', audio_data, 'audio/webm')
        }
        params = {
            'language': language
        }
        
        # Send request to STT API
        response = requests.post(
            stt_url,
            files=files,
            params=params,
            timeout=30
        )
        
        # Log response details for debugging
        if response.status_code != 200:
            error_detail = response.text[:500] if response.text else "No error detail"
            logger.error(f"STT API returned status {response.status_code}: {error_detail}")
        
        response.raise_for_status()
        result = response.json()
        
        # Extract transcript from response
        transcript = result.get('text', '').strip()
        
        if transcript:
            logger.info(f"STT API transcription successful: {transcript[:100]}...")
            return transcript
        else:
            logger.warning("STT API returned empty transcript, trying Whisper fallback")
            # Fall through to Whisper fallback
        
    except requests.exceptions.HTTPError as e:
        # HTTP error (4xx, 5xx) - check if it's 400 (invalid file)
        if hasattr(e.response, 'status_code') and e.response.status_code == 400:
            error_detail = e.response.text[:200] if e.response.text else "Ficheiro de áudio inválido ou corrompido"
            logger.warning(f"STT API rejected audio file (400): {error_detail}, trying Whisper fallback")
        else:
            logger.warning(f"STT API HTTP error: {e}, trying Whisper fallback")
        # Fall through to Whisper fallback
    except requests.exceptions.RequestException as e:
        logger.warning(f"STT API error: {e}, trying Whisper fallback")
        # Fall through to Whisper fallback
    except Exception as e:
        logger.warning(f"Unexpected error with STT API: {e}, trying Whisper fallback")
        # Fall through to Whisper fallback
    
    # Fallback to Whisper if API failed
    logger.info("Attempting transcription with Whisper (local)")
    return _transcribe_with_whisper(audio_data, language)


def _transcribe_with_whisper(audio_data: bytes, language: str) -> Optional[str]:
    """
    Transcribe using OpenAI Whisper (local model).
    
    Requires: pip install openai-whisper
    Also requires: ffmpeg to be installed on the system
    
    The model is cached globally after first load for better performance.
    
    Args:
        audio_data: Raw audio bytes (WebM/Opus format expected)
        language: Language code (e.g., "pt" for Portuguese)
        
    Returns:
        Transcribed text or None if error
    """
    global _whisper_model_cache
    
    try:
        import whisper
    except ImportError:
        logger.error("Whisper not installed. Install with: pip install openai-whisper")
        return None
    
    audio_path = None
    try:
        # Save audio to temporary file
        # Whisper handles various formats including WebM/Opus
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
            f.write(audio_data)
            audio_path = f.name
        
        # Load model (cache for reuse)
        if _whisper_model_cache is None:
            logger.info("Loading Whisper model (base)...")
            _whisper_model_cache = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        
        # Transcribe with language hint
        # Use task="transcribe" for transcription (not translation)
        result = _whisper_model_cache.transcribe(
            audio_path,
            language=language if language else None,
            task="transcribe"
        )
        
        # Extract text from result
        transcribed_text = result.get("text", "").strip()
        
        if transcribed_text:
            logger.info(f"Whisper transcription successful: {transcribed_text[:100]}...")
            return transcribed_text
        else:
            logger.warning("Whisper returned empty transcript")
            return None
        
    except FileNotFoundError as e:
        logger.error(f"ffmpeg not found. Whisper requires ffmpeg to be installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}", exc_info=True)
        return None
    finally:
        # Clean up temporary file
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary audio file {audio_path}: {e}")


def estimate_speech_duration(audio_data: bytes) -> float:
    """
    Estimate speech duration from audio data.
    
    For WebM/Opus, this is approximate. For accurate duration,
    parse the WebM container or use audio libraries.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Estimated duration in seconds
    """
    # Simple estimation: assume ~50kbps Opus encoding
    # This is rough and should be improved with actual parsing
    estimated_duration = len(audio_data) / (50 * 1024 / 8)  # bytes to seconds
    return max(0.1, estimated_duration)  # Minimum 0.1s


def detect_silence(audio_chunks: list, threshold: int = 3) -> bool:
    """
    Detect if we've accumulated enough chunks to consider processing.
    
    Simple VAD (Voice Activity Detection) based on chunk count.
    In production, use actual VAD algorithms.
    
    Args:
        audio_chunks: List of audio chunks
        threshold: Number of chunks to accumulate before processing
        
    Returns:
        True if should process now, False otherwise
    """
    return len(audio_chunks) >= threshold



