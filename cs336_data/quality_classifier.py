"""
Quality classifier using fastText.

Train a binary classifier to distinguish high-quality (Wikipedia) from 
low-quality (Common Crawl) text.
"""

import fasttext
from pathlib import Path

# Model path
MODEL_PATH = Path("data/quality_classifier.bin")

# Global model cache
_model = None


def _get_model():
    """Load the trained quality classifier model."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Quality classifier model not found at {MODEL_PATH}. "
                "Run: uv run python -m cs336_data.quality_classifier train"
            )
        fasttext.FastText.eprint = lambda x: None
        _model = fasttext.load_model(str(MODEL_PATH))
    return _model


def classify_quality(text: str) -> tuple[str, float]:
    """
    Classify text as high-quality (wiki) or low-quality (cc).
    
    Args:
        text: The text to classify.
        
    Returns:
        A tuple of (label, confidence_score).
        Label is "wiki" (high quality) or "cc" (low quality/Common Crawl).
        Confidence score is between 0 and 1.
    """
    model = _get_model()
    # FastText expects single line, replace newlines with spaces
    text_clean = text.replace("\n", " ")
    predictions = model.predict(text_clean, k=1)
    # predictions is ([labels], [scores])
    label = predictions[0][0].replace("__label__", "")  # "wiki" or "cc"
    score = predictions[1][0]
    return label, float(score)


def prepare_training_data(
    positive_path: str = "data/positive_examples.jsonl",
    negative_path: str = "data/negative_examples.jsonl",
    output_path: str = "data/quality_classifier_train.txt",
    max_samples: int | None = None,
    seed: int = 42,
):
    """
    Prepare training data in fastText format.
    
    FastText format: __label__<label> <text on single line>
    """
    import json
    import random
    
    positive_file = Path(positive_path)
    negative_file = Path(negative_path)
    output_file = Path(output_path)
    
    # Load positive examples (Wikipedia = high quality)
    with open(positive_file, "r", encoding="utf-8") as f:
        positive_docs = [json.loads(line) for line in f]
    
    # Load negative examples (Common Crawl = low quality)
    with open(negative_file, "r", encoding="utf-8") as f:
        negative_docs = [json.loads(line) for line in f]
    
    print(f"Loaded {len(positive_docs)} positive (wiki) examples")
    print(f"Loaded {len(negative_docs)} negative (cc) examples")
    
    # Balance the dataset
    random.seed(seed)
    min_count = min(len(positive_docs), len(negative_docs))
    if max_samples:
        min_count = min(min_count, max_samples // 2)
    
    positive_sample = random.sample(positive_docs, min_count)
    negative_sample = random.sample(negative_docs, min_count)
    
    print(f"Using {min_count} samples per class ({min_count * 2} total)")
    
    # Write in fastText format
    all_samples = []
    for doc in positive_sample:
        text = doc.get("text", "").replace("\n", " ").strip()
        if text:
            all_samples.append(f"__label__wiki {text}")
    
    for doc in negative_sample:
        text = doc.get("text", "").replace("\n", " ").strip()
        if text:
            all_samples.append(f"__label__cc {text}")
    
    # Shuffle
    random.shuffle(all_samples)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for line in all_samples:
            f.write(line + "\n")
    
    print(f"Saved training data to {output_file}")
    return str(output_file)


def train_classifier(
    train_path: str = "data/quality_classifier_train.txt",
    model_path: str = "data/quality_classifier.bin",
    epochs: int = 25,
    lr: float = 0.5,
    wordNgrams: int = 2,
    dim: int = 100,
):
    """
    Train a fastText classifier for quality classification.
    """
    print(f"Training fastText classifier...")
    print(f"  epochs: {epochs}")
    print(f"  learning rate: {lr}")
    print(f"  word n-grams: {wordNgrams}")
    print(f"  dimensions: {dim}")
    
    # Suppress warnings
    fasttext.FastText.eprint = lambda x: None
    
    model = fasttext.train_supervised(
        input=train_path,
        epoch=epochs,
        lr=lr,
        wordNgrams=wordNgrams,
        dim=dim,
        loss="softmax",
    )
    
    model.save_model(model_path)
    print(f"Model saved to {model_path}")
    
    # Evaluate on training data
    result = model.test(train_path)
    print(f"\nTraining accuracy: {result[1]:.4f}")
    print(f"Training precision: {result[1]:.4f}")
    print(f"Training recall: {result[2]:.4f}")
    
    return model


def evaluate_classifier(
    model_path: str = "data/quality_classifier.bin",
    test_samples: list[tuple[str, str]] | None = None,
):
    """Evaluate the classifier on test samples."""
    fasttext.FastText.eprint = lambda x: None
    model = fasttext.load_model(model_path)
    
    if test_samples is None:
        # Use fixture files as test
        test_samples = []
        
        fixtures_path = Path("tests/fixtures")
        low_quality_path = fixtures_path / "low_quality_cc.txt"
        high_quality_path = fixtures_path / "high_quality_wiki_reference.txt"
        
        if low_quality_path.exists():
            with open(low_quality_path) as f:
                test_samples.append((f.read(), "cc"))
        
        if high_quality_path.exists():
            with open(high_quality_path) as f:
                test_samples.append((f.read(), "wiki"))
    
    print("\nEvaluation on test samples:")
    print("=" * 60)
    correct = 0
    for text, expected in test_samples:
        text_clean = text.replace("\n", " ")
        predictions = model.predict(text_clean, k=2)
        predicted = predictions[0][0].replace("__label__", "")
        score = predictions[1][0]
        
        is_correct = predicted == expected
        correct += int(is_correct)
        status = "✓" if is_correct else "✗"
        
        preview = text[:80].replace("\n", " ")
        print(f"{status} Expected: {expected}, Got: {predicted} ({score:.3f})")
        print(f"  Text: {preview}...")
        print()
    
    print(f"Accuracy: {correct}/{len(test_samples)} ({correct/len(test_samples)*100:.1f}%)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Quality classifier training and inference")
    parser.add_argument("command", choices=["prepare", "train", "evaluate", "all"],
                        help="Command to run")
    parser.add_argument("--positive", default="data/positive_examples.jsonl",
                        help="Path to positive examples JSONL")
    parser.add_argument("--negative", default="data/negative_examples.jsonl",
                        help="Path to negative examples JSONL")
    parser.add_argument("--epochs", type=int, default=25,
                        help="Number of training epochs")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Max samples to use for training")
    
    args = parser.parse_args()
    
    if args.command in ["prepare", "all"]:
        prepare_training_data(
            positive_path=args.positive,
            negative_path=args.negative,
            max_samples=args.max_samples,
        )
    
    if args.command in ["train", "all"]:
        train_classifier(epochs=args.epochs)
    
    if args.command in ["evaluate", "all"]:
        evaluate_classifier()


if __name__ == "__main__":
    main()
