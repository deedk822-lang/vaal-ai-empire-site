/**
 * WhatsApp POPIA Consent Management Middleware
 * APEX Security Framework v2.0 Compliant
 * 
 * Implements:
 * - POPIA explicit consent requirement
 * - User opt-out handling (24-hour SLA)
 * - Audit trail for all consent changes
 * - Voice note biometric data protection
 */

const crypto = require('crypto');
const logger = require('../utils/logger');

/**
 * POPIA-compliant consent schema for User model
 * APEX: Data minimization + audit trail
 */
const whatsappConsentSchema = {
  whatsapp: {
    // Session messages (user-initiated): always allowed per WhatsApp policy
    session_enabled: { type: Boolean, default: true },
    
    // Business-initiated messages: require explicit POPIA consent
    marketing_consent: {
      granted: { type: Boolean, default: false },
      granted_at: Date,
      granted_via: { 
        type: String, 
        enum: ['whatsapp_opt_in', 'web_form', 'support_agent', 'onboarding'] 
      },
      scope: [{ 
        type: String, 
        enum: ['promotions', 'order_updates', 'account_alerts', 'service_notifications'] 
      }],
      expires_at: Date, // POPIA: Consent time-limited (max 2 years)
      revoked_at: Date,
      revoked_via: {
        type: String,
        enum: ['whatsapp_stop', 'web_form', 'support_agent', 'auto_expired']
      },
      // APEX: Complete audit trail for compliance
      audit_trail: [{
        action: { 
          type: String, 
          enum: ['granted', 'revoked', 'expired', 'renewed', 'scope_changed'] 
        },
        timestamp: { type: Date, default: Date.now },
        ip_address: String,
        user_agent: String,
        reference: String, // e.g., "OPT-IN-MSG-12345"
        performed_by: String // user_id or 'system'
      }]
    },
    
    // Voice note processing: separate consent for biometric data (POPIA)
    voice_processing_consent: {
      granted: { type: Boolean, default: false },
      granted_at: Date,
      purpose: [{ 
        type: String, 
        enum: ['asr_transcription', 'tts_response', 'fraud_analysis', 'quality_improvement'] 
      }],
      retention_days: { type: Number, default: 30, max: 90 }, // POPIA: Minimize retention
      encrypted_storage: { type: Boolean, default: true },
      auto_purge_enabled: { type: Boolean, default: true }
    },
    
    // Last interaction tracking for session window
    last_interaction_at: Date,
    session_window_expires_at: Date // 24 hours from last message
  }
};

/**
 * Check if user has valid POPIA consent for business-initiated messages
 * APEX: Server-side security decision (invariant #4)
 * 
 * @param {Object} user - User document from database
 * @param {string} messageCategory - 'marketing', 'utility', 'authentication'
 * @returns {Object} { allowed: boolean, reason: string, action: string }
 */
function checkBusinessMessageConsent(user, messageCategory) {
  // Session messages (user replied within 24h): always allowed per WhatsApp
  if (messageCategory === 'session') {
    const sessionValid = user.whatsapp?.session_window_expires_at > new Date();
    return {
      allowed: sessionValid,
      reason: sessionValid ? 'session_window_active' : 'session_window_expired',
      action: sessionValid ? 'proceed' : 'request_session_message'
    };
  }
  
  // Utility messages (transactional): allowed with basic consent
  if (messageCategory === 'utility') {
    const hasConsent = user.whatsapp?.marketing_consent?.granted === true;
    return {
      allowed: hasConsent,
      reason: hasConsent ? 'consent_valid' : 'consent_required',
      action: hasConsent ? 'proceed' : 'request_consent'
    };
  }
  
  // Marketing messages: require explicit consent + not expired + not revoked
  const consent = user.whatsapp?.marketing_consent;
  if (!consent) {
    return {
      allowed: false,
      reason: 'consent_not_found',
      action: 'request_consent'
    };
  }
  
  if (consent.revoked_at) {
    return {
      allowed: false,
      reason: 'consent_revoked',
      action: 'honor_opt_out'
    };
  }
  
  if (consent.expires_at && consent.expires_at < new Date()) {
    return {
      allowed: false,
      reason: 'consent_expired',
      action: 'request_renewal'
    };
  }
  
  if (!consent.scope?.includes('promotions')) {
    return {
      allowed: false,
      reason: 'scope_insufficient',
      action: 'request_scope_expansion'
    };
  }
  
  return {
    allowed: true,
    reason: 'consent_valid',
    consent_id: consent._id
  };
}

/**
 * Handle user opt-out (STOP message)
 * POPIA: Must honor within 24 hours
 * APEX: Audit trail + immediate enforcement
 * 
 * @param {string} msisdn - User's phone number
 * @param {Object} context - Request context for audit trail
 */
async function handleOptOut(msisdn, context) {
  try {
    const User = require('../models/User');
    
    const user = await User.findOne({ phone: msisdn });
    if (!user) {
      logger.warn('Opt-out received for unknown user', { 
        msisdn_hash: crypto.createHash('sha256').update(msisdn).digest('hex').substring(0, 16)
      });
      return { success: false, error: 'user_not_found' };
    }
    
    // Revoke consent immediately
    user.whatsapp.marketing_consent.granted = false;
    user.whatsapp.marketing_consent.revoked_at = new Date();
    user.whatsapp.marketing_consent.revoked_via = 'whatsapp_stop';
    
    // APEX: Complete audit trail
    user.whatsapp.marketing_consent.audit_trail.push({
      action: 'revoked',
      timestamp: new Date(),
      ip_address: context.ip,
      user_agent: context.user_agent,
      reference: `OPT-OUT-${Date.now()}`,
      performed_by: 'user'
    });
    
    await user.save();
    
    logger.info('POPIA opt-out processed', {
      user_id: user._id,
      msisdn_hash: crypto.createHash('sha256').update(msisdn).digest('hex').substring(0, 16),
      processed_at: new Date()
    });
    
    return { success: true, user_id: user._id };
  } catch (error) {
    logger.error('Opt-out processing failed', { error: error.message, msisdn: 'REDACTED' });
    return { success: false, error: 'processing_failed' };
  }
}

/**
 * Express middleware: Check consent before sending business-initiated message
 * APEX: Enforces security invariants at trust boundary
 */
async function requireWhatsAppConsent(req, res, next) {
  try {
    const { msisdn, message_category = 'marketing' } = req.body;
    
    if (!msisdn) {
      return res.status(400).json({ error: 'msisdn_required' });
    }
    
    const User = require('../models/User');
    const user = await User.findOne({ phone: msisdn });
    
    if (!user) {
      return res.status(404).json({ error: 'user_not_found' });
    }
    
    const consentCheck = checkBusinessMessageConsent(user, message_category);
    
    if (!consentCheck.allowed) {
      // APEX: Log for compliance audit
      logger.info('WhatsApp message blocked: POPIA consent not valid', {
        user_id: user._id,
        msisdn_hash: crypto.createHash('sha256').update(msisdn).digest('hex').substring(0, 16),
        category: message_category,
        reason: consentCheck.reason,
        timestamp: new Date()
      });
      
      // Send consent request template (pre-approved by Meta)
      // This is allowed even without consent as it's a request, not marketing
      return res.status(403).json({
        error: 'consent_required',
        reason: consentCheck.reason,
        action: consentCheck.action,
        message: 'User must explicitly opt-in before receiving business messages per POPIA'
      });
    }
    
    // Attach consent info to request for downstream use
    req.whatsappConsent = consentCheck;
    next();
    
  } catch (error) {
    logger.error('WhatsApp consent check failed', { error: error.message });
    return res.status(500).json({ error: 'consent_check_failed' });
  }
}

/**
 * Check voice note processing consent
 * APEX: Biometric data requires separate consent per POPIA
 */
function checkVoiceConsent(user, purpose = 'asr_transcription') {
  const voiceConsent = user.whatsapp?.voice_processing_consent;
  
  if (!voiceConsent?.granted) {
    return { allowed: false, reason: 'voice_consent_not_granted' };
  }
  
  if (!voiceConsent.purpose?.includes(purpose)) {
    return { allowed: false, reason: 'purpose_not_authorized' };
  }
  
  return {
    allowed: true,
    encrypted_storage: voiceConsent.encrypted_storage,
    retention_days: voiceConsent.retention_days,
    auto_purge: voiceConsent.auto_purge_enabled
  };
}

module.exports = {
  whatsappConsentSchema,
  checkBusinessMessageConsent,
  handleOptOut,
  requireWhatsAppConsent,
  checkVoiceConsent
};
