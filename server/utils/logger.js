/**
 * APEX-Compliant Logger
 * Security-first logging with PII protection and structured output
 * 
 * Implements:
 * - Invariant #1: Credentials/PII never logged
 * - Structured JSON logging for observability
 * - Log level-based output routing
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Ensure logs directory exists
const logsDir = path.join(__dirname, '..', 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

/**
 * Sensitive field patterns that should be redacted
 * APEX: Never log credentials, tokens, or PII
 */
const SENSITIVE_FIELDS = [
  /password/i,
  /token/i,
  /secret/i,
  /api[_-]?key/i,
  /private[_-]?key/i,
  /credential/i,
  /auth/i,
  /passphrase/i,
  /signature/i,
  /credit[_-]?card/i,
  /cvv/i,
  /ssn/i,
  /id[_-]?number/i,
  /passport/i
];

/**
 * Redact sensitive fields from log data
 * @param {Object} data - Raw log data
 * @returns {Object} Sanitized data
 */
function redactSensitiveData(data) {
  if (!data || typeof data !== 'object') return data;
  
  const sanitized = {};
  for (const [key, value] of Object.entries(data)) {
    const isSensitive = SENSITIVE_FIELDS.some(pattern => pattern.test(key));
    if (isSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = redactSensitiveData(value);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

/**
 * Format log entry as structured JSON
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} meta - Additional metadata
 * @returns {Object} Structured log entry
 */
function formatLogEntry(level, message, meta = {}) {
  const entry = {
    timestamp: new Date().toISOString(),
    level: level.toUpperCase(),
    message,
    service: 'vaal-ai-empire',
    environment: process.env.NODE_ENV || 'development',
    ...redactSensitiveData(meta)
  };
  
  // Add trace ID if available
  if (process.env.TRACE_ID) {
    entry.trace_id = process.env.TRACE_ID;
  }
  
  return entry;
}

/**
 * Write log to file
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} meta - Additional metadata
 */
function writeToFile(level, message, meta) {
  try {
    const entry = formatLogEntry(level, message, meta);
    const logLine = JSON.stringify(entry) + '\n';
    
    // Write to appropriate log file based on level
    const logFile = level === 'error' || level === 'fatal' 
      ? path.join(logsDir, 'error.log')
      : path.join(logsDir, 'app.log');
    
    fs.appendFileSync(logFile, logLine, { encoding: 'utf8' });
  } catch (err) {
    // Silent fail - don't crash on logging errors
    console.error('Logging error:', err.message);
  }
}

/**
 * Console output with colors (development only)
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} meta - Additional metadata
 */
function writeToConsole(level, message, meta) {
  if (process.env.NODE_ENV === 'production') return;
  
  const colors = {
    debug: '\x1b[36m',   // Cyan
    info: '\x1b[32m',    // Green
    warn: '\x1b[33m',    // Yellow
    error: '\x1b[31m',   // Red
    fatal: '\x1b[35m',   // Magenta
    reset: '\x1b[0m'
  };
  
  const color = colors[level] || colors.reset;
  const timestamp = new Date().toISOString();
  const metaStr = Object.keys(meta).length ? ' ' + JSON.stringify(redactSensitiveData(meta)) : '';
  
  console.log(`${color}[${timestamp}] ${level.toUpperCase()}: ${message}${metaStr}${colors.reset}`);
}

/**
 * Logger implementation
 */
const logger = {
  /**
   * Debug level logging
   * @param {string} message - Log message
   * @param {Object} meta - Additional metadata
   */
  debug(message, meta = {}) {
    writeToFile('debug', message, meta);
    writeToConsole('debug', message, meta);
  },

  /**
   * Info level logging
   * @param {string} message - Log message
   * @param {Object} meta - Additional metadata
   */
  info(message, meta = {}) {
    writeToFile('info', message, meta);
    writeToConsole('info', message, meta);
  },

  /**
   * Warning level logging
   * @param {string} message - Log message
   * @param {Object} meta - Additional metadata
   */
  warn(message, meta = {}) {
    writeToFile('warn', message, meta);
    writeToConsole('warn', message, meta);
  },

  /**
   * Error level logging
   * @param {string} message - Log message
   * @param {Object} meta - Additional metadata
   */
  error(message, meta = {}) {
    writeToFile('error', message, meta);
    writeToConsole('error', message, meta);
  },

  /**
   * Fatal level logging (system crash imminent)
   * @param {string} message - Log message
   * @param {Object} meta - Additional metadata
   */
  fatal(message, meta = {}) {
    writeToFile('fatal', message, meta);
    writeToConsole('fatal', message, meta);
  },

  /**
   * Create child logger with default metadata
   * @param {Object} defaultMeta - Default metadata for all logs
   * @returns {Object} Child logger
   */
  child(defaultMeta = {}) {
    return {
      debug: (msg, meta) => logger.debug(msg, { ...defaultMeta, ...meta }),
      info: (msg, meta) => logger.info(msg, { ...defaultMeta, ...meta }),
      warn: (msg, meta) => logger.warn(msg, { ...defaultMeta, ...meta }),
      error: (msg, meta) => logger.error(msg, { ...defaultMeta, ...meta }),
      fatal: (msg, meta) => logger.fatal(msg, { ...defaultMeta, ...meta }),
      child: (moreMeta) => logger.child({ ...defaultMeta, ...moreMeta })
    };
  },

  /**
   * Log security event (APEX-compliant)
   * @param {string} eventType - Security event type
   * @param {Object} details - Event details
   */
  security(eventType, details = {}) {
    const securityMeta = {
      event_type: eventType,
      category: 'security',
      ...details
    };
    this.info(`Security event: ${eventType}`, securityMeta);
  },

  /**
   * Log audit event (POPIA-compliant)
   * @param {string} action - Audit action
   * @param {Object} details - Audit details
   */
  audit(action, details = {}) {
    const auditMeta = {
      action,
      category: 'audit',
      ...details
    };
    this.info(`Audit: ${action}`, auditMeta);
  }
};

module.exports = logger;
