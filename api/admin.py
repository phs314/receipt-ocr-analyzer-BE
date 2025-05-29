from django.contrib import admin
from .models import Participant, Receipt, ReceiptInfo, Settlement

admin.site.register(Participant)
admin.site.register(Receipt)
admin.site.register(ReceiptInfo)
admin.site.register(Settlement)