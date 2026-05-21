import os
import re
import zipfile
import html
import sys

def clean_xml_string(s):
    """Escapes characters for XML compatibility."""
    return html.escape(s)

def build_epub(txt_path, epub_path, title="Thái Bình Lệnh", author="Diêm ZK"):
    print(f"[*] Đang đọc file nguồn: {txt_path}...")
    
    # Đọc file truyện với các bảng mã dự phòng
    content = ""
    for encoding in ['gb18030', 'utf-8-sig', 'utf-8', 'gbk', 'cp936']:
        try:
            with open(txt_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"[+] Đọc thành công bằng bảng mã: {encoding}")
            break
        except UnicodeDecodeError:
            continue
            
    if not content:
        print("[-] Lỗi: Không thể giải mã file TXT bằng bất kỳ bảng mã thông dụng nào!")
        return False

    # Tách dòng
    lines = content.splitlines()
    print(f"[*] Tổng số dòng đọc được: {len(lines)}")

    # Khởi tạo danh sách chương
    chapters = []
    current_chapter_title = "Giới thiệu & Tóm tắt"
    current_chapter_content = []

    # Regex nhận diện tiêu đề chương thông minh (hỗ trợ cả tiếng Trung và tiếng Việt)
    # Ví dụ: "第1章", "第一章", "Chương 82", v.v.
    chapter_pattern = re.compile(r'^\s*(?:第\s*[0-9一二三四五六七八九十百千万\s]+\s*[章节集]|Chương\s*[0-9\s]+).*', re.IGNORECASE)

    print("[*] Đang phân tích cấu trúc chương...")
    for idx, line in enumerate(lines):
        striped_line = line.strip()
        if not striped_line:
            continue
            
        # Kiểm tra xem dòng này có phải là tiêu đề chương mới không
        match = chapter_pattern.match(striped_line)
        # Bỏ qua các tiêu đề trùng lặp hoặc dòng quá dài nhầm lẫn
        if match and len(striped_line) < 100:
            # Lưu chương cũ trước khi chuyển sang chương mới
            if current_chapter_content or len(chapters) == 0:
                chapters.append((current_chapter_title, current_chapter_content))
            current_chapter_title = striped_line
            current_chapter_content = []
            if len(chapters) % 50 == 0 and len(chapters) > 0:
                print(f"    -> Đã nhận diện đến chương {len(chapters)}: {current_chapter_title}")
        else:
            # Dòng nội dung bình thường, lọc các dòng quảng cáo/rác của ebook
            if "ixdzs" not in striped_line and "爱下电子书" not in striped_line:
                current_chapter_content.append(striped_line)

    # Đóng chương cuối cùng
    if current_chapter_content or current_chapter_title != "Giới thiệu & Tóm tắt":
        chapters.append((current_chapter_title, current_chapter_content))

    print(f"[+] Phân tích hoàn tất! Tổng cộng phát hiện: {len(chapters)} chương.")

    # Đóng gói thành file EPUB (Thực chất là file zip đặc biệt)
    print(f"[*] Đang đóng gói file EPUB tại: {epub_path}...")
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        
        # 1. Ghi file mimetype đầu tiên và KHÔNG được nén (STORED) để đạt chuẩn EPUB
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        
        # 2. Ghi thư mục META-INF/container.xml
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebpssoap+xml-media-type" />
  </rootfiles>
</container>"""
        # Sửa lại media-type chuẩn
        container_xml = container_xml.replace("oebpssoap", "oebps-package")
        epub.writestr("META-INF/container.xml", container_xml)

        # 3. Tạo Stylesheet CSS chất lượng cao để hiển thị đẹp mắt
        style_css = """body {
    font-family: "Georgia", "Times New Roman", "DejaVu Serif", serif;
    margin: 5% 5% 5% 5%;
    line-height: 1.6;
    text-align: justify;
    font-size: 1.1em;
    color: #111111;
}
h1, h2, h3 {
    text-align: center;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 1em;
    color: #8b0000;
    line-height: 1.2;
}
p {
    text-indent: 2em;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
}
.preface {
    font-style: italic;
    color: #555555;
    background-color: #f9f9f9;
    padding: 15px;
    border-left: 4px solid #8b0000;
    border-radius: 4px;
}
"""
        epub.writestr("OEBPS/style.css", style_css)

        # 4. Ghi từng chương thành các file XHTML
        spine_items = []
        manifest_items = []
        ncx_navpoints = []

        for i, (ch_title, ch_lines) in enumerate(chapters):
            ch_filename = f"chapter_{i}.xhtml"
            
            # Tạo nội dung XHTML cho chương
            html_lines = []
            for line in ch_lines:
                escaped_line = clean_xml_string(line)
                # Đánh dấu đoạn giới thiệu ở chương đầu để áp dụng CSS đặc biệt
                if i == 0:
                    html_lines.append(f'<p class="preface">{escaped_line}</p>')
                else:
                    html_lines.append(f'<p>{escaped_line}</p>')
            
            xhtml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{clean_xml_string(ch_title)}</title>
  <link rel="stylesheet" href="style.css" type="text/css" />
</head>
<body>
  <h1>{clean_xml_string(ch_title)}</h1>
  {"".join(html_lines)}
</body>
</html>"""
            
            epub.writestr(f"OEBPS/{ch_filename}", xhtml_content)
            
            # Đăng ký thông tin manifest và spine
            manifest_items.append(f'<item id="ch_{i}" href="{ch_filename}" media-type="application/xhtml+xml" />')
            spine_items.append(f'<itemref idref="ch_{i}" />')
            
            # Đăng ký thông tin cho mục lục NCX
            ncx_navpoints.append(f"""    <navPoint id="ch_{i}" playOrder="{i+1}">
      <navLabel>
        <text>{clean_xml_string(ch_title)}</text>
      </navLabel>
      <content src="{ch_filename}"/>
    </navPoint>""")

        # 5. Ghi file toc.ncx (Mục lục cấu trúc của EPUB)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD XHTML 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:voz-thread-archiver-tai-binh-lenh"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{clean_xml_string(title)}</text>
  </docTitle>
  <navMap>
{"\n".join(ncx_navpoints)}
  </navMap>
</ncx>"""
        epub.writestr("OEBPS/toc.ncx", toc_ncx)

        # 6. Ghi file content.opf (Khai báo siêu dữ liệu của EPUB)
        manifest_str = "\n    ".join(manifest_items)
        spine_str = "\n    ".join(spine_items)
        
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{clean_xml_string(title)}</dc:title>
    <dc:creator opf:role="aut">{clean_xml_string(author)}</dc:creator>
    <dc:language>zh</dc:language>
    <dc:identifier id="bookid">urn:uuid:voz-thread-archiver-tai-binh-lenh</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
    <item id="style" href="style.css" media-type="text/css" />
    {manifest_str}
  </manifest>
  <spine toc="ncx">
    {spine_str}
  </spine>
</package>"""
        epub.writestr("OEBPS/content.opf", content_opf)

    print(f"[+] Xong! File EPUB hoàn chỉnh đã được tạo thành công: {epub_path}")
    print("[*] Bạn có thể kéo thả file này vào Apple Books, Moon+ Reader, Koodo, Kindle hoặc bất cứ trình đọc nào!")
    return True

if __name__ == "__main__":
    txt_file = os.path.join("books", "太平令.txt")
    epub_file = os.path.join("books", "太平令.epub")
    
    if not os.path.exists(txt_file):
        # Fallback to root directory if books folder is not used
        txt_file = "太平令.txt"
        epub_file = "太平令.epub"
        
    if not os.path.exists(txt_file):
        print(f"[-] Không tìm thấy file nguồn '{txt_file}' ở thư mục 'books/' hoặc thư mục hiện tại.")
        sys.exit(1)
        
    build_epub(txt_file, epub_file)
