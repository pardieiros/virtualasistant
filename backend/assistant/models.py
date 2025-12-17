from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField


class ShoppingItem(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('bought', 'Bought'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_items')
    name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True)
    preferred_store = models.CharField(max_length=100, blank=True)
    alternative_stores = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'preferred_store']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"


class AgendaEvent(models.Model):
    CATEGORY_CHOICES = [
        ('personal', 'Personal'),
        ('work', 'Work'),
        ('health', 'Health'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agenda_events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='personal')
    all_day = models.BooleanField(default=False)
    send_notification = models.BooleanField(default=False, help_text="Send push notification before event starts")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['user', 'start_datetime']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"


class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Note {self.id} ({self.user.username})"


class HomeAssistantConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='homeassistant_config')
    base_url = models.URLField(blank=True)
    long_lived_token = models.CharField(max_length=500, blank=True)
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"HA Config ({self.user.username})"


class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'endpoint']
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Push Subscription ({self.user.username})"


class UserNotificationPreferences(models.Model):
    """User preferences for push notifications."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    agenda_events_enabled = models.BooleanField(default=True, help_text="Enable notifications for agenda events")
    agenda_reminder_minutes = models.IntegerField(default=15, help_text="Minutes before event to send notification")
    shopping_updates_enabled = models.BooleanField(default=False, help_text="Enable notifications for shopping list updates")
    notes_enabled = models.BooleanField(default=True, help_text="Enable notifications for notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Notification Preferences"
        verbose_name_plural = "User Notification Preferences"
    
    def __str__(self):
        return f"Notification Preferences ({self.user.username})"


class Memory(models.Model):
    """
    Stores user memories with vector embeddings for semantic search.
    This allows the assistant to remember past interactions, preferences, and context.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memories')
    content = models.TextField(help_text="The memory content (what happened, what was said, etc.)")
    embedding = VectorField(dimensions=768, null=True, blank=True, help_text="Vector embedding for semantic search")
    memory_type = models.CharField(
        max_length=50,
        choices=[
            ('shopping', 'Shopping'),
            ('agenda', 'Agenda'),
            ('preference', 'Preference'),
            ('fact', 'Fact'),
            ('interaction', 'Interaction'),
            ('other', 'Other'),
        ],
        default='interaction',
        help_text="Type of memory"
    )
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata (e.g., item names, dates, etc.)")
    importance = models.FloatField(default=0.5, help_text="Importance score (0.0 to 1.0) for filtering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'memory_type']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Memory {self.id} ({self.user.username}): {self.content[:50]}..."


class Conversation(models.Model):
    """
    Stores conversation sessions with the assistant.
    Each conversation can have multiple messages and is searchable via embeddings.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True, help_text="Auto-generated or user-provided title")
    embedding = VectorField(dimensions=768, null=True, blank=True, help_text="Vector embedding for semantic search")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Conversation {self.id} ({self.user.username}): {self.title or 'Untitled'}"


class ConversationMessage(models.Model):
    """
    Individual messages within a conversation.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.role} message in conversation {self.conversation.id}"


class TerminalAPIConfig(models.Model):
    """
    Configuration for Terminal API integration (Proxmox host management).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='terminal_api_config')
    api_url = models.URLField(help_text="URL of the Terminal API service (e.g., http://192.168.1.73:8900)")
    api_token = models.CharField(max_length=500, help_text="Bearer token for authentication")
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Terminal API Config ({self.user.username})"


class DeviceAlias(models.Model):
    """
    Custom names/aliases for Home Assistant devices.
    Allows users to assign friendly names to entities for voice commands.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_aliases')
    entity_id = models.CharField(max_length=255, help_text="Home Assistant entity ID (e.g., climate.kitchen)")
    alias = models.CharField(max_length=200, help_text="Friendly name (e.g., 'ar condicionado da cozinha')")
    area = models.CharField(max_length=200, blank=True, help_text="Area/room name (e.g., 'Cozinha')")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'entity_id']
        indexes = [
            models.Index(fields=['user', 'area']),
            models.Index(fields=['user', 'entity_id']),
        ]
    
    def __str__(self):
        return f"{self.alias} ({self.entity_id}) - {self.user.username}"

