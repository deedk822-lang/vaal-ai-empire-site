/**
 * Secure Logging Utility
 * Sanitizes sensitive data before logging to prevent information leakage
 */

const winston = require('winston');

// Sensitive fields that should be redacted
const SENSITIVE_FIELDS = [
  'password',
  'token',
  'jwt',
  'secret',
  'apiKey',
  'api_key',
  'authorization',
  'auth',
  'cookie',
  'session',
  'creditCard',
  'cardNumber',
  'cvv',
  'ssn',
  'sin',
];

/**
 * Sanitize a string value
 * @param {string} value - Value to sanitize
 * @returns {string} - Sanitized value
 */
const sanitizeString = (value) => {
  if (typeof value !== 'string') return value;
  
  // Redact potential sensitive patterns
  const patterns = [
    { regex: /sk_live_[a-zA-Z0-9]{24,}/g, replacement: '[STRIPE_KEY_REDACTED]' },
    { regex: /sk_test_[a-zA-Z0-9]{24,}/g, replacement: '[STRIPE_TEST_KEY_REDACTED]' },
    { regex: /AKIA[0-9A-Z]{16}/g, replacement: '[AWS_KEY_REDACTED]' },
    { regex: /ghp_[a-zA-Z0-9]{36}/g, replacement: '[GITHUB_TOKEN_REDACTED]' },
    { regex: /Bearer\s+[a-zA-Z0-9\-_]+/g, replacement: 'Bearer [TOKEN_REDACTED]' },
    { regex: /Basic\s+[a-zA-Z0-9=]+/g, replacement: 'Basic [CREDENTIALS_REDACTED]' },
  ];
  
  let sanitized = value;
  patterns.forEach(({ regex, replacement }) => {
    sanitized = sanitized.replace(regex, replacement);
  });
  
  return sanitized;
};

/**
 * Recursively sanitize an object
 * @param {object} obj - Object to sanitize
 * @returns {object} - Sanitized object
 */
const sanitizeObject = (obj) => {
  if (!obj || typeof obj !== 'object') {
    return sanitizeString(obj);
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item));
  }
  
  const sanitized = {};
  for (const [key, value] of Object.entries(obj)) {
    // Check if key contains sensitive field name
    const isSensitive = SENSITIVE_FIELDS.some(field => 
      key.toLowerCase().includes(field.toLowerCase())
    );
    
    if (isSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeObject(value);
    } else if (typeof value === 'string') {
      sanitized[key] = sanitizeString(value);
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
};

/**
 * Sanitize log input
 * @param {any} input - Input to sanitize
 * @returns {any} - Sanitized input
 */
const sanitizeLogInput = (input) => {
  if (typeof input === 'string') {
    return sanitizeString(input);
  }
  if (typeof input === 'object' && input !== null) {
    return sanitizeObject(input);
  }
  return input;
};

// Create Winston logger
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json()
  ),
  defaultMeta: { service: 'vaal-ai-empire' },
  transports: [
    // Write all logs with level 'error' and below to error.log
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error',
    }),
    // Write all logs with level 'info' and below to combined.log
    new winston.transports.File({ 
      filename: 'logs/combined.log',
    }),
  ],
});

// Console transport for development
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    ),
  }));
}

// Wrap logger methods to sanitize input
const originalLog = logger.log.bind(logger);
logger.log = (level, message, meta) => {
  const sanitizedMessage = sanitizeLogInput(message);
  const sanitizedMeta = sanitizeObject(meta || {});
  return originalLog(level, sanitizedMessage, sanitizedMeta);
};

module.exports = {
  logger,
  sanitizeLogInput,
  sanitizeObject,
  sanitizeString,
};
