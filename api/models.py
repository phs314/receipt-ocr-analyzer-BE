from django.db import models
from django.utils import timezone

# Create your models here.
class Receipt(models.Model):
    title = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='receipts/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Receipt {self.title} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"