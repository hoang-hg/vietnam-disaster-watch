
import json
with open('backend/logs/review_potential_disasters.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()[-30:]

with open('last_logs.txt', 'w', encoding='utf-8') as f:
    for l in lines:
        try:
            data = json.loads(l)
            score = data.get('score', 0)
            title = data.get('title', 'NO TITLE')
            f.write(f"{score}: {title}\n")
        except:
            pass
