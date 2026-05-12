// content.js — injected into Amazon pages
// Scrapes the bestseller list page (with pagination) and individual book pages

(function() {

  // ── Helpers ──────────────────────────────────────────────

  function clean(t) {
    return (t || '').replace(/\s+/g, ' ').trim();
  }

  function parseRating(t) {
    if (!t) return '';
    const m = t.match(/(\d+\.?\d*)\s*out of/);
    if (m) return parseFloat(m[1]);
    const m2 = t.match(/(\d+\.?\d*)/);
    return m2 ? parseFloat(m2[1]) : '';
  }

  function parseReviews(t) {
    if (!t) return '';
    const n = parseInt(t.replace(/,/g, ''));
    return isNaN(n) ? '' : n;
  }

  function parsePrice(t) {
    if (!t) return '';
    if (t.toLowerCase().includes('free')) return 'Free';
    const m = t.match(/\$[\d,.]+/);
    return m ? m[0] : clean(t);
  }

  function standardizeDate(t) {
    if (!t) return '';
    t = clean(t);
    const formats = [
      { re: /^(\w+)\s+(\d{1,2}),\s+(\d{4})$/, fn: (m) => new Date(`${m[1]} ${m[2]}, ${m[3]}`) },
      { re: /^(\w+)\s+(\d{4})$/,               fn: (m) => new Date(`${m[1]} 1, ${m[2]}`) },
      { re: /^(\d{4})-(\d{2})-(\d{2})$/,       fn: (m) => new Date(`${m[1]}-${m[2]}-${m[3]}`) },
    ];
    for (const { re, fn } of formats) {
      const m = t.match(re);
      if (m) {
        const d = fn(m);
        if (!isNaN(d)) return d.toISOString().slice(0, 10);
      }
    }
    return t;
  }

  function qs(el, sel) {
    try { return el.querySelector(sel); } catch { return null; }
  }
  function qsa(el, sel) {
    try { return [...el.querySelectorAll(sel)]; } catch { return []; }
  }
  function txt(el, sel) {
    const found = qs(el, sel);
    return found ? clean(found.textContent) : '';
  }

  // ── Scrape list page ──────────────────────────────────────

  function scrapeListPage() {
    // Try primary selector, then fallback for new grid layout
    let items = qsa(document, '.zg-item-immersion');
    if (!items.length) {
      items = qsa(document, '[id^="gridItemRoot"]');
    }
    if (!items.length) return null; // not on the right page

    const books = items.map(item => {
      // Rank
      const rank = txt(item, '.zg-bdg-text').replace('#', '');

      // Title — try multiple selectors
      let title = '';
      for (const sel of [
        '._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y',
        '.p13n-sc-line-clamp-2',
        '.p13n-sc-line-clamp-3',
        '.p13n-sc-line-clamp-4',
        '[class*="line-clamp"]',
      ]) {
        const el = qs(item, sel);
        if (el && el.textContent.trim()) { title = clean(el.textContent); break; }
      }
      if (!title) {
        const a = qs(item, 'a[title]');
        if (a) title = clean(a.getAttribute('title') || a.textContent);
      }

      // Author
      let author = '';
      const authorSkip = ['kindle edition', 'paperback', 'hardcover', 'audiobook',
                          'audio cd', 'board book', 'mass market paperback',
                          'formats available', 'kindle unlimited'];
      
      const authEls = qsa(item, 'a.a-link-child, .a-row.a-size-small a, span.a-size-small.a-color-base, .a-row.a-size-small > .a-color-secondary');
      for (const el of authEls) {
        const candidate = clean(el.textContent);
        const lower = candidate.toLowerCase();
        if (candidate && !authorSkip.includes(lower) && !authorSkip.some(skip => lower.includes(skip))) {
          author = candidate;
          break;
        }
      }

      // Fallback
      if (!author) {
        const spanEls = qsa(item, 'span.a-size-small');
        for (const span of spanEls) {
          const text = clean(span.textContent);
          const lower = text.toLowerCase();
          if (text && !authorSkip.includes(lower) && !authorSkip.some(skip => lower.includes(skip)) && isNaN(parseInt(text.replace(/,/g, '')))) {
            author = text;
            break;
          }
        }
      }

      // Rating — prefer aria-label which has "X out of 5 stars"
      let rating = '';
      for (const sel of ['.a-icon-star-small', '[class*="star"]', '.a-icon-star']) {
        const el = qs(item, sel);
        if (el) {
          rating = parseRating(el.getAttribute('aria-label') || el.textContent);
          if (rating !== '') break;
        }
      }

      // Reviews
      const revEl = qs(item, 'a[href*="customerReviews"]');
      const num_reviews = revEl ? parseReviews(revEl.textContent) : '';

      // Price
      const priceEl = qs(item, '.p13n-sc-price') || qs(item, '[class*="price"]');
      const price = priceEl ? parsePrice(priceEl.textContent) : '';

      // URL — clean ASIN-based link
      const linkEl = qs(item, 'a[href*="/dp/"]');
      let url = '';
      if (linkEl) {
        const href = linkEl.getAttribute('href') || '';
        const asin = href.match(/\/dp\/([A-Z0-9]{10})/);
        url = asin ? `https://www.amazon.com/dp/${asin[1]}` : href;
      }

      return { rank, title, author, rating, num_reviews, price, url,
               description: '', publisher: '', publication_date: '' };
    });

    return books;
  }

  // ── Get pagination info ─────────────────────────────────────

  function getPaginationInfo() {
    // Find "next page" link on bestseller list
    const nextLinks = [
      // Primary: pagination next button
      qs(document, 'li.a-last a'),
      qs(document, 'ul.a-pagination li.a-last a'),
      // Fallback: look for page 2 link
      qs(document, 'ul.a-pagination li:not(.a-selected):not(.a-disabled):last-child a'),
      // Another pattern: "Next Page" text link
      ...qsa(document, 'a').filter(a =>
        a.textContent.trim().toLowerCase() === 'next' ||
        a.textContent.trim().toLowerCase() === 'next page'
      ),
    ].filter(Boolean);

    // Current page number
    const currentPageEl = qs(document, 'ul.a-pagination li.a-selected a');
    const currentPage = currentPageEl ? parseInt(currentPageEl.textContent.trim()) : 1;

    // Also look for page links to determine total pages
    const pageLinks = qsa(document, 'ul.a-pagination li a');
    const pageNumbers = pageLinks
      .map(a => parseInt(a.textContent.trim()))
      .filter(n => !isNaN(n));
    const totalPages = pageNumbers.length ? Math.max(...pageNumbers) : 1;

    let nextPageUrl = '';
    if (nextLinks.length > 0) {
      const href = nextLinks[0].getAttribute('href') || '';
      if (href.startsWith('http')) {
        nextPageUrl = href;
      } else if (href.startsWith('/')) {
        nextPageUrl = 'https://www.amazon.com' + href;
      }
    }

    return {
      currentPage,
      totalPages,
      nextPageUrl,
      hasNextPage: !!nextPageUrl,
    };
  }

  // ── Scrape individual book page ───────────────────────────

  function scrapeBookPage() {
    const result = { description: '', publisher: '', publication_date: '' };

    // Try to click "Read more" expander if present
    const expander = qs(document, '#bookDescription_feature_div .a-expander-trigger');
    if (expander) {
      try { expander.click(); } catch {}
    }

    // Description — try to read expanded content
    for (const sel of [
      '#bookDescription_feature_div .a-expander-content',
      '#bookDescription_feature_div',
      '#productDescription',
    ]) {
      const el = qs(document, sel);
      if (el && el.textContent.trim()) {
        result.description = clean(el.textContent).slice(0, 1500);
        break;
      }
    }

    // Publisher & Publication Date from detail bullets
    const bullets = qsa(document, '#detailBullets_feature_div li');
    for (const li of bullets) {
      const t = clean(li.textContent);
      const lower = t.toLowerCase();
      if (lower.includes('publisher')) {
        const parts = t.split(':');
        if (parts.length >= 2) {
          result.publisher = parts.slice(1).join(':').replace(/\(.*?\)/g, '').trim();
        }
      }
      if (lower.includes('publication date')) {
        const parts = t.split(':');
        if (parts.length >= 2) {
          result.publication_date = standardizeDate(parts.slice(1).join(':').trim());
        }
      }
    }

    // Fallback: newer Amazon layout
    if (!result.publisher) {
      const el = qs(document, '#rpi-attribute-book_details-publisher .rpi-attribute-value');
      if (el) result.publisher = clean(el.textContent);
    }
    if (!result.publication_date) {
      const el = qs(document, '#rpi-attribute-book_details-publication_date .rpi-attribute-value');
      if (el) result.publication_date = standardizeDate(clean(el.textContent));
    }

    // Additional fallback: data-feature-name based selectors
    if (!result.publisher) {
      const el = qs(document, '[data-feature-name="bookDetails"] [class*="publisher"]');
      if (el) result.publisher = clean(el.textContent);
    }

    return result;
  }

  // ── Message listener ──────────────────────────────────────

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.action === 'scrapeList') {
      const books = scrapeListPage();
      sendResponse({ books });
    }
    if (msg.action === 'scrapeBook') {
      const data = scrapeBookPage();
      sendResponse({ data });
    }
    if (msg.action === 'getPagination') {
      const info = getPaginationInfo();
      sendResponse({ pagination: info });
    }
    return true; // keep channel open for async
  });

})();
