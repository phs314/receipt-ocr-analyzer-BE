import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Receipt, Participant, ReceiptInfo, Settlement

class Command(BaseCommand):
    help = '로컬 MySQL 데이터베이스 초기화'

    def handle(self, *args, **options):
        self.stdout.write('🔄 로컬 데이터베이스 초기화 시작...')
        
        # 1. 모든 데이터 삭제 (역순으로 - 외래키 때문에)
        self.stdout.write('🗃️ 데이터베이스 데이터 삭제 중...')
        # Settlement.objects.all().delete()
        ReceiptInfo.objects.all().delete()
        Participant.objects.all().delete()
        Receipt.objects.all().delete()
        
        # 2. 미디어 파일 삭제
        self.stdout.write('📁 업로드된 파일 삭제 중...')
        media_receipts = os.path.join(settings.MEDIA_ROOT, 'receipts')
        if os.path.exists(media_receipts):
            shutil.rmtree(media_receipts)
        os.makedirs(media_receipts, exist_ok=True)
        
        self.stdout.write(
            self.style.SUCCESS('🎉 로컬 데이터베이스 초기화 완료!')
        )