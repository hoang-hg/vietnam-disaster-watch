
import re

with open("d:/viet-disaster-watch/backend/app/nlp.py", "r", encoding="utf-8") as f:
    content = f.readlines()

found_line = -1
for i, line in enumerate(content):
    if "PROVINCES =" in line:
        print(f"Found on line {i+1}: {line.strip()}")
        found_line = i
        break

if found_line != -1:
    # Print next 50 lines to see the list
    for j in range(found_line + 1, min(len(content), found_line + 100)):
        print(content[j].strip())
else:
    print("PROVINCES = not found")
