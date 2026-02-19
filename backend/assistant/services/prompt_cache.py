"""
Caching system for system prompts and context to improve performance.
Uses Django cache framework with configurable TTLs.
"""
from django.core.cache import cache
from django.contrib.auth.models import User
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

# Cache keys
CACHE_KEY_BASE_PROMPT = "prompt:base"
CACHE_KEY_USER_CONTEXT = "prompt:user_context:{user_id}"
CACHE_KEY_MEMORIES = "prompt:memories:{user_id}:{query_hash}"

# Cache TTLs (in seconds)
TTL_BASE_PROMPT = 3600  # 1 hour (rarely changes)
TTL_USER_CONTEXT = 600  # 10 minutes
TTL_MEMORIES = 60  # 60 seconds


def get_base_system_prompt_cached() -> str:
    """
    Get base system prompt from cache or generate if not cached.
    This is the static part that rarely changes.
    """
    cached = cache.get(CACHE_KEY_BASE_PROMPT)
    if cached:
        logger.debug("Base system prompt loaded from cache")
        return cached
    
    # Generate base prompt (static, no user/time data)
    from .ollama_client import get_base_system_prompt
    prompt = get_base_system_prompt()
    cache.set(CACHE_KEY_BASE_PROMPT, prompt, TTL_BASE_PROMPT)
    logger.debug("Base system prompt generated and cached")
    return prompt


def get_user_context_cached(user: User) -> str:
    """
    Get user context (HA devices, aliases) from cache or generate.
    Cached for 10 minutes.
    """
    if not user or not user.id:
        return ""
    
    cache_key = CACHE_KEY_USER_CONTEXT.format(user_id=user.id)
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"User context loaded from cache for user {user.id}")
        return cached
    
    # Generate user context
    from .ollama_client import get_user_context_prompt
    context = get_user_context_prompt(user)
    cache.set(cache_key, context, TTL_USER_CONTEXT)
    logger.debug(f"User context generated and cached for user {user.id}")
    return context


def get_relevant_memories_cached(user: User, user_message: str, limit: int = 5) -> List[Dict]:
    """
    Get relevant memories with caching and heuristic filtering.
    Only searches if message has relevant keywords.
    """
    if not user or not user.id:
        return []
    
    # Heuristic: prefer semantic search when message seems memory-related,
    # otherwise fall back to recent memories so assistant keeps continuity.
    message_lower = user_message.lower()
    
    # Keywords that suggest memory might be relevant
    memory_keywords = [
        'lembra', 'lembraste', 'disseste', 'falaste', 'mencionaste',
        'disse', 'preferência', 'gosto', 'costume', 'sempre',
        'antes', 'último', 'última', 'passado', 'ontem'
    ]
    
    # Check if any keyword is in message
    should_search = any(keyword in message_lower for keyword in memory_keywords)
    
    if not should_search:
        from .memory_service import get_recent_memories
        recent = get_recent_memories(user, limit=min(limit, 3))
        recent_dicts = [
            {'content': mem.content, 'type': mem.memory_type}
            for mem in recent
        ]
        logger.debug(f"Using {len(recent_dicts)} recent memories for user {user.id}")
        return recent_dicts
    
    # Create cache key based on message hash
    import hashlib
    query_hash = hashlib.md5(user_message.encode()).hexdigest()[:8]
    cache_key = CACHE_KEY_MEMORIES.format(user_id=user.id, query_hash=query_hash)
    
    cached = cache.get(cache_key)
    if cached is not None:  # Can be empty list
        logger.debug(f"Memories loaded from cache for user {user.id}")
        return cached
    
    # Search memories
    from .memory_service import search_memories
    try:
        memories = search_memories(user, user_message, limit=limit)
        memory_dicts = [
            {'content': mem.content, 'type': mem.memory_type}
            for mem in memories
        ]
        cache.set(cache_key, memory_dicts, TTL_MEMORIES)
        logger.debug(f"Found {len(memory_dicts)} memories for user {user.id}")
        return memory_dicts
    except Exception as e:
        logger.warning(f"Failed to search memories for user {user.id}: {e}")
        cache.set(cache_key, [], TTL_MEMORIES)  # Cache empty result to avoid repeated failures
        return []


def invalidate_user_context_cache(user_id: int):
    """Invalidate user context cache when HA config or aliases change."""
    cache_key = CACHE_KEY_USER_CONTEXT.format(user_id=user_id)
    cache.delete(cache_key)
    logger.info(f"User context cache invalidated for user {user_id}")


def invalidate_base_prompt_cache():
    """Invalidate base prompt cache (rarely needed)."""
    cache.delete(CACHE_KEY_BASE_PROMPT)
    logger.info("Base system prompt cache invalidated")















