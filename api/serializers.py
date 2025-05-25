from rest_framework import serializers
from .models import Receipt, Participant

class ReceiptSerializer(serializers.ModelSerializer):
    """영수증 모델에 대한 시리얼라이저"""
    class Meta:
        model = Receipt
        fields = '__all__'

class ParticipantSerializer(serializers.ModelSerializer):
    """참여자 정보에 대한 시리얼라이저"""
    class Meta:
        model = Participant
        fields = '__all__'