"""
Service for generating embeddings using Ollama.
"""
import requests
from typing import List, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_embedding(text: str, model: Optional[str] = None) -> Optional[List[float]]:
    """
    Generate embedding vector for text using Ollama embeddings API.
    
    Args:
        text: Text to generate embedding for
        model: Optional model name (defaults to OLLAMA_MODEL)
    
    Returns:
        List of floats representing the embedding vector, or None if error
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    model_name = model or settings.OLLAMA_MODEL
    
    payload = {
        "model": model_name,
        "prompt": text,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        embedding = data.get("embedding")
        
        if embedding and isinstance(embedding, list):
            return embedding
        else:
            logger.error(f"Invalid embedding response from Ollama: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama embeddings API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating embedding: {e}")
        return None


def generate_embeddings_batch(texts: List[str], model: Optional[str] = None) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts.
    
    Args:
        texts: List of texts to generate embeddings for
        model: Optional model name
    
    Returns:
        List of embeddings (or None for failed ones)
    """
    embeddings = []
    for text in texts:
        embedding = generate_embedding(text, model)
        embeddings.append(embedding)
    return embeddings

