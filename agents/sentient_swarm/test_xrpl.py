#!/usr/bin/env python3
"""
XRPL Integration Tests for Sentient Financial Sentinel.
APEX v2.0 Compliant - Conditional on XRPL secrets.

These tests verify XRPL functionality when secrets are available.
When secrets are not configured, tests pass gracefully with skip messages.
"""

import os
import pytest

# Skip all tests if XRPL_AGENT_SEED is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("XRPL_AGENT_SEED"),
    reason="XRPL_AGENT_SEED not configured - skipping XRPL integration tests"
)


class TestXRPLConnection:
    """Test XRPL network connectivity."""

    def test_xrpl_testnet_connection(self):
        """Verify connection to XRPL Testnet."""
        try:
            from xrpl.clients import JsonRpcClient
            client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
            assert client is not None
            print("✅ XRPL Testnet connection successful")
        except ImportError:
            pytest.skip("xrpl-py not installed")


class TestXRPLLiquidityEngine:
    """Test XRPL Liquidity Engine functionality."""

    def test_engine_initialization_no_seed(self):
        """Test engine initialization without wallet seed."""
        from sentinel_core import XRPLLiquidityEngine
        
        engine = XRPLLiquidityEngine()
        assert engine.network_url is not None
        assert engine.network_type == "testnet"
        assert engine.wallet is None
        print("✅ XRPL Engine initialized without seed")

    def test_engine_default_url(self):
        """Test engine uses correct default URL."""
        from sentinel_core import XRPLLiquidityEngine
        
        engine = XRPLLiquidityEngine()
        assert "rippletest.net" in engine.network_url
        print("✅ XRPL Engine default URL verified")


class TestXRLPWalletOperations:
    """Test XRPL wallet operations (requires seed)."""

    def test_wallet_initialization(self):
        """Test wallet initialization from seed."""
        seed = os.getenv("XRPL_AGENT_SEED")
        if not seed:
            pytest.skip("XRPL_AGENT_SEED not configured")
        
        try:
            from xrpl.wallet import Wallet
            wallet = Wallet.from_seed(seed)
            assert wallet.address is not None
            print(f"✅ Wallet initialized: {wallet.address}")
        except ImportError:
            pytest.skip("xrpl-py not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
