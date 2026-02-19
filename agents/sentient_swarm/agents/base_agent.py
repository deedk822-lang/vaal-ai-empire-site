"""
Base agent class with shared infrastructure.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all swarm agents."""
    
    def __init__(self, name: str, llm_client=None, metrics=None, tracer=None):
        self.name = name
        self.llm = llm_client
        self.metrics = metrics
        self.tracer = tracer
        self.output_dir = os.path.join("output", name.lower().replace(" ", "_"))
        os.makedirs(self.output_dir, exist_ok=True)
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task."""
        pass
    
    def log(self, message: str, **kwargs):
        """Log with agent context."""
        print(f"[{self.name}] {message}", **kwargs)
    
    def write_file(self, filename: str, content: str) -> str:
        """Write output file."""
        filepath = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
