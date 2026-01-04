
import re
import ast

def load_storm_keywords():
    try:
        with open(r"d:\viet-disaster-watch\backend\app\sources.py", "r", encoding="utf-8") as f:
            content = f.read()
            # Extract DISASTER_GROUPS dictionary string
            match = re.search(r'DISASTER_GROUPS\s*=\s*({.*?})\s*$', content, re.DOTALL | re.MULTILINE)
            if not match:
                # Fallback: try to find just the storm list if the big dict regex fails (it might be nested or have comments that break regex)
                # Let's try to parse the file broadly or just find "storm": [...]
                match_storm = re.search(r'"storm":\s*\[(.*?)\]', content, re.DOTALL)
                if match_storm:
                    # Parse the list content
                    list_str = "[" + match_storm.group(1) + "]"
                    return ast.literal_eval(list_str)
                else:
                    print("Could not find storm keywords in sources.py")
                    return []
            
            # If we found the dict, let's try to parse it safely-ish
            # Actually, ast.literal_eval might fail if there are variables.
            # Let's stick to the list extraction
            match_storm = re.search(r'"storm":\s*\[(.*?)\]', content, re.DOTALL)
            if match_storm:
                 list_str = "[" + match_storm.group(1) + "]"
                 return ast.literal_eval(list_str)
            return []
    except Exception as e:
        print(f"Error reading sources.py: {e}")
        return []

def check_matches():
    titles = [
        "Chi Pu diện đầm cá tính tại sự kiện WeYoung 2025",
        "Giá Bitcoin hôm nay 26.12: Tăng giá, dự báo triển vọng tích cực năm 2026",
        "Man Utd overhauls midfield, Bruno Fernandes' position in jeopardy.",
        "Giá vàng châu Á lập kỷ lục mới trong phiên sáng 26/12",
        "Lá chắn laser 'Tia sắt' của Israel chính thức đi vào hoạt động",
         "Tháo gỡ vướng mắc trong tổ chức thi hành Luật Đất đai",
         "Nhìn lại thế giới 2025: Phá vỡ cạm bẫy"
    ]

    storm_keywords = load_storm_keywords()
    print(f"Loaded {len(storm_keywords)} storm keywords.")

    for title in titles:
        print(f"\nTitle: {title}")
        matches = []
        for kw in storm_keywords:
            # Check for word boundary match as nlp.py would (simplified)
            # nlp.py wraps in \b if it's not a path or something. 
            # In regex: \bword\b. 
            # But let's just check containment first.
            
            # 1. Literal containment
            if kw.lower() in title.lower():
                matches.append(f"'{kw}' (Literal)")
                
            # 2. Pattern match (if kw behaves like regex or we enforce word boundaries)
            try:
                # nlp.py logic: v_safe(p).replace(" ", r"\s+")
                # We'll just do simple \b check
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, title, re.IGNORECASE):
                    matches.append(f"'{kw}' (Regex Boundary)")
            except:
                pass
                
        if matches:
            print(f"  FOUND MATCHES: {matches}")
        else:
            print("  No matches found.")

if __name__ == "__main__":
    check_matches()
