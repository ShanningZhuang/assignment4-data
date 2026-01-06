import fasttext

# Load models once at module level
_nsfw_model = None
_toxic_model = None


def _get_nsfw_model():
    global _nsfw_model
    if _nsfw_model is None:
        fasttext.FastText.eprint = lambda x: None
        _nsfw_model = fasttext.load_model("data/jigsaw_fasttext_bigrams_nsfw_final.bin")
    return _nsfw_model


def _get_toxic_model():
    global _toxic_model
    if _toxic_model is None:
        fasttext.FastText.eprint = lambda x: None
        _toxic_model = fasttext.load_model("data/jigsaw_fasttext_bigrams_hatespeech_final.bin")
    return _toxic_model


def classify_nsfw(text: str) -> tuple[str, float]:
    """Classify text as NSFW or not.
    
    Returns:
        A tuple of (label, confidence_score).
        Label is "nsfw" or "non-nsfw".
    """
    model = _get_nsfw_model()
    text_clean = text.replace("\n", " ")
    predictions = model.predict(text_clean, k=1)
    label = predictions[0][0].replace("__label__", "")  # "nsfw" or "non-nsfw"
    score = predictions[1][0]
    return label, float(score)


def classify_toxic_speech(text: str) -> tuple[str, float]:
    """Classify text as toxic/hate speech or not.
    
    Returns:
        A tuple of (label, confidence_score).
        Label is "toxic" or "non-toxic".
    """
    model = _get_toxic_model()
    text_clean = text.replace("\n", " ")
    predictions = model.predict(text_clean, k=1)
    label = predictions[0][0].replace("__label__", "")  # "toxic" or "non-toxic"
    score = predictions[1][0]
    return label, float(score)


def analyze_harmful_content(jsonl_path: str, output_dir: str = "data", num_samples: int = 20, seed: int = 42):
    """Analyze harmful content in documents from JSONL file."""
    import json
    import random
    from pathlib import Path

    output_path = Path(output_dir)

    # Load documents
    with open(jsonl_path, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f]

    # Classify each document
    results = []
    stats = {"nsfw": 0, "toxic": 0, "any_harmful": 0}

    for doc in docs:
        text = doc.get("text", "")
        url = doc.get("url", "")
        
        nsfw_label, nsfw_score = classify_nsfw(text)
        toxic_label, toxic_score = classify_toxic_speech(text)
        
        result = {
            "url": url,
            "nsfw_label": nsfw_label,
            "nsfw_score": nsfw_score,
            "toxic_label": toxic_label,
            "toxic_score": toxic_score,
            "text": text,
        }
        # Preserve existing fields
        if "language" in doc:
            result["language"] = doc["language"]
            result["score"] = doc.get("score")
        if "masked_text" in doc:
            result["masked_text"] = doc["masked_text"]
        
        results.append(result)
        
        if nsfw_label == "nsfw":
            stats["nsfw"] += 1
        if toxic_label == "toxic":
            stats["toxic"] += 1
        if nsfw_label == "nsfw" or toxic_label == "toxic":
            stats["any_harmful"] += 1

    total = len(results)
    print(f"Total documents: {total}")
    print(f"NSFW documents: {stats['nsfw']} ({stats['nsfw']/total*100:.1f}%)")
    print(f"Toxic documents: {stats['toxic']} ({stats['toxic']/total*100:.1f}%)")
    print(f"Any harmful: {stats['any_harmful']} ({stats['any_harmful']/total*100:.1f}%)")

    # Save results
    output_file = output_path / "harmful_content.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"\nSaved results to {output_file}")

    # Random sample
    random.seed(seed)
    harmful_docs = [r for r in results if r["nsfw_label"] == "nsfw" or r["toxic_label"] == "toxic"]
    sample = random.sample(harmful_docs, min(num_samples, len(harmful_docs)))

    print(f"\n{'='*80}")
    print(f"SAMPLE HARMFUL DOCUMENTS ({len(sample)} examples):")
    print("="*80)
    for item in sample:
        domain = item["url"].split("/")[2] if "/" in item["url"] else item["url"]
        preview = item["text"][:150].replace("\n", " ")
        print(f"\n{domain}:")
        print(f"  NSFW: {item['nsfw_label']} (score={item['nsfw_score']:.3f})")
        print(f"  Toxic: {item['toxic_label']} (score={item['toxic_score']:.3f})")
        print(f"  Preview: {preview}...")


if __name__ == "__main__":
    analyze_harmful_content("data/pii_all.jsonl")

