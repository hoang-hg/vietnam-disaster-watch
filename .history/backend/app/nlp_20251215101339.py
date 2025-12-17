import re
import unicodedata
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS

# Impact keywords for better extraction
IMPACT_KEYWORDS = {
    "deaths": [
        "chết", "tử vong", "tử nạn", "thiệt mạng", "thương vong", 
        "thi thể", "chết đuối", "đuối nước", "ngạt nước", "vùi lấp", "chôn vùi", "mắc kẹt"
    ],
    "missing": [
        "mất tích", "chưa tìm thấy", "mất liên lạc", "không liên lạc được",
        "chưa xác định tung tích", "không rõ tung tích", "bị cuốn trôi",
        "đang tìm kiếm", "cứu nạn", "cứu hộ"
    ],
    "injured": [
        "bị thương", "bị thương nặng", "bị thương nhẹ", "chấn thương",
        "đa chấn thương", "nhập viện", "cấp cứu", "điều trị",
        "chuyển viện", "sơ cứu"
    ],
    "damage": [
        "thiệt hại", "tổn thất", "hư hỏng", "hư hại", "tàn phá",
        "ước tính thiệt hại", "thiệt hại về tài sản", "sập nhà", "đổ sập",
        "tốc mái", "ngập nhà", "cuốn trôi", "sạt lở đường", "đứt đường",
        "chia cắt", "cô lập", "sập cầu", "mất điện", "mất nước", "mất sóng"
    ]
}

# Boilerplate tokens to strip from titles/summaries before matching
BOILERPLATE_TOKENS = [
    r"\bvideo\b", r"\bảnh\b", r"\bclip\b", r"\bphóng\s*sự\b", r"\btrực\s*tiếp\b",
    r"\blive\b", r"\bhtv\b", r"\bphoto\b", r"\bupdate\b"
]

# Map common Vietnamese number words to integers (approximate where needed)
NUMBER_WORDS = {
    "không": 0,
    "một": 1, "mốt": 1, "1": 1,
    "hai": 2, "2": 2,
    "ba": 3, "3": 3,
    "bốn": 4, "tư": 4, "4": 4,
    "năm": 5, "5": 5,
    "sáu": 6, "6": 6,
    "bảy": 7, "7": 7,
    "tám": 8, "8": 8,
    "chín": 9, "9": 9,
    "mười": 10, "10": 10,
    "vài": 3,
    "hàng chục": 20,
    "một trăm": 100,
    
}

# 1) Phân loại thiên tai theo từ khóa (rule-based)
DISASTER_RULES = [
    # 1) Earthquake
    ("earthquake", [
        r"(?<!\w)động\s*đất(?!\w)",
        r"(?<!\w)rung\s*chấn(?!\w)",
        r"(?<!\w)dư\s*chấn(?!\w)",
        r"(?<!\w)tâm\s*chấn(?!\w)",
        r"(?<!\w)chấn\s*tiêu(?!\w)",
        r"(?<!\w)đứt\s*gãy(?!\w)",
        r"(?<!\w)nứt\s*đất(?!\w)",
        r"(?<!\w)nứt\s*nhà(?!\w)",
        r"(?<!\w)nghiêng\s*lắc(?!\w)",
        # Magnitude patterns
        r"(?<!\w)(?:độ\s*lớn|cường\s*độ)\s*\d+(?:[.,]\d+)?(?!\w)",
        r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:độ\s*richter|richter)(?!\w)",
        r"(?<!\w)(?:magnitude|mag)\s*\d+(?:[.,]\d+)?(?!\w)",
        r"(?<!\w)\bM\s*\d+(?:[.,]\d+)?\b(?!\w)",
    ]),

    # 2) Tsunami
    ("tsunami", [
        r"(?<!\w)sóng\s*thần(?!\w)",
        r"(?<!\w)cảnh\s*báo\s*sóng\s*thần(?!\w)",
        r"(?<!\w)báo\s*động\s*sóng\s*thần(?!\w)",
        r"(?<!\w)tsunami(?!\w)",
        # Often used description
        r"(?<!\w)biển\s*rút(?!\w)",
        r"(?<!\w)nước\s*biển\s*rút(?!\w)",
    ]),

    # 3) Landslide / Subsidence / Sinkhole
    ("landslide", [
        r"(?<!\w)sạt\s*lở(?!\w)",
        r"(?<!\w)sạt\s*lở\s*đất(?!\w)",
        r"(?<!\w)lở\s*đất(?!\w)",
        r"(?<!\w)trượt\s*đất(?!\w)",
        r"(?<!\w)trượt\s*lở(?!\w)",
        r"(?<!\w)lở\s*núi(?!\w)",
        r"(?<!\w)lở\s*đá(?!\w)",
        r"(?<!\w)đá\s*lăn(?!\w)",
        r"(?<!\w)đất\s*đá\s*(?:tràn|đổ)\s*xuống(?!\w)",
        # Taluy variants
        r"(?<!\w)ta\s*luy(?!\w)",
        r"(?<!\w)taluy(?!\w)",
        r"(?<!\w)sạt\s*(?:ta\s*luy|taluy)(?!\w)",
        r"(?<!\w)sập\s*(?:ta\s*luy|taluy)(?!\w)",
        # Erosion / bank collapse
        r"(?<!\w)sạt\s*lở\s*bờ\s*sông(?!\w)",
        r"(?<!\w)sạt\s*lở\s*bờ\s*biển(?!\w)",
        r"(?<!\w)xói\s*lở\s*bờ\s*sông(?!\w)",
        r"(?<!\w)xói\s*lở\s*bờ\s*biển(?!\w)",
        # Subsidence / sinkhole
        r"(?<!\w)sụt\s*lún(?!\w)",
        r"(?<!\w)lún\s*sụt(?!\w)",
        r"(?<!\w)sụp\s*lún(?!\w)",
        r"(?<!\w)hố\s*tử\s*thần(?!\w)",
        r"(?<!\w)hố\s*sụt(?!\w)",
        r"(?<!\w)sụp\s*đường(?!\w)",
    ]),

    # 4) Flood / Inundation / Flash flood / Tide
    ("flood", [
        r"(?<!\w)mưa\s*lũ(?!\w)",
        r"(?<!\w)lũ(?!\w)",
        r"(?<!\w)lụt(?!\w)",
        r"(?<!\w)ngập(?!\w)",
        r"(?<!\w)ngập\s*lụt(?!\w)",
        r"(?<!\w)ngập\s*úng(?!\w)",
        r"(?<!\w)ngập\s*sâu(?!\w)",
        r"(?<!\w)ngập\s*cục\s*bộ(?!\w)",
        # Flash flood
        r"(?<!\w)lũ\s*quét(?!\w)",
        r"(?<!\w)lũ\s*ống(?!\w)",
        # River level & warning thresholds
        r"(?<!\w)đỉnh\s*lũ(?!\w)",
        r"(?<!\w)nước\s*lũ(?!\w)",
        r"(?<!\w)nước\s*sông\s*dâng(?!\w)",
        r"(?<!\w)mực\s*nước\s*(?:lên|dâng|tăng)(?!\w)",
        r"(?<!\w)vượt\s*báo\s*động\s*(?:1|2|3|I|II|III)(?!\w)",
        r"(?<!\w)báo\s*động\s*(?:1|2|3|I|II|III)(?!\w)",
        # Tide / surge
        r"(?<!\w)triều\s*cường(?!\w)",
        r"(?<!\w)nước\s*dâng(?!\w)",
        r"(?<!\w)nước\s*dâng\s*do\s*bão(?!\w)",
        # Dyke/dam incidents & discharge
        r"(?<!\w)vỡ\s*đê(?!\w)",
        r"(?<!\w)vỡ\s*kè(?!\w)",
        r"(?<!\w)vỡ\s*bờ\s*bao(?!\w)",
        r"(?<!\w)tràn\s*bờ(?!\w)",
        r"(?<!\w)vỡ\s*đập(?!\w)",
        r"(?<!\w)sự\s*cố\s*(?:đập|hồ\s*chứa)(?!\w)",
        r"(?<!\w)xả\s*lũ(?!\w)",
        r"(?<!\w)xả\s*tràn(?!\w)",
        r"(?<!\w)xả\s*đáy(?!\w)",
        r"(?<!\w)mở\s*cửa\s*xả(?!\w)",
    ]),

    # 5) Storm / Tropical cyclone / Low pressure
    ("storm", [
        r"(?<!\w)bão(?!\w)",
        r"(?<!\w)bão\s*số\s*\d+(?!\w)",
        r"(?<!\w)siêu\s*bão(?!\w)",
        r"(?<!\w)bão\s*mạnh(?!\w)",
        r"(?<!\w)bão\s*rất\s*mạnh(?!\w)",
        r"(?<!\w)bão\s*cực\s*mạnh(?!\w)",
        r"(?<!\w)hoàn\s*lưu\s*bão(?!\w)",
        r"(?<!\w)tâm\s*bão(?!\w)",
        r"(?<!\w)đổ\s*bộ(?!\w)",  # useful but should be combined with context rules
        # Tropical depression
        r"(?<!\w)áp\s*thấp(?!\w)",
        r"(?<!\w)áp\s*thấp\s*nhiệt\s*đới(?!\w)",
        r"(?<!\w)ATNĐ(?!\w)",
        r"(?<!\w)vùng\s*áp\s*thấp(?!\w)",
        # Sometimes English appears
        r"(?<!\w)typhoon(?!\w)",
        r"(?<!\w)tropical\s*(?:storm|depression)(?!\w)",
        r"(?<!\w)cyclone(?!\w)",
    ]),

    # 6) Wind / Thunderstorm / Tornado / Hail / Lightning
    ("wind_hail", [
        r"(?<!\w)gió\s*mạnh(?!\w)",
        r"(?<!\w)gió\s*giật(?!\w)",
        r"(?<!\w)gió\s*giật\s*cấp\s*\d+(?!\w)",
        r"(?<!\w)dông(?!\w)",
        r"(?<!\w)mưa\s*giông(?!\w)",
        r"(?<!\w)dông\s*lốc(?!\w)",
        r"(?<!\w)giông\s*lốc(?!\w)",
        r"(?<!\w)lốc(?!\w)",
        r"(?<!\w)tố\s*lốc(?!\w)",
        r"(?<!\w)lốc\s*xoáy(?!\w)",
        r"(?<!\w)vòi\s*rồng(?!\w)",
        r"(?<!\w)mưa\s*đá(?!\w)",
        r"(?<!\w)giông\s*sét(?!\w)",
        r"(?<!\w)sét(?!\w)",
        r"(?<!\w)sét\s*đánh(?!\w)",
    ]),

    # 7) Wildfire
    ("wildfire", [
        r"(?<!\w)cháy\s*rừng(?!\w)",
        r"(?<!\w)cháy\s*thực\s*bì(?!\w)",
        r"(?<!\w)đám\s*cháy\s*rừng(?!\w)",
        r"(?<!\w)bùng\s*phát\s*cháy(?!\w)",
        r"(?<!\w)nguy\s*cơ\s*cháy\s*rừng(?!\w)",
        r"(?<!\w)cấp\s*(?:dự\s*báo\s*)?cháy\s*rừng(?!\w)",
        r"(?<!\w)khói\s*mù(?!\w)",
    ]),

    # 8) Extreme weather (split patterns but keep one label)
    ("extreme_weather", [
        # Heatwave
        r"(?<!\w)nắng\s*nóng(?!\w)",
        r"(?<!\w)nắng\s*nóng\s*gay\s*gắt(?!\w)",
        r"(?<!\w)nắng\s*nóng\s*đặc\s*biệt(?!\w)",
        r"(?<!\w)nhiệt\s*độ\s*(?:cao|tăng|lên\s*tới|kỷ\s*lục)(?!\w)",

        # Drought
        r"(?<!\w)hạn\s*hán(?!\w)",
        r"(?<!\w)khô\s*hạn(?!\w)",
        r"(?<!\w)thiếu\s*nước(?!\w)",
        r"(?<!\w)cạn\s*kiệt(?!\w)",

        # Cold wave / frost
        r"(?<!\w)rét\s*đậm(?!\w)",
        r"(?<!\w)rét\s*hại(?!\w)",
        r"(?<!\w)không\s*khí\s*lạnh(?!\w)",
        r"(?<!\w)băng\s*giá(?!\w)",
        r"(?<!\w)sương\s*muối(?!\w)",

        # Saline intrusion
        r"(?<!\w)xâm\s*nhập\s*mặn(?!\w)",
        r"(?<!\w)nhiễm\s*mặn(?!\w)",
        r"(?<!\w)độ\s*mặn(?!\w)",
        r"(?<!\w)mặn\s*xâm\s*nhập(?!\w)",
    ]),

    # 9) Heavy rain as its own label (optional but rất hữu ích)
    ("heavy_rain", [
        r"(?<!\w)mưa\s*lớn(?!\w)",
        r"(?<!\w)mưa\s*to(?!\w)",
        r"(?<!\w)mưa\s*rất\s*to(?!\w)",
        r"(?<!\w)mưa\s*cực\s*lớn(?!\w)",
        r"(?<!\w)mưa\s*diện\s*rộng(?!\w)",
        r"(?<!\w)mưa\s*kéo\s*dài(?!\w)",
        r"(?<!\w)mưa\s*kỷ\s*lục(?!\w)",
        r"(?<!\w)mưa\s*cực\s*đoan(?!\w)",
        # meteorological triggers often used in alerts
        r"(?<!\w)dải\s*hội\s*tụ\s*nhiệt\s*đới(?!\w)",
        r"(?<!\w)rãnh\s*áp\s*thấp(?!\w)",
        r"(?<!\w)gió\s*mùa\s*tây\s*nam(?!\w)",
    ]),

    # 10) Marine hazard (useful for coastal news)
    ("marine_hazard", [
        r"(?<!\w)biển\s*động(?!\w)",
        r"(?<!\w)biển\s*động\s*mạnh(?!\w)",
        r"(?<!\w)sóng\s*lớn(?!\w)",
        r"(?<!\w)sóng\s*cao(?!\w)",
        r"(?<!\w)gió\s*mạnh\s*trên\s*biển(?!\w)",
        r"(?<!\w)cấm\s*biển(?!\w)",
    ]),
]

# Add pollution / air-quality related context patterns (and PM terms)
POLLUTION_TERMS = [
    r"ô\s*nhiễm", r"ô\s*nhiễm\s*không\s*khí", r"chất\s*lượng\s*không\s*khí", r"AQI",
    r"PM2\.5", r"PM10", r"bụi\s*mịn", r"khói\s*độc", r"khói\s*mù", r"nồng\s*độ\s*bụi"
]


# Build regex patterns from keywords
def _build_impact_patterns():
    patterns = {}
    # build a pattern for numeric words as well as digits
    numword_patterns = [re.escape(k) for k in NUMBER_WORDS.keys()]
    # sort so multi-word tokens come first
    numword_patterns.sort(key=lambda s: -len(s))
    numword_pattern = "|".join(numword_patterns)
    number_group = rf"(\d+|(?:{numword_pattern}))"

    for impact_type, keywords in IMPACT_KEYWORDS.items():
        keyword_patterns = [re.escape(kw) for kw in keywords]
        keyword_pattern = "|".join(keyword_patterns)

        if impact_type in ("deaths", "missing", "injured"):
            patterns[impact_type] = re.compile(
                rf"{number_group}\s*(?:người\s*)?(?:{keyword_pattern})|(?:{keyword_pattern})\s*(?:khoảng\s*)?{number_group}\s*(?:người)?",
                re.IGNORECASE,
            )
        elif impact_type == "damage":
            patterns["damage"] = re.compile(
                rf"(?:{keyword_pattern})\s*(?:khoảng\s*)?(?:ước\s*tính\s*)?{number_group}\s*(?:tỉ|tỷ|triệu)\s*(?:đồng)?|{number_group}\s*(?:tỉ|tỷ|triệu)\s*đồng",
                re.IGNORECASE,
            )

    return patterns

# Weights for scoring (tweakable)
WEIGHT_RULE = 3.0
WEIGHT_IMPACT = 3.5
WEIGHT_AGENCY = 2.0
WEIGHT_SOURCE = 1.0
WEIGHT_PROVINCE = 0.5

IMPACT_PATTERNS = _build_impact_patterns()

RE_AGENCY = re.compile(r"(Cục\s+Quản\s+lý\s+đê\s+điều.*?PCTT|Ban\s+Chỉ\s+đạo.*?PCTT|Trung\s+tâm\s+Dự\s+báo.*?KTTV|Viện\s+Vật\s+lý\s+Địa\s+cầu|Trung\s+tâm\s+báo\s+tin\s+động\s+đất.*?sóng\s+thần)", re.IGNORECASE)

PROVINCES = [
    # Tên chính thức đầu tiên để return
    "Hà Nội", "TP.HCM", "Thành phố Hồ Chí Minh", "Đà Nẵng", "Huế", "Thừa Thiên Huế",
    "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị", "Quảng Nam", "Quảng Ngãi", 
    "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận",
    "Gia Lai", "Kon Tum", "Đắk Lắk", "Đắk Nông", "Lâm Đồng", 
    "Lào Cai", "Yên Bái", "Sơn La", "Điện Biên", "Lai Châu",
    "Thanh Hóa", "Quảng Ninh", "Hải Phòng", "Hải Dương", 
    "Bắc Giang", "Bắc Ninh", "Thái Nguyên", "Cao Bằng", "Lạng Sơn",
    "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu", "Vũng Tàu",
    "Long An", "Tiền Giang", "Bến Tre", "Trà Vinh", "Sóc Trăng", "Cà Mau",
]

# Add common region names / sea references so extract_province can return broader areas
PROVINCE_REGIONS = [
    "Biển Đông", "Nam Trung Bộ", "Bắc Bộ", "Miền Trung", "Miền Bắc", "Miền Nam", "Tây Nguyên", "Trung Bộ", "Nam Bộ"
]

def _to_int(num_str: str) -> int:
    if num_str is None:
        return 0
    s = str(num_str).strip().lower()
    # direct digit
    if re.match(r"^\d+$", s):
        try:
            return int(s)
        except Exception:
            return 0
    # spelled number words
    if s in NUMBER_WORDS:
        return int(NUMBER_WORDS[s])
    # try removing punctuation
    s2 = s.replace(".", "").replace(",", "")
    if s2.isdigit():
        return int(s2)
    return 0

def _to_float(num_str: str) -> float:
    if num_str is None:
        return 0.0
    s = str(num_str).strip().lower()
    if s in NUMBER_WORDS:
        return float(NUMBER_WORDS[s])
    s2 = s.replace(".", "").replace(",", ".")
    try:
        return float(s2)
    except ValueError:
        return 0.0

def _sanitize_text_for_match(s: str) -> str:
    if not s:
        return s
    # remove boilerplate tokens like 'video', 'ảnh', 'clip'
    out = s
    for tok in BOILERPLATE_TOKENS:
        out = re.sub(tok, " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def contains_disaster_keywords(text: str) -> bool:
    """Decide using context/hazard/negative patterns per recommended rules.

    Rules:
      - If negative_hit -> False
      - If hazard_score >=1 and context_score >=1 -> True
      - If hazard is earthquake/tsunami and hazard_score >=1 -> True
      - Fallback: previous score threshold (>=3.0)
    """
    sig = compute_disaster_signals(text)
    if sig.get("negative_hit"):
        return False
    if sig.get("hazard_score", 0) >= 1 and sig.get("context_score", 0) >= 1:
        return True
    # Special-case: earthquake/tsunami are highly indicative
    for lbl in sig.get("rule_matches", []):
        if lbl in {"earthquake", "tsunami"} and sig.get("hazard_score", 0) >= 1:
            return True
    # Fallback to numeric score
    return sig.get("score", 0.0) >= 3.0


def compute_disaster_signals(text: str) -> dict:
    """Compute signals and a numeric score for disaster relevance.

    Weights (heuristic): rule_match=3, impact=3, agency=2, non-ambiguous source keyword=1 each, province=0.5.
    """
    # Preprocess: sanitize, normalize whitespace and lower
    t_raw = (text or "").strip()
    t_sanit = _sanitize_text_for_match(t_raw)
    t = re.sub(r"\s+", " ", t_sanit).lower()
    t_unaccent = _strip_accents(t)

    # rule matches (hazard)
    rule_matches = []
    for label, patterns in DISASTER_RULES:
        matched = False
        for p in patterns:
            if re.search(p, t, flags=re.IGNORECASE) or re.search(p, t_unaccent, flags=re.IGNORECASE):
                matched = True
                break
        if matched:
            rule_matches.append(label)

    # hazard score is count of distinct matched hazard types
    hazard_score = len(set(rule_matches))
    rule_score = WEIGHT_RULE if hazard_score else 0.0

    # impact keywords
    impact_hits = []
    for k, klist in IMPACT_KEYWORDS.items():
        for kw in klist:
            if kw.lower() in t or kw.lower() in t_unaccent:
                impact_hits.append((k, kw))
                break
    impact_score = WEIGHT_IMPACT if impact_hits else 0.0

    # agency
    agency_match = bool(RE_AGENCY.search(t))
    agency_score = WEIGHT_AGENCY if agency_match else 0.0

    # province
    province_found = False
    prov = None
    try:
        prov = extract_province(t)
        province_found = prov != "unknown"
    except Exception:
        province_found = False
    province_score = 0.5 if province_found else 0.0

    # source keywords (from sources.py); treat ambiguous separately
    ambiguous = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo", "cảnh báo sớm", "dự báo thời tiết"}
    source_hits = []
    non_ambiguous_hits = []
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if kl in t or kl in t_unaccent:
            source_hits.append(kl)
            if kl not in ambiguous:
                non_ambiguous_hits.append(kl)
    source_score = float(len(non_ambiguous_hits)) * WEIGHT_SOURCE

    score = rule_score + impact_score + agency_score + source_score + province_score

    # context matches (include pollution terms)
    context_hits = []
    for p in DISASTER_CONTEXT_PATTERNS:
        if p.search(t) or p.search(t_unaccent):
            context_hits.append(p.pattern)
    # pollution/air-quality context
    for pt in POLLUTION_TERMS:
        if re.search(pt, t, flags=re.IGNORECASE) or re.search(pt, t_unaccent, flags=re.IGNORECASE):
            context_hits.append(pt)
    context_score = len(context_hits)

    # negative patterns
    negative_hit = False
    for p in DISASTER_NEGATIVE_PATTERNS:
        if p.search(t) or p.search(t_unaccent):
            negative_hit = True
            break

    signals = {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": prov if province_found else None,
        "source_hits": source_hits,
        "non_ambiguous_hits": non_ambiguous_hits,
        "score": score,
        "hazard_score": hazard_score,
        "context_hits": context_hits,
        "context_score": context_score,
        "negative_hit": negative_hit,
    }
    return signals


def diagnose(text: str) -> dict:
    """Return a diagnostic dict with score and human-readable reason for logging."""
    sig = compute_disaster_signals(text)
    parts = []
    if sig.get("rule_matches"):
        parts.append("rule:" + ",".join(sig["rule_matches"]))
    if sig.get("impact_hits"):
        parts.append("impact")
    if sig.get("agency"):
        parts.append("agency")
    if sig.get("non_ambiguous_hits"):
        parts.append("keywords:" + ",".join(sig["non_ambiguous_hits"]))
    if sig.get("province"):
        parts.append("province:" + sig["province"])

    reason = ", ".join(parts) if parts else "no strong signals"
    return {"score": sig.get("score", 0.0), "reason": reason, "signals": sig}


# Precompile title keyword patterns for fast title-only checks
TITLE_KEYWORD_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in SOURCE_DISASTER_KEYWORDS]


def title_contains_disaster_keyword(title: str) -> bool:
    """Return True if the article *title* contains any disaster keyword from sources.DISASTER_KEYWORDS.

    This enforces a strict title-only check (used when we want to accept only when the title
    explicitly mentions a disaster-related term).
    """
    if not title:
        return False
    # sanitize and check both original and unaccented variants
    t = _sanitize_text_for_match(title)
    t_unaccent = _strip_accents(t)
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if re.search(r"\b" + re.escape(kl) + r"\b", t, flags=re.IGNORECASE):
            return True
        # unaccented keyword
        kl_un = _strip_accents(kl)
        if kl_un and re.search(r"\b" + re.escape(kl_un) + r"\b", t_unaccent, flags=re.IGNORECASE):
            return True
    return False


# Context patterns: indicate warnings/response/impact words that raise precision
DISASTER_CONTEXT_PATTERNS = [
    # warning / risk level
    re.compile(r"(?<!\w)cảnh\s*báo(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)khuyến\s*cáo(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cảnh\s*báo\s*sớm(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cấp\s*độ\s*rủi\s*ro(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)rủi\s*ro\s*thiên\s*tai(?!\w)", re.IGNORECASE),

    # response / evacuation / rescue
    re.compile(r"(?<!\w)ứng\s*phó(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)khắc\s*phục(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)sơ\s*tán(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)di\s*dời(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cứu\s*hộ(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cứu\s*nạn(?!\w)", re.IGNORECASE),

    # impact / disruption
    re.compile(r"(?<!\w)thiệt\s*hại(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)thương\s*vong(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)mất\s*tích(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)bị\s*thương(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)chia\s*cắt(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cô\s*lập(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)mất\s*điện(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)mất\s*liên\s*lạc(?!\w)", re.IGNORECASE),
]


# Negative patterns: common metaphorical or noisy phrases to exclude
DISASTER_NEGATIVE_PATTERNS = [
    # storm metaphors
    re.compile(r"(?<!\w)bão\s*giá(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng)(?!\w)", re.IGNORECASE),

    # earthquake metaphors
    re.compile(r"(?<!\w)động\s*đất\s*(?:thị\s*trường|giá|chứng\s*khoán|bất\s*động\s*sản)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)rung\s*chấn\s*(?:dư\s*luận|thị\s*trường)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|mạng)(?!\w)", re.IGNORECASE),

    # flood metaphors
    re.compile(r"(?<!\w)lũ\s*(?:lượt|fan|like|view|đơn\s*hàng)(?!\w)", re.IGNORECASE),
]


def _strip_accents(s: str) -> str:
    if not s:
        return s
    nkfd = unicodedata.normalize("NFD", s)
    return "".join([c for c in nkfd if not unicodedata.combining(c)])

def classify_disaster(text: str) -> str:
    t = text.lower()
    for label, patterns in DISASTER_RULES:
        for p in patterns:
            if re.search(p, t, flags=re.IGNORECASE):
                return label
    return "unknown"

def extract_province(text: str) -> str:
    text_lower = text.lower()
    for prov in PROVINCES:
        prov_lower = prov.lower()
        if prov_lower in text_lower:
            if prov == "Thành phố Hồ Chí Minh":
                return "TP.HCM"
            if prov == "Thừa Thiên Huế":
                return "Huế"
            return prov
    # check for region / sea mentions
    for region in globals().get("PROVINCE_REGIONS", []):
        if region.lower() in text_lower:
            return region
    return "unknown"

def extract_impacts(text: str) -> dict:
    """Extract impact numbers using keyword-based patterns."""
    deaths = missing = injured = None
    damage = None

    m = IMPACT_PATTERNS["deaths"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        deaths = _to_int(num_str)
        if deaths == 0:
            deaths = None
    
    m = IMPACT_PATTERNS["missing"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        missing = _to_int(num_str)
        if missing == 0:
            missing = None
    
    m = IMPACT_PATTERNS["injured"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        injured = _to_int(num_str)
        if injured == 0:
            injured = None

    m = IMPACT_PATTERNS["damage"].search(text)
    if m:
        damage_str = m.group(1) or m.group(2) or "0"
        damage = _to_float(damage_str)
        if damage == 0:
            damage = None

    agency = None
    m = RE_AGENCY.search(text)
    if m:
        agency = m.group(1)

    return {
        "deaths": deaths,
        "missing": missing,
        "injured": injured,
        "damage_billion_vnd": damage,
        "agency": agency,
    }

def extract_event_time(published_at: datetime, text: str) -> datetime | None:
    candidates = []
    for m in re.finditer(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text):
        candidates.append(m.group(1))
    for c in candidates[:3]:
        try:
            dt = dtparser.parse(c, dayfirst=True)
            if dt.year == 1900:
                dt = dt.replace(year=published_at.year)
            return dt
        except Exception:
            continue
    return None

def summarize(text: str, max_len: int = 220) -> str:
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Limit length
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"
