// Vaal AI Empire - Main JavaScript
// African Futurism meets Industrial Tech

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAnimations();
    initializeCounters();
    initializeCharts();
    initializeNeuralNetwork();
    initializeTypedText();
    startEngineSimulations();
    initializePaymentSystem();
});

// Typed text animation for hero section
function initializeTypedText() {
    const typed = new Typed('#typed-text', {
        strings: [
            'Africa...',
            'we built the future.',
            'we built the Empire.'
        ],
        typeSpeed: 80,
        backSpeed: 50,
        backDelay: 2000,
        startDelay: 1000,
        loop: false,
        showCursor: true,
        cursorChar: '|',
        onComplete: function() {
            // Add glow effect when complete
            document.getElementById('typed-text').classList.add('glow-text');
        }
    });
}

// Animate metric counters
function initializeCounters() {
    const counters = document.querySelectorAll('.metric-counter');
    
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    counters.forEach(counter => observer.observe(counter));
}

function animateCounter(element) {
    const target = parseInt(element.dataset.target);
    const duration = 2000;
    const increment = target / (duration / 16);
    let current = 0;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        
        if (target >= 100) {
            element.textContent = Math.floor(current) + (target >= 500 ? 'K' : '+');
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Initialize ECharts for engine visualizations
function initializeCharts() {
    // Tax Recovery Chart
    const taxChart = echarts.init(document.getElementById('taxChart'));
    const taxOption = {
        backgroundColor: 'transparent',
        grid: { top: 10, right: 10, bottom: 20, left: 30 },
        xAxis: {
            type: 'category',
            data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 },
            splitLine: { lineStyle: { color: '#333' } }
        },
        series: [{
            data: [12, 19, 25, 32, 41, 58],
            type: 'line',
            smooth: true,
            lineStyle: { color: '#00ff88', width: 2 },
            itemStyle: { color: '#00ff88' },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(0,255,136,0.3)' },
                        { offset: 1, color: 'rgba(0,255,136,0.1)' }
                    ]
                }
            }
        }]
    };
    taxChart.setOption(taxOption);
    
    // Crisis Detection Chart
    const crisisChart = echarts.init(document.getElementById('crisisChart'));
    const crisisOption = {
        backgroundColor: 'transparent',
        grid: { top: 10, right: 10, bottom: 20, left: 30 },
        xAxis: {
            type: 'category',
            data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 },
            splitLine: { lineStyle: { color: '#333' } }
        },
        series: [{
            data: [3, 7, 12, 8, 15, 6],
            type: 'bar',
            itemStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: '#ff6600' },
                        { offset: 1, color: '#ff9933' }
                    ]
                }
            }
        }]
    };
    crisisChart.setOption(crisisOption);
    
    // Talent Placement Chart
    const talentChart = echarts.init(document.getElementById('talentChart'));
    const talentOption = {
        backgroundColor: 'transparent',
        grid: { top: 10, right: 10, bottom: 20, left: 30 },
        xAxis: {
            type: 'category',
            data: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#666' } },
            axisLabel: { color: '#999', fontSize: 10 },
            splitLine: { lineStyle: { color: '#333' } }
        },
        series: [{
            data: [8, 15, 23, 31],
            type: 'line',
            smooth: true,
            lineStyle: { color: '#9933ff', width: 2 },
            itemStyle: { color: '#9933ff' },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(153,51,255,0.3)' },
                        { offset: 1, color: 'rgba(153,51,255,0.1)' }
                    ]
                }
            }
        }]
    };
    talentChart.setOption(talentOption);
    
    // Make charts responsive
    window.addEventListener('resize', () => {
        taxChart.resize();
        crisisChart.resize();
        talentChart.resize();
    });
}

// Neural network visualization using p5.js
function initializeNeuralNetwork() {
    const networkContainer = document.getElementById('neuralNetwork');
    if (!networkContainer) return;
    
    new p5((p) => {
        let nodes = [];
        let connections = [];
        
        p.setup = function() {
            const canvas = p.createCanvas(networkContainer.offsetWidth, networkContainer.offsetHeight);
            canvas.parent('neuralNetwork');
            
            // Create nodes
            for (let i = 0; i < 20; i++) {
                nodes.push({
                    x: p.random(p.width),
                    y: p.random(p.height),
                    vx: p.random(-1, 1),
                    vy: p.random(-1, 1),
                    size: p.random(3, 8)
                });
            }
            
            // Create connections
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dist = p.dist(nodes[i].x, nodes[i].y, nodes[j].x, nodes[j].y);
                    if (dist < 150) {
                        connections.push({ from: i, to: j, strength: p.random(0.3, 1) });
                    }
                }
            }
        };
        
        p.draw = function() {
            p.clear();
            
            // Update and draw nodes
            for (let node of nodes) {
                node.x += node.vx;
                node.y += node.vy;
                
                // Bounce off edges
                if (node.x < 0 || node.x > p.width) node.vx *= -1;
                if (node.y < 0 || node.y > p.height) node.vy *= -1;
                
                // Draw node
                p.fill(0, 102, 255, 150);
                p.noStroke();
                p.ellipse(node.x, node.y, node.size);
                
                // Draw glow
                p.fill(0, 102, 255, 50);
                p.ellipse(node.x, node.y, node.size * 2);
            }
            
            // Draw connections
            for (let conn of connections) {
                const from = nodes[conn.from];
                const to = nodes[conn.to];
                
                p.stroke(0, 102, 255, conn.strength * 100);
                p.strokeWeight(conn.strength * 2);
                p.line(from.x, from.y, to.x, to.y);
                
                // Animate connection strength
                conn.strength += p.random(-0.05, 0.05);
                conn.strength = p.constrain(conn.strength, 0.1, 1);
            }
        };
        
        p.windowResized = function() {
            p.resizeCanvas(networkContainer.offsetWidth, networkContainer.offsetHeight);
        };
    });
}

// Engine simulations and animations
function startEngineSimulations() {
    // Simulate tax recovery updates
    setInterval(() => {
        const taxElement = document.getElementById('taxRecovery');
        if (taxElement) {
            const currentValue = parseInt(taxElement.textContent.replace(/[RK,]/g, '')) || 0;
            const newValue = currentValue + Math.floor(Math.random() * 5000);
            taxElement.textContent = 'R' + newValue.toLocaleString();
        }
    }, 5000);
    
    // Simulate crisis alerts
    setInterval(() => {
        const alertElement = document.getElementById('crisisAlerts');
        if (alertElement) {
            const currentValue = parseInt(alertElement.textContent) || 0;
            const newValue = currentValue + Math.floor(Math.random() * 3);
            alertElement.textContent = newValue;
        }
    }, 8000);
    
    // Simulate developer placements
    setInterval(() => {
        const placementElement = document.getElementById('developersPlaced');
        if (placementElement) {
            const currentValue = parseInt(placementElement.textContent) || 0;
            const newValue = currentValue + Math.floor(Math.random() * 2);
            placementElement.textContent = newValue + '';
        }
    }, 12000);
    
    // Simulate self-healing log updates
    setInterval(() => {
        const logElement = document.getElementById('healingLog');
        if (logElement) {
            const timestamp = new Date().toLocaleTimeString();
            const messages = [
                `[${timestamp}] System health check completed. All systems nominal.`,
                `[${timestamp}] Optimizing neural network parameters...`,
                `[${timestamp}] Updating SARS regulation database...`,
                `[${timestamp}] Processing GDELT data streams...`,
                `[${timestamp}] Validating developer skill assessments...`
            ];
            
            const randomMessage = messages[Math.floor(Math.random() * messages.length)];
            logElement.innerHTML = `<div>${randomMessage}</div>` + logElement.innerHTML;
            
            // Keep only last 4 messages
            const lines = logElement.innerHTML.split('</div>');
            if (lines.length > 4) {
                logElement.innerHTML = lines.slice(0, 4).join('</div>');
            }
        }
    }, 15000);
}

// Model highlighting functionality
function highlightModel(model) {
    // Remove previous highlights
    document.querySelectorAll('.card-hover').forEach(card => {
        card.classList.remove('border-blue-500');
    });
    
    // Add highlight to clicked model
    event.currentTarget.classList.add('border-blue-500');
    
    // Show model-specific information
    const modelInfo = {
        qwen: "Qwen-Max is orchestrating R500K tax recoveries while you sleep, coordinating the entire AI empire with strategic intelligence.",
        mistral: "Mistral Large ensures SARS compliance down to the last rand, handling all regulatory communications with precision.",
        aya: "Aya Vision sees what's coming—strikes, shortages, opportunities—providing multimodal intelligence before anyone else."
    };
    
    // Could show this in a toast notification or modal
    console.log(`Highlighted: ${model} - ${modelInfo[model]}`);
}

// Engine toggle functionality
function toggleEngine(engine) {
    const engines = {
        financial: { status: 'financialStatus', active: 'Active', inactive: 'Standby' },
        guardian: { status: 'guardianStatus', active: 'Processing', inactive: 'Monitoring' },
        talent: { status: 'talentStatus', active: 'Active', inactive: 'Idle' }
    };
    
    const engineConfig = engines[engine];
    const statusElement = document.getElementById(engineConfig.status);
    
    if (statusElement) {
        const isActive = statusElement.textContent === engineConfig.active;
        statusElement.textContent = isActive ? engineConfig.inactive : engineConfig.active;
        
        // Add visual feedback
        const button = event.currentTarget;
        button.style.transform = 'scale(0.95)';
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 150);
    }
}

// Initialize scroll animations
function initializeAnimations() {
    // Animate elements on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe all cards and sections
    document.querySelectorAll('.card-hover, section > div').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// Navigation functions
function scrollToDemo() {
    document.getElementById('dashboard').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

// Modal functions
function showEarlyAccess() {
    const modal = document.getElementById('earlyAccessModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    // Animate modal appearance
    anime({
        targets: modal.querySelector('div'),
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 300,
        easing: 'easeOutCubic'
    });
}

function hideEarlyAccess() {
    const modal = document.getElementById('earlyAccessModal');
    
    anime({
        targets: modal.querySelector('div'),
        scale: [1, 0.8],
        opacity: [1, 0],
        duration: 200,
        easing: 'easeInCubic',
        complete: () => {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    });
}

function submitEarlyAccess(event) {
    event.preventDefault();
    
    // Simulate form submission
    const formData = new FormData(event.target);
    const email = formData.get('email') || event.target.querySelector('input[type="email"]').value;
    
    // Show success message
    const modal = document.getElementById('earlyAccessModal');
    const content = modal.querySelector('div');
    
    content.innerHTML = `
        <div class="text-center">
            <div class="text-6xl mb-4">🚀</div>
            <h3 class="text-2xl font-bold text-white mb-4">Welcome to the Empire</h3>
            <p class="text-gray-300 mb-6">
                Thank you for your interest in the Vaal AI Empire. 
                We'll notify you when early access becomes available.
            </p>
            <button onclick="hideEarlyAccess()" class="btn-primary px-8 py-3 rounded-lg text-white font-semibold">
                Continue Exploring
            </button>
        </div>
    `;
    
    // Reset form after delay
    setTimeout(() => {
        hideEarlyAccess();
        setTimeout(() => {
            content.innerHTML = `
                <h3 class="text-2xl font-bold text-white mb-4">Join the Empire</h3>
                <p class="text-gray-300 mb-6">
                    Be among the first to experience South Africa's autonomous AI empire. 
                    Limited early access available for December 2025 launch.
                </p>
                <form onsubmit="submitEarlyAccess(event)">
                    <input type="email" placeholder="Enter your email" class="w-full p-3 rounded-lg bg-gray-800 border border-gray-600 text-white mb-4" required>
                    <input type="text" placeholder="Company name" class="w-full p-3 rounded-lg bg-gray-800 border border-gray-600 text-white mb-4" required>
                    <select class="w-full p-3 rounded-lg bg-gray-800 border border-gray-600 text-white mb-6" required>
                        <option value="">Select your industry</option>
                        <option value="manufacturing">Manufacturing</option>
                        <option value="finance">Finance</option>
                        <option value="technology">Technology</option>
                        <option value="agriculture">Agriculture</option>
                        <option value="other">Other</option>
                    </select>
                    <div class="flex gap-4">
                        <button type="submit" class="btn-primary px-6 py-3 rounded-lg text-white font-semibold flex-1">
                            Request Access
                        </button>
                        <button type="button" onclick="hideEarlyAccess()" class="border border-gray-600 px-6 py-3 rounded-lg text-gray-300 hover:bg-gray-800">
                            Cancel
                        </button>
                    </div>
                </form>
            `;
        }, 500);
    }, 3000);
}

// Utility functions
function formatCurrency(amount) {
    return 'R' + amount.toLocaleString();
}

function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Add some industrial sound effects (optional)
function playIndustrialSound() {
    // This could be implemented with Web Audio API
    // For now, just a placeholder
    console.log('🔧 Industrial sound played');
}

// Add hover effects to buttons
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('button, .btn-primary');
    
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            playIndustrialSound();
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Add particle effect on button clicks
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON' || e.target.classList.contains('btn-primary')) {
        createParticleEffect(e.clientX, e.clientY);
    }
});

function createParticleEffect(x, y) {
    // Simple particle effect
    for (let i = 0; i < 5; i++) {
        const particle = document.createElement('div');
        particle.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 4px;
            height: 4px;
            background: #0066ff;
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
        `;
        document.body.appendChild(particle);
        
        anime({
            targets: particle,
            translateX: (Math.random() - 0.5) * 100,
            translateY: (Math.random() - 0.5) * 100,
            opacity: [1, 0],
            scale: [1, 0],
            duration: 1000,
            easing: 'easeOutCubic',
            complete: () => particle.remove()
        });
    }
}

// Console easter egg
console.log(`
🚀 VAAL AI EMPIRE - SYSTEM ONLINE
=================================
Built in the Vaal Triangle
Built for Africa
Built to dominate

Digital sovereignty begins here.
`);

// Payment System Integration
function initializePaymentSystem() {
    // Initialize Stripe elements if on payment page
    if (document.getElementById('paymentForm')) {
        initializePaymentForm();
    }
    
    // Initialize payment tracking
    initializePaymentTracking();
}

function initializePaymentForm() {
    const paymentForm = document.getElementById('paymentForm');
    if (!paymentForm) return;
    
    // Add payment method change handler
    const paymentMethodSelect = paymentForm.querySelector('select');
    const cardElement = document.getElementById('cardElement');
    
    if (paymentMethodSelect && cardElement) {
        paymentMethodSelect.addEventListener('change', function() {
            if (this.value === 'card') {
                cardElement.classList.remove('hidden');
            } else {
                cardElement.classList.add('hidden');
            }
        });
    }
    
    // Add form submission handler
    paymentForm.addEventListener('submit', handlePaymentSubmission);
}

function handlePaymentSubmission(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const paymentData = {
        amount: formData.get('amount') || e.target.querySelector('input[type="number"]').value,
        email: formData.get('email') || e.target.querySelector('input[type="email"]').value,
        payment_method: formData.get('payment_method') || e.target.querySelector('select').value,
        consent: e.target.querySelector('input[type="checkbox"]').checked
    };
    
    // Validate payment data
    if (!paymentData.consent) {
        showPaymentError('Please provide consent for data processing.');
        return;
    }
    
    if (!paymentData.amount || paymentData.amount <= 0) {
        showPaymentError('Please enter a valid amount.');
        return;
    }
    
    // Simulate payment processing
    processPayment(paymentData);
}

function processPayment(paymentData) {
    const submitButton = document.querySelector('#paymentForm button[type="submit"]');
    const originalText = submitButton.textContent;
    
    // Show loading state
    submitButton.textContent = 'Processing Payment...';
    submitButton.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        // Simulate successful payment
        const transactionId = 'TXN_' + Math.random().toString(36).substr(2, 9).toUpperCase();
        const timestamp = new Date().toISOString();
        
        // Log transaction
        logTransaction({
            id: transactionId,
            amount: paymentData.amount,
            currency: 'ZAR',
            method: paymentData.payment_method,
            email: paymentData.email,
            status: 'success',
            timestamp: timestamp
        });
        
        // Show success
        showPaymentSuccess(transactionId);
        
        // Reset form
        document.getElementById('paymentForm').reset();
        document.getElementById('cardElement').classList.add('hidden');
        
        // Reset button
        submitButton.textContent = originalText;
        submitButton.disabled = false;
        
    }, 2000);
}

function logTransaction(transaction) {
    // Store transaction in local storage for demo
    const transactions = JSON.parse(localStorage.getItem('vaal_transactions') || '[]');
    transactions.unshift(transaction);
    localStorage.setItem('vaal_transactions', JSON.stringify(transactions.slice(0, 50))); // Keep last 50
}

function showPaymentSuccess(transactionId) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-gray-900 rounded-lg p-8 max-w-md mx-4 border border-gray-700 text-center">
            <div class="text-6xl mb-4">✅</div>
            <h3 class="text-2xl font-bold text-white mb-4">Payment Successful</h3>
            <div class="bg-gray-800 rounded-lg p-4 mb-6">
                <div class="text-sm text-gray-400 mb-2">Transaction ID</div>
                <div class="text-white font-mono">${transactionId}</div>
            </div>
            <p class="text-gray-300 mb-6">
                Your transaction has been processed securely. You will receive a confirmation email shortly.
            </p>
            <button onclick="this.parentElement.parentElement.remove()" class="btn-primary px-8 py-3 rounded-lg text-white font-semibold">
                Continue
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Animate modal appearance
    anime({
        targets: modal.querySelector('div'),
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 300,
        easing: 'easeOutCubic'
    });
}

function showPaymentError(message) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-gray-900 rounded-lg p-8 max-w-md mx-4 border border-gray-700 text-center">
            <div class="text-6xl mb-4">❌</div>
            <h3 class="text-2xl font-bold text-white mb-4">Payment Error</h3>
            <p class="text-gray-300 mb-6">${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" class="bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg text-white font-semibold">
                Try Again
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Animate modal appearance
    anime({
        targets: modal.querySelector('div'),
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 300,
        easing: 'easeOutCubic'
    });
}

function initializePaymentTracking() {
    // Simulate real-time transaction updates
    setInterval(() => {
        updateTransactionLog();
    }, 15000);
}

function updateTransactionLog() {
    const logElement = document.querySelector('.transaction-log');
    if (!logElement) return;
    
    // Simulate new transactions
    const currencies = ['ZAR', 'USD', 'EUR', 'GBP'];
    const statuses = ['SUCCESS', 'PENDING', 'FAILED'];
    const amounts = [5000, 2500, 1200, 10000, 7500];
    
    const timestamp = new Date().toLocaleTimeString();
    const amount = amounts[Math.floor(Math.random() * amounts.length)];
    const fromCurrency = currencies[Math.floor(Math.random() * currencies.length)];
    const toCurrency = currencies[Math.floor(Math.random() * currencies.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    
    const logEntry = document.createElement('div');
    logEntry.className = `status-${status.toLowerCase()}`;
    logEntry.textContent = `[${timestamp}] R${amount.toLocaleString()} ${fromCurrency} → ${toCurrency} - ${status}`;
    
    // Add to log
    logElement.insertBefore(logEntry, logElement.firstChild);
    
    // Keep only last 6 entries
    while (logElement.children.length > 6) {
        logElement.removeChild(logElement.lastChild);
    }
}

// Payment plan selection
function selectPlan(plan) {
    const plans = {
        starter: {
            name: 'Starter Plan',
            price: '2.9% + R2.50',
            features: ['Credit & debit cards', 'Mobile payments', 'Local bank transfers']
        },
        professional: {
            name: 'Professional Plan',
            price: '2.4% + R1.50',
            features: ['International payments', 'Cryptocurrency support', 'Advanced fraud protection']
        },
        enterprise: {
            name: 'Enterprise Plan',
            price: 'Custom pricing',
            features: ['Volume discounts', 'Dedicated support', 'Custom compliance']
        }
    };
    
    const selectedPlan = plans[plan];
    
    // Create plan selection modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-gray-900 rounded-lg p-8 max-w-md mx-4 border border-gray-700">
            <h3 class="text-2xl font-bold text-white mb-4">${selectedPlan.name}</h3>
            <div class="text-3xl font-bold text-blue-400 mb-6">${selectedPlan.price}</div>
            <ul class="space-y-2 mb-6">
                ${selectedPlan.features.map(feature => `
                    <li class="flex items-center space-x-2">
                        <span class="text-green-400">✓</span>
                        <span class="text-gray-300">${feature}</span>
                    </li>
                `).join('')}
            </ul>
            <div class="flex gap-4">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="btn-primary px-6 py-3 rounded-lg text-white font-semibold flex-1">
                    Get Started
                </button>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="border border-gray-600 px-6 py-3 rounded-lg text-gray-300 hover:bg-gray-800">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Animate modal appearance
    anime({
        targets: modal.querySelector('div'),
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 300,
        easing: 'easeOutCubic'
    });
}

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeAnimations,
        initializeCounters,
        initializeCharts,
        initializePaymentSystem,
        highlightModel,
        toggleEngine,
        showEarlyAccess,
        hideEarlyAccess,
        selectPlan,
        processPayment,
        showPaymentSuccess,
        showPaymentError
    };
}