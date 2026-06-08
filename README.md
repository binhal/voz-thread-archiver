# Novel Translation Toolchain

This repository manages Chinese-to-Vietnamese novel translation workspaces. Each book lives under `library/<book-id>/` with its own source text, extracted Chinese chapters, translated Vietnamese chapters, progress JSON, outputs, and translation harness.

## Layout

```text
library/<book-id>/
  book.yaml
  harness.md
  glossary.tsv
  characters.md
  continuity.md
  source/
  chapters/cn/
  chapters/vi/
  progress/gemini/
  output/
novel_tools/
```

## Commands

```powershell
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools context --book thai-binh-lenh --chapter 563
python -m novel_tools extract --book thai-binh-lenh --chapter 563
python -m novel_tools register --book thai-binh-lenh --chapter 563
python -m novel_tools compile --book thai-binh-lenh
python -m novel_tools unify --book thai-binh-lenh
```

## Workflow

1. Add or select a book workspace under `library/`.
2. Edit that book's `harness.md`, `glossary.tsv`, and `characters.md`.
3. Extract a chapter.
4. Translate into `chapters/vi/chapter_XXXX.txt`.
5. Register the chapter JSON.
6. Compile the book output.
