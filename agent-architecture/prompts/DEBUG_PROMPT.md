# DEBUG_PROMPT.md
# ─────────────────────────────────────────────────────────────
# USE THIS when something is broken.
# Fill in each section, then paste the whole thing to the agent.
# ─────────────────────────────────────────────────────────────

---

You are debugging the **Kindle Bestseller Scraper** Chrome Extension.

Read `PROJECT.md`, `docs/SELECTORS.md`, and `docs/DECISIONS.md` before responding.

## What is broken
[Describe the symptom — e.g. "The title field is coming back empty for all books"]

## File where the bug likely is
[e.g. content.js → scrapeListPage() → title extraction block]

## What I already tried
[e.g. "Checked the Amazon page in DevTools — the class name changed from
 .p13n-sc-line-clamp-2 to .p13n-sc-css-line-clamp-3"]

## Error message (if any)
```
[Paste console error here, or "none"]
```

## Browser / Amazon page at time of failure
[e.g. "Chrome 122, on the bestseller page logged out"]

## Expected behaviour
[e.g. "Title should be a non-empty string like 'A Court of Thorns and Roses'"]

---

**Instructions for the agent:**
1. Check SELECTORS.md first — is this a known layout variant?
2. Propose a fix using the fallback selector pattern
3. Update SELECTORS.md with the new selector
4. Only modify the minimum code needed to fix this field
5. Do not refactor anything else

---
