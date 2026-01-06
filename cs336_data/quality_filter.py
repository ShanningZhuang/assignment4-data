import re


def gopher_quality_filter(text: str) -> bool:
    """Apply Gopher quality filters to text.
    
    Returns True if text passes all quality filters, False otherwise.
    
    Filters (from Gopher paper Appendix A):
    1. Word count: 50 <= words <= 100,000
    2. Mean word length: 3 <= mean <= 10 characters
    3. Ellipsis lines: <= 30% of lines end with "..."
    4. Alphabetic words: >= 80% of words contain at least one alphabetic character
    """
    # Tokenize into words (split on whitespace)
    words = text.split()
    
    if not words:
        return False
    
    # Filter 1: Word count (50 to 100,000)
    word_count = len(words)
    if word_count < 50 or word_count > 100000:
        return False
    
    # Filter 2: Mean word length (3 to 10 characters)
    total_length = sum(len(word) for word in words)
    mean_word_length = total_length / word_count
    if mean_word_length < 3 or mean_word_length > 10:
        return False
    
    # Filter 3: Lines ending with ellipsis (<= 30%)
    lines = text.split("\n")
    if lines:
        ellipsis_lines = sum(1 for line in lines if line.rstrip().endswith("..."))
        ellipsis_ratio = ellipsis_lines / len(lines)
        if ellipsis_ratio > 0.3:
            return False
    
    # Filter 4: Words with at least one alphabetic character (>= 80%)
    alpha_words = sum(1 for word in words if any(c.isalpha() for c in word))
    alpha_ratio = alpha_words / word_count
    if alpha_ratio < 0.8:
        return False
    
    return True


def analyze_quality_filter(jsonl_path: str, output_dir: str = "data", num_samples: int = 20, seed: int = 42):
    """Analyze quality filtering on documents from JSONL file."""
    import json
    import random
    from pathlib import Path

    output_path = Path(output_dir)

    # Load documents
    with open(jsonl_path, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f]

    # Apply filter to each document
    results = []
    passed = 0
    failed = 0

    for doc in docs:
        text = doc.get("text", "")
        url = doc.get("url", "")
        
        passes = gopher_quality_filter(text)
        
        result = {
            "url": url,
            "passes_quality": passes,
            "text": text,
        }
        # Preserve existing fields
        for key in ["language", "score", "masked_text"]:
            if key in doc:
                result[key] = doc[key]
        
        results.append(result)
        if passes:
            passed += 1
        else:
            failed += 1

    total = len(results)
    print(f"Total documents: {total}")
    print(f"Passed quality filter: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed quality filter: {failed} ({failed/total*100:.1f}%)")

    # Save results
    output_file = output_path / "quality_filtered.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"\nSaved results to {output_file}")

    # Random sample of failed documents
    random.seed(seed)
    failed_docs = [r for r in results if not r["passes_quality"]]
    passed_docs = [r for r in results if r["passes_quality"]]
    
    sample_failed = random.sample(failed_docs, min(num_samples // 2, len(failed_docs)))
    sample_passed = random.sample(passed_docs, min(num_samples // 2, len(passed_docs)))

    print(f"\n{'='*80}")
    print(f"SAMPLE FAILED DOCUMENTS ({len(sample_failed)} examples):")
    print("="*80)
    for item in sample_failed:
        domain = item["url"].split("/")[2] if "/" in item["url"] else item["url"]
        text = item["text"]
        words = text.split()
        word_count = len(words)
        mean_len = sum(len(w) for w in words) / max(1, word_count)
        lines = text.split("\n")
        ellipsis_pct = sum(1 for l in lines if l.rstrip().endswith("...")) / max(1, len(lines)) * 100
        alpha_pct = sum(1 for w in words if any(c.isalpha() for c in w)) / max(1, word_count) * 100
        
        preview = text[:150].replace("\n", " ")
        print(f"\n{domain}:")
        print(f"  Words: {word_count}, Mean len: {mean_len:.1f}, Ellipsis: {ellipsis_pct:.1f}%, Alpha: {alpha_pct:.1f}%")
        print(f"  Preview: {preview}...")

    print(f"\n{'='*80}")
    print(f"SAMPLE PASSED DOCUMENTS ({len(sample_passed)} examples):")
    print("="*80)
    for item in sample_passed:
        domain = item["url"].split("/")[2] if "/" in item["url"] else item["url"]
        text = item["text"]
        words = text.split()
        word_count = len(words)
        mean_len = sum(len(w) for w in words) / max(1, word_count)
        
        preview = text[:150].replace("\n", " ")
        print(f"\n{domain}:")
        print(f"  Words: {word_count}, Mean len: {mean_len:.1f}")
        print(f"  Preview: {preview}...")


if __name__ == "__main__":
    analyze_quality_filter("data/harmful_content.jsonl")


