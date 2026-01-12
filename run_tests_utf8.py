
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
    
    # Write to file with utf-8 encoding explicitly
    with open(r"d:\viet-disaster-watch\test_output_utf8.txt", "w", encoding="utf-8") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\nSTDERR:\n")
            f.write(result.stderr)
            
except Exception as e:
    with open(r"d:\viet-disaster-watch\test_output_utf8.txt", "w", encoding="utf-8") as f:
        f.write(str(e))
