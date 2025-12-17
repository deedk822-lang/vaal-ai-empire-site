"""
Vaal AI Empire - AG2 Multi-Agent Orchestrator

Orchestrates Financial Sentinel, Guardian Engine, and Talent Accelerator agents.
Supports multiple patterns: AutoPattern, GroupChat, Sequential, Human-in-the-loop.
"""

import os
import sys
import asyncio
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from autogen import ConversableAgent, UserProxyAgent, LLMConfig
from autogen.agentchat import run_group_chat
from autogen.agentchat.group.patterns import AutoPattern

from agents.ag2.financial_sentinel_agent import FinancialSentinelAgent
from agents.ag2.guardian_engine_agent import GuardianEngineAgent


class VaalAIEmpireOrchestrator:
    """
    Central orchestrator for Vaal AI Empire's AG2 multi-agent system.
    
    Patterns:
    - AutoPattern: Automatic agent selection based on task
    - GroupChat: All agents collaborate on complex tasks
    - Sequential: Agents work in order (Financial → Guardian → Talent)
    - HumanInTheLoop: Human approval for critical actions (payments, compliance)
    """
    
    def __init__(self, llm_config_path: str = "OAI_CONFIG_LIST", cohere_api_key: str = None):
        self.llm_config = LLMConfig.from_json(path=llm_config_path)
        self.cohere_api_key = cohere_api_key or os.getenv('COHERE_API_KEY')
        
        # Initialize agents
        self.financial_sentinel = None
        self.guardian_engine = None
        self.human_proxy = None
        
        self.initialized = False
    
    async def initialize(self):
        """Initialize all agents and register tools."""
        if self.initialized:
            print("[Orchestrator] Already initialized.")
            return
        
        print("[Orchestrator] 🔥 Initializing Vaal AI Empire...")
        
        # Create Financial Sentinel
        self.financial_sentinel = FinancialSentinelAgent(
            llm_config=self.llm_config,
            cohere_api_key=self.cohere_api_key
        )
        await self.financial_sentinel.initialize()
        
        # Create Guardian Engine
        self.guardian_engine = GuardianEngineAgent(
            llm_config=self.llm_config,
            cohere_api_key=self.cohere_api_key
        )
        await self.guardian_engine.initialize()
        
        # Create Human Proxy Agent (for approvals)
        self.human_proxy = UserProxyAgent(
            name="human_validator",
            system_message=(
                "You are a human business owner. "
                "Review agent recommendations and approve/reject critical actions. "
                "Type 'APPROVED' to proceed, 'REJECT' to cancel, or provide feedback."
            ),
            human_input_mode="ALWAYS",
            code_execution_config=False,
            description="Human validator for critical business decisions (payments, compliance, contracts)."
        )
        
        self.initialized = True
        print("[Orchestrator] ✅ Vaal AI Empire ready! Financial Sentinel + Guardian Engine online.")
    
    async def auto_pattern(self, task: str, max_rounds: int = 20, require_human_approval: bool = False) -> Dict[str, Any]:
        """
        AutoPattern orchestration - AG2 automatically selects best agent for each step.
        
        Args:
            task: Natural language task description
            max_rounds: Maximum conversation rounds
            require_human_approval: Whether to require human approval for final output
        
        Returns:
            Dict with 'summary', 'chat_history', 'cost'
        """
        if not self.initialized:
            await self.initialize()
        
        agents = [self.financial_sentinel.agent, self.guardian_engine.agent]
        
        # Add human validator if required
        user_agent = self.human_proxy if require_human_approval else None
        
        pattern = AutoPattern(
            agents=agents,
            initial_agent=self.financial_sentinel.agent,  # Start with Financial Sentinel
            user_agent=user_agent,
            group_manager_args={"name": "empire_manager", "llm_config": self.llm_config}
        )
        
        print(f"[Orchestrator] 🚀 Running AutoPattern: {task}")
        
        response = run_group_chat(
            pattern=pattern,
            messages=task,
            max_rounds=max_rounds
        )
        
        response.process()
        
        return {
            'summary': response.summary,
            'chat_history': response.chat_history,
            'cost': getattr(response, 'cost', None)
        }
    
    async def sequential_workflow(self, task: str, workflow_steps: List[str]) -> Dict[str, Any]:
        """
        Sequential workflow - Agents work in defined order.
        
        Example workflow:
        1. Financial Sentinel calculates tax recovery
        2. Guardian Engine checks for crisis risks
        3. Human approves final recommendation
        
        Args:
            task: Initial task description
            workflow_steps: List of agent names in order ['financial_sentinel', 'guardian_engine', 'human']
        
        Returns:
            Dict with results from each step
        """
        if not self.initialized:
            await self.initialize()
        
        results = {'task': task, 'steps': []}
        current_message = task
        
        for step_name in workflow_steps:
            if step_name == 'financial_sentinel':
                agent = self.financial_sentinel.agent
                print(f"[Orchestrator] 💰 Step: Financial Sentinel")
            elif step_name == 'guardian_engine':
                agent = self.guardian_engine.agent
                print(f"[Orchestrator] 🛡️ Step: Guardian Engine")
            elif step_name == 'human':
                agent = self.human_proxy
                print(f"[Orchestrator] 👤 Step: Human Approval")
            else:
                continue
            
            # Run agent
            response = agent.run(
                recipient=agent,
                message=current_message,
                max_turns=5
            )
            
            step_result = {
                'agent': step_name,
                'output': response.summary if hasattr(response, 'summary') else str(response)
            }
            
            results['steps'].append(step_result)
            current_message = step_result['output']  # Pass output to next step
        
        return results
    
    async def tax_recovery_workflow(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized workflow: Tax Recovery Analysis + Crisis Check.
        
        Steps:
        1. Financial Sentinel calculates Section 12H + ETI
        2. Guardian Engine checks current crisis risks
        3. Combined recommendation with risk-adjusted timeline
        
        Args:
            company_data: {
                'learnerships': [...],
                'employees': [...],
                'sector': 'manufacturing',
                'current_eaf': 62.5  # Optional Eskom metric
            }
        
        Returns:
            Complete tax recovery + crisis analysis
        """
        if not self.initialized:
            await self.initialize()
        
        print("[Orchestrator] 🔥 Running Tax Recovery + Crisis Analysis Workflow")
        
        # Step 1: Financial Sentinel calculates tax recovery
        import json
        
        task = f"""
        Calculate complete tax recovery for this South African company:
        
        Learnerships: {json.dumps(company_data.get('learnerships', []))}
        Employees: {json.dumps(company_data.get('employees', []))}
        
        Use calculate_section_12h and calculate_eti tools. Provide total recovery and tax savings.
        """
        
        financial_response = self.financial_sentinel.agent.run(
            recipient=self.financial_sentinel.agent,
            message=task,
            max_turns=5
        )
        
        # Step 2: Guardian Engine checks crisis risk
        if 'current_eaf' in company_data:
            crisis_task = f"""
            Assess current load-shedding risk for {company_data.get('sector', 'general business')} sector.
            Current Eskom EAF: {company_data['current_eaf']}%
            
            Use assess_loadshedding_risk tool.
            """
            
            crisis_response = self.guardian_engine.agent.run(
                recipient=self.guardian_engine.agent,
                message=crisis_task,
                max_turns=3
            )
        else:
            crisis_response = "No current crisis data provided. Skipping risk assessment."
        
        # Step 3: Combine results
        return {
            'tax_recovery': financial_response.summary if hasattr(financial_response, 'summary') else str(financial_response),
            'crisis_assessment': crisis_response.summary if hasattr(crisis_response, 'summary') else str(crisis_response),
            'company_data': company_data
        }
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents."""
        return {
            'financial_sentinel': '✅ Online' if self.financial_sentinel and self.financial_sentinel.initialized else '❌ Offline',
            'guardian_engine': '✅ Online' if self.guardian_engine and self.guardian_engine.initialized else '❌ Offline',
            'human_proxy': '✅ Ready' if self.human_proxy else '❌ Not configured',
            'orchestrator': '✅ Initialized' if self.initialized else '❌ Not initialized'
        }


# Quick test function
async def test_orchestrator():
    """Test the orchestrator with sample data."""
    orchestrator = VaalAIEmpireOrchestrator()
    await orchestrator.initialize()
    
    print("\n" + "="*50)
    print("Agent Status:")
    for agent, status in orchestrator.get_agent_status().items():
        print(f"  {agent}: {status}")
    print("="*50 + "\n")
    
    # Test tax recovery workflow
    company_data = {
        'learnerships': [
            {'id': 1, 'nqf_level': 5, 'disabled': False, 'completed': True},
            {'id': 2, 'nqf_level': 8, 'disabled': False, 'completed': True}
        ],
        'employees': [
            {'id': 1, 'age': 24, 'monthly_salary': 4000, 'months_employed': 6},
            {'id': 2, 'age': 27, 'monthly_salary': 5500, 'months_employed': 15}
        ],
        'sector': 'manufacturing',
        'current_eaf': 62.5
    }
    
    result = await orchestrator.tax_recovery_workflow(company_data)
    
    print("\n" + "="*50)
    print("TAX RECOVERY + CRISIS ANALYSIS RESULT:")
    print("="*50)
    print(result['tax_recovery'])
    print("\n" + "-"*50)
    print(result['crisis_assessment'])
    print("="*50)


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
