
file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"
with open(file_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if "def match_disaster_rules" in line:
            print(f"Line {i+1}: {line.strip()}")
