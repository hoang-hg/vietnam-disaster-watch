import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app import nlp
from app.database import SessionLocal
from app.models import Article
from app.dedup import find_duplicate_article
from app.event_matcher import upsert_event_for_article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestPotentials")

LOGS_DIR = Path("logs")
POTENTIAL_FILE = LOGS_DIR / "review_potential_disasters.jsonl"
SUCCESS_COUNT = 0

def ingest_item(db: Session, data: dict):
    global SUCCESS_COUNT
    title = data.get("title")
    url = data.get("url")
    source_name = data.get("source")
    score = data.get("score", 0)
    
    pub_at_str = data.get("published_at")
    if pub_at_str:
        try:
            pub_at = datetime.fromisoformat(pub_at_str.replace("Z", "+00:00"))
        except:
            pub_at = datetime.now(timezone.utc)
    else:
        pub_at = datetime.now(timezone.utc)

    # Check if already exists in DB
    if find_duplicate_article(db, data.get("domain", ""), url, title, pub_at):
        return False

    # Extract details again to be sure
    full_text = data.get("title", "") + " " + (data.get("summary", "") or "")
    disaster_info = nlp.classify_disaster(full_text)
    province = nlp.extract_province(full_text)
    impacts = nlp.extract_impacts(full_text)
    summary = nlp.summarize(data.get("summary", "") or title, title=title)
    stage = nlp.determine_event_stage(full_text)

    # Convert to Article model
    article = Article(
        source=source_name,
        domain=data.get("domain", "reprocessed"),
        title=title,
        url=url,
        published_at=pub_at,
        disaster_type=disaster_info.get("primary_type", "unknown"),
        province=province,
        stage=stage,
        deaths=nlp.safe_impact_value(impacts["deaths"]),
        missing=nlp.safe_impact_value(impacts["missing"]),
        injured=nlp.safe_impact_value(impacts["injured"]),
        damage_billion_vnd=nlp.safe_impact_value(impacts["damage_billion_vnd"]),
        summary=summary,
        impact_details=nlp.extract_impact_details(full_text)
    )

    try:
        db.add(article)
        db.flush()
        # Attach to event
        upsert_event_for_article(db, article)
        db.commit()
        SUCCESS_COUNT += 1
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting {title}: {e}")
        return False

def run_recovery():
    if not POTENTIAL_FILE.exists():
        logger.info("No potentials to recover.")
        return

    logger.info(f"Checking potentials in {POTENTIAL_FILE}...")
    remaining_potentials = []
    
    with SessionLocal() as db:
        with open(POTENTIAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    score = data.get("score", 0)
                    
                    # RECOVERY LOGIC: Ingest if score is good enough (e.g. > 8.5)
                    # or if it has clear Disaster + Province info
                    diag = data.get("diagnose", {})
                    has_prov = diag.get("province") is not None
                    has_hazard = len(diag.get("rule_matches", [])) > 0
                    
                    if score >= 9.5 or (score >= 8.5 and has_prov and has_hazard):
                        if ingest_item(db, data):
                            logger.info(f"[RECOVERED] {data['title']} (Score: {score})")
                        else:
                            # If duplicate, just don't keep in potentials
                            pass
                    else:
                        # Keep for manual review later
                        remaining_potentials.append(data)
                except Exception:
                    continue

    # Update the potential file (remove recovered ones)
    with open(POTENTIAL_FILE, "w", encoding="utf-8") as f:
        for p in remaining_potentials:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            
    logger.info(f"Done. Successfully recovered {SUCCESS_COUNT} articles.")

if __name__ == "__main__":
    # Add helper to nlp if not exists for safe value extraction
    if not hasattr(nlp, 'safe_impact_value'):
        def _safe_val(v):
            if v is None: return None
            if isinstance(v, (int, float)): return v
            if isinstance(v, dict): return v.get("max")
            if isinstance(v, list) and len(v)>0: return v[0].get("max")
            return None
        nlp.safe_impact_value = _safe_val
        
    run_recovery()
