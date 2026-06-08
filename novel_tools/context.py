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
