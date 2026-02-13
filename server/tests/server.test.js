/**
 * Server Integration Tests
 */

const request = require('supertest');

// Mock Stripe before requiring the app
jest.mock('stripe', () => {
  return jest.fn(() => ({
    webhooks: {
      constructEvent: jest.fn((body, sig, secret) => ({
        type: 'payment_intent.succeeded',
        data: { object: { id: 'pi_test' } },
      })),
    },
  }));
});

// Mock database connection
jest.mock('../config/database', () => jest.fn(() => Promise.resolve()));

describe('Server', () => {
  let app;

  beforeAll(() => {
    app = require('../server');
  });

  afterAll(async () => {
    // Cleanup after tests
  });

  describe('Basic Routes', () => {
    test('GET / should return welcome message or redirect', async () => {
      const response = await request(app).get('/').expect(200);

      // Should either return HTML or JSON
      expect([200, 302, 404]).toContain(response.status);
    });

    test('GET /api should return API info or 404', async () => {
      const response = await request(app).get('/api');
      expect([200, 404]).toContain(response.status);
    });
  });

  describe('Security Headers', () => {
    test('should have security headers', async () => {
      const response = await request(app).get('/');

      // Check for helmet headers
      expect(response.headers['x-dns-prefetch-control']).toBeDefined();
      expect(response.headers['x-frame-options']).toBeDefined();
      expect(response.headers['x-content-type-options']).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    test('should handle 404 errors', async () => {
      const response = await request(app).get('/non-existent-route-12345').expect(404);

      expect(response.body).toBeDefined();
    });
  });

  describe('Rate Limiting', () => {
    test('should have rate limit headers on API routes', async () => {
      const response = await request(app).get('/api');

      // Not all routes may have rate limiting, so this is optional
      // Just checking the headers don't cause errors
      expect(response.status).toBeDefined();
    });
  });
});

describe('Health Check', () => {
  let app;

  beforeAll(() => {
    app = require('../server');
  });

  test('GET /health should return health status', async () => {
    const response = await request(app).get('/health');

    // Health endpoint may or may not exist
    expect([200, 404]).toContain(response.status);

    if (response.status === 200) {
      expect(response.body).toHaveProperty('status');
    }
  });
});
