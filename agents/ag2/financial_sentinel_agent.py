"""
financial_sentinel_agent.py — Vaal AI Empire
Production-grade AG2 financial sentinel agent.

Updated to use the PerplexityFinancialClient with:
 • Circuit breaker resilience
 • Rate limiting
 • OpenTelemetry tracing
 • Prometheus metrics
 • SEC EDGAR XBRL structured facts

The agent degrades gracefully when PERPLEXITY_API_KEY is absent:
 all EDGAR operations still work (no key required).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import autogen
    _HAS_AUTOGEN = True
except ImportError:
    _HAS_AUTOGEN = False
    logger.warning("autogen not installed — FinancialSentinelAgent will be limited.")

from agents.lib.perplexity_financial_client import (
    PerplexityFinancialClient,
    MarketNewsResult,
    SECFilingResult,
)


class FinancialSentinelAgent:
    """
    AG2-powered financial monitoring agent.

    Registers Perplexity Search API tools conditionally when an API key is supplied.
    The PERPLEXITY_API_KEY environment variable is used automatically when
    perplexity_api_key is not passed explicitly.

    When no API key is available, EDGAR operations still work (no key required)
    but news search will be disabled.
    """

    def __init__(
        self,
        llm_config: Dict[str, Any],
        perplexity_api_key: Optional[str] = None,
        name: str = "FinancialSentinel",
        default_country: Optional[str] = None,
    ) -> None:
        self.name            = name
        self.llm_config      = llm_config
        self.default_country = default_country  # e.g. "ZA" for South Africa

        # Client reads PERPLEXITY_API_KEY env var when api_key=None
        try:
            self.perplexity: Optional[PerplexityFinancialClient] = (
                PerplexityFinancialClient(api_key=perplexity_api_key)
            )
            logger.info("[%s] PerplexityFinancialClient initialised.", self.name)
        except ImportError as exc:
            self.perplexity = None
            logger.warning("[%s] %s — tools disabled.", self.name, exc)
        except ValueError as exc:
            # No API key provided and not in environment
            self.perplexity = None
            logger.info("[%s] No Perplexity API key — EDGAR-only mode.", self.name)

        if _HAS_AUTOGEN:
            self._agent = autogen.AssistantAgent(
                name=self.name,
                llm_config=llm_config,
                system_message=self._system_message(),
            )
            self._register_tools()

    # ─────────── private ───────────

    @staticmethod
    def _system_message() -> str:
        return (
            "You are FinancialSentinel, an expert financial analyst for African markets. "
            "Use available tools to retrieve real-time market news and SEC/regulatory filings. "
            "Always cite your sources, flag data quality issues, and note when data "
            "may be delayed or incomplete."
        )

    def _register_tools(self) -> None:
        if self.perplexity is None:
            return

        @self._agent.register_for_execution()
        @self._agent.register_for_llm(
            name="fetch_market_news",
            description=(
                "Search real-time financial news for given tickers or topics. "
                "Returns ranked results from authoritative financial sources."
            ),
        )
        def _tool_fetch_news(
            topics: List[str],
            max_results: int = 3,
            country: Optional[str] = None,
        ) -> str:
            # Handle single ticker or list of topics
            if isinstance(topics, str):
                topics = [topics]
            ticker = topics[0] if topics else "UNKNOWN"
            return self.fetch_market_news(ticker, max_results, country=country)

        @self._agent.register_for_execution()
        @self._agent.register_for_llm(
            name="fetch_company_financials",
            description=(
                "Fetch SEC EDGAR filing data for a stock ticker. "
                "Returns key financial metrics (revenue, net income, EPS, assets, etc.) "
                "plus recent analyst commentary from the web."
            ),
        )
        def _tool_fetch_financials(
            ticker: str,
            filing_type: str = "10-K",
        ) -> str:
            return self.fetch_company_financials(ticker, filing_type)

    # ─────────── public tool methods ───────────

    def fetch_market_news(
        self,
        ticker: str,
        max_results: int = 3,
        country: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> str:
        """
        Search real-time financial news for `ticker`.

        max_results is clamped to [1, 20] (Search API hard limit).
        Defaults to the agent's `default_country` when country is not specified.
        """
        if self.perplexity is None:
            return "❌ Market news unavailable: Perplexity Search client not initialised."

        country = country or self.default_country or "US"

        try:
            result: MarketNewsResult = self.perplexity.fetch_market_news(
                ticker=ticker,
                company_name=company_name,
                max_results=max_results,
                country=country,
            )
        except Exception as e:
            return f"❌ Error fetching market news: {e!s}"

        if result.error:
            return f"❌ {result.error}"

        parts: List[str] = []
        for article in result.articles:
            title   = article.title or "Untitled"
            snippet = article.snippet or ""
            url     = article.url or ""
            date    = article.date or ""

            # Ellipsis only when actually truncated
            snippet_display = snippet[:120] + "…" if len(snippet) > 120 else snippet
            url_display     = url[:70]     + "…" if len(url) > 70         else url

            parts.append(f"• **{title}**")
            parts.append(f"  {snippet_display}")
            parts.append(f"  🔗 {url_display}" + (f"  _(published: {date})_" if date else ""))

        return "\n".join(parts) if parts else "No results found."

    def fetch_company_financials(
        self,
        ticker: str,
        filing_type: str = "10-K",
    ) -> str:
        """Fetch and format SEC EDGAR filing metrics for `ticker`."""
        if self.perplexity is None:
            return "❌ Financials unavailable: Perplexity Search client not initialised."

        try:
            result: SECFilingResult = self.perplexity.fetch_sec_filings(
                ticker=ticker,
                filing_type=filing_type,
                max_results=3,
            )
        except Exception as e:
            return f"❌ Error fetching financials for {ticker}: {e!s}"

        if result.error:
            return f"❌ {result.error}"

        lines = [
            f"## {ticker} — {filing_type}",
            f"CIK: {result.cik or 'N/A'}",
            "",
            "### Key Metrics",
        ]

        for fact in result.facts[:10]:  # Limit to 10 facts for readability
            value_str = f"{fact.value:,.2f}" if abs(fact.value) >= 1000 else f"{fact.value:.4f}"
            lines.append(f"  {fact.label}: {value_str} {fact.unit}")
            lines.append(f"    Period: {fact.period_end} (FY {fact.fiscal_year or 'N/A'})")

        if result.filings:
            lines += ["", "### Recent Filings"]
            for filing in result.filings[:3]:
                lines.append(f"  • [{filing.title}]({filing.url})")

        lines.append(f"\n_Retrieved in {result.latency_ms:.0f}ms_")
        return "\n".join(lines)

    def get_health(self) -> Dict[str, Any]:
        """Return Perplexity client health metrics."""
        if self.perplexity is None:
            return {"status": "disabled", "reason": "Client not initialised."}
        report = self.perplexity.health_check()
        return {
            "status":        "healthy" if report.healthy else "degraded",
            "latency_ms":    report.latency_ms,
            "perplexity_ok": report.perplexity_ok,
            "edgar_ok":      report.edgar_ok,
            "error":         report.error,
        }
