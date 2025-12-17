#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test multiple crawl cycles to populate health metrics.
"""

import asyncio
import sys
from app.crawler import _process_once_async


async def run_multiple_crawls(num_runs: int = 3):
    """Run crawl multiple times and show summary."""
    print(f"\n Running {num_runs} crawl cycles...\n")
    
    for i in range(1, num_runs + 1):
        print(f"--- CRAWL {i}/{num_runs} ---")
        try:
            result = await _process_once_async()
            
            # Show per-source summary
            articles_added = sum(s.get("articles_added", 0) for s in result.get("per_source", []))
            elapsed = result.get("elapsed", 0)
            
            print(f"✅ Finished: {articles_added} articles in {elapsed:.1f}s")
            print()
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    print("✅ All crawls completed!")
    print("\nRun 'python monitor_rss_health.py 1' to see health report")


if __name__ == "__main__":
    num_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(run_multiple_crawls(num_runs))
