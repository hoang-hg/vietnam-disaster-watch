
try:
    with open(r'd:\viet-disaster-watch\backend\test_full_output.txt', 'r', encoding='utf-16') as f:
        print(f.read())
except Exception:
    try:
        with open(r'd:\viet-disaster-watch\backend\test_full_output.txt', 'r', encoding='utf-8') as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading file: {e}")
