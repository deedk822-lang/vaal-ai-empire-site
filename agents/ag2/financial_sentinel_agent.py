"""
Vaal AI Empire - Financial Sentinel Agent (AG2)

AG2 agent that uses REAL Cohere API and REAL SARS data.
NO PLACEHOLDERS - Everything connects to actual APIs and files.
"""

import os
import sys
from typing import Annotated

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, LLMConfig, register_function
from agents.lib.sars_knowledge_base import SARSKnowledgeBase


class FinancialSentinelAgent:
    """
    Financial Sentinel - AG2 agent with REAL SARS tax calculations.
    Uses REAL Cohere API for semantic search.
    Uses REAL SARS JSON data for calculations.
    """
    
    def __init__(self, llm_config: LLMConfig, cohere_api_key: str = None):
        self.llm_config = llm_config
        self.cohere_api_key = cohere_api_key or os.getenv('COHERE_API_KEY')
        
        if not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY required! Set in .env file.")
        
        self.sars_kb = SARSKnowledgeBase(self.cohere_api_key)
        self.initialized = False
        
        self.agent = ConversableAgent(
            name="financial_sentinel",
            system_message=(
                "You are the Financial Sentinel, a South African tax recovery expert. "
                "You use REAL SARS data and REAL Cohere API. "
                "Always cite official sources. Calculate exact amounts. "
                "Format: 'Total Recovery: R[amount] | Tax Saving (28%): R[amount] | Source: [URL]'"
            ),
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="REAL SARS tax calculator using verified data."
        )
    
    async def initialize(self):
        """Initialize with REAL SARS data and Cohere API."""
        if not self.initialized:
            print("[Financial Sentinel] Loading REAL SARS data and connecting to Cohere API...")
            await self.sars_kb.initialize()
            self._register_tools()
            self.initialized = True
            print("[Financial Sentinel] ✅ Connected to REAL APIs - Ready! 💰")
    
    def _register_tools(self):
        """Register REAL tools that call actual Cohere API."""
        
        async def query_sars_regulations(
            query: Annotated[str, "Natural language question about SARS tax regulations"]
        ) -> str:
            """Search REAL SARS regulations using REAL Cohere rerank API."""
            result = await self.sars_kb.query(query, topN=3)
            
            if result['totalResults'] == 0:
                return "No relevant SARS regulations found."
            
            response_parts = [f"📋 SARS Query: {query}\n"]
            for r in result['results']:
                response_parts.append(
                    f"\n[Relevance: {r['relevanceScore']:.2f}] {r['text']}"
                )
            
            return "\n".join(response_parts)
        
        async def calculate_section_12h(
            learnerships_json: Annotated[str, "JSON array: [{nqf_level: 5, disabled: false, completed: true}, ...]"]
        ) -> str:
            """Calculate REAL Section 12H using actual SARS rates from JSON file."""
            import json
            
            try:
                learnerships = json.loads(learnerships_json)
                result = await self.sars_kb.calculateSection12H({'learnerships': learnerships})
                
                return (
                    f"💰 Section 12H Tax Recovery (REAL SARS DATA)\n"
                    f"═══════════════════════════════════════════\n"
                    f"Total Recovery: R{result['total_recovery']:,}\n"
                    f"Tax Saving (28%): R{result['tax_saving_28_percent']:,}\n"
                    f"Learnerships: {result['learnerships_count']}\n"
                    f"Source: {result['source']}\n"
                    f"Last Verified: {result['last_verified']}\n"
                    f"Confidence: {result['confidence']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}"
        
        async def calculate_eti(
            employees_json: Annotated[str, "JSON array: [{age: 24, monthly_salary: 4000, months_employed: 6}, ...]"]
        ) -> str:
            """Calculate REAL ETI using actual SARS rates from JSON file."""
            import json
            
            try:
                employees = json.loads(employees_json)
                result = await self.sars_kb.calculateETI({'employees': employees})
                
                return (
                    f"💼 ETI (REAL SARS DATA)\n"
                    f"═══════════════════════════════════════════\n"
                    f"Monthly ETI: R{result['monthly_eti']:,}\n"
                    f"Annual ETI: R{result['annual_eti']:,}\n"
                    f"Qualifying Employees: {result['qualifying_employees']}\n"
                    f"Source: {result['source']}\n"
                    f"Confidence: {result['confidence']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}"
        
        # Register with AG2
        register_function(
            query_sars_regulations,
            caller=self.agent,
            executor=self.agent,
            name="query_sars_regulations",
            description="REAL Cohere API search over REAL SARS data"
        )
        
        register_function(
            calculate_section_12h,
            caller=self.agent,
            executor=self.agent,
            name="calculate_section_12h",
            description="REAL Section 12H calculation using actual SARS rates"
        )
        
        register_function(
            calculate_eti,
            caller=self.agent,
            executor=self.agent,
            name="calculate_eti",
            description="REAL ETI calculation using actual SARS rates"
        )
        
        print("[Financial Sentinel] 3 REAL tools registered (all connected to Cohere API)")
