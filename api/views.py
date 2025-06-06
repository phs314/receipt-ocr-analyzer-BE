from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Receipt, Participant, ReceiptInfo, Settlement 
from django.http import HttpResponse
from openpyxl import Workbook
from .serializers import ReceiptSerializer, ParticipantSerializer, ReceiptInfoSerializer, SettlementSerializer
from api.ocr_pipeline.preprocessing import preprocess_image_to_memory
from api.ocr_pipeline.image_to_text import ocr_image_from_memory
from api.ocr_pipeline.process_text import TextPostProcessor
from api.ocr_pipeline.extract_item2 import extract_menu_items_from_lines
import os
import uuid

class ReceiptViewSet(viewsets.ViewSet):
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
        영수증 이미지를 업로드하고 서버에 저장합니다.

        ### Request Body
        - `image`: 영수증 이미지 파일 (필수, JPEG/PNG)

        ### Responses
        - 201: 성공적으로 업로드됨
            ```json
            {
                "success": true,
                "message": "영수증이 성공적으로 업로드되었습니다.",
                "data": { ... }
            }
            ```
        - 400: 잘못된 요청 (이미지 없음 또는 형식 오류)
            ```json
            {
                "error": "이미지 파일이 필요합니다."
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "업로드 중 오류가 발생했습니다: ...에러메시지..."
            }
            ```
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
        
class ParticipantViewSet(viewsets.ViewSet):
    """
    참가자 API ViewSet

    영수증 분석에 참여하는 사용자를 관리합니다.
    """
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['POST'], url_path='join')
    def create_participant(self, request):
        """
        참가자 추가 API

        ---
        새로운 참가자를 추가합니다.

        ### Request Body
        - `name`: 참가자 이름 (필수, 문자열)

        ### Request Example
        ```json
        {
            "name": "홍길동"
        }
        ```

        ### Responses
        - 201: 참가자 추가 성공
            ```json
            {
                "success": true,
                "message": "참가자가 성공적으로 추가되었습니다.",
                "data": {
                    "id": 1,
                    "name": "홍길동"
                }
            }
            ```
        - 400: 잘못된 요청 (이름 누락 또는 형식 오류)
            ```json
            {
                "success": false,
                "error": "이름은 필수입니다."
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "참가자 추가 중 오류가 발생했습니다: ...에러메시지..."
            }
            ```
        """
        try:
            serializer = ParticipantSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            participant = serializer.save()
            
            return Response({
                'success': True,
                'message': '참가자가 성공적으로 추가되었습니다.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'참가자 추가 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['GET'], url_path='members')
    def list_participants(self, request):
        """
        참가자 목록 조회 API

        ---
        등록된 모든 참가자 목록을 조회합니다.

        ### Request Body
        - (body 없음) GET 요청이므로 별도의 body를 받지 않습니다.

        ### Responses
        - 200: 참가자 목록 조회 성공
            ```json
            {
                "success": true,
                "message": "참가자 목록을 성공적으로 조회했습니다.",
                "data": [
                    {
                        "id": 1,
                        "name": "홍길동"
                    },
                    {
                        "id": 2,
                        "name": "김철수"
                    },
                    {
                        "id": 3,
                        "name": "이영희"
                    }
                ]
            }
            ```
        - 200: 참가자가 없는 경우
            ```json
            {
                "success": true,
                "message": "참가자 목록을 성공적으로 조회했습니다.",
                "data": []
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "참가자 목록 조회 중 오류가 발생했습니다: ...에러메시지..."
            }
            ```
        """
        try:
            participants = Participant.objects.all()
            serializer = ParticipantSerializer(participants, many=True)
            
            return Response({
                'success': True,
                'message': '참가자 목록을 성공적으로 조회했습니다.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'참가자 목록 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ReceiptInfoViewSet(viewsets.ViewSet):
    """
    영수증 상세 정보(품목) API ViewSet
    """
    queryset = ReceiptInfo.objects.all()
    serializer_class = ReceiptInfoSerializer

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['get'], url_path='analyze')
    def analyze_receipts(self, request):
        """
        영수증 OCR 분석 및 품목 추출 API

        ---
        업로드된 Receipt 객체의 이미지 각각에 대해 OCR 파이프라인을 실행하고,
        추출된 품목 정보를 ReceiptInfo로 저장 및 직렬화해 반환합니다.

        ### Request Body
        - (body 없음) GET 요청이므로 별도의 body를 받지 않습니다.

        ### Responses
        - 200: 성공, 추출된 품목 리스트 반환
            ```json
            {
                "success": true,
                "message": "영수증 분석이 성공적으로 완료되었습니다.",
                "results": [
                    {
                        "receipt": 1,
                        "store_name": "예시가게",
                        "item_name": "김밥",
                        "quantity": 2,
                        "unit_price": 3000,
                        "total_amount": 6000
                    }
                ]
            }
            ```
        - 400: 분석할 영수증 없음
            ```json
            {
                "success": false,
                "error": "분석할 영수증이 없습니다."
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "분석 중 오류가 발생했습니다: ...에러메시지..."
            }
            ```
        """
        try:
            # Receipt 테이블에서 모든 영수증 객체 불러오기
            receipts = Receipt.objects.all()
            if not receipts.exists():
                return Response({'success': False, 'error': '분석할 영수증이 없습니다.'}, status=400)

            processor = TextPostProcessor(dict_path=os.path.join(settings.BASE_DIR, 'api', 'ocr_pipeline', 'dictionary.txt'))
            serialized_items = []

            for receipt in receipts:
                image_path = os.path.join(settings.MEDIA_ROOT, receipt.image_path)
                if not os.path.exists(image_path):
                    continue  # 이미지 파일이 없으면 건너뜀
                
                print(f"🔎 [{receipt.id}] 이미지 처리 시작: {image_path}")

                # 1. 전처리
                bin_imgs = preprocess_image_to_memory(image_path)

                # 2. OCR
                ocr_results = ocr_image_from_memory(bin_imgs)

                # 3. 후처리
                processed_lines = processor.process_lines(ocr_results)
                
                # 4. 품목 추출
                result = extract_menu_items_from_lines(processed_lines)

                # 5. 가게명/음식명 각각 find_closest_word 적용
                store_name = result.get("store_name", "")
                items = result.get("items") or []  # None이면 빈 리스트로 대체

                for item in items:
                    data = {
                        "receipt": receipt.id,
                        "store_name": store_name,
                        "item_name": item["item_name"],
                        "quantity": item["quantity"],
                        "unit_price": item["unit_price"],
                        "total_amount": item["total_amount"],
                    }
                    serializer = ReceiptInfoSerializer(data=data)
                    serializer.is_valid(raise_exception=True)
                    instance = serializer.save()
                    serialized_items.append(ReceiptInfoSerializer(instance).data)

            return Response({
                'success': True,
                'message': '영수증 분석이 성공적으로 완료되었습니다.',
                'results': serialized_items
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'분석 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SettlementViewSet(viewsets.ViewSet):
    """
    정산 API ViewSet

    영수증 기반으로 참가자들의 금액을 정산합니다.
    """
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate_settlement(self, request):
        """
        정산 계산 API

        ---
        정산 계산을 수행합니다.

        request body 예시:
        {
            "receipt_id": 1,
            "method": "equal" or "item",
            "participants": ["하승연", "최희수"],
            "items": [
                { "item_name": "김밥", "participants": ["최희수"] },
                { "item_name": "라면", "participants": ["하승연", "최희수"] }
            ]
        }

        ### Responses
        - 200: 정산 완료
            ```json
            {
                "success": true,
                "message": "정산이 완료되었습니다.",
                "result": {
                    "참가자1": 5000,
                    "참가자2": 5000
                }
            }
            ```
        - 400: 필수값 누락/항목 부족
            ```json
            {
                "error": "receipt_id와 participants는 필수입니다."
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "...에러메시지..."
            }
            ```
        """
        try:
            receipt_id = request.data.get("receipt_id")
            method = request.data.get("method", "equal")
            participant_names = request.data.get("participants", [])
            item_assignments = request.data.get("items", [])

            if not receipt_id:
                return Response({'error': 'receipt_id는 필수입니다.'}, status=400)

            receipt = Receipt.objects.get(id=receipt_id)
            items = receipt.items.all()  # ReceiptInfo 리스트

            result = {}

            if method == "equal":
                if not participant_names:
                    return Response({'error': '1/N 정산은 participants 필수입니다.'}, status=400)

                total = sum(item.total_amount for item in items)
                share = total // len(participant_names)
                for name in participant_names:
                    result[name] = share

            elif method == "item":
                if not item_assignments:
                    return Response({'error': '항목별 정산은 items 필수입니다.'}, status=400)

                for assignment in item_assignments:
                    item_name = assignment.get("item_name")
                    names = assignment.get("participants", [])
                    matched_items = items.filter(item_name=item_name)

                    if not matched_items.exists():
                        continue

                    for item in matched_items:
                        share = item.total_amount // max(len(names), 1)
                        for name in names:
                            result[name] = result.get(name, 0) + share
            else:
                return Response({'error': 'method는 "equal" 또는 "item"이어야 합니다.'}, status=400)

            # Settlement 저장
            settlement = Settlement.objects.create(receipt=receipt, result=result)
            participants = Participant.objects.filter(name__in=result.keys())
            settlement.participants.set(participants)

            return Response({
                "success": True,
                "message": "정산이 완료되었습니다.",
                "result": result
            })

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500) 
        
def export_settlement_excel(request, settlement_id):
    from datetime import datetime

    settlement = Settlement.objects.get(id=settlement_id)
    receipt = settlement.receipt
    receipt_infos = receipt.items.all()  # related_name='items'로 ReceiptInfo 접근

    wb = Workbook()
    ws = wb.active
    ws.title = "정산 결과"

    # 1. 상호명 및 업로드일
    ws.append(["상호명", receipt_infos.first().store_name if receipt_infos.exists() else "정보 없음"])
    ws.append(["업로드일", receipt.upload_time.strftime('%Y-%m-%d %H:%M:%S')])
    ws.append([])

    # 2. 메뉴 목록
    ws.append(["메뉴명", "수량", "단가", "총액"])
    for info in receipt_infos:
        ws.append([info.item_name, info.quantity, info.unit_price, info.total_amount])
    ws.append([])

    # 3. 정산 결과
    ws.append(["참여자", "정산 금액"])
    for name, amount in settlement.result.items():
        ws.append([name, amount])

    # 응답 반환
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"settlement_{settlement_id}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response