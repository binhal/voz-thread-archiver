import os
import sys
import json
import glob
import re

# Configure stdout to handle UTF-8 printing on Windows
sys.stdout.reconfigure(encoding='utf-8')

def get_latest_chapter():
    # Find all chapter files in chapters/vi/ folder
    files = glob.glob(os.path.join("chapters", "vi", "chapter_*.txt"))
    if not files:
        return None
    
    chapter_numbers = []
    for f in files:
        basename = os.path.basename(f)
        # Match only chapter_XXXX.txt, not chapter_XXXX_cn.txt
        if not basename.endswith("_cn.txt"):
            match = re.search(r'chapter_(\d+)\.txt', basename)
            if match:
                chapter_numbers.append(int(match.group(1)))
            
    if not chapter_numbers:
        return None
    return max(chapter_numbers)

def process_chapter(chapter_num):
    txt_path = os.path.join("chapters", "vi", f"chapter_{chapter_num:04d}.txt")
    cn_path = os.path.join("chapters", "cn", f"chapter_{chapter_num:04d}_cn.txt")
    json_path = os.path.join("progress", "gemini", f"chapter_{chapter_num:04d}.json")

    if not os.path.exists(txt_path):
        print(f"[-] Error: Translated chapter file does not exist: {txt_path}")
        return False

    print(f"[*] Processing Chapter {chapter_num:04d}...")
    
    # 1. Read translated Vietnamese content
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if not lines:
        print(f"[-] Error: {txt_path} is empty!")
        return False

    # The first line is the translated title
    translated_title = lines[0].strip()

    # Rest of the lines are the content
    content_lines = []
    for line in lines[1:]:
        content_lines.append(line)

    # Clean up leading/trailing empty lines of content_lines, but keep internal ones
    while content_lines and content_lines[0].strip() == "":
        content_lines.pop(0)
    while content_lines and content_lines[-1].strip() == "":
        content_lines.pop()

    # 2. Get original Chinese title from the Chinese source file if available
    original_title = f"第{chapter_num}章"  # Default fallback
    if os.path.exists(cn_path):
        try:
            with open(cn_path, "r", encoding="utf-8") as f:
                cn_lines = f.read().splitlines()
            if cn_lines:
                # Find first non-empty line
                for cl in cn_lines:
                    if cl.strip():
                        original_title = cl.strip()
                        break
                print(f"[+] Found original Chinese title: {original_title}")
        except Exception as e:
            print(f"[!] Warning: Could not read Chinese title from {cn_path}: {e}")
    else:
        print(f"[!] Warning: Chinese source chapter not found at {cn_path}. Using fallback title.")

    chapter_data = {
        "index": chapter_num,
        "original_title": original_title,
        "translated_title": translated_title,
        "translated_content": content_lines
    }

    # Create progress/gemini folder if it doesn't exist
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Successfully generated: {json_path}")
    return True

def main():
    if len(sys.argv) > 1:
        try:
            chapter_num = int(sys.argv[1])
        except ValueError:
            print("[-] Error: Chapter number must be an integer!")
            sys.exit(1)
    else:
        # Auto-detect latest chapter
        chapter_num = get_latest_chapter()
        if chapter_num is None:
            print("[-] Error: No translated chapters found in 'chapters/vi/'.")
            sys.exit(1)
        print(f"[*] Auto-detected latest translated chapter: Chapter {chapter_num}")
        confirm = input(f"Do you want to process Chapter {chapter_num}? (Y/n): ").strip().lower()
        if confirm not in ("", "y", "yes"):
            print("[-] Aborted.")
            sys.exit(0)

    process_chapter(chapter_num)

if __name__ == "__main__":
    main()
