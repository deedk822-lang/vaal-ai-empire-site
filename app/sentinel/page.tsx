'use client';

/**
 * Sentient Financial Sentinel Dashboard
 * Next.js 15 App Router - Real-time Thinking Visualization
 * APEX Security Framework v2.0 Phase 1
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Types
interface ThinkingStep {
  id: string;
  type: 'analysis' | 'reasoning' | 'action' | 'settlement';
  content: string;
  timestamp: Date;
  status: 'pending' | 'active' | 'complete' | 'error';
}

interface VaultBalance {
  currency: string;
  available: number;
  locked: number;
  pending: number;
}

interface ConsentStatus {
  granted: boolean;
  scopes: string[];
  expiresAt: string;
}

interface SentinelState {
  mode: 'observation' | 'advisory' | 'autonomous' | 'emergency';
  thinking: ThinkingStep[];
  vaultBalances: VaultBalance[];
  consent: ConsentStatus | null;
  lastActivity: Date | null;
  error: string | null;
}

// Animated thinking component
function ThinkingVisualization({ steps }: { steps: ThinkingStep[] }) {
  return (
    <div className="thinking-container space-y-3">
      <AnimatePresence mode="popLayout">
        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ delay: index * 0.1 }}
            className={`thinking-step p-4 rounded-lg border-l-4 ${
              step.status === 'active' 
                ? 'border-blue-500 bg-blue-50' 
                : step.status === 'complete'
                ? 'border-green-500 bg-green-50'
                : step.status === 'error'
                ? 'border-red-500 bg-red-50'
                : 'border-gray-300 bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-gray-500">
                {step.timestamp.toLocaleTimeString()}
              </span>
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-600">
                {step.type}
              </span>
              {step.status === 'active' && (
                <motion.span
                  animate={{ opacity: [1, 0.5, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="ml-auto"
                >
                  ●
                </motion.span>
              )}
            </div>
            <p className="mt-2 text-sm text-gray-800">{step.content}</p>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// Vault balance display
function VaultDisplay({ balances }: { balances: VaultBalance[] }) {
  return (
    <div className="vault-container bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 text-white">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        XRPL Vault
      </h3>
      
      <div className="space-y-4">
        {balances.map((balance) => (
          <div key={balance.currency} className="vault-balance">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xl">
                {balance.available.toLocaleString()} {balance.currency}
              </span>
              <span className="text-xs text-slate-400">Available</span>
            </div>
            {(balance.locked > 0 || balance.pending > 0) && (
              <div className="mt-2 text-xs text-slate-400">
                {balance.locked > 0 && (
                  <span className="mr-3">🔒 {balance.locked.toLocaleString()} locked</span>
                )}
                {balance.pending > 0 && (
                  <span>⏳ {balance.pending.toLocaleString()} pending</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Consent manager
function ConsentManager({ 
  consent, 
  onGrant, 
  onRevoke 
}: { 
  consent: ConsentStatus | null;
  onGrant: (scopes: string[]) => void;
  onRevoke: () => void;
}) {
  const availableScopes = [
    { id: 'voice_processing', label: 'Voice Processing', description: 'Process voice commands' },
    { id: 'financial_analysis', label: 'Financial Analysis', description: 'Analyze your financial data' },
    { id: 'autonomous_trading', label: 'Autonomous Trading', description: 'Execute trades on your behalf' },
    { id: 'xrpl_settlement', label: 'XRPL Settlement', description: 'Process blockchain payments' },
  ];

  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);

  if (consent?.granted) {
    return (
      <div className="consent-manager bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-semibold text-green-800">Consent Active</h4>
            <p className="text-sm text-green-600 mt-1">
              Expires: {new Date(consent.expiresAt).toLocaleDateString()}
            </p>
          </div>
          <button
            onClick={onRevoke}
            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
          >
            Revoke
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {consent.scopes.map((scope) => (
            <span key={scope} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
              {scope}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="consent-manager bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <h4 className="font-semibold text-yellow-800 mb-3">Grant Consent (POPIA)</h4>
      
      <div className="space-y-2 mb-4">
        {availableScopes.map((scope) => (
          <label key={scope.id} className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedScopes.includes(scope.id)}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedScopes([...selectedScopes, scope.id]);
                } else {
                  setSelectedScopes(selectedScopes.filter((s) => s !== scope.id));
                }
              }}
              className="mt-1"
            />
            <div>
              <span className="font-medium text-gray-800">{scope.label}</span>
              <p className="text-xs text-gray-500">{scope.description}</p>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={() => selectedScopes.length > 0 && onGrant(selectedScopes)}
        disabled={selectedScopes.length === 0}
        className="w-full py-2 bg-yellow-500 text-white rounded font-medium hover:bg-yellow-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Grant Consent
      </button>
    </div>
  );
}

// Mode selector
function ModeSelector({ 
  mode, 
  onChange 
}: { 
  mode: SentinelMode['mode'];
  onChange: (mode: SentinelState['mode']) => void;
}) {
  const modes: Array<{ id: SentinelState['mode']; label: string; color: string }> = [
    { id: 'observation', label: 'Observation', color: 'bg-gray-100 text-gray-700' },
    { id: 'advisory', label: 'Advisory', color: 'bg-blue-100 text-blue-700' },
    { id: 'autonomous', label: 'Autonomous', color: 'bg-purple-100 text-purple-700' },
    { id: 'emergency', label: 'Emergency', color: 'bg-red-100 text-red-700' },
  ];

  return (
    <div className="flex gap-2">
      {modes.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition ${
            mode === m.id ? m.color : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

// Main dashboard component
export default function SentinelDashboard() {
  const [state, setState] = useState<SentinelState>({
    mode: 'observation',
    thinking: [],
    vaultBalances: [
      { currency: 'XRP', available: 1250.5, locked: 100, pending: 50 },
      { currency: 'RLUSD', available: 5000, locked: 0, pending: 0 },
    ],
    consent: null,
    lastActivity: null,
    error: null,
  });

  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Add thinking step
  const addThinkingStep = useCallback((
    type: ThinkingStep['type'],
    content: string,
    status: ThinkingStep['status'] = 'active'
  ) => {
    const step: ThinkingStep = {
      id: crypto.randomUUID(),
      type,
      content,
      timestamp: new Date(),
      status,
    };
    
    setState((prev) => ({
      ...prev,
      thinking: [...prev.thinking.slice(-9), step], // Keep last 10
      lastActivity: new Date(),
    }));
    
    return step.id;
  }, []);

  // Update thinking step status
  const updateThinkingStep = useCallback((id: string, status: ThinkingStep['status']) => {
    setState((prev) => ({
      ...prev,
      thinking: prev.thinking.map((step) =>
        step.id === id ? { ...step, status } : step
      ),
    }));
  }, []);

  // Process query
  const processQuery = async () => {
    if (!input.trim() || isProcessing) return;

    setIsProcessing(true);
    setInput('');

    // Simulate processing flow
    const analysisId = addThinkingStep('analysis', `Analyzing: "${input.slice(0, 50)}..."`);
    
    await new Promise((r) => setTimeout(r, 800));
    updateThinkingStep(analysisId, 'complete');

    const reasoningId = addThinkingStep('reasoning', 'Processing financial context...');
    
    await new Promise((r) => setTimeout(r, 600));
    updateThinkingStep(reasoningId, 'complete');

    // In autonomous mode, simulate action
    if (state.mode === 'autonomous') {
      const actionId = addThinkingStep('action', 'Executing autonomous action...');
      
      await new Promise((r) => setTimeout(r, 500));
      updateThinkingStep(actionId, 'complete');
    }

    addThinkingStep('analysis', 'Response: Financial analysis complete. Your portfolio is performing within expected parameters.', 'complete');
    
    setIsProcessing(false);
  };

  // Grant consent
  const handleGrantConsent = (scopes: string[]) => {
    const expiresAt = new Date();
    expiresAt.setFullYear(expiresAt.getFullYear() + 1);

    setState((prev) => ({
      ...prev,
      consent: {
        granted: true,
        scopes,
        expiresAt: expiresAt.toISOString(),
      },
    }));

    addThinkingStep('analysis', `Consent granted for: ${scopes.join(', ')}`, 'complete');
  };

  // Revoke consent
  const handleRevokeConsent = () => {
    setState((prev) => ({
      ...prev,
      consent: null,
    }));

    addThinkingStep('analysis', 'Consent revoked', 'complete');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Sentient Financial Sentinel</h1>
                <p className="text-xs text-gray-500">APEX v2.0 • Qwen 3.5-Plus • XRPL</p>
              </div>
            </div>
            
            <ModeSelector 
              mode={state.mode} 
              onChange={(mode) => setState((prev) => ({ ...prev, mode }))}
            />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Thinking visualization */}
          <div className="lg:col-span-2 space-y-4">
            {/* Input */}
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && processQuery()}
                  placeholder="Ask about your finances, investments, or XRPL settlements..."
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isProcessing}
                />
                <button
                  onClick={processQuery}
                  disabled={isProcessing || !input.trim()}
                  className="px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? 'Processing...' : 'Send'}
                </button>
              </div>
              
              {/* Voice input button */}
              <div className="mt-3 flex gap-2">
                <button className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg text-gray-700 hover:bg-gray-200 transition">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  Voice Input
                </button>
                <select className="px-4 py-2 bg-gray-100 rounded-lg text-gray-700 border-0 focus:ring-2 focus:ring-blue-500">
                  <option value="en-ZA">English (SA)</option>
                  <option value="zu-ZA">Zulu</option>
                  <option value="xh-ZA">Xhosa</option>
                  <option value="af-ZA">Afrikaans</option>
                </select>
              </div>
            </div>

            {/* Thinking visualization */}
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <motion.span
                  animate={{ rotate: isProcessing ? 360 : 0 }}
                  transition={{ repeat: isProcessing ? Infinity : 0, duration: 2, ease: 'linear' }}
                >
                  ⚙️
                </motion.span>
                Real-time Thinking
              </h3>
              
              {state.thinking.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <p>No activity yet</p>
                  <p className="text-sm mt-1">Ask a question to see the thinking process</p>
                </div>
              ) : (
                <ThinkingVisualization steps={state.thinking} />
              )}
            </div>
          </div>

          {/* Right column - Vault & Consent */}
          <div className="space-y-4">
            <VaultDisplay balances={state.vaultBalances} />
            <ConsentManager
              consent={state.consent}
              onGrant={handleGrantConsent}
              onRevoke={handleRevokeConsent}
            />
            
            {/* Status */}
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <h3 className="font-semibold text-gray-800 mb-3">System Status</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Mode</span>
                  <span className="font-medium capitalize">{state.mode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Model</span>
                  <span className="font-medium">Qwen 3.5-Plus</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Network</span>
                  <span className="font-medium">XRPL Testnet</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Last Activity</span>
                  <span className="font-medium">
                    {state.lastActivity 
                      ? state.lastActivity.toLocaleTimeString() 
                      : 'None'}
                  </span>
                </div>
              </div>
            </div>

            {/* APEX Compliance */}
            <div className="bg-slate-800 rounded-xl p-4 text-white">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                🛡️ APEX Compliance
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  <span>POPIA Consent Tracking</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  <span>Audit Trail Active</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  <span>No PII Logging</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  <span>XRPL Settlement Verified</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>🇿🇦 Built in the Vaal. Built for Africa.</span>
            <span>APEX Security Framework v2.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
