
file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
changed = False
for line in lines:
    if '(?<!báo' in line and 'storm' in lines[lines.index(line)-1] if lines.index(line)>0 else False:
        # Heuristic to find the correct line (line 437 approx)
        # Or just match content
        pass
    
    if '(?<!báo' in line and '(?<!tin' in line:
        line = line.replace(r'\s', ' ')
        changed = True
        print("Fixed storm regex line.")
    
    new_lines.append(line)

if not changed:
    # Try searching generically for loop
    for i, line in enumerate(new_lines):
        if '(?<!báo' in line:
            new_lines[i] = line.replace(r'\s', ' ')
            changed = True
            print(f"Fixed storm regex line at {i+1}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

if not changed:
    print("Could not find storm regex line to fix.")
