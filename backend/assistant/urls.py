from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import CustomTokenObtainPairSerializer
from .views import (
    ShoppingItemViewSet,
    AgendaEventViewSet,
    NoteViewSet,
    HomeAssistantConfigViewSet,
    TerminalAPIConfigViewSet,
    ConversationViewSet,
    ChatView,
    ChatStreamView,
    TTSView,
    PushSubscriptionViewSet,
    UserNotificationPreferencesViewSet,
    PusherAuthView,
    DeviceAliasViewSet,
    TodoItemViewSet,
    VideoUploadView,
    VideoUploadChunkView,
    STTAPIView,
    VideoTranscriptionViewSet,
)

router = DefaultRouter()
router.register(r'shopping-items', ShoppingItemViewSet, basename='shopping-item')
router.register(r'agenda', AgendaEventViewSet, basename='agenda-event')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'homeassistant', HomeAssistantConfigViewSet, basename='homeassistant-config')
router.register(r'device-aliases', DeviceAliasViewSet, basename='device-alias')
router.register(r'terminal-api', TerminalAPIConfigViewSet, basename='terminal-api-config')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'push-subscriptions', PushSubscriptionViewSet, basename='push-subscription')
router.register(r'notification-preferences', UserNotificationPreferencesViewSet, basename='notification-preferences')
router.register(r'todos', TodoItemViewSet, basename='todo-item')
router.register(r'video-transcriptions', VideoTranscriptionViewSet, basename='video-transcription')

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

urlpatterns = [
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/stream/', ChatStreamView.as_view(), name='chat_stream'),
    path('tts/', TTSView.as_view(), name='tts'),
    path('pusher/auth/', PusherAuthView.as_view(), name='pusher_auth'),
    path('video/upload/', VideoUploadView.as_view(), name='video_upload'),
    path('video/upload/chunk/', VideoUploadChunkView.as_view(), name='video_upload_chunk'),
    path('stt/health/', STTAPIView.as_view(), name='stt_health'),
    path('stt/jobs/', STTAPIView.as_view(), name='stt_jobs'),
    path('stt/jobs/<str:job_id>/', STTAPIView.as_view(), name='stt_job_status'),
    path('stt/jobs/<str:job_id>/result/', STTAPIView.as_view(), name='stt_job_result'),
    path('stt/jobs/<str:job_id>/events/', STTAPIView.as_view(), name='stt_job_events'),
    path('', include(router.urls)),
]

