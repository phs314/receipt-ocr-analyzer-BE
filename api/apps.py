import os
import sys
from django.apps import AppConfig
from django.core.management import call_command

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # runserver 시에만 실행 (migrate, shell 등에서는 실행 안 됨)
        if 'runserver' in sys.argv and not self._is_reloading():
            self.reset_database_on_startup()

    def _is_reloading(self):
        """Django autoreload로 인한 재시작인지 확인"""
        return os.environ.get('RUN_MAIN') == 'true'

    def reset_database_on_startup(self):
        """서버 시작 시 기존 reset_local_db 명령어 실행"""
        try:
            print('🔄 서버 시작 시 데이터베이스 자동 초기화...')
            
            # 기존에 만든 reset_local_db 명령어 실행
            call_command('reset_local_db')
            
        except Exception as e:
            print(f'❌ 자동 초기화 실패: {e}')