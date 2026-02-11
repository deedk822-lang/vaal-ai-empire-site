/**
 * Prometheus Metrics Middleware
 * Exposes metrics for Prometheus scraping
 */

const client = require('prom-client');

// Create a Registry to register the metrics
const register = new client.Registry();

// Add default metrics (memory, CPU, event loop lag, etc.)
client.collectDefaultMetrics({
    register,
    prefix: 'vaal_ai_empire_',
    gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
});

// Custom metrics
const httpRequestDuration = new client.Histogram({
    name: 'vaal_ai_empire_http_request_duration_seconds',
    help: 'Duration of HTTP requests in seconds',
    labelNames: ['method', 'route', 'status_code'],
    buckets: [0.001, 0.01, 0.1, 0.5, 1, 2, 5, 10],
    registers: [register],
});

const httpRequestsTotal = new client.Counter({
    name: 'vaal_ai_empire_http_requests_total',
    help: 'Total number of HTTP requests',
    labelNames: ['method', 'route', 'status_code'],
    registers: [register],
});

const activeConnections = new client.Gauge({
    name: 'vaal_ai_empire_active_connections',
    help: 'Number of active connections',
    registers: [register],
});

const stripeWebhookEvents = new client.Counter({
    name: 'vaal_ai_empire_stripe_webhook_events_total',
    help: 'Total number of Stripe webhook events received',
    labelNames: ['event_type', 'status'],
    registers: [register],
});

const checkoutSessionsCreated = new client.Counter({
    name: 'vaal_ai_empire_checkout_sessions_created_total',
    help: 'Total number of checkout sessions created',
    labelNames: ['price_id'],
    registers: [register],
});

// Middleware to measure request duration
const metricsMiddleware = (req, res, next) => {
    const start = Date.now();
    
    // Track active connections
    activeConnections.inc();
    
    // Override res.end to capture response time
    const originalEnd = res.end.bind(res);
    res.end = function (...args) {
        const duration = (Date.now() - start) / 1000; // Convert to seconds
        const route = req.route ? req.route.path : req.path;
        
        httpRequestDuration.observe(
            { method: req.method, route, status_code: res.statusCode },
            duration
        );
        
        httpRequestsTotal.inc({
            method: req.method,
            route,
            status_code: res.statusCode,
        });
        
        activeConnections.dec();
        
        originalEnd(...args);
    };
    
    next();
};

// Metrics endpoint handler
const metricsEndpoint = async (req, res) => {
    try {
        res.set('Content-Type', register.contentType);
        res.end(await register.metrics());
    } catch (error) {
        res.status(500).json({ error: 'Failed to generate metrics' });
    }
};

// Helper functions to record custom metrics
const recordStripeWebhook = (eventType, status) => {
    stripeWebhookEvents.inc({ event_type: eventType, status });
};

const recordCheckoutSession = (priceId) => {
    checkoutSessionsCreated.inc({ price_id: priceId });
};

module.exports = {
    register,
    metricsMiddleware,
    metricsEndpoint,
    recordStripeWebhook,
    recordCheckoutSession,
};
