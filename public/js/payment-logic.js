/**
 * PAYMENT INFRASTRUCTURE - PAYFAST INTEGRATION
 * South Africa's premier payment gateway - ZAR native
 * 🇿🇦 Built for Africa
 */

// PayFast Configuration
const PAYFAST_CONFIG = {
    apiUrl: window.location.hostname === 'localhost' 
        ? 'http://localhost:4242' 
        : '',
    sandbox: true // Will be updated from server
};

// Transaction log system
const transactionLog = {
    entries: [],
    maxEntries: 50,
    
    add(type, amount, currency, status, details = {}) {
        const timestamp = new Date().toLocaleTimeString();
        const entry = {
            timestamp,
            type,
            amount: parseFloat(amount).toFixed(2),
            currency,
            status,
            ...details
        };
        
        this.entries.unshift(entry);
        if (this.entries.length > this.maxEntries) {
            this.entries.pop();
        }
        
        this.render();
    },
    
    render() {
        const logElement = document.querySelector('.transaction-log');
        if (!logElement) return;
        
        const html = this.entries.map(entry => {
            const statusClass = `status-${entry.status.toLowerCase()}`;
            return `<div class="${statusClass}">[${entry.timestamp}] ${entry.currency} ${entry.amount} → ${entry.type} - ${entry.status.toUpperCase()}</div>`;
        }).join('');
        
        logElement.innerHTML = html || '<div class="text-gray-500">No transactions yet</div>';
    }
};

// Initialize PayFast
async function initializePayments() {
    try {
        const response = await fetch(`${PAYFAST_CONFIG.apiUrl}/config`);
        if (!response.ok) throw new Error('Failed to load payment configuration');
        
        const config = await response.json();
        PAYFAST_CONFIG.merchantId = config.merchantId;
        PAYFAST_CONFIG.merchantKey = config.merchantKey;
        PAYFAST_CONFIG.sandbox = config.sandbox;
        PAYFAST_CONFIG.prices = config.prices;
        
        console.log('✅ PayFast initialized', config.sandbox ? '(SANDBOX)' : '(PRODUCTION)');
    } catch (error) {
        console.error('Payment initialization error:', error);
        showNotification('Payment system unavailable. Please try again later.', 'error');
    }
}

// Initiate PayFast payment
async function initiatePayFastPayment(plan, email, name) {
    try {
        const submitButton = document.querySelector('button[type="submit"]') || 
                            document.querySelector('.btn-primary');
        const originalText = submitButton?.textContent;
        if (submitButton) {
            submitButton.textContent = 'Processing...';
            submitButton.disabled = true;
        }
        
        // Create payment on server
        const response = await fetch(`${PAYFAST_CONFIG.apiUrl}/create-payment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan, email, name })
        });
        
        if (!response.ok) throw new Error('Failed to create payment');
        
        const { paymentData, payfastUrl, paymentId } = await response.json();
        
        // Log transaction
        transactionLog.add(
            'PayFast',
            paymentData.amount,
            'ZAR',
            'PENDING',
            { paymentId }
        );
        
        // Create and submit form to PayFast
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = payfastUrl;
        form.acceptCharset = 'UTF-8';
        
        // Add all payment data as hidden inputs
        Object.entries(paymentData).forEach(([key, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = value;
            form.appendChild(input);
        });
        
        document.body.appendChild(form);
        form.submit();
        
    } catch (error) {
        console.error('PayFast payment error:', error);
        showNotification(`Payment failed: ${error.message}`, 'error');
        
        const submitButton = document.querySelector('button[type="submit"]') || 
                            document.querySelector('.btn-primary');
        if (submitButton) {
            submitButton.textContent = 'Pay Now';
            submitButton.disabled = false;
        }
    }
}

// Plan selection and payment
async function selectPlan(plan) {
    const plans = {
        starter: {
            name: 'Vaal Starter',
            price: 999, // R999
            priceDisplay: 'R999/month',
            features: [
                '✅ Financial Sentinel engine',
                '✅ Guardian Engine alerts',
                '✅ Email support',
                '✅ SARS compliance monitoring',
                '✅ 7-day free trial'
            ]
        },
        empire: {
            name: 'Vaal Empire',
            price: 2999, // R2,999
            priceDisplay: 'R2,999/month',
            features: [
                '✅ All Starter features',
                '✅ Talent Accelerator engine',
                '✅ Priority support',
                '✅ Custom integrations',
                '✅ Advanced analytics',
                '✅ 7-day free trial'
            ]
        }
    };
    
    const selectedPlan = plans[plan];
    if (!selectedPlan) return;
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center';
    modal.id = 'plan-modal';
    modal.innerHTML = `
        <div class="bg-gray-900 rounded-lg p-8 max-w-md mx-4 border border-gray-700">
            <div class="text-center mb-6">
                <h3 class="text-2xl font-bold text-white mb-2">${selectedPlan.name}</h3>
                <div class="text-3xl font-bold text-green-400">${selectedPlan.priceDisplay}</div>
                <div class="text-sm text-gray-400 mt-1">🇿🇦 ZAR - South African Rand</div>
            </div>
            
            <ul class="space-y-2 mb-6">
                ${selectedPlan.features.map(feature => `
                    <li class="text-gray-300">${feature}</li>
                `).join('')}
            </ul>
            
            <!-- Payment Form -->
            <form id="payfast-form" class="space-y-4">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">Full Name</label>
                    <input type="text" name="name" required 
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
                        placeholder="Your full name">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">Email</label>
                    <input type="email" name="email" required 
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
                        placeholder="your@email.com">
                </div>
                <div class="flex items-start space-x-2">
                    <input type="checkbox" id="consent" required class="mt-1">
                    <label for="consent" class="text-sm text-gray-400">
                        I agree to the <a href="/legal-compliance.html" class="text-blue-400 hover:underline">Terms & Conditions</a>
                    </label>
                </div>
                <div class="flex gap-4">
                    <button type="submit" class="btn-primary px-6 py-3 rounded-lg text-white font-semibold flex-1">
                        Pay with PayFast
                    </button>
                    <button type="button" onclick="document.getElementById('plan-modal').remove()" 
                        class="border border-gray-600 px-6 py-3 rounded-lg text-gray-300 hover:bg-gray-800">
                        Cancel
                    </button>
                </div>
            </form>
            
            <div class="mt-4 text-center">
                <img src="https://www.payfast.co.za/images/payfast-logo.png" alt="PayFast" class="h-8 mx-auto opacity-70">
                <p class="text-xs text-gray-500 mt-2">Secure payment powered by PayFast</p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Handle form submission
    const form = document.getElementById('payfast-form');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const name = form.querySelector('input[name="name"]').value;
        const email = form.querySelector('input[name="email"]').value;
        const consent = form.querySelector('#consent').checked;
        
        if (!consent) {
            showNotification('Please accept the Terms & Conditions', 'error');
            return;
        }
        
        await initiatePayFastPayment(plan, email, name);
    });
    
    // Animate
    if (typeof anime !== 'undefined') {
        anime({
            targets: modal.querySelector('div'),
            scale: [0.8, 1],
            opacity: [0, 1],
            duration: 300,
            easing: 'easeOutCubic'
        });
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'error' ? 'bg-red-600' : 'bg-green-600';
    
    notification.className = `fixed top-24 right-6 ${bgColor} text-white px-6 py-4 rounded-lg shadow-lg z-50 max-w-md`;
    notification.innerHTML = `
        <div class="flex items-center space-x-3">
            <span class="text-2xl">${type === 'error' ? '❌' : '✅'}</span>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    if (typeof anime !== 'undefined') {
        anime({
            targets: notification,
            translateX: [400, 0],
            opacity: [0, 1],
            duration: 300,
            easing: 'easeOutCubic'
        });
    }
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (typeof anime !== 'undefined') {
            anime({
                targets: notification,
                translateX: [0, 400],
                opacity: [1, 0],
                duration: 300,
                easing: 'easeInCubic',
                complete: () => notification.remove()
            });
        } else {
            notification.remove();
        }
    }, 5000);
}

// Check for payment return
function checkPaymentReturn() {
    const urlParams = new URLSearchParams(window.location.search);
    const paymentId = urlParams.get('payment_id');
    
    if (paymentId && window.location.pathname.includes('success')) {
        // Show success message
        transactionLog.add('PayFast', '0.00', 'ZAR', 'SUCCESS', { paymentId });
    }
}

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    initializePayments();
    checkPaymentReturn();
    
    // Initialize transaction log with demo data
    setTimeout(() => {
        transactionLog.add('PayFast', '999.00', 'ZAR', 'SUCCESS');
        transactionLog.add('EFT', '2999.00', 'ZAR', 'SUCCESS');
        transactionLog.add('Card', '500.00', 'ZAR', 'PENDING');
    }, 1000);
});

// Export for global access
window.selectPlan = selectPlan;
window.initiatePayFastPayment = initiatePayFastPayment;
