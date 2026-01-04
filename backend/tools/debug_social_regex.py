
import re

text = "cà mau: cứu 13 ngư dân của tàu cá bị chìm ở đảo hòn chuối\ncứu hộ cứu nạn tàu cá chìm..."
text_unaccented = "ca mau: cuu 13 ngu dan cua tau ca bi chim o dao hon chuoi\ncuu ho cuu nan tau ca chim..."

social_regex = r"\b(?:án\s*mạng|hành\s*hạ|ngược\s*đãi|ma\s*túy|thuốc\s*lắc|đánh\s*bạc|sới\s*bạc|casino|cá\s*độ|đá\s*gà|mại\s*dâm|buôn\s*lậu|hàng\s*lậu|hàng\s*cấm|tàng\s*trữ|hàng\s*giả|lừa\s*đảo|chiếm\s*đoạt|truy\s*nã|nghi\s*phạm|hung\s*thủ|sát\s*hại|bạo\s*hành|bắt\s*cóc|trục\s*lợi|giả\s*chết|karaoke)\b"

pat = re.compile(social_regex, re.IGNORECASE)

print(f"Testing Social Regex against normalized text...")
match = pat.search(text)
if match:
    print(f"MATCH (Accented): '{match.group(0)}'")
else:
    print("NO MATCH (Accented)")

match = pat.search(text_unaccented)
if match:
    print(f"MATCH (Unaccented): '{match.group(0)}'")
else:
    print("NO MATCH (Unaccented)")

# Test splitting to find partials
parts = social_regex.replace(r"\b(?:", "").replace(r")\b", "").split("|")
for p in parts:
    sub_pat = re.compile(r"\b" + p + r"\b", re.IGNORECASE)
    if sub_pat.search(text):
         print(f"  -> Sub-match (Accented): {p}")
    if sub_pat.search(text_unaccented):
         print(f"  -> Sub-match (Unaccented): {p}")
