import re
import unicodedata
import json
import os
from typing import Iterable, Union, Optional, Tuple, Set

# Load Flood Zones Data
FLOOD_ZONES_DATA = {}
try:
    _fz_path = os.path.join(os.path.dirname(__file__), "..", "data", "flood_zones.json")
    if os.path.exists(_fz_path):
        with open(_fz_path, "r", encoding="utf-8") as f:
            FLOOD_ZONES_DATA = json.load(f)
except Exception:
    pass

PatternLike = Union[str, re.Pattern]

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

def has_phrase(t0: str, phrase: str) -> bool:
    return bool(re.search(rf"\b{re.escape(phrase)}\b", t0))

def has_any(text: str, patterns: Iterable[PatternLike]) -> bool:
    if not text:
        return False
    for p in patterns:
        if isinstance(p, re.Pattern):
            if p.search(text):
                return True
        else:
            # treat p as regex string
            if re.search(p, text, flags=re.IGNORECASE | re.UNICODE):
                return True
    return False

# --- PARSERS ---

def kmh_to_beaufort(kmh: float) -> int:
    # Ngưỡng xấp xỉ theo thang Beaufort (km/h)
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
    "i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,
    "x":10,"xi":11,"xii":12,"xiii":13,"xiv":14,"xv":15,"xvi":16
}

RISK_DECL_PAT = re.compile(
    r"(?:cap\s*do\s*)?rui\s*ro\s*thien\s*tai[^0-9ivx]{0,20}"
    r"(?:cap\s*)?(\d{1,2}|[ivx]{1,5})\b",
    flags=re.IGNORECASE
)

def extract_declared_risk_level(text: str) -> Optional[int]:
    _, t0 = canon(text)
    vals: list[int] = []
    for m in RISK_DECL_PAT.finditer(t0):
        s = m.group(1).lower()
        if s.isdigit():
            vals.append(int(s))
        else:
            r = _roman_to_int(s)
            if r is not None:
                vals.append(r)
    # clamp to 1..5
    vals = [v for v in vals if 1 <= v <= 5]
    return max(vals) if vals else None

def extract_rain_accum(text: str) -> dict:
    """
    Return dict with keys: mm_24, mm_48, mm_72 if detected.
    Accepts patterns like 'trong 24 giờ', '24h', '48 giờ', '72h'.
    """
    _, t0 = canon(text)
    out = {}

    def _max_mm_near(pat_time: str) -> Optional[float]:
        m = re.search(pat_time, t0)
        if not m:
            return None
        start = max(0, m.start() - 120)
        end = min(len(t0), m.end() + 120)
        window = t0[start:end]
        cand = [float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*mm\b", window)]
        return max(cand) if cand else None

    out["mm_24"] = _max_mm_near(r"(24\s*h|24\s*gio|trong\s*24\s*gio)")
    out["mm_48"] = _max_mm_near(r"(48\s*h|48\s*gio|trong\s*48\s*gio)")
    out["mm_72"] = _max_mm_near(r"(72\s*h|72\s*gio|trong\s*72\s*gio)")
    return {k:v for k,v in out.items() if v is not None}

def _roman_to_int(s: str) -> Optional[int]:
    s = s.lower().strip()
    return ROMAN.get(s)

def extract_beaufort_max(text: str) -> Optional[int]:
    t, t0 = canon(text)
    vals: list[int] = []

    # cấp/cap X hoặc X-Y hoặc X,Y hoặc X đến Y
    for m in re.finditer(r"(?:cấp|cap)\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # Roman numerals: Cấp XI, XII...
    for m in re.finditer(r"(?:cấp|cap)\s*([ivx]{1,5})\b", t0, flags=re.IGNORECASE):
        r = _roman_to_int(m.group(1))
        if r is not None:
            vals.append(r)

    # giật cấp ...
    for m in re.finditer(r"giat\s*(?:cap|cấp)?\s*(\d{1,2})(?:\s*(?:-|,|den|toi)\s*(\d{1,2}))?", t0):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals.append(max(a, b))

    # gió theo km/h (dùng t để giữ dấu / hoặc t0 với km h)
    for m in re.finditer(
        r"gio[^0-9]{0,30}(\d+(?:[.,]\d+)?)\s*(?:km\s*/\s*h|km\s*h|kmh)\b",
        t,  # using t to matched normalized text preserving /
        flags=re.IGNORECASE | re.UNICODE
    ):
        kmh = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(kmh))

    # gió theo m/s (có ngữ cảnh "gió" gần đó) 1 m/s = 3.6 km/h
    for m in re.finditer(
        r"gio[^0-9]{0,30}(\d+(?:[.,]\d+)?)\s*m\s*/\s*s\b",
        t, flags=re.IGNORECASE | re.UNICODE
    ):
        ms = float(m.group(1).replace(",", "."))
        vals.append(kmh_to_beaufort(ms * 3.6))

    if ("siêu bão" in t) or ("sieu bao" in t0):
        vals.append(16)

    return max(vals) if vals else None

def extract_max_mm_24h(text: str) -> Optional[float]:
    cand: list[float] = []
    t, _ = canon(text)

    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(2).replace(",", ".")))
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(1).replace(",", ".")))

    # L/m2 == mm
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:l|lit|lít)\s*/\s*m\s*(?:2|\^2)\b", t, flags=re.IGNORECASE):
        cand.append(float(m.group(1).replace(",", ".")))

    return max(cand) if cand else None

def extract_max_meters(text: str) -> Optional[float]:
    """
    Parse mét (m/mét/met) và cm -> m.
    Loại bỏ trường hợp m/s (vận tốc gió, dòng chảy...) để tránh nhầm.
    """
    t, _ = canon(text)
    cand: list[float] = []

    # meters, but NOT m/s
    for m in re.finditer(
        r"(\d+(?:[.,]\d+)?)\s*(?:m|mét|met)\b(?!\s*(?:/s|\^?[23]\b|[23]\b))",
        t,
        flags=re.IGNORECASE | re.UNICODE,
    ):
        cand.append(float(m.group(1).replace(",", ".")))

    # centimeters -> meters
    for m in re.finditer(
        r"(\d+(?:[.,]\d+)?)\s*cm\b",
        t,
        flags=re.IGNORECASE | re.UNICODE,
    ):
        cand.append(float(m.group(1).replace(",", ".")) / 100.0)

    return max(cand) if cand else None

def extract_duration_days_bucket(text: str) -> Optional[str]:
    _, t0 = canon(text)

    if re.search(r"\b(5|6|7|8|9|10)\s*(ngay|ngay dem|tuan)\b|nhieu\s*ngay|dai\s*ngay", t0):
        return ">4"

    if re.search(r"(tren|hon)\s*2\s*ngay|2\s*-\s*4\s*ngay|\b3\s*ngay\b|\b4\s*ngay\b|keo\s*dai|48\s*gio|72\s*gio", t0):
        return "2-4"

    if re.search(r"1\s*-\s*2\s*ngay|\b24\s*h\b|\b24\s*gio\b|\b1\s*ngay\s*dem\b", t0):
        return "1-2"

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
    if "tu 3 ngay" in t0: return 3
    return 0

def extract_visibility_m(text: str) -> Optional[int]:
    t, t0 = canon(text)
    # Range km
    m = re.search(r"(tam\s*nhin|visibility)[^0-9]{0,40}(\d+(?:[.,]\d+)?)(?:\s*-\s*(\d+(?:[.,]\d+)?))?\s*km\b", t0)
    if m:
        a = float(m.group(2).replace(",", "."))
        b = float(m.group(3).replace(",", ".")) if m.group(3) else a
        return int(max(a, b) * 1000)
    
    # 500m
    m = re.search(r"(tam\s*nhin|visibility)[^0-9]{0,40}(\d{1,4})\s*m\b", t0)
    if m: return int(m.group(2))
    
    m = re.search(r"(duoi|<)\s*(\d{1,4})\s*m\b", t0)
    if m: return int(m.group(2))
    return None

def extract_max_mm(text: str) -> Optional[float]:
    """
    Lấy max lượng mưa theo mm.
    Hỗ trợ mm và L/m2 (1 L/m2 = 1 mm).
    """
    t, _ = canon(text)
    cand: list[float] = []

    # range mm
    for m in re.finditer(
        r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mm\b",
        t, flags=re.IGNORECASE | re.UNICODE
    ):
        cand.append(float(m.group(2).replace(",", ".")))

    # single mm
    for m in re.finditer(
        r"(\d+(?:[.,]\d+)?)\s*mm\b",
        t, flags=re.IGNORECASE | re.UNICODE
    ):
        cand.append(float(m.group(1).replace(",", ".")))

    # L/m2 variants (== mm)
    for m in re.finditer(
        r"(\d+(?:[.,]\d+)?)\s*(?:l|lit|lít)\s*/\s*m\s*(?:2|\^2)\b",
        t, flags=re.IGNORECASE | re.UNICODE
    ):
        cand.append(float(m.group(1).replace(",", ".")))

    return max(cand) if cand else None

def extract_surge_height_m(text: str) -> Optional[float]:
    t, t0 = canon(text)

    # Ưu tiên bắt ngay sau keyword (có thể là range)
    m = re.search(
        r"(?:nước\s*dâng|nuoc\s*dang|triều\s*cường|trieu\s*cuong)"
        r"[^0-9]{0,80}"
        r"(\d+(?:[.,]\d+)?)(?:\s*(?:-|den|toi)\s*(\d+(?:[.,]\d+)?))?\s*(m|mét|met|cm)\b",
        t,
        flags=re.IGNORECASE | re.UNICODE,
    )
    if m:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", ".")) if m.group(2) else a
        unit = m.group(3).lower()
        val = max(a, b)
        return val / 100.0 if unit == "cm" else val

    # Fallback: chỉ khi có đúng ngữ cảnh nước dâng/triều cường
    if ("nuoc dang" in t0) or ("trieu cuong" in t0):
        return extract_max_meters(text)

    return None

def extract_saline_intrusion_km(text: str) -> Optional[float]:
    t, t0 = canon(text)
    m = re.search(
        r"(?:xam\s*nhap\s*man|do\s*man|nhiem\s*man)[^0-9]{0,80}"
        r"(?:vao\s*sau|den|toi)?[^0-9]{0,40}"
        r"(\d+(?:[.,]\d+)?)(?:\s*(?:-|den|toi)\s*(\d+(?:[.,]\d+)?))?\s*km\b",
        t0
    )
    if m:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", ".")) if m.group(2) else a
        return max(a, b)

    if any(k in t0 for k in ["xam nhap man", "do man", "nhiem man"]):
        # Exclude km/h
        cand = [
            float(x.replace(",", "."))
            for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*km\b(?!\s*/\s*h)", t0)
        ]
        return max(cand) if cand else None
    return None

def extract_quake_mag(text: str) -> Optional[float]:
    t, t0 = canon(text)
    m = re.search(r"\b(?:m|mw|ml)\s*(\d+(?:[.,]\d+)?)\b", t0)
    if m: return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*do\s*(?:richter)?\b|do\s*lon[^0-9]{0,10}(\d+(?:[.,]\d+)?)\b", t0)
    if m:
        g = m.group(1) or m.group(2)
        return float(g.replace(",", ".")) if g else None
    return None

def extract_wave_height_m(text: str) -> Optional[float]:
    t, t0 = canon(text)
    if "song" not in t0 and "bien dong" not in t0: return None
    m = re.search(r"song[^0-9]{0,40}(\d+(?:[.,]\d+)?)(?:\s*-\s*(\d+(?:[.,]\d+)?))?\s*m\b", t0)
    if not m: return None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", ".")) if m.group(2) else a
    return max(a,b)

def extract_antecedent_days_bucket(t_accents: str) -> Optional[str]:
    # Article 46: "from 1 to 2 days" or "over 2 days"
    t0 = strip_accents(t_accents)
    if re.search(r"(tu\s*1\s*ngay\s*den\s*2\s*ngay|1\s*-\s*2\s*ngay)", t0):
        return "1-2"
    if re.search(r"(tren|hon)\s*2\s*ngay", t0):
        return ">2"
    return None

def extract_hazard_zone(t_accents: str) -> Optional[str]:
    t0 = strip_accents(t_accents)
    if re.search(r"nguy co rat cao", t0):
        return "rat_cao"
    if re.search(r"nguy co cao", t0):
        return "cao"
    if re.search(r"nguy co trung binh", t0):
        return "trung_binh"
    if re.search(r"nguy co thap", t0):
        return "thap"
    return None

def extract_max_temp(text: str) -> Optional[float]:
    t, t0 = canon(text)
    # Matches simple and ranges for Temp
    # Regex against t0 to handle stripped content, but unit needs care?
    # risk_lookup.check_heat_risk used t0 with "do c", "do", "c".
    TEMP_UNIT = r"(?:do\s*c|°\s*c|\bc\b)"
    vals = []
    # Ranges A-B
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(2).replace(",", ".")))
    # Single values
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(1).replace(",", ".")))
    
    if vals: return max(vals)
    return None

def extract_max_salinity(text: str) -> Optional[float]:
    t, t0 = canon(text)
    # Units: ‰, g/l, ppt
    UNIT = r"(?:g\s*/\s*l|g\s*l|phan\s*nghin|‰|psu|ppt)"
    vals = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + UNIT, t0, re.IGNORECASE):
         vals.append(float(m.group(1).replace(",", ".")))
    return max(vals) if vals else None

def extract_water_level(text: str) -> Optional[float]:
    """Extract generic water level (flood, surge, inundation depth)."""
    t, t0 = canon(text)
    # Contexts: muc nuoc, nuoc dang, ngap, do sau, dinh lu, bao dong
    CTX = r"(?:muc\s*nuoc|nuoc\s*dang|ngap|do\s*sau|dinh\s*lu|bao\s*dong)"
    # Pattern: CTX ... X (m|cm)
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

# --- REGION DEFINITIONS (Decision 18) ---
# Use stripped sets for matching against t0 (canonical)

NAM_BO = {
  "tp ho chi minh","ba ria vung tau","dong nai","binh duong","long an","tien giang","ben tre",
  "tra vinh","vinh long","dong thap","an giang","kien giang","can tho","hau giang","soc trang",
  "bac lieu","ca mau","tay ninh","binh phuoc", "nam bo", "mien tay", "dong nam bo"
}
TAY_BAC = {"lai chau","dien bien","son la","hoa binh","lao cai","yen bai", "tay bac"}
VIET_BAC = {"ha giang","cao bang","bac kan","tuyen quang","lang son","thai nguyen","phu tho","bac giang", "viet bac"}
NAM_TRUNG_BO = {"da nang", "quang nam", "quang ngai", "binh dinh", "phu yen", "khanh hoa", "ninh thuan", "binh thuan", "nam trung bo"}
TAY_NGUYEN = {"kon tum", "gia lai", "dak lak", "dak nong", "lam dong", "tay nguyen"}

# --- STORM RISK (Bão/ATNĐ - Article 42) ---

def is_storm_context(t: str, t0: str) -> bool:
    # Ưu tiên có dấu: phân biệt bão vs báo
    if ("bão" in t) or ("áp thấp nhiệt đới" in t):
        return True

    # Nếu nguồn không dấu: chỉ nhận "bao" khi có ngữ cảnh khí tượng
    # Tránh "bao cao" (báo cáo), "bao chi" (báo chí)
    if re.search(r"\bbao\s*(cao|chi)\b", t0):
        return False

    # Nhận bão không dấu khi có: cấp/gió/số hiệu/ATND
    return bool(
        re.search(r"\b(atnd|ap thap nhiet doi)\b", t0)
        or re.search(r"\bbao\s*(so\s*\d+|cap\s*\d{1,2}|giat|tren|manh)\b", t0)
    )

def check_storm_risk(text: str) -> int:
    t, t0 = canon(text)
    if not is_storm_context(t, t0): return 0

    wind = extract_beaufort_max(text)
    if wind is None:
        # ATND fallback: Table 2 says ATND (6-7) is Level 3
        if re.search(r"\b(atnd|ap thap nhiet doi)\b", t0): return 3 
        return 0

    is_sea = any(k in t0 for k in ["bien dong", "hoang sa", "truong sa", "vung bien"])
    # Zones
    is_s = any(k in t0 for k in NAM_BO) # Zone 4
    is_sc = any(k in t0 for k in NAM_TRUNG_BO) # Zone 3
    is_hl = any(k in t0 for k in TAY_NGUYEN) or any(k in t0 for k in TAY_BAC) or any(k in t0 for k in VIET_BAC) # Zone 5
    # Zone 2 (North/Central) is coverage fallback

    # Table 2 Logic
    # >= 16 (Super Typhoon)
    if wind >= 16:
        if is_sea: return 4
        return 5 # Land (All zones)

    # 14-15 (Very Strong)
    if wind >= 14:
        if is_sea: return 4
        if is_s or is_sc or is_hl: return 5
        return 4 # North/Central

    # 12-13 (Very Strong)
    if wind >= 12:
        if is_sea: return 3
        if is_s: return 5
        # South Central, Highlands, North -> 4
        return 4

    # 10-11 (Strong)
    if wind >= 10:
        if is_sea: return 3
        if is_s: return 4
        return 3 # Others

    # 6-9 (ATND, Storm)
    if wind >= 6:
        return 3

    return 0

# --- WATER SURGE (Nước dâng) - Article 43 ---
# Use Meter Parser

LOC_QN_TH = ["quang ninh", "hai phong", "thai binh", "nam dinh", "ninh binh", "thanh hoa"]
LOC_NA_HT = ["nghe an", "ha tinh"]
LOC_QB_TTH = ["quang binh", "quang tri", "thua thien hue"]
LOC_DN_BD = ["da nang", "quang nam", "quang ngai", "binh dinh"]
LOC_PY_NT = ["phu yen", "khanh hoa", "ninh thuan"]
LOC_BT_VT = ["binh thuan", "ba ria", "vung tau"]
LOC_HCM_CM = ["tp ho chi minh", "tien giang", "ben tre", "tra vinh", "soc trang", "bac lieu", "ca mau", "hcm", "sai gon"]
LOC_CM_KG = ["ca mau", "kien giang"]

def check_surge_risk(text: str) -> int:
    t, t0 = canon(text)
    if "nuoc dang" not in t0 and "trieu cuong" not in t0: return 0

    h = extract_surge_height_m(text)
    if h is None: return 0

    def in_loc(lst): return any(p in t0 for p in lst)

    # Group 1: QN-TH
    if in_loc(LOC_QN_TH):
        if h > 6: return 5
        if h > 5: return 4
        if h > 4: return 3
        if h > 3: return 2
        return 0

    # Group 2: NA-HT
    if in_loc(LOC_NA_HT):
        if h > 6: return 5
        if h > 4: return 4
        if h > 3: return 3
        if h > 2: return 2
        return 0

    # Group 3: QB-TTH
    if in_loc(LOC_QB_TTH):
        if h > 5: return 5
        if h > 3: return 4
        if h > 2: return 3
        if h > 1: return 2
        return 0

    # Group 4/8: DN-BD & CM-KG
    if in_loc(LOC_DN_BD) or in_loc(LOC_CM_KG):
        if h > 3: return 4
        if h > 2: return 3
        if h > 1: return 2
        return 0

    # Group 5: PY-NT
    if in_loc(LOC_PY_NT):
        if h > 3: return 3
        if h > 2: return 2
        return 0

    # Group 6/7: BT-VT & HCM-CM
    if in_loc(LOC_BT_VT) or in_loc(LOC_HCM_CM):
        if h > 4: return 4
        if h > 3: return 3
        if h > 2: return 2
        return 0

    # Default fallback
    if h >= 1.0: return 2
    
    return 0

    return 0

# --- HEAVY RAIN - Article 44 ---
# Using extract_max_mm_24h

TERRAIN_MT = ["trung du", "mien nui", "vung nui", "tay nguyen", "tay bac", "viet bac"]

def check_rain_risk(text: str) -> int:
    t, t0 = canon(text)

    # Use accum or max_mm
    accum = extract_rain_accum(text)
    mm = accum.get("mm_24") or accum.get("mm_48") or accum.get("mm_72") or extract_max_mm(text)
    if mm is None: return 0

    rain_context = any(k in t0 for k in ["mua lon", "mua to", "mua rat to", "mua dien rong"])
    if (mm < 100) and (not rain_context): return 0

    # Determine duration bucket
    days = "1-2" # Default
    d_extracted = extract_duration_days_bucket(text)
    if d_extracted:
        days = d_extracted
    else:
        # Infer from accum key if bucket missing
        if accum.get("mm_72") and mm == accum["mm_72"]: days = "2-4"
    
    is_mt = any(k in t0 for k in TERRAIN_MT)
    
    # Area Heuristic (downgrade logic reserved if needed, but table is strict)
    is_wide = any(k in t0 for k in ["dien rong", "nhieu noi", "nhieu huyen", "lan rong"])

    # Matrix Table (Decision 18)
    
    # > 400mm
    if mm > 400:
        if is_mt:
            # Mtn: 1-2(3), >2(4)
            if days == "1-2": return 3
            return 4
        else:
            # Plain: 1-4(3), >4(4)
            if days == ">4": return 4
            return 3

    # 200 - 400mm
    if mm > 200:
        if is_mt:
            # Mtn: 1-2(2), 2-4(3), >4(4)
            if days == ">4": return 4
            if days == "2-4": return 3
            return 2
        else:
            # Plain: 1-2(2), >2(3)
            if days == "1-2": return 2
            return 3

    # 100 - 200mm
    if mm >= 100:
        if is_mt:
            # Mtn: 1-2(1), 2-4(2), >4(3)
            if days == ">4": return 3
            if days == "2-4": return 2
            return 1
        else:
            # Plain: 1-2(1), >2(2)
            if days == "1-2": return 1
            return 2

    return 0



# --- FLOOD - Article 45 ---

def check_flood_risk(text: str) -> int:
    t, t0 = canon(text)
    if not any(k in t0 for k in ["lu lut","ngap lut","lu len","muc nuoc","bao dong"]):
        return 0
    
    # 1. Identify Region (1-4)
    rid = 1 # Default Region 1
    matched_rids = []
    
    def _match_item(item):
        tram = item.get("ten_tram")
        song = item.get("ten_song")
        tinh = item.get("tinh")
        if tram:
            # Station match
            if canon(tram)[1] in t0: return True
        if song and tinh:
            # River and Province match
            if canon(song)[1] in t0 and canon(tinh)[1] in t0: return True
        return False
        
    for k, v in FLOOD_ZONES_DATA.items():
        k_id = int(k.replace("khu_vuc_", ""))
        for item in v:
            if _match_item(item):
                matched_rids.append(k_id)
                
    if matched_rids:
        # Conflict resolution: Take MAX region ID (Usually Stricter/Urban)
        rid = max(matched_rids)

    # 2. Identify Flood Level
    # Levels mapped to Table Rows
    # Lvl 7: > Hist
    # Lvl 6: BD3+1 to Hist
    # Lvl 5: BD3+0.3 to BD3+1
    # Lvl 4: BD3 to BD3+0.3
    # Lvl 3: BD2 to BD3
    # Lvl 2: BD1 to BD2
    # Lvl 1: < BD1 (or just detected without level?)
    
    lvl = 1 # Default if keyword detected but no level found? Or 0?
    
    is_above = any(k in t0 for k in ["tren", "vuot", "cao hon"])
    is_below = any(k in t0 for k in ["duoi", "thap hon"])
    
    # Check Historic
    if "lich su" in t0:
        if is_above: lvl = 7
        else: lvl = 6 # Treat 'At Historic' as high range of Row 2 => Risk 3/4
        
    # Check BD3
    elif re.search(r"\b(bd|bao dong)\s*(3|iii)\b", t0):
        if is_below:
            lvl = 3 # Below BD3 -> Range BD2-BD3
        else:
             # Above or equal BD3
             offset = 0.0
             m = re.search(r"\b(bd|bao dong)\s*(3|iii).*?(\d+[.,]\d+)", t0)
             if m:
                 try: offset = float(m.group(3).replace(",","."))
                 except: pass
             
             if offset >= 1.0: lvl = 6 # Row 2
             elif offset >= 0.3: lvl = 5 # Row 3
             else: lvl = 4 # Row 4
             
    # Check BD2
    elif re.search(r"\b(bd|bao dong)\s*(2|ii)\b", t0):
        if is_below: lvl = 2 # Below BD2 -> Range BD1-BD2
        else: lvl = 3 # Above BD2 -> Range BD2-BD3
        
    # Check BD1
    elif re.search(r"\b(bd|bao dong)\s*(1|i)\b", t0):
        if is_below: lvl = 0
        else: lvl = 2 # Above BD1 -> Range BD1-BD2

    # 3. Apply Matrix
    # Row 1 (> Hist)
    if lvl == 7: return 5 if rid == 4 else 3
    
    # Row 2 (BD3+1 to Hist)
    if lvl == 6: return 4 if rid == 4 else 3
    
    # Row 3 (BD3+0.3 to BD3+1)
    if lvl == 5:
        if rid == 4: return 4
        if rid == 3: return 3
        return 2 # R1, R2
        
    # Row 4 (BD3 to BD3+0.3)
    if lvl == 4:
        if rid in [3, 4]: return 3
        return 2 # R1, R2
        
    # Row 5 (BD2 to BD3)
    if lvl == 3:
        if rid == 4: return 3
        if rid in [2, 3]: return 2
        return 1 # R1
        
    # Row 6 (BD1 to BD2)
    if lvl == 2:
        return 2 if rid == 4 else 1
        
    return 0

# --- FLASH FLOOD / LANDSLIDE - Article 46 ---

ZONE_PROVINCES_R1 = {"lai chau", "son la", "dien bien", "hoa binh", "lao cai", "yen bai", "ha giang"}
ZONE_PROVINCES_R2 = {"tuyen quang", "bac kan", "lang son", "cao bang", "thanh hoa", "nghe an", "quang ngai"}
ZONE_PROVINCES_R3 = {"phu tho", "thai nguyen", "quang ninh", "ha tinh", "quang binh", "quang tri", "thua thien hue", "tp da nang", "da nang", "quang nam", "khanh hoa", "kon tum", "gia lai", "dak lak", "dak nong", "lam dong"}
ZONE_PROVINCES_R4 = {"vinh phuc", "bac giang", "hai phong", "binh dinh", "phu yen", "khanh hoa", "ninh thuan", "binh thuan"}

def assert_disjoint(*zones: Set[str]) -> None:
    seen = {}
    for i, z in enumerate(zones, start=1):
        for p in z:
            if p in seen:
                # Log or print warning (raising error stops app)
                print(f"WARNING: Province '{p}' appears in zones {seen[p]} and {i}")
            seen[p] = i

# assert_disjoint(ZONE_PROVINCES_R1, ZONE_PROVINCES_R2, ZONE_PROVINCES_R3, ZONE_PROVINCES_R4)

def detect_flashflood_region(t0: str) -> Optional[int]:
    def hit(s): return any(p in t0 for p in s)
    if hit(ZONE_PROVINCES_R1): return 1
    if hit(ZONE_PROVINCES_R2): return 2
    if hit(ZONE_PROVINCES_R3): return 3
    if hit(ZONE_PROVINCES_R4): return 4
    return None

def check_flash_flood_risk(text: str) -> int:
    t, t0 = canon(text)

    if not any(k in t0 for k in ["lu quet","sat lo","sat lo dat","truot lo","truot dat","da lan","suc truot"]):
        return 0

    mm = extract_max_mm_24h(t)
    days_bucket = extract_antecedent_days_bucket(t)   # "1-2" | ">2"
    hz = extract_hazard_zone(t)                       # thap/trung_binh/cao/rat_cao
    region = detect_flashflood_region(t0)             # 1..4

    if mm is None or days_bucket is None or hz is None or region is None:
        return 0

    def in_set(x, s): return x in s
    level = 0

    # --- LEVEL 3 ---
    if 100 <= mm <= 200 and days_bucket == "1-2" and region in (1,2) and hz == "rat_cao":
        level = max(level, 3)
    if 200 < mm <= 400 and days_bucket == ">2":
        if region in (1,2) and in_set(hz, {"cao","rat_cao"}): level = max(level, 3)
        if region == 3 and hz == "rat_cao": level = max(level, 3)
    if mm > 400 and days_bucket == ">2":
        if region in (1,2) and in_set(hz, {"cao","rat_cao"}): level = max(level, 3)
        if region == 3 and hz == "rat_cao": level = max(level, 3)

    # --- LEVEL 2 ---
    if 100 <= mm <= 200 and days_bucket == "1-2":
        if region in (1,2) and hz == "cao": level = max(level, 2)
        if region == 3 and hz == "rat_cao": level = max(level, 2)
    if 200 < mm <= 400 and days_bucket == ">2":
        if region in (1,2) and hz == "trung_binh": level = max(level, 2)
        if region == 3 and hz == "cao": level = max(level, 2)
        if region == 4 and hz == "rat_cao": level = max(level, 2)
    if mm > 400 and days_bucket == ">2":
        if region in (1,2) and in_set(hz, {"thap","trung_binh"}): level = max(level, 2)
        if region == 3 and in_set(hz, {"trung_binh","cao"}): level = max(level, 2)
        if region == 4 and in_set(hz, {"cao","rat_cao"}): level = max(level, 2)

    # --- LEVEL 1 ---
    if 100 <= mm <= 200 and days_bucket == "1-2":
        if region in (1,2) and hz == "thap": level = max(level, 1)
        if region == 3 and in_set(hz, {"thap","trung_binh"}): level = max(level, 1)
        if region == 4 and hz == "trung_binh": level = max(level, 1)
    if 200 < mm <= 400 and days_bucket == ">2":
        if region in (1,2) and hz == "thap": level = max(level, 1)
        if region == 3 and in_set(hz, {"thap","trung_binh"}): level = max(level, 1)
    if mm > 400 and days_bucket == ">2":
        if region in (1,2) and hz == "thap": level = max(level, 1)

    return level

# --- HEAT - Article 47 ---

def check_heat_risk(text: str) -> int:
    t, t0 = canon(text)
    if "nang nong" not in t0: return 0

    dur = extract_duration_days_count(text)
    if dur < 3: return 0

    # Temp Extraction
    TEMP_UNIT = r"(?:do|°\s*c|do\s*c|\bc\b)"
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0)
    ranges = re.findall(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0)
    vals = [float(x.replace(",",".")) for x in matches]
    for a,b in ranges: vals.append(float(b.replace(",",".")))
    
    temp = max(vals) if vals else 0
    if temp == 0:
        if "tren 41" in t0: temp = 42
        elif "39 den 41" in t0: temp = 40
        elif "37 den 39" in t0: temp = 38
        elif "35 den 37" in t0: temp = 36
        elif "dac biet gay gat" in t0: temp = 40
        elif "gay gat" in t0: temp = 39

    if temp < 35: return 0

    # Region
    is_s = any(p in t0 for p in NAM_BO) or any(p in t0 for p in TAY_NGUYEN)
    CTR_PROV = {"thanh hoa","nghe an","ha tinh","quang binh","quang tri","thua thien hue"}
    is_c = any(p in t0 for p in NAM_TRUNG_BO) or any(p in t0 for p in CTR_PROV) or "trung bo" in t0
    is_n = not is_s and not is_c

    # Matrix Logic
     # > 25 Days
    if dur > 25:
        if temp > 41: return 4
        if temp > 39: # 39-41
            if is_s: return 4
            return 3
        if temp > 37: # 37-39
            if is_s: return 3
            return 2
        return 1

    # > 10 - 25 Days
    if dur > 10:
        if temp > 41:
            if is_s: return 4
            return 3
        if temp > 39: # 39-41
            if is_s: return 3
            return 2
        if temp > 37: # 37-39
            if is_s: return 2
            return 1
        return 1

    # > 5 - 10 Days
    if dur > 5:
        if temp > 41:
            if is_s: return 3
            return 2
        if temp > 39: # 39-41
            return 2
        return 1

    # 3 - 5 Days
    if dur >= 3:
        if temp > 41:
            if is_c: return 1
            return 2 # N(2), S(2)
        if temp > 39: # 39-41
            if is_s: return 2
            return 1 # N(1), C(1)
        return 1
        
    return 0

# --- SALINE - Article 49 ---

def check_saline_risk(text: str) -> int:
    t, t0 = canon(text)
    if ("xam nhap man" not in t0) and ("do man" not in t0) and ("nhiem man" not in t0):
        return 0

    depth = extract_saline_intrusion_km(text)
    if depth is None: return 0
    
    # Check plural river mouths (Regulatory requirement Art 49)
    has_many = "nhieu cua song" in t0 or "cac cua song" in t0 or t0.count("song ") >= 2
    if "dong bang song cuu long" in t0 or "dbscl" in t0 or "nam bo" in t0: has_many = True
    
    if not has_many: return 0
        
    unit_pat = r"(?:g\s*/\s*l|g\s*l|phan\s*nghin|‰|psu|ppt)"
    # Default to 4‰ (Agricultural limit) unless 1‰ explicitly focused and < 4
    is_4 = True
    # If 1‰ mentioned and NO mention of >=4, switch to 1‰ table?
    # Simple logic: if text mentions 1‰, use 1‰. If 4‰, use 4‰.
    # If both, usually context is "ranh man 4g/l vao sau X km", "ranh man 1g/l vao sau Y km".
    # This single function processes whole text. It finds MAX depth.
    # If max depth is associated with 1‰, we should use 1‰ table.
    # But extract_saline_intrusion_km finds max depth regardless of grammar.
    # Conservative Approach: Use 4‰ table (stricter for deeper depth?)
    # Compare:
    # 4‰ table: >50km -> 3 or 4.
    # 1‰ table: >50km -> 2.
    # So 4‰ table is STRICTER (Higher Risk for same distance? No, 4‰ intrusion is harder).
    # Wait. If 4g/l goes 50km deep, that's worse than 1g/l going 50km deep.
    # So if we observe 50km, we must know if it is 1g/l or 4g/l.
    # If implicit, "xam nhap sau 50km", standard implies 4g/l usually.
    # I will stick to is_4 = True default.
    
    if re.search(r"\b1\s*" + unit_pat, t0) and not re.search(r"\b[4-9]\s*" + unit_pat, t0):
        is_4 = False
        
    # Regions
    is_s = any(p in t0 for p in NAM_BO) or "nam bo" in t0 or "dbscl" in t0
    BTB = {"thanh hoa","nghe an","ha tinh","quang binh","quang tri","thua thien hue"}
    is_n_nc = any(p in t0 for p in BTB) or "bac bo" in t0 or "bac trung bo" in t0
    # C (TTB + NTB)
    TTB_NTB = {"da nang","quang nam","quang ngai","binh dinh","phu yen","khanh hoa","ninh thuan","binh thuan"}
    is_c = any(p in t0 for p in TTB_NTB) or "trung bo" in t0 or any(p in t0 for p in NAM_TRUNG_BO)
    
    if not (is_s or is_n_nc or is_c): is_s = True 

    # 4‰ Table
    if is_4:
        if is_n_nc:
            # Col 4: >90(4), 50-90(4), 25-50(3), 15-25(2)
            if depth > 50: return 4
            if depth > 25: return 3
            if depth > 15: return 2
            return 0
        if is_c:
            # Col 5: >90(4), 50-90(3), 25-50(2), 15-25(1)
            if depth > 90: return 4
            if depth > 50: return 3
            if depth > 25: return 2
            if depth > 15: return 1
            return 0
        if is_s:
            # Col 6: >90(4), 50-90(3), 25-50(2)
            if depth > 90: return 4
            if depth > 50: return 3
            if depth > 25: return 2
            return 0
            
    # 1‰ Table
    if depth > 90: return 3
    if depth > 50: return 2
    if depth > 25: return 1
    return 0

# --- STRONG WIND SEA - Article 50 ---

LOC_SEA_VENBO = ["ven bien", "ven bo", "vung bien ven bo", "gan bo"]
LOC_SEA_OFFSHORE = ["bien dong", "hoang sa", "truong sa", "ngoai khoi", "xa bo", "dao"]

def check_strong_wind_risk(text: str) -> int:
    t, t0 = canon(text)
    if "gio manh" not in t0 and "gio cap" not in t0: return 0

    lv = extract_beaufort_max(text)
    if lv is None: return 0
    
    # Article 50: strictly Wind Level
    
    is_venbo = any(k in t0 for k in LOC_SEA_VENBO)
    is_offshore = any(k in t0 for k in LOC_SEA_OFFSHORE)
    
    if (not is_venbo) and (not is_offshore):
        return 0 
    
    # Coastal (Ven bo)
    if is_venbo:
        if lv >= 7: return 3
        if lv >= 6: return 2
        return 0

    # Offshore (Ngoai khoi / Bien Dong)
    if is_offshore:
        if lv >= 9: return 3
        if lv >= 7: return 2
        # Lv 6 is empty in table (Risk not classified or Low)
        return 0

    return 0
    
# --- OTHERS (Simple) ---

LOC_HIGHWAY_AIRPORT = ["cao toc", "san bay", "cang hang khong", "duong bang"]
LOC_SEA_RIVER_PASS = ["tren bien", "tren song", "deo", "nui", "cua song"]

def check_fog_risk(text: str) -> int:
    t, t0 = canon(text)
    if "suong mu" not in t0:
        return 0

    dense = "day dac" in t0
    vis = extract_visibility_m(text)
    
    is_critical = any(k in t0 for k in LOC_HIGHWAY_AIRPORT)
    is_sea_pass = any(k in t0 for k in LOC_SEA_RIVER_PASS)
    
    # Level 2 (Art 51)
    if vis is not None and vis < 50 and is_critical: return 2
    
    # Level 1
    if is_critical and dense: return 1
    if is_sea_pass and vis is not None and vis < 50: return 1
    
    return 0

def check_extreme_other_risk(text: str) -> int:
    t, t0 = canon(text)

    # Lốc: ưu tiên chữ có dấu, hoặc cụm "lốc xoáy/giông lốc"
    has_loc = ("lốc" in t) or bool(re.search(r"\bloc\s*(xoay|xoa y|kem|manh)\b", t0)) or ("giong loc" in t0)
    # Loại "lọc ..."
    if re.search(r"\bloc\s*(nuoc|khong\s*khi|dau|bui|rac)\b", t0):
        has_loc = False

    # Sét: ưu tiên "sét" hoặc cụm "sét đánh/giông sét"
    has_set = ("sét" in t) or ("giong set" in t0) or bool(re.search(r"\bset\s*danh\b", t0))
    # Loại "set up/setting"
    if re.search(r"\bset\s*(up|ups|ting|ting\s*up)\b", t0):
        has_set = False

    # Mưa đá
    has_hail = ("mưa đá" in t) or ("mua da" in t0)

    if not (has_loc or has_set or has_hail): return 0
    
    # Level 2 check: "Từ 1/2 số huyện, xã trở lên" -> Diện rộng/Nhiều nơi
    is_wide = any(k in t0 for k in ["dien rong", "nhieu noi", "nhieu huyen", "toan tinh", "hau het", "hang loat", "nhieu xa"])
    if is_wide: return 2
    
    # Level 1: Dưới 1/2 số huyện (Cục bộ/Rải rác)
    return 1

def check_cold_risk(text: str) -> int:
    t, t0 = canon(text)
    if "ret hai" not in t0 and "suong muoi" not in t0 and "bang gia" not in t0: return 0

    dur = extract_duration_days_count(text)
    
    # Temp Parsing
    TEMP_UNIT = r"(?:do|°\s*c|do\s*c|\bc\b)"
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0)
    ranges = re.findall(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + TEMP_UNIT, t0)
    vals = [float(x.replace(",",".")) for x in matches]
    for a,b in ranges: vals.append(float(a.replace(",","."))) # Use min of range
    
    valid_temps = [v for v in vals if v < 20]
    temp = 13 # Default barrier for Ret Hai
    if valid_temps:
        temp = min(valid_temps)
    else:
        if "duoi 0" in t0: temp = -1
        elif "bang gia" in t0 or "suong muoi" in t0: temp = -1
    
    # Region
    is_mtn = "vung nui" in t0 or "trung du" in t0 or any(p in t0 for p in ["lao cai","yen bai","ha giang","lang son","cao bang","son la","lai chau","dien bien"])
    
    # Logic Table
    # > 10 Days
    if dur > 10:
        if temp < 0: return 3
        if temp <= 4: return 3
        if temp <= 8:
            return 1 if is_mtn else 3
        if temp <= 13:
            return 1 if is_mtn else 2

    # > 5-10 Days
    elif dur > 5:
        if temp < 0:
            return 3 if is_mtn else 2
        if temp <= 4: return 2
        if temp <= 8:
            return 1 if is_mtn else 2
        if temp <= 13:
            return 0 if is_mtn else 1

    # 3-5 Days
    elif dur >= 3:
        if temp < 0:
            return 2 if is_mtn else 1
        if temp <= 4: return 1
        if temp <= 8:
            return 0 if is_mtn else 1
    
    # If < 3 days but severe cold often implies warning.
    # Default Level 1 if Ret Hai confirmed
    return 1
    
def check_wildfire_risk(text: str) -> int:
    t, t0 = canon(text)
    if "chay rung" not in t0: return 0
    
    # Extract Level
    lvl = 0
    if "cap v" in t0 or "cap 5" in t0 or "cuc ky nguy hiem" in t0: lvl = 5
    elif "cap iv" in t0 or "cap 4" in t0 or "nguy hiem" in t0: lvl = 4
    elif "cap iii" in t0 or "cap 3" in t0 or "cap cao" in t0: lvl = 3
    elif "cap ii" in t0 or "cap 2" in t0: lvl = 2
    elif "cap i" in t0 or "cap 1" in t0: lvl = 1
    
    if lvl == 0: return 0
    
    dur = extract_duration_days_count(text)
    # Default duration if not found? 
    # If "keo dai" matches but no number? 
    # If strict compliance, needing duration. 
    # If no duration, assuming worst case is dangerous (Level 5).
    # Assuming best case is safe (Level 0/1).
    # Common warnings: "Du bao chay rung cap V tai cac tinh...". (Implicitly immediate).
    # Table starts at 3-5 days.
    # I will default to duration 3 days if unspecified? Or 0?
    # Let's use 0 -> Risk 1.
    
    # Cap V (Vung 4)
    if lvl == 5:
        if dur > 20: return 5
        if dur > 15: return 4
        if dur > 10: return 3
        if dur > 5: return 2
        return 1
        
    # Cap IV (Vung 3)
    if lvl == 4:
        if dur > 20: return 4 # Wait. Vung 3 >20 is 4.
        if dur > 15: return 3
        if dur > 10: return 3
        if dur > 5: return 2
        return 1

    # Cap III (Vung 2)
    if lvl == 3:
        if dur > 20: return 3
        if dur > 15: return 2
        return 1
    
    return 1 # Vung 1 is always 1

def check_quake_risk(text: str) -> int:
    t, t0 = canon(text)
    if "bien dong dat" in t0 or "hoat dong dat" in t0: return 0 
    if not re.search(r"\bdong\s*dat\b", t0): return 0

    # Extract Intensity (MSK-64)
    msk = 0
    # Roman Numerals
    romans = {"xii":12, "xi":11, "x":10, "ix":9, "viii":8, "vii":7, "vi":6, "v":5}
    for r, v in romans.items():
        if re.search(rf"\bcap\s*{r}\b", t0):
            msk = max(msk, v)
    
    # Arabic Numerals (5-12)
    matches = re.findall(r"\bcap\s*(\d+)", t0)
    for m in matches:
        v = int(m)
        if 5 <= v <= 12: msk = max(msk, v)
            
    # Area Type
    is_res = any(k in t0 for k in ["thuy dien", "ho chua", "dap", "thuy loi"])
    is_urban = any(k in t0 for k in ["thanh pho", "thi xa", "do thi", "thi tran", "nha cao tang"])
    
    # Logic Table (Article 55)
    if msk > 8: return 5 # > VIII
    
    if msk >= 7: # VII - VIII (7, 8)
        if is_res or is_urban: return 4
        return 3
        
    if msk >= 6: # VI - VII (6)
        if is_res: return 3
        return 2 # Urban and Rural are 2
        
    if msk >= 5: # V - VI (5)
        return 1

    # Fallback if no Intensity detected but Magnitude is present
    # Heuristic mapping for usability
    mag = extract_quake_mag(text)
    if mag:
        if mag >= 6.0: return 5
        if mag >= 5.0: return 3
        if mag >= 3.5: return 1
        
    return 0

def check_tsunami_risk(text: str) -> int:
    t, t0 = canon(text)
    # Avoid "song than" in words like "song than thien"
    if not re.search(r"\bsong\s*than\b", t0): return 0
    if "cuoc song than" in t0: return 0

    h = extract_max_meters(t)
    if h is not None:
        if h > 16: return 5
        if h > 8: return 4
        if h > 4: return 3
        if h >= 2: return 2
        return 1
    
    # Check explicit intensity (Roman or Arabic)
    if re.search(r"cap\s*(12|xii)", t0): return 5
    if re.search(r"cap\s*(11|xi\b)", t0): return 4
    if re.search(r"cap\s*(9|10|ix|x\b)", t0): return 3
    if re.search(r"cap\s*(7|8|vii|viii)", t0): return 2
    if re.search(r"cap\s*(6|vi\b)", t0): return 1

    return 1
    
# --- DROUGHT - Article 48 --- (Added back)
def check_drought_risk(text: str) -> int:
    t, t0 = canon(text)
    if "han han" not in t0 and "kho han" not in t0: return 0

    # Extract months
    # "thieu hut ... 3 thang", "keo dai 3 thang"
    months = 0
    m_match = re.search(r"\b(\d+)\s*thang\b", t0)
    if m_match: months = int(m_match.group(1))

    # Extract water %
    # "thieu hut 30 %", "thieu hut 30%"
    pct = 0
    p_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*%", t0)
    if p_match: pct = float(p_match.group(1).replace(",", "."))
    
    # Definition of Central Region for Drought (Art 48 generally implies Trung Bo)
    is_s = any(p in t0 for p in NAM_BO) or any(p in t0 for p in TAY_NGUYEN)
    CTR_PROV = {"thanh hoa","nghe an","ha tinh","quang binh","quang tri","thua thien hue"}
    is_c = any(p in t0 for p in NAM_TRUNG_BO) or any(p in t0 for p in CTR_PROV) or "trung bo" in t0
    is_n = not is_s and not is_c

    # Logic
    # Group > 70%
    if pct > 70:
        # Col 7,8,9: >5(4), 3-5(4), 2-3(3) for ALL regions
        if months > 3: return 4
        if months >= 2: return 3
        # Fallback if months unknown but pct > 70? Likely 3 or 4.
        return 3
        
    # Group > 50 - 70%
    elif pct > 50:
        if is_n:
            # Col 4: >5(3), 3-5(2), 2-3(1)
            if months > 5: return 3
            if months > 3: return 2
            if months >= 2: return 1
        elif is_c:
            # Col 5: >5(3), 3-5(3), 2-3(2)
            if months > 5: return 3
            if months > 3: return 3
            if months >= 2: return 2
        elif is_s:
            # Col 6: >5(4), 3-5(3), 2-3(2)
            if months > 5: return 4
            if months > 3: return 3
            if months >= 2: return 2
        return 2

    # Group 20 - 50%
    elif pct >= 20: 
        if is_n:
            # Col 1: >5(2), 3-5(1), 2-3(0)
            if months > 5: return 2
            if months > 3: return 1
        elif is_c:
            # Col 2: >5(2), 3-5(1), 2-3(1)
            if months > 5: return 2
            if months > 3: return 1
            if months >= 2: return 1
        elif is_s:
            # Col 3: >5(3), 3-5(2), 2-3(1)
            if months > 5: return 3
            if months > 3: return 2
            if months >= 2: return 1
        return 1

    # Heuristics if no numeric data
    if "dac biet gay gat" in t0 or "khoc liet" in t0: return 4
    if "gay gat" in t0: return 3
    
    return 1

CHECKS = [
    ("storm", check_storm_risk),
    ("surge", check_surge_risk),
    ("rain", check_rain_risk),
    ("flood", check_flood_risk),
    ("flash_flood", check_flash_flood_risk),
    ("heat", check_heat_risk),
    ("saline", check_saline_risk),
    ("strong_wind_sea", check_strong_wind_risk),
    ("fog", check_fog_risk),
    ("extreme_other", check_extreme_other_risk),
    ("cold", check_cold_risk),
    ("wildfire", check_wildfire_risk),
    ("quake", check_quake_risk),
    ("tsunami", check_tsunami_risk),
    ("drought", check_drought_risk),
]

def assess(text: str, prefer_declared: bool = True, explain: bool = False) -> dict:
    hazards = []
    debug = []

    declared = extract_declared_risk_level(text)
    overall = declared or 0

    if declared:
        hazards.append({"hazard": "declared", "level": declared})
        if explain:
            debug.append({"rule": "declared_risk", "level": declared})

    for name, fn in CHECKS:
        try:
            lv = fn(text)
        except Exception as e:
            lv = 0
            if explain:
                debug.append({"hazard": name, "error": str(e)})

        if lv > 0:
            hazards.append({"hazard": name, "level": lv})
            if explain:
                debug.append({"hazard": name, "level": lv})

            if not (prefer_declared and declared):
                overall = max(overall, lv)

    hazards.sort(key=lambda x: x["level"], reverse=True)
    out = {"overall_level": overall, "hazards": hazards}
    if explain:
        out["debug"] = debug
    return out
