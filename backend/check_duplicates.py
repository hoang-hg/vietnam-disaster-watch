import re
import sys
from collections import defaultdict

file_path = 'd:/viet-disaster-watch/backend/app/nlp.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_line = -1
end_line = -1

for i, line in enumerate(lines):
    if 'ABSOLUTE_VETO = [' in line:
        start_line = i + 1
    if start_line != -1 and line.strip() == ']':
        end_line = i
        break

if start_line == -1 or end_line == -1:
    print("Could not find ABSOLUTE_VETO list")
    sys.exit(1)

veto_lines = lines[start_line:end_line]
items = []
pattern_to_lines = defaultdict(list)

for i, line in enumerate(veto_lines):
    absolute_line_num = start_line + i + 1
    # Extract string inside r\"...\" or '...'
    match = re.search(r'r?\"(.*?)\"', line)
    if not match:
        match = re.search(r"r?'(.*?)'", line)
    
    if match:
        content = match.group(1).strip()
        if content:
            items.append((content, absolute_line_num))
            pattern_to_lines[content].append(absolute_line_num)

print(f"Total items in ABSOLUTE_VETO: {len(items)}")

duplicates = {p: l for p, l in pattern_to_lines.items() if len(l) > 1}

if not duplicates:
    print("No exact duplicates found.")
else:
    print(f"Found {len(duplicates)} duplicate patterns:")
    for pat, l_nums in duplicates.items():
        print(f"Pattern: {pat}")
        print(f"  Lines: {l_nums}")

# Also check for overlapping terms within the same line (multi-term groups)
all_terms = []
term_to_lines = defaultdict(list)

for content, line_num in items:
    # If it's a group like (?:a|b|c)
    if '(?:' in content and ')' in content:
        inner = re.search(r'\(\?:(.*?)\)', content)
        if inner:
            terms = inner.group(1).split('|')
            for t in terms:
                t = t.strip().replace(r'\s*', ' ')
                term_to_lines[t].append(line_num)
    else:
        t = content.strip().replace(r'\b', '').replace(r'\s*', ' ')
        term_to_lines[t].append(line_num)

duplicate_terms = {t: l for t, l in term_to_lines.items() if len(l) > 1}
if duplicate_terms:
    print(f"\nFound {len(duplicate_terms)} terms appearing in multiple lines:")
    for t, l_nums in sorted(duplicate_terms.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        print(f"Term: {t} -> Lines: {l_nums}")
