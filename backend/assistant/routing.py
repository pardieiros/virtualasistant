"""
WebSocket routing for assistant app.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/voice/$', consumers.VoiceConsumer.as_asgi()),
    re_path(r'^ws/classroom/?$', consumers.ClassroomConsumer.as_asgi()),
]
