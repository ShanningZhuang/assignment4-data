"""
Clean data pipeline - filters documents to produce high-quality training data.

Filters applied:
1. Language: Keep only specified languages (default: English)
2. Harmful content: Remove NSFW and toxic documents
3. Quality: Apply Gopher quality heuristics
4. PII: Optionally mask personally identifiable information
"""

import argparse
import json
from pathlib import Path

from cs336_data.language_identification import identify_language
from cs336_data.harmful_content import classify_nsfw, classify_toxic_speech
from cs336_data.quality_filter import gopher_quality_filter
from cs336_data.mask_pii import mask_all_pii


def clean_document(
    doc: dict,
    allowed_languages: set[str],
    mask_pii: bool,
    apply_quality_filter: bool,
    min_words: int | None,
) -> dict | None:
    """
    Apply all filters to a document.
    
    Returns the cleaned document if it passes all filters, None otherwise.
    """
    text = doc.get("text", "")
    if not text.strip():
        return None
    
    # Language filter
    if "language" in doc:
        lang = doc["language"]
        lang_score = doc.get("score", 1.0)
    else:
        lang, lang_score = identify_language(text)
    
    if lang not in allowed_languages:
        return None
    
    # Harmful content filter
    if "nsfw_label" in doc:
        nsfw_label = doc["nsfw_label"]
        toxic_label = doc["toxic_label"]
    else:
        nsfw_label, _ = classify_nsfw(text)
        toxic_label, _ = classify_toxic_speech(text)
    
    if nsfw_label == "nsfw" or toxic_label == "toxic":
        return None
    
    # Quality filter
    if apply_quality_filter:
        if "passes_quality" in doc:
            passes = doc["passes_quality"]
        else:
            passes = gopher_quality_filter(text)
        if not passes:
            return None
    
    # Min words filter (optional additional constraint)
    if min_words is not None:
        word_count = len(text.split())
        if word_count < min_words:
            return None
    
    # PII masking
    if mask_pii:
        if "masked_text" in doc:
            clean_text = doc["masked_text"]
        else:
            clean_text, _ = mask_all_pii(text)
    else:
        clean_text = text
    
    # Build output document
    return {
        "url": doc.get("url", ""),
        "text": clean_text,
        "language": lang,
        "language_score": lang_score,
    }


def clean_data(
    input_path: str,
    output_path: str,
    languages: list[str] = None,
    mask_pii: bool = True,
    apply_quality_filter: bool = True,
    min_words: int | None = None,
):
    """
    Process input JSONL and write cleaned documents to output.
    """
    if languages is None:
        languages = ["en"]
    allowed_languages = set(languages)
    
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    # Load all documents
    with open(input_file, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f]
    
    total = len(docs)
    cleaned = []
    stats = {
        "total": total,
        "language_filtered": 0,
        "harmful_filtered": 0,
        "quality_filtered": 0,
        "passed": 0,
    }
    
    print(f"Processing {total} documents...")
    
    for i, doc in enumerate(docs):
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{total}...")
        
        text = doc.get("text", "")
        if not text.strip():
            continue
        
        # Track which filter rejected (for stats)
        # Language check
        if "language" in doc:
            lang = doc["language"]
        else:
            lang, _ = identify_language(text)
        
        if lang not in allowed_languages:
            stats["language_filtered"] += 1
            continue
        
        # Harmful content check
        if "nsfw_label" in doc:
            nsfw_label = doc["nsfw_label"]
            toxic_label = doc["toxic_label"]
        else:
            nsfw_label, _ = classify_nsfw(text)
            toxic_label, _ = classify_toxic_speech(text)
        
        if nsfw_label == "nsfw" or toxic_label == "toxic":
            stats["harmful_filtered"] += 1
            continue
        
        # Quality check
        if apply_quality_filter:
            if "passes_quality" in doc:
                passes = doc["passes_quality"]
            else:
                passes = gopher_quality_filter(text)
            if not passes:
                stats["quality_filtered"] += 1
                continue
        
        # Min words check
        if min_words is not None:
            word_count = len(text.split())
            if word_count < min_words:
                stats["quality_filtered"] += 1
                continue
        
        # PII masking
        if mask_pii:
            if "masked_text" in doc:
                clean_text = doc["masked_text"]
            else:
                clean_text, _ = mask_all_pii(text)
        else:
            clean_text = text
        
        # Build output document
        cleaned.append({
            "url": doc.get("url", ""),
            "text": clean_text,
            "language": lang,
        })
        stats["passed"] += 1
    
    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        for item in cleaned:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    # Print statistics
    print("\n" + "=" * 60)
    print("CLEANING RESULTS")
    print("=" * 60)
    print(f"Total input documents:    {stats['total']}")
    print(f"Filtered by language:     {stats['language_filtered']} ({stats['language_filtered']/stats['total']*100:.1f}%)")
    print(f"Filtered by harmful:      {stats['harmful_filtered']} ({stats['harmful_filtered']/stats['total']*100:.1f}%)")
    print(f"Filtered by quality:      {stats['quality_filtered']} ({stats['quality_filtered']/stats['total']*100:.1f}%)")
    print(f"Final clean documents:    {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    print(f"\nOutput saved to: {output_file}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean data by applying language, harmful content, and quality filters."
    )
    parser.add_argument(
        "--input", "-i",
        default="data/language_ids.jsonl",
        help="Input JSONL file (default: data/language_ids.jsonl)"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/cleaned_data.jsonl",
        help="Output JSONL file (default: data/cleaned_data.jsonl)"
    )
    parser.add_argument(
        "--languages", "-l",
        default="en",
        help="Comma-separated list of allowed language codes (default: en)"
    )
    parser.add_argument(
        "--no-mask-pii",
        action="store_true",
        help="Don't mask PII in output (default: mask PII)"
    )
    parser.add_argument(
        "--no-quality-filter",
        action="store_true",
        help="Skip quality filtering (default: apply quality filter)"
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=None,
        help="Minimum word count (in addition to quality filter)"
    )
    
    args = parser.parse_args()
    
    languages = [lang.strip() for lang in args.languages.split(",")]
    
    clean_data(
        input_path=args.input,
        output_path=args.output,
        languages=languages,
        mask_pii=not args.no_mask_pii,
        apply_quality_filter=not args.no_quality_filter,
        min_words=args.min_words,
    )


if __name__ == "__main__":
    main()
