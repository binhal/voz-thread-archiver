import os
import sys
import glob
import json
import re

# Configure stdout to handle UTF-8 printing on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Paths relative to the script location
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
VI_DIR = os.path.join(WORKSPACE_DIR, "chapters", "vi")
GEMINI_DIR = os.path.join(WORKSPACE_DIR, "progress", "gemini")

# Hardcoded translations for the Chinese titles
CHINESE_TRANSLATIONS = {
    "李观一和瑶光的江湖": "Giang hồ của Lý Quan Nhất và Dao Quang",
    "婚约？": "Hôn ước?",
    "术士当断绝长生，钓鲸客已见观一": "Thuật sĩ đáng dứt trường sinh, Điếu Kình Khách đã gặp Quan Nhất"
}

def clean_title_prefix(title_str):
    """
    Remove chapter prefixes like 'Chương X:', '第X章', 'Chương X', etc.
    """
    cleaned = re.sub(r'^(?:Chương|第)\s*\d+\s*[章:]\s*', '', title_str, flags=re.IGNORECASE).strip()
    cleaned = cleaned.lstrip(':').strip()
    return cleaned

def unify_chapters():
    print("[*] Bắt đầu đồng bộ số chương theo chỉ số liên tục (Global Index)...")
    
    # Tìm tất cả các file JSON có sẵn trong progress/gemini
    json_files = glob.glob(os.path.join(GEMINI_DIR, "chapter_*.json"))
    if not json_files:
        print("[-] Không tìm thấy chương nào trong thư mục progress/gemini/")
        return
        
    chapter_indices = []
    for f in json_files:
        match = re.search(r'chapter_(\d+)\.json', os.path.basename(f))
        if match:
            chapter_indices.append(int(match.group(1)))
            
    chapter_indices.sort()
    print(f"[*] Phát hiện {len(chapter_indices)} chương từ {chapter_indices[0]} đến {chapter_indices[-1]}")
    
    updated_count = 0
    for idx in chapter_indices:
        # Chỉ đồng bộ từ chương 240 trở đi (phần có phân quyển)
        if idx < 240:
            continue
            
        txt_filename = f"chapter_{idx:04d}.txt"
        txt_path = os.path.join(VI_DIR, txt_filename)
        
        json_filename = f"chapter_{idx:04d}.json"
        json_path = os.path.join(GEMINI_DIR, json_filename)
        
        title_text = None
        
        # 1. Cập nhật file .txt trong chapters/vi
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            
            if lines:
                old_title = lines[0].strip()
                title_text = clean_title_prefix(old_title)
                
                # Bản dịch cho các tiêu đề chữ Hán
                if title_text in CHINESE_TRANSLATIONS:
                    title_text = CHINESE_TRANSLATIONS[title_text]
                
                new_title = f"Chương {idx}: {title_text}"
                lines[0] = new_title
                
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(lines))
            else:
                print(f"[-] Cảnh báo: File {txt_filename} trống!")
        
        # 2. Cập nhật file .json trong progress/gemini
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            old_translated_title = data.get("translated_title", "")
            
            if title_text is None:
                title_text = clean_title_prefix(old_translated_title)
                if title_text in CHINESE_TRANSLATIONS:
                    title_text = CHINESE_TRANSLATIONS[title_text]
            
            new_translated_title = f"Chương {idx}: {title_text}"
            data["translated_title"] = new_translated_title
            data["index"] = idx
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            updated_count += 1
            
    print(f"[+] Đồng bộ hoàn tất cho {updated_count} chương!")

if __name__ == "__main__":
    unify_chapters()
