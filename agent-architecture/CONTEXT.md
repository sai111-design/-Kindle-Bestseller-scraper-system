# CONTEXT.md
## Agent Context File — Amazon Kindle Scraping Agent
> **What this file is:** This is the single file you edit to retarget the agent at any
> Amazon category. The agent reads this at startup. Nothing in the code needs to change —
> only this file. Think of it as the agent's "assignment brief."

---

## 1. Mission

Extract structured bestseller data from an Amazon Kindle category page and all linked
individual product pages, then export a clean, analysis-ready dataset.

---

## 2. Target

```
CATEGORY_NAME   : Paranormal Romance
CATEGORY_URL    : https://www.amazon.com/Best-Sellers-Kindle-Store-Paranormal-Romance/zgbs/digital-text/6734920011
PAGINATION      : single page (top 20 books shown by default)
PLATFORM        : Amazon.com (US)
```

> **To retarget:** Replace `CATEGORY_NAME` and `CATEGORY_URL` above with any
> Amazon Kindle bestseller category. Everything else cascades automatically.
>
> Example swap targets:
> - Kindle > Fantasy:         `.../zgbs/digital-text/16272011`
> - Kindle > Mystery:         `.../zgbs/digital-text/6734923011`
> - Kindle > Science Fiction: `.../zgbs/digital-text/6734937011`

---

## 3. Data Schema

These are the exact fields the agent must populate for every book.
If a field is unavailable, leave it blank — never guess or hallucinate.

### 3a. List Page Fields
Extracted from the main bestseller grid.

| Field         | Type    | Source Element                          | Cleaning Rule                        |
|---------------|---------|-----------------------------------------|--------------------------------------|
| `rank`        | integer | `.zg-bdg-text`                          | Strip `#`, cast to int               |
| `title`       | string  | `._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y