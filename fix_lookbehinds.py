
import re

file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences
# Note: In string literals, backslash is already escaped if raw string?
# In file content, regex string r"(?<!\w)" appears as literal characters: '(', '?', '<', '!', '\\', 'w', ')'
# So we replace that substring.

new_content = content.replace(r"(?<!\w)", r"\b")
new_content = new_content.replace(r"(?!\w)", r"\b")

# Also fix the weird lookbehinds in extract_wind section just in case I missed any or if script runs before manual fix (though I manually fixed wind already)
# But I removed them in previous step.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replaced all variable width lookbehind/lookahead markers with boundary anchors.")
