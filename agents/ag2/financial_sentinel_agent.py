"""
financial_sentinel_agent.py — Vaal AI Empire
Production-grade AG2 financial sentinel agent.

Updated to use the Perplexity Search API correctly:
 • batch_market_news exposes domain/country/language/exclude controls
 • max_results clamped to [1, 20] (Search API limit)
 • perplexity_api_key: Optional[str]
 • Ellipsis only on actual truncation
 • {e!s} in exception f-strings
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

from agents.lib.perplexity_financial_client import PerplexityFinancialClient


class FinancialSentinelAgent:
    """
    AG2-powered financial monitoring agent.

    Registers Perplexity Search API tools conditionally when an API key is supplied.
    The PERPLEXITY_API_KEY environment variable is used automatically when
    perplexity_api_key is not passed explicitly.
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
            logger.info("[%s] Perplexity Search client initialised.", self.name)
        except ImportError as exc:
            self.perplexity = None
            logger.warning("[%s] %s — tools disabled.", self.name, exc)

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
            return self.fetch_market_news(topics, max_results, country=country)

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
        topics: List[str],
        max_results: int = 3,
        country: Optional[str] = None,
        exclude_sources: Optional[List[str]] = None,
    ) -> str:
        """
        Search real-time financial news for `topics`.

        max_results is clamped to [1, 20] (Search API hard limit).
        Defaults to the agent's `default_country` when country is not specified.
        """
        if self.perplexity is None:
            return "❌ Market news unavailable: Perplexity Search client not initialised."

        max_results = max(1, min(20, max_results))
        country     = country or self.default_country

        try:
            results = self.perplexity.batch_market_news(
                topics,
                max_per_topic=max_results,
                country=country,
                exclude_sources=exclude_sources,
            )
        except Exception as e:
            return f"❌ Error fetching market news: {e!s}"

        parts: List[str] = []
        for topic, articles in results.items():
            if isinstance(articles, dict) and "error" in articles:
                parts.append(f"**{topic}**: ⚠ {articles['error']}")
                continue

            parts.append(f"### {topic}")
            for art in articles:
                title   = art.get("title",   "Untitled")
                snippet = art.get("snippet", "")
                url     = art.get("url",     "")
                date    = art.get("date",    "")

                # Ellipsis only when actually truncated
                snippet_display = snippet[:120] + "…" if len(snippet) > 120 else snippet
                url_display     = url[:70]     + "…" if len(url) > 70         else url

                parts.append(f"  • **{title}**")
                parts.append(f"    {snippet_display}")
                parts.append(f"    🔗 {url_display}" + (f"  _(published: {date})_" if date else ""))

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
            data = self.perplexity.fetch_sec_filing(ticker, filing_type)
        except Exception as e:
            return f"❌ Error fetching financials for {ticker}: {e!s}"

        if "error" in data:
            return f"❌ {data['error']}"

        m     = data.get("metrics", {})
        lines = [
            f"## {m.get('entity_name', ticker)} — {filing_type} ({data.get('year', 'N/A')})",
            f"CIK: {data.get('cik', 'N/A')}",
            "",
            "### Key Metrics",
        ]

        metric_labels = {
            "revenues":            "Revenue",
            "net_income":          "Net Income",
            "eps_basic":           "EPS (Basic)",
            "total_assets":        "Total Assets",
            "total_liabilities":   "Total Liabilities",
            "operating_cash_flow": "Operating Cash Flow",
        }
        for key, label in metric_labels.items():
            val = m.get(key)
            if val is not None:
                # Format large numbers with commas
                try:
                    lines.append(f"  {label}: {float(val):,.2f}")
                except (ValueError, TypeError):
                    lines.append(f"  {label}: {val}")

        ctx = data.get("search_context", [])
        if ctx:
            lines += ["", "### Recent Coverage"]
            for item in ctx[:3]:
                lines.append(f"  • {item.get('title', '')}")
                lines.append(f"    {item.get('url', '')}")

        lines.append(f"\n_Retrieved: {data.get('retrieved_at', 'unknown')}_")
        return "\n".join(lines)

    def get_health(self) -> Dict[str, Any]:
        """Return Perplexity client health metrics."""
        if self.perplexity is None:
            return {"status": "disabled", "reason": "Client not initialised."}
        return self.perplexity.get_health_metrics()
