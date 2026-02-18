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
    
    # Fallback templates when LLM is unavailable
    FALLBACK_CSS = '''/* Liquid Glass Design System - Fallback */
:root {
  --glass-bg: rgba(255, 255, 255, 0.1);
  --glass-border: rgba(255, 255, 255, 0.2);
  --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}

.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
}
'''

    FALLBACK_JS = '''// Glass Interactions - Fallback
class GlassInteractions {
  constructor() {
    this.cards = document.querySelectorAll('.glass-card');
    this.init();
  }
  init() {
    this.cards.forEach(card => {
      card.addEventListener('mousemove', this.handleMouseMove.bind(this));
      card.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
    });
  }
  handleMouseMove(e) {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.transform = `perspective(1000px) rotateX(${(y - rect.height/2)/20}deg) rotateY(${-(x - rect.width/2)/20}deg)`;
  }
  handleMouseLeave(e) {
    e.currentTarget.style.transform = '';
  }
}
'''

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
        
        css_content = self.FALLBACK_CSS
        css_provider = "fallback"
        css_tokens = 0
        
        if self.llm:
            css_response = await self.llm.generate(
                prompt=css_prompt,
                system_message="You are an expert CSS developer specializing in modern glassmorphism UI.",
                temperature=0.7
            )
            
            if css_response.success:
                css_content = css_response.content
                css_provider = css_response.provider.value
                css_tokens = css_response.tokens_used
        else:
            self.log("⚠️  No LLM available, using fallback CSS template")
        
        css_file = self.write_file("liquid-glass.css", css_content)
        
        # Generate JS interactions
        js_prompt = """Generate JavaScript for glass card interactions:

Requirements:
1. 3D tilt effect on mouse move
2. Haptic feedback on click (if supported)
3. Keyboard accessibility (focus states)
4. Touch support for mobile
5. Use requestAnimationFrame for performance

Output valid JavaScript only."""
        
        js_content = self.FALLBACK_JS
        js_provider = "fallback"
        js_tokens = 0
        
        if self.llm:
            js_response = await self.llm.generate(
                prompt=js_prompt,
                system_message="You are a frontend JavaScript expert.",
                temperature=0.7
            )
            
            if js_response.success:
                js_content = js_response.content
                js_provider = js_response.provider.value
                js_tokens = js_response.tokens_used
        else:
            self.log("⚠️  No LLM available, using fallback JS template")
        
        js_file = self.write_file("glass-interactions.js", js_content)
        
        # Calculate metrics
        css_lines = len(css_content.split('\n'))
        js_lines = len(js_content.split('\n'))
        
        fallback_used = css_provider == "fallback" or js_provider == "fallback"
        
        return {
            'agent': self.name,
            'status': 'success',
            'files': [css_file, js_file],
            'metrics': {
                'css_lines': css_lines,
                'js_lines': js_lines,
                'css_tokens': css_tokens,
                'js_tokens': js_tokens,
                'fallback_used': fallback_used,
                'providers': [css_provider, js_provider]
            }
        }
