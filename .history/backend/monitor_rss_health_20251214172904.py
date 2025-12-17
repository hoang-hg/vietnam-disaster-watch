#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS health monitoring - track source reliability over time.
Parses crawl_log.jsonl to generate reports.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def load_crawl_logs(days: int = 7) -> list[dict]:
    """Load crawl logs from last N days."""
    logs_file = Path(__file__).parent / "logs" / "crawl_log.jsonl"
    
    if not logs_file.exists():
        print(f"❌ crawl_log.jsonl not found at {logs_file}")
        return []
    
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    logs = []
    
    try:
        with open(logs_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts = datetime.fromisoformat(record.get("timestamp", ""))
                    if ts >= cutoff_time:
                        logs.append(record)
                except Exception:
                    pass
    except Exception as e:
        print(f"❌ Error reading logs: {e}")
    
    return logs


def generate_health_report(days: int = 7):
    """Generate RSS health report."""
    logs = load_crawl_logs(days)
    
    if not logs:
        print(f"❌ No logs found for past {days} days")
        return
    
    # Aggregate per-source stats
    stats = defaultdict(lambda: {
        "total_crawls": 0,
        "successful_crawls": 0,
        "feeds_used": defaultdict(int),
        "total_articles": 0,
        "errors": []
    })
    
    for log in logs:
        for src_stat in log.get("per_source", []):
            src_name = src_stat.get("source", "unknown")
            stats[src_name]["total_crawls"] += 1
            
            if src_stat.get("feed_used"):
                stats[src_name]["feeds_used"][src_stat["feed_used"]] += 1
                stats[src_name]["successful_crawls"] += 1
                stats[src_name]["total_articles"] += src_stat.get("articles_added", 0)
            else:
                if error := src_stat.get("error"):
                    stats[src_name]["errors"].append(error)
    
    # Print report
    print("\n" + "=" * 80)
    print(f"📊 RSS HEALTH REPORT - Last {days} days ({len(logs)} crawls)")
    print("=" * 80)
    
    # Sort by success rate
    sorted_sources = sorted(
        stats.items(),
        key=lambda x: (x[1]["successful_crawls"] / x[1]["total_crawls"]) if x[1]["total_crawls"] > 0 else 0,
        reverse=True
    )
    
    for src_name, stat in sorted_sources:
        success_rate = (stat["successful_crawls"] / stat["total_crawls"]) * 100 if stat["total_crawls"] > 0 else 0
        
        if success_rate == 100:
            icon = "✅"
        elif success_rate >= 75:
            icon = "🟢"
        elif success_rate >= 50:
            icon = "🟡"
        else:
            icon = "🔴"
        
        print(f"\n{icon} {src_name:<35} {success_rate:>6.1f}% ({stat['successful_crawls']}/{stat['total_crawls']} crawls)")
        
        # Show feed usage
        if stat["feeds_used"]:
            for feed_type, count in sorted(stat["feeds_used"].items(), key=lambda x: -x[1]):
                pct = (count / stat["total_crawls"]) * 100
                print(f"   • {feed_type:<15} {pct:>6.1f}% ({count} times)")
        
        # Show article count and avg per crawl
        avg_per_crawl = stat["total_articles"] / stat["successful_crawls"] if stat["successful_crawls"] > 0 else 0
        print(f"   📰 Total articles: {stat['total_articles']} ({avg_per_crawl:.1f} per crawl)")
        
        # Show errors
        if stat["errors"]:
            error_counts = defaultdict(int)
            for err in stat["errors"]:
                # Normalize error messages
                if "404" in err:
                    error_counts["404 Not Found"] += 1
                elif "timeout" in err.lower():
                    error_counts["Timeout"] += 1
                elif "ssl" in err.lower():
                    error_counts["SSL Error"] += 1
                else:
                    error_counts[err[:50]] += 1
            
            print(f"   ❌ Errors encountered:")
            for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:3]:
                print(f"      - {err} ({count} times)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    total_sources = len(stats)
    healthy = sum(1 for s in stats.values() if (s["successful_crawls"] / s["total_crawls"] * 100) >= 75)
    total_articles = sum(s["total_articles"] for s in stats.values())
    avg_per_crawl = total_articles / len(logs) if logs else 0
    
    print(f"✅ Healthy sources: {healthy}/{total_sources}")
    print(f"📰 Total articles collected: {total_articles} ({avg_per_crawl:.0f} per crawl)")
    print(f"🔄 Total crawls: {len(logs)}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    needs_attention = [
        (name, stat) for name, stat in stats.items()
        if (stat["successful_crawls"] / stat["total_crawls"] * 100) < 50
    ]
    
    if needs_attention:
        print(f"   ⚠️  {len(needs_attention)} sources failing >50% of the time - investigate URLs")
        for src_name, _ in needs_attention[:3]:
            print(f"      - {src_name}")
    else:
        print(f"   ✅ All sources performing well!")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    generate_health_report(days)
