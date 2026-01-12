
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import app.nlp as nlp
import app.sources as sources

title = "Chăm sóc sầu riêng sau bão - sntv.vn"
text = "Hướng dẫn chăm sóc sầu riêng sau cơn bão để phục hồi sản xuất."

diag = nlp.diagnose(text, title=title)
print(f"Diagnosis: {diag}")
