#!/usr/bin/env python3
"""
CosyVoice Streaming Voice Processor
Phase 1 - Sentient Financial Sentinel

Real-time voice streaming for South African languages with <500ms latency.
Supports code-switching between English and indigenous languages.

APEX Security Framework v2.0 Compliant:
- Invariant #1: Credentials never logged
- Invariant #2: Auth verified per-request
- Invariant #7: Full audit trail

Author: Vaal AI Empire
License: Proprietary
"""

import os
import json
import asyncio
import time
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator, List
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats for streaming."""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    WEBM = "webm"
    PCM = "pcm"  # Raw PCM for real-time streaming


class VoiceModel(Enum):
    """Available CosyVoice voice models."""
    LONGXIAOCHUN = "longxiaochun"  # Female, warm, professional
    LONGXIAOXIA = "longxiaoxia"    # Female, youthful, energetic
    LONGWAN = "longwan"            # Male, mature, authoritative
    LONGYUE = "longyue"            # Female, gentle, caring


@dataclass
class StreamingConfig:
    """Configuration for streaming voice processing."""
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.MP3
    chunk_size_ms: int = 100  # 100ms chunks for real-time streaming
    buffer_size: int = 10     # Number of chunks to buffer
    language: str = "en-ZA"
    voice: VoiceModel = VoiceModel.LONGXIAOCHUN
    enable_code_switching: bool = True


class CosyVoiceStreamingProcessor:
    """
    CosyVoice-v3-plus streaming voice processor with real-time capabilities.

    Features:
    - <500ms latency for South African languages
    - Code-switching support (English + Zulu/Xhosa/etc.)
    - Streaming TTS (text-to-speech) with chunking
    - Streaming ASR (speech-to-text) with real-time results
    - WebSocket-ready for real-time communication
    """

    # South African language support
    SA_LANGUAGES = {
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

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[StreamingConfig] = None
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.config = config or StreamingConfig()

        # API endpoints
        self.tts_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts"
        self.asr_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr"
        self.streaming_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/streaming"

        # Metrics tracking
        self.total_tts_requests = 0
        self.total_asr_requests = 0
        self.total_tts_latency_ms = 0
        self.total_asr_latency_ms = 0

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY not set - voice features disabled")
        else:
            logger.info("CosyVoice streaming processor initialized", extra={
                "language": self.config.language,
                "voice": self.config.voice.value,
                "sample_rate": self.config.sample_rate
            })

    async def synthesize_streaming(
        self,
        text: str,
        language: Optional[str] = None,
        voice: Optional[VoiceModel] = None,
        consent_ref: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech in real-time chunks.

        Yields audio chunks as they're generated for <500ms latency.

        Args:
            text: Text to synthesize
            language: Target language (defaults to config)
            voice: Voice model (defaults to config)
            consent_ref: POPIA consent reference

        Yields:
            Audio data chunks (MP3 format by default)
        """
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY not set")

        start_time = time.time()
        request_id = f"tts-{uuid4().hex[:8]}"
        lang = language or self.config.language
        voice_model = voice or self.config.voice

        logger.info("Streaming TTS started", extra={
            "request_id": request_id,
            "text_length": len(text),
            "language": lang
        })

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # For long texts, split into sentences for streaming
                sentences = self._split_text_for_streaming(text)

                for sentence in sentences:
                    if not sentence.strip():
                        continue

                    payload = {
                        "model": "cosyvoice-v3-plus",
                        "input": {"text": sentence},
                        "parameters": {
                            "voice": voice_model.value,
                            "language": lang,
                            "format": self.config.format.value,
                            "sample_rate": self.config.sample_rate,
                            "streaming": True
                        }
                    }

                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "enable"
                    }

                    async with session.post(
                        self.tts_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            # Stream the audio data
                            async for chunk in response.content.iter_chunked(4096):
                                yield chunk
                        else:
                            error = await response.text()
                            logger.error(f"TTS chunk failed: {error[:200]}")

        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")
            raise

        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self.total_tts_requests += 1
            self.total_tts_latency_ms += duration_ms

            logger.info("Streaming TTS completed", extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "consent_ref": consent_ref
            })

    async def synthesize_complete(
        self,
        text: str,
        language: Optional[str] = None,
        voice: Optional[VoiceModel] = None,
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize complete audio (non-streaming).

        Args:
            text: Text to synthesize
            language: Target language
            voice: Voice model
            consent_ref: POPIA consent reference

        Returns:
            Complete audio data with metadata
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "DASHSCOPE_API_KEY not set"
            }

        start_time = time.time()
        request_id = f"tts-{uuid4().hex[:8]}"
        lang = language or self.config.language
        voice_model = voice or self.config.voice

        audit = {
            "action": "tts_synthesis",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "language": lang,
            "voice": voice_model.value,
            "text_length": len(text),
            "consent_reference": consent_ref
        }

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "cosyvoice-v3-plus",
                    "input": {"text": text},
                    "parameters": {
                        "voice": voice_model.value,
                        "language": lang,
                        "format": self.config.format.value,
                        "sample_rate": self.config.sample_rate
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
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        duration_ms = int((time.time() - start_time) * 1000)

                        self.total_tts_requests += 1
                        self.total_tts_latency_ms += duration_ms

                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["audio_size_bytes"] = len(audio_data)

                        logger.info("TTS synthesis completed", extra={
                            "request_id": request_id,
                            "duration_ms": duration_ms
                        })

                        return {
                            "status": "success",
                            "audio_data": audio_data,
                            "audio_base64": base64.b64encode(audio_data).decode('utf-8'),
                            "format": self.config.format.value,
                            "sample_rate": self.config.sample_rate,
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
            logger.error(f"TTS synthesis failed: {e}")
            audit["status"] = "error"
            audit["error"] = str(e)[:200]

            return {
                "status": "error",
                "message": str(e)[:200],
                "audit": audit
            }

    async def transcribe_streaming(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: Optional[str] = None,
        consent_ref: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Transcribe streaming audio in real-time.

        Yields partial transcription results as audio is processed.

        Args:
            audio_stream: Async generator of audio chunks
            language: Source language (auto-detected if not specified)
            consent_ref: POPIA consent reference

        Yields:
            Partial transcription results with metadata
        """
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY not set")

        start_time = time.time()
        request_id = f"asr-{uuid4().hex[:8]}"
        lang = language or self.config.language

        logger.info("Streaming ASR started", extra={
            "request_id": request_id,
            "language": lang
        })

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Paraformer-v2 streaming endpoint
                async with session.post(
                    self.streaming_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/octet-stream"
                    },
                    data=audio_stream
                ) as response:
                    async for line in response.content:
                        if line:
                            try:
                                result = json.loads(line)
                                partial_text = result.get("output", {}).get("text", "")
                                is_final = result.get("output", {}).get("is_final", False)

                                yield {
                                    "request_id": request_id,
                                    "text": partial_text,
                                    "is_final": is_final,
                                    "language": lang,
                                    "duration_ms": int((time.time() - start_time) * 1000)
                                }

                                if is_final:
                                    break

                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Streaming ASR failed: {e}")
            raise

        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self.total_asr_requests += 1
            self.total_asr_latency_ms += duration_ms

            logger.info("Streaming ASR completed", extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "consent_ref": consent_ref
            })

    async def transcribe_complete(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe complete audio (non-streaming).

        Supports code-switching between South African languages.

        Args:
            audio_data: Raw audio bytes
            language: Source language (auto-detected if not specified)
            consent_ref: POPIA consent reference

        Returns:
            Transcription result with metadata
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "DASHSCOPE_API_KEY not set"
            }

        start_time = time.time()
        request_id = f"asr-{uuid4().hex[:8]}"
        lang = language or self.config.language

        audit = {
            "action": "asr_transcription",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "language": lang,
            "audio_size_bytes": len(audio_data),
            "consent_reference": consent_ref
        }

        try:
            import aiohttp

            # Encode audio as base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "paraformer-v2",
                    "input": {"audio": audio_base64},
                    "parameters": {
                        "language": lang,
                        "format": "auto",
                        "enable_code_switching": self.config.enable_code_switching,
                        "enable_words": True,  # Word-level timestamps
                        "enable_punctuation": True
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
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        duration_ms = int((time.time() - start_time) * 1000)

                        text = result.get("output", {}).get("text", "")
                        detected_language = result.get("output", {}).get("detected_language", lang)
                        words = result.get("output", {}).get("words", [])

                        self.total_asr_requests += 1
                        self.total_asr_latency_ms += duration_ms

                        audit["status"] = "success"
                        audit["duration_ms"] = duration_ms
                        audit["text_length"] = len(text)
                        audit["detected_language"] = detected_language

                        logger.info("ASR transcription completed", extra={
                            "request_id": request_id,
                            "duration_ms": duration_ms,
                            "text_length": len(text),
                            "detected_language": detected_language
                        })

                        return {
                            "status": "success",
                            "text": text,
                            "language": detected_language,
                            "words": words,
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
            logger.error(f"ASR transcription failed: {e}")
            audit["status"] = "error"
            audit["error"] = str(e)[:200]

            return {
                "status": "error",
                "message": str(e)[:200],
                "audit": audit
            }

    async def transcribe_base64(
        self,
        audio_base64: str,
        language: Optional[str] = None,
        consent_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe base64-encoded audio.

        Convenience method for audio already in base64 format.

        Args:
            audio_base64: Base64-encoded audio data
            language: Source language
            consent_ref: POPIA consent reference

        Returns:
            Transcription result
        """
        audio_data = base64.b64decode(audio_base64)
        return await self.transcribe_complete(audio_data, language, consent_ref)

    def _split_text_for_streaming(self, text: str) -> List[str]:
        """
        Split text into sentences for streaming synthesis.

        Optimized for natural speech breaks in South African languages.
        """
        import re

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)

        # For very long sentences, split on commas/clauses
        result = []
        for sentence in sentences:
            if len(sentence) > 200:
                # Split on commas for long sentences
                clauses = re.split(r'(?<=[,，])\s+', sentence)
                result.extend(clauses)
            else:
                result.append(sentence)

        return [s.strip() for s in result if s.strip()]

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        avg_tts_latency = (
            self.total_tts_latency_ms / self.total_tts_requests
            if self.total_tts_requests > 0 else 0
        )
        avg_asr_latency = (
            self.total_asr_latency_ms / self.total_asr_requests
            if self.total_asr_requests > 0 else 0
        )

        return {
            "total_tts_requests": self.total_tts_requests,
            "total_asr_requests": self.total_asr_requests,
            "avg_tts_latency_ms": round(avg_tts_latency, 2),
            "avg_asr_latency_ms": round(avg_asr_latency, 2),
            "target_latency_ms": 500,
            "tts_within_sla": avg_tts_latency < 500 if avg_tts_latency > 0 else None,
            "asr_within_sla": avg_asr_latency < 500 if avg_asr_latency > 0 else None
        }


class VoiceCommandProcessor:
    """
    High-level voice command processor for the Sentient Financial Sentinel.

    Integrates CosyVoice streaming with the financial sentinel for
    real-time voice-based financial interactions.
    """

    def __init__(
        self,
        cosyvoice: CosyVoiceStreamingProcessor,
        consent_manager: Any  # ConsentManager from sentinel_core
    ):
        self.cosyvoice = cosyvoice
        self.consent_manager = consent_manager
        self._session_contexts: Dict[str, Dict[str, Any]] = {}

    async def process_voice_input(
        self,
        audio_data: bytes,
        user_id: str,
        session_id: Optional[str] = None,
        language: str = "en-ZA"
    ) -> Dict[str, Any]:
        """
        Process voice input and return transcription with context.

        Args:
            audio_data: Raw audio bytes
            user_id: User identifier
            session_id: Optional session ID for context continuity
            language: Expected language

        Returns:
            Transcription with session context
        """
        # Generate or retrieve session context
        if not session_id:
            session_id = f"session-{uuid4().hex[:8]}"

        if session_id not in self._session_contexts:
            self._session_contexts[session_id] = {
                "user_id": user_id,
                "language": language,
                "turn_count": 0,
                "history": []
            }

        context = self._session_contexts[session_id]

        # Transcribe audio
        result = await self.cosyvoice.transcribe_complete(
            audio_data=audio_data,
            language=language,
            consent_ref=f"voice-session-{session_id}"
        )

        if result["status"] == "success":
            # Update session context
            context["turn_count"] += 1
            context["history"].append({
                "role": "user",
                "text": result["text"],
                "timestamp": datetime.utcnow().isoformat()
            })

            result["session_id"] = session_id
            result["turn_count"] = context["turn_count"]

        return result

    async def generate_voice_response(
        self,
        text: str,
        user_id: str,
        session_id: str,
        language: str = "en-ZA"
    ) -> Dict[str, Any]:
        """
        Generate voice response for text.

        Args:
            text: Response text
            user_id: User identifier
            session_id: Session ID for context
            language: Target language

        Returns:
            Audio response with metadata
        """
        if session_id in self._session_contexts:
            context = self._session_contexts[session_id]
            context["history"].append({
                "role": "assistant",
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })

        return await self.cosyvoice.synthesize_complete(
            text=text,
            language=language,
            consent_ref=f"voice-session-{session_id}"
        )

    async def streaming_voice_conversation(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        user_id: str,
        language: str = "en-ZA"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Full-duplex streaming voice conversation.

        Yields partial results as the conversation progresses.

        Args:
            audio_stream: Streaming audio input
            user_id: User identifier
            language: Expected language

        Yields:
            Partial transcription and response chunks
        """
        session_id = f"stream-{uuid4().hex[:8]}"

        # Transcribe streaming
        async for partial in self.cosyvoice.transcribe_streaming(
            audio_stream,
            language=language,
            consent_ref=f"stream-{session_id}"
        ):
            partial["session_id"] = session_id
            yield partial

            # When final transcription received, could trigger synthesis here
            if partial.get("is_final"):
                # Mark end of transcription phase
                yield {
                    "session_id": session_id,
                    "phase": "transcription_complete",
                    "text": partial.get("text", "")
                }

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context for a given session ID."""
        return self._session_contexts.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear a session context."""
        if session_id in self._session_contexts:
            del self._session_contexts[session_id]
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point for testing CosyVoice streaming."""
    import argparse

    parser = argparse.ArgumentParser(description="CosyVoice Streaming Processor")
    parser.add_argument("--tts", type=str, help="Text to synthesize")
    parser.add_argument("--asr", type=str, help="Audio file path to transcribe")
    parser.add_argument("--language", type=str, default="en-ZA", help="Language code")
    parser.add_argument("--voice", type=str, default="longxiaochun", help="Voice model")
    parser.add_argument("--output", type=str, help="Output file for TTS")
    parser.add_argument("--metrics", action="store_true", help="Show performance metrics")
    args = parser.parse_args()

    processor = CosyVoiceStreamingProcessor()

    if args.metrics:
        print(json.dumps(processor.get_metrics(), indent=2))
        return

    if args.tts:
        print(f"Synthesizing: {args.tts[:50]}...")
        result = await processor.synthesize_complete(
            text=args.tts,
            language=args.language,
            voice=VoiceModel(args.voice)
        )

        if result["status"] == "success":
            if args.output:
                with open(args.output, "wb") as f:
                    f.write(result["audio_data"])
                print(f"Audio saved to: {args.output}")
            else:
                print(f"Generated {len(result['audio_data'])} bytes of audio")
                print(f"Duration: {result['duration_ms']}ms")
        else:
            print(f"Error: {result['message']}")

    elif args.asr:
        print(f"Transcribing: {args.asr}")
        with open(args.asr, "rb") as f:
            audio_data = f.read()

        result = await processor.transcribe_complete(
            audio_data=audio_data,
            language=args.language
        )

        if result["status"] == "success":
            print(f"Transcription: {result['text']}")
            print(f"Detected language: {result.get('language', args.language)}")
            print(f"Duration: {result['duration_ms']}ms")
        else:
            print(f"Error: {result['message']}")

    else:
        print("CosyVoice Streaming Processor ready.")
        print("Use --tts 'text' to synthesize speech")
        print("Use --asr 'file' to transcribe audio")
        print("Use --metrics to show performance metrics")


if __name__ == "__main__":
    asyncio.run(main())
