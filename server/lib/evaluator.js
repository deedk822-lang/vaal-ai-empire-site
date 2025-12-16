// Vaal AI Empire - LLM Evaluation Framework
// Advanced evaluation metrics inspired by Opik

class LLMEvaluator {
  constructor(config = {}) {
    this.config = config;
    this.results = [];
  }

  /**
   * Evaluate hallucination
   * @param {string} input - Original input
   * @param {string} output - LLM output
   * @param {array} context - Source context
   * @returns {object} Score and reason
   */
  async evaluateHallucination(input, output, context) {
    // Simple keyword-based hallucination detection
    const contextText = Array.isArray(context) ? context.join(' ') : context;
    const outputWords = output.toLowerCase().split(/\s+/);
    const contextWords = new Set(contextText.toLowerCase().split(/\s+/));

    let supportedWords = 0;
    let totalWords = outputWords.length;

    outputWords.forEach(word => {
      if (word.length > 3 && contextWords.has(word)) {
        supportedWords++;
      }
    });

    const score = totalWords > 0 ? (supportedWords / totalWords) : 1.0;

    return {
      score: Math.min(score, 1.0),
      reason: score > 0.7 ? 'Output well-supported by context' : 'Potential hallucination detected',
      value: score > 0.7 ? 1.0 : 0.0,
      metadata: {
        supportedWords,
        totalWords,
        coveragePercent: (score * 100).toFixed(2)
      }
    };
  }

  /**
   * Evaluate answer relevance
   * @param {string} input - User question
   * @param {string} output - LLM answer
   * @returns {object}
   */
  async evaluateAnswerRelevance(input, output) {
    const inputWords = new Set(input.toLowerCase().split(/\s+/).filter(w => w.length > 3));
    const outputWords = output.toLowerCase().split(/\s+/);

    let matchedWords = 0;
    outputWords.forEach(word => {
      if (word.length > 3 && inputWords.has(word)) {
        matchedWords++;
      }
    });

    const score = inputWords.size > 0 ? (matchedWords / inputWords.size) : 0;

    return {
      score: Math.min(score, 1.0),
      reason: score > 0.5 ? 'Answer is relevant to question' : 'Answer may not address the question',
      value: score > 0.5 ? 1.0 : 0.0,
      metadata: {
        matchedWords,
        totalQuestionWords: inputWords.size
      }
    };
  }

  /**
   * Evaluate context precision
   * @param {string} input
   * @param {array} context
   * @returns {object}
   */
  async evaluateContextPrecision(input, context) {
    const inputWords = new Set(input.toLowerCase().split(/\s+/).filter(w => w.length > 3));
    let relevantChunks = 0;

    context.forEach(chunk => {
      const chunkWords = chunk.toLowerCase().split(/\s+/);
      const hasRelevantWords = chunkWords.some(word => inputWords.has(word));
      if (hasRelevantWords) relevantChunks++;
    });

    const score = context.length > 0 ? (relevantChunks / context.length) : 0;

    return {
      score,
      reason: score > 0.7 ? 'Context is highly relevant' : 'Context may contain noise',
      value: score,
      metadata: {
        relevantChunks,
        totalChunks: context.length
      }
    };
  }

  /**
   * Evaluate moderation (content safety)
   * @param {string} text
   * @returns {object}
   */
  async evaluateModeration(text) {
    const lowerText = text.toLowerCase();
    const flaggedTerms = ['offensive', 'hate', 'violence', 'explicit'];
    
    const hasFlagged = flaggedTerms.some(term => lowerText.includes(term));

    return {
      score: hasFlagged ? 0.0 : 1.0,
      reason: hasFlagged ? 'Content flagged for review' : 'Content appears safe',
      value: hasFlagged ? 0.0 : 1.0,
      flagged: hasFlagged
    };
  }

  /**
   * Run evaluation suite
   * @param {object} params
   * @returns {object} All evaluation results
   */
  async runEvaluation(params) {
    const { input, output, context } = params;
    const results = {};

    if (context) {
      results.hallucination = await this.evaluateHallucination(input, output, context);
      results.contextPrecision = await this.evaluateContextPrecision(input, context);
    }

    results.answerRelevance = await this.evaluateAnswerRelevance(input, output);
    results.moderation = await this.evaluateModeration(output);

    // Calculate overall score
    const scores = Object.values(results).map(r => r.score);
    results.overall = {
      score: scores.reduce((a, b) => a + b, 0) / scores.length,
      passed: scores.every(s => s > 0.6)
    };

    this.results.push({
      timestamp: Date.now(),
      ...results
    });

    return results;
  }

  /**
   * Get evaluation statistics
   * @returns {object}
   */
  getStats() {
    if (this.results.length === 0) {
      return { totalEvaluations: 0 };
    }

    const avgScore = this.results.reduce((sum, r) => sum + (r.overall?.score || 0), 0) / this.results.length;
    const passed = this.results.filter(r => r.overall?.passed).length;

    return {
      totalEvaluations: this.results.length,
      averageScore: avgScore,
      passRate: (passed / this.results.length) * 100,
      passed,
      failed: this.results.length - passed
    };
  }
}

module.exports = { LLMEvaluator };