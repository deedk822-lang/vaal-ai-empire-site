#!/usr/bin/env python3
"""
Multilingual Voice Agent - Production Integration with Ollama

This is the KEY differentiator: One agent that handles 
CODE-SWITCHING South African speech, not language silos.

Competitors build: isiZulu bot, isiXhosa bot, English bot (separate)
We build: One bot that understands "I'm going ekhaya now"

Features:
- Ollama primary (free, unlimited, low latency)
- DashScope fallback (cloud backup with free tier)
- Automatic language detection and code-switching support
- Qwen2.5 native multilingual support (100+ languages)
"""

import asyncio
import base64
import io
import os
import logging
from pathlib import Path
from typing import ClassVar, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# APEX: Optional heavy ML dependencies - gracefully degrade in CI/test environments
try:
    import torch
    import torchaudio
    from transformers import pipeline
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None
    torchaudio = None
    pipeline = None

from .base_agent import BaseAgent

# Configure logging
logger = logging.getLogger(__name__)

# Import ModelRouter for Ollama + DashScope fallback
try:
    from agents.lib.model_router import ModelRouter, classify_task
    MODEL_ROUTER_AVAILABLE = True
except ImportError:
    MODEL_ROUTER_AVAILABLE = False
    logger.warning("ModelRouter not available - using default LLM client")


@dataclass
class LanguageDetectionResult:
    """Result of language detection on utterance."""
    primary_language: str
    language_mix: Dict[str, float]
    is_code_switched: bool
    confidence: float


@dataclass
class VoiceInteractionResult:
    """Result of voice interaction."""
    query_text: str
    response_text: str
    detected_languages: List[str]
    audio_response: Optional[str]  # base64 encoded
    is_code_switched: bool


class MultilingualVoiceAgent(BaseAgent):
    """
    Voice interface for code-switching South Africa.
    
    Unlike traditional voice agents that require language selection,
    this agent automatically detects and handles mixed-language input.
    
    Example interactions:
    - User: "Ngifuna ukubhalisa ibhizinisi" (pure isiZulu)
    - User: "I want to register a business" (pure English)
    - User: "Can you please ngisize?" (mixed - THIS IS THE REALITY)
    
    All handled seamlessly.
    """
    
    # Language configuration
    SUPPORTED_LANGUAGES: ClassVar[Dict[str, Dict[str, str]]] = {
        "zu": {"name": "isiZulu", "greeting": "Sawubona"},
        "xh": {"name": "isiXhosa", "greeting": "Molo"},
        "af": {"name": "Afrikaans", "greeting": "Hallo"},
        "st": {"name": "Sesotho", "greeting": "Dumela"},
        "en": {"name": "English", "greeting": "Hello"},
    }
    
    # Code-switching patterns we expect
    COMMON_MIXES: ClassVar[List[Tuple[str, str]]] = [
        ("en", "zu"),  # English + isiZulu (most common in urban SA)
        ("zu", "en"),
        ("en", "xh"),  # English + isiXhosa
        ("xh", "en"),
        ("af", "en"),  # Afrikaans + English
        ("zu", "af"),  # isiZulu + Afrikaans (less common but exists)
    ]
    
    def __init__(self, 
                 llm_client=None, 
                 metrics=None, 
                 tracer=None,
                 asr_model_path: Optional[Path] = None,
                 tts_model_path: Optional[Path] = None,
                 use_ollama: bool = True):
        super().__init__("MultilingualVoice", llm_client, metrics, tracer)
        
        # Model paths
        self.asr_model_path = asr_model_path or Path("models/multilingual_asr/final")
        self.tts_model_path = tts_model_path or Path("models/multilingual_tts")
        
        # Lazy-loaded models
        self._asr_pipeline = None
        self._tts_model = None
        self._audio_processor = None
        
        # Thread-safe lazy loading locks
        self._asr_lock = asyncio.Lock()
        self._tts_lock = asyncio.Lock()
        
        # Language detection thresholds
        self.CODESWITCH_THRESHOLD = 0.3  # If secondary language > 30%, it's code-switched
        
        # Initialize ModelRouter for Ollama + DashScope fallback
        self.use_ollama = use_ollama and MODEL_ROUTER_AVAILABLE
        self._model_router = None
        
        if self.use_ollama and MODEL_ROUTER_AVAILABLE:
            try:
                self._model_router = ModelRouter()
                logger.info("MultilingualVoiceAgent initialized with Ollama + DashScope fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize ModelRouter: {e}")
                self._model_router = None
        else:
            logger.info("MultilingualVoiceAgent initialized (using default LLM client)")
        
        self.log("MultilingualVoiceAgent initialized (code-switching enabled)")
    
    async def _load_asr(self):
        """Lazy-load ASR model with thread-safe locking."""
        async with self._asr_lock:
            if self._asr_pipeline is None:
                if not _TORCH_AVAILABLE:
                    raise RuntimeError("torch/torchaudio not installed. Install with: pip install torch torchaudio transformers")
                self.log(f"Loading ASR model from {self.asr_model_path}")
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Load model in thread pool to avoid blocking event loop
                def _load_model():
                    return pipeline(
                        "automatic-speech-recognition",
                        model=str(self.asr_model_path),
                        tokenizer=str(self.asr_model_path),
                        feature_extractor=str(self.asr_model_path),
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                        device=device,
                    )
                
                self._asr_pipeline = await asyncio.to_thread(_load_model)
                self.log(f"ASR model loaded on {device}")
    
    async def _load_tts(self):
        """Lazy-load TTS model with thread-safe locking."""
        async with self._tts_lock:
            if self._tts_model is None:
                if not _TORCH_AVAILABLE:
                    raise RuntimeError("torch not installed. Install with: pip install torch torchaudio transformers")
                try:
                    device = 0 if torch.cuda.is_available() else -1
                    self.log(f"Loading TTS model from {self.tts_model_path}")

                    def _load_tts_model():
                        return pipeline(
                            "text-to-speech",
                            model=str(self.tts_model_path) if self.tts_model_path.exists() else "facebook/mms-tts-eng",
                            device=device
                        )

                    self._tts_model = await asyncio.to_thread(_load_tts_model)
                    self.log("TTS model loaded successfully")
                except (OSError, RuntimeError) as e:
                    self.log(f"TTS model load failed: {e!s}", level="error")
                    self._tts_model = None
                    raise
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle multilingual voice interaction.
        
        Context:
        {
            "action": "stt" | "tts" | "chat" | "detect_language",
            "audio_base64": "...",  # for stt/chat
            "text": "...",  # for tts/chat
            "language_hint": "zu",  # optional hint
            "context": "business_registration"  # domain context
        }
        """
        action = context.get("action", "chat")
        
        if action == "stt":
            return await self._speech_to_text(context)
        elif action == "tts":
            return await self._text_to_speech(context)
        elif action == "chat":
            return await self._voice_chat(context)
        elif action == "detect_language":
            return await self._detect_language(context)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def _speech_to_text(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert speech to text with automatic language detection.
        
        Key feature: Handles code-switching naturally.
        Returns both transcription AND language analysis.
        """
        await self._load_asr()
        
        audio_b64 = context.get("audio_base64")
        if not audio_b64:
            return {"error": "No audio provided"}
        
        # Decode audio
        try:
            audio_bytes = base64.b64decode(audio_b64)
            audio_buffer = io.BytesIO(audio_bytes)
            
            # Load with torchaudio
            waveform, sample_rate = torchaudio.load(audio_buffer)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            
        except (ValueError, OSError) as e:
            return {"error": f"Audio decoding failed: {e!s}"}
        
        # Transcribe
        try:
            result = self._asr_pipeline(
                waveform.squeeze().numpy(),
                return_timestamps=True,
            )
            
            text = result["text"]
            
            # Detect languages in transcription
            lang_detection = self._analyze_language_mix(text)
            
            return {
                "text": text,
                "language_detection": {
                    "primary": lang_detection.primary_language,
                    "mix": lang_detection.language_mix,
                    "is_code_switched": lang_detection.is_code_switched,
                    "confidence": lang_detection.confidence,
                },
                "chunks": result.get("chunks", []),  # Word-level timestamps
            }
            
        except (RuntimeError, ValueError) as e:
            return {"error": f"Transcription failed: {e!s}"}
    
    async def _text_to_speech(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert text to speech.

        Handles code-switched text by:
        1. Detecting language switches in text
        2. Using appropriate prosody for each segment
        3. Or using multilingual model that handles mixing naturally
        """
        text = context.get("text")
        if not text:
            return {"error": "No text provided"}

        # Detect primary language
        lang_detection = self._analyze_language_mix(text)
        primary_lang = lang_detection.primary_language

        # Synthesize
        try:
            await self._load_tts()

            if self._tts_model is None:
                return {"error": "TTS model unavailable"}

            # Run TTS in thread pool to avoid blocking
            result = await asyncio.to_thread(self._tts_model, text)

            # Extract audio data
            audio_array = result.get("audio", result.get("waveform", np.array([])))
            sample_rate = result.get("sampling_rate", result.get("sample_rate", 22050))

            # Convert numpy array to base64 WAV
            import wave
            buf = io.BytesIO()
            if isinstance(audio_array, np.ndarray):
                audio_int16 = (audio_array * 32767).astype(np.int16)
            else:
                audio_int16 = np.array(audio_array, dtype=np.int16)

            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())

            audio_b64 = base64.b64encode(buf.getvalue()).decode()

            return {
                "audio_base64": audio_b64,
                "format": "wav",
                "sample_rate": sample_rate,
                "primary_language": primary_lang,
                "detected_mix": lang_detection.language_mix,
            }

        except (RuntimeError, ValueError) as e:
            self.log(f"TTS synthesis error: {e!s}", level="error")
            return {"error": f"{e!s}"}
    
    async def _voice_chat(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full voice conversation: ASR -> LLM -> TTS
        
        This is the main use case - user speaks in any language mix,
        gets spoken response in appropriate language.
        """
        # 1. Speech to text
        stt_result = await self._speech_to_text(context)
        
        if "error" in stt_result:
            return stt_result
        
        query_text = stt_result["text"]
        lang_info = stt_result["language_detection"]
        
        # 2. Get LLM response
        # The prompt should acknowledge the language mix
        system_prompt = self._create_multilingual_prompt(lang_info)
        
        llm_response = await self._get_llm_response(
            query=query_text,
            system_prompt=system_prompt,
            context=context.get("context", "general")
        )
        
        # 3. Text to speech
        tts_context = {
            "action": "tts",
            "text": llm_response,
            "language_hint": lang_info["primary"],
        }
        tts_result = await self._text_to_speech(tts_context)

        # Log TTS errors but don't fail the whole interaction
        tts_error = tts_result.get("error")
        if tts_error:
            self.log(f"TTS synthesis failed: {tts_error}", level="warning")

        # Combine results
        return {
            "query_text": query_text,
            "response_text": llm_response,
            "response_audio": tts_result.get("audio_base64"),
            "tts_error": tts_error,  # Propagate TTS error to caller
            "detected_languages": list(lang_info["mix"].keys()),
            "is_code_switched": lang_info["is_code_switched"],
            "confidence": lang_info["confidence"],
        }
    
    async def _detect_language(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Just detect language of text without full STT/TTS.
        Useful for routing or analytics.
        """
        text = context.get("text", "")
        if not text:
            return {"error": "No text provided"}
        
        detection = self._analyze_language_mix(text)
        
        return {
            "text": text,
            "primary_language": detection.primary_language,
            "language_mix": detection.language_mix,
            "is_code_switched": detection.is_code_switched,
            "confidence": detection.confidence,
        }
    
    def _analyze_language_mix(self, text: str) -> LanguageDetectionResult:
        """
        Analyze which languages are present in text.
        
        This is key to handling code-switching.
        We look for language markers and calculate proportions.
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        if not words:
            return LanguageDetectionResult(
                primary_language="unknown",
                language_mix={},
                is_code_switched=False,
                confidence=0.0
            )
        
        # Language markers (from prepare_multilingual.py)
        language_markers = {
            "zu": ["yebo", "cha", "ikhaya", "umama", "ubaba", "ngiyabonga", 
                   "sawubona", "kunjani", "ngiyaphila", "ngisize", "lalela"],
            "xh": ["ewe", "hayi", "ekhaya", "umama", "utata", "enkosi",
                   "molo", "unjani", "ndiyaphila", "ndincede", "mamela"],
            "af": ["ja", "nee", "huis", "ma", "pa", "dankie", "hallo",
                   "hoe gaan dit", "goed", "help", "luister", "praat", "maar"],
            "st": ["ee", "tjhee", "lapeng", "mme", "ntate", "kea leboha",
                   "dumela", "o phela joang", "ke phela hantle", "nthuse"],
            "en": ["the", "and", "you", "that", "have", "for", "with", 
                   "this", "but", "from", "they", "she", "he"],
        }
        
        # Count markers for each language
        # Use hybrid matching: word-boundary for single tokens, substring for phrases
        scores = {}
        for lang, markers in language_markers.items():
            matches = sum(
                1 for marker in markers
                if (' ' in marker and marker in text_lower)  # phrase: substring OK
                or (' ' not in marker and marker in words)   # single word: exact match
            )
            # Normalize by number of markers to avoid bias
            scores[lang] = matches / max(len(markers), 1)
        
        # Also check word-level presence
        word_scores = {}
        for lang, markers in language_markers.items():
            word_matches = sum(1 for word in words if word in markers)
            word_scores[lang] = word_matches / len(words)
        
        # Combine scores
        combined_scores = {}
        for lang in scores:
            combined_scores[lang] = (scores[lang] * 0.5 + word_scores[lang] * 0.5)
        
        # Determine primary and secondary
        sorted_langs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_langs[0][0] if sorted_langs else "unknown"
        secondary_score = sorted_langs[1][1] if len(sorted_langs) > 1 else 0
        
        # Determine if code-switched
        is_code_switched = secondary_score > self.CODESWITCH_THRESHOLD
        
        # Calculate confidence
        total_score = sum(combined_scores.values())
        confidence = sorted_langs[0][1] / total_score if total_score > 0 else 0
        
        return LanguageDetectionResult(
            primary_language=primary,
            language_mix=combined_scores,
            is_code_switched=is_code_switched,
            confidence=confidence
        )
    
    def _create_multilingual_prompt(self, lang_info: Dict) -> str:
        """
        Create system prompt that acknowledges language context.
        
        This helps the LLM respond appropriately to code-switched input.
        """
        primary = lang_info.get("primary", "en")
        is_mixed = lang_info.get("is_code_switched", False)
        
        base_prompt = "You are a helpful assistant for South African SMEs."
        
        if is_mixed:
            # User is code-switching - acknowledge it
            base_prompt += (
                f" The user is speaking in a mix of languages, primarily "
                f"{self.SUPPORTED_LANGUAGES.get(primary, {}).get('name', primary)}. "
                f"Respond naturally - you can use English or mix appropriately, "
                f"but prioritize clarity."
            )
        else:
            # Pure language
            lang_name = self.SUPPORTED_LANGUAGES.get(primary, {}).get('name', primary)
            base_prompt += f" The user is speaking in {lang_name}."
            
            # Add specific guidance
            if primary == "zu":
                base_prompt += " Use respectful forms (ningi vs. wena) appropriately."
            elif primary == "xh":
                base_prompt += " Use appropriate click sounds in responses if relevant."
        
        return base_prompt
    
    async def _get_llm_response(self, query: str, system_prompt: str, context: str) -> str:
        """
        Get response from LLM with Ollama primary + DashScope fallback.
        
        Strategy:
        - Use ModelRouter for automatic failover (Ollama -> DashScope)
        - Select optimal model based on task type
        - Qwen2.5 for multilingual support (100+ languages)
        """
        # Try ModelRouter first (Ollama primary with DashScope fallback)
        if self._model_router is not None:
            try:
                # Classify task for optimal model selection
                task_type = classify_task(query) if 'classify_task' in dir() else 'multilingual'
                model = self._model_router.get_model_for_task('multilingual')
                
                # Build messages
                enriched_prompt = f"{system_prompt}\n\nContext: {context}" if context else system_prompt
                messages = [
                    {"role": "system", "content": enriched_prompt},
                    {"role": "user", "content": query}
                ]
                
                # Get response with automatic failover
                response = self._model_router.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=500
                )
                
                return response["choices"][0]["message"]["content"].strip()
                
            except Exception as e:
                logger.warning(f"ModelRouter failed: {e}, falling back to default LLM")
                # Fall through to default LLM
        
        # Fallback to default LLM client
        if self.llm:
            enriched_prompt = f"{system_prompt}\n\nContext: {context}" if context else system_prompt
            response = await self.llm.generate(
                prompt=query,
                system_message=enriched_prompt,
                temperature=0.7,
                max_tokens=500
            )
            return response.content
        
        # No LLM available
        return "Ngiyaxolisa, akuwazi ukuphendula. (Sorry, I cannot respond at this time.)"


# API endpoint examples
"""
POST /api/v1/voice/chat
Content-Type: application/json

{
    "audio_base64": "...base64_encoded_audio...",
    "context": "business_registration",
    "language_hint": "zu"
}

Response:
{
    "query_text": "Can you please ngisize ngebhizinisi?",
    "response_text": "Yebo, ngizokusiza. Do you have your ID document?",
    "detected_languages": ["en", "zu"],
    "is_code_switched": true,
    "confidence": 0.89,
    "response_audio": "...base64_encoded_audio..."
}

Note how both query and response naturally mix languages - 
this is how real South Africans communicate!
"""
