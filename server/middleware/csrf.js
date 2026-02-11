/**
 * CSRF Protection Middleware
 * Generates and validates CSRF tokens for state-changing operations
 * Uses __Host- prefixed cookie for additional security
 */

const crypto = require('crypto');

// Cookie name with __Host- prefix for additional security
// __Host- prefix requires: secure, path=/, no domain attribute
const CSRF_COOKIE_NAME = '__Host-csrfToken';

// Generate a secure random token
const generateToken = () => {
  return crypto.randomBytes(32).toString('hex');
};

/**
 * Create CSRF token middleware
 * Generates a token and stores it in the __Host- prefixed cookie
 */
const createCsrfToken = (req, res, next) => {
  // Skip for GET, HEAD, OPTIONS requests (they should be safe)
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    // Generate new token for GET requests to include in forms
    if (!req.cookies[CSRF_COOKIE_NAME]) {
      const token = generateToken();
      // __Host- prefix requires: secure, path=/, no domain attribute
      res.cookie(CSRF_COOKIE_NAME, token, {
        httpOnly: true,
        secure: true, // Required for __Host- prefix
        path: '/',    // Required for __Host- prefix
        sameSite: 'strict',
        maxAge: 24 * 60 * 60 * 1000, // 24 hours
        // No domain attribute - Required for __Host- prefix
      });
      req.csrfToken = token;
    } else {
      req.csrfToken = req.cookies[CSRF_COOKIE_NAME];
    }
    return next();
  }
  
  next();
};

/**
 * Constant-time token comparison to prevent timing attacks
 * @param {string} headerToken - Token from request header
 * @param {string} cookieToken - Token from cookie
 * @returns {boolean} - True if tokens match
 */
const constantTimeCompare = (headerToken, cookieToken) => {
  // Check if both tokens exist
  if (!headerToken || !cookieToken) {
    return false;
  }
  
  // Convert to buffers
  const bufHeader = Buffer.from(headerToken, 'utf8');
  const bufCookie = Buffer.from(cookieToken, 'utf8');
  
  // Check length - must match for timingSafeEqual
  if (bufHeader.length !== bufCookie.length) {
    return false;
  }
  
  // Constant-time comparison to prevent timing attacks
  try {
    return crypto.timingSafeEqual(bufHeader, bufCookie);
  } catch (error) {
    // If buffers have different lengths, timingSafeEqual throws
    return false;
  }
};

/**
 * Verify CSRF token middleware
 * Validates the token in the request header against the __Host- prefixed cookie
 */
const verifyCsrfToken = (req, res, next) => {
  // Skip for GET, HEAD, OPTIONS requests
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }
  
  // Get token from header
  const tokenFromHeader = req.headers['x-csrf-token'] || req.headers['x-xsrf-token'];
  
  // Get token from __Host- prefixed cookie
  const tokenFromCookie = req.cookies[CSRF_COOKIE_NAME];
  
  // Check if tokens exist and match using constant-time comparison (double-submit pattern)
  if (!constantTimeCompare(tokenFromHeader, tokenFromCookie)) {
    return res.status(403).json({
      success: false,
      error: 'Invalid or missing CSRF token',
      message: 'Please include a valid CSRF token in the X-CSRF-Token header',
    });
  }
  
  next();
};

/**
 * Get CSRF token for frontend
 * Endpoint to retrieve the current CSRF token
 */
const getCsrfToken = (req, res) => {
  const token = req.cookies[CSRF_COOKIE_NAME] || generateToken();
  
  // Set cookie if not exists
  if (!req.cookies[CSRF_COOKIE_NAME]) {
    // __Host- prefix requires: secure, path=/, no domain attribute
    res.cookie(CSRF_COOKIE_NAME, token, {
      httpOnly: true,
      secure: true, // Required for __Host- prefix
      path: '/',    // Required for __Host- prefix
      sameSite: 'strict',
      maxAge: 24 * 60 * 60 * 1000,
      // No domain attribute - Required for __Host- prefix
    });
  }
  
  res.status(200).json({
    success: true,
    csrfToken: token,
  });
};

module.exports = {
  createCsrfToken,
  verifyCsrfToken,
  getCsrfToken,
  CSRF_COOKIE_NAME,
};
