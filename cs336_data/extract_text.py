# Note: We suggest using the FastWARC library to iterate over records in each WARC file. Specifically, the following classes may be helpful:

from fastwarc.warc import ArchiveIterator, WarcRecordType
from resiliparse.extract.html2text import extract_plain_text
from resiliparse.parse.encoding import detect_encoding


def extract_text_from_html_bytes(html_bytes: bytes) -> str | None:
    """Extract text from a byte string containing raw HTML."""
    try:
        html_str = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        encoding = detect_encoding(html_bytes)
        html_str = html_bytes.decode(encoding, errors="replace")
    return extract_plain_text(html_str)


def extract_all_from_warc(warc_path: str, output_file: str = "data/warc_extractions.jsonl"):
    """Extract all text from a WARC file and save to JSONL."""
    import gzip
    import json

    results = []
    with gzip.open(warc_path, "rb") as f:
        for record in ArchiveIterator(f, record_types=WarcRecordType.response):
            url = record.headers.get("WARC-Target-URI")
            if url and record.http_content_type and "text/html" in record.http_content_type:
                html_bytes = record.reader.read()
                text = extract_text_from_html_bytes(html_bytes)
                if text and len(text.strip()) > 50:
                    results.append({"url": url, "text": text})

    with open(output_file, "w") as f:
        for item in results:
            f.write(json.dumps(item) + "\n")

    print(f"Extracted {len(results)} documents to {output_file}")
    return results


def compare_warc_wet(warc_path: str, wet_path: str, output_dir: str = "data", num_examples: int = 2):
    """Compare text extraction from WARC vs WET files."""
    import gzip
    from pathlib import Path

    output_path = Path(output_dir)

    # Extract text from WARC (HTML) using our function
    warc_extractions = {}
    with gzip.open(warc_path, "rb") as f:
        for record in ArchiveIterator(f, record_types=WarcRecordType.response):
            url = record.headers.get("WARC-Target-URI")
            if url and record.http_content_type and "text/html" in record.http_content_type:
                html_bytes = record.reader.read()
                text = extract_text_from_html_bytes(html_bytes)
                warc_extractions[url] = text

    # Read pre-extracted text from WET
    wet_extractions = {}
    with gzip.open(wet_path, "rb") as f:
        for record in ArchiveIterator(f, record_types=WarcRecordType.conversion):
            url = record.headers.get("WARC-Target-URI")
            if url:
                wet_extractions[url] = record.reader.read().decode("utf-8", errors="replace")

    # Compare examples and save to files
    common_urls = set(warc_extractions.keys()) & set(wet_extractions.keys())
    for i, url in enumerate(list(common_urls)[:num_examples]):
        print(f"\n{'='*80}\nURL: {url}\n{'='*80}")
        print(f"\n--- OUR EXTRACTION (first 500 chars) ---\n{warc_extractions[url][:500]}")
        print(f"\n--- WET EXTRACTION (first 500 chars) ---\n{wet_extractions[url][:500]}")

        # Save full extractions to files
        our_file = output_path / f"extraction_ours_{i}.txt"
        wet_file = output_path / f"extraction_wet_{i}.txt"
        our_file.write_text(warc_extractions[url] or "")
        wet_file.write_text(wet_extractions[url] or "")
        print(f"\nSaved full extractions to: {our_file}, {wet_file}")


if __name__ == "__main__":
    # Extract all text and save to JSONL
    extract_all_from_warc("data/CC-MAIN-20250417135010-20250417165010-00065.warc.gz")
    
    # Also run comparison for reference
    compare_warc_wet(
        "data/CC-MAIN-20250417135010-20250417165010-00065.warc.gz",
        "data/CC-MAIN-20250417135010-20250417165010-00065.warc.wet.gz",
    )