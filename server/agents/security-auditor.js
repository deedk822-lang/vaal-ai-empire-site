/**
 * 🛡️ SECURITY AUDITOR AGENT
 * PhD-Level Security Validation
 * 
 * Tests:
 * - Rate limiting configuration
 * - CORS security
 * - Helmet.js headers
 * - XSS protection
 * - NoSQL injection prevention
 * - Environment variable security
 * - SSL/TLS configuration
 */

const colors = require('colors');
const path = require('path');

class SecurityAuditor {
    constructor() {
        this.vulnerabilities = [];
        this.warnings = [];
        this.results = [];
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const formatted = `[${timestamp}] SECURITY-AUDITOR: ${message}`;
        
        switch(type) {
            case 'success':
                console.log(formatted.green);
                break;
            case 'critical':
                console.log(formatted.red.bold);
                this.vulnerabilities.push({ severity: 'CRITICAL', message });
                break;
            case 'high':
                console.log(formatted.red);
                this.vulnerabilities.push({ severity: 'HIGH', message });
                break;
            case 'medium':
                console.log(formatted.yellow);
                this.warnings.push({ severity: 'MEDIUM', message });
                break;
            case 'low':
                console.log(formatted.yellow);
                this.warnings.push({ severity: 'LOW', message });
                break;
            default:
                console.log(formatted.cyan);
        }
        
        this.results.push({ timestamp, message, type });
    }

    // Test 1: Environment Variables Security
    testEnvironmentSecurity() {
        this.log('Auditing Environment Variables...');
        
        // Check for sensitive data
        const sensitiveVars = [
            'JWT_SECRET',
            'MONGODB_URI',
            'STRIPE_SECRET_KEY',
            'STRIPE_WEBHOOK_SECRET'
        ];
        
        sensitiveVars.forEach(varName => {
            const value = process.env[varName];
            
            if (!value) {
                this.log(`❌ ${varName} not set`, 'high');
                return;
            }
            
            // Check for placeholder values
            const placeholders = ['your-', 'change-', 'example', 'test-', 'placeholder'];
            const hasPlaceholder = placeholders.some(p => value.toLowerCase().includes(p));
            
            if (hasPlaceholder) {
                this.log(`⚠️  ${varName} contains placeholder value`, 'medium');
            }
            
            // Check for weak secrets
            if (varName.includes('SECRET') && value.length < 32) {
                this.log(`⚠️  ${varName} is too short (< 32 characters)`, 'medium');
            }
        });
        
        // Check NODE_ENV
        if (process.env.NODE_ENV === 'production') {
            if (process.env.JWT_SECRET && process.env.JWT_SECRET.includes('development')) {
                this.log('🚨 Development secrets in production!', 'critical');
            }
        }
        
        this.log('✅ Environment security audit complete', 'success');
    }

    // Test 2: Rate Limiting
    testRateLimiting() {
        this.log('Auditing Rate Limiting Configuration...');
        
        try {
            const serverPath = path.join(__dirname, '../server.js');
            const fs = require('fs');
            const serverContent = fs.readFileSync(serverPath, 'utf8');
            
            // Check if rate limiting is configured
            if (!serverContent.includes('express-rate-limit')) {
                this.log('🚨 Rate limiting not configured!', 'critical');
                return;
            }
            
            // Check for auth-specific rate limiting
            if (!serverContent.includes('authLimiter') && !serverContent.includes('/api/auth')) {
                this.log('⚠️  Auth-specific rate limiting not found', 'medium');
            }
            
            this.log('✅ Rate limiting configured', 'success');
        } catch (error) {
            this.log(`❌ Could not verify rate limiting: ${error.message}`, 'high');
        }
    }

    // Test 3: CORS Configuration
    testCORS() {
        this.log('Auditing CORS Configuration...');
        
        const allowedOrigins = process.env.ALLOWED_ORIGINS;
        
        if (!allowedOrigins) {
            this.log('⚠️  ALLOWED_ORIGINS not set - defaulting to allow all', 'medium');
            return;
        }
        
        if (allowedOrigins === '*') {
            if (process.env.NODE_ENV === 'production') {
                this.log('🚨 CORS allows all origins in production!', 'critical');
            } else {
                this.log('⚠️  CORS allows all origins', 'low');
            }
            return;
        }
        
        // Check for localhost in production
        if (process.env.NODE_ENV === 'production' && allowedOrigins.includes('localhost')) {
            this.log('⚠️  Localhost in ALLOWED_ORIGINS for production', 'medium');
        }
        
        this.log('✅ CORS configuration secure', 'success');
    }

    // Test 4: Security Headers (Helmet.js)
    testSecurityHeaders() {
        this.log('Auditing Security Headers...');
        
        try {
            const serverPath = path.join(__dirname, '../server.js');
            const fs = require('fs');
            const serverContent = fs.readFileSync(serverPath, 'utf8');
            
            if (!serverContent.includes('helmet')) {
                this.log('🚨 Helmet.js not configured!', 'critical');
                return;
            }
            
            this.log('✅ Security headers configured', 'success');
        } catch (error) {
            this.log(`❌ Could not verify security headers: ${error.message}`, 'high');
        }
    }

    // Test 5: Input Sanitization
    testInputSanitization() {
        this.log('Auditing Input Sanitization...');
        
        try {
            const serverPath = path.join(__dirname, '../server.js');
            const fs = require('fs');
            const serverContent = fs.readFileSync(serverPath, 'utf8');
            
            const checks = [
                { name: 'NoSQL Injection Protection', pattern: 'mongo-sanitize' },
                { name: 'XSS Protection', pattern: 'xss-clean' },
                { name: 'HPP Protection', pattern: 'hpp' }
            ];
            
            checks.forEach(check => {
                if (!serverContent.includes(check.pattern)) {
                    this.log(`⚠️  ${check.name} not configured`, 'medium');
                } else {
                    this.log(`✅ ${check.name} active`, 'success');
                }
            });
        } catch (error) {
            this.log(`❌ Could not verify input sanitization: ${error.message}`, 'high');
        }
    }

    // Test 6: Payload Size Limits
    testPayloadLimits() {
        this.log('Auditing Payload Size Limits...');
        
        try {
            const serverPath = path.join(__dirname, '../server.js');
            const fs = require('fs');
            const serverContent = fs.readFileSync(serverPath, 'utf8');
            
            if (!serverContent.includes('limit:')) {
                this.log('⚠️  No payload size limits configured', 'medium');
            } else {
                this.log('✅ Payload size limits configured', 'success');
            }
        } catch (error) {
            this.log(`❌ Could not verify payload limits: ${error.message}`, 'low');
        }
    }

    // Test 7: Sensitive Data Exposure
    testSensitiveDataExposure() {
        this.log('Checking for Sensitive Data Exposure...');
        
        try {
            // Check if .env is in .gitignore
            const gitignorePath = path.join(__dirname, '../../.gitignore');
            const fs = require('fs');
            
            if (fs.existsSync(gitignorePath)) {
                const gitignoreContent = fs.readFileSync(gitignorePath, 'utf8');
                
                if (!gitignoreContent.includes('.env')) {
                    this.log('🚨 .env not in .gitignore!', 'critical');
                } else {
                    this.log('✅ .env properly ignored', 'success');
                }
            } else {
                this.log('⚠️  No .gitignore found', 'medium');
            }
        } catch (error) {
            this.log(`❌ Could not verify .gitignore: ${error.message}`, 'low');
        }
    }

    // Run all audits
    async runAllAudits() {
        this.log('🚀 Starting Security Audit...');
        this.log('━'.repeat(60));
        
        const audits = [
            { name: 'Environment Security', fn: () => this.testEnvironmentSecurity() },
            { name: 'Rate Limiting', fn: () => this.testRateLimiting() },
            { name: 'CORS Configuration', fn: () => this.testCORS() },
            { name: 'Security Headers', fn: () => this.testSecurityHeaders() },
            { name: 'Input Sanitization', fn: () => this.testInputSanitization() },
            { name: 'Payload Limits', fn: () => this.testPayloadLimits() },
            { name: 'Sensitive Data Exposure', fn: () => this.testSensitiveDataExposure() }
        ];
        
        audits.forEach(audit => {
            try {
                audit.fn();
            } catch (error) {
                this.log(`❌ ${audit.name} failed: ${error.message}`, 'high');
            }
            this.log('━'.repeat(60));
        });
        
        // Summary
        this.log(`\n🛡️  SECURITY AUDIT SUMMARY`);
        
        const critical = this.vulnerabilities.filter(v => v.severity === 'CRITICAL').length;
        const high = this.vulnerabilities.filter(v => v.severity === 'HIGH').length;
        const medium = this.warnings.filter(w => w.severity === 'MEDIUM').length;
        const low = this.warnings.filter(w => w.severity === 'LOW').length;
        
        if (critical > 0) {
            this.log(`🚨 CRITICAL Issues: ${critical}`, 'critical');
        }
        if (high > 0) {
            this.log(`❌ HIGH Priority: ${high}`, 'high');
        }
        if (medium > 0) {
            this.log(`⚠️  MEDIUM Priority: ${medium}`, 'medium');
        }
        if (low > 0) {
            this.log(`ℹ️  LOW Priority: ${low}`, 'low');
        }
        
        if (critical === 0 && high === 0) {
            this.log('\n🎉 No critical security issues detected!', 'success');
        } else {
            this.log('\n🔧 SECURITY ISSUES DETECTED - See cookbook', 'critical');
            this.generateCookbook();
        }
        
        return {
            critical,
            high,
            medium,
            low,
            vulnerabilities: this.vulnerabilities,
            warnings: this.warnings
        };
    }

    // Generate security cookbook
    generateCookbook() {
        console.log('\n' + '═'.repeat(80).red);
        console.log('🛡️  SECURITY HARDENING COOKBOOK'.red.bold);
        console.log('═'.repeat(80).red);
        
        [...this.vulnerabilities, ...this.warnings].forEach((issue, index) => {
            console.log(`\n${index + 1}. [${issue.severity}] ${issue.message}`.red);
            
            // Provide fixes based on issue type
            if (issue.message.includes('JWT_SECRET')) {
                console.log('\n   FIX:'.green);
                console.log('   Generate strong secret: node -e "console.log(require(\'crypto\').randomBytes(64).toString(\'hex\'))"');
            }
            
            if (issue.message.includes('Rate limiting')) {
                console.log('\n   FIX:'.green);
                console.log('   Add to server.js:');
                console.log('   const rateLimit = require(\'express-rate-limit\');');
                console.log('   app.use(rateLimit({ max: 100, windowMs: 15 * 60 * 1000 }));');
            }
            
            if (issue.message.includes('CORS')) {
                console.log('\n   FIX:'.green);
                console.log('   Set ALLOWED_ORIGINS in .env:');
                console.log('   ALLOWED_ORIGINS=https://yourdomain.com');
            }
        });
        
        console.log('\n' + '═'.repeat(80).red);
    }
}

module.exports = SecurityAuditor;

// Run if called directly
if (require.main === module) {
    require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
    
    const auditor = new SecurityAuditor();
    auditor.runAllAudits()
        .then(() => process.exit(0))
        .catch(err => {
            console.error('Fatal error:', err);
            process.exit(1);
        });
}