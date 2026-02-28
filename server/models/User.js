'use strict';

/**
 * User.js — Vaal AI Empire
 * Production-grade Mongoose user model.
 *
 * Fixes applied vs previous revision:
 *  • generateVerificationToken now sets this._rawVerificationToken
 *  • Pre-save hook comment updated to reflect caller responsibility
 *  • dataConsent.consentDate is NEVER cleared (immutable first-grant timestamp)
 *  • dataConsent.consentWithdrawnAt + consentHistory added for full audit trail
 *  • findExpiringSubscriptions and getStatistics statics retained
 */

const crypto   = require('crypto');
const mongoose = require('mongoose');
const bcrypt   = require('bcryptjs');
const validator = require('validator');

// ─────────────────────────────────────────────
// Sub-schemas
// ─────────────────────────────────────────────

const dataConsentSchema = new mongoose.Schema(
  {
    analytics:          { type: Boolean, default: false },
    marketing:          { type: Boolean, default: false },
    thirdParty:         { type: Boolean, default: false },
    /** Immutable timestamp of FIRST consent grant — never nulled */
    consentDate:        { type: Date },
    /** Set when ALL consents are withdrawn */
    consentWithdrawnAt: { type: Date },
    /** Full audit log of consent state changes */
    consentHistory: [
      {
        timestamp:  { type: Date, default: Date.now },
        analytics:  Boolean,
        marketing:  Boolean,
        thirdParty: Boolean,
        action:     { type: String, enum: ['granted', 'withdrawn', 're-granted'] },
      },
    ],
  },
  { _id: false },
);

// ─────────────────────────────────────────────
// Main schema
// ─────────────────────────────────────────────

const userSchema = new mongoose.Schema(
  {
    name: {
      type:     String,
      required: [true, 'Please provide your name.'],
      trim:     true,
      maxlength: [50, 'Name cannot exceed 50 characters.'],
    },

    email: {
      type:      String,
      required:  [true, 'Please provide your email.'],
      unique:    true,
      lowercase: true,
      validate:  [validator.isEmail, 'Please provide a valid email.'],
    },

    role: {
      type:    String,
      enum:    ['user', 'admin', 'moderator'],
      default: 'user',
    },

    password: {
      type:      String,
      required:  [true, 'Please provide a password.'],
      minlength: [8, 'Password must be at least 8 characters.'],
      select:    false,
    },

    passwordConfirm: {
      type:     String,
      required: [true, 'Please confirm your password.'],
      validate: {
        // Only runs on CREATE / SAVE
        validator(val) { return val === this.password; },
        message: 'Passwords do not match.',
      },
    },

    passwordChangedAt: Date,
    passwordResetToken: String,
    passwordResetExpires: Date,

    // APEX: Account locking mechanism for brute-force protection
    loginAttempts: { type: Number, default: 0 },
    lockUntil: { type: Date },

    isVerified: { type: Boolean, default: false },
    verificationToken:        String,
    verificationTokenExpires: Date,

    subscriptionStatus: {
      type:    String,
      enum:    ['free', 'trial', 'active', 'past_due', 'canceled', 'expired'],
      default: 'free',
    },

    subscriptionExpiresAt: Date,

    stripeCustomerId:     String,
    stripeSubscriptionId: String,

    dataConsent: { type: dataConsentSchema, default: () => ({}) },

    active: { type: Boolean, default: true, select: false },
  },
  {
    timestamps: true,
    toJSON:     { virtuals: true },
    toObject:   { virtuals: true },
  },
);

// ─────────────────────────────────────────────
// Indexes
// ─────────────────────────────────────────────

userSchema.index({ email: 1 }, { unique: true });
userSchema.index({ subscriptionExpiresAt: 1 });
userSchema.index({ stripeCustomerId: 1 }, { sparse: true });

// ─────────────────────────────────────────────
// Pre-save hooks
// ─────────────────────────────────────────────

// Hash password on change
userSchema.pre('save', async function hashPassword(next) {
  if (!this.isModified('password')) return next();
  this.password        = await bcrypt.hash(this.password, 12);
  this.passwordConfirm = undefined;
  next();
});

// Stamp passwordChangedAt when password is modified (not on new doc)
userSchema.pre('save', function stampPasswordChange(next) {
  if (!this.isModified('password') || this.isNew) return next();
  // Subtract 1 s to ensure token issued BEFORE this timestamp
  this.passwordChangedAt = new Date(Date.now() - 1000);
  next();
});

/**
 * Data-consent audit hook.
 *
 * Rules:
 *  • consentDate is the IMMUTABLE first-granted timestamp — never cleared.
 *  • consentWithdrawnAt is set when ALL consents drop to false.
 *  • consentHistory records every state transition.
 *
 * NOTE: _rawVerificationToken cleanup is the CALLER's responsibility.
 *       Capture `user._rawVerificationToken` and delete it before using it.
 */
userSchema.pre('save', function manageConsent(next) {
  if (!this.isModified('dataConsent')) return next();

  const dc = this.dataConsent;
  const hasAnyConsent = dc.analytics || dc.marketing || dc.thirdParty;

  if (hasAnyConsent) {
    // Record first-ever grant timestamp (never overwrite)
    if (!dc.consentDate) {
      dc.consentDate = new Date();
    }
    // Clear withdrawal flag if consent is re-granted
    if (dc.consentWithdrawnAt) {
      dc.consentWithdrawnAt = undefined;
      dc.consentHistory.push({
        action:     're-granted',
        analytics:  dc.analytics,
        marketing:  dc.marketing,
        thirdParty: dc.thirdParty,
      });
    } else {
      dc.consentHistory.push({
        action:     'granted',
        analytics:  dc.analytics,
        marketing:  dc.marketing,
        thirdParty: dc.thirdParty,
      });
    }
  } else {
    // All consents withdrawn — stamp withdrawal timestamp, preserve consentDate
    dc.consentWithdrawnAt = new Date();
    dc.consentHistory.push({
      action:     'withdrawn',
      analytics:  false,
      marketing:  false,
      thirdParty: false,
    });
  }

  next();
});

// Exclude inactive users from all queries
userSchema.pre(/^find/, function excludeInactive(next) {
  this.find({ active: { $ne: false } });
  next();
});

// ─────────────────────────────────────────────
// Instance methods
// ─────────────────────────────────────────────

userSchema.methods.correctPassword = async function correctPassword(
  candidatePassword,
  userPassword,
) {
  return bcrypt.compare(candidatePassword, userPassword);
};

userSchema.methods.changedPasswordAfter = function changedPasswordAfter(
  JWTTimestamp,
) {
  if (this.passwordChangedAt) {
    const changedTimestamp = Math.floor(this.passwordChangedAt.getTime() / 1000);
    return JWTTimestamp < changedTimestamp;
  }
  return false;
};

userSchema.methods.createPasswordResetToken = function createPasswordResetToken() {
  const resetToken = crypto.randomBytes(32).toString('hex');
  this.passwordResetToken = crypto
    .createHash('sha256')
    .update(resetToken)
    .digest('hex');
  this.passwordResetExpires = new Date(Date.now() + 10 * 60 * 1000); // 10 min
  return resetToken;
};

/**
 * generateVerificationToken
 *
 * Creates a hashed token stored on the document AND sets
 * this._rawVerificationToken as a transient (non-persisted) property
 * so that callers can reliably read it from the saved document.
 *
 * CALLER RESPONSIBILITY:
 *   const rawToken = user._rawVerificationToken;
 *   delete user._rawVerificationToken;
 *   await sendVerificationEmail(user.email, rawToken);
 */
userSchema.methods.generateVerificationToken = function generateVerificationToken() {
  const rawToken = crypto.randomBytes(32).toString('hex');

  this.verificationToken = crypto
    .createHash('sha256')
    .update(rawToken)
    .digest('hex');

  this.verificationTokenExpires = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 h

  // Transient — accessible after save but never persisted
  this._rawVerificationToken = rawToken;

  return rawToken;
};

/**
 * Return a safe public profile object (no sensitive fields).
 */
userSchema.methods.getProfile = function getProfile() {
  return {
    id:                 this._id,
    name:               this.name,
    email:              this.email,
    role:               this.role,
    isVerified:         this.isVerified,
    subscriptionStatus: this.subscriptionStatus,
    createdAt:          this.createdAt,
    updatedAt:          this.updatedAt,
  };
};

// ─────────────────────────────────────────────
// Statics
// ─────────────────────────────────────────────

userSchema.statics.findExpiringSubscriptions = function findExpiringSubscriptions(
  withinDays = 7,
) {
  const cutoff = new Date(Date.now() + withinDays * 24 * 60 * 60 * 1000);
  return this.find({
    subscriptionStatus:    'active',
    subscriptionExpiresAt: { $lte: cutoff, $gt: new Date() },
  });
};

userSchema.statics.getStatistics = async function getStatistics() {
  const [totals] = await this.aggregate([
    {
      $group: {
        _id:           null,
        total:         { $sum: 1 },
        verified:      { $sum: { $cond: ['$isVerified', 1, 0] } },
        active:        { $sum: { $cond: [{ $eq: ['$subscriptionStatus', 'active'] }, 1, 0] } },
        trial:         { $sum: { $cond: [{ $eq: ['$subscriptionStatus', 'trial'] }, 1, 0] } },
        free:          { $sum: { $cond: [{ $eq: ['$subscriptionStatus', 'free'] }, 1, 0] } },
      },
    },
  ]);
  return totals || { total: 0, verified: 0, active: 0, trial: 0, free: 0 };
};

// ─────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────

const User = mongoose.model('User', userSchema);
module.exports = User;
