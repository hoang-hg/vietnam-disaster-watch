
import sys
import os
sys.path.append(os.getcwd())
from app.nlp import ABSOLUTE_VETO

try:
    pat = ABSOLUTE_VETO[704]
    print(f"ABSOLUTE_VETO[704] = {pat}")
except IndexError:
    print(f"Index 704 out of bounds. Length: {len(ABSOLUTE_VETO)}")
