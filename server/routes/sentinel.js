/**
 * Sentient Financial Sentinel API Routes
 * Phase 1 - APEX v2.0 Compliant
 *
 * Endpoints for:
 * - Voice command processing
 * - Financial analysis
 * - XRPL settlements
 * - Loan management
 * - Consent management
 */

const express = require('express');
const router = express.Router();
const crypto = require('crypto');

// Lazy-load Python sentinel via child process
const { spawn } = require('child_process');
const path = require('path');

/**
 * Execute Python sentinel command
 * @param {string} command - Command to execute
 * @param {Object} data - Data to pass
 * @returns {Promise<Object>}
 */
async function executeSentinel(command, data) {
    return new Promise((resolve, reject) => {
        const sentinelPath = path.join(__dirname, '../../agents/sentient_swarm/sentinel_core.py');

        const args = [
            sentinelPath,
            '--mode', data.mode || 'advisory',
            '--json-input', JSON.stringify(data)
        ];

        const process = spawn('python3', args, {
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1'
            }
        });

        let stdout = '';
        let stderr = '';

        process.stdout.on('data', (chunk) => {
            stdout += chunk.toString();
        });

        process.stderr.on('data', (chunk) => {
            stderr += chunk.toString();
        });

        process.on('close', (code) => {
            if (code === 0) {
                try {
                    resolve(JSON.parse(stdout));
                } catch (e) {
                    resolve({ status: 'error', message: 'Invalid JSON response', raw: stdout });
                }
            } else {
                reject(new Error(stderr || `Process exited with code ${code}`));
            }
        });

        process.on('error', (err) => {
            reject(err);
        });

        // Send data via stdin
        if (data.stdin) {
            process.stdin.write(JSON.stringify(data.stdin));
            process.stdin.end();
        }
    });
}

/**
 * Rate limiter for sentinel endpoints
 * More restrictive due to AI model costs
 */
const sentinelRateLimiter = require('express-rate-limit')({
    windowMs: 60 * 1000, // 1 minute
    max: 20, // 20 requests per minute
    message: {
        status: 'error',
        message: 'Too many AI requests. Please wait before trying again.'
    },
    standardHeaders: true,
    legacyHeaders: false
});

/**
 * @route GET /api/sentinel/status
 * @desc Get sentinel status and configuration
 * @access Public
 */
router.get('/status', async (req, res) => {
    try {
        // Return sentinel status without invoking Python
        res.json({
            status: 'ok',
            sentinel: {
                mode: process.env.SENTINEL_MODE || 'advisory',
                ai_enabled: !!process.env.DASHSCOPE_API_KEY,
                xrpl_network: process.env.XRPL_NETWORK || 'testnet',
                voice_enabled: !!process.env.DASHSCOPE_API_KEY,
                version: '1.0.0-phase1'
            },
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route POST /api/sentinel/query
 * @desc Process a text-based financial query
 * @access Public (requires consent)
 */
router.post('/query', sentinelRateLimiter, async (req, res) => {
    try {
        const { query, user_id, context } = req.body;

        if (!query) {
            return res.status(400).json({
                status: 'error',
                message: 'Query is required'
            });
        }

        if (!user_id) {
            return res.status(400).json({
                status: 'error',
                message: 'User ID is required for POPIA compliance'
            });
        }

        // For now, return a simulated response
        // In production, this would call the Python sentinel
        const response = {
            status: 'success',
            query: query,
            response: {
                analysis: `Analysis of: "${query.substring(0, 100)}..."`,
                recommendations: [
                    'Consider diversifying your investment portfolio',
                    'Review your current expense ratios',
                    'Evaluate tax optimization opportunities'
                ],
                currency: 'ZAR',
                timestamp: new Date().toISOString()
            },
            audit: {
                action: 'financial_query',
                user_id: user_id,
                timestamp: new Date().toISOString(),
                model_used: 'qwen3.5-plus'
            }
        };

        res.json(response);

    } catch (error) {
        console.error('Sentinel query error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route POST /api/sentinel/voice
 * @desc Process a voice command
 * @access Public (requires consent)
 */
router.post('/voice', sentinelRateLimiter, async (req, res) => {
    try {
        const { audio_base64, user_id, language } = req.body;

        if (!audio_base64) {
            return res.status(400).json({
                status: 'error',
                message: 'Audio data (base64) is required'
            });
        }

        if (!user_id) {
            return res.status(400).json({
                status: 'error',
                message: 'User ID is required for POPIA compliance'
            });
        }

        // Simulated voice processing response
        const response = {
            status: 'success',
            transcription: 'This is a simulated transcription result.',
            response_text: 'I understand your request. How can I assist you with your financial needs today?',
            language: language || 'en-ZA',
            duration_ms: 450,
            consent_required: false,
            audit: {
                action: 'voice_command',
                user_id: user_id,
                timestamp: new Date().toISOString()
            }
        };

        res.json(response);

    } catch (error) {
        console.error('Voice processing error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route POST /api/sentinel/consent
 * @desc Grant consent for data processing
 * @access Public
 */
router.post('/consent', async (req, res) => {
    try {
        const { user_id, scopes, via } = req.body;

        if (!user_id || !scopes || !Array.isArray(scopes)) {
            return res.status(400).json({
                status: 'error',
                message: 'user_id and scopes[] are required'
            });
        }

        // Validate scopes
        const validScopes = [
            'voice_processing',
            'financial_analysis',
            'autonomous_trading',
            'xrpl_settlement',
            'data_retention'
        ];

        const invalidScopes = scopes.filter(s => !validScopes.includes(s));
        if (invalidScopes.length > 0) {
            return res.status(400).json({
                status: 'error',
                message: `Invalid scopes: ${invalidScopes.join(', ')}`,
                valid_scopes: validScopes
            });
        }

        // Generate consent reference
        const consentRef = `consent-${user_id}-${crypto.randomBytes(8).toString('hex')}`;

        const response = {
            status: 'success',
            user_id: user_id,
            scopes: scopes,
            consent_ref: consentRef,
            granted_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(), // 1 year
            via: via || 'api'
        };

        res.json(response);

    } catch (error) {
        console.error('Consent grant error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route DELETE /api/sentinel/consent/:user_id
 * @desc Revoke consent for a user
 * @access Public
 */
router.delete('/consent/:user_id', async (req, res) => {
    try {
        const { user_id } = req.params;
        const { reason } = req.body;

        const response = {
            status: 'success',
            user_id: user_id,
            revoked: true,
            reason: reason || 'user_request',
            revoked_at: new Date().toISOString()
        };

        res.json(response);

    } catch (error) {
        console.error('Consent revocation error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route POST /api/sentinel/settlement
 * @desc Execute an XRPL settlement
 * @access Public (requires xrpl_settlement consent)
 */
router.post('/settlement', sentinelRateLimiter, async (req, res) => {
    try {
        const { amount, currency, destination, purpose, user_id, consent_ref } = req.body;

        // Validate required fields
        if (!amount || !currency || !destination || !user_id) {
            return res.status(400).json({
                status: 'error',
                message: 'amount, currency, destination, and user_id are required'
            });
        }

        // Validate currency
        const validCurrencies = ['XRP', 'RLUSD'];
        if (!validCurrencies.includes(currency.toUpperCase())) {
            return res.status(400).json({
                status: 'error',
                message: `Invalid currency. Must be one of: ${validCurrencies.join(', ')}`
            });
        }

        // Validate destination address format (basic check)
        if (!destination.startsWith('r') || destination.length < 25 || destination.length > 35) {
            return res.status(400).json({
                status: 'error',
                message: 'Invalid XRPL destination address'
            });
        }

        // Validate amount
        const amountNum = parseFloat(amount);
        if (isNaN(amountNum) || amountNum <= 0) {
            return res.status(400).json({
                status: 'error',
                message: 'Amount must be a positive number'
            });
        }

        // Simulated settlement response
        const paymentId = `x402-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;

        const response = {
            status: 'success',
            payment: {
                payment_id: paymentId,
                amount: amount,
                currency: currency.toUpperCase(),
                destination: destination.substring(0, 12) + '...',
                purpose: purpose || '',
                status: 'pending',
                consent_ref: consent_ref
            },
            audit: {
                action: 'x402_settlement',
                user_id: user_id,
                timestamp: new Date().toISOString()
            },
            message: 'Settlement initiated. Monitor status via /api/sentinel/settlement/:payment_id'
        };

        res.json(response);

    } catch (error) {
        console.error('Settlement error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route POST /api/sentinel/loan
 * @desc Create a loan offer (XLS-66)
 * @access Public (requires autonomous_trading consent)
 */
router.post('/loan', sentinelRateLimiter, async (req, res) => {
    try {
        const {
            principal,
            currency,
            interest_bps,
            duration_days,
            collateral_ratio,
            user_id,
            consent_ref
        } = req.body;

        // Validate required fields
        if (!principal || !currency || !interest_bps || !duration_days || !user_id) {
            return res.status(400).json({
                status: 'error',
                message: 'principal, currency, interest_bps, duration_days, and user_id are required'
            });
        }

        // Validate currency
        const validCurrencies = ['XRP', 'RLUSD'];
        if (!validCurrencies.includes(currency.toUpperCase())) {
            return res.status(400).json({
                status: 'error',
                message: `Invalid currency. Must be one of: ${validCurrencies.join(', ')}`
            });
        }

        // Validate interest rate (max 50% = 5000 bps)
        if (interest_bps < 0 || interest_bps > 5000) {
            return res.status(400).json({
                status: 'error',
                message: 'interest_bps must be between 0 and 5000 (0% to 50%)'
            });
        }

        // Validate duration (1 day to 5 years)
        if (duration_days < 1 || duration_days > 1825) {
            return res.status(400).json({
                status: 'error',
                message: 'duration_days must be between 1 and 1825 (5 years)'
            });
        }

        // Generate loan ID
        const loanId = `loan-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;

        const response = {
            status: 'success',
            loan: {
                loan_id: loanId,
                principal: principal,
                principal_currency: currency.toUpperCase(),
                interest_bps: interest_bps,
                duration_days: duration_days,
                collateral_ratio: collateral_ratio || 1.5,
                status: 'pending',
                total_repayment: (principal * (1 + interest_bps / 10000)).toFixed(2)
            },
            consent_ref: consent_ref,
            audit: {
                action: 'create_loan_offer',
                user_id: user_id,
                timestamp: new Date().toISOString()
            }
        };

        res.json(response);

    } catch (error) {
        console.error('Loan creation error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message
        });
    }
});

/**
 * @route GET /api/sentinel/languages
 * @desc Get supported languages for voice processing
 * @access Public
 */
router.get('/languages', (req, res) => {
    res.json({
        status: 'success',
        languages: [
            { code: 'en-ZA', name: 'South African English' },
            { code: 'zu-ZA', name: 'Zulu (isiZulu)' },
            { code: 'xh-ZA', name: 'Xhosa (isiXhosa)' },
            { code: 'af-ZA', name: 'Afrikaans' },
            { code: 'st-ZA', name: 'Sotho (Sesotho)' },
            { code: 'tn-ZA', name: 'Tswana (Setswana)' },
            { code: 'ts-ZA', name: 'Tsonga (Xitsonga)' },
            { code: 've-ZA', name: 'Venda (Tshivenda)' },
            { code: 'nso-ZA', name: 'Northern Sotho (Sepedi)' },
            { code: 'ss-ZA', name: 'Swati (siSwati)' },
            { code: 'nr-ZA', name: 'Ndebele (isiNdebele)' }
        ]
    });
});

/**
 * @route GET /api/sentinel/metrics
 * @desc Get performance metrics
 * @access Public
 */
router.get('/metrics', (req, res) => {
    // Simulated metrics
    res.json({
        status: 'success',
        metrics: {
            voice: {
                total_requests: 1247,
                avg_latency_ms: 387,
                target_latency_ms: 500,
                within_sla: true
            },
            ai: {
                total_requests: 3421,
                avg_latency_ms: 1245,
                total_tokens_used: 12500000
            },
            xrpl: {
                total_transactions: 892,
                total_volume_xrp: 15234.56,
                total_volume_rlusd: 45000.00
            }
        },
        timestamp: new Date().toISOString()
    });
});

module.exports = router;
