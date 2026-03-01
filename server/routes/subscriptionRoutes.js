const express = require('express');
const { createCheckoutSession } = require('../controllers/subscriptionController');
const { protect } = require('../middleware/auth');

const router = express.Router();

// All subscription routes should be protected
router.use(protect);

router.post('/create-checkout', createCheckoutSession);

module.exports = router;
