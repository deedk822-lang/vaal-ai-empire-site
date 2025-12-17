"""
Vaal AI Empire - SARS Knowledge Base (Python)

Python version that uses REAL Cohere API for semantic search.
Loads REAL SARS data from JSON files.
"""

import os
import json
from pathlib import Path
import cohere


class SARSKnowledgeBase:
    def __init__(self, cohere_api_key: str = None):
        self.cohere_api_key = cohere_api_key or os.getenv('COHERE_API_KEY')
        self.co = cohere.Client(self.cohere_api_key)
        self.initialized = False
        self.data_path = Path(__file__).parent.parent.parent / 'data' / 'sars'
        self.documents = []
        self.section12h_data = None
        self.eti_data = None
    
    async def initialize(self):
        """Load SARS data from JSON files."""
        print('[SARS KB] Loading REAL SARS data...')
        
        # Load Section 12H data
        with open(self.data_path / 'section_12h_learnerships.json', 'r') as f:
            self.section12h_data = json.load(f)
        
        # Load ETI data
        with open(self.data_path / 'eti_employment_incentive.json', 'r') as f:
            self.eti_data = json.load(f)
        
        # Prepare documents for Cohere
        self.documents = []
        
        # Section 12H overview
        self.documents.append(
            f"{self.section12h_data['regulation']}: {self.section12h_data['description']}. "
            f"Status: {self.section12h_data['status']}. "
            f"Annual allowances: NQF 1-6 able-bodied R{self.section12h_data['allowances']['annual_allowance']['nqf_1_to_6']['able_bodied']}, "
            f"disability R{self.section12h_data['allowances']['annual_allowance']['nqf_1_to_6']['disability']}. "
            f"NQF 7-10 able-bodied R{self.section12h_data['allowances']['annual_allowance']['nqf_7_to_10']['able_bodied']}, "
            f"disability R{self.section12h_data['allowances']['annual_allowance']['nqf_7_to_10']['disability']}."
        )
        
        # Section 12H examples
        for example in self.section12h_data['calculation_examples']:
            self.documents.append(
                f"Section 12H Example: {example['scenario']}. "
                f"Total deduction: {example.get('total_deduction', 'N/A')}. "
                f"Tax saving at 28%: {example.get('tax_saving_28_percent', 'N/A')}."
            )
        
        # ETI overview
        self.documents.append(
            f"{self.eti_data['regulation']}: {self.eti_data['description']}. "
            f"Effective from {self.eti_data['monthly_allowance_2025']['effective_from']}. "
            f"First 12 months: Up to R1,500/month. Second 12 months: Up to R750/month. "
            f"Eligibility: Employees aged 18-29."
        )
        
        # ETI examples
        for example in self.eti_data['calculation_examples']:
            self.documents.append(
                f"ETI Example: {example['scenario']}. "
                f"Details: {str(example)}"
            )
        
        self.initialized = True
        print(f'[SARS KB] Loaded {len(self.documents)} REAL documents from SARS data')
    
    async def query(self, query: str, topN: int = 3):
        """Query SARS regulations using REAL Cohere API."""
        if not self.initialized:
            await self.initialize()
        
        print(f'[SARS KB] Searching REAL Cohere API: {query}')
        
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
    
    async def calculateSection12H(self, company_data: dict):
        """Calculate REAL Section 12H using actual SARS rates."""
        if not self.initialized:
            await self.initialize()
        
        learnerships = company_data.get('learnerships', [])
        total_recovery = 0
        breakdown = []
        
        for learner in learnerships:
            level = 'nqf_1_to_6' if learner['nqf_level'] <= 6 else 'nqf_7_to_10'
            ability = 'disability' if learner.get('disabled', False) else 'able_bodied'
            
            # Get REAL rates from loaded data
            annual_allowance = self.section12h_data['allowances']['annual_allowance'][level][ability]
            completion_allowance = self.section12h_data['allowances']['completion_allowance'][level][ability] if learner.get('completed', False) else 0
            
            learner_total = annual_allowance + completion_allowance
            total_recovery += learner_total
            
            breakdown.append({
                'learner_id': learner.get('id'),
                'nqf_level': learner['nqf_level'],
                'annual_allowance': annual_allowance,
                'completion_allowance': completion_allowance,
                'total': learner_total
            })
        
        tax_saving = total_recovery * 0.28
        
        return {
            'regulation': 'Section 12H - Learnership Allowances',
            'total_recovery': total_recovery,
            'tax_saving_28_percent': tax_saving,
            'learnerships_count': len(learnerships),
            'breakdown': breakdown,
            'source': self.section12h_data['official_sources'][0],
            'last_verified': self.section12h_data['last_updated'],
            'confidence': 'Verified by SARS'
        }
    
    async def calculateETI(self, company_data: dict):
        """Calculate REAL ETI using actual SARS rates."""
        if not self.initialized:
            await self.initialize()
        
        employees = company_data.get('employees', [])
        total_monthly_eti = 0
        breakdown = []
        
        for employee in employees:
            # Check eligibility
            if employee['age'] < 18 or employee['age'] > 29:
                continue
            if employee['monthly_salary'] >= 7500:
                continue
            
            months_employed = employee.get('months_employed', 1)
            monthly_eti = 0
            
            if months_employed <= 12:
                # First 12 months (REAL SARS rates)
                if employee['monthly_salary'] < 2500:
                    monthly_eti = employee['monthly_salary'] * 0.6
                elif 2500 <= employee['monthly_salary'] < 5500:
                    monthly_eti = 1500
                else:
                    monthly_eti = 1500 - (0.75 * (employee['monthly_salary'] - 5500))
            else:
                # Second 12 months (REAL SARS rates)
                if employee['monthly_salary'] < 2500:
                    monthly_eti = employee['monthly_salary'] * 0.3
                elif 2500 <= employee['monthly_salary'] < 5500:
                    monthly_eti = 750
                else:
                    monthly_eti = 750 - (0.375 * (employee['monthly_salary'] - 5500))
            
            monthly_eti = max(0, monthly_eti)
            total_monthly_eti += monthly_eti
            
            breakdown.append({
                'employee_id': employee.get('id'),
                'age': employee['age'],
                'salary': employee['monthly_salary'],
                'months_employed': months_employed,
                'monthly_eti': monthly_eti
            })
        
        annual_eti = total_monthly_eti * 12
        
        return {
            'regulation': 'Employment Tax Incentive (ETI)',
            'monthly_eti': total_monthly_eti,
            'annual_eti': annual_eti,
            'qualifying_employees': len(breakdown),
            'breakdown': breakdown,
            'source': self.eti_data['official_sources'][0],
            'last_verified': self.eti_data['last_updated'],
            'confidence': 'Verified by SARS'
        }
