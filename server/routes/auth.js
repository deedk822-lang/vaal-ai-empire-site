'use strict';

/**
 * auth.js — Vaal AI Empire
 * Production-grade authentication & authorisation middleware.
 *
 * Fixes applied vs previous revision:
 *  • Deduplicated token-extraction into extractToken(req)
 *  • getMe: null-guard on User.findById result
 *  • verifyEmail: added verificationTokenExpires check
 *  • optionalAuth: only swallows JWT errors, re-throws all others
 *  • Removed final module.exports reassignment (used exports.* throughout)
 */

const crypto       = require('crypto');
const { promisify } = require('util');
const jwt          = require('jsonwebtoken');
const User         = require('../models/User');
const AppError     = require('../utils/appError');
const catchAsync   = require('../utils/catchAsync');

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/**
 * Sign a JWT for a given user id.
 * @param {string} id  MongoDB ObjectId as string
 * @returns {string}   Signed JWT
 */
const signToken = (id) =>
  jwt.sign({ id }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || '90d',
  });

exports.signToken = signToken;

/**
 * Send a JWT cookie + JSON response.
 */
const createSendToken = (user, statusCode, req, res) => {
  const token = signToken(user._id);

  const cookieOptions = {
    expires: new Date(
      Date.now() +
        parseInt(process.env.JWT_COOKIE_EXPIRES_IN || 90, 10) *
          24 * 60 * 60 * 1000,
    ),
    httpOnly: true,
    secure:   req.secure || req.headers['x-forwarded-proto'] === 'https',
    sameSite: 'strict',
  };

  res.cookie('jwt', token, cookieOptions);

  // Remove sensitive fields before sending
  user.password = undefined;
  user.__v      = undefined;

  res.status(statusCode).json({
    status: 'success',
    token,
    data: { user },
  });
};

/**
 * Shared token extractor — Bearer header takes priority, then cookie.
 * Returns the raw JWT string or null.
 * @param {import('express').Request} req
 * @returns {string|null}
 */
const extractToken = (req) => {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.split(' ')[1];
  }
  if (req.cookies && req.cookies.jwt && req.cookies.jwt !== 'loggedout') {
    return req.cookies.jwt;
  }
  return null;
};

// ─────────────────────────────────────────────
// Auth handlers
// ─────────────────────────────────────────────

exports.signup = catchAsync(async (req, res, next) => {
  const { name, email, password, passwordConfirm } = req.body;

  const newUser = await User.create({ name, email, password, passwordConfirm });

  // Capture raw verification token BEFORE it disappears from the doc
  const rawToken = newUser._rawVerificationToken;
  delete newUser._rawVerificationToken;

  if (rawToken) {
    // Fire-and-forget — don't block registration if email fails
    try {
      const { sendVerificationEmail } = require('../utils/email');
      await sendVerificationEmail(newUser.email, rawToken);
    } catch (err) {
      // Log but don't surface to client
      console.error('[signup] Verification email failed:', err.message);
    }
  }

  createSendToken(newUser, 201, req, res);
});

exports.login = catchAsync(async (req, res, next) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return next(new AppError('Please provide email and password.', 400));
  }

  const user = await User.findOne({ email }).select('+password');

  if (!user || !(await user.correctPassword(password, user.password))) {
    return next(new AppError('Incorrect email or password.', 401));
  }

  createSendToken(user, 200, req, res);
});

exports.logout = (req, res) => {
  res.cookie('jwt', 'loggedout', {
    expires:  new Date(Date.now() + 10 * 1000),
    httpOnly: true,
    sameSite: 'strict',
  });
  res.status(200).json({ status: 'success' });
};

// ─────────────────────────────────────────────
// Route protection
// ─────────────────────────────────────────────

exports.protect = catchAsync(async (req, res, next) => {
  const token = extractToken(req);

  if (!token) {
    return next(
      new AppError('You are not logged in. Please log in to get access.', 401),
    );
  }

  // Verify token — throws JsonWebTokenError / TokenExpiredError on failure
  const decoded = await promisify(jwt.verify)(token, process.env.JWT_SECRET);

  // Check user still exists
  const currentUser = await User.findById(decoded.id);
  if (!currentUser) {
    return next(
      new AppError('The user belonging to this token no longer exists.', 401),
    );
  }

  // Check password wasn't changed after token was issued
  if (currentUser.changedPasswordAfter(decoded.iat)) {
    return next(
      new AppError('User recently changed password. Please log in again.', 401),
    );
  }

  req.user        = currentUser;
  res.locals.user = currentUser;
  next();
});

/**
 * Optional auth — populates req.user when a valid token is present but
 * never blocks the request.  Only JWT-specific errors are swallowed;
 * all other errors (DB, unexpected) are propagated via next(err).
 */
exports.optionalAuth = async (req, res, next) => {
  try {
    const token = extractToken(req);
    if (!token) return next();

    const decoded     = await promisify(jwt.verify)(token, process.env.JWT_SECRET);
    const currentUser = await User.findById(decoded.id);

    if (currentUser && !currentUser.changedPasswordAfter(decoded.iat)) {
      req.user        = currentUser;
      res.locals.user = currentUser;
    }

    return next();
  } catch (err) {
    // Only swallow JWT-specific errors
    if (
      err instanceof jwt.JsonWebTokenError ||
      err instanceof jwt.TokenExpiredError ||
      err instanceof jwt.NotBeforeError
    ) {
      return next(); // Treat as unauthenticated
    }
    // All other errors (DB connectivity, unexpected) must propagate
    return next(err);
  }
};

// ─────────────────────────────────────────────
// Role-based access
// ─────────────────────────────────────────────

exports.restrictTo = (...roles) =>
  (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(
        new AppError('You do not have permission to perform this action.', 403),
      );
    }
    next();
  };

/** Convenience alias — restrict to admin only */
exports.adminOnly = exports.restrictTo('admin');

// ─────────────────────────────────────────────
// Password reset
// ─────────────────────────────────────────────

exports.forgotPassword = catchAsync(async (req, res, next) => {
  const user = await User.findOne({ email: req.body.email });
  if (!user) {
    return next(new AppError('There is no user with that email address.', 404));
  }

  const resetToken = user.createPasswordResetToken();
  await user.save({ validateBeforeSave: false });

  try {
    const resetURL = `${req.protocol}://${req.get('host')}/api/v1/auth/resetPassword/${resetToken}`;
    const { sendPasswordResetEmail } = require('../utils/email');
    await sendPasswordResetEmail(user.email, resetURL);

    res.status(200).json({ status: 'success', message: 'Token sent to email.' });
  } catch (err) {
    user.passwordResetToken   = undefined;
    user.passwordResetExpires = undefined;
    await user.save({ validateBeforeSave: false });

    return next(
      new AppError('There was an error sending the email. Try again later.', 500),
    );
  }
});

exports.resetPassword = catchAsync(async (req, res, next) => {
  const hashedToken = crypto
    .createHash('sha256')
    .update(req.params.token)
    .digest('hex');

  const user = await User.findOne({
    passwordResetToken:   hashedToken,
    passwordResetExpires: { $gt: Date.now() },
  });

  if (!user) {
    return next(new AppError('Token is invalid or has expired.', 400));
  }

  user.password             = req.body.password;
  user.passwordConfirm      = req.body.passwordConfirm;
  user.passwordResetToken   = undefined;
  user.passwordResetExpires = undefined;
  await user.save();

  createSendToken(user, 200, req, res);
});

exports.updatePassword = catchAsync(async (req, res, next) => {
  const user = await User.findById(req.user.id).select('+password');

  if (!(await user.correctPassword(req.body.passwordCurrent, user.password))) {
    return next(new AppError('Your current password is wrong.', 401));
  }

  user.password        = req.body.password;
  user.passwordConfirm = req.body.passwordConfirm;
  await user.save();

  createSendToken(user, 200, req, res);
});

// ─────────────────────────────────────────────
// Email verification
// ─────────────────────────────────────────────

exports.verifyEmail = catchAsync(async (req, res, next) => {
  const hashedToken = crypto
    .createHash('sha256')
    .update(req.params.token)
    .digest('hex');

  // Include expiry check to reject stale tokens
  const user = await User.findOne({
    verificationToken:          hashedToken,
    isVerified:                 false,
    verificationTokenExpires:   { $gt: Date.now() },   // ← was missing
  });

  if (!user) {
    return next(
      new AppError('Verification token is invalid or has expired.', 400),
    );
  }

  user.isVerified               = true;
  user.verificationToken        = undefined;
  user.verificationTokenExpires = undefined;
  await user.save({ validateBeforeSave: false });

  res.status(200).json({ status: 'success', message: 'Email verified successfully.' });
});

// ─────────────────────────────────────────────
// Current user
// ─────────────────────────────────────────────

exports.getMe = catchAsync(async (req, res, next) => {
  const user = await User.findById(req.user.id);

  // Null-guard — user might have been deleted after token was issued
  if (!user) {
    return next(new AppError('User not found.', 404));
  }

  res.status(200).json({
    status: 'success',
    data:   { user: user.getProfile() },
  });
});
