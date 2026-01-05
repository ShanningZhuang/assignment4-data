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


def analyze_warc_languages(warc_path: str, num_samples: int = 20, seed: int = 42):
    """Analyze language distribution in a WARC file."""
    import gzip
    import random
    from fastwarc.warc import ArchiveIterator, WarcRecordType
    from cs336_data.extract_text import extract_text_from_html_bytes

    # Extract text and identify language
    results = []
    with gzip.open(warc_path, "rb") as f:
        for record in ArchiveIterator(f, record_types=WarcRecordType.response):
            url = record.headers.get("WARC-Target-URI")
            if url and record.http_content_type and "text/html" in record.http_content_type:
                html_bytes = record.reader.read()
                text = extract_text_from_html_bytes(html_bytes)
                if text and len(text.strip()) > 50:  # Skip empty/tiny pages
                    lang, score = identify_language(text)
                    results.append((url, lang, score, text[:200]))

    # Statistics
    total = len(results)
    english_count = sum(1 for _, lang, _, _ in results if lang == "en")
    print(f"Total documents: {total}")
    print(f"English documents: {english_count} ({english_count/total*100:.1f}%)")
    print()

    # Random sample
    random.seed(seed)
    sample = random.sample(results, min(num_samples, total))

    print(f"Random sample of {len(sample)} documents:")
    print("=" * 80)
    for i, (url, lang, score, text_preview) in enumerate(sample, 1):
        domain = url.split("/")[2] if "/" in url else url
        print(f"{i}. [{lang}] score={score:.3f} | {domain}")
        print(f"   Preview: {text_preview[:100].replace(chr(10), ' ')}...")
        print()


if __name__ == "__main__":
    analyze_warc_languages("data/CC-MAIN-20250417135010-20250417165010-00065.warc.gz")

