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

# --- PRE-COMPILED REGEX FOR METRICS ---
RE_BEAUFORT = re.compile(r"(?<!khan\s)(?<!khẩn\s)(?:cấp|cap)\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", re.IGNORECASE)
RE_BEAUFORT_ROMAN = re.compile(r"(?:cấp|cap)\s*([ivx]{1,5})\b", re.IGNORECASE)
RE_BEAUFORT_GUST = re.compile(r"giat\s*(?:cap|cấp)?\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", re.IGNORECASE)
RE_KMH = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:km\s*/\s*h|km\s*h|kmh)\b", re.IGNORECASE)
RE_MS = re.compile(r"(\d+(?:[.,]\d+)?)\s*m\s*/\s*s\b", re.IGNORECASE)

RE_MM_RANGE = re.compile(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mm\b", re.IGNORECASE)
RE_MM_SINGLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm\b", re.IGNORECASE)
RE_MM_LM2 = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:l|lit|lít)\s*/\s*m\s*(?:2|\^2)\b", re.IGNORECASE)

UNIT_T = r"(?:°\s*c)"
UNIT_T0 = r"(?:do\s*c|\bc\b)"
RE_TEMP_RANGE_T = re.compile(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + UNIT_T, re.IGNORECASE)
RE_TEMP_SINGLE_T = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_T, re.IGNORECASE)
RE_TEMP_RANGE_T0 = re.compile(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + UNIT_T0, re.IGNORECASE)
RE_TEMP_SINGLE_T0 = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_T0, re.IGNORECASE)

UNIT_S_T = r"(?:‰|psu|ppt)"
UNIT_S_T0 = r"(?:g\s*/\s*l|g\s*l|phan\s*nghin)"
RE_SALINITY_T = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_S_T, re.IGNORECASE)
RE_SALINITY_T0 = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_S_T0, re.IGNORECASE)

CTX_WATER = r"(?:muc\s*nuoc|nuoc\s*dang|ngap|do\s*sau|dinh\s*lu|bao\s*dong)"
RE_WATER_LEVEL = re.compile(CTX_WATER + r"[^0-9]{0,50}\s+(\d+(?:[.,]\d+)?)(?:\s*(?:-|den)\s*(\d+(?:[.,]\d+)?))?\s*(m|mét|met|cm)\b(?!\s*/)", re.IGNORECASE)

RE_DURATION_NGAY = re.compile(r"trong\s*(\d{1,2})\s*ngay", re.IGNORECASE)
RE_DURATION_NGAY_TOI = re.compile(r"(\d{1,2})\s*ngay\s*toi", re.IGNORECASE)
RE_DURATION_KEO_DAI = re.compile(r"keo\s*dai\s*(\d{1,2})\s*ngay", re.IGNORECASE)

RE_QUAKE_MW_ML = re.compile(r"\b(?:mw|ml)\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
RE_QUAKE_ANCHOR = re.compile(r"(?:dong\s*dat|chan\s*dong|dia\s*chan)", re.IGNORECASE)
RE_QUAKE_M = re.compile(r"\bm\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
RE_QUAKE_RICHTER = re.compile(r"(\d+(?:[.,]\d+)?)\s*do\s*(?:richter)?\b|do\s*lon[^0-9]{0,10}(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)

def _roman_to_int(s: str) -> Optional[int]:
    s = s.lower().strip()
    return ROMAN.get(s)

# --- METRICS EXTRACTION ---

def extract_beaufort_max(text: str) -> Optional[int]:
    t, t0 = canon(text)
    vals: list[int] = []

    # cấp/cap X (exclude 'khẩn cấp')
    for m in RE_BEAUFORT.finditer(t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # Roman numerals
    for m in RE_BEAUFORT_ROMAN.finditer(t0):
        r = _roman_to_int(m.group(1))
        if r is not None:
            vals.append(r)

    # giật cấp ...
    for m in RE_BEAUFORT_GUST.finditer(t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # km/h
    for m in RE_KMH.finditer(t):
        kmh = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(kmh))

    # m/s (1 m/s = 3.6 km/h)
    for m in RE_MS.finditer(t):
        ms = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(ms * 3.6))

    if ("siêu bão" in t) or ("sieu bao" in t0):
        vals.append(16)

    return max(vals) if vals else None

def extract_max_mm(text: str) -> Optional[float]:
    t, _ = canon(text)
    cand: list[float] = []

    # range mm
    for m in RE_MM_RANGE.finditer(t):
        cand.append(float(m.group(2).replace(",", ".")))

    # single mm
    for m in RE_MM_SINGLE.finditer(t):
        cand.append(float(m.group(1).replace(",", ".")))

    # L/m2 (== mm)
    for m in RE_MM_LM2.finditer(t):
        cand.append(float(m.group(1).replace(",", ".")))

    return max(cand) if cand else None

def extract_max_temp(text: str) -> Optional[float]:
    t, t0 = canon(text)
    # Check both t and t0 to handle both °C and "do C"
    # Try with t for °C
    for m in RE_TEMP_RANGE_T.finditer(t):
         vals.append(float(m.group(2).replace(",", ".")))
    for m in RE_TEMP_SINGLE_T.finditer(t):
         vals.append(float(m.group(1).replace(",", ".")))
    # Try with t0 for "do C"
    for m in RE_TEMP_RANGE_T0.finditer(t0):
         vals.append(float(m.group(2).replace(",", ".")))
    for m in RE_TEMP_SINGLE_T0.finditer(t0):
         vals.append(float(m.group(1).replace(",", ".")))
    return max(vals) if vals else None

def extract_max_salinity(text: str) -> Optional[float]:
    t, t0 = canon(text)
    # Symbols in t, text keywords in t0
    for m in RE_SALINITY_T.finditer(t):
         vals.append(float(m.group(1).replace(",", ".")))
    for m in RE_SALINITY_T0.finditer(t0):
         vals.append(float(m.group(1).replace(",", ".")))
    return max(vals) if vals else None

def extract_water_level(text: str) -> Optional[float]:
    _, t0 = canon(text)
    m = RE_WATER_LEVEL.search(t0)
    if m:
        v1 = float(m.group(1).replace(",", "."))
        v2 = float(m.group(2).replace(",", ".")) if m.group(2) else v1
        val = max(v1, v2)
        unit = m.group(3).lower()
        if "cm" in unit: val /= 100.0
        return val
    return None

def extract_duration_days_count(text: str) -> int:
    _, t0 = canon(text)
    m = RE_DURATION_NGAY.search(t0)
    if m: return int(m.group(1))
    m = RE_DURATION_NGAY_TOI.search(t0)
    if m: return int(m.group(1))
    m = RE_DURATION_KEO_DAI.search(t0)
    if m: return int(m.group(1))
    
    if "nhieu ngay" in t0 or "dai ngay" in t0:
        return 3
    return 0

def extract_quake_mag(text: str) -> Optional[float]:
    _, t0 = canon(text)
    m = RE_QUAKE_MW_ML.search(t0)
    if m: return float(m.group(1).replace(",", "."))
    # For single 'm', require it to be 'm 5.0' appearing after 'dong dat' or 'chan dong'
    if RE_QUAKE_ANCHOR.search(t0):
        m = RE_QUAKE_M.search(t0)
        if m: return float(m.group(1).replace(",", "."))
    m = RE_QUAKE_RICHTER.search(t0)
    if m:
        g = m.group(1) or m.group(2)
        return float(g.replace(",", ".")) if g else None
    return None
