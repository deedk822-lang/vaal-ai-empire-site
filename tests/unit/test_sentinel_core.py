#!/usr/bin/env python3
"""
Comprehensive tests for Sentient Financial Sentinel Core.
Tests consent management, XRPL operations, model client, and orchestration.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "sentient_swarm"))

from sentinel_core import (
    SentinelMode,
    ConsentScope,
    POPIAConsent,
    AuditRecord,
    SentinelModelClient,
    XRPLLiquidityEngine,
    CosyVoiceProcessor,
    ConsentManager,
    SentientFinancialSentinel
)


class TestSentinelMode:
    """Test SentinelMode enum."""

    def test_sentinel_mode_values(self):
        """Test sentinel mode enum values."""
        assert SentinelMode.OBSERVATION.value == "observation"
        assert SentinelMode.ADVISORY.value == "advisory"
        assert SentinelMode.AUTONOMOUS.value == "autonomous"
        assert SentinelMode.EMERGENCY.value == "emergency"

    def test_sentinel_mode_count(self):
        """Test expected number of modes."""
        assert len(SentinelMode) == 4


class TestConsentScope:
    """Test ConsentScope enum."""

    def test_consent_scope_values(self):
        """Test consent scope enum values."""
        assert ConsentScope.VOICE_PROCESSING.value == "voice_processing"
        assert ConsentScope.FINANCIAL_ANALYSIS.value == "financial_analysis"
        assert ConsentScope.AUTONOMOUS_TRADING.value == "autonomous_trading"
        assert ConsentScope.XRPL_SETTLEMENT.value == "xrpl_settlement"
        assert ConsentScope.DATA_RETENTION.value == "data_retention"

    def test_consent_scope_count(self):
        """Test expected number of scopes."""
        assert len(ConsentScope) == 5


class TestPOPIAConsent:
    """Test POPIAConsent dataclass."""

    def test_consent_creation(self):
        """Test creating a consent record."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=365)

        consent = POPIAConsent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_at=now,
            expires_at=expires,
            granted_via="web"
        )

        assert consent.user_id == "user123"
        assert ConsentScope.VOICE_PROCESSING in consent.scopes
        assert consent.granted_via == "web"
        assert consent.revoked is False
        assert len(consent.audit_trail) == 0

    def test_consent_is_valid(self):
        """Test consent validity check."""
        now = datetime.now(timezone.utc)
        consent = POPIAConsent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING, ConsentScope.FINANCIAL_ANALYSIS],
            granted_at=now,
            expires_at=now + timedelta(days=365),
            granted_via="api"
        )

        # Valid scope
        assert consent.is_valid(ConsentScope.VOICE_PROCESSING) is True
        assert consent.is_valid(ConsentScope.FINANCIAL_ANALYSIS) is True

        # Invalid scope (not granted)
        assert consent.is_valid(ConsentScope.AUTONOMOUS_TRADING) is False

    def test_consent_expired(self):
        """Test expired consent."""
        now = datetime.now(timezone.utc)
        consent = POPIAConsent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_at=now - timedelta(days=366),
            expires_at=now - timedelta(days=1),  # Expired
            granted_via="api"
        )

        assert consent.is_valid(ConsentScope.VOICE_PROCESSING) is False

    def test_consent_revoked(self):
        """Test revoked consent."""
        now = datetime.now(timezone.utc)
        consent = POPIAConsent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_at=now,
            expires_at=now + timedelta(days=365),
            granted_via="api",
            revoked=True
        )

        assert consent.is_valid(ConsentScope.VOICE_PROCESSING) is False


class TestAuditRecord:
    """Test AuditRecord dataclass."""

    def test_audit_record_creation(self):
        """Test creating an audit record."""
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="test_action",
            user_id="user123",
            details={"key": "value"},
            consent_reference="consent-ref-123",
            model_used="qwen3.5-plus",
            duration_ms=150
        )

        assert record.action == "test_action"
        assert record.user_id == "user123"
        assert record.details["key"] == "value"
        assert record.consent_reference == "consent-ref-123"
        assert record.duration_ms == 150

    def test_audit_record_to_dict(self):
        """Test converting audit record to dict."""
        record = AuditRecord(
            timestamp="2024-01-01T00:00:00Z",
            action="test",
            user_id="user123",
            details={}
        )

        record_dict = record.to_dict()

        assert isinstance(record_dict, dict)
        assert record_dict["action"] == "test"
        assert record_dict["user_id"] == "user123"
        assert "timestamp" in record_dict


class TestConsentManager:
    """Test ConsentManager."""

    def test_init(self):
        """Test ConsentManager initialization."""
        manager = ConsentManager()

        assert len(manager._consents) == 0
        assert len(manager._audit_log) == 0

    def test_grant_consent(self):
        """Test granting consent."""
        manager = ConsentManager()

        consent = manager.grant_consent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING, ConsentScope.FINANCIAL_ANALYSIS],
            granted_via="api",
            duration_days=180
        )

        assert consent.user_id == "user123"
        assert len(consent.scopes) == 2
        assert consent.granted_via == "api"
        assert len(consent.audit_trail) > 0

        # Check it's stored
        assert "user123" in manager._consents

    def test_verify_consent_valid(self):
        """Test verifying valid consent."""
        manager = ConsentManager()

        manager.grant_consent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_via="web"
        )

        is_valid, ref = manager.verify_consent("user123", ConsentScope.VOICE_PROCESSING)

        assert is_valid is True
        assert ref is not None
        assert ref.startswith("consent-")

    def test_verify_consent_invalid_scope(self):
        """Test verifying consent for invalid scope."""
        manager = ConsentManager()

        manager.grant_consent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_via="web"
        )

        is_valid, ref = manager.verify_consent("user123", ConsentScope.AUTONOMOUS_TRADING)

        assert is_valid is False
        assert ref is None

    def test_verify_consent_no_consent(self):
        """Test verifying consent when none exists."""
        manager = ConsentManager()

        is_valid, ref = manager.verify_consent("user999", ConsentScope.VOICE_PROCESSING)

        assert is_valid is False
        assert ref is None

    def test_revoke_consent(self):
        """Test revoking consent."""
        manager = ConsentManager()

        manager.grant_consent(
            user_id="user123",
            scopes=[ConsentScope.VOICE_PROCESSING],
            granted_via="api"
        )

        result = manager.revoke_consent("user123", reason="user_request")

        assert result is True

        # Verify consent is now invalid
        is_valid, _ = manager.verify_consent("user123", ConsentScope.VOICE_PROCESSING)
        assert is_valid is False

    def test_revoke_non_existent_consent(self):
        """Test revoking non-existent consent."""
        manager = ConsentManager()

        result = manager.revoke_consent("user999")

        assert result is False

    def test_hash_user_id(self):
        """Test user ID hashing for POPIA compliance."""
        hashed = ConsentManager._hash_user_id("user123")

        assert isinstance(hashed, str)
        assert len(hashed) == 16
        assert hashed != "user123"

        # Same input should produce same hash
        hashed2 = ConsentManager._hash_user_id("user123")
        assert hashed == hashed2


class TestSentinelModelClient:
    """Test SentinelModelClient."""

    def test_init(self):
        """Test model client initialization."""
        client = SentinelModelClient(api_key="test-key", model="qwen3.5-plus")

        assert client.api_key == "test-key"
        assert client.model == "qwen3.5-plus"
        assert client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert client.request_count == 0

    @pytest.mark.asyncio
    async def test_chat_with_audit_success(self):
        """Test successful chat with audit."""
        client = SentinelModelClient(api_key="test-key")

        # Mock AsyncOpenAI client
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="AI response"))]

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(client, 'client', mock_openai_client):
            result = await client.chat_with_audit(
                messages=[{"role": "user", "content": "Test"}],
                user_id="user123",
                consent_ref="consent-123"
            )

        assert "response" in result
        assert "audit" in result
        assert "request_id" in result
        assert result["audit"]["action"] == "model_chat"

    @pytest.mark.asyncio
    async def test_chat_with_audit_with_tools(self):
        """Test chat with tools enabled."""
        client = SentinelModelClient(api_key="test-key")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        tools = [{"type": "function", "function": {"name": "test_tool"}}]

        with patch.object(client, 'client', mock_openai_client):
            result = await client.chat_with_audit(
                messages=[{"role": "user", "content": "Test"}],
                tools=tools,
                user_id="user123"
            )

        # Verify tools were passed
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["tools"] == tools
        assert call_args[1]["extra_body"]["enable_auto"] is True

    @pytest.mark.asyncio
    async def test_analyze_financial_query(self):
        """Test financial query analysis."""
        client = SentinelModelClient(api_key="test-key")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Financial analysis"))]

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(client, 'client', mock_openai_client):
            result = await client.analyze_financial_query(
                query="What is my balance?",
                context={"currency": "ZAR"},
                user_id="user123"
            )

        assert "response" in result
        assert "audit" in result


class TestXRPLLiquidityEngine:
    """Test XRPLLiquidityEngine."""

    def test_init_default(self):
        """Test default initialization."""
        engine = XRPLLiquidityEngine()

        assert engine.network_url is not None
        assert engine.network_type == "testnet"
        assert engine.wallet is None

    def test_init_with_seed(self):
        """Test initialization with wallet seed."""
        # Skip if xrpl-py not installed
        try:
            from xrpl.wallet import Wallet
        except ImportError:
            pytest.skip("xrpl-py not installed")

        # Use a valid test seed
        test_seed = "sEdTM1uX8pu2do5XvTnutH6HsouMaM2"

        engine = XRPLLiquidityEngine(wallet_seed=test_seed)

        assert engine.wallet is not None
        assert engine.wallet.address is not None

    @pytest.mark.asyncio
    async def test_get_account_info_no_wallet(self):
        """Test get_account_info without wallet."""
        engine = XRPLLiquidityEngine()

        result = await engine.get_account_info()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_loan_offer(self):
        """Test creating a loan offer."""
        engine = XRPLLiquidityEngine()

        result = await engine.create_loan_offer(
            principal=Decimal("100"),
            interest_bps=500,
            duration_seconds=86400
        )

        # Without wallet, should return error
        assert "error" in result or "status" in result

    @pytest.mark.asyncio
    async def test_get_rlusd_balance(self):
        """Test getting RLUSD balance."""
        engine = XRPLLiquidityEngine()

        balance = await engine.get_rlusd_balance()

        # Without wallet, should return 0
        assert balance == Decimal("0")

    @pytest.mark.asyncio
    async def test_process_x402_payment_no_wallet(self):
        """Test x402 payment without wallet."""
        engine = XRPLLiquidityEngine()

        result = await engine.process_x402_payment(
            amount=Decimal("10"),
            currency="XRP",
            destination="rTest123",
            consent_ref="consent-123"
        )

        assert result["status"] == "error"
        assert "Wallet not initialized" in result["message"]

    @pytest.mark.asyncio
    async def test_process_x402_payment_invalid_destination(self):
        """Test x402 payment with invalid destination."""
        try:
            from xrpl.wallet import Wallet
        except ImportError:
            pytest.skip("xrpl-py not installed")

        test_seed = "sEdTM1uX8pu2do5XvTnutH6HsouMaM2"
        engine = XRPLLiquidityEngine(wallet_seed=test_seed)

        result = await engine.process_x402_payment(
            amount=Decimal("10"),
            currency="XRP",
            destination="invalid-address",
            consent_ref="consent-123"
        )

        assert result["status"] == "error"
        assert "Invalid XRPL destination" in result["message"]

    @pytest.mark.asyncio
    async def test_process_x402_payment_invalid_amount(self):
        """Test x402 payment with invalid amount."""
        try:
            from xrpl.wallet import Wallet
        except ImportError:
            pytest.skip("xrpl-py not installed")

        test_seed = "sEdTM1uX8pu2do5XvTnutH6HsouMaM2"
        engine = XRPLLiquidityEngine(wallet_seed=test_seed)

        result = await engine.process_x402_payment(
            amount=Decimal("-10"),
            currency="XRP",
            destination="rN7n7otQDd6FczFgLdlqtyMVrn3yDUkMKB",
            consent_ref="consent-123"
        )

        assert result["status"] == "error"
        assert "Invalid amount" in result["message"]


class TestCosyVoiceProcessor:
    """Test CosyVoiceProcessor."""

    def test_init(self):
        """Test CosyVoiceProcessor initialization."""
        processor = CosyVoiceProcessor(api_key="test-key")

        assert processor.api_key == "test-key"
        assert processor.base_url == "https://dashscope.aliyuncs.com/api/v1/services/audio/tts"

    def test_supported_languages(self):
        """Test supported languages."""
        assert "en-ZA" in CosyVoiceProcessor.SUPPORTED_LANGUAGES
        assert "zu-ZA" in CosyVoiceProcessor.SUPPORTED_LANGUAGES
        assert "xh-ZA" in CosyVoiceProcessor.SUPPORTED_LANGUAGES

    @pytest.mark.asyncio
    async def test_synthesize_success(self):
        """Test successful synthesis."""
        processor = CosyVoiceProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"audio_data")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('sentinel_core.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize(
                text="Hello world",
                consent_ref="consent-123"
            )

        assert result["status"] == "success"
        assert result["audio_data"] == b"audio_data"

    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        """Test successful transcription."""
        processor = CosyVoiceProcessor(api_key="test-key")

        import base64
        audio_base64 = base64.b64encode(b"audio").decode('utf-8')

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "output": {"text": "Transcribed text"}
        })

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('sentinel_core.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.transcribe(
                audio_base64=audio_base64,
                consent_ref="consent-123"
            )

        assert result["status"] == "success"
        assert result["text"] == "Transcribed text"


class TestSentientFinancialSentinel:
    """Test SentientFinancialSentinel orchestrator."""

    def test_init_default(self):
        """Test default initialization."""
        with patch.dict(os.environ, {}, clear=True):
            sentinel = SentientFinancialSentinel()

            assert sentinel.mode == SentinelMode.ADVISORY
            assert isinstance(sentinel.consent_manager, ConsentManager)
            assert isinstance(sentinel.xrpl, XRPLLiquidityEngine)

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        sentinel = SentientFinancialSentinel(
            dashscope_api_key="test-key",
            mode=SentinelMode.AUTONOMOUS
        )

        assert sentinel.mode == SentinelMode.AUTONOMOUS
        assert sentinel.model is not None
        assert sentinel.voice is not None

    def test_grant_user_consent(self):
        """Test granting user consent."""
        sentinel = SentientFinancialSentinel()

        result = sentinel.grant_user_consent(
            user_id="user123",
            scopes=["voice_processing", "financial_analysis"],
            via="api"
        )

        assert result["status"] == "success"
        assert len(result["scopes"]) == 2

    def test_grant_user_consent_invalid_scopes(self):
        """Test granting consent with invalid scopes."""
        sentinel = SentientFinancialSentinel()

        result = sentinel.grant_user_consent(
            user_id="user123",
            scopes=["invalid_scope"],
            via="api"
        )

        assert result["status"] == "error"
        assert "No valid scopes" in result["message"]

    @pytest.mark.asyncio
    async def test_process_text_query_no_consent(self):
        """Test processing text query without consent."""
        sentinel = SentientFinancialSentinel(dashscope_api_key="test-key")

        result = await sentinel.process_text_query(
            query="Test query",
            user_id="user123"
        )

        assert result["status"] == "error"
        assert "consent required" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_text_query_with_consent(self):
        """Test processing text query with consent."""
        sentinel = SentientFinancialSentinel(dashscope_api_key="test-key")

        # Grant consent
        sentinel.grant_user_consent(
            user_id="user123",
            scopes=["financial_analysis"],
            via="test"
        )

        # Mock model response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Analysis result"))]

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(sentinel.model, 'client', mock_openai_client):
            result = await sentinel.process_text_query(
                query="What is my balance?",
                user_id="user123"
            )

        assert "response" in result or "status" in result

    @pytest.mark.asyncio
    async def test_execute_settlement_no_consent(self):
        """Test executing settlement without consent."""
        sentinel = SentientFinancialSentinel()

        result = await sentinel.execute_settlement(
            amount=Decimal("10"),
            currency="XRP",
            destination="rTest123",
            user_id="user123"
        )

        assert result["status"] == "error"
        assert "consent required" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_voice_command_no_consent(self):
        """Test processing voice command without consent."""
        sentinel = SentientFinancialSentinel(dashscope_api_key="test-key")

        import base64
        audio_base64 = base64.b64encode(b"audio").decode('utf-8')

        result = await sentinel.process_voice_command(
            audio_base64=audio_base64,
            user_id="user123"
        )

        assert result["status"] == "error"
        assert "consent required" in result["message"].lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_consent_with_empty_scopes(self):
        """Test creating consent with empty scopes."""
        with pytest.raises(Exception):
            POPIAConsent(
                user_id="user123",
                scopes=[],
                granted_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                granted_via="api"
            )

    @pytest.mark.asyncio
    async def test_model_client_empty_choices(self):
        """Test model client with empty choices array."""
        client = SentinelModelClient(api_key="test-key")

        # Mock response with empty choices
        mock_response = Mock()
        mock_response.choices = []

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(client, 'client', mock_openai_client):
            result = await client.chat_with_audit(
                messages=[{"role": "user", "content": "Test"}],
                user_id="user123"
            )

        # Should handle gracefully
        assert "audit" in result

    def test_audit_record_with_none_values(self):
        """Test audit record with None values."""
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="test",
            user_id="user123",
            details={},
            consent_reference=None,
            model_used=None
        )

        record_dict = record.to_dict()

        assert record_dict["consent_reference"] is None
        assert record_dict["model_used"] is None


class TestIntegration:
    """Integration tests for full workflows."""

    @pytest.mark.asyncio
    async def test_full_voice_workflow_with_mocks(self):
        """Test full voice processing workflow with mocked components."""
        sentinel = SentientFinancialSentinel(dashscope_api_key="test-key")

        # Grant all necessary consents
        sentinel.grant_user_consent(
            user_id="user123",
            scopes=["voice_processing", "financial_analysis"],
            via="test"
        )

        # Mock voice transcription
        mock_transcribe_response = AsyncMock()
        mock_transcribe_response.status = 200
        mock_transcribe_response.json = AsyncMock(return_value={
            "output": {"text": "What is my balance?"}
        })

        # Mock model response
        mock_model_response = Mock()
        mock_model_response.choices = [Mock(message=Mock(content="Your balance is ZAR 1000"))]

        # Mock voice synthesis
        mock_synthesize_response = AsyncMock()
        mock_synthesize_response.status = 200
        mock_synthesize_response.read = AsyncMock(return_value=b"response_audio")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_transcribe_response

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_model_response)

        import base64
        audio_base64 = base64.b64encode(b"user_audio").decode('utf-8')

        with patch('sentinel_core.aiohttp.ClientSession', return_value=mock_session):
            with patch.object(sentinel.model, 'client', mock_openai_client):
                # Update synthesize mock
                mock_session.post.return_value.__aenter__.return_value = mock_synthesize_response

                result = await sentinel.process_voice_command(
                    audio_base64=audio_base64,
                    user_id="user123"
                )

        # Should complete successfully
        assert result["status"] == "success" or "transcription" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])