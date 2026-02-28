#!/usr/bin/env python3
"""
Comprehensive tests for CosyVoice Streaming Voice Processor.
Tests TTS, ASR, streaming, and voice command processing.
"""

import pytest
import asyncio
import base64
import json
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "sentient_swarm"))

from cosyvoice_streaming import (
    AudioFormat,
    VoiceModel,
    StreamingConfig,
    CosyVoiceStreamingProcessor,
    VoiceCommandProcessor
)


class TestAudioFormat:
    """Test AudioFormat enum."""

    def test_audio_format_values(self):
        """Test audio format enum values."""
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.WAV.value == "wav"
        assert AudioFormat.OGG.value == "ogg"
        assert AudioFormat.WEBM.value == "webm"
        assert AudioFormat.PCM.value == "pcm"

    def test_audio_format_count(self):
        """Test expected number of audio formats."""
        assert len(AudioFormat) == 5


class TestVoiceModel:
    """Test VoiceModel enum."""

    def test_voice_model_values(self):
        """Test voice model enum values."""
        assert VoiceModel.LONGXIAOCHUN.value == "longxiaochun"
        assert VoiceModel.LONGXIAOXIA.value == "longxiaoxia"
        assert VoiceModel.LONGWAN.value == "longwan"
        assert VoiceModel.LONGYUE.value == "longyue"

    def test_voice_model_count(self):
        """Test expected number of voice models."""
        assert len(VoiceModel) == 4


class TestStreamingConfig:
    """Test StreamingConfig dataclass."""

    def test_default_config(self):
        """Test default streaming configuration."""
        config = StreamingConfig()

        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.format == AudioFormat.MP3
        assert config.chunk_size_ms == 100
        assert config.buffer_size == 10
        assert config.language == "en-ZA"
        assert config.voice == VoiceModel.LONGXIAOCHUN
        assert config.enable_code_switching is True

    def test_custom_config(self):
        """Test custom streaming configuration."""
        config = StreamingConfig(
            sample_rate=48000,
            format=AudioFormat.WAV,
            language="zu-ZA",
            voice=VoiceModel.LONGWAN
        )

        assert config.sample_rate == 48000
        assert config.format == AudioFormat.WAV
        assert config.language == "zu-ZA"
        assert config.voice == VoiceModel.LONGWAN


class TestCosyVoiceStreamingProcessorInit:
    """Test CosyVoiceStreamingProcessor initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key-123")

        assert processor.api_key == "test-key-123"
        assert isinstance(processor.config, StreamingConfig)
        assert processor.total_tts_requests == 0
        assert processor.total_asr_requests == 0

    def test_init_without_api_key(self):
        """Test initialization without API key (uses env var)."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "env-key"}):
            processor = CosyVoiceStreamingProcessor()
            assert processor.api_key == "env-key"

    def test_init_no_api_key_warning(self):
        """Test warning when no API key is set."""
        with patch.dict(os.environ, {}, clear=True):
            processor = CosyVoiceStreamingProcessor()
            assert processor.api_key is None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        custom_config = StreamingConfig(
            sample_rate=48000,
            language="af-ZA"
        )
        processor = CosyVoiceStreamingProcessor(
            api_key="test-key",
            config=custom_config
        )

        assert processor.config.sample_rate == 48000
        assert processor.config.language == "af-ZA"

    def test_supported_languages(self):
        """Test that SA_LANGUAGES contains expected languages."""
        expected_langs = ["en-ZA", "zu-ZA", "xh-ZA", "af-ZA", "st-ZA"]

        for lang in expected_langs:
            assert lang in CosyVoiceStreamingProcessor.SA_LANGUAGES


class TestSynthesizeComplete:
    """Test complete (non-streaming) synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_complete_success(self):
        """Test successful complete synthesis."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake_audio_data")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize_complete(
                text="Hello world",
                language="en-ZA",
                consent_ref="test-consent-123"
            )

        assert result["status"] == "success"
        assert result["audio_data"] == b"fake_audio_data"
        assert "audio_base64" in result
        assert result["format"] == "mp3"
        assert result["duration_ms"] > 0
        assert "audit" in result
        assert result["audit"]["consent_reference"] == "test-consent-123"

    @pytest.mark.asyncio
    async def test_synthesize_complete_no_api_key(self):
        """Test synthesis without API key."""
        processor = CosyVoiceStreamingProcessor(api_key=None)

        result = await processor.synthesize_complete(text="Hello")

        assert result["status"] == "error"
        assert "DASHSCOPE_API_KEY" in result["message"]

    @pytest.mark.asyncio
    async def test_synthesize_complete_api_error(self):
        """Test synthesis with API error."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad request error")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize_complete(text="Hello")

        assert result["status"] == "error"
        assert "Bad request" in result["message"]

    @pytest.mark.asyncio
    async def test_synthesize_complete_with_custom_voice(self):
        """Test synthesis with custom voice model."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"audio")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize_complete(
                text="Test",
                voice=VoiceModel.LONGWAN
            )

        assert result["status"] == "success"


class TestSynthesizeStreaming:
    """Test streaming synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_streaming_success(self):
        """Test successful streaming synthesis."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Mock streaming response
        mock_response = AsyncMock()
        mock_response.status = 200

        async def mock_iter_chunked(size):
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        chunks = []
        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            async for chunk in processor.synthesize_streaming(
                text="Hello streaming world",
                consent_ref="stream-consent"
            ):
                chunks.append(chunk)

        assert len(chunks) > 0
        assert b"chunk1" in chunks

    @pytest.mark.asyncio
    async def test_synthesize_streaming_no_api_key(self):
        """Test streaming synthesis without API key."""
        processor = CosyVoiceStreamingProcessor(api_key=None)

        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            async for _ in processor.synthesize_streaming(text="Hello"):
                pass

    @pytest.mark.asyncio
    async def test_synthesize_streaming_long_text(self):
        """Test streaming synthesis with long text (sentence splitting)."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        long_text = "First sentence. Second sentence. Third sentence."

        mock_response = AsyncMock()
        mock_response.status = 200

        async def mock_iter():
            yield b"audio"

        mock_response.content.iter_chunked = lambda x: mock_iter()

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        chunks = []
        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            async for chunk in processor.synthesize_streaming(text=long_text):
                chunks.append(chunk)

        # Should have called API multiple times for different sentences
        assert len(chunks) > 0


class TestTranscribeComplete:
    """Test complete (non-streaming) transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_complete_success(self):
        """Test successful complete transcription."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        audio_data = b"fake_audio_bytes"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "output": {
                "text": "Transcribed text",
                "detected_language": "en-ZA",
                "words": []
            }
        })

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.transcribe_complete(
                audio_data=audio_data,
                consent_ref="transcribe-consent"
            )

        assert result["status"] == "success"
        assert result["text"] == "Transcribed text"
        assert result["language"] == "en-ZA"
        assert "audit" in result

    @pytest.mark.asyncio
    async def test_transcribe_complete_no_api_key(self):
        """Test transcription without API key."""
        processor = CosyVoiceStreamingProcessor(api_key=None)

        result = await processor.transcribe_complete(audio_data=b"audio")

        assert result["status"] == "error"
        assert "DASHSCOPE_API_KEY" in result["message"]

    @pytest.mark.asyncio
    async def test_transcribe_complete_api_error(self):
        """Test transcription with API error."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server error")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.transcribe_complete(audio_data=b"audio")

        assert result["status"] == "error"


class TestTranscribeBase64:
    """Test base64 audio transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_base64_success(self):
        """Test successful base64 transcription."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        audio_base64 = base64.b64encode(b"audio_data").decode('utf-8')

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "output": {"text": "Result", "detected_language": "en-ZA", "words": []}
        })

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.transcribe_base64(audio_base64=audio_base64)

        assert result["status"] == "success"
        assert result["text"] == "Result"

    @pytest.mark.asyncio
    async def test_transcribe_base64_invalid(self):
        """Test transcription with invalid base64."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        result = await processor.transcribe_base64(audio_base64="not-valid-base64!!!")

        assert result["status"] == "error"
        assert "Invalid base64" in result["message"]


class TestTranscribeStreaming:
    """Test streaming transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_streaming_success(self):
        """Test successful streaming transcription."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Mock audio stream
        async def audio_generator():
            yield b"chunk1"
            yield b"chunk2"

        mock_response = AsyncMock()
        mock_response.status = 200

        async def mock_content_iter():
            yield b'{"output": {"text": "partial", "is_final": false}}'
            yield b'{"output": {"text": "final text", "is_final": true}}'

        mock_response.content.__aiter__ = mock_content_iter

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        results = []
        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            async for result in processor.transcribe_streaming(
                audio_stream=audio_generator(),
                consent_ref="stream-consent"
            ):
                results.append(result)

        assert len(results) > 0
        assert any(r.get("is_final") for r in results)

    @pytest.mark.asyncio
    async def test_transcribe_streaming_no_api_key(self):
        """Test streaming transcription without API key."""
        processor = CosyVoiceStreamingProcessor(api_key=None)

        async def audio_gen():
            yield b"audio"

        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            async for _ in processor.transcribe_streaming(audio_stream=audio_gen()):
                pass

    @pytest.mark.asyncio
    async def test_transcribe_streaming_api_error(self):
        """Test streaming transcription with API error."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        async def audio_gen():
            yield b"audio"

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad request")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(Exception):
                async for _ in processor.transcribe_streaming(audio_stream=audio_gen()):
                    pass


class TestSplitTextForStreaming:
    """Test text splitting for streaming."""

    def test_split_simple_sentences(self):
        """Test splitting simple sentences."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        text = "First sentence. Second sentence. Third sentence."
        sentences = processor._split_text_for_streaming(text)

        assert len(sentences) >= 3
        assert "First sentence" in sentences[0]

    def test_split_long_sentence(self):
        """Test splitting very long sentence."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Create a long sentence with commas
        text = "This is a very long sentence, " * 20 + "with many clauses."
        sentences = processor._split_text_for_streaming(text)

        # Should split long sentences
        assert len(sentences) > 1

    def test_split_empty_text(self):
        """Test splitting empty text."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        sentences = processor._split_text_for_streaming("")

        assert len(sentences) == 0

    def test_split_mixed_punctuation(self):
        """Test splitting with mixed punctuation."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        text = "Question? Exclamation! Statement. Chinese。"
        sentences = processor._split_text_for_streaming(text)

        assert len(sentences) >= 3


class TestGetMetrics:
    """Test metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_initial_state(self):
        """Test initial metrics state."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        metrics = processor.get_metrics()

        assert metrics["total_tts_requests"] == 0
        assert metrics["total_asr_requests"] == 0
        assert metrics["avg_tts_latency_ms"] == 0
        assert metrics["avg_asr_latency_ms"] == 0
        assert metrics["target_latency_ms"] == 500

    @pytest.mark.asyncio
    async def test_metrics_after_tts(self):
        """Test metrics after TTS requests."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"audio")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            await processor.synthesize_complete(text="Test")

        metrics = processor.get_metrics()

        assert metrics["total_tts_requests"] == 1
        assert metrics["avg_tts_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_metrics_sla_check(self):
        """Test SLA checking in metrics."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Manually set metrics
        processor.total_tts_requests = 1
        processor.total_tts_latency_ms = 300  # Within SLA

        metrics = processor.get_metrics()

        assert metrics["tts_within_sla"] is True


class TestVoiceCommandProcessor:
    """Test VoiceCommandProcessor."""

    def test_init(self):
        """Test VoiceCommandProcessor initialization."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()

        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        assert processor.cosyvoice == cosyvoice
        assert processor.consent_manager == consent_manager
        assert len(processor._session_contexts) == 0

    @pytest.mark.asyncio
    async def test_process_voice_input_new_session(self):
        """Test processing voice input with new session."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()

        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        # Mock transcribe_complete
        async def mock_transcribe(audio_data, language, consent_ref):
            return {
                "status": "success",
                "text": "Hello world",
                "language": language
            }

        cosyvoice.transcribe_complete = mock_transcribe

        result = await processor.process_voice_input(
            audio_data=b"audio",
            user_id="user123",
            language="en-ZA"
        )

        assert result["status"] == "success"
        assert result["text"] == "Hello world"
        assert "session_id" in result
        assert result["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_process_voice_input_existing_session(self):
        """Test processing voice input with existing session."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()

        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        async def mock_transcribe(audio_data, language, consent_ref):
            return {"status": "success", "text": "Message", "language": language}

        cosyvoice.transcribe_complete = mock_transcribe

        # First call creates session
        result1 = await processor.process_voice_input(
            audio_data=b"audio1",
            user_id="user123",
            session_id="session-abc"
        )

        # Second call uses existing session
        result2 = await processor.process_voice_input(
            audio_data=b"audio2",
            user_id="user123",
            session_id="session-abc"
        )

        assert result2["turn_count"] == 2

    @pytest.mark.asyncio
    async def test_generate_voice_response(self):
        """Test generating voice response."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()

        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        # Mock synthesize_complete
        async def mock_synthesize(text, language, consent_ref):
            return {
                "status": "success",
                "audio_data": b"response_audio"
            }

        cosyvoice.synthesize_complete = mock_synthesize

        result = await processor.generate_voice_response(
            text="Response text",
            user_id="user123",
            session_id="session-abc",
            language="en-ZA"
        )

        assert result["status"] == "success"
        assert result["audio_data"] == b"response_audio"

    def test_session_lru_eviction(self):
        """Test LRU eviction of old sessions."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()
        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        # Create MAX_SESSIONS + 1 sessions
        for i in range(processor.MAX_SESSIONS + 1):
            session_id = f"session-{i}"
            processor._session_contexts[session_id] = {
                "user_id": f"user{i}",
                "history": []
            }
            processor._prune_sessions()

        # Should have exactly MAX_SESSIONS
        assert len(processor._session_contexts) == processor.MAX_SESSIONS

    def test_get_session_context(self):
        """Test getting session context."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()
        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        processor._session_contexts["session-123"] = {"user_id": "user", "history": []}

        context = processor.get_session_context("session-123")
        assert context is not None
        assert context["user_id"] == "user"

        # Non-existent session
        context = processor.get_session_context("session-999")
        assert context is None

    def test_clear_session(self):
        """Test clearing a session."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()
        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        processor._session_contexts["session-123"] = {"user_id": "user", "history": []}

        result = processor.clear_session("session-123")
        assert result is True
        assert "session-123" not in processor._session_contexts

        # Clear non-existent session
        result = processor.clear_session("session-999")
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_text_synthesis(self):
        """Test synthesis with empty text."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize_complete(text="")

        # Should handle empty text gracefully
        assert "status" in result

    @pytest.mark.asyncio
    async def test_very_long_text_synthesis(self):
        """Test synthesis with very long text."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        long_text = "test " * 1000

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"audio")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch('cosyvoice_streaming.aiohttp.ClientSession', return_value=mock_session):
            result = await processor.synthesize_complete(text=long_text)

        assert result["status"] == "success"

    def test_invalid_language_code(self):
        """Test handling of invalid language code."""
        processor = CosyVoiceStreamingProcessor(api_key="test-key")

        # Should not crash with invalid language
        config = StreamingConfig(language="invalid-lang")
        processor_custom = CosyVoiceStreamingProcessor(
            api_key="test-key",
            config=config
        )

        assert processor_custom.config.language == "invalid-lang"

    @pytest.mark.asyncio
    async def test_history_cap_enforcement(self):
        """Test that history is capped at MAX_HISTORY_PER_SESSION."""
        cosyvoice = CosyVoiceStreamingProcessor(api_key="test-key")
        consent_manager = Mock()
        processor = VoiceCommandProcessor(cosyvoice, consent_manager)

        async def mock_transcribe(audio_data, language, consent_ref):
            return {"status": "success", "text": "Message", "language": language}

        cosyvoice.transcribe_complete = mock_transcribe

        # Create many turns
        session_id = "test-session"
        for i in range(processor.MAX_HISTORY_PER_SESSION + 10):
            await processor.process_voice_input(
                audio_data=b"audio",
                user_id="user",
                session_id=session_id
            )

        context = processor.get_session_context(session_id)
        assert len(context["history"]) <= processor.MAX_HISTORY_PER_SESSION


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])