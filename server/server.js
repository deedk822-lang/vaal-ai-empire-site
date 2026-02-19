// Vaal AI Empire - Main Server
// Enterprise-grade Stripe + Auth + Observability Platform
// Built in the Vaal. Built for Africa.

require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const cookieParser = require('cookie-parser');
const path = require('path');

// Initialize Stripe
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

// Database connection
let connectDB;
try {
    connectDB = require('./config/database');
} catch (error) {
    console.log('ℹ️  Database module not found, running without MongoDB');
    connectDB = async () => console.log('📊 MongoDB connection skipped');
}

// Import middleware
let globalErrorHandler, notFound;
try {
    const errorHandler = require('./middleware/errorHandler');
    globalErrorHandler = errorHandler.globalErrorHandler;
    notFound = errorHandler.notFound;
} catch (error) {
    console.log('ℹ️  Error handler module not found, using defaults');
    globalErrorHandler = (err, req, res, next) => {
        console.error(err);
        res.status(500).json({ error: 'Internal server error' });
    };
    notFound = (req, res) => res.status(404).json({ error: 'Not found' });
}

// Import routes
let authRoutes, paymentRoutes, subscriptionRoutes, analyticsRoutes, observabilityRoutes;
try {
    authRoutes = require('./routes/auth');
} catch (e) { console.log('ℹ️  Auth routes not found'); }
try {
    paymentRoutes = require('./routes/paymentRoutes');
} catch (e) { console.log('ℹ️  Payment routes not found'); }
try {
    subscriptionRoutes = require('./routes/subscriptionRoutes');
} catch (e) { console.log('ℹ️  Subscription routes not found'); }
try {
    analyticsRoutes = require('./routes/analyticsRoutes');
} catch (e) { console.log('ℹ️  Analytics routes not found'); }
try {
    observabilityRoutes = require('./routes/observability');
} catch (e) { console.log('ℹ️  Observability routes not found'); }

// Import tracer if available
let tracer;
try {
    const { getTracer } = require('./lib/tracing');
    tracer = getTracer({
        projectName: 'vaal-ai-empire',
        environment: process.env.NODE_ENV || 'development'
    });
} catch (error) {
    console.log('ℹ️  Observability module not found, running without tracing');
}

const app = express();
const port = process.env.PORT || 3000;

// =============================
// SECURITY MIDDLEWARE
// =============================

// Set security HTTP headers
app.use(helmet());

// Rate limiting
const limiter = rateLimit({
    max: 100,
    windowMs: 15 * 60 * 1000,
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/api', limiter);

// Auth-specific rate limiter
const authLimiter = rateLimit({
    max: 5,
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

// =============================
// BODY PARSING
// =============================

app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));
app.use(cookieParser());

// Static files
app.use(express.static(path.join(__dirname, '..')));

// =============================
// REQUEST LOGGING MIDDLEWARE
// =============================

app.use((req, res, next) => {
    if (tracer) {
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
    }
    req.timestamp = Date.now();
    next();
});

// =============================
// ROUTES
// =============================

// Health check
app.get('/health', (req, res) => {
    const stats = tracer ? tracer.getStats() : {};
    res.json({
        status: 'ok',
        service: 'vaal-ai-empire',
        timestamp: new Date().toISOString(),
        node: process.version,
        uptime: process.uptime(),
        stats
    });
});

// Home page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'index.html'));
});

// API Routes
if (authRoutes) app.use('/api/auth', authRoutes);
if (paymentRoutes) app.use('/api/payments', paymentRoutes);
if (subscriptionRoutes) app.use('/api/subscriptions', subscriptionRoutes);
if (analyticsRoutes) app.use('/api/analytics', analyticsRoutes);
if (observabilityRoutes) app.use('/api/observability', observabilityRoutes);

// =============================
// STRIPE ROUTES
// =============================

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

    try {
        const session = await stripe.checkout.sessions.create({
            mode: 'subscription',
            line_items: [{ price: priceId, quantity: 1 }],
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
                }
            }
        });

        if (tracer) {
            tracer.recordMetric('checkout_created', { priceId, sessionId: session.id });
        }

        res.json({ sessionId: session.id });
    } catch (error) {
        console.error('Error creating checkout session:', error);
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
app.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
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

    // Handle events
    switch (event.type) {
        case 'checkout.session.completed':
            console.log('✅ Checkout completed:', event.data.object.id);
            break;
        case 'customer.subscription.created':
            console.log('✅ Subscription created:', event.data.object.id);
            break;
        case 'customer.subscription.updated':
            console.log('🔄 Subscription updated:', event.data.object.id);
            break;
        case 'customer.subscription.deleted':
            console.log('❌ Subscription canceled:', event.data.object.id);
            break;
        case 'invoice.paid':
            console.log('💰 Invoice paid:', event.data.object.id);
            break;
        case 'invoice.payment_failed':
            console.log('⚠️ Payment failed:', event.data.object.id);
            break;
        default:
            console.log(`Unhandled event type: ${event.type}`);
    }

    res.json({ received: true });
});

// Customer Portal
app.post('/create-portal-session', async (req, res) => {
    const { customerId } = req.body;

    try {
        const portalSession = await stripe.billingPortal.sessions.create({
            customer: customerId,
            return_url: `${process.env.DOMAIN}/account.html`
        });
        res.json({ url: portalSession.url });
    } catch (error) {
        console.error('Error creating portal session:', error);
        res.status(500).json({ error: error.message });
    }
});

// =============================
// ERROR HANDLING
// =============================

app.use(notFound);
app.use(globalErrorHandler);

// =============================
// SERVER STARTUP
// =============================

const startServer = async () => {
    try {
        await connectDB();

        // Cleanup old traces every hour
        if (tracer) {
            setInterval(() => {
                tracer.cleanup(24 * 60 * 60 * 1000);
            }, 60 * 60 * 1000);
        }

        app.listen(port, () => {
            console.log('');
            console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
            console.log('   VAAL AI EMPIRE - SERVER');
            console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
            console.log('');
            console.log(`🚀 Running on: http://localhost:${port}`);
            console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
            console.log('');
            console.log('🇿🇦 Built in the Vaal. Built for Africa.');
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
};

// Handle unhandled promise rejections
process.on('unhandledRejection', (err) => {
    console.error('UNHANDLED REJECTION! 💥 Shutting down...');
    console.error(err.name, err.message);
    process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
    console.error('UNCAUGHT EXCEPTION! 💥 Shutting down...');
    console.error(err.name, err.message);
    process.exit(1);
});

startServer();

module.exports = app;
