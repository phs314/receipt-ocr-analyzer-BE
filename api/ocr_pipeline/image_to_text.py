import easyocr
import re
import numpy as np

# EasyOCR 모델 전역 초기화
reader = easyocr.Reader(['en', 'ko'], gpu=False)

def group_by_y_coordinates(result, threshold=15):
    if not result:
        return []
    def get_y_center(item):
        bbox = item[0]
        y_values = [point[1] for point in bbox]
        return sum(y_values) / len(y_values)
    sorted_result = sorted(result, key=get_y_center)
    groups = []
    current_group = [sorted_result[0]]
    current_y = get_y_center(sorted_result[0])
    for item in sorted_result[1:]:
        y_center = get_y_center(item)
        if abs(y_center - current_y) <= threshold:
            current_group.append(item)
        else:
            groups.append(current_group)
            current_group = [item]
            current_y = y_center
    if current_group:
        groups.append(current_group)
    return groups

def ocr_image_from_memory(np_img):
    """
    단일 numpy 이미지에 대해 줄 단위 텍스트 리스트 반환
    """
    try:
        ocr_result = reader.readtext(np_img)
        grouped = group_by_y_coordinates(ocr_result)
        lines = []
        for group in grouped:
            sorted_group = sorted(group, key=lambda x: min(point[0] for point in x[0]))
            line_text = " ".join(item[1] for item in sorted_group)
            line_text = re.sub(r'\b\d{10,}\b', '', line_text)  # 바코드 등 긴 숫자 제거
            if line_text.strip():
                lines.append(line_text.strip())
        print(f"✅ OCR 완료")
        return lines
    except Exception as e:
        print(f"OCR 실패: {e}")
        return []

# 사용 예시:
# from preprocessing import preprocess_folder_to_memory
# bin_imgs = preprocess_folder_to_memory('media/receipts/')
# text_results = ocr_images_from_memory(bin_imgs)
# for base_name, lines in text_results:
#     print(f"{base_name}:")
#     for line in lines:
#         print(line)