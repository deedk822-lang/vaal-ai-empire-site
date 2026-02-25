// Vaal AI Empire - Tracing & Observability System
// Inspired by Opik's comprehensive tracing architecture

const crypto = require('crypto');
const { sanitizeLog, validateMetadata, logStructured } = require('../utils/sanitizeLog');

// Allowed metadata keys for trace/span metadata (prevents property injection)
const TRACE_METADATA_ALLOWED_KEYS = [
  'method', 'path', 'userId', 'sessionId', 'userAgent', 
  'ipHash', 'duration', 'status', 'error', 'component',
  'project', 'environment', 'statusCode'
];

const SPAN_METADATA_ALLOWED_KEYS = [
  'operation', 'component', 'error', 'http.method', 'http.status_code',
  'db.operation', 'db.statement', 'rpc.method', 'messaging.destination',
  'model', 'provider', 'inputTokens', 'prompt', 'output', 'outputTokens', 
  'totalTokens', 'cost'
];

class VaalTracer {
  constructor(config = {}) {
    this.config = {
      projectName: config.projectName || 'vaal-ai-empire',
      environment: config.environment || 'production',
      enableMetrics: config.enableMetrics !== false,
      ...config
    };
    
    this.traces = new Map();
    this.spans = new Map();
    this.metrics = [];
  }

  /**
   * Start a new trace
   * @param {string} name - Trace name
   * @param {object} metadata - Additional metadata
   * @returns {string} traceId
   */
  startTrace(name, metadata = {}) {
    const traceId = this.generateId();
    
    // SECURITY: Sanitize name and validate metadata to prevent injection
    const sanitizedName = sanitizeLog(String(name || 'unnamed'));
    const safeMetadata = validateMetadata(metadata, TRACE_METADATA_ALLOWED_KEYS);
    
    const trace = {
      id: traceId,
      name: sanitizedName,
      startTime: Date.now(),
      endTime: null,
      metadata: {
        ...safeMetadata,
        project: this.config.projectName,
        environment: this.config.environment
      },
      spans: [],
      status: 'running',
      error: null
    };

    this.traces.set(traceId, trace);
    
    // SECURITY: Use structured logging instead of template literals
    // This prevents log injection by not interpolating user input
    // codeql[js/log-injection] User input is sanitized via sanitizeLog and passed as structured data, not interpolated
    logStructured('info', 'trace_started', {
      traceId,
      name: sanitizedName
    });
    
    return traceId;
  }

  /**
   * End a trace
   * @param {string} traceId
   * @param {object} result - Final result
   */
  endTrace(traceId, result = {}) {
    const trace = this.traces.get(traceId);
    if (!trace) {
      // SECURITY: Use structured logging
      // codeql[js/log-injection] User input is sanitized via sanitizeLog before logging
      logStructured('warn', 'trace_not_found', {
        traceId: sanitizeLog(String(traceId))
      });
      return;
    }

    trace.endTime = Date.now();
    trace.duration = trace.endTime - trace.startTime;
    trace.status = result.error ? 'error' : 'completed';
    trace.result = result;

    if (this.config.enableMetrics) {
      this.recordMetric('trace_completed', {
        name: trace.name,
        duration: trace.duration,
        status: trace.status
      });
    }

    // SECURITY: Use structured logging
    // codeql[js/log-injection] Values come from internal trace object, not direct user input
    logStructured('info', 'trace_completed', {
      traceId,
      name: trace.name,
      duration: trace.duration,
      status: trace.status
    });
  }

  /**
   * Start a span within a trace
   * @param {string} traceId
   * @param {string} name - Span name
   * @param {object} metadata
   * @returns {string} spanId
   */
  startSpan(traceId, name, metadata = {}) {
    const trace = this.traces.get(traceId);
    if (!trace) {
      // SECURITY: Use structured logging
      // codeql[js/log-injection] User input is sanitized via sanitizeLog before logging
      logStructured('warn', 'trace_not_found_for_span', {
        traceId: sanitizeLog(String(traceId))
      });
      return null;
    }

    const spanId = this.generateId();
    
    // SECURITY: Sanitize name and validate metadata
    const sanitizedName = sanitizeLog(String(name || 'unnamed'));
    const safeMetadata = validateMetadata(metadata, SPAN_METADATA_ALLOWED_KEYS);
    
    const span = {
      id: spanId,
      traceId,
      name: sanitizedName,
      startTime: Date.now(),
      endTime: null,
      metadata: safeMetadata,
      status: 'running',
      error: null
    };

    this.spans.set(spanId, span);
    trace.spans.push(spanId);

    return spanId;
  }

  /**
   * End a span
   * @param {string} spanId
   * @param {object} result
   */
  endSpan(spanId, result = {}) {
    const span = this.spans.get(spanId);
    if (!span) return;

    span.endTime = Date.now();
    span.duration = span.endTime - span.startTime;
    span.status = result.error ? 'error' : 'completed';
    span.result = result;
  }

  /**
   * Record custom metric
   * @param {string} name
   * @param {object} data
   */
  recordMetric(name, data = {}) {
    const sanitizedName = sanitizeLog(String(name || 'unnamed'));
    const safeData = validateMetadata(data, [...TRACE_METADATA_ALLOWED_KEYS, ...SPAN_METADATA_ALLOWED_KEYS]);
    
    const metric = {
      timestamp: Date.now(),
      name: sanitizedName,
      data: safeData,
      project: this.config.projectName
    };

    this.metrics.push(metric);

    // Keep only last 10000 metrics
    if (this.metrics.length > 10000) {
      this.metrics = this.metrics.slice(-10000);
    }
  }

  /**
   * Get trace by ID
   * @param {string} traceId
   * @returns {object}
   */
  getTrace(traceId) {
    const trace = this.traces.get(traceId);
    if (!trace) return null;

    return {
      ...trace,
      spans: trace.spans.map(spanId => this.spans.get(spanId)).filter(Boolean)
    };
  }

  /**
   * Get all traces
   * @param {object} filters
   * @returns {array}
   */
  getTraces(filters = {}) {
    let traces = Array.from(this.traces.values());

    if (filters.status) {
      traces = traces.filter(t => t.status === filters.status);
    }

    if (filters.name) {
      // SECURITY: Sanitize filter name before using in includes
      const sanitizedFilter = sanitizeLog(String(filters.name));
      traces = traces.filter(t => t.name && t.name.includes(sanitizedFilter));
    }

    if (filters.limit) {
      traces = traces.slice(0, parseInt(filters.limit));
    }

    return traces.map(trace => ({
      ...trace,
      spans: trace.spans.map(spanId => this.spans.get(spanId)).filter(Boolean)
    }));
  }

  /**
   * Get metrics
   * @param {object} filters
   * @returns {array}
   */
  getMetrics(filters = {}) {
    let metrics = [...this.metrics];

    if (filters.name) {
      // SECURITY: Sanitize filter name
      const sanitizedFilter = sanitizeLog(String(filters.name));
      metrics = metrics.filter(m => m.name === sanitizedFilter);
    }

    if (filters.since) {
      const since = parseInt(filters.since);
      if (!isNaN(since)) {
        metrics = metrics.filter(m => m.timestamp >= since);
      }
    }

    if (filters.limit) {
      const limit = parseInt(filters.limit);
      if (!isNaN(limit)) {
        metrics = metrics.slice(-limit);
      }
    }
    
    return metrics;
  }

  /**
   * Track LLM call
   * @param {string} traceId
   * @param {object} params
   * @returns {string} spanId
   */
  trackLLMCall(traceId, params) {
    // SECURITY: Validate params before using
    const safeParams = validateMetadata(params || {}, SPAN_METADATA_ALLOWED_KEYS);
    
    const spanId = this.startSpan(traceId, 'llm_call', {
      model: safeParams.model,
      provider: safeParams.provider,
      inputTokens: safeParams.inputTokens,
      prompt: safeParams.prompt
    });

    return spanId;
  }

  /**
   * Complete LLM call
   * @param {string} spanId
   * @param {object} response
   */
  completeLLMCall(spanId, response) {
    // SECURITY: Validate response before using
    const safeResponse = validateMetadata(response || {}, SPAN_METADATA_ALLOWED_KEYS);
    
    this.endSpan(spanId, {
      output: safeResponse.output,
      outputTokens: safeResponse.outputTokens,
      totalTokens: safeResponse.totalTokens,
      cost: safeResponse.cost
    });

    this.recordMetric('llm_call_completed', {
      outputTokens: safeResponse.outputTokens,
      cost: safeResponse.cost
    });
  }

  /**
   * Generate unique ID
   * @returns {string}
   */
  generateId() {
    return crypto.randomBytes(16).toString('hex');
  }

  /**
   * Get statistics
   * @returns {object}
   */
  getStats() {
    const traces = Array.from(this.traces.values());
    const completedTraces = traces.filter(t => t.status === 'completed');
    const errorTraces = traces.filter(t => t.status === 'error');

    return {
      totalTraces: traces.length,
      completedTraces: completedTraces.length,
      errorTraces: errorTraces.length,
      averageDuration: completedTraces.length > 0
        ? completedTraces.reduce((sum, t) => sum + (t.duration || 0), 0) / completedTraces.length
        : 0,
      totalSpans: this.spans.size,
      totalMetrics: this.metrics.length
    };
  }

  /**
   * Clear old data
   * @param {number} olderThan - Milliseconds
   */
  cleanup(olderThan = 24 * 60 * 60 * 1000) {
    const cutoff = Date.now() - olderThan;
    let removed = 0;

    for (const [id, trace] of this.traces.entries()) {
      if (trace.startTime < cutoff) {
        // Clean up associated spans
        if (trace.spans) {
          trace.spans.forEach(spanId => this.spans.delete(spanId));
        }
        this.traces.delete(id);
        removed++;
      }
    }

    // SECURITY: Use structured logging
    logStructured('info', 'cleanup_completed', {
      removed,
      cutoff: new Date(cutoff).toISOString()
    });
  }
}

// Singleton instance
let globalTracer = null;

module.exports = {
  VaalTracer,
  getTracer: (config) => {
    if (!globalTracer) {
      globalTracer = new VaalTracer(config);
    }
    return globalTracer;
  },
  createTracer: (config) => new VaalTracer(config)
};
