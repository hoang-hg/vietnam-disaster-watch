
import subprocess
import sys

try:
    result = subprocess.run(
        [sys.executable, "tests/test_disaster_filtering.py"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=r"d:\viet-disaster-watch\backend"
    )
    
    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        if "FAIL" in line or "WRONG_CAT" in line:
            print(line)
            # Print reason line which is likely next
            if i+1 < len(lines) and "Reason:" in lines[i+1]:
                print(lines[i+1])
    
    print("\nSTDERR (if any):")
    print(result.stderr)

except Exception as e:
    print(e)
