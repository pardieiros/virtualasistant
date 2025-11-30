from django.contrib import admin
from .models import ShoppingItem, AgendaEvent, Note, HomeAssistantConfig, PushSubscription


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'priority', 'preferred_store', 'created_at']
    list_filter = ['status', 'priority', 'preferred_store', 'created_at']
    search_fields = ['name', 'notes']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AgendaEvent)
class AgendaEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_datetime', 'category', 'location']
    list_filter = ['category', 'all_day', 'start_datetime']
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

