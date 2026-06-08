from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


class ConfigError(Exception):
    """Raised when a book configuration file is invalid."""


@dataclass(frozen=True)
class BookConfig:
    id: str
    title: str
    source_file: Path
    output_txt: Path
    output_epub: Path
    provider: str
    progress_dir: Path
    chapter_start_index: int
    chapter_title_format: str
    source_title: str | None = None
    author: str | None = None
    source_language: str | None = None
    target_language: str | None = None
    epub_title: str | None = None
    epub_author: str | None = None


def parse_limited_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip():
            continue
        if raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("\t"):
            raise ConfigError(f"Tabs are not allowed on line {line_number}")

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ConfigError(f"Indentation must use two spaces on line {line_number}")

        level = indent // 2
        line = raw_line.strip()
        if line.startswith("-"):
            raise ConfigError(f"Arrays are not supported on line {line_number}")
        if ":" not in line:
            raise ConfigError(f"Expected key/value pair on line {line_number}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f"Missing key on line {line_number}")

        while stack and stack[-1][0] >= level:
            stack.pop()
        if not stack:
            raise ConfigError(f"Invalid indentation on line {line_number}")
        if level != stack[-1][0] + 1:
            raise ConfigError(f"Invalid indentation on line {line_number}")

        parent = stack[-1][1]
        if key in parent:
            raise ConfigError(f"Duplicate key '{key}' on line {line_number}")

        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((level, child))
        else:
            parent[key] = _parse_scalar(value)

    return root


def load_book_config(book_dir: Path) -> BookConfig:
    config_path = Path(book_dir) / "book.yaml"
    try:
        data = parse_limited_yaml(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read {config_path}: {exc}") from exc

    return BookConfig(
        id=_required_str(data, "id"),
        title=_required_str(data, "title"),
        source_title=_optional_str(data, "source_title"),
        author=_optional_str(data, "author"),
        source_language=_optional_str(data, "language.source"),
        target_language=_optional_str(data, "language.target"),
        chapter_start_index=_required_int(data, "chapter.start_index"),
        chapter_title_format=_required_str(data, "chapter.title_format"),
        source_file=Path(_required_str(data, "source.file")),
        output_txt=Path(_required_str(data, "outputs.txt")),
        output_epub=Path(_required_str(data, "outputs.epub")),
        provider=_required_str(data, "providers.default"),
        progress_dir=Path(_required_str(data, "providers.progress_dir")),
        epub_title=_optional_str(data, "epub.title"),
        epub_author=_optional_str(data, "epub.author"),
    )


def _parse_scalar(value: str) -> str | int:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _get_field(data: dict[str, Any], field_path: str) -> Any:
    current: Any = data
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ConfigError(f"Missing required field: {field_path}")
        current = current[part]
    return current


def _required_str(data: dict[str, Any], field_path: str) -> str:
    value = _get_field(data, field_path)
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"Expected non-empty string field: {field_path}")
    return value


def _optional_str(data: dict[str, Any], field_path: str) -> str | None:
    try:
        value = _get_field(data, field_path)
    except ConfigError:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"Expected string field: {field_path}")
    return value


def _required_int(data: dict[str, Any], field_path: str) -> int:
    value = _get_field(data, field_path)
    if not isinstance(value, int):
        raise ConfigError(f"Expected integer field: {field_path}")
    return value
