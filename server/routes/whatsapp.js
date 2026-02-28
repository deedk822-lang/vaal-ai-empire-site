/**
 * WhatsApp Business API Webhook Routes
 * APEX Security Framework v2.0 Compliant
 * 
 * Routes:
 * - GET /webhooks/whatsapp - Meta verification challenge
 * - POST /webhooks/whatsapp - Incoming webhook events
 * 
 * @module routes/whatsapp
 * @requires express
 * @requires crypto
 * @requires express-rate-limit
 */

const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');

const {
  verifyWhatsAppSignature,
  sanitizeWhatsAppContent,
  verifyWebhookChallenge
} = require('../services/whatsapp-webhook-validator');

const { handleOptOut } = require('../middleware/whatsapp-consent');
const logger = require('../utils/logger');

/**
 * Rate limiter for webhook verification endpoint
 * Prevents DDoS and brute force attacks
 * @type {RateLimit}
 */
const whatsappVerificationLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per window
  message: 'Too many verification attempts',
  standardHeaders: true,
  legacyHeaders: false
});

/**
 * Rate limiter for webhook POST endpoint
 * Higher limit to accommodate Meta's bursty traffic
 * @type {RateLimit}
 */
const whatsappWebhookLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 1000, // 1000 requests per minute
  message: 'Too many webhook requests',
  standardHeaders: true,
  legacyHeaders: false
});

// APEX: Use raw body for signature verification
router.use(express.raw({ type: 'application/json', verify: (req, res, buf) => { req.rawBody = buf; } }));

/**
 * GET /webhooks/whatsapp
 * Meta verification challenge handler
 * Used when configuring webhook in Meta Dashboard
 * 
 * @function
 * @param {express.Request} req - Express request object
 * @param {express.Response} res - Express response object
 * 
 * @example
 * GET /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=xxx&hub.challenge=123
 * Response: 200 "123" (echo of challenge)
 */
router.get('/', whatsappVerificationLimiter, (req, res) => {
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];
  
  logger.info('WhatsApp webhook verification attempt', {
    mode,
    ip: req.ip,
    token_provided: !!token
  });
  
  const response = verifyWebhookChallenge(mode, token, challenge);
  
  if (response) {
    // APEX: Sanitize challenge to prevent reflected XSS
    const sanitizedChallenge = String(response).replace(/[^a-zA-Z0-9]/g, '');
    return res.status(200).type('text/plain').send(sanitizedChallenge);
  }
  
  return res.status(403).type('text/plain').send('Verification failed');
});

/**
 * POST /webhooks/whatsapp
 * Incoming webhook event handler
 * 
 * Security:
 * - Rate limiting
 * - Signature validation
 * - Content sanitization
 * - Async processing for Meta's 20s SLA
 * 
 * @function
 * @param {express.Request} req - Express request object
 * @param {express.Response} res - Express response object
 */
router.post('/', whatsappWebhookLimiter, async (req, res) => {
  const signature = req.headers['x-hub-signature-256'];
  const payload = req.rawBody?.toString('utf-8') || '';
  
  // APEX Invariant #2: Verify auth on EVERY request
  if (!verifyWhatsAppSignature(signature, payload)) {
    logger.warn('WhatsApp webhook signature validation failed', {
      ip: req.ip,
      user_agent: req.headers['user-agent'],
      signature_hash: signature ? 
        crypto.createHash('sha256').update(signature).digest('hex').substring(0, 16) : 
        'missing',
      payload_hash: crypto.createHash('sha256').update(payload).digest('hex').substring(0, 16)
    });
    
    return res.status(401).send('Unauthorized');
  }
  
  try {
    const event = JSON.parse(payload);
    
    // APEX: Process event asynchronously to meet Meta's 20s SLA
    handleWhatsAppEvent(event).catch(error => {
      logger.error('WhatsApp event processing error', { 
        error: error.message,
        event_type: event.object
      });
    });
    
    // Meta requires 200 OK within 20 seconds
    res.status(200).send('EVENT_RECEIVED');
    
  } catch (error) {
    logger.error('WhatsApp webhook parsing error', { error: error.message });
    res.status(200).send('EVENT_RECEIVED');
  }
});

/**
 * Process WhatsApp webhook event
 * Routes messages to appropriate handlers based on type
 * 
 * @async
 * @param {Object} event - Parsed webhook event
 * @param {string} event.object - Event object type (whatsapp_business_account)
 * @param {Array} event.entry - Array of entry objects
 * @returns {Promise<void>}
 */
async function handleWhatsAppEvent(event) {
  if (event.object !== 'whatsapp_business_account') {
    logger.warn('Unexpected webhook object type', { type: event.object });
    return;
  }
  
  for (const entry of event.entry || []) {
    for (const change of entry.changes || []) {
      const value = change.value;
      
      // Handle incoming messages
      if (value.messages) {
        for (const message of value.messages) {
          await handleMessage(message, value);
        }
      }
      
      // Handle message statuses (delivered, read, failed)
      if (value.statuses) {
        for (const status of value.statuses) {
          await handleMessageStatus(status);
        }
      }
    }
  }
}

/**
 * Handle incoming WhatsApp message
 * Routes to appropriate handler based on message type
 * 
 * @async
 * @param {Object} message - Message object from Meta
 * @param {string} message.from - Sender's phone number
 * @param {string} message.type - Message type (text, voice, image, etc.)
 * @param {Object} metadata - Additional message metadata
 * @returns {Promise<void>}
 */
async function handleMessage(message, _metadata) {
  try {
    const msisdn = message.from;
    const messageType = message.type;
    
    // APEX Invariant #3: Sanitize ALL input
    const sanitizedMsisdn = sanitizeWhatsAppContent(msisdn, 'text');
    
    logger.info('WhatsApp message received', {
      msisdn_hash: crypto.createHash('sha256').update(msisdn).digest('hex').substring(0, 16),
      type: messageType,
      timestamp: message.timestamp
    });
    
    // Check for opt-out commands
    if (messageType === 'text') {
      const text = message.text?.body?.toUpperCase().trim() || '';
      if (['STOP', 'UNSUBSCRIBE', 'OPT OUT', 'CANCEL'].includes(text)) {
        await handleOptOut(msisdn, {
          ip: 'webhook',
          user_agent: 'WhatsApp/Meta'
        });
        return;
      }
    }
    
    // Route to appropriate handler based on message type
    switch (messageType) {
      case 'text':
        await handleTextMessage(message, sanitizedMsisdn);
        break;
      case 'audio':
      case 'voice':
        await handleVoiceMessage(message, sanitizedMsisdn);
        break;
      case 'image':
      case 'document':
        await handleMediaMessage(message, sanitizedMsisdn);
        break;
      default:
        logger.info('Unhandled WhatsApp message type', { type: messageType });
    }
    
    // Update user's session window
    await updateSessionWindow(msisdn);
    
  } catch (error) {
    logger.error('Message handling error', { 
      error: error.message,
      message_type: message?.type
    });
  }
}

/**
 * Handle text message
 * Processes text content and routes to NLP pipeline
 * 
 * @async
 * @param {Object} message - Message object
 * @param {string} sanitizedMsisdn - Sanitized sender phone number
 * @returns {Promise<void>}
 * 
 * @see https://github.com/deedk822-lang/vaal-ai-empire-site/issues/XX - MultilingualVoiceAgent integration
 */
async function handleTextMessage(message, sanitizedMsisdn) {
  const text = sanitizeWhatsAppContent(message.text?.body, 'text');
  
  if (!text) {
    logger.warn('Empty text message after sanitization');
    return;
  }
  
  // Route to MultilingualVoiceAgent for NLP processing
  // Implementation tracked in GitHub Issues
  logger.info('Text message processed', { 
    msisdn_hash: sanitizedMsisdn ? 
      crypto.createHash('sha256').update(sanitizedMsisdn).digest('hex').substring(0, 16) : 
      'unknown',
    text_length: text.length
  });
}

/**
 * Handle voice message
 * Checks biometric consent and queues for ASR processing
 * 
 * @async
 * @param {Object} message - Message object
 * @param {string} sanitizedMsisdn - Sanitized sender phone number
 * @returns {Promise<void>}
 * 
 * @see https://github.com/deedk822-lang/vaal-ai-empire-site/issues/XX - ASR pipeline integration
 */
async function handleVoiceMessage(message, _sanitizedMsisdn) {
  try {
    const User = require('../models/User');
    const user = await User.findOne({ phone: message.from });
    
    if (!user) {
      logger.warn('Voice message from unknown user');
      return;
    }
    
    // Check voice processing consent (POPIA requirement for biometric data)
    const { checkVoiceConsent } = require('../middleware/whatsapp-consent');
    const voiceConsent = checkVoiceConsent(user, 'asr_transcription');
    
    if (!voiceConsent.allowed) {
      logger.info('Voice message blocked: consent not granted', {
        user_id: user._id,
        reason: voiceConsent.reason
      });
      return;
    }
    
    // Get media URL (valid for 5 minutes from Meta)
    const mediaUrl = message.audio?.link || message.voice?.link;
    if (!mediaUrl) {
      logger.warn('Voice message without media URL');
      return;
    }
    
    // Validate media URL for security
    const sanitizedUrl = sanitizeWhatsAppContent(mediaUrl, 'media_url');
    if (!sanitizedUrl) {
      logger.warn('Voice message media URL failed validation');
      return;
    }
    
    // Queue for ASR (Automatic Speech Recognition) processing
    // APEX: Must encrypt at rest + auto-purge per consent retention policy
    logger.info('Voice message queued for processing', {
      user_id: user._id,
      retention_days: voiceConsent.retention_days,
      encrypted: voiceConsent.encrypted_storage
    });
    
  } catch (error) {
    logger.error('Voice message handling error', { error: error.message });
  }
}

/**
 * Handle media message (image, document)
 * Processes uploaded files for business workflows
 * 
 * @async
 * @param {Object} message - Message object
 * @param {string} sanitizedMsisdn - Sanitized sender phone number
 * @returns {Promise<void>}
 * 
 * @see https://github.com/deedk822-lang/vaal-ai-empire-site/issues/XX - Document processing pipeline
 */
async function handleMediaMessage(message, _sanitizedMsisdn) {
  // Media processing for business registration, document verification, etc.
  // Implementation tracked in GitHub Issues
  logger.info('Media message received', {
    type: message.type,
    mime_type: message[message.type]?.mime_type
  });
}

/**
 * Handle message status updates
 * Tracks delivery, read, and failure status
 * 
 * @async
 * @param {Object} status - Status object from Meta
 * @param {string} status.id - Message ID
 * @param {string} status.status - Message status (sent, delivered, read, failed)
 * @returns {Promise<void>}
 * 
 * @see https://github.com/deedk822-lang/vaal-ai-empire-site/issues/XX - Message tracking integration
 */
async function handleMessageStatus(status) {
  logger.info('Message status update', {
    message_id: status.id,
    status: status.status,
    timestamp: status.timestamp
  });
  
  // Update message tracking in database
  // Implementation tracked in GitHub Issues
}

/**
 * Update user's session window
 * WhatsApp allows business-initiated messages for 24 hours after user message
 * 
 * @async
 * @param {string} msisdn - User's phone number
 * @returns {Promise<void>}
 */
async function updateSessionWindow(msisdn) {
  try {
    const User = require('../models/User');
    const now = new Date();
    const windowExpires = new Date(now.getTime() + 24 * 60 * 60 * 1000); // 24 hours
    
    await User.updateOne(
      { phone: msisdn },
      {
        $set: {
          'whatsapp.last_interaction_at': now,
          'whatsapp.session_window_expires_at': windowExpires
        }
      }
    );
  } catch (error) {
    logger.error('Session window update failed', { error: error.message });
  }
}

module.exports = router;
