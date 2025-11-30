from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig


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
            'location', 'category', 'all_day', 'created_at'
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


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    action = serializers.DictField(required=False, allow_null=True)
