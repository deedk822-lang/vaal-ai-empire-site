/**
 * Centralized log sanitization to prevent log injection attacks.
 * Strips control characters that could manipulate log parsers.
 * POPIA-compliant: Does not alter PII, only control characters.
 * 
 * @module server/utils/sanitizeLog
 * @security Prevents log injection attacks from user-supplied data
 */

/**
 * Sanitizes a value for safe logging by removing control characters.
 * 
 * @param {*} value - The value to sanitize
 * @returns {string} - Sanitized string safe for logging
 * 
 * @example
 * // Basic usage
 * sanitizeLog('normal text') // 'normal text'
 * 
 * @example
 * // Log injection prevention
 * sanitizeLog('user input\nFAKE LOG ENTRY') // 'user input_FAKE LOG ENTRY'
 * 
 * @example
 * // Object sanitization
 * sanitizeLog({ email: 'user@test.com', token: 'abc\nmalicious' })
 * // '{"email":"user@test.com","token":"abc_malicious"}'
 */
function sanitizeLog(value) {
  // Handle null/undefined
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  
  // Handle objects (including arrays)
  if (typeof value === 'object') {
    try {
      // Recursively sanitize object values
      const sanitized = sanitizeObject(value);
      return JSON.stringify(sanitized).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    } catch (e) {
      // Circular reference or other JSON error
      return '[Object: non-serializable]';
    }
  }
  
  // Handle primitives
  return String(value).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
}

/**
 * Recursively sanitizes object properties.
 * 
 * @param {Object|Array} obj - Object to sanitize
 * @param {Set} seen - Set of seen objects (for circular reference detection)
 * @returns {Object|Array} - Sanitized object
 */
function sanitizeObject(obj, seen = new Set()) {
  // Prevent circular references
  if (seen.has(obj)) return '[Circular]';
  seen.add(obj);
  
  // Handle arrays
  if (Array.isArray(obj)) {
    return obj.map(item => {
      if (typeof item === 'object' && item !== null) {
        return sanitizeObject(item, seen);
      }
      return typeof item === 'string' 
        ? item.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_')
        : item;
    });
  }
  
  // Handle objects
  const result = {};
  for (const [key, value] of Object.entries(obj)) {
    // Sanitize key
    const sanitizedKey = key.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    
    // Sanitize value
    if (typeof value === 'string') {
      result[sanitizedKey] = value.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    } else if (typeof value === 'object' && value !== null) {
      result[sanitizedKey] = sanitizeObject(value, seen);
    } else {
      result[sanitizedKey] = value;
    }
  }
  
  return result;
}

/**
 * Creates a sanitized log entry object.
 * POPIA-compliant: Hashes sensitive fields instead of logging raw values.
 * 
 * @param {string} level - Log level (info, warn, error, debug)
 * @param {string} message - Log message
 * @param {Object} meta - Additional metadata
 * @returns {Object} - Sanitized log entry ready for JSON serialization
 */
function createLogEntry(level, message, meta = {}) {
  const crypto = require('crypto');
  
  // Fields to hash for POPIA compliance
  const sensitiveFields = ['email', 'phone', 'ip', 'address', 'idNumber', 'password', 'token'];
  
  const sanitizedMeta = {};
  for (const [key, value] of Object.entries(meta)) {
    if (sensitiveFields.includes(key) && typeof value === 'string') {
      // Hash sensitive values (first 8 chars for debugging)
      const hash = crypto.createHash('sha256').update(value).digest('hex');
      sanitizedMeta[key] = `HASH:${hash.slice(0, 8)}...`;
    } else {
      sanitizedMeta[key] = sanitizeLog(value);
    }
  }
  
  return {
    timestamp: new Date().toISOString(),
    level,
    message: sanitizeLog(message),
    meta: sanitizedMeta,
    service: 'vaal-ai-empire',
    environment: process.env.NODE_ENV || 'development'
  };
}

/**
 * Safe logging functions that automatically sanitize all inputs.
 */
const safeLog = {
  info: (message, meta = {}) => {
    console.log(JSON.stringify(createLogEntry('info', message, meta)));
  },
  
  warn: (message, meta = {}) => {
    console.warn(JSON.stringify(createLogEntry('warn', message, meta)));
  },
  
  error: (message, meta = {}) => {
    console.error(JSON.stringify(createLogEntry('error', message, meta)));
  },
  
  debug: (message, meta = {}) => {
    if (process.env.NODE_ENV !== 'production') {
      console.debug(JSON.stringify(createLogEntry('debug', message, meta)));
    }
  }
};

module.exports = {
  sanitizeLog,
  sanitizeObject,
  createLogEntry,
  safeLog
};
