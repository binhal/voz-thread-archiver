from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from novel_tools.config import ConfigError, load_book_config
from novel_tools.paths import BookPaths


SOURCE_ENCODINGS = ("gb18030", "utf-8-sig", "utf-8", "gbk", "cp936")
INTRO_TITLE = "Giới thiệu & Tóm tắt"
CHAPTER_TITLE_PATTERN = re.compile(
    r"^\s*(第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]).*"
)
AD_MARKERS = ("ixdzs", "爱下电子书")


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    lines: list[str]


def read_source_text(path: Path) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in SOURCE_ENCODINGS:
        try:
            return Path(path).read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except OSError as exc:
            raise ConfigError(f"Could not read source file {path}: {exc}") from exc
    raise ConfigError(f"Could not decode source file {path}") from last_error


def split_chapters(content: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    current_title = INTRO_TITLE
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if _is_chapter_title(line):
            if current_lines or not chapters:
                chapters.append(Chapter(len(chapters), current_title, current_lines))
            current_title = line
            current_lines = []
            continue

        if not _is_ad_line(line):
            current_lines.append(line)

    if current_lines or current_title != INTRO_TITLE:
        chapters.append(Chapter(len(chapters), current_title, current_lines))

    return chapters


def extract_chapter(book_dir: Path, chapter_index: int) -> Path:
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)
    chapters = split_chapters(read_source_text(paths.source_file))

    if chapter_index < 0 or chapter_index >= len(chapters):
        raise ConfigError(f"Chapter index {chapter_index} is out of range")

    chapter = chapters[chapter_index]
    output_path = paths.cn_chapter_file(chapter_index)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{chapter.title}\n\n" + "\n".join(chapter.lines), encoding="utf-8")
    return output_path


def _is_chapter_title(line: str) -> bool:
    return len(line) < 100 and CHAPTER_TITLE_PATTERN.match(line) is not None


def _is_ad_line(line: str) -> bool:
    return any(marker in line for marker in AD_MARKERS)
