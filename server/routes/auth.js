const express = require('express');
const {
    signup,
    login,
    logout,
    protect,
    restrictTo,
    forgotPassword,
    resetPassword,
    updatePassword,
    verifyEmail,
    getMe
} = require('../middleware/auth');

const router = express.Router();

// Public routes
router.post('/signup', signup);
router.post('/login', login);
router.post('/logout', logout);
router.post('/forgot-password', forgotPassword);
router.patch('/reset-password/:token', resetPassword);
router.get('/verify-email/:token', verifyEmail);

// Protected routes (require authentication)
router.use(protect); // All routes after this require authentication

router.get('/me', getMe);
router.patch('/update-password', updatePassword);

// Admin only routes
router.get('/admin', restrictTo('admin'), (req, res) => {
    res.status(200).json({
        status: 'success',
        message: 'Admin access granted'
    });
});

module.exports = router;