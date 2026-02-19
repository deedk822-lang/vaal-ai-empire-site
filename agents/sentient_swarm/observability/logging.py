"""
Structured logging compatible with Grafana.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict


class StructuredLogger:
    """JSON structured logger for Grafana integration."""
    
    def __init__(self, service: str = "sentient-swarm"):
        self.service = service
    
    def _log(self, level: str, message: str, **kwargs):
        """Output structured log."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "service": self.service,
            "message": message,
            **kwargs
        }
        print(json.dumps(log_entry), file=sys.stderr)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
