/**
 * Vaal AI Empire - SARS Knowledge Base Library
 * 
 * Provides semantic search over SARS tax regulations for the Financial Sentinel agent.
 * Uses Cohere embeddings + reranking for accurate tax incentive retrieval.
 */

const CohereSemanticSearch = require('./cohere-search');
const path = require('path');
const fs = require('fs');

class SARSKnowledgeBase {
  constructor(cohereApiKey) {
    this.search = new CohereSemanticSearch(cohereApiKey);
    this.initialized = false;
    this.dataPath = path.join(__dirname, '../../data/sars');
  }

  /**
   * Initialize SARS knowledge base with Section 12H and ETI data
   */
  async initialize() {
    console.log('[SARS KB] Initializing SARS knowledge base...');

    // Load Section 12H data
    const section12hPath = path.join(this.dataPath, 'section_12h_learnerships.json');
    const section12h = JSON.parse(fs.readFileSync(section12hPath, 'utf-8'));

    // Load ETI data
    const etiPath = path.join(this.dataPath, 'eti_employment_incentive.json');
    const eti = JSON.parse(fs.readFileSync(etiPath, 'utf-8'));

    // Prepare documents for embedding
    const documents = [];

    // Section 12H documents
    documents.push({
      id: 'section_12h_overview',
      source: 'Section 12H - Learnership Allowances',
      text: `${section12h.regulation}: ${section12h.description}. Status: ${section12h.status}. ` +
            `Annual allowances: NQF 1-6 able-bodied R${section12h.allowances.annual_allowance.nqf_1_to_6.able_bodied}, ` +
            `disability R${section12h.allowances.annual_allowance.nqf_1_to_6.disability}. ` +
            `NQF 7-10 able-bodied R${section12h.allowances.annual_allowance.nqf_7_to_10.able_bodied}, ` +
            `disability R${section12h.allowances.annual_allowance.nqf_7_to_10.disability}. ` +
            `Completion allowances available upon learnership completion.`,
      data: section12h
    });

    // Add calculation examples
    section12h.calculation_examples.forEach((example, idx) => {
      documents.push({
        id: `section_12h_example_${idx}`,
        source: 'Section 12H - Calculation Example',
        text: `Section 12H Example: ${example.scenario}. ` +
              `Annual allowance: ${example.annual_allowance || 'N/A'}. ` +
              `Completion allowance: ${example.completion_allowance || 'N/A'}. ` +
              `Total deduction: ${example.total_deduction}. ` +
              `Tax saving at 28%: ${example.tax_saving_28_percent}. ` +
              `${example.notes || ''}`,
        data: example
      });
    });

    // Add documentation requirements
    documents.push({
      id: 'section_12h_docs',
      source: 'Section 12H - Documentation',
      text: `Section 12H documentation required: ${section12h.documentation_required.sars_forms.join(', ')}. ` +
            `Proof of registration: ${section12h.documentation_required.proof_of_registration}. ` +
            `Proof of completion: ${section12h.documentation_required.proof_of_completion}. ` +
            `Learner details: ${section12h.documentation_required.learner_details}.`,
      data: section12h.documentation_required
    });

    // ETI documents
    documents.push({
      id: 'eti_overview',
      source: 'Employment Tax Incentive (ETI)',
      text: `${eti.regulation}: ${eti.description}. ` +
            `Effective from ${eti.monthly_allowance_2025.effective_from}. ` +
            `Qualifying threshold: ${eti.monthly_allowance_2025.qualifying_threshold}. ` +
            `Minimum hours: ${eti.monthly_allowance_2025.minimum_hours}. ` +
            `First 12 months: Up to R1,500/month. Second 12 months: Up to R750/month. ` +
            `Eligibility: Employees aged 18-29, South African citizens or permanent residents.`,
      data: eti
    });

    // Add ETI calculation examples
    eti.calculation_examples.forEach((example, idx) => {
      documents.push({
        id: `eti_example_${idx}`,
        source: 'ETI - Calculation Example',
        text: `ETI Example: ${example.scenario}. ` +
              `${Object.entries(example)
                .filter(([key]) => key !== 'scenario')
                .map(([key, value]) => `${key}: ${value}`)
                .join('. ')}.`,
        data: example
      });
    });

    console.log(`[SARS KB] Prepared ${documents.length} documents for embedding`);

    // Initialize semantic search index
    await this.search.initializeIndex('sars_regulations', documents);

    this.initialized = true;
    console.log('[SARS KB] SARS knowledge base initialized successfully');

    return {
      documents: documents.length,
      sources: ['Section 12H', 'ETI'],
      status: 'ready'
    };
  }

  /**
   * Query SARS regulations using semantic search
   * @param {string} query - Natural language query
   * @param {Object} options - Search options
   */
  async query(query, options = {}) {
    if (!this.initialized) {
      throw new Error('SARS KB not initialized. Call initialize() first.');
    }

    const {
      topN = 3,
      includeContext = true,
      threshold = 0.5 // Minimum relevance score
    } = options;

    console.log(`[SARS KB] Query: ${query}`);

    // Search SARS regulations
    const results = await this.search.search('sars_regulations', query, {
      k: 10,
      rerank: true,
      topN: topN
    });

    // Filter by relevance threshold
    const filteredResults = results.filter(r => r.relevanceScore >= threshold);

    // Format response
    const response = {
      query: query,
      results: filteredResults.map(r => ({
        rank: r.rank,
        text: r.text,
        relevanceScore: r.relevanceScore,
        ...(includeContext && {
          source: r.text.split(':')[0],
          confidence: r.relevanceScore >= 0.9 ? 'High' : 
                     r.relevanceScore >= 0.7 ? 'Medium' : 'Low'
        })
      })),
      totalResults: filteredResults.length
    };

    console.log(`[SARS KB] Found ${response.totalResults} relevant results`);
    return response;
  }

  /**
   * Calculate Section 12H tax recovery for a company
   * @param {Object} companyData - Company learnership data
   */
  async calculateSection12H(companyData) {
    const { learnerships } = companyData;

    // Load Section 12H rates
    const section12hPath = path.join(this.dataPath, 'section_12h_learnerships.json');
    const section12h = JSON.parse(fs.readFileSync(section12hPath, 'utf-8'));

    let totalRecovery = 0;
    const breakdown = [];

    learnerships.forEach(learner => {
      const level = learner.nqf_level <= 6 ? 'nqf_1_to_6' : 'nqf_7_to_10';
      const ability = learner.disabled ? 'disability' : 'able_bodied';
      
      // Annual allowance
      const annualAllowance = section12h.allowances.annual_allowance[level][ability];
      
      // Completion allowance (if completed)
      const completionAllowance = learner.completed ? 
        section12h.allowances.completion_allowance[level][ability] : 0;

      const learnerTotal = annualAllowance + completionAllowance;
      totalRecovery += learnerTotal;

      breakdown.push({
        learner_id: learner.id,
        nqf_level: learner.nqf_level,
        disabled: learner.disabled,
        annual_allowance: annualAllowance,
        completion_allowance: completionAllowance,
        total: learnerTotal
      });
    });

    // Calculate tax saving at 28% corporate rate
    const taxSaving = totalRecovery * 0.28;

    return {
      regulation: 'Section 12H - Learnership Allowances',
      total_recovery: totalRecovery,
      tax_saving_28_percent: taxSaving,
      learnerships_count: learnerships.length,
      breakdown: breakdown,
      source: section12h.official_sources[0],
      last_verified: section12h.last_updated,
      confidence: 'Verified by SARS'
    };
  }

  /**
   * Calculate ETI tax recovery for a company
   * @param {Object} companyData - Company employee data
   */
  async calculateETI(companyData) {
    const { employees } = companyData;

    // Load ETI rates
    const etiPath = path.join(this.dataPath, 'eti_employment_incentive.json');
    const eti = JSON.parse(fs.readFileSync(etiPath, 'utf-8'));

    let totalMonthlyETI = 0;
    const breakdown = [];

    employees.forEach(employee => {
      // Check eligibility
      if (employee.age < 18 || employee.age > 29) return;
      if (employee.monthly_salary >= 7500) return;

      // Determine ETI amount based on salary and employment period
      let monthlyETI = 0;
      const monthsEmployed = employee.months_employed || 1;

      if (monthsEmployed <= 12) {
        // First 12 months
        if (employee.monthly_salary < 2500) {
          monthlyETI = employee.monthly_salary * 0.6; // 60%
        } else if (employee.monthly_salary >= 2500 && employee.monthly_salary < 5500) {
          monthlyETI = 1500;
        } else {
          monthlyETI = 1500 - (0.75 * (employee.monthly_salary - 5500));
        }
      } else {
        // Second 12 months
        if (employee.monthly_salary < 2500) {
          monthlyETI = employee.monthly_salary * 0.3; // 30%
        } else if (employee.monthly_salary >= 2500 && employee.monthly_salary < 5500) {
          monthlyETI = 750;
        } else {
          monthlyETI = 750 - (0.375 * (employee.monthly_salary - 5500));
        }
      }

      monthlyETI = Math.max(0, monthlyETI); // Ensure non-negative
      totalMonthlyETI += monthlyETI;

      breakdown.push({
        employee_id: employee.id,
        age: employee.age,
        salary: employee.monthly_salary,
        months_employed: monthsEmployed,
        monthly_eti: monthlyETI
      });
    });

    const annualETI = totalMonthlyETI * 12;

    return {
      regulation: 'Employment Tax Incentive (ETI)',
      monthly_eti: totalMonthlyETI,
      annual_eti: annualETI,
      qualifying_employees: breakdown.length,
      breakdown: breakdown,
      source: eti.official_sources[0],
      last_verified: eti.last_updated,
      confidence: 'Verified by SARS'
    };
  }
}

module.exports = SARSKnowledgeBase;
