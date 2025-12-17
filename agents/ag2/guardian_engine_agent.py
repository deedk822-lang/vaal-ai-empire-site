"""
Vaal AI Empire - Guardian Engine Agent (AG2)

AG2 agent that uses REAL Cohere API and REAL crisis data.
NO PLACEHOLDERS - Everything connects to actual APIs and files.
"""

import os
import sys
from typing import Annotated

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, LLMConfig, register_function
from agents.lib.crisis_detector import CrisisDetector


class GuardianEngineAgent:
    """
    Guardian Engine - AG2 agent with REAL crisis detection.
    Uses REAL Cohere API for semantic search.
    Uses REAL Eskom data for risk assessment.
    """
    
    def __init__(self, llm_config: LLMConfig, cohere_api_key: str = None):
        self.llm_config = llm_config
        self.cohere_api_key = cohere_api_key or os.getenv('COHERE_API_KEY')
        
        if not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY required! Set in .env file.")
        
        self.crisis_detector = CrisisDetector(self.cohere_api_key)
        self.initialized = False
        
        self.agent = ConversableAgent(
            name="guardian_engine",
            system_message=(
                "You are the Guardian Engine, monitoring REAL South African crises. "
                "You use REAL Cohere API and REAL Eskom data. "
                "Issue alerts: 🟢 GREEN (Low), 🟡 YELLOW (Medium), 🟠 ORANGE (High), 🔴 RED (Critical). "
                "Format: 'Risk Level: [COLOR] | Alert: [MESSAGE] | Actions: [RECOMMENDATIONS]'"
            ),
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="REAL crisis detection using verified Eskom data."
        )
    
    async def initialize(self):
        """Initialize with REAL crisis data and Cohere API."""
        if not self.initialized:
            print("[Guardian Engine] Loading REAL crisis data and connecting to Cohere API...")
            await self.crisis_detector.initialize()
            self._register_tools()
            self.initialized = True
            print("[Guardian Engine] ✅ Connected to REAL APIs - Ready! 🛡️")
    
    def _register_tools(self):
        """Register REAL tools that call actual Cohere API."""
        
        def assess_loadshedding_risk(
            eaf: Annotated[float, "Energy Availability Factor (0-100)"],
            unplanned_outages_mw: Annotated[int, "Unplanned outages in MW"] = None,
            coal_stockpile_days: Annotated[int, "Coal stockpile days"] = None
        ) -> str:
            """Assess REAL load-shedding risk using actual Eskom thresholds."""
            
            metrics = {'eaf': eaf}
            if unplanned_outages_mw:
                metrics['unplanned_outages_mw'] = unplanned_outages_mw
            if coal_stockpile_days:
                metrics['coal_stockpile_days'] = coal_stockpile_days
            
            result = self.crisis_detector.assessLoadsheddingRisk(metrics)
            
            alert_emoji = {
                'GREEN': '🟢',
                'YELLOW': '🟡',
                'ORANGE': '🟠',
                'RED': '🔴'
            }.get(result['alert_level'], '⚪')
            
            response_parts = [
                f"{alert_emoji} Load-shedding Risk (REAL ESKOM DATA)",
                f"═══════════════════════════════════════════",
                f"Overall Risk: {result['overall_risk']}",
                f"Alert Level: {result['alert_level']}",
                f"Timestamp: {result['timestamp']}\n"
            ]
            
            if result['risks']:
                response_parts.append("⚠️ Risk Indicators:")
                for risk in result['risks']:
                    response_parts.append(
                        f"  • {risk['indicator']}: {risk['current_value']} (threshold: {risk['threshold']})\n"
                        f"    → {risk['likely_outcome']}"
                    )
            
            response_parts.append("\n🎯 Recommended Actions:")
            for i, rec in enumerate(result['recommendations'], 1):
                response_parts.append(f"  {i}. {rec}")
            
            response_parts.append(f"\n📊 Source: {result['source']}")
            
            return "\n".join(response_parts)
        
        async def query_crisis_intelligence(
            query: Annotated[str, "Question about SA crises"]
        ) -> str:
            """Search REAL crisis data using REAL Cohere rerank API."""
            result = await self.crisis_detector.query(query, topN=3)
            
            if result['totalResults'] == 0:
                return "No relevant crisis intelligence found."
            
            response_parts = [f"🔍 Crisis Query: {query}\n"]
            for r in result['results']:
                response_parts.append(
                    f"\n[Relevance: {r['relevanceScore']:.2f}] {r['text']}"
                )
            
            return "\n".join(response_parts)
        
        def get_business_impact(
            sector: Annotated[str, "Sector: manufacturing/retail/it_services/sme_services"],
            stage: Annotated[int, "Load-shedding stage (1-6)"]
        ) -> str:
            """Get REAL business impact from actual crisis data file."""
            try:
                result = self.crisis_detector.getBusinessImpact(sector, stage)
                
                return (
                    f"🏭 Business Impact (REAL DATA)\n"
                    f"═══════════════════════════════════════════\n"
                    f"Sector: {result['sector'].replace('_', ' ').title()}\n"
                    f"Stage: {result['stage']}\n"
                    f"Severity: {result['severity']}\n\n"
                    f"📉 Impact:\n{result['impact']}\n\n"
                    f"🛡️ Mitigation:\n{result['mitigation']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}"
        
        # Register with AG2
        register_function(
            assess_loadshedding_risk,
            caller=self.agent,
            executor=self.agent,
            name="assess_loadshedding_risk",
            description="REAL load-shedding risk assessment using actual Eskom thresholds"
        )
        
        register_function(
            query_crisis_intelligence,
            caller=self.agent,
            executor=self.agent,
            name="query_crisis_intelligence",
            description="REAL Cohere API search over REAL crisis data"
        )
        
        register_function(
            get_business_impact,
            caller=self.agent,
            executor=self.agent,
            name="get_business_impact",
            description="REAL business impact from actual crisis data file"
        )
        
        print("[Guardian Engine] 3 REAL tools registered (all connected to Cohere API)")
