"""
PerplexityFinancialClient — Production-grade financial intelligence layer.

Integrates:
  • Perplexity Search API  — real-time market news & filing discovery
  • SEC EDGAR XBRL API     — structured financial facts (no key required)
  • OpenTelemetry          — distributed tracing (OPENTELEMETRY_API_KEY)
  • Prometheus             — RED metrics exposed for Grafana dashboards
  • Exponential backoff    — resilient under transient API failures
  • Circuit breaker        — stops hammering a degraded upstream
  • Rate limiter           — stays within Perplexity's request quota

Environment variables (all sourced from GitHub Actions secrets):
  PERPLEXITY_API_KEY      — required
  OPENTELEMETRY_API_KEY   — optional; disables tracing if absent
  PROMETHEUS_URL          — optional; disables push-gateway metrics if absent
  PROMETHEUS_USER         — optional
  PROMETHEUS_API_KEY      — optional
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import ClassVar, List, Optional
from urllib.parse import urlparse

import httpx  # used for EDGAR; no extra auth required

logger = logging.getLogger(__name__)

# ── Optional: Perplexity SDK ─────────────────────────────────────────────────
try:
    from perplexity import Perplexity
    HAS_PERPLEXITY = True
except ImportError:
    HAS_PERPLEXITY = False
    logger.warning("perplexityai not installed — pip install perplexityai")

# ── Optional: OpenTelemetry ──────────────────────────────────────────────────
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    logger.warning("opentelemetry packages not installed — tracing disabled")

# ── Optional: Prometheus push-gateway ────────────────────────────────────────
try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        push_to_gateway,
    )
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    logger.warning("prometheus_client not installed — metrics disabled")


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

EDGAR_BASE         = "https://data.sec.gov"
EDGAR_SUBMISSIONS  = EDGAR_BASE + "/submissions/CIK{cik}.json"
EDGAR_COMPANY_FACTS= EDGAR_BASE + "/api/xbrl/companyfacts/CIK{cik}.json"
EDGAR_HEADERS      = {"User-Agent": "VaalAIEmpire contact@vaalai.co.za"}

# Perplexity Search API limits
PERPLEXITY_MAX_RESULTS  = 20
PERPLEXITY_MAX_DOMAINS  = 20

# Circuit-breaker thresholds
CB_FAILURE_THRESHOLD  = 5     # consecutive failures before opening
CB_RECOVERY_TIMEOUT   = 60.0  # seconds before attempting half-open probe

# Rate limiter: Perplexity Search API — conservative default
RATE_LIMIT_CALLS = 10         # calls
RATE_LIMIT_PERIOD = 1.0       # per second

SEC_ALLOWLIST: ClassVar[List[str]] = ["sec.gov", "efts.sec.gov", "investor.gov"]
NEWS_DENYLIST: ClassVar[List[str]] = ["-reddit.com", "-quora.com", "-pinterest.com", "-facebook.com", "-twitter.com"]


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    date: Optional[str] = None
    source_domain: str = ""

    def __post_init__(self) -> None:
        self.source_domain = _safe_extract_domain(self.url)


@dataclass
class MarketNewsResult:
    ticker: str
    query: str
    articles: list[SearchResult] = field(default_factory=list)
    fetched_at: str = field(default_factory=_utcnow_iso)
    latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.articles)


@dataclass
class EdgarFact:
    """A single XBRL financial fact from SEC EDGAR."""
    concept: str          # e.g. "us-gaap/Revenues"
    label: str
    value: float
    unit: str             # e.g. "USD", "shares"
    period_end: str       # ISO date
    form: str             # e.g. "10-K"
    fiscal_year: Optional[int] = None


@dataclass
class SECFilingResult:
    ticker: str
    cik: str
    filing_type: str
    filings: list[SearchResult] = field(default_factory=list)
    facts: list[EdgarFact] = field(default_factory=list)
    fetched_at: str = field(default_factory=_utcnow_iso)
    latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def latest_fact(self, concept: str) -> Optional[EdgarFact]:
        """Return the most recent EDGAR fact for a given XBRL concept."""
        matches = [f for f in self.facts if concept.lower() in f.concept.lower()]
        return max(matches, key=lambda f: f.period_end, default=None)


@dataclass
class HealthReport:
    healthy: bool
    latency_ms: Optional[float] = None
    perplexity_ok: bool = False
    edgar_ok: bool = False
    error: Optional[str] = None
    checked_at: str = field(default_factory=_utcnow_iso)


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure: circuit breaker
# ─────────────────────────────────────────────────────────────────────────────

class _CBState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class _CircuitBreaker:
    """
    Thread-safe circuit breaker with CLOSED → OPEN → HALF_OPEN → CLOSED flow.
    Prevents cascading failures when an upstream API is degraded.
    """

    def __init__(self, name: str, threshold: int = CB_FAILURE_THRESHOLD,
                 recovery_timeout: float = CB_RECOVERY_TIMEOUT) -> None:
        self.name             = name
        self._threshold       = threshold
        self._recovery_timeout= recovery_timeout
        self._failures        = 0
        self._state           = _CBState.CLOSED
        self._opened_at       = 0.0
        self._lock            = Lock()

    def call(self, fn, *args, **kwargs):
        with self._lock:
            if self._state == _CBState.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    self._state = _CBState.HALF_OPEN
                    logger.info("[CB:%s] → HALF_OPEN (probing)", self.name)
                else:
                    raise RuntimeError(
                        f"Circuit breaker OPEN for '{self.name}'. "
                        f"Retry in {self._recovery_timeout:.0f}s."
                    )
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                if self._state == _CBState.HALF_OPEN:
                    self._state    = _CBState.CLOSED
                    self._failures = 0
                    logger.info("[CB:%s] → CLOSED (recovered)", self.name)
                elif self._state == _CBState.CLOSED:
                    self._failures = 0
            return result
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self._threshold:
                    self._state     = _CBState.OPEN
                    self._opened_at = time.monotonic()
                    logger.error(
                        "[CB:%s] → OPEN after %d failures", self.name, self._failures
                    )
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure: token-bucket rate limiter
# ─────────────────────────────────────────────────────────────────────────────

class _RateLimiter:
    """Thread-safe token bucket. Blocks the calling thread when empty."""

    def __init__(self, calls: int = RATE_LIMIT_CALLS, period: float = RATE_LIMIT_PERIOD) -> None:
        self._capacity  = calls
        self._tokens    = float(calls)
        self._period    = period
        self._rate      = calls / period
        self._last_refill = time.monotonic()
        self._lock      = Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._capacity,
                self._tokens + elapsed * self._rate,
            )
            self._last_refill = now
            if self._tokens < 1:
                sleep_for = (1 - self._tokens) / self._rate
                time.sleep(sleep_for)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure: retry with exponential backoff
# ─────────────────────────────────────────────────────────────────────────────

def _with_retry(fn, retries: int = 3, base_delay: float = 1.0,
                backoff: float = 2.0, jitter: float = 0.1):
    """
    Execute fn with exponential backoff on transient failures.
    Raises the last exception if all retries are exhausted.
    """
    import random
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = base_delay * (backoff ** attempt) + random.uniform(0, jitter)
                logger.warning(
                    "Retry %d/%d in %.2fs after: %s", attempt + 1, retries, delay, exc
                )
                time.sleep(delay)
    raise last_exc


# ─────────────────────────────────────────────────────────────────────────────
# Observability: OpenTelemetry
# ─────────────────────────────────────────────────────────────────────────────

def _init_tracer(service_name: str = "perplexity-financial-client"):
    if not HAS_OTEL:
        return None
    otel_key = os.environ.get("OPENTELEMETRY_API_KEY", "")
    if not otel_key:
        return None
    try:
        resource  = Resource.create({"service.name": service_name})
        provider  = TracerProvider(resource=resource)
        exporter  = OTLPSpanExporter(
            headers={"api-key": otel_key},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        return trace.get_tracer(service_name)
    except Exception as exc:
        logger.warning("OpenTelemetry init failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Observability: Prometheus metrics
# ─────────────────────────────────────────────────────────────────────────────

class _Metrics:
    """
    Prometheus RED metrics for the financial client.
    Pushed to the Prometheus push-gateway after each operation
    (PROMETHEUS_URL / PROMETHEUS_USER / PROMETHEUS_API_KEY).
    """

    def __init__(self) -> None:
        self._enabled = (
            HAS_PROMETHEUS
            and bool(os.environ.get("PROMETHEUS_URL"))
        )
        if not self._enabled:
            return
        self._registry = CollectorRegistry()
        self.requests_total = Counter(
            "financial_client_requests_total",
            "Total Search API requests",
            ["operation", "status"],
            registry=self._registry,
        )
        self.latency = Histogram(
            "financial_client_latency_seconds",
            "Search API request latency",
            ["operation"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self._registry,
        )
        self.circuit_breaker_state = Gauge(
            "financial_client_circuit_breaker_open",
            "1 if the circuit breaker is open, 0 if closed",
            registry=self._registry,
        )

    def record(self, operation: str, status: str, latency_s: float) -> None:
        if not self._enabled:
            return
        try:
            self.requests_total.labels(operation=operation, status=status).inc()
            self.latency.labels(operation=operation).observe(latency_s)
            self._push()
        except Exception as exc:
            logger.debug("Prometheus record error: %s", exc)

    def _push(self) -> None:
        url  = os.environ.get("PROMETHEUS_URL", "")
        user = os.environ.get("PROMETHEUS_USER", "")
        key  = os.environ.get("PROMETHEUS_API_KEY", "")
        if not url:
            return
        try:
            handler = None
            if user and key:
                import base64
                token = base64.b64encode(f"{user}:{key}".encode()).decode()
                def handler(url, method, timeout, headers, data):
                    headers["Authorization"] = f"Basic {token}"
                    import urllib.request
                    req = urllib.request.Request(url, data=data, headers=headers, method=method)
                    with urllib.request.urlopen(req, timeout=timeout):
                        pass
            push_to_gateway(
                url,
                job="vaal-financial-client",
                registry=self._registry,
                handler=handler,
            )
        except Exception as exc:
            logger.debug("Prometheus push failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# EDGAR CIK resolver
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_cik(ticker: str) -> str:
    """
    Resolve a ticker symbol to an SEC EDGAR CIK using the EDGAR full-text
    search API.  Returns zero-padded 10-digit CIK string.

    Raises:
        ValueError: ticker not found in EDGAR.
        httpx.HTTPError: network / HTTP error.
    """
    url = f"{EDGAR_BASE}/cgi-bin/browse-edgar?company=&CIK={ticker}&type=&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom"
    resp = httpx.get(url, headers=EDGAR_HEADERS, timeout=10.0, follow_redirects=True)
    resp.raise_for_status()

    # Parse CIK from Atom feed
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    entries = root.findall("atom:entry", ns)
    if not entries:
        raise ValueError(f"CIK not found for ticker '{ticker}'")
    cik_tag = entries[0].find("atom:id", ns)
    if cik_tag is None or not cik_tag.text:
        raise ValueError(f"Malformed EDGAR response for ticker '{ticker}'")
    # id text is like: urn:tag:www.sec.gov,2008:accession-number-...
    # The CIK appears in the <content> block; use <updated> URL approach instead
    content = entries[0].find("atom:content", ns)
    if content is not None:
        import re
        match = re.search(r"CIK=(\d+)", content.text or "")
        if match:
            return match.group(1).zfill(10)

    # Fallback: extract from filing-href
    filing_href = entries[0].find(".//{http://www.w3.org/2005/Atom}id")
    if filing_href is not None:
        import re
        match = re.search(r"/(\d{10})/", filing_href.text or "")
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract CIK for ticker '{ticker}'")


# ─────────────────────────────────────────────────────────────────────────────
# EDGAR XBRL fact extraction
# ─────────────────────────────────────────────────────────────────────────────

_XBRL_CONCEPTS = {
    "Revenues":                          "Revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
    "NetIncomeLoss":                     "Net Income",
    "EarningsPerShareBasic":             "EPS (Basic)",
    "EarningsPerShareDiluted":           "EPS (Diluted)",
    "Assets":                            "Total Assets",
    "Liabilities":                       "Total Liabilities",
    "StockholdersEquity":                "Stockholders Equity",
    "OperatingIncomeLoss":               "Operating Income",
    "GrossProfit":                       "Gross Profit",
    "CommonStockSharesOutstanding":      "Shares Outstanding",
    "CashAndCashEquivalentsAtCarryingValue": "Cash & Equivalents",
    "LongTermDebt":                      "Long-Term Debt",
    "ResearchAndDevelopmentExpense":     "R&D Expense",
}


def _extract_edgar_facts(cik: str, filing_type: str = "10-K") -> list[EdgarFact]:
    """
    Pull structured XBRL financial facts from EDGAR companyfacts endpoint.
    Returns the most recent annual (10-K) or quarterly (10-Q) filing facts
    across the key concepts defined in _XBRL_CONCEPTS.

    Args:
        cik:         10-digit zero-padded CIK.
        filing_type: "10-K" or "10-Q".

    Returns:
        List of EdgarFact, one per XBRL concept found.
    """
    url  = EDGAR_COMPANY_FACTS.format(cik=cik)
    resp = httpx.get(url, headers=EDGAR_HEADERS, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    us_gaap = data.get("facts", {}).get("us-gaap", {})
    facts: list[EdgarFact] = []

    for concept, label in _XBRL_CONCEPTS.items():
        concept_data = us_gaap.get(concept)
        if not concept_data:
            continue
        units_block = concept_data.get("units", {})
        # USD for monetary, pure for ratios, shares for counts
        for unit_label, entries in units_block.items():
            # Filter to the requested form type and pick most recent
            filtered = [
                e for e in entries
                if e.get("form") == filing_type
                and e.get("end")
                and isinstance(e.get("val"), (int, float))
            ]
            if not filtered:
                continue
            latest = max(filtered, key=lambda e: e["end"])
            fy = latest.get("fy")
            facts.append(EdgarFact(
                concept    = f"us-gaap/{concept}",
                label      = label,
                value      = float(latest["val"]),
                unit       = unit_label,
                period_end = latest["end"],
                form       = latest["form"],
                fiscal_year= int(fy) if fy else None,
            ))
            break   # one unit type per concept is enough

    return sorted(facts, key=lambda f: f.period_end, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main client
# ─────────────────────────────────────────────────────────────────────────────

class PerplexityFinancialClient:
    """
    Production financial intelligence client.

    Data sources:
      1. Perplexity Search API  — real-time news & filing discovery
      2. SEC EDGAR XBRL API     — authoritative structured financial facts

    Observability:
      • OpenTelemetry distributed traces (OPENTELEMETRY_API_KEY)
      • Prometheus RED metrics pushed to gateway (PROMETHEUS_URL)

    Resilience:
      • Exponential backoff retries (3 attempts, 2× backoff)
      • Per-upstream circuit breakers
      • Token-bucket rate limiter (10 req/s default)

    Optional Perplexity integration: FinancialSentinelAgent instantiates
    this client only when PERPLEXITY_API_KEY is present; the agent degrades
    gracefully without it. EDGAR access is always available (no key needed).
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Args:
            api_key: Perplexity API key.  Defaults to PERPLEXITY_API_KEY env var.

        Raises:
            ImportError: perplexityai package not installed.
            ValueError:  API key missing or blank.
        """
        if not HAS_PERPLEXITY:
            raise ImportError(
                "perplexityai not installed. Run: pip install perplexityai"
            )

        resolved_key = api_key or os.environ.get("PERPLEXITY_API_KEY", "")
        if not resolved_key or not resolved_key.strip():
            raise ValueError(
                "Perplexity API key not found. "
                "Set PERPLEXITY_API_KEY or pass api_key= explicitly."
            )

        self._client       = Perplexity(api_key=resolved_key)
        self._rate_limiter = _RateLimiter()
        self._cb_perplexity= _CircuitBreaker("perplexity-search")
        self._cb_edgar     = _CircuitBreaker("edgar-xbrl")
        self._metrics      = _Metrics()
        self._tracer       = _init_tracer()

        logger.info(
            "PerplexityFinancialClient ready — OTEL=%s Prometheus=%s",
            self._tracer is not None,
            self._metrics._enabled,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_market_news(
        self,
        ticker: str,
        company_name: Optional[str] = None,
        max_results: int = 10,
        country: str = "ZA",
    ) -> MarketNewsResult:
        """
        Fetch real-time market news for a ticker via Perplexity Search API.

        Args:
            ticker:       Stock/crypto ticker, e.g. "JSE:NPN", "AAPL".
            company_name: Human-readable name to enrich the query.
            max_results:  Ranked results to return (1–20).
            country:      ISO 3166-1 alpha-2 regional bias (default: ZA).

        Returns:
            MarketNewsResult with ranked SearchResult articles.
        """
        span_ctx = self._start_span("fetch_market_news", {"ticker": ticker})
        t0 = time.monotonic()
        label = company_name or ticker
        query = (
            f"{label} ({ticker}) stock market news earnings revenue "
            f"financial results analyst outlook"
        )

        try:
            self._rate_limiter.acquire()

            def _call():
                return self._client.search.create(
                    query=query,
                    search_domain_filter=NEWS_DENYLIST,
                    country=country,
                    max_results=min(max_results, PERPLEXITY_MAX_RESULTS),
                    max_tokens_per_page=2048,
                )

            response = self._cb_perplexity.call(
                lambda: _with_retry(_call, retries=3)
            )

            articles = [
                SearchResult(
                    title   = r.title,
                    url     = r.url,
                    snippet = r.snippet,
                    date    = getattr(r, "date", None),
                )
                for r in (getattr(response, "results", None) or [])
            ]

            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record("fetch_market_news", "success", latency_ms / 1000)
            self._end_span(span_ctx, {"result_count": len(articles)})
            logger.info("fetch_market_news(%s): %d results in %.0fms",
                        ticker, len(articles), latency_ms)

            return MarketNewsResult(
                ticker     = ticker,
                query      = query,
                articles   = articles,
                latency_ms = round(latency_ms, 1),
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record("fetch_market_news", "error", latency_ms / 1000)
            self._end_span(span_ctx, {"error": str(exc)}, error=True)
            logger.error("fetch_market_news(%s) failed in %.0fms: %s",
                         ticker, latency_ms, exc)
            return MarketNewsResult(ticker=ticker, query=query, error=str(exc),
                                    latency_ms=round(latency_ms, 1))

    def fetch_sec_filings(
        self,
        ticker: str,
        filing_type: str = "10-K",
        max_results: int = 5,
    ) -> SECFilingResult:
        """
        Fetch SEC filings combining:
          1. Perplexity Search (sec.gov allowlist) for filing discovery
          2. EDGAR XBRL API for authoritative structured financial facts

        Args:
            ticker:       US-listed ticker (EDGAR lookup by symbol).
            filing_type:  SEC form type: "10-K", "10-Q", "8-K", etc.
            max_results:  Search results for filing discovery (1–20).

        Returns:
            SECFilingResult with ranked filings + structured XBRL facts.
        """
        span_ctx = self._start_span("fetch_sec_filings",
                                    {"ticker": ticker, "form": filing_type})
        t0 = time.monotonic()
        query = f"{ticker} SEC {filing_type} EDGAR annual report filing"
        cik   = ""

        try:
            # ── 1. Perplexity Search (filing discovery) ──────────────────────
            self._rate_limiter.acquire()

            def _search():
                return self._client.search.create(
                    query=query,
                    search_domain_filter=SEC_ALLOWLIST,
                    max_results=min(max_results, PERPLEXITY_MAX_RESULTS),
                    max_tokens_per_page=4096,
                )

            response = self._cb_perplexity.call(
                lambda: _with_retry(_search, retries=3)
            )

            raw = getattr(response, "results", None) or []
            filings = [
                SearchResult(
                    title   = r.title,
                    url     = r.url,
                    snippet = r.snippet,
                    date    = getattr(r, "date", None),
                )
                for r in raw
            ]

            # ── 2. EDGAR XBRL (structured financial facts) ───────────────────
            facts: list[EdgarFact] = []
            try:
                cik = self._cb_edgar.call(
                    lambda: _with_retry(lambda: _resolve_cik(ticker), retries=2)
                )
                facts = self._cb_edgar.call(
                    lambda: _with_retry(
                        lambda: _extract_edgar_facts(cik, filing_type), retries=2
                    )
                )
                logger.info("EDGAR XBRL: %d facts for %s (CIK %s)", len(facts), ticker, cik)
            except ValueError as ve:
                # Ticker not in EDGAR (non-US listings like JSE) — not an error
                logger.info("EDGAR: %s — skipping XBRL (non-US listing?)", ve)
            except Exception as edgar_exc:
                # EDGAR unavailable — degrade gracefully, still return search results
                logger.warning("EDGAR XBRL fetch failed for %s: %s", ticker, edgar_exc)

            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record("fetch_sec_filings", "success", latency_ms / 1000)
            self._end_span(span_ctx, {
                "filing_count": len(filings), "fact_count": len(facts)
            })
            logger.info(
                "fetch_sec_filings(%s, %s): %d filings, %d XBRL facts in %.0fms",
                ticker, filing_type, len(filings), len(facts), latency_ms,
            )

            return SECFilingResult(
                ticker      = ticker,
                cik         = cik,
                filing_type = filing_type,
                filings     = filings,
                facts       = facts,
                latency_ms  = round(latency_ms, 1),
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record("fetch_sec_filings", "error", latency_ms / 1000)
            self._end_span(span_ctx, {"error": str(exc)}, error=True)
            logger.error("fetch_sec_filings(%s) failed in %.0fms: %s",
                         ticker, latency_ms, exc)
            return SECFilingResult(
                ticker      = ticker,
                cik         = cik,
                filing_type = filing_type,
                error       = str(exc),
                latency_ms  = round(latency_ms, 1),
            )

    def fetch_company_financials(
        self,
        ticker: str,
        company_name: Optional[str] = None,
    ) -> dict:
        """
        Unified financial intelligence for a company.

        Combines market news (Perplexity Search) + authoritative EDGAR
        XBRL facts into a single dict for agent tool consumption.

        Returns:
            {ticker, news, filings, xbrl_facts, summary_metrics, fetched_at, error}
        """
        news    = self.fetch_market_news(ticker, company_name=company_name, max_results=5)
        filings = self.fetch_sec_filings(ticker, filing_type="10-K", max_results=3)

        # Build a clean summary of XBRL key metrics for the agent
        summary: dict[str, object] = {}
        for fact in filings.facts:
            summary[fact.label] = {
                "value":      fact.value,
                "unit":       fact.unit,
                "period_end": fact.period_end,
                "fiscal_year":fact.fiscal_year,
            }

        return {
            "ticker":          ticker,
            "cik":             filings.cik,
            "news":            [_result_to_dict(a) for a in news.articles],
            "filings":         [_result_to_dict(f) for f in filings.filings],
            "xbrl_facts":      [
                {
                    "label":       f.label,
                    "value":       f.value,
                    "unit":        f.unit,
                    "period_end":  f.period_end,
                    "fiscal_year": f.fiscal_year,
                    "form":        f.form,
                }
                for f in filings.facts
            ],
            "summary_metrics": summary,
            "fetched_at":      _utcnow_iso(),
            "error":           news.error or filings.error,
        }

    def health_check(self) -> HealthReport:
        """
        Verify connectivity to both Perplexity Search API and EDGAR.

        Returns:
            HealthReport with per-upstream status and end-to-end latency.
        """
        t0 = time.monotonic()
        perplexity_ok = False
        edgar_ok      = False
        errors: list[str] = []

        # ── Perplexity probe ─────────────────────────────────────────────────
        try:
            self._rate_limiter.acquire()
            probe = self._client.search.create(
                query="Vaal AI financial markets",
                max_results=1,
                max_tokens_per_page=64,
            )
            perplexity_ok = bool(getattr(probe, "results", None))
        except Exception as exc:
            errors.append(f"Perplexity: {exc}")
            logger.warning("Health check — Perplexity failed: %s", exc)

        # ── EDGAR probe ──────────────────────────────────────────────────────
        try:
            resp = httpx.get(
                f"{EDGAR_BASE}/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&count=1&output=atom",
                headers=EDGAR_HEADERS,
                timeout=8.0,
                follow_redirects=True,
            )
            edgar_ok = resp.status_code == 200
        except Exception as exc:
            errors.append(f"EDGAR: {exc}")
            logger.warning("Health check — EDGAR failed: %s", exc)

        latency_ms = (time.monotonic() - t0) * 1000
        healthy    = perplexity_ok and edgar_ok

        return HealthReport(
            healthy        = healthy,
            latency_ms     = round(latency_ms, 1),
            perplexity_ok  = perplexity_ok,
            edgar_ok       = edgar_ok,
            error          = "; ".join(errors) if errors else None,
        )

    # ── Observability helpers ─────────────────────────────────────────────────

    def _start_span(self, name: str, attributes: dict) -> object:
        if self._tracer is None:
            return None
        try:
            span = self._tracer.start_span(name)
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
            return span
        except Exception:
            return None

    def _end_span(self, span, attributes: dict, error: bool = False) -> None:
        if span is None:
            return
        try:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
            if error and HAS_OTEL:
                span.set_status(trace.StatusCode.ERROR)
            span.end()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return "unknown"


def _result_to_dict(r: SearchResult) -> dict:
    return {
        "title":         r.title,
        "url":           r.url,
        "snippet":       r.snippet,
        "date":          r.date,
        "source_domain": r.source_domain,
    }
