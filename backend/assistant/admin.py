from django.contrib import admin
from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig, PushSubscription, UserNotificationPreferences, Memory


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'priority', 'preferred_store', 'created_at']
    list_filter = ['status', 'priority', 'preferred_store', 'created_at']
    search_fields = ['name', 'notes']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AgendaEvent)
class AgendaEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_datetime', 'category', 'location', 'send_notification']
    list_filter = ['category', 'all_day', 'send_notification', 'start_datetime']
    search_fields = ['title', 'description', 'location']
    readonly_fields = ['created_at']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'text_preview']
    list_filter = ['created_at']
    search_fields = ['text']
    readonly_fields = ['created_at', 'updated_at']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'


@admin.register(HomeAssistantConfig)
class HomeAssistantConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'enabled', 'base_url', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'endpoint']
    readonly_fields = ['created_at']


@admin.register(UserNotificationPreferences)
class UserNotificationPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'agenda_events_enabled', 'agenda_reminder_minutes', 'shopping_updates_enabled']
    list_filter = ['agenda_events_enabled', 'shopping_updates_enabled']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'memory_type', 'content_preview', 'importance', 'created_at']
    list_filter = ['memory_type', 'created_at']
    search_fields = ['content', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'

