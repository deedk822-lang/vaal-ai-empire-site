// Vaal AI Empire - Observability API Routes
// Endpoints for traces, metrics, and evaluation

const express = require('express');
const { getTracer } = require('../lib/tracing');
const { LLMEvaluator } = require('../lib/evaluator');

const router = express.Router();
const tracer = getTracer();
const evaluator = new LLMEvaluator();

// Get all traces
router.get('/traces', (req, res) => {
  const { status, name, limit = 50 } = req.query;
  
  const traces = tracer.getTraces({
    status,
    name,
    limit: parseInt(limit)
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
  
  const traceId = tracer.startTrace(name, metadata);
  
  res.json({
    traceId,
    message: 'Trace started'
  });
});

// End trace
router.post('/traces/:traceId/end', (req, res) => {
  const { result } = req.body;
  
  tracer.endTrace(req.params.traceId, result);
  
  res.json({
    message: 'Trace ended'
  });
});

// Get metrics
router.get('/metrics', (req, res) => {
  const { name, since, limit = 100 } = req.query;
  
  const metrics = tracer.getMetrics({
    name,
    since: since ? parseInt(since) : undefined,
    limit: parseInt(limit)
  });

  res.json({
    metrics,
    total: metrics.length
  });
});

// Record metric
router.post('/metrics', (req, res) => {
  const { name, data } = req.body;
  
  tracer.recordMetric(name, data);
  
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

    const results = await evaluator.runEvaluation({ input, output, context });
    
    res.json(results);
  } catch (error) {
    console.error('Evaluation error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Track LLM call
router.post('/llm/track', (req, res) => {
  const { traceId, model, provider, prompt, inputTokens } = req.body;
  
  const spanId = tracer.trackLLMCall(traceId, {
    model,
    provider,
    prompt,
    inputTokens
  });
  
  res.json({ spanId });
});

// Complete LLM call
router.post('/llm/complete', (req, res) => {
  const { spanId, output, outputTokens, totalTokens, cost } = req.body;
  
  tracer.completeLLMCall(spanId, {
    output,
    outputTokens,
    totalTokens,
    cost
  });
  
  res.json({ message: 'LLM call completed' });
});

module.exports = router;