"""
Code validation and security scanning.

Validates generated code for:
- Syntax correctness
- Security vulnerabilities
- Best practices
"""

import re
from typing import Any, Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    """Single validation issue."""
    severity: str  # error, warning, info
    code: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None


@dataclass
class ValidationResult:
    """Complete validation result."""
    valid: bool
    language: str
    issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class CodeValidator:
    """Validates code syntax and structure."""
    
    def validate_javascript(self, code: str) -> ValidationResult:
        """Validate JavaScript code."""
        issues = []
        
        # Basic syntax checks
        open_braces = code.count('{') - code.count('}')
        open_parens = code.count('(') - code.count(')')
        open_brackets = code.count('[') - code.count(']')
        
        if open_braces != 0:
            issues.append(ValidationIssue(
                severity='error',
                code='SYNTAX001',
                message=f'Unmatched braces ({open_braces})'
            ))
        if open_parens != 0:
            issues.append(ValidationIssue(
                severity='error',
                code='SYNTAX002',
                message=f'Unmatched parentheses ({open_parens})'
            ))
        if open_brackets != 0:
            issues.append(ValidationIssue(
                severity='error',
                code='SYNTAX003',
                message=f'Unmatched brackets ({open_brackets})'
            ))
        
        # Check for common JS issues
        if ';;' in code:
            issues.append(ValidationIssue(
                severity='warning',
                code='STYLE001',
                message='Double semicolons found'
            ))
        
        # Calculate metrics (limit lines to prevent memory issues with large files)
        max_lines = 10000
        lines = code.split('\n')[:max_lines]
        metrics = {
            'lines': len(lines),
            'non_empty_lines': len([l for l in lines if l.strip()]),
            'functions': min(code.count('function') + code.count('=>'), 1000),
        }
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == 'error']) == 0,
            language='javascript',
            issues=issues,
            metrics=metrics
        )
    
    def validate_css(self, code: str) -> ValidationResult:
        """Validate CSS code."""
        issues = []
        
        # Check braces
        open_braces = code.count('{') - code.count('}')
        if open_braces != 0:
            issues.append(ValidationIssue(
                severity='error',
                code='CSS001',
                message=f'Unmatched braces ({open_braces})'
            ))
        
        # Check for common CSS issues
        if ';}' in code:
            issues.append(ValidationIssue(
                severity='warning',
                code='CSS002',
                message='Unnecessary semicolon before closing brace'
            ))
        
        # Metrics
        selectors = len([l for l in code.split('\n') if '{' in l])
        metrics = {
            'lines': len(code.split('\n')),
            'selectors': selectors,
            'rules': code.count(';'),
        }
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == 'error']) == 0,
            language='css',
            issues=issues,
            metrics=metrics
        )
    
    def validate_html(self, code: str) -> ValidationResult:
        """Validate HTML code."""
        issues = []
        
        # Basic tag balance check (very simplified)
        common_tags = ['div', 'span', 'p', 'a', 'section', 'article']
        for tag in common_tags:
            opens = len(re.findall(rf'<{tag}[\s>]', code, re.IGNORECASE))
            closes = len(re.findall(rf'</{tag}>', code, re.IGNORECASE))
            self_closing = len(re.findall(rf'<{tag}[^>]*/>', code, re.IGNORECASE))
            
            if opens > closes + self_closing:
                issues.append(ValidationIssue(
                    severity='warning',
                    code='HTML001',
                    message=f'Potentially unclosed <{tag}> tags'
                ))
        
        # Check for doctype
        if '<!DOCTYPE' not in code.upper() and '<html' in code.lower():
            issues.append(ValidationIssue(
                severity='info',
                code='HTML002',
                message='Missing DOCTYPE declaration'
            ))
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == 'error']) == 0,
            language='html',
            issues=issues,
            metrics={'lines': len(code.split('\n'))}
        )


class SecurityScanner:
    """Scans code for security vulnerabilities."""
    
    # Dangerous patterns by language
    DANGEROUS_PATTERNS = {
        'javascript': {
            'eval_usage': re.compile(r'\beval\s*\(', re.IGNORECASE),
            'inner_html': re.compile(r'\.innerHTML\s*=', re.IGNORECASE),
            'document_write': re.compile(r'document\.write\s*\(', re.IGNORECASE),
            'outer_html': re.compile(r'\.outerHTML\s*=', re.IGNORECASE),
            'insert_adjacent_html': re.compile(r'\.insertAdjacentHTML\s*\(', re.IGNORECASE),
            'set_timeout_string': re.compile(r'setTimeout\s*\(\s*["\']', re.IGNORECASE),
            'set_interval_string': re.compile(r'setInterval\s*\(\s*["\']', re.IGNORECASE),
            'function_constructor': re.compile(r'new\s+Function\s*\(', re.IGNORECASE),
        },
        'python': {
            'eval_usage': re.compile(r'\beval\s*\(', re.IGNORECASE),
            'exec_usage': re.compile(r'\bexec\s*\(', re.IGNORECASE),
            'os_system': re.compile(r'os\.system\s*\(', re.IGNORECASE),
            'subprocess_shell': re.compile(r'subprocess\.\w+\s*\([^)]*shell\s*=\s*True', re.IGNORECASE),
            'pickle_load': re.compile(r'pickle\.load', re.IGNORECASE),
            'yaml_load': re.compile(r'yaml\.load\s*\([^)]*\)(?!\s*\s*Loader\s*=\s*yaml\.SafeLoader)', re.IGNORECASE),
        },
        'css': {
            'expression': re.compile(r'expression\s*\(', re.IGNORECASE),
            'javascript_protocol': re.compile(r'javascript:', re.IGNORECASE),
            'behavior': re.compile(r'behavior\s*:\s*url', re.IGNORECASE),
        },
        'html': {
            'inline_event': re.compile(r'\s(on\w+)\s*=', re.IGNORECASE),
            'javascript_scheme': re.compile(r'href\s*=\s*["\']javascript:', re.IGNORECASE),
        }
    }
    
    SEVERITY = {
        'eval_usage': 'critical',
        'inner_html': 'high',
        'document_write': 'high',
        'outer_html': 'high',
        'insert_adjacent_html': 'high',
        'set_timeout_string': 'medium',
        'set_interval_string': 'medium',
        'function_constructor': 'high',
        'exec_usage': 'critical',
        'os_system': 'high',
        'subprocess_shell': 'high',
        'pickle_load': 'high',
        'yaml_load': 'medium',
        'expression': 'critical',
        'javascript_protocol': 'critical',
        'behavior': 'high',
        'inline_event': 'low',
        'javascript_scheme': 'high',
    }
    
    def scan(self, code: str, language: str) -> List[ValidationIssue]:
        """Scan code for security issues."""
        issues = []
        patterns = self.DANGEROUS_PATTERNS.get(language, {})
        
        for pattern_name, pattern in patterns.items():
            matches = list(pattern.finditer(code))
            if matches:
                severity = self.SEVERITY.get(pattern_name, 'medium')
                for match in matches:
                    # Get line number
                    line = code[:match.start()].count('\n') + 1
                    
                    issues.append(ValidationIssue(
                        severity=severity,
                        code=f'SEC_{pattern_name.upper()}',
                        message=f'Dangerous pattern detected: {pattern_name}',
                        line=line
                    ))
        
        return issues
    
    def scan_javascript(self, code: str) -> ValidationResult:
        """Scan JavaScript for security issues."""
        issues = self.scan(code, 'javascript')
        
        # Additional JS-specific checks
        if 'JSON.parse(' in code and 'try' not in code:
            issues.append(ValidationIssue(
                severity='warning',
                code='SEC_JSON_PARSE',
                message='JSON.parse without try-catch may crash on invalid JSON'
            ))
        
        critical = len([i for i in issues if i.severity == 'critical'])
        high = len([i for i in issues if i.severity == 'high'])
        
        return ValidationResult(
            valid=critical == 0,  # Critical issues make it invalid
            language='javascript',
            issues=issues,
            metrics={
                'critical_issues': critical,
                'high_issues': high,
                'total_issues': len(issues)
            }
        )
    
    def scan_css(self, code: str) -> ValidationResult:
        """Scan CSS for security issues."""
        issues = self.scan(code, 'css')
        
        critical = len([i for i in issues if i.severity == 'critical'])
        
        return ValidationResult(
            valid=critical == 0,
            language='css',
            issues=issues,
            metrics={'critical_issues': critical}
        )
    
    def scan_html(self, code: str) -> ValidationResult:
        """Scan HTML for security issues."""
        issues = self.scan(code, 'html')
        
        # Check for inline scripts
        if '<script>' in code.lower():
            issues.append(ValidationIssue(
                severity='info',
                code='SEC_INLINE_SCRIPT',
                message='Inline script detected - consider external file for CSP compliance'
            ))
        
        high = len([i for i in issues if i.severity in ('high', 'critical')])
        
        return ValidationResult(
            valid=high == 0,
            language='html',
            issues=issues,
            metrics={'high_severity_issues': high}
        )
    
    def generate_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate security scan report."""
        total_issues = sum(len(r.issues) for r in results)
        critical = sum(1 for r in results for i in r.issues if i.severity == 'critical')
        high = sum(1 for r in results for i in r.issues if i.severity == 'high')
        
        return {
            'summary': {
                'files_scanned': len(results),
                'total_issues': total_issues,
                'critical': critical,
                'high': high,
                'medium': sum(1 for r in results for i in r.issues if i.severity == 'medium'),
                'low': sum(1 for r in results for i in r.issues if i.severity == 'low'),
                'passed': all(r.valid for r in results)
            },
            'files': [
                {
                    'language': r.language,
                    'valid': r.valid,
                    'issue_count': len(r.issues),
                    'issues': [
                        {
                            'severity': i.severity,
                            'code': i.code,
                            'message': i.message,
                            'line': i.line
                        }
                        for i in r.issues
                    ]
                }
                for r in results
            ]
        }
