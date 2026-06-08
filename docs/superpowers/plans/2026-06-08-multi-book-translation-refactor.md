# Multi-Book Translation Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the repo from a single-book translation workspace into an explicit multi-book toolchain with `library/<book-id>/` workspaces and `python -m novel_tools ...` commands.

**Architecture:** Add a small `novel_tools` package that owns reusable mechanics: config loading, path resolution, chapter extraction, progress JSON registration, compilation, EPUB packaging, and context assembly. Book-specific metadata and translation style live under each `library/<book-id>/`; the existing `skills/novel-translator/SKILL.md` becomes a generic workflow that loads per-book context.

**Tech Stack:** Python standard library, `unittest`, `argparse`, `json`, `zipfile`, `pathlib`, `re`. Use a small purpose-built YAML reader/writer for the limited `book.yaml` shape instead of adding dependencies.

---

## File Structure

Create:

- `novel_tools/__init__.py`: package marker.
- `novel_tools/__main__.py`: module entry point for `python -m novel_tools`.
- `novel_tools/cli.py`: `argparse` command router.
- `novel_tools/config.py`: load and validate limited `book.yaml`.
- `novel_tools/paths.py`: resolve repo and book paths safely.
- `novel_tools/chapters.py`: source decoding, chapter splitting, chapter extraction.
- `novel_tools/progress.py`: read/write progress JSON, detect latest/gaps, register translated chapters.
- `novel_tools/compiler.py`: merge progress JSONs into configured TXT output.
- `novel_tools/epub.py`: EPUB builder adapted from `txt_to_epub.py`.
- `novel_tools/context.py`: resolved agent context bundle.
- `tests/test_config.py`
- `tests/test_chapters.py`
- `tests/test_progress.py`
- `tests/test_compiler.py`
- `tests/test_context.py`

Modify:

- `skills/novel-translator/SKILL.md`: make the skill generic and book-explicit.
- `README.md`: document multi-book layout and commands.

Move during migration:

- `books/太平令.txt` -> `library/thai-binh-lenh/source/太平令.txt`
- `books/太平令.epub` -> `library/thai-binh-lenh/source/太平令.epub`
- `books/太平令_Vietnamese_gemini.txt` -> `library/thai-binh-lenh/output/thai-binh-lenh.vi.txt`
- `books/太平令_Vietnamese_gemini.epub` -> `library/thai-binh-lenh/output/thai-binh-lenh.vi.epub`
- `books/轮回乐园.txt` -> `library/luan-hoi-lac-vien/source/轮回乐园.txt`
- `chapters/cn/*` -> `library/thai-binh-lenh/chapters/cn/`
- `chapters/vi/*` -> `library/thai-binh-lenh/chapters/vi/`
- `progress/gemini/*` -> `library/thai-binh-lenh/progress/gemini/`
- `progress/minimax/*` -> `library/thai-binh-lenh/progress/minimax/`

Delete after verification:

- `compile_gemini.py`
- `extract_chapter.py`
- `generate_progress_json.py`
- `translate_novel.py`
- `unify_chapters.py`
- top-level `books/`, `chapters/`, and `progress/` if empty

Keep:

- `voz_thread_backup.py`
- `test_voz_thread_backup.py`
- `txt_to_epub.py` only until `novel_tools/epub.py` is verified, then remove it if no imports remain.

### Limited `book.yaml` Parser Contract

Use a deterministic limited parser in `novel_tools/config.py`; do not add PyYAML. It only needs to support:

- UTF-8 text.
- indentation with two spaces.
- string scalars with or without double quotes.
- integer scalars.
- nested mappings.
- no arrays.

This matches the planned `book.yaml` files and keeps the repo dependency-free.

---

### Task 1: Config and Path Foundation

**Files:**
- Create: `novel_tools/__init__.py`
- Create: `novel_tools/config.py`
- Create: `novel_tools/paths.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing config/path tests**

Create `tests/test_config.py`:

```python
import tempfile
import unittest
from pathlib import Path

from novel_tools.config import BookConfig, ConfigError, load_book_config
from novel_tools.paths import BookPaths, find_library_dir, list_book_ids


BOOK_YAML = '''\
id: sample-book
title: "Sample Book"
source_title: "原书"
author: "Author"
language:
  source: zh-CN
  target: vi
chapter:
  start_index: 10
  title_format: "Chương {index}: {title}"
source:
  file: "source/sample.txt"
outputs:
  txt: "output/sample.vi.txt"
  epub: "output/sample.vi.epub"
providers:
  default: gemini
  progress_dir: "progress/gemini"
epub:
  title: "Sample Book VI"
  author: "Author"
'''


class ConfigTests(unittest.TestCase):
    def test_load_book_config_reads_nested_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")

            config = load_book_config(book_dir)

            self.assertIsInstance(config, BookConfig)
            self.assertEqual(config.id, "sample-book")
            self.assertEqual(config.title, "Sample Book")
            self.assertEqual(config.chapter_start_index, 10)
            self.assertEqual(config.provider, "gemini")
            self.assertEqual(config.progress_dir, Path("progress/gemini"))

    def test_load_book_config_rejects_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "bad-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text("id: bad-book\n", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_book_config(book_dir)

    def test_book_paths_resolve_inside_book_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            config = load_book_config(book_dir)

            paths = BookPaths(book_dir, config)

            self.assertEqual(paths.source_file, book_dir / "source" / "sample.txt")
            self.assertEqual(paths.vi_chapters_dir, book_dir / "chapters" / "vi")
            self.assertEqual(paths.progress_dir, book_dir / "progress" / "gemini")
            self.assertEqual(paths.output_txt, book_dir / "output" / "sample.vi.txt")

    def test_find_library_and_list_books(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library"
            (library / "a").mkdir(parents=True)
            (library / "b").mkdir(parents=True)
            (library / "a" / "book.yaml").write_text(BOOK_YAML.replace("sample-book", "a"), encoding="utf-8")
            (library / "b" / "book.yaml").write_text(BOOK_YAML.replace("sample-book", "b"), encoding="utf-8")

            self.assertEqual(find_library_dir(root), library)
            self.assertEqual(list_book_ids(root), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: import failure because `novel_tools.config` does not exist yet.

- [ ] **Step 3: Implement config and path modules**

Create `novel_tools/__init__.py`:

```python
"""Reusable tools for multi-book novel translation workspaces."""
```

Create `novel_tools/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class BookConfig:
    id: str
    title: str
    source_title: str | None
    author: str | None
    source_file: Path
    output_txt: Path
    output_epub: Path
    provider: str
    progress_dir: Path
    chapter_start_index: int
    chapter_title_format: str
    epub_title: str
    epub_author: str
    source_language: str | None = None
    target_language: str | None = None


def load_book_config(book_dir: Path) -> BookConfig:
    data = parse_limited_yaml((book_dir / "book.yaml").read_text(encoding="utf-8"))
    required = [
        ("id",),
        ("title",),
        ("source", "file"),
        ("outputs", "txt"),
        ("outputs", "epub"),
        ("providers", "default"),
        ("providers", "progress_dir"),
        ("chapter", "start_index"),
        ("chapter", "title_format"),
    ]
    for path in required:
        if _get(data, path) is None:
            raise ConfigError(f"Missing required book.yaml field: {'.'.join(path)}")

    title = str(_get(data, ("title",)))
    author = _optional_str(_get(data, ("author",)))
    return BookConfig(
        id=str(_get(data, ("id",))),
        title=title,
        source_title=_optional_str(_get(data, ("source_title",))),
        author=author,
        source_file=Path(str(_get(data, ("source", "file")))),
        output_txt=Path(str(_get(data, ("outputs", "txt")))),
        output_epub=Path(str(_get(data, ("outputs", "epub")))),
        provider=str(_get(data, ("providers", "default"))),
        progress_dir=Path(str(_get(data, ("providers", "progress_dir")))),
        chapter_start_index=int(_get(data, ("chapter", "start_index"))),
        chapter_title_format=str(_get(data, ("chapter", "title_format"))),
        epub_title=str(_get(data, ("epub", "title")) or title),
        epub_author=str(_get(data, ("epub", "author")) or author or "Unknown"),
        source_language=_optional_str(_get(data, ("language", "source"))),
        target_language=_optional_str(_get(data, ("language", "target"))),
    )


def parse_limited_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise ConfigError(f"Invalid indentation on line {line_number}")
        stripped = raw_line.strip()
        if ":" not in stripped:
            raise ConfigError(f"Expected key/value on line {line_number}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConfigError(f"Invalid nesting on line {line_number}")
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> str | int:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)
```

Create `novel_tools/paths.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import BookConfig, ConfigError


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists() or (path / "README.md").exists():
            return path
    return current


def find_library_dir(root: Path | None = None) -> Path:
    return (root or find_repo_root()) / "library"


def list_book_ids(root: Path | None = None) -> list[str]:
    library = find_library_dir(root)
    if not library.exists():
        return []
    return sorted(
        path.name for path in library.iterdir()
        if path.is_dir() and (path / "book.yaml").exists()
    )


def book_dir_for_id(book_id: str, root: Path | None = None) -> Path:
    library = find_library_dir(root)
    book_dir = (library / book_id).resolve()
    library_resolved = library.resolve()
    if library_resolved not in [book_dir, *book_dir.parents]:
        raise ConfigError(f"Book path escapes library: {book_id}")
    return book_dir


@dataclass(frozen=True)
class BookPaths:
    book_dir: Path
    config: BookConfig

    @property
    def source_file(self) -> Path:
        return self._resolve(self.config.source_file)

    @property
    def cn_chapters_dir(self) -> Path:
        return self.book_dir / "chapters" / "cn"

    @property
    def vi_chapters_dir(self) -> Path:
        return self.book_dir / "chapters" / "vi"

    @property
    def progress_dir(self) -> Path:
        return self._resolve(self.config.progress_dir)

    @property
    def output_txt(self) -> Path:
        return self._resolve(self.config.output_txt)

    @property
    def output_epub(self) -> Path:
        return self._resolve(self.config.output_epub)

    def cn_chapter_file(self, chapter: int) -> Path:
        return self.cn_chapters_dir / f"chapter_{chapter:04d}_cn.txt"

    def vi_chapter_file(self, chapter: int) -> Path:
        return self.vi_chapters_dir / f"chapter_{chapter:04d}.txt"

    def progress_file(self, chapter: int) -> Path:
        return self.progress_dir / f"chapter_{chapter:04d}.json"

    def _resolve(self, relative: Path) -> Path:
        path = (self.book_dir / relative).resolve()
        book_resolved = self.book_dir.resolve()
        if book_resolved not in [path, *path.parents]:
            raise ConfigError(f"Configured path escapes book directory: {relative}")
        return path
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add novel_tools/__init__.py novel_tools/config.py novel_tools/paths.py tests/test_config.py
git commit -m "feat: add book config and path resolution"
```

---

### Task 2: CLI Skeleton, Book Listing, and Inspection

**Files:**
- Create: `novel_tools/__main__.py`
- Create: `novel_tools/cli.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `tests/test_config.py`:

```python
from io import StringIO
from unittest.mock import patch

from novel_tools.cli import main
```

Add methods inside `ConfigTests`:

```python
    def test_cli_list_books_prints_book_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                out = StringIO()
                code = main(["list-books"], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("sample-book", out.getvalue())
            self.assertIn("Sample Book", out.getvalue())

    def test_cli_inspect_prints_counts_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "chapters" / "cn").mkdir(parents=True)
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "progress" / "gemini").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text("Chương 10: A\n\nBody", encoding="utf-8")
            (book_dir / "progress" / "gemini" / "chapter_0010.json").write_text("{}", encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                out = StringIO()
                code = main(["inspect", "--book", "sample-book"], stdout=out)
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("Book: sample-book", text)
            self.assertIn("Vietnamese chapters: 1", text)
            self.assertIn("Progress entries: 1", text)
            self.assertIn("output/sample.vi.txt", text)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: import failure for `novel_tools.cli`.

- [ ] **Step 3: Implement CLI skeleton**

Create `novel_tools/__main__.py`:

```python
from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `novel_tools/cli.py`:

```python
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TextIO

from .config import load_book_config
from .paths import BookPaths, book_dir_for_id, find_repo_root, list_book_ids


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    out = stdout or sys.stdout
    parser = argparse.ArgumentParser(prog="novel_tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-books")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--book", required=True)
    args = parser.parse_args(argv)

    root = find_repo_root()
    if args.command == "list-books":
        return _list_books(root, out)
    if args.command == "inspect":
        return _inspect(root, args.book, out)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _list_books(root: Path, out: TextIO) -> int:
    for book_id in list_book_ids(root):
        book_dir = book_dir_for_id(book_id, root)
        config = load_book_config(book_dir)
        print(f"{config.id}\t{config.title}", file=out)
    return 0


def _inspect(root: Path, book_id: str, out: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    cn_count = _count_matching(paths.cn_chapters_dir, r"chapter_\d{4}_cn\.txt")
    vi_count = _count_matching(paths.vi_chapters_dir, r"chapter_\d{4}\.txt")
    progress_count = _count_matching(paths.progress_dir, r"chapter_\d{4}\.json")
    print(f"Book: {config.id}", file=out)
    print(f"Title: {config.title}", file=out)
    print(f"Source: {config.source_file}", file=out)
    print(f"Chinese chapters: {cn_count}", file=out)
    print(f"Vietnamese chapters: {vi_count}", file=out)
    print(f"Progress entries: {progress_count}", file=out)
    print(f"Output TXT: {config.output_txt}", file=out)
    print(f"Output EPUB: {config.output_epub}", file=out)
    return 0


def _count_matching(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    regex = re.compile(pattern)
    return sum(1 for path in directory.iterdir() if path.is_file() and regex.fullmatch(path.name))
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add novel_tools/__main__.py novel_tools/cli.py tests/test_config.py
git commit -m "feat: add novel tools CLI skeleton"
```

---

### Task 3: Chapter Splitting and Extraction

**Files:**
- Create: `novel_tools/chapters.py`
- Create: `tests/test_chapters.py`
- Modify: `novel_tools/cli.py`

- [ ] **Step 1: Write failing chapter tests**

Create `tests/test_chapters.py`:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novel_tools.chapters import Chapter, extract_chapter, split_chapters
from novel_tools.cli import main
from tests.test_config import BOOK_YAML


SOURCE_TEXT = """前言
这是介绍。
第1章 第一章标题
第一章内容一。
第一章内容二。
第2章 第二章标题
第二章内容。
"""


class ChapterTests(unittest.TestCase):
    def test_split_chapters_detects_chinese_chapter_titles(self):
        chapters = split_chapters(SOURCE_TEXT)

        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].title, "Giới thiệu & Tóm tắt")
        self.assertEqual(chapters[1].index, 1)
        self.assertEqual(chapters[1].title, "第1章 第一章标题")
        self.assertEqual(chapters[1].lines, ["第一章内容一。", "第一章内容二。"])

    def test_extract_chapter_writes_selected_book_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "source").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "source" / "sample.txt").write_text(SOURCE_TEXT, encoding="utf-8")

            written = extract_chapter(book_dir, 1)

            self.assertEqual(written, book_dir / "chapters" / "cn" / "chapter_0001_cn.txt")
            self.assertIn("第1章 第一章标题", written.read_text(encoding="utf-8"))
            self.assertIn("第一章内容一。", written.read_text(encoding="utf-8"))

    def test_cli_extract_uses_book_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "source").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "source" / "sample.txt").write_text(SOURCE_TEXT, encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["extract", "--book", "sample-book", "--chapter", "2"])

            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "chapters" / "cn" / "chapter_0002_cn.txt").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_chapters
```

Expected: import failure for `novel_tools.chapters` or unknown CLI command `extract`.

- [ ] **Step 3: Implement chapter module**

Create `novel_tools/chapters.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigError, load_book_config
from .paths import BookPaths


ENCODINGS = ("gb18030", "utf-8-sig", "utf-8", "gbk", "cp936")
CHAPTER_PATTERN = re.compile(r"^\s*(第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]).*")


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    lines: list[str]


def read_text_with_fallback(path: Path) -> str:
    for encoding in ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ConfigError(f"Could not decode text file: {path}")


def split_chapters(content: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    current_title = "Giới thiệu & Tóm tắt"
    current_lines: list[str] = []
    current_index = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = CHAPTER_PATTERN.match(stripped)
        if match and len(stripped) < 100:
            if current_lines or not chapters:
                chapters.append(Chapter(current_index, current_title, current_lines))
            current_index = len(chapters)
            current_title = stripped
            current_lines = []
        elif "ixdzs" not in stripped and "爱下电子书" not in stripped:
            current_lines.append(stripped)
    if current_lines or current_title != "Giới thiệu & Tóm tắt":
        chapters.append(Chapter(current_index, current_title, current_lines))
    return chapters


def extract_chapter(book_dir: Path, chapter_index: int) -> Path:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    content = read_text_with_fallback(paths.source_file)
    chapters = split_chapters(content)
    if chapter_index < 0 or chapter_index >= len(chapters):
        raise ConfigError(f"Chapter index {chapter_index} is out of range 0..{len(chapters) - 1}")
    chapter = chapters[chapter_index]
    output = paths.cn_chapter_file(chapter_index)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(chapter.title + "\n\n" + "\n".join(chapter.lines), encoding="utf-8")
    return output
```

- [ ] **Step 4: Add `extract` command to CLI**

Modify `novel_tools/cli.py`:

```python
from .chapters import extract_chapter
```

Add parser setup after `inspect_parser`:

```python
    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--book", required=True)
    extract_parser.add_argument("--chapter", required=True, type=int)
```

Add command branch before `parser.error`:

```python
    if args.command == "extract":
        book_dir = book_dir_for_id(args.book, root)
        path = extract_chapter(book_dir, args.chapter)
        print(f"Wrote {path}", file=out)
        return 0
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_chapters tests.test_config
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add novel_tools/chapters.py novel_tools/cli.py tests/test_chapters.py
git commit -m "feat: add book-scoped chapter extraction"
```

---

### Task 4: Progress Registration and Gap Detection

**Files:**
- Create: `novel_tools/progress.py`
- Create: `tests/test_progress.py`
- Modify: `novel_tools/cli.py`

- [ ] **Step 1: Write failing progress tests**

Create `tests/test_progress.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.progress import find_indices, register_chapter
from tests.test_config import BOOK_YAML


class ProgressTests(unittest.TestCase):
    def test_register_chapter_writes_progress_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "chapters" / "cn").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text(
                "Chương 10: Tiêu đề\n\nDòng một.\nDòng hai.", encoding="utf-8"
            )
            (book_dir / "chapters" / "cn" / "chapter_0010_cn.txt").write_text(
                "第10章 原题\n\n中文内容", encoding="utf-8"
            )

            output = register_chapter(book_dir, 10)

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["index"], 10)
            self.assertEqual(data["original_title"], "第10章 原题")
            self.assertEqual(data["translated_title"], "Chương 10: Tiêu đề")
            self.assertEqual(data["translated_content"], ["Dòng một.", "Dòng hai."])

    def test_find_indices_returns_sorted_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "chapter_0012.json").write_text("{}", encoding="utf-8")
            (directory / "chapter_0010.json").write_text("{}", encoding="utf-8")
            self.assertEqual(find_indices(directory, ".json"), [10, 12])

    def test_cli_register_uses_selected_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text(
                "Chương 10: Tiêu đề\n\nDòng một.", encoding="utf-8"
            )
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["register", "--book", "sample-book", "--chapter", "10"])
            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "progress" / "gemini" / "chapter_0010.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_progress
```

Expected: import failure for `novel_tools.progress` or unknown CLI command `register`.

- [ ] **Step 3: Implement progress module**

Create `novel_tools/progress.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import ConfigError, load_book_config
from .paths import BookPaths


def find_indices(directory: Path, suffix: str) -> list[int]:
    if not directory.exists():
        return []
    pattern = re.compile(r"chapter_(\d{4})" + re.escape(suffix) + r"$")
    indices: list[int] = []
    for path in directory.iterdir():
        match = pattern.fullmatch(path.name)
        if match:
            indices.append(int(match.group(1)))
    return sorted(indices)


def register_chapter(book_dir: Path, chapter_index: int) -> Path:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    vi_path = paths.vi_chapter_file(chapter_index)
    cn_path = paths.cn_chapter_file(chapter_index)
    if not vi_path.exists():
        raise ConfigError(f"Translated chapter does not exist: {vi_path}")
    vi_lines = vi_path.read_text(encoding="utf-8").splitlines()
    if not vi_lines:
        raise ConfigError(f"Translated chapter is empty: {vi_path}")
    translated_title = vi_lines[0].strip()
    content_lines = vi_lines[1:]
    while content_lines and not content_lines[0].strip():
        content_lines.pop(0)
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()
    original_title = f"第{chapter_index}章"
    if cn_path.exists():
        for line in cn_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                original_title = line.strip()
                break
    data = {
        "index": chapter_index,
        "original_title": original_title,
        "translated_title": translated_title,
        "translated_content": content_lines,
    }
    output = paths.progress_file(chapter_index)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def latest_index(directory: Path, suffix: str) -> int | None:
    indices = find_indices(directory, suffix)
    return indices[-1] if indices else None


def missing_indices(indices: list[int], start: int, end: int) -> list[int]:
    existing = set(indices)
    return [idx for idx in range(start, end + 1) if idx not in existing]
```

- [ ] **Step 4: Add `register` command and richer inspect**

Modify imports in `novel_tools/cli.py`:

```python
from .progress import find_indices, latest_index, missing_indices, register_chapter
```

Add parser:

```python
    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--book", required=True)
    register_parser.add_argument("--chapter", required=True, type=int)
```

Add command branch:

```python
    if args.command == "register":
        book_dir = book_dir_for_id(args.book, root)
        path = register_chapter(book_dir, args.chapter)
        print(f"Wrote {path}", file=out)
        return 0
```

Update `_inspect` to include latest/gaps:

```python
    vi_indices = find_indices(paths.vi_chapters_dir, ".txt")
    progress_indices = find_indices(paths.progress_dir, ".json")
    latest_vi = vi_indices[-1] if vi_indices else None
    latest_progress = progress_indices[-1] if progress_indices else None
    gap_end = latest_vi if latest_vi is not None else config.chapter_start_index - 1
    gaps = missing_indices(progress_indices, config.chapter_start_index, gap_end) if gap_end >= config.chapter_start_index else []
    print(f"Latest Vietnamese chapter: {latest_vi if latest_vi is not None else 'none'}", file=out)
    print(f"Latest progress chapter: {latest_progress if latest_progress is not None else 'none'}", file=out)
    print(f"Progress gaps: {', '.join(str(gap) for gap in gaps[:20]) if gaps else 'none'}", file=out)
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_progress tests.test_config tests.test_chapters
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add novel_tools/progress.py novel_tools/cli.py tests/test_progress.py
git commit -m "feat: add book-scoped progress registration"
```

---

### Task 5: Compilation and EPUB Packaging

**Files:**
- Create: `novel_tools/compiler.py`
- Create: `novel_tools/epub.py`
- Create: `tests/test_compiler.py`
- Modify: `novel_tools/cli.py`

- [ ] **Step 1: Write failing compiler tests**

Create `tests/test_compiler.py`:

```python
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.compiler import compile_book
from tests.test_config import BOOK_YAML


class CompilerTests(unittest.TestCase):
    def test_compile_book_merges_progress_and_builds_epub(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            progress_dir = book_dir / "progress" / "gemini"
            progress_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            for index in [10, 11]:
                data = {
                    "index": index,
                    "original_title": f"第{index}章",
                    "translated_title": f"Chương {index}: Tựa",
                    "translated_content": [f"Nội dung {index}."],
                }
                (progress_dir / f"chapter_{index:04d}.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )

            result = compile_book(book_dir)

            self.assertEqual(result.chapters_merged, 2)
            txt = result.output_txt.read_text(encoding="utf-8")
            self.assertIn("Chương 10: Tựa", txt)
            self.assertIn("Nội dung 11.", txt)
            self.assertTrue(result.output_epub.exists())
            with zipfile.ZipFile(result.output_epub) as epub:
                self.assertIn("mimetype", epub.namelist())
                self.assertIn("OEBPS/content.opf", epub.namelist())

    def test_cli_compile_uses_selected_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            progress_dir = book_dir / "progress" / "gemini"
            progress_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            data = {
                "index": 10,
                "original_title": "第10章",
                "translated_title": "Chương 10: Tựa",
                "translated_content": ["Nội dung."],
            }
            (progress_dir / "chapter_0010.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["compile", "--book", "sample-book"])
            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "output" / "sample.vi.txt").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_compiler
```

Expected: import failure for `novel_tools.compiler`.

- [ ] **Step 3: Implement EPUB module**

Create `novel_tools/epub.py` by adapting `txt_to_epub.py` into dependency-free functions:

```python
from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


def clean_xml_string(value: str) -> str:
    return html.escape(value)


def split_translated_txt(content: str) -> list[tuple[str, list[str]]]:
    chapter_pattern = re.compile(r"^\s*(?:第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]|Chương\s*[0-9\s]+).*", re.IGNORECASE)
    chapters: list[tuple[str, list[str]]] = []
    current_title = "Giới thiệu & Tóm tắt"
    current_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or set(stripped) == {"-"}:
            continue
        if chapter_pattern.match(stripped) and len(stripped) < 100:
            if current_lines or not chapters:
                chapters.append((current_title, current_lines))
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(stripped)
    if current_lines or current_title != "Giới thiệu & Tóm tắt":
        chapters.append((current_title, current_lines))
    return chapters


def build_epub_from_text(content: str, epub_path: Path, title: str, author: str, language: str = "vi") -> None:
    chapters = split_translated_txt(content)
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as epub:
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>""",
        )
        epub.writestr(
            "OEBPS/style.css",
            """body { font-family: Georgia, 'Times New Roman', serif; margin: 5%; line-height: 1.6; text-align: justify; }
h1 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; }
p { text-indent: 2em; margin-top: 0.5em; margin-bottom: 0.5em; }""",
        )
        manifest_items: list[str] = []
        spine_items: list[str] = []
        navpoints: list[str] = []
        for i, (chapter_title, lines) in enumerate(chapters):
            filename = f"chapter_{i}.xhtml"
            paragraphs = "\n".join(f"<p>{clean_xml_string(line)}</p>" for line in lines)
            epub.writestr(
                f"OEBPS/{filename}",
                f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{clean_xml_string(chapter_title)}</title><link rel="stylesheet" href="style.css" type="text/css" /></head>
<body><h1>{clean_xml_string(chapter_title)}</h1>{paragraphs}</body>
</html>""",
            )
            manifest_items.append(f'<item id="ch_{i}" href="{filename}" media-type="application/xhtml+xml" />')
            spine_items.append(f'<itemref idref="ch_{i}" />')
            navpoints.append(
                f'<navPoint id="ch_{i}" playOrder="{i + 1}"><navLabel><text>{clean_xml_string(chapter_title)}</text></navLabel><content src="{filename}"/></navPoint>'
            )
        epub.writestr(
            "OEBPS/toc.ncx",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="urn:uuid:novel-tools"/></head>
<docTitle><text>{clean_xml_string(title)}</text></docTitle>
<navMap>{''.join(navpoints)}</navMap>
</ncx>""",
        )
        epub.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{clean_xml_string(title)}</dc:title>
<dc:creator>{clean_xml_string(author)}</dc:creator>
<dc:language>{clean_xml_string(language)}</dc:language>
<dc:identifier id="bookid">urn:uuid:novel-tools</dc:identifier>
</metadata>
<manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" /><item id="style" href="style.css" media-type="text/css" />{''.join(manifest_items)}</manifest>
<spine toc="ncx">{''.join(spine_items)}</spine>
</package>""",
        )
```

- [ ] **Step 4: Implement compiler module**

Create `novel_tools/compiler.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import load_book_config
from .epub import build_epub_from_text
from .paths import BookPaths
from .progress import find_indices


@dataclass(frozen=True)
class CompileResult:
    chapters_merged: int
    output_txt: Path
    output_epub: Path


def compile_book(book_dir: Path) -> CompileResult:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    indices = [idx for idx in find_indices(paths.progress_dir, ".json") if idx >= config.chapter_start_index]
    lines: list[str] = []
    for idx in indices:
        data = json.loads(paths.progress_file(idx).read_text(encoding="utf-8"))
        lines.append(data["translated_title"])
        lines.append("")
        lines.extend(data["translated_content"])
        lines.append("")
        lines.append("-" * 50)
        lines.append("")
    content = "\n".join(lines)
    paths.output_txt.parent.mkdir(parents=True, exist_ok=True)
    paths.output_txt.write_text(content, encoding="utf-8")
    build_epub_from_text(
        content,
        paths.output_epub,
        title=config.epub_title,
        author=config.epub_author,
        language=config.target_language or "vi",
    )
    return CompileResult(len(indices), paths.output_txt, paths.output_epub)
```

- [ ] **Step 5: Add `compile` CLI command**

Modify imports in `novel_tools/cli.py`:

```python
from .compiler import compile_book
```

Add parser:

```python
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--book", required=True)
```

Add branch:

```python
    if args.command == "compile":
        book_dir = book_dir_for_id(args.book, root)
        result = compile_book(book_dir)
        print(f"Merged {result.chapters_merged} chapters", file=out)
        print(f"Wrote {result.output_txt}", file=out)
        print(f"Wrote {result.output_epub}", file=out)
        return 0
```

- [ ] **Step 6: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_compiler tests.test_progress tests.test_chapters tests.test_config
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add novel_tools/compiler.py novel_tools/epub.py novel_tools/cli.py tests/test_compiler.py
git commit -m "feat: add book-scoped compilation"
```

---

### Task 6: Context Bundle Command

**Files:**
- Create: `novel_tools/context.py`
- Create: `tests/test_context.py`
- Modify: `novel_tools/cli.py`

- [ ] **Step 1: Write failing context tests**

Create `tests/test_context.py`:

```python
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.context import build_context
from tests.test_config import BOOK_YAML


class ContextTests(unittest.TestCase):
    def test_build_context_includes_book_files_and_chapter_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "harness.md").write_text("# Style\nUse crisp prose.", encoding="utf-8")
            (book_dir / "glossary.tsv").write_text("术士\tthuật sĩ\tnote", encoding="utf-8")
            (book_dir / "characters.md").write_text("# Characters\nA speaks formally.", encoding="utf-8")

            text = build_context(book_dir, 10)

            self.assertIn("Book ID: sample-book", text)
            self.assertIn("# Style", text)
            self.assertIn("术士\tthuật sĩ", text)
            self.assertIn("chapter_0010_cn.txt", text)
            self.assertIn("chapter_0010.txt", text)

    def test_cli_context_prints_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "harness.md").write_text("# Style\nUse crisp prose.", encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                out = StringIO()
                code = main(["context", "--book", "sample-book", "--chapter", "10"], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("Use crisp prose.", out.getvalue())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_context
```

Expected: import failure for `novel_tools.context`.

- [ ] **Step 3: Implement context module**

Create `novel_tools/context.py`:

```python
from __future__ import annotations

from pathlib import Path

from .config import load_book_config
from .paths import BookPaths


def build_context(book_dir: Path, chapter_index: int) -> str:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    sections = [
        "# Translation Context",
        "",
        "## Book",
        f"Book ID: {config.id}",
        f"Title: {config.title}",
        f"Source title: {config.source_title or ''}",
        f"Author: {config.author or ''}",
        f"Source language: {config.source_language or ''}",
        f"Target language: {config.target_language or ''}",
        f"Chapter index: {chapter_index}",
        f"Source chapter path: {paths.cn_chapter_file(chapter_index)}",
        f"Target chapter path: {paths.vi_chapter_file(chapter_index)}",
        f"Progress JSON path: {paths.progress_file(chapter_index)}",
    ]
    for filename, heading in [
        ("harness.md", "Harness"),
        ("glossary.tsv", "Glossary"),
        ("characters.md", "Characters"),
        ("continuity.md", "Continuity"),
    ]:
        path = book_dir / filename
        if path.exists():
            sections.extend(["", f"## {heading}", path.read_text(encoding="utf-8").strip()])
    return "\n".join(sections).rstrip() + "\n"
```

- [ ] **Step 4: Add `context` CLI command**

Modify imports in `novel_tools/cli.py`:

```python
from .context import build_context
```

Add parser:

```python
    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("--book", required=True)
    context_parser.add_argument("--chapter", required=True, type=int)
```

Add branch:

```python
    if args.command == "context":
        book_dir = book_dir_for_id(args.book, root)
        print(build_context(book_dir, args.chapter), end="", file=out)
        return 0
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_context tests.test_compiler tests.test_progress tests.test_chapters tests.test_config
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add novel_tools/context.py novel_tools/cli.py tests/test_context.py
git commit -m "feat: add book translation context command"
```

---

### Task 7: Title Unification

**Files:**
- Modify: `novel_tools/progress.py`
- Modify: `novel_tools/cli.py`
- Modify: `tests/test_progress.py`

- [ ] **Step 1: Add failing unify test**

Append to `tests/test_progress.py`:

```python
from novel_tools.progress import unify_titles
```

Add method:

```python
    def test_unify_titles_updates_txt_and_json_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "progress" / "gemini").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text(
                "Chương 1: Tựa cũ\n\nBody", encoding="utf-8"
            )
            data = {
                "index": 10,
                "original_title": "第10章",
                "translated_title": "Chương 1: Tựa cũ",
                "translated_content": ["Body"],
            }
            (book_dir / "progress" / "gemini" / "chapter_0010.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )

            count = unify_titles(book_dir)

            self.assertEqual(count, 1)
            self.assertTrue(
                (book_dir / "chapters" / "vi" / "chapter_0010.txt")
                .read_text(encoding="utf-8")
                .startswith("Chương 10: Tựa cũ")
            )
            updated = json.loads((book_dir / "progress" / "gemini" / "chapter_0010.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["translated_title"], "Chương 10: Tựa cũ")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_progress
```

Expected: import failure for `unify_titles`.

- [ ] **Step 3: Implement title unification**

Append to `novel_tools/progress.py`:

```python
def clean_title_prefix(title: str) -> str:
    cleaned = re.sub(r"^(?:Chương|第)\s*\d+\s*[章:]?\s*", "", title, flags=re.IGNORECASE).strip()
    return cleaned.lstrip(":").strip()


def unify_titles(book_dir: Path) -> int:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    updated = 0
    for idx in find_indices(paths.progress_dir, ".json"):
        if idx < config.chapter_start_index:
            continue
        json_path = paths.progress_file(idx)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        title_text = clean_title_prefix(str(data.get("translated_title", "")))
        new_title = config.chapter_title_format.format(index=idx, title=title_text)
        data["index"] = idx
        data["translated_title"] = new_title
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path = paths.vi_chapter_file(idx)
        if txt_path.exists():
            lines = txt_path.read_text(encoding="utf-8").splitlines()
            if lines:
                lines[0] = new_title
                txt_path.write_text("\n".join(lines), encoding="utf-8")
        updated += 1
    return updated
```

- [ ] **Step 4: Add `unify` CLI command**

Modify imports in `novel_tools/cli.py`:

```python
from .progress import find_indices, latest_index, missing_indices, register_chapter, unify_titles
```

Add parser:

```python
    unify_parser = subparsers.add_parser("unify")
    unify_parser.add_argument("--book", required=True)
```

Add branch:

```python
    if args.command == "unify":
        book_dir = book_dir_for_id(args.book, root)
        count = unify_titles(book_dir)
        print(f"Updated {count} chapters", file=out)
        return 0
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```powershell
python -m unittest tests.test_progress tests.test_context tests.test_compiler tests.test_chapters tests.test_config
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add novel_tools/progress.py novel_tools/cli.py tests/test_progress.py
git commit -m "feat: add book-scoped title unification"
```

---

### Task 8: Migrate Book Workspaces

**Files:**
- Create: `library/thai-binh-lenh/book.yaml`
- Create: `library/thai-binh-lenh/harness.md`
- Create: `library/thai-binh-lenh/glossary.tsv`
- Create: `library/thai-binh-lenh/characters.md`
- Create: `library/thai-binh-lenh/continuity.md`
- Create: `library/luan-hoi-lac-vien/book.yaml`
- Create: `library/luan-hoi-lac-vien/harness.md`
- Create: `library/luan-hoi-lac-vien/glossary.tsv`
- Create: `library/luan-hoi-lac-vien/characters.md`
- Create: `library/luan-hoi-lac-vien/continuity.md`
- Move: current book/chapter/progress artifacts into `library/`

- [ ] **Step 1: Capture pre-migration counts**

Run:

```powershell
Get-ChildItem chapters/vi -Filter 'chapter_*.txt' | Measure-Object
Get-ChildItem chapters/cn -Filter 'chapter_*_cn.txt' | Measure-Object
Get-ChildItem progress/gemini -Filter 'chapter_*.json' | Measure-Object
Get-ChildItem progress/minimax -Filter 'chapter_*.json' | Measure-Object
```

Expected current counts from exploration:

```text
chapters/vi: 323
chapters/cn: 318
progress/gemini: 330
progress/minimax: 21
```

If counts differ, record the actual counts in the commit message body.

- [ ] **Step 2: Create book directories**

Run:

```powershell
New-Item -ItemType Directory -Force library/thai-binh-lenh/source,library/thai-binh-lenh/chapters/cn,library/thai-binh-lenh/chapters/vi,library/thai-binh-lenh/progress/gemini,library/thai-binh-lenh/progress/minimax,library/thai-binh-lenh/output
New-Item -ItemType Directory -Force library/luan-hoi-lac-vien/source,library/luan-hoi-lac-vien/chapters/cn,library/luan-hoi-lac-vien/chapters/vi,library/luan-hoi-lac-vien/progress/gemini,library/luan-hoi-lac-vien/output
```

Expected: directories exist.

- [ ] **Step 3: Move files with PowerShell-native commands**

Run:

```powershell
Move-Item -LiteralPath 'books/太平令.txt' -Destination 'library/thai-binh-lenh/source/太平令.txt'
Move-Item -LiteralPath 'books/太平令.epub' -Destination 'library/thai-binh-lenh/source/太平令.epub'
Move-Item -LiteralPath 'books/太平令_Vietnamese_gemini.txt' -Destination 'library/thai-binh-lenh/output/thai-binh-lenh.vi.txt'
Move-Item -LiteralPath 'books/太平令_Vietnamese_gemini.epub' -Destination 'library/thai-binh-lenh/output/thai-binh-lenh.vi.epub'
Move-Item -LiteralPath 'books/轮回乐园.txt' -Destination 'library/luan-hoi-lac-vien/source/轮回乐园.txt'
Move-Item -LiteralPath 'chapters/cn/'* -Destination 'library/thai-binh-lenh/chapters/cn/'
Move-Item -LiteralPath 'chapters/vi/'* -Destination 'library/thai-binh-lenh/chapters/vi/'
Move-Item -LiteralPath 'progress/gemini/'* -Destination 'library/thai-binh-lenh/progress/gemini/'
Move-Item -LiteralPath 'progress/minimax/'* -Destination 'library/thai-binh-lenh/progress/minimax/'
```

Expected: files are moved, not copied. Do not delete any directories yet.

- [ ] **Step 4: Add `thai-binh-lenh` config and context files**

Create `library/thai-binh-lenh/book.yaml`:

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

Create `library/thai-binh-lenh/harness.md`:

```markdown
# Thái Bình Lệnh Translation Harness

Translate Chinese wuxia and historical fantasy prose into polished, natural Vietnamese.

## Style

- Balance Hán-Việt and Thuần Việt.
- Keep martial arts terms, official titles, and epic terminology in elegant Hán-Việt.
- Translate narrative descriptions and common verbs into smooth natural Vietnamese.
- Avoid rigid word-for-word translation.
- Keep the rhythm dynamic, fast-paced, and poetic.
- Use standard Vietnamese idioms where they fit naturally.

## Character Voice

- Lý Quan Nhất: use `hắn` or `cậu` in narration. When speaking to elders, use `con/cháu`; refer to elders as `Trần lão`, `thái ngoại tổ phụ`, or `tiền bối` according to context.
- Dao Quang: silver-haired girl. Lý Quan Nhất may refer to her as `muội` or `nàng`; she may call Mộ Dung Long Đồ `thái ngoại tổ phụ` or `ông cố ngoại`.
- Yến Đại Thanh: interior/logistics lead. Use `Yến Đại Thanh` or `Đại Thanh`; he uses `ta` and calls Lý Quan Nhất `Chúa công` or `tiểu tử` in casual settings.
- Đề Kỵ / Ti Kỵ: coarse and proud government secret police. They may use `gia gia/ông đây` and call commoners `đồ chó già` or `lũ ngu dân` when appropriate.
- Arrogant nobles or young scholars: use `ta/bản quan`; refer to commoners as `lũ thăng đấu tiểu dân` and frame service as `vinh hạnh` where context supports it.

## Formatting

- Line 1 of each Vietnamese chapter must be `Chương <global_index>: <Title>`.
- Line 2 must be empty.
- Preserve paragraph boundaries.
- Remove author notes, vote requests, unrelated updates, and translator notes.
```

Create empty optional files:

```powershell
Set-Content -LiteralPath 'library/thai-binh-lenh/glossary.tsv' -Value '' -Encoding utf8
Set-Content -LiteralPath 'library/thai-binh-lenh/characters.md' -Value '# Characters' -Encoding utf8
Set-Content -LiteralPath 'library/thai-binh-lenh/continuity.md' -Value '# Continuity' -Encoding utf8
```

- [ ] **Step 5: Add `luan-hoi-lac-vien` starter config**

Create `library/luan-hoi-lac-vien/book.yaml`:

```yaml
id: luan-hoi-lac-vien
title: "Luân Hồi Lạc Viên"
source_title: "轮回乐园"
author: "Unknown"
language:
  source: zh-CN
  target: vi
chapter:
  start_index: 0
  title_format: "Chương {index}: {title}"
source:
  file: "source/轮回乐园.txt"
outputs:
  txt: "output/luan-hoi-lac-vien.vi.txt"
  epub: "output/luan-hoi-lac-vien.vi.epub"
providers:
  default: gemini
  progress_dir: "progress/gemini"
epub:
  title: "Luân Hồi Lạc Viên (Bản dịch Việt)"
  author: "Unknown"
```

Create `library/luan-hoi-lac-vien/harness.md`:

```markdown
# Luân Hồi Lạc Viên Translation Harness

Translate Chinese action, survival, game-system, and dark-fantasy prose into sharp, readable Vietnamese.

## Style

- Keep combat descriptions clear, kinetic, and concrete.
- Keep system/game terminology consistent.
- Prefer direct Vietnamese phrasing for action beats.
- Keep specialized abilities, factions, titles, and equipment terms stable once chosen.

## Formatting

- Line 1 of each Vietnamese chapter must be `Chương <global_index>: <Title>`.
- Line 2 must be empty.
- Preserve paragraph boundaries.
- Remove author notes, vote requests, unrelated updates, and translator notes.
```

Create empty optional files:

```powershell
Set-Content -LiteralPath 'library/luan-hoi-lac-vien/glossary.tsv' -Value '' -Encoding utf8
Set-Content -LiteralPath 'library/luan-hoi-lac-vien/characters.md' -Value '# Characters' -Encoding utf8
Set-Content -LiteralPath 'library/luan-hoi-lac-vien/continuity.md' -Value '# Continuity' -Encoding utf8
```

- [ ] **Step 6: Verify migrated counts and commands**

Run:

```powershell
Get-ChildItem library/thai-binh-lenh/chapters/vi -Filter 'chapter_*.txt' | Measure-Object
Get-ChildItem library/thai-binh-lenh/chapters/cn -Filter 'chapter_*_cn.txt' | Measure-Object
Get-ChildItem library/thai-binh-lenh/progress/gemini -Filter 'chapter_*.json' | Measure-Object
Get-ChildItem library/thai-binh-lenh/progress/minimax -Filter 'chapter_*.json' | Measure-Object
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools inspect --book luan-hoi-lac-vien
python -m novel_tools context --book thai-binh-lenh --chapter 562
```

Expected:

- Counts match pre-migration counts.
- `list-books` shows both book ids.
- `inspect --book thai-binh-lenh` shows existing chapter/progress counts.
- `inspect --book luan-hoi-lac-vien` shows source configured and zero chapter/progress counts.
- `context` includes the Thái Bình Lệnh harness.

- [ ] **Step 7: Commit migration**

```powershell
git add library
git add -A books chapters progress
git commit -m "refactor: migrate books into library workspaces"
```

---

### Task 9: Update Generic Translation Skill and README

**Files:**
- Modify: `skills/novel-translator/SKILL.md`
- Modify: `README.md`

- [ ] **Step 1: Rewrite `skills/novel-translator/SKILL.md` as generic workflow**

Replace book-specific paths with this workflow contract:

```markdown
---
name: novel-translator
description: "Translate configured Chinese web novels into polished Vietnamese using book-specific harnesses"
---

<objective>
Translate a chapter for a selected book workspace under `library/<book-id>/`, using that book's `book.yaml`, `harness.md`, and optional context files.
</objective>

<context>
$ARGUMENTS: Must include a book id and chapter index, for example `--book thai-binh-lenh --chapter 563`.
</context>

<process>
1. Resolve context:
   `python -m novel_tools context --book <book-id> --chapter <chapter>`
2. If the Chinese source chapter is missing, extract it:
   `python -m novel_tools extract --book <book-id> --chapter <chapter>`
3. Translate `chapters/cn/chapter_XXXX_cn.txt` into `chapters/vi/chapter_XXXX.txt` inside the selected book workspace.
4. Follow the selected book's `harness.md`, `glossary.tsv`, `characters.md`, and `continuity.md`.
5. Preserve paragraph boundaries. Remove author notes, vote requests, unrelated updates, and translator notes.
6. Use target format:
   - Line 1: `Chương <global_index>: <Title>`
   - Line 2: empty
   - Line 3+: translated paragraphs
7. Review source-to-target coverage, pronouns, terminology, and formatting.
8. Register progress:
   `python -m novel_tools register --book <book-id> --chapter <chapter>`
9. Compile after a batch:
   `python -m novel_tools compile --book <book-id>`
10. Run verification:
   `python -m novel_tools inspect --book <book-id>`
</process>

<security_notes>
- Never write outside the selected `library/<book-id>/` workspace unless the user explicitly asks.
- Never place API keys in files.
- Regenerate progress JSON after any translated chapter edit.
</security_notes>
```

- [ ] **Step 2: Update README**

Replace the single-title structure with multi-book instructions:

```markdown
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
```

- [ ] **Step 3: Verify docs mention no old single-book commands**

Run:

```powershell
rg -n "compile_gemini|generate_progress_json|extract_chapter|translate_novel|太平令_Vietnamese_gemini|chapters/vi" README.md skills/novel-translator/SKILL.md
```

Expected: no stale references except where explaining migrated historical data, if any.

- [ ] **Step 4: Commit docs and skill update**

```powershell
git add README.md skills/novel-translator/SKILL.md
git commit -m "docs: document multi-book translation workflow"
```

---

### Task 10: Remove Legacy Translation Scripts

**Files:**
- Delete: `compile_gemini.py`
- Delete: `extract_chapter.py`
- Delete: `generate_progress_json.py`
- Delete: `translate_novel.py`
- Delete: `unify_chapters.py`
- Delete: `txt_to_epub.py` if `rg "txt_to_epub|build_epub" -g "*.py"` shows no remaining imports.

- [ ] **Step 1: Confirm no imports depend on old scripts**

Run:

```powershell
rg -n "compile_gemini|extract_chapter|generate_progress_json|translate_novel|unify_chapters|txt_to_epub|build_epub" -g "*.py" -g "*.md"
```

Expected: references only in historical design/plan docs, not in live code or README/skill.

- [ ] **Step 2: Delete old scripts**

Run:

```powershell
Remove-Item -LiteralPath compile_gemini.py
Remove-Item -LiteralPath extract_chapter.py
Remove-Item -LiteralPath generate_progress_json.py
Remove-Item -LiteralPath translate_novel.py
Remove-Item -LiteralPath unify_chapters.py
```

If no imports remain:

```powershell
Remove-Item -LiteralPath txt_to_epub.py
```

- [ ] **Step 3: Remove empty old directories**

Run:

```powershell
Get-ChildItem books -Force
Get-ChildItem chapters -Force
Get-ChildItem progress -Force
```

If all are empty, remove them:

```powershell
Remove-Item -LiteralPath books -Recurse
Remove-Item -LiteralPath chapters -Recurse
Remove-Item -LiteralPath progress -Recurse
```

- [ ] **Step 4: Run full verification**

Run:

```powershell
python -m unittest
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools compile --book thai-binh-lenh
python -m novel_tools inspect --book luan-hoi-lac-vien
python -m novel_tools context --book thai-binh-lenh --chapter 562
```

Expected:

- All tests pass, including `test_voz_thread_backup.py`.
- `thai-binh-lenh` compiles to `library/thai-binh-lenh/output/thai-binh-lenh.vi.txt` and `.epub`.
- `luan-hoi-lac-vien` inspect succeeds without translated chapters.
- Context command prints the selected book harness.

- [ ] **Step 5: Commit cleanup**

```powershell
git add -A
git commit -m "refactor: remove legacy single-book scripts"
```

---

## Final Verification

Run:

```powershell
python -m unittest
python -m novel_tools list-books
python -m novel_tools inspect --book thai-binh-lenh
python -m novel_tools compile --book thai-binh-lenh
python -m novel_tools inspect --book luan-hoi-lac-vien
python -m novel_tools context --book thai-binh-lenh --chapter 562
git status --short --branch
```

Expected:

- All tests pass.
- Both book ids are listed.
- `thai-binh-lenh` has the migrated chapter/progress counts.
- `thai-binh-lenh` output TXT and EPUB are regenerated in `library/thai-binh-lenh/output/`.
- `luan-hoi-lac-vien` is configured and inspectable.
- Working tree is clean after final commit.

## Self-Review Notes

- Spec coverage: the plan covers the self-contained `library/<book-id>/` layout, structured `book.yaml`, per-book harnesses, generic skill update, explicit `--book` commands, migration of both current books, old script removal, and verification.
- Scope: this is one cohesive refactor with a working checkpoint after each task. It does not introduce a database, vector store, GUI, or compatibility wrappers.
- Type consistency: `BookConfig`, `BookPaths`, `extract_chapter`, `register_chapter`, `compile_book`, `build_context`, and CLI command names are defined before use in later tasks.
