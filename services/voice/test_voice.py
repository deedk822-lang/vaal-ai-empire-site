#!/usr/bin/env python3
"""
Voice Service Tests for Sentient Financial Sentinel.
APEX v2.0 Compliant - CosyVoice-v3-plus integration tests.

These tests verify voice processing functionality.
When DASHSCOPE_API_KEY is not configured, tests pass with skip messages.
"""

import os
import pytest

# Skip all tests if DASHSCOPE_API_KEY is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("DASHSCOPE_API_KEY"),
    reason="DASHSCOPE_API_KEY not configured - skipping voice integration tests"
)


class TestCosyVoiceProcessor:
    """Test CosyVoice voice processing."""

    def test_processor_initialization(self):
        """Test CosyVoice processor initialization."""
        try:
            # APEX: Import from actual module where CosyVoiceProcessor is defined
            from agents.sentient_swarm.sentinel_core import CosyVoiceProcessor
            
            api_key = os.getenv("DASHSCOPE_API_KEY")
            processor = CosyVoiceProcessor(api_key)
            assert processor.api_key is not None
            print("✅ CosyVoice processor initialized")
        except ImportError:
            pytest.skip("CosyVoice module not available")

    def test_supported_languages(self):
        """Test supported African languages - validates against actual implementation."""
        try:
            # APEX: Import from actual module and verify against implementation
            from agents.sentient_swarm.sentinel_core import CosyVoiceProcessor
            
            # Get the actual supported languages from the implementation
            actual_languages = set(CosyVoiceProcessor.SUPPORTED_LANGUAGES)
            
            # Expected South African official languages
            expected_languages = {
                "en-ZA",  # English (South Africa)
                "af-ZA",  # Afrikaans
                "zu-ZA",  # Zulu
                "xh-ZA",  # Xhosa
                "st-ZA",  # Sotho
                "tn-ZA",  # Tswana
                "ts-ZA",  # Tsonga
                "ve-ZA",  # Venda
            }
            
            # Verify all expected languages are supported
            assert expected_languages.issubset(actual_languages), \
                f"Missing languages: {expected_languages - actual_languages}"
            
            print(f"✅ {len(actual_languages)} languages supported by implementation")
            print(f"   Expected {len(expected_languages)} SA languages verified")
        except ImportError:
            pytest.skip("CosyVoice module not available")


class TestVoiceStreaming:
    """Test voice streaming functionality."""

    def test_streaming_config(self):
        """Test voice streaming configuration - validates against actual StreamingConfig."""
        try:
            # APEX: Import actual StreamingConfig class
            from agents.sentient_swarm.cosyvoice_streaming import StreamingConfig
            
            # Create instance with sample values
            config = StreamingConfig(
                sample_rate=16000,
                channels=1,
                format="wav",
                chunk_size=1024
            )
            
            # Assert against actual instance attributes
            assert config.sample_rate == 16000, f"Expected sample_rate=16000, got {config.sample_rate}"
            assert config.channels == 1, f"Expected channels=1, got {config.channels}"
            assert config.format == "wav", f"Expected format='wav', got {config.format}"
            assert config.chunk_size == 1024, f"Expected chunk_size=1024, got {config.chunk_size}"
            
            print("✅ Voice streaming config verified against StreamingConfig class")
        except ImportError:
            pytest.skip("StreamingConfig not available from cosyvoice_streaming")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
