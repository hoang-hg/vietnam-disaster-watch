
from backend.app import nlp

title = "Triệt phá đường dây mua bán người, giải cứu 3 nạn nhân ô tô ở TP.HCM"
text = title
diag = nlp.diagnose(text, title=title)
print(f"Title: {title}")
print(f"Score: {diag['score']}")
print(f"Signals: {diag['signals']}")
print(f"Reason: {diag['reason']}")
