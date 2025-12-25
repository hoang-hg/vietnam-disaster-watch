import re
import sys

# Extract ABSOLUTE_VETO and CONDITIONAL_VETO from nlp.py
with open('d:/viet-disaster-watch/backend/app/nlp.py', 'r', encoding='utf-8') as f:
    content = f.read()

def extract_list(name, text):
    start_match = re.search(rf'{name}\s*=\s*\[', text)
    if not start_match: return []
    start = start_match.end()
    # Find the closing square bracket matching the balance
    balance = 1
    i = start
    while balance > 0 and i < len(text):
        if text[i] == '[': balance += 1
        elif text[i] == ']': balance -= 1
        i += 1
    list_text = text[start:i-1]
    # Extract items using regex (r\"...\" or '...')
    # Simplified extraction that handles backslashes better
    matches = re.findall(r'r\"((?:\\.|[^\"\\])*)\"|r\'((?:\\.|[^\'\\])*)\'|\"((?:\\.|[^\"\\])*)\"|\'((?:\\.|[^\'\\])*)\'', list_text)
    items = []
    for m in matches:
        for group in m:
            if group:
                items.append(group)
    return items

abs_veto_raw = extract_list('ABSOLUTE_VETO', content)
cond_veto_raw = extract_list('CONDITIONAL_VETO', content)

def clean_items(raw):
    # Remove duplicates but keep some order for readability or grouping
    seen = set()
    unique = []
    for i in raw:
        i = i.strip()
        if i and i not in seen:
            seen.add(i)
            unique.append(i)
    return unique

unique_abs = clean_items(abs_veto_raw)
unique_cond = clean_items(cond_veto_raw)

print(f'--- {len(unique_abs)} UNIQUE ABSOLUTE VETO ---')
for i in unique_abs: print(i)
print(f'\n--- {len(unique_cond)} UNIQUE CONDITIONAL VETO ---')
for i in unique_cond: print(i)
