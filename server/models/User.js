 feat/auth-error-handling-5447018483623698560
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const crypto = require('crypto');

const userSchema = new mongoose.Schema({
    email: {
        type: String,
        required: [true, 'Please provide your email'],
        unique: true,
        lowercase: true,
        trim: true,
        validate: {
            validator: function(v) {
                return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
            },
            message: 'Please provide a valid email'
        }
    },
    password: {
        type: String,
        required: [true, 'Please provide a password'],
        minlength: [8, 'Password must be at least 8 characters'],
        select: false
    },
    passwordChangedAt: Date,
    passwordResetToken: String,
    passwordResetExpires: Date,

    firstName: {
        type: String,
        required: [true, 'Please provide your first name'],
        trim: true
    },
    lastName: {
        type: String,
        required: [true, 'Please provide your last name'],
        trim: true
    },
    company: {
        type: String,
        trim: true

/**
 * USER MODEL - PRODUCTION READY
 * 
 * Features:
 * - Bcrypt password hashing (12 rounds)
 * - Account locking after 5 failed logins (2 hour lock)
 * - Email verification system
 * - Password reset with crypto tokens (10 min expiry)
 * - POPIA compliance tracking
 * - KYC document management
 * - Subscription management
 * - Role-based access control
 * - Password change tracking
 */

const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const crypto = require('crypto');
const validator = require('validator');

const userSchema = new mongoose.Schema({
    // Authentication
    email: {
        type: String,
        required: [true, 'Email is required'],
        unique: true,
        lowercase: true,
        trim: true,
        validate: [validator.isEmail, 'Please provide a valid email']
    },
    password: {
        type: String,
        required: [true, 'Password is required'],
        minlength: [8, 'Password must be at least 8 characters'],
        select: false // Don't return password by default
    },
    passwordChangedAt: Date,
    
    // Personal Information
    firstName: {
        type: String,
        required: [true, 'First name is required'],
        trim: true,
        maxlength: [50, 'First name cannot exceed 50 characters']
    },
    lastName: {
        type: String,
        required: [true, 'Last name is required'],
        trim: true,
        maxlength: [50, 'Last name cannot exceed 50 characters']
    },
    company: {
        type: String,
        trim: true,
        maxlength: [100, 'Company name cannot exceed 100 characters']
 main
    },
    phone: {
        type: String,
        trim: true,
        validate: {
            validator: function(v) {
 feat/auth-error-handling-5447018483623698560
                if (!v) return true; // Optional field
                return /^[+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$/.test(v);

                return !v || validator.isMobilePhone(v, 'any');
 main
            },
            message: 'Please provide a valid phone number'
        }
    },
 feat/auth-error-handling-5447018483623698560


    
    // Role & Permissions
 main
    role: {
        type: String,
        enum: ['user', 'admin', 'enterprise'],
        default: 'user'
    },
 feat/auth-error-handling-5447018483623698560

    subscription: {
        plan: {
            type: String,
            enum: ['trial', 'starter', 'professional', 'enterprise'],
            default: 'trial'
        },
        status: {
            type: String,
            enum: ['active', 'inactive', 'cancelled', 'expired'],
            default: 'active'
        },
        startDate: {
            type: Date,
            default: Date.now
        },
        endDate: Date,
        stripeCustomerId: String,
        stripeSubscriptionId: String
    },

    isVerified: {
        type: Boolean,
        default: false
    },
    verificationToken: String,
    verificationTokenExpires: Date,

    loginAttempts: {
        type: Number,
        default: 0
    },
    lockUntil: Date,

    lastLogin: Date,

    compliance: {
        popia: {
            consent: Boolean,
            analytics: Boolean,
            thirdParty: Boolean,
            consentDate: Date
        },
        kyc: {
            status: {
                type: String,
                enum: ['pending', 'approved', 'rejected'],
                default: 'pending'
            },
            documentType: String,
            documentUrl: String,
            rejectionReason: String,
            reviewedBy: {
                type: mongoose.Schema.Types.ObjectId,
                ref: 'User'
            }
        }
    },

    active: {
        type: Boolean,
        default: true,
        select: false
    }

    
    // Email Verification
    isVerified: {
        type: Boolean,
        default: false
    },
    verificationToken: String,
    verificationTokenExpires: Date,
    
    // Password Reset
    passwordResetToken: String,
    passwordResetExpires: Date,
    
    // Account Security
    lastLogin: Date,
    loginAttempts: {
        type: Number,
        default: 0
    },
    lockUntil: Date,
    
    // Subscription Management
    subscription: {
        plan: {
            type: String,
            enum: ['free', 'starter', 'empire'],
            default: 'free'
        },
        status: {
            type: String,
            enum: ['active', 'cancelled', 'past_due', 'trialing'],
            default: 'active'
        },
        stripeCustomerId: String,
        stripeSubscriptionId: String,
        currentPeriodStart: Date,
        currentPeriodEnd: Date,
        cancelAtPeriodEnd: Boolean,
        trialEndsAt: Date
    },
    
    // POPIA Compliance (SA Data Protection)
    dataConsent: {
        marketing: {
            type: Boolean,
            default: false
        },
        analytics: {
            type: Boolean,
            default: true
        },
        thirdParty: {
            type: Boolean,
            default: false
        },
        consentDate: {
            type: Date,
            default: Date.now
        }
    },
    
    // KYC (Know Your Customer)
    kycStatus: {
        type: String,
        enum: ['pending', 'verified', 'rejected'],
        default: 'pending'
    },
    kycDocuments: [{
        type: {
            type: String,
            enum: ['id', 'proof_of_address', 'company_registration', 'tax_clearance'],
            required: true
        },
        url: {
            type: String,
            required: true
        },
        status: {
            type: String,
            enum: ['pending', 'approved', 'rejected'],
            default: 'pending'
        },
        rejectionReason: String,
        uploadedAt: {
            type: Date,
            default: Date.now
        },
        reviewedAt: Date,
        reviewedBy: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User'
        }
    }],
    
    // Preferences
    preferredCurrency: {
        type: String,
        enum: ['ZAR', 'USD', 'EUR', 'GBP'],
        default: 'ZAR'
    },
    notificationPreferences: {
        email: {
            type: Boolean,
            default: true
        },
        sms: {
            type: Boolean,
            default: false
        },
        push: {
            type: Boolean,
            default: true
        }
    },
    
    // Account Status
    isActive: {
        type: Boolean,
        default: true
    },
    deactivatedAt: Date,
    deactivationReason: String
    
 main
}, {
    timestamps: true,
    toJSON: { virtuals: true },
    toObject: { virtuals: true }
});

 feat/auth-error-handling-5447018483623698560
// Virtual for full name

// ============================================
// VIRTUALS
// ============================================

// Full name
 main
userSchema.virtual('fullName').get(function() {
    return `${this.firstName} ${this.lastName}`;
});

 feat/auth-error-handling-5447018483623698560
// Virtual for account lock status

// Is account locked
 main
userSchema.virtual('isLocked').get(function() {
    return !!(this.lockUntil && this.lockUntil > Date.now());
});

 feat/auth-error-handling-5447018483623698560
// Index for faster queries
userSchema.index({ email: 1 });
userSchema.index({ 'subscription.status': 1 });
userSchema.index({ createdAt: -1 });

// Hash password before saving
userSchema.pre('save', async function(next) {
    if (!this.isModified('password')) return next();
    this.password = await bcrypt.hash(this.password, 12);
    next();
});

// Update passwordChangedAt property
userSchema.pre('save', function(next) {
    if (!this.isModified('password') || this.isNew) return next();
    this.passwordChangedAt = Date.now() - 1000;
    next();
});

// Generate verification token
userSchema.pre('save', function(next) {
    if (!this.isNew || this.verificationToken) return next();
    this.verificationToken = crypto.randomBytes(32).toString('hex');
    this.verificationTokenExpires = Date.now() + 24 * 60 * 60 * 1000; // 24 hours
    next();
});

// Compare password method

// Subscription active
userSchema.virtual('hasActiveSubscription').get(function() {
    return this.subscription.status === 'active' && 
           this.subscription.currentPeriodEnd > Date.now();
});

// ============================================
// MIDDLEWARE (PRE-SAVE HOOKS)
// ============================================

// Hash password before saving
userSchema.pre('save', async function(next) {
    // Only hash if password was modified
    if (!this.isModified('password')) return next();
    
    try {
        // Generate salt with 12 rounds (recommended for production)
        const salt = await bcrypt.genSalt(12);
        
        // Hash password
        this.password = await bcrypt.hash(this.password, salt);
        
        // Update passwordChangedAt
        if (!this.isNew) {
            this.passwordChangedAt = Date.now() - 1000; // Subtract 1s to account for JWT timing
        }
        
        next();
    } catch (error) {
        next(error);
    }
});

// Generate verification token before saving new users
userSchema.pre('save', function(next) {
    if (this.isNew && !this.verificationToken && !this.isVerified) {
        this.verificationToken = crypto.randomBytes(32).toString('hex');
        this.verificationTokenExpires = Date.now() + 24 * 60 * 60 * 1000; // 24 hours
    }
    next();
});

// ============================================
// INSTANCE METHODS
// ============================================

// Compare password for login
 main
userSchema.methods.comparePassword = async function(candidatePassword) {
    return await bcrypt.compare(candidatePassword, this.password);
};

 feat/auth-error-handling-5447018483623698560
// Check if password was changed after JWT was issued
userSchema.methods.changedPasswordAfter = function(JWTTimestamp) {
    if (this.passwordChangedAt) {
        const changedTimestamp = parseInt(this.passwordChangedAt.getTime() / 1000, 10);
        return JWTTimestamp < changedTimestamp;
    }
    return false;

// Increment login attempts and lock account if needed
userSchema.methods.incrementLoginAttempts = async function() {
    // Reset attempts if lock has expired
    if (this.lockUntil && this.lockUntil < Date.now()) {
        return this.updateOne({
            $set: { loginAttempts: 1 },
            $unset: { lockUntil: 1 }
        });
    }
    
    const updates = { $inc: { loginAttempts: 1 } };
    
    // Lock account after 5 failed attempts
    const maxAttempts = 5;
    const lockTime = 2 * 60 * 60 * 1000; // 2 hours
    
    if (this.loginAttempts + 1 >= maxAttempts && !this.isLocked) {
        updates.$set = { lockUntil: Date.now() + lockTime };
    }
    
    return this.updateOne(updates);
};

// Reset login attempts after successful login
userSchema.methods.resetLoginAttempts = async function() {
    return this.updateOne({
        $set: { loginAttempts: 0 },
        $unset: { lockUntil: 1 }
    });
 main
};

// Generate password reset token
userSchema.methods.generatePasswordResetToken = function() {
 feat/auth-error-handling-5447018483623698560
    const resetToken = crypto.randomBytes(32).toString('hex');
    this.passwordResetToken = crypto.createHash('sha256').update(resetToken).digest('hex');
    this.passwordResetExpires = Date.now() + 10 * 60 * 1000; // 10 minutes
    return resetToken;
};

// Increment login attempts and lock account if necessary
userSchema.methods.incrementLoginAttempts = async function() {
    if (this.lockUntil && this.lockUntil < Date.now()) {
        await this.updateOne({ $set: { loginAttempts: 1 }, $unset: { lockUntil: 1 } });
        return;
    }
    const updates = { $inc: { loginAttempts: 1 } };
    if (this.loginAttempts + 1 >= 5 && !this.isLocked) {
        updates.$set = { lockUntil: Date.now() + 2 * 60 * 60 * 1000 }; // 2 hours
    }
    await this.updateOne(updates);
};

// Reset login attempts
userSchema.methods.resetLoginAttempts = async function() {
    await this.updateOne({ $set: { loginAttempts: 0 }, $unset: { lockUntil: 1 } });
};

// Get user profile (without sensitive data)
userSchema.methods.getProfile = function() {
    const { email, firstName, lastName, fullName, company, phone, role, subscription, isVerified, lastLogin, createdAt } = this;
    return { id: this._id, email, firstName, lastName, fullName, company, phone, role, subscription, isVerified, lastLogin, createdAt };
};

// Statistics method
userSchema.statics.getStatistics = async function() {
    const totalUsers = await this.countDocuments();
    const verifiedUsers = await this.countDocuments({ isVerified: true });
    const activeSubscriptions = await this.countDocuments({ 'subscription.status': 'active' });
    const verificationRate = totalUsers > 0 ? (verifiedUsers / totalUsers) * 100 : 0;
    return {
        totalUsers,
        verifiedUsers,
        activeSubscriptions,
        verificationRate: parseFloat(verificationRate.toFixed(1))
    };
};

const User = mongoose.model('User', userSchema);
module.exports = User;

    // Generate random token
    const resetToken = crypto.randomBytes(32).toString('hex');
    
    // Hash token and save to database
    this.passwordResetToken = crypto
        .createHash('sha256')
        .update(resetToken)
        .digest('hex');
    
    // Token expires in 10 minutes
    this.passwordResetExpires = Date.now() + 10 * 60 * 1000;
    
    // Return unhashed token (to send via email)
    return resetToken;
};

// Generate email verification token
userSchema.methods.generateVerificationToken = function() {
    this.verificationToken = crypto.randomBytes(32).toString('hex');
    this.verificationTokenExpires = Date.now() + 24 * 60 * 60 * 1000; // 24 hours
    return this.verificationToken;
};

// Check if user changed password after JWT was issued
userSchema.methods.changedPasswordAfter = function(JWTTimestamp) {
    if (this.passwordChangedAt) {
        const changedTimestamp = parseInt(this.passwordChangedAt.getTime() / 1000, 10);
        return JWTTimestamp < changedTimestamp;
    }
    return false;
};

// Get safe user profile (excluding sensitive data)
userSchema.methods.getProfile = function() {
    const user = this.toObject();
    
    // Remove sensitive fields
    delete user.password;
    delete user.verificationToken;
    delete user.verificationTokenExpires;
    delete user.passwordResetToken;
    delete user.passwordResetExpires;
    delete user.loginAttempts;
    delete user.lockUntil;
    delete user.passwordChangedAt;
    
    return user;
};

// Update subscription
userSchema.methods.updateSubscription = function(subscriptionData) {
    this.subscription = {
        ...this.subscription,
        ...subscriptionData
    };
    return this.save();
};

// Add KYC document
userSchema.methods.addKYCDocument = function(documentData) {
    this.kycDocuments.push(documentData);
    return this.save();
};

// ============================================
// STATIC METHODS
// ============================================

// Find user by email
userSchema.statics.findByEmail = function(email) {
    return this.findOne({ email: email.toLowerCase() });
};

// Find users by subscription plan
userSchema.statics.findBySubscriptionPlan = function(plan) {
    return this.find({ 'subscription.plan': plan });
};

// Find users with expiring subscriptions (next 7 days)
userSchema.statics.findExpiringSubscriptions = function() {
    const sevenDaysFromNow = new Date();
    sevenDaysFromNow.setDate(sevenDaysFromNow.getDate() + 7);
    
    return this.find({
        'subscription.status': 'active',
        'subscription.currentPeriodEnd': {
            $lte: sevenDaysFromNow,
            $gte: new Date()
        }
    });
};

// Get user statistics
userSchema.statics.getStatistics = async function() {
    const stats = await this.aggregate([
        {
            $group: {
                _id: null,
                totalUsers: { $sum: 1 },
                verifiedUsers: {
                    $sum: { $cond: ['$isVerified', 1, 0] }
                },
                activeSubscriptions: {
                    $sum: { $cond: [{ $eq: ['$subscription.status', 'active'] }, 1, 0] }
                }
            }
        },
        {
            $project: {
                _id: 0,
                totalUsers: 1,
                verifiedUsers: 1,
                activeSubscriptions: 1,
                verificationRate: {
                    $multiply: [
                        { $divide: ['$verifiedUsers', '$totalUsers'] },
                        100
                    ]
                }
            }
        }
    ]);
    
    return stats[0] || {
        totalUsers: 0,
        verifiedUsers: 0,
        activeSubscriptions: 0,
        verificationRate: 0
    };
};

// ============================================
// INDEXES (For Query Performance)
// ============================================

userSchema.index({ email: 1 });
userSchema.index({ role: 1 });
userSchema.index({ kycStatus: 1 });
userSchema.index({ 'subscription.plan': 1, 'subscription.status': 1 });
userSchema.index({ createdAt: -1 });
userSchema.index({ verificationToken: 1 });
userSchema.index({ passwordResetToken: 1 });

module.exports = mongoose.model('User', userSchema);
 main
