---
name: novel-translator
description: "Translate configured Chinese web novels into polished Vietnamese using book-specific harnesses"
---

<objective>
Translate a chapter for a selected book workspace under `library/<book-id>/`, using that book's `book.yaml`, `harness.md`, and optional context files.
</objective>

<context>
$ARGUMENTS: Must include a book id and chapter index, for example `--book thai-binh-lenh --chapter 563`.
</context>

<process>
1. Resolve context:
   `python -m novel_tools context --book <book-id> --chapter <chapter>`
2. If the Chinese source chapter is missing, extract it:
   `python -m novel_tools extract --book <book-id> --chapter <chapter>`
3. Translate `chapters/cn/chapter_XXXX_cn.txt` into `chapters/vi/chapter_XXXX.txt` inside the selected book workspace.
4. Follow the selected book's `harness.md`, `glossary.tsv`, `characters.md`, and `continuity.md`.
5. Preserve paragraph boundaries. Remove author notes, vote requests, unrelated updates, and translator notes.
6. Use target format:
   - Line 1: `Chương <global_index>: <Title>`
   - Line 2: empty
   - Line 3+: translated paragraphs
7. Review source-to-target coverage, pronouns, terminology, and formatting.
8. Register progress:
   `python -m novel_tools register --book <book-id> --chapter <chapter>`
9. Compile after a batch:
   `python -m novel_tools compile --book <book-id>`
10. Run verification:
    `python -m novel_tools inspect --book <book-id>`
</process>

<security_notes>
- Never write outside the selected `library/<book-id>/` workspace unless the user explicitly asks.
- Never place API keys in files.
- Regenerate progress JSON after any translated chapter edit.
</security_notes>
