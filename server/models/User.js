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
    },
    phone: {
        type: String,
        trim: true,
        validate: {
            validator: function(v) {
                if (!v) return true; // Optional field
                return /^[+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$/.test(v);
            },
            message: 'Please provide a valid phone number'
        }
    },
    
    role: {
        type: String,
        enum: ['user', 'admin', 'enterprise'],
        default: 'user'
    },
    
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
    
    loginAttempts: {
        type: Number,
        default: 0
    },
    lockUntil: Date,
    
    lastLogin: Date,
    
    active: {
        type: Boolean,
        default: true,
        select: false
    }
}, {
    timestamps: true,
    toJSON: { virtuals: true },
    toObject: { virtuals: true }
});

// Virtual for full name
userSchema.virtual('fullName').get(function() {
    return `${this.firstName} ${this.lastName}`;
});

// Virtual for account lock status
userSchema.virtual('isLocked').get(function() {
    return !!(this.lockUntil && this.lockUntil > Date.now());
});

// Index for faster queries
userSchema.index({ email: 1 });
userSchema.index({ createdAt: -1 });

// Hash password before saving
userSchema.pre('save', async function(next) {
    // Only run if password was modified
    if (!this.isModified('password')) return next();
    
    // Hash password with cost of 12
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
    next();
});

// Compare password method
userSchema.methods.comparePassword = async function(candidatePassword) {
    return await bcrypt.compare(candidatePassword, this.password);
};

// Check if password was changed after JWT was issued
userSchema.methods.changedPasswordAfter = function(JWTTimestamp) {
    if (this.passwordChangedAt) {
        const changedTimestamp = parseInt(
            this.passwordChangedAt.getTime() / 1000,
            10
        );
        return JWTTimestamp < changedTimestamp;
    }
    return false;
};

// Generate password reset token
userSchema.methods.generatePasswordResetToken = function() {
    const resetToken = crypto.randomBytes(32).toString('hex');
    
    this.passwordResetToken = crypto
        .createHash('sha256')
        .update(resetToken)
        .digest('hex');
    
    this.passwordResetExpires = Date.now() + 10 * 60 * 1000; // 10 minutes
    
    return resetToken;
};

// Increment login attempts
userSchema.methods.incrementLoginAttempts = async function() {
    // If lock has expired, reset attempts
    if (this.lockUntil && this.lockUntil < Date.now()) {
        return this.updateOne({
            $set: { loginAttempts: 1 },
            $unset: { lockUntil: 1 }
        });
    }
    
    const updates = { $inc: { loginAttempts: 1 } };
    
    // Lock account after 5 failed attempts for 2 hours
    const maxAttempts = 5;
    const lockTime = 2 * 60 * 60 * 1000; // 2 hours
    
    if (this.loginAttempts + 1 >= maxAttempts && !this.isLocked) {
        updates.$set = { lockUntil: Date.now() + lockTime };
    }
    
    return this.updateOne(updates);
};

// Reset login attempts
userSchema.methods.resetLoginAttempts = async function() {
    return this.updateOne({
        $set: { loginAttempts: 0 },
        $unset: { lockUntil: 1 }
    });
};

// Get user profile (without sensitive data)
userSchema.methods.getProfile = function() {
    return {
        id: this._id,
        email: this.email,
        firstName: this.firstName,
        lastName: this.lastName,
        fullName: this.fullName,
        company: this.company,
        phone: this.phone,
        role: this.role,
        subscription: this.subscription,
        isVerified: this.isVerified,
        lastLogin: this.lastLogin,
        createdAt: this.createdAt
    };
};

const User = mongoose.model('User', userSchema);

module.exports = User;