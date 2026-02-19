"""
Structured JSON logger for enterprise log aggregation.
Compatible with ELK, Datadog, Grafana Loki.
"""

import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """
    Structured JSON logger.
    
    Output format compatible with:
    - ELK Stack
    - Datadog
    - Grafana Loki
    - Splunk
    """
    
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50
    }
    
    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = self.LEVELS.get(level, 20)
    
    def _log(self, level: str, message: str, **kwargs):
        """Output structured log line."""
        if self.LEVELS.get(level, 0) < self.level:
            return
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": message,
            "service": "sentient-swarm",
            "pid": self._get_pid(),
            **kwargs
        }
        
        # Output to stderr (convention for logs)
        print(json.dumps(log_entry, default=str), file=sys.stderr, flush=True)
    
    def _get_pid(self) -> int:
        """Get process ID."""
        import os
        return os.getpid()
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)
    
    def exception(self, message: str, exc: Exception, **kwargs):
        """Log exception with stack trace."""
        import traceback
        self._log(
            "ERROR",
            message,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            stack_trace=traceback.format_exc(),
            **kwargs
        )
