
import json
import os

log_file = r'd:\viet-disaster-watch\backend\logs\review_potential_disasters.jsonl'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-5:]:
            try:
                data = json.loads(line)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print(line)
else:
    print("File not found")
