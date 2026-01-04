
import re

with open("d:/viet-disaster-watch/backend/app/nlp.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "DISASTER_RULES =" in line and "RE" not in line:
        print(f"Found at line {i+1}: {line.strip()}")
