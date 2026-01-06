"""
Fast WARC downloader using async HTTP requests.

Downloads URLs and saves successful responses to a WARC file.
Failed fetches (timeouts, errors) are excluded from the output.

Usage:
    python download_warc.py --urls urls.txt.gz --output output.warc.gz
    
Similar to:
    wget --timeout=5 -i urls.txt --warc-file=output.warc -O /dev/null
But faster (async) and only saves successful fetches.
"""

import asyncio
import gzip
import io
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import aiohttp
from tqdm import tqdm
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders


# Timeout settings
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 10
TOTAL_TIMEOUT = 15

# Concurrency settings
MAX_CONCURRENT = 500
LIMIT_PER_HOST = 20


def stream_urls(urls_path: str, limit: int | None = None):
    """Stream URLs from file (supports .gz)."""
    count = 0
    open_func = gzip.open if urls_path.endswith('.gz') else open
    with open_func(urls_path, "rt", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url and url.startswith('http'):
                yield url
                count += 1
                if limit and count >= limit:
                    break


async def fetch_url(
    session: aiohttp.ClientSession,
    url: str,
    error_counts: dict,
) -> tuple[str, bytes, dict] | None:
    """Fetch URL and return (url, content, headers) or None on failure."""
    try:
        timeout = aiohttp.ClientTimeout(
            total=TOTAL_TIMEOUT,
            connect=CONNECT_TIMEOUT,
            sock_read=READ_TIMEOUT
        )
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            if response.status >= 400:
                error_counts["http_error"] = error_counts.get("http_error", 0) + 1
                return None
            
            # Read content (limit to 10MB)
            content = await response.content.read(10 * 1024 * 1024)
            
            # Collect response info
            headers = dict(response.headers)
            return (url, content, {
                "status": response.status,
                "reason": response.reason or "OK",
                "headers": headers,
                "final_url": str(response.url),  # After redirects
            })
            
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


async def worker(
    worker_id: int,
    queue: asyncio.Queue,
    session: aiohttp.ClientSession,
    results_queue: asyncio.Queue,
    pbar: tqdm,
    stats: dict,
    error_counts: dict,
):
    """Worker that fetches URLs and puts results in results_queue."""
    while True:
        try:
            url = await queue.get()
            if url is None:  # Shutdown signal
                queue.task_done()
                break
            
            result = await fetch_url(session, url, error_counts)
            if result:
                await results_queue.put(result)
                stats["saved"] += 1
            else:
                stats["failed"] += 1
            
            pbar.update(1)
            pbar.set_postfix(saved=stats["saved"], failed=stats["failed"])
            queue.task_done()
            
        except asyncio.CancelledError:
            break


async def warc_writer_task(
    results_queue: asyncio.Queue,
    output_path: str,
    done_event: asyncio.Event,
):
    """Task that writes results to WARC file."""
    # Open WARC file for writing
    with gzip.open(output_path, 'wb') as output:
        writer = WARCWriter(output, gzip=False)  # Already gzipped by outer
        
        while True:
            try:
                # Wait for result with timeout to check done_event
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if done_event.is_set() and results_queue.empty():
                        break
                    continue
                
                url, content, info = result
                
                # Create WARC response record
                http_headers = StatusAndHeaders(
                    f"{info['status']} {info['reason']}",
                    list(info['headers'].items()),
                    protocol='HTTP/1.1'
                )
                
                # Create the record
                record = writer.create_warc_record(
                    uri=info['final_url'],
                    record_type='response',
                    payload=io.BytesIO(content),
                    http_headers=http_headers,
                    warc_headers_dict={
                        'WARC-Target-URI': url,  # Original URL
                        'WARC-Date': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    }
                )
                
                writer.write_record(record)
                results_queue.task_done()
                
            except asyncio.CancelledError:
                break


async def download_to_warc(
    urls_path: str,
    output_path: str = "output.warc.gz",
    max_concurrent: int = MAX_CONCURRENT,
    limit: int | None = None,
    timeout: int = TOTAL_TIMEOUT,
):
    """Main download function."""
    # Update global timeout settings
    global TOTAL_TIMEOUT, CONNECT_TIMEOUT, READ_TIMEOUT
    TOTAL_TIMEOUT = timeout
    CONNECT_TIMEOUT = max(3, timeout // 3)
    READ_TIMEOUT = max(5, timeout // 2)
    
    print(f"Downloading URLs from {urls_path}")
    print(f"  - Output: {output_path}")
    print(f"  - {max_concurrent} concurrent requests")
    print(f"  - Timeout: {timeout}s")
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    stats = {"saved": 0, "failed": 0}
    error_counts = {}
    
    # Try to increase file descriptor limit
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_limit = min(hard, max(soft, 10000))
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard))
        print(f"  - File descriptor limit: {new_limit}")
    except Exception:
        pass
    
    # Configure connector
    connector = aiohttp.TCPConnector(
        limit=max_concurrent,
        limit_per_host=LIMIT_PER_HOST,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; WARCDownloader/1.0)"}
    
    # Queues
    url_queue = asyncio.Queue(maxsize=max_concurrent * 2)
    results_queue = asyncio.Queue()
    done_event = asyncio.Event()
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        pbar = tqdm(desc="Downloading", unit="url", total=limit)
        
        # Start WARC writer task
        writer_task = asyncio.create_task(
            warc_writer_task(results_queue, output_path, done_event)
        )
        
        # Start workers
        workers = [
            asyncio.create_task(
                worker(i, url_queue, session, results_queue, pbar, stats, error_counts)
            )
            for i in range(max_concurrent)
        ]
        
        # Feed URLs
        for url in stream_urls(urls_path, limit=limit):
            await url_queue.put(url)
        
        # Send shutdown signals
        for _ in range(max_concurrent):
            await url_queue.put(None)
        
        # Wait for workers
        await asyncio.gather(*workers)
        
        # Signal writer to finish
        done_event.set()
        await writer_task
        
        pbar.close()
    
    total = stats["saved"] + stats["failed"]
    print(f"\nDone! Downloaded {stats['saved']}/{total} URLs to {output_path}")
    
    if error_counts:
        print("\nError breakdown:")
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"  - {error_type}: {count} ({100*count/total:.1f}%)")
    
    return stats["saved"]


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download URLs to WARC file (async, fast, excludes failures)"
    )
    parser.add_argument(
        "--urls", "-i",
        required=True,
        help="Input URLs file (supports .gz)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output.warc.gz",
        help="Output WARC file path"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=MAX_CONCURRENT,
        help=f"Maximum concurrent requests (default: {MAX_CONCURRENT})"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of URLs to process"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=TOTAL_TIMEOUT,
        help=f"Request timeout in seconds (default: {TOTAL_TIMEOUT})"
    )
    
    args = parser.parse_args()
    
    asyncio.run(download_to_warc(
        urls_path=args.urls,
        output_path=args.output,
        max_concurrent=args.concurrent,
        limit=args.limit,
        timeout=args.timeout,
    ))


if __name__ == "__main__":
    main()

