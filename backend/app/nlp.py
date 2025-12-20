import re
import unicodedata
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from . import sources
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS
from . import risk_lookup

# CONSTANTS & CONFIG

# Impact keywords
IMPACT_KEYWORDS = {
    "deaths": {
        "terms": [
            "chết", "tử vong", "tử nạn", "tử thương", "thiệt mạng", "thương vong", "nạn nhân tử vong", "số người chết", "làm chết", "cướp đi sinh mạng", "tìm thấy thi thể", "không qua khỏi", 
            "tử vong tại chỗ", "tử vong sau khi", "đã tử vong", "chết cháy", "tử vong do ngạt", "ngạt khói", "ngạt khí", "chết đuối", "đuối nước", "ngạt nước", "bị cuốn trôi tử vong", "bị vùi lấp tử vong", "bị chôn vùi tử vong"
        ],
        "regex": [
            r"\b(ít nhất|tối thiểu|khoảng|hơn)?\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|học sinh|công nhân|chiến sĩ)\s*(chết|tử vong|thiệt mạng|tử nạn|tử thương|thương vong)\b",
            r"\b(làm|khiến)\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|học sinh)\s*(chết|tử vong|thiệt mạng|thương vong)\b",
            r"\b(tìm thấy|phát hiện)\s*(thi thể|xác)\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|học sinh)?\b",
            r"\b(cướp đi sinh mạng|tước đi sinh mạng)\s*(của)?\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu)\b"
        ]
    },

    "missing": {
        "terms": [
            "mất tích", "thất lạc", "chưa tìm thấy", "chưa tìm được", "chưa thấy","mất liên lạc", "không liên lạc được", "không thể liên lạc","chưa xác định tung tích", "không rõ tung tích", "chưa rõ số phận","bị cuốn trôi", 
            "trôi mất", "bị nước cuốn", "bị lũ cuốn","bị vùi lấp", "bị chôn vùi", "mắc kẹt", "bị mắc kẹt","đang tìm kiếm", "tổ chức tìm kiếm", "công tác tìm kiếm","tìm kiếm cứu nạn", "cứu nạn", "cứu hộ", "tìm kiếm cứu hộ"
        ],
        "regex": [
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|công nhân|thuyền viên|ngư dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(bị|đã)?\s*(mất tích|mất liên lạc|chưa tìm thấy|chưa liên lạc được|không rõ tung tích|cuốn trôi|lũ cuốn|nước cuốn|vùi lấp|mắc kẹt)\b",
            r"\b(tìm kiếm|chưa tìm thấy|chưa liên lạc được|mất liên lạc|vẫn chưa liên lạc được|chưa xác định tung tích|chưa rõ tung tích)\s*(với|cho|with)?\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|công nhân|nhóm)?\b",
            r"\b(cuốn trôi|cuốn|vùi lấp|chôn vùi)\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu)\b"
        ]
    },

    "injured": {
        "terms": [
            "bị thương", "bị thương nặng", "bị thương nhẹ", "trọng thương", "xây xát", "chấn thương", "đa chấn thương", "gãy xương", "bỏng", "bị bỏng", "bất tỉnh", "ngất xỉu", "sốc", "ngộ độc", "khó thở", "nhập viện", "đưa đi bệnh viện", 
            "đưa vào bệnh viện", "cấp cứu", "điều trị", "sơ cứu", "chuyển viện", "đang điều trị", "được điều trị"
        ],
        "regex": [
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu|ca)\s*(bị thương|trọng thương|nhập viện|cấp cứu|đa chấn thương|thương tích|xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(làm|khiến|gây)\s*(b|trọng thương|bị bỏng|bất tỉnh|gãy xương|đa chấn thương)\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu)\b",
            r"\b(đưa|chuyển|sơ cứu|điều trị cho|cấp cứu cho|ghi nhận|có)(?:[^0-9]{0,30})?\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân|em|cháu)(?:[^a-z0-9]{0,10})?\s*(đi|tới|bị|do)?\s*(cấp cứu|bệnh viện|viện|xây xát|bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(bị thương|bị xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(người|nạn nhân)\b"
        ]
    },

    "marine": {
        "terms": [
            "chìm tàu", "tàu chìm", "đắm tàu", "tàu đắm", "lật tàu", "lật thuyền", "trôi dạt", "dạt vào bờ", "mất tín hiệu", "mất liên lạc", "không liên lạc được", "gặp nạn trên biển", "gặp nạn", 
            "tai nạn đường thủy", "đánh chìm", "chìm", "đắm", "lật", "trôi", "tàu cá", "tàu hàng", "tàu du lịch", "sà lan", "thuyền", "cano", "ghe", "ghe chài", "ngư dân", "thuyền viên", "cứu nạn trên biển", 
            "tìm kiếm trên biển", "lai dắt", "kéo về bờ", "cứu nạn", "cứu hộ"
        ],
        "regex": [
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\s*(bị|đã)?\s*(chìm|đắm|lật|trôi dạt|mất liên lạc|hư hỏng|mất tích|gặp nạn)\b", 
            r"\b(chìm|đắm|lật|trôi dạt|đánh chìm|lai dắt|cứu hộ|cứu nạn)\s*(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\b",
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(ngư dân|thuyền viên)(?:[^0-9]{0,20})?\s*(b|đã)?\s*(mất liên lạc|mất tích|trôi dạt|gặp nạn)\b",
            r"\b(mất liên lạc|cứu hộ|cứu nạn|liên lạc được)\s*(với|cho|with)?\s*(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|ngư dân|thuyền viên|thuyền|phương tiện|sà lan)\b"
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
            r"\b(thiệt hại|tổn thất)(?:[^0-9]{0,30})?\s*(?:ước|ước tính|khoảng|lên tới|hơn|trên|ban đầu|\s)*(\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?)\s*(tỷ|triệu)\s*(đồng|VND)\b",
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)(?:[^0-9]{0,20})?\s*(bị|đã|có)?\s*(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|sạt lở|gãy đổ|vùi lấp|nứt|sụt lún|sửa|sửa chữa|chia cắt|cô lập|cháy|mất điện|mất nước|ảnh hưởng|trôi|ngập úng)\b",
            r"\b(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|cuốn trôi|vùi lấp|làm sập|gãy đổ|nứt|sụt lún|sửa|chia cắt|cô lập|cháy|mất điện|mất nước|ảnh hưởng|trôi|ngập úng)(?:[^0-9]{0,20})?\s*(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)\b",
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(căn nhà|ngôi nhà|hộ|nhà|căn)(?:[^0-9]{0,10})?\s*(có|bị)?\s*(nhà)?\s*(bị)?\s*(sạt lở|sập|trôi|lũ cuốn|vùi lấp|chia cắt|cô lập|cháy|mất điện|mất nước|ảnh hưởng)\b"
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
            # “cấm đường quốc lộ 6”, “đóng đường tỉnh lộ 159”
            r"\b(cấm|đóng|tạm dừng|tạm ngưng)\s*(đường|lưu thông)\b",
            r"\b(sơ tán|di dời|di tản)\s*(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(sơ tán|di dời|di tản)\s*(khẩn cấp)?\s*(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(người|hộ|hộ dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(phải|cần|đã)?\s*(sơ tán|di dời|di tản)\b"
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
            # hectares: 12 ha lúa / 2,5 ha hoa màu / 5 sào ruộng
            # Added "sào", "tấn" (for yield loss)
            r"\b(\d+(?:[.,]\d+)?)\s*(ha|hecta|héc ta|sào|tấn)\b",
            # counts: 3.000 con gia cầm chết
            r"\b(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(con)\s*(trâu|bò|lợn|gà|vịt|gia súc|gia cầm)\b",
            # aquaculture: 3 lồng bè (Num Unit)
            r"\b(\d+(?:\s*[–-]\s*\d+)?)\s*(lồng bè|lồng|bè)\b"
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
    "damage": ["không gây thiệt hại", "chưa có thiệt hại", "không có thiệt hại về tài sản"],
    "general": ["bác bỏ", "tin đồn", "dự kiến", "diễn tập", "kịch bản", "giả định", "trước khi"]
}

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
    "vài": 3, "hàng chục": 20, "một trăm": 100, "hai trăm": 200, "ba trăm": 300, 
    "năm trăm": 500, "nghìn": 1000, "một nghìn": 1000,
}

# 34 PROVINCES MAPPING (NEW SAU SAP NHAP)
# Format: New_Name -> List of Old_Names to match in text
PROVINCE_MAPPING = {
    # Miền Bắc
    "Hà Nội": ["Hà Nội", "HN", "Ha Noi"],
    "Hà Giang": ["Hà Giang"],
    "Cao Bằng": ["Cao Bằng"],
    "Bắc Kạn": ["Bắc Kạn"],
    "Tuyên Quang": ["Tuyên Quang"],
    "Lào Cai": ["Lào Cai"],
    "Điện Biên": ["Điện Biên"],
    "Lai Châu": ["Lai Châu"],
    "Sơn La": ["Sơn La"],
    "Yên Bái": ["Yên Bái"],
    "Hòa Bình": ["Hòa Bình"],
    "Thái Nguyên": ["Thái Nguyên"],
    "Lạng Sơn": ["Lạng Sơn"],
    "Quảng Ninh": ["Quảng Ninh"],
    "Bắc Giang": ["Bắc Giang"],
    "Phú Thọ": ["Phú Thọ"],
    "Vĩnh Phúc": ["Vĩnh Phúc"],
    "Bắc Ninh": ["Bắc Ninh"],
    "Hải Dương": ["Hải Dương"],
    "Hải Phòng": ["Hải Phòng"],
    "Hưng Yên": ["Hưng Yên"],
    "Thái Bình": ["Thái Bình"],
    "Hà Nam": ["Hà Nam"],
    "Nam Định": ["Nam Định"],
    "Ninh Bình": ["Ninh Bình"],
    # Miền Trung
    "Thanh Hóa": ["Thanh Hóa"],
    "Nghệ An": ["Nghệ An"],
    "Hà Tĩnh": ["Hà Tĩnh"],
    "Quảng Bình": ["Quảng Bình"],
    "Quảng Trị": ["Quảng Trị"],
    "Thừa Thiên Huế": ["Thừa Thiên Huế", "Huế", "TT-Huế", "T.T.Huế"],
    "Đà Nẵng": ["Đà Nẵng"],
    "Quảng Nam": ["Quảng Nam"],
    "Quảng Ngãi": ["Quảng Ngãi"],
    "Bình Định": ["Bình Định"],
    "Phú Yên": ["Phú Yên"],
    "Khánh Hòa": ["Khánh Hòa"],
    "Ninh Thuận": ["Ninh Thuận"],
    "Bình Thuận": ["Bình Thuận"],
    # Tây Nguyên
    "Kon Tum": ["Kon Tum"],
    "Gia Lai": ["Gia Lai"],
    "Đắk Lắk": ["Đắk Lắk", "Dak Lak"],
    "Đắk Nông": ["Đắk Nông", "Dak Nong"],
    "Lâm Đồng": ["Lâm Đồng"],
    # Miền Nam
    "TP Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn"],
    "Bình Phước": ["Bình Phước"],
    "Tây Ninh": ["Tây Ninh"],
    "Bình Dương": ["Bình Dương"],
    "Đồng Nai": ["Đồng Nai"],
    "Bà Rịa - Vũng Tàu": ["Bà Rịa", "Vũng Tàu", "BR-VT", "BRVT"],
    "Long An": ["Long An"],
    "Tiền Giang": ["Tiền Giang"],
    "Bến Tre": ["Bến Tre"],
    "Trà Vinh": ["Trà Vinh"],
    "Vĩnh Long": ["Vĩnh Long"],
    "Đồng Tháp": ["Đồng Tháp"],
    "An Giang": ["An Giang"],
    "Kiên Giang": ["Kiên Giang"],
    "Cần Thơ": ["Cần Thơ"],
    "Hậu Giang": ["Hậu Giang"],
    "Sóc Trăng": ["Sóc Trăng"],
    "Bạc Liêu": ["Bạc Liêu"],
    "Cà Mau": ["Cà Mau"],
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
  # 1) Bão & áp thấp nhiệt đới
  ("storm", [
    # Bão (loại trừ: đi bão, bão giá, bão mạng, bão lòng, cơn bão số... khi nói về giá cả)
    r"(?<!\w)(?<!đi\s)(?<!dự\s)bão(?!\sgiá)(?!\smạng)(?!\slòng)(?!\stài\s)(?!\stín\s)(?!\w)",
    r"bão\s*số\s*\d+",
    r"siêu\s*bão", r"hoàn\s*lưu\s*bão", r"tâm\s*bão",
    r"đổ\s*bộ", r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông",
    # Áp thấp (loại trừ: huyết áp thấp, cao áp thấp)
    r"(?<!huyết\s)áp\s*thấp\s*nhiệt\s*đới",
    r"(?<!huyết\s)(?<!cao\s)áp\s*thấp(?!\w)",
    r"(?<!\w)ATNĐ(?!\w)", r"vùng\s*áp\s*thấp",
    r"xoáy\s*thuận\s*nhiệt\s*đới", r"nhiễu\s*động\s*nhiệt\s*đới",
    r"gió\s*mạnh\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
  ]),


  # 2) Nước dâng, Triều cường (Moved UP to prioritize over flood)
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng",
    r"đỉnh\s*triều", r"ngập\s*do\s*triều", r"sóng\s*lớn\s*đánh\s*tràn"
  ]),

  # 3) Lũ, Ngập lụt, Sạt lở, Sụt lún (Grouped as flood_landslide)
  ("flood_landslide", [
    # Mưa lớn (driver)
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"mưa\s*cực\s*lớn",
    r"mưa\s*đặc\s*biệt\s*lớn", r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài",
    r"mưa\s*kỷ\s*lục", r"mưa\s*cực\s*đoan", r"mưa\s*như\s*trút",
    # Lũ / Ngập (Strict boundaries)
    r"(?<!\w)lũ(?!\w)(?!\s*lượt)(?!\s*khách)",
    r"(?<!\w)lụt(?!\w)", r"lũ\s*lụt", r"lũ\s*lớn", r"lũ\s*lịch\s*sử", r"lũ\s*dâng",
    r"(?<!\w)ngập(?!\w)(?!\s*đầu\s*tư)(?!\s*tràn)(?!\s*trong)(?!\s*ngụa)(?!\s*mặn)",
    r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu",
    r"ngập\s*cục\s*bộ", r"nước\s*lên\s*nhanh", r"mực\s*nước\s*dâng", r"đỉnh\s*lũ",
    r"báo\s*động\s*(?:1|2|3|I|II|III)", r"vượt\s*báo\s*động",
    r"vỡ\s*đê", r"vỡ\s*kè", r"tràn\s*đê", r"tràn\s*bờ", r"vỡ\s*đập", r"sự\s*cố\s*đập", r"xả\s*lũ",
    r"hồ\s*chứa", r"thủy\s*lợi", r"tràn\s*đập", r"tràn\s*qua\s*đập",
    # Lũ quét / Lũ ống
    r"lũ\s*quét", r"lũ\s*ống", r"nước\s*lũ\s*cuốn\s*trôi",
    # Sạt lở / Sụt lún (Loại trừ: đất đai, bất động sản, vận chuyển đất)
    r"(?<!\w)sạt(?!\w)", r"sạt\s*lở(?!\s*giá)", r"sạt\s*lở\s*đất", r"lở\s*đất", r"trượt\s*đất", r"trượt\s*lở",
    r"sạt\s*taluy", r"taluy", r"sạt\s*lở\s*bờ\s*sông", r"sạt\s*lở\s*bờ\s*biển",
    r"sụt\s*lún", r"hố\s*tử\s*thần", r"hố\s*sụt", r"nứt\s*đất", r"sụp\s*đường", r"sụp\s*lún"
  ]),

  # 4) Nắng nóng, Hạn hán, Xâm nhập mặn
  ("heat_drought", [
    # Nắng nóng
    r"nắng\s*nóng", r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt",
    r"nhiệt\s*độ\s*kỷ\s*lục", r"oi\s*bức", r"nhiệt\s*độ\s*cao",
    # Hạn hán
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước", r"cạn\s*kiệt",
    r"khát\s*nước", r"nứt\s*nẻ", r"đất\s*khô\s*nứt", r"cạn\s*hồ",
    # Mặn
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"độ\s*mặn", r"mặn\s*xâm\s*nhập",
    r"hạn\s*mặn", r"(?<!\w)ppt(?!\w)", r"(?<!\w)g/l(?!\w)"
  ]),

  # 5) Gió mạnh, Sương mù (trên biển và đất liền)
  ("wind_fog", [
    # Gió
    r"gió\s*mạnh", r"gió\s*giật", r"gió\s*mùa", r"gió\s*cấp", r"gió\s*lớn",
    r"biển\s*động", r"sóng\s*lớn", r"sóng\s*cao", r"cấm\s*biển", r"sóng\s*to",
    # Sương mù
    r"sương\s*mù", r"sương\s*mù\s*dày\s*đặc", r"mù\s*dày\s*đặc",
    r"tầm\s*nhìn\s*hạn\s*chế", r"giảm\s*tầm\s*nhìn"
  ]),

  # 6) Thời tiết cực đoan khác (Lốc, Sét, Mưa đá, Rét)
  ("extreme_other", [
    # Dông lốc
    r"(?<!\w)dông(?!\w)", r"dông\s*lốc", r"(?<!\w)lốc(?!\w)", r"lốc\s*xoáy", r"vòi\s*rồng", r"tố\s*lốc",
    # Mưa đá, Sét
    r"mưa\s*đá", r"(?<!\w)sét(?!\w)", r"giông\s*sét", r"sét\s*đánh",
    # Rét, Băng giá
    r"rét\s*đậm", r"rét\s*hại", r"không\s*khí\s*lạnh", r"sương\s*muối", r"băng\s*giá"
  ]),

  # 7) Cháy rừng
  ("wildfire", [
    # Explicitly wildfire only
    r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"PCCCR", r"cháy\s*thực\s*bì", r"rừng\s*phòng\s*hộ", r"rừng\s*sản\s*xuất", 
    r"đám\s*cháy\s*rừng", r"lửa\s*rừng", r"rừng\s*tràm", r"rừng\s*thông", r"keo\s*lá\s*tràm"
  ]),

  # 8) Động đất, Sóng thần
  ("quake_tsunami", [
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn",
    # Removed ambiguous "nứt đất/nhà" (common in landslides)
    r"sóng\s*thần", r"cảnh\s*báo\s*sóng\s*thần", r"tsunami",
    r"richter", r"chấn\s*tiêu", r"tâm\s*chấn",
    r"magnitude"
  ])
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc",
  # Official Sources
  r"trung\s*tâm\s*dự\s*báo", r"đài\s*khí\s*tượng", r"thủy\s*văn",
  r"ban\s*chỉ\s*huy", r"ban\s*chỉ\s*đạo", r"phòng\s*chống\s*thiên\s*tai", 
  r"sở\s*nn&ptnt", r"bộ\s*nông\s*nghiệp", r"ubnd",
  r"tin\s*bão", r"tin\s*áp\s*thấp", r"công\s*điện", r"khẩn\s*cấp",
  # Recovery / Relief (Moved from Negatives to Positive Context)
  r"khắc\s*phục", r"hỗ\s*trợ", r"cứu\s*trợ", r"ủng\s*hộ",
  r"thăm\s*hỏi", r"chia\s*sẻ", r"quyên\s*góp", r"tiếp\s*nhận",
  r"sửa\s*chữa", r"khôi\s*phục", r"tái\s*thiết", r"bồi\s*thường",
  r"bảo\s*hiểm", r"trợ\s*cấp", r"phân\s*bổ", r"nguồn\s*vốn",
  r"bệnh\s*viện", r"điều\s*trị", r"bác\s*sĩ", r"cấp\s*cứu"
]

# RECOVERY Keywords for Event Stage Classification
RECOVERY_KEYWORDS = [
    r"khắc\s*phục", r"hỗ\s*trợ", r"cứu\s*trợ", r"ủng\s*hộ",
    r"thăm\s*hỏi", r"chia\s*sẻ", r"quyên\s*góp", r"tiếp\s*nhận",
    r"sửa\s*chữa", r"khôi\s*phục", r"tái\s*thiết", r"bồi\s*thường",
    r"bảo\s*hiểm", r"trợ\s*cấp", r"phân\s*bổ", r"nguồn\s*vốn" 
]

# 1. HARD NEGATIVE: Absolute Veto (Metaphors, Sports, Showbiz, Accidents)
HARD_NEGATIVE = [
  # Bão (Metaphorical)
  r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng)(?!\w)",
  r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
  r"bão\s*sao\s*kê", r"bão\s*(?:chấn\s*thương|sa\s*thải)(?!\w)",
  r"(?<!thiên\s)bão\s*lòng", r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm)",
  r"siêu\s*bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu)", 
  r"bão\s*view", r"bão\s*comment", r"bão\s*order", r"bão\s*đơn",
  r"bão\s*hàng", r"bão\s*flash\s*sale", r"bão\s*voucher",
  r"siêu\s*dự\s*án", r"siêu\s*công\s*trình",
  
  # Động đất / Lũ / Sóng (Metaphorical)
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí)",
  r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|V-pop|V-League)",
  
  # === ADDED NOISE FILTERS ===
  # Economy / Real Estate
  r"bất\s*động\s*sản", r"cơn\s*sốt\s*đất", r"sốt\s*đất", r"đất\s*nền", r"chung\s*cư",
  r"dự\s*án\s*nhà\s*ở", r"shophouse", r"biệt\s*thự", r"đấu\s*giá\s*đất",
  r"lãi\s*suất", r"tín\s*dụng", r"ngân\s*hàng", r"tỉ\s*giá", r"VN-Index", r"chứng\s*khoán", r"cổ\s*phiếu",
  r"giá\s*(?:vàng|heo|cà\s*phê|lúa|xăng|dầu|trái\s*cây)", r"tăng\s*giá", r"giảm\s*giá", r"hạ\s*nhiệt\s*(?:giá|thị\s*trường)",
  r"xuất\s*khẩu", r"nhập\s*khẩu", r"GDP", r"tăng\s*trưởng\s*kinh\s*tế",

  # Traffic Accidents (Distinguish from Disaster)
  r"tai\s*nạn\s*giao\s*thông", r"va\s*chạm\s*xe", r"tông\s*xe", r"tông\s*chết",
  r"xe\s*tải", r"xe\s*khách", r"xe\s*đầu\s*kéo", r"xe\s*container", r"xe\s*buýt",
  r"(?<!thiên\s)tai\s*nạn\s*liên\s*hoàn", r"vi\s*phạm\s*nồng\s*độ\s*cồn",

  # Sports
  r"bóng\s*đá", r"cầu\s*thủ", r"đội\s*tuyển", r"World\s*Cup", r"V-League", r"Sea\s*Games",
  r"AFF\s*Cup", r"huấn\s*luyện\s*viên", r"bàn\s*thắng", r"ghi\s*bàn", r"vô\s*địch",
  r"huy\s*chương", r"HCV", r"HCB", r"HCD",

  # Showbiz / Events
  r"showbiz", r"hoa\s*hậu", r"người\s*mẫu", r"ca\s*sĩ", r"diễn\s*viên", r"liveshow",
  r"scandal", r"drama", r"sao\s*Việt", r"khánh\s*thành", r"khai\s*trương", r"kỷ\s*niệm\s*ngày",
  
  
  r"án\s*mạng", r"giết\s*người", r"cướp\s*giật", r"trộm\s*cắp", r"cát\s*tặc", r"khai\s*thác\s*cát",
  # Removed súng/bắn for military/rescue flare context
  r"hung\s*thủ", r"nghi\s*phạm",
  r"truy\s*nã", r"đối\s*tượng\s*lừa\s*đảo", r"đối\s*tượng\s*ma\s*túy", r"đối\s*tượng\s*truy\s*nã",
  r"bắt\s*giữ", r"bị\s*can", r"xử\s*phạt", r"xét\s*xử", r"phiên\s*tòa",
  r"tử\s*hình", r"án\s*tù", r"tội\s*phạm",

  # Fire / Explosion (Urban/Industrial - Not Forest)
  # Removed aggressive 'cháy nhà/xưởng' and 'hỏa hoạn' to avoid FP on wildfire descriptions.
  # Positive rules for wildfire are specific enough.
  r"lửa\s*ngùn\s*ngụt", 
  r"bà\s*hỏa", r"chập\s*điện", r"nổ\s*bình\s*gas",
  r"bom\s*mìn", r"vật\s*liệu\s*nổ", r"thuốc\s*nổ", r"đạn\s*pháo", r"chiến\s*tranh", r"thời\s*chiến",

  # Pollution / Environment 
  r"quan\s*trắc\s*môi\s*trường", r"rác\s*thải",
  r"chất\s*lượng\s*không\s*khí", r"(?<!\w)AQI(?!\w)", r"bụi\s*mịn", r"chỉ\s*số\s*không\s*khí",

  r"giàn\s*giáo", r"sập\s*giàn\s*giáo", r"tai\s*nạn\s*lao\s*động", r"an\s*toàn\s*lao\s*động",
  r"công\s*trình\s*xây\s*dựng", r"thi\s*công",
  r"thiết\s*kế\s*nội\s*thất", r"trần\s*thạch\s*cao", r"la\s*phông", r"tấm\s*ốp",
  r"trang\s*trí\s*nhà", r"nhà\s*đẹp", r"căn\s*hộ\s*mẫu", r"chung\s*cư\s*cao\s*cấp", r"biệt\s*thự",
  r"bảo\s*trì", r"bảo\s*dưỡng", r"nghiệm\s*thu", r"lắp\s*đặt", r"hệ\s*thống\s*kỹ\s*thuật",
  r"tủ\s*điện", r"thẩm\s*duyệt\s*PCCC", r"tập\s*huấn\s*PCCC", r"diễn\s*tập\s*PCCC",

  # Extended Traffic Noise
  r"xe\s*cứu\s*thương", r"biển\s*số\s*xe", r"đấu\s*giá\s*biển\s*số",
  r"đăng\s*kiểm", r"giấy\s*phép", r"phạt\s*nguội",
  
  # Other Misc
  r"tặng\s*quà", r"trao\s*quà", r"từ\s*thiện", r"hiến\s*máu", # Filter out pure charity events if not linked to active disaster keywords strongly

  # Administrative / Legal / Political (Non-disaster)
  r"giấy\s*chứng\s*nhận", r"sổ\s*đỏ", r"quyền\s*sử\s*dụng\s*đất", r"giao\s*đất", r"chuyển\s*nhượng",
  r"công\s*chức", r"viên\s*chức", r"biên\s*chế", r"thẩm\s*quyền", r"hành\s*chính",
  r"quốc\s*phòng\s*toàn\s*dân", r"an\s*ninh\s*quốc\s*phòng", r"quân\s*sự", r"binh\s*sĩ",
  r"vụ\s*án", r"tranh\s*chấp", r"khiếu\s*nại", r"tố\s*cáo", r"điều\s*tra\s*viên", r"bị\s*can",
  r"kháng\s*chiến", r"đại\s*biểu\s*quốc\s*hội", r"tổng\s*tuyển\s*cử", r"chính\s*trị",
  r"phân\s*công\s*công\s*tác", r"nhân\s*sự", r"bầu\s*cử", r"nhiệm\s*kỳ",
  
  # Education
  r"đại\s*học", r"cao\s*đẳng", r"tuyển\s*sinh", r"đào\s*tạo", r"giáo\s*dục", r"học\s*bổng",
  r"tốt\s*nghiệp", r"thạc\s*sĩ", r"tiến\s*sĩ",
  
  # Finance / Banking (Specific)
  r"vốn\s*điều\s*lệ", r"tăng\s*vốn", r"cổ\s*đông", r"lợi\s*nhuận", r"doanh\s*thu",
  r"ADB", r"WB", r"IMF", r"ODA", # International banks often in economic news
  
  # Health / Lifestyle
  r"ung\s*thư", r"tế\s*bào", r"tiểu\s*đường", r"huyết\s*áp", r"đột\s*quỵ",
  r"dinh\s*dưỡng", r"thực\s*phẩm", r"món\s*ăn", r"đặc\s*sản", r"giảm\s*cân", r"làm\s*đẹp",
  r"ngăn\s*ngừa\s*bệnh", r"sức\s*khỏe\s*sinh\s*sản",

  # Tech / Internet / Misc
  r"Google", r"Facebook", r"Youtube", r"TikTok", r"Zalo\s*Pay", r"tính\s*năng", r"cập\s*nhật",
  r"tra\s*từ", r"từ\s*điển", r"bài\s*hát", r"ca\s*khúc", r"MV", r"triệu\s*view", r"top\s*trending",
  r"công\s*nghệ\s*số", r"dữ\s*liệu", r"trao\s*quyền", r"thủ\s*tục",
  r"văn\s*hóa", r"nghệ\s*thuật", r"triển\s*lãm", r"khai\s*mạc", r"lễ\s*hội",
  r"tình\s*yêu\s*lan\s*tỏa", r"đánh\s*thức\s*những\s*lãng\s*quên",
  
  # Metaphors (Reinforced)
  r"bão\s*tố\s*cuộc\s*đời", r"sóng\s*gió\s*cuộc\s*đời", r"bão\s*tố\s*tình\s*yêu",
  r"bão\s*lòng",
  
  # Transport / Aviation / Urban Traffic
  r"kẹt\s*xe", r"ùn\s*tắc", r"giao\s*thông\s*đô\s*thị",

  # === NEW: MODERN VIETNAMESE PATTERNS (2024+) ===
  
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
  r"nhà\s*thông\s*minh", r"smart\s*home", r"AI", r"trí\s*tuệ\s*nhân\s*tạo",
  
  # Travel / Tourism
  r"combo\s*du\s*lịch", r"săn\s*vé\s*máy\s*bay",
  
  # Cosmetics / Beauty
  r"mỹ\s*phẩm", r"skincare", r"làm\s*đẹp\s*da", r"review\s*mỹ\s*phẩm",
  
  # COVID-related metaphors (not actual disaster)
  r"làn\s*sóng\s*(?:COVID|covid|dịch)\s*thứ",
  r"bão\s*COVID", r"bão\s*F0",
  
  # Political / Diplomatic (Metaphorical)
  r"bão\s*(?:ngoại\s*giao|chính\s*trị)", 
  r"rung\s*chấn\s*chính\s*trường",
  
  # === SIMPLIFIED: ONLY FILTER TRULY UNRELATED CONTENT ===
  # System is for "comprehensive disaster risk reporting" including:
  #   - Active disasters, warnings, forecasts
  #   - Recovery, aftermath, reconstruction  
  #   - Infrastructure investment for disaster prevention
  #   - Weather forecasts and updates
  # ONLY filter spam, entertainment, pure politics, animals, etc.
  
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
  r"thủ\s*tướng", r"bộ\s*trưởng", r"lãnh\s*đạo",
  r"khởi\s*công", r"khánh\s*thành", r"nghiệm\s*thu", 
  r"an\s*ninh\s*mạng", r"chuyển\s*đổi\s*số", r"công\s*nghệ", r"startup",
  r"giải\s*thưởng", r"vinh\s*danh",
  # Tai nạn (Soft Negative - pass if caused by storm/flood)
  r"tai\s*nạn\s*giao\s*thông", r"xe\s*tải", r"xe\s*container", r"xe\s*khách",
  # Fire non-wildfire
  r"cháy\s*(?:nhà|xe|kho|xưởng|chung\s*cư|công\s*ty|chợ|siêu\s*thị|tàu\s*cá|quán)",
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng)"
]

# Combined Negative List for backward compatibility (used in NO_ACCENT generation)
DISASTER_NEGATIVE = HARD_NEGATIVE + SOFT_NEGATIVE

# Removed old compiled patterns
POLLUTION_TERMS = [r"ô\s*nhiễm", r"AQI", r"PM2\.5", r"bụi\s*mịn"]

# Pre-compute unaccented patterns for matching against t0 (canonical text)
DISASTER_RULES_NO_ACCENT = []
for label, pats in DISASTER_RULES:
    nops = [risk_lookup.strip_accents(p) for p in pats]
    DISASTER_RULES_NO_ACCENT.append((label, nops))

DISASTER_CONTEXT_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_NEGATIVE]

# Build impact extraction patterns with named groups and qualifier support
def _build_impact_patterns():
    """
    Build regex patterns for extracting impact metrics.
    Uses regexes defined in IMPACT_KEYWORDS.
    """
    patterns = {}
    
    for impact_type, data in IMPACT_KEYWORDS.items():
        regex_list = data.get("regex", [])
        patterns[impact_type] = []
        for r_str in regex_list:
            try:
                patterns[impact_type].append(re.compile(r_str, re.IGNORECASE))
            except re.error as e:
                print(f"Error compiling regex for {impact_type}: {r_str} -> {e}")
                
    return patterns

IMPACT_PATTERNS = _build_impact_patterns()
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
    # Check Rules (Iterate both accented and unaccented)
    for i, (label, patterns) in enumerate(DISASTER_RULES):
        matched = False
        # Match Accented on t
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                matched = True; break
        # Disable Unaccented Check to prevent False Positives (bao -> bão, lu -> lũ)
        # if not matched:
        #     _, patterns_no = DISASTER_RULES_NO_ACCENT[i]
        #     for p in patterns_no:
        #         if re.search(p, t0, re.IGNORECASE):
        #             matched = True; break
        if matched: rule_matches.append(label)

    hazard_score = len(set(rule_matches))
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

    # Context Matches
    context_hits = []
    for i, p_str in enumerate(DISASTER_CONTEXT):
        matched = False
        if re.search(p_str, t, re.IGNORECASE): matched = True
        # Disable Unaccented Check for Context
        # else:
        #     p_no = DISASTER_CONTEXT_NO_ACCENT[i]
        #     if re.search(p_no, t0, re.IGNORECASE): matched = True
        if matched: context_hits.append(p_str)
        
    for pt in POLLUTION_TERMS:
        if re.search(pt, t, re.IGNORECASE): context_hits.append(pt)
    context_score = len(context_hits)

    # NEGATIVE CHECKS (Split)
    hard_negative = False
    for p in HARD_NEGATIVE:
        if re.search(p, t, re.IGNORECASE): 
            hard_negative = True; break
            
    soft_negative = False
    if not hard_negative:
        for p in SOFT_NEGATIVE:
            if re.search(p, t, re.IGNORECASE):
                soft_negative = True; break

    metrics = extract_disaster_metrics(t)
    impact_details = extract_impact_details(t)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": hazard_score,
        "context_score": context_score,
        "hard_negative": hard_negative,
        "soft_negative": soft_negative,
        "metrics": metrics,
        "impact_details": impact_details
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


def contains_disaster_keywords(text: str, trusted_source: bool = False) -> bool:
    """
    Simplified Logic (Hybrid v3):
    1. HARD NEGATIVE -> Absolute Rejection (filters spam, metaphors, unrelated).
    2. HAZARD KEYWORD -> Accept immediately (includes recovery, infrastructure, forecasts).
    3. METRICS -> Accept if specific disaster metrics found (e.g. rainfall, water level).
    
    Removed complex scoring thresholds to improve recall for valid disaster news.
    """
    sig = compute_disaster_signals(text)
    
    # 0. VIP Whitelist (Critical Warnings that bypass ALL filters)
    # Rescue valid storm warnings/aid that might get caught by aggressive filters
    for vip in sources.VIP_TERMS:
        if re.search(vip, text, re.IGNORECASE):
            return True

    # 1. Absolute Veto (The "Shield")
    if sig["hard_negative"]:
        return False
        
    # 2. Hazard Keyword Found (One of 158 terms from sources.py or DISASTER_RULES)
    if sig["hazard_score"] > 0:
        return True
        
    # 3. Warning/Forecast Signatures (NEW: To capture "Tin bão", "Cảnh báo lũ", "Dự báo thời tiết")
    # Even if exact hazard key is tricky, if we see "Dự báo" + "mưa lớn/bão/lũ", we take it.
    if re.search(r"(dự\s*báo|cảnh\s*báo|tin\s*(?:không\s*khí\s*lạnh|bão|lũ|mưa|nắng\s*nóng))", text, re.IGNORECASE):
        # Must also have some disaster-ish context if not a direct hazard term
        if sig["context_score"] > 0 or re.search(r"(thời\s*tiết|thiên\s*tai|nguy\s*hiểm)", text, re.IGNORECASE):
            return True

    # 4. Metrics Fallback (e.g. "Mưa 200mm", "Sức gió cấp 12" without explicit keyword?)
    # Rare case, but good safety net.
    if sig["metrics"]: 
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
    for p in DISASTER_NEGATIVE:
        if re.search(p, t, re.IGNORECASE):
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
    sig = compute_disaster_signals(full_text)
    
    matches = list(set(sig["rule_matches"])) # Deduplicate
    
    if not matches:
        return {
            "primary_type": "unknown",
            "primary_level": 0,
            "all_hazards": []
        }
    
    # Simple Priority for Primary Type
    PRIO = [
        "quake_tsunami",
        "storm_surge", # Prioritize surge over storm for specificity 
        "storm",
        "flood_landslide", 
        "wildfire", 
        "heat_drought", 
        "wind_fog", 
        "extreme_other"
    ]
    
    # Build list
    all_hazards = [{"type": m, "level": 1} for m in matches] # Default Level 1
    
    # Sort by Priority
    all_hazards.sort(key=lambda h: PRIO.index(h["type"]) if h["type"] in PRIO else 99)
    
    return {
        "primary_type": all_hazards[0]["type"],
        "primary_level": 1,
        "all_hazards": all_hazards
    }

def detect_flood_station(text: str) -> dict:
    """
    Detect flood monitoring station mentions in text using flood_zones.json.
    Returns:
    {
        "has_station": bool,           # Whether any station was detected
        "stations": [                   # List of detected stations
            {
                "name": str,            # Station name
                "river": str,           # River name
                "province": str,        # Province
                "region": int,          # Flood region (1-4) per Decision 18
                "confidence": float     # Match confidence (0-1)
            }
        ],
        "primary_region": int | None   # Most confident region (for risk calc)
    }
    """
    from . import risk_lookup
    
    # Get FLOOD_ZONES_DATA from risk_lookup
    # It's already loaded there
    if not hasattr(risk_lookup, 'FLOOD_ZONES_DATA') or not risk_lookup.FLOOD_ZONES_DATA:
        return {"has_station": False, "stations": [], "primary_region": None}
    
    t, t0 = risk_lookup.canon(text)
    stations_found = []
    
    # Search through all regions
    for region_key, stations_list in risk_lookup.FLOOD_ZONES_DATA.items():
        # Extract region number (khu_vuc_1 -> 1)
        region_num = int(region_key.replace("khu_vuc_", ""))
        
        for station_info in stations_list:
            station_name = station_info.get("ten_tram")
            river_name = station_info.get("ten_song")
            province = station_info.get("tinh")
            
            confidence = 0.0
            match_reasons = []
            
            # Match station name (highest confidence)
            if station_name:
                station_t0 = risk_lookup.strip_accents(station_name).lower()
                if station_t0 in t0:
                    confidence = 0.9
                    match_reasons.append("station_name")
            
            # Match river + province (medium confidence)
            if river_name and province and confidence < 0.9:
                river_t0 = risk_lookup.strip_accents(river_name).lower()
                prov_t0 = risk_lookup.strip_accents(province).lower()
                
                if river_t0 in t0 and prov_t0 in t0:
                    confidence = 0.7
                    match_reasons.append("river_province")
            
            # Add to results if confident enough
            if confidence >= 0.7:
                stations_found.append({
                    "name": station_name or f"Trạm {river_name}",
                    "river": river_name,
                    "province": province,
                    "region": region_num,
                    "confidence": confidence,
                    "match_reasons": match_reasons
                })
    
    # Sort by confidence
    stations_found.sort(key=lambda x: -x["confidence"])
    
    # Determine primary region (highest confidence)
    primary_region = stations_found[0]["region"] if stations_found else None
    
    return {
        "has_station": len(stations_found) > 0,
        "stations": stations_found,
        "primary_region": primary_region
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
    """
    impacts = {}
    
    # Normalize text (lower, strip accents/spaces)
    # Note: Regexes must be compatible with lowercased text (compile with re.I)
    t = normalize_text(text)
    
    for impact_type, patterns in IMPACT_PATTERNS.items():
        found_items = []
        for pat in patterns:
            for m in pat.finditer(t):
                # NEGATION CHECK
                start, end = m.span()
                pre_text = t[max(0, start - 30):start]
                post_text = t[end:min(len(t), end + 30)]
                
                # Check specific negations for this type + general negations
                specific_negs = NEGATION_TERMS.get(impact_type, [])
                general_negs = NEGATION_TERMS.get("general", [])
                all_negs = specific_negs + general_negs
                
                if any(neg in pre_text for neg in all_negs) or any(neg in post_text for neg in all_negs):
                    continue

                # Parse groups pattern: First number-like group is value
                groups = m.groups()
                val = 0
                unit = None
                
                # Heuristic to find Value (Num) vs Unit
                for g in groups:
                    if not g: continue
                    
                    # Try parsing as number (including range support)
                    g_clean = re.sub(r"[^0-9–-]", "", g) # Keep digits and hyphens
                    if g_clean and (g_clean[0].isdigit() or g_clean.startswith("-")):
                         # If it's a range like "3-5"
                         if "-" in g or "–" in g:
                             nums = re.findall(r"\d+", g)
                             if nums:
                                 val = [int(n) for n in nums]
                         else:
                             val = _to_int(g)
                             
                         # Specific override for float types if needed (damage, agriculture)
                         if impact_type in ("damage", "agriculture") and isinstance(val, int):
                              try:
                                  if ',' in g:
                                      val = float(g.replace(',', '.'))
                                  elif '.' in g and len(g.split('.')[1]) != 3: 
                                      val = float(g)
                              except:
                                  pass
                         break
                
                if val:
                    # Find unit (first non-number, non-qualifier string)
                    for g in groups:
                        if not g: continue
                        # If it's a number, skip
                        if re.sub(r"[^0-9–-]", "", g).isdigit(): continue
                        # Skip qualifiers
                        if g.lower() in ("ít nhất", "tối thiểu", "khoảng", "hơn", "trên", "gần", "tới", "lên tới", "ước tính", "ước", "ban đầu", "dự kiến"): continue
                        
                        # Skip known keywords (e.g. "thiệt hại", "tổn thất") to avoid capturing them as unit
                        # BUT do not skip if it's a known unit noun like "ngư dân" or "thuyền viên"
                        terms = IMPACT_KEYWORDS[impact_type].get("terms", [])
                        is_unit_noun = g.lower() in ("người", "nhà văn hóa", "căn nhà", "ngôi nhà", "trường học", "nhà", "hộ", "căn", "ngôi", "tàu cá", "tàu hàng", "tàu du lịch", "tàu", "thuyền thúng", "thuyền", "thuyền viên", "ngư dân", "ha", "hecta", "tấn", "sào", "lồng bè", "lồng", "bè", "sà lan", "ghe chài", "ghe")
                        if g.lower() in terms and not is_unit_noun: continue
                        
                        # Skip common verbs if they are not the intended unit (heuristic)
                        if len(g) < 4 and g.lower() in ("làm", "gây", "bị", "đã", "có", "mất", "với", "cho", "vào", "đến"): continue
                        if g.lower() in ("khẩn cấp", "mất tích", "chìm", "vùi lấp", "tốc mái", "ngập", "thiệt hại", "tổn thất", "nứt", "sửa", "chia cắt", "cô lập", "làm sập", "làm", "khiến", "gây", "tử vong", "thiệt mạng", "cháy", "mất điện", "mất nước", "ảnh hưởng", "trôi", "ngập úng"): continue

                        unit = g
                        break
                    
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
             # Text numbers check
             if "nghìn" in t or "ngàn" in t:
                 m = re.search(r"(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|hàng|vài)\s*(nghìn|ngàn)\s*(ngôi|căn)?\s*(nhà|hộ)", t)
                 if m:
                     if m.group(1) == "một": found_items.append({"num": 1000, "unit": "nhà"})
                     elif m.group(1) == "hàng": found_items.append({"num": 1000, "unit": "nhà"})
             # "Một" for single house damage (only if no numeric damage for houses found)
             elif "một" in t and any(x in t for x in ["ngôi nhà", "căn nhà", "thiệt hại một nhà"]):
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
