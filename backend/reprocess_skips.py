import json
from pathlib import Path
from app import nlp
from app.database import SessionLocal
from app.models import Article
from app.dedup import find_duplicate_article
from app.event_matcher import upsert_event_for_article

LOGS_DIR = Path("logs")
SKIP_FILE = LOGS_DIR / "skip_debug.jsonl"
REVIEW_FILE = LOGS_DIR / "review_potential_disasters.jsonl"
CLEAN_SKIP_FILE = LOGS_DIR / "skip_debug_cleaned.jsonl"

def reprocess():
    if not SKIP_FILE.exists():
        print("No skip_debug.jsonl found.")
        return

    potentials = []
    cleaned_count = 0
    total_count = 0

    print("Analyzing skips... This might take a while.")
    
    with SessionLocal() as db:
        # We'll write a 'cleaned' version without the absolute garbage
        with open(CLEAN_SKIP_FILE, "w", encoding="utf-8") as clean_f:
            with open(SKIP_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    total_count += 1
                    try:
                        data = json.loads(line)
                        title = data.get("title", "")
                        text = data.get("summary", "") or title # Use summary if available
                        diag = data.get("diagnose", {})
                        
                        # 1. Filter out absolute veto (Trash)
                        if diag.get("signals", {}).get("absolute_veto"):
                            continue
                        
                        # 2. Keep in cleaned file
                        clean_f.write(line)
                        cleaned_count += 1
                        
                        # 3. Look for "Low Score but Disaster-ish"
                        # Only check those with some disaster signals but was rejected
                        score = diag.get("score", 0)
                        rule_matches = diag.get("signals", {}).get("rule_matches", [])
                        
                        if score >= 5.0 and len(rule_matches) > 0:
                            # Re-run current NLP logic to see if it passes now (due to keyword improvements)
                            # or if it's a borderline case
                            is_relevant = nlp.contains_disaster_keywords(text, title=title)
                            
                            if is_relevant:
                                print(f"[POTENTIAL FOUND] {title} (Score: {score})")
                                data["reprocessed_status"] = "PASSED_RECHECK"
                                potentials.append(data)
                                
                                # OPTIONAL: Auto-ingest if it passes current strict logic
                                if not find_duplicate_article(db, title, data.get("domain", "")):
                                    # Create article object
                                    # (Note: Need more fields like image_url, etc. if available)
                                    pass
                    except:
                        continue

    # Save potentials for user review
    with open(REVIEW_FILE, "w", encoding="utf-8") as pf:
        for p in potentials:
            pf.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Total processed: {total_count}")
    print(f"Cleaned (No Veto): {cleaned_count}")
    print(f"Potential Disasters Found: {len(potentials)}")
    print(f"Details saved to {REVIEW_FILE.name}")

if __name__ == "__main__":
    reprocess()
