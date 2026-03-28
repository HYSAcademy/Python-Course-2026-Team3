"""
Load Test Comparison: Async vs Sync
Measures FULL processing time — from upload to status: completed.

Run:
    poetry run python load_test_comparison.py
"""

import asyncio
import aiohttp
import requests
import time
from pathlib import Path


API_URL = "http://localhost"
TEST_FOLDER = Path.home() / "Desktop" / "test"
NUM_REQUESTS = 20
POLL_INTERVAL = 0.5   # seconds between status checks
MAX_WAIT = 60         # max seconds to wait for processing


def get_archives() -> list[Path]:
    archives = list(TEST_FOLDER.glob("archive_*.zip"))
    if not archives:
        print("❌ No archives found in ~/Desktop/test/")
        print("   Create some .zip files there first.")
        exit(1)
    result = []
    for i in range(NUM_REQUESTS):
        result.append(archives[i % len(archives)])
    return result


async def upload_and_wait_async(
    session: aiohttp.ClientSession, path: Path, idx: int
) -> dict:
    """Upload archive and wait until status is completed or failed."""
    start = time.time()

    try:
        with open(path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("file", f, filename=path.name)
            async with session.post(
                f"{API_URL}/upload-archives/",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 202:
                    return {
                        "idx": idx,
                        "success": False,
                        "ms": (time.time() - start) * 1000,
                        "error": f"Upload failed: HTTP {resp.status}",
                    }
                body = await resp.json()
                archive_id = body["archive_id"]
    except Exception as e:
        return {
            "idx": idx,
            "success": False,
            "ms": (time.time() - start) * 1000,
            "error": f"Upload error: {e}",
        }

    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            async with session.get(
                f"{API_URL}/archives/{archive_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status")
                    if status == "completed":
                        return {
                            "idx": idx,
                            "success": True,
                            "ms": (time.time() - start) * 1000,
                            "files": len(data.get("extracted_files", [])),
                        }
                    if status == "failed":
                        return {
                            "idx": idx,
                            "success": False,
                            "ms": (time.time() - start) * 1000,
                            "error": data.get("error_message", "unknown"),
                        }
        except Exception:
            pass

    return {
        "idx": idx,
        "success": False,
        "ms": (time.time() - start) * 1000,
        "error": f"Timeout after {MAX_WAIT}s",
    }


async def run_async_test(archives: list[Path]) -> dict:
    print("\n" + "=" * 55)
    print("🚀 ASYNC TEST — 20 concurrent uploads + wait for processing")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        wall_start = time.time()
        tasks = [
            upload_and_wait_async(session, path, i + 1)
            for i, path in enumerate(archives)
        ]
        results = await asyncio.gather(*tasks)
        wall_total = time.time() - wall_start

    return _print_stats(results, wall_total, "ASYNC")


def upload_and_wait_sync(path: Path, idx: int) -> dict:
    """Upload archive and wait until status is completed or failed."""
    start = time.time()

    try:
        with open(path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/upload-archives/",
                files={"file": (path.name, f)},
                timeout=30,
            )
        if resp.status_code != 202:
            return {
                "idx": idx,
                "success": False,
                "ms": (time.time() - start) * 1000,
                "error": f"Upload failed: HTTP {resp.status_code}",
            }
        archive_id = resp.json()["archive_id"]
    except Exception as e:
        return {
            "idx": idx,
            "success": False,
            "ms": (time.time() - start) * 1000,
            "error": f"Upload error: {e}",
        }

    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.get(f"{API_URL}/archives/{archive_id}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                if status == "completed":
                    return {
                        "idx": idx,
                        "success": True,
                        "ms": (time.time() - start) * 1000,
                        "files": len(data.get("extracted_files", [])),
                    }
                if status == "failed":
                    return {
                        "idx": idx,
                        "success": False,
                        "ms": (time.time() - start) * 1000,
                        "error": data.get("error_message", "unknown"),
                    }
        except Exception:
            pass

    return {
        "idx": idx,
        "success": False,
        "ms": (time.time() - start) * 1000,
        "error": f"Timeout after {MAX_WAIT}s",
    }


def run_sync_test(archives: list[Path]) -> dict:
    print("\n" + "=" * 55)
    print("🐢 SYNC TEST — 20 sequential uploads + wait for processing")
    print("=" * 55)

    wall_start = time.time()
    results = [
        upload_and_wait_sync(path, i + 1) for i, path in enumerate(archives)
    ]
    wall_total = time.time() - wall_start

    return _print_stats(results, wall_total, "SYNC")


def _print_stats(results: list[dict], total: float, label: str) -> dict:
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    durations = [r["ms"] for r in successful]

    print(f"\n  Successful : {len(successful)}/{len(results)}")
    print(f"  Failed     : {len(failed)}")
    print(f"  Wall time  : {total:.2f}s  ← total time for ALL 20 requests")
    print(f"  RPS        : {len(successful) / total:.2f}")

    if durations:
        print(f"\n  Time per request (upload → completed):")
        print(f"    Min : {min(durations) / 1000:.1f}s")
        print(f"    Max : {max(durations) / 1000:.1f}s")
        print(f"    Avg : {sum(durations) / len(durations) / 1000:.1f}s")

    if failed:
        print(f"\n  Failed requests:")
        for r in failed:
            print(f"    [{r['idx']:2}] {r.get('error', 'unknown')}")

    print(f"\n  Per-request results:")
    for r in results:
        mark = "✓" if r["success"] else "✗"
        sec = r["ms"] / 1000
        files = f"  ({r['files']} files)" if r.get("files") else ""
        print(f"    [{r['idx']:2}] {mark}  {sec:.1f}s{files}")

    return {
        "label": label,
        "total_sec": total,
        "successful": len(successful),
        "failed": len(failed),
        "rps": len(successful) / total,
        "avg_ms": sum(durations) / len(durations) if durations else 0,
    }


def print_comparison(async_stats: dict, sync_stats: dict) -> None:
    print("\n" + "=" * 55)
    print("📊 FINAL COMPARISON")
    print("=" * 55)
    print(f"\n{'Metric':<25} {'ASYNC':>12} {'SYNC':>12}")
    print("-" * 49)
    print(f"{'Wall time (s)':<25} {async_stats['total_sec']:>12.2f} {sync_stats['total_sec']:>12.2f}")
    print(f"{'RPS':<25} {async_stats['rps']:>12.2f} {sync_stats['rps']:>12.2f}")
    print(f"{'Avg per request (s)':<25} {async_stats['avg_ms']/1000:>12.1f} {sync_stats['avg_ms']/1000:>12.1f}")
    print(f"{'Successful':<25} {async_stats['successful']:>12} {sync_stats['successful']:>12}")

    if async_stats["total_sec"] > 0 and sync_stats["total_sec"] > 0:
        speedup = sync_stats["total_sec"] / async_stats["total_sec"]
        print(f"\n  ⚡ Async completed all 20 requests in {async_stats['total_sec']:.1f}s")
        print(f"  🐢 Sync completed all 20 requests in {sync_stats['total_sec']:.1f}s")
        if speedup >= 1:
            print(f"\n  ✅ Async is {speedup:.1f}x faster than sync")
        else:
            print(f"\n  ⚠️  Sync appears faster — workers may be the bottleneck")
            print(f"     Try: docker-compose up --scale worker=3")

    print("=" * 55)


async def main() -> None:
    print("\n" + "=" * 55)
    print("📦 LOAD TEST: ASYNC vs SYNC (full pipeline)")
    print(f"   Requests    : {NUM_REQUESTS}")
    print(f"   Endpoint    : {API_URL}/upload-archives/")
    print(f"   Measures    : upload + background processing time")
    print(f"   Poll every  : {POLL_INTERVAL}s")
    print(f"   Max wait    : {MAX_WAIT}s per request")
    print("=" * 55)

    archives = get_archives()
    print(f"\n✓ Found {len(set(archives))} unique archive(s), using {NUM_REQUESTS} total")

    async_stats = await run_async_test(archives)

    print(f"\nWaiting 5 seconds before sync test...")
    await asyncio.sleep(5)

    sync_stats = run_sync_test(archives)

    print_comparison(async_stats, sync_stats)


if __name__ == "__main__":
    asyncio.run(main())