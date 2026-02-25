// Vaal AI Empire - Log Sanitization Utility
// Prevents log injection and property injection attacks
// POPIA-compliant: Does not alter PII values, only strips control characters

/**
 * Sanitize a string value by removing control characters
 * @param {string} str - String to sanitize
 * @returns {string} - Sanitized string
 */
function sanitizeString(str) {
  if (typeof str !== 'string') return str;
  return str.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
}

/**
 * Centralized log sanitization to prevent log injection and property injection.
 * 
 * @param {*} value - Any value to sanitize
 * @param {Object} options - Optional configuration
 * @param {string[]} options.allowedKeys - Whitelist of allowed object keys (for metadata)
 * @returns {string|object} - Sanitized value
 */
function sanitizeLog(value, options = {}) {
  const { allowedKeys = null } = options;
  
  // Handle null/undefined
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  
  // Handle primitives
  if (typeof value === 'string') {
    return sanitizeString(value);
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  
  // Handle objects with key whitelisting to prevent property injection
  if (typeof value === 'object') {
    try {
      const sanitized = sanitizeObject(value, new Set(), options);
      return JSON.stringify(sanitized).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    } catch (e) {
      return '[Object]';
    }
  }
  
  // Fallback for other types
  return String(value).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
}

/**
 * Recursively sanitize object values with key whitelisting.
 * Uses Object.create(null) to prevent prototype pollution.
 * 
 * @param {Object|Array} obj - Object to sanitize
 * @param {Set} seen - Circular reference tracking
 * @param {Object} options - Configuration
 * @param {string[]} options.allowedKeys - Whitelist of allowed keys (null = allow all)
 * @returns {Object|Array} - Sanitized object with safe property names
 */
function sanitizeObject(obj, seen = new Set(), options = {}) {
  const { allowedKeys = null } = options;
  
  // Prevent circular references
  if (seen.has(obj)) return '[Circular]';
  seen.add(obj);
  
  // Handle arrays
  if (Array.isArray(obj)) {
    return obj.map(item => 
      typeof item === 'object' && item !== null 
        ? sanitizeObject(item, seen, options)
        : sanitizeLog(item, options)
    );
  }
  
  // Handle objects with key validation
  // Use Object.create(null) to avoid prototype pollution
  const result = Object.create(null);
  
  for (const [key, value] of Object.entries(obj)) {
    // SECURITY: Sanitize key - strip control characters
    // Convert to string and remove dangerous characters
    // codeql[js/prototype-pollution-assignment] Key is sanitized and validated against whitelist
    const sanitizedKey = String(key).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    
    // SECURITY: If allowedKeys is provided, skip keys not in whitelist
    if (allowedKeys && !allowedKeys.includes(sanitizedKey)) {
      continue;
    }
    
    // SECURITY: Skip prototype pollution keys even if allowedKeys is null
    if (sanitizedKey === '__proto__' || sanitizedKey === 'constructor' || sanitizedKey === 'prototype') {
      continue;
    }
    
    // Sanitize value based on type
    if (typeof value === 'string') {
      // codeql[js/prototype-pollution-assignment] Key was sanitized and dangerous keys filtered
      result[sanitizedKey] = value.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
    } else if (typeof value === 'object' && value !== null) {
      // codeql[js/prototype-pollution-assignment] Key was sanitized and dangerous keys filtered
      result[sanitizedKey] = sanitizeObject(value, seen, options);
    } else {
      // codeql[js/prototype-pollution-assignment] Key was sanitized and dangerous keys filtered
      result[sanitizedKey] = value;
    }
  }
  
  return result;
}

/**
 * Validate metadata against allowed keys
 * Returns only whitelisted keys to prevent property injection
 * 
 * @param {Object} metadata - Metadata object to validate
 * @param {string[]} allowedKeys - Array of allowed key names
 * @returns {Object} - Filtered metadata with only allowed keys
 */
function validateMetadata(metadata, allowedKeys) {
  if (!metadata || typeof metadata !== 'object') {
    return Object.create(null);
  }
  
  const result = Object.create(null);
  
  for (const key of Object.keys(metadata)) {
    // SECURITY: Skip dangerous keys
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      continue;
    }
    
    // SECURITY: Only include allowed keys
    if (allowedKeys.includes(key)) {
      const value = metadata[key];
      if (typeof value === 'string') {
        result[key] = value.replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
      } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        result[key] = sanitizeObject(value, new Set());
      } else {
        result[key] = value;
      }
    }
  }
  
  return result;
}

/**
 * Structured logging helper - outputs JSON format
 * Prevents log injection by never interpolating user input
 * 
 * @param {string} level - Log level (info, warn, error, debug)
 * @param {string} event - Event name
 * @param {Object} data - Additional data (must be sanitized before passing)
 */
function logStructured(level, event, data = {}) {
  const entry = {
    level,
    event,
    timestamp: new Date().toISOString(),
    ...data
  };
  
  // Output as single-line JSON (log parsers expect this format)
  const output = JSON.stringify(entry).replace(/[\r\n]/g, ' ');
  
  switch (level) {
    case 'error': console.error(output); break;
    case 'warn': console.warn(output); break;
    case 'debug': if (process.env.NODE_ENV !== 'production') console.debug(output); break;
    default: console.log(output);
  }
}

module.exports = { 
  sanitizeLog, 
  sanitizeObject, 
  sanitizeString,
  validateMetadata,
  logStructured 
};
