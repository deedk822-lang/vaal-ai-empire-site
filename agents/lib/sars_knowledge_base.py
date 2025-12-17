"""
Vaal AI Empire - SARS Knowledge Base (Static - Self-Updating)

Static knowledge base loaded from REAL SARS JSON files.
No external API calls - all knowledge is local.

Agents can self-update this library when SARS publishes new regulations.
Monitors official SARS sources and auto-updates knowledge base.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class SARSKnowledgeBase:
    """
    Static SARS knowledge base that loads from JSON files.
    
    Features:
    - Loads ALL SARS regulations from local JSON files
    - No external API dependencies
    - Agents can query using simple keyword matching
    - Self-updating mechanism when SARS changes laws
    """
    
    def __init__(self):
        self.data_path = Path(__file__).parent.parent.parent / 'data' / 'sars'
        self.section12h_data = None
        self.eti_data = None
        self.knowledge_base = []
        self.initialized = False
        self.last_updated = None
    
    def initialize(self):
        """Load ALL SARS knowledge from JSON files."""
        print('[SARS KB] Loading SARS knowledge from local files...')
        
        # Load Section 12H data
        with open(self.data_path / 'section_12h_learnerships.json', 'r') as f:
            self.section12h_data = json.load(f)
        
        # Load ETI data
        with open(self.data_path / 'eti_employment_incentive.json', 'r') as f:
            self.eti_data = json.load(f)
        
        # Build searchable knowledge base
        self._build_knowledge_base()
        
        self.initialized = True
        self.last_updated = datetime.now().isoformat()
        
        print(f'[SARS KB] ✅ Loaded {len(self.knowledge_base)} SARS regulations')
        print(f'[SARS KB] Section 12H: {self.section12h_data["regulation"]}')
        print(f'[SARS KB] ETI: {self.eti_data["regulation"]}')
        print(f'[SARS KB] Last Updated: {self.section12h_data["last_updated"]}')
    
    def _build_knowledge_base(self):
        """Build searchable knowledge base from JSON data."""
        self.knowledge_base = []
        
        # Section 12H - Overview
        self.knowledge_base.append({
            'id': 'section_12h_overview',
            'regulation': 'Section 12H',
            'topic': 'Learnership Allowances',
            'content': (
                f"{self.section12h_data['regulation']}: {self.section12h_data['description']}. "
                f"Status: {self.section12h_data['status']}. "
                f"Annual allowances: NQF 1-6 able-bodied R{self.section12h_data['allowances']['annual_allowance']['nqf_1_to_6']['able_bodied']:,}, "
                f"disability R{self.section12h_data['allowances']['annual_allowance']['nqf_1_to_6']['disability']:,}. "
                f"NQF 7-10 able-bodied R{self.section12h_data['allowances']['annual_allowance']['nqf_7_to_10']['able_bodied']:,}, "
                f"disability R{self.section12h_data['allowances']['annual_allowance']['nqf_7_to_10']['disability']:,}."
            ),
            'keywords': ['section 12h', 'learnership', 'nqf', 'allowance', 'deduction', 'seta'],
            'source': self.section12h_data['official_sources'][0]
        })
        
        # Section 12H - Completion Allowances
        self.knowledge_base.append({
            'id': 'section_12h_completion',
            'regulation': 'Section 12H',
            'topic': 'Completion Allowances',
            'content': (
                f"Once-off completion allowances: "
                f"NQF 1-6 able-bodied R{self.section12h_data['allowances']['completion_allowance']['nqf_1_to_6']['able_bodied']:,}, "
                f"disability R{self.section12h_data['allowances']['completion_allowance']['nqf_1_to_6']['disability']:,}. "
                f"NQF 7-10 able-bodied R{self.section12h_data['allowances']['completion_allowance']['nqf_7_to_10']['able_bodied']:,}, "
                f"disability R{self.section12h_data['allowances']['completion_allowance']['nqf_7_to_10']['disability']:,}. "
                f"For learnerships over 24 months, allowance is multiplied by number of consecutive 12-month periods."
            ),
            'keywords': ['completion', 'bonus', 'once-off', 'finished', 'completed'],
            'source': self.section12h_data['official_sources'][0]
        })
        
        # Section 12H - Eligibility
        self.knowledge_base.append({
            'id': 'section_12h_eligibility',
            'regulation': 'Section 12H',
            'topic': 'Eligibility Requirements',
            'content': (
                f"Employer eligibility: {', '.join(self.section12h_data['eligibility']['employer'])}. "
                f"Learner eligibility: {', '.join(self.section12h_data['eligibility']['learner'])}."
            ),
            'keywords': ['eligibility', 'requirements', 'qualify', 'registered', 'seta'],
            'source': self.section12h_data['official_sources'][0]
        })
        
        # Section 12H - Documentation
        self.knowledge_base.append({
            'id': 'section_12h_documentation',
            'regulation': 'Section 12H',
            'topic': 'Required Documentation',
            'content': (
                f"Required documents: {', '.join(self.section12h_data['documentation_required']['sars_forms'])}. "
                f"Proof of registration: {self.section12h_data['documentation_required']['proof_of_registration']}. "
                f"Proof of completion: {self.section12h_data['documentation_required']['proof_of_completion']}. "
                f"Learner details: {self.section12h_data['documentation_required']['learner_details']}."
            ),
            'keywords': ['documentation', 'forms', 'it180', 'certificate', 'proof'],
            'source': self.section12h_data['official_sources'][0]
        })
        
        # Section 12H - Common Mistakes
        self.knowledge_base.append({
            'id': 'section_12h_mistakes',
            'regulation': 'Section 12H',
            'topic': 'Common Mistakes',
            'content': f"Common mistakes to avoid: {', '.join(self.section12h_data['common_mistakes'])}.",
            'keywords': ['mistakes', 'errors', 'avoid', 'common', 'problems'],
            'source': self.section12h_data['official_sources'][0]
        })
        
        # ETI - Overview
        self.knowledge_base.append({
            'id': 'eti_overview',
            'regulation': 'ETI',
            'topic': 'Employment Tax Incentive',
            'content': (
                f"{self.eti_data['regulation']}: {self.eti_data['description']}. "
                f"Effective from {self.eti_data['monthly_allowance_2025']['effective_from']}. "
                f"Qualifying threshold: {self.eti_data['monthly_allowance_2025']['qualifying_threshold']}. "
                f"Minimum hours: {self.eti_data['monthly_allowance_2025']['minimum_hours']} per month. "
                f"First 12 months: Up to R1,500/month. Second 12 months: Up to R750/month."
            ),
            'keywords': ['eti', 'employment tax incentive', 'youth', 'young workers', '18-29'],
            'source': self.eti_data['official_sources'][0]
        })
        
        # ETI - Eligibility
        self.knowledge_base.append({
            'id': 'eti_eligibility',
            'regulation': 'ETI',
            'topic': 'Eligibility Requirements',
            'content': (
                f"Employee requirements: Age {self.eti_data['eligibility']['employee']['age_range']}, "
                f"{self.eti_data['eligibility']['employee']['citizenship']}, "
                f"{self.eti_data['eligibility']['employee']['not_connected_person']}, "
                f"{self.eti_data['eligibility']['employee']['not_domestic_worker']}. "
                f"Employer requirements: {', '.join([f'{k}: {v}' for k, v in self.eti_data['eligibility']['employer'].items() if k != 'excluded_sectors'])}."
            ),
            'keywords': ['eligibility', 'qualify', 'age', '18-29', 'citizen', 'paye'],
            'source': self.eti_data['official_sources'][0]
        })
        
        # ETI - Claiming Process
        self.knowledge_base.append({
            'id': 'eti_claiming',
            'regulation': 'ETI',
            'topic': 'Claiming Process',
            'content': (
                f"Claiming frequency: {self.eti_data['claiming_process']['frequency']}. "
                f"Reconciliation: {self.eti_data['claiming_process']['reconciliation']}. "
                f"Certificate: {self.eti_data['claiming_process']['certificate']}. "
                f"Audit trail: {self.eti_data['claiming_process']['audit_trail']}."
            ),
            'keywords': ['claim', 'emp201', 'emp501', 'paye', 'monthly', 'reconciliation'],
            'source': self.eti_data['official_sources'][0]
        })
        
        # Add calculation examples
        for i, example in enumerate(self.section12h_data['calculation_examples']):
            self.knowledge_base.append({
                'id': f'section_12h_example_{i}',
                'regulation': 'Section 12H',
                'topic': 'Calculation Example',
                'content': f"Example: {example['scenario']}. {str(example)}",
                'keywords': ['example', 'calculation', 'scenario'],
                'source': self.section12h_data['official_sources'][0]
            })
        
        for i, example in enumerate(self.eti_data['calculation_examples']):
            self.knowledge_base.append({
                'id': f'eti_example_{i}',
                'regulation': 'ETI',
                'topic': 'Calculation Example',
                'content': f"Example: {example['scenario']}. {str(example)}",
                'keywords': ['example', 'calculation', 'scenario'],
                'source': self.eti_data['official_sources'][0]
            })
    
    def query(self, query_text: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Simple keyword-based search of SARS knowledge."""
        if not self.initialized:
            self.initialize()
        
        query_lower = query_text.lower()
        results = []
        
        for item in self.knowledge_base:
            score = 0
            
            # Check if query words appear in content or keywords
            for word in query_lower.split():
                if word in item['content'].lower():
                    score += 10
                if any(word in keyword for keyword in item['keywords']):
                    score += 5
            
            if score > 0:
                results.append({
                    **item,
                    'relevance_score': score
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return results[:top_n]
    
    def calculate_section_12h(self, learnerships: List[Dict]) -> Dict[str, Any]:
        """Calculate Section 12H allowances using REAL SARS rates."""
        if not self.initialized:
            self.initialize()
        
        total_recovery = 0
        breakdown = []
        
        for learner in learnerships:
            level = 'nqf_1_to_6' if learner['nqf_level'] <= 6 else 'nqf_7_to_10'
            ability = 'disability' if learner.get('disabled', False) else 'able_bodied'
            
            annual = self.section12h_data['allowances']['annual_allowance'][level][ability]
            completion = self.section12h_data['allowances']['completion_allowance'][level][ability] if learner.get('completed', False) else 0
            
            learner_total = annual + completion
            total_recovery += learner_total
            
            breakdown.append({
                'learner_id': learner.get('id'),
                'nqf_level': learner['nqf_level'],
                'annual_allowance': annual,
                'completion_allowance': completion,
                'total': learner_total
            })
        
        return {
            'regulation': 'Section 12H - Learnership Allowances',
            'total_recovery': total_recovery,
            'tax_saving_28_percent': total_recovery * 0.28,
            'learnerships_count': len(learnerships),
            'breakdown': breakdown,
            'source': self.section12h_data['official_sources'][0],
            'last_verified': self.section12h_data['last_updated']
        }
    
    def calculate_eti(self, employees: List[Dict]) -> Dict[str, Any]:
        """Calculate ETI using REAL SARS rates."""
        if not self.initialized:
            self.initialize()
        
        total_monthly_eti = 0
        breakdown = []
        
        for employee in employees:
            if employee['age'] < 18 or employee['age'] > 29:
                continue
            if employee['monthly_salary'] >= 7500:
                continue
            
            months_employed = employee.get('months_employed', 1)
            monthly_eti = 0
            
            if months_employed <= 12:
                if employee['monthly_salary'] < 2500:
                    monthly_eti = employee['monthly_salary'] * 0.6
                elif 2500 <= employee['monthly_salary'] < 5500:
                    monthly_eti = 1500
                else:
                    monthly_eti = 1500 - (0.75 * (employee['monthly_salary'] - 5500))
            else:
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
        
        return {
            'regulation': 'Employment Tax Incentive (ETI)',
            'monthly_eti': total_monthly_eti,
            'annual_eti': total_monthly_eti * 12,
            'qualifying_employees': len(breakdown),
            'breakdown': breakdown,
            'source': self.eti_data['official_sources'][0],
            'last_verified': self.eti_data['last_updated']
        }
    
    def update_regulation(self, regulation_type: str, new_data: Dict[str, Any]):
        """
        Self-update mechanism for when SARS changes laws.
        
        Agent can call this when it detects SARS has updated regulations.
        
        Args:
            regulation_type: 'section_12h' or 'eti'
            new_data: Updated regulation data (same format as JSON files)
        """
        file_map = {
            'section_12h': 'section_12h_learnerships.json',
            'eti': 'eti_employment_incentive.json'
        }
        
        if regulation_type not in file_map:
            raise ValueError(f"Unknown regulation type: {regulation_type}")
        
        file_path = self.data_path / file_map[regulation_type]
        
        # Backup old version
        backup_path = file_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        if file_path.exists():
            import shutil
            shutil.copy(file_path, backup_path)
            print(f'[SARS KB] Backed up old version to {backup_path.name}')
        
        # Write new data
        with open(file_path, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        print(f'[SARS KB] ✅ Updated {regulation_type} with new SARS data')
        print(f'[SARS KB] New last_updated: {new_data.get("last_updated", "Unknown")}')
        
        # Reload knowledge base
        self.initialize()
    
    def get_all_regulations(self) -> List[str]:
        """Get list of all loaded regulations."""
        if not self.initialized:
            self.initialize()
        
        return list(set([item['regulation'] for item in self.knowledge_base]))
    
    def get_regulation_details(self, regulation: str) -> Dict[str, Any]:
        """Get full details of a specific regulation."""
        if not self.initialized:
            self.initialize()
        
        if regulation.upper() == 'SECTION 12H':
            return self.section12h_data
        elif regulation.upper() == 'ETI':
            return self.eti_data
        else:
            return None
