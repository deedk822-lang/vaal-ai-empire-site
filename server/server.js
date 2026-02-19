// Vaal AI Empire - Main Server
// Enterprise-grade Stripe + Auth + Observability Platform
// Built in the Vaal. Built for Africa.

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const mongoSanitize = require('express-mongo-sanitize');
const xss = require('xss-clean');
const hpp = require('hpp');
const path = require('path');

// Import middleware
const { globalErrorHandler, notFound } = require('./middleware/errorHandler');

// Import routes
const authRoutes = require('./routes/auth');
const paymentRoutes = require('./routes/paymentRoutes');
const subscriptionRoutes = require('./routes/subscriptionRoutes');
const analyticsRoutes = require('./routes/analyticsRoutes');

// Import observability (if exists)
let observabilityRoutes, tracer;
try {
    const { getTracer } = require('./lib/tracing');
    observabilityRoutes = require('./routes/observability');
    tracer = getTracer({
        projectName: 'vaal-ai-empire',
        environment: process.env.NODE_ENV || 'development'
    });
} catch (error) {
    console.log('ℹ️  Observability module not found, running without tracing');
}

const app = express();
const port = process.env.PORT || 4242;

// =============================
// SECURITY MIDDLEWARE
// =============================

// Set security HTTP headers
app.use(helmet());

// Rate limiting
const limiter = rateLimit({
    max: 100, // 100 requests per windowMs
    windowMs: 15 * 60 * 1000, // 15 minutes
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/api', limiter);

// Auth-specific rate limiter (stricter)
const authLimiter = rateLimit({
    max: 5, // 5 login attempts per windowMs
    windowMs: 15 * 60 * 1000,
    message: 'Too many login attempts, please try again later.',
    skipSuccessfulRequests: true
});
app.use('/api/auth/login', authLimiter);
app.use('/api/auth/signup', authLimiter);

// CORS
const corsOptions = {
    origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : '*',
    credentials: true,
    optionsSuccessStatus: 200
};
app.use(cors(corsOptions));

// Body parser with size limits
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Data sanitization against NoSQL injection
app.use(mongoSanitize());

// Data sanitization against XSS
app.use(xss());

// Prevent parameter pollution
app.use(hpp());

// =============================
// STATIC FILES
// =============================

app.use(express.static(path.join(__dirname, '../')));

// =============================
// API ROUTES
// =============================

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0'
    });
});

// Config endpoint for Stripe
app.get('/config', (req, res) => {
    res.json({
        publishableKey: process.env.STRIPE_PUBLISHABLE_KEY,
        prices: {
            starter: process.env.STARTER_PRICE_ID,
            empire: process.env.EMPIRE_PRICE_ID
        }
    });
});

// Auth routes
app.use('/api/auth', authRoutes);

// Payment routes
app.use('/api/payments', paymentRoutes);

// Subscription routes
app.use('/api/subscriptions', subscriptionRoutes);

// Analytics routes
app.use('/api/analytics', analyticsRoutes);

// Observability routes (if available)
if (observabilityRoutes) {
    app.use('/observability', observabilityRoutes);
}

// =============================
// CHECKOUT SESSION ENDPOINTS
// =============================

// Create Checkout Session
app.post('/create-checkout-session', async (req, res) => {
    const { priceId } = req.body;
    
    if (!priceId) {
        return res.status(400).json({ error: 'Price ID is required' });
    }

    try {
        const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
        
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

        if (tracer) {
            tracer.recordMetric('checkout_created', { priceId, sessionId: session.id });
        }

        res.json({ sessionId: session.id });
    } catch (error) {
        console.error('Error creating checkout session:', error);
        if (tracer) {
            tracer.recordError(error, { context: 'create_checkout_session' });
        }
        res.status(500).json({ 
            error: 'Failed to create checkout session',
            message: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// Session status endpoint
app.get('/session-status', async (req, res) => {
    const { session_id } = req.query;
    
    if (!session_id) {
        return res.status(400).json({ error: 'Session ID is required' });
    }

    try {
        const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
        const session = await stripe.checkout.sessions.retrieve(session_id);
        
        res.json({
            status: session.status,
            customer_email: session.customer_details?.email,
            subscription: session.subscription
        });
    } catch (error) {
        console.error('Error retrieving session:', error);
        res.status(500).json({ error: 'Failed to retrieve session status' });
    }
});

// Webhook endpoint for Stripe events
app.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
    const sig = req.headers['stripe-signature'];
    const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET;
    
    let event;
    
    try {
        const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
        event = stripe.webhooks.constructEvent(req.body, sig, endpointSecret);
    } catch (err) {
        console.error('Webhook signature verification failed:', err.message);
        return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    // Handle the event
    switch (event.type) {
        case 'checkout.session.completed':
            console.log('✅ Checkout session completed:', event.data.object.id);
            // TODO: Provision account, send welcome email, etc.
            break;
        case 'invoice.paid':
            console.log('💰 Invoice paid:', event.data.object.id);
            break;
        case 'invoice.payment_failed':
            console.log('❌ Payment failed:', event.data.object.id);
            break;
        case 'customer.subscription.deleted':
            console.log('🚫 Subscription cancelled:', event.data.object.id);
            break;
        default:
            console.log(`Unhandled event type: ${event.type}`);
    }

    res.json({ received: true });
});

// =============================
// ERROR HANDLING
// =============================

// 404 handler
app.use(notFound);

// Global error handler
app.use(globalErrorHandler);

// =============================
// START SERVER
// =============================

app.listen(port, () => {
    console.log('⚡ Vaal AI Empire Server');
    console.log(`🚀 Running on http://localhost:${port}`);
    console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log('═══════════════════════════════════════');
});

module.exports = app;
