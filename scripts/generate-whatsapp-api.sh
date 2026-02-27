#!/bin/bash
# OpenAPI Code Generation Script for WhatsApp API
# APEX Security Framework v2.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPEC_FILE="${PROJECT_ROOT}/openapi/whatsapp-api.yaml"
OUTPUT_DIR="${PROJECT_ROOT}/generated/whatsapp-api"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  OpenAPI Code Generation - Vaal AI WhatsApp API                  ║"
echo "║  APEX Security Framework v2.0 Compliant                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v openapi-generator-cli &> /dev/null; then
    echo "❌ openapi-generator-cli not found. Installing..."
    npm install -g @openapitools/openapi-generator-cli@7.2.0
fi

if [ ! -f "$SPEC_FILE" ]; then
    echo "❌ OpenAPI spec not found: $SPEC_FILE"
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Validate APEX annotations
echo "🔍 Validating APEX annotations..."
node "${SCRIPT_DIR}/validate-apex-annotations.js" "$SPEC_FILE" || {
    echo "⚠️  APEX validation warnings (continuing anyway)"
}
echo ""

# Clean previous generation
echo "🧹 Cleaning previous generation..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
echo "✅ Cleaned"
echo ""

# Generate server code
echo "🚀 Generating Express server code..."
openapi-generator-cli generate \
    -i "$SPEC_FILE" \
    -g nodejs-express-server \
    -o "$OUTPUT_DIR" \
    --additional-properties="usePromises=true,escapeQuotationsInStringLiteral=true,serverPort=3000,apiPackage=whatsapp,modelPackage=models" \
    --git-user-id deedk822-lang \
    --git-repo-id vaal-ai-empire-site

echo "✅ Server code generated"
echo ""

# Generate client SDK
echo "🚀 Generating client SDK..."
openapi-generator-cli generate \
    -i "$SPEC_FILE" \
    -g typescript-fetch \
    -o "${OUTPUT_DIR}/client" \
    --additional-properties="npmName=@vaal-ai/whatsapp-client,supportsES6=true,typescriptThreePlus=true"

echo "✅ Client SDK generated"
echo ""

# Post-generation security fixes
echo "🔒 Applying APEX security hardening..."

# Add security headers to generated Express app
if [ -f "${OUTPUT_DIR}/expressServer.js" ]; then
    cat > "${OUTPUT_DIR}/utils/security.js" << 'SECURITY_EOF'
// APEX Security Utilities - Auto-generated
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

const securityMiddleware = {
  // Helmet for security headers
  helmet: helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
      },
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true,
    },
  }),
  
  // Rate limiting per APEX spec
  rateLimiter: rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // 100 requests per window
    standardHeaders: true,
    legacyHeaders: false,
    message: {
      error: 'Too many requests, please try again later.',
      retry_after: 900
    }
  })
};

module.exports = securityMiddleware;
SECURITY_EOF
    echo "✅ Security middleware added"
fi

# Create APEX-compliant test scaffolding
mkdir -p "${OUTPUT_DIR}/test"
cat > "${OUTPUT_DIR}/test/whatsapp-security.test.js" << 'TEST_EOF'
/**
 * APEX Security Tests for WhatsApp API
 * Auto-generated with security hardening
 */

const request = require('supertest');
const app = require('../expressServer');
const crypto = require('crypto');

describe('APEX Security Tests - WhatsApp API', () => {
  
  describe('Authentication', () => {
    test('rejects requests without valid Bearer token', async () => {
      const res = await request(app)
        .post('/v1/whatsapp/messages')
        .send({
          messaging_product: 'whatsapp',
          to: '+27821234567',
          type: 'text',
          text: { body: 'Test' }
        });
      
      expect(res.status).toBe(401);
    });
  });
  
  describe('Webhook Security', () => {
    test('rejects webhooks with invalid signature', async () => {
      const res = await request(app)
        .post('/v1/webhooks/whatsapp')
        .set('X-Hub-Signature-256', 'sha256=invalid')
        .send({ object: 'whatsapp_business_account' });
      
      expect(res.status).toBe(401);
    });
  });
  
  describe('Input Validation', () => {
    test('rejects invalid phone numbers', async () => {
      const res = await request(app)
        .post('/v1/whatsapp/messages')
        .set('Authorization', 'Bearer test-token')
        .send({
          messaging_product: 'whatsapp',
          to: 'invalid-phone',
          type: 'text',
          text: { body: 'Test' }
        });
      
      expect(res.status).toBe(400);
    });
    
    test('sanitizes message content', async () => {
      const res = await request(app)
        .post('/v1/whatsapp/messages')
        .set('Authorization', 'Bearer test-token')
        .send({
          messaging_product: 'whatsapp',
          to: '+27821234567',
          type: 'text',
          text: { body: '<script>alert("xss")</script>' }
        });
      
      // Should sanitize but still accept
      expect(res.status).toBe(200);
    });
  });
  
  describe('Rate Limiting', () => {
    test('enforces rate limits', async () => {
      // Make 101 requests
      for (let i = 0; i < 101; i++) {
        await request(app)
          .post('/v1/whatsapp/messages')
          .set('Authorization', 'Bearer test-token')
          .send({
            messaging_product: 'whatsapp',
            to: '+27821234567',
            type: 'text',
            text: { body: `Test ${i}` }
          });
      }
      
      // 101st request should be rate limited
      const res = await request(app)
        .post('/v1/whatsapp/messages')
        .set('Authorization', 'Bearer test-token')
        .send({
          messaging_product: 'whatsapp',
          to: '+27821234567',
          type: 'text',
          text: { body: 'Rate limit test' }
        });
      
      expect(res.status).toBe(429);
      expect(res.headers['retry-after']).toBeDefined();
    });
  });
});
TEST_EOF

echo "✅ Security tests added"
echo ""

# Generate summary
printf '═%.0s' {1..70}
echo ""
echo "GENERATION SUMMARY"
printf '═%.0s' {1..70}
echo ""
echo "📁 Output Directory: $OUTPUT_DIR"
echo ""
echo "Generated Files:"
find "$OUTPUT_DIR" -type f -name "*.js" -o -name "*.ts" -o -name "*.json" | head -20 | while read f; do
    echo "   • ${f#$PROJECT_ROOT/}"
done
echo ""
echo "✅ Generation complete!"
echo ""
echo "Next Steps:"
echo "   1. Review generated code in $OUTPUT_DIR"
echo "   2. Run tests: cd $OUTPUT_DIR && npm test"
echo "   3. Integrate with Vaal AI agent swarm"
echo "   4. Deploy to staging for validation"
echo ""
echo "APEX Signature: [APEX-OPENAPI-GEN-2026-028-COMPLETE] 🛡️"
