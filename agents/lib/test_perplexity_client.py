#!/usr/bin/env python3
"""
Test suite for PerplexityFinancialClient
"""

import os
import sys
import unittest
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from perplexity_financial_client import PerplexityFinancialClient
    HAS_PERPLEXITY = True
except ImportError as e:
    print(f"Import error: {e}")
    HAS_PERPLEXITY = False


@unittest.skipUnless(HAS_PERPLEXITY, "Perplexity SDK not installed")
@unittest.skipUnless(os.getenv("PERPLEXITY_API_KEY"), "No API key")
class TestPerplexityFinancialClient(unittest.TestCase):
    """Test Perplexity financial client."""
    
    @classmethod
    def setUpClass(cls):
        cls.api_key = os.getenv("PERPLEXITY_API_KEY")
        cls.client = PerplexityFinancialClient(api_key=cls.api_key)
    
    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client)
        self.assertIsNotNone(self.client.perf_metrics)
    
    def test_batch_market_news(self):
        """Test batch news fetching."""
        queries = ["AAPL stock", "MSFT earnings"]
        results = self.client.batch_market_news(queries, max_results=2)
        
        self.assertIsInstance(results, dict)
        for query in queries:
            self.assertIn(query, results)
            self.assertIsInstance(results[query], list)
    
    def test_extract_financial_metrics(self):
        """Test financial metrics extraction."""
        metrics = self.client.extract_financial_metrics("Apple Inc", "AAPL")
        
        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics.get("company"), "Apple Inc")
        self.assertIn("timestamp", metrics)
    
    def test_health_metrics(self):
        """Test performance monitoring."""
        # Make some requests first
        self.client.batch_market_news(["test"], max_results=1)
        
        health = self.client.get_health_metrics()
        
        self.assertIn("total_requests", health)
        self.assertIn("avg_latency_ms", health)
        self.assertIn("error_count", health)
        self.assertGreater(health["total_requests"], 0)


class TestPerplexityWithoutKey(unittest.TestCase):
    """Test behavior without API key."""
    
    def test_missing_key(self):
        """Test that missing API key raises error."""
        if not HAS_PERPLEXITY:
            self.skipTest("Perplexity not installed")
        
        with self.assertRaises(Exception):
            PerplexityFinancialClient(api_key="")


def run_demo():
    """Run a demo of the client."""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("❌ Set PERPLEXITY_API_KEY environment variable")
        return
    
    if not HAS_PERPLEXITY:
        print("❌ Install Perplexity SDK: pip install perplexity")
        return
    
    print("=" * 60)
    print("Perplexity Financial Client Demo")
    print("=" * 60)
    
    client = PerplexityFinancialClient(api_key=api_key)
    
    # 1. Batch news
    print("\n1. Fetching market news for AAPL, MSFT...")
    news = client.batch_market_news(["AAPL stock analysis", "MSFT AI"], max_results=2)
    
    for query, articles in news.items():
        print(f"\n  {query}:")
        for a in articles[:1]:
            print(f"    - {a['headline'][:50]}... ({a['source']})")
    
    # 2. Financial metrics
    print("\n2. Fetching Apple financial metrics...")
    metrics = client.extract_financial_metrics("Apple Inc", "AAPL")
    print(f"   P/E: {metrics.get('pe_ratio')}")
    print(f"   Market Cap: ${metrics.get('market_cap_billions')}B")
    
    # 3. Health check
    print("\n3. Performance metrics...")
    health = client.get_health_metrics()
    print(f"   Requests: {health['total_requests']}")
    print(f"   Avg Latency: {health['avg_latency_ms']:.1f}ms")
    print(f"   Errors: {health['error_count']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    
    args = parser.parse_args()
    
    if args.test:
        unittest.main(argv=[''], verbosity=2, exit=False)
    elif args.demo:
        run_demo()
    else:
        print("Usage: python test_perplexity_client.py --demo")
        print("       python test_perplexity_client.py --test")
