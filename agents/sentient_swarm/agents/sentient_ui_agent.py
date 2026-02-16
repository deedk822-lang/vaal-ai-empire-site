"""
Sentient UI Agent - Generates Liquid Glass components.

Uses GLM5_API_KEY or KIMI_API_KEY to generate CSS/JS.
"""

from typing import Any, Dict
from .base_agent import BaseAgent


class SentientUIAgent(BaseAgent):
    """Generates glassmorphism UI components."""
    
    def __init__(self, llm_client=None, metrics=None, tracer=None):
        super().__init__("SentientUI", llm_client, metrics, tracer)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate liquid glass components."""
        self.log("🎨 Generating Liquid Glass components...")
        
        # Generate CSS
        css_prompt = """Generate production CSS for glassmorphism design system:

Requirements:
1. Glass cards with backdrop-filter blur(20px)
2. Liquid buttons with ripple effects
3. Ambient animated backgrounds
4. Support prefers-reduced-motion
5. GPU acceleration (transform: translateZ(0))
6. CSS custom properties for theming

Output valid CSS only."""
        
        css_response = await self.llm.generate(
            prompt=css_prompt,
            system_message="You are an expert CSS developer specializing in modern glassmorphism UI.",
            temperature=0.7
        )
        
        css_file = self.write_file("liquid-glass.css", css_response.content)
        
        # Generate JS interactions
        js_prompt = """Generate JavaScript for glass card interactions:

Requirements:
1. 3D tilt effect on mouse move
2. Haptic feedback on click (if supported)
3. Keyboard accessibility (focus states)
4. Touch support for mobile
5. Use requestAnimationFrame for performance

Output valid JavaScript only."""
        
        js_response = await self.llm.generate(
            prompt=js_prompt,
            system_message="You are a frontend JavaScript expert.",
            temperature=0.7
        )
        
        js_file = self.write_file("glass-interactions.js", js_response.content)
        
        # Calculate metrics
        css_lines = len(css_response.content.split('\n'))
        js_lines = len(js_response.content.split('\n'))
        
        fallback_used = css_response.provider.value != 'glm5' or js_response.provider.value != 'glm5'
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [css_file, js_file],
            'metrics': {
                'css_lines': css_lines,
                'js_lines': js_lines,
                'css_tokens': css_response.tokens_used,
                'js_tokens': js_response.tokens_used,
                'fallback_used': fallback_used,
                'providers': [css_response.provider.value, js_response.provider.value]
            }
        }
