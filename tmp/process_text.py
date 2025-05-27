import re
import os
import Levenshtein

"""
영수증 텍스트 후처리 모듈
- OCR로 인식된 텍스트에서 오류 수정
- 한글 자모 분해를 통한 유사도 계산
- 메뉴명과 가격 정보 정규화
"""

class TextPostProcessor:
    def __init__(self, dict_path="dictionary.txt"):
        self.dict_path = dict_path
        self.dictionary = self.load_dictionary(dict_path)
        
        # 한글 자모 매핑 테이블
        self.chosung_list = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 
                             'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        self.jungsung_list = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 
                              'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
        self.jongsung_list = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 
                              'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 
                              'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        
        print(f"텍스트 후처리기 초기화 완료")
    
    def load_dictionary(self, dict_path):
        dictionary = []
        try:
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    dictionary = [line.strip() for line in f if line.strip()]  # 공백 줄 제외하고 로드
                print(f"{len(dictionary)}개 단어 로드됨")
            else:
                print(f"사전 파일 없음: {dict_path}")
        except Exception as e:
            print(f"사전 로드 오류: {e}")
        return dictionary
    
    def decompose_hangul(self, text):
        result = []
        for char in text:
            if '가' <= char <= '힣':  # 한글 문자인지 확인
                char_code = ord(char) - ord('가')
                cho = char_code // (21 * 28)  # 초성 인덱스 계산
                jung = (char_code % (21 * 28)) // 28  # 중성 인덱스 계산
                jong = char_code % 28  # 종성 인덱스 계산 (0이면 종성 없음)
                
                result.append(self.chosung_list[cho])
                result.append(self.jungsung_list[jung])
                if jong > 0:  # 종성이 있는 경우만 추가
                    result.append(self.jongsung_list[jong])
            else:
                result.append(char)  # 한글 아닌 문자는 그대로 유지
        return ''.join(result)
    
    def calculate_jamo_similarity(self, word1, word2):
        jamo1 = self.decompose_hangul(word1)  # 첫 번째 단어 자모 분해
        jamo2 = self.decompose_hangul(word2)  # 두 번째 단어 자모 분해
        
        # 짧은 단어는 jaro 알고리즘, 긴 단어는 ratio 알고리즘 사용
        if len(word1) <= 2 or len(word2) <= 2:
            similarity = Levenshtein.jaro(jamo1, jamo2)
        else:
            similarity = Levenshtein.ratio(jamo1, jamo2)
        
        # 길이 차이에 따른 보정 (사전 단어가 짧으면 페널티)
        len_diff = len(word2) - len(word1)
        if len_diff < 0:
            similarity += 0.1 * len_diff
        
        return max(0, min(1, similarity))  # 0~1 범위로 제한
    
    def find_closest_word(self, word, threshold=0.70):
        best_match = None
        max_similarity = 0
            
        for candidate in self.dictionary:
            # 길이 차이가 너무 크면 건너뛰기 (성능 최적화)
            if abs(len(word) - len(candidate)) > len(word) / 2:
                continue
            
            similarity = self.calculate_jamo_similarity(word, candidate)
            
            # 더 높은 유사도이거나, 같은 유사도인데 더 긴 단어 선호
            if (similarity > max_similarity or 
                (similarity == max_similarity and len(candidate) > len(best_match or ""))):
                max_similarity = similarity
                best_match = candidate
        
        # 임계값 이상이고 완전 일치가 아닌 경우에만 교정
        if max_similarity >= threshold and max_similarity < 1:
            print(f"✅ 교정: {word} → {best_match} (유사도: {max_similarity:.4f})")
            return best_match
        return None  # 적합한 단어를 찾지 못함
    
    def normalize_number(self, text):
        if not text:
            return text
        
        # OCR 숫자 오류 패턴 보정
        text = re.sub(r'(\d*)O(\d*)', r'\g<1>0\g<2>', text)  # O → 0
        text = re.sub(r'(\d+)O\b', r'\g<1>0', text)  # 끝자리 O → 0
        text = re.sub(r'\bO(\d+)', r'0\g<1>', text)  # 첫자리 O → 0
        text = re.sub(r'(\d*[,\.])O(\d*)', r'\g<1>0\g<2>', text)  # 콤마/점 뒤 O → 0
        text = re.sub(r'(\d*)U(\d*)', r'\g<1>0\g<2>', text)  # U → 0
        
        text = re.sub(r'(\d*)\((\d*)', r'\1\2', text)  # 숫자 주변 괄호 제거
        text = re.sub(r'(\d*)\)(\d*)', r'\1\2', text)
        
        text = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1,\2', text)  # 콤마 주변 공백 제거
        text = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', text)  # 소수점 주변 공백 제거
        
        text = re.sub(r'(\d{1,3})\.(\d{3})(?!\d)', r'\1,\2', text)  # 천단위 점 → 콤마로 통일
            
        # 숫자 사이 공백 패턴 처리
        def handle_number_spacing(match):
            num1 = match.group(1)
            num2 = match.group(2)
            
            if len(num1) < 3 and len(num2) == 3:  # 1~2자리 + 3자리: 콤마로 변환
                return f"{num1},{num2}"
            elif len(num1) == 3 and len(num2) == 3:
                if num2 == "000":  # 3자리 + 000 패턴: 콤마 사용
                    return f"{num1},{num2}"
                else:
                    return f"{num1} {num2}"  # 기존 공백 유지
            else:
                return f"{num1},{num2}"  # 그 외 패턴: 콤마로 변환
        
        text = re.sub(r'(\d{1,3})\s+(\d{3})(?!\d)', handle_number_spacing, text)
        
        return text
    
    def clean_text(self, text):
        if not text:
            return text
        
        text = re.sub(r'\s+', ' ', text).strip()  # 중복 공백 제거
        
        text = re.sub(r'(\d+)l(\d+)', r'\g<1>1\g<2>', text)  # l → 1 변환
        text = re.sub(r'(\d+)I(\d+)', r'\g<1>1\g<2>', text)  # I → 1 변환
        
        # 시간 표기 정리
        text = re.sub(r';', ':', text)  # 세미콜론 → 콜론
        text = re.sub(r'([^\s]):([^\s])', r'\1 : \2', text)  # 콜론 앞뒤 공백 추가
        text = re.sub(r'([^\s]):', r'\1 :', text)  # 콜론 앞 공백 추가
        text = re.sub(r':([^\s])', r': \1', text)  # 콜론 뒤 공백 추가
        
        # 한글 단어 교정
        words = text.split()
        for i, word in enumerate(words):
            # 숫자가 없고, 한글이 있고, 2글자 이상인 단어만 교정
            if not re.search(r'\d', word) and re.search(r'[가-힣]', word) and len(word) > 1:
                closest_word = self.find_closest_word(word)
                if closest_word:  # 사전에서 유사한 단어를 찾은 경우
                    words[i] = closest_word
        
        return ' '.join(words)
    
    def merge_number_line(self, lines):
        if len(lines) <= 1:
            return lines
        
        number_pattern = re.compile(r'^[\d,.\s OlI]+$')  # 숫자와 특수문자로만 구성된 패턴
        i = 1  # 두 번째 줄부터 검사
        
        while i < len(lines):
            current_line = lines[i].strip()
            
            # 숫자로만 구성된 줄인지 확인
            if current_line and number_pattern.match(current_line):
                prev_line = lines[i-1].strip()
                
                if prev_line:  # 이전 줄이 비어있지 않으면 병합
                    # 현재 줄 숫자 정규화
                    processed_line = re.sub(r'(\d*)O(\d*)', r'\g<1>0\g<2>', current_line)
                    processed_line = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1,\2', processed_line)
                    processed_line = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', processed_line)
                    
                    lines[i-1] = f"{lines[i-1].rstrip()} {processed_line}"  # 이전 줄에 병합
                    lines.pop(i)  # 현재 줄 제거
                else:
                    i += 1  # 이전 줄이 비어있으면 다음으로
            else:
                i += 1  # 숫자 줄이 아니면 다음으로
        
        return lines
    
    def process_text(self, text):
        lines = text.split('\n')  # 줄 단위로 분리
        processed_lines = [self.process_line(line) for line in lines]  # 각 줄 처리
        processed_lines = self.merge_number_line(processed_lines)  # 숫자 줄 병합
        return '\n'.join(processed_lines)  # 처리된 줄 결합
    
    def process_line(self, line):
        if not line.strip():  # 빈 줄 처리
            return line
        
        line = self.clean_text(line)  # 텍스트 정리 및 단어 교정
        line = self.normalize_number(line)  # 숫자 형식 정규화
        
        return line
    
    def process_file(self, input_path, output_path):
        try:
            # 파일 읽기
            with open(input_path, 'r', encoding='utf-8') as file:
                content = file.read()
                content = re.sub(r'^// filepath:.*\n', '', content)  # 주석 제거
                
                print(f"처리 시작: {input_path}")
                processed_text = self.process_text(content)  # 텍스트 처리
                
                # 결과 저장 디렉토리 생성
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(processed_text)
                
                print(f"처리 완료: {output_path}")
                return True
        except Exception as e:
            print(f"처리 오류: {e}")
            return False
    
    def process_directory(self, input_dir, output_dir):
        os.makedirs(output_dir, exist_ok=True)  # 출력 디렉토리 생성
        print(f"{input_dir} 폴더에서 텍스트 로드중...")
        
        processed_count = 0
        total_files = 0
        
        for filename in os.listdir(input_dir):
            if filename.endswith('.txt'):  # txt 파일만 처리
                total_files += 1
                base_filename = os.path.splitext(filename)[0]
                
                # _raw 접미사 처리
                if base_filename.endswith("_raw"):
                    new_base = base_filename[:-4]  # "_raw" 제거
                else:
                    new_base = base_filename
                
                new_filename = f"{new_base}_processed.txt"  # 처리된 파일명
                
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, new_filename)
                
                print(f"\n처리 중: {filename} → {new_filename}")
                if self.process_file(input_path, output_path):
                    processed_count += 1  # 성공 카운트 증가
        
        print(f"처리 완료: {processed_count}/{total_files} 파일 처리됨")
        return processed_count

# 메인 실행
if __name__ == "__main__":
    print("텍스트 후처리기 초기화...")
    
    processor = TextPostProcessor(dict_path="dictionary.txt")  # 후처리기 초기화
    
    OUTPUT_DIR = "output"
    input_dir = os.path.join(OUTPUT_DIR, "ocr_raw_txt")  # 원본 텍스트 폴더
    output_dir = os.path.join(OUTPUT_DIR, "ocr_processed_txt")  # 처리된 텍스트 폴더
    
    print(f"\n{input_dir} 폴더 처리 시작...")
    processor.process_directory(input_dir, output_dir)  # 디렉토리 내 모든 파일 처리