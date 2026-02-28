/**
 * PayFast Payment Controller
 * South African payment gateway integration
 * 
 * APEX Security Framework v2.0 Compliant
 * POPIA Compliant
 */

const crypto = require('crypto');
const { URL } = require('url');
const { catchAsync } = require('../middleware/errorHandler');
const { AppError } = require('../middleware/errorHandler');

// PayFast Configuration
// APEX: PAYFAST_PASSPHRASE is the correct env var name per PayFast spec
const PAYFAST_CONFIG = {
    merchant_id: process.env.PAYFAST_MERCHANT_ID,
    merchant_key: process.env.PAYFAST_MERCHANT_KEY,
    signing_key: process.env.PAYFAST_PASSPHRASE,  // APEX-FIX: Renamed from PAYFAST_SIGNING_KEY
    sandbox: process.env.PAYFAST_SANDBOX === 'true',
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

/**
 * Validate and canonicalize domain URL
 * APEX: Prevent SSRF and injection via DOMAIN env var
 * 
 * @param {string} domain - Raw domain from env
 * @returns {string|null} - Canonicalized URL or null if invalid
 */
function validateAndCanonicalizeDomain(domain) {
    if (!domain || typeof domain !== 'string') {
        return null;
    }
    
    // Allowed hosts for production
    const ALLOWED_HOSTS = [
        'vaal-ai-empire.vercel.app',
        'vaal-ai-empire-site.vercel.app',
        'vaal.co.za',
        'www.vaal.co.za',
        'api.vaal.co.za'
    ];
    
    try {
        // Ensure scheme is present for URL parsing
        let urlStr = domain.trim();
        if (!urlStr.startsWith('http://') && !urlStr.startsWith('https://')) {
            urlStr = 'https://' + urlStr;
        }
        
        const parsed = new URL(urlStr);
        
        // Only allow http/https schemes
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            console.error(`Invalid scheme in DOMAIN: ${parsed.protocol}`);
            return null;
        }
        
        // In production, validate against allowlist
        // In development, allow localhost
        const hostname = parsed.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        
        if (!isLocalhost && !ALLOWED_HOSTS.includes(hostname)) {
            console.error(`Domain hostname not in allowlist: ${hostname}`);
            return null;
        }
        
        // Return canonicalized URL (no trailing slash)
        return parsed.origin;
    } catch (e) {
        console.error(`Invalid DOMAIN format: ${domain}`);
        return null;
    }
}

/**
 * Get PayFast configuration for frontend
 * APEX: Expose only non-sensitive config
 */
exports.getPayFastConfig = (req, res) => {
    res.status(200).json({
        merchantId: PAYFAST_CONFIG.merchant_id,
        sandbox: PAYFAST_CONFIG.sandbox,
        baseUrl: PAYFAST_CONFIG.baseUrl
    });
};

/**
 * Generate PayFast payment signature
 * APEX: MD5 is REQUIRED by PayFast specification
 * 
 * @param {object} data - Payment data
 * @param {string} signingKey - Merchant signing key
 * @returns {string} MD5 signature
 */
function generatePayFastSignature(data, signingKey = '') {
    const paramString = Object.keys(data).sort()
        .map(key => `${key}=${encodeURIComponent(String(data[key])).replace(/%20/g, '+')}`)
        .join('&');
    
    const stringToHash = signingKey 
        ? `${paramString}&passphrase=${encodeURIComponent(signingKey)}` 
        : paramString;
    
    // APEX: MD5 is mandated by PayFast API for ITN signature generation.
    // This is NOT password storage - it's HMAC-style request signing required by
    // the third-party payment provider. PayFast's ITN specification explicitly
    // mandates MD5. Using bcrypt/scrypt/argon2 would break PayFast integration.
    // Reference: https://developers.payfast.co.za/docs/secure-your-integration/
    return crypto.createHash('md5').update(stringToHash).digest('hex'); // codeql[js/insufficient-password-hash] PAYFAST-API-COMPLIANCE: MD5 mandated by PayFast ITN spec — NOT password hashing — owner: @deedk822-lang, expiry: 2027-Q1, JIRA-SEC-0042
}

/**
 * Create PayFast payment request
 * APEX: All amounts validated server-side
 */
exports.createPayment = catchAsync(async (req, res, next) => {
    const { plan, email, name } = req.body;
    
    // Validate plan
    const VALID_PLANS = ['starter', 'empire'];
    if (!plan || !VALID_PLANS.includes(plan)) {
        return next(new AppError('Invalid plan selection', 400));
    }
    
    // Validate email
    if (!email || !email.includes('@')) {
        return next(new AppError('Valid email required', 400));
    }
    
    // Set amounts (in cents for ZAR)
    const amounts = {
        starter: parseInt(process.env.VAAL_STARTER_PRICE) || 99900,  // R999.00
        empire: parseInt(process.env.VAAL_EMPIRE_PRICE) || 299900   // R2,999.00
    };
    
    const amount = amounts[plan];
    const itemName = plan === 'empire' ? 'Vaal Empire' : 'Vaal Starter';
    const paymentId = `Vaal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // APEX: Validate and canonicalize DOMAIN before building URLs
    const baseUrl = validateAndCanonicalizeDomain(process.env.DOMAIN) || 'http://localhost:3000';
    
    // Build PayFast data
    const paymentData = {
        merchant_id: PAYFAST_CONFIG.merchant_id,
        merchant_key: PAYFAST_CONFIG.merchant_key,
        return_url: `${baseUrl}/success.html?payment_id=${encodeURIComponent(paymentId)}`,
        cancel_url: `${baseUrl}/canceled.html`,
        notify_url: `${baseUrl}/payfast/notify`,
        name_first: name ? name.split(' ')[0] : 'Customer',
        name_last: name ? name.split(' ').slice(1).join(' ') || '' : '',
        email_address: email,
        m_payment_id: paymentId,
        amount: (amount / 100).toFixed(2),
        item_name: itemName,
        item_description: `${itemName} - Monthly Subscription`,
        custom_str1: plan,
        custom_str2: 'vaal-ai-empire',
        custom_int1: 1
    };
    
    // Generate signature
    paymentData.signature = generatePayFastSignature(paymentData, PAYFAST_CONFIG.signing_key);
    
    res.status(200).json({
        success: true,
        paymentId,
        payfastUrl: PAYFAST_CONFIG.baseUrl,
        paymentData
    });
});

/**
 * Verify PayFast ITN (Instant Transaction Notification)
 * APEX: Signature validation + server-side verification
 */
exports.verifyITN = catchAsync(async (req, res) => {  // APEX-FIX: Removed unused 'next' param
    // PayFast sends POST data as form-urlencoded
    const data = req.body;
    
    // APEX: Validate signature first
    const { signature, ...rest } = data;
    const calculatedSignature = generatePayFastSignature(rest, PAYFAST_CONFIG.signing_key);
    
    if (signature !== calculatedSignature) {
        console.error('❌ Invalid PayFast signature');
        return res.status(400).send('Invalid signature');
    }
    
    // APEX: Verify with PayFast server (SSRF protection)
    const ALLOWED_PAYFAST_HOSTS = ['sandbox.payfast.co.za', 'www.payfast.co.za'];
    
    try {
        const validateUrl = new URL(PAYFAST_CONFIG.validateUrl);
        if (!ALLOWED_PAYFAST_HOSTS.includes(validateUrl.hostname)) {
            console.error('❌ Invalid PayFast validation URL');
            return res.status(400).send('Invalid validation URL');
        }
        
        // Post validation to PayFast
        const axios = require('axios');
        const verifyResponse = await axios.post(
            PAYFAST_CONFIG.validateUrl,
            new URLSearchParams(data).toString(),
            {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                timeout: 10000,
                maxRedirects: 0
            }
        );
        
        const status = verifyResponse.data?.toString().trim().toUpperCase();
        if (status !== 'VALID') {
            console.error('❌ PayFast validation failed:', status || 'empty response');
            return res.status(400).send('Validation failed');
        }
        
        // APEX: Log successful payment (PII sanitized)
        console.log('✅ PayFast payment verified:', {
            payment_id: data.m_payment_id,
            pf_payment_id: data.pf_payment_id,
            amount: data.amount,
            plan: data.custom_str1
        });
        
        // TODO: Update database, activate subscription, send confirmation email
        
        res.status(200).send('OK');
        
    } catch (error) {
        console.error('❌ PayFast verification error:', error.message);
        if (!PAYFAST_CONFIG.sandbox) {
            return res.status(400).send('Verification failed');
        }
        // In sandbox, still return OK for testing
        res.status(200).send('OK');
    }
});

/**
 * Get payment status
 * APEX: Server-side status check
 */
exports.getPaymentStatus = catchAsync(async (req, res, next) => {
    const { paymentId } = req.params;
    
    if (!paymentId) {
        return next(new AppError('Payment ID required', 400));
    }
    
    // TODO: Query database for payment status
    // For now, return placeholder
    res.status(200).json({
        paymentId,
        status: 'pending', // pending, completed, failed, refunded
        timestamp: new Date().toISOString()
    });
});
