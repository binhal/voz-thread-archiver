import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.config import BookConfig, ConfigError, load_book_config, parse_limited_yaml
from novel_tools.paths import BookPaths, book_dir_for_id, find_library_dir, list_book_ids


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
            (book_dir / "chapters" / "cn" / "chapter_0010_cn.txt").write_text("第10章 A", encoding="utf-8")
            (book_dir / "chapters" / "cn" / "chapter_10000_cn.txt").write_text("第10000章 A", encoding="utf-8")
            (book_dir / "chapters" / "cn" / "chapter_abcd_cn.txt").write_text("lookalike", encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text("Chương 10: A\n\nBody", encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_10000.txt").write_text("Chương 10000: A\n\nBody", encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_abcd.txt").write_text("lookalike", encoding="utf-8")
            (book_dir / "progress" / "gemini" / "chapter_0010.json").write_text("{}", encoding="utf-8")
            (book_dir / "progress" / "gemini" / "chapter_10000.json").write_text("{}", encoding="utf-8")
            (book_dir / "progress" / "gemini" / "chapter_abcd.json").write_text("{}", encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                out = StringIO()
                code = main(["inspect", "--book", "sample-book"], stdout=out)
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("Book: sample-book", text)
            self.assertIn("Chinese chapters: 2", text)
            self.assertIn("Vietnamese chapters: 2", text)
            self.assertIn("Progress entries: 2", text)
            self.assertIn("output/sample.vi.txt", text)

    def test_book_dir_for_id_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library"
            outside = root / "outside"
            outside.mkdir(parents=True)
            (outside / "book.yaml").write_text(BOOK_YAML.replace("sample-book", "outside"), encoding="utf-8")
            library.mkdir()

            with self.assertRaises(ConfigError):
                book_dir_for_id("../outside", root)

    def test_parse_limited_yaml_rejects_indentation_after_scalar(self):
        with self.assertRaises(ConfigError):
            parse_limited_yaml("id: bad\n  title: Bad\n")

    def test_parse_limited_yaml_rejects_skipped_indentation_levels(self):
        with self.assertRaises(ConfigError):
            parse_limited_yaml("book:\n    id: bad\n")


if __name__ == "__main__":
    unittest.main()
