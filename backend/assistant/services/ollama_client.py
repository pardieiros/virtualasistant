import requests
from typing import List, Dict, Optional
from django.conf import settings


SYSTEM_PROMPT = """You are a personal assistant for the user. You help with:

- Detailed shopping lists (items, quantities, stores, notes)
- Agenda and events
- Notes and personal memory
- (In future) controlling the smart home via Home Assistant

When you need the system to execute a real action, you MUST add a final line:

ACTION: {"tool": "tool_name", "args": { ... }}

Available tools:
- add_shopping_item: args { "name": string, "quantity": string (optional), "preferred_store": string (optional), "category": string (optional), "notes": string (optional), "priority": "low"|"medium"|"high" (optional) }
- show_shopping_list: args {}
- add_agenda_event: args { "title": string, "start_datetime": ISO string, "end_datetime": ISO string (optional), "location": string (optional), "description": string (optional), "category": "personal"|"work"|"health"|"other" (optional), "all_day": boolean (optional) }
- save_note: args { "text": string }
- homeassistant_call_service: args { "domain": string, "service": string, "data": object } (for future Home Assistant integration)

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


def build_messages(history: List[Dict], user_message: str) -> List[Dict[str, str]]:
    """
    Build the message list for Ollama, including system prompt.
    
    Args:
        history: Previous conversation history
        user_message: Current user message
    
    Returns:
        List of messages formatted for Ollama
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
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

