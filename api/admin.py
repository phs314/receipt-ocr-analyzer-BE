from django.contrib import admin
from .models import Receipt, ReceiptInfo, Participant, Settlement

admin.site.register(Receipt)
admin.site.register(ReceiptInfo)
admin.site.register(Participant)
admin.site.register(Settlement)
