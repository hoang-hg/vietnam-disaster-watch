
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app import nlp

texts = [
    "Nước dâng do bão làm ngập 1.200 hộ dân vùng trũng.",
    "Ngập sâu khiến 1.600 hộ dân bị chia cắt.",
    "Mưa cực đoan làm cô lập 150 hộ dân.",
    "Đám cháy làm sập 5 căn nhà gần rừng.",
    "Sập cầu khiến giao thông chia cắt, 1 căn nhà bị đổ sập."
]

for t in texts:
    res = nlp.extract_impact_details(t)
    print(f"Text: {t}")
    print(f"Result: {res}")
    print("-" * 20)
