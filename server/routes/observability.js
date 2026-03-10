// Vaal AI Empire - Observability API Routes
// Endpoints for traces, metrics, and evaluation

const express = require('express');
const { getTracer } = require('../lib/tracing');
const { LLMEvaluator } = require('../lib/evaluator');
const { sanitizeLog, validateMetadata } = require('../utils/sanitizeLog');

const router = express.Router();
const tracer = getTracer();
const evaluator = new LLMEvaluator();

// Allowed metadata keys for trace creation (prevents property injection)
const TRACE_METADATA_ALLOWED_KEYS = [
  'method', 'path', 'userId', 'sessionId', 'userAgent', 
  'ipHash', 'duration', 'status', 'error', 'component',
  'project', 'environment', 'statusCode'
];

const SPAN_METADATA_ALLOWED_KEYS = [
  'operation', 'component', 'error', 'http.method', 'http.status_code',
  'db.operation', 'db.statement', 'rpc.method', 'messaging.destination',
  'model', 'provider', 'inputTokens', 'prompt'
];

// Get all traces
router.get('/traces', (req, res) => {
  const { status, name, limit = 50 } = req.query;
  
  // SECURITY: Parse and validate limit
  const parsedLimit = parseInt(limit);
  const safeLimit = isNaN(parsedLimit) ? 50 : Math.min(parsedLimit, 1000);
  
  const traces = tracer.getTraces({
    status: status ? sanitizeLog(String(status)) : undefined,
    name: name ? sanitizeLog(String(name)) : undefined,
    limit: safeLimit
  });

  res.json({
    traces,
    total: traces.length
  });
});

// Get single trace
router.get('/traces/:traceId', (req, res) => {
  const trace = tracer.getTrace(req.params.traceId);
  
  if (!trace) {
    return res.status(404).json({ error: 'Trace not found' });
  }

  res.json(trace);
});

// Create new trace
router.post('/traces', (req, res) => {
  const { name, metadata } = req.body;
  
  // SECURITY: Validate name is a string
  if (name !== undefined && typeof name !== 'string') {
    return res.status(400).json({ error: 'Name must be a string' });
  }
  
  // SECURITY: Validate metadata is an object if provided
  if (metadata !== undefined && (typeof metadata !== 'object' || metadata === null || Array.isArray(metadata))) {
    return res.status(400).json({ error: 'Metadata must be an object' });
  }
  
  // SECURITY: Validate metadata keys to prevent property injection
  const safeMetadata = metadata ? validateMetadata(metadata, TRACE_METADATA_ALLOWED_KEYS) : {};
  
  const traceId = tracer.startTrace(name, safeMetadata);
  
  res.json({
    traceId,
    message: 'Trace started'
  });
});

// End trace
router.post('/traces/:traceId/end', (req, res) => {
  const { result } = req.body;
  
  // SECURITY: Validate result is an object if provided
  if (result !== undefined && (typeof result !== 'object' || result === null)) {
    return res.status(400).json({ error: 'Result must be an object' });
  }
  
  tracer.endTrace(req.params.traceId, result);
  
  res.json({
    message: 'Trace ended'
  });
});

// Get metrics
router.get('/metrics', (req, res) => {
  const { name, since, limit = 100 } = req.query;
  
  // SECURITY: Parse and validate limit
  const parsedLimit = parseInt(limit);
  const safeLimit = isNaN(parsedLimit) ? 100 : Math.min(parsedLimit, 10000);
  
  // SECURITY: Parse and validate since
  const parsedSince = since ? parseInt(since) : undefined;
  const safeSince = (parsedSince && !isNaN(parsedSince)) ? parsedSince : undefined;
  
  const metrics = tracer.getMetrics({
    name: name ? sanitizeLog(String(name)) : undefined,
    since: safeSince,
    limit: safeLimit
  });

  res.json({
    metrics,
    total: metrics.length
  });
});

// Record metric
router.post('/metrics', (req, res) => {
  const { name, data } = req.body;
  
  // SECURITY: Validate name is a non-empty string
  if (!name || typeof name !== 'string') {
    return res.status(400).json({ error: 'Name is required and must be a string' });
  }
  
  // SECURITY: Validate data is an object if provided
  if (data !== undefined && (typeof data !== 'object' || data === null || Array.isArray(data))) {
    return res.status(400).json({ error: 'Data must be an object' });
  }
  
  const safeName = sanitizeLog(name);
  const safeData = data ? validateMetadata(data, [...TRACE_METADATA_ALLOWED_KEYS, ...SPAN_METADATA_ALLOWED_KEYS]) : {};
  
  tracer.recordMetric(safeName, safeData);
  
  res.json({
    message: 'Metric recorded'
  });
});

// Get stats
router.get('/stats', (req, res) => {
  const stats = tracer.getStats();
  const evalStats = evaluator.getStats();

  res.json({
    tracing: stats,
    evaluation: evalStats,
    timestamp: Date.now()
  });
});

// Run evaluation
router.post('/evaluate', async (req, res) => {
  try {
    const { input, output, context } = req.body;
    
    if (!input || !output) {
      return res.status(400).json({ error: 'Input and output required' });
    }

    // SECURITY: Validate inputs are strings
    if (typeof input !== 'string' || typeof output !== 'string') {
      return res.status(400).json({ error: 'Input and output must be strings' });
    }
    
    if (context !== undefined && typeof context !== 'string') {
      return res.status(400).json({ error: 'Context must be a string if provided' });
    }

    const results = await evaluator.runEvaluation({ 
      input: sanitizeLog(input), 
      output: sanitizeLog(output), 
      context: context ? sanitizeLog(context) : undefined 
    });
    
    res.json(results);
  } catch (error) {
    // SECURITY: Use structured error logging
    console.error(JSON.stringify({
      level: 'error',
      event: 'evaluation_error',
      error: error.message,
      timestamp: new Date().toISOString()
    }));
    res.status(500).json({ error: error.message });
  }
});

// Track LLM call
router.post('/llm/track', (req, res) => {
  const { traceId, model, provider, prompt, inputTokens } = req.body;
  
  // SECURITY: Validate required fields
  if (!traceId || typeof traceId !== 'string') {
    return res.status(400).json({ error: 'TraceId is required and must be a string' });
  }
  
  // SECURITY: Validate and sanitize optional fields
  const safeParams = {};
  if (model !== undefined) safeParams.model = sanitizeLog(String(model));
  if (provider !== undefined) safeParams.provider = sanitizeLog(String(provider));
  if (prompt !== undefined) safeParams.prompt = sanitizeLog(String(prompt));
  if (inputTokens !== undefined) {
    const parsed = parseInt(inputTokens);
    if (!isNaN(parsed)) safeParams.inputTokens = parsed;
  }
  
  const spanId = tracer.trackLLMCall(traceId, safeParams);
  
  if (!spanId) {
    return res.status(404).json({ error: 'Trace not found' });
  }
  
  res.json({ spanId });
});

// Complete LLM call
router.post('/llm/complete', (req, res) => {
  const { spanId, output, outputTokens, totalTokens, cost } = req.body;
  
  // SECURITY: Validate spanId
  if (!spanId || typeof spanId !== 'string') {
    return res.status(400).json({ error: 'SpanId is required and must be a string' });
  }
  
  // SECURITY: Validate and sanitize response data
  const safeResponse = {};
  if (output !== undefined) safeResponse.output = sanitizeLog(String(output));
  if (outputTokens !== undefined) {
    const parsed = parseInt(outputTokens);
    if (!isNaN(parsed)) safeResponse.outputTokens = parsed;
  }
  if (totalTokens !== undefined) {
    const parsed = parseInt(totalTokens);
    if (!isNaN(parsed)) safeResponse.totalTokens = parsed;
  }
  if (cost !== undefined) {
    const parsed = parseFloat(cost);
    if (!isNaN(parsed)) safeResponse.cost = parsed;
  }
  
  tracer.completeLLMCall(spanId, safeResponse);
  
  res.json({ message: 'LLM call completed' });
});

module.exports = router;
