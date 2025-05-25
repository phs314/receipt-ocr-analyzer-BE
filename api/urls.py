from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

router = DefaultRouter()
router.register('receipt', views.ReceiptViewSet, 'receipt')
router.register('participant', views.ParticipantViewSet, 'participant')

urlpatterns = [
    path('', include(router.urls)),  # 영수증 업로드 API
]