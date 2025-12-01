from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any
from django.conf import settings
from .models import AgendaEvent, UserNotificationPreferences
from .push_notifications import send_web_push_to_user
from .services.web_search_service import search_web, format_search_results
from .services.pusher_service import publish_to_user
from .services.ollama_client import call_ollama, build_messages, parse_action
from .services.tool_dispatcher import dispatch_tool
from django.contrib.auth.models import User


@shared_task
def check_upcoming_events():
    """
    Check for events starting soon and send push notifications based on user preferences.
    This task runs every minute via Celery Beat.
    """
    now = timezone.now()
    # Check events starting in the next 60 minutes (to cover all possible reminder times)
    time_window_start = now
    time_window_end = now + timedelta(minutes=60)
    
    # Find events that start in this window and have notifications enabled
    upcoming_events = AgendaEvent.objects.filter(
        start_datetime__gte=time_window_start,
        start_datetime__lte=time_window_end,
        send_notification=True,
    ).select_related('user')
    
    notified_events = []
    
    for event in upcoming_events:
        # Check if user has notifications enabled for agenda events
        try:
            preferences = UserNotificationPreferences.objects.get(user=event.user)
            if not preferences.agenda_events_enabled:
                continue
            reminder_minutes = preferences.agenda_reminder_minutes
        except UserNotificationPreferences.DoesNotExist:
            # Default: notifications enabled, 10 minutes reminder
            reminder_minutes = 10
        
        # Check if we should send notification based on reminder time
        # Calculate minutes until event starts
        time_until_event = (event.start_datetime - now).total_seconds() / 60
        
        # Skip if event already passed
        if time_until_event < 0:
            continue
        
        # Send notification when we're within 1 minute of the reminder time
        # For example, if reminder is 15 minutes, send when time_until_event is between 14 and 16 minutes
        # This gives a 2-minute window to catch the notification
        if abs(time_until_event - reminder_minutes) > 1:
            # Not within the reminder window, skip
            continue
        
        # Format the notification message
        if event.all_day:
            time_str = "Todo o dia"
        else:
            time_str = event.start_datetime.strftime("%H:%M")
        
        message = f"Evento a chegar: {event.title}"
        if event.location:
            message += f" em {event.location}"
        message += f" às {time_str}"
        
        # Send notification to all user's subscriptions using send_web_push_to_user
        try:
            send_web_push_to_user(
                user=event.user,
                payload={
                    'title': 'Evento na Agenda',
                    'body': message,
                    'url': '/agenda',
                    'tag': 'agenda-reminder',
                    'data': {
                        'type': 'agenda_event',
                        'event_id': event.id,
                        'title': event.title,
                    }
                }
            )
        except Exception as e:
            # Log error but continue with other events
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending push notification for event {event.id}: {e}")
        
        notified_events.append(event.id)
    
    return {
        'checked_events': upcoming_events.count(),
        'notified_events': len(notified_events),
        'event_ids': notified_events
    }


@shared_task(name='assistant.tasks.perform_web_search_and_respond')
def perform_web_search_and_respond(
    user_id: int,
    query: str,
    original_message: str,
    conversation_history: list,
    search_query: str
) -> Dict[str, Any]:
    """
    Perform web search and generate a response using Ollama.
    This task runs asynchronously and sends updates via Pusher.
    
    Args:
        user_id: User ID
        query: Original user query
        original_message: Original user message
        conversation_history: Previous conversation history
        search_query: The search query to use
    
    Returns:
        Dictionary with search results and response
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Web search task started for user {user_id}, query: {search_query}")
    
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"User found: {user.username}")
        
        # Notify user that search started
        logger.info("Sending search started notification")
        searching_message = f'🔍 A pesquisar na internet sobre: "{search_query}"...'
        
        # Generate audio for searching message
        audio_base64 = None
        try:
            from .services.tts_service import generate_speech
            import base64
            audio_data = generate_speech(searching_message)
            if audio_data:
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                logger.info(f"Audio generated for searching message, size: {len(audio_data)} bytes")
        except Exception as e:
            logger.warning(f"Error generating audio for searching message: {e}")
        
        pusher_data = {
            'message': searching_message,
            'type': 'search_status',
            'status': 'searching'
        }
        
        if audio_base64:
            pusher_data['audio'] = audio_base64
            pusher_data['audio_format'] = 'wav'
        
        pusher_sent = publish_to_user(
            user_id,
            'assistant-message',
            pusher_data
        )
        if not pusher_sent:
            logger.warning(f"Could not send search started notification via Pusher to user {user_id}")
        
        # Perform web search (with retry logic built-in)
        logger.info(f"Performing web search for: {search_query}")
        search_results = search_web(search_query, max_results=5, retries=3)
        logger.info(f"Search completed, found {len(search_results)} results")
        
        if not search_results:
            # No results found
            logger.warning("No search results found")
            error_message = 'Desculpa, não encontrei resultados na pesquisa. O DuckDuckGo pode estar a limitar as pesquisas. Podes reformular a pergunta ou tentar novamente mais tarde?'
            
            # Try to notify user, but don't fail if Pusher is not configured
            pusher_sent = publish_to_user(
                user_id,
                'assistant-message',
                {
                    'message': error_message,
                    'type': 'search_status',
                    'status': 'no_results'
                }
            )
            
            if not pusher_sent:
                logger.warning("Could not send notification via Pusher (may not be configured)")
            
            return {
                'success': False,
                'message': 'No search results found',
                'error': 'Rate limited or no results'
            }
        
        # Format search results
        formatted_results = format_search_results(search_results)
        
        # Build context with search results
        search_context = f"""O utilizador fez uma pergunta que requer informação atualizada da internet.

Pergunta original: {original_message}

{formatted_results}

Com base nestes resultados da pesquisa, responde à pergunta do utilizador de forma clara e útil. Cita as fontes quando relevante. Responde em português de Portugal."""
        
        # Build messages for Ollama with search results
        messages = build_messages(conversation_history, search_context, user=user)
        
        # Call Ollama with search context
        logger.info("Calling Ollama with search results")
        response_text = call_ollama(messages)
        logger.info(f"Ollama response received, length: {len(response_text)}")
        
        # Parse action if present
        action = parse_action(response_text)
        
        # Clean response text
        clean_response = response_text
        if action:
            lines = response_text.strip().split('\n')
            clean_lines = [
                line for line in lines
                if not line.strip().startswith('ACTION:')
            ]
            clean_response = '\n'.join(clean_lines).strip()
        
        # Execute action if present
        action_result = None
        if action:
            logger.info(f"Action found in response: {action.get('tool')}")
            tool_name = action.get('tool')
            tool_args = action.get('args', {})
            action_result = dispatch_tool(tool_name, tool_args, user)
        
        # Generate audio for the response
        audio_data = None
        audio_base64 = None
        try:
            logger.info("Generating audio for response")
            from .services.tts_service import generate_speech
            audio_data = generate_speech(clean_response)
            if audio_data:
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                logger.info(f"Audio generated successfully, size: {len(audio_data)} bytes")
            else:
                logger.warning("Failed to generate audio")
        except Exception as e:
            logger.error(f"Error generating audio: {e}", exc_info=True)
            # Continue without audio if generation fails
        
        # Send final response to user
        logger.info("Sending final response to user")
        logger.info(f"Response message length: {len(clean_response)}")
        logger.info(f"About to call publish_to_user for user {user_id}")
        try:
            pusher_data = {
                'message': clean_response,
                'type': 'search_response',
                'status': 'completed',
                'action': action if action else None,
                'action_result': action_result if action_result else None,
                'search_results': search_results[:3],  # Send top 3 results for reference
            }
            
            # Add audio if available
            if audio_base64:
                pusher_data['audio'] = audio_base64
                pusher_data['audio_format'] = 'wav'
                logger.info("Including audio in Pusher message")
            
            pusher_sent = publish_to_user(
                user_id,
                'assistant-message',
                pusher_data
            )
            logger.info(f"Pusher publish result: {pusher_sent}")
        except Exception as e:
            logger.error(f"Error calling publish_to_user: {e}", exc_info=True)
            pusher_sent = False
        
        if not pusher_sent:
            logger.error(f"CRITICAL: Could not send response via Pusher to user {user_id}. Response will not reach frontend!")
            logger.error("Pusher configuration check:")
            logger.error(f"  SOCKET_APP_ID: {getattr(settings, 'SOCKET_APP_ID', 'NOT SET')[:20] if getattr(settings, 'SOCKET_APP_ID', '') else 'NOT SET'}...")
            logger.error(f"  SOCKET_APP_KEY: {getattr(settings, 'SOCKET_APP_KEY', 'NOT SET')[:20] if getattr(settings, 'SOCKET_APP_KEY', '') else 'NOT SET'}...")
            logger.error(f"  SOCKET_HOST: {getattr(settings, 'SOCKET_HOST', 'NOT SET')}")
            logger.error(f"  SOCKET_PORT: {getattr(settings, 'SOCKET_PORT', 'NOT SET')}")
            # TODO: Consider alternative notification method (database polling, etc.)
        
        logger.info("Web search task completed successfully")
        return {
            'success': True,
            'response': clean_response,
            'search_results': search_results,
            'action': action,
            'action_result': action_result
        }
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'success': False,
            'error': 'User not found'
        }
    except Exception as e:
        logger.error(f"Error in web search task: {e}", exc_info=True)
        
        # Notify user of error
        try:
            publish_to_user(
                user_id,
                'assistant-message',
                {
                    'message': 'Desculpa, ocorreu um erro ao pesquisar. Por favor tenta novamente.',
                    'type': 'search_status',
                    'status': 'error'
                }
            )
        except Exception as pub_error:
            logger.error(f"Error sending error notification: {pub_error}")
        
        # Re-raise to let Celery handle retry if configured
        raise

