// Vaal AI Empire - Main Server
// Enterprise-grade PayFast + Auth + Observability Platform
// Built in the Vaal. Built for Africa. 🇿🇦

require('dotenv').config();
const express = require('express');
// REMOVED: const bodyParser = require('body-parser');
// bodyParser was imported but never used anywhere in this file.
// express.json() and express.urlencoded() replace it entirely.
// Fixes CodeQL js/unused-variable (note alert, server.js:58)
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const cookieParser = require('cookie-parser');
const path = require('path');
const crypto = require('crypto');

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
// LOG SANITIZER
// =============================

/**
 * Strips newline and control characters from any value before logging.
 * Prevents log injection when values originate from user-supplied HTTP
 * request fields (PayFast ITN POST body, request paths, etc).
 * Fixes CodeQL js/log-injection on server.js:384,388,393,397,401
 *
 * @param {*} value
 * @returns {string}
 */
function sanitizeLog(value) {
    return String(value).replace(/[\r\n\t\x00-\x1f\x7f]/g, '_');
}

// =============================
// PAYFAST CONFIGURATION
// =============================

const PAYFAST_CONFIG = {
    merchant_id:  process.env.PAYFAST_MERCHANT_ID  || '10000100',
    merchant_key: process.env.PAYFAST_MERCHANT_KEY || '',
    passphrase:   process.env.PAYFAST_PASSPHRASE   || '',
    sandbox:      process.env.PAYFAST_SANDBOX === 'true',
    get baseUrl() {
        return this.sandbox
            ? 'https://sandbox.payfast.co.za/eng/process'
            : 'https://www.payfast.co.za/eng/process';
    },
    get validateUrl() {
        return this.sandbox
            ? 'https://sandbox.payfast.co.za/eng/query/validate'
            : 'https://www.payfast.co.za/eng/query/validate';
    }
};

// =============================
// PAYFAST SIGNATURE UTILITIES
// =============================

/**
 * Generates a PayFast payment request signature.
 *
 * ⚠️  NOT a password storage operation.
 * PayFast's ITN specification explicitly mandates MD5 for payment
 * signature generation. This cannot be replaced with bcrypt, scrypt,
 * PBKDF2, or Argon2 — PayFast will reject any other algorithm.
 *
 * The passphrase here is a shared API secret used purely for HMAC-style
 * request signing, not a user credential being stored or verified.
 *
 * Reference: https://developers.payfast.co.za/docs#step_1_form_fields
 *
 * @param {object} data       - Payment fields (must not include 'signature')
 * @param {string} passphrase - Merchant passphrase (empty string if not set)
 * @returns {string}          - MD5 hex signature required by PayFast
 */
function generatePayFastSignature(data, passphrase = '') {
    const paramString = Object.keys(data)
        .sort()
        .map(key => `${key}=${encodeURIComponent(String(data[key])).replace(/%20/g, '+')}`)
        .join('&');

    const stringToHash = passphrase
        ? `${paramString}&passphrase=${encodeURIComponent(passphrase)}`
        : paramString;

    // MD5 is mandated by PayFast API spec for ITN signature generation.
    // This is NOT password storage - it's HMAC-style request signing.
    // PayFast explicitly requires MD5 and rejects other algorithms.
    // See: https://developers.payfast.co.za/docs#signature-generation
    return crypto.createHash('md5').update(stringToHash).digest('hex'); // codeql[js/insufficient-password-hash] This is PayFast API signature generation, not password hashing
}

/**
 * Verifies a PayFast ITN signature.
 * Uses destructuring to avoid mutating the caller's object (avoids the
 * side-effect of the original `delete data.signature` approach).
 *
 * @param {object} data       - Full ITN POST body including 'signature'
 * @param {string} passphrase - Merchant passphrase
 * @returns {boolean}
 */
function verifyPayFastSignature(data, passphrase = '') {
    const { signature, ...rest } = data;
    const calculatedSignature = generatePayFastSignature(rest, passphrase);
    return signature === calculatedSignature;
}

// =============================
// SECURITY MIDDLEWARE
// =============================

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
    req.timestamp = Date.now();
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
        payment: 'PayFast',
        stats
    });
});

// Home page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'index.html'));
});

// API Routes
if (authRoutes)          app.use('/api/auth',         authRoutes);
if (paymentRoutes)       app.use('/api/payments',      paymentRoutes);
if (subscriptionRoutes)  app.use('/api/subscriptions', subscriptionRoutes);
if (analyticsRoutes)     app.use('/api/analytics',     analyticsRoutes);
if (observabilityRoutes) app.use('/api/observability', observabilityRoutes);

// =============================
// PAYFAST ROUTES
// =============================

// Get PayFast configuration (for frontend)
app.get('/config', (req, res) => {
    res.json({
        merchantId:  PAYFAST_CONFIG.merchant_id,
        merchantKey: PAYFAST_CONFIG.merchant_key,
        sandbox:     PAYFAST_CONFIG.sandbox,
        returnUrl:   `${process.env.DOMAIN}/success.html`,
        cancelUrl:   `${process.env.DOMAIN}/canceled.html`,
        notifyUrl:   `${process.env.DOMAIN}/payfast/notify`,
        prices: {
            starter: {
                name:        'Vaal Starter',
                amount:      parseInt(process.env.VAAL_STARTER_PRICE) || 99900,
                description: 'Vaal Starter - Monthly Subscription'
            },
            empire: {
                name:        'Vaal Empire',
                amount:      parseInt(process.env.VAAL_EMPIRE_PRICE) || 299900,
                description: 'Vaal Empire - Monthly Subscription'
            }
        }
    });
});

// Create PayFast payment
app.post('/create-payment', async (req, res) => {
    const { plan, email, name } = req.body;

    let amount, itemName;
    if (plan === 'empire') {
        amount   = parseInt(process.env.VAAL_EMPIRE_PRICE)  || 299900;
        itemName = 'Vaal Empire';
    } else {
        amount   = parseInt(process.env.VAAL_STARTER_PRICE) || 99900;
        itemName = 'Vaal Starter';
    }

    const paymentId = `Vaal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const paymentData = {
        merchant_id:      PAYFAST_CONFIG.merchant_id,
        merchant_key:     PAYFAST_CONFIG.merchant_key,
        return_url:       `${process.env.DOMAIN}/success.html?payment_id=${paymentId}`,
        cancel_url:       `${process.env.DOMAIN}/canceled.html`,
        notify_url:       `${process.env.DOMAIN}/payfast/notify`,
        name_first:       name ? name.split(' ')[0] : 'Customer',
        name_last:        name ? name.split(' ').slice(1).join(' ') || '' : '',
        email_address:    email || '',
        m_payment_id:     paymentId,
        amount:           (amount / 100).toFixed(2),
        item_name:        itemName,
        item_description: `${itemName} - Monthly Subscription`,
        custom_str1:      plan,
        custom_str2:      'vaal-ai-empire',
        custom_int1:      1,
    };

    const signature = generatePayFastSignature(paymentData, PAYFAST_CONFIG.passphrase);
    paymentData.signature = signature;

    if (tracer) tracer.recordMetric('payment_created', { paymentId, plan, amount });

    res.json({
        success:    true,
        paymentId,
        paymentData,
        payfastUrl: PAYFAST_CONFIG.baseUrl,
        sandbox:    PAYFAST_CONFIG.sandbox
    });
});

// PayFast ITN (Instant Transaction Notification) webhook
app.post('/payfast/notify', express.urlencoded({ extended: true }), async (req, res) => {
    console.log('📢 PayFast ITN received');

    const data = req.body;

    // Verify signature before touching any other fields
    if (!verifyPayFastSignature({ ...data }, PAYFAST_CONFIG.passphrase)) {
        console.error('❌ Invalid PayFast signature');
        return res.status(400).send('Invalid signature');
    }

    // Verify with PayFast server (security best practice)
    try {
        const axios = require('axios');
        const verifyResponse = await axios.post(
            PAYFAST_CONFIG.validateUrl,
            new URLSearchParams(data).toString(),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        );

        if (verifyResponse.data !== 'VALID') {
            console.error('❌ PayFast validation failed');
            return res.status(400).send('Validation failed');
        }
    } catch (error) {
        console.error('❌ PayFast verification error:', error.message);
        if (!PAYFAST_CONFIG.sandbox) {
            return res.status(400).send('Verification failed');
        }
    }

    // Sanitize ALL user-supplied ITN fields before logging.
    // req.body comes directly from PayFast's POST — an attacker who spoofs
    // the ITN endpoint could inject newlines to forge log entries.
    // Fixes CodeQL js/log-injection on lines 384, 388, 393, 397, 401.
    const paymentStatus = sanitizeLog(data.payment_status);
    const paymentId     = sanitizeLog(data.m_payment_id);
    const amount        = parseFloat(data.amount_gross) || 0; // numeric — safe without sanitizeLog
    const plan          = sanitizeLog(data.custom_str1);

    console.log(`💰 Payment ${paymentId}: ${paymentStatus} - R${amount}`);

    switch (paymentStatus) {
        case 'COMPLETE':
            console.log(`✅ Payment completed: ${paymentId}`);
            if (tracer) tracer.recordMetric('payment_complete', { paymentId, plan, amount });
            // TODO: Update database, send email, activate subscription
            break;
        case 'FAILED':
            console.log(`❌ Payment failed: ${paymentId}`);
            if (tracer) tracer.recordMetric('payment_failed', { paymentId, plan });
            break;
        case 'PENDING':
            console.log(`⏳ Payment pending: ${paymentId}`);
            break;
        default:
            console.log(`ℹ️ Unknown status: ${paymentStatus}`);
    }

    res.status(200).send('OK');
});

// Check payment status
app.get('/payment-status/:paymentId', async (req, res) => {
    const { paymentId } = req.params;

    // TODO: Check payment status from database
    res.json({
        paymentId,
        status:  'pending',
        message: 'Payment status check'
    });
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
            console.log(`💳 Payments: PayFast (${PAYFAST_CONFIG.sandbox ? 'SANDBOX' : 'PRODUCTION'})`);
            console.log('');
            console.log('🇿🇦 Built in the Vaal. Built for Africa.');
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
};

process.on('unhandledRejection', (err) => {
    console.error('UNHANDLED REJECTION! 💥 Shutting down...');
    console.error(err.name, err.message);
    process.exit(1);
});

process.on('uncaughtException', (err) => {
    console.error('UNCAUGHT EXCEPTION! 💥 Shutting down...');
    console.error(err.name, err.message);
    process.exit(1);
});

startServer();

module.exports = app;
