const express = require('express');
const { createPaymentIntent, getStripeConfig } = require('../controllers/paymentController');
const { protect } = require('../middleware/auth');

const router = express.Router();

// This endpoint is public, so it doesn't need protection
router.get('/config/stripe', getStripeConfig);

// All payment routes below should be protected
router.use(protect);

router.post('/create-intent', createPaymentIntent);

module.exports = router;
