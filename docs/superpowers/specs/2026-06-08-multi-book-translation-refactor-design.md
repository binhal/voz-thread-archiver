# Multi-Book Translation Refactor Design

## Goal

Refactor the repository from a single-title translation workspace into a multi-book translation toolchain. Each book should be self-contained, with its own source text, extracted chapters, translated chapters, progress JSON, compiled outputs, and translation harness. Shared mechanics should live in one reusable Python package and one generic agent skill.

The first migration target is the existing `thai-binh-lenh` work. The second title, `luan-hoi-nhac-vien`, should be added as a new book workspace using the existing raw source file.

## Decisions

- Use self-contained book directories under `library/<book-id>/`.
- Use the book id `thai-binh-lenh`.
- Store machine-readable book metadata in `book.yaml`.
- Store book-specific translation guidance in `harness.md`, with optional `glossary.tsv`, `characters.md`, and `continuity.md`.
- Require explicit `--book <book-id>` arguments for all book operations.
- Remove old top-level scripts after equivalent `novel_tools` commands exist. Do not keep compatibility wrappers.
- Keep `skills/novel-translator/SKILL.md` as the generic reusable agent workflow, edited for multi-book use.
- Move only book-specific style rules into each book workspace.

## Repository Shape

```text
library/
  thai-binh-lenh/
    book.yaml
    harness.md
    glossary.tsv
    characters.md
    continuity.md
    source/
      太平令.txt
      太平令.epub
    chapters/
      cn/
      vi/
    progress/
      gemini/
      minimax/
    output/
      thai-binh-lenh.vi.txt
      thai-binh-lenh.vi.epub

  luan-hoi-nhac-vien/
    book.yaml
    harness.md
    glossary.tsv
    characters.md
    continuity.md
    source/
      轮回乐园.txt
    chapters/
      cn/
      vi/
    progress/
      gemini/
    output/

novel_tools/
  __main__.py
  cli.py
  config.py
  paths.py
  chapters.py
  progress.py
  compiler.py
  epub.py
  context.py

tests/
  test_config.py
  test_chapters.py
  test_progress.py
  test_compiler.py
  test_context.py
```

After migration, top-level `books/`, `chapters/`, and `progress/` are removed if no longer needed. The legacy VOZ thread backup files can remain separate from the novel translation refactor.

## Book Configuration

Each book has a `book.yaml` with metadata and paths relative to that book directory.

```yaml
id: thai-binh-lenh
title: "Thái Bình Lệnh"
source_title: "太平令"
author: "Diêm ZK"
language:
  source: zh-CN
  target: vi
chapter:
  start_index: 240
  title_format: "Chương {index}: {title}"
source:
  file: "source/太平令.txt"
outputs:
  txt: "output/thai-binh-lenh.vi.txt"
  epub: "output/thai-binh-lenh.vi.epub"
providers:
  default: gemini
  progress_dir: "progress/gemini"
epub:
  title: "Thái Bình Lệnh (Bản dịch Việt)"
  author: "Diêm ZK"
```

Required fields are `id`, `title`, `source.file`, `chapter.start_index`, `chapter.title_format`, `providers.default`, `providers.progress_dir`, `outputs.txt`, and `outputs.epub`.

## Translation Harness

`skills/novel-translator/SKILL.md` remains the common agent workflow. It should be edited to:

- require a `--book <book-id>` argument or equivalent explicit book selection;
- load the selected book via `python -m novel_tools context --book <book-id> --chapter <chapter>`;
- follow generic workflow steps: extract source, translate, review, register progress JSON, compile, verify, commit when requested;
- keep reusable rules: preserve paragraph structure, remove author notes, avoid translator notes, keep the target file format stable, verify source-to-target coverage, and regenerate JSON after any chapter edit.

Each book's `harness.md` contains only book-specific guidance: tone, terminology, pronouns, character voices, relationship rules, world-specific terms, and exceptions. For `thai-binh-lenh`, this includes guidance for Lý Quan Nhất, Dao Quang, Yến Đại Thanh, Đề Kỵ / Ti Kỵ, and other title-specific conventions.

Optional context files:

```text
glossary.tsv       # source term, target term, note
characters.md      # voices, relationships, aliases
continuity.md      # rolling notes, unresolved terms, prior decisions
```

## CLI Contract

All book operations are explicit:

```powershell
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools extract --book thai-binh-lenh --chapter 563
python -m novel_tools register --book thai-binh-lenh --chapter 563
python -m novel_tools compile --book thai-binh-lenh
python -m novel_tools context --book thai-binh-lenh --chapter 563
python -m novel_tools unify --book thai-binh-lenh
```

Command behavior:

- `list-books`: read `library/*/book.yaml` and display available book ids and titles.
- `inspect`: show source path, chapter counts, progress counts, latest translated chapter, gaps, and output paths.
- `extract`: extract one Chinese chapter from the configured source TXT into `chapters/cn/`.
- `register`: convert `chapters/vi/chapter_XXXX.txt` into `progress/<provider>/chapter_XXXX.json`.
- `compile`: merge configured progress JSON from `chapter.start_index` to the latest available chapter and build TXT/EPUB outputs.
- `context`: print a resolved translation context bundle for an agent, including book metadata, harness, optional glossary, optional characters, optional continuity notes, and source/target chapter paths.
- `unify`: normalize translated titles for one selected book only.

Old scripts are removed once the equivalent commands pass verification:

```text
compile_gemini.py
extract_chapter.py
generate_progress_json.py
translate_novel.py
unify_chapters.py
```

## Engine Boundaries

`novel_tools` contains reusable mechanics only. It must not encode specific book names, character names, or style guidance.

- `__main__.py`: module entry point for `python -m novel_tools`.
- `cli.py`: argument parsing and command routing.
- `config.py`: load and validate `book.yaml`.
- `paths.py`: resolve `library/<book-id>` paths and protect operations from crossing workspace boundaries.
- `chapters.py`: source TXT decoding, chapter splitting, and source chapter extraction.
- `progress.py`: progress JSON read/write, latest chapter detection, gaps, and registration.
- `compiler.py`: merge progress entries into final TXT.
- `epub.py`: package compiled TXT into EPUB.
- `context.py`: assemble the context bundle for the translation agent.

## Migration Plan

1. Create `library/thai-binh-lenh/`.
2. Move current canonical data:
   - `books/太平令.txt` to `library/thai-binh-lenh/source/太平令.txt`
   - `books/太平令.epub` to `library/thai-binh-lenh/source/太平令.epub`
   - `books/太平令_Vietnamese_gemini.txt` to `library/thai-binh-lenh/output/thai-binh-lenh.vi.txt`
   - `books/太平令_Vietnamese_gemini.epub` to `library/thai-binh-lenh/output/thai-binh-lenh.vi.epub`
   - `chapters/cn/*` to `library/thai-binh-lenh/chapters/cn/`
   - `chapters/vi/*` to `library/thai-binh-lenh/chapters/vi/`
   - `progress/gemini/*` to `library/thai-binh-lenh/progress/gemini/`
   - `progress/minimax/*` to `library/thai-binh-lenh/progress/minimax/`
3. Create `library/thai-binh-lenh/book.yaml`.
4. Split translation guidance:
   - keep `skills/novel-translator/SKILL.md` as the generic multi-book workflow;
   - move only `thai-binh-lenh`-specific style rules into `library/thai-binh-lenh/harness.md`;
   - keep reusable process rules in the skill.
5. Create `library/luan-hoi-nhac-vien/`.
6. Move `books/轮回乐园.txt` to `library/luan-hoi-nhac-vien/source/轮回乐园.txt`.
7. Create starter `book.yaml` and `harness.md` for `luan-hoi-nhac-vien`.
8. Remove old top-level `books/`, `chapters/`, and `progress/` after the new CLI passes verification.

Migration must not modify translated chapter content. Move files and update paths only.

## Verification

Automated tests:

- `book.yaml` validation catches missing required fields.
- `list-books` detects multiple book directories.
- chapter extraction writes to the selected book only.
- registration writes the correct progress JSON for the selected book only.
- compilation of one book does not read or write another book.
- context output includes metadata, harness, glossary, characters, continuity, and chapter paths when present.
- migration preserves `thai-binh-lenh` source chapter counts, translated chapter counts, and progress JSON counts.
- existing VOZ backup tests still pass.

Manual verification:

```powershell
python -m unittest
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools compile --book thai-binh-lenh
python -m novel_tools inspect --book luan-hoi-nhac-vien
python -m novel_tools context --book thai-binh-lenh --chapter 563
```

## Non-Goals

- Do not introduce a database, vector store, or generated memory system in this refactor.
- Do not rewrite the translation quality process beyond making it multi-book aware.
- Do not change existing translated chapter content during migration.
- Do not build a GUI.
- Do not preserve old script names as compatibility wrappers.
