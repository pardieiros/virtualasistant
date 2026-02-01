from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig, PushSubscription, UserNotificationPreferences, Conversation, ConversationMessage, TerminalAPIConfig, DeviceAlias, TodoItem, VideoTranscription


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add user_id to token payload
        token['user_id'] = user.id
        return token


class ShoppingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingItem
        fields = [
            'id', 'name', 'quantity', 'category', 'preferred_store',
            'alternative_stores', 'notes', 'priority', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class AgendaEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgendaEvent
        fields = [
            'id', 'title', 'description', 'start_datetime', 'end_datetime',
            'location', 'category', 'all_day', 'send_notification', 'created_at'
        ]
        read_only_fields = ['created_at']


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'text', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class HomeAssistantConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeAssistantConfig
        fields = ['id', 'base_url', 'enabled', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mask the token in responses
        if instance.long_lived_token:
            data['token_configured'] = True
        else:
            data['token_configured'] = False
        return data


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField()
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    conversation_id = serializers.IntegerField(required=False, allow_null=True)


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    action = serializers.DictField(required=False, allow_null=True)


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ['id', 'endpoint', 'p256dh', 'auth', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserNotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreferences
        fields = [
            'agenda_events_enabled', 'agenda_reminder_minutes',
            'shopping_updates_enabled', 'notes_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'message_count', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TerminalAPIConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerminalAPIConfig
        fields = ['id', 'api_url', 'enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mask the token in responses
        if instance.api_token:
            data['token_configured'] = True
        else:
            data['token_configured'] = False
        return data


class DeviceAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceAlias
        fields = ['id', 'entity_id', 'alias', 'area', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TodoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoItem
        fields = [
            'id', 'title', 'description', 'priority', 'status',
            'due_date', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'completed_at']


class VideoTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoTranscription
        fields = [
            'id', 'filename', 'transcription_text', 'language',
            'diarization_enabled', 'speaker_mappings', 'summary',
            'summary_generating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'summary_generating']


class VideoTranscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoTranscription
        fields = [
            'filename', 'transcription_text', 'language',
            'diarization_enabled', 'speaker_mappings'
        ]


class SpeakerMappingUpdateSerializer(serializers.Serializer):
    speaker_mappings = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        help_text="Mapping of speaker IDs (User1, User2, etc.) to actual names"
    )
