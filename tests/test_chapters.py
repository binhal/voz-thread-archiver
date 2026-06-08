import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novel_tools.chapters import extract_chapter, split_chapters
from novel_tools.cli import main
from tests.test_config import BOOK_YAML


SOURCE_TEXT = """前言
这是介绍。
第1章 第一章标题
第一章内容一。
第一章内容二。
第2章 第二章标题
第二章内容。
"""


class ChapterTests(unittest.TestCase):
    def test_split_chapters_detects_chinese_chapter_titles(self):
        chapters = split_chapters(SOURCE_TEXT)

        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].title, "Giới thiệu & Tóm tắt")
        self.assertEqual(chapters[1].index, 1)
        self.assertEqual(chapters[1].title, "第1章 第一章标题")
        self.assertEqual(chapters[1].lines, ["第一章内容一。", "第一章内容二。"])

    def test_extract_chapter_writes_selected_book_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "source").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "source" / "sample.txt").write_text(SOURCE_TEXT, encoding="utf-8")

            written = extract_chapter(book_dir, 1)

            self.assertEqual(written, book_dir / "chapters" / "cn" / "chapter_0001_cn.txt")
            self.assertIn("第1章 第一章标题", written.read_text(encoding="utf-8"))
            self.assertIn("第一章内容一。", written.read_text(encoding="utf-8"))

    def test_cli_extract_uses_book_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "source").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "source" / "sample.txt").write_text(SOURCE_TEXT, encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["extract", "--book", "sample-book", "--chapter", "2"])

            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "chapters" / "cn" / "chapter_0002_cn.txt").exists())


if __name__ == "__main__":
    unittest.main()
