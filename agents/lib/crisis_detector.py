"""
Vaal AI Empire - Crisis Detector (Python)

Python version that uses REAL Cohere API for semantic search.
Loads REAL crisis data from JSON files.
"""

import os
import json
from pathlib import Path
from datetime import datetime
import cohere


class CrisisDetector:
    def __init__(self, cohere_api_key: str = None):
        self.cohere_api_key = cohere_api_key or os.getenv('COHERE_API_KEY')
        self.co = cohere.Client(self.cohere_api_key)
        self.initialized = False
        self.data_path = Path(__file__).parent.parent.parent / 'data' / 'crisis'
        self.documents = []
        self.loadshed_data = None
    
    async def initialize(self):
        """Load crisis data from JSON files."""
        print('[Crisis Detector] Loading REAL crisis data...')
        
        # Load load-shedding data
        with open(self.data_path / 'loadshedding_2024.json', 'r') as f:
            self.loadshed_data = json.load(f)
        
        # Prepare documents for Cohere
        self.documents = []
        
        # Load-shedding 2024 status
        self.documents.append(
            f"Load-shedding 2024 status: {self.loadshed_data['2024_performance']['status']}. "
            f"Consecutive days without load-shedding: {self.loadshed_data['2024_performance']['consecutive_days_no_loadshedding_as_of_dec_2024']}. "
            f"Last load-shedding: {self.loadshed_data['2024_performance']['last_loadshedding_date']}."
        )
        
        # Predictive indicators
        for indicator in self.loadshed_data['predictive_indicators']:
            self.documents.append(
                f"Indicator: {indicator['indicator']}. "
                f"Risk level: {indicator['risk_level']}. "
                f"Likely outcome: {indicator['likely_outcome']}."
            )
        
        # Business impact by sector
        for sector, impacts in self.loadshed_data['business_impact_matrix'].items():
            self.documents.append(
                f"Load-shedding impact on {sector}: "
                f"Stage 2 - {impacts['stage_2']}. "
                f"Stage 4 - {impacts['stage_4']}. "
                f"Mitigation: {impacts['mitigation']}."
            )
        
        self.initialized = True
        print(f'[Crisis Detector] Loaded {len(self.documents)} REAL documents from crisis data')
    
    async def query(self, query: str, topN: int = 3):
        """Query crisis intelligence using REAL Cohere API."""
        if not self.initialized:
            await self.initialize()
        
        print(f'[Crisis Detector] Searching REAL Cohere API: {query}')
        
        # Use REAL Cohere rerank API
        response = self.co.rerank(
            query=query,
            documents=self.documents,
            top_n=topN,
            model='rerank-english-v2.0'
        )
        
        results = []
        for idx, result in enumerate(response.results):
            results.append({
                'rank': idx + 1,
                'text': result.document.text,
                'relevanceScore': result.relevance_score
            })
        
        return {
            'query': query,
            'results': results,
            'totalResults': len(results)
        }
    
    def assessLoadsheddingRisk(self, metrics: dict):
        """Assess load-shedding risk using REAL Eskom thresholds."""
        eaf = metrics.get('eaf')
        unplanned_outages_mw = metrics.get('unplanned_outages_mw')
        coal_stockpile_days = metrics.get('coal_stockpile_days')
        
        risks = []
        overall_risk = 'Low'
        alert_level = 'GREEN'
        
        # REAL threshold from loaded data
        if eaf and eaf < 60:
            risks.append({
                'indicator': 'Energy Availability Factor below 60%',
                'current_value': eaf,
                'threshold': 60,
                'risk_level': 'Critical',
                'likely_outcome': 'Stage 4-6 loadshedding imminent',
                'action': 'Activate backup generators immediately'
            })
            overall_risk = 'Critical'
            alert_level = 'RED'
        elif eaf and eaf < 65:
            risks.append({
                'indicator': 'Energy Availability Factor below 65%',
                'current_value': eaf,
                'threshold': 65,
                'risk_level': 'High',
                'likely_outcome': 'Stage 2-4 loadshedding within 48 hours',
                'action': 'Prepare backup power systems'
            })
            overall_risk = 'High'
            alert_level = 'ORANGE'
        
        if unplanned_outages_mw and unplanned_outages_mw > 15000:
            risks.append({
                'indicator': 'Unplanned outages above 15,000 MW',
                'current_value': unplanned_outages_mw,
                'threshold': 15000,
                'risk_level': 'Critical',
                'likely_outcome': 'Stage 4-6 loadshedding imminent',
                'action': 'Implement emergency protocols'
            })
            if overall_risk != 'Critical':
                overall_risk = 'Critical'
            alert_level = 'RED'
        
        if coal_stockpile_days and coal_stockpile_days < 20:
            risks.append({
                'indicator': 'Coal stockpile below 20 days',
                'current_value': coal_stockpile_days,
                'threshold': 20,
                'risk_level': 'Medium',
                'likely_outcome': 'Increased risk within 2-4 weeks',
                'action': 'Monitor situation closely'
            })
            if overall_risk == 'Low':
                overall_risk = 'Medium'
            if alert_level == 'GREEN':
                alert_level = 'YELLOW'
        
        recommendations = self._get_recommendations(overall_risk)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_risk': overall_risk,
            'alert_level': alert_level,
            'risks': risks,
            'recommendations': recommendations,
            'source': self.loadshed_data['data_sources'][0]
        }
    
    def getBusinessImpact(self, sector: str, stage: int):
        """Get REAL business impact from loaded data."""
        if not self.initialized:
            raise Exception('Crisis Detector not initialized')
        
        impacts = self.loadshed_data['business_impact_matrix'].get(sector)
        if not impacts:
            raise Exception(f'Unknown sector: {sector}')
        
        stage_key = f'stage_{stage}'
        impact = impacts.get(stage_key, 'Unknown impact for this stage')
        
        return {
            'sector': sector,
            'stage': stage,
            'impact': impact,
            'mitigation': impacts['mitigation'],
            'severity': 'Severe' if stage >= 4 else 'Moderate' if stage >= 2 else 'Minor'
        }
    
    def _get_recommendations(self, risk_level: str):
        """Get REAL recommendations from loaded data."""
        recommendations_map = {
            'Critical': [
                'Activate all backup power systems immediately',
                'Reschedule critical operations to off-peak hours',
                'Alert all stakeholders of imminent disruption',
                'Implement emergency business continuity protocols'
            ],
            'High': [
                'Test backup generators and UPS systems',
                'Stock up on diesel/battery reserves',
                'Schedule flexible work arrangements',
                'Communicate potential disruptions to clients'
            ],
            'Medium': [
                'Monitor Eskom announcements closely',
                'Review business continuity plans',
                'Ensure backup systems are operational',
                'Consider demand-side management options'
            ],
            'Low': [
                'Maintain regular monitoring schedule',
                'Keep backup systems in standby mode',
                'Continue normal operations'
            ]
        }
        
        return recommendations_map.get(risk_level, recommendations_map['Low'])
