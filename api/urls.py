from django.urls import path
from . import views

urlpatterns = [
    path('receipt/upload/', views.upload_receipt, name='upload_receipt'),
]