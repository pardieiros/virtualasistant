from typing import Dict, Any, Optional
import logging
from django.contrib.auth.models import User
from datetime import datetime, timezone, timedelta
from ..models import ShoppingItem, AgendaEvent, Note, UserNotificationPreferences
from .homeassistant_client import call_homeassistant_service, get_homeassistant_states
from .terminal_api_service import execute_terminal_command

logger = logging.getLogger(__name__)


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
    elif tool_name == 'homeassistant_get_states':
        return homeassistant_get_states(args, user)
    elif tool_name == 'terminal_command':
        return terminal_command(args, user)
    elif tool_name == 'web_search':
        # Web search is handled asynchronously via Celery task
        # This should not be called directly
        return {
            'success': False,
            'message': 'Web search should be handled asynchronously'
        }
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
        
        # Send push notification if user has shopping updates enabled (async task)
        try:
            preferences = UserNotificationPreferences.objects.get(user=user)
            if preferences.shopping_updates_enabled:
                from ..tasks import send_web_push_notification_task
                send_web_push_notification_task.delay(
                    user_id=user.id,
                    payload={
                        'title': 'Item adicionado à lista de compras',
                        'body': f'"{item.name}" foi adicionado à tua lista de compras',
                        'url': '/shopping-list',
                        'tag': 'shopping-item-added',
                        'data': {
                            'type': 'shopping_item',
                            'item_id': item.id,
                            'item_name': item.name,
                        }
                    }
                )
        except UserNotificationPreferences.DoesNotExist:
            # No preferences set, don't send notification
            pass
        except Exception as push_error:
            # Log error but don't fail the operation
            logger.warning(f"Failed to queue push notification for shopping item: {push_error}")
        
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
        # Parse start datetime
        start_datetime_str = args['start_datetime'].replace('Z', '+00:00')
        start_datetime = datetime.fromisoformat(start_datetime_str)
        
        # Make timezone-aware if not already
        now = datetime.now(timezone.utc)
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        
        # Validate and adjust date if needed
        
        # Check if date is clearly wrong (more than 1 day in the past, or very old dates like 2023)
        # Allow events from today even if time has passed (user might want to log past events)
        one_day_ago = now - timedelta(days=1)
        is_old_date = start_datetime.year < now.year or (start_datetime.year == now.year and start_datetime < one_day_ago)
        
        if is_old_date:
            # Date is clearly wrong (very old or more than 1 day in the past)
            # This is likely an error from LLM, adjust it
            # Keep the time but move to today or tomorrow
            today_at_time = now.replace(
                hour=start_datetime.hour,
                minute=start_datetime.minute,
                second=0,
                microsecond=0
            )
            
            if today_at_time < now:
                # Time has passed today, schedule for tomorrow
                start_datetime = today_at_time + timedelta(days=1)
            else:
                # Time hasn't passed today, schedule for today
                start_datetime = today_at_time
        # If date is today or in the future (even if a few hours ago), trust the LLM
        # The LLM now has access to current date and should handle "today" correctly
        
        # Parse end datetime if provided
        end_datetime = None
        if args.get('end_datetime'):
            end_datetime_str = args['end_datetime'].replace('Z', '+00:00')
            end_datetime = datetime.fromisoformat(end_datetime_str)
            if end_datetime.tzinfo is None:
                end_datetime = end_datetime.replace(tzinfo=timezone.utc)
            
            # Ensure end_datetime is after start_datetime
            if end_datetime <= start_datetime:
                # Add 1 hour if end is before or equal to start
                end_datetime = start_datetime + timedelta(hours=1)
        
        event = AgendaEvent.objects.create(
            user=user,
            title=args.get('title', ''),
            description=args.get('description', ''),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=args.get('location', ''),
            category=args.get('category', 'personal'),
            all_day=args.get('all_day', False),
            send_notification=args.get('send_notification', True),  # Default to True when added by Ollama
        )
        
        # Send immediate push notification when event is added (async task)
        try:
            from ..tasks import send_web_push_notification_task
            time_str = "Todo o dia" if event.all_day else event.start_datetime.strftime("%H:%M")
            message = f'Evento "{event.title}" adicionado à agenda'
            if event.location:
                message += f' em {event.location}'
            message += f' às {time_str}'
            
            send_web_push_notification_task.delay(
                user_id=user.id,
                payload={
                    'title': 'Evento adicionado à agenda',
                    'body': message,
                    'url': '/agenda',
                    'tag': 'agenda-event-added',
                    'data': {
                        'type': 'agenda_event',
                        'event_id': event.id,
                        'title': event.title,
                    }
                }
            )
        except Exception as push_error:
            # Log error but don't fail the operation
            logger.warning(f"Failed to queue push notification for agenda event: {push_error}")
        
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
        
        # Send push notification when note is saved (async task)
        try:
            from ..tasks import send_web_push_notification_task
            # Truncate note text for notification (max 100 chars)
            note_preview = note.text[:100] + ('...' if len(note.text) > 100 else '')
            send_web_push_notification_task.delay(
                user_id=user.id,
                payload={
                    'title': 'Nota guardada',
                    'body': note_preview,
                    'url': '/notes',
                    'tag': 'note-saved',
                    'data': {
                        'type': 'note',
                        'note_id': note.id,
                    }
                }
            )
        except Exception as push_error:
            # Log error but don't fail the operation
            logger.warning(f"Failed to queue push notification for note: {push_error}")
        
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
        domain = args.get('domain')
        service = args.get('service')
        data = args.get('data', {})
        
        result = call_homeassistant_service(
            user=user,
            domain=domain,
            service=service,
            data=data
        )
        
        # Send push notification for climate devices (air conditioners) (async task)
        if result.get('success') and domain == 'climate':
            try:
                from ..tasks import send_web_push_notification_task
                from ..models import DeviceAlias
                
                entity_id = data.get('entity_id', '')
                if entity_id:
                    # Get device alias/name
                    alias_obj = DeviceAlias.objects.filter(user=user, entity_id=entity_id).first()
                    device_name = alias_obj.alias if alias_obj else entity_id.split('.')[-1].replace('_', ' ').title()
                    
                    # Build notification message based on service
                    if service == 'set_temperature':
                        temperature = data.get('temperature')
                        hvac_mode = data.get('hvac_mode', '')
                        mode_text = ''
                        if hvac_mode == 'heat':
                            mode_text = ' (aquecimento)'
                        elif hvac_mode == 'cool':
                            mode_text = ' (arrefecimento)'
                        elif hvac_mode == 'auto':
                            mode_text = ' (automático)'
                        
                        title = 'Ar condicionado ligado'
                        body = f'{device_name} ligado a {temperature}°C{mode_text}'
                        
                    elif service == 'turn_off':
                        title = 'Ar condicionado desligado'
                        body = f'{device_name} desligado'
                        
                    elif service == 'set_hvac_mode':
                        hvac_mode = data.get('hvac_mode', '')
                        mode_text = {
                            'heat': 'aquecimento',
                            'cool': 'arrefecimento',
                            'auto': 'automático',
                            'off': 'desligado'
                        }.get(hvac_mode, hvac_mode)
                        title = 'Modo do ar condicionado alterado'
                        body = f'{device_name} alterado para modo {mode_text}'
                        
                    else:
                        # Generic notification for other climate services
                        title = 'Ar condicionado controlado'
                        body = f'{device_name} - {service}'
                    
                    send_web_push_notification_task.delay(
                        user_id=user.id,
                        payload={
                            'title': title,
                            'body': body,
                            'url': '/homeassistant',
                            'tag': 'homeassistant-climate-control',
                            'data': {
                                'type': 'homeassistant_climate',
                                'entity_id': entity_id,
                                'service': service,
                                'device_name': device_name,
                            }
                        }
                    )
            except Exception as push_error:
                # Log error but don't fail the operation
                logger.warning(f"Failed to queue push notification for climate control: {push_error}")
        
        return result
    except Exception as e:
        return {
            'success': False,
            'message': f'Error calling Home Assistant: {str(e)}'
        }


def homeassistant_get_states(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Get Home Assistant device states."""
    try:
        result = get_homeassistant_states(user)
        return result
    except Exception as e:
        return {
            'success': False,
            'message': f'Error getting Home Assistant states: {str(e)}'
        }


def terminal_command(args: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Execute a terminal command via Terminal API."""
    command = args.get('command', '').strip()
    
    if not command:
        return {
            'success': False,
            'message': 'Command is required',
            'stdout': '',
            'stderr': 'Command is required',
            'returncode': -1,
        }
    
    result = execute_terminal_command(command, user)
    return result

