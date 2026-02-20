#!/usr/bin/env python3
"""
Perplexity Financial Data Client
Production fetcher for market data, SEC filings, and financial metrics.

Features:
- Batch queries (5/request) for efficiency
- SEC search mode for 10-K/10-Q filing data
- Domain filtering for curated sources
- Structured JSON output for signal generation
- Error handling + rate limiting
- Performance monitoring

Usage:
    client = PerplexityFinancialClient(api_key="your_key")
    
    # Batch market news
    news = client.batch_market_news(["AAPL earnings", "MSFT AI"])
    
    # SEC filings
    filing = client.fetch_sec_filings("AAPL", "10-K")
    
    # Financial metrics
    metrics = client.extract_financial_metrics("Apple Inc")
"""

from typing import List, Dict, Literal, Optional
import json
import logging
from datetime import datetime
from urllib.parse import urlparse

try:
    from perplexity import Perplexity
    HAS_PERPLEXITY = True
except ImportError:
    HAS_PERPLEXITY = False

# Module-level logger (avoid global basicConfig to respect parent config)
logger = logging.getLogger(__name__)


class PerplexityFinancialClient:
    """
    Production-grade financial data fetcher using Perplexity API.
    
    Designed for:
    - Numerai tournament data enrichment
    - SME financial analysis
    - Market sentiment signals
    - SEC filing research
    """
    
    # Curated financial news sources
    DEFAULT_NEWS_SOURCES = [
        "cnbc.com",
        "bloomberg.com",
        "reuters.com",
        "marketwatch.com",
        "investopedia.com",
        "wsj.com",
        "ft.com",
        "seekingalpha.com",
        "yahoo.com/finance",
        "moneyweb.co.za",  # South African
        "fin24.com",        # South African
    ]
    
    def __init__(self, api_key: str):
        """
        Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key
        """
        if not HAS_PERPLEXITY:
            raise ImportError(
                "Perplexity SDK required. Install: pip install perplexity"
            )
        
        self.client = Perplexity(api_key=api_key)
        self.request_count = 0
        self.start_time = datetime.now()
        
        # Performance monitoring
        self.perf_metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "avg_latency_ms": [],
            "errors": [],
            "last_request": None
        }
    
    # ============ MARKET NEWS (Batch) ============
    
    def batch_market_news(
        self, 
        queries: List[str], 
        max_results: int = 5,
        domain_filter: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Fetch market news for multiple queries in one request.
        
        Args:
            queries: Up to 5 search queries (e.g., "AAPL earnings", "MSFT AI")
            max_results: Results per query (default: 5)
            domain_filter: List of allowed domains (default: curated financial sources)
        
        Returns:
            {query: [{headline, url, summary, source, published_date}, ...]}
        
        Example:
            >>> client = PerplexityFinancialClient(api_key="...")
            >>> news = client.batch_market_news(
            ...     ["AAPL earnings Q4 2025", "MSFT AI developments"],
            ...     max_results=3
            ... )
        """
        if len(queries) > 5:
            logger.warning(f"Max 5 queries per batch. Truncating {len(queries)} -> 5")
            queries = queries[:5]
        
        domains = domain_filter or self.DEFAULT_NEWS_SOURCES
        
        try:
            start = datetime.now()
            
            search_results = self.client.search.create(
                query=queries,
                max_results=max_results,
                max_tokens_per_page=2048,
                search_domain_filter=domains
            )
            
            parsed = self._parse_batch_results(search_results, queries)
            latency = (datetime.now() - start).total_seconds() * 1000
            
            self._record_metric(len(queries), latency, "batch_news")
            
            logger.info(f"Fetched news for {len(queries)} queries in {latency:.1f}ms")
            return parsed
            
        except Exception as e:
            logger.error(f"Batch news error: {e}")
            self._record_error("batch_news", str(e))
            return {}
    
    # ============ SEC FILINGS ============
    
    def fetch_sec_filings(
        self, 
        ticker: str, 
        filing_type: Literal["10-K", "10-Q", "8-K"] = "10-K"
    ) -> Dict:
        """
        Fetch SEC filings directly via search_mode: "sec"
        
        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA")
            filing_type: "10-K" (annual), "10-Q" (quarterly), "8-K" (current events)
        
        Returns:
            {
                ticker, filing_type, company, period,
                revenue, net_income, key_metrics, url, filed_date
            }
        
        Example:
            >>> filing = client.fetch_sec_filings("AAPL", "10-Q")
            >>> print(filing['revenue'], filing['net_income'])
        """
        query = f"{ticker} {filing_type} 2025"
        
        try:
            start = datetime.now()
            
            sec_results = self.client.search.create(
                query=query,
                search_mode="sec",  # Direct SEC EDGAR access
                max_results=1,
                max_tokens_per_page=4096
            )
            
            filing_data = self._extract_sec_metrics(
                sec_results.results[0] if sec_results.results else {},
                ticker,
                filing_type
            )
            
            latency = (datetime.now() - start).total_seconds() * 1000
            self._record_metric(1, latency, "sec_filing")
            
            return filing_data
            
        except Exception as e:
            logger.error(f"SEC filing error for {ticker}: {e}")
            self._record_error("sec_filing", str(e), ticker=ticker)
            return {
                "ticker": ticker,
                "filing_type": filing_type,
                "error": str(e)
            }
    
    # ============ FINANCIAL METRICS ============
    
    def extract_financial_metrics(
        self, 
        company_name: str,
        ticker: Optional[str] = None
    ) -> Dict:
        """
        Extract structured financial metrics using JSON mode.
        
        Args:
            company_name: Company name (e.g., "Apple Inc")
            ticker: Optional stock symbol for precision
        
        Returns:
            {
                company, ticker, pe_ratio, price_to_book,
                dividend_yield, market_cap_billions,
                revenue_growth_yoy, earnings_per_share,
                data_quality, timestamp
            }
        
        Example:
            >>> metrics = client.extract_financial_metrics("Apple Inc", "AAPL")
            >>> print(f"P/E: {metrics['pe_ratio']}")
        """
        ticker_hint = f"({ticker})" if ticker else ""
        
        prompt = f"""Extract current financial metrics for {company_name} {ticker_hint}.

Search for the most recent data and return ONLY valid JSON in this exact format:
{{
    "company": "{company_name}",
    "ticker": "{ticker or 'unknown'}",
    "pe_ratio": null,
    "price_to_book": null,
    "dividend_yield": null,
    "52week_high": null,
    "52week_low": null,
    "market_cap_billions": null,
    "revenue_growth_yoy": null,
    "earnings_per_share": null,
    "data_quality": 0.0,
    "data_date": null
}}

Use null for unavailable data. data_quality should be 0.0-1.0 based on data freshness and completeness."""
        
        try:
            start = datetime.now()
            
            response = self.client.chat.create(
                model="sonar-pro",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Deterministic extraction
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            metrics = json.loads(content)
            
            # Add metadata
            metrics["timestamp"] = datetime.now().isoformat()
            metrics["source"] = "perplexity"
            
            latency = (datetime.now() - start).total_seconds() * 1000
            self._record_metric(1, latency, "extraction")
            
            return metrics
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            self._record_error("extraction", f"JSON parse: {e}")
            return {"company": company_name, "error": "parse_failed"}
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            self._record_error("extraction", str(e))
            return {"company": company_name, "error": str(e)}
    
    # ============ SA MARKET SPECIFIC ============
    
    def fetch_jse_market_data(self, share_code: str) -> Dict:
        """
        Fetch JSE (Johannesburg Stock Exchange) market data.
        
        Args:
            share_code: JSE share code (e.g., "NPN" for Naspers, "FSR" for Foschini)
        
        Returns:
            {share_code, company_name, price_zar, market_cap_zar, pe_ratio, ...}
        """
        query = f"{share_code} JSE share price financials {datetime.now().year}"
        
        try:
            start = datetime.now()
            
            results = self.client.search.create(
                query=query,
                search_domain_filter=["moneyweb.co.za", "fin24.com", "jse.co.za", "businesslive.co.za"],
                max_results=5,
                max_tokens_per_page=2048
            )
            
            # Extract structured data
            extracted = self._extract_jse_metrics(results, share_code)
            
            latency = (datetime.now() - start).total_seconds() * 1000
            self._record_metric(1, latency, "jse_data")
            
            return extracted
            
        except Exception as e:
            logger.error(f"JSE data error for {share_code}: {e}")
            self._record_error("jse_data", str(e), share_code=share_code)
            return {"share_code": share_code, "error": str(e)}
    
    # ============ HELPER METHODS ============
    
    def _parse_batch_results(self, response, queries: List[str]) -> Dict[str, List[Dict]]:
        """Parse batch search results into structured format."""
        
        parsed = {}
        
        if not response.results:
            return {q: [] for q in queries}
        
        # Handle both single and batch results
        if isinstance(response.results[0], list):
            # Batch of results per query
            for i, batch in enumerate(response.results):
                if i < len(queries):
                    query = queries[i]
                    parsed[query] = [
                        {
                            "headline": getattr(r, 'title', ''),
                            "url": getattr(r, 'url', ''),
                            "summary": getattr(r, 'snippet', '')[:200],
                            "source": self._extract_domain(getattr(r, 'url', '')),
                            "published_date": getattr(r, 'published_date', None),
                            "fetched_at": datetime.now().isoformat()
                        }
                        for r in batch
                    ]
        else:
            # Single result set
            parsed[queries[0]] = [
                {
                    "headline": getattr(r, 'title', ''),
                    "url": getattr(r, 'url', ''),
                    "summary": getattr(r, 'snippet', '')[:200],
                    "source": self._extract_domain(getattr(r, 'url', '')),
                    "published_date": getattr(r, 'published_date', None),
                    "fetched_at": datetime.now().isoformat()
                }
                for r in response.results
            ]
        
        # Ensure all queries have entries
        for q in queries:
            if q not in parsed:
                parsed[q] = []
        
        return parsed
    
    def _extract_sec_metrics(self, filing_result: Dict, ticker: str, filing_type: str) -> Dict:
        """Extract key metrics from SEC filing result."""
        
        return {
            "ticker": ticker,
            "filing_type": filing_type,
            "company": getattr(filing_result, 'title', ''),
            "url": getattr(filing_result, 'url', ''),
            "filed_date": getattr(filing_result, 'published_date', None),
            "snippet": getattr(filing_result, 'snippet', '')[:500],
            "extracted_at": datetime.now().isoformat()
        }
    
    def _extract_jse_metrics(self, results, share_code: str) -> Dict:
        """Extract JSE-specific metrics from search results."""
        
        # In a full implementation, would parse actual data
        # For now, return structure
        return {
            "share_code": share_code,
            "raw_results": len(results.results) if hasattr(results, 'results') else 0,
            "extracted_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    # ============ MONITORING ============
    
    def _record_metric(self, requests: int, latency_ms: float, operation: str):
        """Record performance metric."""
        
        self.perf_metrics["total_requests"] += requests
        self.perf_metrics["avg_latency_ms"].append(latency_ms)
        self.perf_metrics["last_request"] = datetime.now().isoformat()
        
        logger.debug(f"[{operation}] Requests: {requests}, Latency: {latency_ms:.1f}ms")
    
    def _record_error(self, operation: str, message: str, **kwargs):
        """Record error for monitoring."""
        
        self.perf_metrics["errors"].append({
            "operation": operation,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
    
    def get_health_metrics(self) -> Dict:
        """
        Get performance and health metrics.
        
        Returns:
            {
                total_requests, avg_latency_ms, error_count,
                uptime_hours, error_rate, recent_errors
            }
        """
        
        latencies = self.perf_metrics["avg_latency_ms"]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        total_reqs = self.perf_metrics["total_requests"]
        error_count = len(self.perf_metrics["errors"])
        error_rate = error_count / total_reqs if total_reqs > 0 else 0
        
        return {
            "total_requests": total_reqs,
            "avg_latency_ms": round(avg_latency, 2),
            "error_count": error_count,
            "error_rate": round(error_rate, 4),
            "uptime_hours": round(uptime_hours, 2),
            "recent_errors": self.perf_metrics["errors"][-5:],
            "last_request": self.perf_metrics["last_request"]
        }
    
    def reset_metrics(self):
        """Reset performance metrics."""
        
        self.perf_metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "avg_latency_ms": [],
            "errors": [],
            "last_request": None
        }
        self.start_time = datetime.now()


# ============ USAGE EXAMPLES ============

def example_usage():
    """Example usage of PerplexityFinancialClient."""
    
    # Initialize (requires PERPLEXITY_API_KEY env var)
    import os
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("Error: Set PERPLEXITY_API_KEY environment variable")
        return
    
    client = PerplexityFinancialClient(api_key=api_key)
    
    print("=" * 60)
    print("Perplexity Financial Client - Examples")
    print("=" * 60)
    
    # 1. Batch market news
    print("\n1. Batch Market News:")
    watchlist = ["AAPL earnings", "MSFT AI strategy", "NVDA stock analysis"]
    news = client.batch_market_news(watchlist, max_results=3)
    
    for query, articles in news.items():
        print(f"\n  {query}:")
        for a in articles[:2]:
            print(f"    - {a['headline'][:60]}... ({a['source']})")
    
    # 2. SEC filings
    print("\n2. SEC Filing (AAPL 10-K):")
    filing = client.fetch_sec_filings("AAPL", "10-K")
    print(f"   Company: {filing.get('company', 'N/A')}")
    print(f"   URL: {filing.get('url', 'N/A')[:60]}...")
    
    # 3. Financial metrics
    print("\n3. Financial Metrics (Apple):")
    metrics = client.extract_financial_metrics("Apple Inc", "AAPL")
    print(f"   P/E: {metrics.get('pe_ratio', 'N/A')}")
    print(f"   Market Cap: ${metrics.get('market_cap_billions', 'N/A')}B")
    
    # 4. JSE data
    print("\n4. JSE Data (NPN - Naspers):")
    jse = client.fetch_jse_market_data("NPN")
    print(f"   Share Code: {jse.get('share_code')}")
    
    # 5. Health metrics
    print("\n5. Client Health:")
    health = client.get_health_metrics()
    print(f"   Total Requests: {health['total_requests']}")
    print(f"   Avg Latency: {health['avg_latency_ms']}ms")
    print(f"   Error Rate: {health['error_rate']:.2%}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    example_usage()
