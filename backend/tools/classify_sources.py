import json
from pathlib import Path

def classify_sources():
    json_path = Path("sources.json")
    if not json_path.exists():
        print("File sources.json not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. List of strictly UNTRUSTED (Aggregators/Commercial/High-noise)
    untrusted_domains = [
        "baomoi.com", "24h.com.vn", "soha.vn", "vietbao.vn", 
        "nguoiduatin.vn", "doisongphapluat.com.vn", "tinmoi.vn",
        "kenh14.vn", "zingnews.vn"
    ]
    untrusted_keywords = [
        "tổng hợp", "giải trí", "tin mới", "người đưa tin"
    ]

    count_true = 0
    count_false = 0

    for s in data["sources"]:
        name = s["name"].lower()
        domain = s["domain"].lower()

        # Check if it falls into untrusted category
        is_untrusted = False
        if any(d in domain for d in untrusted_domains):
            is_untrusted = True
        if any(kw in name for kw in untrusted_keywords):
            is_untrusted = True

        if is_untrusted:
            s["trusted"] = False
            count_false += 1
        else:
            # Everything else (Gov, Province, Major Papers) is Trusted
            s["trusted"] = True
            count_true += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Update complete: {count_true} Trusted sources, {count_false} Untrusted sources.")

if __name__ == "__main__":
    classify_sources()
