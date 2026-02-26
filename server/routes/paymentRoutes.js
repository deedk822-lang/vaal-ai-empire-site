/**
 * PayFast Payment Routes
 * South African payment gateway integration
 * 
 * APEX Security Framework v2.0 Compliant
 */

const express = require('express');
const router = express.Router();
const rateLimit = require('express-rate-limit');
const {
    getPayFastConfig,
    createPayment,
    verifyITN,
    getPaymentStatus
} = require('../controllers/paymentController');

// APEX: Rate limiting on payment endpoints
const paymentLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 50, // 50 requests per window
    message: {
        error: 'Too many payment requests. Please try again later.'
    },
    standardHeaders: true,
    legacyHeaders: false
});

/**
 * @route   GET /api/payments/config
 * @desc    Get PayFast configuration (non-sensitive)
 * @access  Public
 */
router.get('/config', getPayFastConfig);

/**
 * @route   POST /api/payments/create
 * @desc    Create new PayFast payment
 * @access  Public (with rate limiting)
 */
router.post('/create', paymentLimiter, createPayment);

/**
 * @route   POST /payfast/notify
 * @desc    PayFast ITN (Instant Transaction Notification) webhook
 * @access  Public (PayFast servers only)
 */
router.post('/payfast/notify', verifyITN);

/**
 * @route   GET /api/payments/status/:paymentId
 * @desc    Get payment status
 * @access  Private (authenticated users)
 */
router.get('/status/:paymentId', getPaymentStatus);

module.exports = router;
