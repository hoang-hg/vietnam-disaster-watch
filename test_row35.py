
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import app.nlp as nlp
import app.sources as sources

title = "Bão số 10: Sẵn sàng phương án, tuyệt đối không chủ quan - dangcongsan.vn"
text = "Nội dung bài báo về công tác ứng phó bão số 10."

diag = nlp.diagnose(text, title=title)
print(f"Diagnosis: {diag}")
