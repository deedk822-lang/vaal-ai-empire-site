 feature/stripe-checkout
# Vaal AI Empire - Checkout Server

Node.js/Express server for handling Stripe subscription checkout.
=======
# Vaal AI Empire - Server

Node.js/Express server handling Stripe subscription checkout.
 main

## Quick Start

```bash
 feature/stripe-checkout
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your Stripe keys

# Start server
npm start
```

## Environment Variables

See `.env.example` for required configuration.

## API Endpoints

- `GET /` - Serve static files
- `GET /config` - Get Stripe publishable key and price IDs
- `POST /create-checkout-session` - Create Stripe Checkout session
- `GET /checkout-session` - Retrieve session details
- `POST /webhook` - Handle Stripe webhook events
- `POST /create-portal-session` - Create customer portal session
- `GET /health` - Health check endpoint

## Deployment

See `STRIPE_SETUP.md` for full deployment guide.

## Testing

Use Stripe test cards:
- Success: `4242 4242 4242 4242`
- 3D Secure: `4000 0025 0000 3155`
- Declined: `4000 0000 0000 0002`

## Support

Email: founders@vaalai.co.za
=======
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

See `.env.example` for all required variables.

## Endpoints

- `GET /` - Homepage
- `GET /config` - Stripe configuration
- `POST /create-checkout-session` - Create checkout
- `GET /checkout-session` - Get session details
- `POST /webhook` - Stripe webhooks
- `POST /create-portal-session` - Customer portal
- `GET /health` - Health check

## Testing

Test card: `4242 4242 4242 4242`

## Production

See main INSTALL.md for deployment instructions.

## Support

founders@vaalai.co.za
 main
