import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.compiler import compile_book
from tests.test_config import BOOK_YAML


class CompilerTests(unittest.TestCase):
    def test_compile_book_merges_progress_and_builds_epub(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            progress_dir = book_dir / "progress" / "gemini"
            progress_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            for index in [10, 11]:
                data = {
                    "index": index,
                    "original_title": f"第{index}章",
                    "translated_title": f"Chương {index}: Tựa",
                    "translated_content": [f"Nội dung {index}."],
                }
                (progress_dir / f"chapter_{index:04d}.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )

            result = compile_book(book_dir)

            self.assertEqual(result.chapters_merged, 2)
            txt = result.output_txt.read_text(encoding="utf-8")
            self.assertIn("Chương 10: Tựa", txt)
            self.assertIn("Nội dung 11.", txt)
            self.assertTrue(result.output_epub.exists())
            with zipfile.ZipFile(result.output_epub) as epub:
                self.assertIn("mimetype", epub.namelist())
                self.assertIn("OEBPS/content.opf", epub.namelist())

    def test_cli_compile_uses_selected_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            progress_dir = book_dir / "progress" / "gemini"
            progress_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            data = {
                "index": 10,
                "original_title": "第10章",
                "translated_title": "Chương 10: Tựa",
                "translated_content": ["Nội dung."],
            }
            (progress_dir / "chapter_0010.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                code = main(["compile", "--book", "sample-book"])
            self.assertEqual(code, 0)
            self.assertTrue((book_dir / "output" / "sample.vi.txt").exists())


if __name__ == "__main__":
    unittest.main()
