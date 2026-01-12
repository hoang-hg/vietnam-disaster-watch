
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(r'd:\viet-disaster-watch\backend'))

from app import nlp
import re

text = "Cảnh báo gió mạnh cấp 6-7 trên vùng biển Cà Mau"
print(f"Testing text: {text}")

t_acc, _ = nlp.risk_lookup.canon(text)
print(f"Normalized (Acc): {t_acc}")

# Check Rules
for label, compiled_acc in nlp.DISASTER_RULES_RE:
    for pat_re in compiled_acc:
        m = pat_re.search(t_acc)
        if m:
            print(f"MATCH: label='{label}', pattern='{pat_re.pattern}', match='{m.group(0)}'")

res = nlp.classify_disaster(text)
print(f"Classify Result: {res}")
