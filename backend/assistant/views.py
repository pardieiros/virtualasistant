from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q

from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig, PushSubscription, UserNotificationPreferences
from .serializers import (
    ShoppingItemSerializer,
    AgendaEventSerializer,
    NoteSerializer,
    HomeAssistantConfigSerializer,
    ChatMessageSerializer,
    ChatResponseSerializer,
    PushSubscriptionSerializer,
    UserNotificationPreferencesSerializer,
)
from .services.ollama_client import build_messages, call_ollama, parse_action
from .services.tool_dispatcher import dispatch_tool
from .services.pusher_service import publish_to_user
from .services.memory_service import extract_memories_from_conversation
from .tasks import perform_web_search_and_respond
from .services.tts_service import generate_speech
from django.conf import settings
import hmac
import hashlib


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
        serializer.save(user=self.request.user)
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'shopping-updated',
            {'action': 'created', 'item': serializer.data}
        )
    
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
        serializer.save(user=self.request.user)
        # Publish update via Soketi
        publish_to_user(
            self.request.user.id,
            'agenda-updated',
            {'action': 'created', 'event': serializer.data}
        )
    
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
        serializer.save(user=self.request.user)


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
            serializer = self.get_serializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])
        
        # Build messages for Ollama (with memory retrieval)
        messages = build_messages(history, message, user=request.user)
        
        try:
            # Call Ollama
            response_text = call_ollama(messages)
            
            # Parse action if present
            action = parse_action(response_text)
            
            # Clean response text (remove ACTION line if present)
            clean_response = response_text
            if action:
                lines = response_text.strip().split('\n')
                clean_lines = [
                    line for line in lines
                    if not line.strip().startswith('ACTION:')
                ]
                clean_response = '\n'.join(clean_lines).strip()
            
            # Check if action is web_search - handle asynchronously
            if action and action.get('tool') == 'web_search':
                search_query = action.get('args', {}).get('query', message)
                
                logger.info(f"Web search requested for user {request.user.id}, query: {search_query}")
                
                try:
                    # Launch async task for web search
                    task_result = perform_web_search_and_respond.delay(
                        user_id=request.user.id,
                        query=message,
                        original_message=message,
                        conversation_history=history,
                        search_query=search_query
                    )
                    logger.info(f"Web search task launched with ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Error launching web search task: {e}", exc_info=True)
                    # Fallback: return error message
                    return Response({
                        'reply': 'Erro ao iniciar pesquisa. Por favor tenta novamente.',
                        'action': action,
                        'action_result': {'status': 'error', 'message': str(e)},
                        'search_in_progress': False
                    }, status=status.HTTP_200_OK)
                
                # Return immediately with a message that search is in progress
                return Response({
                    'reply': f'🔍 A pesquisar na internet sobre: "{search_query}"...',
                    'action': action,
                    'action_result': {'status': 'searching', 'message': 'Search in progress', 'task_id': task_result.id},
                    'search_in_progress': True
                }, status=status.HTTP_200_OK)
            
            # Execute other actions synchronously
            action_result = None
            actions_taken = []
            if action:
                tool_name = action.get('tool')
                tool_args = action.get('args', {})
                action_result = dispatch_tool(tool_name, tool_args, request.user)
                actions_taken.append({
                    'tool': tool_name,
                    'args': tool_args,
                    'result': action_result
                })
            
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
                from .services.tts_service import generate_speech
                import base64
                audio_data = generate_speech(clean_response)
                if audio_data:
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    logger.info(f"Audio generated for response, size: {len(audio_data)} bytes")
            except Exception as e:
                logger.warning(f"Error generating audio: {e}")
            
            # Prepare response
            response_data = {
                'reply': clean_response,
                'action': action if action else None,
                'action_result': action_result if action_result else None,
            }
            
            # Publish to Soketi for realtime updates
            pusher_data = {
                'message': clean_response,
                'action': action,
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
                    'via_pusher': True,  # Signal that message is coming via Pusher
                }, status=status.HTTP_200_OK)
            else:
                # Pusher not working - return full response as fallback
                logger.warning("Pusher not available, returning full response in HTTP")
                return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
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

