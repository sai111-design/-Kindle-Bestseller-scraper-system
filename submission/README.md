## Kindle Bestseller Scraper — Source Code

### Project Structure
- .venv/         → Python virtual environment
- extension/     → Chrome Extension frontend (Manifest V3)
- scraper.py     → Selenium scraping logic (Phase 1 + Phase 2)
- server.py      → Flask API server with /api/scrape and /api/progress endpoints
- requirements.txt → Python dependencies

### How to Run
1. Activate virtual environment: 
   Windows: .venv\Scripts\activate
   Mac/Linux: source .venv/bin/activate
2. Start the backend: python server.py
3. Load extension/ as an unpacked extension in Chrome (Developer Mode)
4. Select a category and click Scrape

### Dataset
kindle_paranormal_romance_20260311_201020.csv contains the 
final scraped output for the Paranormal Romance category.
