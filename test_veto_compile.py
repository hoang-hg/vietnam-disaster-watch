
import re
import sys
from backend.app.sources import ABSOLUTE_VETO, CONDITIONAL_VETO, SOFT_NEGATIVE

def test_pats(pats, name):
    print(f"Testing {name}...")
    for i, p in enumerate(pats):
        try:
            re.compile(p)
        except re.error as e:
            print(f"Error in {name} index {i}: {p}")
            print(f"Reason: {e}")

test_pats(ABSOLUTE_VETO, "ABSOLUTE_VETO")
test_pats(CONDITIONAL_VETO, "CONDITIONAL_VETO")
test_pats(SOFT_NEGATIVE, "SOFT_NEGATIVE")
