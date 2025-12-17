# Vaal AI Empire - Agent Libraries

## 🤖 Overview

This directory contains the core AI agent libraries that power the Vaal AI Empire's three autonomous engines:

1. **Financial Sentinel** - Tax recovery and compliance
2. **Guardian Engine** - Crisis detection and response
3. **Talent Accelerator** - Skills assessment and placement

---

## 📚 Libraries

### **Core Infrastructure**

#### `lib/cohere-search.js`
**Semantic Search Engine**
- Powered by Cohere's `embed-english-v3.0` (1024-dim embeddings)
- HNSW index for fast vector search
- Reranking with `rerank-english-v2.0` for precision
- Support for multiple knowledge bases
- Index persistence to disk

**Usage:**
```javascript
const CohereSemanticSearch = require('./lib/cohere-search');
const search = new CohereSemanticSearch(process.env.COHERE_API_KEY);

// Initialize index
await search.initializeIndex('my_knowledge', documents);

// Search
const results = await search.search('my_knowledge', 'tax incentives for SMEs', {
  k: 10,
  rerank: true,
  topN: 3
});
```

---

### **Financial Sentinel**

#### `lib/sars-knowledge-base.js`
**SARS Tax Regulations Expert**
- Semantic search over Section 12H & ETI regulations
- Automatic tax recovery calculations
- Real SARS formulas and rates
- Citation of official sources

**Usage:**
```javascript
const SARSKnowledgeBase = require('./lib/sars-knowledge-base');
const sarsKB = new SARSKnowledgeBase(process.env.COHERE_API_KEY);

// Initialize
await sarsKB.initialize();

// Query regulations
const answer = await sarsKB.query('How much can I claim for NQF level 5 learnerships?');

// Calculate Section 12H recovery
const recovery = await sarsKB.calculateSection12H({
  learnerships: [
    { id: 1, nqf_level: 5, disabled: false, completed: true },
    { id: 2, nqf_level: 8, disabled: false, completed: true }
  ]
});
// Returns: { total_recovery: 60000, tax_saving_28_percent: 16800, ... }

// Calculate ETI recovery
const etiRecovery = await sarsKB.calculateETI({
  employees: [
    { id: 1, age: 24, monthly_salary: 4000, months_employed: 6 },
    { id: 2, age: 27, monthly_salary: 5500, months_employed: 15 }
  ]
});
// Returns: { monthly_eti: 2625, annual_eti: 31500, ... }
```

---

### **Guardian Engine**

#### `lib/crisis-detector.js`
**Crisis Intelligence System**
- Semantic search over crisis patterns
- Real-time load-shedding risk assessment
- Business impact analysis by sector
- Predictive indicators based on Eskom metrics

**Usage:**
```javascript
const CrisisDetector = require('./lib/crisis-detector');
const guardian = new CrisisDetector(process.env.COHERE_API_KEY);

// Initialize
await guardian.initialize();

// Query crisis intelligence
const intel = await guardian.query('What happens during Stage 4 loadshedding?');

// Assess current risk
const risk = guardian.assessLoadsheddingRisk({
  eaf: 58.2,  // Energy Availability Factor
  unplanned_outages_mw: 12000,
  coal_stockpile_days: 18
});
// Returns: { overall_risk: 'Critical', alert_level: 'RED', ... }

// Get business impact
const impact = guardian.getBusinessImpact('manufacturing', 4);
// Returns: { sector: 'manufacturing', stage: 4, impact: '...', severity: 'Severe' }
```

---

## 🔧 Installation

### **Dependencies**
```bash
npm install cohere-ai hnswlib-node
```

### **Environment Variables**
```bash
# .env
COHERE_API_KEY=your_cohere_api_key_here
```

Get your Cohere API key: https://dashboard.cohere.com/api-keys

---

## 🚀 Quick Start

### **1. Initialize All Agents**
```javascript
const SARSKnowledgeBase = require('./agents/lib/sars-knowledge-base');
const CrisisDetector = require('./agents/lib/crisis-detector');

async function initializeAgents() {
  // Financial Sentinel
  const sarsKB = new SARSKnowledgeBase(process.env.COHERE_API_KEY);
  await sarsKB.initialize();
  
  // Guardian Engine
  const guardian = new CrisisDetector(process.env.COHERE_API_KEY);
  await guardian.initialize();
  
  return { sarsKB, guardian };
}

initializeAgents().then(({ sarsKB, guardian }) => {
  console.log('✅ All agents initialized!');
});
```

### **2. Express API Integration**
```javascript
const express = require('express');
const app = express();

let agents;

// Initialize agents on startup
initializeAgents().then(initialized => {
  agents = initialized;
  console.log('✅ Agents ready');
});

// API endpoint for tax calculation
app.post('/api/calculate-tax-recovery', async (req, res) => {
  const { learnerships, employees } = req.body;
  
  // Calculate Section 12H
  const section12h = await agents.sarsKB.calculateSection12H({ learnerships });
  
  // Calculate ETI
  const eti = await agents.sarsKB.calculateETI({ employees });
  
  res.json({
    section_12h: section12h,
    eti: eti,
    total_recovery: section12h.total_recovery + eti.annual_eti,
    total_tax_saving: section12h.tax_saving_28_percent + (eti.annual_eti * 0.28)
  });
});

// API endpoint for crisis assessment
app.post('/api/assess-crisis-risk', async (req, res) => {
  const { eaf, unplanned_outages_mw, coal_stockpile_days } = req.body;
  
  const risk = agents.guardian.assessLoadsheddingRisk({
    eaf,
    unplanned_outages_mw,
    coal_stockpile_days
  });
  
  res.json(risk);
});

app.listen(4242, () => console.log('🔥 Vaal AI Empire API running on :4242'));
```

---

## 📊 Performance

### **Cohere Embed v3.0**
- **Dimensions:** 1024
- **Speed:** ~1000 texts/second
- **Accuracy:** State-of-the-art on MTEB benchmark

### **HNSW Index**
- **Search Speed:** <1ms for 10K vectors
- **Recall:** >99% @ k=10
- **Memory:** ~4KB per vector

### **Rerank v2.0**
- **Speed:** ~100 documents/second
- **Precision:** +15% vs. embedding-only search

---

## 🧪 Testing

```bash
# Test SARS Knowledge Base
node -e "
const SARS = require('./agents/lib/sars-knowledge-base');
(async () => {
  const kb = new SARS(process.env.COHERE_API_KEY);
  await kb.initialize();
  const result = await kb.query('Section 12H allowances');
  console.log(result);
})();
"

# Test Crisis Detector
node -e "
const Crisis = require('./agents/lib/crisis-detector');
(async () => {
  const detector = new Crisis(process.env.COHERE_API_KEY);
  await detector.initialize();
  const risk = detector.assessLoadsheddingRisk({ eaf: 58 });
  console.log(risk);
})();
"
```

---

## 📈 Roadmap

### **Phase 1: Core Agents** ✅
- [x] Cohere semantic search infrastructure
- [x] SARS knowledge base (Section 12H + ETI)
- [x] Crisis detector (load-shedding)

### **Phase 2: Advanced Features** 🚧
- [ ] Talent Accelerator agent
- [ ] Real-time Eskom API integration
- [ ] Multi-province knowledge bases
- [ ] International benchmarking

### **Phase 3: Production** 📋
- [ ] Agent orchestration layer
- [ ] Caching and optimization
- [ ] Monitoring and telemetry
- [ ] A/B testing framework

---

## 🔗 Resources

- **Cohere Documentation:** https://docs.cohere.com/
- **SARS Official:** https://www.sars.gov.za/
- **Eskom Load-shedding:** https://loadshedding.eskom.co.za/
- **HNSW Algorithm:** https://arxiv.org/abs/1603.09320

---

**Built in the Vaal Triangle. Powered by Cohere. Verified by SARS.**

© 2025 Vaal AI Empire
