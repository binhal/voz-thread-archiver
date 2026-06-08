from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


def clean_xml_string(value: str) -> str:
    return html.escape(value)


def split_translated_txt(content: str) -> list[tuple[str, list[str]]]:
    chapter_pattern = re.compile(r"^\s*(?:第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]|Chương\s*[0-9\s]+).*", re.IGNORECASE)
    chapters: list[tuple[str, list[str]]] = []
    current_title = "Giới thiệu & Tóm tắt"
    current_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or set(stripped) == {"-"}:
            continue
        if chapter_pattern.match(stripped) and len(stripped) < 100:
            if current_lines or not chapters:
                chapters.append((current_title, current_lines))
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(stripped)
    if current_lines or current_title != "Giới thiệu & Tóm tắt":
        chapters.append((current_title, current_lines))
    return chapters


def build_epub_from_text(content: str, epub_path: Path, title: str, author: str, language: str = "vi") -> None:
    chapters = split_translated_txt(content)
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as epub:
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>""",
        )
        epub.writestr(
            "OEBPS/style.css",
            """body { font-family: Georgia, 'Times New Roman', serif; margin: 5%; line-height: 1.6; text-align: justify; }
h1 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; }
p { text-indent: 2em; margin-top: 0.5em; margin-bottom: 0.5em; }""",
        )
        manifest_items: list[str] = []
        spine_items: list[str] = []
        navpoints: list[str] = []
        for i, (chapter_title, lines) in enumerate(chapters):
            filename = f"chapter_{i}.xhtml"
            paragraphs = "\n".join(f"<p>{clean_xml_string(line)}</p>" for line in lines)
            epub.writestr(
                f"OEBPS/{filename}",
                f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{clean_xml_string(chapter_title)}</title><link rel="stylesheet" href="style.css" type="text/css" /></head>
<body><h1>{clean_xml_string(chapter_title)}</h1>{paragraphs}</body>
</html>""",
            )
            manifest_items.append(f'<item id="ch_{i}" href="{filename}" media-type="application/xhtml+xml" />')
            spine_items.append(f'<itemref idref="ch_{i}" />')
            navpoints.append(
                f'<navPoint id="ch_{i}" playOrder="{i + 1}"><navLabel><text>{clean_xml_string(chapter_title)}</text></navLabel><content src="{filename}"/></navPoint>'
            )
        epub.writestr(
            "OEBPS/toc.ncx",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="urn:uuid:novel-tools"/></head>
<docTitle><text>{clean_xml_string(title)}</text></docTitle>
<navMap>{''.join(navpoints)}</navMap>
</ncx>""",
        )
        epub.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{clean_xml_string(title)}</dc:title>
<dc:creator>{clean_xml_string(author)}</dc:creator>
<dc:language>{clean_xml_string(language)}</dc:language>
<dc:identifier id="bookid">urn:uuid:novel-tools</dc:identifier>
</metadata>
<manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" /><item id="style" href="style.css" media-type="text/css" />{''.join(manifest_items)}</manifest>
<spine toc="ncx">{''.join(spine_items)}</spine>
</package>""",
        )
