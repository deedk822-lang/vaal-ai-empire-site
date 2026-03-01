# Vaal AI Empire - Server

Node.js/Express server handling Stripe subscription checkout with enterprise-grade security.

## Quick Start

```bash
cd server
npm install
cp .env.example .env
# Edit .env with your Stripe keys
npm start
```

## Requirements

- Node.js 18+
- npm 9+
- Stripe account

## Environment Variables

See `.env.example` for all required variables including:
- `STRIPE_SECRET_KEY` - Your Stripe secret key
- `STRIPE_PUBLISHABLE_KEY` - Your Stripe publishable key
- `STRIPE_WEBHOOK_SECRET` - Webhook endpoint secret
- `STARTER_PRICE_ID` - Stripe price ID for Vaal Starter plan
- `EMPIRE_PRICE_ID` - Stripe price ID for Vaal Empire plan
- `DOMAIN` - Your domain (e.g., http://localhost:4242)
- `JWT_SECRET` - Secret for JWT token generation
- `MONGODB_URI` - MongoDB connection string

## API Endpoints

- `GET /` - Serve static files
- `GET /health` - Health check endpoint
- `GET /config` - Get Stripe publishable key and price IDs
- `POST /create-checkout-session` - Create Stripe Checkout session
- `GET /session-status` - Retrieve session details
- `POST /webhook` - Handle Stripe webhook events
- `/api/auth/*` - Authentication routes
- `/api/payments/*` - Payment management routes
- `/api/subscriptions/*` - Subscription management routes
- `/api/analytics/*` - Analytics routes

## Security Features

- Helmet.js for security headers
- Express rate limiting
- CORS protection
- MongoDB sanitization
- XSS protection
- HPP (HTTP Parameter Pollution) protection

## Testing

Use Stripe test cards:
- Success: `4242 4242 4242 4242`
- 3D Secure: `4000 0025 0000 3155`
- Declined: `4000 0000 0000 0002`

## Deployment

See main `INSTALL.md` and `STRIPE_SETUP.md` for full deployment guide.

## Support

Email: founders@vaalai.co.za
