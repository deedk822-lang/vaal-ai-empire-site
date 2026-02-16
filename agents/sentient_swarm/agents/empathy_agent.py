"""
Empathy Agent - Human-first content generation.
"""

from typing import Any, Dict
from .base_agent import BaseAgent


class EmpathyAgent(BaseAgent):
    """Generates empathetic, human-first content."""
    
    def __init__(self, llm_client=None, metrics=None, tracer=None):
        super().__init__("Empathy", llm_client, metrics, tracer)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate empathetic copy."""
        self.log("💝 Generating empathetic content...")
        
        # Generate content guidelines
        guidelines_prompt = """Create content guidelines for a South African AI company:

Sections:
1. Brand Voice (authentic, non-corporate)
2. Tone Guidelines (empathetic, encouraging)
3. Microcopy Examples (error messages, CTAs, empty states)
4. Inclusive Language Guide (SA context awareness)
5. Storytelling Framework

Output as Markdown."""
        
        guidelines_response = await self.llm.generate(
            prompt=guidelines_prompt,
            system_message="You are a senior copywriter specializing in authentic brand voice.",
            temperature=0.8
        )
        
        if not guidelines_response.success:
            return {
                'agent': self.name,
                'status': 'failed',
                'error': guidelines_response.error,
                'files': []
            }
        
        guidelines_file = self.write_file("content-guidelines.md", guidelines_response.content)
        
        # Generate page copy
        pages = ['home', 'about', 'services', 'contact']
        page_files = []
        
        for page in pages:
            page_prompt = f"""Write {page} page copy for an AI company serving South African SMEs.

Requirements:
- Headline and 3 supporting sections
- Empathetic tone acknowledging business challenges
- Clear value propositions
- Call-to-action
- 300-500 words total"""
            
            page_response = await self.llm.generate(
                prompt=page_prompt,
                system_message="You are a conversion copywriter.",
                temperature=0.7
            )
            
            if not page_response.success:
                return {
                    'agent': self.name,
                    'status': 'failed',
                    'error': page_response.error,
                    'files': [guidelines_file] + page_files
                }
            
            page_file = self.write_file(f"{page}-copy.md", page_response.content)
            page_files.append(page_file)
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [guidelines_file] + page_files,
            'metrics': {
                'pages_generated': len(pages),
                'total_tokens': guidelines_response.tokens_used + sum([0]),  # Simplified
                'provider': guidelines_response.provider.value
            }
        }
