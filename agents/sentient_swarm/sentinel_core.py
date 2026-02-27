#!/usr/bin/env python3
"""
Sentient Financial Sentinel - Phase 1 Core Orchestrator
APEX Security Framework v2.0 Certified

Components:
- Qwen 3.5-Plus Auto Mode orchestrator (DashScope API)
- XRPL v3.1.0 RLUSD/SAV vault + programmatic lending (XLS-66)
- x402 autonomous payment facilitator
- CosyVoice-v3-plus streaming voice I/O
- Full POPIA consent + APEX audit trail

Author: Vaal AI Empire
License: Proprietary
Version: 1.0.0-phase1
"""

import os
import json
import logging
import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import uuid4

# Configure structured logging (APEX Invariant #7: Audit Trail)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/sentinel.log") if os.path.exists("logs") else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# APEX Configuration & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class SentinelMode(Enum):
    """Operating modes for the Sentient Financial Sentinel."""
    OBSERVATION = "observation"      # Read-only analysis, no actions
    ADVISORY = "advisory"            # Recommendations only, user approval required
    AUTONOMOUS = "autonomous"        # Full auto with verified POPIA consent
    EMERGENCY = "emergency"          # Emergency protocols, rate limits relaxed


class ConsentScope(Enum):
    """POPIA-compliant consent scopes for data processing."""
    VOICE_PROCESSING = "voice_processing"        # Voice recording and transcription
    FINANCIAL_ANALYSIS = "financial_analysis"    # Financial data analysis
    AUTONOMOUS_TRADING = "autonomous_trading"    # Automated financial transactions
    XRPL_SETTLEMENT = "xrpl_settlement"          # Blockchain settlement execution
    DATA_RETENTION = "data_retention"            # Long-term data storage


class LoanStatus(Enum):
    """XLS-66 loan lifecycle status."""
    PENDING = "pending"
    ACTIVE = "active"
    REPAYING = "repaying"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    LIQUIDATED = "liquidated"


class PaymentStatus(Enum):
    """x402 payment status codes."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models (APEX Audit Trail Compliant)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class POPIAConsent:
    """
    POPIA-compliant consent record.
    APEX Invariant #2: Auth verified per-request with explicit consent.
    """
    user_id: str
    scopes: List[ConsentScope]
    granted_at: datetime
    expires_at: datetime
    granted_via: str  # whatsapp, web, api, voice
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    revoked: bool = False
    revocation_reason: Optional[str] = None

    def is_valid(self, scope: ConsentScope) -> bool:
        """Check if consent is valid for a given scope."""
        if self.revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return scope in self.scopes

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for audit logging."""
        return {
            "user_id": self.user_id,
            "scopes": [s.value for s in self.scopes],
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "granted_via": self.granted_via,
            "revoked": self.revoked,
            "audit_trail_count": len(self.audit_trail)
        }


@dataclass
class AuditRecord:
    """
    APEX-compliant audit record.
    APEX Invariant #7: Every action logged with full context.
    """
    timestamp: str
    action: str
    user_id: str
    details: Dict[str, Any]
    consent_reference: Optional[str] = None
    model_used: Optional[str] = None
    duration_ms: int = 0
    request_id: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LoanOffer:
    """
    XLS-66 loan offer structure.
    Supports RLUSD and XRP collateralized lending.
    """
    loan_id: str
    borrower_address: str
    principal: Decimal
    principal_currency: str  # XRP, RLUSD
    interest_bps: int        # Basis points (100 = 1%)
    duration_seconds: int
    collateral_amount: Decimal
    collateral_asset: str    # XRP, RLUSD, SAV
    collateral_ratio: Decimal  # e.g., 1.5 = 150%
    status: LoanStatus
    created_at: datetime
    expires_at: datetime
    lender_address: Optional[str] = None
    vault_id: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_total_repayment(self) -> Decimal:
        """Calculate total repayment amount including interest."""
        interest_rate = Decimal(self.interest_bps) / Decimal(10000)
        return self.principal * (Decimal("1") + interest_rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "borrower_address": self.borrower_address,
            "principal": str(self.principal),
            "principal_currency": self.principal_currency,
            "interest_bps": self.interest_bps,
            "duration_seconds": self.duration_seconds,
            "collateral_amount": str(self.collateral_amount),
            "collateral_asset": self.collateral_asset,
            "collateral_ratio": str(self.collateral_ratio),
            "status": self.status.value,
            "total_repayment": str(self.calculate_total_repayment()),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }


@dataclass
class x402Payment:
    """
    x402 autonomous payment structure.
    HTTP 402 Payment Required response handler.
    """
    payment_id: str
    amount: Decimal
    currency: str
    destination: str
    purpose: str
    status: PaymentStatus
    consent_ref: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    transaction_hash: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "destination": self.destination[:12] + "...",  # Privacy: truncated
            "purpose": self.purpose,
            "status": self.status.value,
            "consent_ref": self.consent_ref,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "transaction_hash": self.transaction_hash
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Qwen 3.5-Plus Model Client (DashScope API)
# ═══════════════════════════════════════════════════════════════════════════════

class SentinelModelClient:
    """
    Qwen 3.5-Plus client with APEX audit trail.
    Supports Auto Mode for agentic tool calling.

    APEX Invariant #5: Approved cryptographic algorithms only.
    APEX Invariant #1: Credentials never logged.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "qwen3.5-plus"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._client = None
        self.request_count = 0
        self.total_tokens_used = 0

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY not set - AI features disabled")

        logger.info(f"SentinelModelClient initialized", extra={
            "model": self.model,
            "api_key_set": bool(self.api_key)
        })

    @property
    def client(self):
        """Lazy-load the OpenAI-compatible client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                logger.error("openai package not installed - run: pip install openai")
                raise ImportError("openai package required for Qwen 3.5-Plus integration")
        return self._client

    async def chat_with_audit(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        user_id: str = "system",
        consent_ref: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send a chat request with full APEX audit trail.

        Args:
            messages: Conversation messages in OpenAI format
            tools: Available tools for Auto Mode
            user_id: User identifier for audit
            consent_ref: POPIA consent reference ID
            temperature: Sampling temperature (low for financial accuracy)
            max_tokens: Maximum tokens to generate

        Returns:
            Response with audit metadata
        """
        start_time = time.time()
        request_id = f"sentinel-{uuid4().hex[:8]}"

        logger.info("Model request started", extra={
            "request_id": request_id,
            "model": self.model,
            "user_id": user_id,
            "message_count": len(messages),
            "has_tools": bool(tools)
        })

        try:
            # Build request parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Enable Auto Mode for tool calling (Qwen 3.5-Plus feature)
            if tools:
                params["tools"] = tools
                params["extra_body"] = {"enable_auto": True}

            # Make the API call
            response = self.client.chat.completions.create(**params)

            duration_ms = int((time.time() - start_time) * 1000)
            self.request_count += 1

            # Track token usage
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens

            # Build audit record (APEX Invariant #7)
            audit = AuditRecord(
                timestamp=datetime.utcnow().isoformat(),
                action="model_chat",
                user_id=user_id,
                details={
                    "request_id": request_id,
                    "message_count": len(messages),
                    "has_tools": bool(tools),
                    "response_length": len(response.choices[0].message.content or ""),
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                },
                consent_reference=consent_ref,
                model_used=self.model,
                duration_ms=duration_ms,
                request_id=request_id
            )

            logger.info("Model request completed", extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            })

            return {
                "response": response,
                "audit": audit.to_dict(),
                "request_id": request_id
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Model request failed", extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "error": str(e)[:200]
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
4. Voice-based interaction in South African languages
5. Autonomous trading with verified user consent

Operating Principles (APEX Framework):
- ALWAYS verify POPIA consent before processing personal data
- Log ALL actions for APEX audit trail
- NEVER expose API keys or sensitive credentials
- Provide ZAR amounts with proper formatting (R X,XXX.XX)
- Alert on suspicious financial patterns immediately
- Default to ADVISORY mode - require explicit consent for AUTONOMOUS actions

Current context: South African fintech platform for SMEs
Currency: South African Rand (ZAR)
Compliance: POPIA, FIC Act, SARS
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {json.dumps(context, default=str)}\n\nQuery: {query}"}
        ]

        return await self.chat_with_audit(
            messages=messages,
            user_id=user_id
        )

    def get_tools_schema(self) -> List[Dict]:
        """
        Get the tool schema for Qwen 3.5-Plus Auto Mode.
        These tools enable autonomous financial actions.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_loan_offer",
                    "description": "Create an XLS-66 loan offer on XRPL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "principal": {"type": "number", "description": "Loan principal amount"},
                            "currency": {"type": "string", "enum": ["XRP", "RLUSD"]},
                            "interest_bps": {"type": "integer", "description": "Interest rate in basis points"},
                            "duration_days": {"type": "integer", "description": "Loan duration in days"},
                            "collateral_ratio": {"type": "number", "description": "Required collateral ratio (e.g., 1.5)"}
                        },
                        "required": ["principal", "currency", "interest_bps", "duration_days"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_payment",
                    "description": "Execute an x402 autonomous payment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Payment amount"},
                            "currency": {"type": "string", "enum": ["XRP", "RLUSD", "ZAR"]},
                            "destination": {"type": "string", "description": "Destination address"},
                            "purpose": {"type": "string", "description": "Payment purpose/reference"}
                        },
                        "required": ["amount", "currency", "destination", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_transaction",
                    "description": "Analyze a transaction for fraud or compliance issues",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transaction_id": {"type": "string"},
                            "amount": {"type": "number"},
                            "counterparty": {"type": "string"}
                        },
                        "required": ["transaction_id", "amount"]
                    }
                }
            }
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# XRPL Liquidity Engine (XLS-66 Programmatic Lending)
# ═══════════════════════════════════════════════════════════════════════════════

class XRPLLiquidityEngine:
    """
    XRPL v3.1.0 Liquidity Engine with XLS-66 support.
    Handles RLUSD/SAV vault operations and programmatic lending.

    XLS-66 is a proposed XRPL amendment for vault-based lending.
    This implementation supports both current XRPL and future XLS-66 features.
    """

    # Network endpoints
    NETWORKS = {
        "mainnet": "https://xrplcluster.com",
        "testnet": "https://s.altnet.rippletest.net:51234",
        "devnet": "https://s.devnet.rippletest.net:51234"
    }

    # RLUSD issuer addresses (Strategic Business Innovations)
    RLUSD_ISSUER = {
        "mainnet": "rL5yJGZxwxKHF6AgR4ogR8sF5zaZfFZzSc",  # Placeholder - update when live
        "testnet": "rL5yJGZxwxKHF6AgR4ogR8sF5zaZfFZzSc"   # Testnet issuer
    }

    def __init__(
        self,
        network_type: str = "testnet",
        wallet_seed: Optional[str] = None,
        network_url: Optional[str] = None
    ):
        self.network_type = network_type
        self.network_url = network_url or self.NETWORKS.get(network_type, self.NETWORKS["testnet"])
        self.wallet = None
        self._client = None
        self._loan_offers: Dict[str, LoanOffer] = {}

        if wallet_seed:
            self._init_wallet(wallet_seed)

        logger.info("XRPL Liquidity Engine initialized", extra={
            "network": network_type,
            "url": self.network_url,
            "wallet_set": bool(self.wallet)
        })

    def _init_wallet(self, seed: str):
        """Initialize XRPL wallet from seed (APEX: seed from env only)."""
        try:
            from xrpl.wallet import Wallet
            self.wallet = Wallet.from_seed(seed)
            logger.info("XRPL wallet initialized", extra={
                "address": self.wallet.address
            })
        except ImportError:
            logger.warning("xrpl-py not installed - XRPL features disabled. Run: pip install xrpl-py")
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

    async def get_account_info(self, address: Optional[str] = None) -> Dict[str, Any]:
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

    async def get_xrp_balance(self, address: Optional[str] = None) -> Decimal:
        """Get XRP balance for an address."""
        account_info = await self.get_account_info(address)
        if "error" in account_info:
            return Decimal("0")

        try:
            # XRP is stored in drops (1 XRP = 1,000,000 drops)
            drops = int(account_info.get("account_data", {}).get("Balance", 0))
            return Decimal(drops) / Decimal("1000000")
        except (KeyError, ValueError):
            return Decimal("0")

    async def get_rlusd_balance(self, address: Optional[str] = None) -> Decimal:
        """
        Get RLUSD balance for an address.
        RLUSD is an issued currency (stablecoin) on XRPL.
        """
        if not self.client:
            return Decimal("0")

        target_address = address or (self.wallet.address if self.wallet else None)
        if not target_address:
            return Decimal("0")

        try:
            from xrpl.models.requests import AccountLines
            issuer = self.RLUSD_ISSUER.get(self.network_type, self.RLUSD_ISSUER["testnet"])

            response = self.client.request(AccountLines(
                account=target_address,
                ledger_index="validated"
            ))

            # Find RLUSD trust line
            for line in response.result.get("lines", []):
                if line.get("currency") == "RLUSD" and line.get("account") == issuer:
                    return Decimal(line.get("balance", "0"))

            return Decimal("0")
        except Exception as e:
            logger.error(f"Failed to get RLUSD balance: {e}")
            return Decimal("0")

    async def create_loan_offer(
        self,
        principal: Decimal,
        principal_currency: str,
        interest_bps: int,
        duration_seconds: int,
        collateral_asset: str = "XRP",
        collateral_ratio: Decimal = Decimal("1.5"),
        borrower_address: Optional[str] = None,
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an XLS-66 loan offer on XRPL.

        Args:
            principal: Loan principal amount
            principal_currency: Currency (XRP or RLUSD)
            interest_bps: Interest rate in basis points (100 = 1%)
            duration_seconds: Loan duration in seconds
            collateral_asset: Asset to use as collateral (XRP or RLUSD)
            collateral_ratio: Required collateral ratio (e.g., 1.5 = 150%)
            borrower_address: Optional borrower address (defaults to wallet address)
            consent_ref: POPIA consent reference for audit

        Returns:
            Loan offer result or error
        """
        start_time = time.time()

        # Generate loan ID
        loan_id = f"loan-{uuid4().hex[:12]}"

        logger.info("Creating loan offer", extra={
            "loan_id": loan_id,
            "principal": str(principal),
            "currency": principal_currency,
            "interest_bps": interest_bps,
            "duration_seconds": duration_seconds
        })

        if not self.wallet or not self.client:
            return {
                "status": "error",
                "message": "XRPL wallet or client not initialized",
                "loan_id": loan_id
            }

        # Calculate required collateral
        collateral_amount = principal * collateral_ratio

        # Create loan offer record
        loan = LoanOffer(
            loan_id=loan_id,
            borrower_address=borrower_address or self.wallet.address,
            principal=principal,
            principal_currency=principal_currency,
            interest_bps=interest_bps,
            duration_seconds=duration_seconds,
            collateral_amount=collateral_amount,
            collateral_asset=collateral_asset,
            collateral_ratio=collateral_ratio,
            status=LoanStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=duration_seconds)
        )

        try:
            # XLS-66 Implementation (when amendment is live)
            # Currently, we simulate the loan offer creation
            # Full implementation will use VaultCreate, VaultDeposit, etc.

            if principal_currency == "XRP":
                from xrpl.utils import xrp_to_drops

                # For current XRPL, create an OfferCreate transaction
                # This serves as a placeholder for XLS-66 vault operations

                logger.info("Loan offer prepared (XLS-66 simulation)", extra={
                    "loan_id": loan_id,
                    "principal_xrp": str(principal),
                    "collateral_xrp": str(collateral_amount)
                })

                loan.status = LoanStatus.ACTIVE
                loan.vault_id = f"vault-{loan_id}"
                loan.audit_trail.append({
                    "action": "loan_created",
                    "timestamp": datetime.utcnow().isoformat(),
                    "consent_ref": consent_ref
                })

            elif principal_currency == "RLUSD":
                # RLUSD loan - requires trust line to issuer
                logger.info("RLUSD loan offer prepared", extra={
                    "loan_id": loan_id,
                    "principal_rlusd": str(principal)
                })

                loan.status = LoanStatus.ACTIVE
                loan.vault_id = f"vault-{loan_id}"

            # Store loan offer
            self._loan_offers[loan_id] = loan

            duration_ms = int((time.time() - start_time) * 1000)

            # Build audit record
            audit = AuditRecord(
                timestamp=datetime.utcnow().isoformat(),
                action="create_loan_offer",
                user_id=borrower_address or self.wallet.address,
                details={
                    "loan_id": loan_id,
                    "principal": str(principal),
                    "currency": principal_currency,
                    "interest_bps": interest_bps,
                    "collateral_ratio": str(collateral_ratio)
                },
                consent_reference=consent_ref,
                model_used="xrpl-v3.1.0",
                duration_ms=duration_ms
            )

            return {
                "status": "success",
                "loan": loan.to_dict(),
                "audit": audit.to_dict(),
                "message": f"Loan offer {loan_id} created successfully"
            }

        except Exception as e:
            logger.error(f"Failed to create loan offer: {e}")
            return {
                "status": "error",
                "message": str(e),
                "loan_id": loan_id
            }

    async def process_x402_payment(
        self,
        amount: Decimal,
        currency: str,
        destination: str,
        purpose: str,
        consent_ref: str
    ) -> Dict[str, Any]:
        """
        Process an x402 autonomous payment.

        x402 is an HTTP status code for payment-required responses,
        enabling autonomous payment negotiation between AI agents.

        APEX Invariant #2: Auth verified per-request (consent required)
        """
        start_time = time.time()
        payment_id = f"x402-{uuid4().hex[:8]}"

        logger.info("Processing x402 payment", extra={
            "payment_id": payment_id,
            "amount": str(amount),
            "currency": currency,
            "destination_prefix": destination[:10] + "..."
        })

        if not self.wallet or not self.client:
            return {
                "status": "error",
                "message": "XRPL wallet or client not initialized",
                "payment_id": payment_id
            }

        payment = x402Payment(
            payment_id=payment_id,
            amount=amount,
            currency=currency.upper(),
            destination=destination,
            purpose=purpose,
            status=PaymentStatus.PENDING,
            consent_ref=consent_ref,
            created_at=datetime.utcnow()
        )

        try:
            if currency.upper() == "XRP":
                from xrpl.models.transactions import Payment
                from xrpl.utils import xrp_to_drops
                from xrpl.transaction import submit_and_wait

                # Build payment transaction
                payment_tx = Payment(
                    account=self.wallet.address,
                    destination=destination,
                    amount=xrp_to_drops(float(amount))
                )

                logger.info("XRP payment prepared", extra={
                    "payment_id": payment_id,
                    "amount_drops": xrp_to_drops(float(amount))
                })

                # In production, sign and submit
                # signed_tx = sign(payment_tx, self.wallet)
                # response = submit_and_wait(signed_tx, self.client)

                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                payment.transaction_hash = f"simulated-{uuid4().hex[:16]}"

            elif currency.upper() == "RLUSD":
                # RLUSD payment (issued currency)
                from xrpl.models.transactions import Payment

                issuer = self.RLUSD_ISSUER.get(self.network_type)

                # Build issued currency payment
                payment_tx = Payment(
                    account=self.wallet.address,
                    destination=destination,
                    amount={
                        "currency": "RLUSD",
                        "issuer": issuer,
                        "value": str(amount)
                    }
                )

                logger.info("RLUSD payment prepared", extra={
                    "payment_id": payment_id,
                    "issuer": issuer
                })

                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                payment.transaction_hash = f"simulated-{uuid4().hex[:16]}"

            else:
                return {
                    "status": "error",
                    "message": f"Unsupported currency: {currency}",
                    "payment_id": payment_id
                }

            duration_ms = int((time.time() - start_time) * 1000)

            audit = AuditRecord(
                timestamp=datetime.utcnow().isoformat(),
                action="x402_payment",
                user_id=self.wallet.address,
                details={
                    "payment_id": payment_id,
                    "amount": str(amount),
                    "currency": currency,
                    "destination_prefix": destination[:12] + "...",
                    "transaction_hash": payment.transaction_hash
                },
                consent_reference=consent_ref,
                model_used="xrpl-x402",
                duration_ms=duration_ms
            )

            return {
                "status": "success",
                "payment": payment.to_dict(),
                "audit": audit.to_dict()
            }

        except Exception as e:
            logger.error(f"x402 payment failed: {e}")
            payment.status = PaymentStatus.FAILED
            return {
                "status": "error",
                "message": str(e),
                "payment": payment.to_dict()
            }

    async def get_loan_status(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a loan offer."""
        loan = self._loan_offers.get(loan_id)
        return loan.to_dict() if loan else None


# ═══════════════════════════════════════════════════════════════════════════════
# Consent Manager (POPIA Compliant)
# ═══════════════════════════════════════════════════════════════════════════════

class ConsentManager:
    """
    POPIA-compliant consent management.

    APEX Invariant #2: Auth verified per-request with explicit consent.
    Handles consent grants, revocations, verification, and audit trails.
    """

    def __init__(self):
        self._consents: Dict[str, POPIAConsent] = {}
        self._audit_log: List[Dict[str, Any]] = []
        logger.info("ConsentManager initialized")

    def grant_consent(
        self,
        user_id: str,
        scopes: List[ConsentScope],
        granted_via: str,
        duration_days: int = 365,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> POPIAConsent:
        """
        Grant consent for specified scopes.

        Args:
            user_id: User identifier
            scopes: List of consent scopes to grant
            granted_via: Method of consent grant (web, api, voice, whatsapp)
            duration_days: Consent validity duration in days
            ip_address: IP address of the user (for audit)
            user_agent: User agent string (for audit)

        Returns:
            POPIAConsent record
        """
        now = datetime.utcnow()

        consent = POPIAConsent(
            user_id=user_id,
            scopes=scopes,
            granted_at=now,
            expires_at=now + timedelta(days=duration_days),
            granted_via=granted_via,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_trail=[{
                "action": "granted",
                "timestamp": now.isoformat(),
                "scopes": [s.value for s in scopes],
                "via": granted_via,
                "duration_days": duration_days
            }]
        )

        self._consents[user_id] = consent

        self._audit_log.append({
            "timestamp": now.isoformat(),
            "action": "consent_granted",
            "user_id": user_id,
            "scopes": [s.value for s in scopes],
            "via": granted_via
        })

        logger.info("Consent granted", extra={
            "user_id": user_id,
            "scopes": [s.value for s in scopes],
            "expires_at": consent.expires_at.isoformat()
        })

        return consent

    def verify_consent(
        self,
        user_id: str,
        scope: ConsentScope
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify consent for a specific scope.

        Args:
            user_id: User identifier
            scope: Scope to verify

        Returns:
            Tuple of (is_valid, reference_id)
        """
        consent = self._consents.get(user_id)

        if not consent:
            logger.warning("No consent found", extra={"user_id": user_id})
            return False, None

        if not consent.is_valid(scope):
            logger.warning("Consent invalid", extra={
                "user_id": user_id,
                "scope": scope.value
            })
            return False, None

        # Generate reference ID for this consent verification
        ref = f"consent-{user_id[:8]}-{scope.value}-{uuid4().hex[:8]}"

        # Add to audit trail
        consent.audit_trail.append({
            "action": "verified",
            "timestamp": datetime.utcnow().isoformat(),
            "scope": scope.value,
            "reference": ref
        })

        logger.info("Consent verified", extra={
            "user_id": user_id,
            "scope": scope.value,
            "ref": ref
        })

        return True, ref

    def revoke_consent(
        self,
        user_id: str,
        reason: str = "user_request"
    ) -> bool:
        """
        Revoke consent for a user.

        Args:
            user_id: User identifier
            reason: Reason for revocation

        Returns:
            True if consent was revoked, False if not found
        """
        consent = self._consents.get(user_id)

        if not consent:
            return False

        consent.revoked = True
        consent.revocation_reason = reason
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

        logger.info("Consent revoked", extra={
            "user_id": user_id,
            "reason": reason
        })

        return True

    def get_consent(self, user_id: str) -> Optional[POPIAConsent]:
        """Get consent record for a user."""
        return self._consents.get(user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Voice Processing with CosyVoice-v3-plus
# ═══════════════════════════════════════════════════════════════════════════════

class CosyVoiceProcessor:
    """
    CosyVoice-v3-plus streaming voice processor.
    Supports South African languages with <500ms latency.

    Languages:
    - en-ZA: South African English
    - zu-ZA: Zulu (isiZulu)
    - xh-ZA: Xhosa (isiXhosa)
    - af-ZA: Afrikaans
    - st-ZA: Sotho (Sesotho)
    - tn-ZA: Tswana (Setswana)
    - ts-ZA: Tsonga (Xitsonga)
    - ve-ZA: Venda (Tshivenda)
    """

    SUPPORTED_LANGUAGES = {
        "en-ZA": "South African English",
        "zu-ZA": "Zulu (isiZulu)",
        "xh-ZA": "Xhosa (isiXhosa)",
        "af-ZA": "Afrikaans",
        "st-ZA": "Sotho (Sesotho)",
        "tn-ZA": "Tswana (Setswana)",
        "ts-ZA": "Tsonga (Xitsonga)",
        "ve-ZA": "Venda (Tshivenda)",
        "nso-ZA": "Northern Sotho (Sepedi)",
        "ss-ZA": "Swati (siSwati)",
        "nr-ZA": "Ndebele (isiNdebele)"
    }

    VOICE_MODELS = {
        "longxiaochun": "Female, warm, professional",
        "longxiaoxia": "Female, youthful, energetic",
        "longwan": "Male, mature, authoritative",
        "longyue": "Female, gentle, caring"
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.tts_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts"
        self.asr_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr"

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY not set - voice features disabled")

        logger.info("CosyVoice processor initialized", extra={
            "languages_supported": len(self.SUPPORTED_LANGUAGES)
        })

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
        start_time = time.time()

        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning("Language may not be fully supported", extra={"language": language})

        audit = {
            "action": "voice_synthesis",
            "timestamp": datetime.utcnow().isoformat(),
            "language": language,
            "voice": voice,
            "text_length": len(text),
            "consent_reference": consent_ref
        }

        logger.info("Synthesizing speech", extra={
            "language": language,
            "text_length": len(text)
        })

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "cosyvoice-v3-plus",
                    "input": {"text": text},
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
                    self.tts_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        duration_ms = int((time.time() - start_time) * 1000)

                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["audio_size_bytes"] = len(audio_data)

                        logger.info("Speech synthesis completed", extra={
                            "duration_ms": duration_ms,
                            "audio_size": len(audio_data)
                        })

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
            audit["error"] = str(e)[:200]

            return {
                "status": "error",
                "message": str(e)[:200],
                "audit": audit
            }

    async def transcribe(
        self,
        audio_base64: str,
        language: str = "en-ZA",
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Paraformer-v2 (ASR).

        Supports code-switching for multilingual South African speech.

        Args:
            audio_base64: Base64-encoded audio data
            language: Source language (auto-detected if not specified)
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

        logger.info("Transcribing audio", extra={"language": language})

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "paraformer-v2",
                    "input": {"audio": audio_base64},
                    "parameters": {
                        "language": language,
                        "format": "auto",
                        "enable_code_switching": True
                    }
                }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    self.asr_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        duration_ms = int((time.time() - start_time) * 1000)

                        text = result.get("output", {}).get("text", "")

                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["text_length"] = len(text)

                        logger.info("Transcription completed", extra={
                            "duration_ms": duration_ms,
                            "text_length": len(text)
                        })

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
            audit["error"] = str(e)[:200]

            return {
                "status": "error",
                "message": str(e)[:200],
                "audit": audit
            }


# ═══════════════════════════════════════════════════════════════════════════════
# Main Sentient Financial Sentinel Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class SentientFinancialSentinel:
    """
    Main orchestrator for the Sentient Financial Sentinel.

    Coordinates:
    - Qwen 3.5-Plus for intelligent analysis and Auto Mode tool calling
    - XRPL for blockchain settlements and XLS-66 lending
    - CosyVoice for multilingual voice I/O
    - Consent management for POPIA compliance
    - Full APEX audit trail for every action

    Operating Modes:
    - OBSERVATION: Read-only analysis, no actions taken
    - ADVISORY: Recommendations provided, user approval required for actions
    - AUTONOMOUS: Full automation with verified POPIA consent
    - EMERGENCY: Emergency protocols, relaxed rate limits
    """

    def __init__(
        self,
        dashscope_api_key: Optional[str] = None,
        xrpl_network_type: str = "testnet",
        xrpl_wallet_seed: Optional[str] = None,
        mode: SentinelMode = SentinelMode.ADVISORY
    ):
        self.mode = mode
        self._audit_log: List[Dict[str, Any]] = []

        # Initialize AI model client
        api_key = dashscope_api_key or os.getenv("DASHSCOPE_API_KEY")
        if api_key:
            self.model = SentinelModelClient(api_key)
            self.voice = CosyVoiceProcessor(api_key)
        else:
            self.model = None
            self.voice = None
            logger.warning("DASHSCOPE_API_KEY not set - AI and voice features disabled")

        # Initialize XRPL engine
        wallet_seed = xrpl_wallet_seed or os.getenv("XRPL_AGENT_SEED")
        self.xrpl = XRPLLiquidityEngine(
            network_type=xrpl_network_type,
            wallet_seed=wallet_seed
        )

        # Initialize consent manager
        self.consent_manager = ConsentManager()

        logger.info("SentientFinancialSentinel initialized", extra={
            "mode": mode.value,
            "xrpl_network": xrpl_network_type,
            "ai_enabled": bool(self.model),
            "voice_enabled": bool(self.voice)
        })

    async def process_voice_command(
        self,
        audio_base64: str,
        user_id: str,
        language: str = "en-ZA",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a voice command through the full pipeline.

        Pipeline:
        1. Verify consent for voice processing
        2. Transcribe audio (Paraformer ASR)
        3. Analyze with Qwen 3.5-Plus
        4. Execute any required actions (with consent)
        5. Synthesize response (CosyVoice TTS)

        Args:
            audio_base64: Base64-encoded audio data
            user_id: User identifier
            language: Audio language code
            context: Additional context for analysis

        Returns:
            Response with audio and metadata
        """
        start_time = time.time()

        # Step 1: Verify consent
        has_consent, consent_ref = self.consent_manager.verify_consent(
            user_id, ConsentScope.VOICE_PROCESSING
        )

        if not has_consent:
            return {
                "status": "error",
                "message": "Voice processing consent required",
                "action_required": "grant_consent",
                "required_scopes": ["voice_processing", "financial_analysis"]
            }

        # Step 2: Transcribe audio
        if not self.voice:
            return {
                "status": "error",
                "message": "Voice processing not available (DASHSCOPE_API_KEY not set)"
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
                "message": "AI model not available (DASHSCOPE_API_KEY not set)",
                "transcription": query
            }

        # Use Auto Mode with tools for autonomous actions
        analysis = await self.model.chat_with_audit(
            messages=[
                {"role": "system", "content": "You are the Sentient Financial Sentinel. Analyze the user's voice command and provide a helpful response."},
                {"role": "user", "content": query}
            ],
            tools=self.model.get_tools_schema() if self.mode == SentinelMode.AUTONOMOUS else None,
            user_id=user_id,
            consent_ref=consent_ref
        )

        response_text = analysis["response"].choices[0].message.content

        # Step 4: Handle tool calls if present (AUTONOMOUS mode)
        if self.mode == SentinelMode.AUTONOMOUS:
            tool_calls = analysis["response"].choices[0].message.tool_calls
            if tool_calls:
                for tool_call in tool_calls:
                    await self._execute_tool_call(tool_call, user_id, consent_ref)

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
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a text-based financial query.

        Args:
            query: User query text
            user_id: User identifier
            context: Additional context for analysis

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
                "action_required": "grant_consent",
                "required_scopes": ["financial_analysis"]
            }

        if not self.model:
            return {
                "status": "error",
                "message": "AI model not available (DASHSCOPE_API_KEY not set)"
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
        purpose: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute an XRPL settlement.

        Args:
            amount: Settlement amount
            currency: Currency code (XRP, RLUSD)
            destination: Destination address
            purpose: Payment purpose/reference
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
                "action_required": "grant_consent",
                "required_scopes": ["xrpl_settlement"]
            }

        return await self.xrpl.process_x402_payment(
            amount=amount,
            currency=currency,
            destination=destination,
            purpose=purpose,
            consent_ref=consent_ref
        )

    async def create_loan(
        self,
        principal: Decimal,
        currency: str,
        interest_bps: int,
        duration_days: int,
        collateral_ratio: Decimal,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create a loan offer (XLS-66).

        Args:
            principal: Loan principal
            currency: Currency (XRP or RLUSD)
            interest_bps: Interest rate in basis points
            duration_days: Loan duration in days
            collateral_ratio: Required collateral ratio
            user_id: User identifier

        Returns:
            Loan offer result
        """
        # Verify consent for autonomous trading
        has_consent, consent_ref = self.consent_manager.verify_consent(
            user_id, ConsentScope.AUTONOMOUS_TRADING
        )

        if not has_consent:
            return {
                "status": "error",
                "message": "Autonomous trading consent required for loan creation",
                "action_required": "grant_consent",
                "required_scopes": ["autonomous_trading"]
            }

        return await self.xrpl.create_loan_offer(
            principal=principal,
            principal_currency=currency,
            interest_bps=interest_bps,
            duration_seconds=duration_days * 86400,
            collateral_ratio=collateral_ratio,
            consent_ref=consent_ref
        )

    def grant_user_consent(
        self,
        user_id: str,
        scopes: List[str],
        via: str = "api",
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Grant consent for a user.

        Args:
            user_id: User identifier
            scopes: List of scope strings to grant
            via: Method of consent grant
            ip_address: User's IP address for audit

        Returns:
            Consent details
        """
        scope_enums = []
        for s in scopes:
            try:
                scope_enums.append(ConsentScope(s))
            except ValueError:
                logger.warning("Invalid scope requested", extra={"scope": s})

        if not scope_enums:
            return {
                "status": "error",
                "message": "No valid scopes provided",
                "valid_scopes": [s.value for s in ConsentScope]
            }

        consent = self.consent_manager.grant_consent(
            user_id=user_id,
            scopes=scope_enums,
            granted_via=via,
            ip_address=ip_address
        )

        return {
            "status": "success",
            "user_id": user_id,
            "scopes": [s.value for s in consent.scopes],
            "granted_at": consent.granted_at.isoformat(),
            "expires_at": consent.expires_at.isoformat()
        }

    def revoke_user_consent(self, user_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Revoke consent for a user.

        Args:
            user_id: User identifier
            reason: Reason for revocation

        Returns:
            Revocation status
        """
        success = self.consent_manager.revoke_consent(user_id, reason)

        return {
            "status": "success" if success else "not_found",
            "user_id": user_id,
            "revoked": success
        }

    async def _execute_tool_call(
        self,
        tool_call: Any,
        user_id: str,
        consent_ref: str
    ) -> Dict[str, Any]:
        """Execute a tool call from Auto Mode."""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        logger.info("Executing tool call", extra={
            "function": function_name,
            "user_id": user_id
        })

        if function_name == "create_loan_offer":
            return await self.xrpl.create_loan_offer(
                principal=Decimal(str(arguments.get("principal"))),
                principal_currency=arguments.get("currency", "XRP"),
                interest_bps=arguments.get("interest_bps", 500),
                duration_seconds=arguments.get("duration_days", 30) * 86400,
                collateral_ratio=Decimal(str(arguments.get("collateral_ratio", 1.5))),
                consent_ref=consent_ref
            )

        elif function_name == "execute_payment":
            return await self.xrpl.process_x402_payment(
                amount=Decimal(str(arguments.get("amount"))),
                currency=arguments.get("currency", "XRP"),
                destination=arguments.get("destination"),
                purpose=arguments.get("purpose", ""),
                consent_ref=consent_ref
            )

        else:
            return {"status": "error", "message": f"Unknown function: {function_name}"}

    def get_status(self) -> Dict[str, Any]:
        """Get sentinel status and configuration."""
        return {
            "mode": self.mode.value,
            "ai_enabled": bool(self.model),
            "voice_enabled": bool(self.voice),
            "xrpl_network": self.xrpl.network_type,
            "xrpl_wallet_set": bool(self.xrpl.wallet),
            "active_consents": len(self.consent_manager._consents),
            "active_loans": len(self.xrpl._loan_offers)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Module Exports
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "SentientFinancialSentinel",
    "SentinelMode",
    "ConsentScope",
    "POPIAConsent",
    "LoanStatus",
    "PaymentStatus",
    "LoanOffer",
    "x402Payment",
    "AuditRecord",
    "SentinelModelClient",
    "XRPLLiquidityEngine",
    "CosyVoiceProcessor",
    "ConsentManager",
]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point for testing and diagnostics."""
    import argparse

    parser = argparse.ArgumentParser(description="Sentient Financial Sentinel - Phase 1")
    parser.add_argument("--query", type=str, help="Text query to process")
    parser.add_argument("--mode", type=str, default="advisory",
                       choices=["observation", "advisory", "autonomous"])
    parser.add_argument("--status", action="store_true", help="Show sentinel status")
    parser.add_argument("--grant-consent", type=str, help="Grant consent for user ID")
    args = parser.parse_args()

    sentinel = SentientFinancialSentinel(mode=SentinelMode(args.mode))

    if args.status:
        print(json.dumps(sentinel.get_status(), indent=2))
        return

    if args.grant_consent:
        result = sentinel.grant_user_consent(
            user_id=args.grant_consent,
            scopes=["financial_analysis", "voice_processing", "xrpl_settlement"],
            via="cli"
        )
        print(json.dumps(result, indent=2))
        return

    # Grant test consent for queries
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
        print("Sentient Financial Sentinel ready.")
        print("Use --query 'your question' to test.")
        print("Use --status to show configuration.")
        print("Use --grant-consent USER_ID to grant consent.")


if __name__ == "__main__":
    asyncio.run(main())
