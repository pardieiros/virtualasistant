"""
Service for managing user memories with vector search.
"""
from typing import List, Optional, Dict, Any
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from ..models import Memory
from .embedding_service import generate_embedding
import logging

logger = logging.getLogger(__name__)


def save_memory(
    user: User,
    content: str,
    memory_type: str = 'interaction',
    metadata: Optional[Dict[str, Any]] = None,
    importance: float = 0.5,
    generate_embedding_now: bool = True
) -> Memory:
    """
    Save a new memory for the user.
    
    Args:
        user: User who owns the memory
        content: Memory content
        memory_type: Type of memory (shopping, agenda, preference, fact, interaction, other)
        metadata: Optional metadata dictionary
        importance: Importance score (0.0 to 1.0)
        generate_embedding_now: Whether to generate embedding immediately
    
    Returns:
        Created Memory instance
    """
    memory = Memory.objects.create(
        user=user,
        content=content,
        memory_type=memory_type,
        metadata=metadata or {},
        importance=importance,
    )
    
    if generate_embedding_now:
        embedding = generate_embedding(content)
        if embedding:
            memory.embedding = embedding
            memory.save(update_fields=['embedding'])
        else:
            logger.warning(f"Failed to generate embedding for memory {memory.id}")
    
    return memory


def search_memories(
    user: User,
    query: str,
    limit: int = 5,
    memory_types: Optional[List[str]] = None,
    min_importance: float = 0.0,
    similarity_threshold: float = 0.7
) -> List[Memory]:
    """
    Search for relevant memories using vector similarity.
    
    Args:
        user: User to search memories for
        query: Search query text
        limit: Maximum number of results
        memory_types: Optional list of memory types to filter by
        min_importance: Minimum importance score
        similarity_threshold: Minimum similarity score (0.0 to 1.0)
    
    Returns:
        List of Memory instances ordered by relevance
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    if not query_embedding:
        logger.warning("Failed to generate embedding for query, falling back to text search")
        return search_memories_text(user, query, limit, memory_types, min_importance)
    
    # Build base queryset
    queryset = Memory.objects.filter(user=user, importance__gte=min_importance)
    
    # Filter by memory types if specified
    if memory_types:
        queryset = queryset.filter(memory_type__in=memory_types)
    
    # Filter out memories without embeddings
    queryset = queryset.exclude(embedding__isnull=True)
    
    if not queryset.exists():
        # No memories with embeddings, fall back to text search
        return search_memories_text(user, query, limit, memory_types, min_importance)
    
    # Perform vector similarity search
    # Using cosine distance (0 = identical, 2 = opposite)
    # Lower distance = higher similarity
    try:
        from pgvector.django import CosineDistance
        
        # Calculate cosine distance
        # cosine_distance returns 0 for identical, 2 for opposite
        # We want similarity >= threshold
        # similarity = 1 - (distance / 2), so distance <= 2 * (1 - threshold)
        max_distance = 2 * (1 - similarity_threshold)
        
        results = queryset.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).filter(
            distance__lte=max_distance
        ).order_by('distance')[:limit]
        
        return list(results)
    except Exception as e:
        logger.error(f"Error in vector search: {e}, falling back to text search")
        return search_memories_text(user, query, limit, memory_types, min_importance)


def search_memories_text(
    user: User,
    query: str,
    limit: int = 5,
    memory_types: Optional[List[str]] = None,
    min_importance: float = 0.0
) -> List[Memory]:
    """
    Fallback text-based search when vector search is not available.
    
    Args:
        user: User to search memories for
        query: Search query text
        limit: Maximum number of results
        memory_types: Optional list of memory types to filter by
        min_importance: Minimum importance score
    
    Returns:
        List of Memory instances
    """
    queryset = Memory.objects.filter(
        user=user,
        importance__gte=min_importance,
        content__icontains=query
    )
    
    if memory_types:
        queryset = queryset.filter(memory_type__in=memory_types)
    
    return list(queryset.order_by('-importance', '-created_at')[:limit])


def get_recent_memories(
    user: User,
    limit: int = 10,
    memory_types: Optional[List[str]] = None
) -> List[Memory]:
    """
    Get recent memories for the user.
    
    Args:
        user: User to get memories for
        limit: Maximum number of results
        memory_types: Optional list of memory types to filter by
    
    Returns:
        List of Memory instances
    """
    queryset = Memory.objects.filter(user=user)
    
    if memory_types:
        queryset = queryset.filter(memory_type__in=memory_types)
    
    return list(queryset.order_by('-created_at')[:limit])


def extract_memories_from_conversation(
    user: User,
    user_message: str,
    assistant_response: str,
    actions_taken: Optional[List[Dict[str, Any]]] = None
) -> List[Memory]:
    """
    Extract and save important memories from a conversation.
    
    This function identifies important information from the conversation
    and saves it as memories.
    
    Args:
        user: User in the conversation
        user_message: User's message
        assistant_response: Assistant's response
        actions_taken: Optional list of actions that were executed
    
    Returns:
        List of created Memory instances
    """
    memories = []

    # Always persist the interaction so the assistant can remember "what user said".
    # Keep concise content to avoid polluting memory with very large chunks.
    user_excerpt = (user_message or "").strip()[:500]
    assistant_excerpt = (assistant_response or "").strip()[:500]
    if user_excerpt:
        interaction_content = (
            f"Interação recente - Utilizador: {user_excerpt}"
            + (f" | Assistente: {assistant_excerpt}" if assistant_excerpt else "")
        )

        # Avoid storing exact duplicates repeatedly in short bursts.
        recent_duplicate = Memory.objects.filter(
            user=user,
            memory_type='interaction',
            content=interaction_content,
            created_at__gte=timezone.now() - timedelta(minutes=15),
        ).exists()

        if not recent_duplicate:
            memories.append(save_memory(
                user=user,
                content=interaction_content,
                memory_type='interaction',
                metadata={
                    'source': 'chat_turn',
                    'user_message': user_excerpt,
                    'assistant_response': assistant_excerpt,
                },
                importance=0.35,
            ))
    
    # Save shopping-related memories
    if actions_taken:
        for action in actions_taken:
            tool = action.get('tool')
            args = action.get('args', {})
            
            if tool == 'add_shopping_item':
                memory_content = f"Added {args.get('name')} to shopping list"
                if args.get('preferred_store'):
                    memory_content += f" (preferred store: {args.get('preferred_store')})"
                memories.append(save_memory(
                    user=user,
                    content=memory_content,
                    memory_type='shopping',
                    metadata={'item_name': args.get('name'), 'store': args.get('preferred_store')},
                    importance=0.6
                ))
            
            elif tool == 'add_agenda_event':
                memory_content = f"Created event: {args.get('title')}"
                if args.get('location'):
                    memory_content += f" at {args.get('location')}"
                memories.append(save_memory(
                    user=user,
                    content=memory_content,
                    memory_type='agenda',
                    metadata={
                        'event_title': args.get('title'),
                        'start_datetime': args.get('start_datetime'),
                        'location': args.get('location')
                    },
                    importance=0.7
                ))
            
            elif tool == 'save_note':
                memory_content = f"Saved note: {args.get('text', '')[:100]}"
                memories.append(save_memory(
                    user=user,
                    content=memory_content,
                    memory_type='fact',
                    metadata={'note_text': args.get('text')},
                    importance=0.5
                ))
    
    # Save general interaction if it contains important information
    # (This is a simple heuristic - could be improved with LLM-based extraction)
    important_keywords = [
        'prefer', 'preferência', 'gosto', 'não gosto', 'sempre', 'nunca',
        'habitualmente', 'costumo', 'chamo-me', 'sou', 'tenho', 'vivo', 'trabalho',
    ]
    if any(keyword in user_message.lower() for keyword in important_keywords):
        memories.append(save_memory(
            user=user,
            content=f"User said: {user_message}",
            memory_type='preference',
            importance=0.8
        ))
    
    return memories
