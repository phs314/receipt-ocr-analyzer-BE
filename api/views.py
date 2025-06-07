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
import shutil

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
        
            # 단일 파일 대신 getlist를 사용하여 여러 파일 가져오기
            images = request.FILES.getlist('image')
            
            if not images:
                return Response({'error': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

            uploaded_receipts_data = [] # 업로드된 영수증 정보들을 담을 리스트

            for image in images: # 각 이미지 파일을 반복 처리
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
                }
                serializer = ReceiptSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                receipt = serializer.save()
                uploaded_receipts_data.append(serializer.data)
            
            return Response({
                'success': True,
                'message': f'{len(uploaded_receipts_data)}개의 영수증이 성공적으로 업로드되었습니다.',
                'data': uploaded_receipts_data # 여러 영수증 정보를 리스트로 반환
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['POST'],  url_path='clear_all_data')
    def clear_all_data(self, request):
        """
        모든 백엔드 데이터 초기화 API

        ---
        영수증 이미지 파일, 영수증 데이터, 참여자 데이터, 영수증 상세 정보, 정산 데이터를
        모두 초기화합니다. 이 API는 프론트엔드 새로고침 시 자동으로 호출되도록 구현하여
        개발/테스트 환경에서 데이터 누적을 방지하는 데 사용될 수 있습니다.

        ### Responses
        - 200: 성공적으로 초기화됨
            ```json
            {
                "success": true,
                "message": "모든 데이터와 업로드된 영수증 이미지가 성공적으로 초기화되었습니다."
            }
            ```
        - 500: 서버 오류
            ```json
            {
                "success": false,
                "error": "데이터 초기화 중 오류가 발생했습니다: ...에러메시지..."
            }
            ```
        """
        try:
            # 1. 모든 ReceiptInfo 데이터 삭제
            ReceiptInfo.objects.all().delete()
            print("✅ 모든 ReceiptInfo 데이터 삭제 완료.")

            # 2. 모든 Settlement 데이터 삭제
            Settlement.objects.all().delete()
            print("✅ 모든 Settlement 데이터 삭제 완료.")

            # 3. 모든 Receipt 데이터 삭제
            Receipt.objects.all().delete()
            print("✅ 모든 Receipt 데이터 삭제 완료.")
            
            # 4. 모든 Participant 데이터 삭제
            Participant.objects.all().delete()
            print("✅ 모든 Participant 데이터 삭제 완료.")

            # 5. 업로드된 영수증 이미지 파일 삭제
            images_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
            if os.path.exists(images_dir):
                shutil.rmtree(images_dir)
                os.makedirs(images_dir) # 삭제 후 다시 생성
                print(f"✅ 영수증 이미지 디렉토리 초기화 완료: {images_dir}")
            else:
                print(f"⚠️ 영수증 이미지 디렉토리가 존재하지 않습니다: {images_dir}")

            return Response({
                'success': True,
                'message': '모든 데이터와 업로드된 영수증 이미지가 성공적으로 초기화되었습니다.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"❌ 데이터 초기화 중 오류 발생: {str(e)}")
            return Response({
                'success': False,
                'error': f'데이터 초기화 중 오류가 발생했습니다: {str(e)}'
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
            #누적된 이전 분석 결과 모두 삭제
            ReceiptInfo.objects.all().delete()

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

        Request Body 예시:
        {
            "method": "equal" or "item",
            "receipts": [
                {
                    "receipt_id": 1,
                    "items": [
                        {"item_name": "김밥", "participants": ["최희수"]},
                        {"item_name": "라면", "participants": ["하승연", "최희수"]}
                    ]
                },
                {
                    "receipt_id": 2,
                    "items": [
                        {"item_name": "돈까스", "participants": ["하승연"]}
                    ]
                }
            ],
            "participants": ["최희수", "하승연"]  // equal 방식일 경우만 필요
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
            method = request.data.get("method", "equal")
            receipts = request.data.get("receipts", [])
            participant_names = request.data.get("participants", [])

            if not receipts or not method:
                return Response({'error': 'method와 receipts는 필수입니다.'}, status=400)

            overall_result = {}
            used_receipts = []

            for receipt_info in receipts:
                receipt_id = receipt_info.get("receipt_id")
                if not receipt_id:
                    continue

                try:
                    receipt = Receipt.objects.get(id=receipt_id)
                except Receipt.DoesNotExist:
                    continue

                items = receipt.items.all()
                result = {}  # {참여자이름: 금액}

                if method == "equal":
                    if not participant_names:
                        return Response({'error': '1/N 정산은 participants 필수입니다.'}, status=400)

                    total = sum(item.total_amount for item in items)
                    share = total // len(participant_names)
                    for name in participant_names:
                        result[name] = share

                elif method == "item":
                    item_assignments = receipt_info.get("items", [])
                    if not item_assignments:
                        return Response({'error': f'항목별 정산은 items 필수 (receipt_id: {receipt_id})'}, status=400)

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

                for name, amount in result.items():
                    overall_result[name] = overall_result.get(name, 0) + amount

                used_receipts.append(receipt_id)

            # Settlement 저장
            # Settlement는 영수증 1개 기준으로 만들지 않고, 전체 처리 후 한 번에 생성
            # 전체 루프 종료 후 아래처럼 처리
            settlement = Settlement.objects.create(result=overall_result, method=method)
            settlement.receipts.set(Receipt.objects.filter(id__in=used_receipts))
            settlement.participants.set(Participant.objects.filter(name__in=overall_result.keys()))
            
            # 디버그 로그
            print(f"✅ 정산 방식: {method}")
            print(f"✅ 정산 결과: {overall_result}")
            print(f"✅ 포함된 영수증 ID 목록: {used_receipts}")

            return Response({
                "success": True,
                "message": f"{len(used_receipts)}개 영수증 정산 완료",
                "result": overall_result
            })

        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)

def export_settlement_excel(request, settlement_id):
    settlement = Settlement.objects.get(id=settlement_id)
    receipts = settlement.receipts.all()

     # ✅ 로그 출력 (엑셀에 들어갈 데이터 확인용)
    print("✅ 정산 방식:", settlement.method)
    print("✅ 정산 결과:", settlement.result)
    print("✅ 포함된 영수증 ID 목록:", [r.id for r in receipts])
    for receipt in receipts:
        print(f"📄 영수증 ID {receipt.id} - 업로드일: {receipt.upload_time}")
        for info in receipt.items.all():
            print(f"  - 품목: {info.item_name}, 수량: {info.quantity}, 금액: {info.total_amount}")


    wb = Workbook()
    ws = wb.active
    ws.title = "정산 결과"

    for idx, receipt in enumerate(receipts, start=1):
        receipt_infos = receipt.items.all()
        first_info = receipt_infos.first()

        # ✅ 수식 오류 방지를 위해 '=' 제거
        ws.append([f"영수증 {idx}"])
        ws.append(["상호명", first_info.store_name if first_info else "정보 없음"])
        ws.append(["업로드일", receipt.upload_time.strftime('%Y-%m-%d %H:%M:%S')])
        ws.append(["정산 방식", settlement.method])
        ws.append([])

        if settlement.method == "equal":
            total = sum(info.total_amount for info in receipt_infos)
            ws.append(["총 결제금액", total])
            ws.append(["정산 방식", "N분의 1"])
            ws.append([])
        else:
            ws.append(["메뉴명", "수량", "단가", "총액"])
            for info in receipt_infos:
                ws.append([info.item_name, info.quantity, info.unit_price, info.total_amount])
            ws.append([])

    # ✅ 정산 결과
    ws.append(["정산 결과"])
    ws.append(["참여자", "정산 금액"])
    for name, amount in settlement.result.items():
        ws.append([name, amount])

    # ✅ 반환
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"settlement_{settlement_id}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response