
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import app.nlp as nlp
import app.sources as sources

title = "Công điện số 183/CĐ-TTg: Tập trung khắc phục nhanh hậu quả bão số 10 và mưa lũ - dangcongsan.vn"
text = "Công điện của Thủ tướng Chính phủ về việc khắc phục hậu quả bão lụt."

signals = nlp.compute_disaster_signals(text, title=title)
diag = nlp.diagnose(text, title=title)

print(f"Score: {signals['score']}")
print(f"Signals: {signals}")
print(f"Diagnosis: {diag}")
