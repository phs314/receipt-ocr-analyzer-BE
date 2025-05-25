from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.ReceiptViewSet, 'upload')

urlpatterns = [
    path('receipt/', include(router.urls)),  # 영수증 업로드 API
]