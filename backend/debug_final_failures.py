
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(r'd:\viet-disaster-watch\backend'))

from app import nlp
import re

def test_text(text):
    print(f"--- Testing: {text} ---")
    t_acc, _ = nlp.risk_lookup.canon(text)
    sig = nlp.compute_disaster_signals(text)
    print(f"Score: {sig['score']}")
    print(f"Hazard Score: {sig['hazard_score']}")
    print(f"Weights: {sig['hazard_weights']}")
    print(f"Whitelisted: {sig['is_whitelisted']}")
    print(f"Impact hits: {sig['impact_hits']}")
    print(f"Location found: {sig['is_province_match'] or sig['is_sensitive_location']}")
    
    is_disaster = nlp.contains_disaster_keywords(text)
    print(f"IS_DISASTER: {is_disaster}")
    
    cls = nlp.classify_disaster(text)
    print(f"Category: {cls['primary_type']}")

test_text("Thủy điện xả lũ, hạ du nguy cơ ngập lụt diện rộng")
test_text("Cảnh báo sóng thần sau động đất lớn ngoài khơi Philippines")
