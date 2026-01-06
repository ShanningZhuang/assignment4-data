"""
Data scraping pipeline for high-quality text extraction.

Pipeline:
1. Fetch URL content via async HTTP (aiohttp) - I/O bound
2. Process content in process pool - CPU bound:
   - Extract text from HTML
   - Language identification
   - Harmful content detection
   - Quality filtering
3. Save high-quality text to JSONL
4. Hybrid async + multiprocessing for maximum throughput
"""

import asyncio
import gzip
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import aiohttp
from tqdm import tqdm

from cs336_data.extract_text import extract_text_from_html_bytes
from cs336_data.language_identification import identify_language
from cs336_data.harmful_content import classify_nsfw, classify_toxic_speech
from cs336_data.quality_filter import gopher_quality_filter

# Process pool for CPU-bound tasks (initialized lazily)
_process_pool = None
CPU_WORKERS = max(1, os.cpu_count() - 2)  # Leave some cores for system


# Thresholds for filtering
LANGUAGE_CONFIDENCE_THRESHOLD = 0.5
NSFW_THRESHOLD = 0.9
TOXIC_THRESHOLD = 0.9
MIN_TEXT_LENGTH = 100

# HTTP request settings - fast failure for throughput
CONNECT_TIMEOUT = 5   # Fast fail on connection issues
READ_TIMEOUT = 10     # Don't wait too long
TOTAL_TIMEOUT = 15    # Overall timeout - fail fast, move on

# Concurrency settings - push hard!
MAX_CONCURRENT_REQUESTS = 1000  # Very high concurrency
LIMIT_PER_HOST = 30  # Connections per server


def process_content(url: str, html_bytes: bytes) -> dict | None:
    """Process fetched content through filtering pipeline (CPU-bound)."""
    # Extract text from HTML
    text = extract_text_from_html_bytes(html_bytes)
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        return None
    
    # Language identification - keep only English
    lang, lang_score = identify_language(text)
    if lang != "en" or lang_score < LANGUAGE_CONFIDENCE_THRESHOLD:
        return None
    
    # Filter harmful content
    nsfw_label, nsfw_score = classify_nsfw(text)
    if nsfw_label == "nsfw" and nsfw_score >= NSFW_THRESHOLD:
        return None
    
    toxic_label, toxic_score = classify_toxic_speech(text)
    if toxic_label == "toxic" and toxic_score >= TOXIC_THRESHOLD:
        return None
    
    # Apply Gopher quality filters
    if not gopher_quality_filter(text):
        return None
    
    return {
        "url": url,
        "text": text,
        "language": lang,
        "language_score": lang_score,
        "nsfw_label": nsfw_label,
        "nsfw_score": nsfw_score,
        "toxic_label": toxic_label,
        "toxic_score": toxic_score,
    }


def stream_urls(urls_path: str, limit: int | None = None):
    """Generator that streams URLs from gzipped file."""
    count = 0
    with gzip.open(urls_path, "rt", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                yield url
                count += 1
                if limit and count >= limit:
                    break


async def worker(
    worker_id: int,
    queue: asyncio.Queue,
    session: aiohttp.ClientSession,
    process_pool: ProcessPoolExecutor,
    output_file,
    file_lock: asyncio.Lock,
    pbar: tqdm,
    stats: dict,
    error_counts: dict,
):
    """Worker that continuously pulls URLs from queue and processes them."""
    while True:
        try:
            url = await queue.get()
            if url is None:  # Poison pill - shutdown signal
                queue.task_done()
                break
            
            try:
                # Process URL directly - no semaphore, workers ARE the concurrency limit
                result = await process_url_direct(session, url, process_pool, error_counts)
                if result:
                    async with file_lock:
                        output_file.write(json.dumps(result, ensure_ascii=False) + "\n")
                    stats["saved"] += 1
                else:
                    stats["failed"] += 1
            except Exception:
                stats["failed"] += 1
            
            pbar.update(1)
            pbar.set_postfix(saved=stats["saved"], failed=stats["failed"])
            queue.task_done()
            
        except asyncio.CancelledError:
            break


async def process_url_direct(
    session: aiohttp.ClientSession,
    url: str,
    process_pool: ProcessPoolExecutor,
    error_counts: dict,
) -> dict | None:
    """Fetch and process URL directly (no semaphore)."""
    try:
        return await asyncio.wait_for(
            _fetch_and_process(session, url, process_pool, error_counts),
            timeout=TOTAL_TIMEOUT + 5
        )
    except asyncio.TimeoutError:
        error_counts["wrapper_timeout"] = error_counts.get("wrapper_timeout", 0) + 1
        return None


async def _fetch_and_process(
    session: aiohttp.ClientSession,
    url: str,
    process_pool: ProcessPoolExecutor,
    error_counts: dict,
) -> dict | None:
    """Internal fetch and process."""
    try:
        timeout = aiohttp.ClientTimeout(
            total=TOTAL_TIMEOUT,
            connect=CONNECT_TIMEOUT,
            sock_read=READ_TIMEOUT
        )
        async with session.get(url, timeout=timeout) as response:
            if response.status >= 400:
                error_counts["http_error"] = error_counts.get("http_error", 0) + 1
                return None
            html_bytes = await response.content.read(5 * 1024 * 1024)  # Max 5MB
    except asyncio.TimeoutError:
        error_counts["timeout"] = error_counts.get("timeout", 0) + 1
        return None
    except aiohttp.ClientConnectorError:
        error_counts["connect_fail"] = error_counts.get("connect_fail", 0) + 1
        return None
    except aiohttp.ClientError:
        error_counts["client_error"] = error_counts.get("client_error", 0) + 1
        return None
    except Exception:
        error_counts["other"] = error_counts.get("other", 0) + 1
        return None
    
    # Process in process pool
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(process_pool, process_content, url, html_bytes)
        return result
    except Exception:
        return None


class AsyncFileWriter:
    """Async-compatible file writer wrapper."""
    def __init__(self, file_handle):
        self.file = file_handle
    
    def write(self, data):
        self.file.write(data)
    
    def flush(self):
        self.file.flush()


async def scrape_urls_async(
    urls_path: str,
    output_path: str = "data/scraped_high_quality.jsonl",
    max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    cpu_workers: int = CPU_WORKERS,
    limit: int | None = None,
    num_workers: int = None,  # Number of worker coroutines
):
    """Main async scraping function using queue-based continuous processing."""
    if num_workers is None:
        num_workers = max_concurrent  # One worker per concurrent slot
    
    print(f"Starting scrape from {urls_path}")
    print(f"  - {max_concurrent} concurrent HTTP requests")
    print(f"  - {num_workers} async workers")
    print(f"  - {cpu_workers} CPU workers for processing")
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    stats = {"saved": 0, "failed": 0}
    error_counts = {}  # Track error types
    
    # Try to increase file descriptor limit for high concurrency
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_limit = min(hard, max(soft, 10000))
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard))
        print(f"  - File descriptor limit: {new_limit}")
    except Exception:
        pass
    
    # Configure aiohttp connector for high concurrency
    connector = aiohttp.TCPConnector(
        limit=max_concurrent,
        limit_per_host=LIMIT_PER_HOST,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DataScraper/1.0)"}
    
    # Queue for URLs - workers pull from this continuously
    queue = asyncio.Queue(maxsize=num_workers * 2)  # Small buffer to avoid memory issues
    file_lock = asyncio.Lock()
    
    # Use process pool for CPU-bound tasks
    with ProcessPoolExecutor(max_workers=cpu_workers) as process_pool:
        with open(output_file, "w", encoding="utf-8") as f:
            writer = AsyncFileWriter(f)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                pbar = tqdm(desc="Scraping", unit="url", total=limit)
                
                # Start worker tasks - each worker is one concurrent slot
                workers = [
                    asyncio.create_task(
                        worker(i, queue, session, process_pool, writer, file_lock, pbar, stats, error_counts)
                    )
                    for i in range(num_workers)
                ]
                
                # Producer: feed URLs into queue
                url_count = 0
                for url in stream_urls(urls_path, limit=limit):
                    await queue.put(url)
                    url_count += 1
                
                # Send poison pills to stop workers
                for _ in range(num_workers):
                    await queue.put(None)
                
                # Wait for all workers to finish
                await asyncio.gather(*workers)
                
                pbar.close()
                f.flush()
    
    total = stats["saved"] + stats["failed"]
    print(f"\nDone! Processed {total} URLs, saved {stats['saved']} high-quality documents to {output_path}")
    
    # Print error breakdown
    if error_counts:
        print("\nError breakdown:")
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"  - {error_type}: {count} ({100*count/total:.1f}%)")
    
    return stats["saved"]


def scrape_urls(
    urls_path: str,
    output_path: str = "data/scraped_high_quality.jsonl",
    max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    cpu_workers: int = CPU_WORKERS,
    limit: int | None = None,
    num_workers: int = None,
):
    """Wrapper to run async scraper from sync context."""
    return asyncio.run(scrape_urls_async(
        urls_path=urls_path,
        output_path=output_path,
        max_concurrent=max_concurrent,
        cpu_workers=cpu_workers,
        limit=limit,
        num_workers=num_workers,
    ))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape URLs and extract high-quality text (queue-based async)")
    parser.add_argument(
        "--urls", 
        default="data/enwiki-20240420-extracted_urls.txt.gz",
        help="Path to gzipped URLs file"
    )
    parser.add_argument(
        "--output",
        default="data/scraped_high_quality.jsonl", 
        help="Output JSONL path"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=MAX_CONCURRENT_REQUESTS,
        help="Maximum concurrent HTTP requests (also default for workers)"
    )
    parser.add_argument(
        "--cpu-workers",
        type=int,
        default=CPU_WORKERS,
        help="Number of CPU workers for processing"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of URLs to process (for testing)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of async worker coroutines (default: same as concurrent)"
    )
    
    args = parser.parse_args()
    
    scrape_urls(
        urls_path=args.urls,
        output_path=args.output,
        max_concurrent=args.concurrent,
        cpu_workers=args.cpu_workers,
        limit=args.limit,
        num_workers=args.workers,
    )
