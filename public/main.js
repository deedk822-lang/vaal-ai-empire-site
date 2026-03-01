/**
 * VAAL AI EMPIRE - MAIN DASHBOARD LOGIC
 * Production-ready interactive experience
 */

// ============================================
// CONFIGURATION
// ============================================

const CONFIG = {
    apiUrl: window.location.hostname === 'localhost' 
        ? 'http://localhost:4242' 
        : 'https://api.vaalai.co.za',
    updateInterval: 5000, // 5 seconds
    animationDuration: 2000,
    metrics: {
        taxRecovery: { current: 0, target: 500000, increment: 15000 },
        crisisAlerts: { current: 0, target: 247, increment: 3 },
        developersPlaced: { current: 0, target: 142, increment: 2 }
    }
};

// ============================================
// NEURAL NETWORK BACKGROUND (P5.js)
// ============================================

let neuralSketch = function(p) {
    let nodes = [];
    let connections = [];
    
    p.setup = function() {
        const container = document.getElementById('neuralNetwork');
        if (!container) return;
        
        const canvas = p.createCanvas(container.offsetWidth, container.offsetHeight);
        canvas.parent('neuralNetwork');
        
        // Create nodes
        for (let i = 0; i < 50; i++) {
            nodes.push({
                x: p.random(p.width),
                y: p.random(p.height),
                vx: p.random(-0.5, 0.5),
                vy: p.random(-0.5, 0.5)
            });
        }
    };
    
    p.draw = function() {
        p.clear();
        
        // Update and draw nodes
        nodes.forEach((node, i) => {
            // Move nodes
            node.x += node.vx;
            node.y += node.vy;
            
            // Bounce off edges
            if (node.x < 0 || node.x > p.width) node.vx *= -1;
            if (node.y < 0 || node.y > p.height) node.vy *= -1;
            
            // Draw connections
            nodes.slice(i + 1).forEach(other => {
                const d = p.dist(node.x, node.y, other.x, other.y);
                if (d < 150) {
                    p.stroke(0, 102, 255, p.map(d, 0, 150, 50, 0));
                    p.strokeWeight(1);
                    p.line(node.x, node.y, other.x, other.y);
                }
            });
            
            // Draw node
            p.fill(0, 102, 255, 150);
            p.noStroke();
            p.circle(node.x, node.y, 4);
        });
    };
    
    p.windowResized = function() {
        const container = document.getElementById('neuralNetwork');
        if (container) {
            p.resizeCanvas(container.offsetWidth, container.offsetHeight);
        }
    };
};

// ============================================
// HERO SECTION ANIMATIONS
// ============================================

function initHeroAnimations() {
    // Typed.js hero text
    if (typeof Typed !== 'undefined') {
        new Typed('#typed-text', {
            strings: [
                'the Vaal Triangle',
                'AI sovereignty',
                'African innovation',
                'the impossible',
                'digital colonization'
            ],
            typeSpeed: 60,
            backSpeed: 40,
            backDelay: 2000,
            loop: true,
            cursorChar: '_',
            smartBackspace: true
        });
    }
    
    // Animated counters
    animateCounters();
}

function animateCounters() {
    const counters = document.querySelectorAll('.metric-counter');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = CONFIG.animationDuration;
        const increment = target / (duration / 16); // 60fps
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target;
            }
        };
        
        // Start animation when in viewport
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        observer.observe(counter);
    });
}

// ============================================
// DASHBOARD METRICS (Real-time Updates)
// ============================================

let metricsInterval;

function initDashboardMetrics() {
    updateTaxRecovery();
    updateCrisisAlerts();
    updateDevelopersPlaced();
    
    // Update metrics every 5 seconds
    metricsInterval = setInterval(() => {
        updateTaxRecovery();
        updateCrisisAlerts();
        updateDevelopersPlaced();
    }, CONFIG.updateInterval);
}

function updateTaxRecovery() {
    const element = document.getElementById('taxRecovery');
    if (!element) return;
    
    const metric = CONFIG.metrics.taxRecovery;
    metric.current = Math.min(
        metric.current + metric.increment,
        metric.target
    );
    
    element.textContent = `R${(metric.current / 1000).toFixed(0)}K`;
    
    // Animate
    if (typeof anime !== 'undefined') {
        anime({
            targets: element,
            scale: [1, 1.1, 1],
            duration: 500,
            easing: 'easeInOutQuad'
        });
    }
}

function updateCrisisAlerts() {
    const element = document.getElementById('crisisAlerts');
    if (!element) return;
    
    const metric = CONFIG.metrics.crisisAlerts;
    metric.current = Math.min(
        metric.current + metric.increment,
        metric.target
    );
    
    element.textContent = metric.current;
    
    // Animate
    if (typeof anime !== 'undefined') {
        anime({
            targets: element,
            scale: [1, 1.1, 1],
            duration: 500,
            easing: 'easeInOutQuad'
        });
    }
}

function updateDevelopersPlaced() {
    const element = document.getElementById('developersPlaced');
    if (!element) return;
    
    const metric = CONFIG.metrics.developersPlaced;
    metric.current = Math.min(
        metric.current + metric.increment,
        metric.target
    );
    
    element.textContent = metric.current;
    
    // Animate
    if (typeof anime !== 'undefined') {
        anime({
            targets: element,
            scale: [1, 1.1, 1],
            duration: 500,
            easing: 'easeInOutQuad'
        });
    }
}

// ============================================
// ECHARTS VISUALIZATIONS
// ============================================

let taxChart, crisisChart, talentChart;

function initCharts() {
    if (typeof echarts === 'undefined') return;
    
    // Tax Recovery Chart
    const taxChartEl = document.getElementById('taxChart');
    if (taxChartEl) {
        taxChart = echarts.init(taxChartEl);
        taxChart.setOption({
            grid: { top: 10, right: 10, bottom: 20, left: 40 },
            xAxis: {
                type: 'category',
                data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                axisLine: { lineStyle: { color: '#666' } },
                axisLabel: { color: '#999', fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#999', fontSize: 10 },
                splitLine: { lineStyle: { color: '#333' } }
            },
            series: [{
                data: [85, 120, 95, 140, 110],
                type: 'line',
                smooth: true,
                lineStyle: { color: '#00ff88', width: 2 },
                itemStyle: { color: '#00ff88' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
                        { offset: 1, color: 'rgba(0, 255, 136, 0)' }
                    ])
                }
            }]
        });
    }
    
    // Crisis Chart
    const crisisChartEl = document.getElementById('crisisChart');
    if (crisisChartEl) {
        crisisChart = echarts.init(crisisChartEl);
        crisisChart.setOption({
            grid: { top: 10, right: 10, bottom: 20, left: 40 },
            xAxis: {
                type: 'category',
                data: ['00:00', '06:00', '12:00', '18:00', '24:00'],
                axisLine: { lineStyle: { color: '#666' } },
                axisLabel: { color: '#999', fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#999', fontSize: 10 },
                splitLine: { lineStyle: { color: '#333' } }
            },
            series: [{
                data: [12, 18, 24, 15, 20],
                type: 'bar',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#ff8800' },
                        { offset: 1, color: '#cc6600' }
                    ])
                }
            }]
        });
    }
    
    // Talent Chart
    const talentChartEl = document.getElementById('talentChart');
    if (talentChartEl) {
        talentChart = echarts.init(talentChartEl);
        talentChart.setOption({
            grid: { top: 10, right: 10, bottom: 20, left: 40 },
            xAxis: {
                type: 'category',
                data: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                axisLine: { lineStyle: { color: '#666' } },
                axisLabel: { color: '#999', fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#999', fontSize: 10 },
                splitLine: { lineStyle: { color: '#333' } }
            },
            series: [{
                data: [28, 32, 38, 42, 45],
                type: 'line',
                smooth: true,
                lineStyle: { color: '#a855f7', width: 2 },
                itemStyle: { color: '#a855f7' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(168, 85, 247, 0.3)' },
                        { offset: 1, color: 'rgba(168, 85, 247, 0)' }
                    ])
                }
            }]
        });
    }
    
    // Auto-resize charts
    window.addEventListener('resize', () => {
        taxChart?.resize();
        crisisChart?.resize();
        talentChart?.resize();
    });
}

// ============================================
// MODEL COUNCIL INTERACTIONS
// ============================================

function highlightModel(modelName) {
    const models = {
        qwen: { color: '#00ff88', name: 'Qwen-Max' },
        mistral: { color: '#0066ff', name: 'Mistral Large' },
        aya: { color: '#ff8800', name: 'Aya Vision' }
    };
    
    const model = models[modelName];
    if (!model) return;
    
    // Visual feedback
    console.log(`Highlighted: ${model.name}`);
    
    // Could add visual effects here
    if (typeof anime !== 'undefined') {
        const cards = document.querySelectorAll('.card-hover');
        cards.forEach((card, index) => {
            const modelKeys = Object.keys(models);
            if (modelKeys[index] === modelName) {
                anime({
                    targets: card,
                    borderColor: model.color,
                    scale: [1, 1.02, 1],
                    duration: 500,
                    easing: 'easeInOutQuad'
                });
            }
        });
    }
}

// ============================================
// ENGINE CONTROLS
// ============================================

const engineStates = {
    financial: true,
    guardian: true,
    talent: true
};

function toggleEngine(engineType) {
    engineStates[engineType] = !engineStates[engineType];
    
    const statusElement = document.getElementById(`${engineType}Status`);
    if (statusElement) {
        statusElement.textContent = engineStates[engineType] ? 'Active' : 'Paused';
        statusElement.style.color = engineStates[engineType] ? '#00ff88' : '#999';
    }
    
    // Visual feedback
    const button = event?.target.closest('.engine-control');
    if (button && typeof anime !== 'undefined') {
        anime({
            targets: button,
            scale: [1, 0.95, 1],
            duration: 200,
            easing: 'easeInOutQuad'
        });
    }
    
    // Show notification
    showNotification(
        `${engineType.charAt(0).toUpperCase() + engineType.slice(1)} Engine ${engineStates[engineType] ? 'activated' : 'paused'}`,
        engineStates[engineType] ? 'success' : 'info'
    );
}

// ============================================
// SELF-HEALING LOG SIMULATION
// ============================================

let healingLogInterval;

function initSelfHealingLog() {
    const logElement = document.getElementById('healingLog');
    if (!logElement) return;
    
    const logs = [
        { time: '14:23:45', message: 'Error detected in tax_calculation_module.py', type: 'error' },
        { time: '14:23:46', message: 'Analyzing code repository...', type: 'info' },
        { time: '14:23:47', message: 'Root cause: Deprecated SARS API endpoint', type: 'warning' },
        { time: '14:23:48', message: 'Fetching updated API documentation...', type: 'info' },
        { time: '14:23:49', message: 'Generating patch code...', type: 'info' },
        { time: '14:23:50', message: 'Applying patch via GitHub API...', type: 'info' },
        { time: '14:23:51', message: 'Running automated tests...', type: 'info' },
        { time: '14:23:52', message: 'Tests passed. Deploying to production...', type: 'success' },
        { time: '14:23:53', message: 'Redeployment successful. Zero downtime.', type: 'success' }
    ];
    
    let currentIndex = 0;
    
    healingLogInterval = setInterval(() => {
        if (currentIndex >= logs.length) {
            clearInterval(healingLogInterval);
            return;
        }
        
        const log = logs[currentIndex];
        const color = log.type === 'error' ? '#ff4444' : 
                      log.type === 'success' ? '#00ff88' : 
                      log.type === 'warning' ? '#ffaa00' : '#ffffff';
        
        const newLog = document.createElement('div');
        newLog.style.color = color;
        newLog.textContent = `[${log.time}] ${log.message}`;
        
        logElement.appendChild(newLog);
        
        // Remove old logs
        if (logElement.children.length > 6) {
            logElement.removeChild(logElement.firstChild);
        }
        
        currentIndex++;
    }, 1000);
}

// ============================================
// EARLY ACCESS MODAL
// ============================================

function showEarlyAccess() {
    const modal = document.getElementById('earlyAccessModal');
    if (modal) {
        modal.style.display = 'flex';
        
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
}

function hideEarlyAccess() {
    const modal = document.getElementById('earlyAccessModal');
    if (modal) {
        if (typeof anime !== 'undefined') {
            anime({
                targets: modal.querySelector('div'),
                scale: [1, 0.8],
                opacity: [1, 0],
                duration: 200,
                easing: 'easeInCubic',
                complete: () => {
                    modal.style.display = 'none';
                }
            });
        } else {
            modal.style.display = 'none';
        }
    }
}

async function submitEarlyAccess(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = {
        email: form.querySelector('input[type="email"]').value,
        company: form.querySelector('input[type="text"]').value,
        industry: form.querySelector('select').value,
        timestamp: new Date().toISOString()
    };
    
    try {
        // Submit to backend
        const response = await fetch(`${CONFIG.apiUrl}/api/early-access`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Submission failed');
        
        // Success
        showNotification('Welcome to the Empire! Check your email for next steps.', 'success');
        hideEarlyAccess();
        form.reset();
        
    } catch (error) {
        console.error('Early access submission error:', error);
        showNotification('Submission failed. Please try again.', 'error');
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'error' ? 'bg-red-600' : 
                     type === 'success' ? 'bg-green-600' : 
                     'bg-blue-600';
    
    notification.className = `fixed top-24 right-6 ${bgColor} text-white px-6 py-4 rounded-lg shadow-lg z-50 max-w-md`;
    notification.innerHTML = `
        <div class="flex items-center space-x-3">
            <span class="text-2xl">${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</span>
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

function scrollToDemo() {
    const dashboard = document.getElementById('dashboard');
    if (dashboard) {
        dashboard.scrollIntoView({ behavior: 'smooth' });
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔥 Vaal AI Empire Initializing...');
    
    // Initialize neural network background
    if (typeof p5 !== 'undefined') {
        new p5(neuralSketch);
    }
    
    // Initialize hero animations
    initHeroAnimations();
    
    // Initialize dashboard
    initDashboardMetrics();
    initCharts();
    
    // Initialize self-healing log
    setTimeout(() => initSelfHealingLog(), 2000);
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.card-hover').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    console.log('✅ Vaal AI Empire Online');
});

// Export for global access
window.highlightModel = highlightModel;
window.toggleEngine = toggleEngine;
window.showEarlyAccess = showEarlyAccess;
window.hideEarlyAccess = hideEarlyAccess;
window.submitEarlyAccess = submitEarlyAccess;
window.scrollToDemo = scrollToDemo;