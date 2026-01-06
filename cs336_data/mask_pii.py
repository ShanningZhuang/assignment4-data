import re


# Email regex pattern - matches common email formats
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

# Phone regex pattern - matches US phone formats:
# 2831823829, (283)-182-3829, (283) 182 3829, 283-182-3829
PHONE_PATTERN = re.compile(
    r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)

# IPv4 regex pattern - matches 4 octets (0-255) separated by dots
IP_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)


def mask_emails(text: str) -> tuple[str, int]:
    """Mask email addresses in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = EMAIL_PATTERN.findall(text)
    masked_text = EMAIL_PATTERN.sub("|||EMAIL_ADDRESS|||", text)
    return masked_text, len(matches)


def mask_phone_numbers(text: str) -> tuple[str, int]:
    """Mask phone numbers in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = PHONE_PATTERN.findall(text)
    masked_text = PHONE_PATTERN.sub("|||PHONE_NUMBER|||", text)
    return masked_text, len(matches)


def mask_ips(text: str) -> tuple[str, int]:
    """Mask IPv4 addresses in text.
    
    Returns:
        A tuple of (masked_text, num_masked).
    """
    matches = IP_PATTERN.findall(text)
    masked_text = IP_PATTERN.sub("|||IP_ADDRESS|||", text)
    return masked_text, len(matches)


def mask_all_pii(text: str) -> tuple[str, dict[str, int]]:
    """Mask all PII (emails, phones, IPs) in text.
    
    Returns:
        A tuple of (masked_text, counts_dict).
    """
    masked_text = text
    emails = EMAIL_PATTERN.findall(masked_text)
    masked_text = EMAIL_PATTERN.sub("|||EMAIL_ADDRESS|||", masked_text)
    phones = PHONE_PATTERN.findall(masked_text)
    masked_text = PHONE_PATTERN.sub("|||PHONE_NUMBER|||", masked_text)
    ips = IP_PATTERN.findall(masked_text)
    masked_text = IP_PATTERN.sub("|||IP_ADDRESS|||", masked_text)
    return masked_text, {"emails": len(emails), "phones": len(phones), "ips": len(ips)}


def analyze_pii_masking(jsonl_path: str, output_dir: str = "data", num_samples: int = 20, seed: int = 42):
    """Analyze PII masking on extracted WARC documents."""
    import json
    import random
    from pathlib import Path

    output_path = Path(output_dir)

    # Load extractions (supports both warc_extractions.jsonl and language_ids.jsonl formats)
    with open(jsonl_path, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f]

    # Find all PII in documents
    pii_results = []
    stats = {"emails": 0, "phones": 0, "ips": 0}

    for doc in docs:
        text = doc["text"]
        url = doc["url"]
        # Preserve language fields if present (from language_ids.jsonl)
        language = doc.get("language")
        score = doc.get("score")

        emails = EMAIL_PATTERN.findall(text)
        phones = PHONE_PATTERN.findall(text)
        ips = IP_PATTERN.findall(text)

        if emails or phones or ips:
            masked_text, _ = mask_all_pii(text)
            result = {
                "url": url,
                "emails": emails,
                "phones": phones,
                "ips": ips,
                "text": text,
                "masked_text": masked_text,
            }
            # Add language info if available
            if language is not None:
                result["language"] = language
                result["score"] = score
            pii_results.append(result)
            if emails:
                stats["emails"] += 1
            if phones:
                stats["phones"] += 1
            if ips:
                stats["ips"] += 1

    print(f"Documents with any PII: {len(pii_results)}")
    print(f"Documents with emails: {stats['emails']}")
    print(f"Documents with phones: {stats['phones']}")
    print(f"Documents with IPs: {stats['ips']}")

    # Save all PII matches to a single JSONL file
    output_file = output_path / "pii_all.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in pii_results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved all PII matches to {output_file}")

    # Sample random examples and print
    random.seed(seed)
    samples = random.sample(pii_results, min(num_samples, len(pii_results)))

    print("\n" + "=" * 80)
    print(f"SAMPLE PII MATCHES ({len(samples)} examples):")
    print("=" * 80)
    for item in samples:
        domain = item["url"].split("/")[2] if "/" in item["url"] else item["url"]
        text = item["text"]
        print(f"\n{domain}:")
        if item["emails"]:
            print(f"  Emails: {item['emails'][:3]}")
        if item["phones"]:
            print(f"  Phones: {item['phones'][:3]}")
            for m in item["phones"][:1]:
                idx = text.find(m)
                if idx >= 0:
                    ctx_start = max(0, idx - 40)
                    ctx_end = min(len(text), idx + len(m) + 40)
                    context = text[ctx_start:ctx_end].replace("\n", " ")
                    print(f"    Context: ...{context}...")
        if item["ips"]:
            print(f"  IPs: {item['ips'][:3]}")
            for m in item["ips"][:1]:
                idx = text.find(m)
                if idx >= 0:
                    ctx_start = max(0, idx - 40)
                    ctx_end = min(len(text), idx + len(m) + 40)
                    context = text[ctx_start:ctx_end].replace("\n", " ")
                    print(f"    Context: ...{context}...")


if __name__ == "__main__":
    analyze_pii_masking("data/language_ids.jsonl")
