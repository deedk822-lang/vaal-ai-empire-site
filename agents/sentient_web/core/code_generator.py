"""
Real code generation with file writing and validation.

Generates actual CSS, JavaScript, and HTML files - not just dictionaries.
Implements +AAA standards for code quality and security.
"""

import os
import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Import the unified CodeValidator from validator.py
from .validator import CodeValidator, ValidationResult, ValidationIssue


@dataclass
class GeneratedFile:
    """Represents a generated file with metadata."""
    path: str
    content: str
    language: str
    checksum: str = field(init=False)
    size_bytes: int = field(init=False)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validation_status: str = "pending"
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.checksum = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        self.size_bytes = len(self.content.encode('utf-8'))


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    files: List[GeneratedFile] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class CodeGenerator(ABC):
    """Abstract base class for code generators."""
    
    def __init__(self, output_dir: str, validator: Optional[CodeValidator] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validator = validator or CodeValidator()
        self.generated_files: List[GeneratedFile] = []
    
    @abstractmethod
    async def generate(self, spec: Dict[str, Any]) -> GenerationResult:
        """Generate code based on specification."""
        pass
    
    def write_file(self, filename: str, content: str, language: str) -> GeneratedFile:
        """Write file to disk and return metadata."""
        filepath = self.output_dir / filename
        
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create metadata
        gen_file = GeneratedFile(
            path=str(filepath.relative_to(self.output_dir)),
            content=content,
            language=language
        )
        
        # Validate using the unified CodeValidator
        if language == 'javascript':
            result = self.validator.validate_javascript(content)
        elif language == 'css':
            result = self.validator.validate_css(content)
        elif language == 'html':
            result = self.validator.validate_html(content)
        else:
            result = ValidationResult(valid=True, language=language, issues=[])
        
        gen_file.validation_status = 'valid' if result.valid else 'invalid'
        gen_file.validation_errors = [i.message for i in result.issues]
        
        self.generated_files.append(gen_file)
        return gen_file
    
    def get_generation_report(self) -> Dict[str, Any]:
        """Get report of all generated files."""
        total = len(self.generated_files)
        valid = sum(1 for f in self.generated_files if f.validation_status == 'valid')
        invalid = total - valid
        total_size = sum(f.size_bytes for f in self.generated_files)
        
        return {
            'total_files': total,
            'valid_files': valid,
            'invalid_files': invalid,
            'total_size_bytes': total_size,
            'files': [
                {
                    'path': f.path,
                    'language': f.language,
                    'size': f.size_bytes,
                    'checksum': f.checksum,
                    'validation': f.validation_status,
                    'errors': f.validation_errors
                }
                for f in self.generated_files
            ]
        }


class CSSGenerator(CodeGenerator):
    """Generates production-ready CSS files."""
    
    LIQUID_GLASS_TEMPLATE = '''/* 
 * Liquid Glass Design System
 * Generated: {timestamp}
 * Version: 2026.1.0
 */

:root {{
  --glass-bg: rgba(255, 255, 255, 0.1);
  --glass-border: rgba(255, 255, 255, 0.2);
  --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
  --glass-blur: blur(20px) saturate(180%);
}}

/* Base Glass Card */
.glass-card {{
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.3s ease;
}}

.glass-card:hover {{
  transform: translateY(-4px);
  box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
}}

/* Liquid Button */
.liquid-button {{
  position: relative;
  padding: 12px 24px;
  background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.05));
  border: 1px solid var(--glass-border);
  border-radius: 50px;
  color: inherit;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}

.liquid-button::before {{
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}}

.liquid-button:hover::before {{
  width: 300px;
  height: 300px;
}}

/* Ambient Surface */
.ambient-surface {{
  background: linear-gradient(
    135deg, 
    var(--ambient-start, #667eea), 
    var(--ambient-end, #764ba2)
  );
  background-size: 400% 400%;
  animation: ambient-shift 20s ease infinite;
}}

@keyframes ambient-shift {{
  0% {{ background-position: 0% 50%; }}
  50% {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* Performance Optimizations */
.gpu-accelerated {{
  transform: translateZ(0);
  will-change: transform;
  backface-visibility: hidden;
}}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {{
  .glass-card,
  .liquid-button,
  .ambient-surface {{
    transition: none;
    animation: none;
  }}
}}

/* High Contrast Mode */
@media (prefers-contrast: high) {{
  .glass-card {{
    border-width: 2px;
    border-color: currentColor;
  }}
}}
'''
    
    async def generate(self, spec: Dict[str, Any]) -> GenerationResult:
        """Generate CSS files based on specification."""
        files = []
        errors = []
        
        try:
            # Generate main liquid glass CSS
            timestamp = datetime.now().isoformat()
            css_content = self.LIQUID_GLASS_TEMPLATE.format(timestamp=timestamp)
            
            # Add custom components from spec
            components = spec.get('components', [])
            for component in components:
                css_content += self._generate_component_css(component)
            
            # Write file
            file = self.write_file('liquid-glass.css', css_content, 'css')
            files.append(file)
            
            # Generate responsive variants
            responsive_css = self._generate_responsive_css()
            file = self.write_file('liquid-glass.responsive.css', responsive_css, 'css')
            files.append(file)
            
            # Generate dark mode
            dark_css = self._generate_dark_mode_css()
            file = self.write_file('liquid-glass.dark.css', dark_css, 'css')
            files.append(file)
            
        except Exception as e:
            errors.append(f"CSS generation failed: {e}")
        
        return GenerationResult(
            success=len(errors) == 0,
            files=files,
            errors=errors,
            metrics=self.get_generation_report()
        )
    
    def _generate_component_css(self, component: Dict[str, Any]) -> str:
        """Generate CSS for a specific component."""
        name = component.get('name', 'component')
        selector = f".glass-{name.lower()}"
        props = component.get('css_props', {})
        
        css_lines = [f"\n/* Component: {name} */", f"{selector} {{"]
        for prop, value in props.items():
            css_lines.append(f"  {prop}: {value};")
        css_lines.append("}")
        
        return '\n'.join(css_lines)
    
    def _generate_responsive_css(self) -> str:
        """Generate responsive breakpoints."""
        return '''
/* Responsive Breakpoints */
@media (max-width: 768px) {
  .glass-card {
    border-radius: 12px;
  }
}

@media (max-width: 480px) {
  .glass-card {
    border-radius: 8px;
    backdrop-filter: blur(10px) saturate(150%);
  }
}
'''
    
    def _generate_dark_mode_css(self) -> str:
        """Generate dark mode overrides."""
        return '''
/* Dark Mode */
@media (prefers-color-scheme: dark) {
  :root {
    --glass-bg: rgba(0, 0, 0, 0.3);
    --glass-border: rgba(255, 255, 255, 0.1);
  }
}
'''


class JSGenerator(CodeGenerator):
    """Generates production-ready JavaScript files."""
    
    HAPTIC_FEEDBACK_TEMPLATE = '''/**
 * Haptic Feedback System
 * Generated: {{timestamp}}
 * @class HapticFeedback
 */

class HapticFeedback {{
  constructor(options = {{}}) {{
    this.enabled = 'vibrate' in navigator && options.enabled !== false;
    this.defaultPattern = options.pattern || [50];
    this.isSupported = this._checkSupport();
    
    if (!this.isSupported) {{
      console.warn('Haptic feedback not supported on this device');
    }}
  }}

  _checkSupport() {{
    return 'vibrate' in navigator && 
           !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }}

  /**
   * Trigger haptic feedback
   * @param {number|number[]} pattern - Vibration pattern
   * @returns {boolean} Success status
   */
  trigger(pattern = this.defaultPattern) {{
    if (!this.enabled || !this.isSupported) {{
      return false;
    }}

    try {{
      navigator.vibrate(pattern);
      return true;
    }} catch (error) {{
      console.error('Haptic feedback failed:', error);
      return false;
    }}
  }}

  /**
   * Predefined feedback patterns
   */
  static get Patterns() {{
    return {{
      TAP: [50],
      DOUBLE_TAP: [50, 100, 50],
      SUCCESS: [100, 50, 100],
      ERROR: [200, 100, 200],
      WARNING: [100, 50, 100, 50, 100],
      SELECTION: [30]
    }};
  }}

  /**
   * Enable haptic feedback on all interactive elements
   */
  static initGlobal() {{
    const haptic = new HapticFeedback();
    
    document.querySelectorAll('button, .liquid-button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        haptic.trigger(HapticFeedback.Patterns.TAP);
      }});
    }});

    return haptic;
  }}
}}

// Auto-initialize if not in test environment
if (typeof module === 'undefined' && typeof window !== 'undefined') {{
  window.HapticFeedback = HapticFeedback;
  
  // Initialize on DOM ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => HapticFeedback.initGlobal());
  }} else {{
    HapticFeedback.initGlobal();
  }}
}}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {{
  module.exports = {{ HapticFeedback }};
}}
'''
    
    def _generate_haptic_feedback(self) -> str:
        """Generate haptic feedback module."""
        timestamp = datetime.now().isoformat()
        return f"""/**
 * Haptic Feedback System
 * Generated: {timestamp}
 * @class HapticFeedback
 */

class HapticFeedback {{
  constructor(options = {{}}) {{
    this.enabled = 'vibrate' in navigator && options.enabled !== false;
    this.defaultPattern = options.pattern || [50];
    this.isSupported = this._checkSupport();
    
    if (!this.isSupported) {{
      console.warn('Haptic feedback not supported on this device');
    }}
  }}

  _checkSupport() {{
    return 'vibrate' in navigator && 
           !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }}

  /**
   * Trigger haptic feedback
   * @param {{number|number[]}} pattern - Vibration pattern
   * @returns {{boolean}} Success status
   */
  trigger(pattern = this.defaultPattern) {{
    if (!this.enabled || !this.isSupported) {{
      return false;
    }}

    try {{
      navigator.vibrate(pattern);
      return true;
    }} catch (error) {{
      console.error('Haptic feedback failed:', error);
      return false;
    }}
  }}

  /**
   * Predefined feedback patterns
   */
  static get Patterns() {{
    return {{
      TAP: [50],
      DOUBLE_TAP: [50, 100, 50],
      SUCCESS: [100, 50, 100],
      ERROR: [200, 100, 200],
      WARNING: [100, 50, 100, 50, 100],
      SELECTION: [30]
    }};
  }}

  /**
   * Enable haptic feedback on all interactive elements
   */
  static initGlobal() {{
    const haptic = new HapticFeedback();
    
    document.querySelectorAll('button, .liquid-button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        haptic.trigger(HapticFeedback.Patterns.TAP);
      }});
    }});

    return haptic;
  }}
}}

// Auto-initialize if not in test environment
if (typeof module === 'undefined' && typeof window !== 'undefined') {{
  window.HapticFeedback = HapticFeedback;
  
  // Initialize on DOM ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => HapticFeedback.initGlobal());
  }} else {{
    HapticFeedback.initGlobal();
  }}
}}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {{
  module.exports = {{ HapticFeedback }};
}}
"""
    
    async def generate(self, spec: Dict[str, Any]) -> GenerationResult:
        """Generate JavaScript files based on specification."""
        files = []
        errors = []
        
        try:
            # Generate haptic feedback module
            haptic_js = self._generate_haptic_feedback()
            file = self.write_file('haptic-feedback.js', haptic_js, 'javascript')
            files.append(file)
            
            # Generate glass interaction module
            glass_js = self._generate_glass_interactions()
            file = self.write_file('glass-interactions.js', glass_js, 'javascript')
            files.append(file)
            
            # Generate performance observer
            perf_js = self._generate_performance_observer()
            file = self.write_file('performance-monitor.js', perf_js, 'javascript')
            files.append(file)
            
        except Exception as e:
            errors.append(f"JavaScript generation failed: {e}")
        
        return GenerationResult(
            success=len(errors) == 0,
            files=files,
            errors=errors,
            metrics=self.get_generation_report()
        )
    
    def _generate_glass_interactions(self) -> str:
        """Generate glass card interaction handlers."""
        return '''/**
 * Glass Card Interactions
 * Handles mouse/tilt effects for glassmorphism components
 */

class GlassInteractions {
  constructor() {
    this.cards = document.querySelectorAll('.glass-card');
    this.init();
  }

  init() {
    this.cards.forEach(card => {
      // Tilt effect on mouse move
      card.addEventListener('mousemove', this.handleMouseMove.bind(this));
      card.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
      
      // Accessibility: keyboard focus effect
      card.addEventListener('focus', this.handleFocus.bind(this));
      card.addEventListener('blur', this.handleBlur.bind(this));
      
      // Make focusable if not already
      if (!card.hasAttribute('tabindex')) {
        card.setAttribute('tabindex', '0');
      }
    });
  }

  handleMouseMove(e) {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    const rotateX = (y - centerY) / 20;
    const rotateY = (centerX - x) / 20;
    
    // Use requestAnimationFrame for performance
    requestAnimationFrame(() => {
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
    });
  }

  handleMouseLeave(e) {
    const card = e.currentTarget;
    requestAnimationFrame(() => {
      card.style.transform = '';
    });
  }

  handleFocus(e) {
    e.currentTarget.classList.add('glass-card--focused');
  }

  handleBlur(e) {
    e.currentTarget.classList.remove('glass-card--focused');
  }
}

// Initialize
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new GlassInteractions());
  } else {
    new GlassInteractions();
  }
}
'''
    
    def _generate_performance_observer(self) -> str:
        """Generate Core Web Vitals monitoring."""
        return '''/**
 * Core Web Vitals Monitor
 * Tracks LCP, INP, CLS for Digital Preeminence 2026 standards
 */

class CWMonitor {
  constructor(options = {}) {
    this.thresholds = {
      LCP: { good: 2500, poor: 4000 },
      INP: { good: 200, poor: 500 },
      CLS: { good: 0.1, poor: 0.25 },
      ...options.thresholds
    };
    this.callbacks = [];
    this.metrics = {};
    
    this.init();
  }

  init() {
    // LCP
    this.observeLCP();
    // CLS
    this.observeCLS();
    // INP (if supported)
    if ('PerformanceEventTiming' in window) {
      this.observeINP();
    }
    // FCP
    this.observeFCP();
  }

  observeLCP() {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      this.metrics.LCP = lastEntry.startTime;
      this.report('LCP', this.metrics.LCP);
    }).observe({ entryTypes: ['largest-contentful-paint'] });
  }

  observeCLS() {
    let clsValue = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      }
      this.metrics.CLS = clsValue;
      this.report('CLS', this.metrics.CLS);
    }).observe({ entryTypes: ['layout-shift'] });
  }

  observeINP() {
    let maxDuration = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > maxDuration) {
          maxDuration = entry.duration;
          this.metrics.INP = maxDuration;
          this.report('INP', this.metrics.INP);
        }
      }
    }).observe({ entryTypes: ['event'] });
  }

  observeFCP() {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length > 0) {
        this.metrics.FCP = entries[0].startTime;
        this.report('FCP', this.metrics.FCP);
      }
    }).observe({ entryTypes: ['paint'] });
  }

  report(metric, value) {
    const status = this.getStatus(metric, value);
    console.log(`[CWV] ${metric}: ${value} (${status})`);
    
    this.callbacks.forEach(cb => cb(metric, value, status));
  }

  getStatus(metric, value) {
    const t = this.thresholds[metric];
    if (!t) return 'unknown';
    
    if (value <= t.good) return 'good';
    if (value >= t.poor) return 'poor';
    return 'needs-improvement';
  }

  onMetric(callback) {
    this.callbacks.push(callback);
  }

  getMetrics() {
    return { ...this.metrics };
  }
}

// Auto-initialize
if (typeof window !== 'undefined') {
  window.cwvMonitor = new CWMonitor();
}
'''
