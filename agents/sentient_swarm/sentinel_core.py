#!/usr/bin/env python3
"""
Sentient Financial Sentinel - Core Orchestrator
APEX Security Framework v2.0 Phase 1 Implementation

Components:
- Qwen 3.5-Plus Auto Mode orchestrator
- XRPL v3.1.0 RLUSD/SAV vault + programmatic lending (XLS-66)
- x402 autonomous payment facilitator
- CosyVoice-v3-plus streaming voice I/O
- Full POPIA consent + APEX audit trail

Author: Vaal AI Empire
License: Proprietary
"""

import os
import json
import hashlib  # APEX: For POPIA-compliant user_id hashing
import logging
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# APEX Configuration & Models
# ═══════════════════════════════════════════════════════════════════

class SentinelMode(Enum):
    """Operating modes for the Sentient Financial Sentinel."""
    OBSERVATION = "observation"  # Read-only analysis
    ADVISORY = "advisory"        # Recommendations only
    AUTONOMOUS = "autonomous"    # Full auto with consent
    EMERGENCY = "emergency"      # Emergency protocols


class ConsentScope(Enum):
    """POPIA-compliant consent scopes."""
    VOICE_PROCESSING = "voice_processing"
    FINANCIAL_ANALYSIS = "financial_analysis"
    AUTONOMOUS_TRADING = "autonomous_trading"
    XRPL_SETTLEMENT = "xrpl_settlement"
    DATA_RETENTION = "data_retention"


@dataclass
class POPIAConsent:
    """POPIA-compliant consent record."""
    user_id: str
    scopes: List[ConsentScope]
    granted_at: datetime
    expires_at: datetime
    granted_via: str  # whatsapp, web, api
    audit_trail: List[Dict] = field(default_factory=list)
    revoked: bool = False
    
    def is_valid(self, scope: ConsentScope) -> bool:
        """Check if consent is valid for a given scope."""
        if self.revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return scope in self.scopes


@dataclass
class AuditRecord:
    """APEX-compliant audit record."""
    timestamp: str
    action: str
    user_id: str
    details: Dict[str, Any]
    consent_reference: Optional[str] = None
    model_used: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "user_id": self.user_id,
            "details": self.details,
            "consent_reference": self.consent_reference,
            "model_used": self.model_used,
            "duration_ms": self.duration_ms
        }


# ═══════════════════════════════════════════════════════════════════
# Qwen 3.5-Plus Model Client
# ═══════════════════════════════════════════════════════════════════

class SentinelModelClient:
    """
    Qwen 3.5-Plus client with APEX audit trail.
    Supports Auto Mode for agentic tool calling.
    """
    
    def __init__(self, api_key: str, model: str = "qwen3.5-plus"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._client = None
        self.request_count = 0
        logger.info(f"SentinelModelClient initialized with model: {model}")
    
    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                logger.error("openai package not installed")
                raise
        return self._client
    
    async def chat_with_audit(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        user_id: str = "system",
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request with full APEX audit trail.
        
        Args:
            messages: Conversation messages
            tools: Available tools for Auto Mode
            user_id: User identifier for audit
            consent_ref: Consent reference ID
            
        Returns:
            Response with audit metadata
        """
        start_time = time.time()
        request_id = f"sentinel-{uuid4().hex[:8]}"
        
        logger.info(f"Model request started", extra={
            "request_id": request_id,
            "model": self.model,
            "user_id": user_id,
            "message_count": len(messages)
        })
        
        try:
            # Build request parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,  # Low for financial accuracy
                "max_tokens": 4096
            }
            
            # Enable Auto Mode for tool calling
            if tools:
                params["tools"] = tools
                params["extra_body"] = {"enable_auto": True}
            
            # Make the API call
            response = self.client.chat.completions.create(**params)
            
            duration_ms = int((time.time() - start_time) * 1000)
            self.request_count += 1
            
            # Build audit record
            audit = AuditRecord(
                timestamp=datetime.utcnow().isoformat(),
                action="model_chat",
                user_id=user_id,
                details={
                    "request_id": request_id,
                    "message_count": len(messages),
                    "has_tools": bool(tools),
                    "response_length": len(response.choices[0].message.content or "")
                },
                consent_reference=consent_ref,
                model_used=self.model,
                duration_ms=duration_ms
            )
            
            logger.info(f"Model request completed", extra={
                "request_id": request_id,
                "duration_ms": duration_ms
            })
            
            return {
                "response": response,
                "audit": audit.to_dict(),
                "request_id": request_id
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Model request failed: {e}", extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "error": str(e)
            })
            raise
    
    async def analyze_financial_query(
        self,
        query: str,
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Analyze a financial query using Qwen 3.5-Plus.
        
        Specialized for South African financial context:
        - ZAR currency handling
        - SARS compliance
        - PayFast integration
        - XRPL settlements
        """
        system_prompt = """You are the Sentient Financial Sentinel, an autonomous AI agent for South African SME financial management.

Your capabilities:
1. Financial analysis and tax optimization (SARS compliant)
2. PayFast payment gateway integration (ZAR)
3. XRPL blockchain settlements (RLUSD, SAV vaults)
4. Voice-based interaction in African languages
5. Autonomous trading with user consent

Operating Principles:
- Always verify POPIA consent before processing personal data
- Log all actions for APEX audit trail
- Never expose API keys or sensitive credentials
- Provide ZAR amounts with proper formatting
- Alert on suspicious financial patterns

Current context: South African fintech platform for SMEs.
Currency: South African Rand (ZAR)
Compliance: POPIA, FIC Act, SARS"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {json.dumps(context)}\n\nQuery: {query}"}
        ]
        
        return await self.chat_with_audit(
            messages=messages,
            user_id=user_id
        )


# ═══════════════════════════════════════════════════════════════════
# XRPL Liquidity Engine (XLS-66)
# ═══════════════════════════════════════════════════════════════════

class XRPLLiquidityEngine:
    """
    XRPL v3.1.0 Liquidity Engine with XLS-66 support.
    Handles RLUSD/SAV vault operations and programmatic lending.
    """
    
    def __init__(
        self,
        network_url: Optional[str] = None,
        wallet_seed: Optional[str] = None,
        network_type: str = "testnet"  # testnet or mainnet
    ):
        # Default to XRPL Testnet if no URL provided
        self.network_url = network_url or os.getenv("XRPL_NETWORK_URL", "https://s.altnet.rippletest.net:51234")
        self.network_type = network_type
        self.wallet = None
        self._client = None
        
        if wallet_seed:
            self._init_wallet(wallet_seed)
        
        logger.info(f"XRPL Liquidity Engine initialized: {network_type}")
    
    def _init_wallet(self, seed: str):
        """Initialize XRPL wallet from seed."""
        try:
            from xrpl.wallet import Wallet
            self.wallet = Wallet.from_seed(seed)
            logger.info(f"Wallet initialized: {self.wallet.address}")
        except ImportError:
            logger.warning("xrpl-py not installed - XRPL features disabled")
        except Exception as e:
            logger.error(f"Failed to initialize wallet: {e}")
    
    @property
    def client(self):
        """Lazy-load XRPL client."""
        if self._client is None:
            try:
                from xrpl.clients import JsonRpcClient
                self._client = JsonRpcClient(self.network_url)
            except ImportError:
                logger.warning("xrpl-py not installed")
        return self._client
    
    async def get_account_info(self, address: Optional[str] = None) -> Dict:
        """Get account information from XRPL."""
        if not self.client:
            return {"error": "XRPL client not initialized"}
        
        target_address = address or (self.wallet.address if self.wallet else None)
        if not target_address:
            return {"error": "No address specified"}
        
        try:
            from xrpl.models.requests import AccountInfo
            response = self.client.request(AccountInfo(
                account=target_address,
                ledger_index="validated"
            ))
            return response.result
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {"error": str(e)}
    
    async def create_loan_offer(
        self,
        principal: Decimal,
        interest_bps: int,
        duration_seconds: int,
        collateral_asset: str = "XRP"
    ) -> Dict[str, Any]:
        """
        Create an XLS-66 loan offer on XRPL.
        
        Args:
            principal: Loan principal in XRP or RLUSD
            interest_bps: Interest rate in basis points (100 = 1%)
            duration_seconds: Loan duration in seconds
            collateral_asset: Asset to use as collateral
            
        Returns:
            Transaction result or error
        """
        if not self.wallet or not self.client:
            return {"error": "Wallet or client not initialized"}
        
        try:
            from xrpl.utils import xrp_to_drops
            from xrpl.models.transactions import OfferCreate
            
            # Build loan offer transaction
            # Note: Full XLS-66 implementation requires AMM/Vault objects
            
            logger.info(f"Creating loan offer: {principal} XRP, {interest_bps}bps, {duration_seconds}s")
            
            # Placeholder for XLS-66 vault integration
            # Full implementation would use VaultCreate, VaultDeposit, etc.
            
            return {
                "status": "pending",
                "principal": str(principal),
                "interest_bps": interest_bps,
                "duration_seconds": duration_seconds,
                "collateral_asset": collateral_asset,
                "message": "Loan offer created (simulation - requires XLS-66 amendment)"
            }
            
        except Exception as e:
            logger.error(f"Failed to create loan offer: {e}")
            return {"error": str(e)}
    
    async def get_rlusd_balance(self, address: Optional[str] = None) -> Decimal:
        """Get RLUSD balance for an address."""
        target_address = address or (self.wallet.address if self.wallet else None)
        if not target_address:
            return Decimal("0")
        
        # RLUSD is an issued currency on XRPL
        # Implementation would query trust lines
        return Decimal("0")  # Placeholder
    
    async def process_x402_payment(
        self,
        amount: Decimal,
        currency: str,
        destination: str,
        consent_ref: str
    ) -> Dict[str, Any]:
        """
        Process an x402 autonomous payment.
        
        x402 is an HTTP status code for payment-required responses,
        enabling autonomous payment negotiation.
        
        Args:
            amount: Payment amount
            currency: Currency code (XRP, RLUSD, ZAR)
            destination: Destination address
            consent_ref: Consent reference for audit trail
            
        Returns:
            Payment result
        """
        start_time = time.time()
        
        audit_record = {
            "action": "x402_payment",
            "timestamp": datetime.utcnow().isoformat(),
            "amount": str(amount),
            "currency": currency,
            "destination": destination[:10] + "...",  # Truncate for privacy
            "consent_reference": consent_ref
        }
        
        logger.info(f"Processing x402 payment", extra=audit_record)
        
        try:
            if not self.wallet:
                return {
                    "status": "error",
                    "message": "Wallet not initialized",
                    "audit": audit_record
                }
            
            # For XRP payments
            if currency.upper() == "XRP":
                from xrpl.models.transactions import Payment
                from xrpl.utils import xrp_to_drops
                
                payment = Payment(
                    account=self.wallet.address,
                    destination=destination,
                    amount=xrp_to_drops(float(amount))
                )
                
                # Sign and submit (in production)
                # signed = sign(payment, self.wallet)
                # response = submit(signed, self.client)
                
                audit_record["status"] = "success"
                audit_record["duration_ms"] = int((time.time() - start_time) * 1000)
                
                return {
                    "status": "success",
                    "transaction_type": "Payment",
                    "amount": str(amount),
                    "currency": "XRP",
                    "audit": audit_record,
                    "message": "Payment prepared (requires signing in production)"
                }
            
            # For RLUSD (issued currency)
            elif currency.upper() == "RLUSD":
                audit_record["status"] = "pending"
                return {
                    "status": "pending",
                    "message": "RLUSD payment requires issuer configuration",
                    "audit": audit_record
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported currency: {currency}",
                    "audit": audit_record
                }
                
        except Exception as e:
            logger.error(f"x402 payment failed: {e}")
            audit_record["status"] = "error"
            audit_record["error"] = str(e)
            return {
                "status": "error",
                "message": str(e),
                "audit": audit_record
            }


# ═══════════════════════════════════════════════════════════════════
# Voice Processing with CosyVoice
# ═══════════════════════════════════════════════════════════════════

class CosyVoiceProcessor:
    """
    CosyVoice-v3-plus streaming voice processor.
    Supports African languages with <500ms latency.
    """
    
    SUPPORTED_LANGUAGES = [
        "en-ZA",  # South African English
        "zu-ZA",  # Zulu
        "xh-ZA",  # Xhosa
        "af-ZA",  # Afrikaans
        "st-ZA",  # Sotho
        "tn-ZA",  # Tswana
        "ts-ZA",  # Tsonga
        "ve-ZA",  # Venda
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts"
        logger.info("CosyVoice processor initialized")
    
    async def synthesize(
        self,
        text: str,
        language: str = "en-ZA",
        voice: str = "longxiaochun",
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize speech using CosyVoice-v3-plus.
        
        Args:
            text: Text to synthesize
            language: Target language code
            voice: Voice model to use
            consent_ref: POPIA consent reference
            
        Returns:
            Audio data and metadata
        """
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Language {language} may not be fully supported")
        
        start_time = time.time()
        
        audit = {
            "action": "voice_synthesis",
            "timestamp": datetime.utcnow().isoformat(),
            "language": language,
            "voice": voice,
            "text_length": len(text),
            "consent_reference": consent_ref
        }
        
        logger.info(f"Synthesizing speech: {language}, {len(text)} chars")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "cosyvoice-v3-plus",
                    "input": {
                        "text": text
                    },
                    "parameters": {
                        "voice": voice,
                        "language": language,
                        "format": "mp3",
                        "sample_rate": 16000
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["audio_size_bytes"] = len(audio_data)
                        
                        return {
                            "status": "success",
                            "audio_data": audio_data,
                            "format": "mp3",
                            "duration_ms": duration_ms,
                            "audit": audit
                        }
                    else:
                        error = await response.text()
                        audit["status"] = "error"
                        audit["error"] = error[:200]
                        return {
                            "status": "error",
                            "message": error[:200],
                            "audit": audit
                        }
                        
        except Exception as e:
            logger.error(f"Voice synthesis failed: {e}")
            audit["status"] = "error"
            audit["error"] = str(e)
            return {
                "status": "error",
                "message": str(e),
                "audit": audit
            }
    
    async def transcribe(
        self,
        audio_base64: str,
        language: str = "en-ZA",
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Paraformer (ASR).
        
        Args:
            audio_base64: Base64-encoded audio data
            language: Source language
            consent_ref: POPIA consent reference
            
        Returns:
            Transcription result
        """
        start_time = time.time()
        
        audit = {
            "action": "voice_transcription",
            "timestamp": datetime.utcnow().isoformat(),
            "language": language,
            "audio_size_bytes": len(audio_base64),
            "consent_reference": consent_ref
        }
        
        logger.info(f"Transcribing audio: {language}")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "paraformer-v2",
                    "input": {
                        "audio": audio_base64
                    },
                    "parameters": {
                        "language": language,
                        "format": "mp3"
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/audio/asr",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        text = result.get("output", {}).get("text", "")
                        
                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["text_length"] = len(text)
                        
                        return {
                            "status": "success",
                            "text": text,
                            "language": language,
                            "duration_ms": duration_ms,
                            "audit": audit
                        }
                    else:
                        error = await response.text()
                        audit["status"] = "error"
                        return {
                            "status": "error",
                            "message": error[:200],
                            "audit": audit
                        }
                        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            audit["status"] = "error"
            audit["error"] = str(e)
            return {
                "status": "error",
                "message": str(e),
                "audit": audit
            }


# ═══════════════════════════════════════════════════════════════════
# Consent Manager (POPIA Compliant)
# ═══════════════════════════════════════════════════════════════════

class ConsentManager:
    """
    POPIA-compliant consent management.
    Handles consent grants, revocations, and verification.
    """
    
    def __init__(self):
        self._consents: Dict[str, POPIAConsent] = {}
        self._audit_log: List[Dict] = []
        logger.info("ConsentManager initialized")
    
    def grant_consent(
        self,
        user_id: str,
        scopes: List[ConsentScope],
        granted_via: str,
        duration_days: int = 365
    ) -> POPIAConsent:
        """Grant consent for specified scopes."""
        now = datetime.utcnow()
        
        consent = POPIAConsent(
            user_id=user_id,
            scopes=scopes,
            granted_at=now,
            expires_at=now + timedelta(days=duration_days),
            granted_via=granted_via,
            audit_trail=[{
                "action": "granted",
                "timestamp": now.isoformat(),
                "scopes": [s.value for s in scopes],
                "via": granted_via
            }]
        )
        
        self._consents[user_id] = consent
        
        self._audit_log.append({
            "timestamp": now.isoformat(),
            "action": "consent_granted",
            "user_id": user_id,
            "scopes": [s.value for s in scopes]
        })
        
        logger.info(f"Consent granted for user {user_id}: {[s.value for s in scopes]}")
        return consent
    
    def verify_consent(
        self,
        user_id: str,
        scope: ConsentScope
    ) -> tuple[bool, Optional[str]]:
        """
        Verify consent for a specific scope.
        
        Returns:
            Tuple of (is_valid, reference_id)
        """
        consent = self._consents.get(user_id)
        
        if not consent:
            logger.warning(f"No consent found for user {user_id}")
            return False, None
        
        if not consent.is_valid(scope):
            logger.warning(f"Consent invalid for user {user_id}, scope {scope.value}")
            return False, None
        
        ref = f"consent-{user_id}-{scope.value}-{uuid4().hex[:8]}"
        
        # Add to audit trail
        consent.audit_trail.append({
            "action": "verified",
            "timestamp": datetime.utcnow().isoformat(),
            "scope": scope.value,
            "reference": ref
        })
        
        return True, ref
    
    def revoke_consent(self, user_id: str, reason: str = "user_request") -> bool:
        """Revoke consent for a user."""
        consent = self._consents.get(user_id)
        
        if not consent:
            return False
        
        consent.revoked = True
        consent.audit_trail.append({
            "action": "revoked",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason
        })
        
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "consent_revoked",
            "user_id": user_id,
            "reason": reason
        })
        
        logger.info(f"Consent revoked for user {user_id}: {reason}")
        return True


# ═══════════════════════════════════════════════════════════════════
# Main Sentient Financial Sentinel Orchestrator
# ═══════════════════════════════════════════════════════════════════

class SentientFinancialSentinel:
    """
    Main orchestrator for the Sentient Financial Sentinel.
    
    Coordinates:
    - Qwen 3.5-Plus for intelligent analysis
    - XRPL for blockchain settlements
    - CosyVoice for voice I/O
    - Consent management for POPIA compliance
    """
    
    def __init__(
        self,
        dashscope_api_key: Optional[str] = None,
        xrpl_network_url: Optional[str] = None,
        xrpl_wallet_seed: Optional[str] = None,
        mode: SentinelMode = SentinelMode.ADVISORY
    ):
        self.mode = mode
        
        # Initialize components
        api_key = dashscope_api_key or os.getenv("DASHSCOPE_API_KEY")
        if api_key:
            self.model = SentinelModelClient(api_key)
            self.voice = CosyVoiceProcessor(api_key)
        else:
            self.model = None
            self.voice = None
            logger.warning("DASHSCOPE_API_KEY not set - AI features disabled")
        
        network_url = xrpl_network_url or os.getenv("XRPL_NETWORK_URL", "https://s.altnet.rippletest.net:51234")
        wallet_seed = xrpl_wallet_seed or os.getenv("XRPL_AGENT_SEED")
        self.xrpl = XRPLLiquidityEngine(network_url, wallet_seed)
        
        self.consent_manager = ConsentManager()
        
        self._audit_log: List[Dict] = []
        
        logger.info(f"SentientFinancialSentinel initialized in {mode.value} mode")
    
    async def process_voice_command(
        self,
        audio_base64: str,
        user_id: str,
        language: str = "en-ZA",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a voice command through the full pipeline.
        
        Pipeline:
        1. Verify consent for voice processing
        2. Transcribe audio
        3. Analyze with Qwen 3.5-Plus
        4. Execute any required actions
        5. Synthesize response
        
        Args:
            audio_base64: Base64-encoded audio
            user_id: User identifier
            language: Audio language
            context: Additional context
            
        Returns:
            Response with audio and metadata
        """
        start_time = time.time()
        
        # APEX Section 0 & 7: POPIA Consent Logging (no PII in logs)
        request_id = f"voice-{uuid4().hex[:8]}"
        logger.info("POPIA consent check", extra={
            "request_id": request_id,
            "user_id_hash": hashlib.sha256(user_id.encode()).hexdigest()[:16],
            "consent_scope": ConsentScope.VOICE_PROCESSING.value,
            "language": language
        })
        
        # Step 1: Verify consent
        has_consent, consent_ref = self.consent_manager.verify_consent(
            user_id, ConsentScope.VOICE_PROCESSING
        )
        
        if not has_consent:
            return {
                "status": "error",
                "message": "Voice processing consent required",
                "action_required": "grant_consent"
            }
        
        # Step 2: Transcribe
        if not self.voice:
            return {
                "status": "error",
                "message": "Voice processing not available"
            }
        
        transcription = await self.voice.transcribe(
            audio_base64, language, consent_ref
        )
        
        if transcription["status"] != "success":
            return transcription
        
        query = transcription["text"]
        
        # Step 3: Analyze with model
        if not self.model:
            return {
                "status": "error",
                "message": "AI model not available",
                "transcription": query
            }
        
        analysis = await self.model.analyze_financial_query(
            query=query,
            context=context or {},
            user_id=user_id
        )
        
        response_text = analysis["response"].choices[0].message.content
        
        # Step 4: Check for action requirements
        # TODO: Parse tool calls from response if autonomous mode
        
        # Step 5: Synthesize response
        synthesis = await self.voice.synthesize(
            text=response_text,
            language=language,
            consent_ref=consent_ref
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "success",
            "transcription": query,
            "response_text": response_text,
            "audio_response": synthesis.get("audio_data"),
            "duration_ms": duration_ms,
            "consent_reference": consent_ref,
            "audit": {
                "action": "voice_command_processed",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "language": language,
                "duration_ms": duration_ms
            }
        }
    
    async def process_text_query(
        self,
        query: str,
        user_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a text-based financial query.
        
        Args:
            query: User query text
            user_id: User identifier
            context: Additional context
            
        Returns:
            Analysis response
        """
        # Verify consent
        has_consent, consent_ref = self.consent_manager.verify_consent(
            user_id, ConsentScope.FINANCIAL_ANALYSIS
        )
        
        if not has_consent:
            return {
                "status": "error",
                "message": "Financial analysis consent required",
                "action_required": "grant_consent"
            }
        
        if not self.model:
            return {
                "status": "error",
                "message": "AI model not available"
            }
        
        return await self.model.analyze_financial_query(
            query=query,
            context=context or {},
            user_id=user_id
        )
    
    async def execute_settlement(
        self,
        amount: Decimal,
        currency: str,
        destination: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute an XRPL settlement.
        
        Args:
            amount: Settlement amount
            currency: Currency code
            destination: Destination address
            user_id: User identifier
            
        Returns:
            Settlement result
        """
        # Verify consent for XRPL settlement
        has_consent, consent_ref = self.consent_manager.verify_consent(
            user_id, ConsentScope.XRPL_SETTLEMENT
        )
        
        if not has_consent:
            return {
                "status": "error",
                "message": "XRPL settlement consent required",
                "action_required": "grant_consent"
            }
        
        return await self.xrpl.process_x402_payment(
            amount=amount,
            currency=currency,
            destination=destination,
            consent_ref=consent_ref
        )
    
    def grant_user_consent(
        self,
        user_id: str,
        scopes: List[str],
        via: str = "api"
    ) -> Dict[str, Any]:
        """
        Grant consent for a user.
        
        Args:
            user_id: User identifier
            scopes: List of scope strings
            via: Consent grant method
            
        Returns:
            Consent details
        """
        scope_enums = []
        for s in scopes:
            try:
                scope_enums.append(ConsentScope(s))
            except ValueError:
                logger.warning(f"Invalid scope: {s}")
        
        if not scope_enums:
            return {
                "status": "error",
                "message": "No valid scopes provided"
            }
        
        consent = self.consent_manager.grant_consent(
            user_id=user_id,
            scopes=scope_enums,
            granted_via=via
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "scopes": [s.value for s in consent.scopes],
            "expires_at": consent.expires_at.isoformat()
        }


# ═══════════════════════════════════════════════════════════════════
# Module Exports
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    "SentientFinancialSentinel",
    "SentinelMode",
    "ConsentScope",
    "POPIAConsent",
    "SentinelModelClient",
    "XRPLLiquidityEngine",
    "CosyVoiceProcessor",
    "ConsentManager",
]


# ═══════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sentient Financial Sentinel")
    parser.add_argument("--query", type=str, help="Text query to process")
    parser.add_argument("--mode", type=str, default="advisory", 
                       choices=["observation", "advisory", "autonomous"])
    args = parser.parse_args()
    
    sentinel = SentientFinancialSentinel(mode=SentinelMode(args.mode))
    
    # Grant test consent
    sentinel.grant_user_consent(
        user_id="test-user",
        scopes=["financial_analysis", "voice_processing"],
        via="cli"
    )
    
    if args.query:
        result = await sentinel.process_text_query(
            query=args.query,
            user_id="test-user",
            context={"source": "cli"}
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Sentient Financial Sentinel ready. Use --query to test.")


if __name__ == "__main__":
    asyncio.run(main())
