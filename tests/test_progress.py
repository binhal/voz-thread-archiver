import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.progress import find_indices, register_chapter
from tests.test_config import BOOK_YAML


class ProgressTests(unittest.TestCase):
    def test_register_chapter_writes_progress_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "chapters" / "cn").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text(
                "Chương 10: Tiêu đề\n\nDòng một.\nDòng hai.", encoding="utf-8"
            )
            (book_dir / "chapters" / "cn" / "chapter_0010_cn.txt").write_text(
                "第10章 原题\n\n中文内容", encoding="utf-8"
            )

            output = register_chapter(book_dir, 10)

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["index"], 10)
            self.assertEqual(data["original_title"], "第10章 原题")
            self.assertEqual(data["translated_title"], "Chương 10: Tiêu đề")
            self.assertEqual(data["translated_content"], ["Dòng một.", "Dòng hai."])

    def test_find_indices_returns_sorted_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "chapter_0012.json").write_text("{}", encoding="utf-8")
            (directory / "chapter_0010.json").write_text("{}", encoding="utf-8")
            self.assertEqual(find_indices(directory, ".json"), [10, 12])

    def test_cli_register_uses_selected_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            (book_dir / "chapters" / "vi").mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "chapters" / "vi" / "chapter_0010.txt").write_text(
                "Chương 10: Tiêu đề\n\nDòng một.", encoding="utf-8"
            )
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["register", "--book", "sample-book", "--chapter", "10"])
            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "progress" / "gemini" / "chapter_0010.json").exists())


if __name__ == "__main__":
    unittest.main()
