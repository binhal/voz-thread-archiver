from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TextIO

from novel_tools.chapters import extract_chapter
from novel_tools.config import ConfigError, load_book_config
from novel_tools.paths import BookPaths, book_dir_for_id, find_repo_root, list_book_ids
from novel_tools.progress import find_indices, latest_index, missing_indices, register_chapter, unify_titles
from novel_tools.compiler import compile_book
from novel_tools.context import build_context


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
        if args.command == "extract":
            return _extract(root, args.book, args.chapter, output)
        if args.command == "register":
            return _register(root, args.book, args.chapter, output)
        if args.command == "compile":
            return _compile(root, args.book, output)
        if args.command == "context":
            return _context(root, args.book, args.chapter, output)
        if args.command == "unify":
            return _unify(root, args.book, output)
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

    extract_parser = subparsers.add_parser("extract", help="Extract a source chapter")
    extract_parser.add_argument("--book", required=True, help="Book id to extract from")
    extract_parser.add_argument("--chapter", required=True, type=int, help="Chapter index to extract")

    register_parser = subparsers.add_parser("register", help="Register progress for a translated chapter")
    register_parser.add_argument("--book", required=True, help="Book id to register chapter for")
    register_parser.add_argument("--chapter", required=True, type=int, help="Chapter index to register")

    compile_parser = subparsers.add_parser("compile", help="Compile translated book to txt and epub")
    compile_parser.add_argument("--book", required=True, help="Book id to compile")

    context_parser = subparsers.add_parser("context", help="Get translation context for a chapter")
    context_parser.add_argument("--book", required=True, help="Book id")
    context_parser.add_argument("--chapter", required=True, type=int, help="Chapter index")

    unify_parser = subparsers.add_parser("unify", help="Unify chapter titles across txt and progress JSON")
    unify_parser.add_argument("--book", required=True, help="Book id")

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

    vi_indices = find_indices(paths.vi_chapters_dir, ".txt")
    progress_indices = find_indices(paths.progress_dir, ".json")
    latest_vi = vi_indices[-1] if vi_indices else None
    latest_progress = progress_indices[-1] if progress_indices else None
    gap_end = latest_vi if latest_vi is not None else config.chapter_start_index - 1
    gaps = missing_indices(progress_indices, config.chapter_start_index, gap_end) if gap_end >= config.chapter_start_index else []

    print(f"Latest Vietnamese chapter: {latest_vi if latest_vi is not None else 'none'}", file=stdout)
    print(f"Latest progress chapter: {latest_progress if latest_progress is not None else 'none'}", file=stdout)
    print(f"Progress gaps: {', '.join(str(gap) for gap in gaps[:20]) if gaps else 'none'}", file=stdout)
    print(f"Output txt: {_display_path(paths.output_txt, root)}", file=stdout)
    print(f"Output epub: {_display_path(paths.output_epub, root)}", file=stdout)
    return 0


def _extract(root: Path, book_id: str, chapter_index: int, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    output_path = extract_chapter(book_dir, chapter_index)
    print(f"Wrote {_display_path(output_path, root)}", file=stdout)
    return 0


def _register(root: Path, book_id: str, chapter_index: int, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    output_path = register_chapter(book_dir, chapter_index)
    print(f"Wrote {_display_path(output_path, root)}", file=stdout)
    return 0


def _compile(root: Path, book_id: str, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    result = compile_book(book_dir)
    print(f"Merged {result.chapters_merged} chapters", file=stdout)
    print(f"Wrote {_display_path(result.output_txt, root)}", file=stdout)
    print(f"Wrote {_display_path(result.output_epub, root)}", file=stdout)
    return 0


def _context(root: Path, book_id: str, chapter_index: int, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    print(build_context(book_dir, chapter_index), end="", file=stdout)
    return 0


def _unify(root: Path, book_id: str, stdout: TextIO) -> int:
    book_dir = book_dir_for_id(book_id, root)
    count = unify_titles(book_dir)
    print(f"Updated {count} chapters", file=stdout)
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
