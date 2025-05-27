from django.shortcuts import render

def index(request):
    """메인 페이지를 렌더링합니다."""
    return render(request, 'main/index.html')

def receipt_upload_page(request):
    return render(request, 'main/receipt_test.html')

def settlement_page(request):
    """정산 페이지를 렌더링합니다."""
    return render(request, 'main/settlement.html')