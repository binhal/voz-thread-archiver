from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from novel_tools.config import BookConfig, ConfigError


def find_repo_root(start: Path | None = None) -> Path:
    current = Path.cwd() if start is None else Path(start)
    current = current.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ConfigError(f"Could not find repository root from {current}")


def find_library_dir(start: Path | None = None) -> Path:
    root = find_repo_root(start) if start is None else Path(start)
    library = root / "library"
    if not library.is_dir():
        raise ConfigError(f"Could not find library directory at {library}")
    return library


def list_book_ids(start: Path | None = None) -> list[str]:
    library = find_library_dir(start)
    return sorted(
        child.name
        for child in library.iterdir()
        if child.is_dir() and (child / "book.yaml").is_file()
    )


def book_dir_for_id(book_id: str, start: Path | None = None) -> Path:
    library = find_library_dir(start).resolve()
    book_dir = (library / book_id).resolve()
    try:
        book_dir.relative_to(library)
    except ValueError as exc:
        raise ConfigError(f"Book id escapes library directory: {book_id}") from exc
    if not (book_dir / "book.yaml").is_file():
        raise ConfigError(f"Unknown book id: {book_id}")
    return book_dir


@dataclass(frozen=True)
class BookPaths:
    book_dir: Path
    config: BookConfig

    def __post_init__(self) -> None:
        book_dir = Path(self.book_dir).resolve()
        object.__setattr__(self, "book_dir", book_dir)
        object.__setattr__(self, "source_file", self._inside(self.config.source_file))
        object.__setattr__(self, "cn_chapters_dir", self._inside(Path("chapters/cn")))
        object.__setattr__(self, "vi_chapters_dir", self._inside(Path("chapters/vi")))
        object.__setattr__(self, "progress_dir", self._inside(self.config.progress_dir))
        object.__setattr__(self, "output_txt", self._inside(self.config.output_txt))
        object.__setattr__(self, "output_epub", self._inside(self.config.output_epub))

    def cn_chapter_file(self, chapter_index: int) -> Path:
        return self._inside(Path("chapters/cn") / f"chapter_{chapter_index:04d}_cn.txt")

    def vi_chapter_file(self, chapter_index: int) -> Path:
        return self._inside(Path("chapters/vi") / f"chapter_{chapter_index:04d}.txt")

    def progress_file(self, chapter_index: int) -> Path:
        return self._inside(self.config.progress_dir / f"chapter_{chapter_index:04d}.json")

    def _inside(self, relative_path: Path) -> Path:
        resolved = (self.book_dir / relative_path).resolve()
        try:
            resolved.relative_to(self.book_dir)
        except ValueError as exc:
            raise ConfigError(f"Configured path escapes book directory: {relative_path}") from exc
        return resolved
