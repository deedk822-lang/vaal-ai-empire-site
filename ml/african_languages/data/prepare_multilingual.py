#!/usr/bin/env python3
"""
Prepare MULTILINGUAL training data for code-switching South Africa.

Urban South Africans don't speak in silos - they mix isiZulu, English, 
isiXhosa, Afrikaans, Sesotho, tsotsitaal, and slang seamlessly.

This creates training data that reflects REALITY, not textbook purity.
"""

import os
import re
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
from tqdm import tqdm

# Language mixing patterns observed in urban SA
CODE_SWITCH_PATTERNS = {
    "zulu_english": [
        ("Yebo, I understand", ["zu", "en"]),
        ("I'm going ekhaya now", ["en", "zu", "en"]),
        ("Can you please ngisize?", ["en", "zu"]),
        ("Sizani bantu, we have a problem", ["zu", "en"]),
    ],
    "xhosa_english": [
        ("Ewe, I agree", ["xh", "en"]),
        ("Let's go ekhaya", ["en", "xh"]),
        ("Please ndincede", ["en", "xh"]),
    ],
    "tsotsitaal_mix": [
        # Tsotsitaal is urban township slang that mixes everything
        ("Sharp sharp, I'm coming now now", ["slang", "en"]),
        ("Lalela here, we need to talk", ["zu", "en"]),
        ("This thing is maar expensive", ["en", "af"]),
    ],
    "workplace_mix": [
        # Professional settings
        ("The deadline is kusasa", ["en", "zu"]),
        ("We need ukuthi deliver on time", ["en", "zu", "en"]),
        ("The client is unhappy, kodwa we can fix it", ["en", "zu", "en"]),
    ],
}

LANGUAGE_MARKERS = {
    "zu": ["yebo", "cha", "ikhaya", "umama", "ubaba", "ngiyabonga", "sawubona", 
           "kunjani", "ngiyaphila", "ngisize", "lalela", "khuluma", "hamba", "woza",
           "manje", "kusasa", "izolo", "lapha", "khona", "lapho", "kanjani", "ningi"],
    "xh": ["ewe", "hayi", "ekhaya", "umama", "utata", "enkosi", "molo", "unjani",
           "ndiyaphila", "ndincede", "mamela", "thetha", "hamba", "yiza", "ngoku",
           "ngomso", "izolo", "apha", "kula", "apho", "njani", "ninzi"],
    "af": ["ja", "nee", "huis", "ma", "pa", "dankie", "hallo", "hoe gaan dit",
           "goed", "help", "luister", "praat", "gaan", "kom", "nou", "môre", "gister",
           "hier", "daar", "waar", "hoe", "baie", "maar", "nogal"],
    "st": ["ee", "tjhee", "lapeng", "mme", "ntate", "kea leboha", "dumela",
           "o phela joang", "ke phela hantle", "nthuse", "mamela", "buang", "tsamaya",
           "tloha", "hona joale", "kamora", "maobane", "mona", "moo", "fi", "joang", "ngata"],
}

SLANG_TERMS = [
    "sharp", "sharp-sharp", "now-now", "just now", "bra", "bru", "china", 
    "boet", "ousie", "gogo", "mkhulu", "tata", "cherrie", "my bru", "awe",
    "ekse", "howzit", "yebo-gogo", "mzansi", "kasie", "location", "ekasi"
]


class MultilingualDataBuilder:
    """Build realistic multilingual training data."""
    
    def __init__(self, output_dir: Path = Path("data/multilingual")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_common_voice(self, cv_dir: Path) -> Dict[str, List[Dict]]:
        """Load Common Voice data for all languages."""
        data = {}
        
        for lang_code in ["zu", "xh", "af", "st", "tn"]:
            tsv_file = cv_dir / lang_code / "validated.tsv"
            if not tsv_file.exists():
                # Try subdirectory
                subdirs = list((cv_dir / lang_code).glob("*/validated.tsv"))
                if subdirs:
                    tsv_file = subdirs[0]
            
            if tsv_file.exists():
                df = pd.read_csv(tsv_file, sep="\t")
                data[lang_code] = df.to_dict("records")
                print(f"Loaded {len(data[lang_code])} clips for {lang_code}")
            else:
                print(f"Warning: No data found for {lang_code}")
                data[lang_code] = []
        
        return data
    
    def create_synthetic_codeswitch(self, text1: str, text2: str, 
                                     lang1: str, lang2: str) -> Tuple[str, List[str]]:
        """
        Create synthetic code-switched sentence.
        
        Examples:
        - "I will go" + "ekhaya" -> "I will go ekhaya"
        - "Ngiyabonga" + "very much" -> "Ngiyabonga very much"
        """
        patterns = [
            # Pattern 1: Insert word/phrase from lang2 into lang1
            lambda t1, t2: f"{t1} {t2.split()[0] if t2 else ''}",
            # Pattern 2: Start with lang2, finish with lang1
            lambda t1, t2: f"{t2.split()[0] if t2 else ''}, {t1}",
            # Pattern 3: Lang1 with lang2 particle at end
            lambda t1, t2: f"{t1} {t2.split()[0] if t2 else ''}",
        ]
        
        pattern = random.choice(patterns)
        mixed = pattern(text1, text2)
        
        # Clean up
        mixed = re.sub(r"\s+", " ", mixed).strip()
        
        # Create language labels (simplified - word-level would be better)
        labels = [lang1, lang2]  # Sentence-level for now
        
        return mixed, labels
    
    def augment_with_codeswitching(self, data: Dict[str, List[Dict]], 
                                    num_synthetic: int = 10000) -> List[Dict]:
        """
        Create synthetic code-switched training examples.
        
        This is the KEY differentiator - we train on mixed language,
        not pure silos.
        """
        augmented = []
        
        print(f"Creating {num_synthetic} synthetic code-switched examples...")
        
        for _ in tqdm(range(num_synthetic)):
            # Pick two random languages
            lang1, lang2 = random.sample(["zu", "xh", "af", "st"], 2)
            
            if not data[lang1] or not data[lang2]:
                continue
            
            # Get random sentences
            sent1 = random.choice(data[lang1])
            sent2 = random.choice(data[lang2])
            
            text1 = sent1.get("sentence", "")
            text2 = sent2.get("sentence", "")
            
            # Create code-switched version
            mixed_text, labels = self.create_synthetic_codeswitch(
                text1, text2, lang1, lang2
            )
            
            # Use audio from primary language (lang1)
            # In production, would need to verify this makes sense
            augmented.append({
                "sentence": mixed_text,
                "path": sent1.get("path"),
                "primary_language": lang1,
                "mixed_languages": labels,
                "is_synthetic_code_switch": True,
                "original_text_1": text1,
                "original_text_2": text2,
            })
        
        return augmented
    
    def detect_language_mix(self, text: str) -> Dict:
        """
        Detect which languages are present in mixed text.
        
        Returns confidence scores for each language.
        """
        text_lower = text.lower()
        words = set(text_lower.split())
        
        scores = {}
        for lang_code, markers in LANGUAGE_MARKERS.items():
            matches = sum(1 for marker in markers if marker in words)
            scores[lang_code] = matches / max(len(words), 1)
        
        # Detect slang (substring match is appropriate for slang phrases)
        slang_matches = sum(1 for slang in SLANG_TERMS if slang in text_lower)
        scores["slang"] = slang_matches / max(len(words), 1)
        
        # Detect English (absence of markers + common English words)
        english_words = ["the", "and", "you", "that", "have", "for", "not", "with"]
        eng_matches = sum(1 for word in english_words if word in words)
        scores["en"] = eng_matches / len(english_words)
        
        return scores
    
    def create_training_manifest(self, data: Dict[str, List[Dict]], 
                                  augmented: List[Dict],
                                  output_file: Path):
        """
        Create unified training manifest.
        
        Format:
        {
            "audio_path": "...",
            "text": "mixed language sentence",
            "language_mix": {"zu": 0.6, "en": 0.4},
            "is_code_switched": true
        }
        """
        manifest = []
        
        # Add original data
        for lang_code, clips in data.items():
            for clip in clips:
                text = clip.get("sentence", "")
                if not text:
                    continue
                
                mix_scores = self.detect_language_mix(text)
                
                # Only mark as code-switched if there's actual detection and no dominant language
                max_score = max(mix_scores.values()) if mix_scores else 0
                is_code_switched = (max_score > 0) and (max_score < 0.8)
                
                manifest.append({
                    "audio_path": clip.get("path"),
                    "text": text,
                    "primary_language": lang_code,
                    "language_mix": mix_scores,
                    "is_code_switched": is_code_switched,
                })
        
        # Add synthetic code-switched data
        for clip in augmented:
            text = clip["sentence"]
            mix_scores = self.detect_language_mix(text)
            
            manifest.append({
                "audio_path": clip.get("path"),
                "text": text,
                "primary_language": clip["primary_language"],
                "language_mix": mix_scores,
                "is_code_switched": True,
                "is_synthetic": True,
            })
        
        # Save
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"Created manifest with {len(manifest)} examples")
        print(f"  - Original clips: {sum(len(v) for v in data.values())}")
        print(f"  - Synthetic code-switched: {len(augmented)}")
        
        # Stats
        codeswitch_count = sum(1 for m in manifest if m["is_code_switched"])
        if len(manifest) > 0:
            print(f"  - Total code-switched: {codeswitch_count} ({100*codeswitch_count/len(manifest):.1f}%)")
        else:
            print("  - No samples in manifest")
        
        return manifest
    
    def build(self, cv_dir: Path, num_synthetic: int = 10000):
        """Full pipeline to build multilingual training data."""
        
        print("=" * 60)
        print("Building Multilingual Training Data")
        print("Training for code-switching reality, not language silos")
        print("=" * 60)
        
        # Load Common Voice data
        print("\n1. Loading Common Voice data...")
        data = self.load_common_voice(cv_dir)
        
        # Create synthetic code-switched examples
        print("\n2. Creating synthetic code-switched data...")
        augmented = self.augment_with_codeswitching(data, num_synthetic)
        
        # Create unified manifest
        print("\n3. Creating training manifest...")
        manifest_file = self.output_dir / "multilingual_manifest.json"
        manifest = self.create_training_manifest(data, augmented, manifest_file)
        
        print("\n✅ Done! Multilingual training data ready.")
        print(f"Manifest: {manifest_file}")
        
        return manifest


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv-dir", type=Path, required=True,
                       help="Path to Common Voice data directory")
    parser.add_argument("--output-dir", type=Path, default=Path("data/multilingual"))
    parser.add_argument("--num-synthetic", type=int, default=10000,
                       help="Number of synthetic code-switched examples")
    
    args = parser.parse_args()
    
    builder = MultilingualDataBuilder(args.output_dir)
    builder.build(args.cv_dir, args.num_synthetic)


if __name__ == "__main__":
    main()
