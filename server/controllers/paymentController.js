const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { catchAsync } = require('../middleware/errorHandler');
const { AppError } = require('../middleware/errorHandler');

exports.getStripeConfig = (req, res) => {
    res.status(200).json({
        publishableKey: process.env.STRIPE_PUBLISHABLE_KEY
    });
};

exports.createPaymentIntent = catchAsync(async (req, res, next) => {
    const { amount, currency, paymentMethod, customerEmail, customerName, metadata } = req.body;

    if (!amount || amount < 500) { // Minimum amount of 500 cents (R5.00)
        return next(new AppError('Amount must be at least R5.00', 400));
    }

    const paymentIntent = await stripe.paymentIntents.create({
        amount,
        currency,
        payment_method_types: [paymentMethod],
        receipt_email: customerEmail,
        description: `Payment from ${customerName}`,
        metadata
    });

    res.status(201).json({
        clientSecret: paymentIntent.client_secret,
        paymentIntentId: paymentIntent.id
    });
});
