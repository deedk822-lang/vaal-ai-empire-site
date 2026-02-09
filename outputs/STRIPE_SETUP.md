# ⚡ Vaal AI Empire - Stripe Checkout Setup Guide

## Quick Start (15 Minutes)

This guide will help you set up Stripe subscription checkout for the Vaal AI Empire platform.

---

## 📝 Prerequisites

- [x] Stripe account (free at [stripe.com](https://stripe.com))
- [x] Node.js 18+ installed
- [x] Git repository cloned
- [x] Terminal/command line access

---

## Step 1: Create Stripe Products (5 minutes)

### Option A: Using Stripe CLI (Fastest)

```bash
# Install Stripe CLI if not installed
# Mac: brew install stripe/stripe-cli/stripe
# Windows: scoop install stripe
# Linux: https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Create Vaal Starter product
stripe products create \
  --name="Vaal Starter" \
  --description="Essential AI tools for growing SMEs"

# Note the product ID (prod_XXXXX)

# Create Starter price
stripe prices create \
  -d "product=prod_XXXXX" \
  -d "unit_amount=99900" \
  -d "currency=zar" \
  -d "recurring[interval]=month" \
  -d "recurring[trial_period_days]=7"

# Save this price ID (price_XXXXX)

# Create Vaal Empire product
stripe products create \
  --name="Vaal Empire" \
  --description="Full autonomous AI empire with all engines"

# Note the product ID

# Create Empire price
stripe prices create \
  -d "product=prod_YYYYY" \
  -d "unit_amount=299900" \
  -d "currency=zar" \
  -d "recurring[interval]=month" \
  -d "recurring[trial_period_days]=7"

# Save this price ID (price_YYYYY)
```

### Option B: Using Stripe Dashboard

1. Go to https://dashboard.stripe.com/products
2. Click **"+ Add product"**
3. For **Vaal Starter**:
   - Name: `Vaal Starter`
   - Description: `Essential AI tools for growing SMEs`
   - Pricing: `R999 / month`
   - Add 7-day free trial
   - Click **Save**
   - **Copy the Price ID** (starts with `price_`)

4. Repeat for **Vaal Empire**:
   - Name: `Vaal Empire`
   - Description: `Full autonomous AI empire`
   - Pricing: `R2,999 / month`
   - Add 7-day free trial
   - **Copy the Price ID**

---

## Step 2: Configure Environment (2 minutes)

```bash
# Navigate to server directory
cd server

# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Update these values in `.env`:**

```env
# Get from: https://dashboard.stripe.com/apikeys
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE

# Your Price IDs from Step 1
STARTER_PRICE_ID=price_starter_id_here
EMPIRE_PRICE_ID=price_empire_id_here

# For local testing
DOMAIN=http://localhost:4242
STATIC_DIR=../
PORT=4242
```

---

## Step 3: Install Dependencies (2 minutes)

```bash
# Install Node.js packages
npm install

# Verify installation
npm list
```

You should see:
- ✅ stripe@^14.9.0
- ✅ express@^4.18.2
- ✅ dotenv@^16.3.1
- ✅ body-parser@^1.20.2

---

## Step 4: Test Locally (3 minutes)

```bash
# Start the server
npm start

# You should see:
# ⚡ Vaal AI Empire Checkout Server
# 🚀 Running on http://localhost:4242
```

**Open browser:**
- http://localhost:4242 - Homepage
- http://localhost:4242/pricing - Pricing page

**Test checkout with Stripe test cards:**

```
Card Number: 4242 4242 4242 4242
Expiry: 12/26 (any future date)
CVC: 123 (any 3 digits)
Postal Code: 12345
```

**Click "Start Free Trial"** → Should redirect to Stripe Checkout

---

## Step 5: Set Up Webhooks (3 minutes)

### For Local Testing:

```bash
# In a new terminal window
stripe listen --forward-to localhost:4242/webhook

# Copy the webhook signing secret (whsec_XXXXX)
```

**Update `.env`:**
```env
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
```

### For Production:

1. Go to https://dashboard.stripe.com/webhooks
2. Click **"+ Add endpoint"**
3. Enter URL: `https://vaalai.co.za/webhook`
4. Select events to listen for:
   - [x] `checkout.session.completed`
   - [x] `customer.subscription.created`
   - [x] `customer.subscription.updated`
   - [x] `customer.subscription.deleted`
   - [x] `invoice.paid`
   - [x] `invoice.payment_failed`
5. Click **Add endpoint**
6. Copy **Signing secret**
7. Add to production `.env`

---

## 🚀 Deploy to Production

### Update Environment for Production:

```env
# Production Stripe keys
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_LIVE_KEY
STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_KEY

# Production domain
DOMAIN=https://vaalai.co.za

# Production webhook secret
STRIPE_WEBHOOK_SECRET=whsec_YOUR_PRODUCTION_SECRET

NODE_ENV=production
```

### Deploy to Alibaba Cloud:

```bash
# On your local machine
git add .
git commit -m "Add Stripe checkout"
git push origin feature/stripe-checkout

# SSH to your server
ssh user@your-server-ip

# Pull latest code
cd /var/www/vaal-ai-empire
git pull origin feature/stripe-checkout

# Install dependencies
cd server
npm install --production

# Set up PM2 (process manager)
npm install -g pm2
pm2 start server.js --name vaalai-checkout
pm2 save
pm2 startup

# Configure nginx
sudo nano /etc/nginx/sites-available/vaalai
```

**Nginx configuration:**

```nginx
server {
    listen 80;
    server_name vaalai.co.za www.vaalai.co.za;
    
    location / {
        proxy_pass http://localhost:4242;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site and restart nginx
sudo ln -s /etc/nginx/sites-available/vaalai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Set up SSL (free)
sudo certbot --nginx -d vaalai.co.za -d www.vaalai.co.za
```

---

## ✅ Testing Checklist

### Before Launch:

- [ ] Pricing page loads correctly
- [ ] Both subscription tiers display
- [ ] "Start Free Trial" button works
- [ ] Redirects to Stripe Checkout
- [ ] Test card payment succeeds
- [ ] Success page shows correct details
- [ ] Webhook receives events (check logs)
- [ ] Cancel flow works
- [ ] Mobile responsive
- [ ] SSL certificate active

### Production Testing:

- [ ] Live mode enabled in Stripe
- [ ] Webhook endpoint verified
- [ ] Test real payment (then refund)
- [ ] Confirmation email sent
- [ ] Customer portal accessible
- [ ] Analytics tracking works

---

## 📊 Monitoring

### View Logs:

```bash
# Server logs
pm2 logs vaalai-checkout

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Stripe Dashboard:

- **Payments:** https://dashboard.stripe.com/payments
- **Subscriptions:** https://dashboard.stripe.com/subscriptions
- **Webhooks:** https://dashboard.stripe.com/webhooks
- **Logs:** https://dashboard.stripe.com/logs

---

## 🐛 Troubleshooting

### Issue: "Stripe is not defined"
**Solution:** Ensure Stripe.js is loaded:
```html
<script src="https://js.stripe.com/v3/"></script>
```

### Issue: "Invalid API Key"
**Solution:** Check `.env` file has correct keys:
```bash
echo $STRIPE_SECRET_KEY  # Should start with sk_
```

### Issue: Webhook not receiving events
**Solution:** Verify webhook secret:
```bash
stripe listen --forward-to localhost:4242/webhook
# Use the whsec_ secret shown
```

### Issue: Payment succeeded but webhook didn't fire
**Solution:** Check webhook endpoint in Stripe Dashboard:
- Status should be "Active"
- Recent events should show deliveries
- Click "Send test webhook" to verify

---

## 💰 Pricing Recommendations

### South African Market (ZAR):

| Tier | Monthly | Annual (20% off) |
|------|---------|------------------|
| **Starter** | R999 | R9,590 (R799/mo) |
| **Empire** | R2,999 | R28,790 (R2,399/mo) |

### Early Adopter Discount:

Create coupon in Stripe Dashboard:
- Code: `LAUNCH50`
- Discount: 50% off for 3 months
- Valid for: First 100 customers

---

## 🎓 Next Steps

1. **Customize branding:**
   - https://dashboard.stripe.com/settings/branding
   - Upload logo and set brand colors

2. **Set up Customer Portal:**
   - https://dashboard.stripe.com/settings/billing/portal
   - Enable subscription management

3. **Configure email notifications:**
   - https://dashboard.stripe.com/settings/emails
   - Customize receipt and invoice emails

4. **Add tax settings** (if applicable):
   - https://dashboard.stripe.com/settings/tax

5. **Integrate with your backend:**
   - Use webhooks to provision access
   - Store customer data in your database
   - Send welcome emails

---

## 📞 Support

**Stripe Support:**
- Docs: https://stripe.com/docs
- Discord: https://stripe.com/go/developer-chat
- Email: support@stripe.com

**Vaal AI Empire:**
- Email: founders@vaalai.co.za
- GitHub Issues: [Create issue]

---

**⚡ Built in the Vaal. Built for Africa. Built to dominate.** 🇸🇦