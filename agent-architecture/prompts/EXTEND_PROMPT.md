# EXTEND_PROMPT.md
# ─────────────────────────────────────────────────────────────
# USE THIS when adding a new feature.
# Fill in each section, then paste the whole thing to the agent.
# ─────────────────────────────────────────────────────────────

---

You are extending the **Kindle Bestseller Scraper** Chrome Extension.

Read `PROJECT.md`, `docs/SELECTORS.md`, and `docs/DECISIONS.md` before responding.

## Feature to add
[Describe what you want — e.g. "Add support for scraping page 2 and 3 of the
 bestseller list, not just page 1"]

## Why this is needed
[e.g. "Amazon shows 20 books per page, up to 100 total across 5 pages.
 We only get the top 20 right now."]

## Constraints
[e.g. "Must work without breaking the existing single-page scrape.
 The user should be able to choose how many pages to scrape: 1, 2, or 5."]

## Files that will likely need changes
[List them — e.g. popup.html (add page count selector), popup.js (loop pages),
 content.js (detect pagination links)]

## New fields in the schema (if any)
[e.g. "None — same 10 fields, just more rows"]
[OR: "Add 'series_name' field — string, extracted from subtitle on book page"]

---

**Instructions for the agent:**
1. Check DECISIONS.md — was this feature considered and rejected before?
2. If new CSS selectors are needed, add them to SELECTORS.md first
3. If a schema field is added, update PROJECT.md data schema
4. Implement the minimum change needed
5. Update the [ ] checklist in PROJECT.md to [x]
6. Add an ADR entry in DECISIONS.md explaining your approach

---
