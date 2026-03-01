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

# APEX: Allowed XRPL testnet hosts for URL validation (exact hosts only, no base domains)
ALLOWED_XRPL_HOSTS = ["s.altnet.rippletest.net"]

# APEX: Reusable decorator for seed-dependent tests
seed_required = pytest.mark.skipif(
    not os.getenv("XRPL_AGENT_SEED"),
    reason="XRPL_AGENT_SEED not configured - skipping seed-dependent tests"
)


def _validate_xrpl_host(url: str) -> bool:
    """
    Validate that URL host is an allowed XRPL testnet host.
    APEX: Exact hostname match only - no subdomain wildcards.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # APEX: Exact match only - prevents subdomain bypass
        return host in ALLOWED_XRPL_HOSTS
    except Exception:
        return False


class TestXRPLConnection:
    """Test XRPL network connectivity."""

    def test_xrpl_testnet_connection(self):
        """Verify connection to XRPL Testnet with actual network I/O."""
        try:
            from xrpl.clients import JsonRpcClient
            from xrpl.models.requests import ServerInfo
            
            client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
            
            # APEX: Perform actual network request to verify connectivity
            try:
                response = client.request(ServerInfo())
                result = response.result
                
                # Verify response contains expected fields
                assert "info" in result or "status" in result, f"Unexpected response: {result}"
                print("✅ XRPL Testnet connection successful (ServerInfo received)")
                
            except Exception as conn_err:
                # Network errors in CI should skip, not fail
                pytest.skip(f"XRPL Testnet unreachable: {conn_err}")
                
        except ImportError:
            pytest.skip("xrpl-py not installed")


class TestXRPLLiquidityEngine:
    """Test XRPL Liquidity Engine functionality."""

    def test_engine_initialization_no_seed(self):
        """Test engine initialization without wallet seed."""
        from .sentinel_core import XRPLLiquidityEngine
        
        engine = XRPLLiquidityEngine()
        assert engine.network_url is not None
        assert engine.network_type == "testnet"
        assert engine.wallet is None
        print("✅ XRPL Engine initialized without seed")

    def test_engine_default_url(self):
        """Test engine uses correct default URL with proper hostname validation."""
        from .sentinel_core import XRPLLiquidityEngine
        
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
