// Vaal AI Empire - Dashboard JavaScript
// Real-time analytics and observability

// Sample data for demonstration
const sampleTraces = [
    { timestamp: '2025-12-16 08:15:23', engine: 'Financial Sentinel', operation: 'Tax Recovery Scan', duration: '1.2s', status: 'success' },
    { timestamp: '2025-12-16 08:14:18', engine: 'Guardian Engine', operation: 'Health Check', duration: '0.3s', status: 'success' },
    { timestamp: '2025-12-16 08:13:45', engine: 'Talent Accelerator', operation: 'Candidate Match', duration: '2.1s', status: 'success' },
    { timestamp: '2025-12-16 08:12:30', engine: 'Financial Sentinel', operation: 'SARS Compliance', duration: '0.8s', status: 'success' },
    { timestamp: '2025-12-16 08:11:15', engine: 'Guardian Engine', operation: 'Auto-Healing', duration: '5.4s', status: 'pending' },
];

const sampleExperiments = [
    { name: 'Tax Recovery Optimization', status: 'running', accuracy: 94.5, traces: 1247 },
    { name: 'Prompt Engineering v2', status: 'completed', accuracy: 98.2, traces: 3421 },
    { name: 'Multi-Engine Coordination', status: 'running', accuracy: 91.8, traces: 892 },
];

// Populate traces table
function populateTraces() {
    const tbody = document.getElementById('traces-table');
    if (!tbody) return;

    tbody.innerHTML = sampleTraces.map(trace => `
        <tr>
            <td>${trace.timestamp}</td>
            <td><strong>${trace.engine}</strong></td>
            <td>${trace.operation}</td>
            <td>${trace.duration}</td>
            <td><span class="status-badge ${trace.status}">${trace.status.toUpperCase()}</span></td>
            <td><button class="btn-secondary" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;">View</button></td>
        </tr>
    `).join('');
}

// Populate experiments
function populateExperiments() {
    const grid = document.getElementById('experiments-grid');
    if (!grid) return;

    grid.innerHTML = sampleExperiments.map(exp => `
        <div class="experiment-card">
            <h4>${exp.name}</h4>
            <p class="experiment-meta">Status: <strong>${exp.status}</strong></p>
            <div class="experiment-metrics">
                <div class="metric">
                    <div class="metric-label">Accuracy</div>
                    <div class="metric-value">${exp.accuracy}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Traces</div>
                    <div class="metric-value">${exp.traces.toLocaleString()}</div>
                </div>
            </div>
            <button class="btn-primary" style="width: 100%; padding: 0.75rem;">View Results</button>
        </div>
    `).join('');
}

// Create trace volume chart
function createTraceChart() {
    const canvas = document.getElementById('traceCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            datasets: [{
                label: 'Traces',
                data: [285000, 342000, 398000, 425000],
                borderColor: '#f7b731',
                backgroundColor: 'rgba(247, 183, 49, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#ccc' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    ticks: { color: '#ccc' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
}

// Create performance chart
function createPerformanceChart() {
    const canvas = document.getElementById('performanceCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Financial Sentinel', 'Guardian Engine', 'Talent Accelerator'],
            datasets: [{
                label: 'Success Rate %',
                data: [98.5, 99.7, 96.2],
                backgroundColor: ['#f7b731', '#00ff88', '#3498db'],
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: '#ccc' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    ticks: { color: '#ccc' },
                    grid: { display: false }
                }
            }
        }
    });
}

// Animate counter
function animateCounter(elementId, target) {
    const element = document.getElementById(elementId);
    if (!element) return;

    let current = 0;
    const increment = target / 100;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target.toLocaleString();
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current).toLocaleString();
        }
    }, 20);
}

// Initialize dashboard
window.addEventListener('DOMContentLoaded', () => {
    console.log('⚡ Vaal AI Empire Dashboard - Initializing...');
    
    populateTraces();
    populateExperiments();
    
    // Delay chart creation to ensure DOM is ready
    setTimeout(() => {
        createTraceChart();
        createPerformanceChart();
    }, 100);
    
    // Animate stats
    animateCounter('total-traces', 1247893);
    
    console.log('✅ Dashboard loaded successfully');
});

// Real-time updates simulation
setInterval(() => {
    const traceCount = document.getElementById('total-traces');
    if (traceCount) {
        const current = parseInt(traceCount.textContent.replace(/,/g, ''));
        traceCount.textContent = (current + Math.floor(Math.random() * 10)).toLocaleString();
    }
}, 5000);

// Export for use in other scripts
window.VaalDashboard = {
    populateTraces,
    populateExperiments,
    createTraceChart,
    createPerformanceChart
};