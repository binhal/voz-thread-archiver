import sys
import re
import os

sys.stdout.reconfigure(encoding='utf-8')

txt_path = os.path.join("books", "太平令.txt")

content = ""
for encoding in ['gb18030', 'utf-8-sig', 'utf-8', 'gbk', 'cp936']:
    try:
        with open(txt_path, 'r', encoding=encoding) as f:
            content = f.read()
        print(f"[+] Decoded with {encoding}")
        break
    except UnicodeDecodeError:
        continue

if not content:
    print("[-] Failed to decode file")
    sys.exit(1)

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

print(f"[+] Total chapters found: {len(chapters)}")
if len(sys.argv) > 1:
    try:
        target_idx = int(sys.argv[1])
    except ValueError:
        print("[-] Error: Chapter index must be an integer!")
        sys.exit(1)
else:
    target_idx = 263

print(f"[*] Target chapter index: {target_idx}")

if len(chapters) > target_idx:
    title, lines = chapters[target_idx]
    print(f"[+] Chapter {target_idx} Title: {title}")
    print(f"[+] Content line count: {len(lines)}")
    os.makedirs(os.path.join("chapters", "cn"), exist_ok=True)
    cn_file = os.path.join("chapters", "cn", f"chapter_{target_idx:04d}_cn.txt")
    with open(cn_file, "w", encoding="utf-8") as f:
        f.write(title + "\n\n" + "\n".join(lines))
    print(f"[+] Successfully wrote {cn_file}")
else:
    print(fr"[-] Index {target_idx} is out of range!")

