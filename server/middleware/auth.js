/**
 * Authentication Middleware Module
 * 
 * Handles JWT-based authentication, user login, signup, password management,
 * and route protection for the Vaal AI Empire platform.
 * 
 * @module server/middleware/auth
 * @requires jsonwebtoken
 * @requires crypto
 * @requires ../models/User
 * @requires ./errorHandler
 * 
 * @security APEX v2.0 Compliant
 * @security JWT tokens with configurable expiration
 * @security Password hashing via bcrypt (in User model)
 * @security Account lockout after failed login attempts
 * @security POPIA compliant - minimal PII in tokens
 */

const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const crypto = require('crypto');
const User = require('../models/User');
const { AppError, catchAsync } = require('./errorHandler');

// JWT Configuration - Fail fast if JWT_SECRET is not set
if (!process.env.JWT_SECRET) {
    if (process.env.NODE_ENV === 'test' || process.env.NODE_ENV === 'development') {
        console.warn('⚠️  WARNING: JWT_SECRET not set. Using insecure development fallback.');
        console.warn('⚠️  This should NEVER happen in production!');
    } else {
        throw new Error('JWT_SECRET environment variable must be set');
    }
}

/**
 * JWT secret key for token signing.
 * @type {string}
 * @constant
 */
const JWT_SECRET = process.env.JWT_SECRET || 'development-insecure-jwt-secret-do-not-use-in-production';

/**
 * JWT token expiration time.
 * @type {string}
 * @constant
 * @default '7d'
 */
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

/**
 * JWT cookie expiration time in days.
 * @type {number}
 * @constant
 * @default 7
 */
const JWT_COOKIE_EXPIRES_IN = process.env.JWT_COOKIE_EXPIRES_IN || 7;

/**
 * Generates a JWT token for a given user ID.
 * 
 * @function signToken
 * @param {string} id - MongoDB user ID to encode in the token
 * @returns {string} Signed JWT token
 * @example
 * const token = signToken('507f1f77bcf86cd799439011');
 */
const signToken = (id) => {
    return jwt.sign({ id }, JWT_SECRET, {
        expiresIn: JWT_EXPIRES_IN
    });
};

/**
 * Creates a JWT token and sends it in response (cookie + JSON body).
 * 
 * @function createSendToken
 * @param {Object} user - Mongoose user document
 * @param {number} statusCode - HTTP status code for the response
 * @param {Object} res - Express response object
 * @returns {void} Sends response with token and user data
 * 
 * @example
 * createSendToken(user, 201, res);
 * // Response: { status: 'success', token: '...', data: { user: {...} } }
 */
const createSendToken = (user, statusCode, res) => {
    const token = signToken(user._id);

    // Cookie options - secure in production
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
            user: user.getProfile()
        }
    });
};

/**
 * Handles user signup/registration.
 * 
 * @function signup
 * @async
 * @param {Object} req - Express request object
 * @param {Object} req.body - Request body
 * @param {string} req.body.email - User email address
 * @param {string} req.body.password - User password
 * @param {string} req.body.passwordConfirm - Password confirmation
 * @param {string} [req.body.firstName] - User first name
 * @param {string} [req.body.lastName] - User last name
 * @param {string} [req.body.company] - Company name
 * @param {string} [req.body.phone] - Phone number
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with token and user data
 * 
 * @throws {AppError} 400 - Missing email or password
 * @throws {AppError} 400 - Passwords do not match
 * @throws {AppError} 400 - User already exists
 * 
 * @example
 * // POST /api/auth/signup
 * // Body: { email: 'user@example.com', password: 'password123', passwordConfirm: 'password123' }
 */
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

/**
 * Handles user login authentication.
 * 
 * @function login
 * @async
 * @param {Object} req - Express request object
 * @param {Object} req.body - Request body
 * @param {string} req.body.email - User email address
 * @param {string} req.body.password - User password
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with token and user data
 * 
 * @throws {AppError} 400 - Missing email or password
 * @throws {AppError} 401 - Incorrect email or password
 * @throws {AppError} 423 - Account locked due to too many failed attempts
 * @throws {AppError} 401 - Email not verified (if verification required)
 * 
 * @security Implements account lockout after failed attempts
 * @security Updates last login timestamp on success
 * 
 * @example
 * // POST /api/auth/login
 * // Body: { email: 'user@example.com', password: 'password123' }
 */
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

/**
 * Handles user logout by clearing the JWT cookie.
 * 
 * @function logout
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @returns {void} Sends JSON response confirming logout
 * 
 * @example
 * // GET /api/auth/logout
 * // Response: { status: 'success', message: 'Logged out successfully' }
 */
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

/**
 * Middleware to protect routes - requires valid JWT token.
 * 
 * Verifies the JWT token from Authorization header or cookie,
 * checks if the user still exists and hasn't changed password.
 * 
 * @function protect
 * @async
 * @param {Object} req - Express request object
 * @param {Object} req.headers.authorization - Bearer token (optional)
 * @param {Object} req.cookies.jwt - JWT cookie (optional)
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sets req.user if authenticated
 * 
 * @throws {AppError} 401 - Not logged in
 * @throws {AppError} 401 - Invalid token
 * @throws {AppError} 401 - User no longer exists
 * @throws {AppError} 401 - Password changed after token issued
 * 
 * @example
 * // Use as middleware
 * router.get('/protected-route', auth.protect, controller.handler);
 */
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

/**
 * Middleware factory to restrict access to specific roles.
 * 
 * @function restrictTo
 * @param {...string} roles - Roles that are allowed access
 * @returns {Function} Express middleware function
 * 
 * @throws {AppError} 403 - User does not have permission
 * 
 * @example
 * // Only allow admins
 * router.delete('/users/:id', auth.protect, auth.restrictTo('admin'), controller.deleteUser);
 * 
 * // Allow multiple roles
 * router.put('/orders/:id', auth.protect, auth.restrictTo('admin', 'manager'), controller.updateOrder);
 */
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

/**
 * Handles forgot password request - generates reset token.
 * 
 * @function forgotPassword
 * @async
 * @param {Object} req - Express request object
 * @param {Object} req.body.email - User email address
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with success message
 * 
 * @throws {AppError} 404 - No user with that email
 * @throws {AppError} 500 - Error sending email
 * 
 * @example
 * // POST /api/auth/forgot-password
 * // Body: { email: 'user@example.com' }
 */
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

/**
 * Handles password reset with valid token.
 * 
 * @function resetPassword
 * @async
 * @param {Object} req - Express request object
 * @param {string} req.params.token - Password reset token
 * @param {Object} req.body - Request body
 * @param {string} req.body.password - New password
 * @param {string} req.body.passwordConfirm - Password confirmation
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with new token
 * 
 * @throws {AppError} 400 - Token invalid or expired
 * @throws {AppError} 400 - Passwords do not match
 * 
 * @example
 * // PATCH /api/auth/reset-password/:token
 * // Body: { password: 'newpassword123', passwordConfirm: 'newpassword123' }
 */
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

/**
 * Handles password update for logged-in users.
 * 
 * @function updatePassword
 * @async
 * @param {Object} req - Express request object (requires auth)
 * @param {Object} req.body - Request body
 * @param {string} req.body.passwordCurrent - Current password
 * @param {string} req.body.password - New password
 * @param {string} req.body.passwordConfirm - New password confirmation
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with new token
 * 
 * @throws {AppError} 401 - Current password is wrong
 * @throws {AppError} 400 - Passwords do not match
 * 
 * @example
 * // PATCH /api/auth/update-password
 * // Headers: Authorization: Bearer <token>
 * // Body: { passwordCurrent: 'oldpass', password: 'newpass', passwordConfirm: 'newpass' }
 */
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

/**
 * Handles email verification with token.
 * 
 * @function verifyEmail
 * @async
 * @param {Object} req - Express request object
 * @param {string} req.params.token - Email verification token
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response confirming verification
 * 
 * @throws {AppError} 400 - Invalid token or user already verified
 * 
 * @example
 * // GET /api/auth/verify-email/:token
 */
exports.verifyEmail = catchAsync(async (req, res, next) => {
    const { token } = req.params;

    // Hash the token to compare with stored hash
    const hashedToken = crypto
        .createHash('sha256')
        .update(token)
        .digest('hex');

    const user = await User.findOne({
        verificationToken: hashedToken,
        isVerified: false
    });

    if (!user) {
        return next(
            new AppError('Invalid verification token or user already verified', 400)
        );
    }

    user.isVerified = true;
    user.verificationToken = undefined;
    user.verificationTokenExpires = undefined;
    await user.save({ validateBeforeSave: false });

    res.status(200).json({
        status: 'success',
        message: 'Email verified successfully'
    });
});

/**
 * Gets the current authenticated user's profile.
 * 
 * @function getMe
 * @async
 * @param {Object} req - Express request object (requires auth)
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sends JSON response with user profile
 * 
 * @throws {AppError} 404 - User not found
 * 
 * @example
 * // GET /api/auth/me
 * // Headers: Authorization: Bearer <token>
 */
exports.getMe = catchAsync(async (req, res, next) => {
    const user = await User.findById(req.user.id);
    
    if (!user) {
        return next(new AppError('User not found', 404));
    }

    res.status(200).json({
        status: 'success',
        data: {
            user: user.getProfile()
        }
    });
});

/**
 * Convenience middleware to restrict access to admin role only.
 * @type {Function}
 */
exports.adminOnly = exports.restrictTo('admin');

/**
 * Optional auth middleware - sets user if token present but doesn't require it.
 * 
 * Useful for routes that have enhanced functionality when authenticated
 * but are still accessible to unauthenticated users.
 * 
 * @function optionalAuth
 * @async
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {Promise<void>} Sets req.user if valid token present
 * 
 * @example
 * // Route accessible to all, but enhanced for logged-in users
 * router.get('/public-data', auth.optionalAuth, controller.getPublicData);
 */
exports.optionalAuth = catchAsync(async (req, res, next) => {
    let token;

    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
        token = req.headers.authorization.split(' ')[1];
    } else if (req.cookies.jwt && req.cookies.jwt !== 'loggedout') {
        token = req.cookies.jwt;
    }

    if (token) {
        try {
            const decoded = await promisify(jwt.verify)(token, JWT_SECRET);
            const currentUser = await User.findById(decoded.id);
            if (currentUser && !currentUser.changedPasswordAfter(decoded.iat)) {
                req.user = currentUser;
                res.locals.user = currentUser;
            }
        } catch (err) {
            // Token invalid, but that's okay for optional auth
        }
    }

    next();
});

/**
 * @typedef {Object} AuthModule
 * @property {Function} signup - User registration handler
 * @property {Function} login - User login handler
 * @property {Function} logout - User logout handler
 * @property {Function} protect - Route protection middleware
 * @property {Function} restrictTo - Role-based access control middleware
 * @property {Function} forgotPassword - Password reset request handler
 * @property {Function} resetPassword - Password reset handler
 * @property {Function} updatePassword - Password update handler
 * @property {Function} verifyEmail - Email verification handler
 * @property {Function} getMe - Current user profile handler
 * @property {Function} signToken - JWT token generator
 * @property {Function} adminOnly - Admin-only middleware
 * @property {Function} optionalAuth - Optional auth middleware
 */

// Default export for compatibility
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
    signToken: exports.signToken,
    adminOnly: exports.adminOnly,
    optionalAuth: exports.optionalAuth
};
