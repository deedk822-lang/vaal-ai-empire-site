/**
 * WhatsApp Business API Webhook Routes
 * APEX Security Framework v2.0 Compliant
 * 
 * Routes:
 * - GET /webhooks/whatsapp - Meta verification challenge
 * - POST /webhooks/whatsapp - Incoming webhook events
 */

const express = require('express');
const router = express.Router();
const crypto = require('crypto');

const {
  verifyWhatsAppSignature,
  sanitizeWhatsAppContent,
  verifyWebhookChallenge
} = require('../services/whatsapp-webhook-validator');

const { handleOptOut } = require('../middleware/whatsapp-consent');
const logger = require('../utils/logger');

// APEX: Use raw body for signature verification
router.use(express.raw({ type: 'application/json', verify: (req, res, buf) => { req.rawBody = buf; } }));

/**
 * GET /webhooks/whatsapp
 * Meta verification challenge handler
 * Used when configuring webhook in Meta Dashboard
 */
router.get('/', (req, res) => {
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];
  
  logger.info('WhatsApp webhook verification attempt', {
    mode,
    ip: req.ip,
    // APEX: Don't log the actual token
    token_provided: !!token
  });
  
  const response = verifyWebhookChallenge(mode, token, challenge);
  
  if (response) {
    return res.status(200).send(response);
  }
  
  return res.status(403).send('Verification failed');
});

/**
 * POST /webhooks/whatsapp
 * Incoming webhook event handler
 * APEX: Signature validation + sanitization + processing
 */
router.post('/', async (req, res) => {
  const signature = req.headers['x-hub-signature-256'];
  const payload = req.rawBody?.toString('utf-8') || '';
  
  // APEX Invariant #2: Verify auth on EVERY request
  if (!verifyWhatsAppSignature(signature, payload)) {
    logger.warn('WhatsApp webhook signature validation failed', {
      ip: req.ip,
      user_agent: req.headers['user-agent'],
      // APEX Invariant #1: Log hash only, never raw signature or payload
      signature_hash: signature ? 
        crypto.createHash('sha256').update(signature).digest('hex').substring(0, 16) : 
        'missing',
      payload_hash: crypto.createHash('sha256').update(payload).digest('hex').substring(0, 16)
    });
    
    // APEX: Return 401 but don't expose internal error details
    return res.status(401).send('Unauthorized');
  }
  
  try {
    // Parse validated payload
    const event = JSON.parse(payload);
    
    // APEX: Process event asynchronously to meet Meta's 20s SLA
    handleWhatsAppEvent(event).catch(error => {
      logger.error('WhatsApp event processing error', { 
        error: error.message,
        // APEX: Don't log full event (contains PII)
        event_type: event.object
      });
    });
    
    // Meta requires 200 OK within 20 seconds
    res.status(200).send('EVENT_RECEIVED');
    
  } catch (error) {
    logger.error('WhatsApp webhook parsing error', { error: error.message });
    // Still return 200 to prevent Meta retries for unparseable payloads
    res.status(200).send('EVENT_RECEIVED');
  }
});

/**
 * Process WhatsApp webhook event
 * APEX: Sanitize all content before processing
 * 
 * @param {Object} event - Parsed webhook event
 */
async function handleWhatsAppEvent(event) {
  if (event.object !== 'whatsapp_business_account') {
    logger.warn('Unexpected webhook object type', { type: event.object });
    return;
  }
  
  for (const entry of event.entry || []) {
    for (const change of entry.changes || []) {
      const value = change.value;
      
      // Handle messages
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
 * APEX: Input sanitization + consent checking
 */
async function handleMessage(message, metadata) {
  try {
    const msisdn = message.from; // Sender's phone number
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
 */
async function handleTextMessage(message, sanitizedMsisdn) {
  const text = sanitizeWhatsAppContent(message.text?.body, 'text');
  
  if (!text) {
    logger.warn('Empty text message after sanitization');
    return;
  }
  
  // TODO: Route to MultilingualVoiceAgent for processing
  logger.info('Text message processed', { 
    msisdn_hash: sanitizedMsisdn ? 
      crypto.createHash('sha256').update(sanitizedMsisdn).digest('hex').substring(0, 16) : 
      'unknown',
    text_length: text.length
  });
}

/**
 * Handle voice message
 * APEX: Check biometric consent + encrypt at rest
 */
async function handleVoiceMessage(message, sanitizedMsisdn) {
  try {
    const User = require('../models/User');
    const user = await User.findOne({ phone: message.from });
    
    if (!user) {
      logger.warn('Voice message from unknown user');
      return;
    }
    
    // Check voice processing consent
    const { checkVoiceConsent } = require('../middleware/whatsapp-consent');
    const voiceConsent = checkVoiceConsent(user, 'asr_transcription');
    
    if (!voiceConsent.allowed) {
      logger.info('Voice message blocked: consent not granted', {
        user_id: user._id,
        reason: voiceConsent.reason
      });
      return;
    }
    
    // Get media URL (valid for 5 minutes)
    const mediaUrl = message.audio?.link || message.voice?.link;
    if (!mediaUrl) {
      logger.warn('Voice message without media URL');
      return;
    }
    
    // Validate media URL
    const sanitizedUrl = sanitizeWhatsAppContent(mediaUrl, 'media_url');
    if (!sanitizedUrl) {
      logger.warn('Voice message media URL failed validation');
      return;
    }
    
    // TODO: Download, decrypt, process via ASR pipeline
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
 */
async function handleMediaMessage(message, sanitizedMsisdn) {
  // TODO: Implement document processing for business registration, etc.
  logger.info('Media message received', {
    type: message.type,
    mime_type: message[message.type]?.mime_type
  });
}

/**
 * Handle message status updates
 */
async function handleMessageStatus(status) {
  logger.info('Message status update', {
    message_id: status.id,
    status: status.status,
    timestamp: status.timestamp
  });
  
  // TODO: Update message tracking in database
}

/**
 * Update user's session window (24 hours from last message)
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
