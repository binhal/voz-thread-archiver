import os
import json
import sys
from txt_to_epub import build_epub

sys.stdout.reconfigure(encoding='utf-8')

progress_dir = os.path.join("progress", "gemini")
output_txt = os.path.join("books", "太平令_Vietnamese_gemini.txt")
output_epub = os.path.join("books", "太平令_Vietnamese_gemini.epub")

all_translated_lines = []
total_chapters = 300
START_CHAPTER_IDX = 240

chapters_merged = 0
for idx in range(START_CHAPTER_IDX, total_chapters):
    ch_file = os.path.join(progress_dir, f"chapter_{idx:04d}.json")
    if os.path.exists(ch_file):
        print(f"Merging chapter_{idx:04d}.json")
        with open(ch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Add chapter title
            all_translated_lines.append(data["translated_title"])
            all_translated_lines.append("")
            # Add chapter content
            all_translated_lines.extend(data["translated_content"])
            all_translated_lines.append("")
            all_translated_lines.append("-" * 50)
            all_translated_lines.append("")
            chapters_merged += 1

with open(output_txt, 'w', encoding='utf-8') as f:
    f.write("\n".join(all_translated_lines))
print(f"[+] Merged {chapters_merged} chapters. File written to {output_txt}")

print("[*] Building EPUB...")
try:
    build_epub(output_txt, output_epub, title="Thái Bình Lệnh (Bản dịch Việt)", author="Diêm ZK")
    print(f"[+] EPUB successfully built to {output_epub}")
except Exception as e:
    print(f"[-] Error building EPUB: {e}")
