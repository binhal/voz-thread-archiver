#!/usr/bin/env python3
import json
import re
import html
import time
import random
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://metruyenchuvn.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

def fetch_url(url, retries=3, min_delay=0.1, max_delay=0.3):
    if min_delay > 0:
        time.sleep(random.uniform(min_delay, max_delay))
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error fetching {url}: {e}")
                return None
            time.sleep(1 + attempt)
    return None

def get_book_metadata_and_chap_pages(story_url, min_delay=0.1, max_delay=0.3):
    content = fetch_url(story_url, min_delay=min_delay, max_delay=max_delay)
    if not content:
        raise RuntimeError("Failed to fetch story main page")
    
    # Extract book id (e.g. bid = '34416' or rid = '34416')
    bid_match = re.search(r"var\ (?:bid|rid)\ =\ '(\d+)';", content)
    if not bid_match:
        bid_match = re.search(r'name="bid"\ value="(\d+)"', content)
    if not bid_match:
        raise RuntimeError("Could not find book ID (bid/rid) in story page")
    bid = bid_match.group(1)
    
    # Extract total chapter pages (e.g. page(34416, 14))
    page_matches = re.findall(r"page\(\d+,\s*(\d+)\)", content)
    max_page = max([int(p) for p in page_matches]) if page_matches else 1
    
    print(f"Book ID: {bid}, Total Chapter Pages: {max_page}")
    return bid, max_page

def fetch_chapter_links_from_page(bid, page_num, min_delay=0.1, max_delay=0.3):
    url = f"{BASE_URL}/get/listchap/{bid}?page={page_num}"
    raw = fetch_url(url, min_delay=min_delay, max_delay=max_delay)
    if not raw:
        return []
    try:
        data = json.loads(raw).get("data", "")
    except Exception:
        data = raw
        
    links = re.findall(r"<a\s+href=['\"]([^'\"]+)['\"]>([^<]+)</a>", data)
    chaps = []
    for href, text in links:
        if "/chuong-" in href:
            chaps.append((href, text.strip()))
    return chaps

def clean_chapter_html(html_str):
    # Extract chapter title
    title_match = re.search(r'<h2 class="current-chapter">\s*<a[^>]*>(.*?)</a>', html_str, re.DOTALL)
    if not title_match:
        title_match = re.search(r'<title>(.*?)</title>', html_str)
    
    title = ""
    if title_match:
        title = html.unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip())
        if " - " in title:
            title = title.split(" - ")[-1].strip()

    # Extract chapter content inside <div class="truyen">...</div>
    content_match = re.search(r'<div class="truyen">(.*?)</div>', html_str, re.DOTALL)
    if not content_match:
        return title, ""
    
    raw_content = content_match.group(1)
    
    # Replace <br> or <p> tags with newlines
    raw_content = re.sub(r'<br\s*/?>', '\n', raw_content, flags=re.IGNORECASE)
    raw_content = re.sub(r'</p>', '\n\n', raw_content, flags=re.IGNORECASE)
    raw_content = re.sub(r'<p[^>]*>', '', raw_content, flags=re.IGNORECASE)
    
    # Remove remaining HTML tags
    cleaned = re.sub(r'<[^>]+>', '', raw_content)
    
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    
    # Normalize multiple blank lines
    lines = [line.strip() for line in cleaned.splitlines()]
    normalized_lines = []
    blank = False
    for l in lines:
        if not l:
            if not blank:
                normalized_lines.append("")
                blank = True
        else:
            normalized_lines.append(l)
            blank = False
            
    final_text = "\n".join(normalized_lines).strip()
    return title, final_text

def download_chapter(index, href, title_from_list, chapters_dir, min_delay=0.1, max_delay=0.3):
    out_file = chapters_dir / f"chapter_{index:04d}.txt"
    if out_file.exists() and out_file.stat().st_size > 100:
        return True

    full_url = urllib.parse.urljoin(BASE_URL, href)
    html_content = fetch_url(full_url, min_delay=min_delay, max_delay=max_delay)
    if not html_content:
        print(f"Failed chapter {index}: {href}")
        return False
        
    title, body = clean_chapter_html(html_content)
    if not title:
        title = title_from_list
    if not title.startswith("Chương"):
        title = f"Chương {index}: {title}"
        
    text_to_write = f"{title}\n\n{body}\n"
    out_file.write_text(text_to_write, encoding="utf-8")
    return True

def main():
    parser = argparse.ArgumentParser(description="Safer crawler for metruyenchuvn.com with rate limiting.")
    parser.add_argument("--url", default="https://metruyenchuvn.com/dai-quan-gia-la-ma-hoang", help="Story URL")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent workers (default: 3)")
    parser.add_argument("--min-delay", type=float, default=0.2, help="Minimum delay per request in seconds (default: 0.2)")
    parser.add_argument("--max-delay", type=float, default=0.5, help="Maximum delay per request in seconds (default: 0.5)")
    args = parser.parse_args()

    slug = args.url.rstrip("/").split("/")[-1]
    output_dir = Path(f"/home/le-an-binh/Data/Projects/voz-thread-archiver/library/{slug}")
    chapters_dir = output_dir / "chapters" / "vi"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    bid, max_page = get_book_metadata_and_chap_pages(args.url, min_delay=args.min_delay, max_delay=args.max_delay)
    
    print(f"Fetching all chapter links with {args.workers} workers and {args.min_delay}-{args.max_delay}s delay...")
    all_chaps = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_chapter_links_from_page, bid, p, args.min_delay, args.max_delay): p for p in range(1, max_page + 1)}
        page_results = {}
        for future in as_completed(futures):
            p = futures[future]
            try:
                chaps = future.result()
                page_results[p] = chaps
            except Exception as e:
                print(f"Error fetching list page {p}: {e}")
                
    for p in sorted(page_results.keys()):
        all_chaps.extend(page_results[p])
        
    print(f"Total chapter links collected: {len(all_chaps)}")
    
    chap_tasks = []
    for idx, (href, title_from_list) in enumerate(all_chaps, start=1):
        num_match = re.search(r"chuong-(\d+)-", href)
        chap_num = int(num_match.group(1)) if num_match else idx
        chap_tasks.append((chap_num, href, title_from_list))
        
    print(f"Downloading {len(chap_tasks)} chapters with {args.workers} workers...")
    start_time = time.time()
    success_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_chapter, cnum, href, t, chapters_dir, args.min_delay, args.max_delay): cnum for cnum, href, t in chap_tasks}
        for future in as_completed(futures):
            cnum = futures[future]
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"Exception downloading chapter {cnum}: {e}")
                
    elapsed = time.time() - start_time
    print(f"Done downloading {success_count}/{len(chap_tasks)} chapters in {elapsed:.2f} seconds!")

if __name__ == "__main__":
    main()

