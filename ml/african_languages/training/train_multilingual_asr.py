#!/usr/bin/env python3
"""
Train MULTILINGUAL ASR model for code-switching South Africa.

Key innovation: Single model that understands mixed-language speech,
not separate models for each language.

Architecture: Whisper-based with language-agnostic representations.
"""

import os
import json
import torch
import torchaudio
from torch.utils.data import Dataset, DataLoader
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    EarlyStoppingCallback,
)
from datasets import load_dataset
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultilingualASRDataset(Dataset):
    """
    Dataset for multilingual code-switching ASR.
    
    Unlike traditional datasets that expect one language per sample,
    this handles mixed-language utterances.
    """
    
    def __init__(self, 
                 manifest_path: Path,
                 processor: WhisperProcessor,
                 audio_dir: Path,
                 max_duration: float = 30.0):
        """
        Args:
            manifest_path: Path to multilingual_manifest.json
            processor: WhisperProcessor
            audio_dir: Base directory for audio files
            max_duration: Maximum audio duration in seconds
        """
        self.processor = processor
        self.audio_dir = audio_dir
        self.max_duration = max_duration
        
        # Load manifest
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
        
        # Filter out samples that are too long
        self.manifest = [
            m for m in self.manifest 
            if m.get("duration", 0) <= max_duration or "duration" not in m
        ]
        
        logger.info(f"Loaded {len(self.manifest)} training samples")
        
        # Calculate language mix stats
        self._log_language_stats()
    
    def _log_language_stats(self):
        """Log statistics about language distribution."""
        codeswitch_count = sum(1 for m in self.manifest if m.get("is_code_switched", False))
        logger.info(f"Code-switched samples: {codeswitch_count} ({100*codeswitch_count/len(self.manifest):.1f}%)")
        
        # Primary language distribution
        lang_counts = {}
        for m in self.manifest:
            lang = m.get("primary_language", "unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        logger.info("Primary language distribution:")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {lang}: {count} ({100*count/len(self.manifest):.1f}%)")
    
    def __len__(self):
        return len(self.manifest)
    
    def __getitem__(self, idx):
        item = self.manifest[idx]
        
        # Load audio
        audio_path = self.audio_dir / item["audio_path"]
        
        try:
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
        except Exception as e:
            logger.warning(f"Error loading {audio_path}: {e}")
            # Return dummy data
            waveform = torch.zeros(1, 16000)
        
        # Process audio
        input_features = self.processor.feature_extractor(
            waveform.squeeze().numpy(),
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features[0]
        
        # Process text (mixed language)
        text = item["text"]
        labels = self.processor.tokenizer(text).input_ids
        
        return {
            "input_features": input_features,
            "labels": labels,
            "language_mix": item.get("language_mix", {}),
            "is_code_switched": item.get("is_code_switched", False),
        }


class MultilingualASRTrainer:
    """
    Train multilingual ASR model.
    
    Key features:
    - Handles code-switching naturally
    - Language-agnostic representations
    - Evaluates on real mixed-language scenarios
    """
    
    def __init__(self,
                 model_name: str = "openai/whisper-small",
                 output_dir: Path = Path("models/multilingual_asr")):
        """
        Args:
            model_name: Base Whisper model (small = 244M params, base = 74M)
            output_dir: Where to save checkpoints
        """
        self.model_name = model_name
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load processor and model
        logger.info(f"Loading model: {model_name}")
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        
        # Configure model for multilingual
        # Don't force language token - let model decide or use mixed
        self.model.config.forced_decoder_ids = None
        
        # Enable gradient checkpointing for memory efficiency
        self.model.gradient_checkpointing_enable()
    
    def create_dataloaders(self,
                          train_manifest: Path,
                          eval_manifest: Path,
                          audio_dir: Path,
                          batch_size: int = 16) -> tuple:
        """Create training and evaluation dataloaders."""
        
        train_dataset = MultilingualASRDataset(
            train_manifest, self.processor, audio_dir
        )
        
        eval_dataset = MultilingualASRDataset(
            eval_manifest, self.processor, audio_dir
        )
        
        # Custom collate function
        def data_collator(features):
            # Pad input features
            input_features = torch.stack([f["input_features"] for f in features])
            
            # Pad labels
            labels = [f["labels"] for f in features]
            max_label_len = max(len(l) for l in labels)
            
            # Whisper uses -100 for padding
            padded_labels = torch.full(
                (len(labels), max_label_len), 
                -100, 
                dtype=torch.long
            )
            
            for i, label in enumerate(labels):
                padded_labels[i, :len(label)] = torch.tensor(label)
            
            return {
                "input_features": input_features,
                "labels": padded_labels,
            }
        
        return train_dataset, eval_dataset, data_collator
    
    def compute_metrics(self, pred) -> Dict[str, float]:
        """
        Compute WER (Word Error Rate) with special handling for code-switching.
        """
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        
        # Replace -100 with pad token id
        label_ids[label_ids == -100] = self.processor.tokenizer.pad_token_id
        
        # Decode
        pred_str = self.processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = self.processor.batch_decode(label_ids, skip_special_tokens=True)
        
        # Compute WER
        import jiwer
        wer = jiwer.wer(label_str, pred_str)
        
        # Also compute per-language WER if we have that info
        # (Would need to track language in eval dataset)
        
        return {
            "wer": wer,
            "predictions": pred_str[:3],  # Log first 3 for debugging
            "references": label_str[:3],
        }
    
    def train(self,
              train_manifest: Path,
              eval_manifest: Path,
              audio_dir: Path,
              num_epochs: int = 10,
              batch_size: int = 16,
              learning_rate: float = 1e-5):
        """
        Fine-tune the model.
        
        Training strategy:
        - Use LoRA for parameter-efficient fine-tuning
        - Mixed precision (fp16) for speed
        - Gradient accumulation for larger effective batch size
        - Early stopping based on WER
        """
        
        logger.info("Setting up training...")
        
        # Create datasets
        train_dataset, eval_dataset, data_collator = self.create_dataloaders(
            train_manifest, eval_manifest, audio_dir, batch_size
        )
        
        # Training arguments optimized for 16GB GPU
        training_args = Seq2SeqTrainingArguments(
            output_dir=str(self.output_dir),
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=2,  # Effective batch size = 32
            learning_rate=learning_rate,
            warmup_steps=500,
            max_steps=10000,
            gradient_checkpointing=True,
            fp16=True,
            eval_strategy="steps",
            eval_steps=500,
            save_strategy="steps",
            save_steps=500,
            logging_steps=100,
            logging_dir=str(self.output_dir / "logs"),
            report_to=["tensorboard"],
            load_best_model_at_end=True,
            metric_for_best_model="wer",
            greater_is_better=False,
            prediction_loss_only=False,
            generation_max_length=225,
            predict_with_generate=True,
            # Push to hub if desired
            push_to_hub=False,
        )
        
        # Initialize trainer
        trainer = Seq2SeqTrainer(
            args=training_args,
            model=self.model,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            compute_metrics=self.compute_metrics,
            tokenizer=self.processor.feature_extractor,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
        )
        
        # Train
        logger.info("Starting training...")
        trainer.train()
        
        # Save final model
        final_dir = self.output_dir / "final"
        trainer.save_model(final_dir)
        self.processor.save_pretrained(final_dir)
        
        logger.info(f"Training complete! Model saved to {final_dir}")
        
        return trainer


class MultilingualASRInference:
    """Inference engine for multilingual ASR."""
    
    def __init__(self, model_path: Path, device: str = "cuda"):
        self.processor = WhisperProcessor.from_pretrained(model_path)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_path)
        self.model.to(device)
        self.device = device
        
    def transcribe(self, audio_path: Path) -> Dict:
        """
        Transcribe audio file.
        
        Returns:
            {
                "text": "transcribed text",
                "detected_languages": ["zu", "en"],
                "confidence": 0.95
            }
        """
        # Load audio
        waveform, sample_rate = torchaudio.load(audio_path)
        
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Process
        input_features = self.processor.feature_extractor(
            waveform.squeeze().numpy(),
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features.to(self.device)
        
        # Generate
        with torch.no_grad():
            predicted_ids = self.model.generate(input_features)
        
        # Decode
        transcription = self.processor.batch_decode(
            predicted_ids, 
            skip_special_tokens=True
        )[0]
        
        # Detect languages in output
        detected_langs = self._detect_languages(transcription)
        
        return {
            "text": transcription,
            "detected_languages": detected_langs,
        }
    
    def _detect_languages(self, text: str) -> List[str]:
        """Detect which languages are present in transcription."""
        # Simple keyword-based detection
        # In production, use proper language ID model
        
        from data.prepare_multilingual import LANGUAGE_MARKERS
        
        text_lower = text.lower()
        scores = {}
        
        for lang, markers in LANGUAGE_MARKERS.items():
            matches = sum(1 for m in markers if m in text_lower)
            scores[lang] = matches
        
        # Return languages with at least one match
        detected = [lang for lang, score in scores.items() if score > 0]
        
        return detected if detected else ["en"]


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("models/multilingual_asr"))
    parser.add_argument("--model", default="openai/whisper-small")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-5)
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = MultilingualASRTrainer(
        model_name=args.model,
        output_dir=args.output_dir
    )
    
    # Train
    trainer.train(
        train_manifest=args.train_manifest,
        eval_manifest=args.eval_manifest,
        audio_dir=args.audio_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
