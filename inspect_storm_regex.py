
import re

file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

storm_line = lines[436].strip() # Line 437 is index 436 (0-indexed)
print(f"Line content: {storm_line}")
if len(storm_line) > 291:
    print(f"Char at 291: {storm_line[291]}")
    print(f"Context: {storm_line[280:310]}")
else:
    print("Line shorter than 291 chars")
