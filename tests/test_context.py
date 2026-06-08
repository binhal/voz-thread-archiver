import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from novel_tools.cli import main
from novel_tools.context import build_context
from tests.test_config import BOOK_YAML


class ContextTests(unittest.TestCase):
    def test_build_context_includes_book_files_and_chapter_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "harness.md").write_text("# Style\nUse crisp prose.", encoding="utf-8")
            (book_dir / "glossary.tsv").write_text("术士\tthuật sĩ\tnote", encoding="utf-8")
            (book_dir / "characters.md").write_text("# Characters\nA speaks formally.", encoding="utf-8")

            text = build_context(book_dir, 10)

            self.assertIn("Book ID: sample-book", text)
            self.assertIn("# Style", text)
            self.assertIn("术士\tthuật sĩ", text)
            self.assertIn("chapter_0010_cn.txt", text)
            self.assertIn("chapter_0010.txt", text)

    def test_cli_context_prints_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_dir = root / "library" / "sample-book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
            (book_dir / "harness.md").write_text("# Style\nUse crisp prose.", encoding="utf-8")
            with patch("novel_tools.cli.find_repo_root", return_value=root):
                out = StringIO()
                code = main(["context", "--book", "sample-book", "--chapter", "10"], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("Use crisp prose.", out.getvalue())


if __name__ == "__main__":
    unittest.main()
