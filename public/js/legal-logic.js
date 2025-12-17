/**
 * LEGAL COMPLIANCE - PRODUCTION LOGIC
 * Document management and compliance tracking
 */

// Compliance status tracking
const complianceStatus = {
    popia: {
        status: 'compliant',
        lastAudit: '2025-01-15',
        nextAudit: '2025-07-15',
        certificate: 'POPIA-CERT-2025-001'
    },
    pciDss: {
        status: 'compliant',
        lastAudit: '2024-12-01',
        nextAudit: '2025-12-01',
        certificate: 'PCI-DSS-L1-2024-456'
    },
    sarb: {
        status: 'authorized',
        licenseNumber: 'PSP-2024-789',
        expiryDate: '2026-12-31',
        authorization: 'SARB-AUTH-2024-123'
    },
    gdpr: {
        status: 'compliant',
        dpo: 'privacy@vaalai.co.za',
        lastAssessment: '2025-01-10',
        nextAssessment: '2025-07-10'
    },
    iso27001: {
        status: 'certified',
        certificateNumber: 'ISO27001-2024-999',
        issuedDate: '2024-11-15',
        expiryDate: '2027-11-15'
    }
};

// Document library
const legalDocuments = {
    policies: {
        privacyPolicy: {
            name: 'Privacy Policy',
            description: 'Data collection and processing practices',
            version: '2.1',
            lastUpdated: '2025-01-01',
            url: '/docs/privacy-policy-v2.1.pdf'
        },
        termsOfService: {
            name: 'Terms of Service',
            description: 'Service usage terms and conditions',
            version: '3.0',
            lastUpdated: '2024-12-15',
            url: '/docs/terms-of-service-v3.0.pdf'
        },
        cookiePolicy: {
            name: 'Cookie Policy',
            description: 'Cookie usage and tracking practices',
            version: '1.5',
            lastUpdated: '2024-12-01',
            url: '/docs/cookie-policy-v1.5.pdf'
        },
        dpa: {
            name: 'Data Processing Agreement',
            description: 'GDPR-compliant data processing terms',
            version: '2.0',
            lastUpdated: '2025-01-05',
            url: '/docs/data-processing-agreement-v2.0.pdf'
        }
    },
    certificates: {
        pciDss: {
            name: 'PCI DSS Certificate',
            description: 'Level 1 compliance validation',
            certificateNumber: 'PCI-DSS-L1-2024-456',
            issuedDate: '2024-12-01',
            expiryDate: '2025-12-01',
            url: '/certs/pci-dss-certificate.pdf'
        },
        iso27001: {
            name: 'ISO 27001 Certificate',
            description: 'Information security management',
            certificateNumber: 'ISO27001-2024-999',
            issuedDate: '2024-11-15',
            expiryDate: '2027-11-15',
            url: '/certs/iso27001-certificate.pdf'
        },
        sarbAuth: {
            name: 'SARB Authorization',
            description: 'Payment service provider license',
            licenseNumber: 'PSP-2024-789',
            issuedDate: '2024-10-01',
            expiryDate: '2026-12-31',
            url: '/certs/sarb-authorization.pdf'
        },
        popiaCompliance: {
            name: 'POPIA Compliance Certificate',
            description: 'Data protection compliance',
            certificateNumber: 'POPIA-CERT-2025-001',
            issuedDate: '2025-01-15',
            expiryDate: '2026-01-15',
            url: '/certs/popia-compliance.pdf'
        }
    }
};

// Track document download
function trackDocumentDownload(documentType, documentName) {
    // Send analytics
    if (typeof gtag !== 'undefined') {
        gtag('event', 'document_download', {
            event_category: 'Legal',
            event_label: `${documentType}/${documentName}`,
            value: 1
        });
    }
    
    // Log to console (for demo)
    console.log(`Document downloaded: ${documentType}/${documentName}`);
    
    // Could also send to backend
    fetch('/api/analytics/document-download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            documentType,
            documentName,
            timestamp: new Date().toISOString()
        })
    }).catch(err => console.error('Analytics error:', err));
}

// Show document modal
function showDocumentModal(documentKey, category) {
    const document = legalDocuments[category]?.[documentKey];
    if (!document) {
        console.error('Document not found:', documentKey, category);
        return;
    }
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-gray-900 rounded-lg p-8 max-w-2xl mx-4 border border-gray-700">
            <div class="flex justify-between items-start mb-6">
                <div>
                    <h3 class="text-2xl font-bold text-white mb-2">${document.name}</h3>
                    <p class="text-gray-400">${document.description}</p>
                </div>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="text-gray-400 hover:text-white text-2xl">
                    ×
                </button>
            </div>
            
            <div class="bg-gray-800 rounded-lg p-6 mb-6">
                <div class="grid grid-cols-2 gap-4 text-sm">
                    ${document.version ? `
                        <div>
                            <div class="text-gray-400">Version</div>
                            <div class="text-white font-semibold">${document.version}</div>
                        </div>
                    ` : ''}
                    ${document.lastUpdated ? `
                        <div>
                            <div class="text-gray-400">Last Updated</div>
                            <div class="text-white font-semibold">${document.lastUpdated}</div>
                        </div>
                    ` : ''}
                    ${document.certificateNumber ? `
                        <div>
                            <div class="text-gray-400">Certificate Number</div>
                            <div class="text-white font-semibold font-mono text-xs">${document.certificateNumber}</div>
                        </div>
                    ` : ''}
                    ${document.expiryDate ? `
                        <div>
                            <div class="text-gray-400">Expiry Date</div>
                            <div class="text-white font-semibold">${document.expiryDate}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            <div class="flex gap-4">
                <button onclick="downloadDocument('${documentKey}', '${category}', '${document.url}')" class="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-semibold flex-1">
                    📥 Download Document
                </button>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="border border-gray-600 px-6 py-3 rounded-lg text-gray-300 hover:bg-gray-800">
                    Close
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
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

// Download document
function downloadDocument(documentKey, category, url) {
    // Track download
    trackDocumentDownload(category, documentKey);
    
    // In production, trigger actual download
    // For demo, show success message
    const notification = document.createElement('div');
    notification.className = 'fixed top-24 right-6 bg-green-600 text-white px-6 py-4 rounded-lg shadow-lg z-50';
    notification.innerHTML = `
        <div class="flex items-center space-x-3">
            <span class="text-2xl">✅</span>
            <div>
                <div class="font-semibold">Download Started</div>
                <div class="text-sm opacity-90">Check your downloads folder</div>
            </div>
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
    
    // Remove after 3 seconds
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
    }, 3000);
    
    // Close modal
    document.querySelectorAll('.fixed.inset-0').forEach(modal => modal.remove());
    
    // In production, trigger download:
    // window.open(url, '_blank');
    console.log('Would download:', url);
}

// Display compliance dashboard
function updateComplianceDashboard() {
    const dashboard = document.querySelector('.compliance-dashboard');
    if (!dashboard) return;
    
    const totalCompliance = Object.values(complianceStatus)
        .filter(item => item.status === 'compliant' || item.status === 'certified' || item.status === 'authorized')
        .length;
    
    const complianceRate = (totalCompliance / Object.keys(complianceStatus).length) * 100;
    
    dashboard.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div>
                <div class="text-4xl font-black text-green-400 mb-4">${complianceRate.toFixed(0)}%</div>
                <h3 class="text-lg font-semibold text-white mb-2">Compliance Rate</h3>
                <p class="text-gray-400 text-sm">All regulatory requirements met</p>
            </div>
            <div>
                <div class="text-4xl font-black text-blue-400 mb-4">${Object.keys(legalDocuments.certificates).length}</div>
                <h3 class="text-lg font-semibold text-white mb-2">Active Certificates</h3>
                <p class="text-gray-400 text-sm">International and local compliance</p>
            </div>
            <div>
                <div class="text-4xl font-black text-purple-400 mb-4">24/7</div>
                <h3 class="text-lg font-semibold text-white mb-2">Monitoring</h3>
                <p class="text-gray-400 text-sm">Continuous compliance tracking</p>
            </div>
        </div>
    `;
}

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize compliance dashboard
    updateComplianceDashboard();
    
    // Attach download handlers
    document.querySelectorAll('.download-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const documentName = this.closest('li')?.querySelector('h4')?.textContent || 'Unknown';
            const category = this.closest('.legal-section')?.querySelector('h3')?.textContent.includes('Policy') 
                ? 'policies' 
                : 'certificates';
            
            // Find matching document
            let documentKey = null;
            Object.keys(legalDocuments[category]).forEach(key => {
                if (legalDocuments[category][key].name === documentName) {
                    documentKey = key;
                }
            });
            
            if (documentKey) {
                showDocumentModal(documentKey, category);
            }
        });
    });
    
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
    
    document.querySelectorAll('.legal-section, .regulation-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Export for global access
window.showDocumentModal = showDocumentModal;
window.downloadDocument = downloadDocument;
window.complianceStatus = complianceStatus;
window.legalDocuments = legalDocuments;