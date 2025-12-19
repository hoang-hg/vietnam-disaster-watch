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

def canon(text: str) -> Tuple[str, str]:
    """
    Returns (t, t0):
      - t  : normalized lowercase text 
      - t0 : accent-stripped, punctuation-normalized, space-collapsed
    """
    t = normalize_text(text)
    t0 = strip_accents(t)

    # normalize punctuation -> space
    t0 = re.sub(r"[^a-zA-Z0-9\s]", " ", t0)
    t0 = re.sub(r"\s+", " ", t0).strip()

    # alias expansion (on t0)
    for pat, repl in ALIASES:
        t0 = re.sub(pat, repl, t0)
    t0 = re.sub(r"\s+", " ", t0).strip()

    return t, t0

def kmh_to_beaufort(kmh: float) -> int:
    # Beaufort scale thresholds (km/h)
    thresholds = [
        (184, 16), (167, 15), (150, 14), (134, 13), (118, 12),
        (103, 11), (89, 10), (75, 9), (62, 8), (50, 7),
        (39, 6), (29, 5), (20, 4), (12, 3), (6, 2), (1, 1),
    ]
    for th, b in thresholds:
        if kmh >= th:
            return b
    return 0

ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
    "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16
}

def _roman_to_int(s: str) -> Optional[int]:
    s = s.lower().strip()
    return ROMAN.get(s)

# --- METRICS EXTRACTION ---

def extract_beaufort_max(text: str) -> Optional[int]:
    t, t0 = canon(text)
    vals: list[int] = []

    # cấp/cap X
    for m in re.finditer(r"(?:cấp|cap)\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # Roman numerals
    for m in re.finditer(r"(?:cấp|cap)\s*([ivx]{1,5})\b", t0, flags=re.IGNORECASE):
        r = _roman_to_int(m.group(1))
        if r is not None:
            vals.append(r)

    # giật cấp ...
    for m in re.finditer(r"giat\s*(?:cap|cấp)?\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # km/h
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:km\s*/\s*h|km\s*h|kmh)\b", t, flags=re.IGNORECASE):
        kmh = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(kmh))

    # m/s (1 m/s = 3.6 km/h)
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*m\s*/\s*s\b", t, flags=re.IGNORECASE):
        ms = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(ms * 3.6))

    if ("siêu bão" in t) or ("sieu bao" in t0):
        vals.append(16)

    return max(vals) if vals else None

def extract_max_mm(text: str) -> Optional[float]:
    t, _ = canon(text)
    cand: list[float] = []

    # range mm
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(2).replace(",", ".")))

    # single mm
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(1).replace(",", ".")))

    # L/m2 (== mm)
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:l|lit|lít)\s*/\s*m\s*(?:2|\^2)\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(1).replace(",", ".")))

    return max(cand) if cand else None

def extract_max_temp(text: str) -> Optional[float]:
    _, t0 = canon(text)
    TEMP_UNIT = r"(?:do\s*c|°\s*c|\bc\b)"
    vals = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(2).replace(",", ".")))
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(1).replace(",", ".")))
    return max(vals) if vals else None

def extract_max_salinity(text: str) -> Optional[float]:
    _, t0 = canon(text)
    UNIT = r"(?:g\s*/\s*l|g\s*l|phan\s*nghin|‰|psu|ppt)"
    vals = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(1).replace(",", ".")))
    return max(vals) if vals else None

def extract_water_level(text: str) -> Optional[float]:
    _, t0 = canon(text)
    CTX = r"(?:muc\s*nuoc|nuoc\s*dang|ngap|do\s*sau|dinh\s*lu|bao\s*dong)"
    m = re.search(
        CTX + r"[^0-9]{0,50}\s+(\d+(?:[.,]\d+)?)(?:\s*(?:-|den)\s*(\d+(?:[.,]\d+)?))?\s*(m|mét|met|cm)\b(?!\s*/)", 
        t0, re.IGNORECASE
    )
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
    m = re.search(r"trong\s*(\d{1,2})\s*ngay", t0)
    if m: return int(m.group(1))
    m = re.search(r"(\d{1,2})\s*ngay\s*toi", t0)
    if m: return int(m.group(1))
    m = re.search(r"keo\s*dai\s*(\d{1,2})\s*ngay", t0)
    if m: return int(m.group(1))
    
    if "nhieu ngay" in t0 or "dai ngay" in t0:
        return 3
    return 0

def extract_quake_mag(text: str) -> Optional[float]:
    _, t0 = canon(text)
    m = re.search(r"\b(?:m|mw|ml)\s*(\d+(?:[.,]\d+)?)\b", t0, re.IGNORECASE)
    if m: return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*do\s*(?:richter)?\b|do\s*lon[^0-9]{0,10}(\d+(?:[.,]\d+)?)\b", t0, re.IGNORECASE)
    if m:
        g = m.group(1) or m.group(2)
        return float(g.replace(",", ".")) if g else None
    return None

# --- RISK ASSESSMENT ---

def assess(text: str, prefer_declared: bool = True) -> dict:
    """
    Assess risk based on extracted metrics.
    Returns: {"hazards": [{"hazard": "storm", "level": 2, ...}, ...]}
    """
    try:
        from .sources import DISASTER_GROUPS
    except ImportError:
        DISASTER_GROUPS = {}

    t, t0 = canon(text)
    hazards = []
    
    # 1. Storm / Wind (Beaufort)
    w = extract_beaufort_max(text)
    if w:
        h_type = "storm" # default
        storm_kws = DISASTER_GROUPS.get("storm", [])
        wind_kws = DISASTER_GROUPS.get("wind_fog", [])
        
        if any(k in t for k in storm_kws): h_type = "storm"
        elif any(k in t for k in wind_kws): h_type = "strong_wind_sea"
        
        lvl = 1
        if w >= 16: lvl = 5
        elif w >= 12: lvl = 4
        elif w >= 10: lvl = 3
        elif w >= 8: lvl = 2
        
        hazards.append({"hazard": h_type, "level": lvl, "value": w, "unit": "beaufort"})

    # 2. Rain (mm)
    rain = extract_max_mm(text)
    if rain:
        lvl = 1
        if rain >= 400: lvl = 3
        elif rain >= 200: lvl = 2
        hazards.append({"hazard": "rain", "level": lvl, "value": rain, "unit": "mm"})
        
    # 3. Flood (water level m)
    wl = extract_water_level(text)
    if wl:
        lvl = 1
        if wl >= 3.0: lvl = 3
        elif wl >= 2.0: lvl = 2
        hazards.append({"hazard": "flood", "level": lvl, "value": wl, "unit": "m"})
        
    # 4. Temperature (Heat/Cold)
    temp = extract_max_temp(text)
    if temp:
        if temp >= 35:
            lvl = 1
            if temp >= 39: lvl = 3
            elif temp >= 37: lvl = 2
            hazards.append({"hazard": "heat", "level": lvl, "value": temp, "unit": "C"})
        elif temp <= 15:
             lvl = 1
             if temp <= 10: lvl = 2
             hazards.append({"hazard": "cold", "level": lvl, "value": temp, "unit": "C"})

    # 5. Earthquake (Magnitude)
    mag = extract_quake_mag(text)
    if mag:
        lvl = 1
        if mag >= 6.0: lvl = 4
        elif mag >= 5.0: lvl = 3
        elif mag >= 4.0: lvl = 2
        hazards.append({"hazard": "quake", "level": lvl, "value": mag, "unit": "M"})
        
    # Salinity
    sal = extract_max_salinity(text)
    if sal:
        hazards.append({"hazard": "saline", "level": 1, "value": sal, "unit": "ppt"})

    return {"hazards": hazards}
