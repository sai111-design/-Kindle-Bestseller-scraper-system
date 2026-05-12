import os
import sys
import traceback
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import scrape

app = Flask(__name__)
# Enable CORS so the Chrome extension can make requests from any origin (including chrome-extension://)
CORS(app)

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        "status": "running", 
        "message": "Selenium Server is ready"
    })

current_progress = {"pct": 0, "message": "Ready", "eta": ""}
scrape_start_time = None

def update_progress(current, total, message):
    global current_progress, scrape_start_time
    pct = 20
    eta_str = ""
    
    if current == 0:
        scrape_start_time = time.time()
        
    if total > 0:
        pct = 20 + int((current / total) * 75)
        if scrape_start_time and current > 0:
            elapsed = time.time() - scrape_start_time
            speed = current / elapsed
            remaining = (total - current) / speed if speed > 0 else 0
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                eta_str = f"{mins}m {secs}s left"

    current_progress = {"pct": pct, "message": message, "eta": eta_str}

@app.route('/api/progress', methods=['GET'])
def api_progress():
    return jsonify(current_progress)

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    data = request.json or {}
    category = data.get('category', 'paranormal-romance')
    pages = data.get('pages', 1)
    scrape_details = data.get('scrape_details', True)
    headless = data.get('headless', False) # Set false so user can see what's happening by default

    print(f"\n[API] Received scrape request: {category}, {pages} pages, details: {scrape_details}")

    global current_progress, scrape_start_time
    scrape_start_time = time.time()
    current_progress = {"pct": 10, "message": "Starting Chrome browser...", "eta": ""}

    try:
        books = scrape(category_key=category, max_pages=pages, scrape_details=scrape_details, headless=headless, progress_cb=update_progress)
        current_progress = {"pct": 100, "message": "Data processed successfully", "eta": ""}
        return jsonify({"status": "success", "books": books})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("======================================================")
    print(" 🚀 Kindle Scraper Backend Server is RUNNING")
    print("======================================================")
    print(" Listening on http://localhost:5000")
    print(" Your Chrome Extension is now connected to Selenium.")
    print(" Do not close this terminal!\n")
    app.run(port=5000, debug=False)
