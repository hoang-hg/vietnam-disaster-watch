
import json
import os
import sys
import re
from pathlib import Path

# Add backend to path to import app modules
sys.path.insert(0, os.path.abspath('d:/viet-disaster-watch/backend'))

from app import nlp

POTENTIAL_FILE = Path("d:/viet-disaster-watch/backend/logs/review_potential_disasters.jsonl")
OUT_FILE = Path("d:/viet-disaster-watch/backend/test_10_results.txt")

def test_10():
    if not POTENTIAL_FILE.exists():
        return

    lines_out = []
    lines_out.append(f"{'STT':<4} | {'QUYẾT ĐỊNH':<12} | {'LOẠI':<15} | {'VETO TRIGGER'}")
    lines_out.append("-" * 120)

    with open(POTENTIAL_FILE, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            if count >= 10:
                break
            try:
                data = json.loads(line)
                title = data.get("title", "No Title").strip()
                summary = data.get("summary", "") or ""
                full_text = f"{title} {summary}"
                
                class_dict = nlp.classify_disaster(full_text)
                is_disaster = class_dict.get("is_disaster", False)
                p_type = class_dict.get("primary_type", "unknown")
                
                decision = "CHẤP NHẬN" if is_disaster else "LOẠI BỎ"
                trigger = "None"
                
                for pat in nlp.ABSOLUTE_VETO:
                    match = re.search(pat, full_text, re.IGNORECASE)
                    if match:
                        decision = "VETO"
                        trigger = pat[:50] + " -> " + str(match.group(0))
                        break

                lines_out.append(f"{count+1:<4} | {decision:<12} | {p_type:<15} | {trigger}")
                lines_out.append(f"     Tiêu đề: {title}")
                count += 1
            except Exception:
                continue

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

if __name__ == "__main__":
    test_10()
