from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Receipt, Participant, ReceiptInfo
from .serializers import ReceiptSerializer, ParticipantSerializer, ReceiptInfoSerializer
from api.ocr_pipeline.preprocessing import preprocess_image_to_memory
from api.ocr_pipeline.image_to_text import ocr_image_from_memory
from api.ocr_pipeline.process_text import TextPostProcessor
from api.ocr_pipeline.extract_item import extract_menu_items_from_lines
import os
import uuid

class ReceiptViewSet(viewsets.ModelViewSet):
    """
    영수증 API ViewSet
    
    영수증 이미지를 관리하고 OCR 분석 기능을 제공합니다.
    """
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['POST'] , url_path='upload')
    def upload_receipt(self, request):
        """
        영수증 이미지 업로드 API
        
        ---
        ## GET
        영수증 업로드 페이지를 렌더링합니다.
        
        ## POST
        영수증 이미지를 업로드하고 처리합니다.
        
        ### Request Body
        - `image`: 영수증 이미지 파일 (필수, JPEG/PNG)
        
        ### Responses
        - 201: 성공적으로 업로드됨
        - 400: 잘못된 요청 (이미지 없음 또는 형식 오류)
        - 500: 서버 오류
        """
        # POST 요청일 경우 업로드 처리
        try:
            if 'image' not in request.FILES:
                return Response({'error': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
            image = request.FILES['image']
            
            # media 디렉터리 확인 및 생성
            images_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
            os.makedirs(images_dir, exist_ok=True)
            
            # 파일명 생성 (고유한 파일명 보장)
            original_filename = image.name
            file_extension = os.path.splitext(original_filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # 파일 저장 경로
            file_path = os.path.join('receipts', unique_filename)
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            
            # 파일 저장
            with open(full_path, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            
            # serializer를 사용해 저장
            data = {
                'file_name': original_filename,
                'image_path': file_path,
                # 필요한 추가 필드가 있다면 여기에 포함
            }
            serializer = ReceiptSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            receipt = serializer.save()
            
            return Response({
                'success': True,
                'message': '영수증이 성공적으로 업로드되었습니다.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ParticipantViewSet(viewsets.ModelViewSet):
    """
    참가자 API ViewSet
    
    영수증 분석에 참여하는 사용자를 관리합니다.
    """
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer

    @method_decorator(csrf_exempt, name='dispatch')
    def create(self, request, *args, **kwargs):
        """참가자 생성 메서드 오버라이드"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant = serializer.save()
        
        return Response({
            'success': True,
            'message': '참가자가 성공적으로 추가되었습니다.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
class ReceiptInfoViewSet(viewsets.ModelViewSet):
    """
    영수증 상세 정보(품목) API ViewSet
    """
    queryset = ReceiptInfo.objects.all()
    serializer_class = ReceiptInfoSerializer

    @action(detail=False, methods=['get'], url_path='analyze')
    def analyze_receipts(self, request):
        """
        GET /api/receiptinfo/analyze/
        tmp 파이프라인 전체 실행 후 JSON 결과를 ReceiptInfoSerializer로 직렬화해 반환
        """
        try:
            receipts = Receipt.objects.all()
            serialized_items = []
            processor = TextPostProcessor(dict_path=os.path.join(settings.BASE_DIR, 'tmp', 'dictionary.txt'))

            for receipt in receipts:
                img_path = os.path.join(settings.MEDIA_ROOT, receipt.image_path)
                base_name = receipt.file_name
                try:
                    # 1. 전처리
                    cropped_bin = preprocess_image_to_memory(img_path)
                    if cropped_bin is None:
                        continue

                    # 2. OCR
                    ocr_results = ocr_image_from_memory(cropped_bin)

                    # 3. 후처리
                    processed_lines = processor.process_lines(ocr_results)

                    # 4. 품목 추출
                    result = extract_menu_items_from_lines(processed_lines)
                    for item in result["items"]:
                        data = {
                            "receipt": receipt.id,
                            "store_name": result["store_name"],
                            "item_name": item["item_name"],
                            "quantity": item["quantity"],
                            "unit_price": item["unit_price"],
                            "total_amount": item["total_amount"],
                        }
                        serializer = ReceiptInfoSerializer(data=data)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
                        serialized_items.append(serializer.data)
                except Exception as e:
                    print(f"❌ {base_name} 처리 실패: {e}")
                    continue

            return Response({'success': True, 'results': serialized_items})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)