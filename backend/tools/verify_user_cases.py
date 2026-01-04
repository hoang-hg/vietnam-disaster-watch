
import sys
import os
import re

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import nlp
from app import sources

# Mock data from user request
test_cases = [
    {
        "title": "Cứu 13 ngư dân của tàu cá bị chìm ở đảo Hòn Chuối",
        "text": "Cứu hộ cứu nạn tàu cá chìm...",
        "expected": True
    },
    {
        "title": "Cứu 13 ngư dân",
        "text": "bình thường",
        "expected": True
    },
    {
        "title": "tàu cá bị chìm",
        "text": "bình thường",
        "expected": True
    },
    {
        "title": "đảo Hòn Chuối",
        "text": "bình thường",
        "expected": True
    }
]

print("🚀 RUNNING VERIFICATION ON USER CASES...\n")
passed_count = 0
total_count = len(test_cases)

for case in test_cases:
    print(f"Testing: {case['title']}")
    # Assume source is Trusted only if it passes normally, but let's test strictly first
    # classify returns (is_disaster, details_dict)
    # We use contains_disaster_keywords directly as it is the main filter
    
    # Check signals
    try:
        signals = nlp.compute_disaster_signals(case['text'], case['title'], trusted_source=True)
    except Exception as e:
        print(f"Error computing signals: {e}")
        signals = {"absolute_veto": False, "score": 0}

    match_veto = signals.get("absolute_veto", False)
    
    if match_veto:
        print(f"  🚨 ABSOLUTE VETO TRIGGERED for: '{case['title']}'")
    
    # We want to know if it passes mainly
    result = nlp.contains_disaster_keywords(case['text'], case['title'], trusted_source=True)
    
    status = "✅ PASS" if result == case['expected'] else "❌ FAIL"
    print(f"  -> Result: {result} (Expected: {case['expected']}) - {status}")
    
    # If failed, print diagnose
    if result != case['expected']:
        signals = nlp.compute_disaster_signals(case['text'], case['title'], trusted_source=True)
        print(f"     [DEBUG] Score: {signals['score']}")
        print(f"     [DEBUG] Veto: Abs={signals['absolute_veto']}, Cond={signals['conditional_veto']}")
        print(f"     [DEBUG] Hazard Score: {signals['hazard_score']}, Hazards: {signals['hazard_counts']}")
        
    print("-" * 50)

print(f"\nSummary: {passed_count}/{total_count} cases passed.")
