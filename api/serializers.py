from rest_framework import serializers
from .models import Receipt, Participant, ReceiptInfo, Settlement

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

class ReceiptInfoSerializer(serializers.ModelSerializer):
    """영수증 상세 정보(품목) 시리얼라이저"""
    class Meta:
        model = ReceiptInfo
        fields = '__all__'

class SettlementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Settlement
        fields = ['id', 'receipt', 'participants', 'result', 'created_at']