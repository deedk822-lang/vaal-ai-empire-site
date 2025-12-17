/**
 * Vaal AI Empire - Crisis Detection Library
 * 
 * Provides real-time crisis detection for the Guardian Engine agent.
 * Monitors load-shedding, economic disruptions, and business risks.
 */

const CohereSemanticSearch = require('./cohere-search');
const path = require('path');
const fs = require('fs');

class CrisisDetector {
  constructor(cohereApiKey) {
    this.search = new CohereSemanticSearch(cohereApiKey);
    this.initialized = false;
    this.dataPath = path.join(__dirname, '../../data/crisis');
  }

  /**
   * Initialize crisis detection knowledge base
   */
  async initialize() {
    console.log('[Crisis Detector] Initializing crisis knowledge base...');

    // Load load-shedding data
    const loadshedPath = path.join(this.dataPath, 'loadshedding_2024.json');
    const loadshed = JSON.parse(fs.readFileSync(loadshedPath, 'utf-8'));

    // Load economic context
    const economicPath = path.join(this.dataPath, 'south_africa_economic_context.json');
    const economic = JSON.parse(fs.readFileSync(economicPath, 'utf-8'));

    // Prepare documents for embedding
    const documents = [];

    // Load-shedding overview
    documents.push({
      id: 'loadshedding_2024_status',
      source: 'Eskom Load-shedding 2024',
      text: `Load-shedding status 2024: ${loadshed['2024_performance'].status}. ` +
            `Consecutive loadshedding-free days: ${loadshed['2024_performance'].consecutive_days_no_loadshedding_as_of_dec_2024}. ` +
            `Last load-shedding: ${loadshed['2024_performance'].last_loadshedding_date}. ` +
            `Energy Availability Factor (EAF) Q2 2024: ${loadshed['2024_performance'].key_improvements.energy_availability_factor_eaf.q2_2024}. ` +
            `Peak EAF July 2024: ${loadshed['2024_performance'].key_improvements.energy_availability_factor_eaf.peak_july_2024}. ` +
            `Unplanned outages current: ${loadshed['2024_performance'].key_improvements.unplanned_outages_uclf.current_2024}.`,
      data: loadshed['2024_performance']
    });

    // Historical crisis data
    documents.push({
      id: 'loadshedding_2023_history',
      source: 'Eskom Load-shedding 2023',
      text: `Load-shedding 2023: ${loadshed.historical_crisis_years['2023'].total_loadshedding_days} days of load-shedding. ` +
            `Worst month: ${loadshed.historical_crisis_years['2023'].worst_month}. ` +
            `Highest stage reached: Stage ${loadshed.historical_crisis_years['2023'].highest_stage}. ` +
            `Economic impact: R${(loadshed.historical_crisis_years['2023'].economic_impact_estimate_zar / 1000000000).toFixed(1)} billion.`,
      data: loadshed.historical_crisis_years['2023']
    });

    // Predictive indicators
    loadshed.predictive_indicators.forEach((indicator, idx) => {
      documents.push({
        id: `indicator_${idx}`,
        source: 'Load-shedding Predictive Indicators',
        text: `Indicator: ${indicator.indicator}. ` +
              `Risk level: ${indicator.risk_level}. ` +
              `Likely outcome: ${indicator.likely_outcome}.`,
        data: indicator
      });
    });

    // Business impact by sector
    Object.entries(loadshed.business_impact_matrix).forEach(([sector, impacts]) => {
      documents.push({
        id: `impact_${sector}`,
        source: `Load-shedding Impact - ${sector}`,
        text: `Load-shedding impact on ${sector}: ` +
              `Stage 2 - ${impacts.stage_2}. ` +
              `Stage 4 - ${impacts.stage_4}. ` +
              `Stage 6 - ${impacts.stage_6}. ` +
              `Mitigation: ${impacts.mitigation}.`,
        data: impacts
      });
    });

    // Economic challenges
    economic.key_economic_challenges.forEach((challenge, idx) => {
      documents.push({
        id: `economic_challenge_${idx}`,
        source: 'SA Economic Challenges',
        text: `Economic challenge: ${challenge.challenge}. ` +
              `${Object.entries(challenge)
                .filter(([key]) => key !== 'challenge')
                .map(([key, value]) => `${key}: ${value}`)
                .join('. ')}.`,
        data: challenge
      });
    });

    console.log(`[Crisis Detector] Prepared ${documents.length} documents for embedding`);

    // Initialize semantic search index
    await this.search.initializeIndex('crisis_intelligence', documents);

    // Store raw data for analysis
    this.loadshedData = loadshed;
    this.economicData = economic;

    this.initialized = true;
    console.log('[Crisis Detector] Crisis detector initialized successfully');

    return {
      documents: documents.length,
      sources: ['Load-shedding', 'Economic Context'],
      status: 'ready'
    };
  }

  /**
   * Query crisis intelligence
   * @param {string} query - Natural language query
   * @param {Object} options - Search options
   */
  async query(query, options = {}) {
    if (!this.initialized) {
      throw new Error('Crisis Detector not initialized. Call initialize() first.');
    }

    const { topN = 3, threshold = 0.5 } = options;

    console.log(`[Crisis Detector] Query: ${query}`);

    const results = await this.search.search('crisis_intelligence', query, {
      k: 10,
      rerank: true,
      topN: topN
    });

    const filteredResults = results.filter(r => r.relevanceScore >= threshold);

    return {
      query: query,
      results: filteredResults.map(r => ({
        rank: r.rank,
        text: r.text,
        relevanceScore: r.relevanceScore,
        source: r.text.split(':')[0],
        confidence: r.relevanceScore >= 0.9 ? 'High' : 
                   r.relevanceScore >= 0.7 ? 'Medium' : 'Low'
      })),
      totalResults: filteredResults.length
    };
  }

  /**
   * Assess load-shedding risk based on current metrics
   * @param {Object} eskomMetrics - Current Eskom system metrics
   */
  assessLoadsheddingRisk(eskomMetrics) {
    const { eaf, unplanned_outages_mw, coal_stockpile_days } = eskomMetrics;

    const risks = [];
    let overallRisk = 'Low';
    let alertLevel = 'GREEN';

    // Check EAF threshold
    if (eaf < 60) {
      risks.push({
        indicator: 'Energy Availability Factor below 60%',
        current_value: eaf,
        threshold: 60,
        risk_level: 'Critical',
        likely_outcome: 'Stage 4-6 loadshedding imminent',
        action: 'Activate backup generators immediately'
      });
      overallRisk = 'Critical';
      alertLevel = 'RED';
    } else if (eaf < 65) {
      risks.push({
        indicator: 'Energy Availability Factor below 65%',
        current_value: eaf,
        threshold: 65,
        risk_level: 'High',
        likely_outcome: 'Stage 2-4 loadshedding within 48 hours',
        action: 'Prepare backup power systems'
      });
      overallRisk = 'High';
      alertLevel = 'ORANGE';
    }

    // Check unplanned outages
    if (unplanned_outages_mw && unplanned_outages_mw > 15000) {
      risks.push({
        indicator: 'Unplanned outages above 15,000 MW',
        current_value: unplanned_outages_mw,
        threshold: 15000,
        risk_level: 'Critical',
        likely_outcome: 'Stage 4-6 loadshedding imminent',
        action: 'Implement emergency protocols'
      });
      if (overallRisk !== 'Critical') overallRisk = 'Critical';
      alertLevel = 'RED';
    }

    // Check coal stockpile
    if (coal_stockpile_days && coal_stockpile_days < 20) {
      risks.push({
        indicator: 'Coal stockpile below 20 days',
        current_value: coal_stockpile_days,
        threshold: 20,
        risk_level: 'Medium',
        likely_outcome: 'Increased risk within 2-4 weeks',
        action: 'Monitor situation closely'
      });
      if (overallRisk === 'Low') overallRisk = 'Medium';
      if (alertLevel === 'GREEN') alertLevel = 'YELLOW';
    }

    return {
      timestamp: new Date().toISOString(),
      overall_risk: overallRisk,
      alert_level: alertLevel,
      risks: risks,
      recommendations: this._getRecommendations(overallRisk),
      source: this.loadshedData.data_sources[0]
    };
  }

  /**
   * Get business impact for specific sector and stage
   * @param {string} sector - Business sector (manufacturing, retail, it_services, sme_services)
   * @param {number} stage - Load-shedding stage (1-6)
   */
  getBusinessImpact(sector, stage) {
    const impacts = this.loadshedData.business_impact_matrix[sector];
    if (!impacts) {
      throw new Error(`Unknown sector: ${sector}`);
    }

    const stageKey = `stage_${stage}`;
    const impact = impacts[stageKey] || 'Unknown impact for this stage';

    return {
      sector: sector,
      stage: stage,
      impact: impact,
      mitigation: impacts.mitigation,
      severity: stage >= 4 ? 'Severe' : stage >= 2 ? 'Moderate' : 'Minor'
    };
  }

  _getRecommendations(riskLevel) {
    const recommendations = {
      'Critical': [
        'Activate all backup power systems immediately',
        'Reschedule critical operations to off-peak hours',
        'Alert all stakeholders of imminent disruption',
        'Implement emergency business continuity protocols'
      ],
      'High': [
        'Test backup generators and UPS systems',
        'Stock up on diesel/battery reserves',
        'Schedule flexible work arrangements',
        'Communicate potential disruptions to clients'
      ],
      'Medium': [
        'Monitor Eskom announcements closely',
        'Review business continuity plans',
        'Ensure backup systems are operational',
        'Consider demand-side management options'
      ],
      'Low': [
        'Maintain regular monitoring schedule',
        'Keep backup systems in standby mode',
        'Continue normal operations'
      ]
    };

    return recommendations[riskLevel] || recommendations['Low'];
  }
}

module.exports = CrisisDetector;
