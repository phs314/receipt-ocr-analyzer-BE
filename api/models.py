from django.db import models
from django.utils import timezone

# Create your models here.
class Receipt(models.Model):
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255)
    upload_time = models.DateTimeField(default=timezone.now)
    image_path = models.CharField(max_length=500)
    
    class Meta:
        db_table = 'receipt'  # MySQL 테이블 이름 지정
    
    def __str__(self):
        return f"Receipt {self.file_name} ({self.upload_time.strftime('%Y-%m-%d %H:%M')})"