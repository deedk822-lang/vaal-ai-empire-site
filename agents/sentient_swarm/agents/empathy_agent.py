"""
Empathy Agent - Human-first content generation.
"""

from typing import Any, ClassVar, Dict

from .base_agent import BaseAgent


class EmpathyAgent(BaseAgent):
    """Generates empathetic, human-first content."""
    
    FALLBACK_GUIDELINES = '''# Content Guidelines

## Brand Voice
- Authentic and non-corporate
- Transparent about capabilities
- Respectful of user time

## Tone Guidelines
- Empathetic to business challenges
- Encouraging and supportive
- Mindful of South African context

## Microcopy Examples
- Error: "We encountered an issue. Let's fix it together."
- Loading: "Setting things up for you..."
- Success: "Great! Everything is ready."
'''

    FALLBACK_PAGES: ClassVar[Dict[str, str]] = {
        'home': '# Home\n\n## Empowering South African SMEs with AI\n\nWe understand the unique challenges facing South African businesses. Our AI solutions are designed to help you grow.',
        'about': '# About Us\n\n## Born in South Africa, Built for Africa\n\nWe are a team of local experts passionate about helping businesses succeed with technology.',
        'services': '# Services\n\n## AI Solutions for Your Business\n\n- Process Automation\n- Customer Insights\n- Data Analytics\n- 24/7 Support',
        'contact': '# Contact\n\n## Let\'s Talk\n\nReady to transform your business? Reach out to us.\n\nEmail: hello@example.com'
    }
    
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
        
        guidelines_content = self.FALLBACK_GUIDELINES
        total_tokens = 0
        provider = "fallback"
        
        if self.llm:
            guidelines_response = await self.llm.generate(
                prompt=guidelines_prompt,
                system_message="You are a senior copywriter specializing in authentic brand voice.",
                temperature=0.8
            )
            
            if guidelines_response.success:
                guidelines_content = guidelines_response.content
                total_tokens += guidelines_response.tokens_used
                provider = guidelines_response.provider.value
            else:
                self.log("⚠️  LLM failed, using fallback guidelines")
        else:
            self.log("⚠️  No LLM available, using fallback guidelines")
        
        guidelines_file = self.write_file("content-guidelines.md", guidelines_content)
        
        # Generate page copy
        pages = ['home', 'about', 'services', 'contact']
        page_files = []
        
        for page in pages:
            page_content = self.FALLBACK_PAGES.get(page, f'# {page.title()}\n\nContent coming soon.')
            
            if self.llm:
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
                
                if page_response.success:
                    page_content = page_response.content
                    total_tokens += page_response.tokens_used
                else:
                    self.log(f"⚠️  LLM failed for {page}, using fallback")
            
            page_file = self.write_file(f"{page}-copy.md", page_content)
            page_files.append(page_file)
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [guidelines_file] + page_files,
            'metrics': {
                'pages_generated': len(pages),
                'total_tokens': total_tokens,
                'provider': provider
            }
        }
