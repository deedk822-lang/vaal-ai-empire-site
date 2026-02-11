/**
 * CSRF Protection Middleware
 * Generates and validates CSRF tokens for state-changing operations
 */

const crypto = require('crypto');

// Generate a secure random token
const generateToken = () => {
  return crypto.randomBytes(32).toString('hex');
};

/**
 * Create CSRF token middleware
 * Generates a token and stores it in the session/cookie
 */
const createCsrfToken = (req, res, next) => {
  // Skip for GET, HEAD, OPTIONS requests (they should be safe)
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    // Generate new token for GET requests to include in forms
    if (!req.cookies.csrfToken) {
      const token = generateToken();
      res.cookie('csrfToken', token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 24 * 60 * 60 * 1000, // 24 hours
      });
      req.csrfToken = token;
    } else {
      req.csrfToken = req.cookies.csrfToken;
    }
    return next();
  }
  
  next();
};

/**
 * Verify CSRF token middleware
 * Validates the token in the request header against the cookie
 */
const verifyCsrfToken = (req, res, next) => {
  // Skip for GET, HEAD, OPTIONS requests
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }
  
  // Get token from header
  const tokenFromHeader = req.headers['x-csrf-token'] || req.headers['x-xsrf-token'];
  
  // Get token from cookie
  const tokenFromCookie = req.cookies.csrfToken;
  
  // Check if tokens exist and match
  if (!tokenFromHeader || !tokenFromCookie || tokenFromHeader !== tokenFromCookie) {
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
  const token = req.cookies.csrfToken || generateToken();
  
  // Set cookie if not exists
  if (!req.cookies.csrfToken) {
    res.cookie('csrfToken', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 24 * 60 * 60 * 1000,
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
};
