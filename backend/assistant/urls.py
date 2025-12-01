from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import CustomTokenObtainPairSerializer
from .views import (
    ShoppingItemViewSet,
    AgendaEventViewSet,
    NoteViewSet,
    HomeAssistantConfigViewSet,
    ChatView,
    TTSView,
    PushSubscriptionViewSet,
    UserNotificationPreferencesViewSet,
    PusherAuthView,
)

router = DefaultRouter()
router.register(r'shopping-items', ShoppingItemViewSet, basename='shopping-item')
router.register(r'agenda', AgendaEventViewSet, basename='agenda-event')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'homeassistant', HomeAssistantConfigViewSet, basename='homeassistant-config')
router.register(r'push-subscriptions', PushSubscriptionViewSet, basename='push-subscription')
router.register(r'notification-preferences', UserNotificationPreferencesViewSet, basename='notification-preferences')

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

urlpatterns = [
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('tts/', TTSView.as_view(), name='tts'),
    path('pusher/auth/', PusherAuthView.as_view(), name='pusher_auth'),
    path('', include(router.urls)),
]

