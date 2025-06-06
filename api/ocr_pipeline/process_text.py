import re
import json
import Levenshtein

class TextPostProcessor:
    def __init__(self, dict_path="dictionary.txt"):
        self.dict_path = dict_path
        self.store_item_path = dict_path.endswith('.json')
        
        # 파일 타입에 따라 다른 로딩 방식 사용
        if self.store_item_path:
            self._load_json_dictionary()
        else:
            self._load_text_dictionary()
        self.chosung_list = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 
                             'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        self.jungsung_list = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 
                              'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
        self.jongsung_list = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 
                              'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 
                              'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    def _load_text_dictionary(self):
        """텍스트 파일 로딩 - dictionary만 생성"""
        self.stores_dict = {}
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                self.dictionary = [line.strip() for line in f if line.strip()]
        except Exception:
            self.dictionary = []

    def _load_json_dictionary(self):
        """JSON 파일 로딩 - stores_dict만 생성"""
        self.dictionary = []
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stores_dict = data.get("stores", {})
        except Exception:
            self.stores_dict = {}

    def find_best_store_match(self, target, threshold=0.4):
        """가게명에서 가장 유사한 매치 찾기 (JSON 전용)"""
        if not self.store_item_path or not self.stores_dict:
            return None, 0
            
        best_match = None
        max_similarity = 0
        
        for store_name in self.stores_dict.keys():
            if abs(len(target) - len(store_name)) > len(target) / 2:
                continue

            similarity = self.calculate_jamo_similarity(target, store_name)
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = store_name
            elif similarity == max_similarity and len(store_name) > len(best_match or ""):
                best_match = store_name
        
        return (best_match, max_similarity) if max_similarity >= threshold else (None, 0)

    def find_best_item_match(self, target, store_name, threshold=0.4):
        """특정 가게의 메뉴에서 가장 유사한 매치 찾기 (JSON 전용)"""
        if not self.store_item_path or not self.stores_dict or store_name not in self.stores_dict:
            return None, 0
            
        items_list = self.stores_dict[store_name].get("items", [])
        best_match = None
        max_similarity = 0
        
        for item in items_list:
            if abs(len(target) - len(item)) > len(target) / 2:
                continue
            similarity = self.calculate_jamo_similarity(target, item)
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = item
            elif similarity == max_similarity and len(item) > len(best_match or ""):
                best_match = item
        
        return (best_match, max_similarity) if max_similarity >= threshold else (None, 0)
        
    def decompose_hangul(self, text):
        result = []
        for char in text:
            if '가' <= char <= '힣':
                char_code = ord(char) - ord('가')
                cho = char_code // (21 * 28)
                jung = (char_code % (21 * 28)) // 28
                jong = char_code % 28
                result.append(self.chosung_list[cho])
                result.append(self.jungsung_list[jung])
                if jong > 0:
                    result.append(self.jongsung_list[jong])
            else:
                result.append(char)
        return ''.join(result)

    def calculate_jamo_similarity(self, word1, word2):
        jamo1 = self.decompose_hangul(word1)
        jamo2 = self.decompose_hangul(word2)
        if len(word1) <= 2 or len(word2) <= 2:
            similarity = Levenshtein.jaro(jamo1, jamo2)
        else:
            similarity = Levenshtein.ratio(jamo1, jamo2)
        len_diff = len(word2) - len(word1)
        if len_diff < 0:
            similarity += 0.1 * len_diff
        return max(0, min(1, similarity))

    def find_closest_word(self, word, threshold=0.70):
        best_match = None
        max_similarity = 0
        for candidate in self.dictionary:
            if abs(len(word) - len(candidate)) > len(word) / 2:
                continue
            similarity = self.calculate_jamo_similarity(word, candidate)
            if (similarity > max_similarity or 
                (similarity == max_similarity and len(candidate) > len(best_match or ""))):
                max_similarity = similarity
                best_match = candidate
        if max_similarity >= threshold and max_similarity < 1:
            return best_match
        return None

    def normalize_number(self, text):
        if not text:
            return text
        text = re.sub(r'(\d*)O(\d*)', r'\g<1>0\g<2>', text)
        text = re.sub(r'(\d+)O\b', r'\g<1>0', text)
        text = re.sub(r'\bO(\d+)', r'0\g<1>', text)
        text = re.sub(r'(\d*[,\.])O(\d*)', r'\g<1>0\g<2>', text)
        text = re.sub(r'(\d*)U(\d*)', r'\g<1>0\g<2>', text)
        text = re.sub(r'(\d*)E(\d*)', r'\g<1>0\g<2>', text)
        text = re.sub(r'(\d+)E\b', r'\g<1>0', text) 
        text = re.sub(r'\bE(\d+)', r'0\g<1>', text) 
        text = re.sub(r'(\d*[,\.])E(\d*)', r'\g<1>0\g<2>', text)
        text = re.sub(r'(\d*)\((\d*)', r'\1\2', text)
        text = re.sub(r'(\d*)\)(\d*)', r'\1\2', text)
        text = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1,\2', text)
        text = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', text)
        text = re.sub(r'(\d{1,3})\.(\d{3})(?!\d)', r'\1,\2', text)
        def handle_number_spacing(match):
            num1 = match.group(1)
            num2 = match.group(2)
            if len(num1) < 3 and len(num2) == 3:
                return f"{num1},{num2}"
            elif len(num1) == 3 and len(num2) == 3:
                if num2 == "000":
                    return f"{num1},{num2}"
                else:
                    return f"{num1} {num2}"
            else:
                return f"{num1},{num2}"
        text = re.sub(r'(\d{1,3})\s+(\d{3})(?!\d)', handle_number_spacing, text)
        return text

    def clean_text(self, text):
        if not text:
            return text
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'(\d+)l(\d+)', r'\g<1>1\g<2>', text)
        text = re.sub(r'(\d+)I(\d+)', r'\g<1>1\g<2>', text)
        text = re.sub(r';', ':', text)
        text = re.sub(r'([^\s]):([^\s])', r'\1 : \2', text)
        text = re.sub(r'([^\s]):', r'\1 :', text)
        text = re.sub(r':([^\s])', r': \1', text)
        words = text.split()
        for i, word in enumerate(words):
            if not re.search(r'\d', word) and re.search(r'[가-힣]', word) and len(word) > 1:
                closest_word = self.find_closest_word(word)
                if closest_word:
                    words[i] = closest_word
        return ' '.join(words)

    def merge_number_line(self, lines):
        if len(lines) <= 1:
            return lines
        number_pattern = re.compile(r'^[\d,.\s OlI]+$')
        i = 1
        while i < len(lines):
            current_line = lines[i].strip()
            if current_line and number_pattern.match(current_line):
                prev_line = lines[i-1].strip()
                if prev_line:
                    processed_line = re.sub(r'(\d*)O(\d*)', r'\g<1>0\g<2>', current_line)
                    processed_line = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1,\2', processed_line)
                    processed_line = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', processed_line)
                    lines[i-1] = f"{lines[i-1].rstrip()} {processed_line}"
                    lines.pop(i)
                else:
                    i += 1
            else:
                i += 1
        return lines

    def process_lines(self, lines):
        """
        줄 리스트를 받아 후처리된 줄 리스트로 반환
        """
        processed_lines = [self.process_line(line) for line in lines]
        processed_lines = self.merge_number_line(processed_lines)
        print("✅ 텍스트 후처리 완료")
        return processed_lines

    def process_line(self, line):
        if not line.strip():
            return line
        line = self.clean_text(line)
        line = self.normalize_number(line)
        return line

# 사용 예시:
# processor = TextPostProcessor(dict_path="dictionary.txt")
# processed_lines = processor.process_lines(ocr_lines)