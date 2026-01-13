import re
import unicodedata
import logging
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from functools import lru_cache
from . import sources
from .sources import (
    DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS, 
    DISASTER_CONTEXT,
    SCORING_WEIGHTS as SW,
    RE_CRITICAL_ACTIONS,
    DISASTER_PRIORITY_ORDER,
    NEGATION_TERMS,
    NUMBER_WORDS,
    WHITELIST_TERMS,
    RE_WARNING_TITLE,
    RE_RECOVERY_TITLE,
    RISK_LEVEL_RE,
    RE_AGENCY,
    HIGH_PRIORITY_RE, MEDIUM_PRIORITY_RE,
    NUM_HARD, QUAL, UNIT, DEATH_WORD, INJ_WORD, MISS_WORD, CARE_WORD,
    IMPACT_KEYWORDS,
    ABSOLUTE_VETO_RE, CONDITIONAL_VETO_RE, SOFT_NEGATIVE_RE,
    PLANNING_PREP_KEYWORDS, RE_PLANNING,
    DISASTER_PRIORITY_MAP,
    AMBIGUOUS_KEYWORDS
)

def strip_accents(text):
    """Normalize Vietnamese text by removing accents."""
    if not text: return ""
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
    text = re.sub(r'[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'A', text)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
    text = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', text)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
    text = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', text)
    text = re.sub(r'[ìíịỉĩ]', 'i', text)
    text = re.sub(r'[ÌÍỊỈĨ]', 'I', text)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
    text = re.sub(r'[ÙÚỤỦŨƯỪỨỰỬỮ]', 'U', text)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
    text = re.sub(r'[ỲÝỴỶỸ]', 'Y', text)
    text = re.sub(r'[đ]', 'd', text)
    text = re.sub(r'[Đ]', 'D', text)
    return text
# Re-export key constants for external modules
SCORING_WEIGHTS = SW
DISASTER_PRIORITY_MAP = DISASTER_PRIORITY_MAP

from . import risk_lookup

logger = logging.getLogger(__name__)

def is_junk_title(title: str) -> bool:
    """
    Check if the title is a generic landing page or SEO noise rather than an actual article.
    Helps avoid blacklisting thousands of 'Search Results' pages.
    """
    if not title: return False
    # Use centralized pre-compiled junk pattern
    if sources.JUNK_TITLE_RE and sources.JUNK_TITLE_RE.search(title.lower()):
        return True
    return False

# Pre-compiled patterns for location and metadata extraction
RE_SENTENCE_SPLIT = re.compile(r'(?<=[\.?!;])\s+', re.UNICODE)
RE_COMMUNE = re.compile(r"(?:xã|phường|thị\s*trấn|thị\s*tứ)\s+([A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*(?:\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*)*)")
RE_VILLAGE = re.compile(r"(?:thôn|bản|ấp|xóm|khối|tổ|khu\s*phố|ngõ|ngách|hẻm|số\s*nhà)\s+([A-Z0-9\xC0-\xDFĐ][a-z0-9\xE0-\xFFà-ỹ]*(?:\s+[A-Z0-9\xC0-\xDFĐ][a-z0-9\xE0-\xFFà-ỹ]*)*)")
RE_ROUTE = re.compile(r"(?:tuyến|quốc\s*lộ|tỉnh\s*lộ|đường|cao\s*tốc)\s+([A-Z0-9Đ][a-z0-9à-ỹ\-\.\/]*(\s+[A-Z0-9Đ][a-z0-9à-ỹ\-\.\/]*)*)")
RE_LANDMARK = re.compile(r"((?:sông|suối|núi|cầu|hồ|đập|đèo|kè|cống|vịnh|biển|mương|rạch|kênh|hầm|nhà\s*máy|kho|xưởng|cảng|sân\s*bay|quốc\s*lộ|tỉnh\s*lộ|đường|cao\s*tốc|đường\s*sắt|metro|nhà\s*ga|trạm\s*biến\s*áp|nhà\s*máy\s*nhiệt\s*điện|nhà\s*máy\s*thủy\s*điện|nhà\s*máy\s*điện\s*gió)\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*(?:\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*)*)")

# Negation terms are now centralized in sources.py

def safe_no_accent(pat: str) -> bool:
    """
    Heuristic to determine if a regex pattern is safe to match against
    unaccented text without causing excessive false positives.
    """
    # Whitelist very specific disaster terms that are safe even if short
    hazard_whitelist = ["lũ", "lụt", "lốc", "rét", "bão"]
    # Only allow unaccented if it contains one of these AND is long enough or specific

    # 1. Strip lookarounds (they don't add to match length)
    # (?=...), (?!...), (?<=...), (?<!...)
    p = re.sub(r"\(\?(?![P:])(?:[=!<>]+).*?\)", " ", pat)

    # 2. Strip character classes [a-z], [0-9], etc.
    p = re.sub(r"\[.*?\]", " ", p)

    # 3. Strip escape classes \w, \s, \d, etc.
    p = re.sub(r"\\(?:[wsdbwWSD]|b|B)", " ", p)

    # 4. Strip group syntax but keep contents
    p = re.sub(r"\(\?P<.*?>", " ", p) # named groups
    p = re.sub(r"\(\?:", " ", p)   # non-capturing
    p = re.sub(r"[\(\)]", " ", p)

    # 5. Strip quantifiers and other meta-chars
    p = re.sub(r"[\*\+\?\.\^\\\$|{}]", " ", p)

    # 6. Normalize whitespace
    p = re.sub(r"\s+", " ", p).strip()

    # [LOGIC]
    # - If very long literal string (>= 12), usually safe
    # - If multiple words (contains space) and length >= 10, usually safe
    # - If it's a whitelisted hazard word AND has some specificity (e.g. "lũ ống", "siêu bão")

    if len(p) >= 12: return True
    if " " in p and len(p) >= 10: return True

    # Specific safety for whitelisted words with modifiers
    for hw in hazard_whitelist:
        if hw in p.lower() and len(p) >= 6:
            return True

    return False

def normalize_text(text: str) -> str:
    """
    Lowercase + Normalize whitespace + Unicode NFC (Preserve accents).
    NFC ensures that 'hòa' and 'hoà' are treated as the same string.
    """
    if not text: return ""
    # Unicode Normalization to NFC (Canonical Composition)
    t = unicodedata.normalize('NFC', text)
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def strip_accents_and_normalize(text: str) -> str:
    """
    Lowercase + Normalize whitespace + Strip accents.
    """
    t = normalize_text(text)
    return risk_lookup.strip_accents(t)


# Number words are now centralized in sources.py

# 34 PROVINCES MAPPING (NEW - Effective July 1, 2025)
# Format: New_Name -> List of Old_Names/Variants to match in text

def dedupe_keep_order(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]

PROVINCE_MAPPING = {
    # NORTH
    "TP. Hà Nội": ["Hà Nội", "HN", "Ha Noi", "Thu Do", "Thủ đô Hà Nội"],
    "Hà Giang": ["Hà Giang", "Ha Giang"],
    "Cao Bằng": ["Cao Bằng", "Cao Bang"],
    "Bắc Kạn": ["Bắc Kạn", "Bac Kan"],
    "Tuyên Quang": ["Tuyên Quang", "Tuyen Quang"],
    "Lào Cai": ["Lào Cai", "Lao Cai"],
    "Điện Biên": ["Điện Biên", "Dien Bien"],
    "Lai Châu": ["Lai Châu", "Lai Chau"],
    "Sơn La": ["Sơn La", "Son La"],
    "Yên Bái": ["Yên Bái", "Yen Bai"],
    "Hòa Bình": ["Hòa Bình", "Hoa Binh"],
    "Thái Nguyên": ["Thái Nguyên", "Thai Nguyen"],
    "Lạng Sơn": ["Lạng Sơn", "Lang Son"],
    "Quảng Ninh": ["Quảng Ninh", "Quang Ninh"],
    "Bắc Giang": ["Bắc Giang", "Bac Giang"],
    "Phú Thọ": ["Phú Thọ", "Phu Tho"],
    "Vĩnh Phúc": ["Vĩnh Phúc", "Vinh Phuc"],
    "Bắc Ninh": ["Bắc Ninh", "Bac Ninh"],
    "Hải Dương": ["Hải Dương", "Hai Duong"],
    "TP. Hải Phòng": ["Hải Phòng", "Hai Phong", "HP"],
    "Hưng Yên": ["Hưng Yên", "Hung Yen"],
    "Thái Bình": ["Thái Bình", "Thai Binh"],
    "Hà Nam": ["Hà Nam", "Ha Nam"],
    "Nam Định": ["Nam Định", "Nam Dinh"],
    "Ninh Bình": ["Ninh Bình", "Ninh Binh"],

    # CENTRAL
    "Thanh Hóa": ["Thanh Hóa", "Thanh Hoa"],
    "Nghệ An": ["Nghệ An", "Nghe An"],
    "Hà Tĩnh": ["Hà Tĩnh", "Ha Tinh"],
    "Quảng Bình": ["Quảng Bình", "Quang Binh"],
    "Quảng Trị": ["Quảng Trị", "Quang Tri"],
    "Thừa Thiên Huế": ["Thừa Thiên Huế", "Thua Thien Hue", "TP. Huế", "TP Huế", "Thành phố Huế"], # Huế is city in TTH, but often used for province
    "TP. Đà Nẵng": ["Đà Nẵng", "Da Nang", "ĐN"],
    "Quảng Nam": ["Quảng Nam", "Quang Nam"],
    "Quảng Ngãi": ["Quảng Ngãi", "Quang Ngai", "QNg"],
    "Bình Định": ["Bình Định", "Binh Dinh"],
    "Phú Yên": ["Phú Yên", "Phu Yen"],
    "Khánh Hòa": ["Khánh Hòa", "Khanh Hoa"],
    "Ninh Thuận": ["Ninh Thuận", "Ninh Thuan"],
    "Bình Thuận": ["Bình Thuận", "Binh Thuan"],
    "Kon Tum": ["Kon Tum"],
    "Gia Lai": ["Gia Lai"],
    "Đắk Lắk": ["Đắk Lắk", "Dak Lak"],
    "Đắk Nông": ["Đắk Nông", "Dak Nong"],
    "Lâm Đồng": ["Lâm Đồng", "Lam Dong"],

    # SOUTH
    "Bình Phước": ["Bình Phước", "Binh Phuoc"],
    "Tây Ninh": ["Tây Ninh", "Tay Ninh"],
    "Bình Dương": ["Bình Dương", "Binh Duong"],
    "Đồng Nai": ["Đồng Nai", "Dong Nai"],
    "Bà Rịa - Vũng Tàu": ["Bà Rịa - Vũng Tàu", "Ba Ria - Vung Tau", "BRVT", "Bà Rịa", "Vũng Tàu"],
    "TP. Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn", "HCMC", "Sai Gon", "SG"],
    "Long An": ["Long An"],
    "Tiền Giang": ["Tiền Giang", "Tien Giang"],
    "Bến Tre": ["Bến Tre", "Ben Tre"],
    "Trà Vinh": ["Trà Vinh", "Tra Vinh"],
    "Vĩnh Long": ["Vĩnh Long", "Vinh Long"],
    "Đồng Tháp": ["Đồng Tháp", "Dong Thap"],
    "An Giang": ["An Giang"],
    "Kiên Giang": ["Kiên Giang", "Kien Giang"],
    "TP. Cần Thơ": ["Cần Thơ", "Can Tho"],
    "Hậu Giang": ["Hậu Giang", "Hau Giang"],
    "Sóc Trăng": ["Sóc Trăng", "Soc Trang"],
    "Bạc Liêu": ["Bạc Liêu", "Bac Lieu"],
    "Cà Mau": ["Cà Mau", "Ca Mau"]
}

# Deduplicate province variants
for k, v in PROVINCE_MAPPING.items():
    PROVINCE_MAPPING[k] = dedupe_keep_order(v)
# List of valid (new) province names
PROVINCES = list(PROVINCE_MAPPING.keys())

# Geographic coordinates for the 34 provinces (Approximate Center)
PROVINCE_COORDINATES = {
    "TP. Hà Nội": [21.0285, 105.8542],
    "Hà Giang": [22.8233, 104.9836],
    "Cao Bằng": [22.6667, 106.2500],
    "Bắc Kạn": [22.1470, 105.8348],
    "Tuyên Quang": [21.8228, 105.2173],
    "Lào Cai": [22.4833, 103.9667],
    "Điện Biên": [21.3852, 103.0235],
    "Lai Châu": [22.3846, 103.4641],
    "Sơn La": [21.3259, 103.9126],
    "Yên Bái": [21.7167, 104.9167],
    "Hòa Bình": [20.8133, 105.3383],
    "Thái Nguyên": [21.5928, 105.8442],
    "Lạng Sơn": [21.8548, 106.7621],
    "Quảng Ninh": [21.0063, 107.5944],
    "Bắc Giang": [21.2731, 106.1947],
    "Phú Thọ": [21.3236, 105.2111],
    "Vĩnh Phúc": [21.3083, 105.6044],
    "Bắc Ninh": [21.1833, 106.0667],
    "Hải Dương": [20.9409, 106.3330],
    "TP. Hải Phòng": [20.8449, 106.6881],
    "Hưng Yên": [20.6500, 106.0500],
    "Thái Bình": [20.4464, 106.3364],
    "Hà Nam": [20.5422, 105.9208],
    "Nam Định": [20.4283, 106.1683],
    "Ninh Bình": [20.2539, 105.9750],
    "Thanh Hóa": [19.8000, 105.7667],
    "Nghệ An": [19.1667, 104.9167],
    "Hà Tĩnh": [18.3444, 105.9056],
    "Quảng Bình": [17.4833, 106.6000],
    "Quảng Trị": [16.8256, 107.1017],
    "Thừa Thiên Huế": [16.4637, 107.5908],
    "TP. Đà Nẵng": [16.0544, 108.2022],
    "Quảng Nam": [15.5667, 107.9833],
    "Quảng Ngãi": [15.1206, 108.8042],
    "Bình Định": [13.9358, 109.1350],
    "Phú Yên": [13.0883, 109.0928],
    "Khánh Hòa": [12.2500, 109.1833],
    "Ninh Thuận": [11.5667, 108.9833],
    "Bình Thuận": [11.0833, 108.0000],
    "Kon Tum": [14.3500, 108.0000],
    "Gia Lai": [13.9833, 108.0000],
    "Đắk Lắk": [12.6667, 108.0500],
    "Đắk Nông": [12.0000, 107.6667],
    "Lâm Đồng": [11.9464, 108.4419],
    "Bình Phước": [11.7500, 106.9167],
    "Tây Ninh": [11.3000, 106.1667],
    "Bình Dương": [11.1667, 106.6000],
    "Đồng Nai": [10.9500, 106.8167],
    "Bà Rịa - Vũng Tàu": [10.4914, 107.1706],
    "TP. Hồ Chí Minh": [10.8231, 106.6297],
    "Long An": [10.5333, 106.4000],
    "Tiền Giang": [10.3500, 106.3500],
    "Bến Tre": [10.2333, 106.3833],
    "Trà Vinh": [9.9333, 106.3333],
    "Vĩnh Long": [10.2500, 105.9667],
    "Đồng Tháp": [11.6083, 105.6167],
    "An Giang": [10.3833, 105.4333],
    "Kiên Giang": [10.0167, 105.0833],
    "TP. Cần Thơ": [10.0333, 105.7833],
    "Hậu Giang": [9.7833, 105.4667],
    "Sóc Trăng": [9.6000, 105.9667],
    "Bạc Liêu": [9.2833, 105.7167],
    "Cà Mau": [9.1833, 105.1500]
}

PROVINCE_REGIONS = [
    # 1) Miền / vùng
    "Miền Bắc", "Miền Trung", "Miền Nam",
    "Bắc Bộ", "Trung Bộ", "Nam Bộ",
    "Tây Bắc", "Đông Bắc", "Trung du", "Vùng núi",
    "Đồng bằng sông Hồng",
    "Bắc Trung Bộ", "Trung Trung Bộ", "Nam Trung Bộ", "Duyên hải Nam Trung Bộ",
    "Tây Nguyên",
    "Đông Nam Bộ", "Tây Nam Bộ", "Đồng bằng sông Cửu Long",
    "Ven biển", "Hải đảo", "Biên giới", "Miền Tây", "Miền Đông",

    # 2) Biển / vùng biển / vịnh lớn
    "Biển Đông", "Biển Tây",
    "Vịnh Bắc Bộ", "Vịnh Thái Lan",

    # 3) Vịnh / đầm / phá
    "Vịnh Hạ Long", "Vịnh Lan Hạ", "Vịnh Bái Tử Long",
    "Vịnh Lăng Cô", "Phá Tam Giang", "Đầm Cầu Hai",
    "Vịnh Chân Mây", "Vịnh Đà Nẵng",
    "Vịnh Dung Quất", "Vịnh Quy Nhơn", "Đầm Thị Nại",
    "Vịnh Vũng Rô", "Vịnh Xuân Đài", "Đầm Ô Loan",
    "Vịnh Nha Trang", "Vịnh Cam Ranh", "Vịnh Vân Phong",
    "Vịnh Gành Rái", "Vịnh Rạch Giá", "Vịnh Hà Tiên",

    # 4) Quần đảo / đảo / cụm đảo
    "Hoàng Sa", "Trường Sa",
    "Phú Quốc", "Côn Đảo", "Lý Sơn", "Cô Tô", "Cát Bà",
    "Thổ Chu", "Bạch Long Vĩ", "Nam Du",
    "Cù Lao Chàm", "Cù Lao Xanh", "Cù Lao Ré",
    "Hòn Tre", "Hòn Thơm", "Hòn Sơn", "Hòn Mun", "Hòn Tằm",
    "Hòn Nội", "Đảo Yến", "Điệp Sơn",
    "Quan Lạn", "Minh Châu",

    # 5) Mũi / đèo / hang-động / núi
    "Mũi Cà Mau", "Mũi Đại Lãnh", "Mũi Kê Gà", "Mũi Né",
    "Đèo Hải Vân", "Đèo Ô Quy Hồ", "Đèo Khau Phạ", "Đèo Pha Đin", "Đèo Cù Mông", "Đèo Mã Pí Lèng",
    "Động Phong Nha", "Động Thiên Đường", "Hang Sơn Đoòng", "Hang Én",
    "Fansipan", "Núi Bà Đen",

    # 6) Sông / hồ lớn
    "Sông Hồng", "Sông Đà", "Sông Lô", "Sông Mã", "Sông Cả", "Sông Gianh",
    "Sông Hương", "Sông Thu Bồn", "Sông Trà Khúc", "Sông Ba",
    "Sông Đồng Nai", "Sông Sài Gòn", "Sông Tiền", "Sông Hậu",
    "Vàm Cỏ Đông", "Vàm Cỏ Tây", "Sông Ngàn Phố", "Sông Cửa Long",
    "Hồ Ba Bể", "Hồ Thác Bà", "Hồ Hòa Bình", "Hồ Núi Cốc",
    "Hồ Trị An", "Hồ Dầu Tiếng", "Hồ Tuyền Lâm", "Hồ Tà Đùng",

    # 7) Vườn quốc gia / khu bảo tồn
    "Phong Nha - Kẻ Bàng", "Cúc Phương", "Ba Vì", "Bạch Mã",
    "Cát Tiên", "Tràm Chim", "U Minh Thượng", "U Minh Hạ",
    "Yok Đôn", "Chư Mom Ray", "Bidoup - Núi Bà", "Núi Chúa",
    "VQG Côn Đảo", "VQG Phú Quốc", "VQG Cát Bà",

    # 8) Địa danh / điểm du lịch (khác tên tỉnh/thành phố cấp tỉnh)
    "Sa Pa", "Bắc Hà", "Mù Cang Chải", "Tà Xùa", "Mộc Châu",
    "Tràng An", "Tam Cốc - Bích Động", "Tam Đảo",
    "Hạ Long", "Móng Cái", "Yên Tử",
    "Hội An", "Bà Nà", "Ngũ Hành Sơn", "Mỹ Sơn", "Lăng Cô",
    "Đồng Hới",
    "Đà Lạt", "Nha Trang", "Quy Nhơn", "Phan Thiết",
    "Hà Tiên", "Châu Đốc", "Sa Đéc", "Cần Giờ", "Đất Mũi",
    "Gành Đá Dĩa", "Thác Bản Giốc", "Thác Datanla", "Thác Pongour", "Thác Dray Nur",

    # 9) Alias hay gặp (phục vụ match)
    "TP.HCM", "TP HCM", "HCMC", "Sài Gòn", "Sai Gon",
    "Da Nang", "Phu Quoc", "Ha Long", "Huế", "Nha Trang", "Quy Nhơn", "Phan Thiết"
]


# Pre-compute compiled regexes for Provinces and Regions
PROVINCE_REGEXES = []
PROVINCE_TERM_MAP = {} # lower_variant -> province_name

def _extract_variants_to_map(names, prov_name):
    # Helper to add variants to the global map
    for n in names:
        PROVINCE_TERM_MAP[n.lower()] = prov_name

for name, variants in PROVINCE_MAPPING.items():
    _extract_variants_to_map(variants, name)
    PROVINCE_REGEXES.append({
        "name": name,
        "type": "province",
        "variants": variants,
    })

for reg in PROVINCE_REGIONS:
    PROVINCE_TERM_MAP[reg.lower()] = reg
    PROVINCE_REGEXES.append({
        "name": reg,
        "type": "region",
        "variants": [reg],
    })

def _build_mega_prov_re(is_accented=True):
    all_variants = []
    for k in PROVINCE_TERM_MAP.keys():
        # Escape and protect spaces
        esc = re.escape(k).replace(r"\ ", r"\s+")
        all_variants.append(esc)
    
    # Sort by length descending to ensure longest match wins (e.g. "TP. Hồ Chí Minh" before "Hồ Chí Minh")
    all_variants.sort(key=len, reverse=True)
    pattern = "|".join(all_variants)
    return re.compile(rf"\b({pattern})\b", re.IGNORECASE)

MEGA_PROVINCE_ACC_RE = _build_mega_prov_re(is_accented=True)

# Map for quick lookup of province attributes
PROVINCE_INFO_MAP = { item["name"]: item for item in PROVINCE_REGEXES }
# DISASTER RULES & PATTERNS


# High-priority keywords are now centralized in sources.py
# High-priority keywords are now centralized in sources.py
HIGH_PRIORITY_RE = sources.HIGH_PRIORITY_RE
MEDIUM_PRIORITY_RE = sources.MEDIUM_PRIORITY_RE



# DISASTER_CONTEXT, anchors, and priority maps are now imported from sources.py or compiled there.

ABSOLUTE_VETO = sources.ABSOLUTE_VETO
ABSOLUTE_VETO_RE = sources.ABSOLUTE_VETO_RE
DISASTER_CONTEXT = sources.DISASTER_CONTEXT
DISASTER_RULES = sources.DISASTER_RULES


# OPTIMIZATION: PRE-COMPILE REGEX
RE_FLAGS = re.IGNORECASE | re.VERBOSE | re.DOTALL

# Import helpers from sources to avoid duplication
v_safe = sources.v_safe
build_mega_re = sources.build_mega_re

# Pre-compute accented and unaccented patterns for high-performance matching
# Pre-compute accented patterns for high-performance matching
DISASTER_RULES_RE = []
for label, pats in DISASTER_RULES:
    # Sort patterns by length (descending) to ensure specific phrases (e.g. "heavy rain") 
    # are matched before generic ones (e.g. "rain") in the mega-regex.
    pats_sorted = sorted(pats, key=len, reverse=True)
    pats_v = [v_safe(p) for p in pats_sorted]
    
    # Create accented compiled list (fallback)
    compiled_acc = [re.compile(p, RE_FLAGS) for p in pats_v]
    
    # Attempt to also create a mega-regex for this label if possible
    try:
        mega_pattern = "|".join(f"(?:{p})" for p in pats_v)
        mega_acc = re.compile(mega_pattern, RE_FLAGS)
        compiled_acc = [mega_acc]
    except Exception as e:
        logger.warning(f"Failed to compile mega-regex for {label}, falling back to iterative. Error: {e}")
    
    # Only append accented versions
    DISASTER_RULES_RE.append((label, compiled_acc))

# HIGH_PRIORITY_RE is already imported from sources
# [OPTIMIZED] Whitelist Pattern for Pre-compilation
WHITELIST_RE = RE_CRITICAL_ACTIONS

# DISASTER_CONTEXT needs individual matching to identify specific context contributions
# [OPTIMIZATION] Use a single Mega-Regex for Context instead of iterating hundreds of patterns
# Sort by length to prioritize longer matches (e.g. "khắc phục hậu quả" > "khắc phục")
_context_sorted = sorted(DISASTER_CONTEXT, key=len, reverse=True)
# Wrap each pattern in non-capturing group to prevent precedence issues
_context_pattern = "|".join(f"(?:{v_safe(p)})" for p in _context_sorted)
DISASTER_CONTEXT_RE = re.compile(_context_pattern, RE_FLAGS)

# MEGA-REGEX for Source Keywords (Cleaned)
CLEAN_SOURCE_KEYWORDS = [kw.lower() for kw in SOURCE_DISASTER_KEYWORDS if kw.lower() not in AMBIGUOUS_KEYWORDS]

# Accented (All keywords)
CLEAN_SOURCE_KEYWORDS.sort(key=len, reverse=True)
SOURCE_KEYWORDS_ACC_RE = re.compile("|".join(re.escape(k) for k in CLEAN_SOURCE_KEYWORDS), RE_FLAGS)

# Sensitive Locations compiled list (Accented)
SENSITIVE_LOCATIONS_RE = sources.SENSITIVE_LOCATIONS_RE
INTERNATIONAL_LOCATIONS_RE = sources.INTERNATIONAL_LOCATIONS_RE

# Weight configuration (Externalize? No, keep here for simplicity)
logger.info("NLP regex compilation complete.")

# Build impact extraction patterns with named groups and qualifier support
def _build_impact_patterns():
    """
    Build regex patterns for extracting impact metrics.
    Uses regexes defined in IMPACT_KEYWORDS.
    Returns patterns_acc.
    """
    patterns_acc = {}

    for impact_type, data in IMPACT_KEYWORDS.items():
        regex_list = data.get("regex", [])
        patterns_acc[impact_type] = []
        for r_str in regex_list:
            try:
                # Accented version
                p_acc = re.compile(v_safe(r_str), RE_FLAGS)
                patterns_acc[impact_type].append(p_acc)
            except re.error as e:
                logger.error(f"Error compiling regex for {impact_type}: {r_str} -> {e}")

    return patterns_acc

IMPACT_PATTERNS = _build_impact_patterns()

# Weights (WEIGHT_RULE, WEIGHT_IMPACT, etc.) are now centralized in sources.py as SW.


# ESTIMATES & VALUE PARSING
SOFT_ESTIMATES = {
    "vài": (2, 5, True),
    "mấy": (3, 7, True),
    "nhiều": (5, 99, True),
    "chục": (10, 99, True),
    "hàng chục": (10, 99, True),
    "vài chục": (20, 50, True),
    "mấy chục": (30, 90, True),
    "trăm": (100, 999, True),
    "hàng trăm": (100, 999, True),
    "vài trăm": (200, 500, True),
    "mấy trăm": (300, 900, True),
    "nghìn": (1000, 9999, True),
    "ngàn": (1000, 9999, True),
    "hàng nghìn": (1000, 9999, True),
    "hàng ngàn": (1000, 9999, True),
    "vạn": (10000, 99999, True),
    "triệu": (1000000, 9999999, True),
    "hàng triệu": (1000000, 9999999, True),
    "tỷ": (1000000000, 9999999999, True),
    "tỉ": (1000000000, 9999999999, True),
    "hàng tỷ": (1000000000, 9999999999, True),
}

def _parse_unified_value(gd: dict) -> dict:
    """
    Parse a regex group dict into a standardized value object.
    Returns: {min, max, is_estimated, precision, source_text}
    """
    res = {"min": 0, "max": 0, "is_estimated": False, "precision": 0, "unit": gd.get("unit")}

    num_str = gd.get("num") or gd.get("num_soft") or ""
    qual_str = (gd.get("qualifier") or "").lower()

    # Clean and parse
    s = num_str.strip().lower()
    if not s: return res

    # 1. Hard Digits
    if any(c.isdigit() for c in s):
        res["precision"] = 10 # Highest priority
        
        # [REFINED] Smart normalization: 
        # Convert "1,5" to "1.5" if it looks like a decimal
        # Remove thousands separators if it looks like "1.000" or "1,000"
        s_clean = s
        if re.search(r"\d[.,]\d{1,2}(?!\d)", s):
            # Likely decimal (e.g. 1.5 or 1,50)
            s_clean = s.replace(",", ".")
        else:
            # Likely thousands separator or range
            s_clean = s.replace(".", "").replace(",", "")

        # Handle Ranges (e.g. 5-7)
        nums = re.findall(r"[\d.]+", s_clean)
        if len(nums) >= 2:
            try:
                res["min"] = float(nums[0])
                res["max"] = float(nums[1])
            except ValueError: pass
        elif nums:
            try:
                res["min"] = res["max"] = float(nums[0])
            except ValueError: pass

        # Apply Qualifiers
        if "ít nhất" in qual_str or "hơn" in qual_str or "trên" in qual_str:
            res["max"] = max(res["max"], res["min"] * 10) # Open upper bound
        elif "đóng" in qual_str or "khoảng" in qual_str or "gần" in qual_str:
            res["is_estimated"] = True

    # 2. Soft Words / Estimates
    elif s in SOFT_ESTIMATES:
        res["min"], res["max"], res["is_estimated"] = SOFT_ESTIMATES[s]
        res["precision"] = 5
    elif s in NUMBER_WORDS:
        v = NUMBER_WORDS[s]
        res["min"] = res["max"] = v
        res["precision"] = 8 # Word numbers are better than estimates

    return res

def _to_int(num_str: str) -> int:
    """Legacy helper, use _parse_unified_value for impact."""
    if not num_str: return 0
    s = str(num_str).strip().lower()
    if re.match(r"^\d+$", s): return int(s)
    if s in NUMBER_WORDS: return int(NUMBER_WORDS[s])
    s2 = s.replace(".", "").replace(",", "")
    if s2.isdigit(): return int(s2)
    return 0
# CORE LOGIC

# Pre-compile regexes for performance
# This ensures we don't re-compile thousands of patterns per article check



def extract_provinces(text: str, title: str = "", impact_spans: List[tuple] = None, t_acc: str = None, t_title_acc: str = None) -> List[dict]:
    """
    EXTRACT FOCUS PROVINCES (Heuristic Logic)
    1. If impacts exist, prioritize provinces in ±1 sentence window.
    2. If broadcast/forecast, prioritize title locations or high frequency.
    """
    if not text: return []

    # Unicode Normalization (Only done if not passed in)
    if t_acc is None:
        t_acc, _ = risk_lookup.canon(text or "")
        
    t = t_acc
    
    # We need t_orig for casing/proper noun check
    # risk_lookup.canon returns lowercase. We need original text for IsUpper check.
    # We will assume `text` passed in is the original raw text.
    
    # Pre-process Title
    t_tit_acc = t_title_acc
    
    if (t_tit_acc is None) and title:
        t_tit_acc, _ = risk_lookup.canon(title)
        
    if t_tit_acc is None: t_tit_acc = ""
    
    # [FIX] Align t_orig with t_acc (NFC + Whitespace Collapsing) to ensure indices match for casing check
    # We perform same steps as canon() but skip .lower() to preserve case
    if text:
        t_orig = unicodedata.normalize("NFC", text)
        t_orig = t_orig.replace("–", "-").replace("—", "-").replace("−", "-")
        t_orig = re.sub(r"\s+", " ", t_orig).strip()
    else:
        t_orig = ""

    # 1. Raw Extraction
    raw_hits = []
    # OPTIMIZATION: Use Mega-Regex for all provinces at once
    for m in MEGA_PROVINCE_ACC_RE.finditer(t):
        found_term = m.group(1).lower()
        prov_name = PROVINCE_TERM_MAP.get(found_term)
        if not prov_name: continue
        
        info = PROVINCE_INFO_MAP.get(prov_name)
        if not info: continue

        # Case-sensitive check for Proper Noun
        start, end = m.span()
        original_segment = t_orig[start:end]
        is_proper = original_segment[0].isupper() if original_segment else False
        
        raw_hits.append({
            "name": info["name"],
            "type": info["type"],
            "span": (start, end),
            "is_proper": is_proper
        })

    if not raw_hits: return []

    # 2. Heuristic: Sentence Splitting
    # Split text into sentences and map spans to sentence index
    sentences = RE_SENTENCE_SPLIT.split(t_orig)
    sentence_spans = []
    curr = 0
    for s in sentences:
        sentence_spans.append((curr, curr + len(s)))
        curr += len(s) + 1 # +1 for the space

    def get_sent_idx(char_idx):
        for i, (s, e) in enumerate(sentence_spans):
            if s <= char_idx <= e: return i
        return -1

    # 3. Apply Heuristics
    focus_provinces = []

    # H1: Proximity to Impact (±1 Sentence)
    if impact_spans:
        impact_sent_indices = set()
        for i_s, i_e in impact_spans:
            idx = get_sent_idx(i_s)
            if idx != -1:
                impact_sent_indices.add(idx)
                impact_sent_indices.add(idx - 1)
                impact_sent_indices.add(idx + 1)

        for h in raw_hits:
            h_sent = get_sent_idx(h["span"][0])
            if h_sent in impact_sent_indices:
                focus_provinces.append(h)

    # H2: Title Match (Strategic Positioning)
    title_locations = set()
    title_items = []
    if title:
        for m in MEGA_PROVINCE_ACC_RE.finditer(t_tit_acc):
            found_term = m.group(1).lower()
            prov_name = PROVINCE_TERM_MAP.get(found_term)
            if prov_name and prov_name not in title_locations:
                title_locations.add(prov_name)
                title_items.append(PROVINCE_INFO_MAP[prov_name])

    # 4. Filter and Prioritize
    # Start with raw hits
    candidates = raw_hits[:]
    
    # Inject Title Matches if missing from raw_hits (Text body)
    existing_names = {h["name"] for h in candidates}
    for item in title_items:
        if item["name"] not in existing_names:
            candidates.append({
                "name": item["name"],
                "type": item["type"],
                "span": (-1, -1), # Synthetic span
                "is_proper": True
            })
            existing_names.add(item["name"])

    # Define Relevance Scoring
    # Priority: 
    # 1. In Title (Score 0)
    # 2. In Focus Sentence (Score 1)
    # 3. Frequency (Score 2 - implicit by sorting)
    
    scored_candidates = []
    for h in candidates:
        score = 2 # Default: Low priority
        
        # Check Title
        if h["name"] in title_locations:
            score = 0
            
        # Check Focus (if Score not already 0)
        elif focus_provinces and any(h["name"] == p["name"] for p in focus_provinces):
            score = 1
            
        scored_candidates.append((score, h))

    # Sort: Score Ascending, then Span Start Ascending
    scored_candidates.sort(key=lambda x: (x[0], x[1]["span"][0]))

    # Filter logic:
    # If we have matches with Score 0 or 1, keep them.
    # If not, fallback to Top 3 frequency.
    
    high_prio = [x[1] for x in scored_candidates if x[0] <= 1]
    
    if high_prio:
        return high_prio
        
    # H3: Frequency (Top-3) - Fallback
    freq = {}
    for h in raw_hits: # Use original raw_hits for frequency to avoid bias
        freq[h["name"]] = freq.get(h["name"], 0) + (2 if h["is_proper"] else 1)

    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    top_3_names = {name for name, count in sorted_freq[:3]}
    
    # Return candidates that are in top 3
    return [h for h in candidates if h["name"] in top_3_names]

def match_disaster_rules(t_acc: str, t_title_acc: str) -> tuple[list, dict, dict, bool]:
    """Helper: Matches disaster rules against text/title on Accented channel only."""
    rule_matches = []
    hazard_counts = {}
    hazard_weights = {}
    title_rule_match = False

    for label, compiled_acc in DISASTER_RULES_RE:
        count = 0
        weight = 0
        
        # compiled_acc is a list [mega_re] or [re1, re2...]
        for pat_re in compiled_acc:
            # Check Title First (Weight 3)
            if t_title_acc and pat_re.search(t_title_acc):
                weight += 3
                title_rule_match = True
            
            # Check Body (Weight 1)
            # Optimization: use findall for count if we don't need spans
            m_body = pat_re.findall(t_acc)
            if m_body:
                count += len(m_body)
                weight += len(m_body)

        if weight > 0:
            rule_matches.append(label)
            hazard_counts[label] = count
            hazard_weights[label] = weight
            
    return rule_matches, hazard_counts, hazard_weights, title_rule_match

def check_veto_status(t_acc: str, t_title_acc: str, has_hazard: bool) -> tuple[bool, bool, bool, list]:
    """Helper: Checks Absolute, Conditional, and Soft vetoes using Mega-Regexes."""
    absolute_veto = False
    conditional_veto = False
    soft_negative = False
    negative_matches = []

    # 1. Absolute Veto
    # 1. Absolute Veto
    # [OPTIMIZED] Whitelist / Bypass Veto Check
    is_whitelisted = False
    if WHITELIST_RE.search(t_acc):
        is_whitelisted = True
    elif t_title_acc and WHITELIST_RE.search(t_title_acc):
        is_whitelisted = True

    if not is_whitelisted and ABSOLUTE_VETO_RE and ABSOLUTE_VETO_RE.search(t_acc):
        in_title = t_title_acc and ABSOLUTE_VETO_RE.search(t_title_acc)
        if in_title or not has_hazard:
            absolute_veto = True
            negative_matches.append("ABSOLUTE_VETO_MATCH")
    
    if absolute_veto:
        return True, False, False, negative_matches, is_whitelisted

    # 2. Conditional Veto
    # 2. Conditional Veto
    if not is_whitelisted and CONDITIONAL_VETO_RE and CONDITIONAL_VETO_RE.search(t_acc):
        conditional_veto = True
        negative_matches.append("CONDITIONAL_VETO_MATCH")

    # 3. Soft Negative
    # 3. Soft Negative
    if not is_whitelisted and SOFT_NEGATIVE_RE and SOFT_NEGATIVE_RE.search(t_acc):
        soft_negative = True
        negative_matches.append("SOFT_NEGATIVE_MATCH")

    return absolute_veto, conditional_veto, soft_negative, negative_matches, is_whitelisted

def extract_province(text: str, title: str = "", t_acc: str = None) -> str:
    """Legacy wrapper: returns the Single Best province found.
    Prioritizes specific Province over Region.
    """
    # Note: Legacy wrapper doesn't pass t_title_acc, so it will re-calc if title present.
    all_hits = extract_provinces(text, title=title, t_acc=t_acc)

    # 1. Return first specific province
    for h in all_hits:
        if h["type"] == "province":
            return h["name"]

    # 2. Return first region
    for h in all_hits:
        if h["type"] == "region":
            return h["name"]

    return "unknown"

def extract_disaster_metrics(text: str, t_acc: str = None) -> dict:
    """
    Extracts numerical metrics (wind speed, rainfall, quake mag) directly using regex.
    Optimized to use pre-normalized text inputs.
    """
    metrics = {}
    if t_acc is None:
        t_acc, _ = risk_lookup.canon(text or "")
        
    t = t_acc # Lowercase normalized

    # 1. Rainfall (mm) - Inlined from risk_lookup
    cand_mm = []
    # range mm: 100-200mm
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand_mm.append(float(m.group(2).replace(",", ".")))
    # single mm: 150mm
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mm\b", t, flags=re.IGNORECASE):
        cand_mm.append(float(m.group(1).replace(",", ".")))
    # L/m2
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:l|lit|lít)\s*/\s*m\s*(?:2|\^2)\b", t, flags=re.IGNORECASE):
        cand_mm.append(float(m.group(1).replace(",", ".")))
        
    if cand_mm: metrics["rainfall_mm"] = max(cand_mm)

    # 2. Temperature (C)
    cand_temp = []
    UNIT_T = r"(?:°\s*c)"
    # Try with t for °C
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + UNIT_T, t, re.IGNORECASE):
         cand_temp.append(float(m.group(2).replace(",", ".")))
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_T, t, re.IGNORECASE):
         cand_temp.append(float(m.group(1).replace(",", ".")))
         
    if cand_temp: metrics["temperature_c"] = max(cand_temp)

    # 3. Salinity (per mille)
    cand_salt = []
    UNIT_S = r"(?:‰|psu|ppt)"
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*" + UNIT_S, t, re.IGNORECASE):
         cand_salt.append(float(m.group(1).replace(",", ".")))
    if cand_salt: metrics["salinity_per_mille"] = max(cand_salt)

    # 4. Wind (Beaufort) - Inlined & Simplified
    vals_wind = []
    vals_gust = []
    
    # cấp/cap X (exclude 'khẩn cấp', 'phụ cấp', and 'giật')
    # Support both accented and unaccented variations
    # Refactored to avoid lookbehind errors and handle ranges (cap 10-11)
    for m in re.finditer(r"(?:(khan|khẩn|phụ|phu|giat|giật)\s+)?(?:cấp|cap)\s*(\d{1,2})(?:\s*(?:-|đến|tới)\s*(\d{1,2}))?\b(?!\s*%)", t, flags=re.IGNORECASE):
        if m.group(1): continue # Block 'khẩn cấp', 'phụ cấp', 'giật cấp'
        a = int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a # Use group 3 for range end
        vals_wind.append(max(a, b))
        
    # Roman numerals (sustained)
    for m in re.finditer(r"(?:cấp|cap)\s*([ivx]{1,5})\b", t, flags=re.IGNORECASE):
        r = risk_lookup._roman_to_int(m.group(1))
        if r is not None: vals_wind.append(r)
        
    # giật cấp ...
    for m in re.finditer(r"(?:giật|giat)\s*(?:cap|cấp)?\s*(\d{1,2})(?:\s*(?:-|,|đến|tới|den|toi)\s*(\d{1,2}))?", t):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        vals_gust.append(max(a, b))
        
    # m/s -> Beaufort (sustained)
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*m\s*/\s*s\b", t, flags=re.IGNORECASE):
        ms = float(m.group(1).replace(",", "."))
        vals_wind.append(risk_lookup.kmh_to_beaufort(ms * 3.6))

    if ("siêu bão" in t) or ("sieu bao" in t): vals_wind.append(16)
    
    if vals_wind: metrics["wind_level"] = max(vals_wind)
    if vals_gust: metrics["wind_gust"] = max(vals_gust)

    # 5. Water Level (m)
    # Logic: Search for keywords + number + unit m/cm
    # Updated to include accented keywords
    CTX_WL = r"(?:mực\s*nước|nước\s*dâng|ngập|độ\s*sâu|đỉnh\s*lũ|báo\s*động|muc\s*nuoc|nuoc\s*dang|do\s*sau|dinh\s*lu|bao\s*dong)"
    m_wl = re.search(CTX_WL + r"[^0-9]{0,50}\s+(\d+(?:[.,]\d+)?)(?:\s*(?:-|đến|tới|den)\s*(\d+(?:[.,]\d+)?))?\s*(m|mét|met|cm)\b(?!\s*/)", t, re.IGNORECASE)
    if m_wl:
        v1 = float(m_wl.group(1).replace(",", "."))
        v2 = float(m_wl.group(2).replace(",", ".")) if m_wl.group(2) else v1
        val_wl = max(v1, v2)
        if "cm" in m_wl.group(3).lower(): val_wl /= 100.0
        metrics["water_level_m"] = val_wl

    # 6. Duration
    # Quick heuristics from risk_lookup
    m_dur = re.search(r"trong\s*(\d{1,2})\s*(?:ngày|ngay)", t)
    if m_dur: metrics["duration_days"] = float(m_dur.group(1))
    elif any(kw in t for kw in ["nhiều ngày", "dài ngày", "nhieu ngay", "dai ngay"]):
        metrics["duration_days"] = 3.0

    # 7. Earthquake (Magnitude)
    m_quake = re.search(r"\b(?:mw|ml|m)\s*(\d+(?:[.,]\d+)?)\b", t, re.IGNORECASE)
    if m_quake: 
        metrics["earthquake_magnitude"] = float(m_quake.group(1).replace(",", "."))
    elif re.search(r"(?:động\s*đất|chấn\s*động|địa\s*chấn|dong\s*dat|chan\s*dong|dia\s*chan)", t):
        # Support "5.2 do richter" or "5.2 richter" or "5,2 do"
        m_q2 = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:do|độ)?\s*(?:richter|m|mw|ml)\b", t, re.IGNORECASE)
        if m_q2: metrics["earthquake_magnitude"] = float(m_q2.group(1).replace(",", "."))

    return metrics

def compute_disaster_signals(text: str, title: str = "", trusted_source: bool = False, authority_level: int = 1, t_acc: str = None) -> dict:
    # 1. Standardize Normalization using risk_lookup.canon (Provides Two Channels)
    # Combine title for search if not already in text
    search_text = f"{title}\n{text}" if title and title not in text else text
    
    if t_acc is None:
        t_acc, _ = risk_lookup.canon(search_text or "")
        
    # We also need title separate for rule matching weights
    t_title_acc, _ = risk_lookup.canon(title or "")

    # Helper 1: Disaster Rules
    rule_matches, hazard_counts, hazard_weights, title_rule_match = match_disaster_rules(t_acc, t_title_acc)

    # VIP Term Detection (Immediate Pass Boost)
    is_vip = False
    if (t_title_acc and sources.VIP_TERMS_RE.search(t_title_acc)) or (t_acc and sources.VIP_TERMS_RE.search(t_acc)):
        is_vip = True

    # Helper 2: Negative Checks (Absolute/Conditional/Soft Vetoes)
    absolute_veto, conditional_veto, soft_negative, negative_matches, is_whitelisted = check_veto_status(
        t_acc, t_title_acc, has_hazard=(len(rule_matches) > 0)
    )

    # 2. Hazard (Rule) Match - Category identification
    hazard_found = len(rule_matches) > 0
    rule_score = SW["weight_rule"] if hazard_found else 0.0
    
    # [OPTIMIZATION] Multi-Hazard Bonus: If article mentions multiple categories (e.g. Storm + Flood)
    if len(rule_matches) >= 2:
        rule_score += SW["multi_hazard_bonus"]
        if len(rule_matches) >= 3:
            rule_score += SW["triple_hazard_bonus"]

    # [OPTIMIZATION] High-Priority Keyword Boost
    if HIGH_PRIORITY_RE and HIGH_PRIORITY_RE.search(t_acc):
        rule_score += SW["high_priority_boost"]

    if MEDIUM_PRIORITY_RE and MEDIUM_PRIORITY_RE.search(t_acc):
        rule_score += SW["medium_priority_boost"]

    # [OPTIMIZATION] Risk Level Bonus
    risk_match = RISK_LEVEL_RE.search(t_acc)
    if risk_match:
        level_str = risk_match.group(1).upper()
        # Convert Roman to digit if needed
        level = 0
        if level_str in ["1", "I"]: level = 1
        elif level_str in ["2", "II"]: level = 2
        elif level_str in ["3", "III"]: level = 3
        elif level_str in ["4", "IV"]: level = 4
        elif level_str in ["5", "V"]: level = 5
        
        if level >= 3: rule_score += SW["risk_level_high_boost"]
        elif level >= 1: rule_score += SW["risk_level_low_boost"]

    # [OPTIMIZATION] Title Boost: If hazard keyword in title, add bonus
    if title_rule_match:
        rule_score += SW["title_hazard_boost"]

    # 2. Impact Match - Deaths, missing, or significant damage/metrics
    # REFINED: Use extracted objects to determine impact_score
    raw_details = extract_impact_details(text, t_acc=t_acc)

    # We define impact_found if any typed list in raw_details is non-empty
    impact_found = any(len(lst) > 0 for lst in raw_details.values())

    metrics = extract_disaster_metrics(text, t_acc=t_acc)
    real_metrics_found = any(k != "duration_days" for k in metrics.keys())

    # Impact score is fixed if ANY major impact sign is found after negation-filtering
    impact_score = SW["weight_impact"] if (impact_found or real_metrics_found) else 0.0

    # Determine event stage using impact signals for priority
    event_stage = determine_event_stage(search_text, impact_detected=impact_found)

    # [OPTIMIZATION] Stage Bonus: Help recovery/aid news reach approval
    stage_bonus = 0.0
    if event_stage == "RECOVERY":
        stage_bonus += SW["stage_recovery_bonus"]
    elif event_stage == "FORECAST":
        stage_bonus += SW["stage_forecast_bonus"]

    # [OPTIMIZATION] Magnitude Scaling: Bonus for extreme values
    extreme_bonus = stage_bonus
    if metrics.get("rainfall_mm", 0) >= 150: extreme_bonus += SW["extreme_rainfall_150_bonus"]
    if metrics.get("rainfall_mm", 0) >= 300: extreme_bonus += SW["extreme_rainfall_300_bonus"]
    if metrics.get("wind_level", 0) >= 12: extreme_bonus += SW["extreme_wind_bonus"]
    if metrics.get("earthquake_magnitude", 0) >= 6.0: extreme_bonus += SW["extreme_quake_bonus"]
    
    # Note: raw_details contains dicts, need to extract max. Using d_count/m_count:
    d_count = sum(d["max"] for d in raw_details.get("deaths", []))
    m_count = sum(m["max"] for m in raw_details.get("missing", []))
    if (d_count + m_count) >= 5: extreme_bonus += SW["high_casualty_threshold_boost"]
    
    impact_score += extreme_bonus

    # 3. Agency Match - Official source/agency
    agency_match = bool(RE_AGENCY.search(t_acc))
    agency_score = SW["weight_agency"] if agency_match else 0.0

    # 4. Location Match - Province, Region, or Sensitive Location
    # Pass impact spans to focus on relevant provinces
    all_impact_spans = []
    for typed_impacts in raw_details.values():
        for item in typed_impacts:
            all_impact_spans.append(item["span"])

    prov_hits = extract_provinces(text, title=title, impact_spans=all_impact_spans, t_acc=t_acc, t_title_acc=t_title_acc)

    # Location Score: 2.0 base + 0.5 bonus if it's a Proper Noun (Uppercase)
    location_found = len(prov_hits) > 0
    sensitive_hits = sources.SENSITIVE_LOCATIONS_RE.findall(t_acc)
    location_found = location_found or len(sensitive_hits) > 0

    # International Locations Check
    international_hits = sources.INTERNATIONAL_LOCATIONS_RE.findall(t_acc)
    
    # [FIX] Add Case-Sensitive Check for Risky Short Names (Mỹ, Anh, Pháp...)
    # Must use original 'text' because t_acc is lowercased. Normalize to NFC for consistent matching.
    text_nfc = unicodedata.normalize("NFC", text) if text else ""
    international_hits_cs = sources.INTERNATIONAL_LOCATIONS_CS_RE.findall(text_nfc)
    international_hits.extend(international_hits_cs)

    # [OPTIMIZATION] Strategic Location Boost: Bonus for dams, passes, etc.
    sensitive_bonus = 1.0 if sensitive_hits else 0.0

    # Proper Noun Boost (Strictness adjustment)
    title_has_geo = False
    # Determine best province
    best_prov = "unknown"
    for h in prov_hits:
        if h["type"] == "province":
            best_prov = h["name"]
            break
    if best_prov == "unknown":
        for h in prov_hits:
            if h["type"] == "region":
                best_prov = h["name"]
                break

    if best_prov != "unknown":
        # Check if this best_prov matches something in the title
        # best_prov comes from prov_hits which prioritizes title matches (H2: Title Match)
        if best_prov.lower() in (t_title_acc or ""):
            title_has_geo = True

    proper_boost = 0.0
    if any(h.get("is_proper") for h in prov_hits):
        proper_boost = 1.0 # Base boost for proper noun
        if title_has_geo:
            proper_boost = 1.5 # Extra boost if proper noun is in title
            
    province_score = (SW["weight_province"] if location_found else 0.0) + proper_boost + sensitive_bonus

    best_prov = "unknown"
    for h in prov_hits:
        if h["type"] == "province": best_prov = h["name"]; break
    if best_prov == "unknown":
        for h in prov_hits:
            if h["type"] == "region": best_prov = h["name"]; break
    if best_prov == "unknown" and sensitive_hits:
        best_prov = sensitive_hits[0]

    # 5. Source Keywords Match - Density of relevant words (Two-Channel Optimized)
    # Match both channels and union the results
    non_ambiguous_hits = set(SOURCE_KEYWORDS_ACC_RE.findall(t_acc))
    
    source_score = min(SW["weight_source_max"], float(len(non_ambiguous_hits)) * SW["weight_source"])

    # [OPTIMIZATION] Authority Boost: Scale points based on source tier
    # Level 1: Standard (0.0)
    # Level 2: Trusted (1.5)
    # Level 3: High Authority / Gov (4.0) - Replaces common 3.0+ user request
    authority_bonus = 0.0
    if not soft_negative:
        if authority_level >= 3:
            authority_bonus = SW["authority_level_high_bonus"]
        elif authority_level == 2 or trusted_source:
            authority_bonus = SW["authority_level_med_bonus"]

    # Context Matches (Optimized)
    context_hits = list(set(DISASTER_CONTEXT_RE.findall(t_acc)))

    # UNIFIED CONFIDENCE SCORE
    # Add context bonus
    context_bonus = min(SW["context_max_bonus"], len(context_hits) * SW["context_hit_weight"])
    
    # [OPTIMIZATION] Gold Standard Boost (Refined)
    gold_boost = 0.0
    
    if rule_score > 0 and title_has_geo:
        gold_boost += SW["gold_title_geo_boost"]
        
    # Condition B: TRUSTED WARNING (Official Sources emitting Warnings)
    if trusted_source and (event_stage == "FORECAST" or sources.RE_FORECAST.search(t_title_acc)):
        gold_boost += SW["gold_trusted_warning"]
        
    # Condition C: STANDARD GOLD (High Reliability Combo)
    if rule_score > 0 and (province_score > 0 or sensitive_bonus > 0):
        if (impact_found or real_metrics_found):
             if agency_match or authority_bonus > 0 or trusted_source:
                  gold_boost += SW["gold_standard_high"]
             else:
                  gold_boost += SW["gold_standard_med"]
        elif trusted_source:
             gold_boost += SW["gold_trusted_breaking"]
             
    score = rule_score + impact_score + agency_score + source_score + province_score + authority_bonus + context_bonus + gold_boost
    
    # [CRITICAL] VIP Boost
    if is_vip:
        score += SW["vip_boost"]

    # [OPTIMIZATION] Title Inconsistency Penalty: 
    major_hazard_titles = ["bão", "siêu bão", "lũ ống", "lũ quét", "ngập sâu", "sạt lở"]
    if any(kh in (title or "").lower() for kh in major_hazard_titles):
        # Skip this penalty for recovery articles as they are justified in mentioning the hazard in title
        if not (impact_found or real_metrics_found) and event_stage != "RECOVERY":
            score += SW["penalty_title_clickbait"]
            
    # [OPTIMIZATION] Silent Hazard Boost: If high impact is found in title even without hazard rule match
    if rule_score == 0.0:
        title_impact_low = (title or "").lower()
        # Look for physical damage markers often omitted from hazard lists
        if re.search(r"\b(?:sập|đổ|cuốn\s*trôi|vùi\s*lấp|hư\s*hỏng\s*nặng|thương\s*vong|mất\s*tích|chết|tử\s*vong|nạn\s*nhân|lật\s*thuyền|lật\s*tàu)\b", title_impact_low):
            score += SW["silent_hazard_title_boost"]
            
    # [OPTIMIZATION] Title Action Boost
    if (title or "").strip():
        title_low = title.lower()
        if re.search(r"\b(?:di\s*dời|sơ\s*tán|di\s*tản|cứu\s*trợ|tiếp\s*tế|thư\s*kêu\s*gọi|chiến\s*dịch\s*quang\s*trung)\b", title_low):
            score += SW["title_action_boost"]

    # [OPTIMIZATION] Penalty for No Hazard Rule Match
    if rule_score == 0.0:
        total_casualties = d_count + m_count
        if total_casualties == 0:
            score += SW["penalty_no_hazard"]
        elif total_casualties >= 5:
            score += SW["high_casualty_boost"]
        else:
            score += SW["penalty_ambiguous"]
    
    # [FIX] Conditional Veto Penalty
    if conditional_veto and rule_score == 0.0:
        score += SW["penalty_cond_veto"]
        
    # [OPTIMIZATION] International News Filter
    # If article mentions international locations (e.g. Philippines, Japan) but NO Vietnamese location/region
    # We deprioritize it heavily unless it explicitly mentions "Biển Đông" (covered by Storm rules) or "Việt Nam"
    # Note: location_found = (prov_hits OR sensitive_hits)
    if len(international_hits) > 0 and not location_found:
        # Check for explicit "Việt Nam" or "Biển Đông" or "Bão số" mention
        # "Bão số" implies a Vietnamese named storm (e.g. Bão số 3)
        bypass_international = False
        # [UPDATED] Expanded list to allow International Disasters & Aid to pass as per user request
        bypass_keywords = [
            "việt nam", "viet nam", "biển đông", "bão số", 
            "mưa", "ngập", "lũ", "lụt", "sạt lở", "đất đá", 
            "động đất", "sóng thần", "bão", "áp thấp", "lốc xoáy", "vòi rồng",
            "hạn hán", "xâm nhập mặn", "cháy rừng", "nắng nóng", "rét hại", "băng giá",
            "hỗ trợ", "viện trợ", "cứu trợ", "ủng hộ", "khắc phục", "tài trợ"
        ]
        if any(kw in t_acc for kw in bypass_keywords):
            bypass_international = True
        
        # Check for Neighbor Countries (Lào, Cam, etc.) - Apply reduced penalty
        is_neighbor = False
        neighbor_set = {n.lower() for n in sources.NEIGHBOR_COUNTRIES}
        if any(h in neighbor_set for h in international_hits):
            is_neighbor = True

        if not bypass_international:
             if is_neighbor:
                 score += SW.get("penalty_neighbor_country", -4.0)
             else:
                 score += SW["penalty_international"]
    
    if score < 0: score = 0.0
    
    # [OPTIMIZATION] Drill / Exercise / Sports Penalty
    # We penalize training/drills unless it has massive hazard signals (rare)
    if re.search(r"\b(?:diễn\s*tập|thực\s*binh|luyện\s*tập|thực\s*tập|hội\s*thao|hội\s*thi|thể\s*thao|giải\s*chạy|đua\s*xe)\b", t_acc):
        score += SW["penalty_drill_exercise"]
        if score < 0: score = 0.0

    # [OPTIMIZATION] Soft Negative Penalty: Significant reduction for ambiguous noise
    if soft_negative:
        score += SW["penalty_soft_negative"]
        if score < 0: score = 0.0
    
    # [OPTIMIZATION] Whitelist Score Boost: 
    # If article is whitelisted (critical actions like xả lũ), boost it highly
    if is_whitelisted:
        score += SW.get("whitelist_boost", 10.0)

    # [CRITICAL] Absolute Veto Override
    # If absolute veto is triggered (and not whitelisted), the score MUST be 0
    # to prevent accidental approval by aggregators ignoring the flag.
    if absolute_veto:
        score = 0.0

    context_score = context_bonus


    impact_details = raw_details # Re-use already extracted details

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_found or real_metrics_found,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": rule_score,
        "hazard_counts": hazard_counts,
        "hazard_weights": hazard_weights,
        "context_score": context_score,
        "sensitive_locations": sensitive_hits,
        "absolute_veto": absolute_veto,
        "conditional_veto": conditional_veto,
        "hard_negative": absolute_veto, # Legacy compat
        "soft_negative": soft_negative,
        "negative_hit": negative_matches,
        "is_whitelisted": is_whitelisted,
        "is_vip": is_vip,
        "metrics": metrics,
        "impact_details": impact_details,
        "is_province_match": best_prov != "unknown",
        "is_agency_match": agency_match is not None,
        "is_sensitive_location": len(sensitive_hits) > 0,
        "is_international": len(international_hits) > 0,
        "stage": event_stage # Add the detected stage
    }

def determine_event_stage(text: str, impact_detected: bool = False, t_acc: str = None) -> str:
    """
    Classify event stage: FORECAST, INCIDENT, or RECOVERY.
    Uses keyword density/scoring for robustness.
    """
    t_lower = t_acc if t_acc else (text or "").lower()
    scores = {"FORECAST": 0, "INCIDENT": 0, "RECOVERY": 0}

    # 1. Check Recovery (High weight for specific terms)
    if sources.RE_RECOVERY.search(t_lower): scores["RECOVERY"] += 2

    # 2. Check Forecast/Warning
    if sources.RE_FORECAST.search(t_lower): scores["FORECAST"] += 2

    # 3. Check Incident (Happening/Happened)
    if sources.RE_INCIDENT.search(t_lower): scores["INCIDENT"] += 2

    # [OPTIMIZATION] Impact Priority: If real impact (deaths/missing) is mentioned,
    # it's almost certainly an INCIDENT or RECOVERY, even if the article title says "Forecast".
    if impact_detected:
        if scores["RECOVERY"] > 0:
            return "RECOVERY"
        return "INCIDENT"

    # Selection
    max_score = max(scores.values())
    if max_score == 0: return "INCIDENT" # Default to incident if matches are vague

    # Final decision
    if scores["RECOVERY"] >= 2 and scores["RECOVERY"] >= scores["INCIDENT"]:
        return "RECOVERY"
    if scores["FORECAST"] >= 2 and scores["FORECAST"] >= scores["INCIDENT"]:
        return "FORECAST"

    return "INCIDENT"


def contains_disaster_keywords(text: str, title: str = "", trusted_source: bool = False, authority_level: int = 1) -> bool:
    """
    Stricter Filtering (v4):
    - Separate Title and Body context.
    - Block diplomatic/admin noise.
    - Veto metaphors and social news aggressively.
    """
    # Use full text for signal detection but remember title importance
    full_text = f"{title}\n{text}" if title else text
    t, _ = risk_lookup.canon(full_text)
    title_lower = title.lower() if title else ""
    
    # 0. VIP Whitelist (Critical Warnings/Aid that bypass ALL filters)
    if sources.VIP_TERMS_RE:
        if title and sources.VIP_TERMS_RE.search(title): return True
        if sources.VIP_TERMS_RE.search(text): return True

    # 0.1. DEFINITIVE EVENTS PASS (Strong Identifiers in Title)
    if title:
        # Named Storms, Cold Waves, Heat Waves, Quakes, Tsunamis, Landslides
        if re.search(r"(?:bão|áp\s*thấp).*?(?:số\s*\d+|[A-ZĐ][a-zà-ỹ]+)", title): return True
        # Use new tiered priority REs for consistent and high-quality title bypass
        if HIGH_PRIORITY_RE.search(title_lower): return True
        if MEDIUM_PRIORITY_RE.search(title_lower): return True
        # Official Bulletins
        if re.search(r"(?:bản)?\s*tin\s*(?:dự\s*báo|cảnh\s*báo|khí\s*tượng|thủy\s*văn|hải\s*văn|khẩn\s*cấp)", title_lower, re.IGNORECASE): return True
        if "đài khí tượng" in title_lower or "trung tâm dự báo" in title_lower: return True

    # Calculate final signals and score
    sig = compute_disaster_signals(text, title=title, trusted_source=trusted_source, authority_level=authority_level, t_acc=t)
    
    if sig["absolute_veto"]:
        return False

    # 1.5. CONDITIONAL VETO (Context-Aware Reject)
    # If a conditional veto pattern matches (e.g., "fire", "traffic accident")
    # AND there is NO specific hazard rule match (hazard_score == 0), REJECT.
    # This prevents noise like "house fire" or "car crash" from passing simply due to high source/province scores.
    if sig["conditional_veto"] and sig["hazard_score"] == 0:
        return False

    # 1.6. COMBO REQUIREMENT: (Hazard + Location) OR (Impact)
    # This prevents purely administrative News or general Forecasts with NO location from passing.
    has_hazard = sig["hazard_score"] > 0
    has_location = sig["is_province_match"] or sig["is_sensitive_location"] or sig["is_international"]
    has_impact = sig["impact_hits"]

    # Articles must have (Hazard AND Location) OR (Impact) to be considered
    # Unless it was a Definitive Event, VIP, or High-Confidence Metric
    # [OPTIMIZATION] Also allow (Hazard AND Forecast/Warning) even without explicit location
    # This catches "Toàn quốc cảnh báo nắng nóng" or "Dự báo áp thấp nhiệt đới"
    is_forecast_warning = sig["stage"] == "FORECAST" or sig["stage"] == "WARNING" or RE_WARNING_TITLE.search(title_lower)
    
    # [FIX] Allow strong metrics (rainfall, wind, quake) or Whitelist match to bypass location check
    is_strong_evidence = sig["impact_hits"] or sig["is_whitelisted"]
    
    if not (is_strong_evidence or (has_hazard and has_location) or (has_hazard and is_forecast_warning)):
        return False

    # 2. Main Threshold Check (11.0 points to pass after bonuses)
    if sig["score"] >= SW["threshold_pass"]:
        return True

    # 3. Trusted Source / Verification Fallback (9.5 for official)
    if trusted_source and sig["score"] >= SW["threshold_official"]:
        return True

    is_forecast = sig["stage"] == "FORECAST"
    
    # Article Mode Thresholds:
    threshold = SW["threshold_forecast"] if is_forecast else SW["threshold_pending"]
    
    if sig["score"] >= threshold:
        # Check if title is actually relevant or just mentions location
        if title_lower and not title_contains_disaster_keyword(title_lower):
            # If title is generic (no disaster word) and score is marginal, reject
            return False
        return True
        
    # Special bypass for high-priority Forecast titles
    if is_forecast and title_lower and title_contains_disaster_keyword(title_lower):
        return True
        
    return False


def diagnose(text: str, title: str = "", authority_level: int = 1) -> dict:
    sig = compute_disaster_signals(text, title=title, authority_level=authority_level)
    reason = f"Score {sig['score']:.1f}"
    
    if sig["absolute_veto"]: 
        reason = "Veto (Absolute)"
    elif sig["conditional_veto"] and sig["hazard_score"] == 0:
        reason = "Veto (Conditional - No hazard)"
    else:
        # Align with crawler's tiered approval logic
        is_strong_title = sig.get("is_vip", False) or \
                          (HIGH_PRIORITY_RE and title and HIGH_PRIORITY_RE.search(title.lower())) or \
                          title_contains_disaster_keyword(title)
        
        has_hazard = sig.get("hazard_score", 0) > 0
        has_impact = sig.get("impact_hits", False)
        has_casualties = sig.get("impact_details", {}).get("deaths") or \
                         sig.get("impact_details", {}).get("missing")
        
        approval_threshold = SW["threshold_approve_strong"] if is_strong_title else SW["threshold_approve_strict"]
        score = sig["score"]
        
        if has_casualties and has_hazard and score >= (approval_threshold - 1.0):
             reason = "Approved (High impact casualty)"
        elif score >= approval_threshold:
            if has_hazard or sig.get("is_vip", False):
                reason = "Approved (Strong signals)"
            else:
                reason = "Pending (Audit hazard match)"
        elif score >= SW["threshold_pass"]:
            reason = "Pending (Verification needed)"
        elif authority_level >= 2 and score >= SW["threshold_official"]:
            reason = f"Pending (Official Source Fallback - Score {score:.1f})"
        elif sig.get("rule_matches"):
            reason = f"Rejected (Low score {score:.1f})"
        else:
            reason = "Rejected (Insignificant content)"
    
    return {"score": sig["score"], "signals": sig, "reason": reason}

def title_contains_disaster_keyword(title: str) -> bool:
    """
    Stricter title check using pre-compiled disaster rules (DISASTER_RULES_RE).
    Ensures consistency between title-level filtering and classification.
    """
    if not title: return False
    title_low = title.lower()
    
    # 1. Official Bypass (Critical Actions)
    if RE_CRITICAL_ACTIONS.search(title_low):
         return True # High confidence phrases
         
    # 2. Negative Veto (Absolute Veto)
    # Only use ABSOLUTE_VETO for titles. 
    if ABSOLUTE_VETO_RE and ABSOLUTE_VETO_RE.search(title_low):
        return False
            
    # 3. Rule Matching (Sophisticated Regex from DISASTER_RULES)
    # This ensures consistency: a title is "disaster-related" if it matches a classification rule.
    for label, compiled_list in DISASTER_RULES_RE:
        for pat_re in compiled_list:
            if pat_re.search(title_low):
                return True

    # 4. Fallback for common bulletin headers (since labels might be too specific)
    # [OPTIMIZATION] "Bản tin" or "Dự báo" usually indicates high value if it has a keyword
    if "dự báo thời tiết" in title_low or "bản tin" in title_low or "cảnh báo" in title_low:
        # Use simple keywords as fallback for general weather titles
        # This keeps the 'Disaster Groups' keyword list relevant for broad detection.
        for kw in SOURCE_DISASTER_KEYWORDS:
            if len(kw) > 4 and kw.lower() in title_low:
                return True
            elif len(kw) <= 4 and re.search(rf"\b{re.escape(kw.lower())}\b", title_low):
                return True

    return False

def extract_impacts(text: str, t_acc: str = None, pre_calculated_details: dict = None) -> dict:
    """
    Enhanced extraction to match user's professional report format.
    Fields: commune, village, route, cause, characteristics, along with casualties.
    """
    if pre_calculated_details:
        details = pre_calculated_details
    else:
        details = extract_impact_details(text, t_acc=t_acc)
    t_lower = t_acc if t_acc else text.lower()
    
    res = {
        "deaths": None,
        "missing": None,
        "injured": None,
        "damage_billion_vnd": 0.0,
        "agency": None,
        "commune": None,
        "village": None,
        "route": None,
        "cause": None,
        "characteristics": None,
        "location_description": None,
        "landmark": None
    }
    
    # 1. Human casualties (using max value from detailed extraction)
    for k in ["deaths", "missing", "injured"]:
        if k in details and details[k]:
            res[k] = max([item["max"] for item in details[k]])

    # 2. Financial Damage (Using max value reported to avoid duplicate sums)
    if "damage" in details:
        max_billion = 0.0
        for item in details["damage"]:
            val = item.get("max", 0)
            u = item.get("unit", "").lower()
            val_converted = 0.0
            if "tỷ" in u or "ty" in u or "tỉ" in u: val_converted = val
            elif "triệu" in u or "trieu" in u: val_converted = val / 1000.0
            
            if val_converted > max_billion:
                max_billion = val_converted
        res["damage_billion_vnd"] = max_billion
            
    # 3. Agency
    m_agency = RE_AGENCY.search(text)
    if m_agency: res["agency"] = m_agency.group(1)

    # 4. Location Details (Commune, Village, Route)
    m_commune = RE_COMMUNE.search(text)
    if m_commune: res["commune"] = m_commune.group(1).strip()

    m_village = RE_VILLAGE.search(text)
    if m_village: res["village"] = m_village.group(1).strip()

    m_route = RE_ROUTE.search(text)
    if m_route: res["route"] = m_route.group(1).strip()

    m_landmark = RE_LANDMARK.search(text)
    if m_landmark: res["landmark"] = m_landmark.group(1).strip()

    # 5. Cause
    if "mưa" in t_lower: res["cause"] = "Mưa lớn"
    elif any(kw in t_lower for kw in ["nhân sinh", "xây dựng", "đào đắp", "xẻ núi"]): res["cause"] = "Hoạt động nhân sinh"
    
    # 6. Characteristics
    m_char = re.search(r"([^.?!]*(?:kéo dài|diễn ra|khối lượng|diện tích)[^.?!]*[.?!])", text, re.IGNORECASE)
    if m_char: res["characteristics"] = m_char.group(1).strip()

    # 7. Auto-generated Location Description
    # 7. Auto-generated Location Description
    res["location_description"] = format_location_description(res, extract_province(text, t_acc=t_acc))

    return res

def format_location_description(impacts: dict, province: str) -> str:
    """
    Format a readable location string from components.
    """
    parts = []
    if impacts.get("village"): parts.append(impacts["village"])
    if impacts.get("commune"): parts.append(impacts["commune"])
    if impacts.get("route"): parts.append(impacts["route"])
    if impacts.get("landmark"): parts.append(impacts["landmark"])
    
    loc = ", ".join(parts)
    if loc and province and province != "unknown":
        return f"{loc}, {province}"
    elif loc:
        return loc
    return province if province != "unknown" else ""

    return province if province != "unknown" else ""

def extract_publication_date_from_text(text: str) -> datetime | None:
    """
    Scans text for explicit publication timestamps often found in Vietnamese news bodies.
    Examples: 
      - "Chủ Nhật 05/10/2025, 19:26 (GMT+7)"
      - "07/01/2026 21:24"
    """
    if not text: return None
    
    # Pattern 1: dd/mm/yyyy HH:MM (GMT+7/none)
    # Matches: 05/10/2025, 19:26 (GMT+7) or 05/10/2025 , 19:26
    # Priority matching: dd/mm/yyyy near HH:MM
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*[,|-]?\s*(\d{1,2}):(\d{2})", text)
    if m:
        try:
            day, month, year, hour, minute = map(int, m.groups())
            # Basic validation
            if 1990 < year < 2030 and 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59:
                 dt = datetime(year, month, day, hour, minute)
                 # Assume GMT+7
                 return dt - timedelta(hours=7) 
        except ValueError:
            pass
            
    # Pattern 2: HH:MM dd/mm/yyyy
    m2 = re.search(r"(\d{1,2}):(\d{2})\s*[,|-]?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m2:
        try:
            hour, minute, day, month, year = map(int, m2.groups())
            if 1990 < year < 2030 and 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59:
                 dt = datetime(year, month, day, hour, minute)
                 return dt - timedelta(hours=7) 
        except ValueError:
            pass

    return None

def extract_event_time(published_at: datetime, text: str) -> datetime | None:
    """
    Extract event time from text.
    Supports:
    - Absolute dates: dd/mm/yyyy, dd-mm-yyyy
    - Vietnamese date format: ngày dd tháng mm
    - Relative time: hôm nay, đêm qua, rạng sáng, etc.
    """
    from datetime import timedelta
    
    t = text.lower()
    
    # 1. Try relative time expressions first (most common in Vietnamese news)
    
    # "hôm nay" / "chiều nay" / "sáng nay" / "trưa nay" / "tối nay"
    if re.search(r"\b(hôm\s*nay|chiều\s*nay|sáng\s*nay|trưa\s*nay|tối\s*nay)\b", t):
        return published_at.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "đêm qua" / "tối qua"
    if re.search(r"\b(đêm\s*qua|tối\s*qua)\b", t):
        yesterday = published_at - timedelta(days=1)
        return yesterday.replace(hour=22, minute=0, second=0, microsecond=0)
    
    # "rạng sáng" / "sáng sớm" (early morning of current day)
    if re.search(r"\b(rạng\s*sáng|sáng\s*sớm)\b", t):
        # Check if context suggests yesterday or today
        if re.search(r"(đêm\s*qua|hôm\s*qua).*?(rạng\s*sáng|sáng\s*sớm)", t):
            # "đêm qua rạng sáng" → yesterday night to today early morning
            today = published_at.replace(hour=5, minute=0, second=0, microsecond=0)
            return today
        else:
            # Just "rạng sáng" → current day early morning
            return published_at.replace(hour=5, minute=0, second=0, microsecond=0)
    
    # "hôm qua" / "ngày hôm qua"
    if re.search(r"\b(hôm\s*qua|ngày\s*hôm\s*qua)\b", t):
        yesterday = published_at - timedelta(days=1)
        return yesterday.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "2 ngày trước" / "3 ngày trước"
    m = re.search(r"(\d+)\s*ngày\s*(?:trước|qua)", t)
    if m:
        days_ago = int(m.group(1))
        past_date = published_at - timedelta(days=days_ago)
        return past_date.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "tuần trước" / "tuần qua"
    if re.search(r"\b(tuần\s*(?:trước|qua))\b", t):
        last_week = published_at - timedelta(days=7)
        return last_week.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # 2. Try Vietnamese date format: "ngày 15 tháng 12" or "15 tháng 12"
    m = re.search(r"(?:ngày\s*)?(\d{1,2})\s*tháng\s*(\d{1,2})(?:\s*năm\s*(\d{4}))?", t)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else published_at.year
        
        try:
            return datetime(year, month, day, 12, 0, 0)
        except ValueError:
            pass  # Invalid date, continue to next method
    
    # 3. Try absolute date formats: dd/mm/yyyy, dd-mm-yyyy
    candidates = []
    for m in re.finditer(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text):
        candidates.append(m.group(1))
    
    for c in candidates[:3]:
        try:
            dt = dtparser.parse(c, dayfirst=True)
            if dt.year == 1900: 
                dt = dt.replace(year=published_at.year)
            return dt
        except: 
            continue
    
    return None

def classify_disaster(text: str, title: str = "", hazard_weights: dict = None, t_title_in: str = None, t_body_in: str = None) -> dict:
    """
    Classify disaster type based on 14 specific types and 2 special groups:
    1. storm, 2. flood, 3. flash_flood, 4. landslide, 5. subsidence, 6. drought, 7. salinity,
    8. extreme_weather, 9. heatwave, 10. cold_surge, 11. earthquake, 12. tsunami, 13. storm_surge, 14. wildfire
    + warning_forecast, recovery
    """
    full_text = f"{title}\n{text}" if title else text
    
    t_title = t_title_in
    if t_title is None:
         t_title, _ = risk_lookup.canon(title or "")

    t_body = t_body_in
    if t_body is None:
         t_body, _ = risk_lookup.canon(text or "")

    # Optimization: If hazard_weights passed from compute_disaster_signals, use them directly
    if hazard_weights is None:
        # Use match_disaster_rules to get consistent weights
        # Updated to use only 2 arguments as per signature
        _, _, hazard_weights, _ = match_disaster_rules(t_body, t_title)
    
    # ROOT CAUSE BOOSTING & TIE-BREAKING
    if "storm" in hazard_weights:
        if re.search(r"(?:bão|áp thấp|ATNĐ|ATND).*?(?:số\s*\d+|[A-ZĐ][a-zà-ỹ]+)", t_title, re.IGNORECASE):
            hazard_weights["storm"] += 10

    if "flash_flood" in hazard_weights and "flood" in hazard_weights:
        hazard_weights["flash_flood"] += 2

    if "wildfire" in hazard_weights:
        # Check both title and body (normalized) using centralized indicators
        if not any(fi in t_title for fi in sources.FOREST_INDICATORS) and not any(fi in t_body for fi in sources.FOREST_INDICATORS):
            hazard_weights["wildfire"] -= 10

    primary = "unknown"
    if hazard_weights:
        # Sort by weight, then by priority index (Using strictly ordered list)
        sorted_hazards = sorted(
            hazard_weights.items(),
            key=lambda item: (-item[1], DISASTER_PRIORITY_ORDER.get(item[0], 99))
        )
        if sorted_hazards[0][1] > 0:
            primary = sorted_hazards[0][0]

    # Special Classification: Warning/Forecast & Recovery Groups using pre-compiled patterns
    if RE_WARNING_TITLE.search(t_title):
        primary = "warning_forecast"
    elif RE_RECOVERY_TITLE.search(t_title):
        primary = "recovery"
    elif primary == "unknown":
        # Fallback to content-based detection for these groups using pre-compiled mega-regexes
        if sources.RE_FORECAST.search(t_title) or sources.RE_FORECAST.search(t_body):
            primary = "warning_forecast"
        elif sources.RE_RECOVERY.search(t_title) or sources.RE_RECOVERY.search(t_body):
            primary = "recovery"
        elif (sources.VIP_TERMS_RE and (sources.VIP_TERMS_RE.search(t_title) or sources.VIP_TERMS_RE.search(t_body))):
             primary = "recovery"

    return {
        "primary_type": primary,
        "hazard_weights": hazard_weights,
        "is_disaster": primary != "unknown"
    }


def summarize(text: str, max_len: int = 220, title: str = "") -> str:
    if not text:
        return "Nội dung chi tiết đang được cập nhật..."
    import html
    cleaned = html.unescape(text) # [OPTIMIZATION] Standardize HTML entities for Vietnamese
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if title and (cleaned.lower() == title.lower() or len(cleaned) < 20):
        return "Đang tổng hợp dữ liệu từ bài báo gốc. Vui lòng bấm vào tiêu đề bài báo bên dưới để xem chi tiết."
    if len(cleaned) <= max_len: return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"


# IMPACT EXTRACTION LOGIC


def extract_impact_details(text: str, t_acc: str = None) -> dict:
    """
    UNIFIED IMPACT EXTRACTION (Fusion Strategy)
    Extracts, standardizes, and de-conflicts disaster impact metrics.
    """
    results = {k: [] for k in IMPACT_KEYWORDS.keys()}
    if t_acc is None:
        t_acc, _ = risk_lookup.canon(text or "")
    
    # 1. Collect all raw candidates
    candidates = []
    
    for impact_type in IMPACT_KEYWORDS.keys():
        # [OPTIMIZATION] Build negation list once per type
        negs = NEGATION_TERMS.get(impact_type, []) + NEGATION_TERMS.get("general", [])

        # Only one pass: Accented
        passes = [
            (t_acc, IMPACT_PATTERNS.get(impact_type, []))
        ]
        
        for search_text, patterns in passes:
            for pat in patterns:
                for m in pat.finditer(search_text):
                    # REFINED LOCAL NEGATION (Window: 120 chars total)
                    start, end = m.span()
                    # Check left (60 chars) and right (40 chars)
                    win_start = max(0, start - 60)
                    win_end = min(len(search_text), end + 40)
                    context_win = search_text[win_start:win_end]
                    
                    if any(n in context_win for n in negs):
                        continue
                        
                    val_obj = _parse_unified_value(m.groupdict())
                    if val_obj["min"] == 0 and val_obj["max"] == 0:
                        continue
                        
                    candidates.append({
                        "type": impact_type,
                        "min": val_obj["min"],
                        "max": val_obj["max"],
                        "is_estimated": val_obj["is_estimated"],
                        "precision": val_obj["precision"],
                        "unit": val_obj["unit"],
                        "qualifier": m.groupdict().get("qualifier"),
                        "span": m.span(),
                        "text": m.group(0)
                    })
    
    # 2. Fusion & De-confliction Logic
    # We sort by span start, then by precision descending
    candidates.sort(key=lambda x: (x["span"][0], -x["precision"]))
    
    fused = []
    for cand in candidates:
        is_conflict = False
        to_replace = -1
        
        for i, f in enumerate(fused):
            # Check for significant overlap with existing fused match
            s1, e1 = cand["span"]
            s2, e2 = f["span"]
            overlap = max(0, min(e1, e2) - max(s1, s2))
            
            if overlap > 0:
                # If same type or strongly overlapping, keep the more precise one
                if cand["precision"] > f["precision"]:
                    to_replace = i
                elif cand["precision"] == f["precision"] and (e1-s1) > (e2-s2):
                    to_replace = i
                
                is_conflict = True
                break
        
        if to_replace >= 0:
            fused[to_replace] = cand
        elif not is_conflict:
            fused.append(cand)
            
    # 3. Organize final results
    for f in fused:
        results[f["type"]].append(f)
        
    return results

# DATA INTEGRITY: OUTLIER DETECTION

IMPACT_THRESHOLDS = {
    "deaths": 50,           # > 50 in a single article is rare/major
    "missing": 100,
    "injured": 200,
    "damage_billion_vnd": 5000.0, # 5 trillion VND (Yagi-level)
}

def validate_impacts(impact_dict: dict) -> bool:
    """
    Checks if extracted impacts are within realistic thresholds.
    Returns True if any value looks suspicious/anomalous.
    """
    needs_verification = False
    
    # Check simple counts
    for key in ["deaths", "missing", "injured"]:
        val_list = impact_dict.get(key, [])
        if val_list and isinstance(val_list, list):
            if any(v > IMPACT_THRESHOLDS.get(key, 9999) for v in val_list):
                needs_verification = True
                break
    
    # Check damage (if consolidated list of dicts)
    if not needs_verification:
        damage_items = impact_dict.get("damage", [])
        if damage_items and isinstance(damage_items, list):
            for item in damage_items:
                num = item.get("num", 0)
                unit = (item.get("unit") or "").lower()
                
                # Convert to billion VND for threshold check if possible
                val_billion = 0
                if "tỷ" in unit or "tỉ" in unit or "bnd" in unit:
                    val_billion = num
                elif "triệu" in unit:
                    val_billion = num / 1000.0
                
                if val_billion > IMPACT_THRESHOLDS["damage_billion_vnd"]:
                    needs_verification = True
                    break

    return needs_verification

def extract_all_metadata(text: str, summary_raw: str, title: str, existing_signals: dict = None) -> dict:
    """
    Helper to run all extraction tasks in one go (useful for thread offloading).
    OPTIMIZED v3: Normalized once, shared between signals and extraction. Reuses existing signals if provided.
    """
    # 1. Normalize Separately to allow specific targeting
    t_title_acc, _ = risk_lookup.canon(title or "")
    t_body_acc, _ = risk_lookup.canon(text or "")
    
    # Construct Full Text Normalized (for Signal detection & Global Search)
    if title and title not in text:
        t_acc = f"{t_title_acc} {t_body_acc}".strip()
    else:
        t_acc = t_body_acc
    
    # 2. Compute Signals (includes scoring, Veto, and Hazard matching)
    if existing_signals:
         signals = existing_signals
    else:
         signals = compute_disaster_signals(text, title=title, t_acc=t_acc)
    
    # [OPTIMIZATION] Reuse Impact Details calculated in compute_disaster_signals
    impact_details_raw = signals.get("impact_details", {})
    if not impact_details_raw:
        # Fallback if for some reason it's missing (shouldn't be)
        impact_details_raw = extract_impact_details(text, t_acc=t_acc)
    
    # 3. Classify Type
    disaster_info = classify_disaster(text, title=title, hazard_weights=signals.get("hazard_weights"), t_title_in=t_title_acc, t_body_in=t_body_acc)
    
    # 4. Extract Location
    all_provs = extract_provinces(text, title=title, t_acc=t_acc, t_title_acc=t_title_acc)
    
    best_prov = "unknown"
    for h in all_provs:
        if h["type"] == "province": best_prov = h["name"]; break
    if best_prov == "unknown":
        for h in all_provs:
            if h["type"] == "region": best_prov = h["name"]; break
            
    province = best_prov
    
    # 5. Extract Impacts (Detailed)
    impacts = extract_impacts(text, t_acc=t_acc, pre_calculated_details=impact_details_raw) 
    
    # 6. Summary
    summary_text = summarize(summary_raw.replace("&nbsp;", " "), title=title)
    
    # Optimized: If impacts (deaths/missing) are found, prioritize INCIDENT or RECOVERY
    has_impacts = (impacts.get("deaths") or impacts.get("missing") or impacts.get("injured") or 0) > 0
    stage = determine_event_stage(text, impact_detected=has_impacts, t_acc=t_acc)
    
    needs_verification = validate_impacts(impacts)
    
    return {
        "disaster_type": disaster_info.get("primary_type", "unknown"),
        "province": province,
        "impacts": impacts,
        "summary": summary_text,
        "stage": stage,
        "impact_details": impact_details_raw, 
        "metrics": signals.get("metrics", {}), # [ADDED]
        "needs_verification": needs_verification,
        "has_impacts": has_impacts,
        "landmark": impacts.get("landmark")
    }
