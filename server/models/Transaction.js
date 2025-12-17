const mongoose = require('mongoose');
const crypto = require('crypto');

const transactionSchema = new mongoose.Schema({
    transactionId: {
        type: String,
        unique: true,
        required: true
    },
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    amount: {
        type: Number,
        required: [true, 'Transaction amount is required'],
        min: [0.01, 'Transaction amount must be positive']
    },
    currency: {
        type: String,
        required: true,
        enum: ['ZAR', 'USD', 'EUR', 'GBP', 'BTC', 'ETH'],
        default: 'ZAR'
    },
    paymentMethod: {
        type: String,
        enum: ['card', 'eft', 'crypto', 'wallet'],
        required: true
    },
    status: {
        type: String,
        enum: ['pending', 'completed', 'failed', 'refunded', 'disputed'],
        default: 'pending'
    },
    fees: {
        processing: Number,
        gateway: Number,
        currencyConversion: Number,
        total: Number
    },
    riskScore: {
        type: Number,
        default: 0
    },
    complianceFlags: {
        flaggedForReview: {
            type: Boolean,
            default: false
        }
    },
    auditTrail: [
        {
            status: String,
            timestamp: {
                type: Date,
                default: Date.now
            },
            reason: String,
            user: {
                type: mongoose.Schema.Types.ObjectId,
                ref: 'User'
            },
            metadata: Object
        }
    ],
    refund: {
        refundedTransactionId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Transaction'
        },
        amount: Number,
        reason: String,
        processedBy: {
            type: mongoose.Schema.Types.ObjectId,
            ref: 'User'
        }
    },
    chargeback: {
        reasonCode: String,
        evidenceDueDate: Date,
        status: {
            type: String,
            enum: ['won', 'lost', 'pending']
        },
        timeline: [
            {
                status: String,
                date: Date
            }
        ]
    }
}, {
    timestamps: true
});

// Generate transaction ID before saving
transactionSchema.pre('save', function(next) {
    if (!this.isNew) return next();
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const random = crypto.randomBytes(3).toString('hex').toUpperCase();
    this.transactionId = `TXN_${date}_${random}`;
    next();
});

// Add initial status to audit trail
transactionSchema.pre('save', function(next) {
    if (this.isNew) {
        this.auditTrail.push({
            status: 'pending',
            reason: 'Transaction created'
        });
    }
    next();
});

// Calculate fees method
transactionSchema.methods.calculateFees = function() {
    this.fees = {
        processing: 0,
        gateway: 0,
        currencyConversion: 0,
        total: 0
    };
    this.fees.processing = Math.round((this.amount * 0.029 + 2.50) * 100) / 100;
    this.fees.gateway = 1.00;
    if (this.currency !== 'ZAR') {
        this.fees.currencyConversion = Math.round((this.amount * 0.005) * 100) / 100;
    }
    this.fees.total = this.fees.processing + this.fees.gateway + this.fees.currencyConversion;
};

// Calculate risk score method
transactionSchema.methods.calculateRiskScore = function(country = 'ZA', sanctionsCheck = { passed: true }, amlCheck = { passed: true }) {
    let score = 0;
    if (this.amount > 10000) score += 20;
    if (country !== 'ZA') score += 15;
    if (this.paymentMethod === 'crypto') score += 25;
    if (!sanctionsCheck.passed) score += 50;
    if (!amlCheck.passed) score += 40;
    this.riskScore = Math.min(score, 100);
    if (this.riskScore >= 70) {
        this.complianceFlags.flaggedForReview = true;
    }
};

// Statistics method
transactionSchema.statics.getStatistics = async function(startDate, endDate) {
    const match = {
        createdAt: {
            $gte: new Date(startDate),
            $lte: new Date(endDate)
        }
    };

    const stats = await this.aggregate([
        { $match: match },
        {
            $group: {
                _id: null,
                totalAmount: { $sum: '$amount' },
                totalTransactions: { $sum: 1 },
                totalFees: { $sum: '$fees.total' },
                completedTransactions: { $sum: { $cond: [{ $eq: ['$status', 'completed'] }, 1, 0] } },
                failedTransactions: { $sum: { $cond: [{ $eq: ['$status', 'failed'] }, 1, 0] } },
                refundedTransactions: { $sum: { $cond: [{ $eq: ['$status', 'refunded'] }, 1, 0] } },
                highRiskTransactions: { $sum: { $cond: [{ $gte: ['$riskScore', 70] }, 1, 0] } }
            }
        }
    ]);

    if (stats.length > 0) {
        const { totalAmount, totalTransactions, totalFees, completedTransactions, failedTransactions, refundedTransactions, highRiskTransactions } = stats[0];
        return {
            totalAmount: parseFloat(totalAmount.toFixed(2)),
            totalTransactions,
            totalFees: parseFloat(totalFees.toFixed(2)),
            avgTransactionValue: parseFloat((totalAmount / totalTransactions).toFixed(2)),
            completedTransactions,
            failedTransactions,
            refundedTransactions,
            highRiskTransactions,
            successRate: parseFloat(((completedTransactions / totalTransactions) * 100).toFixed(1))
        };
    }
    return {};
};

const Transaction = mongoose.model('Transaction', transactionSchema);
module.exports = Transaction;
