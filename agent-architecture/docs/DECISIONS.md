# DECISIONS.md — Architecture Decision Log
# Every major choice is recorded here with its tradeoffs.
# Before suggesting a change, check if it was already considered.

---

## ADR-001: Chrome Extension over Python Script
**Decision:** Build a Chrome Extension, not a Python script + Flask app.
**Reason:** The reviewer does not need to install Python, pip, or run a terminal.
            Load unpacked in Chrome → click → done. Zero friction.
**Tradeoff:** Cannot use Selenium or requests. Scraping is limited to what the
             browser's content script can read from the live DOM.
**Status:** Decided ✅

---

## ADR-002: Manifest V3 over V2
**Decision:** Use Manifest V3.
**Reason:** Chrome has deprecated MV2. MV2 extensions generate warnings and
            will stop working. MV3 is the current standard.
**Tradeoff:** Background pages replaced by service workers.
             Some older tutorials use MV2 — ignore them.
**Status:** Decided ✅

---

## ADR-003: Vanilla JS, No npm
**Decision:** No build tools, no bundler, no npm packages.
**Reason:** A Chrome Extension is a folder of files. Adding a build step
            (webpack, vite) means the reviewer needs Node.js installed.
            Vanilla JS keeps the extension loadable directly.
**Tradeoff:** No TypeScript type safety. No lodash helpers.
**Status:** Decided ✅

---

## ADR-004: Tab Navigation vs iframe Scraping
**Decision:** Navigate the active tab to each book URL, scrape, then navigate back.
**Reason:** iframes cannot be injected cross-origin. Fetching HTML with
            fetch() returns stripped HTML without Amazon's JS rendering.
            Tab navigation is the only reliable way to get fully rendered pages.
**Tradeoff:** Scraping is slow (~1–2 mins for 20 books). The tab visibly
             navigates. Not invisible to the user.
**Alternative considered:** Open each book in a background tab — rejected
             because Chrome throttles background tabs and it's harder to
             coordinate message passing.
**Status:** Decided ✅

---

## ADR-005: CSV Download via Blob over Backend
**Decision:** Generate CSV client-side using Blob + URL.createObjectURL.
**Reason:** No server required. Works entirely in-browser.
            The CSV is identical to what a server would produce.
**Tradeoff:** Cannot write directly to the filesystem — goes to Downloads folder.
**Status:** Decided ✅

---

## ADR-006: Random Delay Between Requests
**Decision:** Add 800–1500ms random delay between each book page visit.
**Reason:** Amazon rate-limits and blocks IPs/sessions that hit pages too fast.
            A random delay mimics human browsing patterns.
**Tradeoff:** Makes scraping slower. 20 books ≈ 2–4 minutes total.
**Status:** Decided ✅

---

## Considered and Rejected

| Idea | Why Rejected |
|------|-------------|
| Playwright / Selenium | Requires Python + browser driver install |
| Background service worker scraping | Chrome throttles background tabs |
| IndexedDB for persistent cache | Overkill for a single scrape session |
| Google Sheets API export | Requires OAuth — too complex for this scope |
| Puppeteer + Node server | Adds Node.js dependency, defeats the point |
