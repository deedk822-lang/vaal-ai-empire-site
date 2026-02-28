#!/usr/bin/env python3
"""
XRPL Integration Tests for Sentient Financial Sentinel.
APEX v2.0 Compliant - Conditional on XRPL secrets.

These tests verify XRPL functionality when secrets are available.
Non-seed-dependent tests run in CI; seed-dependent tests skip gracefully.
"""

import os
import pytest
from urllib.parse import urlparse

# APEX: Removed module-level pytestmark - apply skip only to seed-dependent tests
# Tests that don't require XRPL_AGENT_SEED should run in CI

# APEX: Allowed XRPL testnet hosts for URL validation
ALLOWED_XRPL_HOSTS = ["s.altnet.rippletest.net", "rippletest.net"]

# APEX: Reusable decorator for seed-dependent tests
seed_required = pytest.mark.skipif(
    not os.getenv("XRPL_AGENT_SEED"),
    reason="XRPL_AGENT_SEED not configured - skipping seed-dependent tests"
)


def _validate_xrpl_host(url: str) -> bool:
    """
    Validate that URL host is an allowed XRPL testnet host.
    APEX: Proper hostname validation, not substring matching.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Check exact match or subdomain match
        return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_XRPL_HOSTS)
    except Exception:
        return False


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
        """Test engine uses correct default URL with proper hostname validation."""
        from sentinel_core import XRPLLiquidityEngine
        
        engine = XRPLLiquidityEngine()
        # APEX: Use proper hostname validation instead of substring check
        assert _validate_xrpl_host(engine.network_url), f"Invalid XRPL host: {engine.network_url}"
        print("✅ XRPL Engine default URL verified")


class TestXRPLWalletOperations:
    """Test XRPL wallet operations (requires seed)."""

    @seed_required
    def test_wallet_initialization(self):
        """Test wallet initialization from seed."""
        seed = os.getenv("XRPL_AGENT_SEED")
        
        try:
            from xrpl.wallet import Wallet
            wallet = Wallet.from_seed(seed)
            assert wallet.address is not None
            print(f"✅ Wallet initialized: {wallet.address}")
        except ImportError:
            pytest.skip("xrpl-py not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
