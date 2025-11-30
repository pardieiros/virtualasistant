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
)

router = DefaultRouter()
router.register(r'shopping-items', ShoppingItemViewSet, basename='shopping-item')
router.register(r'agenda', AgendaEventViewSet, basename='agenda-event')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'homeassistant', HomeAssistantConfigViewSet, basename='homeassistant-config')

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

urlpatterns = [
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('', include(router.urls)),
]

