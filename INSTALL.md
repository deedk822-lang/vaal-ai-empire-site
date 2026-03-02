# ⚡ Vaal AI Empire - Complete Installation Guide

## 🚀 ONE-COMMAND SETUP (Recommended)

### For Mac/Linux:

```bash
git clone https://github.com/deedk822-lang/vaal-ai-empire-site.git
cd vaal-ai-empire-site
chmod +x setup.sh
./setup.sh
```

### For Windows:

```cmd
git clone https://github.com/deedk822-lang/vaal-ai-empire-site.git
cd vaal-ai-empire-site
setup.bat
```

**That's it!** The script installs everything needed.

---

## 📝 What Gets Installed:

### Required Software (Manual install if needed):

1. **Node.js 18+** - [Download](https://nodejs.org/)
2. **npm** (comes with Node.js)
3. **Git** - [Download](https://git-scm.com/)

### Automatic Installations (via setup script):

- ✅ Express.js (web server)
- ✅ Stripe SDK (v14.9.0)
- ✅ dotenv (environment config)
- ✅ body-parser (request handling)

---

## ⚙️ After Installation:

### Step 1: Get Your Stripe Keys (2 minutes)

1. Go to **https://dashboard.stripe.com/test/apikeys**
2. Copy **Publishable key** (starts with `pk_test_`)
3. Copy **Secret key** (starts with `sk_test_`)

### Step 2: Configure Environment (1 minute)

**Edit `server/.env`:**

```env
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
```

### Step 3: Create Stripe Products (5 minutes)

**Option A - Stripe Dashboard:**

1. Go to https://dashboard.stripe.com/test/products
2. Click "+ Create product"
3. Create **Vaal Starter**: R999/month, 7-day trial
4. Create **Vaal Empire**: R2,999/month, 7-day trial
5. Copy both **Price IDs** to `.env`

**Option B - Stripe CLI:**

```bash
stripe login

# Vaal Starter
stripe products create --name="Vaal Starter"
stripe prices create -d "product=PROD_ID" -d "unit_amount=99900" -d "currency=zar" -d "recurring[interval]=month" -d "recurring[trial_period_days]=7"

# Vaal Empire
stripe products create --name="Vaal Empire"
stripe prices create -d "product=PROD_ID" -d "unit_amount=299900" -d "currency=zar" -d "recurring[interval]=month" -d "recurring[trial_period_days]=7"
```

**Add Price IDs to `server/.env`:**

```env
STARTER_PRICE_ID=price_ABC123
EMPIRE_PRICE_ID=price_XYZ789
```

### Step 4: Start the Server (30 seconds)

```bash
cd server
npm start
```

You should see:

```
⚡ Vaal AI Empire Checkout Server
🚀 Running on http://localhost:4242
```

### Step 5: Test It! (1 minute)

**Open browser:**
- Homepage: http://localhost:4242
- Pricing: http://localhost:4242/pricing.html

**Test checkout with Stripe test card:**

```
Card: 4242 4242 4242 4242
Expiry: 12/26
CVC: 123
Postal: 12345
```

Click "Start Free Trial" → Should redirect to Stripe Checkout

---

## ✅ Installation Checklist:

### Pre-Installation:
- [ ] Node.js 18+ installed
- [ ] Git installed
- [ ] Stripe account created

### During Setup:
- [ ] Repository cloned
- [ ] Setup script ran successfully
- [ ] `.env` file created
- [ ] Dependencies installed

### Post-Setup:
- [ ] Stripe API keys added to `.env`
- [ ] Products created in Stripe
- [ ] Price IDs added to `.env`
- [ ] Server starts without errors
- [ ] Pricing page loads
- [ ] Test payment works

---

## 🐛 Troubleshooting:

### "Node.js not found"

**Solution:** Install Node.js from https://nodejs.org/

```bash
# Check installation
node --version  # Should be 18.0.0 or higher
npm --version   # Should be 9.0.0 or higher
```

### "Cannot find module 'stripe'"

**Solution:** Install dependencies

```bash
cd server
npm install
```

### "Error: Missing Stripe API keys"

**Solution:** Check `server/.env` file has:

```env
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

### "Price configuration error"

**Solution:** Verify Price IDs in `.env`:

```env
STARTER_PRICE_ID=price_...
EMPIRE_PRICE_ID=price_...
```

### "Port 4242 already in use"

**Solution:** Change port in `server/.env`:

```env
PORT=4243
```

---

## 💻 System Requirements:

### Minimum:
- **OS:** Windows 10, macOS 10.15, Ubuntu 20.04
- **RAM:** 2GB
- **Disk:** 500MB
- **Node.js:** 18.0.0+

### Recommended:
- **OS:** Windows 11, macOS 12+, Ubuntu 22.04
- **RAM:** 4GB+
- **Disk:** 1GB
- **Node.js:** 20.0.0+

---

## 📚 Additional Documentation:

- **Full Setup Guide:** `STRIPE_SETUP.md`
- **Server README:** `server/README.md`
- **Stripe Docs:** https://stripe.com/docs

---

## 📦 What's Included:

### Backend:
- Node.js/Express server
- Stripe Checkout integration
- Webhook event handling
- Customer Portal support
- Environment configuration

### Frontend:
- Responsive pricing page
- Payment success page
- Checkout cancellation page
- Stripe.js integration

### Documentation:
- This installation guide
- Complete setup guide
- Deployment instructions
- Troubleshooting tips

---

## 🚀 Next Steps After Installation:

1. **Customize branding:**
   - https://dashboard.stripe.com/settings/branding
   - Upload Vaal AI Empire logo
   - Set brand color: `#f7b731`

2. **Set up webhooks:**
   ```bash
   stripe listen --forward-to localhost:4242/webhook
   ```

3. **Test thoroughly:**
   - Try both subscription tiers
   - Test payment success flow
   - Test cancellation flow
   - Verify webhook events

4. **Deploy to production:**
   - Switch to live Stripe keys
   - Configure production domain
   - Set up SSL certificate
   - Deploy to Alibaba Cloud

---

## 📞 Support:

**Having issues?**

- Email: founders@vaalai.co.za
- GitHub Issues: [Create issue](https://github.com/deedk822-lang/vaal-ai-empire-site/issues)
- Stripe Support: https://stripe.com/docs

---

**⚡ You're now ready to accept subscriptions! Built in the Vaal. Built for Africa.** 🇸🇦