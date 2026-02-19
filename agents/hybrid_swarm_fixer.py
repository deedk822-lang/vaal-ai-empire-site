#!/usr/bin/env python3
"""
Production Hybrid Swarm Auto-Fixer
Uses YOUR actual infrastructure:
- Primary: OLLAMA (local)
- Fallback 1: Kimi K2.5 API
- Fallback 2: GLM-5 API
- Fallback 3: DashScope API
- Monitoring: Prometheus, Grafana, OpenTelemetry

Author: Vaal AI Empire Team
Version: 1.0.0
"""

from __future__ import annotations

import os
import json
import ast
import asyncio
import hashlib
import difflib
import subprocess
import sys
import time
import logging
import re
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('swarm_fixer.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# OpenTelemetry integration (optional)
TELEMETRY_AVAILABLE = False
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from prometheus_client import start_http_server, Counter, Histogram, Gauge, Info
    TELEMETRY_AVAILABLE = True
    logger.info("OpenTelemetry and Prometheus available")
except ImportError:
    logger.warning("OpenTelemetry/Prometheus not available, metrics disabled")

# Prometheus metrics
if TELEMETRY_AVAILABLE:
    try:
        FIXES_ATTEMPTED = Counter(
            'swarm_fixes_attempted_total',
            'Total fixes attempted',
            ['category', 'repository']
        )
        FIXES_APPROVED = Counter(
            'swarm_fixes_approved_total',
            'Total fixes approved',
            ['category', 'repository']
        )
        FIXES_REJECTED = Counter(
            'swarm_fixes_rejected_total',
            'Total fixes rejected',
            ['category', 'repository']
        )
        FIX_DURATION = Histogram(
            'swarm_fix_duration_seconds',
            'Fix generation duration',
            ['provider', 'category']
        )
        EVALUATION_SCORE = Gauge(
            'swarm_evaluation_score',
            'Current evaluation score',
            ['category', 'fix_id']
        )
        API_CALLS = Counter(
            'swarm_api_calls_total',
            'API calls by provider',
            ['provider', 'status', 'repository']
        )
        PROVIDER_FALLBACK = Counter(
            'swarm_provider_fallback_total',
            'Provider fallback count',
            ['from_provider', 'to_provider']
        )
        SWARM_INFO = Info('swarm_fixer', 'Swarm fixer information')
        SWARM_INFO.info({
            'version': '1.0.0',
            'providers': 'ollama,kimi,glm5,dashscope'
        })
    except Exception as e:
        logger.warning(f"Prometheus metrics initialization failed: {e}")
        TELEMETRY_AVAILABLE = False


class FixCategory(Enum):
    """Categories of code fixes"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUG_FIX = "bug_fix"
    CODE_QUALITY = "code_quality"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    TYPE_SAFETY = "type_safety"


class ProviderStatus(Enum):
    """Status of AI providers"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class CodeFix:
    """Represents a code fix"""
    fix_id: str
    file_path: str
    original_code: str
    fixed_code: str
    issue_description: str
    category: str
    confidence: float
    agent_id: str
    line_start: int
    line_end: int
    diff: str
    provider: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Evaluation result for a fix"""
    score: float
    reason: str
    tests_passed: int
    execution_safe: bool
    evaluator: str
    created_at: str
    issues_found: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProviderHealth:
    """Health status of an AI provider"""
    provider: str
    status: ProviderStatus
    latency_ms: float
    last_success: Optional[str]
    error_count: int
    success_count: int


class ASTCodePatcher:
    """Production-grade AST-based code patching with safety guarantees"""

    @staticmethod
    def validate_python_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax without executing"""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"

    @staticmethod
    def apply_fix_with_ast_validation(
        file_path: str,
        fix: CodeFix
    ) -> Tuple[bool, Optional[str]]:
        """Apply fix with full AST validation"""
        try:
            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Validate original file
            valid, error = ASTCodePatcher.validate_python_syntax(original_content)
            if not valid:
                return False, f"Original file has syntax errors: {error}"

            # Validate fixed code
            valid, error = ASTCodePatcher.validate_python_syntax(fix.fixed_code)
            if not valid:
                return False, f"Fixed code has syntax errors: {error}"

            # Apply patch
            original_lines = original_content.splitlines(keepends=True)
            fixed_lines = fix.fixed_code.splitlines(keepends=True)

            # Calculate new content
            new_lines = (
                original_lines[:fix.line_start - 1] +
                fixed_lines +
                ['\n'] +
                original_lines[fix.line_end:]
            )

            new_content = ''.join(new_lines)

            # Final validation of patched content
            valid, error = ASTCodePatcher.validate_python_syntax(new_content)
            if not valid:
                return False, f"Patched code has syntax errors: {error}"

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info(f"Successfully applied fix to {file_path}")
            return True, None

        except Exception as e:
            return False, f"Patch failed: {str(e)}"

    @staticmethod
    def extract_function_context(
        code: str,
        line_number: int,
        context_lines: int = 10
    ) -> Tuple[str, int, int]:
        """Extract complete function/class context using AST"""
        try:
            tree = ast.parse(code)
            lines = code.splitlines()

            # Find the node containing the target line
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        if node.lineno <= line_number <= (node.end_lineno or node.lineno):
                            start = node.lineno - 1
                            end = node.end_lineno or node.lineno
                            func_code = '\n'.join(lines[start:end])
                            return func_code, start + 1, end

            # Fallback to context window
            start = max(0, line_number - context_lines)
            end = min(len(lines), line_number + context_lines)
            context = '\n'.join(lines[start:end])
            return context, start + 1, end

        except Exception as e:
            logger.warning(f"AST parsing failed, using fallback: {e}")
            lines = code.splitlines()
            start = max(0, line_number - context_lines)
            end = min(len(lines), line_number + context_lines)
            context = '\n'.join(lines[start:end])
            return context, start + 1, end

    @staticmethod
    def generate_diff(original: str, fixed: str, file_path: str) -> str:
        """Generate unified diff"""
        original_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        )
        return ''.join(diff)


class HybridAIFixer:
    """
    Hybrid AI code fixer with intelligent provider cascade:
    OLLAMA (primary, local, free) → Kimi K2.5 → GLM-5 → DashScope
    """

    def __init__(self, repository: str = "unknown"):
        self.repository = repository

        # API Keys
        self.kimi_api_key = os.getenv('KIMI_API_KEY', '').strip() or None
        self.glm5_api_key = os.getenv('GLM5_API_KEY', '').strip() or None
        self.dashscope_api_key = os.getenv('DASHSCOPE_API_KEY', '').strip() or None

        # Provider health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}

        # Check OLLAMA availability
        self.ollama_available = self._check_ollama()
        self.ollama_models = self._get_ollama_models() if self.ollama_available else []

        # Initialize health status
        self._init_provider_health()

        logger.info("=" * 60)
        logger.info("Hybrid AI Fixer initialized:")
        logger.info(f"  - OLLAMA: {'✅' if self.ollama_available else '❌'}")
        if self.ollama_available:
            logger.info(f"    Models: {', '.join(self.ollama_models) or 'none'}")
        logger.info(f"  - Kimi K2.5: {'✅' if self.kimi_api_key else '❌'}")
        logger.info(f"  - GLM-5: {'✅' if self.glm5_api_key else '❌'}")
        logger.info(f"  - DashScope: {'✅' if self.dashscope_api_key else '❌'}")
        logger.info("=" * 60)

    def _check_ollama(self) -> bool:
        """Check if OLLAMA is available"""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.info("OLLAMA not installed")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("OLLAMA timeout")
            return False
        except Exception as e:
            logger.warning(f"OLLAMA check failed: {e}")
            return False

    def _get_ollama_models(self) -> List[str]:
        """Get list of available OLLAMA models"""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                models = []
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                return models
        except Exception as e:
            logger.warning(f"Failed to list OLLAMA models: {e}")
        return []

    def _init_provider_health(self):
        """Initialize provider health tracking"""
        self.provider_health['ollama'] = ProviderHealth(
            provider='ollama',
            status=ProviderStatus.AVAILABLE if self.ollama_available else ProviderStatus.UNAVAILABLE,
            latency_ms=0,
            last_success=None,
            error_count=0,
            success_count=0
        )
        self.provider_health['kimi'] = ProviderHealth(
            provider='kimi',
            status=ProviderStatus.AVAILABLE if self.kimi_api_key else ProviderStatus.UNAVAILABLE,
            latency_ms=0,
            last_success=None,
            error_count=0,
            success_count=0
        )
        self.provider_health['glm5'] = ProviderHealth(
            provider='glm5',
            status=ProviderStatus.AVAILABLE if self.glm5_api_key else ProviderStatus.UNAVAILABLE,
            latency_ms=0,
            last_success=None,
            error_count=0,
            success_count=0
        )
        self.provider_health['dashscope'] = ProviderHealth(
            provider='dashscope',
            status=ProviderStatus.AVAILABLE if self.dashscope_api_key else ProviderStatus.UNAVAILABLE,
            latency_ms=0,
            last_success=None,
            error_count=0,
            success_count=0
        )

    async def generate_fix(
        self,
        original_code: str,
        issue: str,
        category: str,
        file_path: str
    ) -> Tuple[Optional[str], str]:
        """
        Generate fix using hybrid cascade approach.
        Returns: (fixed_code, provider_used)
        """
        start_time = time.time()

        # Try providers in order
        providers_to_try = [
            ('ollama', self._generate_with_ollama, self.ollama_available),
            ('kimi', self._generate_with_kimi, bool(self.kimi_api_key)),
            ('glm5', self._generate_with_glm5, bool(self.glm5_api_key)),
            ('dashscope', self._generate_with_dashscope, bool(self.dashscope_api_key)),
        ]

        last_provider = None
        for provider_name, generate_func, is_available in providers_to_try:
            if not is_available:
                continue

            # Track fallback
            if last_provider:
                logger.info(f"⏩ Falling back from {last_provider} to {provider_name}")
                if TELEMETRY_AVAILABLE:
                    PROVIDER_FALLBACK.labels(
                        from_provider=last_provider,
                        to_provider=provider_name
                    ).inc()

            logger.info(f"🤖 Trying {provider_name.upper()}...")
            last_provider = provider_name

            try:
                fixed = await generate_func(original_code, issue, category, file_path)
                if fixed and fixed.strip() and fixed != original_code:
                    duration = time.time() - start_time

                    # Update health
                    self.provider_health[provider_name].success_count += 1
                    self.provider_health[provider_name].last_success = datetime.now(timezone.utc).isoformat()
                    self.provider_health[provider_name].latency_ms = duration * 1000

                    # Prometheus metrics
                    if TELEMETRY_AVAILABLE:
                        FIX_DURATION.labels(
                            provider=provider_name,
                            category=category
                        ).observe(duration)
                        API_CALLS.labels(
                            provider=provider_name,
                            status='success',
                            repository=self.repository
                        ).inc()

                    logger.info(f"✅ {provider_name.upper()} succeeded ({duration:.2f}s)")
                    return fixed, provider_name
                else:
                    logger.warning(f"⚠️ {provider_name.upper()} returned empty/unchanged code")

            except Exception as e:
                logger.error(f"❌ {provider_name.upper()} failed: {e}")
                self.provider_health[provider_name].error_count += 1
                if TELEMETRY_AVAILABLE:
                    API_CALLS.labels(
                        provider=provider_name,
                        status='error',
                        repository=self.repository
                    ).inc()

        logger.error("❌ All AI providers failed")
        return None, 'none'

    async def _generate_with_ollama(
        self,
        original: str,
        issue: str,
        category: str,
        file_path: str
    ) -> Optional[str]:
        """Generate fix using local OLLAMA"""
        prompt = self._create_fix_prompt(original, issue, category, file_path)

        # Try available models in priority order
        model_priority = [
            'kimi-k2.5:cloud',
            'glm5',
            'qwen2.5-coder:14b',
            'deepseek-coder:6.7b',
            'llama3.2:latest',
            'codellama:latest'
        ]

        # Filter to available models
        available_models = [m for m in model_priority if m in self.ollama_models]
        if not available_models and self.ollama_models:
            available_models = self.ollama_models[:2]  # Use first 2 available

        for model in available_models:
            try:
                logger.debug(f"Trying OLLAMA model: {model}")
                result = subprocess.run(
                    ['ollama', 'run', model],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    extracted = self._extract_code(result.stdout)
                    if extracted:
                        logger.debug(f"OLLAMA model {model} succeeded")
                        return extracted

            except subprocess.TimeoutExpired:
                logger.warning(f"OLLAMA model {model} timed out")
                continue
            except Exception as e:
                logger.warning(f"OLLAMA model {model} error: {e}")
                continue

        return None

    async def _generate_with_kimi(
        self,
        original: str,
        issue: str,
        category: str,
        file_path: str
    ) -> Optional[str]:
        """Generate fix using Kimi K2.5 API (Moonshot AI)"""
        if not self.kimi_api_key:
            return None

        prompt = self._create_fix_prompt(original, issue, category, file_path)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.kimi_api_key}',
                    'Content-Type': 'application/json'
                }

                data = {
                    'model': 'moonshot-v1-128k',
                    'messages': [
                        {
                            'role': 'system',
                            'content': f'You are an expert {category} engineer. Fix code issues precisely.'
                        },
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 4000
                }

                async with session.post(
                    'https://api.moonshot.cn/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._extract_code(content)
                    else:
                        text = await response.text()
                        logger.error(f"Kimi API error {response.status}: {text[:200]}")
                        return None

        except Exception as e:
            logger.error(f"Kimi API error: {e}")
            return None

    async def _generate_with_glm5(
        self,
        original: str,
        issue: str,
        category: str,
        file_path: str
    ) -> Optional[str]:
        """Generate fix using GLM-5 API (Zhipu AI)"""
        if not self.glm5_api_key:
            return None

        prompt = self._create_fix_prompt(original, issue, category, file_path)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.glm5_api_key}',
                    'Content-Type': 'application/json'
                }

                data = {
                    'model': 'glm-4-plus',
                    'messages': [
                        {
                            'role': 'system',
                            'content': f'You are an expert {category} engineer.'
                        },
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 4000
                }

                async with session.post(
                    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._extract_code(content)
                    else:
                        text = await response.text()
                        logger.error(f"GLM-5 API error {response.status}: {text[:200]}")
                        return None

        except Exception as e:
            logger.error(f"GLM-5 API error: {e}")
            return None

    async def _generate_with_dashscope(
        self,
        original: str,
        issue: str,
        category: str,
        file_path: str
    ) -> Optional[str]:
        """Generate fix using DashScope API (Alibaba Qwen)"""
        if not self.dashscope_api_key:
            return None

        prompt = self._create_fix_prompt(original, issue, category, file_path)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.dashscope_api_key}',
                    'Content-Type': 'application/json'
                }

                data = {
                    'model': 'qwen-coder-plus',
                    'input': {
                        'messages': [
                            {
                                'role': 'system',
                                'content': f'You are an expert {category} engineer.'
                            },
                            {'role': 'user', 'content': prompt}
                        ]
                    },
                    'parameters': {
                        'temperature': 0.3,
                        'max_tokens': 4000
                    }
                }

                async with session.post(
                    'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get('output', {}).get('text', '')
                        return self._extract_code(content)
                    else:
                        text = await response.text()
                        logger.error(f"DashScope API error {response.status}: {text[:200]}")
                        return None

        except Exception as e:
            logger.error(f"DashScope API error: {e}")
            return None

    def _create_fix_prompt(
        self,
        code: str,
        issue: str,
        category: str,
        file_path: str
    ) -> str:
        """Create optimized fix prompt"""
        return f"""Fix this {category} issue in {file_path}.

CRITICAL RULES:
1. Fix ONLY the specific issue mentioned - no other changes
2. Preserve ALL existing functionality
3. Maintain exact indentation and code style
4. Return ONLY the fixed code in a ```python code block
5. Include necessary imports if missing
6. No explanations or comments outside code

Issue to fix: {issue}

Original code:
```python
{code}
```

Return the complete fixed code:"""

    def _extract_code(self, response: str) -> Optional[str]:
        """Extract code from AI response"""
        if not response:
            return None

        # Try Python code block
        match = re.search(r'```python\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try generic code block
        match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try indented code block
        match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no code block, check if response looks like code
        lines = response.strip().split('\n')
        code_lines = [l for l in lines if l.strip() and not l.startswith('#') and not l.startswith('```')]
        if code_lines and any(keyword in response for keyword in ['def ', 'class ', 'import ', 'return ']):
            return response.strip()

        return None


class HybridEvaluator:
    """
    Hybrid evaluator using YOUR infrastructure:
    OLLAMA (GLM-5) → GLM-5 API → Kimi API → Static Analysis
    """

    def __init__(self, repository: str = "unknown"):
        self.repository = repository
        self.glm5_api_key = os.getenv('GLM5_API_KEY', '').strip() or None
        self.kimi_api_key = os.getenv('KIMI_API_KEY', '').strip() or None
        self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    async def evaluate_fix(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> EvaluationResult:
        """Evaluate fix with hybrid approach"""

        # Try OLLAMA GLM-5 first
        if self.ollama_available:
            result = await self._evaluate_with_ollama(original, fixed, category)
            if result and result.score > 0:
                return result

        # Fallback to GLM-5 API
        if self.glm5_api_key:
            result = await self._evaluate_with_glm5_api(original, fixed, category)
            if result and result.score > 0:
                return result

        # Fallback to Kimi API
        if self.kimi_api_key:
            result = await self._evaluate_with_kimi(original, fixed, category)
            if result and result.score > 0:
                return result

        # Ultimate fallback: static analysis
        return self._static_evaluation(original, fixed, category)

    async def _evaluate_with_ollama(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> Optional[EvaluationResult]:
        """Evaluate with local OLLAMA"""
        prompt = self._create_eval_prompt(original, fixed, category)

        try:
            result = subprocess.run(
                ['ollama', 'run', 'glm5'],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return self._parse_evaluation(result.stdout, 'ollama')
        except:
            pass

        return None

    async def _evaluate_with_glm5_api(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> Optional[EvaluationResult]:
        """Evaluate with GLM-5 API"""
        if not self.glm5_api_key:
            return None

        prompt = self._create_eval_prompt(original, fixed, category)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.glm5_api_key}',
                    'Content-Type': 'application/json'
                }

                data = {
                    'model': 'glm-4-flash',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 500
                }

                async with session.post(
                    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._parse_evaluation(content, 'glm5-api')
        except:
            pass

        return None

    async def _evaluate_with_kimi(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> Optional[EvaluationResult]:
        """Evaluate with Kimi API"""
        if not self.kimi_api_key:
            return None

        prompt = self._create_eval_prompt(original, fixed, category)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.kimi_api_key}',
                    'Content-Type': 'application/json'
                }

                data = {
                    'model': 'moonshot-v1-32k',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 500
                }

                async with session.post(
                    'https://api.moonshot.cn/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._parse_evaluation(content, 'kimi')
        except:
            pass

        return None

    def _static_evaluation(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> EvaluationResult:
        """Static analysis fallback evaluation"""
        issues_found = []

        # Check syntax
        try:
            ast.parse(fixed)
            execution_safe = True
        except SyntaxError as e:
            execution_safe = False
            issues_found.append(f"Syntax error: {e}")

        # Check for common issues
        if 'TODO' in fixed or 'FIXME' in fixed:
            issues_found.append("Contains TODO/FIXME markers")

        if 'pass' in fixed and 'pass' not in original:
            issues_found.append("Added pass statements")

        # Calculate change ratio
        original_lines = set(original.splitlines())
        fixed_lines = set(fixed.splitlines())
        changed = len(original_lines.symmetric_difference(fixed_lines))
        total = len(original_lines) if original_lines else 1
        change_ratio = changed / total

        # Score based on multiple factors
        base_score = 0.7 if execution_safe else 0.3
        change_penalty = min(0.3, change_ratio * 0.3)
        issue_penalty = len(issues_found) * 0.1

        score = max(0.1, min(1.0, base_score - change_penalty - issue_penalty))

        return EvaluationResult(
            score=score,
            reason=f"Static analysis: {len(issues_found)} issues found",
            tests_passed=1 if execution_safe else 0,
            execution_safe=execution_safe,
            evaluator='static',
            created_at=datetime.now(timezone.utc).isoformat(),
            issues_found=issues_found
        )

    def _create_eval_prompt(
        self,
        original: str,
        fixed: str,
        category: str
    ) -> str:
        return f"""Evaluate this {category} code fix.

Original code:
```python
{original[:2000]}
```

Fixed code:
```python
{fixed[:2000]}
```

Rate the fix 0.0-1.0 based on:
- Correctness: Does it fix the issue?
- Quality: Is it well-written?
- Safety: Could it break anything?

Respond ONLY with JSON: {{"score": 0.85, "reason": "brief explanation", "safe": true}}"""

    def _parse_evaluation(
        self,
        response: str,
        evaluator: str
    ) -> Optional[EvaluationResult]:
        """Parse evaluation response"""
        try:
            # Try to find JSON
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return EvaluationResult(
                    score=float(data.get('score', 0)),
                    reason=data.get('reason', 'Parsed from response'),
                    tests_passed=1,
                    execution_safe=data.get('safe', True),
                    evaluator=evaluator,
                    created_at=datetime.now(timezone.utc).isoformat()
                )

            # Try to extract score from text
            score_match = re.search(r'score[:\s]+([0-9.]+)', response, re.IGNORECASE)
            if score_match:
                return EvaluationResult(
                    score=float(score_match.group(1)),
                    reason="Score extracted from text",
                    tests_passed=1,
                    execution_safe=True,
                    evaluator=evaluator,
                    created_at=datetime.now(timezone.utc).isoformat()
                )
        except Exception as e:
            logger.warning(f"Evaluation parsing failed: {e}")

        return None


class MetricsStore:
    """SQLite metrics store with Prometheus export"""

    def __init__(self, db_path: str = "swarm_metrics.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixes (
                fix_id TEXT PRIMARY KEY,
                pr_number INTEGER,
                file_path TEXT,
                category TEXT,
                confidence FLOAT,
                agent_id TEXT,
                approved BOOLEAN,
                evaluation_score FLOAT,
                provider TEXT,
                evaluator TEXT,
                created_at TEXT,
                repository TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_number ON fixes(pr_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON fixes(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider ON fixes(provider)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON fixes(created_at)")

        conn.commit()
        conn.close()

    def record_fix(
        self,
        fix: CodeFix,
        pr_number: int,
        approved: bool,
        evaluation_score: float,
        evaluator: str,
        repository: str = "unknown"
    ):
        """Record fix to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO fixes
            (fix_id, pr_number, file_path, category, confidence, agent_id,
             approved, evaluation_score, provider, evaluator, created_at, repository)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fix.fix_id, pr_number, fix.file_path, fix.category,
            fix.confidence, fix.agent_id, approved, evaluation_score,
            fix.provider, evaluator, fix.created_at, repository
        ))

        conn.commit()
        conn.close()

        # Update Prometheus metrics
        if TELEMETRY_AVAILABLE:
            FIXES_ATTEMPTED.labels(
                category=fix.category,
                repository=repository
            ).inc()
            if approved:
                FIXES_APPROVED.labels(
                    category=fix.category,
                    repository=repository
                ).inc()
            else:
                FIXES_REJECTED.labels(
                    category=fix.category,
                    repository=repository
                ).inc()
            EVALUATION_SCORE.labels(
                category=fix.category,
                fix_id=fix.fix_id[:8]
            ).set(evaluation_score)

    def get_stats(self) -> Dict:
        """Get statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {
            'total_fixes': 0,
            'approved': 0,
            'by_provider': {},
            'by_category': {},
            'avg_score': 0.0
        }

        try:
            cursor.execute("SELECT COUNT(*) FROM fixes")
            stats['total_fixes'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM fixes WHERE approved = 1")
            stats['approved'] = cursor.fetchone()[0]

            cursor.execute("""
                SELECT provider, COUNT(*)
                FROM fixes
                GROUP BY provider
            """)
            stats['by_provider'] = dict(cursor.fetchall())

            cursor.execute("""
                SELECT category, COUNT(*), AVG(evaluation_score)
                FROM fixes
                GROUP BY category
            """)
            for row in cursor.fetchall():
                stats['by_category'][row[0]] = {
                    'count': row[1],
                    'avg_score': row[2] or 0
                }

            cursor.execute("SELECT AVG(evaluation_score) FROM fixes")
            stats['avg_score'] = cursor.fetchone()[0] or 0.0

        except Exception as e:
            logger.error(f"Stats query failed: {e}")

        finally:
            conn.close()

        return stats


class ProductionSwarmFixer:
    """Production swarm using YOUR infrastructure"""

    def __init__(
        self,
        github_token: str,
        repo: str,
        config: Optional[Dict] = None
    ):
        self.github_token = github_token
        self.repo = repo
        self.config = config or {}

        self.ai_fixer = HybridAIFixer(repository=repo)
        self.evaluator = HybridEvaluator(repository=repo)
        self.patcher = ASTCodePatcher()
        self.metrics = MetricsStore()

        # Start Prometheus metrics server
        if TELEMETRY_AVAILABLE:
            try:
                start_http_server(8000)
                logger.info("📊 Prometheus metrics available at http://localhost:8000")
            except Exception as e:
                logger.warning(f"Prometheus server start failed: {e}")

    async def process_pr(self, pr_number: int, issues: List[Dict]) -> Dict:
        """Process PR with full pipeline"""
        start_time = time.time()

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing PR #{pr_number}")
        logger.info(f"Repository: {self.repo}")
        logger.info(f"Issues to fix: {len(issues)}")
        logger.info(f"{'=' * 60}\n")

        if not issues:
            return {
                'status': 'no_issues',
                'pr': pr_number,
                'execution_time_ms': 0
            }

        # Generate fixes
        logger.info("🔧 Generating fixes...")
        fixes = await self._generate_fixes(issues)
        logger.info(f"Generated {len(fixes)} potential fixes")

        if not fixes:
            return {
                'status': 'no_fixes_generated',
                'pr': pr_number,
                'execution_time_ms': (time.time() - start_time) * 1000
            }

        # Evaluate fixes
        logger.info("\n🔍 Evaluating fixes...")
        evaluated = await self._evaluate_fixes(fixes)

        # Apply approved fixes
        approved = [f for f in evaluated if f['approved']]
        logger.info(f"\n✅ {len(approved)}/{len(evaluated)} fixes approved")

        applied = await self._apply_fixes_atomically(approved, pr_number)

        execution_time = (time.time() - start_time) * 1000

        # Get stats
        stats = self.metrics.get_stats()

        return {
            'status': 'completed',
            'pr': pr_number,
            'fixes_total': len(fixes),
            'fixes_approved': len(approved),
            'fixes_applied': applied['count'],
            'execution_time_ms': round(execution_time, 2),
            'stats': stats
        }

    async def _generate_fixes(self, issues: List[Dict]) -> List[Dict]:
        """Generate fixes using hybrid AI"""
        fixes = []

        for i, issue in enumerate(issues):
            try:
                logger.info(f"\n[{i+1}/{len(issues)}] Processing: {issue.get('path', 'unknown')}")

                file_path = issue.get('path')
                if not file_path or not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    continue

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                line_number = issue.get('line', 1)
                original_code, start, end = self.patcher.extract_function_context(
                    content, line_number
                )

                fixed_code, provider = await self.ai_fixer.generate_fix(
                    original_code,
                    issue.get('body', issue.get('description', '')),
                    issue.get('category', 'code_quality'),
                    file_path
                )

                if fixed_code and fixed_code.strip() != original_code.strip():
                    fix_id = hashlib.md5(
                        f"{file_path}:{line_number}:{time.time()}".encode()
                    ).hexdigest()[:12]

                    diff = self.patcher.generate_diff(original_code, fixed_code, file_path)

                    fix = CodeFix(
                        fix_id=fix_id,
                        file_path=file_path,
                        original_code=original_code,
                        fixed_code=fixed_code,
                        issue_description=issue.get('body', ''),
                        category=issue.get('category', 'code_quality'),
                        confidence=0.8,
                        agent_id=f"agent-{issue.get('category', 'general')}",
                        line_start=start,
                        line_end=end,
                        diff=diff,
                        provider=provider,
                        created_at=datetime.now(timezone.utc).isoformat()
                    )

                    fixes.append({'fix': fix, 'issue': issue})
                    logger.info(f"  ✅ Fix generated via {provider}")
                else:
                    logger.warning(f"  ⚠️ No fix generated or code unchanged")

            except Exception as e:
                logger.error(f"  ❌ Error generating fix: {e}")

        return fixes

    async def _evaluate_fixes(self, fixes: List[Dict]) -> List[Dict]:
        """Evaluate fixes with hybrid evaluator"""
        evaluated = []

        for item in fixes:
            fix = item['fix']

            evaluation = await self.evaluator.evaluate_fix(
                fix.original_code,
                fix.fixed_code,
                fix.category
            )

            min_score = self.config.get('min_approval_score', 0.7)
            approved = evaluation.score >= min_score and evaluation.execution_safe

            item['evaluation'] = evaluation
            item['approved'] = approved

            # Record to metrics
            self.metrics.record_fix(
                fix,
                0,  # PR number not available here
                approved,
                evaluation.score,
                evaluation.evaluator,
                self.repo
            )

            status = '✅ APPROVED' if approved else '❌ REJECTED'
            logger.info(
                f"  {status}: {fix.fix_id[:8]}... "
                f"(score: {evaluation.score:.2f}, provider: {fix.provider}, evaluator: {evaluation.evaluator})"
            )

            evaluated.append(item)

        return evaluated

    async def _apply_fixes_atomically(
        self,
        fixes: List[Dict],
        pr_number: int
    ) -> Dict:
        """Apply fixes atomically with rollback support"""
        if not fixes:
            return {'count': 0}

        # Create backup
        backup_ref = f"backup-pr-{pr_number}-{int(time.time())}"
        subprocess.run(['git', 'branch', backup_ref], capture_output=True)

        applied_count = 0
        applied_fixes = []

        try:
            for item in fixes:
                fix = item['fix']
                success, error = self.patcher.apply_fix_with_ast_validation(
                    fix.file_path, fix
                )

                if success:
                    applied_count += 1
                    applied_fixes.append(fix)
                    logger.info(f"  ✅ Applied fix to {fix.file_path}")
                else:
                    logger.error(f"  ❌ Failed to apply fix: {error}")

            # Validate all changes
            if not await self._validate_changes():
                logger.error("Validation failed, rolling back...")
                subprocess.run(['git', 'reset', '--hard', backup_ref], capture_output=True)
                return {'count': 0, 'rolled_back': True}

            # Commit if fixes were applied
            if applied_count > 0:
                await self._create_commit(applied_fixes, pr_number)

            return {'count': applied_count, 'success': True}

        finally:
            # Cleanup backup
            subprocess.run(
                ['git', 'branch', '-D', backup_ref],
                capture_output=True,
                stderr=subprocess.DEVNULL
            )

    async def _validate_changes(self) -> bool:
        """Validate all Python files after changes"""
        try:
            result = subprocess.run(
                ['python3', '-m', 'py_compile'] +
                [f for f in subprocess.getoutput('find . -name "*.py" -type f').split('\n') if f],
                capture_output=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    async def _create_commit(self, fixes: List[CodeFix], pr_number: int):
        """Create git commit for fixes"""
        categories = list(set(f.category for f in fixes))
        providers = list(set(f.provider for f in fixes))

        message = f"""fix: Auto-fix {len(fixes)} issues via hybrid swarm

Categories: {', '.join(categories)}
Providers: {', '.join(providers)}
PR #{pr_number}

Generated by Hybrid Swarm Auto-Fixer
- Primary: OLLAMA (local)
- Fallbacks: Kimi K2.5, GLM-5, DashScope
"""

        subprocess.run(['git', 'add', '.'], capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], capture_output=True)
        logger.info("📝 Created commit for applied fixes")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Hybrid Swarm Auto-Fixer')
    parser.add_argument('--pr', type=int, required=True, help='PR number')
    parser.add_argument('--repo', type=str, required=True, help='Repository (owner/repo)')
    parser.add_argument('--issues', type=str, help='JSON file with issues')
    parser.add_argument('--min-score', type=float, default=0.7, help='Minimum approval score')
    args = parser.parse_args()

    # Check for GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ GITHUB_TOKEN environment variable required")
        sys.exit(1)

    # Load issues
    issues = []
    if args.issues and os.path.exists(args.issues):
        with open(args.issues, 'r') as f:
            issues = json.load(f)
    else:
        # Demo issues for testing
        issues = [
            {
                'path': 'agents/benchmark_executor.py',
                'line': 100,
                'body': 'Consider adding type hints for better code clarity',
                'category': 'code_quality'
            }
        ]

    config = {'min_approval_score': args.min_score}

    fixer = ProductionSwarmFixer(token, args.repo, config)
    result = await fixer.process_pr(args.pr, issues)

    print("\n" + "=" * 60)
    print("HYBRID SWARM FIXER RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
