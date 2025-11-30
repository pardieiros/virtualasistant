from typing import Dict, Any, Optional
from django.contrib.auth.models import User
from datetime import datetime
from ..models import ShoppingItem, AgendaEvent, Note
from .homeassistant_client import call_homeassistant_service


def dispatch_tool(tool_name: str, args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """
    Dispatch a tool call based on tool_name and execute it.
    
    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool
        user: The user making the request
    
    Returns:
        Result dict with 'success', 'message', and optional 'data'
    """
    if tool_name == 'add_shopping_item':
        return add_shopping_item(args, user)
    elif tool_name == 'show_shopping_list':
        return show_shopping_list(user)
    elif tool_name == 'add_agenda_event':
        return add_agenda_event(args, user)
    elif tool_name == 'save_note':
        return save_note(args, user)
    elif tool_name == 'homeassistant_call_service':
        return homeassistant_call_service(args, user)
    else:
        return {
            'success': False,
            'message': f'Unknown tool: {tool_name}'
        }


def add_shopping_item(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Add a new shopping item."""
    try:
        item = ShoppingItem.objects.create(
            user=user,
            name=args.get('name', ''),
            quantity=args.get('quantity', ''),
            category=args.get('category', ''),
            preferred_store=args.get('preferred_store', ''),
            alternative_stores=args.get('alternative_stores', ''),
            notes=args.get('notes', ''),
            priority=args.get('priority', 'medium'),
        )
        return {
            'success': True,
            'message': f'Added "{item.name}" to shopping list',
            'data': {
                'id': item.id,
                'name': item.name,
            }
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error adding item: {str(e)}'
        }


def show_shopping_list(user: User) -> Dict[str, Any]:
    """Get the current shopping list (doesn't modify DB)."""
    items = ShoppingItem.objects.filter(
        user=user,
        status='pending'
    ).order_by('-priority', 'created_at')
    
    return {
        'success': True,
        'message': 'Shopping list retrieved',
        'data': {
            'items': [
                {
                    'id': item.id,
                    'name': item.name,
                    'quantity': item.quantity,
                    'store': item.preferred_store,
                }
                for item in items
            ]
        }
    }


def add_agenda_event(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Add a new agenda event."""
    try:
        start_datetime = datetime.fromisoformat(args['start_datetime'].replace('Z', '+00:00'))
        end_datetime = None
        if args.get('end_datetime'):
            end_datetime = datetime.fromisoformat(args['end_datetime'].replace('Z', '+00:00'))
        
        event = AgendaEvent.objects.create(
            user=user,
            title=args.get('title', ''),
            description=args.get('description', ''),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=args.get('location', ''),
            category=args.get('category', 'personal'),
            all_day=args.get('all_day', False),
        )
        return {
            'success': True,
            'message': f'Added event "{event.title}" to agenda',
            'data': {
                'id': event.id,
                'title': event.title,
            }
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error adding event: {str(e)}'
        }


def save_note(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Save a personal note."""
    try:
        note = Note.objects.create(
            user=user,
            text=args.get('text', ''),
        )
        return {
            'success': True,
            'message': 'Note saved',
            'data': {
                'id': note.id,
            }
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error saving note: {str(e)}'
        }


def homeassistant_call_service(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Call a Home Assistant service."""
    try:
        result = call_homeassistant_service(
            user=user,
            domain=args.get('domain'),
            service=args.get('service'),
            data=args.get('data', {})
        )
        return result
    except Exception as e:
        return {
            'success': False,
            'message': f'Error calling Home Assistant: {str(e)}'
        }

