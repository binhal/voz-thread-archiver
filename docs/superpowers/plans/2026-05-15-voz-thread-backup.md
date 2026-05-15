# VOZ Thread Backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python backup tool that exports VOZ thread pages 1 through 1230 into split Markdown files plus raw HTML and a manifest.

**Architecture:** `voz_thread_backup.py` owns fetching, parsing, Markdown rendering, and CLI orchestration. `test_voz_thread_backup.py` uses local HTML fixtures to verify behavior without network access.

**Tech Stack:** Python 3 standard library, `unittest`, `urllib.request`, `html.parser`, `json`, `pathlib`.

---

### Task 1: Parser and Markdown Rendering

**Files:**
- Create: `test_voz_thread_backup.py`
- Create: `voz_thread_backup.py`

- [ ] Write tests for parsing XenForo-like post articles into author/date/post/body fields.
- [ ] Run `python -m unittest test_voz_thread_backup.py` and verify parser tests fail because the module does not exist.
- [ ] Implement minimal parser and Markdown renderer.
- [ ] Run `python -m unittest test_voz_thread_backup.py` and verify parser tests pass.

### Task 2: Per-Page Export Artifacts

**Files:**
- Modify: `test_voz_thread_backup.py`
- Modify: `voz_thread_backup.py`

- [ ] Write tests for successful page export, failed-page stub output, manifest entries, and index generation.
- [ ] Run `python -m unittest test_voz_thread_backup.py` and verify export tests fail because export orchestration is missing.
- [ ] Implement page writing, manifest writing, index writing, retry-aware fetching, and CLI arguments.
- [ ] Run `python -m unittest test_voz_thread_backup.py` and verify all tests pass.

### Task 3: Live Backup

**Files:**
- Generated: `backup/*.md`
- Generated: `backup/raw/*.html`
- Generated: `backup/manifest.json`

- [ ] Run `python voz_thread_backup.py --start 1 --end 1230 --output backup --delay 1.5 --retries 3`.
- [ ] Inspect `backup/manifest.json` and `backup/index.md`.
- [ ] Report total successful pages, failed pages, and output paths.
