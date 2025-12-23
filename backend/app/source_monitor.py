import asyncio
import httpx
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import SessionLocal
from .models import Article
from .sources import load_sources_from_json, Source

logger = logging.getLogger(__name__)

class SourceMonitor:
    def __init__(self, sources_json_path: str):
        self.sources_json_path = sources_json_path
        self.results_path = Path(sources_json_path).parent / "logs" / "source_status.json"
        self.results_path.parent.mkdir(parents=True, exist_ok=True)

    async def check_connectivity(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Check if a URL is accessible."""
        if not url:
            return {"status": "skipped", "error": "No URL provided"}
        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
                start_time = datetime.now(timezone.utc)
                resp = await client.get(url, headers=headers)
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if resp.status_code == 200:
                    return {"status": "ok", "code": resp.status_code, "elapsed": elapsed}
                else:
                    return {"status": "error", "code": resp.status_code, "error": f"HTTP {resp.status_code}", "elapsed": elapsed}
        except httpx.TimeoutException:
            return {"status": "timeout", "error": "Request timed out"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def get_last_article_info(self, db: Session) -> Dict[str, datetime]:
        """Get the latest article timestamp for each source from the DB."""
        results = db.query(
            Article.source,
            func.max(Article.published_at).label("latest")
        ).group_by(Article.source).all()
        
        return {r.source: r.latest for r in results}

    async def run_check(self):
        """Run full monitor check on all sources."""
        sources = load_sources_from_json(self.sources_json_path)
        db = SessionLocal()
        
        try:
            last_updates = self.get_last_article_info(db)
            now = datetime.now(timezone.utc)
            
            report = {
                "checked_at": now.isoformat(),
                "summary": {
                    "total": len(sources),
                    "broken_rss": 0,
                    "inactive_too_long": 0,
                    "blocked": 0
                },
                "details": []
            }

            # Batch connectivity checks
            tasks = []
            source_map = [] # Track which tasks belong to which source/feed
            
            for src in sources:
                if src.primary_rss:
                    tasks.append(self.check_connectivity(src.primary_rss))
                    source_map.append((src.name, "primary"))
                if src.backup_rss:
                    tasks.append(self.check_connectivity(src.backup_rss))
                    source_map.append((src.name, "backup"))

            # Run checks concurrently
            results = await asyncio.gather(*tasks)
            
            # Organize results
            connectivity_results = {}
            for i, (src_name, feed_type) in enumerate(source_map):
                if src_name not in connectivity_results:
                    connectivity_results[src_name] = {}
                connectivity_results[src_name][feed_type] = results[i]

            for src in sources:
                last_published = last_updates.get(src.name)
                
                # Check if inactive for more than 7 days
                is_inactive = False
                days_since = None
                if last_published:
                    # Ensure last_published is timezone aware for comparison
                    if last_published.tzinfo is None:
                        last_published = last_published.replace(tzinfo=timezone.utc)
                    delta = now - last_published
                    days_since = delta.days
                    if delta > timedelta(days=7):
                        is_inactive = True
                        report["summary"]["inactive_too_long"] += 1
                else:
                    is_inactive = True # Never found an article
                    report["summary"]["inactive_too_long"] += 1

                feeds_status = connectivity_results.get(src.name, {})
                primary_status = feeds_status.get("primary", {"status": "none"})
                backup_status = feeds_status.get("backup", {"status": "none"})
                
                is_broken = False
                if primary_status["status"] not in ["ok", "none"]:
                    is_broken = True
                if src.backup_rss and backup_status["status"] not in ["ok", "none"]:
                    # If primary is ok but backup is broken, we still flag it
                    pass 

                if primary_status["status"] in ["error", "failed"] and primary_status.get("code") in [403, 401]:
                    report["summary"]["blocked"] += 1

                if is_broken:
                    report["summary"]["broken_rss"] += 1

                src_report = {
                    "name": src.name,
                    "domain": src.domain,
                    "last_article_at": last_published.isoformat() if last_published else None,
                    "days_inactive": days_since,
                    "status": "warning" if (is_broken or is_inactive) else "ok",
                    "issues": [],
                    "feeds": {
                        "primary": primary_status,
                        "backup": backup_status
                    }
                }
                
                if is_inactive:
                    src_report["issues"].append(f"No new articles for {days_since if days_since is not None else '??'} days")
                if primary_status["status"] != "ok" and primary_status["status"] != "none":
                    src_report["issues"].append(f"Primary RSS failed: {primary_status.get('error') or primary_status.get('code')}")
                if backup_status["status"] != "ok" and backup_status["status"] != "none":
                    src_report["issues"].append(f"Backup RSS failed: {backup_status.get('error') or backup_status.get('code')}")

                report["details"].append(src_report)

            # Save report
            with open(self.results_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Source monitor finished. Report saved to {self.results_path}")
            return report

        finally:
            db.close()

async def monitor_now():
    root_dir = Path(__file__).resolve().parent.parent
    monitor = SourceMonitor(str(root_dir / "sources.json"))
    return await monitor.run_check()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_now())
