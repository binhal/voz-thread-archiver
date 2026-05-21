# Voz Thread Archiver & Novel Translator 📚✨

This repository is a premium, lightweight, and structured toolchain designed for translating Chinese web novels (specifically *Thái Bình Lệnh* / 太平令) into elegant, polished Vietnamese chapter-by-chapter, and packaging them into beautifully formatted EPUB e-books.

It supports a hybrid workflow of automatic machine translation (Gemini API) and high-quality manual refinement.

---

## 📂 Workspace Structure

The project has been refactored into a clean and modular directory layout to keep the workspace organized:

```text
voz-thread-archiver/
├── books/                              # Completed book files and source texts
│   ├── 太平令.txt                      # Raw original Chinese source novel
│   ├── 太平令.epub                     # Raw original Chinese EPUB
│   ├── 太平令_Vietnamese_gemini.txt    # Merged Vietnamese plain text compile
│   └── 太平令_Vietnamese_gemini.epub   # Completed Vietnamese EPUB ebook
├── chapters/                           # Individual chapter files
│   ├── cn/                             # Raw Chinese source chapters (e.g., chapter_0251_cn.txt)
│   └── vi/                             # Refined Vietnamese translated chapters (e.g., chapter_0251.txt)
├── progress/                           # Structural JSON tracking files
│   ├── gemini/                         # Gemini translation progress metadata
│   └── minimax/                        # Archived legacy Minimax progress metadata
├── docs/                               # Project documentation & guides
├── txt_to_epub.py                      # Core engine to package text into EPUBs
├── compile_gemini.py                   # Combines JSON progress files into the final book
├── generate_progress_json.py           # Smart tool to convert refined text chapters to JSON
└── translate_novel.py                  # API translation helper script
```

---

## 🛠️ Installation & Setup

1. **Python Requirements**: Ensure you have Python 3.8+ installed.
2. **Install Dependencies**: Install the required library for packaging EPUBs:
   ```bash
   pip install ebooklib
   ```
3. **Configure API Keys (Optional)**: If using `translate_novel.py`, set your Gemini API Key in your environment:
   ```bash
   # On Windows (PowerShell)
   $env:GEMINI_API_KEY="your-api-key"
   ```

---

## 🔄 The Translation & Compilation Workflow

Because batch translations often lack literary nuance, the recommended workflow uses a chapter-by-chapter approach to maintain high quality:

### Step 1: Prep the Chinese Source
Place the raw Chinese chapter text inside the `chapters/cn/` directory:
* Filename format: `chapters/cn/chapter_XXXX_cn.txt` (e.g., `chapters/cn/chapter_0251_cn.txt`).
* The first line of this file should contain the original Chinese chapter title.

### Step 2: Refine the Vietnamese Translation
Read from the Chinese source and write your high-quality, refined Vietnamese translation in the `chapters/vi/` directory:
* Filename format: `chapters/vi/chapter_XXXX.txt` (e.g., `chapters/vi/chapter_0251.txt`).
* **Format Guidelines**:
  * Line 1: The chapter title in Vietnamese (e.g., `Chương 251: Điếu Kình Khách Câu Cá...`).
  * Line 2+: The content paragraphs of the chapter.

### Step 3: Generate the Progress JSON
To register your refined chapter into the compilation database, run:
```bash
python generate_progress_json.py
```
* **Smart Auto-Detect**: Running the script with no arguments automatically scans `chapters/vi/`, finds the latest chapter you just refined, extracts the Chinese title from `chapters/cn/` to link them, and prompts you to confirm.
* **Target Specific Chapter**: You can also target a specific chapter manually:
  ```bash
   python generate_progress_json.py 251
  ```
This generates the structured database entry in `progress/gemini/chapter_XXXX.json`.

### Step 4: Compile the Ebook
Whenever you want to rebuild your complete book with all your latest translated chapters, run:
```bash
python compile_gemini.py
```
This script will:
1. Parse all progress JSONs from `progress/gemini/` sequentially.
2. Generate the complete merged text book in `books/太平令_Vietnamese_gemini.txt`.
3. Package it into a beautifully formatted EPUB e-book in `books/太平令_Vietnamese_gemini.epub`, ready to be dropped into Apple Books, Kindle, Moon+ Reader, or any other e-reader!

---

## 💡 Pro-Tips

* **Dynamic Resiliency**: All compilers support graceful fallbacks. If a chapter file is temporarily missing, the compiler skips it cleanly instead of throwing crashes.
* **Console Safety**: The scripts automatically reconfigure standard output to `UTF-8` to ensure beautiful console logs even on Windows systems with non-ASCII text.
