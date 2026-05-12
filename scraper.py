# pyre-ignore-all-errors
# type: ignore
"""
Kindle Bestseller Scraper — Selenium Edition
=============================================
Scrapes Amazon Kindle bestseller data from any category.
Handles geo-restrictions by setting US locale cookies.
Exports data to CSV and TSV (Google Sheets ready).

Usage:
    python scraper.py                     # Default: Paranormal Romance
    python scraper.py --category fantasy  # Use a different category
    python scraper.py --pages 3           # Scrape 3 pages
    python scraper.py --list-categories   # Show all available categories
    python scraper.py --no-details        # Skip visiting individual book pages
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager


# ═══════════════════════════════════════════════════════════════
# CATEGORY DEFINITIONS
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {
    "paranormal-romance":    {"name": "Paranormal Romance",    "node": "6190484011"},
    "romance":               {"name": "Romance",              "node": "158566011"},
    "fantasy":               {"name": "Fantasy",               "node": "158576011"},
    "science-fiction":       {"name": "Science Fiction",        "node": "158591011"},
    "sci-fi-fantasy":        {"name": "Science Fiction & Fantasy", "node": "668010011"},
    "mystery":               {"name": "Mystery",               "node": "157307011"},
    "thriller":              {"name": "Thriller",              "node": "157319011"},
    "mystery-thriller":      {"name": "Mystery, Thriller & Suspense", "node": "157305011"},
    "horror":                {"name": "Horror",                "node": "157053011"},
    "literature":            {"name": "Literature & Fiction",  "node": "157028011"},
    "self-help":             {"name": "Self-Help",             "node": "156563011"},
    "kindle-ebooks":         {"name": "Kindle eBooks (All)",   "node": "154606011"},
}


# ═══════════════════════════════════════════════════════════════
# TERMINAL UI HELPERS
# ═══════════════════════════════════════════════════════════════

class Colors:
    ORANGE  = "\033[38;5;208m"
    GOLD    = "\033[38;5;220m"
    GREEN   = "\033[38;5;78m"
    RED     = "\033[38;5;204m"
    CYAN    = "\033[38;5;117m"
    MUTED   = "\033[38;5;244m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

C = Colors()

def banner():
    print(f"""
{C.ORANGE}╔══════════════════════════════════════════════════════════╗
║{C.BOLD}  📚 Kindle Bestseller Scraper — Selenium Edition        {C.RESET}{C.ORANGE}║
║{C.MUTED}     Pocket FM · Amazon Kindle Data Extraction           {C.RESET}{C.ORANGE}║
╚══════════════════════════════════════════════════════════╝{C.RESET}
""")

def log(msg, icon="→"):
    print(f"  {C.CYAN}{icon}{C.RESET} {msg}")

def log_success(msg):
    print(f"  {C.GREEN}✓{C.RESET} {msg}")

def log_warn(msg):
    print(f"  {C.GOLD}⚠{C.RESET} {msg}")

def log_error(msg):
    print(f"  {C.RED}✗{C.RESET} {msg}")

def log_step(step_num, total, msg):
    bar_len = 30
    filled = int(bar_len * step_num / total)
    bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
    pct = int(100 * step_num / total)
    print(f"\r  {C.ORANGE}[{bar}]{C.RESET} {pct:3d}%  {msg[:50]:<50}", end="", flush=True)

def print_table_row(rank, title, author, price, rating):
    title = (title[:35] + "…") if len(title) > 36 else title
    author = (author[:18] + "…") if len(author) > 19 else author
    print(f"  {C.GOLD}{rank:>3}{C.RESET}  {title:<37} {C.MUTED}{author:<20}{C.RESET} {C.GREEN}{price:<8}{C.RESET} {C.ORANGE}{rating}{C.RESET}")


# ═══════════════════════════════════════════════════════════════
# DATA PARSING HELPERS
# ═══════════════════════════════════════════════════════════════

def clean(text):
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_rating(text):
    """Extract rating float from text like '4.7 out of 5 stars'."""
    if not text:
        return ""
    m = re.search(r'(\d+\.?\d*)\s*out of', text)
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+\.?\d*)', text)
    return float(m.group(1)) if m else ""

def parse_reviews(text):
    """Parse review count from text like '1,203'."""
    if not text:
        return ""
    n = int(text.replace(",", "").strip())
    return n

def parse_price(text):
    """Extract price from text like '$8.99' or 'Free'."""
    if not text:
        return ""
    if "free" in text.lower():
        return "Free"
    m = re.search(r'\$[\d,.]+', text)
    return m.group(0) if m else clean(text)

def standardize_date(text):
    """Convert date to YYYY-MM-DD."""
    if not text:
        return ""
    text = clean(text)
    formats = [
        (r'^(\w+)\s+(\d{1,2}),\s+(\d{4})$', lambda m: f"{m.group(1)} {m.group(2)}, {m.group(3)}"),
        (r'^(\w+)\s+(\d{4})$',                lambda m: f"{m.group(1)} 1, {m.group(2)}"),
        (r'^(\d{4})-(\d{2})-(\d{2})$',       lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
    ]
    for pattern, formatter in formats:
        match = re.match(pattern, text)
        if match:
            try:
                from dateutil import parser as dparser
                d = dparser.parse(formatter(match))
                return d.strftime("%Y-%m-%d")
            except Exception:
                try:
                    for fmt in ["%B %d, %Y", "%B %Y", "%Y-%m-%d"]:
                        try:
                            d = datetime.strptime(formatter(match), fmt)
                            return d.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                except Exception:
                    pass
    return text


# ═══════════════════════════════════════════════════════════════
# SELENIUM DRIVER SETUP
# ═══════════════════════════════════════════════════════════════

def create_driver(headless=False):
    """Create a Chrome WebDriver with Amazon-friendly settings."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Performance & stability
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Set US English locale to get US Amazon content
    options.add_argument("--lang=en-US")
    options.add_argument("--accept-lang=en-US,en;q=0.9")

    # User agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # Fallback: try default Chrome
        driver = webdriver.Chrome(options=options)

    # Remove webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver


def set_us_locale(driver):
    """Set Amazon cookies/preferences to force US English content."""
    driver.get("https://www.amazon.com")
    time.sleep(2)

    # Set locale cookies
    driver.add_cookie({"name": "lc-main", "value": "en_US", "domain": ".amazon.com"})
    driver.add_cookie({"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com"})
    driver.add_cookie({"name": "sp-cdn", "value": "\"L5Z9:IN\"", "domain": ".amazon.com"})

    # Try to dismiss any country redirect dialogs
    try:
        dismiss_btn = driver.find_element(By.ID, "GLUXConfirmClose")
        dismiss_btn.click()
        time.sleep(0.5)
    except NoSuchElementException:
        pass

    # Try clicking "Stay on Amazon.com"
    try:
        stay_btn = driver.find_element(By.XPATH, "//a[contains(text(),'Stay on Amazon.com')]")
        stay_btn.click()
        time.sleep(1)
    except NoSuchElementException:
        pass

    # Try the delivery location popup
    try:
        deliver_el = driver.find_element(By.ID, "nav-global-location-popover-link")
        deliver_el.click()
        time.sleep(1)
        # Try entering a US zip code
        zip_input = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "GLUXZipUpdateInput"))
        )
        zip_input.clear()
        zip_input.send_keys("10001")  # New York ZIP
        apply_btn = driver.find_element(By.ID, "GLUXZipUpdate")
        apply_btn.click()
        time.sleep(1)
        # Close the popup
        try:
            close_btn = driver.find_element(By.XPATH, "//button[@name='glowDoneButton']")
            close_btn.click()
        except NoSuchElementException:
            pass
        time.sleep(1)
    except (NoSuchElementException, TimeoutException):
        pass


# ═══════════════════════════════════════════════════════════════
# LIST PAGE SCRAPER
# ═══════════════════════════════════════════════════════════════

def scrape_list_page(driver) -> List[Dict[str, Any]]:
    """Extract book data from the current bestseller list page."""
    books: List[Dict[str, Any]] = []
    wait = WebDriverWait(driver, 10)

    # Wait for the page to fully load
    time.sleep(2)

    # Try multiple selectors for book cards
    card_selectors = [
        "#gridItemRoot",
        ".zg-item-immersion",
        "[id^='gridItemRoot']",
        ".a-carousel-card",
        "div[data-asin]",
    ]

    items = []
    for sel in card_selectors:
        try:
            items = driver.find_elements(By.CSS_SELECTOR, sel)
            if items:
                break
        except Exception:
            continue

    if not items:
        # More aggressive fallback: look for any link with /dp/ inside a ranked section
        try:
            items = driver.find_elements(By.CSS_SELECTOR, ".zg-grid-general-faceout")
        except Exception:
            pass

    if not items:
        return books

    for item in items:
        try:
            book: Dict[str, Any] = {
                "rank": "",
                "title": "",
                "author": "",
                "rating": "",
                "num_reviews": "",
                "price": "",
                "url": "",
                "description": "",
                "publisher": "",
                "publication_date": ""
            }

            # Rank
            for rank_sel in [".zg-bdg-text", "span.zg-bdg-text", "[class*='badgeText']"]:
                try:
                    rank_el = item.find_element(By.CSS_SELECTOR, rank_sel)
                    book["rank"] = clean(rank_el.text).replace("#", "")
                    break
                except NoSuchElementException:
                    continue

            # Title — try multiple selectors
            for title_sel in [
                "._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y",
                ".p13n-sc-line-clamp-2",
                ".p13n-sc-line-clamp-3",
                ".p13n-sc-line-clamp-4",
                "[class*='line-clamp']",
                "a[href*='/dp/'] span div",
                "a[href*='/dp/']",
            ]:
                try:
                    title_el = item.find_element(By.CSS_SELECTOR, title_sel)
                    t = clean(title_el.text)
                    if t:
                        book["title"] = t
                        break
                except NoSuchElementException:
                    continue

            # If still no title, try the link's title attribute
            if not book["title"]:
                try:
                    link = item.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                    book["title"] = clean(link.get_attribute("title") or link.text)
                except NoSuchElementException:
                    pass

            # Author — try specific author selectors, filtering out "Kindle Edition" etc.
            author_skip = {"kindle edition", "paperback", "hardcover", "audiobook",
                           "audio cd", "board book", "mass market paperback",
                           "formats available", "kindle unlimited"}
            for author_sel in [
                "a.a-link-child",                  # author link (most reliable)
                ".a-row.a-size-small a",           # author link in row
                "span.a-size-small.a-color-base",  # author name span
                ".a-row.a-size-small > .a-color-secondary",
            ]:
                try:
                    auth_els = item.find_elements(By.CSS_SELECTOR, author_sel)
                    for auth_el in auth_els:
                        candidate = clean(auth_el.text)
                        if candidate and candidate.lower() not in author_skip \
                                and not any(skip in candidate.lower() for skip in author_skip):
                            book["author"] = candidate
                            break
                    if book["author"]:
                        break
                except NoSuchElementException:
                    continue

            # Fallback: grab all text spans and pick the one that looks like an author
            if not book["author"]:
                try:
                    spans = item.find_elements(By.CSS_SELECTOR, "span.a-size-small")
                    for span in spans:
                        text = clean(span.text)
                        if text and text.lower() not in author_skip \
                                and not any(skip in text.lower() for skip in author_skip) \
                                and not text.replace(",", "").isdigit():
                            book["author"] = text
                            break
                except NoSuchElementException:
                    pass


            # Rating
            # Amazon often combines rating and review count in the 'aria-label' of the review link
            # Example: "4.7 out of 5 stars, 200,161 ratings"
            found_rating = False
            for star_sel in [
                "a[href*='/product-reviews/']", 
                "i[class*='a-icon-star']", 
                ".a-icon-star-small"
            ]:
                try:
                    star_el = item.find_element(By.CSS_SELECTOR, star_sel)
                    
                    # Try aria-label first (most common for the parent <a> tag)
                    aria = star_el.get_attribute("aria-label")
                    if not aria:
                        aria = star_el.get_attribute("title")
                    if not aria:
                        aria = star_el.text
                    
                    if aria:
                        # If it's the combined string like "4.7 out of 5 stars, 200,161 ratings"
                        # we only want the rating part
                        if "," in aria and "stars" in aria.lower():
                            aria = aria.split(",")[0]
                            
                        parsed_rating = parse_rating(aria)
                        if parsed_rating:
                            book["rating"] = parsed_rating
                            found_rating = True
                            break
                            
                except (NoSuchElementException, Exception):
                    continue

            # Review count
            try:
                rev_el = item.find_element(By.CSS_SELECTOR, "a[href*='customerReviews'], span.a-size-small:last-of-type")
                rev_text = clean(rev_el.text)
                if rev_text and rev_text.replace(",", "").isdigit():
                    book["num_reviews"] = parse_reviews(rev_text)
            except (NoSuchElementException, ValueError):
                pass

            # Price
            for price_sel in [".p13n-sc-price", "span._cDEzb_p13n-sc-price_3mJ9Z", "[class*='price']", ".a-price .a-offscreen"]:
                try:
                    price_el = item.find_element(By.CSS_SELECTOR, price_sel)
                    book["price"] = parse_price(price_el.text or price_el.get_attribute("textContent"))
                    if book["price"]:
                        break
                except NoSuchElementException:
                    continue

            # URL
            try:
                link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                href = link_el.get_attribute("href") or ""
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', href)
                if asin_match:
                    book["url"] = f"https://www.amazon.com/dp/{asin_match.group(1)}"
                else:
                    book["url"] = href.split("?")[0]  # Strip tracking params
            except NoSuchElementException:
                pass

            # Only add if we have at minimum a title or URL
            if book["title"] or book["url"]:
                books.append(book)

        except StaleElementReferenceException:
            continue
        except Exception as e:
            continue

    return books


# ═══════════════════════════════════════════════════════════════
# BOOK PAGE SCRAPER
# ═══════════════════════════════════════════════════════════════

def scrape_book_page(driver) -> Dict[str, Any]:
    """Extract description, publisher, and publication date from a book page."""
    result: Dict[str, Any] = {"description": "", "publisher": "", "publication_date": ""}

    wait = WebDriverWait(driver, 8)
    time.sleep(1.5)

    # Description — try expanding "Read more" first
    try:
        expander = driver.find_element(By.CSS_SELECTOR, "#bookDescription_feature_div .a-expander-trigger")
        driver.execute_script("arguments[0].click();", expander)
        time.sleep(0.5)
    except NoSuchElementException:
        pass

    for desc_sel in [
        "#bookDescription_feature_div .a-expander-content",
        "#bookDescription_feature_div",
        "#productDescription",
        "[data-a-expander-name='book_description_expander'] .a-expander-content",
    ]:
        try:
            desc_el = driver.find_element(By.CSS_SELECTOR, desc_sel)
            text = clean(desc_el.text)
            if text:
                result["description"] = text[:1500]
                break
        except NoSuchElementException:
            continue

    # Publisher and Publication Date from detail bullets
    try:
        bullets = driver.find_elements(By.CSS_SELECTOR, "#detailBullets_feature_div li")
        for li in bullets:
            text = clean(li.text)
            lower = text.lower()
            if "publisher" in lower:
                parts = text.split(":")
                if len(parts) >= 2:
                    pub = ":".join(parts[1:])
                    result["publisher"] = re.sub(r'\(.*?\)', '', pub).strip()
            if "publication date" in lower:
                parts = text.split(":")
                if len(parts) >= 2:
                    pub_date = standardize_date(":".join(parts[1:]).strip())
                    result["publication_date"] = pub_date if pub_date is not None else ""
    except Exception:
        pass

    # Fallback: newer Amazon layout (rpi attributes)
    if not result["publisher"]:
        try:
            pub_el = driver.find_element(By.CSS_SELECTOR,
                "#rpi-attribute-book_details-publisher .rpi-attribute-value span")
            result["publisher"] = clean(pub_el.text)
        except NoSuchElementException:
            pass

    if not result["publication_date"]:
        try:
            date_el = driver.find_element(By.CSS_SELECTOR,
                "#rpi-attribute-book_details-publication_date .rpi-attribute-value span")
            result["publication_date"] = standardize_date(clean(date_el.text))
        except NoSuchElementException:
            pass

    # Another fallback: product details table
    if not result["publisher"] or not result["publication_date"]:
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr")
            for row in rows:
                text = clean(row.text)
                lower = text.lower()
                if "publisher" in lower and not result["publisher"]:
                    try:
                        val = row.find_element(By.CSS_SELECTOR, "td").text
                        result["publisher"] = re.sub(r'\(.*?\)', '', clean(val)).strip()
                    except NoSuchElementException:
                        pass
                if "date" in lower and not result["publication_date"]:
                    try:
                        val = row.find_element(By.CSS_SELECTOR, "td").text
                        result["publication_date"] = standardize_date(clean(val))
                    except NoSuchElementException:
                        pass
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════════════════════════
# PAGINATION HANDLER
# ═══════════════════════════════════════════════════════════════

def get_next_page_url(driver):
    """Find the 'Next page' link on a bestseller list page."""
    selectors = [
        "li.a-last a",
        "ul.a-pagination li.a-last a",
        "a:has(> span.a-declarative[data-action='a-pagination'])",
    ]
    for sel in selectors:
        try:
            link = driver.find_element(By.CSS_SELECTOR, sel)
            href = link.get_attribute("href")
            if href:
                return href
        except NoSuchElementException:
            continue

    # Fallback: look for a link with text "Next" or "→"
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip().lower()
            if text in ["next", "next page", "→", ">"]:
                href = link.get_attribute("href")
                if href:
                    return href
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════
# EXPORT FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def export_csv(books, filename):
    """Export books to a CSV file."""
    cols = ["rank", "title", "author", "rating", "num_reviews",
            "price", "url", "description", "publisher", "publication_date"]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for book in books:
            writer.writerow({k: book.get(k, "") for k in cols})

    return filename


def export_tsv(books, filename):
    """Export books to a TSV file (paste-ready for Google Sheets)."""
    cols = ["rank", "title", "author", "rating", "num_reviews",
            "price", "url", "description", "publisher", "publication_date"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        writer.writeheader()
        for book in books:
            row = {}
            for k in cols:
                val = str(book.get(k, ""))
                row[k] = val.replace("\t", " ").replace("\n", " ")
            writer.writerow(row)

    return filename


# ═══════════════════════════════════════════════════════════════
# MAIN SCRAPER ORCHESTRATION
# ═══════════════════════════════════════════════════════════════

def scrape(category_key="paranormal-romance", max_pages=2, scrape_details=True, headless=False, progress_cb=None):
    """Main scraping function."""

    if category_key not in CATEGORIES:
        log_error(f"Unknown category: {category_key}")
        log(f"Available: {', '.join(CATEGORIES.keys())}")
        return []

    cat = CATEGORIES[category_key]
    category_name = cat["name"]
    node_id = cat["node"]

    banner()
    log(f"Category: {C.BOLD}{category_name}{C.RESET}")
    log(f"Max pages: {max_pages}")
    log(f"Scrape details: {'Yes' if scrape_details else 'No (list only)'}")
    print()

    # ── Step 1: Start browser ─────────────────────
    log("Starting Chrome browser…", "🌐")
    driver = create_driver(headless=headless)

    try:
        # ── Step 2: Set US locale ─────────────────
        log("Setting US locale (to bypass geo-restrictions)…", "🇺🇸")
        set_us_locale(driver)
        log_success("Locale set to US/English")

        all_books: List[Dict[str, Any]] = []

        # ── Step 3: Scrape list pages ─────────────
        for page_num in range(1, max_pages + 1):
            if page_num == 1:
                url = f"https://www.amazon.com/gp/bestsellers/digital-text/{node_id}"
            # For subsequent pages, use the "next page" URL found on the previous page

            log(f"Loading bestseller page {page_num}…", "📄")
            if progress_cb: progress_cb(0, 0, f"Loading list page {page_num}...")
            driver.get(url)
            time.sleep(3)

            # Check for "no bestsellers" message
            try:
                no_results = driver.find_element(By.XPATH,
                    "//*[contains(text(),'no Best Sellers available')]")
                if no_results:
                    log_warn("Amazon says 'no Best Sellers available' — trying alternative URL format…")
                    # Try the zgbs URL format
                    alt_url = f"https://www.amazon.com/Best-Sellers-Kindle-Store/zgbs/digital-text/{node_id}"
                    driver.get(alt_url)
                    time.sleep(3)
            except NoSuchElementException:
                pass

            books = scrape_list_page(driver)

            if not books:
                if page_num == 1:
                    log_error("Could not find any books on the page.")
                    log_warn("This may be due to geo-restrictions or changed page layout.")
                    log(f"Current URL: {driver.current_url}")

                    # Take a debug screenshot
                    screenshot_path = os.path.join(os.path.dirname(__file__), "debug_screenshot.png")
                    driver.save_screenshot(screenshot_path)
                    log(f"Debug screenshot saved: {screenshot_path}")
                    break
                else:
                    log(f"No more books found on page {page_num}. Stopping pagination.")
                    break

            # Adjust ranks for pages > 1
            if page_num > 1:
                offset = len(all_books)
                for i, book in enumerate(books):
                    if not book["rank"]:
                        book["rank"] = str(offset + i + 1)

            all_books.extend(books)
            log_success(f"Page {page_num}: found {len(books)} books (total: {len(all_books)})")

            # Find next page URL
            if page_num < max_pages:
                next_url = get_next_page_url(driver)
                if next_url:
                    url = next_url
                    # Polite delay between pages
                    delay = 2 + random.random() * 2
                    log(f"Waiting {delay:.1f}s before next page…", "⏳")
                    time.sleep(delay)
                else:
                    log("No next page link found. Finished pagination.")
                    break

        if not all_books:
            log_error("No books scraped. Exiting.")
            return []

        # ── Step 4: Print quick preview ───────────
        print()
        log(f"{'─' * 56}", " ")
        print(f"  {C.BOLD}{'#':>3}  {'Title':<37} {'Author':<20} {'Price':<8} {'★'}{C.RESET}")
        log(f"{'─' * 56}", " ")
        for b in all_books[:10]:
            print_table_row(
                b.get("rank", "?"),
                b.get("title", "Unknown"),
                b.get("author", "—"),
                b.get("price", "—"),
                b.get("rating", "—")
            )
        if len(all_books) > 10:
            print(f"  {C.MUTED}... and {len(all_books) - 10} more books{C.RESET}")
        print()

        # ── Step 5: Scrape individual book pages ──
        if scrape_details:
            log(f"Visiting {len(all_books)} individual book pages for details…", "📖")
            print()
            total = len(all_books)
            for i, book in enumerate(all_books):
                if not book["url"]:
                    continue

                log_step(i + 1, total, book.get("title", "")[:45])

                try:
                    driver.get(book["url"])
                    delay = 0.8 + random.random() * 0.7  # 800-1500ms polite delay
                    time.sleep(delay)

                    details = scrape_book_page(driver)
                    book.update(details)
                except Exception as e:
                    pass  # Skip failed books gracefully

            # Final progress bar
            log_step(total, total, "Done!")
            print()
            print()
            log_success(f"Scraped details for {total} books")

        # ── Step 6: Export ─────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = category_key.replace("-", "_")

        csv_file = os.path.join(os.path.dirname(__file__), f"kindle_{safe_name}_{timestamp}.csv")
        tsv_file = os.path.join(os.path.dirname(__file__), f"kindle_{safe_name}_{timestamp}.tsv")

        export_csv(all_books, csv_file)
        export_tsv(all_books, tsv_file)

        print()
        log_success(f"CSV saved: {C.BOLD}{os.path.basename(csv_file)}{C.RESET}")
        log_success(f"TSV saved: {C.BOLD}{os.path.basename(tsv_file)}{C.RESET} (paste into Google Sheets)")

        # Summary stats
        print()
        ratings = [float(b["rating"]) for b in all_books if b.get("rating") and b["rating"] != ""]
        prices = [float(b["price"].replace("$", "")) for b in all_books
                  if b.get("price") and b["price"] not in ("", "Free") and "$" in b["price"]]

        print(f"  {C.ORANGE}{'═' * 50}{C.RESET}")
        print(f"  📊 {C.BOLD}Summary{C.RESET}")
        print(f"     Books scraped:  {C.GOLD}{len(all_books)}{C.RESET}")
        if ratings:
            print(f"     Avg rating:     {C.GOLD}{sum(ratings)/len(ratings):.1f} ★{C.RESET}")
        if prices:
            print(f"     Avg price:      {C.GREEN}${sum(prices)/len(prices):.2f}{C.RESET}")
        with_desc = sum(1 for b in all_books if b.get("description"))
        print(f"     With description: {C.CYAN}{with_desc}/{len(all_books)}{C.RESET}")
        print(f"  {C.ORANGE}{'═' * 50}{C.RESET}")
        print()

        return all_books

    except Exception as e:
        log_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        log("Closing browser…", "🔒")
        driver.quit()


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="📚 Kindle Bestseller Scraper — Selenium Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py                          # Scrape Paranormal Romance (default)
  python scraper.py --category fantasy       # Scrape Fantasy bestsellers
  python scraper.py --category mystery -p 3  # Mystery, 3 pages
  python scraper.py --no-details             # List only, skip book pages
  python scraper.py --headless               # Run without visible browser
  python scraper.py --list-categories        # Show available categories
        """
    )

    parser.add_argument(
        "-c", "--category",
        default="paranormal-romance",
        help="Category to scrape (use --list-categories to see options)"
    )
    parser.add_argument(
        "-p", "--pages",
        type=int, default=2,
        help="Number of pages to scrape (default: 2, each page ≈ 30 books)"
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip visiting individual book pages (faster, no description/publisher)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode (no visible window)"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all available categories and exit"
    )

    args = parser.parse_args()

    if args.list_categories:
        banner()
        print(f"  {C.BOLD}Available Categories:{C.RESET}")
        print()
        for key, val in CATEGORIES.items():
            print(f"    {C.ORANGE}{key:<25}{C.RESET} {val['name']}")
        print()
        print(f"  Usage: python scraper.py --category {C.ORANGE}<name>{C.RESET}")
        print()
        return

    scrape(
        category_key=args.category,
        max_pages=args.pages,
        scrape_details=not args.no_details,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
