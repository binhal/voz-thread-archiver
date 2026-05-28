---
name: novel-translator
description: "Translate Chinese web novels (wuxia/historical fantasy) into polished Vietnamese, register progress, and compile them to EPUB"
---

<objective>
Translate Chinese web novels (specifically wuxia/historical fantasy like "Thái Bình Lệnh" / 太平令) into elegant, high-quality Vietnamese chapter-by-chapter, register progress in the database, and compile/package the translated chapters into a beautifully formatted EPUB e-book.
</objective>

<execution_context>
The skill runs in the workspace context of the translation project (e.g., `voz-thread-archiver`). It relies on:
- A raw text source book in the `books/` directory (e.g., `books/太平令.txt`).
- `chapters/cn/` for raw Chinese chapters (format: `chapter_XXXX_cn.txt`).
- `chapters/vi/` for translated Vietnamese chapters (format: `chapter_XXXX.txt`).
- `progress/gemini/` for tracking database JSONs (format: `chapter_XXXX.json`).
- Helper scripts: `extract_chapter.py`, `generate_progress_json.py`, `compile_gemini.py`, `txt_to_epub.py`.
</execution_context>

<context>
$ARGUMENTS: The target chapter index or number (e.g., "263" or "264") to extract, translate, and register.
If no arguments are provided, perform a scan of `chapters/vi/` to identify the next chapter to translate.
</context>

<process>
Follow these systematic steps to translate a chapter:

### Step 1: Extract the Chinese Source Chapter
Ensure the raw Chinese chapter text is present in the `chapters/cn/` directory.
If it is not present, use the extraction script:
```bash
python extract_chapter.py
```
*Note: Make sure `extract_chapter.py` is configured with the target index to write to `chapters/cn/chapter_XXXX_cn.txt`. The first line of this file must contain the original Chinese chapter title.*

### Step 2: Translate the Chapter
Translate the extracted Chinese text in `chapters/cn/chapter_XXXX_cn.txt` into refined Vietnamese and write the result to `chapters/vi/chapter_XXXX.txt`.

**Critical Translation Guidelines for "Đúng Văn Phong":**
1. **Hán-Việt & Thuần Việt Balance**: Keep martial arts terms, character titles, and epic terminology in elegant Hán-Việt (e.g., 'Pháp Tướng', 'Đề Kỵ', 'thăng đấu tiểu dân', 'long ngâm', 'mi tâm', 'cự long', 'hoài bích có tội', 'đào phạm'). Translate narrative descriptions and common verbs into smooth, natural Vietnamese. Avoid rigid word-for-word translation.
2. **Proper Pronouns**: Choose pronouns based on age, status, and relationships:
   - *Lý Quan Nhất* (protagonist, 13-16 years old): 'hắn' or 'cậu' in narration. When talking to elders (Trần lão đại phu, Mộ Dung Long Đồ), he uses 'con/cháu' and refers to them as 'Trần lão', 'thái ngoại tổ phụ', or 'tiền bối'.
   - *Dao Quang* (silver-haired girl): referred to as 'muội' or 'nàng' by Lý Quan Nhất, calls Mộ Dung Long Đồ 'thái ngoại tổ phụ' or 'ông cố ngoại'.
   - *Yến Đại Thanh* (interior/logistics lead): referred to as 'Yến Đại Thanh' or 'Đại Thanh', uses 'ta' and calls Lý Quan Nhất 'Chúa công' or 'tiểu tử' (in casual settings).
   - *Đề Kỵ / Ti Kỵ* (government secret police): coarse, proud, using 'gia gia/ông đây' and calling commoners 'đồ chó già' or 'lũ ngu dân'.
   - *High-class young scholar / arrogant noble*: arrogant, uses 'ta/bản quan' and refers to commoners as 'lũ thăng đấu tiểu dân' who should feel 'vinh hạnh' (vinh dự) to serve.
3. **Rhythm**: Keep sentences dynamic, fast-paced, and poetic. Use standard Vietnamese idioms when appropriate (e.g., 'tai vách mạch rừng' for '人多耳杂').
4. **Formatting**: Keep the paragraph structure exactly the same. Do not join paragraphs.
5. **Layout in the target file (`chapters/vi/chapter_XXXX.txt`)**:
   - Line 1: Translated Vietnamese Chapter Title. **CRITICAL**: The title must ALWAYS use the continuous global index chapter number (`Chương <global_index>: <Title>`), regardless of whether the original Chinese volume-specific chapter resets (e.g., if the raw title is `第8章` but the file index is `314`, it MUST be translated to `Chương 314: ...`).
   - Line 2: Empty line.
   - Line 3+: Translated content paragraphs. Do not include author notes, introductions, or explanations.

### Step 3: Review and Refine the Translation
Perform a thorough human-like review of the translated chapter (`chapters/vi/chapter_XXXX.txt`) to ensure literary quality and formatting standards:
1. **Source-to-Target Verification**: Compare key sections against `chapters/cn/chapter_XXXX_cn.txt` to ensure no sentences were skipped, truncated, or hallucinated during AI translation.
2. **Pronoun & Consistency Audit**: Crosscheck character dialogues and inner monologues to make sure all pronouns ('ta', 'ngươi', 'hắn', 'cháu', 'tiền bối') perfectly align with the relationship dynamics and social status specified in Step 2.
3. **Fluency & Polish**: Correct any overly literal translations or mechanical Sino-Vietnamese phrasing. Elevate the tone to match premium epic/wuxia literature.
4. **Formatting Check**: Verify that:
   - The first line is the chapter title, followed by an empty line, then the body paragraphs.
   - All author notes (e.g., requesting votes, saying goodnight, unrelated updates) have been completely removed.
   - There are no translator footnotes or parenthetical explanations within the text.

### Step 4: Register Progress JSON
Convert the refined Vietnamese text chapter to a progress JSON to register it in the compilation database:
```bash
python generate_progress_json.py <chapter_number>
```
*Example: `python generate_progress_json.py 263`.*
This creates or updates the JSON file at `progress/gemini/chapter_<chapter_number>.json`.

> [!IMPORTANT]
> **Database Sync Rule:** Whenever you modify, correct, or re-translate any chapter in `chapters/vi/chapter_XXXX.txt` (even for minor spelling or formatting fixes), you **MUST** immediately re-run `python generate_progress_json.py <chapter_number>` to regenerate its JSON file. Otherwise, the compilation database will remain out of sync, and compiled ebooks will still contain the old or duplicate translation.

### Step 5: Compile the Ebook
Compile all translated chapters in the database into the final text file and package it into a beautifully formatted EPUB e-book:
```bash
python compile_gemini.py
```
This automatically merges the chapters starting from index 240, writes [太平令_Vietnamese_gemini.txt](file:///D:/01%20Personal/Projects/voz-thread-archiver/books/%E5%A4%AA%E5%B9%B3%E4%BB%A4_Vietnamese_gemini.txt), and builds the EPUB ebook at [太平令_Vietnamese_gemini.epub](file:///D:/01%20Personal/Projects/voz-thread-archiver/books/%E5%A4%AA%E5%B9%B3%E4%BB%A4_Vietnamese_gemini.epub).

> [!WARNING]
> **Pre-Compilation Check:** Before compiling the ebook, verify that the corresponding `.json` files in `progress/gemini/` for all active chapters are fully up to date and in sync with the files in `chapters/vi/`.

### Step 6: Troubleshooting & Unifying Chapter Numbers
If any chapter numbering inconsistencies ever occur (e.g., a chapter is accidentally numbered using a volume-specific chapter reset from the raw text instead of the continuous global index), you can automatically fix and unify all chapter titles in both `.txt` and `.json` files by running:
```bash
python unify_chapters.py
```
This utility script will scan your translated progress files, clean up any mismatched prefixes, and rewrite the chapter headers to strictly follow `Chương <global_index>: <Title>` starting from chapter 240.

</process>

<notes>
- **API Call Safeguard**: If you use `translate_novel.py` to automate translations via Gemini, ensure that you enter the proper API key and model (recommended `gemini-2.5-flash`). Alternatively, since you are a highly capable AI, you can translate the text directly for ultimate literary accuracy.
- **Console safety**: Ensure standard output is configured to UTF-8 on Windows environments.
- **Ebook packaging**: Ensure `ebooklib` is installed via pip (`pip install ebooklib`) for epub compilation.
</notes>

<security_notes>
- Never pass unvalidated or unescaped user inputs directly to shell commands or file paths.
- All file operations must be restricted to the workspace folder.
</security_notes>
