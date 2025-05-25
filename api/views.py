from django.shortcuts import render, redirect
from django.http import JsonResponse
from rest_framework.decorators import api_view , action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from django.conf import settings
from .models import Receipt
from .serializers import ReceiptSerializer
import os
import uuid
import datetime

class ReceiptViewSet(viewsets.ModelViewSet):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer

    @action(detail=False, methods=['GET', 'POST'] , url_path='upload')
    def upload_receipt(self, request):
        """
        영수증 이미지 업로드 API 및 페이지
        GET: 업로드 페이지 렌더링
        POST: 영수증 이미지 처리
        """
        # GET 요청일 경우 업로드 페이지 렌더링
        if request.method == 'GET':
            return render(request, 'api/receipt_test.html')
        
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
            
            # Receipt 모델에 저장 - MySQL DB에 저장
            receipt = Receipt.objects.create(
                file_name=original_filename,
                image_path=file_path
            )
            
            # 응답 데이터 생성을 위한 시리얼라이저 사용
            response_serializer = ReceiptSerializer(receipt, context={'request': request})
            
            return Response({
                'success': True,
                'message': '영수증이 성공적으로 업로드되었습니다.',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)