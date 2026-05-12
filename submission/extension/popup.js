// popup.js — orchestrates scraping with category switching, pagination, and sheets export

// ── Extension context check ──────────────────────────────────
const isExtension = typeof chrome !== 'undefined' &&
  !!chrome.tabs && typeof chrome.tabs.query === 'function' &&
  !!chrome.runtime && !!chrome.runtime.id;

// ── Category URL builder ─────────────────────────────────────
function buildCategoryUrl(nodeId) {
  return `https://www.amazon.com/gp/bestsellers/digital-text/${nodeId}`;
}

let scrapedData = [];
let selectedCategory = { id: 'paranormal-romance', name: 'Paranormal Romance' };

// ── Boot ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initCategorySelector();
  initSchedulePanel();
  await checkCurrentPage();
});

// ── Tabs ─────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel' + capitalize(btn.dataset.tab)).classList.add('active');
    });
  });
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Category Selector ────────────────────────────────────────
function initCategorySelector() {
  const sel = document.getElementById('categorySelect');

  // Restore from storage
  if (isExtension) {
    chrome.storage.local.get(['selectedCategory'], (result) => {
      if (chrome.runtime.lastError) return;
      if (result.selectedCategory) {
        selectedCategory = result.selectedCategory;
        sel.value = selectedCategory.id;
        updateCategoryUI();
      }
    });
  }

  sel.addEventListener('change', () => {
    const opt = sel.options[sel.selectedIndex];
    selectedCategory = {
      id: sel.value,
      name: opt.dataset.name,
      url: buildCategoryUrl(sel.value),
    };
    if (isExtension) {
      chrome.storage.local.set({ selectedCategory });
    }
    updateCategoryUI();
    checkCurrentPage();
  });
}

function updateCategoryUI() {
  document.getElementById('headerSubtitle').textContent =
    `${selectedCategory.name} bestsellers → CSV in one click`;
  document.getElementById('footerCategory').textContent =
    `Amazon Kindle · ${selectedCategory.name}`;
}

// ── Page Detection (Server Status) ───────────────────────────
async function checkCurrentPage() {
  const dot = document.getElementById('pageDot');
  const status = document.getElementById('pageStatus');
  const hint = document.getElementById('pageHint');
  const btn = document.getElementById('scrapeBtn');

  try {
    const res = await fetch('http://localhost:5000/api/status');
    const data = await res.json();
    if (res.ok && data.status === 'running') {
      if (dot) dot.className = 'page-dot on-list';
      if (status) status.textContent = 'Server Connected ✓';
      if (hint) hint.textContent = 'Selenium scraper is ready for action';
      if (btn) btn.disabled = false;
    } else {
      throw new Error('Server not ready');
    }
  } catch (err) {
    if (dot) dot.className = 'page-dot off';
    if (status) status.textContent = 'Server Offline';
    if (hint) hint.textContent = 'Run `python server.py` in your terminal to enable scraping.';
    if (btn) btn.disabled = true;
  }
}

// ── Main scrape button ───────────────────────────────────────
document.getElementById('scrapeBtn').addEventListener('click', startScrape);
document.getElementById('downloadBtn').addEventListener('click', downloadCSV);
document.getElementById('sheetsBtn').addEventListener('click', copyForSheets);
document.getElementById('resetBtn').addEventListener('click', resetUI);

async function startScrape() {
  setStep(null); // clear
  showSteps(true);
  setBtn('loading');
  hideAlert();

  const usePagination = document.getElementById('paginationToggle').checked;

  try {
    // Step 1: Connecting
    setStep('s1', 'active');
    setProgress(5, 'Connecting to Selenium server...');

    const resCheck = await fetch('http://localhost:5000/api/status').catch(() => null);
    if (!resCheck || !resCheck.ok) {
        showAlert('Cannot connect to local server. Make sure you run `python server.py` in your terminal!', 'error');
        setBtn('idle');
        return;
    }
    
    setStep('s1', 'done');
    setStep('s2', 'active');
    setProgress(20, 'Selenium is scraping (this will take a while, check terminal)...');

    const requestBody = {
       category: selectedCategory.id,
       pages: usePagination ? 3 : 1, // Cap at 3 for frontend sanity
       scrape_details: true,
       headless: false // Show browser window intentionally so user sees it working!
    };

    // Real-time progress advancement
    const progressInterval = setInterval(async () => {
        try {
            const pRes = await fetch('http://localhost:5000/api/progress');
            if (pRes.ok) {
                const pData = await pRes.json();
                setProgress(pData.pct, pData.message || 'Scraping...', pData.eta);
            }
        } catch(e) {}
    }, 500);

    const res = await fetch('http://localhost:5000/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    });
    
    clearInterval(progressInterval);
    
    if (!res.ok) throw new Error('Server returned ' + res.status);
    const json = await res.json();
    
    if (json.status !== 'success' || !json.books) {
       throw new Error(json.message || 'Scraping failed');
    }

    scrapedData = json.books;
    
    setStep('s2', 'done');
    setStep('s3', 'active');
    setProgress(90, 'Processing data...');
    await sleep(400);

    setStep('s3', 'done');
    setProgress(100, 'Done!');

    showStats(scrapedData);
    document.getElementById('downloadBtn').disabled = false;
    document.getElementById('sheetsBtn').disabled = false;
    document.getElementById('resetBtn').style.display = 'block';
    setBtn('done');
    setFooterCount(`${scrapedData.length} books scraped`);
    showAlert(`Successfully scraped ${scrapedData.length} books via Selenium!`, 'success');

  } catch (err) {
    showAlert(`Error: ${err.message}`, 'error');
    setBtn('idle');
  }
}

// ── Data cleaning ────────────────────────────────────────────
function cleanData(books) {
  return books.map(b => ({
    rank:             b.rank || '',
    title:            b.title || '',
    author:           b.author || '',
    rating:           b.rating !== '' ? parseFloat(b.rating) : '',
    num_reviews:      b.num_reviews !== '' ? parseInt(b.num_reviews) : '',
    price:            b.price || '',
    url:              b.url || '',
    description:      (b.description || '').slice(0, 1500),
    publisher:        b.publisher || '',
    publication_date: b.publication_date || '',
  }));
}

// ── Download CSV ─────────────────────────────────────────────
function downloadCSV() {
  if (!scrapedData.length) return;

  const cols = ['rank','title','author','rating','num_reviews','price',
                'url','description','publisher','publication_date'];
  const header = cols.join(',');
  const rows = scrapedData.map(r =>
    cols.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(',')
  );
  const csv = [header, ...rows].join('\n');

  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;

  const safeName = selectedCategory.name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  a.download = `kindle_${safeName}_bestsellers.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('CSV downloaded!');
}

// ── Copy for Google Sheets (TSV to clipboard) ────────────────
async function copyForSheets() {
  if (!scrapedData.length) return;

  const cols = ['rank','title','author','rating','num_reviews','price',
                'url','description','publisher','publication_date'];
  const header = cols.join('\t');
  const rows = scrapedData.map(r =>
    cols.map(c => {
      let val = String(r[c] ?? '');
      // Replace tabs and newlines for clean paste
      val = val.replace(/[\t\n\r]/g, ' ');
      return val;
    }).join('\t')
  );
  const tsv = [header, ...rows].join('\n');

  try {
    await navigator.clipboard.writeText(tsv);
    showToast('Copied! Paste into Google Sheets');

    // Visual feedback on button
    const btn = document.getElementById('sheetsBtn');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg> Copied to clipboard!`;
    setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
  } catch (err) {
    showAlert('Could not copy to clipboard. Try downloading CSV instead.', 'error');
  }
}

// ── Schedule Panel ───────────────────────────────────────────
function initSchedulePanel() {
  if (!isExtension) return;

  const toggle = document.getElementById('scheduleToggle');
  const intervalSel = document.getElementById('intervalSelect');

  // Load saved state
  chrome.runtime.sendMessage({ action: 'getSchedule' }, (schedule) => {
    if (chrome.runtime.lastError) return;
    if (schedule) {
      toggle.checked = schedule.enabled;
      intervalSel.value = String(schedule.intervalHours);
    }
  });

  // Load last run info
  loadLastRunInfo();

  toggle.addEventListener('change', () => {
    const enabled = toggle.checked;
    const intervalHours = parseInt(intervalSel.value);
    chrome.runtime.sendMessage({ action: 'setSchedule', enabled, intervalHours }, () => {
      if (chrome.runtime.lastError) return;
      showToast(enabled ? `Scraping scheduled every ${intervalSel.options[intervalSel.selectedIndex].text}` : 'Scheduled scraping disabled');
    });
  });

  intervalSel.addEventListener('change', () => {
    if (toggle.checked) {
      const intervalHours = parseInt(intervalSel.value);
      chrome.runtime.sendMessage({ action: 'setSchedule', enabled: true, intervalHours }, () => {
        if (chrome.runtime.lastError) return;
        showToast(`Interval updated to ${intervalSel.options[intervalSel.selectedIndex].text}`);
      });
    }
  });
}

function loadLastRunInfo() {
  if (!isExtension) return;
  chrome.runtime.sendMessage({ action: 'getLastRun' }, (lastRun) => {
    if (chrome.runtime.lastError) return;
    const el = document.getElementById('lastRunInfo');
    if (lastRun && lastRun.timestamp) {
      const d = new Date(lastRun.timestamp);
      const timeStr = d.toLocaleString();
      el.innerHTML = `
        <strong>Last scheduled run:</strong><br/>
        <span class="run-time">${timeStr}</span><br/>
        Category: ${lastRun.category || 'Unknown'}<br/>
        Books found: <strong>${lastRun.bookCount || 0}</strong>
      `;
    } else {
      el.textContent = 'No scheduled runs yet.';
    }
  });
}

// ── UI helpers ────────────────────────────────────────────────
function setBtn(state) {
  const btn = document.getElementById('scrapeBtn');
  if (state === 'loading') {
    btn.disabled = true;
    btn.innerHTML = `<div class="step-spinner"></div> Scraping…`;
  } else if (state === 'done') {
    btn.disabled = false;
    btn.innerHTML = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 4v5h5M20 20v-5h-5M4 9a9 9 0 0115 0M20 15a9 9 0 01-15 0"/></svg> Scrape Again`;
  } else {
    btn.disabled = false;
    btn.innerHTML = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35M11 8v6M8 11h6"/></svg> Scrape Amazon Now`;
  }
}

function setProgress(pct, label, eta = '') {
  document.getElementById('progressWrap').classList.add('visible');
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressLabel').textContent = label;
  
  if (eta && pct < 100) {
    document.getElementById('progressPct').textContent = `${pct}% • ${eta}`;
  } else {
    document.getElementById('progressPct').textContent = pct + '%';
  }
}

function showSteps(show) {
  document.getElementById('stepsList').classList.toggle('visible', show);
}

function setStep(id, state) {
  if (!id) {
    ['s1','s2','s3'].forEach(s => {
      const el = document.getElementById(s);
      if (el) {
          el.className = 'step-row';
      }
    });
    return;
  }
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'step-row ' + state;
  if (state === 'active') {
    const icon = el.querySelector('.step-icon');
    icon.innerHTML = '<div class="step-spinner"></div>';
  }
}

function showStats(data) {
  const strip = document.getElementById('statsStrip');
  strip.classList.add('visible');

  document.getElementById('statBooks').textContent = data.length;

  const ratings = data.map(d => parseFloat(d.rating)).filter(n => !isNaN(n));
  document.getElementById('statRating').textContent =
    ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : '—';

  const prices = data.map(d => parseFloat((d.price || '').replace('$', ''))).filter(n => !isNaN(n) && n > 0);
  document.getElementById('statPrice').textContent =
    prices.length ? '$' + (prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : '—';
}

function showAlert(msg, type = 'error') {
  const el = document.getElementById('alert');
  el.className = `alert visible ${type}`;
  el.textContent = msg;
}
function hideAlert() {
  document.getElementById('alert').className = 'alert';
}

function setFooterCount(text) {
  document.getElementById('footerCount').innerHTML =
    `<span>${text}</span>`;
}

function showToast(msg) {
  const el = document.getElementById('tooltip');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => { el.classList.remove('show'); }, 2500);
}

function resetUI() {
  scrapedData = [];
  setStep(null);
  showSteps(false);
  document.getElementById('progressWrap').classList.remove('visible');
  document.getElementById('statsStrip').classList.remove('visible');
  document.getElementById('downloadBtn').disabled = true;
  document.getElementById('sheetsBtn').disabled = true;
  document.getElementById('resetBtn').style.display = 'none';
  document.getElementById('footerCount').innerHTML = '';
  hideAlert();
  setBtn('idle');
  checkCurrentPage();
}

// ── Utilities ─────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function waitForTabLoad(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve(); // resolve anyway — don't block forever
    }, 30000); // 30s timeout

    function listener(id, info) {
      if (id === tabId && info.status === 'complete') {
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function sendToContent(tabId, message) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        console.warn('sendToContent error:', chrome.runtime.lastError.message);
        resolve(null);
      } else {
        resolve(response);
      }
    });
  });
}
