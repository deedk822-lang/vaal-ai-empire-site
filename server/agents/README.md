# 🤖 Autonomous Validation Agents

## Overview

These agents provide PhD-level validation and self-healing capabilities for the Vaal AI Empire backend.

## Agents

### 1. 🔐 Auth Validator (`auth-validator.js`)
**Tests:**
- JWT token generation & validation
- Password hashing (bcrypt)
- Login attempt tracking
- Account locking
- User model validation

**Run:**
```bash
node server/agents/auth-validator.js
```

### 2. 🛡️ Security Auditor (`security-auditor.js`)
**Tests:**
- Environment variable security
- Rate limiting configuration
- CORS settings
- Security headers (Helmet)
- Input sanitization (XSS, NoSQL injection)
- Sensitive data exposure

**Run:**
```bash
node server/agents/security-auditor.js
```

### 3. 🤖 Diagnostic Runner (`diagnostic-runner.js`)
**Orchestrates all agents**

Runs complete system validation.

**Run:**
```bash
node server/agents/diagnostic-runner.js
# or
npm run diagnose
```

## Quick Start

```bash
# Install dependencies
cd server
npm install colors

# Run all diagnostics
node agents/diagnostic-runner.js
```

## Expected Output

```
🤖  VAAL AI EMPIRE - AUTONOMOUS DIAGNOSTIC SYSTEM
    PhD-Level Backend Validation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 Authentication System:
   ✅ Passed: 5
   ❌ Failed: 0
   ⚠️  Warnings: 1

🛡️  Security Audit:
   🚨 Critical: 0
   ❌ High: 0
   ⚠️  Medium: 2
   ℹ️  Low: 1

🎉 OVERALL STATUS: PASS WITH WARNINGS
   Backend functional but has minor issues.
   Review warnings before production deployment.
```

## Troubleshooting Cookbooks

When issues are detected, agents auto-generate cookbooks with fixes:

### Example: JWT Secret Issue
```
📚 AUTHENTICATION TROUBLESHOOTING COOKBOOK

1. ❌ JWT_SECRET not set in environment

   FIX:
   1. Generate a secure secret:
      node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
   2. Add to server/.env:
      JWT_SECRET=<generated-secret>
   3. Restart server
```

## Integration

Add to `package.json`:

```json
{
  "scripts": {
    "diagnose": "node agents/diagnostic-runner.js",
    "test:auth": "node agents/auth-validator.js",
    "test:security": "node agents/security-auditor.js"
  }
}
```

## CI/CD Integration

Run in GitHub Actions:

```yaml
- name: Run Backend Diagnostics
  run: |
    cd server
    npm install
    npm run diagnose
```

## Exit Codes

- `0`: All tests passed
- `1`: Critical failures detected

## Future Agents (Coming Soon)

- 💾 Database Monitor (MongoDB health)
- 🧪 API Tester (endpoint validation)
- 📊 Performance Profiler
- 🔄 Self-Healing Agent (auto-fix common issues)

---

**Built in the Vaal. Built for Africa. Built to dominate.** 🇿🇦⚡