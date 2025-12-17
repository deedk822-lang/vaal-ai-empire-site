// server/agents/security-auditor.js
const fs = require('fs');
const path = require('path');
const colors = require('colors');

const audits = {
    'Environment variable security': () => {
        const envPath = path.resolve(__dirname, '..', '.env');
        if (!fs.existsSync(envPath)) {
            return {
                level: 'HIGH',
                message: '`.env` file is missing. Secrets should never be hardcoded.',
                fix: 'Create a `.env` file in the `server/` directory and add all secrets (e.g., JWT_SECRET, MONGODB_URI).'
            };
        }
        return { level: 'PASS' };
    },
    'Rate limiting configuration': () => {
        // This is a proxy check. In a real scenario, we might inspect the app object.
        const serverCode = fs.readFileSync(path.resolve(__dirname, '..', 'server.js'), 'utf-8');
        if (!serverCode.includes('express-rate-limit')) {
            return {
                level: 'HIGH',
                message: 'Rate limiting is not implemented, leaving the server vulnerable to brute-force and DoS attacks.',
                fix: 'Install `express-rate-limit` and apply it as middleware in `server.js`.'
            };
        }
        return { level: 'PASS' };
    },
    'CORS settings (production vs dev)': () => {
        if (process.env.NODE_ENV === 'production' && !process.env.ALLOWED_ORIGINS) {
            return {
                level: 'CRITICAL',
                message: 'CORS is not restricted in production. `ALLOWED_ORIGINS` is not set.',
                fix: 'Set the `ALLOWED_ORIGINS` environment variable to a comma-separated list of allowed domains (e.g., `https://yourapp.com,https://www.yourapp.com`).'
            };
        }
        return { level: 'PASS' };
    },
    'Helmet.js security headers': () => {
        const serverCode = fs.readFileSync(path.resolve(__dirname, '..', 'server.js'), 'utf-8');
        if (!serverCode.includes('helmet')) {
            return {
                level: 'HIGH',
                message: 'Helmet is not used, exposing the app to common web vulnerabilities.',
                fix: 'Install `helmet` and apply it as middleware at the top of `server.js` (`app.use(helmet())`).'
            };
        }
        return { level: 'PASS' };
    },
    'XSS/NoSQL injection protection': () => {
        const serverCode = fs.readFileSync(path.resolve(__dirname, '..', 'server.js'), 'utf-8');
        const xssFound = serverCode.includes('xss-clean');
        const mongoSanitizeFound = serverCode.includes('express-mongo-sanitize');
        if (!xssFound || !mongoSanitizeFound) {
            let message = '';
            if (!xssFound) message += 'XSS cleaning middleware is missing. ';
            if (!mongoSanitizeFound) message += 'NoSQL injection sanitization is missing.';
            return {
                level: 'HIGH',
                message,
                fix: 'Install and apply `xss-clean` and `express-mongo-sanitize` middleware in `server.js`.'
            };
        }
        return { level: 'PASS' };
    },
    'Sensitive data exposure (.gitignore)': () => {
        const gitignorePath = path.resolve(__dirname, '..', '.gitignore');
        if (!fs.existsSync(gitignorePath)) {
            return {
                level: 'CRITICAL',
                message: 'A `.gitignore` file is missing from the `server/` directory.',
                fix: 'Create a `.gitignore` file in `server/` and add `node_modules`, `.env`, and `logs` to it.'
            };
        }
        const gitignore = fs.readFileSync(gitignorePath, 'utf-8');
        if (!gitignore.includes('.env')) {
            return {
                level: 'CRITICAL',
                message: 'The `.gitignore` file does not include `.env`.',
                fix: 'Add `.env` to your `server/.gitignore` file to prevent leaking secrets.'
            };
        }
        return { level: 'PASS' };
    },
    'Payload size limits': () => {
        const serverCode = fs.readFileSync(path.resolve(__dirname, '..', 'server.js'), 'utf-8');
        if (!serverCode.includes("limit: '10kb'")) {
            return {
                level: 'MEDIUM',
                message: 'Payload size limits are not configured. The server may be vulnerable to DoS attacks via large request bodies.',
                fix: "Add a size limit to your body parsing middleware, e.g., `app.use(express.json({ limit: '10kb' }));`."
            };
        }
        return { level: 'PASS' };
    }
};

const run = () => {
    console.log(colors.cyan('\n┌──────────────────────────────────────────────┐'));
    console.log(colors.cyan('│ 2/2 Security Auditor                         │'));
    console.log(colors.cyan('└──────────────────────────────────────────────┘\n'));

    const results = {
        CRITICAL: 0,
        HIGH: 0,
        MEDIUM: 0,
        LOW: 0,
        errors: []
    };

    for (const [name, audit] of Object.entries(audits)) {
        const result = audit();
        if (result.level === 'PASS') {
            console.log(colors.green(`✅ ${name}`));
        } else {
            const color = {
                CRITICAL: colors.red.bold,
                HIGH: colors.red,
                MEDIUM: colors.yellow,
                LOW: colors.blue
            }[result.level];
            console.log(color(`[${result.level}] ${name}: ${result.message}`));
            results[result.level]++;
            results.errors.push({ audit: name, ...result });
        }
    }

    console.log(colors.bold('\n🛡️  SECURITY AUDIT SUMMARY'));
    console.log(colors.red.bold(`🚨 Critical: ${results.CRITICAL}`));
    console.log(colors.red(`❌ HIGH: ${results.HIGH}`));
    console.log(colors.yellow(`⚠️  MEDIUM: ${results.MEDIUM}`));
    console.log(colors.blue(`ℹ️  LOW: ${results.LOW}`));

    const failedAudits = results.errors.filter(e => ['CRITICAL', 'HIGH'].includes(e.level));
    if (failedAudits.length > 0) {
        console.log(colors.red.bold('\n🛡️  SECURITY HARDENING COOKBOOK'));
        console.log(colors.red('══════════════════════════════════════════\n'));
        failedAudits.forEach((error, i) => {
            console.log(colors.red.bold(`${i + 1}. [${error.level}] ${error.audit}`));
            console.log(`   ${colors.white(error.message)}\n`);
            console.log(colors.yellow.bold('   FIX:'));
            console.log(`   ${colors.cyan(error.fix)}\n`);
        });
    }

    return results;
};

module.exports = { run };
