"""
Integration tests for PerplexityFinancialClient.

These tests hit the REAL Perplexity Search API and REAL SEC EDGAR API.
No mocks. No stubs. Tests skip automatically when secrets are absent
so they never block CI on a cold environment.

Requirements:
    PERPLEXITY_API_KEY must be set (GitHub Actions secret is fine)

Run locally:
    pytest agents/lib/test_perplexity_client.py -v -s

Run in CI (key injected from secrets):
    pytest agents/lib/test_perplexity_client.py -v
"""

from __future__ import annotations

import os
import unittest

LIVE_KEY = os.environ.get("PERPLEXITY_API_KEY", "").strip()

# Import HAS_PERPLEXITY from the module under test
from agents.lib.perplexity_financial_client import HAS_PERPLEXITY

from agents.lib.perplexity_financial_client import (
    PerplexityFinancialClient,
    SearchResult,
    MarketNewsResult,
    SECFilingResult,
    HealthReport,
    _resolve_cik,
    _extract_edgar_facts,
    _safe_extract_domain,
    _utcnow_iso,
    SEC_ALLOWLIST,
    NEWS_DENYLIST,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _skip_no_key():
    return unittest.skipUnless(
        HAS_PERPLEXITY and bool(LIVE_KEY),
        "PERPLEXITY_API_KEY not set or perplexityai not installed"
    )


def _client() -> PerplexityFinancialClient:
    return PerplexityFinancialClient(api_key=LIVE_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation — these run without a live key
# ─────────────────────────────────────────────────────────────────────────────

class TestClientInit(unittest.TestCase):

    @unittest.skipUnless(HAS_PERPLEXITY, "perplexityai not installed")
    def test_blank_key_raises_value_error(self):
        with self.assertRaises(ValueError):
            PerplexityFinancialClient(api_key="")

    @unittest.skipUnless(HAS_PERPLEXITY, "perplexityai not installed")
    def test_whitespace_key_raises_value_error(self):
        with self.assertRaises(ValueError):
            PerplexityFinancialClient(api_key="   ")

    def test_missing_package_raises_import_error(self):
        import importlib, sys
        # Temporarily shadow the module
        real = sys.modules.pop("perplexity", None)
        import agents.lib.perplexity_financial_client as m
        original = m.HAS_PERPLEXITY
        m.HAS_PERPLEXITY = False
        try:
            with self.assertRaises(ImportError):
                PerplexityFinancialClient(api_key="pplx-fake")
        finally:
            m.HAS_PERPLEXITY = original
            if real is not None:
                sys.modules["perplexity"] = real


# ─────────────────────────────────────────────────────────────────────────────
# EDGAR (no key required — always live)
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgarCikResolution(unittest.TestCase):

    def test_apple_cik_resolves(self):
        cik = _resolve_cik("AAPL")
        self.assertEqual(len(cik), 10)
        # AAPL CIK is 0000320193
        self.assertEqual(cik.lstrip("0"), "320193")

    def test_microsoft_cik_resolves(self):
        cik = _resolve_cik("MSFT")
        self.assertEqual(len(cik), 10)

    def test_unknown_ticker_raises_value_error(self):
        with self.assertRaises(ValueError):
            _resolve_cik("XXXXNOTREAL99999")


class TestEdgarXbrlFacts(unittest.TestCase):

    def test_apple_annual_facts_returned(self):
        cik   = _resolve_cik("AAPL")
        facts = _extract_edgar_facts(cik, filing_type="10-K")
        self.assertIsInstance(facts, list)
        self.assertGreater(len(facts), 0)

        labels = {f.label for f in facts}
        # AAPL 10-K must have at minimum these concepts
        self.assertIn("Revenue", labels)
        self.assertIn("Net Income", labels)

    def test_fact_fields_are_populated(self):
        cik   = _resolve_cik("AAPL")
        facts = _extract_edgar_facts(cik, filing_type="10-K")
        revenue = next((f for f in facts if f.label == "Revenue"), None)
        self.assertIsNotNone(revenue, "Revenue fact missing for AAPL")
        self.assertIsInstance(revenue.value, float)
        self.assertGreater(revenue.value, 0)
        self.assertEqual(revenue.unit, "USD")
        self.assertRegex(revenue.period_end, r"\d{4}-\d{2}-\d{2}")
        self.assertEqual(revenue.form, "10-K")

    def test_facts_sorted_most_recent_first(self):
        cik   = _resolve_cik("MSFT")
        facts = _extract_edgar_facts(cik, filing_type="10-K")
        if len(facts) > 1:
            self.assertGreaterEqual(facts[0].period_end, facts[1].period_end)

    def test_quarterly_facts_returned_for_10q(self):
        cik   = _resolve_cik("AAPL")
        facts = _extract_edgar_facts(cik, filing_type="10-Q")
        self.assertGreater(len(facts), 0)
        for f in facts:
            self.assertEqual(f.form, "10-Q")


# ─────────────────────────────────────────────────────────────────────────────
# Perplexity Search API — live, requires PERPLEXITY_API_KEY
# ─────────────────────────────────────────────────────────────────────────────

@_skip_no_key()
class TestHealthCheck(unittest.TestCase):

    def test_both_upstreams_healthy(self):
        report = _client().health_check()
        self.assertIsInstance(report, HealthReport)
        self.assertTrue(report.perplexity_ok,
                        msg=f"Perplexity unhealthy: {report.error}")
        self.assertTrue(report.edgar_ok,
                        msg=f"EDGAR unhealthy: {report.error}")
        self.assertTrue(report.healthy)
        self.assertIsNotNone(report.latency_ms)
        self.assertGreater(report.latency_ms, 0)


@_skip_no_key()
class TestFetchMarketNews(unittest.TestCase):

    def test_returns_articles_for_apple(self):
        result = _client().fetch_market_news("AAPL", company_name="Apple", max_results=5)
        self.assertIsInstance(result, MarketNewsResult)
        self.assertTrue(result.success, msg=result.error)
        self.assertGreater(len(result.articles), 0)

    def test_each_article_has_required_fields(self):
        result = _client().fetch_market_news("AAPL", max_results=3)
        self.assertTrue(result.success, msg=result.error)
        for article in result.articles:
            self.assertIsInstance(article, SearchResult)
            self.assertTrue(article.title,   "title is blank")
            self.assertTrue(article.url,     "url is blank")
            self.assertTrue(article.snippet, "snippet is blank")
            self.assertTrue(article.url.startswith("http"),
                            f"Bad URL: {article.url}")
            self.assertTrue(article.source_domain,
                            f"domain not extracted for {article.url}")

    def test_denylist_domains_not_in_results(self):
        result = _client().fetch_market_news("MSFT", max_results=10)
        self.assertTrue(result.success, msg=result.error)
        blocked = {d.lstrip("-") for d in NEWS_DENYLIST}
        for article in result.articles:
            domain = article.source_domain
            for bad in blocked:
                self.assertNotIn(bad, domain,
                                 f"Denylist domain '{bad}' appeared in results")

    def test_latency_recorded(self):
        result = _client().fetch_market_news("TSLA", max_results=3)
        self.assertGreater(result.latency_ms, 0)

    def test_zse_ticker_returns_results(self):
        """African-market ticker — should not raise, gracefully handles."""
        result = _client().fetch_market_news(
            "JSE:NPN", company_name="Naspers", max_results=5, country="ZA"
        )
        self.assertIsNotNone(result)
        # We don't assert success — JSE results may be sparse
        # but we must never crash
        self.assertIsNone(result.error,
                          msg=f"Unexpected error for JSE ticker: {result.error}")

    def test_max_results_respected(self):
        result = _client().fetch_market_news("AAPL", max_results=3)
        self.assertLessEqual(len(result.articles), 3)


@_skip_no_key()
class TestFetchSECFilings(unittest.TestCase):

    def test_apple_10k_returns_filings_and_facts(self):
        result = _client().fetch_sec_filings("AAPL", filing_type="10-K", max_results=3)
        self.assertIsInstance(result, SECFilingResult)
        self.assertTrue(result.success, msg=result.error)
        self.assertGreater(len(result.filings), 0)
        self.assertGreater(len(result.facts), 0)

    def test_all_search_results_from_sec_domains(self):
        result = _client().fetch_sec_filings("MSFT", filing_type="10-K")
        self.assertTrue(result.success, msg=result.error)
        for filing in result.filings:
            self.assertIn(
                filing.source_domain, SEC_ALLOWLIST,
                msg=f"Non-SEC domain appeared in SEC allowlist results: {filing.source_domain}",
            )

    def test_cik_populated_for_us_ticker(self):
        result = _client().fetch_sec_filings("AAPL")
        self.assertEqual(result.cik.lstrip("0"), "320193")

    def test_xbrl_revenue_is_reasonable(self):
        result = _client().fetch_sec_filings("AAPL", filing_type="10-K")
        self.assertTrue(result.success, msg=result.error)
        revenue_fact = result.latest_fact("Revenue")
        self.assertIsNotNone(revenue_fact, "Revenue XBRL fact missing for AAPL")
        # AAPL revenue > $100B
        self.assertGreater(revenue_fact.value, 100_000_000_000)
        self.assertEqual(revenue_fact.unit, "USD")

    def test_non_us_ticker_degrades_gracefully(self):
        """JSE tickers are not in EDGAR — must not raise, facts will be empty."""
        result = _client().fetch_sec_filings("JSE:NPN", filing_type="10-K")
        self.assertIsNotNone(result)
        self.assertEqual(result.cik, "")     # no CIK for JSE listing
        self.assertEqual(result.facts, [])   # no XBRL facts
        # Search results may still be present
        self.assertIsNone(result.error)

    def test_10q_form_returns_quarterly_facts(self):
        result = _client().fetch_sec_filings("MSFT", filing_type="10-Q", max_results=3)
        self.assertTrue(result.success, msg=result.error)
        for fact in result.facts:
            self.assertEqual(fact.form, "10-Q")

    def test_latency_recorded(self):
        result = _client().fetch_sec_filings("AAPL")
        self.assertGreater(result.latency_ms, 0)


@_skip_no_key()
class TestFetchCompanyFinancials(unittest.TestCase):

    def test_unified_response_shape(self):
        data = _client().fetch_company_financials("AAPL", company_name="Apple")
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn("news",            data)
        self.assertIn("filings",         data)
        self.assertIn("xbrl_facts",      data)
        self.assertIn("summary_metrics", data)
        self.assertIn("fetched_at",      data)
        self.assertIsNone(data["error"])

    def test_summary_metrics_contains_revenue(self):
        data = _client().fetch_company_financials("AAPL")
        self.assertIn("Revenue", data["summary_metrics"])
        revenue = data["summary_metrics"]["Revenue"]
        self.assertIn("value",      revenue)
        self.assertIn("unit",       revenue)
        self.assertIn("period_end", revenue)

    def test_xbrl_facts_serialised_correctly(self):
        data = _client().fetch_company_financials("MSFT")
        self.assertIsInstance(data["xbrl_facts"], list)
        for fact in data["xbrl_facts"]:
            self.assertIn("label",       fact)
            self.assertIn("value",       fact)
            self.assertIn("unit",        fact)
            self.assertIn("period_end",  fact)
            self.assertIn("fiscal_year", fact)
            self.assertIn("form",        fact)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests for pure helpers (no network, no key)
# ─────────────────────────────────────────────────────────────────────────────

class TestHelpers(unittest.TestCase):

    def test_safe_extract_domain_https(self):
        self.assertEqual(_safe_extract_domain("https://sec.gov/filing"), "sec.gov")

    def test_safe_extract_domain_subdomain(self):
        self.assertEqual(
            _safe_extract_domain("https://investor.apple.com/reports"),
            "investor.apple.com",
        )

    def test_safe_extract_domain_malformed(self):
        # Must not raise — CodeRabbit fix
        result = _safe_extract_domain("not a url !!!@#")
        self.assertIsInstance(result, str)  # either "" or "unknown", never raises

    def test_safe_extract_domain_empty(self):
        result = _safe_extract_domain("")
        self.assertIsInstance(result, str)

    def test_utcnow_iso_format(self):
        ts = _utcnow_iso()
        from datetime import datetime, timezone
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed.tzinfo)   # must be timezone-aware


if __name__ == "__main__":
    unittest.main(verbosity=2)
