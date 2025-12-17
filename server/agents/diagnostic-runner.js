// server/agents/diagnostic-runner.js
require('dotenv').config();
const colors = require('colors');
const authValidator = require('./auth-validator');
const securityAuditor = require('./security-auditor');

const runDiagnostics = async () => {
    const startTime = Date.now();
    console.log(colors.bold.blue('🤖  VAAL AI EMPIRE - AUTONOMOUS DIAGNOSTIC SYSTEM'));
    console.log(colors.blue('    PhD-Level Backend Validation'));
    console.log(colors.blue('═══════════════════════════════════════════════\n'));

    try {
        const authResults = await authValidator.run();
        const securityResults = securityAuditor.run();

        const totalFailures = authResults.failed + securityResults.CRITICAL + securityResults.HIGH;
        const totalWarnings = authResults.warnings + securityResults.MEDIUM + securityResults.LOW;

        console.log(colors.bold('\n📊 COMPREHENSIVE DIAGNOSTIC REPORT'));
        console.log(colors.blue('═══════════════════════════════════\n'));

        if (totalFailures > 0) {
            console.log(colors.red.bold('🚨 OVERALL STATUS: FAILED'));
            console.log(colors.red('   Critical issues detected. Backend NOT ready for production.'));
            console.log(colors.red('   Review the cookbooks generated above to fix critical issues.\n'));
        } else if (totalWarnings > 0) {
            console.log(colors.yellow.bold('⚠️  OVERALL STATUS: PASS WITH WARNINGS'));
            console.log(colors.yellow('   Backend functional but has minor issues.'));
            console.log(colors.yellow('   Review warnings before production deployment.\n'));
        } else {
            console.log(colors.green.bold('🎉 OVERALL STATUS: PERFECT'));
            console.log(colors.green('   All systems operational. Backend ready for production!\n'));
        }

        const duration = ((Date.now() - startTime) / 1000).toFixed(2);
        console.log(colors.gray(`⏱️  Diagnostic completed in ${duration}s\n`));

        if (totalFailures > 0) {
            process.exit(1); // Exit with a non-zero code to fail CI/CD pipelines
        }

    } catch (error) {
        console.error(colors.red.bold('\n💥 A fatal error occurred during diagnostics:'));
        console.error(error);
        process.exit(1);
    }
};

runDiagnostics();
