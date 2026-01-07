
import sys
import os

# Add backend to path so we can import app
sys.path.append(os.getcwd())

from app.nlp import diagnose

samples = [
    "Mở đường tiếp tế lương thực cho 5 thôn bị cô lập xã Ngọc Linh",
    "Tin cảnh báo ngập lụt trên khu vực tỉnh Khánh Hòa",
    "Giải cứu 3 người bị lạc khi leo núi Hoàng Ngưu Sơn",
    "Khai trương quán bar nhạc sống hoành tráng",
    "Trao quyết định bổ nhiệm cán bộ và triển khai nhiệm vụ",
    "Xác pháo đỏ đường sau lễ cưới",
    "Thanh niên rơi xuống hố ga tử vong"
]

print("Testing NLP classification on samples:")
with open("test_output_manual.txt", "w", encoding="utf-8") as f:
    for title in samples:
        f.write("-" * 40 + "\n")
        f.write(f"Title: {title}\n")
        result = diagnose(title, title) # Pass title as text and title
        
        f.write(f"Score: {result['score']}\n")
        f.write(f"Reason: {result['reason']}\n")
        f.write(f"Absolute Veto: {result['signals']['absolute_veto']}\n")
        f.write(f"Negative Matches: {result['signals']['negative_hit']}\n")
        f.write(f"Context: {result['signals'].get('context_matches')}\n")
        f.write(f"Rule Matches: {result['signals'].get('rule_matches')}\n")
print("Results written to test_output_manual.txt")
