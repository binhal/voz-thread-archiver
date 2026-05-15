import json
import unittest
from pathlib import Path

from voz_thread_backup import (
    FetchResult,
    build_index,
    export_page,
    parse_thread_page,
    render_page_markdown,
    write_manifest,
)


SAMPLE_HTML = """
<!doctype html>
<html>
<head><title>Example Thread | VOZ</title></head>
<body>
<article class="message message--post js-post" data-author="alice">
  <div class="message-cell message-cell--main">
    <header>
      <h4 class="message-name"><a href="/members/alice.1/">alice</a></h4>
      <a href="/t/thread.1/post-10" class="message-attribution-gadget">#10</a>
      <time class="u-dt" datetime="2020-03-11T01:02:03+0700">Mar 11, 2020</time>
    </header>
    <div class="message-content js-messageContent">
      <div class="bbWrapper">
        Hello <b>world</b><br>
        <a href="https://example.com/book">Book</a>
        <blockquote class="bbCodeBlock">quoted text</blockquote>
      </div>
    </div>
  </div>
</article>
<article class="message message--post js-post">
  <h4 class="message-name"><a>bob</a></h4>
  <time class="u-dt">Yesterday at 10:55 PM</time>
  <div class="bbWrapper">Second post &amp; text</div>
</article>
</body>
</html>
"""

TEST_OUTPUT = Path(".test-output")


def test_output_dir(name: str) -> Path:
    path = TEST_OUTPUT / name
    path.mkdir(parents=True, exist_ok=True)
    return path


class ParserTests(unittest.TestCase):
    def test_parse_thread_page_extracts_posts_and_metadata(self):
        page = parse_thread_page(SAMPLE_HTML, "https://voz.vn/t/thread.1/page-1")

        self.assertEqual(page.title, "Example Thread | VOZ")
        self.assertEqual(len(page.posts), 2)
        self.assertEqual(page.posts[0].author, "alice")
        self.assertEqual(page.posts[0].post_number, "#10")
        self.assertEqual(page.posts[0].datetime, "2020-03-11T01:02:03+0700")
        self.assertIn("Hello", page.posts[0].body_markdown)
        self.assertIn("[Book](https://example.com/book)", page.posts[0].body_markdown)
        self.assertEqual(page.posts[1].author, "bob")
        self.assertIn("Second post & text", page.posts[1].body_markdown)

    def test_render_page_markdown_includes_page_header_and_posts(self):
        page = parse_thread_page(SAMPLE_HTML, "https://voz.vn/t/thread.1/page-1")

        markdown = render_page_markdown(page, 1)

        self.assertIn("# Example Thread | VOZ - Page 1", markdown)
        self.assertIn("Source: https://voz.vn/t/thread.1/page-1", markdown)
        self.assertIn("## #10 - alice", markdown)
        self.assertIn("## Post 2 - bob", markdown)


class ExportTests(unittest.TestCase):
    def test_export_page_writes_markdown_and_raw_html_for_success(self):
        output = test_output_dir("success-export")
        result = FetchResult(
            url="https://voz.vn/t/thread.1/page-1",
            status=200,
            body=SAMPLE_HTML,
            error=None,
        )

        entry = export_page(output, 1, result)

        self.assertEqual(entry["page"], 1)
        self.assertEqual(entry["status"], 200)
        self.assertEqual(entry["post_count"], 2)
        self.assertTrue((output / "page-0001.md").exists())
        self.assertTrue((output / "raw" / "page-0001.html").exists())
        self.assertIn("alice", (output / "page-0001.md").read_text(encoding="utf-8"))

    def test_export_page_writes_stub_for_failed_fetch(self):
        output = test_output_dir("failed-export")
        result = FetchResult(
            url="https://voz.vn/t/thread.1/page-2",
            status=404,
            body=None,
            error="HTTP Error 404: Not Found",
        )

        entry = export_page(output, 2, result)

        self.assertEqual(entry["page"], 2)
        self.assertEqual(entry["status"], 404)
        self.assertEqual(entry["post_count"], 0)
        self.assertFalse((output / "raw" / "page-0002.html").exists())
        self.assertIn("Fetch failed", (output / "page-0002.md").read_text(encoding="utf-8"))

    def test_manifest_and_index_are_written(self):
        output = test_output_dir("manifest-index")
        entries = [
            {
                "page": 1,
                "url": "https://voz.vn/t/thread.1/page-1",
                "status": 200,
                "title": "Thread",
                "post_count": 2,
                "markdown_path": "page-0001.md",
                "raw_path": "raw/page-0001.html",
                "error": None,
            },
            {
                "page": 2,
                "url": "https://voz.vn/t/thread.1/page-2",
                "status": 404,
                "title": None,
                "post_count": 0,
                "markdown_path": "page-0002.md",
                "raw_path": None,
                "error": "HTTP Error 404: Not Found",
            },
        ]

        write_manifest(output, entries)
        build_index(output, entries)

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        index = (output / "index.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["total_pages"], 2)
        self.assertEqual(manifest["successful_pages"], 1)
        self.assertIn("[Page 1](page-0001.md)", index)
        self.assertIn("failed", index)


if __name__ == "__main__":
    unittest.main()
