const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { catchAsync } = require('../middleware/errorHandler');

exports.createCheckoutSession = catchAsync(async (req, res, next) => {
    const { priceId, planType } = req.body;
    const user = req.user;

    const session = await stripe.checkout.sessions.create({
        payment_method_types: ['card'],
        line_items: [
            {
                price: priceId,
                quantity: 1,
            },
        ],
        mode: 'subscription',
        success_url: `${process.env.DOMAIN}/success.html?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${process.env.DOMAIN}/canceled.html`,
        customer_email: user.email,
        metadata: {
            userId: user.id,
            planType
        }
    });

    res.status(201).json({
        sessionId: session.id
    });
});
