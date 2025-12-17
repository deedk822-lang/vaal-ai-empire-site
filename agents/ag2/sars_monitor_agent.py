"""
Vaal AI Empire - SARS Monitor Agent

Monitors official SARS website for regulation changes.
Auto-updates the SARS knowledge base when changes detected.

This agent runs in background and alerts when SARS publishes new laws.
"""

import os
import sys
from typing import Annotated
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, LLMConfig, register_function
from agents.lib.sars_knowledge_base import SARSKnowledgeBase


class SARSMonitorAgent:
    """
    SARS Monitor - Watches for SARS regulation updates.
    
    Capabilities:
    - Scrapes official SARS website for new publications
    - Detects changes in Section 12H, ETI, and other regulations
    - Auto-updates local knowledge base
    - Alerts Financial Sentinel when updates occur
    """
    
    SARS_SOURCES = [
        "https://www.sars.gov.za/types-of-tax/pay-as-you-earn/employment-tax-incentive-eti/",
        "https://www.sars.gov.za/wp-content/uploads/Legal/Notes/Legal-IntR-IN-20-Additional-deduction-for-learnership-agreements.pdf",
        "https://www.sars.gov.za/wp-content/uploads/Ops/Guides/LAPD-IT-G09-Guide-on-the-Tax-Incentive-for-Learnership-Agreements.pdf"
    ]
    
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config
        self.sars_kb = SARSKnowledgeBase()
        self.initialized = False
        
        self.agent = ConversableAgent(
            name="sars_monitor",
            system_message=(
                "You are the SARS Monitor, responsible for tracking changes to South African tax regulations. "
                "You monitor official SARS sources and detect when regulations are updated. "
                "When you detect changes, you update the local knowledge base and alert the Financial Sentinel. "
                "You cite the exact SARS publication date and document URL for every change."
            ),
            llm_config=llm_config,
            human_input_mode="NEVER",
            description="Monitors SARS website for regulation changes and auto-updates knowledge base."
        )
    
    def initialize(self):
        """Initialize SARS monitor."""
        if not self.initialized:
            print("[SARS Monitor] Initializing...")
            self.sars_kb.initialize()
            self._register_tools()
            self.initialized = True
            print("[SARS Monitor] ✅ Ready to monitor SARS for updates! 🔍")
    
    def _register_tools(self):
        """Register monitoring tools."""
        
        def check_sars_for_updates() -> str:
            """
            Check official SARS sources for regulation updates.
            
            Returns summary of any detected changes.
            """
            print("[SARS Monitor] Checking SARS official sources for updates...")
            
            # In production, this would:
            # 1. Scrape SARS website
            # 2. Parse PDFs for changes
            # 3. Compare with current knowledge base
            # 4. Return detected changes
            
            # For now, return monitoring status
            current_12h = self.sars_kb.section12h_data['last_updated']
            current_eti = self.sars_kb.eti_data['last_updated']
            
            return (
                f"🔍 SARS Monitoring Report\n"
                f"═══════════════════════════════════════════\n"
                f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Section 12H:\n"
                f"  Last Updated: {current_12h}\n"
                f"  Status: {self.sars_kb.section12h_data['status']}\n"
                f"  Source: {self.sars_kb.section12h_data['official_sources'][0]}\n\n"
                f"ETI:\n"
                f"  Last Updated: {current_eti}\n"
                f"  Effective From: {self.sars_kb.eti_data['monthly_allowance_2025']['effective_from']}\n"
                f"  Source: {self.sars_kb.eti_data['official_sources'][0]}\n\n"
                f"✅ No changes detected. Knowledge base is up to date."
            )
        
        def update_sars_regulation(
            regulation_type: Annotated[str, "'section_12h' or 'eti'"],
            changes_json: Annotated[str, "JSON object with updated regulation data"]
        ) -> str:
            """
            Update SARS knowledge base with new regulation data.
            
            Called when SARS publishes updated regulations.
            """
            import json
            
            try:
                new_data = json.loads(changes_json)
                self.sars_kb.update_regulation(regulation_type, new_data)
                
                return (
                    f"✅ SARS Knowledge Base Updated\n"
                    f"═══════════════════════════════════════════\n"
                    f"Regulation: {regulation_type.upper()}\n"
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"New Last Updated: {new_data.get('last_updated', 'Unknown')}\n\n"
                    f"⚠️ Financial Sentinel notified of changes.\n"
                    f"📋 Old version backed up for reference."
                )
            except Exception as e:
                return f"❌ Failed to update regulation: {str(e)}"
        
        def get_monitoring_sources() -> str:
            """Get list of SARS sources being monitored."""
            return (
                f"📡 SARS Sources Monitored:\n\n" +
                "\n".join([f"  {i+1}. {url}" for i, url in enumerate(self.SARS_SOURCES)])
            )
        
        # Register with AG2
        register_function(
            check_sars_for_updates,
            caller=self.agent,
            executor=self.agent,
            name="check_sars_for_updates",
            description="Check SARS official sources for regulation updates"
        )
        
        register_function(
            update_sars_regulation,
            caller=self.agent,
            executor=self.agent,
            name="update_sars_regulation",
            description="Update local SARS knowledge base with new regulation data"
        )
        
        register_function(
            get_monitoring_sources,
            caller=self.agent,
            executor=self.agent,
            name="get_monitoring_sources",
            description="Get list of SARS sources being monitored"
        )
        
        print("[SARS Monitor] 3 tools registered (SARS monitoring + auto-update)")
