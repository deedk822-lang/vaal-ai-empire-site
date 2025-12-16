// Vaal AI Empire - Main Server
// Enterprise-grade Stripe + Observability Platform
// Built in the Vaal. Built for Africa.

require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');

// Initialize Stripe
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

// Import observability
const { getTracer } = require('./lib/tracing');
const observabilityRoutes = require('./routes/observability');

const app = express();
const port = process.env.PORT || 4242;

// Initialize tracer
const tracer = getTracer({
  projectName: 'vaal-ai-empire',
  environment: process.env.NODE_ENV || 'development'
});

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '..')));

// Request logging middleware
app.use((req, res, next) => {
  const traceId = tracer.startTrace(`${req.method} ${req.path}`, {
    method: req.method,
    path: req.path,
    ip: req.ip
  });
  
  req.traceId = traceId;
  
  res.on('finish', () => {
    tracer.endTrace(traceId, {
      statusCode: res.statusCode,
      duration: Date.now() - req.timestamp
    });
  });
  
  req.timestamp = Date.now();
  next();
});

// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'index.html'));
});

// Observability routes
app.use('/api/observability', observabilityRoutes);

// Get configuration
app.get('/config', (req, res) => {
  res.json({
    publishableKey: process.env.STRIPE_PUBLISHABLE_KEY,
    prices: {
      starter: process.env.STARTER_PRICE_ID,
      empire: process.env.EMPIRE_PRICE_ID
    }
  });
});

// Create Checkout Session
app.post('/create-checkout-session', async (req, res) => {
  const { priceId } = req.body;
  const spanId = tracer.startSpan(req.traceId, 'create_checkout_session', { priceId });

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      success_url: `${process.env.DOMAIN}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.DOMAIN}/canceled.html`,
      customer_creation: 'always',
      billing_address_collection: 'required',
      allow_promotion_codes: true,
      payment_method_types: ['card'],
      metadata: {
        product: priceId === process.env.STARTER_PRICE_ID ? 'Vaal Starter' : 'Vaal Empire',
        source: 'vaalai_website'
      },
      subscription_data: {
        trial_period_days: 7,
        metadata: {
          product: priceId === process.env.STARTER_PRICE_ID ? 'Vaal Starter' : 'Vaal Empire'
        },
      },
    });

    tracer.endSpan(spanId, { sessionId: session.id });
    tracer.recordMetric('checkout_created', { priceId, sessionId: session.id });

    res.json({ sessionId: session.id });
  } catch (error) {
    console.error('Error creating checkout session:', error);
    tracer.endSpan(spanId, { error: error.message });
    res.status(500).json({ error: error.message });
  }
});

// Get session details
app.get('/checkout-session', async (req, res) => {
  const { sessionId } = req.query;

  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId);
    res.json(session);
  } catch (error) {
    console.error('Error retrieving session:', error);
    res.status(500).json({ error: error.message });
  }
});

// Webhook endpoint
app.post('/webhook', bodyParser.raw({type: 'application/json'}), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  const traceId = tracer.startTrace('webhook_event', {
    type: event.type,
    eventId: event.id
  });

  // Handle events
  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object;
      console.log('✅ Checkout completed:', session.id);
      tracer.recordMetric('checkout_completed', {
        customerId: session.customer,
        subscriptionId: session.subscription
      });
      break;

    case 'customer.subscription.created':
      const subscription = event.data.object;
      console.log('✅ Subscription created:', subscription.id);
      tracer.recordMetric('subscription_created', {
        subscriptionId: subscription.id,
        plan: subscription.items.data[0]?.price.id
      });
      break;

    case 'customer.subscription.updated':
      const updatedSub = event.data.object;
      console.log('🔄 Subscription updated:', updatedSub.id);
      break;

    case 'customer.subscription.deleted':
      const deletedSub = event.data.object;
      console.log('❌ Subscription canceled:', deletedSub.id);
      tracer.recordMetric('subscription_canceled', {
        subscriptionId: deletedSub.id
      });
      break;

    case 'invoice.paid':
      const invoice = event.data.object;
      console.log('💰 Invoice paid:', invoice.id);
      tracer.recordMetric('invoice_paid', {
        amount: invoice.amount_paid,
        currency: invoice.currency
      });
      break;

    case 'invoice.payment_failed':
      const failedInvoice = event.data.object;
      console.log('⚠️ Payment failed:', failedInvoice.id);
      tracer.recordMetric('payment_failed', {
        invoiceId: failedInvoice.id
      });
      break;

    default:
      console.log(`Unhandled event type: ${event.type}`);
  }

  tracer.endTrace(traceId);
  res.json({ received: true });
});

// Customer Portal
app.post('/create-portal-session', async (req, res) => {
  const { customerId } = req.body;

  try {
    const portalSession = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: `${process.env.DOMAIN}/account.html`,
    });

    res.json({ url: portalSession.url });
  } catch (error) {
    console.error('Error creating portal session:', error);
    res.status(500).json({ error: error.message });
  }
});

// Health check
app.get('/health', (req, res) => {
  const stats = tracer.getStats();
  
  res.json({
    status: 'ok',
    service: 'vaal-ai-empire',
    timestamp: new Date().toISOString(),
    node: process.version,
    uptime: process.uptime(),
    stats
  });
});

// Cleanup old traces every hour
setInterval(() => {
  tracer.cleanup(24 * 60 * 60 * 1000); // 24 hours
}, 60 * 60 * 1000);

// Start server
app.listen(port, () => {
  console.log('');
  console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
  console.log('   VAAL AI EMPIRE - SERVER');
  console.log('   10X Enterprise Platform');
  console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
  console.log('');
  console.log(`🚀 Running on: http://localhost:${port}`);
  console.log(`📊 Dashboard: http://localhost:${port}/dashboard.html`);
  console.log(`🔍 Observability: http://localhost:${port}/api/observability`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🌍 Domain: ${process.env.DOMAIN}`);
  console.log('');
  console.log('🇿🇦 Built in the Vaal. Built for Africa.');
  console.log('');
});

module.exports = app;