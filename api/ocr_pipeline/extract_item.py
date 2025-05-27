import re
import math

def normalize_number(text):
    if not text:
        return text
    text = re.sub(r'O', '0', text)  # O를 0으로 변환 (OCR 오류 보정)
    text = re.sub(r'[,.\s]', '', text)  # 콤마, 점, 공백 제거
    return text

def is_price_format(text):
    return bool(re.match(r'^[\d,]+$', text))  # 숫자와 콤마만 포함하는지 확인

def extract_menu_items_from_lines(lines):
    """
    후처리된 줄 리스트(lines)에서 메뉴 항목 추출하여 JSON 객체 반환
    """
    menu_items = []
    store_name = lines[0].strip() if lines and lines[0].strip() else None
    started_processing_menu = False

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        words = line.split()
        is_menu_pattern = (len(words) >= 3 and
                           is_price_format(words[-1]) and
                           is_price_format(words[-2]))
        if is_menu_pattern:
            if not started_processing_menu:
                started_processing_menu = True
            menu_name = ' '.join(words[:-2])
            price = words[-2]
            amount = words[-1]
            try:
                price_int = int(normalize_number(price))
                amount_int = int(normalize_number(amount))
                if amount_int < price_int:
                    amount_int = price_int
                if price_int > 0:
                    quantity = amount_int / price_int
                    if quantity != int(quantity):
                        quantity = math.ceil(quantity)
                        price_int = int(amount_int / quantity)
                else:
                    quantity = 1
                    price_int = amount_int
                menu_items.append({
                    "item_name": menu_name,
                    "unit_price": price_int,
                    "total_amount": amount_int,
                    "quantity": int(quantity)
                })
            except ValueError:
                pass
        elif started_processing_menu:
            break
    result = {
        "store_name": store_name,
        "items": menu_items,
    }
    print(f"✅ 항목 추출 완료 → {store_name or '상호명 없음'} ({len(menu_items)}개)")
    return result