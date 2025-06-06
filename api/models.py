from django.db import models
from django.utils import timezone

# Create your models here.
class Receipt(models.Model):
    """
    영수증 모델
    
    업로드된 영수증 이미지 정보를 저장합니다.
    """
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255)
    upload_time = models.DateTimeField(default=timezone.now)
    image_path = models.CharField(max_length=500)
    
    class Meta:
        db_table = 'receipt'  # MySQL 테이블 이름 지정
    
    def __str__(self):
        return f"Receipt {self.file_name} ({self.upload_time.strftime('%Y-%m-%d %H:%M')})"
    
class ReceiptInfo(models.Model):
    """
    영수증 상세 정보 모델
    
    영수증에서 추출된 각 품목의 상세 정보를 저장합니다.
    """
    id = models.AutoField(primary_key=True)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    store_name = models.CharField(max_length=255, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.IntegerField()
    total_amount = models.IntegerField()
    
    class Meta:
        db_table = 'receipt_info'  # MySQL 테이블 이름 지정
        
    def __str__(self):
        return f"{self.item_name} - {self.quantity}개, {self.total_amount}원 (영수증 ID: {self.id})"

class Participant(models.Model):
    """
    참가자 모델
    
    영수증 분석에 참여하는 참가자 정보를 저장합니다.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)  # varchar 타입으로 이름 저장
    
    class Meta:
        db_table = 'participant'  # MySQL 테이블 이름 지정
        
    def __str__(self):
        return f"Participant {self.id}: {self.name}"

class Settlement(models.Model):
    
    receipt = models.ForeignKey('Receipt', on_delete=models.CASCADE)
    participants = models.ManyToManyField('Participant')
    result = models.JSONField()  # {'홍길동': 3000, '김철수': 3000}
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'settlement'  # MySQL 테이블 이름 지정

    def __str__(self):
        return f"Settlement for Receipt {self.receipt.id} - {self.created_at}"