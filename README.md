# ⚡ Vaal AI Empire

**Digital Sovereignty for South African SMEs**

Complete autonomous AI platform with PayFast subscription billing for the South African market.

🇿🇦 Built in the Vaal. Built for Africa.

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/deedk822-lang/vaal-ai-empire-site.git
cd vaal-ai-empire-site

# Run installer
chmod +x INSTALL.sh
./INSTALL.sh

# Configure PayFast
cd server
cp .env.example .env
# Edit .env with your PayFast merchant keys

# Start server
npm start
```

**Open:** http://localhost:3000

---

## 📦 What's Included

### Complete Website:
- ✅ Professional homepage
- ✅ Pricing page with 2 tiers (Vaal Starter, Vaal Empire)
- ✅ Success/cancel pages
- ✅ Responsive design
- ✅ Mobile-first approach

### PayFast Integration (South Africa):
- ✅ Payment gateway integration
- ✅ ITN (Instant Transaction Notification) handling
- ✅ ZAR currency
- ✅ 7-day free trials
- ✅ Sandbox and Production modes

### Backend:
- ✅ Node.js/Express server
- ✅ Complete API
- ✅ APEX Security Framework v2.0 compliant
- ✅ POPIA compliant
- ✅ Production ready

### AI Capabilities:
- ✅ Financial Sentinel Agent (Perplexity + SEC EDGAR)
- ✅ WhatsApp Business API integration
- ✅ XRPL Settlement (RLUSD stablecoin)
- ✅ Multi-language support (African languages)

---

## 💰 Pricing Plans

| Plan | Price | Features |
|------|-------|----------|
| **Vaal Starter** | R999/mo | Financial Sentinel, Guardian alerts, Email support |
| **Vaal Empire** | R2,999/mo | All features + Talent Accelerator + Priority support |

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Backend** | Node.js, Express |
| **Payments** | PayFast (South Africa) |
| **AI/ML** | Python, AG2 (AutoGen) |
| **Blockchain** | XRPL (RLUSD) |
| **Hosting** | Vercel / Self-hosted |
| **Currency** | ZAR (South African Rand) |

---

## ⚙️ Configuration

### Required Environment Variables:

```bash
# PayFast Configuration
PAYFAST_MERCHANT_ID=your_merchant_id
PAYFAST_MERCHANT_KEY=your_merchant_key
PAYFAST_SIGNATURE_SALT=your_passphrase
PAYFAST_SANDBOX=true  # Set to false for production

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_APP_SECRET=your_app_secret
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Perplexity Financial Intelligence
PERPLEXITY_API_KEY=your_perplexity_key

# Database (Optional)
MONGODB_URI=mongodb://localhost:27017/vaal_ai

# Security
JWT_SECRET=your_jwt_secret
```

See `server/.env.example` for complete list.

---

## 🧪 Testing PayFast Integration

### Sandbox Mode:
1. Visit http://localhost:3000/pricing.html
2. Select a plan and click "Subscribe"
3. Use PayFast sandbox credentials
4. Verify redirect to success page
5. Check ITN webhook received

### Production Deployment:
1. Switch PayFast to live mode (set `PAYFAST_SANDBOX=false`)
2. Update domain in environment variables
3. Configure ITN webhook URL in PayFast dashboard
4. Test with real transaction (small amount)

---

## 🚀 Deployment

### Production Checklist:
- [ ] Switch to live PayFast keys
- [ ] Update DOMAIN in .env
- [ ] Set up ITN webhook endpoint
- [ ] Configure SSL/TLS
- [ ] Test payment flow
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable WhatsApp Business API production mode

### Deploy Commands:
```bash
cd server
npm install --production
npm start
```

---

## 📁 Project Structure

```
vaal-ai-empire-site/
├── index.html              # Homepage
├── pricing.html            # Pricing page
├── success.html            # Payment success
├── canceled.html           # Checkout canceled
├── css/
│   └── styles.css          # All styles
├── js/
│   └── main.js             # Frontend JS
├── server/
│   ├── server.js           # Express server (PayFast + WhatsApp)
│   ├── package.json        # Dependencies
│   ├── routes/
│   │   ├── whatsapp.js     # WhatsApp webhook routes
│   │   └── paymentRoutes.js # PayFast routes
│   ├── services/
│   │   ├── whatsapp-webhook-validator.js
│   │   └── payfast-handler.js
│   └── .env.example        # Config template
├── agents/
│   ├── ag2/                # AutoGen agents
│   │   └── financial_sentinel_agent.py
│   └── lib/
│       ├── perplexity_financial_client.py
│       └── xrpl_settlement.py
├── INSTALL.sh              # Auto-installer
└── README.md               # This file
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `APEX_EXECUTION_REPORT.md` | Complete APEX v2.0 security audit |
| `IMPLEMENTATION_COMPLETE.md` | Implementation verification |
| `PERPLEXITY_INTEGRATION_STATUS.md` | Financial agent documentation |
| `HYBRID_DEPLOYMENT.md` | Deployment architecture |
| `BACKEND_SETUP.md` | Server configuration guide |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Node.js not found" | Install from https://nodejs.org/ |
| "Cannot find module" | Run `npm install` in server/ |
| "Missing API keys" | Check `server/.env` file |
| "Port in use" | Change PORT in .env |
| "PayFast ITN failing" | Verify signature calculation |

---

## 📧 Support

- **Email:** founders@vaalai.co.za
- **GitHub:** [Issues](https://github.com/deedk822-lang/vaal-ai-empire-site/issues)
- **PayFast:** https://developers.payfast.co.za/docs

---

## 🇿🇦 About

Vaal AI Empire provides **digital sovereignty** for South African SMEs through autonomous AI engines:

1. **Financial Sentinel** - Tax recovery, compliance monitoring, financial intelligence
2. **Guardian Engine** - Infrastructure monitoring, predictive maintenance
3. **Talent Accelerator** - Automated hiring, skills matching

**Launch:** December 27, 2025

---

## 📝 License

Proprietary © 2025 Vaal AI Empire, Inc.

---

⚡ **Built in the Vaal. Built for Africa. Built to dominate.** 🇿🇦
