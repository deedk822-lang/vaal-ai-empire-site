// Vaal AI Empire - Tracing & Observability System
// Inspired by Opik's comprehensive tracing architecture

const crypto = require('crypto');

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
    const trace = {
      id: traceId,
      name,
      startTime: Date.now(),
      endTime: null,
      metadata: {
        ...metadata,
        project: this.config.projectName,
        environment: this.config.environment
      },
      spans: [],
      status: 'running',
      error: null
    };

    this.traces.set(traceId, trace);
    console.log(`⚡ Trace started: ${name} [${traceId}]`);
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
      console.warn(`Trace not found: ${traceId}`);
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

    console.log(`✅ Trace completed: ${trace.name} [${traceId}] - ${trace.duration}ms`);
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
      console.warn(`Trace not found: ${traceId}`);
      return null;
    }

    const spanId = this.generateId();
    const span = {
      id: spanId,
      traceId,
      name,
      startTime: Date.now(),
      endTime: null,
      metadata,
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
    const metric = {
      timestamp: Date.now(),
      name,
      data,
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
      traces = traces.filter(t => t.name.includes(filters.name));
    }

    if (filters.limit) {
      traces = traces.slice(0, filters.limit);
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
      metrics = metrics.filter(m => m.name === filters.name);
    }

    if (filters.since) {
      metrics = metrics.filter(m => m.timestamp >= filters.since);
    }

    if (filters.limit) {
      metrics = metrics.slice(-filters.limit);
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
    const spanId = this.startSpan(traceId, 'llm_call', {
      model: params.model,
      provider: params.provider,
      inputTokens: params.inputTokens,
      prompt: params.prompt
    });

    return spanId;
  }

  /**
   * Complete LLM call
   * @param {string} spanId
   * @param {object} response
   */
  completeLLMCall(spanId, response) {
    this.endSpan(spanId, {
      output: response.output,
      outputTokens: response.outputTokens,
      totalTokens: response.totalTokens,
      cost: response.cost
    });

    this.recordMetric('llm_call_completed', {
      outputTokens: response.outputTokens,
      cost: response.cost
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
        this.traces.delete(id);
        removed++;
      }
    }

    console.log(`🧹 Cleaned up ${removed} old traces`);
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