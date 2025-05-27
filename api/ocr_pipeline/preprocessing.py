import cv2
import numpy as np
import os

def four_point_transform(image, pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxW, maxH))

def detect_and_crop_mask(org_path):
    """
    마스크 기반으로 영수증을 크롭한 컬러 이미지를 리턴합니다.
    """
    org = cv2.imread(org_path)
    if org is None:
        raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {org_path}")

    base_name = os.path.splitext(os.path.basename(org_path))[0]

    # 1) 그레이스케일 → OTSU 역이진화로 종이 마스크 생성
    gray_full = cv2.cvtColor(org, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(
        gray_full, 0, 255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )

    # 2) 모폴로지 Closing → 틈·구멍 메우기
    h, w = org.shape[:2]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w//20, h//20))
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 3) 면적 50% 이상 컨투어 필터 → 최대 contour 선택
    cnts, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    total_area = w * h
    cnts = [c for c in cnts if cv2.contourArea(c) >= 0.5 * total_area]
    if not cnts:
        raise RuntimeError("유의미한 영수증 영역을 찾지 못했습니다.")
    c = max(cnts, key=cv2.contourArea)

    # 4) 4점 얻기 (approxPolyDP or fallback)
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)
    if len(approx) == 4:
        pts = approx.reshape(4, 2).astype("float32")
    else:
        rect = cv2.minAreaRect(c)
        pts = cv2.boxPoints(rect).astype("float32")

    # 5) 컬러 크롭
    cropped_color = four_point_transform(org, pts)

    return cropped_color, base_name

def binarize_for_ocr(cropped_color):
    """
    크롭된 컬러 이미지를 그레이→OTSU 이진화하여,
    OCR에 최적화된 선명한 흑백 이미지를 리턴합니다.
    """
    gray = cv2.cvtColor(cropped_color, cv2.COLOR_BGR2GRAY)
    _, cropped_bin = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )
    return cropped_bin

def preprocess_image_to_memory(img_path):
    """
    단일 이미지 파일을 전처리하여 binarized_image만 반환
    """
    try:
        cropped_color, _ = detect_and_crop_mask(img_path)
        cropped_bin = binarize_for_ocr(cropped_color)
        print(f"✅ OCR용 이진화 크롭 완료 → {img_path}")
        return cropped_bin
    except Exception as e:
        print(f"❌ {img_path} 처리 실패: {e}")
        return None

# 사용 예시:
# bin_imgs = preprocess_folder_to_memory('media/receipts/')
# for base_name, bin_img in bin_imgs:
#     # bin_img를 바로 다음 단계 함수에 넘기면 됩니다.