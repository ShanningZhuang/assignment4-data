import fasttext

# Load the model once at module level
_model = None


def _get_model():
    global _model
    if _model is None:
        # Suppress FastText warning about deprecated load_model
        fasttext.FastText.eprint = lambda x: None
        _model = fasttext.load_model("data/lid.176.bin")
    return _model


def identify_language(text: str) -> tuple[str, float]:
    """Identify the main language in a Unicode string.
    
    Returns:
        A tuple of (language_code, confidence_score).
        Language code is a 2-letter ISO 639-1 code (e.g., "en", "zh").
        Confidence score is between 0 and 1.
    """
    model = _get_model()
    # FastText expects single line, replace newlines with spaces
    text_clean = text.replace("\n", " ")
    predictions = model.predict(text_clean, k=1)
    # predictions is ([labels], [scores])
    label = predictions[0][0]  # e.g., "__label__en"
    score = predictions[1][0]  # confidence score
    # Strip "__label__" prefix to get language code
    lang_code = label.replace("__label__", "")
    return lang_code, float(score)


def analyze_languages(jsonl_path: str, output_dir: str = "data", num_samples: int = 20, seed: int = 42):
    """Analyze language distribution from extracted WARC documents."""
    import json
    import random
    from pathlib import Path
    from collections import Counter

    output_path = Path(output_dir)

    # Load extractions
    with open(jsonl_path, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f]

    # Identify language for each document
    results = []
    for doc in docs:
        text = doc["text"]
        url = doc["url"]
        lang, score = identify_language(text)
        results.append({
            "url": url,
            "language": lang,
            "score": float(score),
            "text": text,
        })

    # Statistics
    total = len(results)
    lang_counts = Counter(r["language"] for r in results)
    english_count = lang_counts.get("en", 0)
    
    print(f"Total documents: {total}")
    print(f"English documents: {english_count} ({english_count/total*100:.1f}%)")
    print(f"\nTop 10 languages:")
    for lang, count in lang_counts.most_common(10):
        print(f"  {lang}: {count} ({count/total*100:.1f}%)")

    # Save all results to JSONL
    output_file = output_path / "language_ids.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"\nSaved language identification results to {output_file}")

    # Random sample
    random.seed(seed)
    sample = random.sample(results, min(num_samples, total))

    print(f"\nRandom sample of {len(sample)} documents:")
    print("=" * 80)
    for i, item in enumerate(sample, 1):
        domain = item["url"].split("/")[2] if "/" in item["url"] else item["url"]
        preview = item["text"][:100].replace("\n", " ")
        print(f"{i}. [{item['language']}] score={item['score']:.3f} | {domain}")
        print(f"   Preview: {preview}...")
        print()


if __name__ == "__main__":
    analyze_languages("data/warc_extractions.jsonl")

