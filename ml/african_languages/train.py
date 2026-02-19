#!/usr/bin/env python3
"""
Unified training script for African Language Engine.

Usage:
    # Download data
    python train.py --stage download --cv-dir data/common_voice
    
    # Prepare multilingual dataset
    python train.py --stage prepare --cv-dir data/common_voice
    
    # Train ASR
    python train.py --stage train-asr
    
    # Train TTS
    python train.py --stage train-tts
    
    # Full pipeline
    python train.py --stage all --cv-dir data/common_voice
"""

import argparse
import sys
from pathlib import Path


def run_download(cv_dir: Path):
    """Download Common Voice datasets."""
    print("=" * 60)
    print("Stage 1: Downloading Common Voice Data")
    print("=" * 60)
    
    from data.download_common_voice import main as download_main
    
    sys.argv = [
        "download_common_voice",
        "--cv-dir", str(cv_dir),
        "--languages", "all",
        "--verify"
    ]
    download_main()


def run_prepare(cv_dir: Path):
    """Prepare multilingual training data."""
    print("\n" + "=" * 60)
    print("Stage 2: Preparing Multilingual Dataset")
    print("=" * 60)
    
    from data.prepare_multilingual import MultilingualDataBuilder
    
    builder = MultilingualDataBuilder()
    builder.build(cv_dir, num_synthetic=10000)


def run_train_asr():
    """Train ASR model."""
    print("\n" + "=" * 60)
    print("Stage 3: Training Multilingual ASR")
    print("=" * 60)
    
    from training.train_multilingual_asr import MultilingualASRTrainer
    
    trainer = MultilingualASRTrainer(
        model_name="openai/whisper-small",
        output_dir=Path("models/multilingual_asr")
    )
    
    # Note: Requires train/eval manifests from prepare stage
    trainer.train(
        train_manifest=Path("data/multilingual/multilingual_manifest_train.json"),
        eval_manifest=Path("data/multilingual/multilingual_manifest_eval.json"),
        audio_dir=Path("data/common_voice"),
        num_epochs=10,
        batch_size=16
    )


def run_train_tts():
    """Train TTS model."""
    print("\n" + "=" * 60)
    print("Stage 4: Training Multilingual TTS")
    print("=" * 60)
    
    from training.train_multilingual_tts import MultilingualTTSTrainer
    
    trainer = MultilingualTTSTrainer(
        output_dir=Path("models/multilingual_tts")
    )
    
    trainer.train(
        data_path=Path("data/multilingual_tts"),
        num_languages=5
    )


def run_demo():
    """Run demo of code-switching capabilities."""
    print("\n" + "=" * 60)
    print("Demo: Code-switching Synthesis")
    print("=" * 60)
    
    test_phrases = [
        ("Sawubona, how are you doing today?", "zu"),
        ("I'm going ekhaya now to see umama", "zu"),
        ("Can you please ngisize with this?", "zu"),
        ("Yebo, I understand completely", "zu"),
        ("Let's meet at the shop after work", "en"),
        ("Ewe, ndiyabonga kakhulu", "xh"),
        ("The price is maar too expensive", "af"),
        ("Sharp sharp, I'll see you now now", "slang"),
    ]
    
    print("\nTest phrases that show code-switching reality:")
    print("-" * 60)
    
    for text, primary_lang in test_phrases:
        print(f"\nText: \"{text}\"")
        print(f"Primary: {primary_lang}")
        
        # Detect language mix
        words = text.lower().split()
        markers = {
            "zu": ["sawubona", "ekhaya", "umama", "ngisize", "yebo"],
            "xh": ["ewe", "ndiyabonga", "kakhulu"],
            "af": ["maar"],
            "en": ["how", "are", "you", "going", "can", "please"],
        }
        
        detected = []
        for lang, marker_list in markers.items():
            if any(m in words for m in marker_list):
                detected.append(lang)
        
        print(f"Detected mix: {detected}")
        print(f"Code-switched: {len(detected) > 1}")


def main():
    parser = argparse.ArgumentParser(
        description="Train African Language Engine"
    )
    parser.add_argument(
        "--stage",
        choices=["download", "prepare", "train-asr", "train-tts", "all", "demo"],
        default="demo",
        help="Training stage to run"
    )
    parser.add_argument(
        "--cv-dir",
        type=Path,
        default=Path("data/common_voice"),
        help="Common Voice data directory"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AFRICAN LANGUAGE ENGINE - Training Pipeline")
    print("Building for code-switching reality, not language silos")
    print("=" * 60)
    
    if args.stage == "download":
        run_download(args.cv_dir)
    
    elif args.stage == "prepare":
        run_prepare(args.cv_dir)
    
    elif args.stage == "train-asr":
        run_train_asr()
    
    elif args.stage == "train-tts":
        run_train_tts()
    
    elif args.stage == "all":
        run_download(args.cv_dir)
        run_prepare(args.cv_dir)
        run_train_asr()
        run_train_tts()
    
    elif args.stage == "demo":
        run_demo()
    
    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
