/**
 * Jest Test Setup
 * Configuration and utilities for server tests
 */

// Set test environment
process.env.NODE_ENV = 'test';
process.env.PORT = '0'; // Use random port

// Mock environment variables
process.env.STRIPE_SECRET_KEY = 'sk_test_mock';
process.env.STRIPE_PUBLISHABLE_KEY = 'pk_test_mock';
process.env.MONGODB_URI = 'mongodb://localhost:27017/vaal_test';
process.env.JWT_SECRET = 'test-jwt-secret-key';
process.env.JWT_EXPIRE = '7d';
process.env.COHERE_API_KEY = 'test-cohere-key';

// Global test utilities
global.testUtils = {
  /**
   * Create a mock request object
   */
  mockRequest: (overrides = {}) => ({
    body: {},
    params: {},
    query: {},
    headers: {},
    cookies: {},
    user: null,
    ...overrides,
  }),

  /**
   * Create a mock response object
   */
  mockResponse: () => {
    const res = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    res.send = jest.fn().mockReturnValue(res);
    res.cookie = jest.fn().mockReturnValue(res);
    res.clearCookie = jest.fn().mockReturnValue(res);
    res.redirect = jest.fn().mockReturnValue(res);
    res.set = jest.fn().mockReturnValue(res);
    res.header = jest.fn().mockReturnValue(res);
    return res;
  },

  /**
   * Create a mock next function
   */
  mockNext: () => jest.fn(),
};

// Silence console during tests unless explicitly needed
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});
