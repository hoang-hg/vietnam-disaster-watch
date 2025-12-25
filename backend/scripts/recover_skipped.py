
import json
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add the backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import Article
from app import nlp
from app.dedup import find_duplicate_article, get_article_hash
from app.event_matcher import upsert_event_for_article
from app.html_scraper import fetch_article_full_text_async
import httpx

async def recover():
    log_file = Path(__file__).resolve().parents[1] / "logs" / "review_potential_disasters.jsonl"
    if not log_file.exists():
        print(f"Log file not found at {log_file}")
        return

    db = SessionLocal()
    recovered_count = 0
    
    print(f"Reading logs from {log_file}...")
    
    # We read from the end to get recent items first (optional)
    lines = log_file.read_text(encoding="utf-8").splitlines()
    
    for line in lines:
        try:
            record = json.loads(line)
        except:
            continue
            
        if record.get("action") == "accepted":
            continue
            
        title = record.get("title")
        url = record.get("url")
        source = record.get("source")
        domain = record.get("domain")
        
        if not title or not url:
            continue
            
        # Re-check with NEW NLP logic
        # We don't have the summary here, so we just use title for the initial check
        if not nlp.contains_disaster_keywords("", title=title, trusted_source=True):
            continue
            
        # Check if already in DB (maybe it was added later)
        existing = db.query(Article).filter(Article.url == url).first()
        if existing:
            continue
            
        # Check for duplicates using the dedup logic
        duplicate = find_duplicate_article(
            db, domain, url, title, datetime.now(timezone.utc), time_window_hours=72
        )
        if duplicate:
            continue
            
        print(f"Recovering: {title} ({url})")
        
        # Try to fetch full text and impacts to make it a "high quality" entry
        try:
            fetch_res = await fetch_article_full_text_async(url, timeout=10)
            if fetch_res:
                full_text = fetch_res["text"] or ""
                final_url = fetch_res["final_url"] or url
                
                # Re-classify with full text
                disaster_info = nlp.classify_disaster(title + " " + full_text)
                disaster_type = disaster_info.get("primary_type", "unknown")
                province = nlp.extract_province(title + " " + full_text)
                impacts = nlp.extract_impacts(full_text or title)
                summary = nlp.summarize(full_text[:500] if full_text else title)
                stage = nlp.determine_event_stage(title + " " + full_text)
                
                article = Article(
                    source=source,
                    domain=domain,
                    title=title,
                    url=final_url,
                    published_at=datetime.now(timezone.utc), # Approx
                    disaster_type=disaster_type,
                    province=province,
                    summary=f"[{stage}] {summary}",
                    full_text=full_text[:50000],
                    image_url=fetch_res["images"][0] if fetch_res["images"] else None,
                    needs_verification=int(nlp.validate_impacts(impacts))
                )
                
                # Map impacts
                for k in ["deaths", "missing", "injured", "damage_billion_vnd"]:
                    val = impacts.get(k)
                    if val and val != "unknown":
                        try:
                           setattr(article, k, float(val))
                        except: pass
                
                db.add(article)
                db.flush()
                
                # Group into event
                upsert_event_for_article(db, article)
                db.commit()
                recovered_count += 1
            else:
                # Basic insert if fetch fails? Probably better to wait for a real crawl
                # but user asked to recover, so let's try our best.
                pass
        except Exception as e:
            print(f"Failed to recover {url}: {e}")
            db.rollback()

    db.close()
    print(f"Done. Recovered {recovered_count} articles.")

if __name__ == "__main__":
    asyncio.run(recover())
