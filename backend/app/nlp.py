import re
import unicodedata
import logging
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from . import sources
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS
from . import risk_lookup

logger = logging.getLogger(__name__)

# CONSTANTS & CONFIG

# Impact keywords
IMPACT_KEYWORDS = {
    "deaths": {
        "terms": [
            "chết", "tử vong", "tử nạn", "tử thương", "thiệt mạng", "thương vong", "nạn nhân tử vong", "số người chết", "làm chết", "cướp đi sinh mạng", "tìm thấy thi thể", "không qua khỏi", 
            "tử vong tại chỗ", "tử vong sau khi", "đã tử vong", "chết cháy", "tử vong do ngạt", "ngạt khói", "ngạt khí", "chết đuối", "đuối nước", "ngạt nước", "bị cuốn trôi tử vong", "bị vùi lấp tử vong", "bị chôn vùi tử vong"
        ],
        "regex": [
            r"\b(?P<qualifier>ít nhất|tối thiểu|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh|công nhân|chiến sĩ)\s*(chết|tử vong|thiệt mạng|tử nạn|tử thương|thương vong)\b",
            r"\b(làm|khiến)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)\s*(chết|tử vong|thiệt mạng|thương vong)\b",
            r"\b(tìm thấy|phát hiện)\s*(thi thể|xác)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)?\b",
            r"\b(cướp đi sinh mạng|tước đi sinh mạng)\s*(của)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b"
        ]
    },

    "missing": {
        "terms": [
            "mất tích", "thất lạc", "chưa tìm thấy", "chưa tìm được", "chưa thấy","mất liên lạc", "không liên lạc được", "không thể liên lạc","chưa xác định tung tích", "không rõ tung tích", "chưa rõ số phận","bị cuốn trôi", 
            "trôi mất", "bị nước cuốn", "bị lũ cuốn","bị vùi lấp", "bị chôn vùi", "mắc kẹt", "bị mắc kẹt","đang tìm kiếm", "tổ chức tìm kiếm", "công tác tìm kiếm","tìm kiếm cứu nạn", "cứu nạn", "cứu hộ", "tìm kiếm cứu hộ"
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|công nhân|thuyền viên|ngư dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(bị|đã)?\s*(mất tích|mất liên lạc|chưa tìm thấy|chưa liên lạc được|không rõ tung tích|cuốn trôi|lũ cuốn|nước cuốn|vùi lấp|mắc kẹt)\b",
            r"\b(tìm kiếm|chưa tìm thấy|chưa liên lạc được|mất liên lạc|vẫn chưa liên lạc được|chưa xác định tung tích|chưa rõ tung tích)\s*(với|cho|with)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|công nhân|nhóm)?\b",
            r"\b(cuốn trôi|cuốn|vùi lấp|chôn vùi)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b"
        ]
    },

    "injured": {
        "terms": [
            "bị thương", "bị thương nặng", "bị thương nhẹ", "trọng thương", "xây xát", "chấn thương", "đa chấn thương", "gãy xương", "bỏng", "bị bỏng", "bất tỉnh", "ngất xỉu", "sốc", "ngộ độc", "khó thở", "nhập viện", "đưa đi bệnh viện", 
            "đưa vào bệnh viện", "cấp cứu", "điều trị", "sơ cứu", "chuyển viện", "đang điều trị", "được điều trị"
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|ca)\s*(bị thương|trọng thương|nhập viện|cấp cứu|đa chấn thương|thương tích|xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(làm|khiến|gây)\s*(bị|trọng thương|bị bỏng|bất tỉnh|gãy xương|đa chấn thương)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b",
            r"\b(đưa|chuyển|sơ cứu|điều trị cho|cấp cứu cho|ghi nhận|có)(?:[^0-9]{0,30})?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)(?:[^a-z0-9]{0,10})?\s*(đi|tới|bị|do)?\s*(cấp cứu|bệnh viện|viện|xây xát|bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(bị thương|bị xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân)\b"
        ]
    },

    "marine": {
        "terms": [
            "chìm tàu", "tàu chìm", "đắm tàu", "tàu đắm", "lật tàu", "lật thuyền", "trôi dạt", "dạt vào bờ", "mất tín hiệu", "mất liên lạc", "không liên lạc được", "gặp nạn trên biển", "gặp nạn", 
            "tai nạn đường thủy", "đánh chìm", "chìm", "đắm", "lật", "trôi", "tàu cá", "tàu hàng", "tàu du lịch", "sà lan", "thuyền", "cano", "ghe", "ghe chài", "ngư dân", "thuyền viên", "cứu nạn trên biển", 
            "tìm kiếm trên biển", "lai dắt", "kéo về bờ", "cứu nạn", "cứu hộ"
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\s*(bị|đã)?\s*(chìm|đắm|lật|trôi dạt|mất liên lạc|hư hỏng|mất tích|gặp nạn)\b", 
            r"\b(chìm|đắm|lật|trôi dạt|đánh chìm|lai dắt|cứu hộ|cứu nạn)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>ngư dân|thuyền viên)(?:[^0-9]{0,20})?\s*(bị|đã)?\s*(mất liên lạc|mất tích|trôi dạt|gặp nạn)\b",
            r"\b(mất liên lạc|cứu hộ|cứu nạn|liên lạc được)\s*(với|cho|with)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|ngư dân|thuyền viên|thuyền|phương tiện|sà lan)\b"
        ]
    },

    "damage": {
        "terms": [
            # general loss
            "thiệt hại", "tổn thất", "ước tính thiệt hại", "thiệt hại về tài sản",
            "thiệt hại nặng", "thiệt hại nghiêm trọng", "tàn phá",
            # houses/buildings (Short verbs added for exclusion)
            "hư hỏng", "hư hại", "hư hỏng nặng", "hư hại nặng",
            "sập", "đổ sập", "sập đổ", "đổ", "nứt", "tốc mái", 
            "sập nhà", "đổ tường", "nứt tường", "nứt nhà",
            "bay mái", "tốc mái hàng loạt", "xiêu vẹo",
            # flood/landslide/erosion
            "ngập", "ngập nhà", "ngập sâu", "ngập lút", "ngập úng",
            "cuốn trôi", "trôi nhà", "trôi xe", "lũ cuốn",
            "sạt lở", "sạt lở đất", "sạt lở đường", "sạt lở taluy",
            "sụt lún", "sụp lún", "nứt mặt đường", "đứt đường", "đường bị chia cắt",
            "chia cắt", "cô lập",
            # infrastructure & utilities
            "sập cầu", "hỏng cầu", "hư hỏng cầu",
            "mất điện", "cúp điện", "cắt điện", "mất điện diện rộng",
            "mất nước", "cắt nước", "mất sóng", "mất liên lạc", "đứt cáp",
            "đổ cột điện", "đứt đường dây", "hư hỏng trạm biến áp",
            # trees/urban damage
            "cây đổ", "đổ cây", "gãy cây", "gãy đổ"
        ],
        "regex": [
            r"\b(thiệt hại|tổn thất)(?:[^0-9]{0,30})?\s*(?P<qualifier>ước|ước tính|khoảng|lên tới|hơn|trên|ban đầu|\s)*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?)\s*(?P<unit>tỷ|triệu)\s*(đồng|VND)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)(?:[^0-9]{0,20})?\s*(bị|đã|có)?\s*(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|sạt lở|gãy đổ|vùi lấp|nứt|sụt lún|chia cắt|cô lập|cháy|mất điện|mất nước|ngập úng|trôi)\b",
            r"\b(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|cuốn trôi|vùi lấp|làm sập|gãy đổ|nứt|sụt lún|chia cắt|cô lập|cháy|mất điện|mất nước|trôi|ngập úng)(?:[^0-9]{0,20})?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|hộ|nhà|căn)(?:[^0-9]{0,10})?\s*(?:đã|bị|có)?\s*(?:nhà\s*)?(?:bị\s*)?(sạt lở|sập|trôi|lũ cuốn|vùi lấp|chia cắt|cô lập|cháy|mất điện|mất nước|ảnh hưởng)\b",
            # Infrastructure & Specific objects
            r"\b(sập|đổ|gãy|hư hỏng|tốc mái|cuốn trôi)\s*(hoàn toàn|hàng loạt)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>mét|m)?\s*(tường rào|mái tôn|nhà xưởng|kho|chuồng trại|trạm biến áp|đường dây|cột điện|cây xanh|cây)\b"
        ]
    },

    "disruption": {
        "terms": [
            "sơ tán", "tạm sơ tán", "sơ tán khẩn cấp",
            "di dời", "di dời khẩn cấp", "di tản",
            "phong tỏa", "cách ly", "hạn chế đi lại",
            "cấm đường", "cấm lưu thông", "cấm phương tiện",
            "đóng đường", "chặn đường", "tạm đóng", "tạm dừng", "tạm ngưng", "đình chỉ",
            "tê liệt giao thông", "ùn tắc", "kẹt xe", "gián đoạn giao thông",
            "đóng cửa trường", "cho học sinh nghỉ", "nghỉ học", "tạm nghỉ học",
            "dừng hoạt động", "hoãn", "hủy",
            "cấm biển", "cấm ra khơi", "tàu thuyền không ra khơi", "neo đậu tránh trú",
            "mất điện diện rộng", "cắt điện", "ngừng cấp điện",
            "mất nước", "ngừng cấp nước",
            "mất sóng", "gián đoạn thông tin", "mất mạng"
        ],
        "regex": [
            r"\b(cấm|đóng|tạm dừng|tạm ngưng)\s*(?P<unit>đường|lưu thông)\b",
            r"\b(sơ tán|di dời|di tản)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(sơ tán|di dời|di tản)\s*(?P<qualifier>khẩn cấp)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(phải|cần|đã)?\s*(sơ tán|di dời|di tản)\b"
        ]
    },

    "agriculture": {
        "terms": [
            # crops/land
            "hoa màu", "cây trồng", "vườn cây", "cây ăn quả",
            "lúa", "ruộng", "diện tích lúa", "mất trắng", "mất mùa",
            "ngập úng hoa màu", "hư hại hoa màu", "thiệt hại mùa màng",
            "mía", "sắn", "ngô", "bắp", "đậu", "lạc", "rau màu",
            "cà phê", "cao su", "hồ tiêu", "điều",
            # livestock
            "gia súc", "gia cầm", "trâu bò", "lợn gà", "vật nuôi",
            "chết gia súc", "chết gia cầm", "trôi gia súc", "trôi gia cầm",
            "chuồng trại", "trại chăn nuôi",
            # aquaculture
            "ao nuôi", "đầm nuôi", "tôm cá", "thủy sản",
            "lồng bè", "lồng nuôi", "bè cá", "mất trắng thủy sản", "trôi lồng bè"
        ],
        "regex": [
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta|héc ta|sào|tấn)\s*(lúa|hoa màu|cây trồng|ruộng|diện tích|mía|ngô|bắp|rau|cà phê|tiêu|điều|bị|ngập|hư hại|thiệt hại|mất trắng|đổ ngã)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>con)\s*(trâu|bò|lợn|gà|vịt|gia súc|gia cầm)\b",
            r"\b(?P<num>\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>lồng bè|lồng|bè)\b",
            r"\b(vỡ|tràn|mất trắng)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>ao|đầm|lồng bè|ha|mẫu|công)\s*(nuôi|tôm|cá|thủy sản)?\b",
            r"\b(chết|trôi)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>con|tấn|kg)?\s*(tôm|cá|gia súc|gia cầm|lợn|gà|bò)\b"
        ]
    },


}

# Boilerplate tokens
BOILERPLATE_TOKENS = [
    r"\bvideo\b", r"\bảnh\b", r"\bclip\b", r"\bphóng\s*sự\b", r"\btrực\s*tiếp\b",
    r"\blive\b", r"\bhtv\b", r"\bphoto\b", r"\bupdate\b"
]

NEGATION_TERMS = {
    "deaths": ["không có người chết", "không có thương vong", "chưa ghi nhận thương vong", "không ghi nhận thiệt hại về người"],
    "missing": ["không có người mất tích", "không ai mất tích", "chưa ghi nhận mất tích"],
    "injured": ["không ai bị thương", "không có người bị thương", "không ghi nhận thương vong"],
    "damage": ["không gây thiệt hại", "chưa có thiệt hại", "không có thiệt hại về tài sản", "không gây thiệt hại về người", "không ghi nhận thiệt hại", "không có thiệt hại đáng kể", "chưa thống kê được thiệt hại"],
    "general": ["bác bỏ", "tin đồn", "dự kiến", "diễn tập", "kịch bản", "giả định", "trước khi"]
}

def safe_no_accent(pat: str) -> bool:
    """
    Determine if a regex pattern is safe to match against unaccented text.
    Prevents single-word disaster terms (like 'bão' -> 'bao') from matching
    unrelated words (like 'báo động', 'bạo hành').
    """
    # 1. Whitelist high-confidence hazard words that are relatively unique
    # We allow these even if they are single words because 'lu', 'loc', 'ret' 
    # are less likely to cause massive noise than 'bao' or 'mua'.
    hazard_whitelist = ["lũ", "lụt", "lốc", "rét"]
    if any(hw in pat.lower() for hw in hazard_whitelist):
        return True

    # 2. Extract "Effective" content by stripping regex syntax
    # Remove lookarounds (?...) and char classes [\w] etc.
    p = re.sub(r"\(\?[:=!<>]+.*?\)", "", pat)
    p = re.sub(r"\\(?:[wsdbwWSD]|b|B)", " ", p)
    p = re.sub(r"[\(\)\|\{\}\[\]\*\+\?\.\^\\\$]", " ", p)
    p = re.sub(r"\s+", " ", p).strip()

    # 3. Strict Safety Heuristic
    # Pattern is safe if it is long enough (> 12 chars) to be specific.
    # OR it is a multi-word phrase AND long enough to avoid short word collisions (e.g. 'bo bao' vs 'bo bao')
    if len(p) >= 12:
        return True
    if " " in p and len(p) >= 10:
        return True
        
    return False

def normalize_text(text: str) -> str:
    """
    Normalize text:
    - Lowercase
    - Strip accents (optional, but requested by user)? 
      User said: "Chuẩn hoá text trước khi match: lower(), bỏ dấu (accent-insensitive), chuẩn hoá khoảng trắng."
      However, we need to be careful. Regexes might expect accents if written with them.
      The provided regexes like "tử vong" HAVE accents.
      So if we strip accents, we must strip accents in regexes too.
      BUT the user provided regexes WITH accents.
      So maybe we should just create a `t_lower` for keyword checking, 
      and `t_norm` (no accent) if we want accent-insensitive match.
      
      For regexes, the user provided regexes contain accents ("chết", "người").
      If we run these against unaccented text, they won't match.
      So let's just do lowercase + whitespace normalization for now, 
      unless we auto-generate unaccented regex versions (extra complexity).
      
      Let's stick to lower() + space normalization.
    """
    if not text: return ""
    # Lowercase
    t = text.lower()
    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


NUMBER_WORDS = {
    "không": 0, "một": 1, "mốt": 1, "1": 1, "hai": 2, "2": 2, "ba": 3, "3": 3,
    "bốn": 4, "tư": 4, "4": 4, "năm": 5, "5": 5, "sáu": 6, "6": 6, "bảy": 7, "7": 7,
    "tám": 8, "8": 8, "chín": 9, "9": 9, "mười": 10, "10": 10,
    "vài": 3, "chục": 10, "mấy chục": 30, "hàng chục": 20, "trăm": 100, "vài trăm": 300, "một trăm": 100, "hai trăm": 200, "ba trăm": 300, 
    "năm trăm": 500, "nghìn": 1000, "ngàn": 1000, "một nghìn": 1000, "vạn": 10000, "hàng vạn": 20000,
    "triệu": 1000000, "tỷ": 1000000000, "tỉ": 1000000000
}

# 34 PROVINCES MAPPING (NEW - Effective July 1, 2025)
# Format: New_Name -> List of Old_Names/Variants to match in text
PROVINCE_MAPPING = {
    # I. Units kept as is (11 units)
    "Hà Nội": ["Hà Nội", "HN", "Ha Noi", "Thủ đô Hà Nội"],
    "Huế": ["Thành phố Huế", "TP Huế", "Thừa Thiên Huế", "TT Huế", "Thua Thien Hue"],
    "Lai Châu": ["Lai Châu", "Lai Chau"],
    "Điện Biên": ["Điện Biên", "Dien Bien"],
    "Sơn La": ["Sơn La", "Son La"],
    "Lạng Sơn": ["Lạng Sơn", "Lang Son"],
    "Quảng Ninh": ["Quảng Ninh", "Quang Ninh"],
    "Thanh Hóa": ["Thanh Hóa", "Thanh Hoa"],
    "Nghệ An": ["Nghệ An", "Nghe An"],
    "Hà Tĩnh": ["Hà Tĩnh", "Ha Tinh"],
    "Cao Bằng": ["Cao Bằng", "Cao Bang"],

    # II. New units formed by merger (23 units)
    "Tuyên Quang": ["Tuyên Quang", "Hà Giang", "Ha Giang", "Tuyen Quang"],
    "Lào Cai": ["Lào Cai", "Yên Bái", "Yen Bai", "Lao Cai"],
    "Thái Nguyên": ["Thái Nguyên", "Bắc Kạn", "Bac Kan", "Thai Nguyen"],
    "Phú Thọ": ["Phú Thọ", "Vĩnh Phúc", "Hòa Bình", "Phu Tho", "Vinh Phuc", "Hoa Binh"],
    "Bắc Ninh": ["Bắc Ninh", "Bắc Giang", "Bac Ninh", "Bac Giang"],
    "Hưng Yên": ["Hưng Yên", "Thái Bình", "Hung Yen", "Thai Binh"],
    "Hải Phòng": ["Hải Phòng", "Hải Dương", "Hai Phong", "Hai Duong", "HP"],
    "Ninh Bình": ["Ninh Bình", "Hà Nam", "Nam Định", "Ninh Binh", "Ha Nam", "Nam Dinh"],
    "Quảng Trị": ["Quảng Trị", "Quảng Bình", "Quang Tri", "Quang Binh"],
    "Đà Nẵng": ["Đà Nẵng", "Quảng Nam", "Da Nang", "Quang Nam", "ĐN"],
    "Quảng Ngãi": ["Quảng Ngãi", "Kon Tum", "Quang Ngai", "Kon Tum", "QNg"],
    "Gia Lai": ["Gia Lai", "Bình Định", "Gia Lai", "Binh Dinh"],
    "Khánh Hòa": ["Khánh Hòa", "Ninh Thuận", "Khanh Hoa", "Ninh Thuan"],
    "Lâm Đồng": ["Lâm Đồng", "Đắk Nông", "Bình Thuận", "Lam Dong", "Dak Nong", "Binh Thuan"],
    "TP Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn", "Bà Rịa - Vũng Tàu", "Bà Rịa", "Vũng Tàu", "Bình Dương", "HCMC", "Sai Gon", "BRVT", "Binh Duong", "SG"],
    "Đồng Nai": ["Đồng Nai", "Bình Phước", "Dong Nai", "Binh Phuoc"],
    "Long An": ["Long An", "Tây Ninh", "Long An", "Tay Ninh"],
    "An Giang": ["An Giang", "Kiên Giang", "An Giang", "Kien Giang"],
    "Cần Thơ": ["Cần Thơ", "Hậu Giang", "Sóc Trăng", "Can Tho", "Hau Giang", "Soc Trang"],
    "Tiền Giang": ["Tiền Giang", "Bến Tre", "Tien Giang", "Ben Tre"],
    "Vĩnh Long": ["Vĩnh Long", "Đồng Tháp", "Vinh Long", "Dong Thap"],
    "Bạc Liêu": ["Bạc Liêu", "Cà Mau", "Bac Lieu", "Ca Mau"],
    "Trà Vinh": ["Trà Vinh", "Tra Vinh"]
}

# List of valid (new) province names
PROVINCES = list(PROVINCE_MAPPING.keys())

PROVINCE_REGIONS = [
    "Biển Đông", "Nam Trung Bộ", "Bắc Bộ", "Miền Trung", "Miền Bắc", "Miền Nam", "Tây Nguyên", "Trung Bộ", "Nam Bộ"
]

# Pre-compute compiled regexes for Provinces and Regions
PROVINCE_REGEXES = []

def _compile_prov_regex(names):
    # Helper to build regex with word boundaries and flexible whitespace
    parts = []
    for n in names:
        # Escape characters, then replace escaped space with \s+
        esc = re.escape(n).replace(r"\ ", r"\s+")
        parts.append(esc)
    pattern = "|".join(parts)
    return re.compile(rf"(?<!\w)({pattern})(?!\w)", re.IGNORECASE)

for name, variants in PROVINCE_MAPPING.items():
    PROVINCE_REGEXES.append({
        "name": name,
        "type": "province",
        "re_acc": _compile_prov_regex(variants),
        "re_no": _compile_prov_regex([risk_lookup.strip_accents(v) for v in variants])
    })

for reg in PROVINCE_REGIONS:
    PROVINCE_REGEXES.append({
        "name": reg,
        "type": "region",
        "re_acc": _compile_prov_regex([reg]),
        "re_no": _compile_prov_regex([risk_lookup.strip_accents(reg)])
    })
# DISASTER RULES & PATTERNS

DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới (Storm/Tropical Cyclone)
  ("storm", [
    r"(?<!\w)(?<!đi\s)(?<!dự\s)bão(?!\sgiá)(?!\smạng)(?!\slòng)(?!\stài\s)(?!\stín\s)(?!\w)",
    r"bão\s*số\s*\d+", r"siêu\s*bão", r"tâm\s*bão", r"mắt\s*bão", r"hoàn\s*lưu\s*bão",
    r"áp\s*thấp\s*nhiệt\s*đới", r"vùng\s*áp\s*thấp", r"ATNĐ", r"ATND", r"xoáy\s*thuận\s*nhiệt\s*đới",
    r"nhiễu\s*động\s*nhiệt\s*đới", r"cường\s*độ\s*bão", r"cấp\s*bão", r"bán\s*kính\s*gió\s*mạnh",
    r"vùng\s*nguy\s*hiểm", r"tọa\s*độ\s*tâm\s*bão", r"vĩ\s*độ\s*tâm\s*bão", r"kinh\s*độ\s*tâm\s*bão",
    r"cường\s*độ\s*gió", r"bão\s*(?:suy\s*yếu|mạnh\s*lên)", r"áp\s*thấp\s*mạnh\s*lên", r"tan\s*dần",
    r"đổ\s*bộ", r"đặc\s*biệt\s*nguy\s*hiểm\s*trên\s*biển", r"hành\s*lang\s*bão",
    r"sức\s*gió\s*mạnh\s*nhất\s*vùng\s*gần\s*tâm\s*bão", r"di\s*chuyển\s*theo\s*hướng\s*tây",
    r"gió\s*bão", r"mưa\s*hoàn\s*lưu", r"bão\s*khẩn\s*cấp", r"tin\s*bão\s*cuối\s*cùng",
    r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông", r"gió\s*giật\s*mạnh",
    r"áp\s*thấp\s*(?:mạnh\s*lên|suy\s*yếu)", r"cơn\s*bão\s*mạnh", r"tin\s*về\s*bão",
    r"xoáy\s*thuận", r"vùng\s*xoáy", r"áp\s*cao\s*cận\s*nhiệt", r"rãnh\s*thấp", r"t tổ\s*hợp\s*thời\s*tiết\s*xấu",
    r"bao\s*so\s*3", r"ap\s*thap\s*nhiet\s*doi", r"bản\s*tin\s*dự\s*báo\s*bão", r"cập\s*nhật\s*bão"
  ]),


  # 2) Nước dâng, Triều cường (Storm Surge / Tidal Flood - Decision 18 Art 3.5)
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"nước\s*dâng\s*do\s*(?:bão|áp\s*thấp\s*nhiệt\s*đới|gió\s*mạnh)", 
    r"nước\s*biển\s*dâng", r"đỉnh\s*triều", r"ngập\s*do\s*triều", r"sóng\s*lớn\s*đánh\s*tràn",
    r"dâng\s*cao\s*bất\s*thường", r"ngập\s*ven\s*biển", r"tràn\s*qua\s*kè", r"sóng\s*tràn",
    r"kỳ\s*triều\s*cường", r"triều\s*cao", r"đỉnh\s*triều\s*kỷ\s*lục", r"vượt\s*báo\s*động\s*triều"
  ]),

  # 3) Lũ, Ngập lụt, Sạt lở, Mưa lớn (Decision 18 Art 3.2: Mưa lớn is now here)
  ("flood_landslide", [
    r"lũ\s*quét", r"lũ\s*ống", r"lũ\s*bùn\s*đá", r"lũ\s*lịch\s*sử", r"lũ\s*đầu\s*nguồn",
    r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu", r"ngập\s*cục\s*bộ", r"biển\s*nước", r"ngập\s*(?:nhà|đường|phố)",
    r"sạt\s*lở\s*đất", r"trượt\s*lở\s*đất", r"sụt\s*lún", r"hố\s*tử\s*thần", r"nứt\s*toác", r"hàm\s*ếch",
    r"vỡ\s*đê", r"tràn\s*đê", r"sự\s*cố\s+đập", r"xả\s+lũ", r"hồ\s+chứa\s+thủy\s+điện", r"thủy\s*lợi",
    r"đỉnh\s*lũ", r"mực\s*nước\s*vượt\s*báo\s*động", r"lũ\s*dâng\s*cao", r"báo\s*động\s*(?:1|2|3|I|II|III)",
    r"chia\s*cắt", r"cô\s*lập", r"cuốn\s*trôi", r"vùi\s*lấp", r"sập\s*taluy", r"đất\s*đá\s*vùi\s*lấp",
    r"sạt\s*lở\s*bờ\s*(?:sông|biển)", r"sụt\s*lún\s*đất", r"nứt\s*đất", r"trượt\s*mái\s*đê", r"mưa\s*lũ",
    r"taluy\s*(?:âm|dương)", r"trượt\s*mái\s*sườn", r"sạt\s*trượt\s*ven\s*sông", r"điều\s*tiết\s*xả\s*lũ",
    r"lưu\s*lượng\s*về\s*hồ", r"ngập\s*lụt\s*trên\s*diện\s*rộng",
    # Mưa lớn patterns (Decision 18 requirements)
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"lượng\s*mưa", r"tổng\s*lượng\s*mưa",
    r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài", r"mưa\s*trên\s*\d+\s*mm", r"mưa\s*vượt\s*\d+\s*mm",
    r"mưa\s*kỷ\s*lục", r"mưa\s*như\s*trút", r"mưa\s*xối\s*xả", r"mưa\s*tầm\s*tã",
    # Hydrology details
    r"lũ\s*trên\s*các\s*sông", r"lũ\s*hạ\s*lưu", r"lũ\s*thượng\s*nguồn", r"lũ\s*lên\s*nhanh",
    r"vỡ\s*đập", r"sự\s*cố\s*hồ\s*đập", r"xả\s*tràn", r"xả\s*khẩn\s*cấp",
    r"sạt\s*lở\s*kè", r"hố\s*sụt", r"nứt\s*nhà"
  ]),

  # 4) Nắng nóng, Hạn hán, Xâm nhập mặn (Heat, Drought & Salinity - Decision 18 Art 3.3)
  ("heat_drought", [
    r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt\s*gay\s*gắt", r"nhiệt\s*độ\s*kỷ\s*lục",
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước\s*ngọt", r"nứt\s*nẻ", r"khát\s*nước",
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"độ\s*mặn", r"ranh\s*mặn", r"mặn\s*xâm\s*nhập\s*sâu",
    r"thiếu\s*nước\s*sinh\s*hoạt", r"xe\s*chở\s*nước\s*ngọt", r"mất\s*mùa\s*do\s*hạn\s*mặn",
    r"độ\s*mặn\s*phần\s*nghìn", r"cống\s*ngăn\s*mặn", r"đẩy\s*mặn", r"nước\s*nhiễm\s*mặn",
    r"đất\s*khô\s*cằn", r"cạn\s*hồ", r"hạn\s*hán\s*kéo\s*dài",
    r"chỉ\s*số\s*tia\s*cực\s*tím", r"chỉ\s*số\s*UV", r"ranh\s*mặn\s*4g/l", r"thiếu\s*hụt\s*nguồn\s*nước",
    r"dòng\s*chảy\s*kiệt", r"mùa\s*cạn", r"kiệt\s*nước", r"mực\s*nước\s*xuống\s*thấp",
    r"lấy\s*nước\s*ngọt", r"vận\s*hành\s*cống\s*ngăn\s*mặn"
  ]),

  # 5) Gió mạnh trên biển, Sương mù (Wind & Fog - Decision 18 Art 3.4)
  ("wind_fog", [
    r"gió\s*mạnh\s*trên\s*biển", r"gió\s*giật\s*mạnh", r"sóng\s*cao\s*\d+\s*mét",
    r"biển\s*động\s*mạnh", r"cấm\s*biển", r"cấm\s*tàu\s*thuyền", r"sóng\s*to\s*vây\s*quanh",
    r"sương\s*mù\s*dày\s*đặc", r"mù\s*quang", r"tầm\s*nhìn\s*xa\s*dưới\s*1km",
    r"không\s*khí\s*lạnh\s*tăng\s*cường", r"gió\s*mùa\s*đông\s*bắc",
    r"gió\s*cấp\s*Beaufort", r"gió\s*giật\s*cấp\s*\d+",
    r"tầm\s*nhìn\s*xa\s*hạn\s*chế", r"biển\s*động\s*rất\s*mạnh",
    r"biển\s*động", r"biển\s*động\s*mạnh", r"biển\s*động\s*rất\s*mạnh"
  ]),
  # 6) Thời tiết cực đoan (Lốc, Sét, Mưa đá, Rét hại - Decision 18 Art 3.6)
  ("extreme_other", [
    r"dông\s*lốc", r"lốc\s*xoáy", r"vòi\s*rồng", r"tố\s*lốc", r"mưa\s*đá", r"mưa\s*đá\s*trắng\s*trời",
    r"sét\s*đánh", r"giông\s*sét", r"mưa\s*to\s*kèm\s*theo\s*dông\s*lốc",
    r"rét\s*đậm\s*rét\s*hại", r"rét\s*hại", r"băng\s*giá", r"sương\s*muối", r"nhiệt\s*độ\s*xuống\s*dưới\s*0",
    r"rét\s*buốt", r"băng\s*giá\s*phủ\s*trắng",
    r"mưa\s*tuyết", r"tuyết\s*rơi"
  ]),
  # 7) Cháy rừng (Wildfire - Decision 18 Art 3.7)
  ("wildfire", [
    r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"PCCCR", r"cháy\s*thực\s*bì", r"lửa\s*rừng", r"cháy\s*lan\s*rộng",
    r"quy\s*chế\s*phòng\s*cháy\s*chữa\s*cháy\s*rừng", r"trực\s*cháy\s*rừng",
    r"cấp\s*cháy\s*rừng\s*cấp\s*(?:IV|V|4|5)", r"nguy\s*cơ\s*cháy\s*rừng\s*rất\s*cao",
    r"cháy\s*rừng\s*(?:phòng\s*hộ|đặc\s*dụng|sản\s*xuất)", r"đốt\s*thực\s*bì", r"đốt\s*nương"
  ]),
  # 8) Động đất, Sóng thần (Quake & Tsunami - Decision 18 Art 3.8-10)
  ("quake_tsunami", [
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn", r"sóng\s*thần", r"richter",
    r"tâm\s*chấn", r"chấn\s*tiêu", r"đất\s*rung\s*lắc", r"viện\s*vật\s*lý\s*địa\s*cầu",
    r"magnitude", r"rung\s*lắc\s*mạnh", r"thang\s*richter", r"cấp\s*báo\s*động\s*sóng\s*thần",
    r"\b(?:m|mw|ml)\s*[=:]?\s*\d+(?:[.,]\d+)?", r"độ\s*lớn\s*\d+(?:[.,]\d+)?", r"\d+(?:[.,]\d+)?\s*độ\s*richter"
  ])
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc",
  # Official Sources & Response
  r"trung\s*tâm\s*dự\s*báo", r"đài\s*khí\s*tượng", r"thủy\s*văn",
  r"ban\s*chỉ\s*huy", r"ban\s*chỉ\s*đạo", r"phòng\s*chống\s*thiên\s*tai", 
  r"sở\s*nn&ptnt", r"bộ\s*nông\s*nghiệp", r"ubnd",
  r"tin\s*bão", r"tin\s*áp\s*thấp", r"công\s*điện", r"hỏa\s*tốc",
  r"nắng\s*nóng", r"hạn\s*hán", r"xâm\s*nhập\s*mặn", r"khô\s*hạn", r"thiếu\s*nước",
  r"phân\s*bổ\s*nguồn\s*vốn", r"trích\s*ngân\s*sách", r"huy\s*động\s*lực\s*lượng",
  r"bốn\s*tại\s*chỗ", r"kịch\s*bản\s*ứng\s*phó", r"diễn\s*tập\s*mưa\s*lũ"
]

# RECOVERY Keywords for Event Stage Classification
RECOVERY_KEYWORDS = [
    r"khắc\s*phục", r"hỗ\s*trợ", r"cứu\s*trợ", r"ủng\s*hộ",
    r"thăm\s*hỏi", r"chia\s*sẻ", r"quyên\s*góp", r"tiếp\s*nhận",
    r"sửa\s*chữa", r"khôi\s*phục", r"tái\s*thiết", r"bồi\s*thường",
    r"bảo\s*hiểm", r"trợ\s*cấp", r"phân\s*bổ", r"nguồn\s*vốn",
    r"tái\s*định\s*cư", r"ổn\s*định\s*cuộc\s*sống", r"vệ\s*sinh\s*môi\s*trường",
    r"tổng\s*kết\s*thiệt\s*hại", r"dựng\s*lại\s*nhà"
]

# 1. ABSOLUTE VETO: Strictly Non-Disaster Contexts (Metaphor, Showbiz, Game, Sport)
# These will be blocked even if they contain "bão", "lũ", "sạt lở" keywords.
ABSOLUTE_VETO = [
  # Bão (Metaphorical)
  r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng|tin\s*đồn|showbiz)(?!\w)",
  r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
  r"bão\s*sao\s*kê", r"bão\s*(?:chấn\s*thương|sa\s*thải|thất\s*nghiệp)(?!\w)",
  r"(?<!thiên\s)bão\s*lòng", r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm)",
  r"siêu\s*bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu|quà\s*tặng)", 
  r"bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu)",
  r"bão\s*view", r"bão\s*comment", r"bão\s*order", r"bão\s*đơn",
  r"bão\s*hàng", r"bão\s*flash\s*sale", r"bão\s*voucher",
  r"siêu\s*dự\s*án", r"siêu\s*công\s*trình", r"siêu\s*xe",
  
  # Động đất / Lũ / Sóng (Metaphorical)
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ|điện\s*ảnh)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|MXH)",
  r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|V-pop|V-League|tình\s*trường)",
  r"cơn\s*lũ\s*(?:tin\s*giả|tội\s*phạm|rác\s*thải\s*số)",
  r"làn\s*sóng\s*(?:tẩy\s*chay|di\s*cư\s*số|công\s*nghệ)",

  # Sports
  r"bóng\s*đá", r"cầu\s*thủ", r"đội\s*tuyển", r"World\s*Cup", r"V-League", r"Sea\s*Games",
  r"AFF\s*Cup", r"huấn\s*luyện\s*viên", r"bàn\s*thắng", r"ghi\s*bàn", r"vô\s*địch",
  r"huy\s*chương", r"HCV", r"HCB", r"HCD",

  # Showbiz / Events / Arts
  r"showbiz", r"hoa\s*hậu", r"người\s*mẫu", r"ca\s*sĩ", r"diễn\s*viên", r"liveshow",
  r"scandal", r"drama", r"sao\s*Việt", r"khánh\s*thành", r"khai\s*trương", r"kỷ\s*niệm\s*ngày",
  r"kỷ\s*niệm\s*\d+\s*năm", r"chương\s*trình\s*nghệ\s*thuật", r"đêm\s*nhạc", r"đêm\s*diễn",
  r"tiết\s*mục", r"hợp\s*xướng", r"giao\s*lưu\s*nghệ\s*thuật", r"(?:phát|truyền)\s*hình\s*trực\s*tiếp\s*chương\s*trình",
  r"tuần\s*lễ\s*thời\s*trang", r"triển\s*lãm\s*nghệ\s*thuật",

  # Administrative / Legal / Political (Non-disaster)
  r"giấy\s*chứng\s*nhận", r"sổ\s*đỏ", r"quyền\s*sử\s*dụng\s*đất", r"giao\s*đất", r"chuyển\s*nhượng",
  r"công\s*chức", r"viên\s*chức", r"biên\s*chế", r"thẩm\s*quyền", r"hành\s*chính",
  r"quốc\s*phòng\s*toàn\s*dân", r"an\s*ninh\s*quốc\s*phòng", r"quân\s*sự", r"binh\s*sĩ",
  r"vụ\s*án", r"tranh\s*chấp", r"khiếu\s*nại", r"tố\s*cáo", r"điều\s*tra\s*viên", r"bị\s*can",
  r"kháng\s*chiến", r"đại\s*biểu\s*quốc\s*hội", r"tổng\s*tuyển\s*cử", r"chính\s*trị",
  r"phân\s*công\s*công\s*tác", r"nhân\s*sự", r"bầu\s*cử", r"nhiệm\s*kỳ",

  # Education
  r"đại\s*học", r"cao\s*đẳng", r"tuyển\s*sinh", r"học\s*bổng",
  r"tốt\s*nghiệp", r"thạc\s*sĩ", r"tiến\s*sĩ",
  
  # Health / Lifestyle
  r"ung\s*thư", r"tế\s*bào", r"tiểu\s*đường", r"huyết\s*áp", r"đột\s*quỵ",
  r"dinh\s*dưỡng", r"thực\s*phẩm", r"món\s*ăn", r"đặc\s*sản", r"giảm\s*cân", r"làm\s*đẹp",
  r"ngăn\s*ngừa\s*bệnh", r"sức\s*khỏe\s*sinh\s*sản",

  # Entertainment Misc
  r"tra\s*từ", r"từ\s*điển", r"bài\s*hát", r"ca\s*khúc", r"MV", r"triệu\s*view", r"top\s*trending",
  r"văn\s*hóa", r"nghệ\s*thuật", r"triển\s*lãm", r"khai\s*mạc", r"lễ\s*hội",
  r"tình\s*yêu\s*lan\s*tỏa", r"đánh\s*thức\s*những\s*lãng\s*quên",
  
  # Metaphors (Reinforced)
  r"bão\s*tố\s*cuộc\s*đời", r"sóng\s*gió\s*cuộc\s*đời", r"bão\s*tố\s*tình\s*yêu",
  r"bão\s*lòng",
  
  # E-commerce / Shopping
  r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng|order)",
  r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam|sân\s*cỏ|chuyển\s*nhượng|giảm\s*giá)",
  r"sóng\s*gió\s*(?:cuộc\s*đời|hôn\s*nhân)",
  r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|tẩy\s*chay|sa\s*thải)",
  r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)",
  r"cơn\s*sốt\s*(?:đất|giá|vé)",
  r"không\s*khí\s*lạnh\s*(?:nhạt|lùng|giá)",
  r"flash\s*sale", r"deal\s*sốc", r"siêu\s*sale", r"mega\s*sale",
  r"live\s*stream\s*bán\s*hàng", r"shopping\s*online",
  
  # Sports (Extended)
  r"(?:đi|về)\s*bão", r"ăn\s*mừng", r"cổ\s*vũ", r"xuống\s*đường",
  r"bóng\s*đá", r"U\d+", r"đội\s*tuyển", r"SEA\s*Games", r"AFF\s*Cup",
  r"vô\s*địch", r"huy\s*chương", r"bàn\s*thắng", r"ghi\s*bàn", r"HLV", r"sân\s*cỏ",
  r"tỉ\s*số", r"chung\s*kết", r"ngược\s*dòng",
  
  # Social Media / Influencer
  r"sốt\s*(?:MXH|mạng\s*xã\s*hội)", r"viral", r"trend", r"trending",
  r"livestream", r"streamer", r"youtuber", r"tiktoker", r"influencer",
  r"follow", r"subscriber", r"sub\s*kênh", r"idol", r"fandom",
  
  # Crypto / NFT / Fintech
  r"bitcoin", r"crypto", r"blockchain", r"NFT", r"token",
  r"ví\s*điện\s*tử", r"ví\s*crypto", r"sàn\s*coin", r"đào\s*coin",
  
  # Gaming
  r"game", r"gaming", r"PUBG", r"Liên\s*Quân", r"esports",
  r"streamer\s*game", r"nạp\s*game", r"skin\s*game",
  
  # Dating / Relationship
  r"hẹn\s*hò", r"tình\s*trường", r"chia\s*tay", r"tan\s*vỡ",
  r"yêu\s*đương", r"tình\s*yêu\s*sét\s*đánh",
  
  # Netflix / Streaming
  r"Netflix", r"phim\s*bộ", r"series", r"tập\s*cuối", r"ending",
  
  # Electric Vehicles / Tech Products
  r"VinFast", r"xe\s*điện", r"iPhone", r"Samsung", r"ra\s*mắt\s*sản\s*phẩm",
  
  # Smart Home / IoT
  r"nhà\s*thông\s*minh", r"smart\s*home",
  
  # Travel / Tourism
  r"combo\s*du\s*lịch", r"săn\s*vé\s*máy\s*bay",
  
  # Cosmetics / Beauty
  r"mỹ\s*phẩm", r"skincare", r"làm\s*đẹp\s*da", r"review\s*mỹ\s*phẩm",
  
  # COVID-related metaphors (not actual disaster)
  r"làn\s*sóng\s*(?:COVID|covid|dịch)\s*thứ",
  r"bão\s*COVID", r"bão\s*F0",

  # User Feedback Blocklist (Enhanced 2025)
  # Social / Good Samaritan / Daily Incidents
  r"nhặt\s*được", r"rơi\s*(?:ví|tiền|vàng)", r"trả\s*lại\s*(?:tiền|tài\s*sản)", r"giao\s*nộp.*công\s*an",
  r"thang\s*máy", r"mắc\s*kẹt.*thang\s*máy", r"móc\s*túi", r"trộm\s*cắp", r"cướp\s*giật",
  
  # Festivities / Tourism / Showbiz / Culture / Cooking
  r"check-in", r"giáng\s*sinh", r"noel", r"nhà\s*thờ", r"phố\s*đi\s*bộ",
  r"biển\s*người", r"chen\s*chân", r"liveshow", r"scandal", r"drama",
  r"du\s*lịch", r"lễ\s*hội", r"văn\s*hóa", r"nghệ\s*thuật", r"trưng\s*bày", r"triển\s*lãm",
  r"làng\s*hoa", r"cây\s*kiểng", r"sinh\s*vật\s*cảnh", r"khai\s*hội", r"tour", r"lữ\s*hành",
  r"ẩm\s*thực", r"món\s*ngon", r"đặc\s*sản", r"nấu\s*ăn", r"đầu\s*bếp", r"nhà\s*hàng",
  r"thi\s*bơi", r"đua\s*thuyền.*(hội|lễ)", r"bơi\s*lội.*(thi|giải)",
  
  # Infrastructure / Traffic / Accidents
  r"thông\s*xe", r"cao\s*tốc", r"ùn\s*ứ.*(?:lễ|tết|cuối\s*tuần)", r"bến\s*xe",
  r"thi\s*công.*dự\s*án", r"tiến\s*độ.*dự\s*án", r"xe\s*tải", r"xe\s*khách", r"va\s*chạm\s*xe",
  r"tai\s*nạn\s*giao\s*thông", r"tông\s*xe", r"tông\s*chết", r"không\s*có\s*vùng\s*cấm",
  r"phạt\s*nguội", r"giấy\s*phép\s*lái\s*xe", r"đăng\s*kiểm",
  
  # Urban/Social Fire (Not Forest)
  r"cơ\s*trưởng", r"phi\s*công",
  r"cháy\s*nhà", r"cháy\s*xưởng", r"cháy\s*quán", r"cháy\s*xe", r"chập\s*điện", r"nổ\s*bình\s*gas",
  
  # Administrative / Political / Finance
  r"HĐND", r"hội\s*đồng\s*nhân\s*dân", r"tiếp\s*xúc\s*cử\s*tri", r"kỳ\s*họp",
  r"Quốc\s*hội", r"Chính\s*phủ", r"nghị\s*quyết", r"nghị\s*định", r"bổ\s*nhiệm",
  r"ngoại\s*giao", r"hội\s*kiến", r"tiếp\s*kiến", r"đối\s*ngoại", r"quyết\s*sách",
  r"Đảng\s*ủy", r"Đảng\s*viên", r"bí\s*thư(?!\s*đã\s*chỉ\s*đạo)",
  r"giảm\s*nghèo", r"xây\s*dựng\s*nông\s*thôn\s*mới", r"chỉ\s*số\s*giá\s*tiêu\s*dùng",
  r"đầu\s*tư", r"kinh\s*doanh", r"thị\s*trường", r"bất\s*động\s*sản", r"giá\s*đất",
  r"lương\s*cơ\s*bản", r"tăng\s*lương", r"lương\s*hưu", r"nghỉ\s*hưu", r"lộ\s*trình\s*lương",
  r"BHYT", r"bhyt", r"hiến\s*máu", r"giọt\s*máu", r" runner", r"giải\s*chạy",
  r"hóa\s*đơn", r"ngân\s*sách", r"quy\s*hoạch", r"đấu\s*giá", r"đấu\s*thầu",
  
  # Violence / Crimes / Legal
  r"bạo\s*hành", r"đánh\s*đập", r"hành\s*hung", r"bắt\s*giữ", r"vụ\s*án", r"điều\s*tra",
  r"khởi\s*tố", r"truy\s*tố", r"xét\s*xử", r"bị\s*cáo", r"tử\s*hình", r"chung\s*thân",
  r"bắt\s*cóc", r"lừa\s*đảo", r"trục\s*lợi", r"giả\s*chết", r"karaoke", r"ma\s*túy", r"tội\s*phạm",
  r"lãnh\s*đạo\s*tỉnh", r"thanh\s*tra", r"kiến\s*nghị\s*xử\s*lý", r"sai\s*phạm",
  r"quân\s*đội.*biểu\s*diễn", r"tàu\s*ngầm", r"phi\s*đội", r"phi\s*trường", r"vé\s*máy\s*bay",
  r"CSGT", r"cảnh\s*sát\s*giao\s*thông", r"tổ\s*công\s*tác", r"quái\s*xế",
  r"MTTQ", r"Mặt\s*trận\s*Tổ\s*quốc", r"kinh\s*tế\s*cửa\s*khẩu",
  r"AstroWind", r"Tailwind\s*CSS", r"\.docx\b", r"\.pdf\b", r"\.doc\b",
  r"đuối\s*nước", r"hồ\s*bơi", r"ngập\s*mặn.*vùng\s*nuôi",
    r"xe\s*lu", r"xe\s*cẩu", r"xe\s*ủi", r"xe\s*ben", r"mất\s*thắng", r"mất\s*phanh",
    r"khai\s*thác\s*đá", r"hoàng\s*thành", r"di\s*tích", r"di\s*sản", r"trùng\s*tu", r"phục\s*hồi(?!\s*sản\s*xuất)",
    r"không\s*tiền\s*mặt", r"khoáng\s*sản", r"ăn\s*gian", r"bền\s*vững", r"đô\s*thị\s*bền\s*vững",
    r"biên\s*giới", r"ngoại\s*giao", r"hội\s*đàm", r"hợp\s*tác\s*quốc\s*tế",
    r"khen\s*thưởng", r"lao\s*động\s*giỏi", r"thi\s*đua", r"ăn\s*mừng",
    r"thâu\s*tóm", r"đất\s*vàng", r"thùng\s*rượu", r"phát\s*triển\s*đô\s*thị",
    r"hộ\s*dân(?!\s*bị\s*cô\s*lập)(?!\s*bị\s*thiệt\s*hại\s*nặng)",
    r"hộ\s*dân(?!\s*bị\s*cô\s*lập)(?!\s*bị\s*thiệt\s*hại\s*nặng)",
    r"câu\s*cá", r"câu\s*trúng", 

    # Human Interest / Social Stories (False Positives for "vùi lấp", "cuốn trôi")
    r"được\s*nhận\s*nuôi", r"nhận\s*nuôi", r"bỏ\s*rơi", r"trẻ\s*sơ\s*sinh", r"bé\s*sơ\s*sinh",
    r"tắm\s*sông", r"tắm\s*suối", r"tắm\s*biển", r"đi\s*bơi", r"đuối\s*nước(?!\s*do\s*lũ)",
    # Removed rigid 'mất tích' veto to prevent false negatives in disaster reports
    r"lan\s*tỏa(?!\s*lâm\s*nguy)",
    r"lan\s*tỏa(?!\s*lâm\s*nguy)",
    
    # New Daily Life Noise (Strict Block)
    r"xổ\s*số", r"vietlott", r"trúng\s*số", r"giải\s*đặc\s*biệt", r"vé\s*số",
    r"ngoại\s*tình", r"đánh\s*ghen", r"ly\s*hôn", r"ly\s*thân", r"tiểu\s*tam",
    r"tước\s*bằng\s*lái", r"tước\s*giấy\s*phép", r"phạt\s*nguội", r"đăng\s*kiểm",
    r"giảm\s*cân", r"tăng\s*cân", r"thực\s*phẩm\s*chức\s*năng", r"làm\s*đẹp", r"trắng\s*da"
]

# 2. CONDITIONAL VETO: Noise that can co-exist with disaster (Economy, Accident, etc.)
# These will be blocked ONLY if there is NO specific hazard score or metrics.
CONDITIONAL_VETO = [
  # Economy / Real Estate
  r"bất\s*động\s*sản", r"cơn\s*sốt\s*đất", r"sốt\s*đất", r"đất\s*nền", r"chung\s*cư",
  r"dự\s*án\s*nhà\s*ở", r"shophouse", r"biệt\s*thự", r"đấu\s*giá\s*đất",
  r"lãi\s*suất", r"tín\s*dụng", r"ngân\s*hàng", r"tỉ\s*giá", r"VN-Index", r"chứng\s*khoán", r"cổ\s*phiếu",
  r"giá\s*(?:vàng|heo|cà\s*phê|lúa|xăng|dầu|trái\s*cây)", r"tăng\s*giá", r"giảm\s*giá", r"hạ\s*nhiệt\s*(?:giá|thị\s*trường)",
  r"xuất\s*khẩu", r"nhập\s*khẩu", r"GDP", r"tăng\s*trưởng\s*kinh\s*tế",
  r"thủ\s*tục", r"trao\s*quyền",
  
  # Tech / Internet / AI (Moved from Absolute Veto)
  r"Google", r"Facebook", r"Youtube", r"TikTok", r"Zalo\s*Pay", r"tính\s*năng", r"cập\s*nhật",
  r"công\s*nghệ\s*số", r"dữ\s*liệu", r"\bAI\b", r"trí\s*tuệ\s*nhân\s*tạo",
  
  # Traffic Accidents (Distinguish from Disaster)
  r"tai\s*nạn\s*giao\s*thông", r"va\s*chạm\s*xe", r"tông\s*xe", r"tông\s*chết",
  r"xe\s*tải", r"xe\s*khách", r"xe\s*đầu\s*kéo", r"xe\s*container", r"xe\s*buýt",
  r"hướng\s*dẫn", r"bí\s*quyết", r"cách\s*xử\s*lý", r"quy\s*trình(?!\s*xả\s*lũ)", r"mẹo\s*hay",
  r"biện\s*pháp(?!\s*khẩn\s*cấp)", r"kỹ\s*năng(?!\s*cứu\s*hộ)", r"phòng\s*tránh",
  r"(?<!thiên\s)tai\s*nạn\s*liên\s*hoàn", r"vi\s*phạm\s*nồng\s*độ\s*cồn",
  
  # Fire / Explosion (Urban/Industrial - Not Forest)
  r"lửa\s*ngùn\s*ngụt", 
  r"bà\s*hỏa", r"chập\s*điện", r"nổ\s*bình\s*gas",
  r"cháy\s*nhà", r"nhà\s*bốc\s*cháy", r"hỏa\s*hoạn\s*nhà\s*dân",
  r"cháy.*quán", r"cháy.*xưởng", r"cháy.*xe",
  r"bom\s*mìn", r"vật\s*liệu\s*nổ", r"thuốc\s*nổ", r"đạn\s*pháo", r"chiến\s*tranh", r"thời\s*chiến",
  
  # Pollution / Environment 
  r"quan\s*trắc\s*môi\s*trường", r"rác\s*thải",
  r"chất\s*lượng\s*không\s*khí", r"(?<!\w)AQI(?!\w)", r"bụi\s*mịn", r"chỉ\s*số\s*không\s*khí",
  
  # Construction / Maintenance
  r"giàn\s*giáo", r"sập\s*giàn\s*giáo", r"tai\s*nạn\s*lao\s*động", r"an\s*toàn\s*lao\s*động",
  r"công\s*trình\s*xây\s*dựng", r"thi\s*công",
  r"thiết\s*kế\s*nội\s*thất", r"trần\s*thạch\s*cao", r"la\s*phông", r"tấm\s*ốp",
  r"trang\s*trí\s*nhà", r"nhà\s*đẹp", r"căn\s*hộ\s*mẫu", r"chung\s*cư\s*cao\s*cấp", r"biệt\s*thự",
  r"bảo\s*trì", r"bảo\s*dưỡng", r"nghiệm\s*thu", r"lắp\s*đặt", r"hệ\s*thống\s*kỹ\s*thuật",
  r"tủ\s*điện", r"thẩm\s*duyệt\s*PCCC", r"tập\s*huấn\s*PCCC", r"diễn\s*tập\s*PCCC",
  
  # Traffic Admin
  r"xe\s*cứu\s*thương", r"biển\s*số\s*xe", r"đấu\s*giá\s*biển\s*số",
  r"đăng\s*kiểm", r"giấy\s*phép", r"phạt\s*nguội",
  
  # Finance / Banking (Specific)
  r"vốn\s*điều\s*lệ", r"tăng\s*vốn", r"cổ\s*đông", r"lợi\s*nhuận", r"doanh\s*thu",
  r"ADB", r"WB", r"IMF", r"ODA",
  
  # Aviation (Moved from Absolute)
  r"sân\s*bay", r"hàng\s*không", r"hạ\s*cánh", r"cất\s*cánh",
  
  # Crime / Legal
  r"án\s*mạng", r"giết\s*người", r"cướp\s*giật", r"trộm\s*cắp", r"cát\s*tặc", r"khai\s*thác\s*cát",
  r"hung\s*thủ", r"nghi\s*phạm",
  r"truy\s*nã", r"đối\s*tượng\s*lừa\s*đảo", r"đối\s*tượng\s*ma\s*túy", r"đối\s*tượng\s*truy\s*nã",
  r"bắt\s*giữ", r"bị\s*can", r"xử\s*phạt", r"xét\s*xử", r"phiên\s*tòa",
  r"tử\s*hình", r"án\s*tù", r"tội\s*phạm",

  # Political / Diplomatic (Metaphorical)
  r"bão\s*(?:ngoại\s*giao|chính\s*trị)", 
  r"rung\s*chấn\s*chính\s*trường",
  
  # Social Vices / Crime (Anti-Disaster Context)
  r"mại\s*dâm", r"mua\s*bán\s*dâm", r"gái\s*bán\s*dâm", r"khách\s*mua\s*dâm",
  r"chứa\s*chấp", r"môi\s*giới\s*mại\s*dâm", r"tú\s*bà", r"động\s*lắc",
  r"đánh\s*bạc", r"sát\s*phạt", r"sới\s*bạc", r"cá\s*độ",
  r"ma\s*túy", r"thuốc\s*lắc", r"pay\s*lak", r"bay\s*lắc",
  
  # Military Sports / Ceremonies (Distinguish from Rescue)
  r"liên\s*đoàn\s*võ\s*thuật", r"võ\s*thuật\s*quân\s*đội",
  r"đại\s*hội\s*nhiệm\s*kỳ", r"đại\s*hội\s*thể\s*dục\s*thể\s*thao",
  r"hội\s*thao", r"hội\s*thi\s*quân\s*sự", r"giải\s*đấu",
  r"vovinam", r"karate", r"taekwondo", r"võ\s*cổ\s*truyền", r"judo", r"sambo",
  
  # === SIMPLIFIED: ONLY FILTER TRULY UNRELATED CONTENT ===
  # System is for "comprehensive disaster risk reporting" including:
  #   - Active disasters, warnings, forecasts
  #   - Recovery, aftermath, reconstruction  
  #   - Infrastructure investment for disaster prevention
  #   - Weather forecasts and updates
  # ONLY filter spam, entertainment, pure politics, animals, etc.
  
  # Pure Spam/English/Tech Content  
  r"how\s*to.*(?:customize|template|branding|tutorial)",
  r"(?:MBA|PhD|bachelor).*(?:degree|program)",
  r"(?:cách|hướng\s*dẫn|thủ\s*thuật).*(?:tách|gộp|nén|chuyển|sửa).*(?:file|tệp|PDF|Word|Excel|ảnh|video)",
  r"diễn\s*đàn.*làm\s*cha\s*mẹ",
  
  # Animals (NOT wildlife/forest fire related)
  r"cá\s*sấu.*(?:xổng\s*chuồng|cắn\s*người)",
  r"thú\s*cưng", r"nuôi\s*(?:chó|mèo|chim|cá)",
  r"(?:bàn\s*giao|tiếp\s*nhận).*(?:cá\s*thể|động\s*vật|chim).*(?:quý\s*hiếm|sách\s*đỏ|rừng)",
  r"chim\s*công", r"voọc", r"khỉ",
  
  # Spam/Tech/Transportation (Unrelated)
  r"metro.*(?:miễn\s*phí|vé.*tết|trung\s*tâm|bến\s*thành)",
  r"taxi\s*bay", 
  r"iPhone.*(?:ra\s*mắt|bán)", r"Samsung.*(?:ra\s*mắt|bán)",
  r"camera.*(?:ngụy\s*trang|quay\s*lén)",
  
  # Pure Politics/Admin (NOT disaster-related)
  r"khơi\s*dậy\s*khát\s*khao\s*cống\s*hiến",
  r"(?:đại\s*hội|hội\s*nghị).*(?:Đảng|đảng\s*bộ)(?!.*(?:thiên\s*tai|lũ|bão))",
  r"(?:tổng\s*kết|thi\s*hành|sửa\s*đổi).*(?:hiến\s*pháp|luật\s*đất\s*đai)(?!.*(?:thiên\s*tai|lũ|bão))",
  r"bầu\s*cử.*(?:quốc\s*hội|hội\s*đồng)",
  r"thăng\s*quân\s*hàm",
  
  # Awards (NOT disaster heroes)
  r"(?:danh\s*hiệu|huân\s*chương).*Lao\s*động(?!.*(?:cứu|thiên\s*tai))",
  r"chúc\s*mừng.*(?:giáng\s*sinh|năm\s*mới|lễ)",
  
  # War-related (NOT natural disasters)
  r"(?:quả\s*bom|bom\s*nặng).*\d+\s*kg(?!.*nước)",  # Exclude "bom nước"
  r"vật\s*liệu\s*nổ", r"đạn\s*pháo.*chiến\s*tranh",
  
  # Social Media Metaphors (NOT real disasters)
  r"gây\s*bão.*(?:mạng\s*xã\s*hội|MXH)",
  r"(?:clip|video).*gây\s*bão.*(?:cộng\s*đồng|dư\s*luận)",
  r"chủ\s*quán.*hành\s*động\s*gây",
  
  # Education (NOT disaster-related)
  r"tuyển\s*sinh.*đại\s*học",
  r"(?:học\s*sinh|sinh\s*viên).*(?:tốt\s*nghiệp|nhận.*học\s*bổng)(?!.*(?:sau\s*lũ|vùng\s*lũ))",
  
  # Medical Success Stories (NOT disaster casualties)
  r"phẫu\s*thuật.*thành\s*công(?!.*(?:sau.*(?:lũ|bão)|nạn\s*nhân))",
  r"khám\s*bệnh\s*miễn\s*phí(?!.*(?:vùng\s*lũ|bão))",
  
  # Pure Entertainment/Lifestyle
  r"hoa\s*hậu", r"người\s*mẫu", r"ca\s*sĩ.*(?:MV|album)",
  r"phim.*(?:chiếu|Netflix)", r"bài\s*hát\s*mới",
  r"đỗ\s*xe.*(?:trước\s*cửa|lòng\s*đường)",

  # Urban Fires (Industrial/Residential - NOT forest) - Removed to avoid FP.
  # Non-disaster fires won't match positive rules anyway.
  
  # Traffic Accidents (NOT disaster related)
  r"tai\s*nạn.*(?:giao\s*thông|liên\s*hoàn|xe\s*khách|xe\s*tải)",
  r"tông.*(?:xe|chết|bị\s*thương)(?!.*(?:lũ|bão))",
  
  # Market/Business (NOT disaster impact)
  r"(?:giá|thị\s*trường).*(?:vàng|đô|chứng\s*khoán|bất\s*động\s*sản)",
  r"(?:lãi|lỗ|doanh\s*thu).*(?:tỷ|triệu)(?!.*(?:thiệt\s*hại|hỗ\s*trợ))",
]

# 2. SOFT NEGATIVE: Potential False Positive (Politics, Admin, Economy)
# Can be overridden if HAZARD SCORE is high enough.
SOFT_NEGATIVE = [
  r"đại\s*hội", r"bầu\s*cử", r"ứng\s*cử", r"đại\s*biểu", r"quốc\s*hội",
  r"mặt\s*trận\s*tổ\s*quốc", r"MTTQ", r"ủy\s*ban", r"kiểm\s*tra", r"giám\s*sát",
  r"thăng\s*quân\s*hàm", r"bổ\s*nhiệm", r"kỷ\s*luật", r"nghị\s*quyết",
  r"thủ\s*tướng", r"bộ\s*trưởng", r"lãnh\s*đạo", r"ngoại\s*giao", r"hội\s*đàm",
  r"khởi\s*công", r"khánh\s*thành", r"nghiệm\s*thu", r"bản\s*tin\s*cuối\s*ngày",
  r"an\s*ninh\s*mạng", r"chuyển\s*đổi\s*số", r"công\s*nghệ", r"startup",
  r"giải\s*thưởng", r"vinh\s*danh", r"kỷ\s*niệm", r"văn\s*hóa\s*văn\s*nghệ",
  # Tai nạn (Soft Negative - pass if caused by storm/flood)
  r"tai\s*nạn\s*giao\s*thông", r"xe\s*tải", r"xe\s*container", r"xe\s*khách",
  # Fire non-wildfire
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng)",
  
  # Missing Persons (moved from Absolute Veto to Soft/Conditional)
  r"mất\s*tích(?!\s*do\s*lũ)(?!\s*do\s*bão)(?!\s*khi\s*đánh\s*bắt)",
  r"thanh\s*nhiên\s*mất\s*tích", r"nữ\s*sinh\s*mất\s*tích", r"học\s*sinh\s*mất\s*tích",
]

# Combined Negative List for backward compatibility (used in NO_ACCENT generation)
DISASTER_NEGATIVE = ABSOLUTE_VETO + CONDITIONAL_VETO + SOFT_NEGATIVE

# Removed old compiled patterns
POLLUTION_TERMS = [r"ô\s*nhiễm", r"AQI", r"PM2\.5", r"bụi\s*mịn"]

# Pre-compute unaccented patterns for matching against t0 (canonical text)
DISASTER_RULES_NO_ACCENT = []
for label, pats in DISASTER_RULES:
    nops = [risk_lookup.strip_accents(p) for p in pats]
    DISASTER_RULES_NO_ACCENT.append((label, nops))

DISASTER_CONTEXT_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_NEGATIVE]

# === OPTIMIZATION: PRE-COMPILE REGEX ===
# Compile patterns once at module level to avoid recompilation overhead
logger.info("Compiling NLP regex patterns...")
DISASTER_RULES_RE = []
for label, pats in DISASTER_RULES:
    compiled_acc = [re.compile(p, re.IGNORECASE) for p in pats]
    # Compile unaccented version only if safe
    compiled_no = []
    for p in pats:
        if safe_no_accent(p):
            p_no = risk_lookup.strip_accents(p)
            compiled_no.append(re.compile(p_no, re.IGNORECASE))
        else:
            compiled_no.append(None) # Marker for unsafe
            
    DISASTER_RULES_RE.append((label, compiled_acc, compiled_no))

ABSOLUTE_VETO_RE = [re.compile(p, re.IGNORECASE) for p in ABSOLUTE_VETO]
CONDITIONAL_VETO_RE = [re.compile(p, re.IGNORECASE) for p in CONDITIONAL_VETO]
SOFT_NEGATIVE_RE = [re.compile(p, re.IGNORECASE) for p in SOFT_NEGATIVE]
# DISASTER_CONTEXT is just list of strings, let's compile it too (though unused in code logic below yet, wait, Context Matches uses it)
# Currently Context Matches loop iterates DISASTER_CONTEXT enum string. Let's pre-compile.
DISASTER_CONTEXT_RE = [re.compile(p, re.IGNORECASE) for p in DISASTER_CONTEXT]
POLLUTION_TERMS_RE = [re.compile(p, re.IGNORECASE) for p in POLLUTION_TERMS]

# Sensitive Locations compiled list
SENSITIVE_LOCATIONS_RE = [re.compile(rf"(?<!\w){re.escape(loc)}(?!\w)", re.IGNORECASE) for loc in sources.SENSITIVE_LOCATIONS]

# Weight configuration (Externalize? No, keep here for simplicity)
WEIGHT_RULE = 3.0
WEIGHT_IMPACT = 2.0
WEIGHT_AGENCY = 2.0
WEIGHT_SOURCE = 1.0
WEIGHT_PROVINCE = 0.5
WEIGHT_SENSITIVE_LOCATION = 1.0 # New weight for sensitive locations
logger.info("NLP regex compilation complete.")

# Build impact extraction patterns with named groups and qualifier support
def _build_impact_patterns():
    """
    Build regex patterns for extracting impact metrics.
    Uses regexes defined in IMPACT_KEYWORDS.
    Returns (patterns_acc, patterns_no).
    """
    patterns_acc = {}
    patterns_no = {}
    
    for impact_type, data in IMPACT_KEYWORDS.items():
        regex_list = data.get("regex", [])
        patterns_acc[impact_type] = []
        patterns_no[impact_type] = []
        for r_str in regex_list:
            try:
                # Accented version
                p_acc = re.compile(r_str, re.IGNORECASE)
                patterns_acc[impact_type].append(p_acc)
                
                # Unaccented version (if safe)
                if safe_no_accent(r_str):
                    r_no = risk_lookup.strip_accents(r_str)
                    patterns_no[impact_type].append(re.compile(r_no, re.IGNORECASE))
            except re.error as e:
                print(f"Error compiling regex for {impact_type}: {r_str} -> {e}")
                
    return patterns_acc, patterns_no

IMPACT_PATTERNS, IMPACT_PATTERNS_NO = _build_impact_patterns()
RE_AGENCY = re.compile(r"(Tổng\s+cục\s+KTTV|Cục\s+Quản\s+lý\s+đê\s+điều|Ban\s+Chỉ\s+đạo.*?PCTT|Trung\s+tâm\s+Dự\s+báo.*?KTTV|Viện\s+Vật\s+lý\s+Địa\s+cầu|Tổng\s+cục\s+Lâm\s+nghiệp|Trung\s+tâm\s+báo\s+tin\s+động\s+đất)", re.IGNORECASE)

WEIGHT_RULE = 3.0
WEIGHT_IMPACT = 3.5
WEIGHT_AGENCY = 2.0
WEIGHT_SOURCE = 1.0
WEIGHT_PROVINCE = 0.5


def _to_int(num_str: str) -> int:
    if not num_str: return 0
    s = str(num_str).strip().lower()
    if re.match(r"^\d+$", s): return int(s)
    if s in NUMBER_WORDS: return int(NUMBER_WORDS[s])
    s2 = s.replace(".", "").replace(",", "")
    if s2.isdigit(): return int(s2)
    return 0

def _to_float(num_str: str) -> float:
    if not num_str: return 0.0
    s = str(num_str).strip().lower()
    if s in NUMBER_WORDS: return float(NUMBER_WORDS[s])
    try:
        if "," in s and "." in s:
            return float(s.replace(".", "").replace(",", "."))
        if "," in s: return float(s.replace(",", "."))
        if "." in s:
            parts = s.rsplit(".", 1)
            if len(parts) == 2 and len(parts[1]) == 3:
                return float(s.replace(".", ""))
            return float(s)
        return float(s)
    except: return 0.0

# Helper functions removed (using risk_lookup)

# CORE LOGIC

def extract_provinces(text: str) -> List[dict]:
    """
    Extract multiple provinces/regions with location info using finditer.
    Returns list of dicts: {name, type, span, match}
    Matches against both t (accented) and t0 (unaccented).
    """
    matches = []
    t, t0 = risk_lookup.canon(text or "")
    
    for item in PROVINCE_REGEXES:
        # Try Accented first
        found_iter = list(item["re_acc"].finditer(t))
        if not found_iter:
             # Try Unaccented if no accented match found for this regex
             found_iter = list(item["re_no"].finditer(t0))
        
        for m in found_iter:
            matches.append({
                "name": item["name"],  # The normalized name
                "type": item["type"],
                "span": m.span(),
                "match": m.group(0)
            })
            
    # Sort by position
    matches.sort(key=lambda x: x["span"][0])
    return matches

def extract_province(text: str) -> str:
    """Legacy wrapper: returns the Single Best province found.
    Prioritizes specific Province over Region.
    """
    all_hits = extract_provinces(text)
    
    # 1. Return first specific province
    for h in all_hits:
        if h["type"] == "province":
            return h["name"]
            
    # 2. Return first region
    for h in all_hits:
        if h["type"] == "region":
            return h["name"]
            
    return "unknown"

def extract_disaster_metrics(text: str) -> dict:
    metrics = {}
    
    # 1. Rainfall (mm)
    val = risk_lookup.extract_max_mm(text)
    if val: metrics["rainfall_mm"] = val
    
    # 2. Temperature (C)
    val = risk_lookup.extract_max_temp(text)
    if val: metrics["temperature_c"] = val
    
    # 3. Salinity (per mille)
    val = risk_lookup.extract_max_salinity(text)
    if val: metrics["salinity_per_mille"] = val
    
    # 4. Wind (Beaufort) - includes conversion from km/h, m/s
    val = risk_lookup.extract_beaufort_max(text)
    if val: metrics["wind_level"] = val
    
    # 5. Water Level (m)
    val = risk_lookup.extract_water_level(text)
    if val: metrics["water_level_m"] = val
    
    # 6. Duration (days)
    val = risk_lookup.extract_duration_days_count(text)
    if val > 0: metrics["duration_days"] = float(val)
    
    # 7. Earthquake (Magnitude)
    val = risk_lookup.extract_quake_mag(text)
    if val: metrics["earthquake_magnitude"] = val

    return metrics

def compute_disaster_signals(text: str) -> dict:
    # 1. Standardize Normalization using risk_lookup.canon
    t, t0 = risk_lookup.canon(text or "")

    rule_matches = []
    hazard_counts = {}
    # Check Rules (Iterate both accented and unaccented)
    # OPTIMIZED: Use DISASTER_RULES_RE
    for i, (label, compiled_acc, compiled_no) in enumerate(DISASTER_RULES_RE):
        count = 0
        # Match Accented on t (compiled)
        matched_label = False
        for pat_re in compiled_acc:
            if pat_re.search(t):
                count += 1
                matched_label = True
        
        if matched_label:
            rule_matches.append(label)
            hazard_counts[label] = count

    hazard_score = len(rule_matches)
    rule_score = WEIGHT_RULE if hazard_score else 0.0

    impact_hits = []
    for k, data in IMPACT_KEYWORDS.items():
        terms = data.get("terms", [])
        for kw in terms:
            if kw.lower() in t:
                impact_hits.append((k, kw)); break
    impact_score = WEIGHT_IMPACT if impact_hits else 0.0

    agency_match = bool(RE_AGENCY.search(t))
    agency_score = WEIGHT_AGENCY if agency_match else 0.0

    # Province Extraction (Enhanced)
    prov_hits = extract_provinces(text)
    specific_prov_found = any(h["type"] == "province" for h in prov_hits)
    
    best_prov = "unknown"
    for h in prov_hits:
        if h["type"] == "province": best_prov = h["name"]; break
    if best_prov == "unknown":
        for h in prov_hits:
            if h["type"] == "region": best_prov = h["name"]; break
    
    province_score = WEIGHT_PROVINCE if specific_prov_found else 0.0

    # Source keywords match
    ambiguous = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
    non_ambiguous_hits = []
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if kl in t and kl not in ambiguous:
            non_ambiguous_hits.append(kl)
    source_score = float(len(non_ambiguous_hits)) * WEIGHT_SOURCE

    score = rule_score + impact_score + agency_score + source_score + province_score

    # Context Matches (Optimized)
    context_hits = []
    # Use DISASTER_CONTEXT_RE
    for i, pat_re in enumerate(DISASTER_CONTEXT_RE):
        matched = False
        if pat_re.search(t): matched = True
        
        # Unaccented Check for Context (Optional, apply same safe logic if needed)
        # For now, let's skip to save CPU unless strictly needed, context is supplementary
        
        if matched: 
            # Get original string for logging
            context_hits.append(DISASTER_CONTEXT[i])
        
    # Pollution Terms (Optimized)
    for pat_re in POLLUTION_TERMS_RE:
        if pat_re.search(t): context_hits.append("pollution_term") # Just marker
    
    # Sensitive Locations Check
    sensitive_found = []
    for i, pat_re in enumerate(SENSITIVE_LOCATIONS_RE):
        if pat_re.search(t):
            loc_name = sources.SENSITIVE_LOCATIONS[i]
            sensitive_found.append(loc_name)
            context_hits.append(f"sensitive_loc:{loc_name}")
            
    context_score = len(context_hits)

    # NEGATIVE CHECKS (Split & Optimized)
    # 1. Absolute Veto
    absolute_veto = False
    negative_matches = []
    for pat_re in ABSOLUTE_VETO_RE:
        if pat_re.search(t): 
            absolute_veto = True
            negative_matches.append(pat_re.pattern)
            break
    
    # 2. Conditional Veto
    conditional_veto = False
    if not absolute_veto:
        for pat_re in CONDITIONAL_VETO_RE:
             if pat_re.search(t):
                 conditional_veto = True
                 negative_matches.append(pat_re.pattern)
                 break
            
    # Soft Negative (Optimized)
    soft_negative = False
    if not absolute_veto and not conditional_veto:
        for pat_re in SOFT_NEGATIVE_RE:
            if pat_re.search(t):
                soft_negative = True
                negative_matches.append(pat_re.pattern)
                break

    metrics = extract_disaster_metrics(text)
    impact_details = extract_impact_details(text)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": hazard_score,
        "hazard_counts": hazard_counts,
        "context_score": context_score,
        "sensitive_locations": sensitive_found,
        "absolute_veto": absolute_veto,
        "conditional_veto": conditional_veto,
        "hard_negative": absolute_veto, # Legacy compat
        "soft_negative": soft_negative,
        "negative_hit": negative_matches,
        "metrics": metrics,
        "impact_details": impact_details,
        "is_province_match": best_prov != "unknown",
        "is_agency_match": agency_match is not None,
        "is_sensitive_location": len(sensitive_found) > 0
    }

def determine_event_stage(text: str) -> str:
    """Classify event stage: WARNING, IMPACT, or RECOVERY"""
    t_lower = text.lower()
    
    # 1. Recovery
    for kw in RECOVERY_KEYWORDS:
        if re.search(kw, t_lower): return "RECOVERY"
        
    # 2. Warning / Forecast
    warning_sig = [
        r"dự\s*báo", r"cảnh\s*báo", r"tin\s*bão", r"áp\s*thấp", 
        r"công\s*điện", r"khẩn\s*cấp", r"nguy\s*cơ", r"chủ\s*động"
    ]
    for kw in warning_sig:
        if re.search(kw, t_lower): return "WARNING"
        
    # 3. Default to IMPACT (Actual event happening)
    return "IMPACT"


def contains_disaster_keywords(text: str, title: str = "", trusted_source: bool = False) -> bool:
    """
    Stricter Filtering (v4):
    - Separate Title and Body context.
    - Block diplomatic/admin noise.
    - Veto metaphors and social news aggressively.
    """
    # Use full text for signal detection but remember title importance
    full_text = f"{title}\n{text}" if title else text
    sig = compute_disaster_signals(full_text)
    t_lower = full_text.lower()
    title_lower = title.lower() if title else ""
    
    # 0. VIP Whitelist (Critical Warnings that bypass ALL filters)
    # Rescue valid storm warnings/aid that might get caught by aggressive filters
    for vip in sources.VIP_TERMS:
        # Check title first, it's more definitive
        if title and re.search(vip, title, re.IGNORECASE):
            return True
        if re.search(vip, text, re.IGNORECASE):
            return True

    # 0.1. DEFINITIVE EVENTS PASS (Strong Identifiers)
    # If the title clearly mentions a Named Storm, Quake, Tsunami, or Surge -> PASS
    # This comes BEFORE Veto to save valid events that might have some noise.
    if title:
        # Storm Naming: "Bão số 3", "Bão Yagi", "Áp thấp nhiệt đới"
        if re.search(r"(?:bão|áp thấp).*?(?:số\s*\d+|[A-ZĐ][a-zà-ỹ]+)", title_lower, re.IGNORECASE):
            return True
        # Quake/Tsunami: "Động đất", "Sóng thần", "Rung chấn"
        if re.search(r"(?:động đất|sóng thần|rung chấn)", title_lower, re.IGNORECASE):
            return True
        # Surge/Hail: "Triều cường", "Mưa đá", "Lũ quét" (Strong definitive hazards)
        if re.search(r"(?:triều cường|mưa đá|lũ quét|sạt lở đất|lũ ống)", title_lower, re.IGNORECASE):
            return True
        # Forecast/Official Warning Pass (e.g. "Bản tin dự báo...", "Đài Khí tượng...")
        # Only if title explicitly targets forecast/warning
        if re.search(r"^(?:bản)?\s*tin\s*(?:dự\s*báo|cảnh\s*báo|khí\s*tượng|thủy\s*văn)", title_lower, re.IGNORECASE):
             return True
        if "đài khí tượng" in title_lower or "trung tâm dự báo" in title_lower:
             return True

    # 1. ABSOLUTE VETO (The "Shield")
    # Block immediately if matched (Metaphors, Showbiz, Game, Sport, Crime, Admin)
    # [STRICTER] Apply veto to TITLE separately. If title has veto, REJECT immediately.
    if title:
        title_sig = compute_disaster_signals(title)
        if title_sig["absolute_veto"]:
            return False

    if sig["absolute_veto"]:
        # Only allow bypass if very strong hazard or real metrics (excluding duration)
        real_metrics_dict = {k: v for k, v in sig["metrics"].items() if k != "duration_days"}
        has_strong_signal = sig["hazard_score"] >= 3 or bool(real_metrics_dict)
        if not has_strong_signal:
            return False

    # 2. CONDITIONAL VETO
    if sig["conditional_veto"]:
        has_real_signal = sig["hazard_score"] > 0 or bool(sig["metrics"])
        if not has_real_signal:
            return False
        
    # 2b. Hazard Keyword Found (Stricter Logic)
    # Require HIGH-CONFIDENCE support if hazard signal is weak (only 1 match).
    has_strong_support = (
        sig["context_score"] >= 2  
        or bool(sig["metrics"])    # Real weather metrics
        or bool(sig["agency"])     # Official agency
        # Require impact AND at least 1 context word (location/agency) to avoid accident noise
        or (len(sig["impact_hits"]) >= 1 and (sig["context_score"] >= 1 or sig["is_province_match"]))
    )
    
    if sig["hazard_score"] >= 2:
        return True
    
    if sig["hazard_score"] == 1:
        # If only 1 hazard type, require strong support
        if has_strong_support:
            return True
        # If no strong support but from trusted source, allow with SMALL support
        # (Avoid "Flower news" by requiring at least a province OR 1 context keyword)
        if trusted_source:
             if sig["is_province_match"] or sig["context_score"] >= 1:
                 return True
        # Reject others
        return False

    # 3. Warning/Forecast Signatures
    # Even if exact hazard key is tricky, if we see "Dự báo" + "mưa lớn/bão/lũ", we take it.
    # [STRICTER] REQUIRE hazard_score > 0 for forecast logic to avoid non-weather warnings.
    forecast_keys = r"(dự\s*báo|cảnh\s*báo|tin\s*(?:không\s*khí\s*lạnh|bão|lũ|mưa|nắng\s*nóng))"
    if sig["hazard_score"] > 0 and re.search(forecast_keys, full_text, re.IGNORECASE):
        # High confidence if in title
        if title_lower and re.search(forecast_keys, title_lower):
             return True
        # Medium confidence if in body with support
        if sig["context_score"] >= 2 or re.search(r"(thời\s*tiết|thiên\s*tai|nguy\s*hiểm)", full_text, re.IGNORECASE):
            return True

    # 4. Metrics Fallback (e.g. "Mưa 200mm", "Sức gió cấp 12")
    # [STRICTER] Only if we have at least 1 hazard keyword OR context.
    # [REFINED] Do NOT use duration_days as the sole metric for fallback, as it's common in social/recruitment news.
    real_metrics = {k: v for k, v in sig["metrics"].items() if k != "duration_days"}
    if real_metrics: 
        if sig["hazard_score"] > 0 or sig["context_score"] > 0:
            return True
        
    # No keywords, no metrics -> Reject
    return False


def diagnose(text: str) -> dict:
    sig = compute_disaster_signals(text)
    reason = f"Score {sig['score']:.1f} < 3.0"
    if sig["negative_hit"]: reason = "Negative keyword match"
    elif sig.get("rule_matches"): reason = f"Matched rules: {sig['rule_matches']}" # Actually valid?
    elif sig["hazard_score"] < 1: reason = "No disaster keywords"
    elif sig["context_score"] < 1: reason = "No context keywords"
    
    return {"score": sig["score"], "signals": sig, "reason": reason}

def title_contains_disaster_keyword(title: str) -> bool:
    """
    Stricter title check using regex word boundaries and negative veto.
    """
    if not title: return False
    t = title.lower()
    
    # Negative veto first
    # [OPTIMIZED] Only use ABSOLUTE_VETO for titles. 
    # Do NOT use Soft/Conditional veto here because titles like "Khởi công hồ chứa" (Soft Neg) might be relevant.
    for pat_re in ABSOLUTE_VETO_RE:
        if pat_re.search(t):
            return False
            
    # Positive check
    for kw in SOURCE_DISASTER_KEYWORDS:
        # Use regex to ensure word boundary for short keywords
        kl = kw.lower()
        if len(kl) <= 4:
            pattern = rf"(?<!\w){re.escape(kl)}(?!\w)"
            if re.search(pattern, t, re.IGNORECASE):
                return True
        else:
            if kl in t:
                return True
    return False

def extract_impacts(text: str) -> dict:
    """
    Wrapper for extract_impact_details to maintain compatibility.
    Maps detailed extraction to flat structure used by crawler.
    """
    details = extract_impact_details(text)
    res = {
        "deaths": None,
        "missing": None,
        "injured": None,
        "damage_billion_vnd": 0.0,
        "agency": None
    }
    
    # 1. Human casualties (List of ints)
    for k in ["deaths", "missing", "injured"]:
        if k in details:
            # crawler._get_impact_value handles lists (takes max or sum? Usually finding max single report is safer for dups, but let's pass list)
            res[k] = details[k]

    # 2. Financial Damage (Convert to Billion VND)
    if "damage" in details:
        total_billion = 0.0
        for item in details["damage"]:
            val = item.get("num", 0)
            u = item.get("unit", "").lower()
            # "tỷ" -> billion
            if "tỷ" in u or "ty" in u:
                total_billion += val
            # "triệu" -> million -> 0.001 billion
            elif "triệu" in u or "trieu" in u:
                total_billion += val / 1000.0
        
        if total_billion > 0:
            res["damage_billion_vnd"] = total_billion
            
    # 3. Agency (Not in details, extracting separately)
    m = RE_AGENCY.search(text)
    if m:
        res["agency"] = m.group(1)
        
    return res

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

def classify_disaster(text: str, title: str = "") -> dict:
    """
    Classify disaster type based on rule matches.
    Simplified version: No complex risk level assessment (User Request).
    """
    # Combine text for better signal detection
    full_text = f"{title}\n{text}" if title else text
    # Weighted matching: Title matches count for 2, Body for 1
    t_title, _ = risk_lookup.canon(title or "")
    t_body, _ = risk_lookup.canon(text or "")
    
    hazard_weights = {}
    for label, compiled_acc, _ in DISASTER_RULES_RE:
        weight = 0
        # Title matches (Priority 2)
        for pat in compiled_acc:
            if pat.search(t_title):
                weight += 2
        
        # Body matches (Priority 1)
        # To avoid overcounting, we only count the body if not already perfectly matched in title or just sum them up
        # Summing is safer to detect "dominant" topics
        for pat in compiled_acc:
            if pat.search(t_body):
                weight += 1
        
        if weight > 0:
            hazard_weights[label] = weight

    # ROOT CAUSE BOOSTING & TIE-BREAKING (Decision 18/2021 Implementation):
    
    # 1. Storm Boosting vs Wind/Fog: If any storm-core (bão, ATNĐ) exists, prioritize storm.
    if "storm" in hazard_weights:
        # Boost named storms
        if re.search(r"(?:bão|áp thấp|ATNĐ|ATND).*?(?:số\s*\d+|[A-ZĐ][a-zà-ỹ]+)", t_title, re.IGNORECASE):
            hazard_weights["storm"] += 10
        # Tie-break: Reduce wind_fog if storm is present
        if "wind_fog" in hazard_weights:
            hazard_weights["wind_fog"] -= 5

    # 2. Surge vs Saltwater Tie-break: Decision 18 Clause 3.3 and 3.5.
    # Salinity (heat_drought) vs Coastal surge (storm_surge).
    salinity_markers = ["mặn", "độ mặn", "xâm nhập mặn", "ranh mặn"]
    if "storm_surge" in hazard_weights and "heat_drought" in hazard_weights:
        if any(sm in full_text.lower() for sm in salinity_markers):
             hazard_weights["heat_drought"] += 5  # Favor Salinity
             hazard_weights["storm_surge"] -= 2
        else:
             hazard_weights["storm_surge"] += 3   # Favor Surge/Tide

    # 3. Wildfire Context Filter: Must have forest indicators to avoid general fire news.
    if "wildfire" in hazard_weights:
        forest_indicators = [
            "rừng", "thực bì", "khoảnh", "tiểu khu", "lâm phần", "lâm nghiệp", "diện tích", "thảm thực vật"
        ]
        if not any(fi in full_text.lower() for fi in forest_indicators):
            # Penalty if it's just "PCCCR" without forest context
            hazard_weights["wildfire"] -= 10

    # 4. Quake Boosting: "Động đất" + magnitude/scale
    if "quake_tsunami" in hazard_weights:
        if re.search(r"(?:động đất|rung chấn|dư chấn|độ lớn).*?(?:độ|richter|magnitude|M|MW|ML)\s*\d", t_title, re.IGNORECASE):
            hazard_weights["quake_tsunami"] += 10

    PRIO = [
        "quake_tsunami",
        "storm_surge",
        "storm",
        "flood_landslide", 
        "wildfire", 
        "heat_drought", 
        "wind_fog", 
        "extreme_other"
    ]

    if not hazard_weights:
        # Check for Recovery/Relief keywords as fallback
        rel_text = f"{title}\n{text}".lower()
        primary = "unknown"
        if any(re.search(kw, rel_text) for kw in RECOVERY_KEYWORDS):
            primary = "recovery"
        elif any(re.search(kw, rel_text, re.IGNORECASE) for kw in sources.VIP_TERMS):
             primary = "relief_aid"
             
        return {
            "primary_type": primary,
            "hazard_weights": {},
            "is_disaster": False
        }
    
    # Select Primary: Highest weighted score first, then PRIO position
    sorted_hazards = sorted(
        hazard_weights.items(),
        key=lambda item: (-item[1], PRIO.index(item[0]) if item[0] in PRIO else 99)
    )
    
    primary = sorted_hazards[0][0]
    if hazard_weights.get(primary, 0) <= 0:
        primary = "unknown"

    return {
        "primary_type": primary,
        "hazard_weights": hazard_weights,
        "is_disaster": primary not in ["unknown", "recovery", "relief_aid"]
    }


def summarize(text: str, max_len: int = 220) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_len: return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"



def extract_impact_details(text: str) -> dict:
    """
    Extract specific impact metrics using regex patterns.
    Matches positional groups from user-defined regexes.
    Handles negation and float values.
    Supports accent-insensitive matching.
    """
    impacts = {}
    
    # Use canonical versions (accented and unaccented)
    t, t0 = risk_lookup.canon(text or "")
    
    for impact_type in IMPACT_KEYWORDS.keys():
        found_items = []
        seen_spans = [] # track (start, end) to avoid duplicates from t and t0
        
        # Pass 1: Accented (t)
        # Pass 2: Unaccented (t0) using IMPACT_PATTERNS_NO
        passes = [
            (t, IMPACT_PATTERNS.get(impact_type, [])),
            (t0, IMPACT_PATTERNS_NO.get(impact_type, []))
        ]
        
        for text_to_search, patterns in passes:
            for pat in patterns:
                for m in pat.finditer(text_to_search):
                    # Check for overlap with already found spans
                    start, end = m.span()
                    is_duplicate = False
                    for s_start, s_end in seen_spans:
                        # If overlap found
                        if max(start, s_start) < min(end, s_end):
                            is_duplicate = True
                            break
                    if is_duplicate: continue
                    seen_spans.append((start, end))

                    # NEGATION CHECK
                    pre_text = text_to_search[max(0, start - 100):start]
                    post_text = text_to_search[end:min(len(text_to_search), end + 100)]
                
                    # Check specific negations for this type + general negations
                    specific_negs = NEGATION_TERMS.get(impact_type, [])
                    general_negs = NEGATION_TERMS.get("general", [])
                    all_negs = specific_negs + general_negs
                    
                    if any(neg in pre_text for neg in all_negs) or any(neg in post_text for neg in all_negs):
                        continue

                    # Parse Named Groups for precision
                    # Supports: ?P<num>, ?P<unit>, ?P<qualifier>
                    gd = m.groupdict()
                    g_num = gd.get("num")
                    g_unit = gd.get("unit")
                    g_qual = gd.get("qualifier")
                    
                    val = 0
                    unit = g_unit if g_unit else None
                    
                    if g_num:
                        # Try parsing as number (including range support)
                        g_clean = re.sub(r"[^0-9–-]", "", g_num) # Keep digits and hyphens
                        if g_clean and (g_clean[0].isdigit() or g_clean.startswith("-")):
                             # If it's a range like "3-5"
                             if "-" in g_num or "–" in g_num:
                                 nums = re.findall(r"\d+", g_num)
                                 if nums:
                                     val = [int(n) for n in nums]
                             else:
                                 val = _to_int(g_num)
                                 
                             # Specific override for float types if needed (damage, agriculture)
                             # If unit is ha, hecta, tỷ, triệu, or temperature/salinity (handled elsewhere mostly)
                             if impact_type in ("damage", "agriculture") and isinstance(val, int):
                                  try:
                                      if ',' in g_num:
                                          val = float(g_num.replace(',', '.'))
                                      elif '.' in g_num and len(g_num.split('.')[1]) != 3: 
                                          val = float(g_num)
                                  except:
                                      pass
                    
                    if val:
                        vals = val if isinstance(val, list) else [val]
                        for v in vals:
                            if impact_type in ("deaths", "missing", "injured"):
                                 found_items.append(v)
                            else:
                                 item = {"num": v}
                                 if unit: item["unit"] = unit
                                 found_items.append(item)

        
        # Special case for text numbers ("một nghìn", "hàng trăm")
        if impact_type == "damage":
             # Text numbers check with Multiplier
             # Supports: "ba nghìn", "hàng trăm", "vài chục"
             pattern = r"\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|chục|trăm|hàng|vài)\s*(nghìn|ngàn|triệu|tỷ|trăm|chục)\s*(?:ngôi|căn|cái)?\s*(nhà|hộ|công trình|kios)"
             m = re.search(pattern, t) # Accented
             if not m:
                 # Try unaccented on t0 with stripped pattern
                 m = re.search(risk_lookup.strip_accents(pattern), t0)
                 
             if m:
                 num_map = {
                     "một": 1, "mot": 1, "hai": 2, "ba": 3, "bốn": 4, "bon": 4, "năm": 5, "nam": 5,
                     "sáu": 6, "sau": 6, "bảy": 7, "bay": 7, "tám": 8, "tam": 8, "chín": 9, "chin": 9, "mười": 10, "muoi": 10,
                     "chục": 10, "chuc": 10, "trăm": 100, "tram": 100, "nghìn": 1000, "nghin": 1000, "ngàn": 1000, "ngan": 1000,
                     "hàng": 2, "hang": 2, "vài": 3, "vai": 3
                 }
                 mul_map = {
                     "chục": 10, "chuc": 10, "trăm": 100, "tram": 100, "nghìn": 1000, "nghin": 1000, "ngàn": 1000, "ngan": 1000, 
                     "triệu": 1000000, "trieu": 1000000, "tỷ": 1000000000, "ty": 1000000000
                 }
                 
                 w_num = m.group(1)
                 w_mul = m.group(2)
                 
                 base_num = num_map.get(w_num, 1)
                 multiplier = mul_map.get(w_mul, 1)
                 
                 final_val = base_num * multiplier
                 found_items.append({"num": final_val, "unit": "nhà"})
             # "Một" for single house damage
             elif ("một" in t or "mot" in t0) and any(x in t or risk_lookup.strip_accents(x) in t0 for x in ["ngôi nhà", "căn nhà", "thiệt hại một nhà"]):
                 # Check if we already have a house damage match
                 already_has_house = False
                 for obj in found_items:
                     u = obj.get("unit", "").lower()
                     if any(x in u for x in ["nhà", "hộ", "căn", "ngôi"]):
                         already_has_house = True
                         break
                 if not already_has_house:
                     found_items.append({"num": 1, "unit": "nhà"})
        
        if found_items:
            # Deduplicate
            if impact_type in ("deaths", "missing", "injured"):
                raw_nums = sorted(list(set([int(x) for x in found_items])))
                if len(raw_nums) > 1:
                    # Case 1: Subset indicators like "trong đó", "bao gồm" -> Take Max (Total)
                    if any(x in t for x in ["trong đó", "bao gồm", "gồm", "trong số", "gồm có"]):
                        impacts[impact_type] = [max(raw_nums)]
                    # Case 2: Current status indicators like "hiện còn", "vẫn còn" -> Take Min (Current)
                    elif any(x in t for x in ["hiện còn", "vẫn còn", "còn"]):
                        impacts[impact_type] = [min(raw_nums)]
                    else:
                        impacts[impact_type] = raw_nums
                else:
                    impacts[impact_type] = raw_nums
            else:
                seen = set()
                unique_res = []
                for obj in found_items:
                    s = f"{obj['num']}_{obj.get('unit','')}"
                    if s not in seen:
                        seen.add(s)
                        unique_res.append(obj)
                impacts[impact_type] = unique_res
                
    return impacts
