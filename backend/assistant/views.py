from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q

from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig, PushSubscription, UserNotificationPreferences, Conversation, ConversationMessage, TerminalAPIConfig, DeviceAlias
from .serializers import DeviceAliasSerializer
from .services.homeassistant_client import (
    get_homeassistant_states,
    call_homeassistant_service
)
from .serializers import (
    ShoppingItemSerializer,
    AgendaEventSerializer,
    NoteSerializer,
    HomeAssistantConfigSerializer,
    ChatMessageSerializer,
    ChatResponseSerializer,
    PushSubscriptionSerializer,
    UserNotificationPreferencesSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationMessageSerializer,
    TerminalAPIConfigSerializer,
)
from .services.ollama_client import handle_user_message, build_messages, stream_ollama_chat
from .services.tool_dispatcher import dispatch_tool
from .services.pusher_service import publish_to_user
from .services.memory_service import extract_memories_from_conversation
from .services.tts_service import generate_speech
from django.conf import settings
from django.http import StreamingHttpResponse
import hmac
import hashlib
import json


class ShoppingItemViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'preferred_store', 'priority']
    search_fields = ['name', 'notes']
    ordering_fields = ['created_at', 'priority', 'name']
    ordering = ['-priority', 'created_at']
    
    def get_queryset(self):
        return ShoppingItem.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'shopping-updated',
            {'action': 'created', 'item': serializer.data}
        )
        
        # Send push notification if enabled (async task)
        try:
            from .tasks import send_web_push_notification_task
            from .models import UserNotificationPreferences
            
            preferences = UserNotificationPreferences.objects.filter(
                user=self.request.user
            ).first()
            
            if preferences and preferences.shopping_updates_enabled:
                payload = {
                    'title': 'Nova compra adicionada',
                    'body': f'{instance.name} foi adicionado à lista de compras',
                    'icon': '/personal_assistance_logo.ico',
                    'badge': '/personal_assistance_logo.ico',
                    'url': '/shopping',
                    'tag': 'shopping-item-created',
                    'data': {
                        'type': 'shopping_item',
                        'item_id': instance.id,
                    },
                }
                send_web_push_notification_task.delay(self.request.user.id, payload)
        except Exception as e:
            import logging
            logger = logging.getLogger('assistant.views')
            logger.warning(f"Failed to queue push notification for shopping item: {e}")
    
    def perform_update(self, serializer):
        serializer.save()
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'shopping-updated',
            {'action': 'updated', 'item': serializer.data}
        )
    
    def perform_destroy(self, instance):
        item_id = instance.id
        instance.delete()
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'shopping-updated',
            {'action': 'deleted', 'item_id': item_id}
        )


class AgendaEventViewSet(viewsets.ModelViewSet):
    serializer_class = AgendaEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'all_day']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_datetime', 'created_at']
    ordering = ['start_datetime']
    
    def get_queryset(self):
        queryset = AgendaEvent.objects.filter(user=self.request.user)
        
        # Optional date range filters
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            # Filter events that start on or after start_date
            queryset = queryset.filter(start_datetime__gte=start_date)
        if end_date:
            # Filter events that start on or before end_date
            # This ensures we get events that occur within the range
            queryset = queryset.filter(start_datetime__lte=end_date)
        
        return queryset.order_by('start_datetime')
    
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'agenda-updated',
            {'action': 'created', 'event': serializer.data}
        )
        
        # Send push notification if enabled (async task)
        try:
            from .tasks import send_web_push_notification_task
            from .models import UserNotificationPreferences
            
            preferences = UserNotificationPreferences.objects.filter(
                user=self.request.user
            ).first()
            
            if preferences and preferences.agenda_events_enabled:
                payload = {
                    'title': 'Novo evento adicionado',
                    'body': f'{instance.title} foi adicionado à agenda',
                    'icon': '/personal_assistance_logo.ico',
                    'badge': '/personal_assistance_logo.ico',
                    'url': '/agenda',
                    'tag': 'agenda-event-created',
                    'data': {
                        'type': 'agenda_event',
                        'event_id': instance.id,
                    },
                }
                send_web_push_notification_task.delay(self.request.user.id, payload)
        except Exception as e:
            import logging
            logger = logging.getLogger('assistant.views')
            logger.warning(f"Failed to queue push notification for agenda event: {e}")
    
    def perform_update(self, serializer):
        serializer.save()
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'agenda-updated',
            {'action': 'updated', 'event': serializer.data}
        )
    
    def perform_destroy(self, instance):
        event_id = instance.id
        instance.delete()
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'agenda-updated',
            {'action': 'deleted', 'event_id': event_id}
        )


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['text']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        
        # Send push notification for new note if enabled (async task)
        try:
            from .tasks import send_web_push_notification_task
            from .models import UserNotificationPreferences
            
            preferences = UserNotificationPreferences.objects.filter(
                user=self.request.user
            ).first()
            
            if preferences and preferences.notes_enabled:
                # Truncate note text for notification body
                note_text = instance.text[:100] + '...' if len(instance.text) > 100 else instance.text
                
                payload = {
                    'title': 'Nova nota criada',
                    'body': note_text,
                    'icon': '/personal_assistance_logo.ico',
                    'badge': '/personal_assistance_logo.ico',
                    'url': '/notes',
                    'tag': 'note-created',
                    'data': {
                        'type': 'note',
                        'note_id': instance.id,
                    },
                }
                send_web_push_notification_task.delay(self.request.user.id, payload)
        except Exception as e:
            import logging
            logger = logging.getLogger('assistant.views')
            logger.warning(f"Failed to queue push notification for note: {e}")


class HomeAssistantConfigViewSet(viewsets.ModelViewSet):
    serializer_class = HomeAssistantConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return HomeAssistantConfig.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get', 'post'])
    def my_config(self, request):
        """Get or create/update the current user's HA config."""
        config, created = HomeAssistantConfig.objects.get_or_create(
            user=request.user
        )
        
        if request.method == 'POST':
            # Handle token separately (don't update if not provided)
            data = request.data.copy()
            long_lived_token = data.pop('long_lived_token', None)
            
            serializer = self.get_serializer(config, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Only update token if provided (not None and not empty string)
            if long_lived_token is not None and long_lived_token.strip():
                config.long_lived_token = long_lived_token.strip()
                config.save(update_fields=['long_lived_token'])
            
            return Response(serializer.data)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def areas_and_devices(self, request):
        """Get all areas and devices organized by area."""
        import logging
        from collections import defaultdict
        
        logger = logging.getLogger('assistant.views')
        
        try:
            logger.info(f"areas_and_devices called by user {request.user.username} (ID: {request.user.id})")
            
            # Get current states (entity registry endpoint doesn't exist in HA REST API)
            logger.debug("Fetching current states from Home Assistant")
            states_result = get_homeassistant_states(request.user)
            if not states_result.get('success'):
                logger.error(f"Failed to get states: {states_result.get('message', 'Unknown error')}")
                return Response(states_result, status=status.HTTP_400_BAD_REQUEST)
            
            states = states_result.get('states', [])
            logger.debug(f"States retrieved: {len(states)} states")
            
            # Get user's aliases (these contain area information)
            aliases = DeviceAlias.objects.filter(user=request.user)
            alias_map = {alias.entity_id: alias for alias in aliases}
            
            # Organize by area (from aliases) or by domain if no area specified
            areas_dict = defaultdict(list)
            no_area_devices = []
            areas_set = set()
            
            for state in states:
                entity_id = state.get('entity_id', '')
                if not entity_id:
                    continue
                
                # Get alias if exists
                alias_obj = alias_map.get(entity_id)
                
                # Get friendly name from attributes or use entity_id
                attributes = state.get('attributes', {})
                friendly_name = attributes.get('friendly_name') or entity_id.split('.')[-1].replace('_', ' ').title()
                
                # Determine area: use alias area if exists
                if alias_obj and alias_obj.area:
                    final_area = alias_obj.area
                    areas_set.add(final_area)
                else:
                    # No area assigned - will go to no_area_devices
                    final_area = None
                
                device_info = {
                    'entity_id': entity_id,
                    'name': friendly_name,
                    'alias': alias_obj.alias if alias_obj else None,
                    'area': final_area or 'Other',
                    'domain': entity_id.split('.')[0],
                    'state': state.get('state', 'unknown'),
                    'attributes': attributes,
                }
                
                if final_area:
                    areas_dict[final_area].append(device_info)
                else:
                    no_area_devices.append(device_info)
            
            # Convert areas set to list
            response_data = {
                'areas': [
                    {
                        'id': area,
                        'name': area,
                        'devices': areas_dict.get(area, [])
                    }
                    for area in sorted(areas_set)
                ],
                'no_area_devices': no_area_devices
            }
            
            logger.info(f"Successfully organized {len(areas_set)} areas with {sum(len(devices) for devices in areas_dict.values())} devices, plus {len(no_area_devices)} devices without area")
            return Response(response_data)
            
        except Exception as e:
            logger.exception(f"Error in areas_and_devices: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': f'Error processing request: {str(e)}',
                    'error_type': type(e).__name__
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def control_device(self, request):
        """Control a device (turn on/off, set temperature, etc.)."""
        entity_id = request.data.get('entity_id')
        domain = request.data.get('domain')
        service = request.data.get('service')
        service_data = request.data.get('data', {})
        
        if not entity_id or not domain or not service:
            return Response(
                {'error': 'entity_id, domain, and service are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add entity_id to service data if not present
        if 'entity_id' not in service_data:
            service_data['entity_id'] = entity_id
        
        result = call_homeassistant_service(request.user, domain, service, service_data)
        
        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class TerminalAPIConfigViewSet(viewsets.ModelViewSet):
    serializer_class = TerminalAPIConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TerminalAPIConfig.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get', 'post'])
    def my_config(self, request):
        """Get or create/update the current user's Terminal API config."""
        config, created = TerminalAPIConfig.objects.get_or_create(
            user=request.user
        )
        
        if request.method == 'POST':
            # Handle token separately (don't update if not provided)
            data = request.data.copy()
            api_token = data.get('api_token', '')
            
            serializer = self.get_serializer(config, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            # Only update token if provided
            if api_token:
                config.api_token = api_token
            config.api_url = data.get('api_url', config.api_url)
            config.enabled = data.get('enabled', config.enabled)
            config.save()
            
            return Response(serializer.data)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class DeviceAliasViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceAliasSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DeviceAlias.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        conversation = serializer.save(user=self.request.user)
        
        # Auto-generate title from first message if provided
        first_message = self.request.data.get('first_message', '')
        if first_message and not conversation.title:
            # Use first 50 chars of first message as title
            conversation.title = first_message[:50] + ('...' if len(first_message) > 50 else '')
            conversation.save()
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add a message to a conversation."""
        conversation = self.get_object()
        role = request.data.get('role', 'user')
        content = request.data.get('content', '')
        
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = ConversationMessage.objects.create(
            conversation=conversation,
            role=role,
            content=content
        )
        
        # Update conversation timestamp
        conversation.save()
        
        serializer = ConversationMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatStreamView(APIView):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    Returns incremental chunks from Ollama as they arrive.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST endpoint for streaming chat.
        Accepts JSON body with 'message', 'history', and optional 'conversation_id'.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])
        conversation_id = serializer.validated_data.get('conversation_id', None)
        
        # Load conversation history if conversation_id provided
        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                conv_messages = conversation.messages.all().order_by('created_at')
                history = [
                    {'role': msg.role, 'content': msg.content}
                    for msg in conv_messages
                ]
            except Conversation.DoesNotExist:
                logger.warning(f"Conversation {conversation_id} not found for user {request.user.id}")
        
        logger.info(f"Starting streaming chat for user {request.user.id}, message: {message[:50]}...")
        
        def event_stream():
            """Generator function for SSE events."""
            nonlocal conversation  # Access conversation from outer scope
            try:
                # Build messages
                messages = build_messages(history, message, user=request.user)
                logger.debug(f"Built {len(messages)} messages for streaming")
                
                accumulated_clean_text = ""
                action_detected = None
                full_text = ""  # Initialize outside loop for conversation saving
                
                # Stream from Ollama
                for event in stream_ollama_chat(messages):
                    event_type = event.get('type')
                    
                    if event_type == 'chunk':
                        # Send chunk to client
                        chunk_content = event.get('content', '')
                        # Check if this chunk might be part of ACTION line
                        # We'll accumulate and filter at the end
                        accumulated_clean_text += chunk_content
                        
                        # Send as SSE message event
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_content})}\n\n"
                    
                    elif event_type == 'done':
                        # Get clean text without ACTION line
                        full_text = event.get('full_text', '')
                        raw_text = event.get('raw_text', '')
                        
                        logger.info(f"Stream completed for user {request.user.id}, text length: {len(full_text)}")
                        
                        # Calculate how much of the accumulated text was ACTION
                        # and send a correction if needed
                        if len(raw_text) > len(full_text):
                            # There was an ACTION line that should be removed from UI
                            logger.debug("ACTION line detected, sending final clean text")
                            yield f"event: final_text\ndata: {json.dumps({'text': full_text})}\n\n"
                        
                        # Send done event
                        yield f"event: done\ndata: {json.dumps({'finished': True})}\n\n"
                    
                    elif event_type == 'action':
                        # Send action as separate event
                        action_detected = event.get('action', {})
                        logger.info(f"Action detected: {action_detected.get('tool')}")
                        yield f"event: action\ndata: {json.dumps({'action': action_detected})}\n\n"
                    
                    elif event_type == 'error':
                        # Send error event
                        error_msg = event.get('error', 'Unknown error')
                        logger.error(f"Streaming error for user {request.user.id}: {error_msg}")
                        yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
                        return
                
                # Save conversation messages if needed
                if conversation:
                    ConversationMessage.objects.create(
                        conversation=conversation,
                        role='user',
                        content=message
                    )
                    ConversationMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=full_text
                    )
                    conversation.save()
                elif not conversation_id:
                    # Create new conversation
                    conversation = Conversation.objects.create(
                        user=request.user,
                        title=message[:50] + ('...' if len(message) > 50 else '')
                    )
                    ConversationMessage.objects.create(
                        conversation=conversation,
                        role='user',
                        content=message
                    )
                    ConversationMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=full_text
                    )
                
                logger.info(f"Streaming completed successfully for user {request.user.id}")
                
            except Exception as e:
                logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        # Return StreamingHttpResponse with SSE headers
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering
        return response
    
    def get(self, request):
        """
        GET endpoint for streaming chat (alternative for simple clients).
        Message passed as query parameter.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        message = request.GET.get('message', '').strip()
        if not message:
            return Response(
                {'error': 'message parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Starting streaming chat (GET) for user {request.user.id}, message: {message[:50]}...")
        
        def event_stream():
            """Generator function for SSE events."""
            try:
                # Build messages (no history for GET requests)
                messages = build_messages([], message, user=request.user)
                logger.debug(f"Built {len(messages)} messages for streaming")
                
                full_text = ""  # Initialize for potential future use
                
                # Stream from Ollama
                for event in stream_ollama_chat(messages):
                    event_type = event.get('type')
                    
                    if event_type == 'chunk':
                        chunk_content = event.get('content', '')
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_content})}\n\n"
                    
                    elif event_type == 'done':
                        full_text = event.get('full_text', '')
                        raw_text = event.get('raw_text', '')
                        
                        logger.info(f"Stream completed for user {request.user.id}, text length: {len(full_text)}")
                        
                        if len(raw_text) > len(full_text):
                            yield f"event: final_text\ndata: {json.dumps({'text': full_text})}\n\n"
                        
                        yield f"event: done\ndata: {json.dumps({'finished': True})}\n\n"
                    
                    elif event_type == 'action':
                        action_detected = event.get('action', {})
                        logger.info(f"Action detected: {action_detected.get('tool')}")
                        yield f"event: action\ndata: {json.dumps({'action': action_detected})}\n\n"
                    
                    elif event_type == 'error':
                        error_msg = event.get('error', 'Unknown error')
                        logger.error(f"Streaming error for user {request.user.id}: {error_msg}")
                        yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
                        return
                
                logger.info(f"Streaming completed successfully for user {request.user.id}")
                
            except Exception as e:
                logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        # Return StreamingHttpResponse with SSE headers
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])
        conversation_id = serializer.validated_data.get('conversation_id', None)
        
        # If conversation_id is provided, load conversation and add messages to history
        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                # Load conversation messages and add to history
                conv_messages = conversation.messages.all().order_by('created_at')
                history = [
                    {'role': msg.role, 'content': msg.content}
                    for msg in conv_messages
                ]
            except Conversation.DoesNotExist:
                pass
        
        try:
            # Use handle_user_message to orchestrate the LLM call and web search
            result = handle_user_message(
                user=request.user,
                history=history,
                user_message=message,
            )
            
            # Extract results from handle_user_message
            clean_response = result["reply"]
            action = result["action"]
            used_search = result["used_search"]
            search_results = result["search_results"]
            
            logger.info(
                f"Jarvas reply generated for user {request.user.id}, "
                f"action={action.get('tool') if action else None}, "
                f"used_search={used_search}, "
                f"conversation_id={conversation_id}"
            )
            
            # Execute other actions synchronously (web_search is already handled internally)
            action_result = None
            actions_taken = []
            tool_name = None  # Initialize outside if block
            if action:
                tool_name = action.get('tool')
                tool_args = action.get('args', {})
                logger.info(
                    f"Executing tool '{tool_name}' for user {request.user.id} "
                    f"with args: {tool_args}"
                )
                action_result = dispatch_tool(tool_name, tool_args, request.user)
                logger.info(
                    f"Tool '{tool_name}' execution completed for user {request.user.id}, "
                    f"success={action_result.get('success', False)}"
                )
                actions_taken.append({
                    'tool': tool_name,
                    'args': tool_args,
                    'result': action_result
                })
                
                # If terminal_command or homeassistant_get_states was executed, make a second LLM call with the result
                if tool_name == 'terminal_command' or tool_name == 'homeassistant_get_states':
                    if tool_name == 'terminal_command':
                        logger.info(
                            f"Processing terminal_command result for user {request.user.id}, "
                            f"success={action_result.get('success', False)}, "
                            f"returncode={action_result.get('returncode', 'N/A')}"
                        )
                        from .services.ollama_client import build_messages, call_ollama, strip_action_line
                        import json
                        
                        # Build messages for second call with terminal result
                        terminal_result_text = ""
                        if action_result.get('success'):
                            # Success case
                            stdout = action_result.get('stdout', '')
                            stderr = action_result.get('stderr', '')
                            returncode = action_result.get('returncode', 'N/A')
                            
                            logger.debug(
                                f"Terminal command succeeded for user {request.user.id}, "
                                f"returncode={returncode}, "
                                f"stdout_length={len(stdout)}, "
                                f"stderr_length={len(stderr)}"
                            )
                            
                            if stdout:
                                terminal_result_text += f"STDOUT:\n{stdout}\n\n"
                            if stderr:
                                terminal_result_text += f"STDERR:\n{stderr}\n\n"
                            if returncode is not None:
                                terminal_result_text += f"Return code: {returncode}\n"
                            user_message = (
                                "Aqui está o resultado do comando que executaste. "
                                "Responde ao utilizador com base neste resultado, apresentando a informação de forma clara e útil.\n\n"
                                f"{terminal_result_text}\n\n"
                                "IMPORTANTE: NÃO uses nenhuma ferramenta nesta resposta. Apenas apresenta os resultados ao utilizador em português de Portugal. "
                                "NÃO escrevas nenhuma linha ACTION: nesta resposta."
                            )
                        else:
                            # Error case
                            error_message = action_result.get('message', 'Unknown error')
                            stderr = action_result.get('stderr', '')
                            returncode = action_result.get('returncode', 'N/A')
                            
                            logger.warning(
                                f"Terminal command failed for user {request.user.id}, "
                                f"error={error_message}, "
                                f"returncode={returncode}, "
                                f"stderr={stderr[:200] if stderr else 'N/A'}"
                            )
                            
                            terminal_result_text = f"ERRO ao executar o comando:\n{error_message}\n"
                            if stderr:
                                terminal_result_text += f"STDERR: {stderr}\n"
                            user_message = (
                                "Ocorreu um erro ao tentar executar o comando do terminal. "
                                "Informa o utilizador sobre o erro de forma clara e útil, explicando o que aconteceu.\n\n"
                                f"{terminal_result_text}\n\n"
                                "IMPORTANTE: NÃO uses nenhuma ferramenta nesta resposta. Apenas informa o utilizador sobre o erro em português de Portugal. "
                                "NÃO escrevas nenhuma linha ACTION: nesta resposta."
                            )
                    elif tool_name == 'homeassistant_get_states':
                        logger.info(
                            f"Processing homeassistant_get_states result for user {request.user.id}, "
                            f"success={action_result.get('success', False)}"
                        )
                        from .services.ollama_client import build_messages, call_ollama, strip_action_line
                        import json
                        
                        if action_result.get('success'):
                            states = action_result.get('states', [])
                            logger.debug(
                                f"Home Assistant states retrieved for user {request.user.id}, "
                                f"states_count={len(states)}"
                            )
                            
                            # Filter climate devices and format for LLM
                            climate_devices = []
                            for state in states:
                                entity_id = state.get('entity_id', '')
                                if entity_id.startswith('climate.'):
                                    device_state = state.get('state', 'unknown')
                                    attributes = state.get('attributes', {})
                                    friendly_name = attributes.get('friendly_name', entity_id.split('.')[-1].replace('_', ' ').title())
                                    temperature = attributes.get('temperature')
                                    hvac_mode = attributes.get('hvac_mode', 'unknown')
                                    
                                    climate_devices.append({
                                        'entity_id': entity_id,
                                        'name': friendly_name,
                                        'state': device_state,
                                        'temperature': temperature,
                                        'hvac_mode': hvac_mode,
                                    })
                            
                            states_json = json.dumps(climate_devices, ensure_ascii=False, indent=2)
                            user_message = (
                                "Aqui estão os estados dos ar condicionados que consultaste. "
                                "Analisa os dados e responde ao utilizador de forma clara, indicando quais estão ligados, desligados, "
                                "as temperaturas e modos (heat/cool/auto).\n\n"
                                f"Estados dos ar condicionados:\n{states_json}\n\n"
                                "IMPORTANTE: NÃO uses nenhuma ferramenta nesta resposta. Apenas apresenta a informação ao utilizador em português de Portugal. "
                                "NÃO escrevas nenhuma linha ACTION: nesta resposta."
                            )
                        else:
                            error_message = action_result.get('message', 'Unknown error')
                            logger.warning(
                                f"Home Assistant get_states failed for user {request.user.id}, "
                                f"error={error_message}"
                            )
                            user_message = (
                                "Ocorreu um erro ao tentar obter os estados dos dispositivos do Home Assistant. "
                                "Informa o utilizador sobre o erro de forma clara e útil.\n\n"
                                f"Erro: {error_message}\n\n"
                                "IMPORTANTE: NÃO uses nenhuma ferramenta nesta resposta. Apenas informa o utilizador sobre o erro em português de Portugal. "
                                "NÃO escrevas nenhuma linha ACTION: nesta resposta."
                            )
                    
                    # Add to history for second call
                    second_history = history + [
                        {'role': 'assistant', 'content': clean_response},
                        {
                            'role': 'user',
                            'content': user_message
                        }
                    ]
                    
                    # Get system prompt and make second call
                    from .services.ollama_client import get_system_prompt
                    from .services.memory_service import search_memories
                    relevant_memories = None
                    if request.user:
                        memories = search_memories(request.user, message, limit=5)
                        relevant_memories = [
                            {'content': mem.content, 'type': mem.memory_type}
                            for mem in memories
                        ]
                    system_prompt = get_system_prompt(request.user, relevant_memories)
                    
                    second_messages = [
                        {"role": "system", "content": system_prompt},
                        *[m for m in second_history if m["role"] in ("user", "assistant")],
                    ]
                    
                    logger.info(
                        f"Making second LLM call for {tool_name} result for user {request.user.id}"
                    )
                    final_raw = call_ollama(second_messages)
                    clean_response = strip_action_line(final_raw)
                    logger.info(
                        f"Second LLM call completed for user {request.user.id}, "
                        f"response_length={len(clean_response)}"
                    )
                    action = None  # Clear action since we've processed it
            
            # Save conversation messages if conversation_id provided or create new conversation
            if conversation_id and conversation:
                # Add user message
                ConversationMessage.objects.create(
                    conversation=conversation,
                    role='user',
                    content=message
                )
                # Add assistant response
                ConversationMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=clean_response
                )
                conversation.save()  # Update timestamp
            elif not conversation_id:
                # Create new conversation with first message
                conversation = Conversation.objects.create(
                    user=request.user,
                    title=message[:50] + ('...' if len(message) > 50 else '')
                )
                ConversationMessage.objects.create(
                    conversation=conversation,
                    role='user',
                    content=message
                )
                ConversationMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=clean_response
                )
            
            # Extract and save memories from this conversation
            try:
                extract_memories_from_conversation(
                    user=request.user,
                    user_message=message,
                    assistant_response=clean_response,
                    actions_taken=actions_taken
                )
            except Exception as e:
                # Log but don't fail the request if memory saving fails
                logger.warning(f"Failed to save memories: {e}")
            
            # Generate audio for the response
            audio_base64 = None
            try:
                import base64
                audio_data = generate_speech(clean_response)
                if audio_data:
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    logger.info(f"Audio generated for response, size: {len(audio_data)} bytes")
            except Exception as e:
                logger.warning(f"Error generating audio: {e}")
            
            # Prepare response with all fields
            response_data = {
                'reply': clean_response,
                'action': action if action else None,
                'action_result': action_result if action_result else None,
                'used_search': used_search,
                'search_results': search_results if search_results else None,
            }
            
            # Publish to Soketi for realtime updates
            pusher_data = {
                'message': clean_response,
                'action': action,
                'used_search': used_search,
                'search_results': search_results if search_results else None,
                'is_terminal_result': tool_name == 'terminal_command' if action else False,  # Flag to identify terminal command results
                'is_homeassistant_result': tool_name == 'homeassistant_get_states' if action else False,  # Flag to identify HA states results
            }
            
            if audio_base64:
                pusher_data['audio'] = audio_base64
                pusher_data['audio_format'] = 'wav'
            
            # Try to publish via Pusher
            pusher_sent = publish_to_user(
                request.user.id,
                'assistant-message',
                pusher_data
            )
            
            # If Pusher is configured and working, don't return full message in HTTP response
            # Frontend will receive it via Pusher to avoid duplicates
            # Only return minimal response to indicate success
            if pusher_sent:
                # Pusher is working - return minimal response, frontend will get message via Pusher
                return Response({
                    'reply': None,  # Message will come via Pusher
                    'action': action if action else None,
                    'action_result': action_result if action_result else None,
                    'used_search': used_search,
                    'search_results': search_results if search_results else None,
                    'via_pusher': True,  # Signal that message is coming via Pusher
                }, status=status.HTTP_200_OK)
            else:
                # Pusher not working - return full response as fallback
                logger.warning("Pusher not available, returning full response in HTTP")
                return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserNotificationPreferencesViewSet(viewsets.ModelViewSet):
    serializer_class = UserNotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserNotificationPreferences.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get', 'post'])
    def my_preferences(self, request):
        """Get or create/update the current user's notification preferences."""
        preferences, created = UserNotificationPreferences.objects.get_or_create(
            user=request.user,
            defaults={
                'agenda_events_enabled': True,
                'agenda_reminder_minutes': 15,
                'shopping_updates_enabled': False,
                'notes_enabled': True,
            }
        )
        
        if request.method == 'POST':
            serializer = self.get_serializer(preferences, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)


class PusherAuthView(APIView):
    """
    Authenticate Pusher private channel subscriptions.
    Required for private channels in Pusher/Soketi.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        socket_id = request.data.get('socket_id')
        channel_name = request.data.get('channel_name')
        
        if not socket_id or not channel_name:
            return Response(
                {'error': 'socket_id and channel_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify channel name format (private-user-{user_id})
        if not channel_name.startswith('private-user-'):
            return Response(
                {'error': 'Invalid channel name'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Extract user_id from channel name
        try:
            channel_user_id = int(channel_name.replace('private-user-', ''))
        except ValueError:
            return Response(
                {'error': 'Invalid channel name format'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify user is requesting their own channel
        if channel_user_id != request.user.id:
            return Response(
                {'error': 'Unauthorized channel access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate auth signature
        app_secret = getattr(settings, 'SOCKET_APP_SECRET', '').strip()
        if not app_secret:
            return Response(
                {'error': 'Pusher not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create auth string: socket_id:channel_name
        auth_string = f"{socket_id}:{channel_name}"
        
        # Generate HMAC SHA256 signature
        signature = hmac.new(
            app_secret.encode('utf-8'),
            auth_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return Response({
            'auth': f"{getattr(settings, 'SOCKET_APP_KEY', '').strip()}:{signature}"
        })


class TTSView(APIView):
    """
    Text-to-Speech endpoint.
    Generates audio from text using the Piper TTS service.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        text = request.data.get('text', '').strip()
        
        if not text:
            return Response(
                {'error': 'Text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate speech audio
        try:
            audio_data = generate_speech(text)
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate speech. TTS service may be unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        if audio_data is None:
            return Response(
                {'error': 'Failed to generate speech. TTS service may be unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Convert audio to base64
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Return audio as base64 JSON
        return Response({
            'audio': audio_base64,
            'format': 'wav',
            'size': len(audio_data)
        })


class PushSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PushSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a push subscription.
        Expects: { "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } }
        """
        endpoint = request.data.get('endpoint')
        keys = request.data.get('keys', {})
        
        if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
            return Response(
                {'error': 'Missing required fields: endpoint, keys.p256dh, keys.auth'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription, created = PushSubscription.objects.get_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': keys['p256dh'],
                'auth': keys['auth'],
            }
        )
        
        if not created:
            # Update existing subscription
            subscription.p256dh = keys['p256dh']
            subscription.auth = keys['auth']
            subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def unregister(self, request):
        """
        Unregister a push subscription by endpoint.
        Expects: { "endpoint": "..." }
        """
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response(
                {'error': 'Missing endpoint'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted = PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint
        ).delete()
        
        return Response(
            {'deleted': deleted[0] > 0},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def vapid_public_key(self, request):
        """
        Get VAPID public key for push notifications.
        """
        from django.conf import settings
        # Support both old and new variable names for compatibility
        vapid_public_key = getattr(settings, 'WEBPUSH_VAPID_PUBLIC_KEY', None) or getattr(settings, 'VAPID_PUBLIC_KEY', None)
        if not vapid_public_key:
            return Response(
                {'error': 'VAPID public key not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({'public_key': vapid_public_key})
    
    @action(detail=False, methods=['post'])
    def test(self, request):
        """
        Send a test push notification to all user's subscriptions.
        """
        from .push_notifications import send_web_push_to_user
        
        payload = {
            'title': 'Test Notification',
            'body': 'This is a test notification from your Personal Assistant! ✅',
            'icon': '/personal_assistance_logo.ico',
            'badge': '/personal_assistance_logo.ico',
            'url': '/',
            'tag': 'test-notification',
            'data': {'type': 'test'},
        }
        
        try:
            results = send_web_push_to_user(request.user, payload)
            
            # Count successes and errors
            success_count = sum(1 for r in results if r.get('success', False))
            errors = [r.get('error') for r in results if not r.get('success', False) and r.get('error')]
            
            if success_count > 0:
                return Response({
                    'success': True,
                    'message': f'Test notification sent to {success_count} device(s)',
                    'results': results,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to send test notification',
                    'results': results,
                    'errors': errors
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            import logging
            logger = logging.getLogger('assistant.views')
            logger.error(f"Error in test notification endpoint: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

