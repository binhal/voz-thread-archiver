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
