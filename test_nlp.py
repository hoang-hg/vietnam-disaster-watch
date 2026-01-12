
import sys
import os
# Adjust path to include backend/app
sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))
# Also add backend to path if needed for relative imports to work when run as module
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import app.nlp as nlp
import app.sources as sources

title = "Tập trung triển khai các biện pháp ứng phó với bão số 11 - dangcongsan.vn"
text = "Nội dung bài báo về việc triển khai các biện pháp ứng phó bão số 11."

signals = nlp.compute_disaster_signals(text, title=title)
diag = nlp.diagnose(text, title=title)

print(f"Score: {signals['score']}")
print(f"Signals: {signals}")
print(f"Diagnosis: {diag}")
