/**
 * Prometheus Metrics Middleware
 * Exposes metrics for Prometheus scraping
 *
 * Includes:
 * - Default Node.js metrics (memory, CPU, event loop lag)
 * - HTTP request metrics
 * - Stripe/payment metrics
 * - Benchmark performance metrics
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

// ============================================
// HTTP Metrics
// ============================================

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

// ============================================
// Stripe/Payment Metrics
// ============================================

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

// ============================================
// Benchmark Performance Metrics
// ============================================

/**
 * Counter for total benchmark tests executed
 * Labels: category (security, efficiency, etc.), status (passed/failed)
 */
const benchmarkTestsTotal = new client.Counter({
  name: 'vaal_ai_empire_benchmark_tests_total',
  help: 'Total number of benchmark tests executed',
  labelNames: ['category', 'status', 'difficulty'],
  registers: [register],
});

/**
 * Histogram for benchmark test duration
 * Labels: category
 * Buckets: 0.1s to 60s
 */
const benchmarkDurationSeconds = new client.Histogram({
  name: 'vaal_ai_empire_benchmark_duration_seconds',
  help: 'Duration of benchmark tests in seconds',
  labelNames: ['category', 'difficulty'],
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60],
  registers: [register],
});

/**
 * Gauge for benchmark quality score (0-10)
 * Labels: category
 */
const benchmarkQualityScore = new client.Gauge({
  name: 'vaal_ai_empire_benchmark_quality_score',
  help: 'Quality score of benchmark results (0-10)',
  labelNames: ['category'],
  registers: [register],
});

/**
 * Gauge for benchmark security score (0-10)
 * Labels: category
 */
const benchmarkSecurityScore = new client.Gauge({
  name: 'vaal_ai_empire_benchmark_security_score',
  help: 'Security score of benchmark results (0-10)',
  labelNames: ['category'],
  registers: [register],
});

/**
 * Gauge for benchmark efficiency score (0-10)
 * Labels: category
 */
const benchmarkEfficiencyScore = new client.Gauge({
  name: 'vaal_ai_empire_benchmark_efficiency_score',
  help: 'Efficiency score of benchmark results (0-10)',
  labelNames: ['category'],
  registers: [register],
});

/**
 * Counter for tokens used in benchmark tests
 * Labels: category
 */
const benchmarkTokensUsed = new client.Counter({
  name: 'vaal_ai_empire_benchmark_tokens_used_total',
  help: 'Total tokens used in benchmark tests',
  labelNames: ['category'],
  registers: [register],
});

/**
 * Gauge for overall benchmark pass rate
 * Labels: category
 */
const benchmarkPassRate = new client.Gauge({
  name: 'vaal_ai_empire_benchmark_pass_rate',
  help: 'Pass rate of benchmark tests (0-100)',
  labelNames: ['category'],
  registers: [register],
});

/**
 * Summary for response time metrics
 * Labels: category
 */
const benchmarkResponseTime = new client.Summary({
  name: 'vaal_ai_empire_benchmark_response_time_ms',
  help: 'Response time of AI model in benchmark tests (milliseconds)',
  labelNames: ['category'],
  maxAgeSeconds: 600,
  ageBuckets: 5,
  registers: [register],
});

/**
 * Counter for code execution attempts in benchmarks
 * Labels: category, success (true/false)
 */
const benchmarkCodeExecutions = new client.Counter({
  name: 'vaal_ai_empire_benchmark_code_executions_total',
  help: 'Total code execution attempts in benchmark tests',
  labelNames: ['category', 'success'],
  registers: [register],
});

// ============================================
// Middleware
// ============================================

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

// ============================================
// Helper Functions - Stripe/Payment
// ============================================

const recordStripeWebhook = (eventType, status) => {
  stripeWebhookEvents.inc({ event_type: eventType, status });
};

const recordCheckoutSession = priceId => {
  checkoutSessionsCreated.inc({ price_id: priceId });
};

// ============================================
// Helper Functions - Benchmarks
// ============================================

/**
 * Record a benchmark test result
 * @param {string} category - Test category (security, efficiency, etc.)
 * @param {boolean} passed - Whether the test passed
 * @param {string} difficulty - Test difficulty (easy, medium, hard)
 */
const recordBenchmarkTest = (category, passed, difficulty = 'medium') => {
  benchmarkTestsTotal.inc({
    category,
    status: passed ? 'passed' : 'failed',
    difficulty
  });
};

/**
 * Record benchmark duration
 * @param {string} category - Test category
 * @param {number} durationSeconds - Duration in seconds
 * @param {string} difficulty - Test difficulty
 */
const recordBenchmarkDuration = (category, durationSeconds, difficulty = 'medium') => {
  benchmarkDurationSeconds.observe({ category, difficulty }, durationSeconds);
};

/**
 * Set benchmark quality score for a category
 * @param {string} category - Test category
 * @param {number} score - Quality score (0-10)
 */
const setBenchmarkQualityScore = (category, score) => {
  benchmarkQualityScore.set({ category }, score);
};

/**
 * Set benchmark security score for a category
 * @param {string} category - Test category
 * @param {number} score - Security score (0-10)
 */
const setBenchmarkSecurityScore = (category, score) => {
  benchmarkSecurityScore.set({ category }, score);
};

/**
 * Set benchmark efficiency score for a category
 * @param {string} category - Test category
 * @param {number} score - Efficiency score (0-10)
 */
const setBenchmarkEfficiencyScore = (category, score) => {
  benchmarkEfficiencyScore.set({ category }, score);
};

/**
 * Record tokens used in a benchmark test
 * @param {string} category - Test category
 * @param {number} tokens - Number of tokens used
 */
const recordBenchmarkTokens = (category, tokens) => {
  benchmarkTokensUsed.inc({ category }, tokens);
};

/**
 * Set benchmark pass rate for a category
 * @param {string} category - Test category
 * @param {number} rate - Pass rate (0-100)
 */
const setBenchmarkPassRate = (category, rate) => {
  benchmarkPassRate.set({ category }, rate);
};

/**
 * Record benchmark response time
 * @param {string} category - Test category
 * @param {number} responseTimeMs - Response time in milliseconds
 */
const recordBenchmarkResponseTime = (category, responseTimeMs) => {
  benchmarkResponseTime.observe({ category }, responseTimeMs);
};

/**
 * Record code execution in a benchmark test
 * @param {string} category - Test category
 * @param {boolean} success - Whether execution succeeded
 */
const recordBenchmarkCodeExecution = (category, success) => {
  benchmarkCodeExecutions.inc({ category, success: success.toString() });
};

/**
 * Record complete benchmark result
 * @param {Object} result - Benchmark result object
 */
const recordBenchmarkResult = (result) => {
  const {
    category,
    passed,
    difficulty = 'medium',
    executionTimeMs,
    responseTimeMs,
    qualityScore,
    securityScore,
    efficiencyScore,
    tokensUsed = 0,
    codeExecuted = false,
    executionSuccess = false
  } = result;

  // Record test result
  recordBenchmarkTest(category, passed, difficulty);

  // Record duration
  if (executionTimeMs) {
    recordBenchmarkDuration(category, executionTimeMs / 1000, difficulty);
  }

  // Record response time
  if (responseTimeMs) {
    recordBenchmarkResponseTime(category, responseTimeMs);
  }

  // Set scores
  if (qualityScore !== undefined) {
    setBenchmarkQualityScore(category, qualityScore);
  }
  if (securityScore !== undefined) {
    setBenchmarkSecurityScore(category, securityScore);
  }
  if (efficiencyScore !== undefined) {
    setBenchmarkEfficiencyScore(category, efficiencyScore);
  }

  // Record tokens
  if (tokensUsed > 0) {
    recordBenchmarkTokens(category, tokensUsed);
  }

  // Record code execution
  if (codeExecuted) {
    recordBenchmarkCodeExecution(category, executionSuccess);
  }
};

// ============================================
// Exports
// ============================================

module.exports = {
  // Core
  register,
  metricsMiddleware,
  metricsEndpoint,

  // Stripe/Payment helpers
  recordStripeWebhook,
  recordCheckoutSession,

  // Benchmark helpers
  recordBenchmarkTest,
  recordBenchmarkDuration,
  setBenchmarkQualityScore,
  setBenchmarkSecurityScore,
  setBenchmarkEfficiencyScore,
  recordBenchmarkTokens,
  setBenchmarkPassRate,
  recordBenchmarkResponseTime,
  recordBenchmarkCodeExecution,
  recordBenchmarkResult,

  // Benchmark metrics (for direct access if needed)
  benchmarkMetrics: {
    testsTotal: benchmarkTestsTotal,
    durationSeconds: benchmarkDurationSeconds,
    qualityScore: benchmarkQualityScore,
    securityScore: benchmarkSecurityScore,
    efficiencyScore: benchmarkEfficiencyScore,
    tokensUsed: benchmarkTokensUsed,
    passRate: benchmarkPassRate,
    responseTime: benchmarkResponseTime,
    codeExecutions: benchmarkCodeExecutions,
  },
};
