/**
 * TRANSACTION MODEL - PRODUCTION READY
 * 
 * Features:
 * - Automatic transaction ID generation
 * - Multi-currency support (ZAR, USD, EUR, GBP, BTC, ETH)
 * - Fee calculation (Stripe-compliant: 2.9% + R2.50)
 * - Risk scoring algorithm (0-100)
 * - Status history audit trail
 * - Settlement tracking
 * - Refund & chargeback management
 * - KYC/AML compliance tracking
 * - Geolocation tracking
 */

const mongoose = require('mongoose');
const crypto = require('crypto');

const transactionSchema = new mongoose.Schema({
    // Transaction Identification
    transactionId: {
        type: String,
        required: true,
        unique: true,
        default: function() {
            // Format: TXN_YYYYMMDD_RANDOM (e.g., TXN_20250117_A3F9K2)
            const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
            const random = crypto.randomBytes(4).toString('hex').toUpperCase();
            return `TXN_${date}_${random}`;
        }
    },
    
    // Customer Information
    customerId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: [true, 'Customer ID is required'],
        index: true
    },
    customerEmail: {
        type: String,
        required: [true, 'Customer email is required'],
        lowercase: true,
        trim: true
    },
    
    // Transaction Details
    amount: {
        type: Number,
        required: [true, 'Transaction amount is required'],
        min: [0, 'Amount cannot be negative'],
        get: v => Math.round(v * 100) / 100 // Round to 2 decimals
    },
    currency: {
        type: String,
        required: true,
        enum: ['ZAR', 'USD', 'EUR', 'GBP', 'BTC', 'ETH'],
        default: 'ZAR',
        uppercase: true
    },
    
    // Transaction Type
    type: {
        type: String,
        required: true,
        enum: ['payment', 'refund', 'payout', 'transfer', 'fee', 'subscription'],
        default: 'payment'
    },
    description: {
        type: String,
        maxlength: [500, 'Description cannot exceed 500 characters'],
        trim: true
    },
    
    // Payment Method
    paymentMethod: {
        type: String,
        required: true,
        enum: ['card', 'bank_transfer', 'mobile_pay', 'crypto', 'wallet', 'eft'],
        default: 'card'
    },
    paymentProvider: {
        type: String,
        enum: ['stripe', 'paystack', 'payfast', 'crypto_wallet', 'manual'],
        default: 'stripe'
    },
    
    // Payment Provider Data
    providerData: {
        stripe: {
            paymentIntentId: String,
            chargeId: String,
            customerId: String,
            paymentMethodId: String
        },
        paystack: {
            reference: String,
            authorizationCode: String,
            accessCode: String
        },
        payfast: {
            paymentId: String,
            merchantId: String,
            signature: String
        },
        crypto: {
            walletAddress: String,
            transactionHash: String,
            network: String,
            confirmations: Number
        }
    },
    
    // Transaction Status
    status: {
        type: String,
        required: true,
        enum: ['pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'disputed'],
        default: 'pending',
        index: true
    },
    
    // Status History (Audit Trail)
    statusHistory: [{
        status: {
            type: String,
            required: true
        },
        timestamp: {
            type: Date,
            default: Date.now
        },
        reason: String,
        updatedBy: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User'
        },
        metadata: mongoose.Schema.Types.Mixed
    }],
    
    // Financial Details
    fees: {
        processing: {
            type: Number,
            default: 0,
            get: v => Math.round(v * 100) / 100
        },
        gateway: {
            type: Number,
            default: 0,
            get: v => Math.round(v * 100) / 100
        },
        currencyConversion: {
            type: Number,
            default: 0,
            get: v => Math.round(v * 100) / 100
        },
        total: {
            type: Number,
            default: 0,
            get: v => Math.round(v * 100) / 100
        }
    },
    
    // Exchange Rate (for multi-currency)
    exchangeRate: {
        rate: Number,
        fromCurrency: String,
        toCurrency: String,
        timestamp: Date
    },
    
    // Settlement Information
    settlement: {
        batchId: String,
        settledAt: Date,
        amount: Number,
        currency: String,
        bankAccount: String
    },
    
    // Risk Assessment
    riskScore: {
        type: Number,
        min: 0,
        max: 100,
        default: 0
    },
    riskFactors: [{
        type: String,
        severity: {
            type: String,
            enum: ['low', 'medium', 'high', 'critical'],
            default: 'low'
        },
        description: String,
        detectedAt: {
            type: Date,
            default: Date.now
        }
    }],
    
    // Compliance & KYC/AML
    complianceFlags: {
        sanctionsScreening: {
            checked: Boolean,
            passed: Boolean,
            checkedAt: Date
        },
        amlCheck: {
            checked: Boolean,
            passed: Boolean,
            checkedAt: Date
        },
        kycVerified: {
            type: Boolean,
            default: false
        },
        flaggedForReview: {
            type: Boolean,
            default: false
        },
        reviewNotes: String
    },
    
    // Customer Context (for fraud detection)
    customerInfo: {
        ipAddress: String,
        userAgent: String,
        deviceFingerprint: String,
        location: {
            country: String,
            city: String,
            region: String,
            coordinates: {
                lat: Number,
                lng: Number
            },
            timezone: String
        }
    },
    
    // Refund Information
    refundData: {
        originalTransactionId: {
            type: String,
            index: true
        },
        refundAmount: Number,
        refundReason: String,
        processedAt: Date,
        refundedBy: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User'
        }
    },
    
    // Chargeback Information
    chargebackData: {
        reasonCode: String,
        reason: String,
        amount: Number,
        disputedAt: Date,
        evidenceDueDate: Date,
        status: {
            type: String,
            enum: ['pending', 'won', 'lost', 'withdrawn'],
            default: 'pending'
        },
        evidenceSubmitted: Boolean,
        resolution: String
    },
    
    // Related Entities
    subscriptionId: {
        type: String,
        index: true
    },
    invoiceId: String,
    orderId: String,
    
    // Metadata (flexible storage)
    metadata: {
        type: mongoose.Schema.Types.Mixed,
        default: {}
    },
    
    // Audit Fields
    createdBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User'
    },
    modifiedBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User'
    },
    
    // Soft Delete
    isDeleted: {
        type: Boolean,
        default: false
    },
    deletedAt: Date,
    deletedBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User'
    }
    
}, {
    timestamps: true,
    toJSON: { virtuals: true, getters: true },
    toObject: { virtuals: true, getters: true }
});

// ============================================
// VIRTUALS
// ============================================

// Net amount (after fees)
transactionSchema.virtual('netAmount').get(function() {
    return Math.round((this.amount - this.fees.total) * 100) / 100;
});

// Transaction age in milliseconds
transactionSchema.virtual('age').get(function() {
    return Date.now() - this.createdAt.getTime();
});

// Is high risk
transactionSchema.virtual('isHighRisk').get(function() {
    return this.riskScore >= 70;
});

// Needs review
transactionSchema.virtual('needsReview').get(function() {
    return this.complianceFlags.flaggedForReview || 
           this.riskScore >= 70 ||
           this.riskFactors.some(f => f.severity === 'critical');
});

// ============================================
// MIDDLEWARE
// ============================================

// Auto-calculate fees before saving
transactionSchema.pre('save', function(next) {
    if (this.isModified('amount') || this.isModified('currency')) {
        this.calculateFees();
    }
    next();
});

// Add initial status to history
transactionSchema.pre('save', function(next) {
    if (this.isNew) {
        this.statusHistory.push({
            status: this.status,
            timestamp: new Date(),
            reason: 'Transaction created'
        });
    }
    next();
});

// ============================================
// INSTANCE METHODS
// ============================================

// Update transaction status with audit trail
transactionSchema.methods.updateStatus = async function(newStatus, reason, updatedBy, metadata = {}) {
    const oldStatus = this.status;
    this.status = newStatus;
    
    // Add to status history
    this.statusHistory.push({
        status: newStatus,
        timestamp: new Date(),
        reason: reason || `Status changed from ${oldStatus} to ${newStatus}`,
        updatedBy,
        metadata
    });
    
    // Special handling for different statuses
    if (newStatus === 'completed') {
        this.metadata.completedAt = new Date();
    }
    
    if (newStatus === 'failed') {
        this.metadata.failedAt = new Date();
        this.metadata.failureReason = reason;
    }
    
    return this.save();
};

// Calculate transaction fees (Stripe-compliant for ZAR)
transactionSchema.methods.calculateFees = function() {
    // Base fee structure (adjust per your payment processor)
    const baseFee = 2.50; // ZAR flat fee
    const percentageFee = 0.029; // 2.9%
    const gatewayFee = 1.00; // Gateway processing fee
    
    // Calculate processing fee: 2.9% + R2.50
    this.fees.processing = Math.round((this.amount * percentageFee + baseFee) * 100) / 100;
    
    // Gateway fee
    this.fees.gateway = gatewayFee;
    
    // Currency conversion fee (if not ZAR)
    if (this.currency !== 'ZAR') {
        this.fees.currencyConversion = Math.round((this.amount * 0.005) * 100) / 100; // 0.5%
    } else {
        this.fees.currencyConversion = 0;
    }
    
    // Total fees
    this.fees.total = Math.round(
        (this.fees.processing + this.fees.gateway + this.fees.currencyConversion) * 100
    ) / 100;
    
    return this.fees;
};

// Calculate risk score based on various factors
transactionSchema.methods.calculateRiskScore = function() {
    let score = 0;
    
    // High amount transactions (>R10,000)
    if (this.amount > 10000) {
        score += 20;
        this.riskFactors.push({
            type: 'high_amount',
            severity: 'medium',
            description: `Transaction amount (${this.currency} ${this.amount}) exceeds threshold`
        });
    }
    
    // International transactions
    if (this.customerInfo?.location?.country && this.customerInfo.location.country !== 'ZA') {
        score += 15;
        this.riskFactors.push({
            type: 'international',
            severity: 'low',
            description: `International transaction from ${this.customerInfo.location.country}`
        });
    }
    
    // Cryptocurrency transactions
    if (this.paymentMethod === 'crypto') {
        score += 25;
        this.riskFactors.push({
            type: 'crypto_payment',
            severity: 'medium',
            description: 'Cryptocurrency payment requires additional verification'
        });
    }
    
    // Failed compliance checks
    if (this.complianceFlags.sanctionsScreening?.checked && 
        !this.complianceFlags.sanctionsScreening?.passed) {
        score += 50;
        this.riskFactors.push({
            type: 'sanctions_hit',
            severity: 'critical',
            description: 'Failed sanctions screening'
        });
    }
    
    if (this.complianceFlags.amlCheck?.checked && 
        !this.complianceFlags.amlCheck?.passed) {
        score += 40;
        this.riskFactors.push({
            type: 'aml_concern',
            severity: 'high',
            description: 'AML check raised concerns'
        });
    }
    
    // Cap score at 100
    this.riskScore = Math.min(score, 100);
    
    // Flag for review if high risk
    if (this.riskScore >= 70) {
        this.complianceFlags.flaggedForReview = true;
    }
    
    return this.riskScore;
};

// Process refund
transactionSchema.methods.processRefund = async function(refundAmount, reason, refundedBy) {
    this.refundData = {
        originalTransactionId: this.transactionId,
        refundAmount: refundAmount || this.amount,
        refundReason: reason,
        processedAt: new Date(),
        refundedBy
    };
    
    await this.updateStatus('refunded', `Refund processed: ${reason}`, refundedBy);
    return this;
};

// ============================================
// STATIC METHODS
// ============================================

// Find transactions by customer
transactionSchema.statics.findByCustomer = function(customerId, options = {}) {
    const query = { customerId, isDeleted: false };
    
    if (options.status) {
        query.status = options.status;
    }
    
    if (options.dateFrom || options.dateTo) {
        query.createdAt = {};
        if (options.dateFrom) {
            query.createdAt.$gte = new Date(options.dateFrom);
        }
        if (options.dateTo) {
            query.createdAt.$lte = new Date(options.dateTo);
        }
    }
    
    if (options.minAmount) {
        query.amount = { $gte: options.minAmount };
    }
    
    return this.find(query)
        .sort({ createdAt: -1 })
        .limit(options.limit || 50)
        .skip(options.offset || 0)
        .populate('customerId', 'firstName lastName email');
};

// Get transaction statistics
transactionSchema.statics.getStatistics = async function(dateFrom, dateTo) {
    const matchStage = {
        $match: {
            createdAt: {
                $gte: new Date(dateFrom),
                $lte: new Date(dateTo)
            },
            isDeleted: false
        }
    };
    
    const stats = await this.aggregate([
        matchStage,
        {
            $group: {
                _id: null,
                totalAmount: { $sum: '$amount' },
                totalTransactions: { $sum: 1 },
                totalFees: { $sum: '$fees.total' },
                avgTransactionValue: { $avg: '$amount' },
                completedTransactions: {
                    $sum: { $cond: [{ $eq: ['$status', 'completed'] }, 1, 0] }
                },
                failedTransactions: {
                    $sum: { $cond: [{ $eq: ['$status', 'failed'] }, 1, 0] }
                },
                refundedTransactions: {
                    $sum: { $cond: [{ $eq: ['$status', 'refunded'] }, 1, 0] }
                },
                highRiskTransactions: {
                    $sum: { $cond: [{ $gte: ['$riskScore', 70] }, 1, 0] }
                }
            }
        },
        {
            $project: {
                _id: 0,
                totalAmount: { $round: ['$totalAmount', 2] },
                totalTransactions: 1,
                totalFees: { $round: ['$totalFees', 2] },
                avgTransactionValue: { $round: ['$avgTransactionValue', 2] },
                completedTransactions: 1,
                failedTransactions: 1,
                refundedTransactions: 1,
                highRiskTransactions: 1,
                successRate: {
                    $multiply: [
                        { $divide: ['$completedTransactions', '$totalTransactions'] },
                        100
                    ]
                }
            }
        }
    ]);
    
    return stats[0] || {
        totalAmount: 0,
        totalTransactions: 0,
        totalFees: 0,
        avgTransactionValue: 0,
        completedTransactions: 0,
        failedTransactions: 0,
        refundedTransactions: 0,
        highRiskTransactions: 0,
        successRate: 0
    };
};

// Find high-risk transactions needing review
transactionSchema.statics.findHighRisk = function() {
    return this.find({
        $or: [
            { riskScore: { $gte: 70 } },
            { 'complianceFlags.flaggedForReview': true },
            { 'riskFactors.severity': 'critical' }
        ],
        isDeleted: false
    }).sort({ riskScore: -1, createdAt: -1 });
};

// ============================================
// INDEXES (Performance Optimization)
// ============================================

transactionSchema.index({ customerId: 1, createdAt: -1 });
transactionSchema.index({ transactionId: 1 });
transactionSchema.index({ status: 1, createdAt: -1 });
transactionSchema.index({ paymentMethod: 1, status: 1 });
transactionSchema.index({ 'settlement.batchId': 1 });
transactionSchema.index({ riskScore: -1 });
transactionSchema.index({ subscriptionId: 1 });
transactionSchema.index({ createdAt: -1 });
transactionSchema.index({ isDeleted: 1, status: 1 });
transactionSchema.index({ customerEmail: 1 });
transactionSchema.index({ 'refundData.originalTransactionId': 1 });

module.exports = mongoose.model('Transaction', transactionSchema);