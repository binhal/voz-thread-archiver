#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


THREAD_URL_TEMPLATE = (
    "https://voz.vn/t/ban-luan-ve-cac-truyen-tien-hiep-kiem-hiep-ky-ao-ver-nextvoz.1421/"
    "page-{page}"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int | None
    body: str | None
    error: str | None


@dataclass(frozen=True)
class Post:
    author: str
    date_text: str | None
    datetime: str | None
    post_number: str | None
    post_url: str | None
    body_markdown: str


@dataclass(frozen=True)
class ThreadPage:
    url: str
    title: str
    posts: list[Post]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return normalize_whitespace("".join(self.parts))


class _MarkdownConverter(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.link_stack: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag in {"br", "p", "div"}:
            self._append("\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append("\n\n### ")
        elif tag == "li":
            self._append("\n- ")
        elif tag == "blockquote":
            self._append("\n\n> ")
        elif tag == "a":
            self.link_stack.append({"href": attr.get("href"), "parts": []})
        elif tag == "img":
            alt = attr.get("alt") or attr.get("title") or attr.get("data-alt") or "image"
            src = attr.get("src") or attr.get("data-src")
            if src:
                src = urllib.parse.urljoin(self.base_url, src)
                self._append(f"![{escape_markdown(alt)}]({src})")
            else:
                self._append(f"Image: {alt}")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.link_stack:
            link = self.link_stack.pop()
            text = normalize_whitespace("".join(link["parts"]))
            href = link.get("href")
            if href and text:
                href = urllib.parse.urljoin(self.base_url, str(href))
                self._append(f"[{escape_markdown(text)}]({href})")
            elif text:
                self._append(text)
        elif tag in {"p", "div", "blockquote", "li"}:
            self._append("\n")

    def handle_data(self, data: str) -> None:
        if self.link_stack:
            self.link_stack[-1]["parts"].append(data)
        else:
            self._append(data)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _append(self, text: str) -> None:
        if self.link_stack:
            self.link_stack[-1]["parts"].append(text)
        else:
            self.parts.append(text)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def escape_markdown(value: str) -> str:
    return value.replace("[", r"\[").replace("]", r"\]")


def text_from_html(fragment: str) -> str:
    parser = _TextExtractor()
    parser.feed(fragment)
    return parser.text()


def html_to_markdown(fragment: str, base_url: str) -> str:
    parser = _MarkdownConverter(base_url)
    parser.feed(fragment)
    return parser.markdown()


def parse_thread_page(page_html: str, url: str) -> ThreadPage:
    title = extract_title(page_html) or "VOZ thread"
    posts = [parse_post(article, url) for article in extract_post_articles(page_html)]
    return ThreadPage(url=url, title=title, posts=posts)


def extract_title(page_html: str) -> str | None:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", page_html)
    if not match:
        return None
    return text_from_html(match.group(1))


def extract_post_articles(page_html: str) -> list[str]:
    pattern = re.compile(
        r"(?is)<article\b(?=[^>]*\bclass=(['\"])[^'\"]*\bmessage--post\b).*?</article>"
    )
    return [match.group(0) for match in pattern.finditer(page_html)]


def parse_post(article_html: str, base_url: str) -> Post:
    attrs = parse_attrs(article_html.partition(">")[0])
    author = attrs.get("data-author") or extract_author(article_html) or "Unknown"
    post_number = extract_post_number(article_html)
    post_url = extract_post_url(article_html, base_url)
    date_text, datetime_value = extract_time(article_html)
    body_html = extract_bbwrapper(article_html)
    body_markdown = html_to_markdown(body_html, base_url) if body_html else ""
    return Post(
        author=normalize_whitespace(author),
        date_text=date_text,
        datetime=datetime_value,
        post_number=post_number,
        post_url=post_url,
        body_markdown=body_markdown,
    )


def parse_attrs(tag_html: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r"""([\w:-]+)\s*=\s*(['"])(.*?)\2""", tag_html, re.S):
        attrs[match.group(1)] = html.unescape(match.group(3))
    return attrs


def extract_author(article_html: str) -> str | None:
    match = re.search(
        r"(?is)<h4\b[^>]*\bclass=(['\"])[^'\"]*\bmessage-name\b.*?</h4>",
        article_html,
    )
    return text_from_html(match.group(0)) if match else None


def extract_post_number(article_html: str) -> str | None:
    match = re.search(
        r"(?is)<a\b[^>]*\bclass=(['\"])[^'\"]*\bmessage-attribution-gadget\b[^>]*>(.*?)</a>",
        article_html,
    )
    return text_from_html(match.group(2)) if match else None


def extract_post_url(article_html: str, base_url: str) -> str | None:
    match = re.search(
        r"(?is)<a\b([^>]*\bclass=(['\"])[^'\"]*\bmessage-attribution-gadget\b[^>]*)>",
        article_html,
    )
    if not match:
        return None
    href = parse_attrs(match.group(1)).get("href")
    return urllib.parse.urljoin(base_url, href) if href else None


def extract_time(article_html: str) -> tuple[str | None, str | None]:
    match = re.search(r"(?is)<time\b([^>]*)>(.*?)</time>", article_html)
    if not match:
        return None, None
    attrs = parse_attrs(match.group(1))
    return text_from_html(match.group(2)), attrs.get("datetime")


def extract_bbwrapper(article_html: str) -> str | None:
    start = re.search(
        r"(?is)<div\b[^>]*\bclass=(['\"])[^'\"]*\bbbWrapper\b[^'\"]*\1[^>]*>",
        article_html,
    )
    if not start:
        return None
    depth = 1
    body_start = start.end()
    tag_pattern = re.compile(r"(?is)</?div\b[^>]*>")
    for match in tag_pattern.finditer(article_html, body_start):
        if match.group(0).lower().startswith("</div"):
            depth -= 1
            if depth == 0:
                return article_html[body_start : match.start()]
        else:
            depth += 1
    return article_html[body_start:]


def render_page_markdown(page: ThreadPage, page_number: int) -> str:
    lines = [
        f"# {page.title} - Page {page_number}",
        "",
        f"Source: {page.url}",
        "",
        f"Posts parsed: {len(page.posts)}",
        "",
    ]
    for index, post in enumerate(page.posts, start=1):
        label = post.post_number or f"Post {index}"
        lines.extend([f"## {label} - {post.author}", ""])
        meta: list[str] = []
        if post.date_text:
            meta.append(post.date_text)
        if post.datetime:
            meta.append(post.datetime)
        if post.post_url:
            meta.append(post.post_url)
        if meta:
            lines.extend([" | ".join(meta), ""])
        lines.extend([post.body_markdown or "_No body parsed._", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_failed_page_markdown(page_number: int, result: FetchResult) -> str:
    status = result.status if result.status is not None else "network-error"
    return (
        f"# VOZ Thread - Page {page_number}\n\n"
        "Fetch failed.\n\n"
        f"- Source: {result.url}\n"
        f"- Status: {status}\n"
        f"- Error: {result.error or 'unknown error'}\n"
    )


def export_page(output_dir: Path, page_number: int, result: FetchResult) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"page-{page_number:04d}.md"
    raw_path = raw_dir / f"page-{page_number:04d}.html"

    if result.body is None:
        markdown_path.write_text(render_failed_page_markdown(page_number, result), encoding="utf-8")
        return {
            "page": page_number,
            "url": result.url,
            "status": result.status,
            "title": None,
            "post_count": 0,
            "markdown_path": markdown_path.name,
            "raw_path": None,
            "error": result.error,
        }

    raw_path.write_text(result.body, encoding="utf-8")
    page = parse_thread_page(result.body, result.url)
    markdown_path.write_text(render_page_markdown(page, page_number), encoding="utf-8")
    return {
        "page": page_number,
        "url": result.url,
        "status": result.status,
        "title": page.title,
        "post_count": len(page.posts),
        "markdown_path": markdown_path.name,
        "raw_path": raw_path.relative_to(output_dir).as_posix(),
        "error": result.error,
    }


def summarize_entries(entries: Iterable[dict[str, object]]) -> dict[str, int]:
    items = list(entries)
    successful = sum(1 for entry in items if entry.get("status") == 200 and not entry.get("error"))
    failed = len(items) - successful
    return {
        "total_pages": len(items),
        "successful_pages": successful,
        "failed_pages": failed,
        "total_posts": sum(int(entry.get("post_count") or 0) for entry in items),
    }


def write_manifest(output_dir: Path, entries: list[dict[str, object]]) -> None:
    manifest = summarize_entries(entries)
    manifest["pages"] = entries
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_index(output_dir: Path, entries: list[dict[str, object]]) -> None:
    summary = summarize_entries(entries)
    lines = [
        "# VOZ Thread Backup Index",
        "",
        f"Total pages: {summary['total_pages']}",
        f"Successful pages: {summary['successful_pages']}",
        f"Failed pages: {summary['failed_pages']}",
        f"Total parsed posts: {summary['total_posts']}",
        "",
        "| Page | Status | Posts | Markdown | Raw | Error |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    for entry in entries:
        page_number = int(entry["page"])
        status_value = entry.get("status")
        status = "ok" if status_value == 200 and not entry.get("error") else f"failed ({status_value or 'network'})"
        markdown_path = str(entry["markdown_path"])
        raw_path = str(entry["raw_path"]) if entry.get("raw_path") else ""
        error = str(entry["error"] or "")
        lines.append(
            f"| {page_number} | {status} | {entry.get('post_count') or 0} | "
            f"[Page {page_number}]({markdown_path}) | "
            f"{f'[raw]({raw_path})' if raw_path else ''} | {error} |"
        )
    (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_url(url: str, retries: int, timeout: float) -> FetchResult:
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
                return FetchResult(url=url, status=response.status, body=body, error=None)
        except urllib.error.HTTPError as exc:
            body = None
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = None
            if exc.code in {403, 404, 410}:
                return FetchResult(url=url, status=exc.code, body=body, error=str(exc))
            last_error = str(exc)
        except urllib.error.URLError as exc:
            last_error = str(exc)
        except TimeoutError as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(min(2 * attempt, 10))
    return FetchResult(url=url, status=None, body=None, error=last_error or "fetch failed")


def backup_range(
    start: int,
    end: int,
    output_dir: Path,
    delay: float,
    retries: int,
    timeout: float,
    url_template: str,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for page_number in range(start, end + 1):
        url = url_template.format(page=page_number)
        print(f"Fetching page {page_number}: {url}", flush=True)
        result = fetch_url(url, retries=retries, timeout=timeout)
        entry = export_page(output_dir, page_number, result)
        entries.append(entry)
        print(
            f"  status={entry.get('status')} posts={entry.get('post_count')} "
            f"error={entry.get('error') or ''}",
            flush=True,
        )
        if page_number < end and delay > 0:
            time.sleep(delay)
    write_manifest(output_dir, entries)
    build_index(output_dir, entries)
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Back up a VOZ XenForo thread to Markdown.")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=1230)
    parser.add_argument("--output", type=Path, default=Path("backup"))
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--url-template", default=THREAD_URL_TEMPLATE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start < 1:
        raise SystemExit("--start must be at least 1")
    if args.end < args.start:
        raise SystemExit("--end must be greater than or equal to --start")
    entries = backup_range(
        start=args.start,
        end=args.end,
        output_dir=args.output,
        delay=args.delay,
        retries=args.retries,
        timeout=args.timeout,
        url_template=args.url_template,
    )
    summary = summarize_entries(entries)
    print(
        "Done: "
        f"{summary['successful_pages']} successful, "
        f"{summary['failed_pages']} failed, "
        f"{summary['total_posts']} posts parsed.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
