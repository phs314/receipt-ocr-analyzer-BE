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
    
class ReceiptInfo(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    store_name = models.CharField(max_length=255)
    item_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.IntegerField()
    total_amount = models.IntegerField()

    def __str__(self):
        return f"{self.item_name} ({self.store_name})"

class Participant(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Settlement(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    participants = models.ManyToManyField(Participant)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement for Receipt {self.receipt.id}"
# 푸쉬가안되네요
