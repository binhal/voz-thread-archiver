# VOZ Thread Backup Design

## Goal

Back up the VOZ XenForo thread at `https://voz.vn/t/ban-luan-ve-cac-truyen-tien-hiep-kiem-hiep-ky-ao-ver-nextvoz.1421/page-{x}` for pages 1 through 1230 into per-page Markdown files.

## Output

- `backup/page-0001.md` through `backup/page-1230.md` for readable Markdown exports.
- `backup/raw/page-0001.html` through `backup/raw/page-1230.html` for raw source preservation when fetches succeed.
- `backup/index.md` linking each page and summarizing status.
- `backup/manifest.json` recording URL, HTTP status, title, parsed post count, raw path, Markdown path, and errors.

## Architecture

A standalone Python script uses the standard library only. It fetches each page with a browser-like user agent, retries transient failures, writes raw HTML when available, parses XenForo post articles into Markdown, and continues through all requested pages even if some pages are missing or blocked.

The parser is intentionally conservative. It extracts post article blocks, author/date/post number metadata, and the `bbWrapper` post body. The raw HTML cache is the source of truth if the Markdown conversion ever needs to be improved.

## Error Handling

HTTP and network failures are recorded per page in the manifest. A failed page gets a small Markdown stub instead of aborting the whole backup. The script only exits nonzero for configuration errors or output write failures.

## Testing

Unit tests cover post extraction, Markdown rendering, manifest/index generation, and failed-page stub behavior using local sample HTML. Live network backup is verified by running the tool after implementation.
