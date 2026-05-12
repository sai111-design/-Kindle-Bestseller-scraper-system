# Kindle Bestseller Scraper System

An end-to-end scraping system for Amazon Kindle bestseller categories, built with:

- **Python + Selenium** for robust scraping
- **Flask API** for local orchestration and progress tracking
- **Chrome Extension (Manifest V3)** for one-click UI, CSV export, and scheduled runs

This project was prepared as a Pocket FM internship assignment.

## What this project does

The system scrapes Amazon Kindle bestseller data and outputs structured records containing:

- rank
- title
- author
- rating
- review count
- price
- product URL
- description
- publisher
- publication date

It supports multiple categories, optional pagination, optional detail-page scraping, real-time progress updates, and CSV export.

## Key features

- Scrapes bestseller list pages with fallback selectors
- Optionally visits each book page for extended metadata
- Handles multiple Kindle categories
- Exposes local API endpoints:
  - `GET /api/status`
  - `GET /api/progress`
  - `POST /api/scrape`
- Chrome extension popup for:
  - category selection
  - scrape trigger
  - progress display
  - CSV download
  - Google Sheets clipboard copy (TSV)
  - scheduled background scraping

## Architecture

1. The extension calls the local Flask backend at `http://localhost:5000`.
2. Flask triggers the Selenium scraper (`scraper.py`).
3. Scraper collects list + detail data from Amazon pages.
4. Backend returns JSON results to the extension.
5. Extension shows stats and lets users export to CSV/Sheets.

## Tech stack

- Python 3
- Selenium
- webdriver-manager
- Flask
- Flask-Cors
- Chrome Extension Manifest V3 (Vanilla JS/HTML/CSS)

## Repository structure

```text
pocket_fm/
|-- scraper.py                     # Main Selenium scraper + CLI
|-- server.py                      # Flask backend API
|-- requirements.txt               # Python dependencies
|-- extension/                     # Chrome extension source
|   |-- manifest.json
|   |-- popup.html
|   |-- popup.js
|   |-- background.js
|   `-- content.js
|-- submission/                    # Snapshot copy of the same deliverables
|-- agent-architecture/            # Supporting architecture docs/prompts
`-- kindle_*.csv                   # Sample/generated output files
```

## Prerequisites

- Python 3.10+ (recommended)
- Google Chrome installed
- Internet access (Amazon pages must be reachable)

## Setup

### 1. Clone repository

```bash
git clone https://github.com/sai111-design/-Kindle-Bestseller-scraper-system.git
cd -Kindle-Bestseller-scraper-system
```

### 2. Create and activate virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Run the backend

Start Flask server:

```bash
python server.py
```

Expected startup endpoint:

- `http://localhost:5000/api/status`

## Load Chrome extension

1. Open `chrome://extensions/`
2. Turn on **Developer mode**
3. Click **Load unpacked**
4. Select the local `extension\` folder
5. Pin and open the extension popup

## How to use

1. Ensure backend (`python server.py`) is running.
2. Open extension popup.
3. Pick category and options.
4. Click **Scrape Amazon Now**.
5. Wait for progress to complete.
6. Download CSV or copy TSV for Google Sheets.

## API reference

### `GET /api/status`

Returns backend liveness.

Example response:

```json
{
  "status": "running",
  "message": "Selenium Server is ready"
}
```

### `GET /api/progress`

Returns current progress state.

Example response:

```json
{
  "pct": 42,
  "message": "Loading list page 1...",
  "eta": "1m 20s left"
}
```

### `POST /api/scrape`

Starts a scrape run.

Request body:

```json
{
  "category": "paranormal-romance",
  "pages": 1,
  "scrape_details": true,
  "headless": false
}
```

Response (success):

```json
{
  "status": "success",
  "books": []
}
```

## CLI usage (direct scraper)

You can run the scraper without Flask/extension:

```bash
python scraper.py --list-categories
python scraper.py --category fantasy --pages 3
python scraper.py --no-details
python scraper.py --headless
```

### CLI options

| Option | Description |
|---|---|
| `-c`, `--category` | Category key to scrape |
| `-p`, `--pages` | Number of list pages to scrape |
| `--no-details` | Skip individual book page scraping |
| `--headless` | Run Chrome in headless mode |
| `--list-categories` | Print available categories and exit |

## Supported categories

| Key | Category |
|---|---|
| `paranormal-romance` | Paranormal Romance |
| `romance` | Romance |
| `fantasy` | Fantasy |
| `science-fiction` | Science Fiction |
| `sci-fi-fantasy` | Science Fiction & Fantasy |
| `mystery` | Mystery |
| `thriller` | Thriller |
| `mystery-thriller` | Mystery, Thriller & Suspense |
| `horror` | Horror |
| `literature` | Literature & Fiction |
| `self-help` | Self-Help |
| `kindle-ebooks` | Kindle eBooks (All) |

## Output schema

| Field | Type | Notes |
|---|---|---|
| `rank` | string | `#` removed where possible |
| `title` | string | Book title |
| `author` | string | Author name |
| `rating` | float/string | Parsed rating if available |
| `num_reviews` | int/string | Parsed review count if available |
| `price` | string | e.g., `$8.99` or `Free` |
| `url` | string | Canonical Amazon `/dp/{ASIN}` URL when available |
| `description` | string | Truncated to max ~1500 chars |
| `publisher` | string | Publisher metadata if found |
| `publication_date` | string | Standardized date where possible |

## Troubleshooting

### Backend shows "Server Offline" in extension

- Confirm `python server.py` is running.
- Confirm `http://localhost:5000/api/status` opens in browser.
- Check firewall or port conflicts on `5000`.

### Selenium/driver issues

- Reinstall dependencies: `pip install -r requirements.txt`
- Update Chrome to latest stable version.
- Retry with `headless: false` to visually inspect navigation.

### No books scraped

- Amazon layout may have changed.
- Geo/country dialogs may block content.
- Retry category/pages and inspect terminal logs + `debug_screenshot.png` (if generated).

## Notes

- Scraping behavior may change if Amazon updates HTML structure.
- Use responsibly and comply with target website terms/policies.

