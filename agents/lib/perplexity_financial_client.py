"""
perplexity_financial_client.py — Vaal AI Empire
Production-grade financial data client using the Perplexity Search API.

Uses the official `perplexityai` SDK (pip install perplexityai):
  from perplexity import Perplexity
  client.search.create(query=..., max_results=..., ...)

Previous revision used the OpenAI-compat chat SDK which was wrong —
the Search API is a separate product with its own endpoint and SDK.

Fixes in this revision:
 • Correct SDK: `from perplexity import Perplexity` + client.search.create()
 • Multi-query batching (up to 5 queries per request)
 • Domain allowlist / denylist via search_domain_filter
 • Language filtering via search_language_filter
 • Regional search via country
 • SEC filings via real EDGAR API (no fake search_mode="sec")
 • Dynamic year via datetime.now().year
 • Bare `except` → `except (ValueError, TypeError)` in _extract_domain
 • logging.basicConfig removed (library must not touch root logger)
 • DEFAULT_NEWS_SOURCES annotated ClassVar[List[str]]
 • avg_latency_ms list → latency_sum_ms + latency_count scalars
 • logger.error → logger.exception to preserve tracebacks
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)  # Application owns root logger config

# ─────────────────────────────────────────────
# Perplexity SDK — lazy import so the module is importable without it
# ─────────────────────────────────────────────

try:
    from perplexity import Perplexity as _PerplexitySDK  # type: ignore[import]
    _SDK_AVAILABLE = True
except ImportError:
    _PerplexitySDK = None  # type: ignore[assignment,misc]
    _SDK_AVAILABLE = False

# ─────────────────────────────────────────────
# SEC EDGAR helpers
# ─────────────────────────────────────────────

_SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SEC_FACTS_URL           = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
_EDGAR_HEADERS           = {"User-Agent": "VaalAI contact@vaalai.co.za"}
_TICKER_CIK_CACHE: Dict[str, int] = {}


def _resolve_cik(ticker: str) -> Optional[int]:
    """Resolve a stock ticker to an SEC CIK number via EDGAR's company list."""
    key = ticker.upper()
    if key in _TICKER_CIK_CACHE:
        return _TICKER_CIK_CACHE[key]
    try:
        resp = requests.get(_SEC_COMPANY_TICKERS_URL, timeout=10, headers=_EDGAR_HEADERS)
        resp.raise_for_status()
        for entry in resp.json().values():
            if entry.get("ticker", "").upper() == key:
                cik = int(entry["cik_str"])
                _TICKER_CIK_CACHE[key] = cik
                return cik
    except Exception:
        logger.exception("CIK lookup failed for ticker %s", ticker)
    return None


def _fetch_edgar_facts(cik: int) -> Optional[str]:
    """Return raw JSON text from EDGAR companyfacts endpoint."""
    try:
        resp = requests.get(
            _SEC_FACTS_URL.format(cik=cik), timeout=15, headers=_EDGAR_HEADERS
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        logger.exception("EDGAR companyfacts request failed for CIK %d", cik)
        return None


# ─────────────────────────────────────────────
# Main client
# ─────────────────────────────────────────────

class PerplexityFinancialClient:
    """
    Financial data client built on the Perplexity Search API.

    SDK reference: https://docs.perplexity.ai/docs/search/quickstart
    Install:       pip install perplexityai

    Features
    --------
    • batch_market_news   — multi-query news search with domain/language/country filters
    • fetch_sec_filing    — real EDGAR API fetch + optional Perplexity summarisation
    • get_health_metrics  — latency, success-rate, error counters
    """

    # Authoritative financial news domains (used as Search API domain allowlist)
    DEFAULT_NEWS_SOURCES: ClassVar[List[str]] = [
        "reuters.com",
        "bloomberg.com",
        "wsj.com",
        "ft.com",
        "cnbc.com",
        "marketwatch.com",
        "seekingalpha.com",
    ]

    # Language filter applied to all news searches
    DEFAULT_LANGUAGE_FILTER: ClassVar[List[str]] = ["en"]

    # Per-result token budget — high for financial content
    DEFAULT_MAX_TOKENS_PER_PAGE: ClassVar[int] = 2048

    def __init__(
        self,
        api_key: Optional[str] = None,
        news_sources: Optional[List[str]] = None,
        language_filter: Optional[List[str]] = None,
    ) -> None:
        if not _SDK_AVAILABLE:
            raise ImportError(
                "perplexityai is required: pip install perplexityai"
            )

        # SDK reads PERPLEXITY_API_KEY env var automatically when api_key=None
        self._client = _PerplexitySDK(api_key=api_key) if api_key else _PerplexitySDK()

        self._news_sources    = news_sources    or self.DEFAULT_NEWS_SOURCES
        self._language_filter = language_filter or self.DEFAULT_LANGUAGE_FILTER

        # Scalar perf counters — never grow in memory
        self._perf: Dict[str, Any] = {
            "calls_total":    0,
            "calls_success":  0,
            "calls_error":    0,
            "latency_sum_ms": 0.0,
            "latency_count":  0,
            "errors_by_type": {},
        }

    # ─────────────────────── internals ───────────────────────

    def _record(self, latency_ms: float, *, success: bool) -> None:
        self._perf["calls_total"]    += 1
        self._perf["latency_sum_ms"] += latency_ms
        self._perf["latency_count"]  += 1
        key = "calls_success" if success else "calls_error"
        self._perf[key] += 1

    def _record_error(self, exc: Exception) -> None:
        name = type(exc).__name__
        self._perf["errors_by_type"][name] = (
            self._perf["errors_by_type"].get(name, 0) + 1
        )
        self._record(0.0, success=False)

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            return urlparse(url).netloc
        except (ValueError, TypeError):
            return "unknown"

    @staticmethod
    def _parse_search_results(search_response: Any) -> List[Dict[str, Any]]:
        """
        Normalise a Search API response into a plain list of dicts.

        Single-query:  search_response.results → flat list
        Multi-query:   search_response.results → list of per-query lists
        """
        raw = search_response.results
        if not raw:
            return []
        # Multi-query returns a list of lists; single returns a flat list
        if isinstance(raw[0], list):
            items: List[Any] = []
            for sublist in raw:
                items.extend(sublist)
            return items
        return list(raw)

    # ─────────────────────── public API ───────────────────────

    def batch_market_news(
        self,
        topics: List[str],
        max_per_topic: int = 3,
        country: Optional[str] = None,
        custom_sources: Optional[List[str]] = None,
        include_sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch financial news for multiple topics using the Search API.

        Uses multi-query mode (up to 5 queries per request) to minimise API calls.
        Domain filtering uses allowlist mode (DEFAULT_NEWS_SOURCES) unless
        `exclude_sources` is provided, in which case denylist mode is used.

        Parameters
        ----------
        topics            : list of search topics / tickers
        max_per_topic     : clamped to [1, 20] per Search API limits
        country           : ISO 3166-1 alpha-2 code (e.g. "US", "ZA")
        custom_sources    : override DEFAULT_NEWS_SOURCES entirely
        include_sources   : allowlist — restrict to these domains
        exclude_sources   : denylist — exclude these domains (prefix "-" added automatically)
        """
        max_per_topic = max(1, min(20, max_per_topic))  # Search API: 1–20

        # Build domain filter — allowlist XOR denylist
        if exclude_sources:
            domain_filter = [f"-{d}" for d in exclude_sources]
        elif include_sources:
            domain_filter = list(include_sources)
        else:
            domain_filter = list(custom_sources or self._news_sources)

        # Batch in chunks of 5 (Search API multi-query limit)
        results: Dict[str, Any] = {}
        BATCH_SIZE = 5

        for batch_start in range(0, len(topics), BATCH_SIZE):
            batch = topics[batch_start : batch_start + BATCH_SIZE]
            start = time.monotonic()

            try:
                kwargs: Dict[str, Any] = dict(
                    query=batch,                          # multi-query list
                    max_results=max_per_topic,
                    search_domain_filter=domain_filter,
                    search_language_filter=self._language_filter,
                    max_tokens_per_page=self.DEFAULT_MAX_TOKENS_PER_PAGE,
                )
                if country:
                    kwargs["country"] = country

                response = self._client.search.create(**kwargs)

                elapsed = (time.monotonic() - start) * 1000
                self._record(elapsed, success=True)

                # Multi-query: results grouped per query in same order
                raw = response.results
                if raw and isinstance(raw[0], list):
                    for topic, topic_results in zip(batch, raw):
                        results[topic] = [self._normalise_result(r) for r in topic_results]
                else:
                    # Fallback: flat list when only one query was in the batch
                    results[batch[0]] = [self._normalise_result(r) for r in raw]

            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                logger.exception("Search API call failed for batch %s", batch)
                self._record_error(exc)
                for topic in batch:
                    results[topic] = {"error": f"{exc!s}"}

        return results

    @staticmethod
    def _normalise_result(r: Any) -> Dict[str, Any]:
        """Convert a Search API result object to a plain dict."""
        return {
            "title":        getattr(r, "title",   ""),
            "url":          getattr(r, "url",     ""),
            "snippet":      getattr(r, "snippet", ""),
            "date":         getattr(r, "date",    ""),
            "last_updated": getattr(r, "last_updated", ""),
        }

    # ─── SEC Filing ───────────────────────────────────────────

    def fetch_sec_filing(
        self,
        ticker: str,
        filing_type: str = "10-K",
        summarise_with_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve SEC filing data from EDGAR, optionally enriched with
        a Perplexity search for additional context.

        Workflow
        --------
        1. Resolve ticker → CIK via EDGAR company list
        2. Fetch companyfacts JSON from EDGAR (structured financial data)
        3. Optionally run a Perplexity search for recent analyst commentary
        """
        start = time.monotonic()

        cik = _resolve_cik(ticker)
        if cik is None:
            return {"error": f"Could not resolve ticker '{ticker}' to a CIK."}

        facts_text = _fetch_edgar_facts(cik)
        if not facts_text:
            return {"error": f"EDGAR companyfacts fetch failed for {ticker} (CIK {cik})."}

        current_year = datetime.now().year  # dynamic — never hardcoded
        metrics      = self._extract_key_metrics(facts_text, filing_type)
        search_ctx: List[Dict[str, Any]] = []

        if summarise_with_search:
            # Single targeted search for analyst context
            try:
                query   = f"{ticker} {filing_type} {current_year} financial results"
                resp    = self._client.search.create(
                    query=query,
                    max_results=3,
                    search_domain_filter=self._news_sources,
                    search_language_filter=["en"],
                    max_tokens_per_page=1024,
                )
                elapsed_partial = (time.monotonic() - start) * 1000
                self._record(elapsed_partial, success=True)
                search_ctx = [self._normalise_result(r) for r in (resp.results or [])]
            except Exception:
                logger.exception("Perplexity context search failed for %s %s", ticker, filing_type)

        elapsed = (time.monotonic() - start) * 1000
        self._record(elapsed, success=True)

        return {
            "ticker":        ticker,
            "filing_type":   filing_type,
            "cik":           cik,
            "year":          current_year,
            "metrics":       metrics,
            "search_context": search_ctx,
            "retrieved_at":  datetime.now().isoformat(),
        }

    @staticmethod
    def _extract_key_metrics(facts_text: str, filing_type: str) -> Dict[str, Any]:
        """
        Extract key financial metrics from EDGAR companyfacts JSON.
        Returns a subset of US-GAAP facts relevant to the filing type.
        """
        try:
            data     = json.loads(facts_text)
            us_gaap  = data.get("facts", {}).get("us-gaap", {})

            def _latest(concept: str) -> Optional[Any]:
                """Return the most recent annual value for a US-GAAP concept."""
                entries = us_gaap.get(concept, {}).get("units", {})
                for unit_vals in entries.values():
                    annual = [
                        v for v in unit_vals
                        if v.get("form") in ("10-K", "10-K/A") and "val" in v
                    ]
                    if annual:
                        return sorted(annual, key=lambda x: x.get("end", ""))[-1].get("val")
                return None

            return {
                "revenues":              _latest("Revenues"),
                "net_income":            _latest("NetIncomeLoss"),
                "eps_basic":             _latest("EarningsPerShareBasic"),
                "total_assets":          _latest("Assets"),
                "total_liabilities":     _latest("Liabilities"),
                "operating_cash_flow":   _latest("NetCashProvidedByUsedInOperatingActivities"),
                "entity_name":           data.get("entityName", ""),
                "cik":                   data.get("cik", ""),
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.exception("Failed to parse EDGAR companyfacts JSON")
            return {}

    # ─── Health / observability ───────────────────────────────

    def get_health_metrics(self) -> Dict[str, Any]:
        """Return aggregated performance and health statistics."""
        pm    = self._perf
        count = pm["latency_count"]
        avg   = pm["latency_sum_ms"] / count if count > 0 else 0.0
        rate  = pm["calls_success"]  / pm["calls_total"] if pm["calls_total"] > 0 else 1.0

        return {
            "calls_total":    pm["calls_total"],
            "calls_success":  pm["calls_success"],
            "calls_error":    pm["calls_error"],
            "avg_latency_ms": round(avg, 2),
            "success_rate":   round(rate, 4),
            "errors_by_type": pm["errors_by_type"],
            "status":         "healthy" if rate >= 0.95 else "degraded",
        }
