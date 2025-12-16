const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const crypto = require('crypto');
const User = require('../models/User');
const { AppError, catchAsync } = require('./errorHandler');

// JWT Configuration
const JWT_SECRET = process.env.JWT_SECRET || 'vaal-ai-empire-jwt-secret-key-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';
const JWT_COOKIE_EXPIRES_IN = process.env.JWT_COOKIE_EXPIRES_IN || 7;

// Generate JWT token
const signToken = (id) => {
    return jwt.sign({ id }, JWT_SECRET, {
        expiresIn: JWT_EXPIRES_IN
    });
};

// Create and send token
const createSendToken = (user, statusCode, res) => {
    const token = signToken(user._id);
    
    // Cookie options
    const cookieOptions = {
        expires: new Date(
            Date.now() + JWT_COOKIE_EXPIRES_IN * 24 * 60 * 60 * 1000
        ),
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict'
    };
    
    res.cookie('jwt', token, cookieOptions);
    
    // Remove password from output
    user.password = undefined;
    
    res.status(statusCode).json({
        status: 'success',
        token,
        data: {
            user
        }
    });
};

// Signup
exports.signup = catchAsync(async (req, res, next) => {
    const { email, password, passwordConfirm, firstName, lastName, company, phone } = req.body;
    
    // Validate required fields
    if (!email || !password) {
        return next(new AppError('Please provide email and password', 400));
    }
    
    if (password !== passwordConfirm) {
        return next(new AppError('Passwords do not match', 400));
    }
    
    // Check if user already exists
    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) {
        return next(new AppError('User with this email already exists', 400));
    }
    
    // Create new user
    const newUser = await User.create({
        email: email.toLowerCase(),
        password,
        firstName,
        lastName,
        company,
        phone
    });
    
    // TODO: Send verification email
    // await sendVerificationEmail(newUser.email, newUser.verificationToken);
    
    createSendToken(newUser, 201, res);
});

// Login
exports.login = catchAsync(async (req, res, next) => {
    const { email, password } = req.body;
    
    // 1) Check if email and password exist
    if (!email || !password) {
        return next(new AppError('Please provide email and password', 400));
    }
    
    // 2) Check if user exists && password is correct
    const user = await User.findOne({ email: email.toLowerCase() }).select('+password');
    
    if (!user) {
        return next(new AppError('Incorrect email or password', 401));
    }
    
    // 3) Check if user is locked
    if (user.isLocked) {
        const lockTime = Math.ceil((user.lockUntil - Date.now()) / 60000);
        return next(
            new AppError(
                `Account is locked. Please try again in ${lockTime} minutes.`,
                423
            )
        );
    }
    
    // 4) Verify password
    const isPasswordCorrect = await user.comparePassword(password);
    
    if (!isPasswordCorrect) {
        // Increment login attempts
        await user.incrementLoginAttempts();
        return next(new AppError('Incorrect email or password', 401));
    }
    
    // 5) Check if user is verified
    if (!user.isVerified && process.env.REQUIRE_EMAIL_VERIFICATION === 'true') {
        return next(new AppError('Please verify your email before logging in', 401));
    }
    
    // 6) Reset login attempts and update last login
    await user.resetLoginAttempts();
    user.lastLogin = new Date();
    await user.save({ validateBeforeSave: false });
    
    // 7) If everything ok, send token to client
    createSendToken(user, 200, res);
});

// Logout
exports.logout = (req, res) => {
    res.cookie('jwt', 'loggedout', {
        expires: new Date(Date.now() + 10 * 1000),
        httpOnly: true
    });
    
    res.status(200).json({
        status: 'success',
        message: 'Logged out successfully'
    });
};

// Protect routes middleware
exports.protect = catchAsync(async (req, res, next) => {
    // 1) Getting token and check if it's there
    let token;
    
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
        token = req.headers.authorization.split(' ')[1];
    } else if (req.cookies.jwt && req.cookies.jwt !== 'loggedout') {
        token = req.cookies.jwt;
    }
    
    if (!token) {
        return next(
            new AppError('You are not logged in! Please log in to get access.', 401)
        );
    }
    
    // 2) Verification token
    const decoded = await promisify(jwt.verify)(token, JWT_SECRET);
    
    // 3) Check if user still exists
    const currentUser = await User.findById(decoded.id);
    if (!currentUser) {
        return next(
            new AppError('The user belonging to this token does no longer exist.', 401)
        );
    }
    
    // 4) Check if user changed password after the token was issued
    if (currentUser.changedPasswordAfter(decoded.iat)) {
        return next(
            new AppError('User recently changed password! Please log in again.', 401)
        );
    }
    
    // GRANT ACCESS TO PROTECTED ROUTE
    req.user = currentUser;
    res.locals.user = currentUser;
    next();
});

// Restrict to certain roles
exports.restrictTo = (...roles) => {
    return (req, res, next) => {
        if (!roles.includes(req.user.role)) {
            return next(
                new AppError('You do not have permission to perform this action', 403)
            );
        }
        next();
    };
};

// Forgot password
exports.forgotPassword = catchAsync(async (req, res, next) => {
    // 1) Get user based on POSTed email
    const user = await User.findOne({ email: req.body.email });
    
    if (!user) {
        return next(new AppError('There is no user with that email address.', 404));
    }
    
    // 2) Generate the random reset token
    const resetToken = user.generatePasswordResetToken();
    await user.save({ validateBeforeSave: false });
    
    // 3) Send it to user's email
    try {
        const resetURL = `${req.protocol}://${req.get('host')}/api/auth/reset-password/${resetToken}`;
        
        // TODO: Send email with resetURL
        // await sendPasswordResetEmail(user.email, resetURL);
        
        res.status(200).json({
            status: 'success',
            message: 'Password reset token sent to email',
            // Remove resetToken in production
            resetToken: process.env.NODE_ENV === 'development' ? resetToken : undefined
        });
    } catch (err) {
        user.passwordResetToken = undefined;
        user.passwordResetExpires = undefined;
        await user.save({ validateBeforeSave: false });
        
        return next(
            new AppError('There was an error sending the email. Try again later!', 500)
        );
    }
});

// Reset password
exports.resetPassword = catchAsync(async (req, res, next) => {
    // 1) Get user based on the token
    const hashedToken = crypto
        .createHash('sha256')
        .update(req.params.token)
        .digest('hex');
    
    const user = await User.findOne({
        passwordResetToken: hashedToken,
        passwordResetExpires: { $gt: Date.now() }
    });
    
    // 2) If token has not expired, and there is user, set the new password
    if (!user) {
        return next(new AppError('Token is invalid or has expired', 400));
    }
    
    if (req.body.password !== req.body.passwordConfirm) {
        return next(new AppError('Passwords do not match', 400));
    }
    
    user.password = req.body.password;
    user.passwordResetToken = undefined;
    user.passwordResetExpires = undefined;
    await user.save();
    
    // 3) Update changedPasswordAt property (handled in pre-save hook)
    
    // 4) Log the user in, send JWT
    createSendToken(user, 200, res);
});

// Update password (for logged in users)
exports.updatePassword = catchAsync(async (req, res, next) => {
    // 1) Get user from collection
    const user = await User.findById(req.user.id).select('+password');
    
    // 2) Check if POSTed current password is correct
    if (!(await user.comparePassword(req.body.passwordCurrent))) {
        return next(new AppError('Your current password is wrong.', 401));
    }
    
    // 3) Validate new password
    if (req.body.password !== req.body.passwordConfirm) {
        return next(new AppError('Passwords do not match', 400));
    }
    
    // 4) Update password
    user.password = req.body.password;
    await user.save();
    
    // 5) Log user in, send JWT
    createSendToken(user, 200, res);
});

// Verify email
exports.verifyEmail = catchAsync(async (req, res, next) => {
    const { token } = req.params;
    
    const user = await User.findOne({
        verificationToken: token,
        isVerified: false
    });
    
    if (!user) {
        return next(
            new AppError('Invalid verification token or user already verified', 400)
        );
    }
    
    user.isVerified = true;
    user.verificationToken = undefined;
    await user.save({ validateBeforeSave: false });
    
    res.status(200).json({
        status: 'success',
        message: 'Email verified successfully'
    });
});

// Get current user
exports.getMe = catchAsync(async (req, res, next) => {
    const user = await User.findById(req.user.id);
    
    res.status(200).json({
        status: 'success',
        data: {
            user
        }
    });
});

module.exports = {
    signup: exports.signup,
    login: exports.login,
    logout: exports.logout,
    protect: exports.protect,
    restrictTo: exports.restrictTo,
    forgotPassword: exports.forgotPassword,
    resetPassword: exports.resetPassword,
    updatePassword: exports.updatePassword,
    verifyEmail: exports.verifyEmail,
    getMe: exports.getMe,
    signToken
};