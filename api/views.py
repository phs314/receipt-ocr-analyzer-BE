from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Receipt

# Create your views here.
@api_view(['POST'])
def upload_receipt(request):
    if 'image' not in request.FILES:
        return Response({'error': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    image = request.FILES['image']
    receipt = Receipt.objects.create(image=image)
    
    return Response({
        'id': receipt.title,
        'image_url': receipt.image.url,
        'uploaded_at': receipt.uploaded_at,
        'message': '영수증이 성공적으로 업로드되었습니다.'
    }, status=status.HTTP_201_CREATED)