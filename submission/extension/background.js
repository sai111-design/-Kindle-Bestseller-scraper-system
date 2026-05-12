chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.get('scrapeAlarm', (alarm) => {
    if (!alarm) {
      chrome.storage.local.get(['schedule'], (result) => {
        if (result.schedule && result.schedule.enabled) {
          chrome.alarms.create('scrapeAlarm', { periodInMinutes: result.schedule.intervalHours * 60 });
        }
      });
    }
  });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'scrapeAlarm') {
    chrome.storage.local.get(['selectedCategory'], async (result) => {
      const cat = result.selectedCategory || { id: 'paranormal-romance', name: 'Paranormal Romance' };
      
      try {
        // Send a background request to the robust local Selenium Server (Flask)
        const res = await fetch('http://localhost:5000/api/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
             category: cat.id,
             pages: 1, 
             scrape_details: false, // Keep background runs fast!
             headless: true         // Do it invisibly
          })
        });
        
        const json = await res.json();
        if (json.status === 'success') {
             const count = (json.books && json.books.length) || 0;
             chrome.action.setBadgeText({ text: String(count) });
             chrome.action.setBadgeBackgroundColor({ color: '#06d6a0' });

             chrome.storage.local.set({
               lastRun: {
                 timestamp: Date.now(),
                 category: cat.name,
                 bookCount: count
               }
             });
        } else {
             console.warn("Server backend error:", json.message);
        }
      } catch (err) {
         console.warn("Background scrape failed. Ensure `python server.py` is running...", err);
      }
    });
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'setSchedule') {
    chrome.storage.local.set({ schedule: { enabled: msg.enabled, intervalHours: msg.intervalHours } });
    if (msg.enabled) {
      chrome.alarms.create('scrapeAlarm', { periodInMinutes: msg.intervalHours * 60 });
    } else {
      chrome.alarms.clear('scrapeAlarm');
    }
    sendResponse({ success: true });
  } 
  else if (msg.action === 'getSchedule') {
    chrome.storage.local.get(['schedule'], (result) => {
      sendResponse(result.schedule || { enabled: false, intervalHours: 24 });
    });
  }
  else if (msg.action === 'getLastRun') {
    chrome.storage.local.get(['lastRun'], (result) => {
      sendResponse(result.lastRun || null);
    });
  }
  return true;
});
