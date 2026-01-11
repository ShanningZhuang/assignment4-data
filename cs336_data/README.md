# CS336 Data Processing Pipeline

## Overview

This pipeline processes raw WARC files into clean, high-quality text data for language model training.

## Pipeline Steps

### Step 1: Extract Text from WARC

Extract text content from raw HTML in WARC files:

```bash
uv run python -m cs336_data.extract_text
```

**Input:** `data/CC-MAIN-*.warc.gz`  
**Output:** `data/warc_extractions.jsonl`  
**Format:** `{"url": "...", "text": "..."}`

### Step 2: Language Identification

Identify the language of each document using FastText:

```bash
uv run python -m cs336_data.language_identification
```

**Input:** `data/warc_extractions.jsonl`  
**Output:** `data/language_ids.jsonl`  
**Format:** `{"url": "...", "language": "en", "score": 0.99, "text": "..."}`

### Step 3: PII Masking

Detect and mask personally identifiable information (emails, phones, IPs):

```bash
uv run python -m cs336_data.mask_pii
```

**Input:** `data/language_ids.jsonl`  
**Output:** `data/pii_all.jsonl` (only docs with PII for analysis)

### Step 4: Harmful Content Detection

Classify documents for NSFW and toxic content:

```bash
uv run python -m cs336_data.harmful_content
```

**Input:** `data/pii_all.jsonl`  
**Output:** `data/harmful_content.jsonl`  
**Format:** Adds `nsfw_label`, `nsfw_score`, `toxic_label`, `toxic_score`

### Step 5: Quality Filtering (Gopher Rules)

Apply quality heuristics from the Gopher paper:

```bash
uv run python -m cs336_data.quality_filter
```

**Input:** `data/harmful_content.jsonl`  
**Output:** `data/quality_filtered.jsonl`  
**Format:** Adds `passes_quality: true/false`

### Step 6: Clean Data (Final Filtering)

Apply all filters and produce clean data:

```bash
uv run python -m cs336_data.clean_data
```

**Input:** `data/language_ids.jsonl` (or any intermediate JSONL)  
**Output:** `data/cleaned_data.jsonl`

This step filters out:
- Non-English documents
- NSFW content
- Toxic/hate speech
- Documents failing quality heuristics
- Optionally masks PII in the output

## Quick Start (Full Pipeline)

Run the entire pipeline (just 2 commands):

```bash
# Step 1: Extract text from WARC
uv run python -m cs336_data.extract_text

# Step 2: Clean data (runs language ID, harmful detection, quality filter, PII masking)
uv run python -m cs336_data.clean_data --input data/warc_extractions.jsonl --output data/cleaned_data.jsonl
```

> **Note:** `clean_data.py` runs all filters internally (language identification, harmful content detection, quality filtering, PII masking). You don't need to run steps 2-5 separately unless you want the intermediate analysis files.

## Clean Data Options

```bash
# Basic usage (English only, no harmful, passes quality)
uv run python -m cs336_data.clean_data

# Custom input/output
uv run python -m cs336_data.clean_data --input data/warc_extractions.jsonl --output data/my_clean.jsonl

# Keep PII unmasked (default masks PII)
uv run python -m cs336_data.clean_data --no-mask-pii

# Allow some non-English (e.g., also keep French and German)
uv run python -m cs336_data.clean_data --languages en,fr,de

# Adjust quality threshold (default uses Gopher rules)
uv run python -m cs336_data.clean_data --min-words 100

# Skip quality filter
uv run python -m cs336_data.clean_data --no-quality-filter
```
