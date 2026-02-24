// Vaal AI Empire — Main Server
// PayFast + Auth + Observability Platform
// Built in the Vaal. Built for Africa. 🇿🇦

'use strict';

require('dotenv').config();

const crypto      = require('crypto');
const path        = require('path');
const express     = require('express');
const cors        = require('cors');
const helmet      = require('helmet');
const rateLimit   = require('express-rate-limit');
const cookieParser= require('cookie-parser');
const { filterXSS }= require('xss');               // replaces abandoned xss-clean

// ── Optional modules ─────────────────────────────────────────────────────────

let connectDB = async () => {};
try {
    connectDB = require('./config/database');
} catch { console.log('ℹ️  Database module not found — running without MongoDB'); }

let globalErrorHandler = (err, _req, res, _next) => {
    console.error(err);
    res.status(err.statusCode || 500).json({
        status:  'error',
        message: err.message || 'Internal server error',
        // Never leak stack traces to clients in production
        ...(process.env.NODE_ENV !== 'production' && { stack: err.stack }),
    });
};
let notFound = (_req, res) => res.status(404).json({ error: 'Not found' });
try {
    const errorHandler  = require('./middleware/errorHandler');
    globalErrorHandler  = errorHandler.globalErrorHandler;
    notFound            = errorHandler.notFound;
} catch { console.log('ℹ️  Error handler module not found — using defaults'); }

let authRoutes, paymentRoutes, subscriptionRoutes, analyticsRoutes, observabilityRoutes;
try { authRoutes         = require('./routes/auth');                } catch { console.log('ℹ️  Auth routes not found'); }
try { paymentRoutes      = require('./routes/paymentRoutes');       } catch { console.log('ℹ️  Payment routes not found'); }
try { subscriptionRoutes = require('./routes/subscriptionRoutes');  } catch { console.log('ℹ️  Subscription routes not found'); }
try { analyticsRoutes    = require('./routes/analyticsRoutes');     } catch { console.log('ℹ️  Analytics routes not found'); }
try { observabilityRoutes= require('./routes/observability');       } catch { console.log('ℹ️  Observability routes not found'); }

let tracer;
try {
    const { getTracer } = require('./lib/tracing');
    tracer = getTracer({ projectName: 'vaal-ai-empire', environment: process.env.NODE_ENV || 'development' });
} catch { console.log('ℹ️  Tracing module not found — running without tracing'); }

// httpx-style fetch — Node 18+ has native fetch; use it instead of axios
// (axios was never in package.json but was required inside a route — replaced here)
// Note: nodeFetch kept for fallback but currently unused; reserved for future use
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const nodeFetch = globalThis.fetch ?? require('node:http');

// ── App ───────────────────────────────────────────────────────────────────────

const app  = express();
const port = parseInt(process.env.PORT || '3000', 10);

// ── PayFast config ────────────────────────────────────────────────────────────

if (!process.env.PAYFAST_MERCHANT_ID || !process.env.PAYFAST_MERCHANT_KEY) {
    console.warn('⚠️  PAYFAST_MERCHANT_ID / PAYFAST_MERCHANT_KEY not set — payments will fail in production');
}

const PAYFAST_CONFIG = {
    merchant_id:  process.env.PAYFAST_MERCHANT_ID  || '10000100',
    merchant_key: process.env.PAYFAST_MERCHANT_KEY || '',
    passphrase:   process.env.PAYFAST_PASSPHRASE   || '',
    sandbox:      process.env.PAYFAST_SANDBOX === 'true',
    get processUrl() {
        return this.sandbox
            ? 'https://sandbox.payfast.co.za/eng/process'
            : 'https://www.payfast.co.za/eng/process';
    },
    get validateUrl() {
        return this.sandbox
            ? 'https://sandbox.payfast.co.za/eng/query/validate'
            : 'https://www.payfast.co.za/eng/query/validate';
    },
};

const PLAN_CONFIG = {
    starter: {
        name:        'Vaal Starter',
        amount:      parseInt(process.env.VAAL_STARTER_PRICE || '99900', 10),  // cents
        description: 'Vaal Starter — Monthly Subscription',
    },
    empire: {
        name:        'Vaal Empire',
        amount:      parseInt(process.env.VAAL_EMPIRE_PRICE  || '299900', 10), // cents
        description: 'Vaal Empire — Monthly Subscription',
    },
};

// ── PayFast helpers ───────────────────────────────────────────────────────────

/**
 * Generates a PayFast payment request signature.
 *
 * NOT a password storage operation.
 * PayFast's API specification explicitly mandates MD5 for ITN signature
 * generation. This cannot be replaced with bcrypt, scrypt, or Argon2.
 * The passphrase is a shared API secret used purely for request signing,
 * not a user password being stored or verified.
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

    // MD5 is mandated by the PayFast API spec — NOT a password hash
    // codeql[js/insufficient-password-hash]
    return crypto.createHash('md5').update(stringToHash).digest('hex');
}

/**
 * Verifies a PayFast ITN signature.
 * Uses destructuring instead of delete to avoid mutating the caller's object.
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

/**
 * Validate an ITN payload with the PayFast server.
 * Uses Node 18 native fetch — no axios dependency.
 */
async function validatePayFastITN(data) {
    const body = new URLSearchParams(data).toString();
    const resp = await fetch(PAYFAST_CONFIG.validateUrl, {
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
    });
    return (await resp.text()).trim() === 'VALID';
}

// ── Security middleware ───────────────────────────────────────────────────────

app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc:  ["'self'"],
            scriptSrc:   ["'self'", 'https://www.payfast.co.za', 'https://sandbox.payfast.co.za'],
            connectSrc:  ["'self'", 'https://www.payfast.co.za', 'https://sandbox.payfast.co.za'],
            frameSrc:    ["'none'"],
            objectSrc:   ["'none'"],
            upgradeInsecureRequests: [],
        },
    },
}));

// CORS — fail-safe: no wildcard fallback; log a warning if env var is missing
const allowedOrigins = process.env.ALLOWED_ORIGINS
    ? process.env.ALLOWED_ORIGINS.split(',').map(o => o.trim())
    : [];

if (allowedOrigins.length === 0) {
    console.warn('⚠️  ALLOWED_ORIGINS not set — CORS will reject all cross-origin requests');
}

app.use(cors({
    origin: (origin, callback) => {
        // Allow server-to-server requests (no Origin header) and listed origins
        if (!origin || allowedOrigins.includes(origin)) return callback(null, true);
        callback(new Error(`CORS: origin '${origin}' not allowed`));
    },
    credentials:         true,
    optionsSuccessStatus: 200,
}));

// Rate limiting
app.use('/api', rateLimit({
    max:       100,
    windowMs:  15 * 60 * 1000,
    message:   'Too many requests from this IP, please try again later.',
    standardHeaders: true,
    legacyHeaders:   false,
}));
const authLimiter = rateLimit({
    max:       5,
    windowMs:  15 * 60 * 1000,
    message:   'Too many login attempts, please try again later.',
    skipSuccessfulRequests: true,
    standardHeaders: true,
    legacyHeaders:   false,
});
app.use('/api/auth/login',  authLimiter);
app.use('/api/auth/signup', authLimiter);

// PayFast endpoints also rate-limited independently
app.use('/create-payment', rateLimit({
    max:      20,
    windowMs: 15 * 60 * 1000,
    message:  'Too many payment requests, please try again later.',
}));

// ── Body parsing ──────────────────────────────────────────────────────────────
// express.json / urlencoded are built into Express 4.16+ — body-parser removed.

app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));
app.use(cookieParser());

// XSS sanitisation — replaces abandoned xss-clean package
// Recursively sanitises all string values in body / query / params
function _sanitize(val) {
    if (typeof val === 'string')         return filterXSS(val);
    if (Array.isArray(val))              return val.map(_sanitize);
    if (val && typeof val === 'object')  return Object.fromEntries(Object.entries(val).map(([k, v]) => [k, _sanitize(v)]));
    return val;
}
app.use((req, _res, next) => {
    req.body   = _sanitize(req.body);
    req.query  = _sanitize(req.query);
    req.params = _sanitize(req.params);
    next();
});

// Static files
app.use(express.static(path.join(__dirname, '..')));

// ── Request tracing ───────────────────────────────────────────────────────────

app.use((req, res, next) => {
    req.timestamp = Date.now();
    if (!tracer) return next();
    const traceId = tracer.startTrace(`${req.method} ${req.path}`, {
        method: req.method,
        path:   req.path,
        ip:     req.ip,
    });
    req.traceId = traceId;
    res.on('finish', () =>
        tracer.endTrace(traceId, { statusCode: res.statusCode, duration: Date.now() - req.timestamp })
    );
    next();
});

// ── Routes ────────────────────────────────────────────────────────────────────

app.get('/health', (_req, res) => {
    res.json({
        status:     'ok',
        service:    'vaal-ai-empire',
        timestamp:  new Date().toISOString(),
        node:       process.version,
        uptime:     process.uptime(),
        payment:    'PayFast',
        sandbox:    PAYFAST_CONFIG.sandbox,
        ...(tracer && { stats: tracer.getStats() }),
    });
});

app.get('/', (_req, res) => res.sendFile(path.join(__dirname, '..', 'index.html')));

if (authRoutes)          app.use('/api/auth',          authRoutes);
if (paymentRoutes)       app.use('/api/payments',       paymentRoutes);
if (subscriptionRoutes)  app.use('/api/subscriptions',  subscriptionRoutes);
if (analyticsRoutes)     app.use('/api/analytics',      analyticsRoutes);
if (observabilityRoutes) app.use('/api/observability',  observabilityRoutes);

// ── PayFast routes ────────────────────────────────────────────────────────────

// Frontend reads this to build the payment form
app.get('/config', (_req, res) => {
    res.json({
        merchantId:  PAYFAST_CONFIG.merchant_id,
        sandbox:     PAYFAST_CONFIG.sandbox,
        processUrl:  PAYFAST_CONFIG.processUrl,
        returnUrl:   `${process.env.DOMAIN}/success`,
        cancelUrl:   `${process.env.DOMAIN}/canceled`,
        notifyUrl:   `${process.env.DOMAIN}/payfast/notify`,
        prices: {
            starter: { name: PLAN_CONFIG.starter.name, amount: PLAN_CONFIG.starter.amount },
            empire:  { name: PLAN_CONFIG.empire.name,  amount: PLAN_CONFIG.empire.amount  },
        },
    });
});

// Create a signed PayFast payment payload — frontend POSTs this as a form
app.post('/create-payment', async (req, res) => {
    const { plan, email = '', name = '' } = req.body;

    if (!plan || !PLAN_CONFIG[plan]) {
        return res.status(400).json({ error: `Invalid plan '${plan}'. Must be 'starter' or 'empire'.` });
    }

    const { amount, name: itemName, description } = PLAN_CONFIG[plan];

    // Cryptographically random payment ID — substr is deprecated, use slice
    const paymentId = `Vaal-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;

    const [firstName, ...rest] = name.trim().split(' ');
    const paymentData = {
        merchant_id:      PAYFAST_CONFIG.merchant_id,
        merchant_key:     PAYFAST_CONFIG.merchant_key,
        return_url:       `${process.env.DOMAIN}/success?payment_id=${paymentId}`,
        cancel_url:       `${process.env.DOMAIN}/canceled`,
        notify_url:       `${process.env.DOMAIN}/payfast/notify`,
        name_first:       firstName || 'Customer',
        name_last:        rest.join(' ') || '',
        email_address:    email,
        m_payment_id:     paymentId,
        amount:           (amount / 100).toFixed(2), // rands
        item_name:        itemName,
        item_description: description,
        custom_str1:      plan,
        custom_str2:      'vaal-ai-empire',
        custom_int1:      '1',
    };

    // Signature computed from a copy — paymentData is not mutated
    const signature = generatePayFastSignature(paymentData, PAYFAST_CONFIG.passphrase);

    if (tracer) tracer.recordMetric('payment_created', { paymentId, plan, amount });

    return res.json({
        success:     true,
        paymentId,
        paymentData: { ...paymentData, signature },
        payfastUrl:  PAYFAST_CONFIG.processUrl,
        sandbox:     PAYFAST_CONFIG.sandbox,
    });
});

// PayFast ITN webhook - rate limited to prevent abuse
const payfastNotifyLimiter = rateLimit({
    max:      50,
    windowMs: 15 * 60 * 1000,
    message:  'Too many ITN requests, please try again later.',
});
app.post('/payfast/notify', payfastNotifyLimiter, express.urlencoded({ extended: false }), async (req, res) => {
    const data = req.body;

    // 1. Verify signature first — fail fast, never continue on bad sig
    if (!verifyPayFastSignature(data, PAYFAST_CONFIG.passphrase)) {
        console.error('❌ PayFast ITN: invalid signature');
        return res.status(400).send('Invalid signature');
    }

    // 2. Validate with PayFast server — required in both sandbox AND production
    try {
        const valid = await validatePayFastITN(data);
        if (!valid) {
            console.error('❌ PayFast ITN: server validation failed');
            return res.status(400).send('Validation failed');
        }
    } catch (err) {
        console.error('❌ PayFast ITN: validation request error:', err.message);
        // Do NOT continue silently — return 400 so PayFast retries
        return res.status(400).send('Validation error');
    }

    const { payment_status, m_payment_id, amount_gross, custom_str1: plan } = data;
    const amount = parseFloat(amount_gross);
    // Sanitize values for safe logging (prevent log injection)
    const safePaymentId = String(m_payment_id).replace(/[\r\n]/g, '_');
    const safeStatus = String(payment_status).replace(/[\r\n]/g, '_');

    console.log(`💰 PayFast ITN ${safePaymentId}: ${safeStatus} — R${amount}`);

    switch (payment_status) {
        case 'COMPLETE':
            console.log(`✅ Payment completed: ${safePaymentId}`);
            if (tracer) tracer.recordMetric('payment_complete', { paymentId: m_payment_id, plan, amount });
            // TODO: update DB, activate subscription, send confirmation email
            break;
        case 'FAILED':
            console.error(`❌ Payment failed: ${safePaymentId}`);
            if (tracer) tracer.recordMetric('payment_failed', { paymentId: m_payment_id, plan });
            break;
        case 'PENDING':
            console.log(`⏳ Payment pending: ${safePaymentId}`);
            break;
        default:
            const safeStatusForLog = String(payment_status).replace(/[\r\n]/g, '_');
            console.log(`ℹ️  Unknown PayFast status '${safeStatusForLog}' for ${safePaymentId}`);
    }

    res.status(200).send('OK');
});

// Payment status check
app.get('/payment-status/:paymentId', (req, res) => {
    const { paymentId } = req.params;
    // TODO: query database for actual status
    res.json({ paymentId, status: 'pending', message: 'Payment status check' });
});

// ── Error handling ────────────────────────────────────────────────────────────

app.use(notFound);
app.use(globalErrorHandler);

// ── Startup ───────────────────────────────────────────────────────────────────

const startServer = async () => {
    try {
        await connectDB();

        if (tracer) {
            setInterval(() => tracer.cleanup(24 * 60 * 60 * 1000), 60 * 60 * 1000);
        }

        app.listen(port, () => {
            console.log('');
            console.log('⚡ VAAL AI EMPIRE — SERVER RUNNING ⚡');
            console.log(`🚀  http://localhost:${port}`);
            console.log(`📊  ${process.env.NODE_ENV || 'development'}`);
            console.log(`💳  PayFast ${PAYFAST_CONFIG.sandbox ? '(SANDBOX)' : '(PRODUCTION)'}`);
            console.log('🇿🇦  Built in the Vaal. Built for Africa.');
        });
    } catch (err) {
        console.error('❌ Failed to start server:', err);
        process.exit(1);
    }
};

process.on('unhandledRejection', (err) => {
    console.error('UNHANDLED REJECTION — shutting down:', err.name, err.message);
    process.exit(1);
});
process.on('uncaughtException', (err) => {
    console.error('UNCAUGHT EXCEPTION — shutting down:', err.name, err.message);
    process.exit(1);
});

startServer();

module.exports = app;
