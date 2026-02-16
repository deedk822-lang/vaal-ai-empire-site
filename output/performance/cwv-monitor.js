// Core Web Vitals Monitoring
(function() {
  // LCP
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    console.log('[CWV] LCP:', lastEntry.startTime);
    // Send to analytics
  }).observe({ entryTypes: ['largest-contentful-paint'] });

  // CLS
  let clsValue = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) {
        clsValue += entry.value;
      }
    }
    console.log('[CWV] CLS:', clsValue);
  }).observe({ entryTypes: ['layout-shift'] });

  // FCP
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    if (entries.length > 0) {
      console.log('[CWV] FCP:', entries[0].startTime);
    }
  }).observe({ entryTypes: ['paint'] });
})();
