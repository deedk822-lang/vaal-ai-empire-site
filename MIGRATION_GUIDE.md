# 🚀 MCP Gateway Migration Guide

## Overview

This guide documents the migration of MCP (Model Context Protocol) gateway scripts and monetization features from [The-lab-verse-monitoring-](https://github.com/deedk822-lang/The-lab-verse-monitoring-) into the Vaal AI Empire platform.

---

## 📦 What's Being Migrated

### 1. MCP Gateway Scripts

**Source Location:** `The-lab-verse-monitoring-/mcp-server/`

**Destination:** `vaal-ai-empire-site/mcp-gateway/`

**Files:**
- `huggingface-gateway.js` - HuggingFace AI models, datasets, and inference
- `socialpilot-gateway.js` - Social media scheduling and analytics
- `unito-gateway.js` - Two-way sync between 60+ productivity tools
- `wpcom-gateway.js` - WordPress.com blog post management
- `package.json` - Dependencies: @modelcontextprotocol/sdk, dotenv
- `setup.sh` - Automated installation script

### 2. Gateway API Endpoints

**Main Gateway:**
```
POST /api/gateway/v1/chat/completions
```

**MCP-Specific Endpoints:**
```
POST /api/mcp/huggingface/messages
POST /api/mcp/socialpilot/messages
POST /api/mcp/unito/messages
POST /api/mcp/wpcom/messages
```

### 3. Monetization System

**Existing in Lab-Verse:**
- Stripe subscription billing (3 tiers)
- Usage-based rate limiting
- Multi-tenant white-label support
- Webhook handling

**To Integrate with Vaal AI:**
- Current plans: Vaal Starter (R999/mo), Vaal Empire (R2,999/mo)
- New MCP tiers to add: Starter ($29), Pro ($99), Enterprise ($299)

---

## 🛠 Step-by-Step Migration

### Phase 1: File Transfer & Setup

#### 1.1 Create Directory Structure

```bash
cd vaal-ai-empire-site

# Create MCP gateway directory
mkdir -p mcp-gateway

# Create API routes directory
mkdir -p pages/api/mcp
```

#### 1.2 Copy Gateway Scripts

**Manual Method:**
```bash
# Clone source repo (if not already done)
git clone https://github.com/deedk822-lang/The-lab-verse-monitoring-.git ../lab-verse

# Copy MCP server files
cp ../lab-verse/mcp-server/huggingface-gateway.js ./mcp-gateway/
cp ../lab-verse/mcp-server/socialpilot-gateway.js ./mcp-gateway/
cp ../lab-verse/mcp-server/unito-gateway.js ./mcp-gateway/
cp ../lab-verse/mcp-server/wpcom-gateway.js ./mcp-gateway/
cp ../lab-verse/mcp-server/package.json ./mcp-gateway/
cp ../lab-verse/mcp-server/setup.sh ./mcp-gateway/
```

**Or use this automated script:**

Create `scripts/migrate-mcp.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Migrating MCP Gateways from Lab-Verse-Monitoring"

# Check if source exists
if [ ! -d "../The-lab-verse-monitoring-" ]; then
  echo "Cloning source repository..."
  cd ..
  git clone https://github.com/deedk822-lang/The-lab-verse-monitoring-.git
  cd vaal-ai-empire-site
fi

# Create directories
mkdir -p mcp-gateway pages/api/mcp

# Copy files
echo "Copying gateway scripts..."
cp ../The-lab-verse-monitoring-/mcp-server/*.js ./mcp-gateway/ 2>/dev/null || true
cp ../The-lab-verse-monitoring-/mcp-server/package.json ./mcp-gateway/
cp ../The-lab-verse-monitoring-/mcp-server/setup.sh ./mcp-gateway/

echo "✅ Files copied successfully"

# Install dependencies
cd mcp-gateway
echo "Installing MCP dependencies..."
npm install

echo ""
echo "✅ Migration complete!"
echo ""
echo "Next steps:"
echo "1. Configure environment variables in server/.env"
echo "2. Create API route handlers in pages/api/mcp/"
echo "3. Test each gateway individually"
```

**Run migration:**
```bash
chmod +x scripts/migrate-mcp.sh
./scripts/migrate-mcp.sh
```

#### 1.3 Update Environment Variables

**Add to `server/.env`:**

```env
# Existing Vaal AI vars
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STARTER_PRICE_ID=price_...
EMPIRE_PRICE_ID=price_...
DOMAIN=http://localhost:4242

# New MCP Gateway vars
GATEWAY_URL=http://localhost:4242
GATEWAY_API_KEY=your-secure-gateway-key-here

# HuggingFace
HF_API_TOKEN=hf_xxxxxxxxxxxxx

# SocialPilot
SOCIALPILOT_ACCESS_TOKEN=sp_xxxxxxxxxxxxx

# Unito
UNITO_ACCESS_TOKEN=unito_xxxxxxxxxxxxx

# WordPress.com
WORDPRESS_COM_OAUTH_TOKEN=wpcom_xxxxxxxxxxxxx

# OpenTelemetry (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-endpoint
```

**Create `server/.env.example`:**
```bash
cp server/.env server/.env.example
# Remove actual tokens, keep variable names
```

---

### Phase 2: API Route Integration

#### 2.1 Create Main Gateway Endpoint

**File:** `pages/api/gateway/v1/chat/completions.js`

```javascript
// Main MCP gateway endpoint for Vaal AI Empire
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Authentication
  const authHeader = req.headers.authorization;
  const gatewayKey = process.env.GATEWAY_API_KEY;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing authorization header' });
  }

  const token = authHeader.substring(7);
  if (token !== gatewayKey) {
    return res.status(401).json({ error: 'Invalid API key' });
  }

  // Rate limiting check (implement based on subscription tier)
  // TODO: Check user's subscription and enforce rate limits

  try {
    const { model, messages } = req.body;

    // Route to appropriate MCP gateway based on model
    let response;
    if (model.includes('hf')) {
      response = await forwardToHuggingFace(messages);
    } else if (model.includes('socialpilot')) {
      response = await forwardToSocialPilot(messages);
    } else if (model.includes('unito')) {
      response = await forwardToUnito(messages);
    } else if (model.includes('wpcom')) {
      response = await forwardToWordPress(messages);
    } else {
      return res.status(400).json({ error: 'Unknown model' });
    }

    res.status(200).json(response);
  } catch (error) {
    console.error('Gateway error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

async function forwardToHuggingFace(messages) {
  // Implementation
  return { success: true, data: {} };
}

async function forwardToSocialPilot(messages) {
  // Implementation
  return { success: true, data: {} };
}

async function forwardToUnito(messages) {
  // Implementation
  return { success: true, data: {} };
}

async function forwardToWordPress(messages) {
  // Implementation
  return { success: true, data: {} };
}
```

#### 2.2 Create Individual MCP Proxies

**Example:** `pages/api/mcp/huggingface.js`

```javascript
import { spawn } from 'child_process';
import path from 'path';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const mcpServerPath = path.join(process.cwd(), 'mcp-gateway/huggingface-gateway.js');
    
    // Spawn MCP server process
    const mcpProcess = spawn('node', [mcpServerPath], {
      env: {
        ...process.env,
        HF_API_TOKEN: process.env.HF_API_TOKEN,
        GATEWAY_KEY: process.env.GATEWAY_API_KEY
      }
    });

    // Handle MCP server output
    let output = '';
    mcpProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    mcpProcess.stderr.on('data', (data) => {
      console.error('MCP Server Error:', data.toString());
    });

    mcpProcess.on('close', (code) => {
      if (code === 0) {
        res.status(200).json(JSON.parse(output));
      } else {
        res.status(500).json({ error: 'MCP server failed' });
      }
    });

    // Send request to MCP server
    mcpProcess.stdin.write(JSON.stringify(req.body));
    mcpProcess.stdin.end();

  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: error.message });
  }
}
```

---

### Phase 3: Frontend Integration

#### 3.1 Update Pricing Page

**Add to `pricing.html`:**

```html
<!-- Existing Vaal AI Plans -->
<div class="pricing-card">
  <h3>Vaal Starter</h3>
  <p class="price">R999/mo</p>
  <ul>
    <li>✓ Financial Sentinel</li>
    <li>✓ Guardian alerts</li>
    <li>✓ Email support</li>
  </ul>
  <button data-plan="starter">Start Free Trial</button>
</div>

<!-- NEW: MCP Gateway Add-ons -->
<div class="pricing-card addon">
  <h3>🚀 MCP Gateway Access</h3>
  <p class="price">+$99/mo</p>
  <ul>
    <li>✓ HuggingFace AI Models</li>
    <li>✓ Social Media Automation</li>
    <li>✓ Tool Synchronization</li>
    <li>✓ WordPress Management</li>
    <li>✓ 10K API calls/month</li>
  </ul>
  <button data-plan="mcp-addon">Add to Plan</button>
</div>
```

#### 3.2 Create Dashboard Page

**File:** `dashboard.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Vaal AI Dashboard</title>
  <link rel="stylesheet" href="/css/styles.css">
</head>
<body>
  <div class="dashboard">
    <h1>MCP Gateway Dashboard</h1>

    <!-- API Key Section -->
    <section class="api-keys">
      <h2>Your API Key</h2>
      <div class="key-display">
        <code id="api-key">Loading...</code>
        <button onclick="copyApiKey()">Copy</button>
      </div>
    </section>

    <!-- Usage Stats -->
    <section class="usage-stats">
      <h2>Usage This Month</h2>
      <div class="stats-grid">
        <div class="stat">
          <h3>API Calls</h3>
          <p id="api-calls">0 / 10,000</p>
        </div>
        <div class="stat">
          <h3>HuggingFace</h3>
          <p id="hf-calls">0</p>
        </div>
        <div class="stat">
          <h3>SocialPilot</h3>
          <p id="sp-calls">0</p>
        </div>
        <div class="stat">
          <h3>WordPress</h3>
          <p id="wp-calls">0</p>
        </div>
      </div>
    </section>

    <!-- Quick Test -->
    <section class="test-gateway">
      <h2>Test Gateway</h2>
      <select id="gateway-select">
        <option value="huggingface">HuggingFace</option>
        <option value="socialpilot">SocialPilot</option>
        <option value="unito">Unito</option>
        <option value="wpcom">WordPress</option>
      </select>
      <textarea id="test-input" placeholder="Enter test query"></textarea>
      <button onclick="testGateway()">Test</button>
      <pre id="test-output"></pre>
    </section>
  </div>

  <script src="/js/dashboard.js"></script>
</body>
</html>
```

---

### Phase 4: Testing

#### 4.1 Test Each Gateway

**Create:** `scripts/test-gateways.sh`

```bash
#!/bin/bash
set -e

echo "🧪 Testing MCP Gateways"
echo ""

# Load environment
source server/.env

BASE_URL="http://localhost:4242"

# Test HuggingFace
echo "1️⃣ Testing HuggingFace Gateway..."
curl -X POST "$BASE_URL/api/mcp/huggingface" \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hf-mcp",
    "messages": [{"role":"user","content":"hf_list_models {\"search\":\"gpt2\"}"}]
  }' | jq .

echo ""

# Test SocialPilot
echo "2️⃣ Testing SocialPilot Gateway..."
curl -X POST "$BASE_URL/api/mcp/socialpilot" \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "socialpilot-mcp",
    "messages": [{"role":"user","content":"sp_list_accounts {}"}]
  }' | jq .

echo ""
echo "✅ Tests complete!"
```

**Run tests:**
```bash
chmod +x scripts/test-gateways.sh
./scripts/test-gateways.sh
```

#### 4.2 Test Stripe Integration

```bash
# Test checkout with MCP addon
curl -X POST http://localhost:4242/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "empire",
    "addons": ["mcp-gateway"]
  }'
```

---

### Phase 5: Deployment

#### 5.1 Update Server Package

**Add to `server/package.json`:**

```json
{
  "scripts": {
    "start": "node server.js",
    "mcp:start": "cd ../mcp-gateway && npm run start:all",
    "dev": "concurrently \"npm start\" \"npm run mcp:start\""
  },
  "devDependencies": {
    "concurrently": "^8.0.0"
  }
}
```

#### 5.2 Deploy to Production

```bash
# Build and deploy
npm run build

# Set production environment variables
export NODE_ENV=production
export GATEWAY_URL=https://vaal-ai-empire.co.za

# Start all services
npm run dev
```

---

## 📊 Revenue Integration

### Pricing Structure

**Vaal AI Core Plans** (Existing):
- Vaal Starter: R999/mo
- Vaal Empire: R2,999/mo

**MCP Gateway Add-ons** (New):
- Basic: +$49/mo (5K API calls)
- Pro: +$99/mo (10K API calls)
- Enterprise: +$199/mo (Unlimited)

**White-Label** (New):
- Agency License: $999/mo
- Setup Fee: $599 one-time

### Updated Stripe Products

Create these in [Stripe Dashboard](https://dashboard.stripe.com/products):

1. **MCP Gateway Basic** - $49/month recurring
2. **MCP Gateway Pro** - $99/month recurring
3. **MCP Gateway Enterprise** - $199/month recurring
4. **Agency White-Label** - $999/month recurring
5. **Setup Service** - $599 one-time

---

## ✅ Post-Migration Checklist

### Technical
- [ ] All gateway scripts copied and tested
- [ ] API routes created and working
- [ ] Environment variables configured
- [ ] Rate limiting implemented
- [ ] Authentication working
- [ ] Error handling tested

### Business
- [ ] Stripe products created
- [ ] Pricing page updated
- [ ] Dashboard launched
- [ ] Documentation published
- [ ] Support channels ready

### Marketing
- [ ] Landing page for MCP features
- [ ] Demo video recorded
- [ ] Case studies prepared
- [ ] Email campaign scheduled

---

## 🆘 Troubleshooting

### "Cannot find module @modelcontextprotocol/sdk"

```bash
cd mcp-gateway
npm install
```

### "Gateway authentication failed"

```bash
# Check environment variable is set
echo $GATEWAY_API_KEY

# If empty, add to .env
echo "GATEWAY_API_KEY=your-key-here" >> server/.env
```

### "MCP server not responding"

```bash
# Check if gateway scripts are executable
chmod +x mcp-gateway/*.js

# Test individual gateway
node mcp-gateway/huggingface-gateway.js
```

---

## 📚 Resources

- **Source Repo:** https://github.com/deedk822-lang/The-lab-verse-monitoring-
- **MCP SDK Docs:** https://modelcontextprotocol.io
- **Stripe API:** https://stripe.com/docs/api
- **HuggingFace API:** https://huggingface.co/docs/api-inference
- **SocialPilot API:** https://socialpilot.co/developers
- **Unito API:** https://guide.unito.io/api-documentation
- **WordPress API:** https://developer.wordpress.com/docs/api/

---

## 🚀 Launch Timeline

**Week 1:**
- Day 1-2: File migration and setup
- Day 3-4: API route creation
- Day 5-7: Testing and debugging

**Week 2:**
- Day 1-2: Frontend integration
- Day 3-4: Stripe product setup
- Day 5-7: Documentation

**Week 3:**
- Day 1-3: Beta testing with select users
- Day 4-5: Bug fixes and polish
- Day 6-7: Public launch

---

**Questions?** Open an issue: https://github.com/deedk822-lang/vaal-ai-empire-site/issues

**Built with ❤️ for Vaal AI Empire** 🇿🇦
