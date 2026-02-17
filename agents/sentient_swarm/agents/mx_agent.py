"""
MX (Machine Experience) Agent - SEO/GEO optimization.

Generates structured data and AI-parseable content.
"""

import json
from typing import Any, Dict
from .base_agent import BaseAgent


class MXAgent(BaseAgent):
    """Optimizes for Machine Experience and Generative Engine Optimization."""
    
    def __init__(self, llm_client=None, metrics=None, tracer=None):
        super().__init__("MX", llm_client, metrics, tracer)
        if self.llm is None:
            raise ValueError("MXAgent requires a valid LLM client.")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured data and GEO content."""
        self.log("🧠 Optimizing for Machine Experience...")
        
        # Generate JSON-LD schema
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": context.get('company_name', 'Vaal AI Empire'),
            "description": context.get('description', 'AI-powered digital sovereignty'),
            "url": context.get('url', 'https://vaalaiempire.co.za'),
            "logo": "https://vaalaiempire.co.za/logo.png",
            "sameAs": [
                "https://twitter.com/vaalaiempire",
                "https://linkedin.com/company/vaal-ai-empire"
            ],
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+27-11-123-4567",
                "contactType": "customer service",
                "areaServed": "ZA",
                "availableLanguage": ["English", "Afrikaans", "Zulu"]
            }
        }
        
        schema_file = self.write_file("organization-schema.json", json.dumps(schema, indent=2))
        
        # Generate GEO-optimized content structure
        geo_prompt = """Generate a content structure optimized for Generative Engine Optimization (GEO):

Create:
1. FAQ schema with 5 questions about AI services for South African SMEs
2. Entity definitions (What is Digital Sovereignty, AI Automation, etc.)
3. Answer-first paragraphs for each topic
4. Citation-ready statements with source placeholders

Output as structured JSON."""
        
        geo_response = await self.llm.generate(
            prompt=geo_prompt,
            system_message="You are an SEO/GEO expert specializing in AI-parseable content.",
            temperature=0.7
        )
        
        if not geo_response.success:
            return {
                'agent': self.name,
                'status': 'failed',
                'error': geo_response.error,
                'files': [schema_file]
            }
        
        # Validate JSON before writing
        try:
            geo_payload = json.loads(geo_response.content)
            geo_file = self.write_file("geo-content.json", json.dumps(geo_payload, indent=2))
        except json.JSONDecodeError:
            geo_file = self.write_file("geo-content.json", json.dumps({
                'raw': geo_response.content,
                'error': 'invalid_json'
            }, indent=2))
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [schema_file, geo_file],
            'metrics': {
                'schema_entities': len(schema),
                'geo_tokens': geo_response.tokens_used,
                'provider': geo_response.provider.value
            }
        }
