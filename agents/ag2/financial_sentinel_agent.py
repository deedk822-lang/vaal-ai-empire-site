"""
Vaal AI Empire - Financial Sentinel Agent (AG2)

Static SARS knowledge base - no external API calls.
Agent can self-update when SARS changes laws.
"""

import os
import sys
from typing import Annotated

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from autogen import ConversableAgent, LLMConfig, register_function

from agents.lib.sars_knowledge_base import SARSKnowledgeBase
from agents.lib.perplexity_financial_client import PerplexityFinancialClient


class FinancialSentinelAgent:
    """
    Financial Sentinel - SARS tax expert with static knowledge base.

    NO EXTERNAL API CALLS (except LLM).
    Uses local SARS JSON files for all knowledge.
    Can self-update when SARS publishes new regulations.
    """

    def __init__(self, llm_config: LLMConfig, perplexity_api_key: str = None):
        self.llm_config = llm_config
        self.sars_kb = SARSKnowledgeBase()
        
        # Optional: Perplexity for market data
        self.perplexity = None
        if perplexity_api_key:
            try:
                self.perplexity = PerplexityFinancialClient(api_key=perplexity_api_key)
            except Exception as e:
                print(f"[Financial Sentinel] Perplexity not available: {e}")
        
        self.initialized = False

        # Build system message based on available tools
        base_message = (
            "You are the Financial Sentinel, a South African tax and financial expert. "
            "You have complete knowledge of SARS regulations loaded from official sources. "
            "Always cite official sources with URLs. Calculate exact ZAR amounts. "
        )
        
        if self.perplexity:
            base_message += (
                "You also have access to real-time market data and financial metrics "
                "via Perplexity for global companies. "
            )
        
        base_message += (
            "Format for tax calculations: 'Total Recovery: R[amount] | Tax Saving (28%): R[amount] | Source: [URL]'"
        )
        
        self.agent = ConversableAgent(
            name="financial_sentinel",
            system_message=base_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="SARS tax calculator and financial analyst with market data access.",
        )

    def initialize(self):
        """Load SARS knowledge from local JSON files."""
        if not self.initialized:
            print("[Financial Sentinel] Loading SARS knowledge base...")
            self.sars_kb.initialize()
            self._register_tools()
            self.initialized = True
            print(
                f"[Financial Sentinel] ✅ Loaded {len(self.sars_kb.knowledge_base)} SARS regulations - Ready! 💰"
            )

    def _register_tools(self):
        """Register SARS tools (no external API calls)."""

        def query_sars_knowledge(
            query: Annotated[str, "Question about SARS tax regulations"],
        ) -> str:
            """Search local SARS knowledge base (no API calls)."""
            results = self.sars_kb.query(query, top_n=3)

            if not results:
                return (
                    "No relevant SARS regulations found. Try rephrasing your question."
                )

            response_parts = [f"📋 SARS Knowledge: {query}\n"]
            for r in results:
                response_parts.append(
                    f"\n[Regulation: {r['regulation']}] {r['topic']}\n"
                    f"{r['content']}\n"
                    f"Source: {r['source']}"
                )

            return "\n".join(response_parts)

        def calculate_section_12h(
            learnerships_json: Annotated[
                str, "JSON: [{nqf_level: 5, disabled: false, completed: true}, ...]"
            ],
        ) -> str:
            """Calculate Section 12H using REAL SARS rates from local files."""
            import json

            try:
                learnerships = json.loads(learnerships_json)
                result = self.sars_kb.calculate_section_12h(learnerships)

                return (
                    f"💰 Section 12H Tax Recovery\n"
                    f"═══════════════════════════════════════════\n"
                    f"Total Recovery: R{result['total_recovery']:,}\n"
                    f"Tax Saving (28%): R{result['tax_saving_28_percent']:,}\n"
                    f"Learnerships: {result['learnerships_count']}\n\n"
                    f"Breakdown:\n"
                    + "\n".join(
                        [
                            f"  Learner {b['learner_id']}: Annual R{b['annual_allowance']:,} + Completion R{b['completion_allowance']:,} = R{b['total']:,}"
                            for b in result["breakdown"]
                        ]
                    )
                    + "\n\n"
                    f"Source: {result['source']}\n"
                    f"Last Verified: {result['last_verified']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}"

        def calculate_eti(
            employees_json: Annotated[
                str, "JSON: [{age: 24, monthly_salary: 4000, months_employed: 6}, ...]"
            ],
        ) -> str:
            """Calculate ETI using REAL SARS rates from local files."""
            import json

            try:
                employees = json.loads(employees_json)
                result = self.sars_kb.calculate_eti(employees)

                return (
                    f"💼 Employment Tax Incentive (ETI)\n"
                    f"═══════════════════════════════════════════\n"
                    f"Monthly ETI: R{result['monthly_eti']:,}\n"
                    f"Annual ETI: R{result['annual_eti']:,}\n"
                    f"Qualifying Employees: {result['qualifying_employees']}\n\n"
                    f"Breakdown:\n"
                    + "\n".join(
                        [
                            f"  Employee {b['employee_id']}: Age {b['age']}, Salary R{b['salary']:,}, ETI R{b['monthly_eti']:.2f}/month"
                            for b in result["breakdown"]
                        ]
                    )
                    + "\n\n"
                    f"Source: {result['source']}\n"
                    f"Last Verified: {result['last_verified']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}"

        def list_all_sars_regulations() -> str:
            """List all SARS regulations currently in knowledge base."""
            regulations = self.sars_kb.get_all_regulations()
            return f"Available SARS Regulations:\n" + "\n".join(
                [f"  • {reg}" for reg in regulations]
            )

        # Register with AG2
        register_function(
            query_sars_knowledge,
            caller=self.agent,
            executor=self.agent,
            name="query_sars_knowledge",
            description="Search local SARS knowledge base (no API calls)",
        )

        register_function(
            calculate_section_12h,
            caller=self.agent,
            executor=self.agent,
            name="calculate_section_12h",
            description="Calculate Section 12H using REAL SARS rates from local files",
        )

        register_function(
            calculate_eti,
            caller=self.agent,
            executor=self.agent,
            name="calculate_eti",
            description="Calculate ETI using REAL SARS rates from local files",
        )

        register_function(
            list_all_sars_regulations,
            caller=self.agent,
            executor=self.agent,
            name="list_all_sars_regulations",
            description="List all SARS regulations in knowledge base",
        )

        # Register Perplexity tools if available
        if self.perplexity:
            def fetch_market_news(
                company: Annotated[str, "Company name or ticker (e.g., 'AAPL' or 'Apple Inc')"],
                max_results: Annotated[int, "Number of news articles (1-5)"] = 3
            ) -> str:
                """Fetch recent market news for a company using Perplexity."""
                try:
                    news = self.perplexity.batch_market_news([company], max_results=max_results)
                    
                    if not news or company not in news:
                        return f"No news found for {company}"
                    
                    articles = news[company]
                    if not articles:
                        return f"No recent news for {company}"
                    
                    response_parts = [f"📰 Market News for {company}:\n"]
                    for i, article in enumerate(articles, 1):
                        response_parts.append(
                            f"\n{i}. {article['headline']}\n"
                            f"   Source: {article['source']}\n"
                            f"   Summary: {article['summary'][:100]}...\n"
                            f"   URL: {article['url'][:60]}..."
                        )
                    
                    return "\n".join(response_parts)
                    
                except Exception as e:
                    return f"❌ Error fetching news: {str(e)}"
            
            def fetch_company_financials(
                company_name: Annotated[str, "Company name (e.g., 'Apple Inc')"],
                ticker: Annotated[str, "Stock ticker (e.g., 'AAPL')"] = ""
            ) -> str:
                """Fetch financial metrics for a company using Perplexity."""
                try:
                    metrics = self.perplexity.extract_financial_metrics(company_name, ticker)
                    
                    if "error" in metrics:
                        return f"❌ Error: {metrics['error']}"
                    
                    return (
                        f"📊 Financial Metrics for {company_name}:\n"
                        f"═══════════════════════════════════════════\n"
                        f"P/E Ratio: {metrics.get('pe_ratio', 'N/A')}\n"
                        f"Price-to-Book: {metrics.get('price_to_book', 'N/A')}\n"
                        f"Market Cap: ${metrics.get('market_cap_billions', 'N/A')}B\n"
                        f"Revenue Growth (YoY): {metrics.get('revenue_growth_yoy', 'N/A')}%\n"
                        f"EPS: {metrics.get('earnings_per_share', 'N/A')}\n"
                        f"Dividend Yield: {metrics.get('dividend_yield', 'N/A')}\n"
                        f"52W High/Low: ${metrics.get('52week_high', 'N/A')} / ${metrics.get('52week_low', 'N/A')}\n"
                        f"Data Quality: {metrics.get('data_quality', 'N/A')}\n"
                    )
                    
                except Exception as e:
                    return f"❌ Error fetching metrics: {str(e)}"
            
            register_function(
                fetch_market_news,
                caller=self.agent,
                executor=self.agent,
                name="fetch_market_news",
                description="Fetch recent market news for a company or stock ticker",
            )
            
            register_function(
                fetch_company_financials,
                caller=self.agent,
                executor=self.agent,
                name="fetch_company_financials",
                description="Fetch financial metrics (P/E, market cap, etc.) for a company",
            )
            
            print("[Financial Sentinel] 6 tools registered (4 local + 2 Perplexity market data)")
        else:
            print("[Financial Sentinel] 4 tools registered (all local - no API calls)")
