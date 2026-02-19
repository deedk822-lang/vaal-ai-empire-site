#!/usr/bin/env python3
"""
Train MULTILINGUAL TTS for code-switching South Africa.

Key insight: Urban South Africans don't speak in pure language blocks.
They mix seamlessly. The TTS needs to handle:
- "I'm going ekhaya" (English + isiZulu)
- "Yebo, I understand" (isiZulu + English)
- "Sharp sharp, ngizokubona" (Slang + isiZulu)

Architecture: YourTTS (voice cloning) with multilingual support.
"""

import os
import json
import torch
import torchaudio
from pathlib import Path
from typing import Dict, List, Optional
from TTS.tts.configs.shared_configs import BaseDatasetConfig
from TTS.tts.datasets import load_tts_samples
from TTS.tts.models.vits import Vits
from TTS.tts.configs.vits_config import VitsConfig
from TTS.utils.audio import AudioProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultilingualTTSDatasetBuilder:
    """
    Prepare dataset for multilingual TTS training.
    
    Key difference: We DON'T separate by language.
    We train one model on all languages mixed.
    """
    
    def __init__(self, output_dir: Path = Path("data/multilingual_tts")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_metadata(self, manifest_path: Path, output_tsv: Path):
        """
        Convert multilingual manifest to TTS format.
        
        TTS format (metadata.csv):
        file_name|transcription|speaker_name
        
        We use language as speaker_name for conditioning.
        """
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        metadata = []
        
        for item in manifest:
            audio_path = item.get("audio_path", "")
            text = item.get("text", "")
            
            if not audio_path or not text:
                continue
            
            # Use primary language as "speaker" for conditioning
            language = item.get("primary_language", "unknown")
            
            # Clean text
            text = text.strip().replace("|", "")  # Remove pipe chars
            
            metadata.append({
                "file_name": audio_path,
                "text": text,
                "speaker": language,
            })
        
        # Save as TSV
        with open(output_tsv, "w", encoding="utf-8") as f:
            for m in metadata:
                f.write(f"{m['file_name']}|{m['text']}|{m['speaker']}\n")
        
        logger.info(f"Created TTS metadata: {len(metadata)} samples")
        logger.info(f"Saved to: {output_tsv}")
        
        return metadata


class MultilingualTTSTrainer:
    """
    Train multilingual TTS model.
    
    Uses VITS (Variational Inference with adversarial learning
    for end-to-end Text-to-Speech) which supports:
    - Multiple speakers (we use as multiple languages)
    - Voice cloning (speaker encoder)
    - High quality synthesis
    """
    
    def __init__(self, output_dir: Path = Path("models/multilingual_tts")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_config(self, 
                      data_path: Path,
                      num_languages: int = 5) -> VitsConfig:
        """
        Create VITS config for multilingual training.
        
        Key settings:
        - Use speaker embedding for language conditioning
        - Enable phoneme cleaners for multiple languages
        """
        
        config = VitsConfig(
            # Model architecture
            model_args={
                "use_speaker_embedding": True,
                "num_speakers": num_languages,  # One per language
                "use_sdp": True,  # Stochastic duration predictor
                "use_speaker_encoder": True,  # For voice cloning
            },
            
            # Audio settings
            audio={
                "sample_rate": 22050,
                "fft_size": 1024,
                "win_length": 1024,
                "hop_length": 256,
                "num_mels": 80,
                "mel_fmin": 0,
                "mel_fmax": None,
            },
            
            # Training settings
            batch_size=32,
            eval_batch_size=16,
            num_loader_workers=4,
            num_eval_loader_workers=4,
            
            # Optimizer
            lr_gen=2e-4,
            lr_disc=2e-4,
            
            # Training duration
            epochs=1000,
            
            # Text processing
            text_cleaner="multilingual_cleaners",
            use_phonemes=False,  # Use graphemes for African languages
            phoneme_language="en",  # Fallback
            
            # Paths
            output_path=str(self.output_dir),
        )
        
        # Dataset config
        dataset_config = BaseDatasetConfig(
            formatter="ljspeech",
            dataset_name="multilingual_sa",
            path=str(data_path),
            meta_file_train="metadata.csv",
        )
        
        config.datasets = [dataset_config]
        
        return config
    
    def train(self, data_path: Path, num_languages: int = 5):
        """
        Train the multilingual TTS model.
        
        Training process:
        1. Load datasets
        2. Initialize VITS model
        3. Train for ~1 week on GPU
        4. Save checkpoints
        """
        
        logger.info("Starting multilingual TTS training...")
        
        # Create config
        config = self.create_config(data_path, num_languages)
        
        # Initialize audio processor
        ap = AudioProcessor.init_from_config(config)
        
        # Load datasets
        train_samples, eval_samples = load_tts_samples(
            config.datasets,
            eval_split=True,
            eval_split_max_size=config.eval_split_max_size,
            eval_split_size=config.eval_split_size,
        )
        
        logger.info(f"Training samples: {len(train_samples)}")
        logger.info(f"Evaluation samples: {len(eval_samples)}")
        
        # Initialize model
        model = Vits(config, ap)
        
        # Trainer (simplified - would use TTS trainer in practice)
        logger.info("Model initialized. Starting training...")
        logger.info(f"Checkpoints will be saved to: {self.output_dir}")
        
        # In practice, would use:
        # from TTS.trainer import Trainer
        # trainer = Trainer(...)
        # trainer.fit()
        
        return model


class MultilingualTTSInference:
    """
    Inference engine for multilingual TTS.
    
    Can synthesize:
    - Pure language: "Sawubona" (isiZulu)
    - Code-switched: "I'm going ekhaya now"
    - With voice cloning: Match specific speaker
    """
    
    def __init__(self, model_path: Path, config_path: Path, device: str = "cuda"):
        """
        Load trained model.
        
        Args:
            model_path: Path to model checkpoint
            config_path: Path to config.json
            device: "cuda" or "cpu"
        """
        from TTS.tts.models.vits import Vits
        from TTS.utils.audio import AudioProcessor
        
        # Load config
        with open(config_path, "r") as f:
            import json
            config_dict = json.load(f)
        
        # Initialize
        self.ap = AudioProcessor.init_from_config(config_dict)
        self.model = Vits(config_dict, self.ap)
        
        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=device)
        self.model.load_state_dict(checkpoint["model"])
        self.model.to(device)
        self.model.eval()
        
        self.device = device
        
        # Language to speaker_id mapping
        self.language_to_speaker = {
            "zu": 0,
            "xh": 1,
            "af": 2,
            "st": 3,
            "en": 4,
        }
        
    def synthesize(self, 
                   text: str, 
                   language: str = "zu",
                   speaker_wav: Optional[Path] = None) -> torch.Tensor:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize (can be code-switched)
            language: Primary language for conditioning
            speaker_wav: Optional reference for voice cloning
            
        Returns:
            Audio waveform as torch tensor
        """
        # Preprocess text
        # In full implementation, would use phonemizer
        
        # Get speaker embedding
        if speaker_wav and hasattr(self.model, 'speaker_encoder'):
            # Compute speaker embedding from reference
            speaker_embedding = self._compute_speaker_embedding(speaker_wav)
        else:
            # Use language as speaker
            speaker_id = self.language_to_speaker.get(language, 0)
            speaker_embedding = None
        
        # Synthesize
        with torch.no_grad():
            outputs = self.model.inference(
                text,
                speaker_id=speaker_id,
                speaker_embedding=speaker_embedding,
            )
        
        waveform = outputs["wav"]
        
        return waveform
    
    def synthesize_to_file(self,
                          text: str,
                          output_path: Path,
                          language: str = "zu",
                          speaker_wav: Optional[Path] = None):
        """Synthesize and save to file."""
        
        waveform = self.synthesize(text, language, speaker_wav)
        
        # Save
        torchaudio.save(
            output_path,
            waveform.unsqueeze(0).cpu(),
            sample_rate=self.ap.sample_rate
        )
        
        logger.info(f"Saved to: {output_path}")
    
    def _compute_speaker_embedding(self, speaker_wav: Path) -> torch.Tensor:
        """Compute speaker embedding from reference audio."""
        # Load audio
        waveform, sr = torchaudio.load(speaker_wav)
        
        # Resample if needed
        if sr != self.ap.sample_rate:
            resampler = torchaudio.transforms.Resample(sr, self.ap.sample_rate)
            waveform = resampler(waveform)
        
        # Compute embedding using speaker encoder
        if hasattr(self.model, 'speaker_encoder'):
            embedding = self.model.speaker_encoder(waveform.to(self.device))
            return embedding
        else:
            return None


def demo_code_switching_synthesis():
    """Demo: Synthesize code-switched sentences."""
    
    test_sentences = [
        ("Sawubona, how are you?", "zu"),
        ("I'm going ekhaya now", "zu"),
        ("Yebo, I understand", "zu"),
        ("Can you please ngisize?", "zu"),
        ("Ewe, thank you very much", "xh"),
        ("Let's meet kusasa morning", "zu"),
    ]
    
    logger.info("Code-switching TTS Demo")
    logger.info("=" * 60)
    
    for text, lang in test_sentences:
        logger.info(f"\nText: {text}")
        logger.info(f"Primary language: {lang}")
        logger.info(f"Contains: {[l for l in ['zu', 'xh', 'af', 'en'] if l in text.lower()]}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["prepare", "train", "demo"], default="demo")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("models/multilingual_tts"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/multilingual_tts"))
    
    args = parser.parse_args()
    
    if args.action == "prepare":
        # Prepare dataset
        builder = MultilingualTTSDatasetBuilder(args.data_dir)
        builder.prepare_metadata(
            args.manifest,
            args.data_dir / "metadata.csv"
        )
    
    elif args.action == "train":
        # Train model
        trainer = MultilingualTTSTrainer(args.output_dir)
        trainer.train(args.data_dir, num_languages=5)
    
    elif args.action == "demo":
        # Demo code-switching
        demo_code_switching_synthesis()
