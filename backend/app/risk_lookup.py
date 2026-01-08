import re
import unicodedata
from typing import Union, Optional, Tuple, Iterable

# --- UTILITIES ---

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).lower()
    # Normalize hyphens
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d")

ALIASES = [
    (r"\btphcm\b", "tp ho chi minh"),
    (r"\bhcmc\b", "tp ho chi minh"),
    (r"\btp\s*hcm\b", "tp ho chi minh"),
    (r"\bbrvt\b", "ba ria vung tau"),
    (r"\bdaklak\b", "dak lak"),
    (r"\bdaknong\b", "dak nong"),
    (r"\bkontum\b", "kon tum"),
]

# Pre-compile alias regexes
ALIASES_RE = [(re.compile(pat), repl) for pat, repl in ALIASES]

def canon(text: str) -> Tuple[str, str]:
    """
    Returns (t, t0):
      - t  : normalized lowercase text 
      - t0 : accent-stripped, punctuation-normalized, space-collapsed
    """
    if not text: return "", ""
    t = normalize_text(text)
    # Ensure NFC normalization for 't' (Accented channel) to match standard Python Regex inputs
    t = unicodedata.normalize("NFC", t)
    t0 = strip_accents(t)

    # normalize punctuation -> space, but PRESERVE decimals (e.g. 2.5)
    # We replace punctuation with space ONLY if it's not between digits or part of a decimal
    t0 = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", t0)
    t0 = re.sub(r"[^a-zA-Z0-9.,\s]", " ", t0)
    t0 = re.sub(r"\s+", " ", t0).strip()

    # alias expansion (on t0) using pre-compiled regexes
    for pat_re, repl in ALIASES_RE:
        t0 = pat_re.sub(repl, t0)
    t0 = re.sub(r"\s+", " ", t0).strip()

    return t, t0

# Beaufort scale thresholds (km/h) - Module level constant
BEAUFORT_THRESHOLDS = [
    (184, 16), (167, 15), (150, 14), (134, 13), (118, 12),
    (103, 11), (89, 10), (75, 9), (62, 8), (50, 7),
    (39, 6), (29, 5), (20, 4), (12, 3), (6, 2), (1, 1),
]

def kmh_to_beaufort(kmh: float) -> int:
    for th, b in BEAUFORT_THRESHOLDS:
        if kmh >= th:
            return b
    return 0

ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
    "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16
}

# --- METRICS EXTRACTION UTILS ---

def _roman_to_int(s: str) -> Optional[int]:
    s = s.lower().strip()
    return ROMAN.get(s)
