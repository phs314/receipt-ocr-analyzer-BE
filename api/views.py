from django.shortcuts import render, redirect
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Receipt
import os
import uuid
import datetime

@api_view(['GET', 'POST'])
def upload_receipt(request):
    # GET 요청: HTML 페이지 렌더링 (프론트엔드)
    if request.method == 'GET':
        return render(request, 'api/receipt_test.html')
    
    # POST 요청: 이미지 처리 (백엔드)
    try:
        if 'image' not in request.FILES:
            return Response({'error': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        image = request.FILES['image']
        
        # 파일 형식 검증
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if hasattr(image, 'content_type') and image.content_type not in allowed_types:
            return Response({
                'error': '지원되지 않는 파일 형식입니다. JPEG 또는 PNG 파일을 업로드하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 파일 크기 제한 (10MB)
        if image.size > 10 * 1024 * 1024:
            return Response({
                'error': '파일 크기가 너무 큽니다. 10MB 이하로 업로드하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Receipt 모델에 저장
        receipt = Receipt.objects.create(
            file_name=original_filename,
            image_path=file_path
        )
        
        # 이미지 URL 생성
        image_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)
        
        # 응답 반환
        return Response({
            'success': True,
            'id': receipt.id,
            'file_name': receipt.file_name,
            'upload_time': receipt.upload_time.isoformat(),
            'image_url': image_url,
            'message': '영수증이 성공적으로 업로드되었습니다.'
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)