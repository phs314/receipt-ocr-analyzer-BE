from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('receipt/', views.receipt_upload_page, name='receipt_upload_page'),  # 추가
]