/**
 * Configurable rate limiting middleware for Express.
 * POPIA-compliant: Uses hashed IP addresses for rate tracking.
 * 
 * @module server/middleware/rateLimiter
 * @security Prevents DoS attacks and API abuse
 */

const rateLimit = require('express-rate-limit');
const crypto = require('crypto');

/**
 * Creates a rate limiter with configurable options.
 * 
 * @param {Object} options - Rate limiter configuration
 * @param {number} options.windowMs - Time window in milliseconds
 * @param {number} options.max - Maximum requests per window
 * @param {string} options.message - Error message when limit exceeded
 * @param {boolean} options.skipSuccessfulRequests - Skip counting successful requests
 * @returns {Function} Express middleware
 */
const createLimiter = ({ windowMs, max, message, skipSuccessfulRequests = false }) => 
  rateLimit({
    windowMs,
    max,
    message: { 
      error: message || 'Too many requests, please try again later.',
      retryAfter: Math.ceil(windowMs / 1000)
    },
    skipSuccessfulRequests,
    
    // POPIA-compliant: Don't log full IP, use hash for rate tracking
    keyGenerator: (req) => {
      const ip = req.ip || req.connection?.remoteAddress || 'unknown';
      const salt = process.env.RATE_LIMIT_SALT || 'vaal-ai-default-salt';
      return crypto.createHash('sha256')
        .update(ip + salt)
        .digest('hex')
        .slice(0, 16);
    },
    
    // Skip rate limiting for internal health checks
    skip: (req) => {
      const skipPaths = ['/health', '/api/health', '/api/payfast/itn'];
      return skipPaths.includes(req.path);
    },
    
    // Standardize headers
    standardHeaders: true,
    legacyHeaders: false,
    
    // Handler for when limit is exceeded
    handler: (req, res) => {
      res.status(429).json({
        error: message || 'Too many requests, please try again later.',
        retryAfter: Math.ceil(windowMs / 1000)
      });
    }
  });

/**
 * Pre-configured rate limiters for different endpoint types.
 */
const rateLimiters = {
  /**
   * Payment endpoints: Stricter limits for financial transactions.
   * Production: 50 requests per 15 minutes
   * Development: 500 requests per 15 minutes (higher for testing)
   */
  payment: createLimiter({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: process.env.NODE_ENV === 'production' ? 50 : 500,
    message: 'Payment request limit exceeded. Please wait 15 minutes before trying again.',
    skipSuccessfulRequests: true // Don't count successful payments
  }),
  
  /**
   * General API: More permissive for normal operations.
   * Production: 200 requests per 15 minutes
   * Development: 2000 requests per 15 minutes
   */
  general: createLimiter({
    windowMs: 15 * 60 * 1000,
    max: process.env.NODE_ENV === 'production' ? 200 : 2000,
    message: 'API request limit exceeded. Please slow down.'
  }),
  
  /**
   * Voice/ASR endpoints: High volume expected for conversational AI.
   * Production: 30 requests per minute
   * Development: 300 requests per minute
   */
  voice: createLimiter({
    windowMs: 1 * 60 * 1000, // 1 minute window
    max: process.env.NODE_ENV === 'production' ? 30 : 300,
    message: 'Voice request limit exceeded. Please slow down.'
  }),
  
  /**
   * Authentication endpoints: Strictest limits to prevent brute force.
   * Production: 5 attempts per 15 minutes
   * Development: 50 attempts per 15 minutes
   */
  auth: createLimiter({
    windowMs: 15 * 60 * 1000,
    max: process.env.NODE_ENV === 'production' ? 5 : 50,
    message: 'Too many authentication attempts. Please try again later.',
    skipSuccessfulRequests: true // Reset on successful login
  }),
  
  /**
   * ITN webhooks: NO rate limiting - PayFast retries on failure.
   * This limiter is essentially disabled.
   */
  webhook: createLimiter({
    windowMs: 1 * 60 * 1000,
    max: 10000, // Very high limit
    message: 'Webhook rate limit exceeded.'
  })
};

/**
 * Middleware to apply rate limiting based on endpoint type.
 * 
 * @param {string} type - Type of rate limiter to use
 * @returns {Function} Express middleware
 */
function applyRateLimit(type = 'general') {
  const limiter = rateLimiters[type] || rateLimiters.general;
  return limiter;
}

/**
 * Creates a custom rate limiter with specific configuration.
 * 
 * @param {Object} config - Custom configuration
 * @returns {Function} Express middleware
 */
function createCustomLimiter(config) {
  return createLimiter({
    windowMs: config.windowMs || 15 * 60 * 1000,
    max: config.max || 100,
    message: config.message || 'Rate limit exceeded.',
    skipSuccessfulRequests: config.skipSuccessfulRequests || false
  });
}

module.exports = {
  rateLimiters,
  applyRateLimit,
  createLimiter,
  createCustomLimiter,
  payment: rateLimiters.payment,
  general: rateLimiters.general,
  voice: rateLimiters.voice,
  auth: rateLimiters.auth,
  webhook: rateLimiters.webhook
};
