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
