# Vaal AI Empire - Checkout Server

Node.js/Express server for handling Stripe subscription checkout.

## Quick Start

```bash
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