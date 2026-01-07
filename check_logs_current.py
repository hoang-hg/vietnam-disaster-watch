
import json
from pathlib import Path
from backend.app import nlp

log_file = Path(r"d:\viet-disaster-watch\backend\logs\review_potential_disasters.jsonl")
if log_file.exists():
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print("Checking last 100 log entries with CURRENT NLP logic...")
    for line in lines[-100:]:
        try:
            data = json.loads(line)
            title = data.get('title', '')
            text = title # Usually summary is also in log but title is enough for quick check
            diag = nlp.diagnose(text, title=title)
            score = diag['score']
            
            if score >= 10.0:
                print(f"STILL PASSES: {score} | {title} | Reason: {diag['reason']}")
            # else: skip to not flood output
        except Exception as e:
            pass
else:
    print("Log file not found")
