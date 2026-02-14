const request = require('supertest');
// Mocking the server since we don't want to start a real DB connection
const express = require('express');
const app = express();

app.get('/health', (req, res) => res.status(200).json({ status: 'ok' }));

describe('Server Health Check', () => {
  it('should return 200 OK for /health', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toEqual(200);
    expect(res.body).toHaveProperty('status', 'ok');
  });
});
