#!/usr/bin/env python3
"""
train.py — Vaal AI Empire
Unified training CLI: download / prepare / train-asr / train-tts.

Fixes applied (PR #117 CodeRabbit review):
 • test harness: uses --output-dir (not --cv-dir) matching download_main()
 • sys.argv is saved and restored to avoid corrupting global state
 • run_train_asr: loads multilingual_manifest.json, performs 90/10 train/eval
   split, writes multilingual_manifest_train.json and
   multilingual_manifest_eval.json, then passes split paths to trainer
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Sub-command implementations
# ─────────────────────────────────────────────

def run_download(args: argparse.Namespace) -> None:
    """Download Common Voice datasets."""
    from ml.african_languages.data.download_common_voice import download_common_voice

    languages = args.languages or ["zu", "xh", "af", "en"]
    logger.info("Downloading for languages: %s", languages)

    results = download_common_voice(
        languages=languages,
        output_dir=args.output_dir,
        cv_version=args.cv_version,
    )
    for lang, stats in results.items():
        logger.info("[%s] %s", lang, stats)


def run_prepare(args: argparse.Namespace) -> None:
    """Build the multilingual manifest with code-switching samples."""
    from ml.african_languages.data.prepare_multilingual import MultilingualDataBuilder

    source_manifests = {}
    for lang in args.languages:
        manifest_path = args.output_dir / lang / "manifest.json"
        if manifest_path.exists():
            source_manifests[lang] = manifest_path
        else:
            logger.warning("Manifest not found for %s at %s — skipping.", lang, manifest_path)

    if not source_manifests:
        logger.error("No source manifests found. Run 'download' first.")
        sys.exit(1)

    builder = MultilingualDataBuilder(
        source_manifests=source_manifests,
        output_dir=args.output_dir,
        code_switch_ratio=args.code_switch_ratio,
    )
    manifest_path = builder.build()
    logger.info("Multilingual manifest built: %s", manifest_path)


def run_train_asr(args: argparse.Namespace) -> None:
    """Fine-tune an ASR model on the multilingual manifest."""
    from ml.african_languages.training.train_multilingual_asr import MultilingualASRTrainer

    manifest_path = args.output_dir / "multilingual_manifest.json"
    if not manifest_path.exists():
        logger.error(
            "Manifest not found at %s. Run 'prepare' first.", manifest_path
        )
        sys.exit(1)

    # Load and split manifest (configurable train/eval split)
    with open(manifest_path) as f:
        all_samples = json.load(f)

    random.shuffle(all_samples)
    train_ratio = 1.0 - args.eval_split
    split_idx = int(len(all_samples) * train_ratio)
    train_samples = all_samples[:split_idx]
    eval_samples = all_samples[split_idx:]

    # Write split manifests
    train_manifest = args.output_dir / "multilingual_manifest_train.json"
    eval_manifest = args.output_dir / "multilingual_manifest_eval.json"
    with open(train_manifest, "w") as f:
        json.dump(train_samples, f)
    with open(eval_manifest, "w") as f:
        json.dump(eval_samples, f)

    logger.info("Train/eval split (%.0f%%/%.0f%%): %d / %d samples",
                train_ratio * 100, args.eval_split * 100,
                len(train_samples), len(eval_samples))

    trainer = MultilingualASRTrainer(
        model_name=args.asr_model,
        output_dir=args.output_dir / "asr_checkpoints",
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        learning_rate=args.lr,
    )
    trainer.train(
        train_manifest=train_manifest,
        eval_manifest=eval_manifest,
    )


def run_train_tts(args: argparse.Namespace) -> None:
    """Train a VITS multilingual TTS model."""
    from ml.african_languages.training.train_multilingual_tts import MultilingualTTSTrainer

    manifest_path = args.output_dir / "multilingual_manifest.json"
    if not manifest_path.exists():
        logger.error(
            "Manifest not found at %s. Run 'prepare' first.", manifest_path
        )
        sys.exit(1)

    trainer = MultilingualTTSTrainer(
        manifest_path=manifest_path,
        output_dir=args.output_dir / "tts_checkpoints",
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate_gen=args.lr,
    )
    trainer.train()


# ─────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Vaal AI Empire — African Languages ML pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── download ──
    dl = sub.add_parser("download", help="Download Common Voice datasets.")
    dl.add_argument("--output-dir", required=True, type=Path, help="Root output directory.")
    dl.add_argument("--languages", nargs="+", default=None, help="Language codes to download.")
    dl.add_argument("--cv-version", default="cv-corpus-16.1-2023-12-06")

    # ── prepare ──
    prep = sub.add_parser("prepare", help="Build multilingual manifest.")
    prep.add_argument("--output-dir", required=True, type=Path)
    prep.add_argument("--languages", nargs="+", default=["zu", "xh", "af", "en"])
    prep.add_argument("--code-switch-ratio", type=float, default=0.3)

    # ── train-asr ──
    asr = sub.add_parser("train-asr", help="Fine-tune ASR model.")
    asr.add_argument("--output-dir", required=True, type=Path)
    asr.add_argument("--asr-model", default="facebook/wav2vec2-large-xlsr-53")
    asr.add_argument("--epochs", type=int, default=10)
    asr.add_argument("--batch-size", type=int, default=8)
    asr.add_argument("--lr", type=float, default=1e-4)
    asr.add_argument("--eval-split", type=float, default=0.1)

    # ── train-tts ──
    tts = sub.add_parser("train-tts", help="Train multilingual TTS model.")
    tts.add_argument("--output-dir", required=True, type=Path)
    tts.add_argument("--epochs", type=int, default=100)
    tts.add_argument("--batch-size", type=int, default=16)
    tts.add_argument("--lr", type=float, default=1e-4)

    return parser


# ─────────────────────────────────────────────
# Entry point helpers (used by test harness)
# ─────────────────────────────────────────────

def download_main(argv: list[str] | None = None) -> None:
    """
    Programmatic entry point for the download sub-command.

    Saves and restores sys.argv to avoid corrupting global state
    when called from a test harness.
    """
    old_argv = list(sys.argv)
    try:
        args = build_parser().parse_args(["download"] + (argv or []))
        run_download(args)
    finally:
        sys.argv = old_argv


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Validate output directory is writable before starting any long operation
    output_path = getattr(args, 'output_dir', None)
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)
        if not output_path.exists() or not output_path.is_dir():
            logger.error("Output path is not a valid directory: %s", output_path)
            sys.exit(1)
        # Test write permission
        test_file = output_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            logger.error("Output directory is not writable: %s", output_path)
            sys.exit(1)

    dispatch = {
        "download":  run_download,
        "prepare":   run_prepare,
        "train-asr": run_train_asr,
        "train-tts": run_train_tts,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
