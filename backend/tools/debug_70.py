
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app import nlp

t = "Sập cầu khiến giao thông chia cắt, 1 căn nhà bị đổ sập."
res = nlp.extract_impact_details(t)
print(f"Result: {res}")
