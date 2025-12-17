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
    "hai trăm": 200,
    "ba trăm": 300, 
    "năm trăm": 500,
    "nghìn": 1000,
    "một nghìn": 1000,
    
}

# 1) Phân loại thiên tai theo từ khóa (rule-based)
# 1) Phân loại thiên tai theo từ khóa (rule-based) - 8 Nhóm theo QĐ 18/2021/QD-TTg
DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới
  ("storm", [
    r"(?<!\w)bão(?!\w)", r"bão\s*số\s*\d+",
    r"siêu\s*bão", r"hoàn\s*lưu\s*bão", r"tâm\s*bão",
    r"đổ\s*bộ", r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông",
    r"suy\s*yếu", r"mạnh\s*lên", r"tăng\s*cấp",
    r"áp\s*thấp\s*nhiệt\s*đới", r"\bATNĐ\b", r"vùng\s*áp\s*thấp",
    r"xoáy\s*thuận\s*nhiệt\s*đới", r"nhiễu\s*động\s*nhiệt\s*đới",
    # cụm báo chí hay kèm
    r"gió\s*mạnh\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai", r"biển\s*động"
  ]),

  # 2) Mưa lớn & lũ lụt (kèm ngập, lũ quét, sạt lở/sụt lún do mưa lũ/dòng chảy)
  ("flood_landslide", [
    # mưa lớn
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"mưa\s*cực\s*lớn",
    r"mưa\s*đặc\s*biệt\s*lớn", r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài",
    r"mưa\s*kỷ\s*lục", r"mưa\s*cực\s*đoan", r"mưa\s*như\s*trút",
    # cơ chế hay được nêu trong bản tin/bài báo
    r"dải\s*hội\s*tụ\s*nhiệt\s*đới", r"rãnh\s*áp\s*thấp", r"gió\s*mùa",

    # lũ/ngập
    r"lũ(?!\s*lượt)", r"lụt", r"lũ\s*lụt",
    r"ngập(?!\s*đầu\s*tư)", r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu",
    r"ngập\s*cục\s*bộ",
    r"nước\s*lên\s*nhanh", r"mực\s*nước\s*dâng", r"đỉnh\s*lũ",
    r"báo\s*động\s*(?:1|2|3|I|II|III)", r"vượt\s*báo\s*động",

    # lũ quét / lũ ống
    r"lũ\s*quét", r"lũ\s*ống", r"nước\s*lũ\s*cuốn\s*trôi",

    # sự cố đê/đập/xả lũ (thường đi kèm tin lũ)
    r"vỡ\s*đê", r"vỡ\s*kè", r"tràn\s*đê", r"tràn\s*bờ",
    r"vỡ\s*đập", r"sự\s*cố\s*đập", r"sự\s*cố\s*hồ\s*chứa",
    r"xả\s*lũ", r"xả\s*tràn", r"mở\s*cửa\s*xả",

    # sạt lở/sụt lún do mưa lũ/dòng chảy
    r"sạt\s*lở", r"sạt\s*lở\s*đất", r"lở\s*đất", r"trượt\s*đất",
    r"sạt\s*lở\s*bờ\s*sông", r"sạt\s*lở\s*bờ\s*biển",
    r"sụt\s*lún", r"hố\s*tử\s*thần"
  ]),

  # 3) Nắng nóng, hạn hán, xâm nhập mặn (kèm sạt lở/sụt lún do hạn)
  ("heat_drought", [
    # nắng nóng
    r"nắng\s*nóng", r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt",
    r"nhiệt\s*độ\s*(?:cao|tăng|kỷ\s*lục)", r"oi\s*bức",
    # hạn hán/thiếu nước
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước", r"cạn\s*kiệt",
    r"khát\s*nước", r"nứt\s*nẻ", r"đất\s*khô\s*nứt",
    r"mực\s*nước\s*hồ\s*chứa\s*(?:giảm|xuống\s*thấp)", r"cạn\s*hồ",
    # xâm nhập mặn
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"mặn\s*xâm\s*nhập",
    r"độ\s*mặn", r"ranh\s*mặn", r"nước\s*mặn\s*xâm\s*nhập",
    r"hạn\s*mặn",
    # hệ quả địa chất do hạn (báo chí hay mô tả)
    r"sạt\s*lở", r"sụt\s*lún"
  ]),

  # 4) Gió mạnh & sương mù (biển + đất liền)
  ("wind_fog", [
    # gió mạnh
    r"gió\s*mạnh", r"gió\s*giật", r"gió\s*giật\s*mạnh",
    r"gió\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"biển\s*động", r"biển\s*động\s*mạnh", r"sóng\s*lớn", r"sóng\s*cao",
    # sương mù
    r"sương\s*mù", r"sương\s*mù\s*dày\s*đặc", r"mù\s*dày\s*đặc",
    r"tầm\s*nhìn\s*hạn\s*chế", r"giảm\s*tầm\s*nhìn"
  ]),

  # 5) Nước dâng (ven bờ & đảo)
  ("storm_surge", [
    r"nước\s*dâng", r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng",
    r"mực\s*nước\s*biển\s*dâng", r"dâng\s*cao", r"đỉnh\s*triều",
    r"triều\s*cường", r"ngập\s*do\s*triều", r"sóng\s*lớn", r"biển\s*động",
    r"xâm\s*thực\s*bờ\s*biển", r"xói\s*lở\s*bờ\s*biển"
  ]),

  # 6) Hiện tượng thời tiết cực đoan khác: lốc, sét, mưa đá, rét hại, sương muối
  ("extreme_other", [
    # lốc
    r"lốc(?!\s*xoáy\s*thị\s*trường)", r"dông\s*lốc", r"giông\s*lốc",
    r"lốc\s*xoáy", r"tố\s*lốc", r"vòi\s*rồng",
    # sét
    r"sét", r"sét\s*đánh", r"giông\s*sét",
    # mưa đá
    r"mưa\s*đá",
    # rét
    r"rét\s*hại", r"rét\s*đậm", r"không\s*khí\s*lạnh", r"không\s*khí\s*lạnh\s*tăng\s*cường",
    r"băng\s*giá",
    # sương muối
    r"sương\s*muối"
  ]),

  # 7) Cháy rừng tự nhiên
  ("wildfire", [
    r"cháy\s*rừng", r"cháy\s*rừng\s*tự\s*nhiên", r"cháy\s*thực\s*bì",
    r"bùng\s*phát\s*cháy", r"đám\s*cháy", r"nguy\s*cơ\s*cháy\s*rừng",
    r"cấp\s*dự\s*báo\s*cháy\s*rừng", r"cấp\s*cháy\s*rừng"
  ]),

  # 8-10) Động đất & sóng thần (ngưỡng M/ Richter hay xuất hiện trong báo)
  ("quake_tsunami", [
    # động đất
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn", r"tâm\s*chấn",
    r"đứt\s*gãy\s*địa\s*chất", # stricter than just "đứt gãy"
    r"nứt\s*đất\s*do\s*động\s*đất", # stricter
    r"(?:độ\s*lớn|cường\s*độ)\s*\d+(?:[.,]\d+)?\s*richter", # Must mention richter or magnitude context if possible, but keeping current patterns for now with caution
    r"\d+(?:[.,]\d+)?\s*(?:độ\s*richter|richter)",
    r"\bM\s*\d+(?:[.,]\d+)?\b", r"(?:magnitude|mag)\s*\d+(?:[.,]\d+)?",
    # sóng thần
    r"sóng\s*thần", r"cảnh\s*báo\s*sóng\s*thần", r"báo\s*động\s*sóng\s*thần", r"\btsunami\b"
  ]),
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc"
]

DISASTER_NEGATIVE = [
  r"bão\s*giá", r"cơn\s*bão\s*dư\s*luận", r"bão\s*tin\s*giả",
  r"rung\s*chấn\s*dư\s*luận", r"chấn\s*động\s*dư\s*luận",
  r"lũ\s*lượt", r"lũ\s*view", r"lũ\s*like"
]

DISASTER_CONTEXT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DISASTER_NEGATIVE]

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
            
    # Extra check: if heavily sports related, assume negative unless very strong disaster rules
    if not negative_hit:
        sports_count = sum(1 for w in SPORTS_TERMS if w in t)
        if sports_count >= 2 and hazard_score < 2:
            # "địa chấn" in a sports article -> likely sports metaphor
            if "địa chấn" in t or "cơn địa chấn" in t:
                negative_hit = True
            # "cơn lốc" in sports
            if "cơn lốc" in t:
                negative_hit = True

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
    re.compile(r"(?<!\w)ngập\s*(?:tràn|trong)\s*(?:hạnh\s*phúc|tiếng\s*cười|quà|bình\s*luận)(?!\w)", re.IGNORECASE),

    # general metaphors / false contexts
    re.compile(r"(?<!\w)bão\s*(?:chấn\s*thương|bệnh\s*tật|sa\s*thải)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|nhập\s*cư|tẩy\s*chay)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cơn\s*sốt\s*(?:đất|giá|vé)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)(?!\w)", re.IGNORECASE),

    # Construction / Planning / Policy (Non-disaster events)
    re.compile(r"(?<!\w)quy\s*hoạch(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)phê\s*duyệt(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)khởi\s*công(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)khánh\s*thành(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)nghiệm\s*thu(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)đấu\s*thầu(?!\w)", re.IGNORECASE),
    
    # Traffic accidents (unless clearly disaster related, usually these are distinct)
    re.compile(r"(?<!\w)tai\s*nạn\s*giao\s*thông(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)va\s*chạm\s*xe(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)xe\s*tải(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)xe\s*container(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)xe\s*khách(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)đường\s*cao\s*tốc(?!\w)", re.IGNORECASE), # "Tuyến cao tốc" issue

    # sports specific
    re.compile(r"(?<!\w)địa\s*chấn\s*(?:sân\s*cỏ|tại\s*world\s*cup|vòng\s*loại)(?!\w)", re.IGNORECASE),
    re.compile(r"(?<!\w)cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam)(?!\w)", re.IGNORECASE), # Dutch team metaphor
    re.compile(r"(?<!\w)(?:thắng|thua)\s*(?:hủy\s*diệt|chấn\s*động)(?!\w)", re.IGNORECASE),
]

# Quick negative context check for sports
SPORTS_TERMS = [
    "bóng đá", "v-league", "ngoại hạng anh", "world cup", "đội tuyển", "cầu thủ", 
    "huấn luyện viên", "sân vận động", "ghi bàn", "thủ môn", "trận đấu"
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

def extract_risk_level(text: str, disaster_type: str) -> int:
    """Determine risk level (1-5) based on text rules or default mappings.
    Updated with logic from Decision 18/2021/QD-TTg for Storms/Tropical Depressions.
    """
    t = text.lower()
    
    # 1. Explicit mention in text (High Priority)
    # Patterns: "rủi ro thiên tai cấp 3", "rủi ro cấp 4", "báo động 3"
    
    levels = []
    
    # "rủi ro thiên tai cấp X"
    m = re.search(r"rủi\s*ro\s*(?:thiên\s*tai\s*)?(?:cấp|mức|độ)\s*(\d)", t)
    if m:
        try:
            val = int(m.group(1))
            if 1 <= val <= 5:
                levels.append(val)
        except: pass

    # "báo động X" (often maps to flood risk)
    m2 = re.search(r"báo\s*động\s*(\d|I|II|III)", t)
    if m2:
        val_str = m2.group(1).upper()
        if val_str == "1" or val_str == "I": levels.append(1)
        elif val_str == "2" or val_str == "II": levels.append(2)
        elif val_str == "3" or val_str == "III": levels.append(3)

    if levels:
        return max(levels)

    # 2. Detailed Rules based on Disaster Type

    # === STORM / TROPICAL DEPRESSION (Bão / ATNĐ) ===
    if disaster_type == "storm":
        # Helper to extract max level mentioned
        # Matches: "cấp 12", "cấp 8-9", "mạnh cấp 10"
        lv_matches = re.findall(r"cấp\s*(\d{1,2})", t)
        parsed_lvs = []
        for v in lv_matches:
            try:
                parsed_lvs.append(int(v))
            except: pass
        
        max_lv = max(parsed_lvs) if parsed_lvs else 0
        
        # Check for "ATNĐ" or "Áp thấp nhiệt đới" implies base level if no explicit level
        is_atnd = "áp thấp nhiệt đới" in t or "atnđ" in t
        if is_atnd and max_lv == 0:
            max_lv = 7 # Treat as < 8

        # Check for Super Storm explicitly
        if "siêu bão" in t:
            max_lv = max(max_lv, 16)

        # Region Detection
        regions = set()
        
        # Sea
        if re.search(r"biển\s*đông|trường\s*sa|hoàng\s*sa", t):
            regions.add("sea")
        # Coastal
        if re.search(r"ven\s*bờ|vùng\s*biển|cửa\s*biển", t):
            regions.add("coastal")
        # Land - South (Nam Bộ)
        if re.search(r"nam\s*bộ|miền\s*tây|đồng\s*bằng\s*sông\s*cửu\s*long|cà\s*mau|kiên\s*giang|bạc\s*liêu|sóc\s*trăng|trà\s*vinh|bến\s*tre|tiền\s*giang|vĩnh\s*long|cần\s*thơ|hậu\s*giang|đồng\s*tháp|an\s*giang|long\s*an|bình\s*phước|bình\s*dương|đồng\s*nai|tây\s*ninh|bà\s*rịa|\bvũng\s*tàu\b|tp\.hcm|hồ\s*chí\s*minh", t):
            regions.add("south")
        # Land - Highlands (Tây Nguyên)
        if re.search(r"tây\s*nguyên|kon\s*tum|gia\s*lai|đắk\s*lắk|đắk\s*nông|lâm\s*đồng", t):
            regions.add("highlands")
        # Land - S.Central (Nam Trung Bộ)
        if re.search(r"nam\s*trung\s*bộ|đà\s*nẵng|quảng\s*nam|quảng\s*ngãi|bình\s*định|phú\s*yên|khánh\s*hòa|ninh\s*thuận|bình\s*thuận", t):
            regions.add("s_central")
        # Land - C.Central (Trung Trung Bộ - loosely defined or overlapping) / N.Central (Bắc Trung Bộ)
        # Grouping Central for simplicity if needed, but rules distinguish specific sets.
        if re.search(r"bắc\s*trung\s*bộ|thanh\s*hóa|nghệ\s*an|hà\s*tĩnh|quảng\s*bình|quảng\s*trị|thừa\s*thiên\s*huế", t):
            regions.add("n_central")
        # Land - North (Northern Delta, NE, NW, Viet Bac)
        if re.search(r"bắc\s*bộ|đồng\s*bằng\s*sông\s*hồng|hà\s*nội|hải\s*phòng|quảng\s*ninh|hải\s*dương|hưng\s*yên|thái\s*bình|hà\s*nam|nam\s*định|ninh\s*bình|vĩnh\s*phúc|bắc\s*ninh", t):
            regions.add("delta_north")
        if re.search(r"đông\s*bắc|hà\s*giang|cao\s*bằng|bắc\s*kạn|lạng\s*sơn|tuyên\s*quang|thái\s*nguyên|phú\s*thọ|bắc\s*giang", t):
            regions.add("ne_north")
        if re.search(r"tây\s*bắc|việt\s*bắc|hòa\s*bình|sơn\s*la|điện\s*biên|lai\s*châu|lào\s*cai|yên\s*bái", t):
            regions.add("nw_north")

        # Global flag for "land" if specific regions not caught but "đất liền" mentioned
        any_land = len(regions.difference({"sea", "coastal"})) > 0 or "đất liền" in t

        # --- LEVEL 5 RULES ---
        # 1. Storm Lv 12-13 on Land South
        if (12 <= max_lv <= 13) and "south" in regions:
            return 5
        # 2. Storm Lv 14-15 on Land NW, Viet Bac, S.Central, Highlands, South
        if (14 <= max_lv <= 15) and ({"nw_north", "s_central", "highlands", "south"}.intersection(regions)):
            return 5
        # 3. Super Storm >= Lv 16 on Coastal, Land (All)
        if max_lv >= 16 and (any_land or "coastal" in regions):
            return 5

        # --- LEVEL 4 RULES ---
        # 1. Storm Lv 10-11 on Land South
        if (10 <= max_lv <= 11) and "south" in regions:
            return 4
        # 2. Storm Lv 12-13 on Coastal, Land NW, Viet Bac, NE, RR Delta, NC, CC, SC, Highlands
        # (Basically Land NOT South)
        target_regions_lv4_2 = {"coastal", "nw_north", "ne_north", "delta_north", "n_central", "s_central", "highlands"}
        if (12 <= max_lv <= 13) and (target_regions_lv4_2.intersection(regions) or (any_land and "south" not in regions)):
            return 4
        # 3. Storm Lv 14-15 on Coastal, Land NE, RR Delta, NC, CC (subset of North/Central)
        target_regions_lv4_3 = {"coastal", "ne_north", "delta_north", "n_central"}
        if (14 <= max_lv <= 15) and (target_regions_lv4_3.intersection(regions)):
            return 4
        # 4. Storm >= Lv 14 on East Sea
        if max_lv >= 14 and "sea" in regions:
            return 4

        # --- LEVEL 3 RULES (Default for Storm/ATNĐ) ---
        # Technically "ATNĐ, Storm Lv 8-9" anywhere, Storm Lv 10-11 except South, Storm Lv 12-13 Sea only.
        # But since we check 5 and 4 first, anything else falling through is likely 3 if it's a storm.
        
        # Explicit checks for upgrading FROM lower levels (if default was 1, but storms start at 3 per reg):
        # 1. ATNĐ, Storm Lv 8-9 (Anywhere) -> 3
        # 2. Storm Lv 10-11 (Anywhere NOT South, i.e. Sea, Coastal, North/Central/Highlands) -> 3
        # 3. Storm Lv 12-13 (East Sea) -> 3
        
        # So essentially, if it's a storm/ATNĐ, the regulatory minimum is Level 3 (except maybe weak lows, but "Áp thấp nhiệt đới" starts at 3).
        return 3

    # === OTHER DISASTERS (Existing Logic) ===

    # Mưa lớn / Lũ lụt: cấp 1-4
    if disaster_type == "flood_landslide":
        if "lũ quét" in t or "sạt lở" in t: return 3 # Flash floods are high risk
        if "lịch sử" in t or "kỷ lục" in t: return 4
        if "báo động 3" in t or "báo động III" in t: return 3
        return 1 # Default rain/flood starts at 1

    # Nắng nóng / Hạn hán: cấp 1
    if disaster_type == "heat_drought":
        if "đặc biệt gay gắt" in t: return 3
        if "gay gắt" in t: return 2
        return 1

    # Lốc, sét, mưa đá/khác: cấp 1-2
    if disaster_type in ("wind_fog", "extreme_other"):
        if "diện rộng" in t or "thiệt hại nặng" in t: return 2
        return 1
    
    # Nước dâng
    if disaster_type == "storm_surge":
        if "nghiêm trọng" in t or "cao kỷ lục" in t: return 3
        return 1
        
    # Động đất / Sóng thần: 
    if disaster_type == "quake_tsunami":
        if "sóng thần" in t: return 5
        # > 6.5 -> risk high (heuristic)
        if re.search(r"(?:[6-9]\.\d|10\.)\s*độ", t):
            return 3
        return 1

    # Cháy rừng
    if disaster_type == "wildfire":
        if "cấp 5" in t or "cực kỳ nguy hiểm" in t: return 5
        if "cấp 4" in t or "nguy hiểm" in t: return 4
        return 1

    return 1 # Default lowest risk
