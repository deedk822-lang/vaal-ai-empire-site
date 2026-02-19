#!/usr/bin/env node
/**
 * 🤖 DIAGNOSTIC RUNNER - MASTER ORCHESTRATOR
 * Coordinates all validation agents
 * 
 * Usage:
 *   node server/agents/diagnostic-runner.js
 *   npm run diagnose (add to package.json)
 */

require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const colors = require('colors');

// Import all agents
const AuthValidator = require('./auth-validator');
const SecurityAuditor = require('./security-auditor');

class DiagnosticRunner {
    constructor() {
        this.startTime = Date.now();
    }

    printBanner() {
        console.clear();
        console.log('\n' + '═'.repeat(80).cyan);
        console.log('🤖  VAAL AI EMPIRE - AUTONOMOUS DIAGNOSTIC SYSTEM'.cyan.bold);
        console.log('    PhD-Level Backend Validation'.cyan);
        console.log('═'.repeat(80).cyan);
        console.log('');
    }

    async run() {
        this.printBanner();
        
        const results = {
            auth: null,
            security: null,
            overall: 'PASS'
        };
        
        try {
            // Run Authentication Validator
            console.log('\n' + '┌'.concat('─'.repeat(78), '┐').yellow);
            console.log('│ 1/2 Authentication Validator'.yellow + ' '.repeat(48) + '│'.yellow);
            console.log('└'.concat('─'.repeat(78), '┘').yellow);
            
            const authValidator = new AuthValidator();
            results.auth = await authValidator.runAllTests();
            
            // Run Security Auditor
            console.log('\n' + '┌'.concat('─'.repeat(78), '┐').yellow);
            console.log('│ 2/2 Security Auditor'.yellow + ' '.repeat(57) + '│'.yellow);
            console.log('└'.concat('─'.repeat(78), '┘').yellow);
            
            const securityAuditor = new SecurityAuditor();
            results.security = await securityAuditor.runAllAudits();
            
            // Generate overall report
            this.generateReport(results);
            
        } catch (error) {
            console.error('\n🚨 DIAGNOSTIC SYSTEM FAILURE:'.red.bold, error.message);
            process.exit(1);
        }
    }

    generateReport(results) {
        console.log('\n' + '═'.repeat(80).magenta);
        console.log('📊 COMPREHENSIVE DIAGNOSTIC REPORT'.magenta.bold);
        console.log('═'.repeat(80).magenta);
        
        // Authentication Results
        console.log('\n🔐 Authentication System:'.cyan.bold);
        console.log(`   ✅ Passed: ${results.auth.passed}`);
        console.log(`   ❌ Failed: ${results.auth.failed}`);
        console.log(`   ⚠️  Warnings: ${results.auth.warnings}`);
        
        // Security Results
        console.log('\n🛡️  Security Audit:'.cyan.bold);
        console.log(`   🚨 Critical: ${results.security.critical}`);
        console.log(`   ❌ High: ${results.security.high}`);
        console.log(`   ⚠️  Medium: ${results.security.medium}`);
        console.log(`   ℹ️  Low: ${results.security.low}`);
        
        // Overall Status
        const hasFailures = results.auth.failed > 0 || results.security.critical > 0 || results.security.high > 0;
        const hasWarnings = results.auth.warnings > 0 || results.security.medium > 0;
        
        console.log('\n' + '─'.repeat(80));
        
        if (hasFailures) {
            console.log('\n🚨 OVERALL STATUS: FAILED'.red.bold);
            console.log('   Critical issues detected. Backend NOT ready for production.'.red);
            console.log('   Review error logs and cookbooks above for fixes.'.red);
        } else if (hasWarnings) {
            console.log('\n⚠️  OVERALL STATUS: PASS WITH WARNINGS'.yellow.bold);
            console.log('   Backend functional but has minor issues.'.yellow);
            console.log('   Review warnings before production deployment.'.yellow);
        } else {
            console.log('\n🎉 OVERALL STATUS: PERFECT'.green.bold);
            console.log('   All systems operational. Backend ready for production!'.green);
        }
        
        // Execution time
        const duration = ((Date.now() - this.startTime) / 1000).toFixed(2);
        console.log(`\n⏱️  Diagnostic completed in ${duration}s`);
        
        console.log('\n' + '═'.repeat(80).magenta);
        
        // Exit code
        if (hasFailures) {
            process.exit(1);
        } else {
            process.exit(0);
        }
    }
}

// Run diagnostics
const runner = new DiagnosticRunner();
runner.run();

