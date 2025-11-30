from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q

from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig
from .serializers import (
    ShoppingItemSerializer,
    AgendaEventSerializer,
    NoteSerializer,
    HomeAssistantConfigSerializer,
    ChatMessageSerializer,
    ChatResponseSerializer,
)
from .services.ollama_client import build_messages, call_ollama, parse_action
from .services.tool_dispatcher import dispatch_tool
from .services.pusher_service import publish_to_user


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
            queryset = queryset.filter(start_datetime__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_datetime__lte=end_date)
        
        return queryset
    
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
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])
        
        # Build messages for Ollama
        messages = build_messages(history, message)
        
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
            
            # Execute action if present
            action_result = None
            if action:
                tool_name = action.get('tool')
                tool_args = action.get('args', {})
                action_result = dispatch_tool(tool_name, tool_args, request.user)
            
            # Prepare response
            response_data = {
                'reply': clean_response,
                'action': action if action else None,
                'action_result': action_result if action_result else None,
            }
            
            # Publish to Soketi for realtime updates
            publish_to_user(
                request.user.id,
                'assistant-message',
                {
                    'message': clean_response,
                    'action': action,
                }
            )
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

