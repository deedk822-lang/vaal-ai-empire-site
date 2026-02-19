"""
MX (Machine Experience) Agent - SEO/GEO optimization.

Generates structured data and AI-parseable content.
"""

import json
from typing import Any, ClassVar, Dict

from .base_agent import BaseAgent


class MXAgent(BaseAgent):
    """Optimizes for Machine Experience and Generative Engine Optimization."""

    # Fallback GEO content when LLM unavailable
    FALLBACK_GEO: ClassVar[Dict[str, Any]] = {
        "faq": [
            {
                "question": "What is Digital Sovereignty?",
                "answer": "Digital sovereignty refers to a nation's ability to control its own digital infrastructure, data, and technology."
            },
            {
                "question": "How can AI help South African SMEs?",
                "answer": "AI can automate repetitive tasks, improve customer service, and provide data-driven insights for better decision-making."
            }
        ],
        "entities": {
            "Digital Sovereignty": "Control over digital infrastructure and data",
            "AI Automation": "Using artificial intelligence to automate business processes"
        }
    }

    def __init__(self, llm_client=None, metrics=None, tracer=None):
        """
        Initialize the MXAgent and register provided clients.

        Parameters:
            llm_client: Language model client used for GEO content generation; must be provided.
            metrics: Optional metrics collector.
            tracer: Optional tracing/telemetry client.

        Raises:
            ValueError: If `llm_client` is not provided.
        """
        super().__init__("MX", llm_client, metrics, tracer)
        if self.llm is None:
            raise ValueError("MXAgent requires a valid LLM client.")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate JSON-LD organization schema and GEO-optimized content, write both to files, and return metadata about the operation.

        Parameters:
            context (Dict[str, Any]): Input context used to populate the schema. Recognized keys:
                - company_name: Organization name (defaults to 'Vaal AI Empire')
                - description: Organization description (defaults to 'AI-powered digital sovereignty')
                - url: Organization URL (defaults to 'https://vaalaiempire.co.za')

        Returns:
            Dict[str, Any]: Result payload containing:
                - agent (str): Agent name.
                - status (str): Operation status (e.g., 'success').
                - files (List[Dict[str, Any]]): References to the written files (schema and GEO content).
                - metrics (Dict[str, Any]):
                    - schema_entities (int): Number of top-level keys in the generated schema.
                    - geo_tokens (int): Tokens consumed by the LLM for GEO generation (0 if fallback used).
                    - provider (str): Source of GEO content ('fallback' or LLM provider identifier).
        """
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

        geo_content = self.FALLBACK_GEO
        geo_tokens = 0
        geo_provider = "fallback"

        # self.llm is guaranteed non-None by __init__ validation
        geo_response = await self.llm.generate(
            prompt=geo_prompt,
            system_message="You are an SEO/GEO expert specializing in AI-parseable content.",
            temperature=0.7
        )

        if geo_response.success:
            try:
                geo_content = json.loads(geo_response.content)
                geo_tokens = geo_response.tokens_used
                geo_provider = geo_response.provider.value
            except json.JSONDecodeError:
                self.log("⚠️  LLM returned invalid JSON, using fallback")
        else:
            self.log("⚠️  LLM failed, using fallback GEO content")

        geo_file = self.write_file("geo-content.json", json.dumps(geo_content, indent=2))

        return {
            'agent': self.name,
            'status': 'success',
            'files': [schema_file, geo_file],
            'metrics': {
                'schema_entities': len(schema),
                'geo_tokens': geo_tokens,
                'provider': geo_provider
            }
        }
