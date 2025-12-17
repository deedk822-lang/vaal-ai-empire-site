"""
Vaal AI Empire - Guardian Engine Agent (AG2)

AG2 agent that wraps the Crisis Detector to monitor South African business risks.
Focuses on load-shedding, economic disruptions, and proactive alerts.
"""

import os
import sys
from typing import Annotated

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, LLMConfig, register_function
from agents.lib.crisis_detector import CrisisDetector


class GuardianEngineAgent:
    """
    Guardian Engine - AG2 agent for crisis detection and prevention.
    
    Capabilities:
    - Assess load-shedding risk (EAF, unplanned outages)
    - Query crisis intelligence
    - Get business impact by sector
    - Provide proactive recommendations
    """
    
    def __init__(self, llm_config: LLMConfig, cohere_api_key: str = None):
        self.llm_config = llm_config
        self.crisis_detector = CrisisDetector(cohere_api_key or os.getenv('COHERE_API_KEY'))
        self.initialized = False
        
        # Create AG2 agent
        self.agent = ConversableAgent(
            name="guardian_engine",
            system_message=(
                "You are the Guardian Engine, a crisis prevention expert for South African businesses. "
                "You monitor load-shedding, economic disruptions, and business risks. "
                "Issue alerts in 3 levels: 🟢 GREEN (Low risk), 🟡 YELLOW (Medium), 🟠 ORANGE (High), 🔴 RED (Critical). "
                "Always provide actionable recommendations. "
                "Format: 'Risk Level: [COLOR] | Alert: [MESSAGE] | Action: [RECOMMENDATIONS]'"
            ),
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="Monitors South African crises: load-shedding, strikes, port delays. Issues real-time alerts."
        )
    
    async def initialize(self):
        """Initialize crisis detector and register tools."""
        if not self.initialized:
            print("[Guardian Engine] Initializing crisis detection system...")
            await self.crisis_detector.initialize()
            self._register_tools()
            self.initialized = True
            print("[Guardian Engine] Ready to protect businesses! 🛡️")
    
    def _register_tools(self):
        """Register crisis detection tools with AG2 agent."""
        
        # Tool 1: Assess load-shedding risk
        def assess_loadshedding_risk(
            eaf: Annotated[float, "Energy Availability Factor (0-100%, e.g., 58.2)"],
            unplanned_outages_mw: Annotated[int, "Unplanned outages in MW (e.g., 12000)"] = None,
            coal_stockpile_days: Annotated[int, "Coal stockpile in days (e.g., 18)"] = None
        ) -> str:
            """Assess load-shedding risk based on current Eskom metrics."""
            
            metrics = {'eaf': eaf}
            if unplanned_outages_mw:
                metrics['unplanned_outages_mw'] = unplanned_outages_mw
            if coal_stockpile_days:
                metrics['coal_stockpile_days'] = coal_stockpile_days
            
            result = self.crisis_detector.assessLoadsheddingRisk(metrics)
            
            # Format alert with emoji
            alert_emoji = {
                'GREEN': '🟢',
                'YELLOW': '🟡',
                'ORANGE': '🟠',
                'RED': '🔴'
            }.get(result['alert_level'], '⚪')
            
            response_parts = [
                f"{alert_emoji} Load-shedding Risk Assessment",
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
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
        
        # Tool 2: Query crisis intelligence
        async def query_crisis_intelligence(
            query: Annotated[str, "Natural language question about South African crises (load-shedding, strikes, economic challenges)"]
        ) -> str:
            """Search crisis intelligence database using semantic search."""
            result = await self.crisis_detector.query(query, topN=3)
            
            if result['totalResults'] == 0:
                return "No relevant crisis intelligence found. Please rephrase your question."
            
            response_parts = [f"🔍 Crisis Intelligence Query: {query}\n"]
            for r in result['results']:
                response_parts.append(
                    f"\n[Relevance: {r['relevanceScore']:.2f}] {r['text']}"
                )
            
            return "\n".join(response_parts)
        
        # Tool 3: Get business impact by sector
        def get_business_impact(
            sector: Annotated[str, "Business sector: 'manufacturing', 'retail', 'it_services', or 'sme_services'"],
            stage: Annotated[int, "Load-shedding stage (1-6)"]
        ) -> str:
            """Get business impact assessment for specific sector and load-shedding stage."""
            
            try:
                result = self.crisis_detector.getBusinessImpact(sector, stage)
                
                return (
                    f"🏭 Business Impact Assessment\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Sector: {result['sector'].replace('_', ' ').title()}\n"
                    f"Load-shedding Stage: {result['stage']}\n"
                    f"Severity: {result['severity']}\n\n"
                    f"📉 Impact:\n{result['impact']}\n\n"
                    f"🛡️ Mitigation:\n{result['mitigation']}"
                )
            except Exception as e:
                return f"❌ Error: {str(e)}. Valid sectors: manufacturing, retail, it_services, sme_services. Stages: 1-6."
        
        # Register tools with AG2
        register_function(
            assess_loadshedding_risk,
            caller=self.agent,
            executor=self.agent,
            name="assess_loadshedding_risk",
            description="Assess load-shedding risk based on Eskom metrics (EAF, outages, coal). Returns color-coded alert."
        )
        
        register_function(
            query_crisis_intelligence,
            caller=self.agent,
            executor=self.agent,
            name="query_crisis_intelligence",
            description="Search crisis intelligence about South African business risks (load-shedding, strikes, etc.)."
        )
        
        register_function(
            get_business_impact,
            caller=self.agent,
            executor=self.agent,
            name="get_business_impact",
            description="Get business impact assessment for a specific sector during load-shedding."
        )
        
        print("[Guardian Engine] 3 tools registered: assess_loadshedding_risk, query_crisis_intelligence, get_business_impact")
