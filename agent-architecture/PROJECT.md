# PROJECT.md — Agent Master Context
# Feed this file first in every new session.

## Project Identity
- **Name:** Kindle Bestseller Scraper
- **Owner:** Pocket FM Internship Assignment
- **Version:** 2.0
- **Goal:** Extract Amazon Kindle bestseller data from any category into a structured CSV
- **Delivery format:** Chrome Extension (no Python, no server, no install)

---

## Tech Stack
| Layer       | Choice              | Reason                                         |
|-------------|---------------------|------------------------------------------------|
| Runtime     | Chrome Extension MV3 | Zero setup for end user                       |
| Scraping    | content.js (DOM)    | Runs inside real browser, sees JS-rendered HTML|
| Orchestration | popup.js          | Controls tab navigation and data flow          |
| Output      | CSV download (Blob) | Native browser API, no backend needed          |
| Styling     | Vanilla CSS         | No build step, single-file popup               |

---

## Repository Structure
```
kindle-scraper-extension/
├── manifest.json        # Chrome MV3 config — permissions, entry points
├── popup.html           # Extension UI — tabbed (Scrape / Schedule)
├── popup.js             # UI logic + scraping orchestration + pagination
├── content.js           # DOM scraping — injected into Amazon pages
├── background.js        # Service worker — scheduled scraping via alarms
├── icon.png             # 48x48 extension icon
│
├── docs/
│   ├── ARCHITECTURE.md  # This file's companion — deep technical design
│   ├── SELECTORS.md     # All Amazon CSS selectors with fallbacks
│   └── DECISIONS.md     # Why each tech choice was made
│
└── prompts/
    ├── INIT_PROMPT.md   # First prompt to give any new agent session
    ├── DEBUG_PROMPT.md  # Prompt template when something breaks
    └── EXTEND_PROMPT.md # Prompt to add new features
```

---

## Data Schema (what gets extracted)
```
rank             : string   — "#1", "#2" etc, stripped of #
title            : string   — Book title
author           : string   — Author name
rating           : float    — e.g. 4.7
num_reviews      : integer  — e.g. 98234
price            : string   — "$8.99" or "Free"
url              : string   — https://www.amazon.com/dp/ASIN
description      : string   — Max 1500 chars, from book page
publisher        : string   — Publisher name
publication_date : string   — YYYY-MM-DD standardised
```

---

## Current Status
- [x] Chrome Extension scaffold built
- [x] List page scraping (content.js)
- [x] Individual book page scraping
- [x] CSV download
- [x] Popup UI with progress bar + stats
- [x] Pagination support (page 2, 3+ of bestseller list)
- [x] Export to Google Sheets (TSV clipboard copy)
- [x] Category switcher (12 Kindle genres)
- [x] Background service worker for scheduled scraping

---

## Constraints the Agent Must Respect
1. Manifest V3 only — no background pages, use service workers
2. No external libraries — pure vanilla JS in all extension files
3. No server / backend — everything runs client-side
4. Polite scraping — random delay 800–1500ms between book page requests
5. Graceful degradation — missing fields = empty string, never crash
6. Amazon selector fallbacks — always try 2–3 selectors per field
