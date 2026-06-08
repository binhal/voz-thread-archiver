from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TextIO

from novel_tools.config import ConfigError, load_book_config
from novel_tools.paths import BookPaths, book_dir_for_id, find_repo_root, list_book_ids


CN_CHAPTER_PATTERN = re.compile(r"^chapter_\d{4,}_cn\.txt$")
VI_CHAPTER_PATTERN = re.compile(r"^chapter_\d{4,}\.txt$")
PROGRESS_ENTRY_PATTERN = re.compile(r"^chapter_\d{4,}\.json$")


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    output = sys.stdout if stdout is None else stdout
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        root = find_repo_root()
        if args.command == "list-books":
            return _list_books(root, output)
        if args.command == "inspect":
            return _inspect_book(root, args.book, output)
    except ConfigError as exc:
        parser.exit(1, f"error: {exc}\n")

    parser.print_help(output)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m novel_tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-books", help="List configured books")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a configured book")
    inspect_parser.add_argument("--book", required=True, help="Book id to inspect")

    return parser


def _list_books(root: Path, stdout: TextIO) -> int:
    for book_id in list_book_ids(root):
        book_dir = book_dir_for_id(book_id, root)
        config = load_book_config(book_dir)
        print(f"{config.id}\t{config.title}", file=stdout)
    return 0


def _inspect_book(root: Path, book_id: str, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    config = load_book_config(book_dir)
    paths = BookPaths(book_dir, config)

    print(f"Book: {config.id}", file=stdout)
    print(f"Title: {config.title}", file=stdout)
    print(f"Source path: {_display_path(paths.source_file, root)}", file=stdout)
    print(f"Chinese chapters: {_count_files(paths.cn_chapters_dir, CN_CHAPTER_PATTERN)}", file=stdout)
    print(f"Vietnamese chapters: {_count_files(paths.vi_chapters_dir, VI_CHAPTER_PATTERN)}", file=stdout)
    print(f"Progress entries: {_count_files(paths.progress_dir, PROGRESS_ENTRY_PATTERN)}", file=stdout)
    print(f"Output txt: {_display_path(paths.output_txt, root)}", file=stdout)
    print(f"Output epub: {_display_path(paths.output_epub, root)}", file=stdout)
    return 0


def _count_files(directory: Path, pattern: re.Pattern[str]) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.iterdir() if path.is_file() and pattern.fullmatch(path.name))


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
