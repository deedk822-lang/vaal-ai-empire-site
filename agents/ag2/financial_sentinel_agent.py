"""
Vaal AI Empire - Financial Sentinel Agent (AG2)

AG2 agent that wraps the SARS Knowledge Base to provide tax recovery insights.
Uses Cohere semantic search + real SARS calculations.
"""

import os
import sys
from typing import Annotated

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, LLMConfig, register_function
from agents.lib.sars_knowledge_base import SARSKnowledgeBase


class FinancialSentinelAgent:
    """
    Financial Sentinel - AG2 agent for SARS tax recovery.
    
    Capabilities:
    - Answer questions about SARS regulations
    - Calculate Section 12H learnership allowances
    - Calculate ETI (Employment Tax Incentive)
    - Provide tax-saving recommendations
    """
    
    def __init__(self, llm_config: LLMConfig, cohere_api_key: str = None):
        self.llm_config = llm_config
        self.sars_kb = SARSKnowledgeBase(cohere_api_key or os.getenv('COHERE_API_KEY'))
        self.initialized = False
        
        # Create AG2 agent
        self.agent = ConversableAgent(
            name="financial_sentinel",
            system_message=(
                "You are the Financial Sentinel, a South African tax recovery expert. "
                "You have access to verified SARS regulations (Section 12H, ETI). "
                "Always cite official sources. Calculate exact tax recovery amounts. "
                "Be precise with ZAR amounts and provide actionable recommendations. "
                "Format: 'Total Recovery: R[amount] | Tax Saving (28%): R[amount] | Source: [URL]'"
            ),
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="Calculates SARS tax recovery for South African SMEs. Specializes in Section 12H and ETI."
        )
    
    async def initialize(self):
        """Initialize SARS knowledge base and register tools."""
        if not self.initialized:
            print("[Financial Sentinel] Initializing SARS knowledge base...")
            await self.sars_kb.initialize()
            self._register_tools()
            self.initialized = True
            print("[Financial Sentinel] Ready to recover tax money! 💰")
    
    def _register_tools(self):
        """Register SARS tools with AG2 agent."""
        
        # Tool 1: Query SARS regulations
        async def query_sars_regulations(
            query: Annotated[str, "Natural language question about SARS tax regulations"]
        ) -> str:
            """Search SARS regulations using semantic search."""
            result = await self.sars_kb.query(query, topN=3)
            
            if result['totalResults'] == 0:
                return "No relevant SARS regulations found. Please rephrase your question."
            
            # Format response
            response_parts = [f"📋 SARS Regulations Query: {query}\n"]
            for r in result['results']:
                response_parts.append(
                    f"\n[Relevance: {r['relevanceScore']:.2f}] {r['text']}"
                )
            
            return "\n".join(response_parts)
        
        # Tool 2: Calculate Section 12H
        async def calculate_section_12h(
            learnerships_json: Annotated[str, "JSON array of learnership data: [{nqf_level: 5, disabled: false, completed: true}, ...]"]
        ) -> str:
            """Calculate Section 12H tax recovery for learnerships."""
            import json
            
            try:
                learnerships = json.loads(learnerships_json)
                result = await self.sars_kb.calculateSection12H({'learnerships': learnerships})
                
                return (
                    f"💰 Section 12H Tax Recovery\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Total Recovery: R{result['total_recovery']:,}\n"
                    f"Tax Saving (28%): R{result['tax_saving_28_percent']:,}\n"
                    f"Learnerships: {result['learnerships_count']}\n"
                    f"Source: {result['source']}\n"
                    f"Last Verified: {result['last_verified']}\n"
                    f"Confidence: {result['confidence']}"
                )
            except json.JSONDecodeError:
                return "❌ Invalid JSON format. Example: [{\"nqf_level\": 5, \"disabled\": false, \"completed\": true}]"
            except Exception as e:
                return f"❌ Error calculating Section 12H: {str(e)}"
        
        # Tool 3: Calculate ETI
        async def calculate_eti(
            employees_json: Annotated[str, "JSON array of employee data: [{age: 24, monthly_salary: 4000, months_employed: 6}, ...]"]
        ) -> str:
            """Calculate ETI (Employment Tax Incentive) for qualifying employees."""
            import json
            
            try:
                employees = json.loads(employees_json)
                result = await self.sars_kb.calculateETI({'employees': employees})
                
                return (
                    f"💼 Employment Tax Incentive (ETI)\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Monthly ETI: R{result['monthly_eti']:,}\n"
                    f"Annual ETI: R{result['annual_eti']:,}\n"
                    f"Qualifying Employees: {result['qualifying_employees']}\n"
                    f"Source: {result['source']}\n"
                    f"Last Verified: {result['last_verified']}\n"
                    f"Confidence: {result['confidence']}"
                )
            except json.JSONDecodeError:
                return "❌ Invalid JSON format. Example: [{\"age\": 24, \"monthly_salary\": 4000, \"months_employed\": 6}]"
            except Exception as e:
                return f"❌ Error calculating ETI: {str(e)}"
        
        # Register tools with AG2
        register_function(
            query_sars_regulations,
            caller=self.agent,
            executor=self.agent,
            name="query_sars_regulations",
            description="Search SARS tax regulations using semantic search. Returns verified regulations with sources."
        )
        
        register_function(
            calculate_section_12h,
            caller=self.agent,
            executor=self.agent,
            name="calculate_section_12h",
            description="Calculate Section 12H learnership tax allowances. Requires JSON array of learnership data."
        )
        
        register_function(
            calculate_eti,
            caller=self.agent,
            executor=self.agent,
            name="calculate_eti",
            description="Calculate Employment Tax Incentive (ETI) for qualifying employees aged 18-29."
        )
        
        print("[Financial Sentinel] 3 tools registered: query_sars_regulations, calculate_section_12h, calculate_eti")
