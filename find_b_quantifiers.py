
import re

file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if re.search(r'\\b[\*\+\?]', line):
        print(f"Line {i+1}: {line.strip()}")
