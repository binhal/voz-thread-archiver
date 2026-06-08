from __future__ import annotations

import json
import re
from pathlib import Path

from .config import ConfigError, load_book_config
from .paths import BookPaths


def find_indices(directory: Path, suffix: str) -> list[int]:
    if not directory.exists():
        return []
    pattern = re.compile(r"chapter_(\d{4,})" + re.escape(suffix) + r"$")
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
