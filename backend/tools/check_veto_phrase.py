
import sys
import os
import re

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import nlp

text = "tàu cá bị chìm"
# Check both normalized and unaccented
t, t0 = nlp.risk_lookup.canon(text)

print(f"Testing text: '{text}'")
print(f"Normalized t: '{t}'")
print(f"Unaccented t0: '{t0}'")

print("Checking ABSOLUTE_VETO_RE (Accent sensitive):")
for i, r in enumerate(nlp.ABSOLUTE_VETO_RE):
    if r.search(t):
        print(f"  MATCH VETO #{i}: {r.pattern}")

print("Checking ABSOLUTE_VETO_NO_RE (Unaccented):")
for i, r in nlp.ABSOLUTE_VETO_NO_RE:
    if r.search(t0):
        print(f"  MATCH VETO (Unaccented) #{i}: {r.pattern}")
