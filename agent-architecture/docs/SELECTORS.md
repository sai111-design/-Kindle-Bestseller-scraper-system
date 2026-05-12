# SELECTORS.md — Amazon CSS Selector Reference
# Update this file whenever Amazon changes its layout.
# Every field must have a PRIMARY selector and at least one FALLBACK.

## Bestseller List Page
URL pattern: `/zgbs/digital-text/6734920011`

### Book Card Container
```
PRIMARY:  .zg-item-immersion
FALLBACK: [id^="gridItemRoot"]
```

### Rank
```
PRIMARY:  .zg-bdg-text
NOTE:     Strip "#" prefix from text content
```

### Title
```
PRIMARY:  ._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y
FALLBACK: .p13n-sc-line-clamp-2
FALLBACK: [class*="line-clamp"]
FALLBACK: a[title]  → use getAttribute('title'), not textContent
```

### Author
```
PRIMARY:  .a-size-small.a-color-secondary
```

### Rating
```
PRIMARY:  .a-icon-star-small  → use getAttribute('aria-label'), e.g. "4.7 out of 5 stars"
FALLBACK: [class*="star"]     → same aria-label approach
FALLBACK: .a-icon-star
PARSE:    regex /(\d+\.?\d*)\s*out of/  → extract float
```

### Review Count
```
PRIMARY:  a[href*="customerReviews"]  → textContent, e.g. "1,203"
PARSE:    strip commas → parseInt
```

### Price
```
PRIMARY:  .p13n-sc-price
FALLBACK: [class*="price"]
EDGE:     Check for "Free" text before parsing $
```

### Book URL
```
PRIMARY:  a[href*="/dp/"]  → getAttribute('href')
PARSE:    regex /\/dp\/([A-Z0-9]{10})/  → build https://www.amazon.com/dp/{ASIN}
NOTE:     Always strip tracking params, keep only ASIN URL
```

---

## Individual Book Page
URL pattern: `/dp/{ASIN}`

### Wait Signal (page ready indicator)
```
Wait for: #productTitle  → confirms page has loaded
```

### Description
```
PRIMARY:  #bookDescription_feature_div .a-expander-content
FALLBACK: #bookDescription_feature_div
FALLBACK: #productDescription
NOTE:     Click .a-expander-trigger first if present (expands "Read more")
CAP:      Truncate to 1500 characters
```

### Publisher
```
PRIMARY:  #detailBullets_feature_div li  → iterate, find li where text.includes('Publisher')
          → split on ':', take index[1], strip content in parentheses e.g. "(January 1, 2020)"
FALLBACK: #rpi-attribute-book_details-publisher .rpi-attribute-value
FALLBACK: [data-feature-name="bookDetails"] [class*="publisher"]
```

### Publication Date
```
PRIMARY:  #detailBullets_feature_div li  → find li where text.includes('Publication date')
          → split on ':', take index[1], standardize
FALLBACK: #rpi-attribute-book_details-publication_date .rpi-attribute-value
STANDARDIZE: See DATE_FORMATS below
```

---

## Date Standardization
Always output YYYY-MM-DD.

```
Input formats seen on Amazon:
  "May 5, 2015"     → 2015-05-05
  "May 2015"        → 2015-05-01  (assume 1st of month)
  "2020-03-10"      → 2020-03-10  (already correct)
  "March 10, 2020"  → 2020-03-10

Regex order to try:
  1. /^(\w+)\s+(\d{1,2}),\s+(\d{4})$/   full date
  2. /^(\w+)\s+(\d{4})$/                 month + year
  3. /^(\d{4})-(\d{2})-(\d{2})$/         ISO already
```

---

## Known Layout Variants
Amazon actively A/B tests. These variants have been observed:

| Variant | Symptom | Fix |
|---------|---------|-----|
| New grid layout | `.zg-item-immersion` missing | Try `[id^="gridItemRoot"]` |
| New detail page | `#detailBullets_feature_div` empty | Try `#rpi-attribute-*` selectors |
| Truncated description | `.a-expander-content` empty | Click `.a-expander-trigger` first |
| Logged-out price | Price shows "Sign in" | Return empty string |

---

## How to Update This File
When a selector breaks:
1. Open Chrome DevTools on the Amazon page
2. Inspect the element that stopped working
3. Find the new class name or ID
4. Add it as a new FALLBACK here (don't delete old ones — A/B tests rotate)
5. Update content.js to include the new fallback
