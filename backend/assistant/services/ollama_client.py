import requests
from typing import List, Dict, Optional
from django.conf import settings
from datetime import datetime, timezone
from django.contrib.auth.models import User
from .memory_service import search_memories, extract_memories_from_conversation


def get_system_prompt(user: Optional[User] = None, relevant_memories: Optional[List[Dict]] = None) -> str:
    """Get system prompt with current date/time information."""
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    current_datetime_iso = now.isoformat()
    
    memories_section = ""
    if relevant_memories:
        memories_section = "\n\nRELEVANT MEMORIES (things you remember about the user):\n"
        for i, memory in enumerate(relevant_memories, 1):
            memories_section += f"{i}. {memory.get('content', '')}\n"
        memories_section += "\nUse these memories to provide personalized and contextual responses. Reference them naturally when relevant.\n"
    
    return f"""You are a personal assistant for the user. You help with:

- Detailed shopping lists (items, quantities, stores, notes)
- Agenda and events
- Notes and personal memory
- (In future) controlling the smart home via Home Assistant

IMPORTANT: Current date and time information:
- Current date: {current_date}
- Current time (UTC): {current_time}
- Current datetime (ISO): {current_datetime_iso}

When the user mentions dates like "today", "tomorrow", "next week", etc., use the current date information above to calculate the correct date.
- "today" = {current_date}
- "tomorrow" = next day after {current_date}
- Always use ISO 8601 format (YYYY-MM-DDTHH:MM:SS+00:00) for dates in the ACTION JSON{memories_section}

When you need the system to execute a real action, you MUST add a final line:

ACTION: {{"tool": "tool_name", "args": {{ ... }}}}

Available tools:
- add_shopping_item: args {{ "name": string, "quantity": string (optional), "preferred_store": string (optional), "category": string (optional), "notes": string (optional), "priority": "low"|"medium"|"high" (optional) }}
- show_shopping_list: args {{}}
- add_agenda_event: args {{ "title": string, "start_datetime": ISO string (REQUIRED, use current date info above for "today"/"tomorrow"), "end_datetime": ISO string (optional), "location": string (optional), "description": string (optional), "category": "personal"|"work"|"health"|"other" (optional), "all_day": boolean (optional), "send_notification": boolean (optional, default false) }}

IMPORTANT: When creating an agenda event, ALWAYS ask the user if they want to receive a push notification reminder before the event starts. If the user says yes, wants a reminder, or mentions notification, set "send_notification": true in the ACTION JSON.
- save_note: args {{ "text": string }}
- web_search: args {{ "query": string }} - Use this when you need current information, facts, news, or data that might change over time. Also use when the user explicitly asks you to search the internet or when you're unsure about something that requires up-to-date information.
- homeassistant_call_service: args {{ "domain": string, "service": string, "data": object }} (for future Home Assistant integration)

IMPORTANT ABOUT WEB SEARCH:
- Use web_search when the user asks about current events, news, weather, stock prices, or any information that changes frequently
- Use web_search when the user explicitly asks you to search or look something up
- Use web_search when you're uncertain about factual information that might be outdated
- DO NOT use web_search for simple questions you can answer from your training data
- When you decide to search, output: ACTION: {{"tool": "web_search", "args": {{"query": "search query here"}}}}

First, respond to the user naturally in Portuguese (Portugal).
On the LAST LINE, only if needed, output the ACTION line.
If no tool is needed, do NOT output ACTION.
Do not explain the JSON format to the user; it's just for the system."""


def call_ollama(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """
    Call Ollama API with messages and return the response.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Optional model name override
    
    Returns:
        The assistant's response text
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    model_name = model or settings.OLLAMA_MODEL
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error calling Ollama: {str(e)}")


def build_messages(history: List[Dict], user_message: str, user: Optional[User] = None) -> List[Dict[str, str]]:
    """
    Build the message list for Ollama, including system prompt with current date/time and relevant memories.
    
    Args:
        history: Previous conversation history
        user_message: Current user message
        user: Optional user instance for memory retrieval
    
    Returns:
        List of messages formatted for Ollama
    """
    # Search for relevant memories if user is provided
    relevant_memories = []
    if user:
        try:
            memories = search_memories(user, user_message, limit=5)
            relevant_memories = [
                {'content': mem.content, 'type': mem.memory_type}
                for mem in memories
            ]
        except Exception as e:
            # If memory search fails, continue without memories
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to retrieve memories: {e}")
    
    # Get system prompt with current date/time and memories (generated fresh each time)
    system_prompt = get_system_prompt(user, relevant_memories)
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history (already formatted)
    for msg in history:
        if msg.get("role") in ["user", "assistant"]:
            messages.append({
                "role": msg["role"],
                "content": msg.get("content", "")
            })
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def parse_action(response_text: str) -> Optional[Dict]:
    """
    Parse ACTION JSON from the LLM response if present.
    
    Args:
        response_text: Full LLM response
    
    Returns:
        Parsed action dict or None
    """
    lines = response_text.strip().split('\n')
    
    for line in reversed(lines):  # Check from the end
        line = line.strip()
        if line.startswith('ACTION:'):
            try:
                action_json = line.replace('ACTION:', '').strip()
                import json
                return json.loads(action_json)
            except (json.JSONDecodeError, ValueError):
                return None
    
    return None

