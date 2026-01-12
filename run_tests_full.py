
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
    
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
            
except Exception as e:
    print(f"Error running test: {e}")
