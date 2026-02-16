"""
Performance Agent - Core Web Vitals and security hardening.
"""

import json
from typing import Any, Dict
from .base_agent import BaseAgent


class PerformanceAgent(BaseAgent):
    """Optimizes Core Web Vitals and security."""
    
    def __init__(self, llm_client=None, metrics=None, tracer=None):
        super().__init__("Performance", llm_client, metrics, tracer)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance configurations."""
        self.log("🛡️ Hardening infrastructure...")
        
        # Performance config
        perf_config = {
            "targets": {
                "LCP": {"value": 2000, "unit": "ms", "priority": "high"},
                "INP": {"value": 200, "unit": "ms", "priority": "high"},
                "CLS": {"value": 0.05, "unit": "", "priority": "high"},
                "TTFB": {"value": 600, "unit": "ms", "priority": "medium"},
                "FCP": {"value": 1800, "unit": "ms", "priority": "medium"}
            },
            "optimizations": {
                "images": {
                    "format": "webp",
                    "lazy_load": True,
                    "responsive": True
                },
                "css": {
                    "critical_inline": True,
                    "unused_remove": True,
                    "minify": True
                },
                "js": {
                    "defer": True,
                    "async": False,
                    "code_split": True
                },
                "fonts": {
                    "display": "swap",
                    "preload": True
                },
                "caching": {
                    "static": "1year",
                    "api": "1hour"
                }
            }
        }
        
        perf_file = self.write_file("performance.config.json", json.dumps(perf_config, indent=2))
        
        # Security headers config
        security_config = {
            "headers": {
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://api.vaalaiempire.co.za;",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
            },
            "features": {
                "https_only": True,
                "subresource_integrity": True,
                "feature_policy": True
            }
        }
        
        security_file = self.write_file("security.config.json", json.dumps(security_config, indent=2))
        
        # Generate monitoring script
        monitoring_js = """// Core Web Vitals Monitoring
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
"""
        
        monitoring_file = self.write_file("cwv-monitor.js", monitoring_js)
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [perf_file, security_file, monitoring_file],
            'metrics': {
                'targets_set': len(perf_config['targets']),
                'security_headers': len(security_config['headers'])
            }
        }
