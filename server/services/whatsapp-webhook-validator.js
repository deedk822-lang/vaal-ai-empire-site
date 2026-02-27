/**
 * WhatsApp Webhook Validator Service
 * APEX Security Framework v2.0 Compliant
 * 
 * Implements:
 * - Invariant #2: Auth verified per-request (HMAC-SHA256)
 * - Invariant #1: Credentials never logged
 * - Invariant #5: Approved cryptographic algorithms
 */

const crypto = require('crypto');
const { URL } = require('url');
const logger = require('../utils/logger');

/**
 * WhatsApp Configuration
 * APEX: All credentials from environment variables (never hardcoded)
 */
const WHATSAPP_CONFIG = {
  accessToken: process.env.WHATSAPP_ACCESS_TOKEN,
  phoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID,
  appSecret: process.env.WHATSAPP_APP_SECRET,
  verifyToken: process.env.WHATSAPP_VERIFY_TOKEN,
  businessAccountId: process.env.WHATSAPP_BUSINESS_ACCOUNT_ID,
  apiVersion: 'v22.0',
  get apiUrl() {
    return `https://graph.facebook.com/${this.apiVersion}/${this.phoneNumberId}`;
  }
};

/**
 * Validate configuration at startup
 * APEX: Fail fast on missing security credentials
 */
function validateConfig() {
  const required = ['accessToken', 'appSecret', 'phoneNumberId', 'verifyToken'];
  const missing = required.filter(key => !WHATSAPP_CONFIG[key]);
  
  if (missing.length > 0) {
    throw new Error(
      `APEX Security Violation: Missing WhatsApp credentials: ${missing.join(', ')}. ` +
      `Set via GitHub Secrets, never in code.`
    );
  }
  
  logger.info('WhatsApp configuration validated (APEX-compliant)');
}

/**
 * Verify WhatsApp webhook signature per Meta spec
 * APEX Invariant #2: Auth verified per-request
 * 
 * @param {string} signature - X-Hub-Signature-256 header value
 * @param {string} payload - Raw request body string
 * @returns {boolean} True if signature valid
 */
function verifyWhatsAppSignature(signature, payload) {
  // APEX: Validate all inputs
  if (!signature || !payload || !WHATSAPP_CONFIG.appSecret) {
    logger.warn('WhatsApp signature validation: Missing parameters');
    return false;
  }
  
  // Extract hash from "sha256=abcdef..." format
  const [, receivedHash] = signature.split('=');
  if (!receivedHash) {
    logger.warn('WhatsApp signature validation: Invalid format');
    return false;
  }
  
  try {
    // APEX Invariant #5: Use approved cryptographic algorithm (HMAC-SHA256)
    const expectedHash = crypto
      .createHmac('sha256', WHATSAPP_CONFIG.appSecret)
      .update(payload, 'utf-8')
      .digest('hex');
    
    // APEX: Constant-time comparison to prevent timing attacks
    const receivedBuffer = Buffer.from(receivedHash, 'hex');
    const expectedBuffer = Buffer.from(expectedHash, 'hex');
    
    if (receivedBuffer.length !== expectedBuffer.length) {
      return false;
    }
    
    return crypto.timingSafeEqual(receivedBuffer, expectedBuffer);
  } catch (error) {
    logger.error('WhatsApp signature validation error', { 
      error: error.message,
      // APEX Invariant #1: Never log raw signature or payload
      signature_prefix: signature.substring(0, 16) + '...'
    });
    return false;
  }
}

/**
 * Sanitize WhatsApp message content
 * APEX Invariant #3: Input validation at trust boundaries
 * 
 * @param {string} content - Raw message content
 * @param {string} contentType - 'text', 'media_url', 'voice'
 * @returns {string|null} Sanitized content or null if invalid
 */
function sanitizeWhatsAppContent(content, contentType = 'text') {
  if (!content) return '';
  
  let sanitized = String(content);
  
  // Base sanitization (control characters)
  // APEX: Use Unicode escapes to avoid lint/noControlCharactersInRegex
  sanitized = sanitized.replace(/[\u0000-\u001F\u007F]/g, '_');
  
  // WhatsApp-specific threats
  if (contentType === 'text') {
    // Prevent injection attacks
    // APEX: Comprehensive regex to catch various script tag variations
    sanitized = sanitized
      // Match script tags with any whitespace variations (e.g., </script >)
      .replace(/<script\b[^>]*>[\s\S]*?<\/script\b[^>]*>/gi, '[SCRIPT_REMOVED]')
      // Block dangerous URL schemes (javascript, vbscript, data)
      .replace(/(javascript|vbscript|data):/gi, 'blocked:')
      // Block HTML event handlers
      .replace(/on\w+\s*=\s*["']?/gi, 'blocked=')
      // Block iframe and other dangerous tags
      .replace(/<(iframe|object|embed|form)\b[^>]*>[\s\S]*?<\/\1\b[^>]*>/gi, '[TAG_REMOVED]');
  }
  
  if (contentType === 'media_url' || contentType === 'voice') {
    // APEX: Validate media URLs are from trusted domains only
    // APEX: Also validate URL scheme to prevent javascript:, vbscript:, data: attacks
    const allowedDomains = [
      'whatsapp.net',
      'fbcdn.net',
      'facebook.com'
    ];
    
    // Block dangerous URL schemes
    const dangerousSchemes = /^(javascript|vbscript|data|file|ftp):/i;
    if (dangerousSchemes.test(sanitized)) {
      logger.warn('WhatsApp media URL uses dangerous scheme', { 
        scheme: sanitized.split(':')[0]
      });
      return null;
    }
    
    try {
      const url = new URL(sanitized);
      
      // Only allow HTTPS URLs
      if (url.protocol !== 'https:') {
        logger.warn('WhatsApp media URL not HTTPS', { protocol: url.protocol });
        return null;
      }
      
      const host = url.hostname.toLowerCase().trim();
      const isTrusted = allowedDomains.some(domain => {
        const d = domain.toLowerCase().trim();
        // APEX: Prevent suffix bypass (evilfacebook.com should not match facebook.com)
        return host === d || host.endsWith('.' + d);
      });
      
      if (!isTrusted) {
        logger.warn('WhatsApp media URL from untrusted domain', { 
          domain: url.hostname,
          // APEX Invariant #1: Don't log full URL (may contain PII)
          url_hash: crypto.createHash('sha256').update(sanitized).digest('hex').substring(0, 16)
        });
        return null;
      }
    } catch (error) {
      logger.warn('WhatsApp media URL invalid', { error: error.message });
      return null;
    }
  }
  
  // APEX: Length limits to prevent DoS
  const MAX_LENGTH = 4096;
  if (sanitized.length > MAX_LENGTH) {
    logger.warn('WhatsApp content truncated (length limit)', { 
      original_length: sanitized.length,
      max_length: MAX_LENGTH
    });
    sanitized = sanitized.substring(0, MAX_LENGTH) + '...[TRUNCATED]';
  }
  
  return sanitized;
}

/**
 * Validate webhook verification challenge from Meta
 * Used during webhook setup in Meta Dashboard
 * 
 * @param {string} mode - hub.mode query parameter
 * @param {string} token - hub.verify_token query parameter
 * @param {string} challenge - hub.challenge query parameter
 * @returns {string|null} Challenge response or null if invalid
 */
function verifyWebhookChallenge(mode, token, challenge) {
  if (mode === 'subscribe' && token === WHATSAPP_CONFIG.verifyToken) {
    logger.info('WhatsApp webhook verification successful');
    return challenge;
  }
  
  logger.warn('WhatsApp webhook verification failed', {
    mode,
    token_valid: token === WHATSAPP_CONFIG.verifyToken,
    // APEX: Don't log the actual token
    token_prefix: token ? token.substring(0, 8) + '...' : 'missing'
  });
  return null;
}

module.exports = {
  WHATSAPP_CONFIG,
  validateConfig,
  verifyWhatsAppSignature,
  sanitizeWhatsAppContent,
  verifyWebhookChallenge
};
