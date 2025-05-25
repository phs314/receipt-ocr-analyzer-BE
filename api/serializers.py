from rest_framework import serializers
from .models import Receipt
from django.conf import settings

class ReceiptSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Receipt
        fields = '__all__'