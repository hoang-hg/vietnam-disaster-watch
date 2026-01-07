
import json
from pathlib import Path

log_file = Path(r"d:\viet-disaster-watch\backend\logs\review_potential_disasters.jsonl")
if log_file.exists():
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[:10]:
            try:
                data = json.loads(line)
                score = data.get('score', 0)
                action = data.get('action', 'N/A')
                title = data.get('title', 'N/A')
                print(f"{score} | {action} | {title}")
            except:
                pass
else:
    print("Log file not found")
