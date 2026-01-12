
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(r'd:\viet-disaster-watch\backend'))

from app import nlp

text = "Mưa lớn kéo dài 3 ngày, lượng mưa phổ biến 150-200mm, gây ngập úng cục bộ"
print(f"Testing text: {text}")

# Normalization
t_acc, _ = nlp.risk_lookup.canon(text)
print(f"Normalized (Acc): {t_acc}")

# Check Rules
print("Checking Rules...")
rule_matches, counts, weights, title_match = nlp.match_disaster_rules(t_acc, t_acc) # Pass same text as title for testing
print(f"Matches: {rule_matches}")
print(f"Counts: {counts}")
print(f"Weights: {weights}")

# Check Classify
res = nlp.classify_disaster(text)
print(f"Classify Result: {res}")
