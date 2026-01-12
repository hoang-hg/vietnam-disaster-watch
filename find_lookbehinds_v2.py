
import re

file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
for i, line in enumerate(lines):
    if "(?<!" in line or "(?<=" in line:
        # Ignore comments
        s_line = line.strip()
        if s_line.startswith("#"): continue
        
        # Check if it's really part of a regex string
        # Heuristic: contains quote
        if '"' in line or "'" in line:
            print(f"Line {i+1}: {s_line}")
            count += 1

print(f"Found {count} potential lookbehinds.")
