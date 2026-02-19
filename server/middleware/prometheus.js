/**
 * Prometheus Metrics Middleware
 * 
 * Provides HTTP request metrics and benchmark-specific metrics
 * for monitoring and observability.
 */

const promClient = require('prom-client');

// Create a Registry
const register = new promClient.Registry();

// Add default metrics
promClient.collectDefaultMetrics({ register });

// HTTP Request Metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5]
});
register.registerMetric(httpRequestDuration);

const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});
register.registerMetric(httpRequestsTotal);

const activeConnections = new promClient.Gauge({
  name: 'active_connections',
  help: 'Number of active connections'
});
register.registerMetric(activeConnections);

// Benchmark-specific Metrics
const benchmarkTestsTotal = new promClient.Counter({
  name: 'vaal_benchmark_tests_total',
  help: 'Total number of benchmark tests run',
  labelNames: ['category', 'status']
});
register.registerMetric(benchmarkTestsTotal);

const benchmarkTestsPassed = new promClient.Counter({
  name: 'vaal_benchmark_tests_passed_total',
  help: 'Total number of benchmark tests passed',
  labelNames: ['category']
});
register.registerMetric(benchmarkTestsPassed);

const benchmarkTestsFailed = new promClient.Counter({
  name: 'vaal_benchmark_tests_failed_total',
  help: 'Total number of benchmark tests failed',
  labelNames: ['category']
});
register.registerMetric(benchmarkTestsFailed);

const benchmarkDuration = new promClient.Histogram({
  name: 'vaal_benchmark_duration_seconds',
  help: 'Duration of benchmark tests in seconds',
  labelNames: ['category'],
  buckets: [0.001, 0.01, 0.1, 1, 10, 30, 60]
});
register.registerMetric(benchmarkDuration);

const benchmarkQualityScore = new promClient.Gauge({
  name: 'vaal_benchmark_quality_score',
  help: 'Quality score from benchmark tests',
  labelNames: ['category', 'metric']
});
register.registerMetric(benchmarkQualityScore);

const benchmarkOverallScore = new promClient.Gauge({
  name: 'vaal_benchmark_overall_score',
  help: 'Overall benchmark score percentage'
});
register.registerMetric(benchmarkOverallScore);

// Express Middleware
function metricsMiddleware(req, res, next) {
  const start = Date.now();
  
  activeConnections.inc();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const route = req.route ? req.route.path : req.path;
    
    httpRequestDuration
      .labels(req.method, route, res.statusCode)
      .observe(duration);
    
    httpRequestsTotal
      .labels(req.method, route, res.statusCode)
      .inc();
    
    activeConnections.dec();
  });
  
  next();
}

// Metrics endpoint
async function metricsEndpoint(req, res) {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
}

// Helper functions for benchmark metrics
function recordBenchmarkTest(category, passed, duration) {
  benchmarkTestsTotal.inc({ category, status: passed ? 'passed' : 'failed' });
  benchmarkDuration.observe({ category }, duration);
  
  if (passed) {
    benchmarkTestsPassed.inc({ category });
  } else {
    benchmarkTestsFailed.inc({ category });
  }
}

function recordBenchmarkQualityScore(category, metric, score) {
  benchmarkQualityScore.set({ category, metric }, score);
}

function recordBenchmarkOverallScore(score) {
  benchmarkOverallScore.set(score);
}

module.exports = {
  register,
  metricsMiddleware,
  metricsEndpoint,
  recordBenchmarkTest,
  recordBenchmarkQualityScore,
  recordBenchmarkOverallScore,
  httpRequestDuration,
  httpRequestsTotal,
  activeConnections,
  benchmarkTestsTotal,
  benchmarkTestsPassed,
  benchmarkTestsFailed,
  benchmarkDuration,
  benchmarkQualityScore,
  benchmarkOverallScore
};
