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
const cookieParser = require('cookie-parser');
const path = require('path');

// Database connection
const connectDB = require('./config/database');

// Initialize Stripe
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

// Import middleware
const { globalErrorHandler, notFound } = require('./middleware/errorHandler');

// Import routes
const authRoutes = require('./routes/auth');
 feat/auth-error-handling-5447018483623698560
const paymentRoutes = require('./routes/paymentRoutes');
const subscriptionRoutes = require('./routes/subscriptionRoutes');
const analyticsRoutes = require('./routes/analyticsRoutes');

 main

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
 feat/auth-error-handling-5447018483623698560

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

// CORS
const corsOptions = {
    origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : '*',
    credentials: true,
    optionsSuccessStatus: 200
};
app.use(cors(corsOptions));

// =============================
// BODY PARSING & SANITIZATION
// =============================

// Body parser (limit payload size)
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));
app.use(cookieParser());

// Data sanitization against NoSQL query injection
app.use(mongoSanitize());

// Data sanitization against XSS
app.use(xss());



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

// =============================
// BODY PARSING & SANITIZATION
// =============================

// Body parser (limit payload size)
app.use(bodyParser.json({ limit: '10kb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '10kb' }));
app.use(cookieParser());

// Data sanitization against NoSQL query injection
app.use(mongoSanitize());

// Data sanitization against XSS
app.use(xss());

 main
// Prevent parameter pollution
app.use(hpp({
    whitelist: ['price', 'plan', 'status'] // Allow these params to be duplicated
}));

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
 feat/auth-error-handling-5447018483623698560

        req.traceId = traceId;


        
        req.traceId = traceId;
        
 main
        res.on('finish', () => {
            tracer.endTrace(traceId, {
                statusCode: res.statusCode,
                duration: Date.now() - req.timestamp
            });
        });
    }
 feat/auth-error-handling-5447018483623698560


    
 main
    req.timestamp = Date.now();
    next();
});

// =============================
// ROUTES
// =============================

// Health check (before authentication)
app.get('/health', (req, res) => {
    const stats = tracer ? tracer.getStats() : {};
 feat/auth-error-handling-5447018483623698560


    
 main
    res.json({
        status: 'ok',
        service: 'vaal-ai-empire',
        timestamp: new Date().toISOString(),
        node: process.version,
        uptime: process.uptime(),
        database: 'connected', // Will be updated by connectDB
        stats
    });
});

// Home page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'index.html'));
});

// API Routes
app.use('/api/auth', authRoutes);
 feat/auth-error-handling-5447018483623698560
app.use('/api/payments', paymentRoutes);
app.use('/api/subscriptions', subscriptionRoutes);
app.use('/api/analytics', analyticsRoutes);

 main

if (observabilityRoutes) {
    app.use('/api/observability', observabilityRoutes);
}

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
 feat/auth-error-handling-5447018483623698560


    
 main
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

// Webhook endpoint (must use raw body)
 feat/auth-error-handling-5447018483623698560
app.post('/webhook', express.raw({type: 'application/json'}), async (req, res) => {

app.post('/webhook', bodyParser.raw({type: 'application/json'}), async (req, res) => {
 main
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
            const session = event.data.object;
            console.log('✅ Checkout completed:', session.id);
            // TODO: Create user subscription in database
            break;

        case 'customer.subscription.created':
            const subscription = event.data.object;
            console.log('✅ Subscription created:', subscription.id);
            break;

        case 'customer.subscription.updated':
            const updatedSub = event.data.object;
            console.log('🔄 Subscription updated:', updatedSub.id);
            break;

        case 'customer.subscription.deleted':
            const deletedSub = event.data.object;
            console.log('❌ Subscription canceled:', deletedSub.id);
            break;

        case 'invoice.paid':
            const invoice = event.data.object;
            console.log('💰 Invoice paid:', invoice.id);
            break;

        case 'invoice.payment_failed':
            const failedInvoice = event.data.object;
            console.log('⚠️ Payment failed:', failedInvoice.id);
            // TODO: Send email to customer
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
            return_url: `${process.env.DOMAIN}/account.html`,
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

// Handle 404 - must be after all other routes
app.use(notFound);

// Global error handler - must be last
app.use(globalErrorHandler);

// =============================
// DATABASE & SERVER STARTUP
// =============================

const startServer = async () => {
    try {
        // Connect to MongoDB
        await connectDB();
 feat/auth-error-handling-5447018483623698560


        
 main
        // Cleanup old traces every hour (if tracer exists)
        if (tracer) {
            setInterval(() => {
                tracer.cleanup(24 * 60 * 60 * 1000); // 24 hours
            }, 60 * 60 * 1000);
        }
 feat/auth-error-handling-5447018483623698560


        
 main
        // Start server
        app.listen(port, () => {
            console.log('');
            console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
            console.log('   VAAL AI EMPIRE - SERVER');
            console.log('   10X Enterprise Platform');
            console.log('⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡');
            console.log('');
            console.log(`🚀 Running on: http://localhost:${port}`);
            console.log(`🔐 Auth API: http://localhost:${port}/api/auth`);
            console.log(`💳 Stripe API: http://localhost:${port}/create-checkout-session`);
            console.log(`📊 Dashboard: http://localhost:${port}/dashboard.html`);
            if (tracer) {
                console.log(`🔍 Observability: http://localhost:${port}/api/observability`);
            }
            console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
            console.log(`🌍 Domain: ${process.env.DOMAIN}`);
            console.log('');
            console.log('🇿🇦 Built in the Vaal. Built for Africa.');
            console.log('');
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

// Start the server
startServer();

module.exports = app;
