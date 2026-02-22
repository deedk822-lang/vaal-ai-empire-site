#!/usr/bin/env python3
"""
Download Mozilla Common Voice datasets for South African languages.
Common Voice is CC-0 licensed (public domain).
"""

import os
import requests
import argparse
from pathlib import Path
from tqdm import tqdm
import tarfile

# South African languages in Common Voice
LANGUAGES = {
    "zu": {
        "name": "isiZulu",
        "cv_code": "zu",
        "version": "cv-corpus-15.0-2023-09-08",
        "estimated_hours": 20,
    },
    "xh": {
        "name": "isiXhosa",
        "cv_code": "xh",
        "version": "cv-corpus-15.0-2023-09-08",
        "estimated_hours": 15,
    },
    "af": {
        "name": "Afrikaans",
        "cv_code": "af",
        "version": "cv-corpus-15.0-2023-09-08",
        "estimated_hours": 50,
    },
    "st": {
        "name": "Sesotho",
        "cv_code": "st",
        "version": "cv-corpus-15.0-2023-09-08",
        "estimated_hours": 10,
    },
    "tn": {
        "name": "Setswana",
        "cv_code": "tn",
        "version": "cv-corpus-15.0-2023-09-08",
        "estimated_hours": 8,
    },
}

BASE_URL = "https://storage.googleapis.com/common-voice-prod-prod"


def download_file(url: str, output_path: Path, chunk_size: int = 8192) -> bool:
    """Download file with progress bar."""
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        
        with open(output_path, "wb") as f, tqdm(
            desc=output_path.name,
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    """Extract tar.gz archive safely using filter='data' to prevent path traversal.

    Uses Python 3.12+ built-in protection against CVE-2007-4559.
    The filter='data' parameter prevents extraction of files outside the target
    directory by rejecting absolute paths and path traversal sequences.
    """
    try:
        print(f"Extracting {archive_path}...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_dir, filter="data")
        return True
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        return False


def download_language(lang_code: str, output_dir: Path, extract: bool = True) -> bool:
    """Download and extract Common Voice dataset for a language."""
    
    if lang_code not in LANGUAGES:
        print(f"Unknown language code: {lang_code}")
        print(f"Available: {list(LANGUAGES.keys())}")
        return False
    
    lang_info = LANGUAGES[lang_code]
    cv_code = lang_info["cv_code"]
    version = lang_info["version"]
    
    # Construct URL
    filename = f"{cv_code}.tar.gz"
    url = f"{BASE_URL}/{version}/{filename}"
    
    # Create output directory
    lang_dir = output_dir / lang_code
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    archive_path = lang_dir / filename
    
    print(f"\n{'='*60}")
    print(f"Downloading {lang_info['name']} ({lang_code})")
    print(f"Estimated size: {lang_info['estimated_hours']} hours")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    # Download
    if not download_file(url, archive_path):
        return False
    
    # Extract
    if extract:
        if not extract_archive(archive_path, lang_dir):
            return False
        
        # Remove archive to save space
        print(f"Removing archive {archive_path}...")
        archive_path.unlink()
    
    print(f"✅ {lang_info['name']} downloaded successfully!")
    return True


def verify_dataset(lang_dir: Path) -> dict:
    """Verify downloaded dataset structure."""
    stats = {
        "valid": False,
        "total_clips": 0,
        "validated_clips": 0,
        "total_hours": 0,
    }
    
    # Look for validated.tsv
    validated_tsv = lang_dir / "validated.tsv"
    if not validated_tsv.exists():
        # Try to find it in subdirectories
        for subdir in lang_dir.iterdir():
            if subdir.is_dir():
                validated_tsv = subdir / "validated.tsv"
                if validated_tsv.exists():
                    break
    
    if not validated_tsv.exists():
        print(f"Warning: validated.tsv not found in {lang_dir}")
        return stats
    
    # Count clips
    import csv
    with open(validated_tsv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            stats["validated_clips"] += 1
            if "duration" in row:
                stats["total_hours"] += float(row["duration"]) / 3600
    
    stats["valid"] = True
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Download Mozilla Common Voice datasets for South African languages"
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=list(LANGUAGES.keys()) + ["all"],
        default=["all"],
        help="Languages to download (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/common_voice"),
        help="Output directory for datasets",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Don't extract archives after download",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify downloaded datasets",
    )
    
    args = parser.parse_args()
    
    # Determine languages to download
    if "all" in args.languages:
        languages = list(LANGUAGES.keys())
    else:
        languages = args.languages
    
    print("African Language Data Pipeline")
    print("=" * 60)
    print(f"Languages: {[LANGUAGES[l]['name'] for l in languages]}")
    print(f"Output: {args.output_dir}")
    print("=" * 60)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download each language
    results = {}
    for lang_code in languages:
        success = download_language(
            lang_code,
            args.output_dir,
            extract=not args.no_extract,
        )
        results[lang_code] = success
    
    # Verify datasets
    if args.verify:
        print("\n" + "=" * 60)
        print("Verifying datasets...")
        print("=" * 60)
        
        for lang_code in languages:
            if not results[lang_code]:
                continue
            
            lang_dir = args.output_dir / lang_code
            stats = verify_dataset(lang_dir)
            
            print(f"\n{LANGUAGES[lang_code]['name']} ({lang_code}):")
            print(f"  Valid: {stats['valid']}")
            print(f"  Validated clips: {stats['validated_clips']}")
            print(f"  Total hours: {stats['total_hours']:.2f}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    for lang_code, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {LANGUAGES[lang_code]['name']} ({lang_code})")
    
    successful = sum(results.values())
    print(f"\nTotal: {successful}/{len(languages)} languages downloaded successfully")


if __name__ == "__main__":
    main()
