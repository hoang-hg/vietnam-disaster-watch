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
POTENTIAL_FILE = Path("d:/viet-disaster-watch/backend/logs/review_potential_disasters.jsonl")
SUCCESS_COUNT = 0

def ingest_item(db: Session, data: dict):
    global SUCCESS_COUNT
    title = data.get("title")
    url = data.get("url")
    source_name = data.get("source")
    
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
        if not hasattr(nlp, 'safe_impact_value'):
            def _safe_val(v):
                if v is None: return None
                if isinstance(v, (int, float)): return v
                if isinstance(v, dict): return v.get("max")
                if isinstance(v, list) and len(v)>0: return v[0].get("max")
                return None
            nlp.safe_impact_value = _safe_val

        with open(POTENTIAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    item_title = data.get("title", "No Title")
                    full_text = f"{item_title}\n{data.get('summary', '')}"
                    class_dict = nlp.classify_disaster(full_text)
                    
                    # VETO Check
                    is_vetoed = False
                    for pat in nlp.ABSOLUTE_VETO:
                        if nlp.re.search(pat, full_text, nlp.re.IGNORECASE):
                            is_vetoed = True
                            break
                    
                    if not is_vetoed and class_dict.get("is_disaster"):
                        if ingest_item(db, data):
                            logger.info(f"[RECOVERED] {item_title} (Type: {class_dict.get('primary_type')})")
                        else:
                            logger.info(f"[DUPLICATE/FAIL] {item_title}")
                    else:
                        if not is_vetoed:
                            logger.info(f"[LOW SIGNAL] {item_title}")
                            remaining_potentials.append(data)
                        else:
                            logger.info(f"[PURGED] {item_title} (Vetoed)")
                except Exception as e:
                    logger.error(f"Error processing line: {e}")
                    continue

    # Update potential file
    with open(POTENTIAL_FILE, "w", encoding="utf-8") as f:
        for p in remaining_potentials:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            
    logger.info(f"Done. Successfully recovered {SUCCESS_COUNT} articles.")

if __name__ == "__main__":
    run_recovery()
