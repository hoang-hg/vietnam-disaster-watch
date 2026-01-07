
import json
import collections

log_path = r"d:\viet-disaster-watch\backend\logs\review_potential_disasters.jsonl"

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = collections.deque(f, 10)
        for line in lines:
            try:
                data = json.loads(line)
                print(f"Title: {data.get('title')}")
                print(f"Score: {data.get('score')}")
                print(f"Reason: {data.get('reasons')}")
                print("-" * 20)
            except json.JSONDecodeError:
                pass
except FileNotFoundError:
    print("Log file not found.")
