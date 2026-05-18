import os
import re
import json
import time
import urllib.request
import urllib.parse
from txt_to_epub import build_epub

# Cấu hình mặc định
INPUT_TXT = "太平令.txt"

# Chỉ số chương bắt đầu dịch (Mặc định là 0 để dịch từ đầu truyện. Đặt là 240 để dịch từ chương "Giang hồ của Lý Quan Nhất và Dao Quang")
START_CHAPTER_IDX = 240

# Thư mục lưu và file đầu ra riêng biệt cho từng chế độ dịch để tránh ghi đè/xung đột
# Bạn có thể tự do điều chỉnh các đường dẫn thư mục này theo nhu cầu của mình
# Cấu hình Model Gemini sử dụng (vui lòng sử dụng "gemini-2.5-flash" hoặc "gemini-3-flash-preview" thay vì gemini-1.5-flash đã bị khai tử)
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_PROGRESS_DIR = "translation_progress_gemini"
GEMINI_OUTPUT_TXT = "太平令_Vietnamese_gemini.txt"
GEMINI_OUTPUT_EPUB = "太平令_Vietnamese_gemini.epub"

MINIMAX_PROGRESS_DIR = "translation_progress_minimax"
MINIMAX_OUTPUT_TXT = "太平令_Vietnamese_minimax.txt"
MINIMAX_OUTPUT_EPUB = "太平令_Vietnamese_minimax.epub"

GOOGLE_PROGRESS_DIR = "translation_progress_google"
GOOGLE_OUTPUT_TXT = "太平令_Vietnamese_google.txt"
GOOGLE_OUTPUT_EPUB = "太平令_Vietnamese_google.epub"

# System Prompt tối ưu hóa cho dịch thuật truyện kiếm hiệp/dã sử của chúng ta
SYSTEM_PROMPT = """You are a master literary translator specializing in translating Chinese web novels (wuxia/historical fantasy) into polished, natural, and elegant Vietnamese.
Your task is to translate the following Chinese text into Vietnamese.

CRITICAL RULES FOR "ĐÚNG VĂN PHONG":
1. Balance Hán-Việt and Thuần Việt: Keep martial arts terms, character titles, and epic terminology in elegant Hán-Việt (e.g., 'Pháp Tướng', 'Đề Kỵ', 'thăng đấu tiểu dân', 'long ngâm', 'mi tâm', 'cự long', 'hoài bích có tội', 'đào phạm'). Translate narrative descriptions and common verbs into smooth, natural Vietnamese. Avoid rigid word-for-word translation.
2. Proper Pronouns: Choose pronouns based on age, status, and relationships:
   - Lý Quan Nhất (the protagonist, 13 years old): 'hắn' or 'cậu' in narration. When talking to elders (Trần lão đại phu), he uses 'con/cháu' and refers to them as 'Trần lão' or 'tiền bối'.
   - Trần lão đại phu: 'Trần lão', calling Lý Quan Nhất 'con/cháu'.
   - Đề Kỵ / Ti Kỵ (arrogant government secret police): coarse, proud, using 'gia gia/ông đây' and calling commoners 'đồ chó già' or 'lũ ngu dân'.
   - High-class young scholar: arrogant, uses 'ta/bản quan' and refers to commoners as 'lũ thăng đấu tiểu dân' who should feel 'vinh hạnh' (vinh dự) to serve.
3. Rhythm: Keep sentences dynamic, fast-paced, and poetic. Use standard Vietnamese idioms when appropriate (e.g., 'tai vách mạch rừng' for '人多耳杂').
4. Formatting: Keep the paragraph structure exactly the same. Do not join paragraphs.
5. Output only the translated Vietnamese text. Do not include any notes, introduction, or explanations."""

def split_chapters(txt_path):
    """Đọc file nguồn và tách thành các chương."""
    print(f"[*] Đang phân tích file nguồn '{txt_path}'...")
    content = ""
    for encoding in ['gb18030', 'utf-8-sig', 'utf-8', 'gbk', 'cp936']:
        try:
            with open(txt_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"[+] Đọc thành công bằng bảng mã: {encoding}")
            break
        except UnicodeDecodeError:
            continue
            
    if not content:
        raise ValueError("Không thể giải mã file nguồn bằng các bảng mã thông dụng!")

    lines = content.splitlines()
    chapters = []
    current_title = "Giới thiệu & Tóm tắt"
    current_content = []
    
    chapter_pattern = re.compile(r'^\s*(第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]).*')

    for line in lines:
        striped = line.strip()
        if not striped:
            continue
        
        match = chapter_pattern.match(striped)
        if match and len(striped) < 100:
            if current_content or len(chapters) == 0:
                chapters.append((current_title, current_content))
            current_title = striped
            current_content = []
        else:
            if "ixdzs" not in striped and "爱下电子书" not in striped:
                current_content.append(striped)
                
    if current_content or current_title != "Giới thiệu & Tóm tắt":
        chapters.append((current_title, current_content))
        
    print(f"[+] Phân tích hoàn tất! Tổng cộng phát hiện: {len(chapters)} chương.")
    return chapters

def call_gemini_api(api_key, text):
    """Gọi Gemini API thông qua urllib thuần."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    
    prompt = f"{SYSTEM_PROMPT}\n\nTranslate this text:\n{text}"
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.25
        }
    }
    
    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            res_body = res.read().decode("utf-8")
            res_json = json.loads(res_body)
            translated_text = res_json['candidates'][0]['content']['parts'][0]['text']
            return translated_text.strip()
    except Exception as e:
        print(f"\n[-] Lỗi gọi Gemini API: {e}")
        return None

def call_minimax_api(api_key, text):
    """Gọi MiniMax API (v1/chat/completions) thông qua urllib thuần."""
    url = "https://api.minimax.io/v1/chat/completions"
    
    # Payload chuẩn theo tài liệu của platform.minimax.io (OpenAI-compatible)
    data = {
        "model": "MiniMax-M2.7",  # Dòng model mới và tối ưu nhất của MiniMax
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "temperature": 0.25
    }
    
    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            res_body = res.read().decode("utf-8")
            res_json = json.loads(res_body)
            translated_text = res_json['choices'][0]['message']['content']
            translated_text = re.sub(r'<think>.*?</think>\s*', '', translated_text, flags=re.DOTALL)
            return translated_text.strip()
    except Exception as e:
        print(f"\n[-] Lỗi gọi MiniMax API: {e}")
        return None

def call_google_translate(text):
    """Gọi Google Translate API miễn phí không cần API Key."""
    paragraphs = text.split('\n')
    translated_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            translated_paragraphs.append("")
            continue
            
        # Gọi API dịch của Google
        encoded_text = urllib.parse.quote(para)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=vi&dt=t&q={encoded_text}"
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                res_body = res.read().decode("utf-8")
                res_json = json.loads(res_body)
                sentences = res_json[0]
                translated_para = "".join([s[0] for s in sentences if s[0]])
                translated_paragraphs.append(translated_para)
            time.sleep(0.5) # Delay nhẹ tránh bị chặn IP
        except Exception as e:
            print(f"\n[-] Lỗi Google Translate cho đoạn: {para[:30]}... Lỗi: {e}")
            translated_paragraphs.append(para)
            
    return "\n".join(translated_paragraphs)

def main():
    print("=" * 60)
    print("           HỆ THỐNG DỊCH TIỂU THUYẾT VÕ HIỆP ĐA NĂNG           ")
    print("=" * 60)
    
    if not os.path.exists(INPUT_TXT):
        print(f"[-] Lỗi: Không tìm thấy file '{INPUT_TXT}' trong thư mục!")
        return

    # Chọn chế độ dịch
    print("\nChọn Chế độ dịch:")
    print("1. Dịch thuật Cao cấp bằng Trí tuệ Nhân tạo (Gemini API) - Khuyên dùng 🌟")
    print("2. Dịch thuật Cao cấp bằng Trí tuệ Nhân tạo (MiniMax API) - Đỉnh cao dịch Trung-Việt 🚀")
    print("3. Dịch thô siêu tốc miễn phí (Google Translate)")
    choice = input("Nhập lựa chọn của bạn (1, 2 hoặc 3): ").strip()

    # Thiết lập thư mục lưu tiến trình và file đầu ra dựa trên chế độ dịch được chọn
    if choice == "1":
        progress_dir = GEMINI_PROGRESS_DIR
        output_txt = GEMINI_OUTPUT_TXT
        output_epub = GEMINI_OUTPUT_EPUB
    elif choice == "2":
        progress_dir = MINIMAX_PROGRESS_DIR
        output_txt = MINIMAX_OUTPUT_TXT
        output_epub = MINIMAX_OUTPUT_EPUB
    else:
        progress_dir = GOOGLE_PROGRESS_DIR
        output_txt = GOOGLE_OUTPUT_TXT
        output_epub = GOOGLE_OUTPUT_EPUB

    # Khởi tạo thư mục lưu tiến trình
    os.makedirs(progress_dir, exist_ok=True)
    
    api_key = ""
    if choice == "1":
        api_key = input("Nhập Gemini API Key của bạn: ").strip()
        if not api_key:
            print("[-] API Key không hợp lệ! Vui lòng chạy lại.")
            return
    elif choice == "2":
        api_key = input("Nhập MiniMax API Key của bạn: ").strip()
        if not api_key:
            print("[-] API Key không hợp lệ! Vui lòng chạy lại.")
            return
            
    # Tách chương
    try:
        chapters = split_chapters(INPUT_TXT)
    except Exception as e:
        print(f"[-] Lỗi tách chương: {e}")
        return

    total_chapters = len(chapters)
    
    print("\n[*] Bắt đầu quá trình dịch thuật...")
    for idx, (title, lines) in enumerate(chapters):
        if idx < START_CHAPTER_IDX:
            continue
        ch_file = os.path.join(progress_dir, f"chapter_{idx:04d}.json")
        
        # Nếu chương này đã dịch rồi, tự động bỏ qua (Tính năng Resume)
        if os.path.exists(ch_file):
            continue
            
        print(f"\r[+] Đang dịch [{idx+1}/{total_chapters}]: {title}...", end="", flush=True)
        
        # Gộp các dòng thành một đoạn text lớn để dịch nguyên chương
        raw_text = "\n".join(lines)
        translated_content = ""
        
        if choice in ["1", "2"]:
            # Chế độ AI (Gemini hoặc MiniMax)
            # Nếu chương quá dài, chia đôi để tránh tràn context / giới hạn token
            if len(raw_text) > 4000:
                mid = len(lines) // 2
                part1 = "\n".join(lines[:mid])
                part2 = "\n".join(lines[mid:])
                
                if choice == "1":
                    t_part1 = call_gemini_api(api_key, part1)
                    time.sleep(1.0) # Tránh Rate Limit
                    t_part2 = call_gemini_api(api_key, part2)
                else:
                    t_part1 = call_minimax_api(api_key, part1)
                    time.sleep(1.0) # Tránh Rate Limit
                    t_part2 = call_minimax_api(api_key, part2)
                
                if t_part1 and t_part2:
                    translated_content = t_part1 + "\n" + t_part2
                else:
                    print(f"\n[-] Lỗi khi dịch chương {idx+1}. Sẽ thử lại sau.")
                    continue
            else:
                if choice == "1":
                    translated_content = call_gemini_api(api_key, raw_text)
                    time.sleep(1.0)
                else:
                    translated_content = call_minimax_api(api_key, raw_text)
                    time.sleep(1.0)
                
            if not translated_content:
                print(f"\n[-] Bỏ qua chương {idx+1} do lỗi API. Bạn có thể chạy lại để resume.")
                continue
        else:
            # Chế độ Google Translate miễn phí
            translated_content = call_google_translate(raw_text)

        # Dịch tiêu đề chương
        if choice == "1":
            translated_title = call_gemini_api(api_key, f"Translate only this chapter title to elegant Vietnamese: {title}")
        elif choice == "2":
            translated_title = call_minimax_api(api_key, f"Dịch duy nhất tiêu đề chương sau sang tiếng Việt văn học: {title}")
        else:
            translated_title = call_google_translate(title)
            
        if not translated_title:
            translated_title = title

        # Lưu lại kết quả chương đã dịch dưới dạng JSON để bảo toàn cấu trúc
        chapter_data = {
            "index": idx,
            "original_title": title,
            "translated_title": translated_title,
            "translated_content": translated_content.split('\n')
        }
        
        with open(ch_file, 'w', encoding='utf-8') as f:
            json.dump(chapter_data, f, ensure_ascii=False, indent=2)
            
        # Delay nhẹ bảo vệ API
        time.sleep(0.5)

    print("\n[+] Đã hoàn thành dịch toàn bộ các chương!")
    print("[*] Đang tiến hành hợp nhất và xuất bản thành phẩm...")

    # Hợp nhất thành file TXT bản dịch hoàn chỉnh
    all_translated_lines = []
    for idx in range(total_chapters):
        if idx < START_CHAPTER_IDX:
            continue
        ch_file = os.path.join(progress_dir, f"chapter_{idx:04d}.json")
        if os.path.exists(ch_file):
            with open(ch_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_translated_lines.append(data["translated_title"])
                all_translated_lines.append("")
                all_translated_lines.extend(data["translated_content"])
                all_translated_lines.append("")
                all_translated_lines.append("-" * 50)
                all_translated_lines.append("")

    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(all_translated_lines))
    print(f"[+] Đã xuất file TXT bản dịch Việt: {output_txt}")

    # Đóng gói sang file EPUB bản dịch hoàn chỉnh bằng script txt_to_epub
    print("[*] Đang đóng gói file EPUB mục lục tiếng Việt...")
    try:
        build_epub(output_txt, output_epub, title="Thái Bình Lệnh (Bản dịch Việt)", author="Diêm ZK")
    except Exception as e:
        print(f"[-] Gặp lỗi khi tự đóng gói sang EPUB: {e}")

    print("=" * 60)
    print("🎉 QUÁ TRÌNH HOÀN TẤT MỸ MÃN!")
    print("=" * 60)

if __name__ == "__main__":
    main()
