# ARCHITECTURE.md — Technical Design

## Data Flow Diagram

```
User clicks "Scrape Amazon Now"
        │
        ▼
  popup.js: checkCurrentPage()
        │  checks chrome.tabs for active URL
        │
        ▼
  popup.js: startScrape()
        │
        ├─► chrome.tabs.update → navigate to BESTSELLER_URL
        │         │
        │         ▼
        │   waitForTabLoad() — polls chrome.tabs.onUpdated
        │         │
        │         ▼
        │   sleep(2000) — wait for Amazon JS to render
        │         │
        │         ▼
        │   sendToContent(tab.id, { action: 'scrapeList' })
        │         │
        │         ▼
        │   content.js: scrapeListPage()
        │         │  reads .zg-item-immersion elements
        │         │  returns array of book objects (no description/publisher yet)
        │         │
        │         ▼
        │   popup.js receives books[]
        │
        └─► FOR EACH book.url:
                  │
                  ▼
            chrome.tabs.update → navigate to book URL
                  │
                  ▼
            waitForTabLoad()
                  │
                  ▼
            sleep(800–1500ms)  ← polite random delay
                  │
                  ▼
            sendToContent(tab.id, { action: 'scrapeBook' })
                  │
                  ▼
            content.js: scrapeBookPage()
                  │  reads description, publisher, publication_date
                  │  returns partial object
                  │
                  ▼
            popup.js merges into books[i]
                  │
                  ▼
            Update progress bar UI
        │
        ▼
  popup.js: cleanData(books)
        │  normalise types, trim strings, standardise dates
        │
        ▼
  popup.js: showStats()
        │  calculate avg rating, avg price, count
        │
        ▼
  User clicks "Download CSV"
        │
        ▼
  downloadCSV()
        │  builds CSV string
        │  Blob → URL.createObjectURL → <a>.click()
        │  triggers browser download dialog
        ▼
  kindle_paranormal_romance_bestsellers.csv saved
```

---

## Message Passing Contract

popup.js → content.js messages:
```js
{ action: 'scrapeList' }
// Response: { books: Book[] }

{ action: 'scrapeBook' }
// Response: { data: { description, publisher, publication_date } }
```

---

## Chrome Permissions Explained

| Permission   | Why needed |
|--------------|------------|
| `activeTab`  | Read and navigate the current tab |
| `scripting`  | Inject content.js into Amazon pages |
| `downloads`  | Trigger CSV file download |
| `host_permissions: amazon.com/*` | Allow content script on all Amazon pages |

---

## Extension vs Other Approaches

```
                    Chrome Extension   Flask App    Python Script
──────────────────────────────────────────────────────────────────
User install steps       3                5+             5+
Requires Python          No               Yes            Yes
Requires terminal        No               Yes            Yes
Sees JS-rendered HTML    Yes              No*            No*
Runs in real browser     Yes              No             No
One-click operation      Yes              Partial        No
Portable (share as zip)  Yes              No             Partial

* Unless using Playwright/Selenium, which adds more dependencies
```
