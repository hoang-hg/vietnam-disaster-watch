
import os

file_path = "d:\\viet-disaster-watch\\backend\\test_output_v6.txt"

try:
    with open(file_path, "r", encoding="utf-16") as f:
        content = f.read()
        print(content)
except Exception as e:
    print(f"Error reading utf-16: {e}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(content)
    except Exception as e2:
        print(f"Error reading utf-8: {e2}")
