/**
 * PayFast Rate Limiting Tests
 * APEX-AUDIT-FIND-002: Validates rate limiting on /payfast/notify
 */

const request = require('supertest');
const app = require('../../server/server');

describe('APEX-AUDIT-FIND-002: PayFast ITN Rate Limiting', () => {
    // Reset rate limiter state between tests
    beforeEach(() => {
        jest.clearAllTimers();
    });

    it('should accept requests under the rate limit', async () => {
        // First request should succeed (returns 400 for invalid signature, not 429)
        const res = await request(app)
            .post('/payfast/notify')
            .send('test=data')
            .expect(400); // Invalid signature, but not rate limited
        
        expect(res.text).toBe('Invalid signature');
    });

    it('should return 429 after exceeding rate limit', async () => {
        // Make 100 requests rapidly (the limit is 100 per minute)
        const requests = [];
        for (let i = 0; i < 100; i++) {
            requests.push(
                request(app)
                    .post('/payfast/notify')
                    .send('test=data')
            );
        }
        await Promise.all(requests);

        // 101st request should be rate limited
        const res = await request(app)
            .post('/payfast/notify')
            .send('test=data');

        expect(res.status).toBe(429);
        expect(res.text).toContain('Too many');
    }, 30000); // 30 second timeout for 100 requests

    it('should include rate limit headers', async () => {
        const res = await request(app)
            .post('/payfast/notify')
            .send('test=data');

        // Should have rate limit headers
        expect(res.headers['ratelimit-limit']).toBeDefined();
        expect(res.headers['ratelimit-remaining']).toBeDefined();
    });
});

describe('APEX-AUDIT-FIND-006: Plan Parameter Validation', () => {
    it('should reject invalid plan values', async () => {
        const res = await request(app)
            .post('/create-payment')
            .send({ plan: 'invalid-plan', email: 'test@test.com', name: 'Test' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Invalid plan');
    });

    it('should reject missing plan parameter', async () => {
        const res = await request(app)
            .post('/create-payment')
            .send({ email: 'test@test.com', name: 'Test' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Invalid plan');
    });

    it('should accept valid plan: starter', async () => {
        const res = await request(app)
            .post('/create-payment')
            .send({ plan: 'starter', email: 'test@test.com', name: 'Test' });

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
    });

    it('should accept valid plan: empire', async () => {
        const res = await request(app)
            .post('/create-payment')
            .send({ plan: 'empire', email: 'test@test.com', name: 'Test' });

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
    });
});
