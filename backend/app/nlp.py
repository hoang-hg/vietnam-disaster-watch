import re
import unicodedata
import logging
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from functools import lru_cache
from . import sources
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS, CONTEXT_KEYWORDS as DISASTER_CONTEXT
from . import risk_lookup

logger = logging.getLogger(__name__)

def is_junk_title(title: str) -> bool:
    """
    Check if the title is a generic landing page or SEO noise rather than an actual article.
    Helps avoid blacklisting thousands of 'Search Results' pages.
    """
    title_low = title.lower()
    junk_patterns = [
        r"kết quả tin tức cho từ khóa",
        r"trang chủ - ",
        r"tìm kiếm - ",
        r"kết quả tìm kiếm",
        r"search results for",
        r"news results for",
    ]
    for p in junk_patterns:
        if re.search(p, title_low):
            return True
    return False

# CONSTANTS & CONFIG
def dedupe_keep_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# Base components without named groups
_NUM_HARD = r"(?:\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*(?:[–-]|đến)\s*\d+)?)"
_NUM_SOFT = r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|hàng\s*chục|hàng\s*trăm|nhiều)"
_QUAL = r"(?:ít\s*nhất|tối\s*thiểu|khoảng|ước\s*tính|trên|hơn|gần)"
_UNIT = r"(?:người|nạn\s*nhân|em|cháu|trẻ\s*em|học\s*sinh|công\s*nhân|thuyền\s*viên|ngư\s*dân|hành\s*khách|tài\s*xế|lái\s*xe|cư\s*dân|du\s*khách|chiến\s*sĩ|phụ\s*nữ|thai\s*phụ|sản\s*phụ|cụ\s*ông|cụ\s*bà)"

# Capturing versions for use in regex lists
NUM_HARD = rf"(?P<num>{_NUM_HARD})"
NUM_SOFT = rf"(?P<num_soft>{_NUM_SOFT})"
QUAL = rf"(?P<qualifier>{_QUAL})?"
UNIT = rf"(?P<unit>{_UNIT})?"

DEATH_WORD = r"(?:chết|tử\s*vong|thiệt\s*mạng|tử\s*nạn|tử\s*thương|không\s*qua\s*khỏi)"
INJ_WORD = r"(?:bị\s*thương|trọng\s*thương|bị\s*thương\s*nặng|bị\s*thương\s*nhẹ|đa\s*chấn\s*thương|thương\s*tích|chấn\s*thương|bỏng|bị\s*bỏng|bất\s*tỉnh|ngất\s*xỉu|nguy\s*kịch)"
CARE_WORD = r"(?:nhập\s*viện|phải\s*nhập\s*viện|cấp\s*cứu|đi\s*cấp\s*cứu|đưa\s*đi\s*cấp\s*cứu|đưa\s*đến\s*bệnh\s*viện|đưa\s*vào\s*viện|đưa\s*tới\s*cơ\s*sở\s*y\s*tế|điều\s*trị)"
MISS_WORD = r"(?:mất\s*tích|mất\s*liên\s*lạc|không\s*liên\s*lạc\s*được|không\s*thể\s*liên\s*lạc|không\s*liên\s*hệ\s*được|không\s*rõ\s*tung\s*tích|chưa\s*xác\s*định\s*tung\s*tích|chưa\s*tìm\s*thấy|vẫn\s*chưa\s*tìm\s*thấy|bặt\s*vô\s*âm\s*tín)"
VESSEL = r"(?P<vessel>tàu\s*cá|tàu\s*hàng|tàu\s*du\s*lịch|tàu\s*chở\s*khách|tàu\s*cao\s*tốc|tàu\s*vận\s*tải|tàu\s*container|tàu\s*dầu|tàu\s*kéo|tàu|thuyền\s*thúng|thuyền|xuồng\s*máy|xuồng|ca\s*nô|cano|ghe\s*chài|ghe|sà\s*lan|phà|đò|phương\s*tiện(?:\s*thủy)?)"
CREW = r"(?P<unit>ngư\s*dân|thuyền\s*viên|hành\s*khách|thủy\s*thủ|thuyền\s*trưởng|thuyền\s*phó|thủy\s*thủ\s*đoàn)"
INCIDENT = r"(?:chìm|đắm|lật|lật\s*úp|lật\s*nghiêng|mắc\s*cạn|va\s*chạm|đâm\s*va|chết\s*máy|hỏng\s*máy|mất\s*lái|mất\s*điều\s*khiển|cháy|bốc\s*cháy|nổ|trôi\s*dạt|mất\s*tín\s*hiệu|mất\s*liên\s*lạc|gặp\s*nạn|bị\s*nạn)"
NUM = r"(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?(?:\s*(?:[–-]|đến)\s*\d+(?:[.,]\d+)?)?)"
PEOPLE = r"(?P<unit>người|nhân\s*khẩu)"
HOUSE = r"(?P<unit2>hộ|hộ\s*dân)"
AREA_UNIT = r"(?P<unit>ha|hecta|héc\s*ta|m2|m²|sào|mẫu|công)"
MASS_UNIT = r"(?P<mass>tấn|kg)"
COUNT_UNIT = r"(?P<count_unit>con)"
CROP = r"(?:lúa|mạ|hoa\s*màu|rau\s*màu|cây\s*trồng|cây\s*ăn\s*quả|vườn\s*cây|mía|sắn|ngô|bắp|khoai|đậu|lạc|cà\s*phê|cao\s*su|hồ\s*tiêu|điều|chè|chuối|thanh\s*long|xoài)"
CROP_STATUS = r"(?:bị\s*)?(?:ngập(?:\s*úng|\s*sâu|\s*lụt)?|hư\s*hại|hư\s*hỏng|thiệt\s*hại|mất\s*trắng|đổ\s*ngã|dập\s*nát|gãy\s*đổ|rụng\s*quả)"
LIVESTOCK = r"(?:trâu|bò|lợn|heo|dê|cừu|gà|vịt|ngan|ngỗng|gia\s*súc|gia\s*cầm)"
LIVE_STATUS = r"(?:bị\s*)?(?:chết|cuốn\s*trôi|trôi|mất|thiệt\s*hại)"
AQUA_OBJ = r"(?:ao|đầm|lồng\s*bè|lồng|bè)"
AQUA = r"(?:tôm|cá|thủy\s*sản)"
AQUA_STATUS = r"(?:bị\s*)?(?:trôi|cuốn\s*trôi|vỡ|tràn|thiệt\s*hại|mất\s*trắng|thất\s*thoát|cá\s*chết|tôm\s*chết)"

# Disaster Priority (Severity for tie-breaking and event upgrades)
DISASTER_PRIORITY = [
    "tsunami", "earthquake", "storm", "flash_flood", "landslide", 
    "flood", "subsidence", "storm_surge", "wildfire", "salinity",
    "drought", "heatwave", "cold_surge", "extreme_weather", "erosion",
    "warning_forecast", "recovery"
]

# Priority map for O(1) lookup during classification sorting
DISASTER_PRIORITY_MAP = {k: i for i, k in enumerate(DISASTER_PRIORITY)}

# Pre-compiled patterns for location and metadata extraction
RE_SENTENCE_SPLIT = re.compile(r'(?<=[\.?!;])\s+', re.UNICODE)
RE_COMMUNE = re.compile(r"(?:xã|phường|thị\s*trấn|thị\s*tứ)\s+([A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*(?:\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*)*)")
RE_VILLAGE = re.compile(r"(?:thôn|bản|ấp|xóm|khối|tổ|khu\s*phố|ngõ|ngách|hẻm|số\s*nhà)\s+([A-Z0-9\xC0-\xDFĐ][a-z0-9\xE0-\xFFà-ỹ]*(?:\s+[A-Z0-9\xC0-\xDFĐ][a-z0-9\xE0-\xFFà-ỹ]*)*)")
RE_ROUTE = re.compile(r"(?:tuyến|quốc\s*lộ|tỉnh\s*lộ|đường|cao\s*tốc)\s+([A-Z0-9Đ][a-z0-9à-ỹ\-\.\/]*(\s+[A-Z0-9Đ][a-z0-9à-ỹ\-\.\/]*)*)")
RE_LANDMARK = re.compile(r"((?:sông|suối|núi|cầu|hồ|đập|đèo|kè|cống|vịnh|biển|mương|rạch|kênh|hầm|nhà\s*máy|kho|xưởng|cảng|sân\s*bay|quốc\s*lộ|tỉnh\s*lộ|đường|cao\s*tốc|đường\s*sắt|metro|nhà\s*ga|trạm\s*biến\s*áp|nhà\s*máy\s*nhiệt\s*điện|nhà\s*máy\s*thủy\s*điện|nhà\s*máy\s*điện\s*gió)\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*(?:\s+[A-Z\xC0-\xDFĐ][a-z\xE0-\xFFà-ỹ]*)*)")

RE_WARNING_TITLE = re.compile(r"bản\s*tin(?:\s*dự\s*báo|\s*cảnh\s*báo)|dự\s*báo\s*thiên\s*tai|tin\s*cảnh\s*báo|cảnh\s*báo\s*thiên\s*tai", re.IGNORECASE)
RE_RECOVERY_TITLE = re.compile(r"khắc\s*phục\s*hậu\s*quả|sau\s*thiên\s*tai|thống\s*kê\s*thiệt\s*hại|rà\s*soát\s*thiệt\s*hại", re.IGNORECASE)

# Impact keywords
IMPACT_KEYWORDS = {
    "deaths": {
        "terms": [
            "chết", "tử vong", "tử nạn", "tử thương", "thiệt mạng", "thương vong", "nạn nhân tử vong", "số người chết", "làm chết", "cướp đi sinh mạng", "tìm thấy thi thể", "không qua khỏi", 
            "tử vong tại chỗ", "tử vong sau khi", "đã tử vong", "chết cháy", "tử vong do ngạt", "ngạt khói", "ngạt khí", "chết đuối", "đuối nước", "ngạt nước", "bị cuốn trôi tử vong", "bị vùi lấp tử vong", "bị chôn vùi tử vong",
            "mất mạng", "không còn dấu hiệu sinh tồn", "phát hiện một thi thể", "ghi nhận tử vong", "đã qua đời do thiên tai", "tử vong", "thiệt mạng", "tử nạn", "tử thương", "không qua khỏi", "tử vong do", "tử vong vì", "tử vong trong", "tử vong khi",
            "tử vong tại bệnh viện", "tử vong trên đường đi cấp cứu", "tử vong trong đêm", "tử vong tại hiện trường", "làm nhiều người thiệt mạng", "làm nhiều người tử vong", "thi thể", "tử thi", "xác", "phát hiện thi thể", "tìm thấy thi thể", "trục vớt thi thể", "vớt được thi thể", "đưa thi thể lên bờ",
            "thi thể nạn nhân", "thi thể thứ", "tìm thấy thêm thi thể", "không còn dấu hiệu sự sống", "ngưng tim", "ngừng tim", "ngưng thở", "ngừng thở", "đã tử", "đã chết", "tử vong tại chỗ", "tại chỗ tử vong",
            "không cứu được", "không thể qua khỏi", "người dân", "ngư dân", "thuyền viên", "hành khách", "tài xế", "lái xe", "du khách", "cư dân", "bệnh nhân", "sản phụ", "tu vong", "thiet mang", "tu nan", "tu thuong", "thi the", "tu thi", "vo thi the", "truc vot",
        ],
        "regex": [
            r"\b(?P<qualifier>ít nhất|tối thiểu|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh|công nhân|chiến sĩ)\s*(?:chết|tử\s*vong|thiệt\s*mạng|tử\s*nạn|tử\s*thương|thương\s*vong)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\s*(?:chết|tử\s*vong)\s*(?:và|,)\s*mất\s*tích\b",
            r"\b(làm|khiến)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)\s*(?:chết|tử\s*vong|thiệt\s*mạng|thương\s*vong)\b",
            r"\b(tìm thấy|phát hiện)\s*(thi thể|xác)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)?\b",
            r"\b(cướp đi sinh mạng|tước đi sinh mạng)\s*(của)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{DEATH_WORD}\b",
            rf"\b(?:cướp\s*đi|tước\s*đi)\s*(?:sinh\s*mạng)?\s*(?:của)?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b(?:làm|khiến)\s*(?:chết|tử\s*vong|thiệt\s*mạng)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b(?:làm|khiến)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{DEATH_WORD}\b",
            rf"\b(?:ghi\s*nhận|xác\s*định|thống\s*kê|báo\s*cáo|tính\s*đến)\s*(?:là|có)?\s*{QUAL}\s*{NUM_HARD}\s*(?:ca\s*)?tử\s*vong\b",
            rf"\btrong\s*đó\s*,?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{DEATH_WORD}\b",
            rf"\b(?:{_QUAL})?\s*(?P<num_a>\d{{1,3}}(?:[.,]\d{{3}})*)\s*người\s*lớn\s*(?:và|,)\s*(?:{_QUAL})?\s*(?P<num_b>\d{{1,3}}(?:[.,]\d{{3}})*)\s*(?:trẻ\s*em|cháu)\s*{DEATH_WORD}\b",
            r"\b(?:tử\s*vong|thiệt\s*mạng|chết)\s*do\s*(?:đuối\s*nước|ngạt\s*nước|sét\s*đánh|vùi\s*lấp|sạt\s*lở|lũ\s*cuốn|bão\s*cuốn|cây\s*đổ|tường\s*sập|điện\s*giật|cháy|ngạt\s*khói)\b",
            rf"\b(?:tìm\s*thấy|phát\s*hiện|trục\s*vớt|vớt\s*được)\s*(?:thêm\s*)?{QUAL}\s*{NUM_HARD}\s*(?:thi\s*thể|tử\s*thi|xác)\s*(?:{UNIT})?\b",
            r"\b(?:thi\s*thể|tử\s*thi)\s*thứ\s*(?P<ordinal>\d{1,3})\b",
            r"\bkhông\s*còn\s*dấu\s*hiệu\s*(?:sinh\s*tồn|sự\s*sống)\b",
            r"\b(?:ngưng|ngừng)\s*tim\b",
            r"\b(?:ngưng|ngừng)\s*thở\b",
            rf"\b{QUAL}\s*{NUM_SOFT}\s*{UNIT}\s*{DEATH_WORD}\b",
        ]
    },

    "missing": {
        "terms": [
            "mất tích", "thất lạc", "chưa tìm thấy", "chưa tìm được", "chưa thấy","mất liên lạc", "không liên lạc được", "không thể liên lạc","chưa xác định tung tích", "không rõ tung tích", "chưa rõ số phận","bị cuốn trôi", 
            "trôi mất", "bị nước cuốn", "bị lũ cuốn","bị vùi lấp", "bị chôn vùi", "mắc kẹt", "bị mắc kẹt","đang tìm kiếm", "tổ chức tìm kiếm", "công tác tìm kiếm","tìm kiếm cứu nạn", "cứu nạn", "cứu hộ", "tìm kiếm cứu hộ",
            "không rõ tung tích", "mất tích trên biển", "trong tình trạng mất liên lạc", "trôi dạt chưa tìm thấy", # Mất tích / chưa rõ tung tích
            "mất tích", "chưa rõ tung tích", "không rõ tung tích", "chưa xác định tung tích",
            "chưa xác định được tung tích", "chưa xác định được vị trí",
            "không rõ số phận", "chưa rõ số phận", "bặt vô âm tín",
            "không có tin tức", "không nhận được tin tức", "không có thông tin",
            "mất liên lạc", "mất tín hiệu", "mất sóng", "mất kết nối", "không bắt được liên lạc",
            "không liên hệ được", "không thể liên hệ", "không gọi được", "không nhắn được",
            "mất tích trên biển", "mất tích ngoài khơi", "mất tích dưới biển",
            "trôi dạt", "trôi dạt trên biển", "trôi dạt chưa tìm thấy", "chưa tìm thấy trên biển",
            "chìm tàu", "lật thuyền", "lật tàu", "rơi xuống biển",
            "bị cuốn trôi", "bị nước cuốn", "bị lũ cuốn", "bị sóng cuốn",
            "bị vùi lấp", "bị chôn vùi", "mắc kẹt", "bị mắc kẹt",
            "tìm kiếm", "truy tìm", "rà soát", "tổ chức tìm kiếm", "mở rộng phạm vi tìm kiếm",
            "tìm kiếm cứu nạn", "tìm kiếm cứu hộ", "cứu hộ cứu nạn", "lực lượng cứu nạn",
            "tìm kiếm xuyên đêm", "tiếp tục tìm kiếm", "đang tìm kiếm", 
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|công nhân|thuyền viên|ngư dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(bị|đã)?\s*(mất tích|mất liên lạc|chưa tìm thấy|chưa liên lạc được|không rõ tung tích|cuốn trôi|lũ cuốn|nước cuốn|vùi lấp|mắc kẹt)\b",
            r"\b(tìm kiếm|chưa tìm thấy|chưa liên lạc được|mất liên lạc|vẫn chưa liên lạc được|chưa xác định tung tích|chưa rõ tung tích)\s*(với|cho|with)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|công nhân|nhóm)?\b",
            r"\b(cuốn trôi|cuốn|vùi lấp|chôn vùi)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}(?:[^0-9]{{0,20}})?\s*(?:bị|đã)?\s*{MISS_WORD}\b",
            rf"\b(?:làm|khiến)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:rơi\s*vào\s*tình\s*trạng\s*)?{MISS_WORD}\b",
            rf"\b(?:đến\s*nay|tính\s*đến|hiện\s*còn|vẫn\s*còn)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{MISS_WORD}\b",
            rf"\btrong\s*đó\s*,?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{MISS_WORD}\b",
            rf"\b{MISS_WORD}\s*(?:trên\s*biển|ngoài\s*khơi|dưới\s*biển|trên\s*sông|trên\s*suối)\s*[:,-]?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{MISS_WORD}\s*(?:trên\s*biển|ngoài\s*khơi|dưới\s*biển|trên\s*sông|trên\s*suối)\b",
            rf"\b(?:trôi\s*dạt|chìm\s*tàu|lật\s*tàu|lật\s*thuyền|rơi\s*xuống\s*biển|rơi\s*xuống\s*sông)\b(?:[^0-9]{{0,60}})?\b{MISS_WORD}\b(?:[^0-9]{{0,20}})?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b(?:đang\s*tìm\s*kiếm|tổ\s*chức\s*tìm\s*kiếm|tiếp\s*tục\s*tìm\s*kiếm|mở\s*rộng\s*phạm\s*vi\s*tìm\s*kiếm|truy\s*tìm|rà\s*soát)\b(?:[^0-9]{{0,30}})?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:mất\s*tích|mất\s*liên\s*lạc|chưa\s*tìm\s*thấy)?\b",
            rf"\b(?:không\s*liên\s*lạc\s*được|không\s*liên\s*hệ\s*được|không\s*bắt\s*được\s*liên\s*lạc|không\s*thể\s*liên\s*lạc)\s*(?:với)?(?:[^0-9]{{0,15}})?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*)?(?:cuốn\s*trôi|nước\s*cuốn|lũ\s*cuốn|vùi\s*lấp|chôn\s*vùi)\b(?:[^.\n]{{0,40}})?\b(?:chưa\s*tìm\s*thấy|không\s*rõ\s*tung\s*tích|mất\s*tích)\b",
            r"\b(?:mat\s*tich|mat\s*lien\s*lac|khong\s*ro\s*tung\s*tich|chua\s*tim\s*thay|troi\s*dat)\b",
        ]
    },

    "injured": {
        "terms": [
            "bị thương", "bị thương nặng", "bị thương nhẹ", "trọng thương", "xây xát", "chấn thương", "đa chấn thương", "gãy xương", "bỏng", "bị bỏng", "bất tỉnh", "ngất xỉu", "sốc", "ngộ độc", "khó thở", "nhập viện", "đưa đi bệnh viện", 
            "đưa vào bệnh viện", "cấp cứu", "điều trị", "sơ cứu", "chuyển viện", "đang điều trị", "được điều trị", "thương tích", "bị thương", "bị thương do", "bị thương vì",
            "bị thương trong", "bị thương khi", "bị thương phải nhập viện", "phải nhập viện", "nhập viện cấp cứu",
            "đi cấp cứu", "được cấp cứu", "cấp cứu tại chỗ", "đưa đi cấp cứu", "đưa đến bệnh viện", "đưa vào viện", "đưa tới cơ sở y tế",
            "đưa đi bệnh viện điều trị", "điều trị tại bệnh viện", "đang cấp cứu",
            "đang điều trị", "được điều trị", "xuất viện", "bị thương nặng", "bị thương nhẹ", "trọng thương", "nguy kịch",
            "đa chấn thương", "chấn thương sọ não", "dập nát", "dập phổi",
            "gãy tay", "gãy chân", "gãy xương", "gãy cột sống", "chấn thương cột sống",
            "bỏng nặng", "bỏng nhẹ", "bị bỏng", "ngạt khói", "sặc khói",
            "ngộ độc khí", "ngộ độc", "khó thở", "hôn mê", "bất tỉnh",
            "người dân", "ngư dân", "thuyền viên", "hành khách", "tài xế", "lái xe",
            "du khách", "cư dân", "học sinh", "công nhân", "chiến sĩ"
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|ca)\s*(bị thương|trọng thương|nhập viện|cấp cứu|đa chấn thương|thương tích|xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(làm|khiến|gây)\s*(bị|trọng thương|bị bỏng|bất tỉnh|gãy xương|đa chấn thương)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b",
            r"\b(đưa|chuyển|sơ cứu|điều trị cho|cấp cứu cho|ghi nhận|có)(?:[^0-9]{0,30})?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)(?:[^a-z0-9]{0,10})?\s*(đi|tới|bị|do)?\s*(cấp cứu|bệnh viện|viện|xây xát|bỏng|bất tỉnh|gãy xương|chấn thương)\b",
            r"\b(bị thương|bị xây xát|bị bỏng|bất tỉnh|gãy xương|chấn thương)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:{INJ_WORD})\b",
            rf"\b(?:ghi\s*nhận|thống\s*kê|xác\s*định|báo\s*cáo|tính\s*đến)\s*(?:là|có)?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*thương|thương\s*tích|nhập\s*viện|cấp\s*cứu)\b",
            rf"\b(?:làm|khiến|gây)\s*(?:{QUAL}\s*)?{NUM_HARD}\s*{UNIT}\s*(?:bị\s*thương|trọng\s*thương|nhập\s*viện|cấp\s*cứu|bỏng|bất\s*tỉnh)\b",
            rf"\b(?:đưa|chuyển|sơ\s*cứu|cấp\s*cứu|điều\s*trị)\s*(?:cho)?(?:[^0-9]{{0,30}})?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:đi|tới|vào)?\s*(?:bệnh\s*viện|cơ\s*sở\s*y\s*tế|viện|trạm\s*y\s*tế|cấp\s*cứu)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:phải\s*nhập\s*viện|được\s*đưa\s*đi\s*cấp\s*cứu|được\s*đưa\s*đến\s*bệnh\s*viện|đang\s*cấp\s*cứu|đang\s*điều\s*trị)\b",
            rf"\btrong\s*đó\s*,?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*thương\s*nặng|bị\s*thương\s*nhẹ|trọng\s*thương)\b",
            r"\b(?:bị\s*thương|thương\s*tích|trọng\s*thương)\s*do\s*(?:cây\s*đổ|tường\s*sập|sạt\s*lở|lũ\s*cuốn|đá\s*lăn|sét\s*đánh|gió\s*giật|mưa\s*đá|va\s*đập|tai\s*nạn)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*(?:ca\s*)?(?:nhập\s*viện|cấp\s*cứu)\b",
            r"\b(?:bi\s*thuong|nhap\s*vien|cap\s*cuu|chan\s*thuong|da\s*chan\s*thuong|gay\s*xuong|bong)\b",
        ]
    },
    "damage": {
        "terms": [
            "thiệt hại", "tổn thất", "ước tính thiệt hại", "thiệt hại về tài sản",
            "thiệt hại nặng", "thiệt hại nghiêm trọng", "tàn phá", "trắng tay", "mất trắng", "trôi sạch", "vỡ trận", "trắng tay chỉ sau một đêm", "điêu đứng", "tan hoang", "mất trắng tài sản", "không còn gì",
            "hư hỏng", "hư hại", "hư hỏng nặng", "hư hại nặng", "tổng giá trị thiệt hại", "con số thiệt hại",
            "sập", "đổ sập", "sập đổ", "đổ", "nứt", "tốc mái",
            "sập nhà", "đổ tường", "nứt tường", "nứt nhà", "sập mái", "sập mái tôn",
            "bay mái", "tốc mái hàng loạt", "xiêu vẹo", "đổ sập hoàn toàn",
            "ngập", "ngập nhà", "ngập sâu", "ngập lút", "ngập úng",
            "cuốn trôi", "trôi nhà", "trôi xe", "lũ cuốn", "nước cuốn",
            "sạt lở", "sạt lở đất", "sạt lở đường", "sạt lở taluy",
            "sụt lún", "sụp lún", "nứt mặt đường", "đứt đường", "đường bị chia cắt",
            "chia cắt", "cô lập", "sập cầu", "hỏng cầu", "hư hỏng cầu",
            "mất điện", "cúp điện", "cắt điện", "mất điện diện rộng",
            "mất nước", "cắt nước", "mất sóng", "mất liên lạc", "đứt cáp",
            "đổ cột điện", "đứt đường dây", "hư hỏng trạm biến áp",
            "cây đổ", "đổ cây", "gãy cây", "gãy đổ",
            "thiệt hại ước tính", "ước tính ban đầu", "thiệt hại ban đầu", "thiệt hại kinh tế",
            "tổng thiệt hại", "tổng mức thiệt hại", "giá trị thiệt hại", "thiệt hại lên tới",
            "thiệt hại hàng chục tỷ", "thiệt hại hàng trăm tỷ",
            "nhà ở", "nhà dân", "nhà cửa", "nhà tạm", "nhà xưởng", "kho xưởng", "kho",
            "công trình", "công trình dân sinh", "công trình công cộng",
            "trường học", "điểm trường", "phòng học", "trạm y tế", "trụ sở", "UBND",
            "nhà văn hóa", "nhà sinh hoạt cộng đồng",
            "sập hoàn toàn", "sập một phần", "hư hỏng hoàn toàn", "hư hỏng nặng", "hư hỏng nhẹ",
            "tốc mái", "tốc mái hoàn toàn", "tốc mái một phần", "bay mái", "bung mái",
            "nứt tường", "nứt nhà", "nứt nền", "nứt mặt đường",
            "xe bị cuốn trôi", "phương tiện bị cuốn trôi", "tài sản bị cuốn trôi", "trôi mất",
            "thiet hai", "ton that", "uoc tinh", "toc mai", "sap", "hu hong", "dien dung", "trang tay", "tan hoang",
            "sat lo", "sut lun", "xoi lo", "mat dien", "mat nuoc", "dut cap quang",
            "hoa mau", "cay trong", "gia suc", "gia cam", "long be", "be ca", "kho xưởng", "kho",
            "công trình", "công trình dân sinh", "công trình công cộng",
            "trường học", "điểm trường", "phòng học", "trạm y tế", "trụ sở", "UBND",
            "nhà văn hóa", "nhà sinh hoạt cộng đồng",
            "sập hoàn toàn", "sập một phần", "hư hỏng hoàn toàn", "hư hỏng nặng", "hư hỏng nhẹ",
            "tốc mái", "tốc mái hoàn toàn", "tốc mái một phần", "bay mái", "bung mái",
            "vùng rốn lũ", "sập bờ kè", "tái thiết", "khắc phục", "xâm nhập mặn sâu",
        ],
        "regex": [
            r"\b(?P<prefix>ước\s*tính\s*)?(?P<keyword>thiệt\s*hại|tổn\s*thất|tổng\s*giá\s*trị\s*thiệt\s*hại|con\s*số\s*thiệt\s*hại|chi\s*phí|mất\s*mát)(?:[^0-9]{0,40})?\s*(?P<qualifier>ước|ước\s*tính|khoảng|lên\s*tới|hơn|trên|ban\s*đầu|ngót|xấp\s*xỉ|\s)*\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?)\s*(?P<unit>tỷ|triệu)\s*(đồng|VND)\b",
            r"\b(mất\s*trắng|thiệt\s*hại\s*khoảng)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)\s*(?P<unit>tỷ|triệu)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)(?:[^0-9]{0,20})?\s*(bị|đã|có)?\s*(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|sạt lở|gãy đổ|vùi lấp|nứt|sụt lún|chia cắt|cô lập|cháy|mất điện|mất nước|ngập úng|trôi)\b",
            r"\b(sập|đổ sập|tốc mái|hư hỏng|hư hại|ngập|cuốn trôi|vùi lấp|làm sập|gãy đổ|nứt|sụt lún|chia cắt|cô lập|cháy|mất điện|mất nước|trôi|ngập úng)(?:[^0-9]{0,20})?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|nhà văn hóa|trường học|cột điện|nhà|căn|hộ|cầu|cống|trường|lớp|trụ sở|cột)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>căn nhà|ngôi nhà|hộ|nhà|căn)(?:[^0-9]{0,10})?\s*(?:đã|bị|có)?\s*(?:nhà\s*)?(?:bị\s*)?(sạt lở|sập|trôi|lũ cuốn|vùi lấp|chia cắt|cô lập|cháy|mất điện|mất nước|ảnh hưởng)\b",
            r"\b(sập|đổ|gãy|hư hỏng|tốc mái|cuốn trôi)\s*(hoàn toàn|hàng loạt)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>mét|m)?\s*(tường rào|mái tôn|nhà xưởng|kho|chuồng trại|trạm biến áp|đường dây|cột điện|cây xanh|cây)\b",
            rf"\b(?:thiệt\s*hại|tổn\s*thất|tổng\s*(?:giá\s*trị|mức)\s*thiệt\s*hại|giá\s*trị\s*thiệt\s*hại)(?:[^0-9]{{0,40}})?{QUAL}\s*{NUM}\s*(?P<unit>đồng|nghìn\s*tỷ|tỷ|triệu)\s*(?:đồng|VND|VNĐ)?\b",
            rf"\b(?:thiệt\s*hại|tổn\s*thất)(?:[^0-9]{{0,40}})?{QUAL}\s*{NUM}\s*(?P<unit>USD|\$|đô\s*la|đô\s*la\s*Mỹ)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*(?:[–-]|đến)\s*\d+)?)\s*(?P<unit>nhà\s*ở|nhà\s*dân|căn\s*nhà|ngôi\s*nhà|hộ|nhà|phòng\s*học|điểm\s*trường|trường\s*học|trạm\s*y\s*tế|trụ\s*sở|nhà\s*xưởng|kho|công\s*trình|nhà\s*văn\s*hóa)\b(?:[^0-9]{0,30})?\b(?:bị|đã|có)?\s*(?:sập(?:\s*hoàn\s*toàn|\s*một\s*phần)?|đổ\s*sập|tốc\s*mái(?:\s*hoàn\s*toàn|\s*một\s*phần)?|bay\s*mái|hư\s*hỏng(?:\s*nặng|\s*nhẹ)?|hư\s*hại(?:\s*nặng|\s*nhẹ)?|ngập(?:\s*sâu|\s*lút)?|nứt|xiêu\s*vẹo|cháy)\b",
            rf"\b(?:sạt\s*lở|xói\s*lở|cuốn\s*trôi|hư\s*hỏng|đứt|sụt\s*lún)\b(?:[^0-9]{{0,25}})?\b(?:tuyến|đoạn)?\s*(?:đường|quốc\s*lộ|tỉnh\s*lộ|đường\s*liên\s*xã|đường\s*liên\s*thôn|đường\s*sắt|kè|đê|cầu|cống)\b(?:[^0-9]{{0,20}})?\s*{QUAL}\s*(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>km|m|mét)\b",
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>km|m|mét)\b(?:[^.\n]{0,20})?\b(?:đường|kè|đê|cầu|cống)\b(?:[^.\n]{0,20})?\b(?:bị\s*)?(?:sạt\s*lở|xói\s*lở|cuốn\s*trôi|hư\s*hỏng|đứt|sụt\s*lún)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>hộ|hộ\s*dân|khách\s*hàng|người|thuê\s*bao|trạm\s*BTS|cột\s*BTS|trạm\s*biến\s*áp|cột\s*điện)\b(?:[^.\n]{0,30})?\b(?:bị|đã|có)?\s*(?:mất\s*điện|cúp\s*điện|mất\s*nước|gián\s*đoạn\s*cấp\s*nước|mất\s*sóng|mất\s*tín\s*hiệu|mất\s*liên\s*lạc|đứt\s*cáp(?:\s*quang)?)\b",
            rf"\b(?:mất\s*điện|cúp\s*điện|mất\s*nước|mất\s*sóng|gián\s*đoạn\s*thông\s*tin|đứt\s*cáp(?:\s*quang)?)\b(?:[^0-9]{{0,30}})?\s*{QUAL}\s*(?P<num>\d{{1,3}}(?:[.,]\d{{3}})*|\d+)\s*(?P<unit>hộ|khách\s*hàng|thuê\s*bao|trạm\s*BTS)\b",
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta)\b(?:[^.\n]{0,30})?\b(?:lúa|mạ|hoa\s*màu|rau\s*màu|cây\s*trồng|vườn\s*cây|rừng|diện\s*tích)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:ngập(?:\s*úng|\s*sâu)?|hư\s*hại|hư\s*hỏng|thiệt\s*hại|mất\s*trắng|dập\s*nát|gãy\s*đổ)\b",
            r"\b(?:mất\s*trắng|thiệt\s*hại|hư\s*hại)\b(?:[^0-9]{0,25})?\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>con)\s*(?:trâu|bò|lợn|heo|dê|ngựa|gà|vịt|gia\s*súc|gia\s*cầm)\b(?:[^.\n]{0,25})?\b(?:bị\s*)?(?:chết|cuốn\s*trôi|thiệt\s*hại|mất)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>lồng\s*bè|bè|ao|đầm)\b(?:[^.\n]{0,30})?\b(?:nuôi|thủy\s*sản|cá)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:hư\s*hỏng|cuốn\s*trôi|thiệt\s*hại|vỡ|trôi)\b",
            r"\b(?:cá|thủy\s*sản)\s*(?:chết|thiệt\s*hại)\b(?:[^0-9]{0,25})?\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tấn|kg|con)?\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>xe|ô\s*tô|xe\s*máy|phương\s*tiện)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:cuốn\s*trôi|ngập|hư\s*hỏng|trôi)\b",
            r"\b(?P<num>hàng\s*(?:trăm|ngàn|nghìn|chục|vạn))\s*(?P<unit>hộ|hộ\s*dân|người|người\s*dân|nhân\s*khẩu|thôn|bản|xã)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:cô\s*lập|chia\s*cắt|ngập|mắc\s*kẹt|sơ\s*tán|di\s*dời)\b",
            r"\b(?:thiet\s*hai|ton\s*that|toc\s*mai|sat\s*lo|sut\s*lun|mat\s*dien|mat\s*nuoc|dut\s*cap\s*quang|hoa\s*mau|cay\s*trong|gia\s*suc|gia\s*cam|long\s*be)\b",
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
            "sơ tán", "sơ tán khẩn cấp", "tạm sơ tán", "sơ tán người dân",
            "di dời", "di dời khẩn cấp", "di dời dân", "di tản", "evacuation",
            "đưa dân đến nơi an toàn", "đưa người dân đi tránh trú", "điểm tránh trú",
            "tê liệt giao thông", "gián đoạn giao thông", "đình trệ giao thông",
            "tắc đường", "ùn tắc", "kẹt xe", "ngập đường", "đường ngập sâu",
            "phân luồng", "cấm đường", "cấm lưu thông", "cấm xe", "hạn chế phương tiện",
            "tạm đóng đường", "đóng đường", "phong tỏa đường", "chốt chặn", "rào chắn",
            "tạm dừng khai thác", "tạm dừng lưu thông", "tạm dừng hoạt động vận tải",
            "tạm dừng chạy tàu", "dừng tàu", "dừng xe", "hoãn chuyến", "hủy chuyến",
            "đóng cửa sân bay", "tạm đóng sân bay", "hoãn bay", "hủy chuyến bay",
            "tạm dừng đường sắt", "dừng chạy tàu", "hoãn tàu", "hủy tàu",
            "dừng phà", "tạm dừng bến phà", "cấm đò", "dừng đò",
            "đóng cửa trường", "cho học sinh nghỉ", "nghỉ học", "tạm nghỉ học",
            "tạm dừng dạy học", "học online", "chuyển sang học trực tuyến",
            "hoãn thi", "dời lịch thi", "tạm dừng làm việc", "cho nghỉ làm",
            "tạm dừng sản xuất", "ngừng sản xuất", "đình chỉ hoạt động",
            "tạm ngưng hoạt động", "tạm đóng cửa", "đóng cửa", "ngừng hoạt động",
            "hoãn", "hủy", "dừng hoạt động", "đóng cửa chợ", "tạm dừng chợ",
            "cấm biển", "cấm ra khơi", "không ra khơi", "không được ra khơi",
            "tàu thuyền không ra khơi", "tàu thuyền vào bờ", "kêu gọi tàu thuyền vào bờ",
            "neo đậu tránh trú", "trú bão", "khu neo đậu", "khu tránh trú bão",
            "mất điện", "mất điện diện rộng", "cúp điện", "cắt điện", "ngừng cấp điện",
            "mất nước", "gián đoạn cấp nước", "ngừng cấp nước",
            "mất sóng", "mất mạng", "mất internet", "mất 3G", "mất 4G", "mất 5G",
            "mất sóng", "mất mạng", "mất internet", "mất 3G", "mất 4G", "mất 5G",
            "gián đoạn thông tin", "gián đoạn viễn thông", "đứt cáp quang",
            "tiếp tế", "cứu trợ", "viện trợ", "hàng cứu trợ", "nhu yếu phẩm", "lương thực",
            "cô lập", "chia cắt", "bị cô lập", "bị chia cắt",
        ],
        "regex": [
            r"\b(cấm|đóng|tạm dừng|tạm ngưng)\s*(?P<unit>đường|lưu thông)\b",
            r"\b(sơ tán|di dời|di tản)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(sơ tán|di dời|di tản)\s*(?P<qualifier>khẩn cấp)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>người|hộ|hộ dân|nhân khẩu)(?:[^0-9]{0,20})?\s*(phải|cần|đã)?\s*(sơ tán|di dời|di tản)\b",
            # A) Sơ tán/di dời/di tản (có số) – hỗ trợ range + qualifier
            rf"\b(?:sơ\s*tán|di\s*dời|di\s*tản)\s*(?:khẩn\s*cấp)?\s*{QUAL}\s*{NUM}\s*(?:{PEOPLE}|{HOUSE})\b",
            rf"\b{QUAL}\s*{NUM}\s*(?:{PEOPLE}|{HOUSE})(?:[^0-9]{{0,25}})?\s*(?:phải|cần|đã)?\s*(?:sơ\s*tán|di\s*dời|di\s*tản)\b",
            r"\b(?:tổ\s*chức\s*)?(?:sơ\s*tán|di\s*dời|di\s*tản)\s*(?:khẩn\s*cấp)?\b",
            r"\bđưa\s*(?:người\s*dân|dân)\s*(?:đến|tới)\s*(?:nơi\s*an\s*toàn|khu\s*tránh\s*trú|điểm\s*tránh\s*trú)\b",
            r"\b(?:cấm|đóng|tạm\s*đóng|phong\s*tỏa|chặn|rào\s*chắn|hạn\s*chế)\s*(?:toàn\s*bộ\s*)?(?P<obj>đường|tuyến\s*đường|quốc\s*lộ|tỉnh\s*lộ|cao\s*tốc|cầu|hầm|bến\s*phà|bến\s*đò|cửa\s*khẩu|luồng\s*lạch)\b",
            r"\b(?:tạm\s*dừng|tạm\s*ngưng|đình\s*chỉ)\s*(?P<obj>lưu\s*thông|giao\s*thông|vận\s*tải|khai\s*thác|hoạt\s*động)\b",
            r"\b(?:hoãn|hủy|huỷ)\s*(?P<obj>chuyến\s*bay|chuyến\s*tàu|chuyến\s*xe|chuyến\s*phà|chuyến\s*đò)\b",
            r"\b(?:đóng\s*cửa|tạm\s*đóng)\s*(?P<obj>sân\s*bay|ga|bến\s*xe|cảng|bến\s*phà)\b",
            r"\b(?:tê\s*liệt|đình\s*trệ|gián\s*đoạn)\s*(?:giao\s*thông|vận\s*tải)\b",
            r"\b(?:ùn\s*tắc|kẹt\s*xe|tắc\s*đường)\b",
            r"\b(?:đóng\s*cửa\s*trường|tạm\s*đóng\s*cửa\s*trường)\b",
            rf"\b{QUAL}\s*{NUM}\s*(?:em|cháu|học\s*sinh)\s*(?:nghỉ\s*học|tạm\s*nghỉ\s*học|nghỉ\s*làm)\b",
            rf"\b(?:cho\s*)?{QUAL}\s*{NUM}\s*(?:em|cháu|học\s*sinh)\s*(?:nghỉ\s*học|tạm\s*nghỉ\s*học)\b",
            r"\b(?:huy\s*động|điều\s*động|tổ\s*chức)?\s*(?P<num_soft>hàng\s*trăm|hàng\s*nghìn|nhiều|vài\s*trăm)\s*(?P<unit>chiến\s*sĩ|cán\s*bộ|người|tình\s*nguyện\s*viên)\s*(?:giúp\s*dân|cứu\s*hộ|cứu\s*nạn|khắc\s*phục|ứng\s*phó)\b",
            r"\b(?P<unit>chiến\s*sĩ|cán\s*bộ|lực\s*lượng)\s*(?P<num_soft>nhiều|khẩn\s*trương|giúp\s*dân)\s*(?:giúp\s*dân|hỗ\s*trợ\s*dân|cấp\s*phát|tiếp\s*tế)\b",
            r"\b(?:hoãn|dời|điều\s*chỉnh)\s*lịch\s*thi|hoãn\s*thi|dời\s*lịch\s*thi\b",
            r"\b(?:cấm\s*biển|cấm\s*ra\s*khơi|không\s*ra\s*khơi|tàu\s*thuyền\s*không\s*ra\s*khơi)\b",
            r"\b(?:kêu\s*gọi|yêu\s*cầu)\s*(?:tàu\s*thuyền|ngư\s*dân)\s*(?:vào\s*bờ|neo\s*đậu|trú\s*bão)\b",
            r"\bneo\s*đậu\s*tránh\s*trú|khu\s*neo\s*đậu|khu\s*tránh\s*trú\s*bão\b",
            r"\b(?:mất\s*điện|cúp\s*điện|cắt\s*điện|ngừng\s*cấp\s*điện)\b",
            r"\b(?:mất\s*nước|ngừng\s*cấp\s*nước|gián\s*đoạn\s*cấp\s*nước)\b",
            r"\b(?:mất\s*sóng|mất\s*mạng|mất\s*internet|gián\s*đoạn\s*thông\s*tin|đứt\s*cáp(?:\s*quang)?)\b",
            rf"\b{QUAL}\s*{NUM}\s*(?P<unit>hộ|khách\s*hàng|thuê\s*bao|trạm\s*BTS)\b(?:[^.\n]{{0,25}})?\b(?:mất\s*điện|mất\s*nước|mất\s*sóng|gián\s*đoạn)\b",
            r"\b(?:tiếp\s*tế|cứu\s*trợ|viện\s*trợ|hàng\s*cứu\s*trợ|nhu\s*yếu\s*phẩm|lương\s*thực)\b",
            r"\b(?:cô\s*lập|chia\s*cắt|bị\s*cô\s*lập|bị\s*chia\s*cắt)\b",
            r"\b(?:so\s*tan|di\s*doi|di\s*tan|cam\s*duong|dong\s*duong|cam\s*bien|cam\s*ra\s*khoi|mat\s*dien|mat\s*nuoc|mat\s*song|dut\s*cap\s*quang)\b",
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
            "lồng bè", "lồng nuôi", "bè cá", "mất trắng thủy sản", "trôi lồng bè",
            "diện tích gieo trồng", "diện tích canh tác", "diện tích bị ảnh hưởng",
            "ngập úng", "ngập sâu", "ngập lụt", "dập nát", "đổ ngã", "gãy đổ", "rụng quả",
            "hư hại", "hư hỏng", "thiệt hại", "mất trắng", "mất mùa",
            "lúa", "mạ", "lúa vụ", "lúa đông xuân", "lúa hè thu",
            "hoa màu", "rau màu", "cây trồng", "cây ăn quả", "vườn cây",
            "mía", "sắn", "ngô", "bắp", "khoai", "đậu", "lạc", "dưa",
            "cà phê", "cao su", "hồ tiêu", "điều", "chè", "chuối", "thanh long", "xoài",
            "gia súc", "gia cầm", "vật nuôi", "chăn nuôi",
            "trâu", "bò", "lợn", "heo", "dê", "cừu", "gà", "vịt", "ngan", "ngỗng",
            "chết", "bị chết", "cuốn trôi", "trôi", "thất thoát",
            "chuồng trại", "trang trại", "trại chăn nuôi", "chuồng bị sập", "chuồng bị ngập",
            "nuôi trồng thủy sản", "thủy sản", "tôm", "cá",
            "ao nuôi", "đầm nuôi", "bè", "lồng", "lồng bè", "lồng nuôi", "bè cá",
            "trôi lồng bè", "vỡ ao", "tràn ao", "thất thoát thủy sản", "cá chết", "tôm chết", "lúa chết", "lúa chết khô", "gặt lúa", "chạy lụt", "chạy lũ",
        ],
        "regex": [
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta|héc\s*ta|sào)\s*(?P<crop>lúa|hoa\s*màu|cây\s*trồng|ruộng|mía|ngô|bắp|rau|cà\s*phê|tiêu|điều)\b(?:[^.\n]{0,30})?\b(?P<status>bị\s*ngập|ngập\s*úng|hư\s*hại|thiệt\s*hại|mất\s*trắng|đổ\s*ngã|dập\s*nát)\b",
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>tấn|kg)\s*(?P<crop>lúa|ngô|mía|rau|nông\s*sản)\b(?:[^.\n]{0,30})?\b(?P<status>hư\s*hại|thiệt\s*hại|mất)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>con)\s*(trâu|bò|lợn|gà|vịt|gia súc|gia cầm)\b",
            r"\b(?P<num>\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>lồng bè|lồng|bè)\b",
            r"\b(vỡ|tràn|mất trắng)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>ao|đầm|lồng bè|ha|mẫu|công)\s*(nuôi|tôm|cá|thủy sản)?\b",
            r"\b(chết|trôi)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>con|tấn|kg)?\s*(tôm|cá|gia súc|gia cầm|lợn|gà|bò)\b",
            rf"\b{QUAL}\s*{NUM}\s*{AREA_UNIT}\s*{CROP}\b(?:[^.\n]{{0,30}})?\b{CROP_STATUS}\b",
            rf"\b{CROP}\b(?:[^.\n]{{0,30}})?\b{CROP_STATUS}\b(?:[^0-9]{{0,30}})?\b{QUAL}\s*{NUM}\s*{AREA_UNIT}\b",
            rf"\b(?:diện\s*tích|gieo\s*trồng|canh\s*tác)\b(?:[^0-9]{{0,20}})?\b{QUAL}\s*{NUM}\s*{AREA_UNIT}\b(?:[^.\n]{{0,30}})?\b(?:bị\s*)?(?:thiệt\s*hại|hư\s*hại|ngập|mất\s*trắng)\b",
            rf"\b(?:thiệt\s*hại|hư\s*hại)\b(?:[^0-9]{{0,25}})?\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta)\b",
            rf"\b{QUAL}\s*{NUM}\s*(?:{MASS_UNIT})\b(?:[^.\n]{{0,20}})?\b(?:nông\s*sản|lúa|ngô|mía|rau)\b(?:[^.\n]{{0,20}})?\b(?:bị\s*)?(?:hư\s*hại|thiệt\s*hại|mất)\b",
            rf"\b{QUAL}\s*{NUM}\s*{COUNT_UNIT}\s*{LIVESTOCK}\b(?:[^.\n]{{0,25}})?\b{LIVE_STATUS}\b",
            rf"\b{LIVESTOCK}\b(?:[^.\n]{{0,25}})?\b{LIVE_STATUS}\b(?:[^0-9]{{0,25}})?\b{QUAL}\s*{NUM}\s*{COUNT_UNIT}\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>chuồng|chuồng\s*trại|trang\s*trại|trại\s*chăn\s*nuôi)\b(?:[^.\n]{0,25})?\b(?:bị\s*)?(?:sập|ngập|hư\s*hỏng|hư\s*hại|cuốn\s*trôi)\b",
            rf"\b{QUAL}\s*{NUM}\s*(?P<unit>{AQUA_OBJ})\b(?:[^.\n]{{0,30}})?\b(?:nuôi|thủy\s*sản|tôm|cá)?\b(?:[^.\n]{{0,30}})?\b{AQUA_STATUS}\b",
            rf"\b{AQUA_STATUS}\b(?:[^0-9]{{0,30}})?\b{QUAL}\s*{NUM}\s*(?P<unit>{AQUA_OBJ})\b",
            rf"\b{QUAL}\s*{NUM}\s*(?:{MASS_UNIT})\b(?:[^.\n]{{0,20}})?\b(?:{AQUA})\s*(?:chết|thiệt\s*hại)\b",
            rf"\b{QUAL}\s*{NUM}\s*{COUNT_UNIT}\s*(?:{AQUA})\b(?:[^.\n]{{0,15}})?\b(?:chết|thiệt\s*hại)\b",
            r"\b(?:hoa\s*mau|cay\s*trong|lua|ngo|bap|mia|san|rau\s*mau|gia\s*suc|gia\s*cam|trau|bo|lon|heo|ga|vit|thuy\s*san|tom|ca|ao\s*nuoi|dam\s*nuoi|long\s*be|mat\s*trang|mat\s*mua|ngap\s*ung|thiet\s*hai)\b",
        ]
    },


}

# Negation terms to avoid false positives in impact extraction
NEGATION_TERMS = {
    "general": [
        "không", "chưa", "không có", "chưa có", "không gây", "không làm", "chưa ghi nhận",
        "không thiệt hại", "tránh", "thoát", "không bị", "chưa bị", "hạn chế", "ngăn chặn",
        "phòng ngừa", "đối phó", "ứng phó", "chuẩn bị", "dự báo", "cảnh báo"
    ],
    "deaths": [
        "không có người chết", "không gây thiệt mạng", "không có thương vong",
        "may mắn không có", "không tử vong", "chưa có người chết"
    ],
    "missing": [
        "đã tìm thấy", "đã liên lạc được", "không còn mất tích", "đã cứu sống",
        "đã được cứu", "không có người mất tích"
    ],
    "injured": [
        "không ai bị thương", "không có người bị thương", "may mắn thoát nạn",
        "xây xát nhẹ", "không nguy hiểm tính mạng"
    ],
    "damage": [
        "không thiệt hại về tài sản", "không gây hư hỏng", "không bị ảnh hưởng",
        "không sập", "không tốc mái", "chưa có thiệt hại"
    ],
    "agriculture": [
        "không ảnh hưởng mùa màng", "không gây ngập", "không thiệt hại lúa",
        "đã thu hoạch xong", "chủ động thu hoạch"
    ]
}

# Deduplicate impact terms to avoid biased scoring and reduce CPU overhead
for k, v in IMPACT_KEYWORDS.items():
    if "terms" in v:
        v["terms"] = dedupe_keep_order(v["terms"])

# Boilerplate tokens
BOILERPLATE_TOKENS = [
    r"\bvideo\b", r"\bảnh\b", r"\bclip\b", r"\bphóng\s*sự\b", r"\btrực\s*tiếp\b",
    r"\blive\b", r"\bhtv\b", r"\bphoto\b", r"\bupdate\b"
]





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
    "TP. Hà Nội": ["Hà Nội", "HN", "Ha Noi", "Thủ đô Hà Nội"],
    "TP. Huế": ["Huế", "Thành phố Huế", "TP Huế", "Thừa Thiên Huế", "TT Huế", "Thua Thien Hue"],
    "Lai Châu": ["Lai Châu", "Lai Chau"],
    "Điện Biên": ["Điện Biên", "Dien Bien"],
    "Sơn La": ["Sơn La", "Son La"],
    "Lạng Sơn": ["Lạng Sơn", "Lang Son"],
    "Quảng Ninh": ["Quảng Ninh", "Quang Ninh"],
    "Thanh Hóa": ["Thanh Hóa", "Thanh Hoa"],
    "Nghệ An": ["Nghệ An", "Nghe An"],
    "Hà Tĩnh": ["Hà Tĩnh", "Ha Tinh"],
    "Cao Bằng": ["Cao Bằng", "Cao Bang"],
    "Tuyên Quang": ["Tuyên Quang", "Hà Giang", "Ha Giang", "Tuyen Quang"],
    "Lào Cai": ["Lào Cai", "Yên Bái", "Yen Bai", "Lao Cai"],
    "Thái Nguyên": ["Thái Nguyên", "Bắc Kạn", "Bac Kan", "Thai Nguyen"],
    "Phú Thọ": ["Phú Thọ", "Vĩnh Phúc", "Hòa Bình", "Phu Tho", "Vinh Phuc", "Hoa Binh"],
    "Bắc Ninh": ["Bắc Ninh", "Bắc Giang", "Bac Ninh", "Bac Giang"],
    "Hưng Yên": ["Hưng Yên", "Thái Bình", "Hung Yen", "Thai Binh"],
    "TP. Hải Phòng": ["Hải Phòng", "Hải Dương", "Hai Phong", "Hai Duong", "HP"],
    "Ninh Bình": ["Ninh Bình", "Hà Nam", "Nam Định", "Ninh Binh", "Ha Nam", "Nam Dinh"],
    "Quảng Trị": ["Quảng Trị", "Quảng Bình", "Quang Tri", "Quang Binh"],
    "TP. Đà Nẵng": ["Đà Nẵng", "Quảng Nam", "Da Nang", "Quang Nam", "ĐN"],
    "Quảng Ngãi": ["Quảng Ngãi", "Kon Tum", "Quang Ngai", "Kon Tum", "QNg"],
    "Gia Lai": ["Gia Lai", "Bình Định", "Gia Lai", "Binh Dinh"],
    "Đắk Lắk": ["Đắk Lắk", "Đắk Nông", "Dak Lak", "Dak Nong"],
    "Khánh Hòa": ["Khánh Hòa", "Ninh Thuận", "Phú Yên", "Khanh Hoa", "Ninh Thuan", "Phu Yen"],
    "Lâm Đồng": ["Lâm Đồng", "Bình Thuận", "Lam Dong", "Binh Thuan"],
    "TP. Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn", "Bà Rịa - Vũng Tàu", "Bà Rịa", "Vũng Tàu", "Bình Dương", "HCMC", "Sai Gon", "BRVT", "Binh Duong", "SG"],
    "Đồng Nai": ["Đồng Nai", "Bình Phước", "Dong Nai", "Binh Phuoc"],
    "Tây Ninh": ["Tây Ninh", "Long An", "Tay Ninh", "Long An"],
    "Đồng Tháp": ["Đồng Tháp", "Tiền Giang", "Bến Tre", "Dong Thap", "Tien Giang", "Ben Tre"],
    "An Giang": ["An Giang", "Kiên Giang", "An Giang", "Kien Giang"],
    "Vĩnh Long": ["Vĩnh Long", "Trà Vinh", "Vinh Long", "Tra Vinh"],
    "TP. Cần Thơ": ["Cần Thơ", "Hậu Giang", "Sóc Trăng", "Can Tho", "Hau Giang", "Soc Trang"],
    "Cà Mau": ["Cà Mau", "Bạc Liêu", "Ca Mau", "Bac Lieu"]
}

# Deduplicate province variants
for k, v in PROVINCE_MAPPING.items():
    PROVINCE_MAPPING[k] = dedupe_keep_order(v)
# List of valid (new) province names
PROVINCES = list(PROVINCE_MAPPING.keys())

# Geographic coordinates for the 34 provinces (Approximate Center)
PROVINCE_COORDINATES = {
    "TP. Hà Nội": [21.0285, 105.8542],
    "TP. Huế": [16.4637, 107.5908],
    "Lai Châu": [22.3846, 103.4641],
    "Điện Biên": [21.3852, 103.0235],
    "Sơn La": [21.3259, 103.9126],
    "Lạng Sơn": [21.8548, 106.7621],
    "Quảng Ninh": [21.0063, 107.5944],
    "Thanh Hóa": [20.0000, 105.5000],
    "Nghệ An": [19.0000, 105.0000],
    "Hà Tĩnh": [18.3444, 105.9056],
    "Cao Bằng": [22.6667, 106.2500],
    "Tuyên Quang": [22.0000, 105.2500],
    "Lào Cai": [22.4833, 103.9667],
    "Thái Nguyên": [21.5928, 105.8442],
    "Phú Thọ": [21.3236, 105.2111],
    "Bắc Ninh": [21.1833, 106.0667],
    "Hưng Yên": [20.6500, 106.0500],
    "TP. Hải Phòng": [20.8449, 106.6881],
    "Ninh Bình": [20.2539, 105.9750],
    "Quảng Trị": [16.7500, 107.1667],
    "TP. Đà Nẵng": [16.0544, 108.2022],
    "Quảng Ngãi": [15.1206, 108.8042],
    "Gia Lai": [14.0000, 108.0000],
    "Đắk Lắk": [12.6667, 108.0500],
    "Khánh Hòa": [12.2500, 109.1833],
    "Lâm Đồng": [11.9464, 108.4419],
    "TP. Hồ Chí Minh": [10.8231, 106.6297],
    "Đồng Nai": [11.0000, 107.0000],
    "Tây Ninh": [11.3000, 106.1667],
    "Đồng Tháp": [10.5000, 105.6667],
    "An Giang": [10.3833, 105.4333],
    "Vĩnh Long": [10.2500, 105.9667],
    "TP. Cần Thơ": [10.0333, 105.7833],
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
    return re.compile(rf"(?<!\w)({pattern})(?!\w)", re.IGNORECASE)

MEGA_PROVINCE_ACC_RE = _build_mega_prov_re(is_accented=True)

# Map for quick lookup of province attributes
PROVINCE_INFO_MAP = { item["name"]: item for item in PROVINCE_REGEXES }
# DISASTER RULES & PATTERNS

DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới (Storm/Tropical Cyclone)
    ("storm", [
        rf"(?<!\w)(?<!báo\s)(?<!tin\s)(?<!thông\stin\s)(?<!tình\shình\s)(?<!đi\s)(?<!dự\s)(?<!tờ\s)(?<!đọc\s)(?<!thông\s)(?<!cảnh\s)(?<!tình\s)(?<!khai\s)(?<!đảm\s)(?<!nhà\s)(?<!đăng\s)(?<!viết\s)(?<!bài\s)(?<!gây\s)(?<!tâm\s)bão(?!\sgiá)(?!\smạng)(?!\slòng)(?!\stài\s)(?!\stín\s)(?!\ssale)(?!\skhuyến\s)(?!\schấn\s)(?!\ssa\s)(?!\struyền\s)(?!\s*chí)(?!\s*cáo)(?!\s*hiểm)(?!\s*vệ)(?!\s*đảm)(?!\s*tàng)(?!\s*toàn)(?!\s*quản)(?!\s*trì)(?!\s*hành)(?!\s*mật)(?!\s*gồm)(?!\s*phủ)(?!\s*quát)(?!\s*trọn)(?!\s*bì)(?!\s*vây)(?!\s*nhiêu)(?!\s*lâu)(?!\s*xa)(?!\s*giờ)(?!\s*lao\s*động)(?!\s*thanh\s*niên)(?!\s*tiền\s*phong)(?!\s*tin\s*tức)(?!\s*công\s*an)(?!\s*phụ\s*nữ)(?!\s*đầu\s*tư)(?!\s*pháp\s*luật)(?!\s*giáo\s*dục)(?!\s*nhân\s*dân)(?!\s*điện\s*tử)(?!\s*vietnamnet)(?!\s*dân\s*trí)(?!\s*vnexpress)(?!\s*công\s*lý)(?!\s*văn\s*hóa)(?!\s*quốc\s*tế)(?!\s*thù)(?!\s*đáp)(?!\s*công)(?!\s*hại)(?!\s*bệnh)(?!\s*lửa)(?!\s*dư\s*luận)(?!\s*chấn\s*thương)(?!\s*đơn)(?!\s*deal)(?!\s*like)(?!\s*view)(?!\s*cấp(?!\s*\d))(?!\w)",
        r"bão\s*số\s*\d+", r"siêu\s*bão", r"tâm\s*bão", r"mắt\s*bão", r"hoàn\s*lưu\s*bão",
        r"áp\s*thấp\s*nhiệt\s*đới", r"vùng\s*áp\s*thấp", r"ATNĐ", r"ATND", r"xoáy\s*thuận\s*nhiệt\s*đới",
        r"nhiễu\s*động\s*nhiệt\s*đới", r"cường\s*độ\s*bão", r"cấp\s*bão", r"gió\s*bão", r"bão\s*khẩn\s*cấp",
        r"đổ\s*bộ", r"tiến\s*vào\s*biển\s*đông", r"tin\s*bão",
        # Named Storms: Stricter, and we'll manually ensure this doesn't pass safe_no_accent if it's too risky
        r"(?<!\w)bão\s+[A-ZĐ][a-zà-ỹ]{3,}(?!\w)",
        r"vùng\s*tâm\s*bão", r"áp\s*sát\s*ven\s*biển", r"hoàn\s*lưu\s*sau\s*bão", r"gió\s*xoáy", r"phong\s*ba", r"mưa\s*lũ", r"mưa\s*bão",
        r"bão\s*tăng\s*tốc", r"thần\s*tốc\s*tiến\s*vào", r"hồi\s*sức\s*sau\s*bão"
    ]),

  # 2) Lũ lụt (Flood) - User Cat 2
  ("flood", [
    r"lũ\s*lụt", r"ngập\s*lụt", r"ngập\s*úng", r"xả\s*lũ",
    r"lũ\s*lên", r"lũ\s*xuống", r"lũ\s*về", r"nước\s*lũ",
    r"đỉnh\s*lũ", r"mực\s*nước\s*vượt\s*báo\s*động", r"lưu\s*lượng\s*về\s*hồ",
    r"lũ\s*trên\s*các\s*sông", r"vỡ\s*đê", r"tràn\s*đê", r"vỡ\s*đập", r"vỡ\s*hồ", r"hồ\s*chứa\s*(?:(?!\.).)*\s*vỡ", r"sự\s*cố\s*hồ", r"xả\s*tràn",
    r"tin\s*lũ", r"báo\s*động\s*(?:1|2|3|I|II|III)",
    r"lũ\s*lịch\s*sử", r"ngập\s*lụt\s*cục\s*bộ", r"vùng\s*trũng\s*thấp", r"\blũ(?!\s*trẻ)\b", r"vùng\s*lũ", r"rốn\s*lũ", r"chạy\s*lũ",
    r"điều\s*tiết\s*lũ", r"thủy\s*điện\s*(?:xả|điều\s*tiết)\s*lũ", r"vượt\s*lũ\s*lịch\s*sử"
  ]),

  # 3) Lũ quét/Lũ ống (Flash Flood) - User Cat 3
  ("flash_flood", [
    r"lũ\s*quét", r"lũ\s*ống", r"lũ\s*bùn(?:\s*đá)?", r"lũ\s*đá", r"nghẽn\s*dòng",
    r"tin\s*cảnh\s*báo\s*lũ\s*quét", r"nguy\s*cơ\s*lũ\s*quét", r"lũ\s*dữ",
    r"lũ\s*cuồn\s*cuộn", r"dòng\s*lũ\s*chảy\s*xiết", r"đất\s*đá\s*đổ\s*về", r"trôi\s*cầu"
  ]),

  # 4) Sạt lở (Landslide) - User Cat 4
  ("landslide", [
    r"sạt\s*lở(?!\s*bờ\s*(?:sông|biển|kè))", r"trượt\s*lở(?!\s*bờ\s*(?:sông|biển|kè))", r"lở\s*núi", r"sập\s*taluy",
    r"đá\s*đổ", r"đá\s*lăn", r"đá\s*rơi", r"sụt\s*trượt", r"vết\s*nứt(?!\s*(?:tường|nhà))",
    r"đất\s*đá\s*vùi\s*lấp", r"đứt\s*gãy", r"sụp\s*đổ\s*địa\s*chất", r"sạt\s*taluy"
  ]),

  # 5) Sụt lún đất (Land Subsidence) - User Cat 5
  ("subsidence", [
    r"sụt\s*lún(?:\s*đất)?", r"sụp\s*lún", r"hố\s*sụt", r"hố\s*tử\s*thần", r"nghiêng\s*lún", r"sập\s*đổ",
    r"nứt\s*toác", r"sụt\s*lún\s*hạ\s*tầng", r"biến\s*dạng\s*mặt\s*đường", r"lún\s*xụt",
    r"sập\s*hầm\s*lò", r"sập\s*mỏ"
  ]),

  # 6) Hạn hán (Drought) - User Cat 6
  ("drought", [
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước(?:\s*sinh\s*hoạt)?", r"đất\s*nứt\s*nẻ", r"khô\s*cằn", r"cạn\s*trơ", r"cây\s*héo",
    r"hạn\s*mặn", r"thiếu\s*hụt\s*nguồn\s*nước", r"dòng\s*chảy\s*kiệt", r"mùa\s*cạn",
    r"vùng\s*hạn", r"chống\s*hạn", r"thiếu\s*hụt\s*mưa", r"mực\s*nước\s*chết"
  ]),

  # 7) Xâm nhập mặn (Salinity Intrusion) - User Cat 7
  ("salinity", [
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*phèn", r"nhiễm\s*mặn", r"ngăn\s*mặn", r"ranh\s*mặn", r"độ\s*mặn\s*cao", r"hạn\s*mặn",
    r"cống\s*ngăn\s*mặn", r"đẩy\s*mặn", r"nước\s*nhiễm\s*mặn", r"\d+(?:[.,]\d+)?\s*(?:‰|%o|g\/l)\b",
    r"nước\s*lợ", r"độ\s*mặn\s*vượt\s*ngưỡng", r"mặn\s*bủa\s*vây"
  ]),

  # 8) Mưa lớn/Mưa đá/Lốc/Sét (Rain/Hail/Tornado/Lightning) - User Cat 8
  # Renamed back to 'extreme_weather' to match Frontend theme.js
  ("extreme_weather", [
    # Rain
    r"mưa\s*lớn", r"mưa\s*xối\s*xả", r"mưa\s*trắng\s*trời", r"mưa\s*to", r"mưa\s*rất\s*to", r"lượng\s*mưa", r"mưa\s*kỷ\s*lục", r"mưa\s*trái\s*mùa",
    # Hail/Tornado/Lightning/Wind
    r"mưa\s*đá", r"lốc(?!\s*xoáy)", r"sấm\s*sét", r"sét\s*đánh", r"phóng\s*điện", r"dông", r"giông", r"lốc\s*xoáy", r"gió\s*mạnh", r"quật\s*đổ", r"tốc\s*mái", r"vòi\s*rồng",
    r"tố\s*lốc", r"giông\s*sét", r"tia\s*sét",
    r"giông\s*cực\s*mạnh", r"gió\s*rít", r"gió\s*giật", r"gió\s*lốc"
  ]),

  # 9) Nắng nóng (Heatwave) - User Cat 9
  ("heatwave", [
    r"nắng\s*nóng", r"thiêu\s*đốt", r"nhiệt\s*độ\s*cao", r"sốc\s*nhiệt", r"trú\s*nóng",
    r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt\s*gay\s*gắt", r"nhiệt\s*độ\s*kỷ\s*lục",
    r"chỉ\s*số\s*tia\s*cực\s*tím", r"chỉ\s*số\s*UV", r"đợt\s*nắng\s*nóng", r"nhiệt\s*độ\s*cao\s*nhất",
    r"nắng\s*cháy\s*da", r"nóng\s*rát", r"nắng\s*hạn"
  ]),

  # 10) Rét hại/Sương muối (Cold/Frost) - User Cat 10
  ("cold_surge", [
    r"trời\s*rét", r"rét\s*hại", r"rét\s*đậm", r"rét\s*khô", r"rét\s*tê\s*tái", r"sương\s*muối", r"băng\s*giá", r"đóng\s*băng", r"tuyết\s*rơi", r"tuyết\s*phủ",
    r"rét\s*đậm\s*rét\s*hại", r"nhiệt\s*độ\s*xuống\s*dưới\s*0",
    r"rét\s*buốt", r"mưa\s*tuyết",
    r"không\s*khí\s*lạnh\s*tăng\s*cường", r"gió\s*mùa\s*đông\s*bắc"
  ]),

  # 11) Động đất (Earthquake) - User Cat 11
  ("earthquake", [
    r"động\s*đất", r"địa\s*chấn", r"rung\s*chuyển", r"rung\s*lắc", r"tâm\s*chấn", r"dư\s*chấn",
    r"rung\s*chấn", r"chấn\s*tiêu", r"richter",
    r"magnitude", r"viện\s*vật\s*lý\s*địa\s*cầu",
    r"sóng\s*địa\s*chấn", r"cấp\s*độ\s*Richter"
  ]),

  # 12) Sóng thần (Tsunami) - User Cat 12
  ("tsunami", [
    r"sóng\s*thần", r"sóng\s*lớn", r"động\s*đất\s*dưới\s*biển",
    r"tsunami", r"cấp\s*báo\s*động\s*sóng\s*thần", r"tin\s*cảnh\s*báo\s*sóng\s*thần",
    r"sóng\s*cao\s*hàng\s*chục\s*mét", r"thảm\s*họa\s*sóng\s*thần"
  ]),

  # 13) Nước dâng (Storm Surge) - User Cat 13
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"sóng\s*tràn",
    r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng", r"ngập\s*lụt\s*do\s*triều"
  ]),

  # 14) Cháy rừng (Wildfire) - User Cat 14
  # 14) Cháy rừng (Wildfire) - User Cat 14
  ("wildfire", [
    r"cháy\s*rừng", r"cháy\s*tán", r"cháy\s*ngầm", r"cháy\s*thực\s*bì", r"lửa\s*rừng", 
    r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng", r"PCCCR", 
    r"giặc\s*lửa\s*rừng", r"dập\s*lửa\s*rừng", r"chữa\s*cháy\s*rừng",
    r"đám\s*cháy\s*(?:lớn|lan)\s*(?:tại|ở|trong)\s*rừng",
    r"huy\s*động\s*dập\s*lửa\s*rừng", r"đốt\s*thực\s*bì"
  ]),

  # 15) Xói lở (Erosion) - User Cat 15
  ("erosion", [
    r"xói\s*lở", r"sạt\s*lở\s*bờ\s*(?:sông|biển)", r"hàm\s*ếch", r"mương\s*xói", r"rãnh\s*xói", r"xâm\s*thực", r"xói\s*mòn",
    r"sập\s*bờ\s*kè", r"vỡ\s*bờ\s*kè", r"vỡ\s*kè"
  ]),

  # 16) Tin cảnh báo, dự báo (Warning/Forecast)
  ("warning_forecast", [
    r"bản\s*tin\s*dự\s*báo", r"tin\s*cảnh\s*báo", r"dự\s*báo\s*thời\s*tiết", r"cảnh\s*báo\s*thiên\s*tai",
    r"bản\s*tin\s*khẩn\s*cấp", r"thông\s*báo\s*khẩn", r"đài\s*khí\s*tượng", r"cảnh\s*báo\s*cực\s*đoan"
  ]),

  # 17) Khắc phục hậu quả (Recovery)
  ("recovery", [
    r"khắc\s*phục\s*hậu\s*quả", r"khắc\s*phục\s*sự\s*cố", r"khôi\s*phục\s*giao\s*thông",
    r"thống\s*kê\s*thiệt\s*hại", r"ủng\s*hộ\s*đồng\s*bào", r"cứu\s*trợ", r"tiếp\s*tế",
    r"dọn\s*dẹp\s*sau\s*bão", r"viện\s*trợ", r"hỗ\s*trợ\s*khẩn\s*cấp",
    r"tái\s*thiết\s*sau\s*(?:bão|lũ)", r"ổn\s*định\s*đời\s*sống\s*sau\s*(?:bão|lũ)",
    r"khôi\s*phục\s*sản\s*xuất", r"quỹ\s*phòng\s*chống", r"hỗ\s*trợ\s*người\s*dân\s*vùng",
    r"nghĩa\s*tình\s*(?:vùng|nơi)\s*lũ", r"cứu\s*trợ\s*người\s*dân\s*bị\s*cô\s*lập",
    r"xây\s*nhà\s*.*vùng\s*lũ", r"thi\s*thể\s*.*đã\s*được\s*tìm\s*thấy", r"khắc\s*phục\s*.*sạt\s*lở",
    r"cô\s*lập\s*.*hộ\s*dân", r"gãy\s*đôi\s*cầu", r"mất\s*tích\s*trên\s*biển",
    r"lũ\s*tràn\s*qua\s*đập", r"hư\s*hỏng\s*mặt\s*đường",
    # GENUINE DISASTER RECOVERY & INCIDENTS (High Priority)
    r"nứt\s*toác.*di\s*dời", r"lũ.*cô\s*lập.*cứu\s*dân",
    r"cuộc\s*gọi\s*cầu\s*cứu", r"tiếp\s*tế\s*thực\s*phẩm.*cô\s*lập",
    r"mưa\s*ngập\s*lịch\s*sử", r"giải\s*cứu.*mắc\s*kẹt",
    r"xuyên\s*đêm.*cứu.*dân", r"thiệt\s*hại.*do\s*thiên\s*tai",
    r"khắc\s*phục.*hư\s*hỏng.*cầu", r"sạt\s*lở.*thiệt\s*mạng",
    r"bờ\s*kè.*đổ\s*sập", r"ngập\s*cầu.*ách\s*tắc",
    r"sạt\s*lở.*cô\s*lập", r"tìm\s*thấy.*thi\s*thể.*đuối\s*nước(?=.*(?:mưa|lũ|bão|sóng|ngập|sạt))",
    r"trao\s*quà\s*.*thiệt\s*hại\s*.*(?:mưa|lũ|bão)", r"trường\s*học\s*.*thiệt\s*hại\s*.*(?:vùng|do)\s*lũ",
    r"lốc\s*xoáy\s*.*thiệt\s*hại", r"khắc\s*phục\s*.*khẩn\s*cấp\s*.*kè",
    r"tìm\s*kiếm\s*.*mất\s*tích\s*.*tàu\s*cá", r"điểm\s*tiếp\s*nhận\s*.*hàng\s*cứu\s*trợ",
    r"tái\s*thiết\s*.*khu\s*tái\s*định\s*cư", r"đảm\s*bảo\s*.*giao\s*thông\s*.*(?:mưa|lũ)",
    r"hỗ\s*trợ\s*.*người\s*dân\s*.*bị\s*thiệt\s*hại", r"chủ\s*động\s*ứng\s*phó\s*.*mưa\s*lũ",
    # ADDITIONAL BOOSTED RECOVERY PHRASES
    r"khắc\s*phục.*hạ\s*tầng.*giao\s*thông", r"hỗ\s*trợ.*đoàn\s*viên.*mưa\s*lũ",
    r"xây.*nhà.*vùng\s*lũ", r"học\s*sinh.*vùng\s*lũ.*trở\s*lại\s*trường",
    r"chuyến\s*hàng.*cứu\s*trợ.*xã\s*đảo", r"gia\s*cố.*bờ\s*kè.*hư\s*hỏng",
    r"khôi\s*phục.*đường\s*sắt.*trôi\s*nền", r"sửa\s*chữa.*kênh\s*mương.*bão\s*lũ",
    r"bơi.*vào.*cứu\s*trợ", r"bơi.*xuồng.*nhận\s*cứu\s*trợ",
    r"drone.*vận\s*chuyển.*cứu\s*trợ", r"trực\s*thăng.*thả\s*hàng",
    r"quỹ\s*cứu\s*trợ.*tiếp\s*nhận",
    r"tốc\s*mái\s*.*(?:bão|lốc)", r"sửa\s*.*(?:nhà|kênh\s*mương)\s*.*sau\s*(?:bão|lũ)",
    r"hư\s*hỏng\s*.*(?:cầu|đường|trường|công\s*trình)\s*.*do\s*(?:bão|lũ)",
    r"thiếu\s*nước\s*sạch\s*.*vùng\s*lũ", r"phục\s*hồi\s*.*sau\s*(?:bão|lũ)",
    r"tái\s*thiết\s*.*(?:cuộc\s*sống|sau\s*bão)", r"nhà\s*bị\s*sập\s*.*(?:mưa|lũ|bão)",
    r"cứu\s*hộ\s*biển",
    r"hỗ\s*trợ\s*.*(?:xây|sửa)\s*nhà\s*.*(?:bão|lũ)", r"rét\s*dưới\s*.*độ",
    r"thăm\s*hỏi\s*hỗ\s*trợ\s*.*(?:mưa|lũ|thiên\s*tai)", r"ngăn\s*nước\s*lũ",
    r"cứu\s*hộ\s*ngư\s*dân\s*trôi\s*dạt",
    r"hỗ\s*trợ\s*kinh\s*phí\s*khắc\s*phục",
    r"ổn\s*định\s*đời\s*sống", r"khôi\s*phục\s*sản\s*xuất", r"tái\s*thiết", r"hỗ\s*trợ\s*dân\s*sinh", r"bình\s*ổn\s*thị\s*trường",
    r"tìm\s*kiếm\s*cứu\s*nạn", r"tìm\s*kiếm\s*người\s*mất\s*tích", r"truy\s*tìm\s*nạn\s*nhân",
    r"thuyền\s*viên\s*mất\s*tích", r"ngư\s*dân\s*mất\s*tích", r"tàu\s*cá\s*mất\s*tích", r"trục\s*vớt\s*tàu", r"hỗ\s*trợ\s*nạn\s*nhân"
  ]),
]

# High-priority keywords are now centralized in sources.py
# High-priority keywords are now centralized in sources.py
HIGH_PRIORITY_RE = sources.HIGH_PRIORITY_RE
DANGER_RE = sources.DANGER_RE

# Risk Level Patterns (Decision 18 Art 4)
RISK_LEVEL_RE = re.compile(r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)?\s*([1-5I-V])", re.IGNORECASE)

HAZARD_ANCHOR = r"(?:bão|áp\s*thấp|lũ|ngập|sạt\s*lở|nắng\s*nóng|hạn\s*hán|xâm\s*nhập\s*mặn|gió\s*mạnh|sương\s*mù|cháy\s*rừng|động\s*đất|sóng\s*thần|triều\s*cường|nước\s*dâng|mưa\s*lớn)"
PCTT_ANCHOR   = r"(?:phòng\s*chống\s*thiên\s*tai|PCTT|TKCN|tìm\s*kiếm\s*cứu\s*nạn)"

DISASTER_CONTEXT = [
  r"rủi\s*ro\s*thiên\s*tai",
  r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai(?:\s*cấp\s*\d+)?",
  r"cảnh\s*báo\s*(?:thiên\s*tai|rủi\s*ro\s*thiên\s*tai)",
  r"tình\s*huống\s*khẩn\s*cấp",
  # B) Ứng phó khẩn cấp (đặc thù)
  r"sơ\s*tán(?:\s*khẩn\s*cấp)?",
  r"di\s*dời(?:\s*khẩn\s*cấp)?",
  r"cứu\s*hộ", r"cứu\s*nạn",
  r"tìm\s*kiếm\s*cứu\s*nạn",
  r"neo\s*đậu\s*tránh\s*trú",
  r"cấm\s*ra\s*khơi|cấm\s*biển",
  r"đóng\s*đường|cấm\s*đường|cấm\s*lưu\s*thông|phân\s*luồng",
  r"phong\s*tỏa\s*khu\s*vực\s*nguy\s*hiểm|cắm\s*biển\s*cảnh\s*báo",
  r"lực\s*lượng\s*xung\s*kích|trực\s*ban",
  # C) Tác động/thiệt hại (đặc thù)
  r"thiệt\s*hại|tổn\s*thất",
  r"thương\s*vong|tử\s*vong|thiệt\s*mạng",
  r"mất\s*tích|mất\s*liên\s*lạc",
  r"bị\s*thương|nhập\s*viện|cấp\s*cứu",
  r"chia\s*cắt|cô\s*lập",
  r"sập\s*cầu|đứt\s*đường|sạt\s*lở\s*đường",
  r"vỡ\s*đê|tràn\s*đê|vỡ\s*đập",
  r"đóng\s*cửa\s*trường|cho\s*nghỉ\s*học|nghỉ\s*học|tạm\s*nghỉ\s*học",
  r"điêu\s*đứng|trắng\s*tay|tan\s*hoang|xót\s*xa|không\s*còn\s*gì|mất\s*trắng",
  r"hỗ\s*trợ\s*khẩn\s*cấp|cứu\s*trợ\s*khẩn\s*cấp|nhu\s*yếu\s*phẩm",
  r"tê\s*liệt\s*giao\s*thông|tuyến\s*đường\s*huyết\s*mạch|chia\s*cắt\s*hoàn\s*toàn|sạt\s*lở\s*nghiêm\s*trọng",
  r"thiệt\s*hại\s*về\s*người|thiệt\s*hại\s*tài\s*sản",
  r"ước\s*tính\s*thiệt\s*hại",
  r"gia\s*cố\s*nhà\s*cửa|chằng\s*chống|cắt\s*tỉa\s*cây",
  r"gia\s*cố\s*lồng\s*bè|đưa\s*tàu\s*thuyền\s*vào\s*bờ",
  r"lệnh\s*cấm\s*biển",
  r"mất\s*điện\s*diện\s*rộng|ngừng\s*cấp\s*điện",
  r"ngừng\s*cấp\s*nước|gián\s*đoạn\s*cấp\s*nước",
  # D) Chỉ báo thủy văn/khí tượng mang tính “bản tin thiên tai”
  r"báo\s*động\s*(?:1|2|3|I|II|III)|vượt\s*báo\s*động",
  r"mực\s*nước|đỉnh\s*lũ|lũ\s*lên|lũ\s*rút",
  r"lượng\s*mưa|tổng\s*lượng\s*mưa|mưa\s*lớn\s*diện\s*rộng",
  r"triều\s*cường|đỉnh\s*triều",
  r"cấp\s*gió|gió\s*giật|beaufort",
  r"độ\s*mặn|ranh\s*mặn|độ\s*mặn\s*\d+\s*(?:‰|%o|g\/l)",
  # E) Từ khóa phục hồi sau thiên tai (recovery – đặc thù)
  r"khắc\s*phục\s*hậu\s*quả|khẩn\s*trương\s*khắc\s*phục",
  r"khôi\s*phục\s*(?:giao\s*thông|cấp\s*điện|cấp\s*nước|liên\s*lạc)",
  r"thông\s*tuyến|khơi\s*thông|giải\s*tỏa|dọn\s*dẹp|thu\s*dọn|nạo\s*vét",
  r"cứu\s*trợ|tiếp\s*tế|cấp\s*phát|phát\s*lương\s*thực|nhu\s*yếu\s*phẩm",
  rf"(?:bản\s*tin|thông\s*báo|thông\s*cáo|cập\s*nhật|tin)(?:[^.\n]{{0,80}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:tin\s*bão|tin\s*áp\s*thấp|bản\s*tin\s*dự\s*báo)(?:[^.\n]{{0,80}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:công\s*điện|hỏa\s*tốc)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:chỉ\s*đạo|chỉ\s*đạo\s*khẩn|yêu\s*cầu|đề\s*nghị|hướng\s*dẫn|ban\s*hành|triển\s*khai|chỉ\s*thị)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:ubnd|ủy\s*ban\s*nhân\s*dân|sở|bộ)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:mất\s*sóng|mất\s*mạng|mất\s*internet|đứt\s*cáp\s*quang|cột\s*bts)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:người\s*dân|hộ\s*dân|nhân\s*khẩu)(?:[^.\n]{{0,80}})(?:sơ\s*tán|di\s*dời|thiệt\s*hại|mất\s*tích|bị\s*thương|{HAZARD_ANCHOR})",
  r"\b(?:canh\s*bao|khuyen\s*cao|so\s*tan|di\s*doi|cuu\s*ho|cuu\s*nan|thiet\s*hai|thuong\s*vong|tu\s*vong|mat\s*tich|chia\s*cat|co\s*lap|mat\s*dien|mat\s*lien\s*lac)\b",
  # ADDED JAN 2026: Additional Evacuation & Impact Terms
  r"\b(?:điểm\s*ngập|ngập\s*sâu|vùng\s*nguy\s*hiểm)\b",
  r"\b(?:sập\s*đổ|tốc\s*mái|xả\s*lũ|tràn\s*qua\s*đê)\b",
  r"\b(?:vùng\s*lũ|rốn\s*lũ|vùng\s*ngập|đồng\s*bào)\b"
]

RECOVERY_ANCHOR = r"(?:hậu\s*quả|sau\s*(?:bão|lũ|mưa\s*lớn|ngập|sạt\s*lở|triều\s*cường|nước\s*dâng|cháy\s*rừng|động\s*đất|sóng\s*thần|rét\s*hại|mưa\s*đá|dông\s*lốc)|thiên\s*tai|bão|lũ|ngập|sạt\s*lở|hạn\s*hán|hạn\s*mặn|xâm\s*nhập\s*mặn)"

# RECOVERY Keywords for Event Stage Classification
# ARTICLE MODE / STAGE SIGNATURES
FORECAST_SIGS = [
    r"bản\s*tin(?:\s*dự\s*báo|\s*cảnh\s*báo)?", r"dự\s*báo", r"cảnh\s*báo",
    r"trong\s*(?:24|48|72|120)\s*(?:giờ|h)\s*tới", r"tâm\s*bão\s*ở\s*khoảng",
    r"vĩ\s*độ|kinh\s*độ", r"bán\s*kính\s*gió\s*mạnh", r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
    r"tốc\s*độ\s*di\s*chuyển", r"hướng\s*di\s*chuyển", r"mm\s*/\s*24h", r"có\s*khả\s*năng\s*mạnh\s*lên",
    r"mô\s*hình\s*dự\s*báo", r"đường\s*đi\s*của\s*bão", r"theo\s*dõi\s*chặt\s*chẽ"
]

INCIDENT_SIGS = [
    r"xảy\s*ra", r"đã\s*(?:đổ\s*bộ|ập\s*xuống|xảy\s*ra|gây)", r"ghi\s*nhận", r"làm\s*(?:\d+|nhiều)\s*người",
    r"khiến\s*(?:\d+|nhiều)\s*người", r"cuốn\s*trôi", r"sập\s*nhà", r"trục\s*vớt", r"cứu\s*hộ\s*khẩn\s*cấp",
    r"di\s*dời\s*dân", r"sơ\s*tán\s*khẩn\s*cấp", r"tình\s*trạng\s*ẩn cấp", r"thiệt\s*mạng", r"số\s*liệu\s*thiệt\s*hại"
]

RECOVERY_KEYWORDS = [
    r"khắc\s*phục\s*hậu\s*quả",
    r"khắc\s*phục\s*sự\s*cố",
    r"khẩn\s*trương\s*khắc\s*phục",
    r"khôi\s*phục\s*(?:giao\s*thông|cấp\s*điện|cấp\s*nước|liên\s*lạc|thông\s*tin|sản\s*xuất|hoạt\s*động)",
    r"cấp\s*điện\s*trở\s*lại|cấp\s*nước\s*trở\s*lại",
    r"thông\s*tuyến|thông\s*xe",
    r"khơi\s*thông\s*(?:cống\s*rãnh|kênh\s*mương|dòng\s*chảy)",
    r"giải\s*tỏa\s*(?:ùn\s*tắc|đất\s*đá|điểm\s*sạt\s*lở)",
    r"thu\s*dọn|dọn\s*dẹp|nạo\s*vét(?:\s*bùn|\s*kênh)?",
    r"thu\s*gom\s*(?:rác|bùn\s*đất|cây\s*đổ)",
    r"tiêu\s*độc|khử\s*trùng|tẩy\s*uế|phun\s*khử\s*khuẩn",
    r"phòng\s*chống\s*dịch\s*bệnh\s*sau\s*thiên\s*tai",
    r"(?:thống\s*kê|rà\s*soát|đánh\s*giá|xác\s*minh|kiểm\s*đếm)\s*thiệt\s*hại",
    r"tổng\s*kết\s*thiệt\s*hại",
    r"(?:giải\s*ngân|tạm\s*ứng|bố\s*trí|cấp)\s*kinh\s*phí",
    r"bổ\s*sung\s*ngân\s*sách",
    r"(?:bồi\s*thường|đền\s*bù|bồi\s*hoàn|chi\s*trả\s*bồi\s*thường)",
    r"bảo\s*hiểm\s*chi\s*trả",
    r"(?:dựng\s*lại|xây\s*dựng\s*lại|xây\s*mới)\s*nhà",
    r"bàn\s*giao\s*(?:nhà|nhà\s*tình\s*nghĩa|nhà\s*đại\s*đoàn\s*kết)",
    r"tái\s*định\s*cư(?:\s*tập\s*trung)?|bố\s*trí\s*tái\s*định\s*cư",
    r"ổn\s*định\s*(?:dân\s*cư|đời\s*sống)|an\s*cư",
    r"khôi\s*phục\s*sinh\s*kế|phục\s*hồi\s*sinh\s*kế",
    r"(?:hỗ\s*trợ|cấp\s*phát)\s*giống",
    r"trợ\s*giúp\s*xã\s*hội",
    r"cứu\s*trợ\s*khẩn\s*cấp",
    r"quỹ\s*(?:phòng\s*chống\s*thiên\s*tai|từ\s*thiện|cứu\s*trợ)",
    r"ủng\s*hộ\s*đồng\s*bào",
    r"lá\s*lành\s*đùm\s*lá\s*rách",
    r"tái\s*đàn",
    r"khôi\s*phục\s*(?:chăn\s*nuôi|nuôi\s*trồng|hoa\s*màu|diện\s*tích\s*sản\s*xuất)",
    rf"(?:hỗ\s*trợ|cứu\s*trợ|ủng\s*hộ|quyên\s*góp|tiếp\s*nhận|trao\s*tặng|cấp\s*phát|tiếp\s*tế|phát\s*(?:quà|tiền|gạo))(?:[^.\n]{{0,120}}){RECOVERY_ANCHOR}",
    rf"{RECOVERY_ANCHOR}(?:[^.\n]{{0,120}})(?:hỗ\s*trợ|cứu\s*trợ|ủng\s*hộ|quyên\s*góp|tiếp\s*nhận|trao\s*tặng|cấp\s*phát|tiếp\s*tế|phát\s*(?:quà|tiền|gạo))",
    rf"(?:trợ\s*cấp|miễn\s*giảm|giãn\s*nợ|khoanh\s*nợ|gia\s*hạn\s*nợ|cho\s*vay\s*ưu\s*đãi|hỗ\s*trợ\s*tín\s*dụng)(?:[^.\n]{{0,120}}){RECOVERY_ANCHOR}",
    rf"{RECOVERY_ANCHOR}(?:[^.\n]{{0,120}})(?:trợ\s*cấp|miễn\s*giảm|giãn\s*nợ|khoanh\s*nợ|gia\s*hạn\s*nợ|cho\s*vay\s*ưu\s*đãi|hỗ\s*trợ\s*tín\s*dụng)",
    r"lập\s*danh\s*sách\s*(?:hỗ\s*trợ|cứu\s*trợ|thiệt\s*hại|hộ\s*bị\s*ảnh\s*hưởng|người\s*bị\s*ảnh\s*hưởng)",
    r"xác\s*định\s*mức\s*hỗ\s*trợ(?:[^.\n]{0,60})?(?:thiệt\s*hại|hộ\s*bị\s*ảnh\s*hưởng|người\s*bị\s*ảnh\s*hưởng)",
    r"hồi\s*sinh(?:\s*vùng\s*lũ|\s*sau\s*bão|\s*sau\s*thiên\s*tai|\s*vùng\s*đất|\s*sinh\s*kế)",
]

# 1. ABSOLUTE VETO: Strictly Non-Disaster Contexts (Metaphor, Showbiz, Game, Sport)
# These will be blocked even if they contain "bão", "lũ", "sạt lở" keywords.
ABSOLUTE_VETO = [
    'cơn\\s*bão\\s*(?:chứng\\s*khoán|chứng\\s*trường|bán\\s*tháo|lãi\\s*suất|tỷ\\s*giá|khủng\\s*hoảng|suy\\s*thoái|giá\\s*cả|dư\\s*luận|truy\\s*ền\\s*thông|tin\\s*giả|mạng|tin\\s*đồn|showbiz|tài\\s*chính|ngoại\\s*giao|chính\\s*trị|rating|đánh\\s*giá|review|hashtag|trend|viral|quà\\s*tặng|lòng|tố)',
    'bão\\s*(?:bán\\s*tháo|margin|call\\s*margin|giải\\s*chấp|chứng\\s*khoán|coin|crypto|tỷ\\s*giá|lãi\\s*suất|phốt|drama|diss|cà\\s*khịa|scandal|tin\\s*đồn|thị\\s*phi|tuyển\\s*dụng|sa\\s*thải|layoff|nghỉ\\s*việc|giá|sale|like|sao\\s*kê|chấn\\s*thương|view|comment|order|đơn|hàng|flash\\s*sale|voucher|ddos|spam|bot|an\\s*ninh\\s*mạng|email|tin\\s*nhắn|notification|thất\\s*nghiệp)',
    'cơn\\s*lốc\\s*(?:giá|tăng\\s*giá|giảm\\s*giá|khuyến\\s*mãi|sale|flash\\s*sale|voucher|đầu\\s*tư|đường\\s*biên|màu\\s*cam|sân\\s*cỏ|chuyển\\s*nhượng)',
    'hạn\\s*hán\\s*(?:bàn\\s*thắng|ghi\\s*bàn|điểm\\s*số|thành\\s*tích|danh\\s*hiệu|ý\\s*tưởng|lời\\s*giải)',
    'khô\\s*hạn\\s*(?:bàn\\s*thắng|ý\\s*tưởng|nội\\s*dung|tương\\s*tác|vốn|tài\\s*chính)',
    'mưa\\s*(?:like|view|comment|đơn\\s*hàng|order|follow|sub|subscriber|deal|voucher|ưu\\s*đãi|quà\\s*tặng|coupon|gạch\\s*đá|lời\\s*khen|feedback|email|tin\\s*nhắn|notification|bàn\\s*thắng|huy\\s*chương)',
    'ngập\\s*(?:deal|ưu\\s*đãi|voucher|order|đơn|hashtag|trend|quà|rác|nợ|hoa|tràn\\s*(?:cảm\\s*xúc|hạnh\\s*phúc|tình\\s*yêu|niềm\\s*vui))',
    'cháy\\s*(?:vé|show|concert|liveshow|tour|hàng|kho|đơn|order|slot|suất|deadline|kpi|dự\\s*án|task|việc|túi|tiền|hết\\s*mình|phố|team|máu|đam\\s*mê|quá|rực)',
    'trào\\s*lưu\\s*(?:đi\\s*cà\\s*phê|quẩy|sống\\s*ảo|check-in|hot|mới|tik\\s*tok)|trend\\s*(?:mới|hot)',
    'bốc\\s*hơi\\s*(?:tài\\s*khoản|vốn\\s*hóa|giá\\s*trị|lợi\\s*nhuận|tài\\s*sản)',
    'sóng\\s*thần\\s*(?:sa\\s*thải|layoff|bán\\s*tháo|giảm\\s*giá|công\\s*nghệ|pháp\\s*lý|lừa\\s*đảo)',
    'làn\\s*sóng\\s*(?:đầu\\s*tư|tẩy\\s*chay|sa\\s*thải|viral|trend|covid|dịch\\s*bệnh|công\\s*nghệ|di\\s*cư\\s*số|di\\s*chuyển)(?!\\s*sóng\\s*thần)',
    'rung\\s*chấn\\s*(?:dư\\s*luận|thị\\s*trường|sân\\s*cỏ|điện\\s*ảnh|chính\\s*trường|vpop)',
    'chấn\\s*động\\s*(?:dư\\s*luận|showbiz|làng\\s*giải\\s*trí|MXH|mạng\\s*xã\\s*hội|vbiz)',
    'địa\\s*chấn\\s*(?:showbiz|làng\\s*giải\\s*trí|Vpop|V-League|tình\\s*trường|chủ\\s*quyền)',
    'cú\\s*sốc(?:\\s*thị\\s*trường|\\s*tình\\s*cảm|\\s*giá|\\s*vpop|\\s*showbiz|\\s*giải\\s*trí)',
    'chấn\\s*thương(?:\\s*chỉnh\\s*hình|\\s*thể\\s*thao|\\s*tâm\\s*lý)|giãn\\s*dây\\s*chằng|đứt\\s*dây\\s*chằng',
    'ưu\\s*đãi\\s*khủng|sale\\s*sập\\s*sàn|giá\\s*sốc|khuyến\\s*mãi\\s*khủng|mua\\s*1\\s*tặng\\s*1',
    'cơn\\s*lũ\\s*(?:tin\\s*giả|tội\\s*phạm|rác\\s*thải\\s*số|lượt|fan|tin\\s*nhắn|email|notification|lời\\s*khen|quà|rác)',
    'sạt\\s*lở\\s*(?:niềm\\s*tin|danh\\s*tiếng|hình\\s*ảnh|tài\\s*chính|đạo\\s*đức|thị\\s*trường|cổ\\s*phiếu)',
    'dông\\s*bão\\s*(?:cuộc\\s*đời|tình\\s*cảm|nội\\s*tâm|hôn\\s*nhân|gia\\s*đình)',
    'đóng\\s*băng\\s*(?:thị\\s*trường|tài\\s*khoản|quan\\s*hệ|tài\\s*sản|dự\\s*án)',
    'cơn\\s*sốt\\s*(?:đất|giá|vé)',
    'không\\s*khí\\s*lạnh\\s*(?:nhạt|lùng|giá)',
    'sức\\s*mạnh\\s*nội\\s*sinh',
    'storm\\s+of|flood\\s+of|tsunami\\s+of',
    '\\b(?:showbiz|vbiz|vpop|kpop|biz|drama|scandal|netizen|fandom|idol|livestream|streamer|youtuber|tiktoker|influencer|shopping\\s*online)\\b',
    '\\b(?:ca\\s*sĩ|diễn\\s*viên|người\\s*mẫu|hoa\\s*hậu|á\\s*hậu|nghệ\\s*sĩ|sao\\s*Việt|sao\\s*hàn|sao\\s*hoa)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|tiết\\s*mục|hợp\\s*xướng|giải\\s*trí|phim\\s*trường|rạp\\s*chiếu\\s*phim|triển\\s*lãm|khai\\s*mạc|lễ\\s*hội|tuần\\s*lễ\\s*thời\\s*trang)\\b',
    '\\b(?:album|mv|ca\\s*khúc|bài\\s*hát|phim\\s*bộ|series|tập\\s*cuối|trailer|spoiler|happening|rap\\s*việt|chị\\s*đẹp|anh\\s*trai|anh\\s*hùng\\s*xạ\\s*điêu|phim\\s*truyền\\s*hình|phim\\s*điện\\s*ảnh)\\b',
    '\\b(?:đám\\s*cưới|hôn\\s*lễ|ly\\s*hôn|ngoại\\s*tình|đánh\\s*ghen|hẹn\\s*hò|chia\\s*tay|tình\\s*trường)\\b',
    '\\b(?:làm\\s*đẹp|skincare|mỹ\\s*phẩm|trắng\\s*da|giảm\\s*cân|tăng\\s*cân|thực\\s*phẩm\\s*chức\\s*năng|thăng\\s*hạng\\s*nhan\\s*sắc)\\b',
    '\\b(?:noel|giáng\\s*sinh|check-in|phố\\s*đi\\s*bộ|ẩm\\s*thực|món\\s*ngon|nhà\\s*hàng|quán\\s*ăn|đầu\\s*bếp)(?!\\s*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ))\\b',
    '\\b(?:quán\\s*bar|pub|nhạc\\s*sống|phòng\\s*trà|vũ\\s*trường|karaoke|massage|bida)\\b',
    '\\b(?:xác\\s*pháo|pháo\\s*hoa|bắn\\s*pháo\\s*hoa|lễ\\s*hội\\s*pháo\\s*hoa|pháo\\s*tết)\\b',
    '\\b(?:bóng\\s*đá|cầu\\s*thủ|đội\\s*tuyển|world\\s*cup|v-league|sea\\s*games|aff\\s*cup|vck|u23|u22|u21|u19|u17|premier\\s*league|serie\\s*a|la\\s*liga|bundesliga|champions\\s*league|europa\\s*league|hlv|huấn\\s*luyện\\s*viên|(?<!nghiêm\\s)trọng\\s*tài|sân\\s*cỏ|tỉ\\s*số|ghi\\s*bàn|bàn\\s*thắng|vô\\s*địch|huy\\s*chương|hcv|hcb|hcd|marathon|giải\\s*chạy|đua\\s*xe|bơi\\s*lội|tennis|vòng\\s*loại|bán\\s*kết|chung\\s*kết|ăn\\s*mừng|cổ\\s*vũ|xuống\\s*đường|nhận\\s*định|soi\\s*kèo|tỷ\\s*lệ\\s*cược|kèo\\s*nhà\\s*cái|đối\\s*đầu|trực\\s*tiếp\\s*trận)\\b',
    '\\b(?:iphone|samsung|oppo|xiaomi|smartphone|macbook|ipad|galaxy|máy\\s*tính\\s*bảng|laptop|xe\\s*điện|vinfast|tesla|chip|vi\\s*xử\\s*lý|hệ\\s*điều\\s*hành|android|ios|ứng\\s*dụng|app|lộ\\s*diện\\s*thiết\\s*kế|giá\\s*bán\\s*niêm\\s*yết|ra\\s*mắt\\s*sản\\s*phẩm|deepfake|giả\\s*giọng|test\\s*de\\s*torture|résistance|trifold)\\b',
    '\\b(?:bitcoin|crypto|blockchain|nft|token|ví\\s*điện\\s*tử|sàn\\s*coin|đào\\s*coin|tiền\\s*ảo|máy\\s*đào)\\b',
    '\\b(?:game|gaming|pubg|liên\\s*quân|esports|nạp\\s*game|skin\\s*game|playstation|xbox|nintendo)\\b',
    'sóng\\s*(?:wifi|wi-?fi|4g|5g|lte|di\\s*động|viễn\\s*thông|radio|trending|trend|viral)(?!\\s*thần)',
    'mất\\s*sóng\\s*(?:wifi|wi-?fi|4g|5g|lte)',
    'bắt\\s*sóng',
    'phủ\\s*sóng',
    'vùng\\s*phủ\\s*sóng',
    'trạm\\s*phát\\s*sóng',
    'tần\\s*số',
    'băng\\s*tần',
    '\\b(?:ukraine|dải\\s*gaza|israel|hamas|venezuela|libya|đài\\s*loan|nga\\s*-\\s*ukraine|kiev|moscow|tên\\s*lửa|đạn\\s*pháo|khai\\s*hỏa|chiến\\s*sự|vùng\\s*kursk|hành\\s*lang\\s*ngũ\\s*cốc|châu\\s*âu|thượng\\s*đỉnh|g7|\\bg20\\b)\\b',
    '\\b(?:uav|drone)(?!\\s*(?:cứu\\s*trợ|tìm\\s*kiếm|lũ|bão|ngập|sạt|tiếp\\s*tế))\\b',
    '(?:xung\\s*đột\\s*vũ\\s*trang|quản\\s*chế\\s*tàu\\s*dầu|phong\\s*tỏa\\s*tàu|tấn\\s*công\\s*bằng\\s*tên\\s*lửa|hội\\s*đồng\\s*bảo\\s*an|phương\\s*tây|chiến\\s*tranh|binh\\s*sĩ|quân\\s*đội|lữ\\s*đoàn)',
    '\\b(?:án\\s*mạng|hành\\s*hạ|ngược\\s*đãi|ma\\s*túy|thuốc\\s*lắc|đánh\\s*bạc|sới\\s*bạc|casino|cá\\s*độ|đá\\s*gà|mại\\s*dâm|buôn\\s*lậu|hàng\\s*lậu|hàng\\s*cấm|tàng\\s*trữ|hàng\\s*giả|lừa\\s*đảo|chiếm\\s*đoạt|truy\\s*nã|nghi\\s*phạm|hung\\s*thủ|sát\\s*hại|bạo\\s*hành|bắt\\s*cóc|trục\\s*lợi|giả\\s*chết|karaoke)\\b',
    '\\b(?:xử\\s*phạt|khởi\\s*tố|truy\\s*tố|xét\\s*xử|phiên\\s*tòa|bản\\s*án|tử\\s*hình|chung\\s*thân|án\\s*tù|bị\\s*can|bị\\s*cáo|tòa\\s*án\\s*nhân\\s*dân|điều\\s*tra\\s*viên|tranh\\s*chấp|khiếu\\s*nại|tố\\s*cáo)\\b',
    '\\b(?:vi\\s*phạm\\s*hành\\s*chính|xử\\s*phạt\\s*vi\\s*phạm|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|nồng\\s*độ\\s*cồn|phạt\\s*nguội|tạm\\s*giữ\\s*phương\\s*tiện|xe\\s*quá\\s*khổ|quá\\s*tải)\\b',
    '\\b(?:nghĩa\\s*vụ\\s*quân\\s*sự|nhập\\s*ngũ|tuyển\\s*quân|giao\\s*nhận\\s*quân|lên\\s*đường\\s*nhập\\s*ngũ|khám\\s*tuyển|hội\\s*đồng\\s*nhân\\s*dân|tiếp\\s*xúc\\s*cử\\s*tri)\\b',
    '\\b(?:huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|tai\\s*biến|ung\\s*thư|phẫu\\s*thuật|cấy\\s*ghép)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:giấy\\s*phép\\s*lái\\s*xe|phạt\\s*nguội|đăng\\s*kiểm|cấp\\s*căn\\s*cước|hộ\\s*chiếu|tước\\s*bằng|định\\s*danh\\s*điện\\s*tử|trốn\\s*truy\\s*nã|đào\\s*tẩu)\\b',
    '\\b(?:xổ\\s*số|vietlott|trúng\\s*số|giải\\s*đặc\\s*biệt|vé\\s*số|kết\\s*quả\\s*mở\\s*thưởng)\\b',
    '\\b(?:ung\\s*thư|tiểu\\s*đường|huyết\\s*áp|đột\\s*quỵ|ngộ\\s*độc|lá\\s*ngón|vắc\\s*xin|chiến\\s*dịch\\s*tiêm\\s*chủng|dinh\\s*dưỡng|thực\\s*phẩm|món\\s*ăn|đặc\\s*sản|bệnh\\s*dại|thủy\\s*đậu|dịch\\s*tả|cúm|sốt\\s*xuất\\s*huyết|chikungunya|đậu\\s*mùa\\s*(?:khỉ)?|sởi|bạch\\s*hầu|ho\\s*gà|uốn\\s*ván|não\\s*mô\\s*cầu|viêm\\s*não|bệnh\\s* truyền\\s*nhiễm|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|sốt\\s*rét|viêm\\s*gan|viêm\\s*phổi|nhiễm\\s*trùng|vi\\s*khuẩn|liên\\s*cầu\\s*khuẩn)(?!.*(?:tiếp\\s*tế|cứu\\s*trợ|cô\\s*lập|vùng\\s*lũ|ngập|lụt|hỗ\\s*trợ|khắc\\s*phục|mưa\\s*lũ))\\b',
    '\\b(?:tự\\s*tử|quyên\\s*sinh|nhảy\\s*cầu|treo\\s*cổ|tự\\s*thiêu|trong\\s*nhà|phòng\\s*trọ|nhà\\s*nghỉ|khách\\s*sạn|chung\\s*cư|bạo\\s*lực\\s*gia\\s*đình)\\b',
    '\\b(?:chê|khen|tranh\\s*cãi|bức\\s*xúc|tố\\s*cáo|lùm\\s*xùm|drama|sao\\s*kê|phốt)(?:.{0,50})(?:tiền|ủng\\s*hộ|từ\\s*thiện|cứu\\s*trợ|chuyển\\s*khoản)\\b',
    '\\b(?:ngồi|đứng|nằm|chụp\\s*ảnh|check-in)\\s*(?:trên|tại|giữa)\\s*đường\\s*ray',
    '\\b(?:cafe|cà\\s*phê)\\s*đường\\s*tàu\\b',
    '\\bchiến\\s*dịch\\s*quang\\s*trung\\b(?!.*(?:nhà|lũ|bão|hỗ\\s*trợ|khắc\\s*phục|tái\\s*thiết|ủng\\s*hộ))',
    '\\b(?:buông\\s*hai\\s*tay|bốc\\s*đầu|thông\\s*chốt|nẹt\\s*pô|lạng\\s*lách|đánh\\s*võng)\\b',
    '\\b(?:đua\\s*ngựa|đua\\s*chó|đua\\s*thuyền\\s*rồng|lễ\\s*hội\\s*đua\\s*thuyền)\\b',
    '\\b(?:đường\\s*sắt\\s*tốc\\s*độ\\s*cao|cao\\s*tốc\\s*bắc\\s*nam|dự\\s*án\\s*trọng\\s*điểm)(?!.*(?:sạt\\s*lở|ngập|hư\\s*hỏng|thiên\\s*tai))\\b',
    '\\b(?:lăng\\s*mộ|nhà\\s*rường|hoàng\\s*thái\\s*hậu|cung\\s*đình|hoàng\\s*cung)\\b',
    '\\b(?:tranh\\s*chấp|mâu\\s*thuẫn|xô\\s*xát|đâm\\s*chém|sát\\s*hại|giết\\s*người|án\\s*mạng|trọng\\s*án)(?!.*(?:bão|lũ))\\b',
    '\\b(?:cháy\\s*nhà\\s*trọ|cháy\\s*quán|cháy\\s*xưởng|cháy\\s*xe|hỏa\\s*hoạn\\s*tại\\s*nhà\\s*dân|cháy\\s*chung\\s*cư|cháy\\s*căn\\s*hộ|cháy\\s*biệt\\s*thự|cháy\\s*kho|cháy\\s*xe\\s*bồn)(?!.*(?:bão|lũ|thiên\\s*tai|sét\\s*đánh|rừng|cứu\\s*nạn|người\\s*chết|dập\\s*lửa|tử\\s*vong|thiệt\\s*mạng|thương\\s*vong))\\b',
    '\\b(?:nhảy\\s*cầu|treo\\s*cổ|tự\\s*thiêu|rơi\\s*lầu|rơi\\s*chung\\s*cư|ngã\\s*từ\\s*tầng)(?!.*(?:sập|đổ|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:đại\\s*hội\\s*đảng|ban\\s*bí\\s*thư|bộ\\s*chính\\s*trị|ủy\\s*viên\\s*trung\\s*ương|hội\\s*nghị\\s*ban\\s*chấp\\s*hành|điều\\s*động\\s*cán\\s*bộ|bổ\\s*nhiệm|luân\\s*chuyển|phân\\s*công|quy\\s*tập\\s*hài\\s*cốt|nghĩa\\s*trang\\s*liệt\\s*sĩ|trao\\s*huân\\s*chương|cờ\\s*thi\\s*đua|vinh\\s*danh|kỷ\\s*niệm\\s*ngày\\s*thành\\s*lập|quỹ\\s*hưu\\s*trí|bảo\\s*hiểm\\s*hưu\\s*trí)(?!.*(?:ứng\\s*phó|phòng\\s*chống|cứu\\s*hộ|cứu\\s*nạn|thiên\\s*tai|bão|lũ|ngập|sạt\\s*lở|khẩn\\s*cấp|chỉ\\s*đạo|hỗ\\s*trợ|khắc\\s*phục|cứu\\s*trợ|tiếp\\s*nhận|trao\\s*tặng|quyên\\s*góp|sơ\\s*tán|di\\s*dời|công\\s*điện|áp\\s*thấp|mưa\\s*lũ|kết\\s*luận|hậu\\s*quả))\\b',
    '\\b(?:nông\\s*thôn\\s*mới|quy\\s*hoạch\\s*đô\\s*thị|vành\\s*đai\\s*\\d+|cao\\s*tốc|khởi\\s*công|thông\\s*xe|nghiệm\\s*thu|đấu\\s*giá\\s*đất|sổ\\s*đỏ|quyền\\s*sử\\s*dụng\\s*đất|giao\\s*đất|chuyển\\s*nhượng|xuất\\s*quân|lễ\\s*ra\\s*quân|hội\\s*thi|tuyên\\s*truyền|tập\\s*huấn|nhà\\s*đại\\s*đoàn\\s*kết|nhà\\s*tình\\s*nghĩa|nhà\\s*tình\\s*thương|nhà\\s*nhân\\s*ái|khai\\s*trương|ra\\s*mắt)(?!.*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ|ứng\\s*phó|phòng\\s*chống|cứu\\s*trợ|hỗ\\s*trợ|sơ\\s*tán|khắc\\s*phục|sự\\s*cố|hư\\s*hỏng|bão|lũ))\\b',
    '\\b(?:sinh\\s*hoạt\\s*chi\\s*bộ|tự\\s*soi\\s*tự\\s*sửa|phê\\s*bình|kiểm\\s*điểm|đảng\\s*viên|kỷ\\s*luật\\s*đảng|cán\\s*bộ\\s*đảng\\s*viên|tinh\\s*gọn\\s*bộ\\s*máy|sắp\\s*xếp\\s*tổ\\s*chức|công\\s*đoàn|đề\\s*án|kiện\\s*toàn|thanh\\s*tra|kết\\s*luận\\s*thanh\\s*tra|sai\\s*phạm|xử\\s*lý\\s*vi\\s*phạm|sắp\\s*xếp\\s*cơ\\s*quan|quy\\s*hoạch\\s*cán\\s*bộ|quản\\s*trị\\s*quốc\\s*gia|kỷ\\s*nguyên\\s*mới|đội\\s*ngũ\\s*cán\\s*bộ|người\\s*đứng\\s*đầu)\\b',
    '\\b(?:thăm\\s*và\\s*làm\\s*việc|làm\\s*việc\\s*tại|kiểm\\s*tra\\s*công\\s*tác|chỉ\\s*đạo\\s*hội\\s*nghị|phát\\s*biểu\\s*chỉ\\s*đạo|tham\\s*dự\\s*hội\\s*nghị|tiếp\\s*xúc\\s*cử\\s*tri)(?!\\s*(?:phòng[\\s,]+chống|ứng\\s*phó|cứu\\s*trợ|khắc\\s*phục|bão|lũ|thiên\\s*tai|thăm|thăm\\s*hỏi|động\\s*viên|chia\\s*sẻ))\\b',
    '(?:dự\\s*án\\s*vành\\s*đai|đường\\s*vành\\s*đai|nút\\s*giao|hầm\\s*chui|cầu\\s*vượt|thông\\s*xe|khánh\\s*thành|khởi\\s*công|xây\\s*dựng\\s*tuyến\\s*đường|nâng\\s*cao\\s*độ\\s*nền)(?!.*(?:kè|đê|hồ|đập|chống|sạt\\s*lở|khắc\\s*phục|ngập))',
    '\\b(?:cháy\\s*(?:dữ\\s*dội\\s*|lớn\\s*|ngùn\\s*ngụt\\s*)?nhà|cháy\\s*cửa\\s*hàng|cháy\\s*quán|cháy\\s*chợ|cháy\\s*gara|cháy\\s*ô\\s*tô|thiêu\\s*rụi\\s*xe|chập\\s*điện|hỏa\\s*hoạn\\s*tại|nổ\\s*bình\\s*gas)(?!.*(?:bão|lũ|thiên\\s*tai|sét\\s*đánh|rừng|cứu\\s*nạn|người\\s*chết|dập\\s*lửa|tử\\s*vong|thiệt\\s*mạng|thương\\s*vong|bé\\s*sơ\\s*sinh))\\b',
    '\\b(?:đuối\\s*nước|chết\\s*đuối|tắm\\s*suối|tắm\\s*hồ|hồ\\s*bơi|bể\\s*bơi|công\\s*viên\\s*nước|tắm\\s*biển)(?!.*(?:bão|lũ|mưa\\s*lũ|ngập|lũ\\s*quét|sóng\\s*thần|cứu\\s*nạn|mất\\s*tích|vùng\\s*lũ))\\b',
    'vận\\s*hành\\s*chính\\s*quyền\\s*địa\\s*phương\\s*2\\s*cấp|cải\\s*cách\\s*hành\\s*chính|chuyển\\s*đổi\\s*số',
    '\\b(?:tháng\\s*hành\\s*động\\s*vì\\s*bình\\s*đẳng\\s*giới|tháng\\s*hành\\s*động\\s*quốc\\s*gia|công\\s*bố\\s*quyết\\s*định|trao\\s*quyết\\s*định)\\b',
    '\\b(?:nhà\\s*ở\\s*xã\\s*hội|mua\\s*nhà|bất\\s*động\\s*sản|thị\\s*trường\\s*nhà\\s*đất|sổ\\s*hồng|phát\\s*hành\\s*tiền|tiền\\s*kỹ\\s*thuật\\s*số|ngân\\s*hàng\\s*trung\\s*ương|izumi\\s*city|căn\\s*hộ|mở\\s*bán|khu\\s*đô\\s*thị|quy\\s*hoạch\\s*không\\s*gian|đô\\s*thị\\s*văn\\s*minh)(?!.*(?:ngập|sạt\\s*lở|hư\\s*hỏng|bão|lũ))\\b',
    '\\b(?:dư\\s*nợ\\s*tín\\s*dụng|tăng\\s*trưởng\\s*kinh\\s*tế|phấn\\s*đấu\\s*đạt|vượt\\s*dự\\s*báo|kinh\\s*tế\\s*vĩ\\s*mô|bội\\s*chi\\s*ngân\\s*sách|gdp|chỉ\\s*số\\s*giá|lạm\\s*phát)(?!.*(?:thiệt\\s*hại|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:cử\\s*tri\\s*kiến\\s*nghị|thẻ\\s*căn\\s*cước|định\\s*danh\\s*điện\\s*tử|vneid|sổ\\s*hộ\\s*khẩu|trợ\\s*cấp\\s*xã\\s*hội|bảo\\s*hiểm\\s*xã\\s*hội|lương\\s*hưu|tiếp\\s*xúc\\s*cử\\s*tri|hđnd|hội\\s*đồng\\s*nhân\\s*dân|lấy\\s*phiếu\\s*tín\\s*nhiệm|chủ\\s*tịch\\s*ubnd|lãnh\\s*đạo\\s*tỉnh)(?!.*(?:bão|lũ|cứu\\s*trợ|thiên\\s*tai|khắc\\s*phục|kiểm\\s*tra|chỉ\\s*đạo|công\\s*điện|khẩn\\s*cấp|hỗ\\s*trợ|thăm|thăm\\s*hỏi|động\\s*viên|sơ\\s*tán|di\\s*dời|ứng\\s*phó))\\b',
    '\\b(?:sổ\\s*đỏ|giấy\\s*chứng\\s*nhận|bản\\s*đồ\\s*địa\\s*chính|tranh\\s*chấp\\s*đất|đền\\s*bù\\s*giải\\s*phóng|cấp\\s*sổ|đo\\s*đạc)(?!.*(?:sạt\\s*lở|tái\\s*định\\s*cư|vùng\\s*lũ|trôi))\\b',
    '\\b(?:giao\\s*lưu\\s*nghệ\\s*thuật|tôn\\s*vinh|chương\\s*trình\\s*ca\\s*nhạc|biểu\\s*diễn|lễ\\s*phát\\s*động|khai\\s*mạc|bế\\s*mạc|tri\\s*ân\\s*khách\\s*hàng|tháng\\s*tri\\s*ân|lan\\s*tỏa\\s*yêu\\s*thương)(?!.*(?:hỗ\\s*trợ|cứu\\s*trợ|quyên\\s*góp|từ\\s*thiện|vùng\\s*lũ|bão|thiên\\s*tai))\\b',
    '\\b(?:tự\\s*tử|nhảy\\s*cầu|bị\\s*trói|bỏ\\s*bao|nghi\\s*phạm|hung\\s*thủ|bạn\\s*trai|ghen\\s*tuông|mâu\\s*thuẫn|xả\\s*súng|nổ\\s*súng|bắn\\s*chết|đâm\\s*chết|chém|truy\\s*sát|thảm\\s*sát|án\\s*mạng|giết\\s*người|cố\\s*ý\\s*gây\\s*thương\\s*tích|bắt\\s*giữ|quả\\s*tang|đánh\\s*bạc|sới\\s*bạc|trộm\\s*cắp|cướp\\s*giật|truy\\s*nã|tội\\s*phạm|buôn\\s*lậu|ma\\s*túy|pháo\\s*nổ|xô\\s*xát|đầu\\s*thú|giả\\s*chết|trục\\s*lợi|tạm\\s*giữ\\s*hình\\s*sự|hỗn\\s*chiến|đánh\\s*nhau|hành\\s*hung|trộm|cướp|đốt\\s*nhà|phá\\s*hoại\\s*tài\\s*sản|tấn\\s*công|ngáo\\s*đá)\\b',
    '\\b(?:tai\\s*nạn\\s*giao\\s*thông|xe\\s*khách|xe\\s*tải|xe\\s*container|tông\\s*xe|va\\s*chạm\\s*xe|lật\\s*xe)(?!.*(?:sạt\\s*lở|lũ|ngập|bão|thiên\\s*tai|mưa\\s*lớn|trôi|mất\\s*tích|cứu\\s*hộ|cứu\\s*nạn))\\b',
    # Stricter general accident veto: "Vụ tai nạn" without disaster context
    r"\b(?:vụ|bị)\s*tai\s*nạn(?:\s*nghiêm\s*trọng)?\b(?!.*(?:do|vì|bởi)\s*(?:bão|lũ|thiên\s*tai|sạt|ngập|mưa))",
    '\\b(?:chém|đâm|đánh\\s*hội\\s*đồng|chặn\\s*đường|hỗn\\s*chiến|mã\\s*tấu|hung\\s*khí)(?!.*(?:bão|lũ))\\b',
    '\\b(?:dùng\\s*dao|cầm\\s*dao|đâm\\s*loạn\\s*xạ|chém\\s*tử\\s*vong|án\\s*mạng|trọng\\s*án|khám\\s*nghiệm\\s*tử\\s*thi)\\b',
    '\\b(?:người\\s*chết|thi\\s*thể|tử\\s*vong)\\s*(?:bất\\s*thường|trong\\s*nhà|nhà\\s*nghỉ|quán|cháy)\\b',
    '\\b(?:hố\\s*ga|giếng\\s*hoang|hố\\s*công\\s*trình)(?!.*(?:ngập|lũ|bão|sạt|mưa|triều\\s*cường))\\b',
    '\\b(?:nam\\s*sinh|nữ\\s*sinh|sinh\\s*viên|cụ\\s*bà|cụ\\s*ông).*(?:tử\\s*vong|thi\\s*thể|mất\\s*tích)(?!\\s*(?:do|vì|bởi)\\s*(?:mưa|lũ|bão|sạt|thiên\\s*tai))',
    '\\b(?:chó\\s*cắn|pitbull|thú\\s*cưng|động\\s*vật\\s*tấn\\s*công|dịch\\s*tả\\s*lợn|cúm\\s*gia\\s*cầm)\\b',
    '\\b(?:mua\\s*bán\\s*người|buôn\\s*người|di\\s*cư\\s*trái\\s*phép|nạn\\s*nhân\\s*mua\\s*bán|tội\\s*phạm\\s*mua\\s*bán|giải\\s*cứu\\s*nạn\\s*nhân\\s*mua\\s*bán|đường\\s*dây\\s*mua\\s*bán|môi\\s*giới\\s*hôn\\s*nhân|lấy\\s*chồng\\s*hàn|lấy\\s*chồng\\s*đài)\\b',
    '\\b(?:lao\\s*động\\s*chui|vượt\\s*biên|nhập\\s*cảnh\\s*trái\\s*phép|tổ\\s*chức\\s*đưa\\s*người|người\\s*rơm|container\\s*đông\\s*lạnh)(?!.*(?:cứu\\s*trợ|bão|lũ|sạt\\s*lở))\\b',
    '\\b(?:việc\\s*nhẹ\\s*lương\\s*cao|lừa\\s*bán|campuchia|casino|biên\\s*giới\\s*tây\\s*nam|xuất\\s*cảnh\\s*trái\\s*phép|người\\s*di\\s*cư|di\\s*cư\\s*bất\\s*hợp\\s*pháp)(?!.*(?:bão|lũ))\\b',
    '\\b(?:sắp\\s*xếp\\s*đơn\\s*vị\\s*hành\\s*chính|tổ\\s*chức\\s*lại|bộ\\s*máy|tập\\s*huấn|bồi\\s*dưỡng|nghiệp\\s*vụ|giải\\s*báo\\s*chí|thể\\s*lệ|cuộc\\s*thi|bầu\\s*cử|đại\\s*hội\\s*đảng|tạm\\s*dừng\\s*điều\\s*động|bổ\\s*nhiệm|miễn\\s*nhiệm|luân\\s*chuyển|kỷ\\s*luật|khai\\s*trừ)(?!\\s*(?:ứng\\s*phó|phòng\\s*chống|cứu\\s*hộ|cứu\\s*nạn|thiên\\s*tai|tìm\\s*kiếm|chó\\s*nghiệp\\s*vụ))\\b',
    '\\b(?:tháng\\s*hành\\s*động\\s*vì\\s*bình\\s*đẳng\\s*giới|tháng\\s*hành\\s*động\\s*quốc\\s*gia|công\\s*bố\\s*quyết\\s*định|trao\\s*quyết\\s*định)\\b',
    '\\b(?:nhà\\s*ở\\s*xã\\s*hội|mua\\s*nhà|bất\\s*động\\s*sản|thị\\s*trường\\s*nhà\\s*đất|sổ\\s*hồng|phát\\s*hành\\s*tiền|tiền\\s*kỹ\\s*thuật\\s*số|ngân\\s*hàng\\s*trung\\s*ương)\\b',
    '\\b(?:giao\\s*lưu\\s*nghệ\\s*thuật|tôn\\s*vinh|chương\\s*trình\\s*ca\\s*nhạc|biểu\\s*diễn|lễ\\s*phát\\s*động|khai\\s*mạc|bế\\s*mạc)(?!.*(?:hỗ\\s*trợ|cứu\\s*trợ|quyên\\s*góp|từ\\s*thiện))\\b',
    '\\b(?:tạm\\s*dừng\\s*ứng\\s*dụng|hệ\\s*thống\\s*thuế|nâng\\s*cấp\\s*hệ\\s*thống|bảo\\s*trì\\s*hệ\\s*thống|cập\\s*nhật\\s*thông\\s*tin|ngành\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử|cổng\\s*dịch\\s*vụ\\s*công)\\b',
    '\\b(?:ban\\s*chỉ\\s*đạo\\s*389|chống\\s*buôn\\s*lậu|hàng\\s*giả|gian\\s*lận\\s*thương\\s*mại|siết\\s*quản\\s*lý|thu\\s*ngân\\s*sách|giải\\s*ngân|đầu\\s*tư\\s*công)\\b',
    '\\b(?:tăng\\s*huyết\\s*áp|thuốc\\s*lá|tân\\s*dược|phục\\s*hồi\\s*chức\\s*năng|nối\\s*chi|phẫu\\s*thuật|cấp\\s*cứu\\s*tích\\s*cực|nhìn\\s*mờ|bệnh\\s*lý|lây\\s*lan|đại\\s*dịch|covid|khẩu\\s*trang|tiêm\\s*chủng|vắc\\s*xin)\\b',
    '\\b(?:té\\s*xe|tự\\s*gây\\s*tai\\s*nạn|tử\\s*vong\\s*tại\\s*chỗ|tử\\s*vong\\s*trong\\s*cửa\\s*hàng|tử\\s*vong\\s*tại\\s*quán|lọt\\s*hố|rơi\\s*xuống\\s*hố)(?!.*(?:sụt\\s*lún|hố\\s*tử\\s*thần|sạt\\s*lở|lũ|bão))\\b',
    '\\b(?:noel|giáng\\s*sinh|tết\\s*dương\\s*lịch|năm\\s*mới|chúc\\s*mừng|quà\\s*tặng|khuyến\\s*mãi|giảm\\s*giá|ưu\\s*đãi|khai\\s*trương)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|rink|ngập))\\b',
    '\\b(?:âm\\s*dương\\s*lịch|lịch\\s*vạn\\s*niên|xem\\s*ngày\\s*tốt|tử\\s*vi|hoàng\\s*đạo|con\\s*giáp|vận\\s*may|tài\\s*lộc)\\b',
    '\\b(?:thịt\\s*(?:bò|heo|lợn|gà|vịt)|thực\\s*phẩm\\s*(?:bẩn|hư\\s*hỏng)|ngộ\\s*độc\\s*thực\\s*phẩm|an\\s*toàn\\s*thực\\s*phẩm|hàng\\s*giả|hàng\\s*nhái)(?!.*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:xe\\s*bồn|xe\\s*tải|đổ\\s*bê\\s*tông|chắn\\s*đường|phế\\s*liệu|mất\\s*an\\s*toàn\\s*giao\\s*thông|vi\\s*phạm\\s*nồng\\s*độ\\s*cồn|tước\\s*bằng\\s*lái|phạt\\s*nguội|xe\\s*đưa\\s*đón|xe\\s*học\\s*sinh)\\b',
    '\\b(?:mất\\s*mùa|được\\s*giá|mất\\s*giá|rớt\\s*giá|xuống\\s*giá|giá\\s*bán|thương\\s*lái|thu\\s*mua|nông\\s*dân\\s*khóc\\s*ròng|tiêu\\s*điều)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:donald\\s*trump|biden|putin|zelensky|kim\\s*jong\\s*un|tập\\s*cận\\s*bình|netanyahu|quân\\s*đội\\s*nga|ukraine|israel|hamas|hezbollah|houthi|gaza|liban|iran|iraq|syria|yemen|triều\\s*tiên|hàn\\s*quốc|trung\\s*quốc|đài\\s*loan|biển\\s*đỏ|eo\\s*biển\\s*hormuz|boston|chicago|hoa\\s*kỳ|ấn\\s*độ|new\\s*delhi|mumbai|pakistan|bangladesh|nepal|sri\\s*lanka|sumatra|singapore|thái\\s*lan|bangkok|lào(?!\\s*cai)|campuchia|myanmar|malaysia|trạm\\s*vũ\\s*trụ|thiên\\s*châu|tàu\\s*vũ\\s*trụ|seoul|itaewon|slovakia|oman|robert\\s*fico|uranium|maroc|peru|nam\\s*phi|australia|sydney|đức|pháp|ý|italia|bồ\\s*đào\\s*nha|argentina|brazil|châu\\s*âu|eu|liên\\s*minh\\s*châu\\s*âu|đông\\s*nam\\s*á|asean|thế\\s*giới|toàn\\s*cầu|quốc\\s*tế|nước\\s*ngoài|palestine)(?!.*(?:bão|lũ|thiên\\s*tai|người\\s*việt|công\\s*dân\\s*việt\\s*nam|ảnh\\s*hưởng\\s*đến\\s*việt\\s*nam|biển\\s*đông|sạt\\s*lở|lở\\s*đất|động\\s*đất|rung\\s*chuyển|sóng\\s*thần|cháy\\s*lớn|sập|vỡ\\s*đập|thảm\\s*họa|cứu\\s*trợ|hỗ\\s*trợ|cứu\\s*hộ|cứu\\s*nạn|sơ\\s*tán|nắng\\s*nóng|hạn\\s*hán|lạnh\\s*giá|băng\\s*tuyết|thiệt\\s*hại|thương\\s*vong|tử\\s*vong|mất\\s*tích))\\b',
    '^(?:tin|thời\\s*sự)\\s*(?:thế\\s*giới|quốc\\s*tế)\\b(?!.*(?:động\\s*đất|sóng\\s*thần|bão|lũ|thiên\\s*tai|thảm\\s*họa|vỡ\\s*đập|cháy|sập|tai\\s*nạn|cứu\\s*hộ|cứu\\s*nạn|cứu\\s*trợ))',
    '\\b(?:liên\\s*hợp\\s*quốc|liên\\s*minh|hội\\s*đồng\\s*bảo\\s*an|nato|g7|g20|cop\\d+)(?!.*(?:hỗ\\s*trợ\\s*việt\\s*nam|bão|lũ|thiên\\s*tai\\s*tại\\s*việt\\s*nam|khẩn\\s*cấp))\\b',
    '\\b(?:man\\s*city|chelsea|benfica|man\\s*utd|mu\\s*vs|liverpool|arsenal|barca|real\\s*madrid|tiền\\s*đạo|hậu\\s*vệ|thủ\\s*môn|hlv|huấn\\s*luyện\\s*viên|đội\\s*tuyển|u22|u23|u19|u17|đt\\s*việt\\s*nam|v-league|premier\\s*league|la\\s*liga|serie\\s*a|bundesliga|champions\\s*league|europa\\s*league|sea\\s*games|aff\\s*cup|asian\\s*cup|world\\s*cup|euro\\s*20\\d{2}|vòng\\s*loại|bảng\\s*xếp\\s*hạng|lịch\\s*thi\\s*đấu|trực\\s*tiếp\\s*bóng\\s*đá|nhận\\s*định\\s*bóng\\s*đá|soi\\s*kèo|marathon|giải\\s*chạy|điền\\s*kinh|đua\\s*xe|f1|bóng\\s*đá|thể\\s*thao|hội\\s*thi\\s*thể\\s*thao|giải\\s*đấu|tranh\\s*tài|vận\\s*động\\s*viên|huy\\s*chương|quần\\s*vợt|tennis|masters|grand\\s*slam|atp|wta|nhận\\s*định\\s*vs|vs\\s*|cagliari|pisa|girona|atletico|fulham|nottingham|estoril|alverca|mainz|st\\.\\s*pauli|lecce|como|aston\\s*villa)(?!.*(?:quyên\\s*góp|ủng\\s*hộ|từ\\s*thiện))\\b',
    '\\b(?:southampton|wolves|everton|nottingham|forest|leicester|fulham|brentford|bournemouth|crystal\\s*palace|brighton|aston\\s*villa|newcastle|west\\s*ham|tottenham|wales|ghana|senegal|ecuador|qatar|iran|saudi\\s*arabia|morocco|tunisia|c\\s*r\\s*7|ronaldo|messi|neymar|mbappe)\\b',
    '\\b(?:quốc\\s*hội\\s*mỹ|hạ\\s*viện\\s*mỹ|thượng\\s*viện\\s*mỹ|tổng\\s*thống\\s*mỹ|bầu\\s*cử\\s*mỹ|nhà\\s*trắng|lầu\\s*năm\\s*góc)(?!\\s*(?:viện\\s*trợ|hỗ\\s*trợ)\\s*(?:bão|lũ|việt\\s*nam))\\b',
    '\\b(?:vinfast|bảo\\s*dưỡng|sửa\\s*chữa\\s*xe|khách\\s*hàng|dịch\\s*vụ|hậu\\s*mãi|bảo\\s*hành|tri\\s*ân|khuyến\\s*mại|giảm\\s*giá|voucher|siêu\\s*thị|mua\\s*sắm|cửa\\s*hàng|showroom|đại\\s*lý|phân\\s*phối|bán\\s*lẻ|thương\\s*mại\\s*điện\\s*tử|sàn\\s*giao\\s*dịch|chốt\\s*đơn|livestream\\s*bán\\s*hàng)\\b',
    '\\b(?:hàng\\s*tết|bình\\s*ổn\\s*giá|dự\\s*trữ\\s*hàng|quà\\s*tết|bánh\\s*kẹo|mứt\\s*tết|hoa\\s*tết|chợ\\s*hoa|lễ\\s*hội\\s*xuân|đường\\s*hoa)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|sạt\\s*lở|ách\\s*tắc))\\b',
    '\\b(?:thu\\s*hoạch|được\\s*mùa|trúng\\s*mùa|năng\\s*suất|sản\\s*lượng|xuất\\s*khẩu|nông\\s*sản|vụ\\s*mùa|trồng\\s*trọt|chăn\\s*nuôi|ốc\\s*hương|tôm\\s*hùm|lồng\\s*bè|container|ách\\s*tắc\\s*tại\\s*cảng|thông\\s*quan)(?!.*(?:thiệt\\s*hại|mất\\s*trắng|ngập|bão|lũ|sạt\\s*lở|hư\\s*hỏng|cuốn\\s*trôi|thiên\\s*tai))\\b',
    '\\b(?:sân\\s*bay|cảng\\s*hàng\\s*không).*(?:tạm\\s*đóng\\s*cửa|nâng\\s*cấp|sửa\\s*chữa|bảo\\s*trì)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thời\\s*tiết|thiên\\s*tai))',
    '\\b(?:giấy\\s*phép\\s*xây\\s*dựng|phân\\s*cấp|ủy\\s*quyền|thủ\\s*tục\\s*hành\\s*chính|cải\\s*cách)(?!.*(?:khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:lan\\s*can|vỉa\\s*hè|bờ\\s*kè|cây\\s*xanh|công\\s*viên|ghế\\s*đá).*(?:hư\\s*hỏng|gãy|đổ)(?!.*(?:sạt\\s*lở|lũ|bão|cuốn\\s*trôi|thiên\\s*tai))',
    '\\b(?:tuyển\\s*dụng|tuyển\\s*lao\\s*động|việc\\s*làm|nhân\\s*sự|chiêu\\s*mộ|thuê\\s*đất|miễn\\s*tiền\\s*thuê|khởi\\s*nghiệp|làm\\s*kinh\\s*tế|phụ\\s*nữ\\s*làm\\s*kinh\\s*tế|thoát\\s*nghèo|vay\\s*vốn|ngân\\s*hàng\\s*chính\\s*sách)\\b',
    '\\b(?:game|casino|nổ\\s*hũ|bắn\\s*cá|đá\\s*gà|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề|xổ\\s*số|vietlott|jackpot|bet|cược|kèo|nhà\\s*cái|đại\\s*lý|đăng\\s*ký\\s*tặng|khuyến\\s*mãi|nạp\\s*đầu|hoàn\\s*trả|code|giftcode|apk|ios|android|app\\s*store|ch\\s*play|version|v\\d+\\.\\d+|tải\\s*app|tải\\s*game|link\\s*tải|trang\\s*chủ|đăng\\s*nhập)\\b',
    '\\b(?:kubet|thabet|sunwin|go88|b52|789club|rikvip|manclub|jun88|new88|hi88|shbet|789bet|f8bet|188bet|w88|fb88|fun88|bk8|m88|v9bet|12bet|dafabet|happyluke|k8|letou|cmd368|sv388|s128|ae888|v68|vi68|kuwin|okvip|nhatvip|tk88|ww88|cwin|88clb|ai88bet|88vin|saba|f168|77king88|bong88ag|mibet|bj88|vn8k|cuocbanh88|net88|s666|on59|388bet|sv388|lc88|789win|ee88|98win|may88|eubet|abc8|tv88|tt88|nk88|win55|88go|b5|vt999|vip8888|q88|bet88|cá\\s*cược|nhà\\s*cái)(?!.*(?:bão|lũ))\\b',
    '\\b(?:b52\\s*bomber|game\\s*b52|tải\\s*game\\s*b52|b52\\s*club|cổng\\s*game)\\b',
    '\\b(?:poker|blackjack|roulette|baccarat|sicbo|keno|number\\s*game|kết\\s*quả\\s*xổ\\s*số|kqxs|quay\\s*số|trúng\\s*thưởng|vé\\s*số|đổi\\s*thưởng|nạp\\s*rút|uy\\s*tín|xanh\\s*chín|cổng\\s*game|bài\\s*đổi\\s*thưởng|chẵn\\s*lẻ|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề|nổ\\s*hũ|bắn\\s*cá|đá\\s*gà|xí\\s*ngầu|cầu\\s*dây)\\b',
    '\\b(?:nha\\s*cai|da\\s*ga|bong\\s*da|tai\\s*xiu|xoc\\s*dia|lo\\s*de|soi\\s*keo|nhan\\s*dinh|truc\\s*tiep|ket\\s*qua|xo\\s*so|khuyen\\s*mai|nap\\s*dau|hoan\\s*tra|ty\\s*le|keo\\s*nha\\s*cai|huawei\\s*store|aptoide|uptodown)\\b',
    '\\b(?:rule\\s*of|earning\\s*app|in\\s*chẵn\\s*lẻ|canon\\s*2900|baccarat\\s*live|vivu88|88\\s*clb|tặng\\s*bạn|ưu\\s*đãi\\s*tân\\s*thủ)\\b',
    '\\b(?:dinh\\s*dưỡng|thực\\s*phẩm\\s*chức\\s*năng|vitamin|khoáng\\s*chất|tăng\\s*cường|sức\\s*đề\\s*kháng|miễn\\s*dịch|giảm\\s*cân|làm\\s*đẹp|spa|thẩm\\s*mỹ|da\\s*liễu|nha\\s*khoa|đông\\s*y|thuốc\\s*nam|bài\\s*thuốc|thực\\s*đơn|món\\s*ngon|đặc\\s*sản|ẩm\\s*thực|axit\\s*uric|tiểu\\s*đường|huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|ung\\s*thư|ruột\\s*kích\\s*thích|cúm\\s*mùa|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|ngộ\\s*độc\\s*thực\\s*phẩm|tỏi\\s*đen|kim\\s*tiền\\s*thảo|nghẹt\\s*mũi|kháng\\s*sinh|sống\\s*khỏe)(?!.*(?:cho|tại|vùng|cứu\\s*trợ|bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:nhồi\\s*máu\\s*cơ\\s*tim|đột\\s*quỵ|tai\\s*biến|dấu\\s*hiệu\\s*cảnh\\s*báo|triệu\\s*chứng\\s*bệnh|căn\\s*bệnh|bác\\s*sĩ\\s*khuyến\\s*cáo|tư\\s*vấn\\s*tâm\\s*lý|sức\\s*khỏe\\s*tâm\\s*thần|đuối\\s*nước\\s*khi\\s*tắm|tắm\\s*biển|tắm\\s*sông|ao\\s*nhà|bể\\s*bơi|hồ\\s*bơi|đá\\s*bóng|đá\\s*banh|vận\\s*động\\s*viên|bác\\s*sĩ\\s*tư\\s*vấn|chăm\\s*sóc\\s*sức\\s*khỏe|tuyệt\\s*thực|bỏ\\s*đói|ung\\s*thư|thalassemia|vô\\s*sinh)(?!.*(?:bão|lũ|ngập|sạt|thiên\\s*tai|tai\\s*nạn))\\b',
    '(?:khám\\s*bệnh|cấp\\s*phát\\s*thuốc|khám\\s*sức\\s*khỏe|tư\\s*vấn\\s*sức\\s*khỏe|bác\\s*sĩ|bệnh\\s*viện|bệnh\\s*xá|trạm\\s*y\\s*tế)(?!\\s*(?:cứu\\s*trợ|vùng\\s*lũ|vùng\\s*bão|thiên\\s*tai|khắc\\s*phục))',
    '\\b(?:tự\\s*hào|truyền\\s*thống|kỷ\\s*niệm|chào\\s*mừng|thành\\s*lập|ra\\s*mắt|khánh\\s*thành|khởi\\s*công|động\\s*thổ|bế\\s*mạc|khai\\s*mạc|hội\\s*thi|hội\\s*diễn|liên\\s*hoan|giao\\s*lưu|gặp\\s*mặt|tọa\\s*đàm|hội\\s*thảo|tập\\s*huấn|bồi\\s*dưỡng|nhiệm\\s*kỳ|văn\\s*kiện|nghị\\s*quyết|chỉ\\s*thị|kế\\s*hoạch|đề\\s*án|dự\\s*án|quy\\s*hoạch|chiến\\s*lược|tầm\\s*nhìn)(?!.*(?:bão|lũ|lụt|ngập|thiên\\s*tai|khẩn\\s*cấp|ứng\\s*phó|cứu\\s*hộ|sạt\\s*lở|rét\\s*đậm|hạn\\s*mặn|vỡ\\s*đê|thăm\\s*hỏi|hỗ\\s*trợ|PCTT|MARD|phòng\\s*chống\\s*thiên\\s*tai|sơ\\s*tán|di\\s*dời|khắc\\s*phục\\s*hậu\\s*quả))\\b',
    '\\b(?:đại\\s*hội\\s*đại\\s*biểu|thường\\s*trực|tiếp\\s*xúc\\s*cử\\s*tri|bầu\\s*cử|ứng\\s*cử|đắc\\s*cử|bổ\\s*nhiệm|miễn\\s*nhiệm|luân\\s*chuyển\\s*cán\\s*bộ|kỷ\\s*luật\\s*đảng|khai\\s*trừ|cách\\s*chức|nghỉ\\s*hưu|về\\s*hưu|hưởng\\s*chế\\s*độ|trao\\s*tặng\\s*huy\\s*hiệu|trao\\s*bằng\\s*khen|tuyên\\s*dương|gương\\s*điển\\s*hình)(?!.*(?:cứu\\s*trợ|ủng\\s*hộ|khắc\\s*phục|bão|lũ|lụt|ngập|sạt\\s*lở|thiên\\s*tai|thăm\\s*hỏi|PCTT|MARD))\\b',
    '\\b(?:xây\\s*dựng\\s*và\\s*phát\\s*triển|thi\\s*đua\\s*yêu\\s*nước|học\\s*tập\\s*và\\s*làm\\s*theo|dân\\s*vận\\s*khéo|nông\\s*thôn\\s*mới|đô\\s*thị\\s*văn\\s*minh|toàn\\s*dân\\s*đoàn\\s*kết|khắc\\s*phục\\s*khó\\s*khăn|vượt\\s*khó|bứt\\s*phá|tăng\\s*tốc|về\\s*đích|dấu\\s*ấn)(?!.*(?:sau\\s*bão|sau\\s*lũ|thiên\\s*tai|sạt\\s*lở|mưa\\s*lũ|khắc\\s*phục\\s*hậu\\s*quả))\\b',
    '\\b(?:hyundai|toyota|honda|kia|mazda|ford|mitsubishi|nissan|suzuki|vinfast|mercedes|bmw|audi|lexus|porsche|land\\s*rover|peugeot|volvo|subaru|volkswagen|xe\\s*hơi|ô\\s*tô|xe\\s*máy|xe\\s*điện|ra\\s*mắt|phiên\\s*bản|thế\\s*hệ|nâng\\s*cấp|trang\\s*bị|động\\s*cơ|công\\s*suất|momen\\s*xoắn|tiêu\\s*thụ|nhiên\\s*liệu|giá\\s*bán|niêm\\s*yết|lăn\\s*bánh|trả\\s*góp|lãi\\s*suất|vay\\s*vốn|ngân\\s*hàng|uav|drone|máy\\s*bay\\s*không\\s*người\\s*lái|dk\\s*việt\\s*nhật)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn|tìm\\s*kiếm|bão|lũ|ngập|lụt|trôi|sạt|thiên\\s*tai|hư\\s*hỏng))\\b',
    '\\b(?:oppo|iphone|samsung|xiaomi|smartphone|laptop|tablet|công\\s*nghệ\\s*số|chuyển\\s*đổi\\s*số|nền\\s*tảng\\s*số|dịch\\s*vụ\\s*số|chatgpt|gemini|ai\\s*vision|trí\\s*tuệ\\s*nhân\\s*tạo|ios|android|windows|macos|linux|phần\\s*mềm|ứng\\s*dụng|app\\s*store|ch\\s*play|google\\s*play|bảo\\s*mật|an\\s*ninh\\s*mạng|hacker|tấn\\s*công\\s*mạng|lừa\\s*đảo\\s*trực\\s*tuyến|mã\\s*độc|virus\\s*máy\\s*tính|asus|rtx|oled|màn\\s*hình|notepad|virtual|workspaces|lenovo|yoga|tab)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn))\\b',
    'việc\\s*nhẹ\\s*lương\\s*cao|bóc\\s*vỏ\\s*tôm|tắt\\s*camera|camera\\s*quay\\s*lén|giải\\s*cứu\\s*(?:rùa|chim|động\\s*vật|thú\\s*quý|tôm\\s*hùm|nông\\s*sản)',
    '\\.docx\\b|\\.pdf\\b|\\.doc\\b|AstroWind|Tailwind\\s*CSS',
    'giá\\s*thanh\\s*long|lên\\s*kệ\\s*siêu\\s*thị|xuất\\s*khẩu\\s*nông\\s*sản|vé\\s*máy\\s*bay\\s*giá\\s*rẻ|tết\\s*nguyên\\s*đán|thưởng\\s*tết|được\\s*mùa|được\\s*giá|năng\\s*suất\\s*cao',
    '\\b(?:khách\\s*du\\s*lịch|lượng\\s*khách|ngành\\s*du\\s*lịch|doanh\\s*thu\\s*du\\s*lịch|kích\\s*cầu\\s*du\\s*lịch|vui\\s*xuân|đón\\s*tết|du\\s*xuân|nghỉ\\s*lễ|dịp\\s*lễ|vé\\s*máy\\s*bay|chặng\\s*bay|đường\\s*bay|hàng\\s*không|vietjet|vietnam\\s*airlines|bamboo\\s*airways|vietravel|check-in|sống\\s*ảo|điểm\\s*đến|khám\\s*phá|trải\\s*nghiệm|tour|combo|voucher|homestay|resort|tham\\s*quan|nghỉ\\s*dưỡng|săn\\s*mây|săn\\s*tuyết|mùa\\s*vàng|mùa\\s*lúa|hoa\\s*tam\\s*giác\\s*mạch|hoa\\s*đỗ\\s*quyên)(?!.*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ|mắc\\s*kẹt|cô\\s*lập|khắc\\s*phục|thiệt\\s*hại|bão|lũ|thiên\\s*tai|cháy|chìm))\\b',
    '\\b(?:diễn\\s*tập|thực\\s*chiến|an\\s*toàn\\s*thông\\s*tin|an\\s*ninh\\s*mạng|bức\\s*xạ|hạt\\s*nhân|an\\s*ninh\\s*phi\\s*truyền\\s*thống)(?!.*(?:người\\s*chết|thương\\s*vong|thiệt\\s*hại\\s*về\\s*người))\\b',
    '\\b(?:nghĩa\\s*vụ\\s*quân\\s*sự|nghĩa\\s*vụ\\s*công\\s*an|tuyển\\s*quân|nhập\\s*ngũ|giao\\s*nhận\\s*quân|khám\\s*tuyển|công\\s*dân\\s*thực\\s*hiện\\s*nghĩa\\s*vụ|tuyển\\s*sinh\\s*công\\s*an|tuyển\\s*sinh\\s*quân\\s*đội|quân\\s*khu|bộ\\s*chỉ\\s*huy|ban\\s*chỉ\\s*huy|bộ\\s*tư\\s*lệnh)(?!.*(?:sơ\\s*tán|di\\s*dời|cứu\\s*hộ|cứu\\s*nạn|bão|lũ|ngập|thiên\\s*tai|khẩn\\s*cấp|hỗ\\s*trợ\\s*dân|giúp\\s*dân|tái\\s*thiết|làm\\s*nhà|hải\\s*văn|sóng\\s*lớn|biển\\s*động|gió\\s*mạnh))\\b',
    '\\b(?:tuần\\s*tra|kiểm\\s*soát|tràn\\s*lan|trấn\\s*áp|tội\\s*phạm|tệ\\s*nạn|ma\\s*túy|cờ\\s*bạc|mại\\s*dâm|pháo\\s*nổ|vũ\\s*khí|vật\\s*liệu\\s*nổ|súng\\s*tự\\s*chế|an\\s*ninh\\s*trật\\s*tự|antt|trật\\s*tự\\s*an\\s*toàn\\s*giao\\s*thông|ttatgt|đảm\\s*bảo\\s*trật\\s*tự|giữ\\s*vững\\s*an\\s*ninh|an\\s*ninh\\s*kinh\\s*tế|an\\s*ninh\\s*chính\\s*trị|an\\s*ninh\\s*quốc\\s*gia|an\\s*ninh\\s*an\\s*toàn)\\b',
    '\\b(?:bảo\\s*vệ\\s*tuyệt\\s*đối|an\\s*toàn\\s*sự\\s*kiện|lễ\\s*hội|quốc\\s*khánh|ngày\\s*lễ|bảo\\s*vệ\\s*mục\\s*tiêu|diễu\\s*binh|diễu\\s*hành)\\b',
    '\\b(?:đỗ\\s*xe|dừng\\s*xe|lấn\\s*làn|vi\\s*phạm\\s*giao\\s*thông|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|gplx|đăng\\s*kiểm|phạt\\s*nguội|camera\\s*phạt|biển\\s*báo|tín\\s*hiệu\\s*đèn|csgt|cảnh\\s*sát\\s*giao\\s*thông\\s*xử\\s*lý|thổi\\s*nồng\\s*độ\\s*cồn)\\b',
    '\\b(?:vpn|mã\\s*độc|dữ\\s*liệu\\s*cá\\s*nhân|bảo\\s*mật\\s*thông\\s*tin|lừa\\s*đảo\\s*trực\\s*tuyến|không\\s*gian\\s*mạng|tài\\s*khoản\\s*ngân\\s*hàng|chiếm\\s*đoạt|giả\\s*danh|mạo\\s*danh|đòi\\s*nợ\\s*thuê|tín\\s*dụng\\s*đen|shark\\s*thủy|trương\\s*mỹ\\s*lan|vạn\\s*thịnh\\s*phát|tân\\s*hoàng\\s*minh|scb|flc|thao\\s*túng|chứng\\s*khoán|tiền\\s*ảo|bitcoin|tiền\\s*kỹ\\s*thuật\\s*số)\\b',
    '\\b(?:bảo\\s*hiểm\\s*thất\\s*nghiệp|trợ\\s*cấp\\s*thất\\s*nghiệp|mức\\s*đóng\\s*bảo\\s*hiểm|hưởng\\s*trợ\\s*cấp|trợ\\s*cấp\\s*xã\\s*hội)\\b',
    '\\b(?:lương\\s*hưu|tăng\\s*lương|cải\\s*cách\\s*tiền\\s*lương|chế\\s*độ\\s*hưu\\s*trí|tuổi\\s*nghỉ\\s*hưu|điều\\s*chỉnh\\s*lương)\\b',
    '\\b(?:tuyến\\s*metro|đường\\s*sắt\\s*đô\\s*thị|tàu\\s*điện\\s*ngầm|đường\\s*sắt\\s*trên\\s*cao|ga\\s*ngầm)(?!.*(?:ngập|lũ|sạt\\s*lở))\\b',
    '\\b(?:phẫu\\s*thuật|ca\\s*mổ|bệnh\\s*lý|sản\\s*phụ|thai\\s*kỳ|tử\\s*cung|hiếm\\s*muộn|vô\\s*sinh|nội\\s*soi|ghép\\s*tạng|thẩm\\s*mỹ|cấy\\s*ghép|ghép\\s*gan|ghép\\s*tim|ghép\\s*thận|tai\\s*máy|trợ\\s*thính)\\b',
    '\\b(?:chiếu\\s*phim|biểu\\s*diễn|văn\\s*nghệ|cuộc\\s*thi|trực\\s*tuyến|tìm\\s*hiểu|hội\\s*diễn|liên\\s*hoan|triển\\s*lãm|hưởng\\s*ứng|phát\\s*động\\s*cuộc\\s*thi|hội\\s*thao|ngoại\\s*khóa|thực\\s*hành\\s*pccc|tìm\\s*hiểu\\s*luật|hội\\s*thi)\\b',
    '\\b(?:hành\\s*trình\\s*công\\s*lý|đạo\\s*đức\\s*nghề\\s*nghiệp|quy\\s*tắc\\s*ứng\\s*xử|văn\\s*hóa\\s*công\\s*sở|nghỉ\\s*(?:tết|lễ)\\s*\\d+\\s*ngày|đề\\s*xuất\\s*nghỉ)\\b',
    '\\b(?:học\\s*phí|điểm\\s*chuẩn|quy\\s*chế\\s*thi|kỳ\\s*thi\\s*tốt\\s*nghiệp|sách\\s*giáo\\s*khoa|kỷ\\s*yếu|tự\\s*chủ\\s*đại\\s*học|dạy\\s*thêm|học\\s*thêm|ôn\\s*thi|luyện\\s*thi|sĩ\\s*tử|điểm\\s*thi|tra\\s*cứu\\s*điểm|khai\\s*giảng|năm\\s*học\\s*mới|tuyển\\s*sinh|giáo\\s*viên\\s*chủ\\s*nhiệm|đề\\s*án\\s*ngoại\\s*ngữ|tiếng\\s*anh|lịch\\s*nghỉ\\s*tết|nghỉ\\s*học|lịch\\s*học|tựu\\s*trường|tặng\\s*sách|trao\\s*tặng\\s*sách|tủ\\s*sách|phân\\s*hiệu|thư\\s*viện)(?!.*(?:vùng\\s*lũ|bão|thiên\\s*tai|hỗ\\s*trợ|khắc\\s*phục|sạt\\s*lở|mưa\\s*lũ|rét|ngập))\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|hưu\\s*trí|lương\\s*hưu|quỹ\\s*hưu\\s*trí|đóng\\s*bảo\\s*hiểm|trợ\\s*cấp\\s*thất\\s*nghiệp|xuất\\s*khẩu\\s*lao\\s*động)(?!.*(?:hỗ\\s*trợ\\s*đồng\\s*bào|vùng\\s*lũ|thiên\\s*tai|khắc\\s*phục))\\b',
    '\\b(?:đấu\\s*thầu\\s*thuốc|vật\\s*tư\\s*y\\s*tế|bảo\\s*hiểm\\s*y\\s*tế|y\\s*đức|quản\\s*lý\\s*bệnh\\s*viện|khám\\s*sức\\s*khỏe\\s*định\\s*kỳ|chăm\\s*sóc\\s*sức\\s*khỏe|đông\\s*y|tây\\s*y|nhiễm\\s*khuẩn)\\b',
    '\\b(?:đại\\s*lễ|cầu\\s*an|lễ\\s*chùa|dâng\\s*hương|tâm\\s*linh|ngoại\\s*cảm|gọi\\s*hồn|vong\\s*linh|chất\\s*độc\\s*da\\s*cam|dioxin|truy\\s*tìm\\s*người)\\b',
    '\\b(?:biệt\\s*thự\\s*biển|condotel|shophouse|vinhomes|sun\\s*group|novaland|mở\\s*bán\\s*giai\\s*đoạn|chiết\\s*khấu\\s*khủng|ocean\\s*city|smart\\s*city|ecopark|đại\\s*đô\\s*thị|khu\\s*đô\\s*thị\\s*mới|đất\\s*nền|phân\\s*lô|bán\\s*đất)\\b',
    '\\b(?:siêu\\s*sale|săn\\s*deal|áp\\s*mã|giảm\\s*sâu|mở\\s*bán\\s*ưu\\s*đãi|càn\\s*quét\\s*giỏ\\s*hàng|đổ\\s*bộ\\s*thị\\s*trường)\\b',
    '\\b(?:clip\\s*gây\\s*bão|video\\s*xôn\\s*xao|hành\\s*động\\s*đẹp\\s*gây\\s*sốt|cư\\s*dân\\s*mạng\\s*truy\\s*tìm|phẫn\\s*nộ\\s*với\\s*hành\\s*động|bông\\s*hoa\\s*thép)\\b',
    '\\b(?:cơn\\s*lốc\\s*tuyển\\s*dụng|cơ\\s*hội\\s*vàng|thăng\\s*tiến\\s*sự\\s*nghiệp|định\\s*hướng\\s*nghề\\s*nghiệp|bí\\s*quyết\\s*thành\\s*công|việc\\s*làm|tuyển\\s*dụng)\\b',
    '\\b(?:công\\s*thức\\s*nấu\\s*ăn|mẹo\\s*vặt\\s*nhà\\s*bếp|top\\s*quán\\s*ngon|review\\s*ẩm\\s*thực|đặc\\s*sản\\s*vùng\\s*miền|thực\\s*đơn\\s*mỗi\\s*ngày)\\b',
    '\\b(?:đề\\s*tài\\s*nghiên\\s*cứu|công\\s*trình\\s*khoa\\s*học|phát\\s*kiến\\s*vĩ\\s*đại|luận\\s*văn\\s*tốt\\s*nghiệp|chuyên\\s*đề\\s*học\\s*thuật)\\b',
    '\\b(?:thiết\\s*bị\\s*báo\\s*cháy|hệ\\s*thống\\s*báo\\s*cháy|tập\\s*huấn\\s*pccc|nghiệm\\s*thu\\s*pccc)\\b',
    '\\b(?:đại\\s*hội\\s*cổ\\s*đông|hội\\s*đồng\\s*quản\\s*trị|hđqt|báo\\s*cáo\\s*tài\\s*chính|cổ\\s*phiếu\\s*quỹ|vốn\\s*hóa\\s*thị\\s*trường|niêm\\s*yết\\s*sàn|trái\\s*phiếu\\s*doanh\\s*nghiệp|chốt\\s*quyền\\s*trả\\s*cổ\\s*tức|chi\\s*trả\\s*cổ\\s*tức)\\b',
    '\\b(?:đặt\\s*tên\\s*đường|chỉnh\\s*trang\\s*đô\\s*thị|tu\\s*bổ\\s*di\\s*tích|xây\\s*dựng\\s*công\\s*viên|vườn\\s*hoa|tượng\\s*đài|chiếu\\s*sáng\\s*đô\\s*thị)\\b',
    '\\b(?:bầu\\s*cử\\s*mỹ|tổng\\s*thống\\s*mỹ|nhà\\s*trắng|điện\\s*kremlin|thám\\s*hiểm\\s*không\\s*gian|nasa|spacex|vũ\\s*trụ|thiên\\s*văn|khảo\\s*cổ|wto|thuế\\s*quan|áp\\s*thuế|tranh\\s*chấp\\s*thương\\s*mại|đình\\s*chiến|lệnh\\s*trừng\\s*phạt|viện\\s*trợ\\s*quân\\s*sự|ngoại\\s*giao|đại\\s*sứ|giáo\\s*hoàng|vatican)\\b',
    '\\b(?:fashion\\s*week|bộ\\s*sưu\\s*tập|thời\\s*trang\\s*cao\\s*cấp|nhãn\\s*hàng\\s*xa\\s*xỉ|túi\\s*xách|nước\\s*hoa|trang\\s*sức|kim\\s*cương)\\b',
    '\\b(?:tử\\s*vi|cung\\s*hoàng\\s*đạo|phong\\s*thủy|hợp\\s*tuổi|ngày\\s*tốt|giờ\\s*xấu|xem\\s*bói|gieo\\s*quẻ|nhân\\s*tướng\\s*học|nhân\\s*mã|xử\\s*nữ|bạch\\s*dương|kim\\s*ngưu|song\\s*tử|cự\\s*giải|sư\\s*tử|thiên\\s*bình|bọ\\s*cạp|ma\\s*kết|bảo\\s*bình|song\\s*ngư)\\b',
    '\\b(?:đánh\\s*giá\\s*xe|trải\\s*nghiệm\\s*lái|động\\s*cơ\\s*turbo|mã\\s*lực|mô-men\\s*xoắn|phụ\\s*tùng\\s*chính\\s*hãng|lazang|lốp\\s*xe|ngoại\\s*thất\\s*xe)\\b',
    '\\b(?:phẫu\\s*thuật\\s*thẩm\\s*mỹ|hút\\s*mỡ|nâng\\s*mũi|tiêm\\s*filler|căng\\s*chỉ|trị\\s*mụn|chăm\\s*sóc\\s*da|spa|thẩm\\s*mỹ\\s*viện)\\b',
    '\\b(?:hội\\s*chợ\\s*thương\\s*mại|ngày\\s*hội\\s*việc\\s*làm|lễ\\s*hội\\s*ẩm\\s*thực|minigame|bốc\\s*thăm\\s*trúng\\s*thưởng|vòng\\s*quay\\s*may\\s*mắn)\\b',
    '\\b(?:thực\\s*đơn\\s*giảm\\s*cân|mẹo\\s*sống\\s*khỏe|tác\\s*dụng\\s*của\\s*rau| yoga|gym|fitness|bài\\s*tập\\s*thể\\s*dục|dinh\\s*dưỡng\\s*lành\\s*mạnh)\\b',
    '\\b(?:nuôi\\s*dạy\\s*con|sữa\\s*mẹ|ăn\\s*dặm|phát\\s*triển\\s*trí\\s*não|đồ\\s*chơi\\s*trẻ\\s*em|mẹ\\s*bầu|thai\\s*nhi|mầm\\s*non)\\b',
    '\\b(?:phê\\s*bình\\s*sách|tác\\s*giả\\s*trẻ|triển\\s*lãm\\s*tranh|hội\\s*họa|điêu\\s*khắc|giai\\s*thoại\\s*lịch\\s*sử|nhân\\s*vật\\s*lịch\\s*sử|thơ\\s*ca|quân\\s*địch|nghi\\s*binh|chiến\\s*tranh|kháng\\s*chiến|đánh\\s*thắng|giải\\s*phóng\\s*miền\\s*nam|quân\\s*ta|quân\\s*ngụy)\\b',
    '\\b(?:chăm\\s*sóc\\s*chó\\s*mèo|thú\\s*cưng|giống\\s*chó|phụ\\s*kiện\\s*pet|thú\\s*y|bệnh\\s*viện\\s*thú\\s*y)\\b',
    '\\b(?:báo\\s*giá\\s*xi\\s*măng|sắt\\s*thép|vật\\s*liệu\\s*xây\\s*dựng|mẫu\\s*nhà\\s*đẹp|nội\\s*thất\\s*hiện\\s*đại|thiết\\s*kế\\s*căn\\s*hộ)\\b',
    '\\b(?:voucher\\s*du\\s*lịch|tour\\s*giá\\s*rẻ|cẩm\\s*nang\\s*điểm\\s*đến|lịch\\s*trình\\s*khám\\s*phá|review\\s*homestay|vé\\s*máy\\s*bay\\s*khứ\\s*hồi|dịch\\s*vụ\\s*nghỉ\\s*dưỡng)\\b',
    '\\b(?:kỹ\\s*thuật\\s*trồng|chăm\\s*sóc\\s*cây\\s*cảnh|phong\\s*lan|bonsai|phân\\s*bón|thuốc\\s*trừ\\s*sâu|nông\\s*nghiệp\\s*công\\s*nghệ\\s*cao|giống\\s*cây\\s*trồng)\\b',
    '\\b(?:học\\s*đàn|học\\s*vẽ|chụp\\s*ảnh\\s*chân\\s*dung|ống\\s*máy\\s*ảnh|mirrorless|dựng\\s*phim|hậu\\s*kỳ|thiết\\s*kế\\s*đồ\\s*họa|photoshop|illustrator)\\b',
    '\\b(?:tiệc\\s*tất\\s*niên|year\\s*end\\s*party|teambuilding|văn\\s*hóa\\s*doanh\\s*nghiệp|nhân\\s*viên\\s*tiêu\\s*biểu|nghỉ\\s*mát\\s*hè|sinh\\s*nhật\\s*công\\s*ty)\\b',
    '\\b(?:tâm\\s*lý\\s*học|trầm\\s*cảm|chữa\\s*lành|sang\\s*chấn\\s*tâm\\s*lý|kỹ\\s*năng\\s*sống|tư\\s*duy\\s*tích\\s*cực|phát\\s*triển\\s*bản\\s*thân|hạnh\\s*phúc\\s*mỗi\\s*ngày)\\b',
    '\\b(?:big\\s*data|machine\\s*learning|trí\\s*tuệ\\s*nhân\\s*tạo|backend|frontend|lập\\s*trình\\s*viên|python|java|javascript|thiết\\s*kế\\s*ui/ux|server|hosting|ên\\s*kết\\s*đào\\s*tạo)\\b',
    '\\b(?:hố\\s*đen|thiên\\s*hà|dải\\s*ngân\\s*hà|vật\\s*chất\\s*tối|gen\\s*di\\s*truyền|dna|tế\\s*bào\\s*gốc|biến\\s*đổi\\s*gen|vi\\s*khuẩn|virus\\s*(?!\\s*it))\\b',
    '\\b(?:viện\\s*kiểm\\s*sát|cơ\\s*quan\\s*điều\\s*tra|luật\\s*sư|bào\\s*chữa|kháng\\s*cáo|tư\\s*vấn\\s*pháp\\s*luật|hợp\\s*đồng\\s*kinh\\s*tế|thừa\\s*kế|tranh\\s*chấp\\s*tài\\s*sản)\\b',
    '\\b(?:đón\\s*tiếp\\s*đoàn|nghị\\s*sự|ký\\s*kết\\s*biên\\s*bản|hợp\\s*tác\\s*chiến\\s*lược|trao\\s*đổi\\s*văn\\s*hóa|ngoại\\s*giao\\s*nhân\\s*dân|thi\\s*đua\\s*khen\\s*thưởng|công\\s*tác\\s*cán\\s*bộ)\\b',
    '\\b(?:khám\\s*xét|niêm\\s*phong|cưỡng\\s*chế\\s*kê\\s*biên|phong\\s*tỏa\\s*tài\\s*khoản|tạm\\s*đình\\s*chỉ\\s*công\\s*tác|lệnh\\s*bắt\\s*tạm\\s*giam|đọc\\s*lệnh\\s*khởi\\s*tố)\\b',
    '\\b(?:nghi\\s*thức\\s*ngoại\\s*giao|lễ\\s*đón|duyệt\\s*đội\\s*danh\\s*dự|tiễn\\s*đoàn|quan\\s*hệ\\s*đối\\s*tác|vun\\s*đắp\\s*tình\\s*hữu\\s*nghị)\\b',
    '\\b(?:căn\\s*hộ\\s*cao\\s*cấp|mặt\\s*bằng\\s*kinh\\s*doanh|thuê\\s*văn\\s*phòng|sang\\s*nhượng\\s*quán|kđt|khu\\s*đô\\s*thị\\s*mới|quy\\s*hoạch\\s*chi\\s*tiết)\\b',
    '\\b(?:tuyển\\s*dụng\\s*gấp|mức\\s*lương\\s*thỏa\\s*thuận|quyền\\s*lợi\\s*hấp\\s*dẫn|môi\\s*trường\\s*làm\\s*việc|nộp\\s*hồ\\s*sơ|phỏng\\s*vấn\\s*online)\\b',
    '\\b(?:trung\\s*đông|hezbollah|houthi|biển\\s*đỏ|eo\\s*biển\\s*hormuz|xung\\s*đột\\s*israel|thủ\\s*tướng\\s*netanyahu)\\b',
    '\\b(?:đồi\\s*capitol|lầu\\s*năm\\s*góc|bầu\\s*cử\\s*tổng\\s*thống|đảng\\s*dân\\s*chủ|đảng\\s*cộng\\s*hòa|donald\\s*trump|joe\\s*biden|kamala\\s*harris)\\b',
    '\\b(?:fed|wall\\s*street|dow\\s*jones|nasdaq|goldman\\s*sachs|jp\\s*morgan|quỹ\\s*tiền\\s*tệ\\s*quốc\\s*tế|ngân\\s*hàng\\s*thế\\s*giới|wb|imf)\\b',
    '\\b(?:huân\\s*chương|bằng\\s*khen|danh\\s*hiệu\\s*cao\\s*quý|kỷ\\s*niệm\\s*chương|nghệ\\s*sĩ\\s*nhân\\s*dân|nsnd|nghệ\\s*sĩ\\s*ưu\\s*tú|nsut)\\b',
    '\\b(?:hội\\s*nghị\\s*hiệp\\s*thương|kỳ\\s*hợp\\s*thứ|đảng\\s*viên\\s*mới|sinh\\s*hoạt\\s*chi\\s*bộ|nghị\\s*quyết\\s*trung\\s*ương|công\\s*tác\\s*kiểm\\s*tra\\s*đảng)\\b',
    '\\b(?:tòa\\s*án\\s*tối\\s*cao|viện\\s*kiểm\\s*sát\\s*nhân\\s*dân|hội\\s*đồng\\s*xét\\s*xử|luật\\s*sư\\s*bào\\s*chữa|tranh\\s*tụng|phiên\\s*tòa\\s*sơ\\s*thẩm|phúc\\s*thẩm|đại\\s*diện\\s*pháp\\s*luật)\\b',
    '\\b(?:di\\s*sản\\s*văn\\s*hóa|phong\\s*tục\\s*tập\\s*quán|bảo\\s*tồn\\s*di\\s*tích|làng\\s*nghề\\s*truyền\\s*thống|nghệ\\s*nhân\\s*ưu\\s*tú|di\\s*vật|cổ\\s*vật)\\b',
    '\\b(?:miss\\s*grand|miss\\s*universe|miss\\s*world|anh\\s*trai\\s*say\\s*hi|anh\\s*trai\\s*vượt\\s*ngàn\\s*chông\\s*gai|the\\s*mask\\s*singer|show\\s*thực\\s*tế)\\b',
    '\\b(?:trích\\s*lập\\s*dự\\s*phòng|nợ\\s*xấu|thanh\\s*khoản|tái\\s*cơ\\s*cấu|phí\\s*bảo\\s*hiểm|hợp\\s*đồng\\s*nhân\\s*thọ|quyền\\s*lợi\\s*khách\\s*hàng)\\b',
    '\\b(?:khớp\\s*lệnh|dư\\s*mua|dư\\s*bán|chứng\\s*khoán\\s*phái\\s*sinh|khối\\s*ngoại|vốn\\s*điều\\s*lệ|lệnh\\s*giới\\s*hạn)\\b',
    '\\b(?:vệ\\s*tinh\\s*nhân\\s*tạo|trạm\\s*không\\s*gian|mưa\\s*sao\\s*băng|nhật\\s*thực|nguyệt\\s*thực|kính\\s*thiên\\s*văn|tàu\\s*vũ\\s*trụ)\\b',
    '\\b(?:bạn\\s*đọc\\s*viết|nhịp\\s*cầu\\s*độc\\s*giả|thư\\s*tòa\\s*soạn|ký\\s*sự\\s*pháp\\s*đình|chuyện\\s*thường\\s*ngày|góc\\s*nhìn\\s*tri\\s*thức|diễn\\s*đàn\\s*kinh\\s*tế)\\b',
    '\\b(?:tư\\s*vấn\\s*hướng\\s*nghiệp|cẩm\\s*nang\\s*du\\s*học|xét\\s*tuyển\\s*học\\s*bạ|chỉ\\s*tiêu\\s*tuyển\\s*sinh|điểm\\s*sàn|nguyện\\s*vọng\\s*1|kỳ\\s*thi\\s*đánh\\s*giá\\s*năng\\s*lực)\\b',
    '\\b(?:ban\\s*quản\\s*trị|phí\\s*bảo\\s*trì|họp\\s*dân\\s*cư|tiện\\s*ích\\s*nội\\s*khu|vận\\s*hành\\s*nhà\\s*máy|hệ\\s*thống\\s*máy\\s*chủ|đường\\s*truyền\\s*internet)\\b',
    '\\b(?:khai\\s*trương\\s*chi\\s*nhánh|giảm\\s*giá\\s*khai\\s*trương|voucher\\s*mua\\s*sắm|thẻ\\s*thành\\s*viên|tích\\s*điểm\\s*đổi\\s*quà|giờ\\s*vàng\\s*mua\\s*sắm)\\b',
    '\\b(?:hạt\\s*giống\\s*tâm\\s*hồn|châm\\s*ngôn\\s*sống|triết\\s*lý\\s*kinh\\s*doanh|quà\\s*tặng\\s*cuộc\\s*sống|nhân\\s*sinh\\s*quan|đắc\\s*nhân\\s*tâm)\\b',
    '\\b(?:nút\\s*giao\\s*thông|cầu\\s*vượt\\s*thép|hầm\\s*chui|dải\\s*phân\\s*cách|lát\\s*vỉ\\s*hè|chỉnh\\s*trang\\s*hàng\\s*rào|cáp\\s*quang\\s*biển|băng\\s*thông|trạm\\s*biến\\s*áp\\s*áp\\s*cao)\\b',
    '\\b(?:tổ\\s*dân\\s*phố|khu\\s*phố\\s*văn\\s*hóa|gia\\s*đình\\s*tiêu\\s*biểu|giấy\\s*khai\\s*sinh|thường\\s*trú|tạm\\s*vắng|căn\\s*cước\\s*công\\s*dân|định\\s*danh\\s*mức\\s*2)\\b',
    '\\b(?:phân\\s*tích\\s*kỹ\\s*thuật|ngưỡng\\s*kháng\\s*cự|hỗ\\s*trợ\\s*mạnh|mô\\s*hình\\s*nến|chỉ\\s*số\\s*rsi|etf|chứng\\s*quyền|trái\\s*phiếu\\s*chính\\s*phủ)\\b',
    '\\b(?:lăng\\s*tẩm|đền\\s*đài|cố\\s*đô|di\\s*tích\\s*quốc\\s*gia|khảo\\s*cổ\\s*học|dấu\\s*tích\\s*cổ|hiện\\s*vật|triều\\s*đại|vua\\s*chúa)\\b',
    '\\b(?:bản\\s*vá\\s*lỗi|mã\\s*nguồn|lỗ\\s*hổng\\s*bảo\\s*mật|tấn\\s*công\\s*ddos|phần\\s*mềm\\s*độc\\s*hại|trải\\s*nghiệm\\s*người\\s*dùng|ux/ui|giao\\s*diện\\s*mới)\\b',
    '\\b(?:đa\\s*dạng\\s*sinh\\s*học|bảo\\s*tồn\\s*động\\s*vật|cá\\s*thể\\s*quý\\s*hiếm|sách\\s*đỏ|thả\\s*về\\s*rừng|vườn\\s*quốc\\s*gia|khu\\s*bảo\\s*tồn|tài\\s*nguyên\\s*sinh\\s*vật)\\b',
    '\\b(?:chứng\\s*chỉ\\s*hành\\s*nghề|đào\\s*tạo\\s*nghiệp\\s*vụ|kỹ\\s*năng\\s*chuyên\\s*môn|huấn\\s*luyện\\s*an\\s*toàn|văn\\s*bằng\\s*quốc\\s*tế|phong\\s*trào\\s*tay\\s*nghề)\\b',
    '\\b(?:tiếp\\s*đại\\s*sứ|trình\\s*quốc\\s*thư|giao\\s*lưu\\s*hữu\\s*nghị|củng\\s*cố\\s*quan\\s*hệ|ngoại\\s*giao\\s*đa\\s*phương|ký\\s*kết\\s*biên\\s*bản\\s*ghi\\s*nhớ|MOU|đối\\s*tác\\s*chiến\\s*lược)\\b',
    '\\b(?:lương\\s*tháng\\s*13|thưởng\\s*năng\\s*suất|nội\\s*quy\\s*lao\\s*động|công\\s*đoàn\\s*cơ\\s*sở|khen\\s*thưởng\\s*định\\s*kỳ|phong\\s*trào\\s*lao\\s*động|thi\\s*đua\\s*ngành)\\b',
    '\\b(?:bản\\s*quyền\\s*tác\\s*giả|sở\\s*hữu\\s*trí\\s*tuệ|bảo\\s*hộ\\s*thương\\s*hiệu|luận\\s*văn\\s*thạc\\s*sĩ|nghiên\\s*cứu\\s*sinh|hội\\s*đồng\\s*bảo\\s*vệ|tạp\\s*chí\\s*khoa\\s*học)\\b',
    '\\b(?:điểm\\s*thu\\s*gom\\s*rác|phí\\s*dịch\\s*vụ\\s*chung\\s*cư|đèn\\s*đường|lát\\s*đá\\s*vỉ\\s*hè|cây\\s*xanh\\s*đô\\s*thị|phun\\s*thuốc\\s*muỗi|diệt\\s*côn\\s*trùng)\\b',
    '\\b(?:trà\\s*đạo|thiền\\s*định|cắm\\s*hoa\\s*nghệ\\s*thuật|sưu\\s*tầm\\s*đồ\\s*cổ|thú\\s*vui\\s*tao\\s*nhã|trưng\\s*bày\\s*sinh\\s*vật\\s*cảnh)\\b',
    '\\b(?:huấn\\s*luyện\\s*quân\\s*sự|tuyển\\s*quân|nhập\\s*ngũ|giao\\s*nhận\\s*quân|khám\\s*tuyển|hội\\s*thao\\s*quốc\\s*phòng)\\b',
    '\\b(?:lễ\\s*hội\\s*dân\\s*gian|hội\\s*làng|tín\\s*ngưỡng\\s*thờ\\s*cúng|không\\s*gian\\s*văn\\s*hóa|không\\s*gian\\s*đi\\s*bộ|nghệ\\s*thuật\\s*đường\\s*phố)\\b',
    '\\b(?:quản\\s*lý\\s*thị\\s*trường|hàng\\s*giả\\s*hàng\\s*nhái|tiêu\\s*hủy\\s*tang\\s*vật|vi\\s*phạm\\s*nhãn\\s*hiệu|quản\\s*lý\\s*giá\\s*cả|bình\\s*ổn\\s*thị\\s*trường)\\b',
    '\\b(?:lấy\\s*ý\\s*kiến\\s*dự\\s*thảo|nghị\\s*định\\s*hướng\\s*dẫn|thông\\s*tư\\s*liên\\s*tịch|hđnd\\s*các\\s*cấp|công\\s*tác\\s*pháp\\s*chế|tuyên\\s*truyền\\s*pháp\\s*luật)\\b',
    '\\b(?:tổng\\s*đài\\s*cskh|đường\\s*dây\\s*nóng\\s*khiếu\\s*nại|giải\\s*đáp\\s*thắc\\s*mắc|phản\\s*hồi\\s*khách\\s*hàng|quy\\s*trình\\s*kỹ\\s*thuật|hỗ\\s*trợ\\s*trực\\s*tuyến)\\b',
    '\\b(?:đập\\s*hộp|trên\\s*tay|review\\s*chi\\s*tiết|đánh\\s*giá\\s*hiệu\\s*năng|so\\s*sánh\\s*cấu\\s*hình|benchmark|antutu|camera\\s*selfie|màn\\s*hình\\s*amoled|tần\\s*số\\s*quét)\\b',
    '\\b(?:tối\\s*ưu\\s*seo|backlink|chạy\\s*quảng\\s*cáo|adsense|google\\s*ads|facebook\\s*ads|tiktok\\s*shop|tiếp\\s*thị\\s*liên\\s*kết|affiliate\\s*marketing|branding|thương\\s*hiệu\\s*cá\\s*nhân)\\b',
    '\\b(?:máy\\s*ảnh\\s*film|len\\s*mf|lens\\s*fix|ngàm\\s*chuyển|phụ\\s*kiện\\s*studio|đèn\\s*flash|chụp\\s*ảnh\\s*nghệ\\s*thuật|quay\\s*phim\\s*4k)\\b',
    '\\b(?:cá\\s*cảnh|thủy\\s*sinh|hồ\\s*cá\\s*koi|cây\\s*không\\s*khí|sen\\s*đá|xương\\s*rồng|đồ\\s*chơi\\s*mô\\s*hình|lego|action\\s*figure|vape|pod\\s*system)\\b',
    '\\b(?:mẹo\\s*làm\\s*bánh|nấu\\s*ăn\\s*ngon|nồi\\s*chiên\\s*không\\s*dầu|máy\\s*ép\\s*chậm|đồ\\s*gia\\s*dụng\\s*thông\\s*minh|robot\\s*hút\\s*bụi|máy\\s*rửa\\s*bát)\\b',
    '\\b(?:ngư\\s*trường\\s*khai\\s*thác|xuất\\s*khẩu\\s*hải\\s*sản|vận\\s*tải\\s*biển|cảng\\s*nước\\s*sâu|luồng\\s*hàng\\s*hải|tàu\\s*viễn\\s*dương|giàn\\s*khoan\\s*dầu|dầu\\s*khí\\s*quốc\\s*gia)\\b',
    '\\b(?:cánh\\s*đồng\\s*mẫu\\s*lớn|hợp\\s*tác\\s*xã\\s*nông\\s*nghiệp|sản\\s*xuất\\s*giỏi|chăn\\s*nuôi\\s*tập\\s*trung|chuỗi\\s*giá\\s*trị|truy\\s*xuất\\s*nguồn\\s*gốc)\\b',
    '\\b(?:suy\\s*giảm\\s*thị\\s*lực|mờ\\s*mắt|nhãn\\s*khoa|thủy\\s*tinh\\s*thể|đục\\s*thủy\\s*tinh\\s*thể|mù\\s*lòa|cận\\s*thị|loạn\\s*thị)(?!.*(?:bão|lũ))\\b',
    '\\b(?:suy\\s*tim|nhồi\\s*máu|cơ\\s*tim|hở\\s*van\\s*tim|đặt\\s*stent|mạch\\s*vành|suy\\s*thận|chạy\\s*thận)(?!.*(?:bão|lũ|cứu\\s*trợ|sơ\\s*tán))\\b',
    '\\b(?:mất\\s*trí\\s*nhớ|alzheimer|sa\\s*sút\\s*trí\\s*tuệ|thần\\s*kinh|tâm\\s*thần\\s*phân\\s*liệt|trầm\\s*cảm)(?!.*(?:bão|lũ))\\b',
    '\\b(?:sởi|rubella|thủy\\s*đậu|quai\\s*bị|tay\\s*chân\\s*miệng|sốt\\s*phát\\s*ban|cúm\\s*gia\\s*cầm|h5n1)(?!.*(?:bão|lũ|vùng\\s*lũ))\\b',
    '\\b(?:xây\\s*dựng\\s*lại\\s*chợ|quy\\s*hoạch\\s*chợ|tiểu\\s*thương\\s*chợ|ban\\s*quản\\s*lý\\s*chợ|sạp\\s*hàng|ki-ốt|chợ\\s*đầu\\s*mối)(?!.*(?:cháy|hỏa\\s*hoạn|ngập|lũ|bão|tốc\\s*mái|sập|tiếp\\s*tế))\\b',
    '\\b(?:trở\\s*lại\\s*làm\\s*việc|ngày\\s*làm\\s*việc\\s*đầu\\s*tiên|khai\\s*xuân|du\\s*xuân|nghỉ\\s*tết|lịch\\s*nghỉ|nghỉ\\s*lễ|nghỉ\\s*bù|đi\\s*làm\\s*lại)(?!.*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục))\\b',
    '\\b(?:đổi\\s*tên\\s*trường|thành\\s*lập\\s*trường|sáp\\s*nhập\\s*trường|giải\\s*thể\\s*trường|công\\s*bố\\s*quyết\\s*định)(?!.*(?:bão|lũ|sạt\\s*lở))\\b',
    '\\b(?:nhập\\s*cư|thẻ\\s*xanh|visa|thị\\s*thực|hồ\\s*sơ\\s*xin|lãnh\\s*sự\\s*quán|đại\\s*sứ\\s*quán)(?!.*(?:cứu\\s*trợ|bão|lũ|sơ\\s*tán|người\\s*việt))\\b',
    '\\b(?:giữ\\s*chức|bổ\\s*nhiệm|phê\\s*chuẩn|miễn\\s*nhiệm|trao\\s*quyết\\s*định|chức\\s*vụ|tân\\s*chủ\\s*tịch|tân\\s*bộ\\s*trưởng|nhân\\s*sự\\s*mới)(?!.*(?:chỉ\\s*đạo|kiểm\\s*tra|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:thực\\s*tập\\s*phương\\s*án|diễn\\s*tập\\s*khu\\s*vực|luyện\\s*tập\\s*chuyển\\s*trạng\\s*thái|hợp\\s*luyện|thao\\s*trường|bắn\\s*đạn\\s*thật)(?!.*(?:trong\\s*mưa\\s*bão|thực\\s*tế|cứu\\s*dân|lũ\\s*lụt|thiên\\s*tai|sạt\\s*lở))\\b',
    '\\b(?:chim|thú|động\\s*vật)\\s*(?:quý\\s*hiếm|hoang\\s*dã|sách\\s*đỏ|bảo\\s*tồn|thả\\s*về\\s*rừng|giao\\s*nộp|bắt\\s*được)\\b',
    '\\b(?:giải\\s*đấu\\s*esports|vòng\\s*bảng|vòng\\s*playoff|tuyển\\s*thủ\\s*chuyên\\s*nghiệp|binh\\s*đoàn|patch\\s*update|meta\\s*game|tướng\\s*mới|trang\\s*phục\\s*vĩnh\\s*viễn)\\b',
    '\\b(?:cải\\s*tạo\\s*nhà|sơn\\s*nhà|lát\\s*sàn|thiết\\s*kế\\s*nội\\s*thất|đồ\\s*gia\\s*dụng|tủ\\s*bếp|phòng\\s*khách\\s*đẹp|mẫu\\s*rèm\\s*cửa|giấy\\s*dán\\s*tường)\\b',
    '\\b(?:tập\\s*gym|bodybuilding|whey\\s*protein|creatine|giảm\\s*mỡ\\s*bụng|cơ\\s*bụng\\s*6\\s*múi|huấn\\s*luyện\\s*viên\\s*cá\\s*nhân|pt|chạy\\s*bộ\\s*mỗi\\s*ngày)\\b',
    '\\b(?:học\\s*bổng\\s*toàn\\s*phần|hội\\s*thảo\\s*quốc\\s*tế|tạp\\s*chí\\s*isi/scopus|công\\s*bố\\s*nghiên\\s*cứu|hệ\\s*đào\\s*tạo\\s*từ\\s*xa|văn\\s*bằng\\s*2|vừa\\s*học\\s*vừa\\s làm)\\b',
    '\\b(?:phí\\s*quản\\s*lý\\s*vận\\s*hành|bảo\\s*trì\\s*thang\\s*máy|hệ\\s*thống\\s*chiếu\\s*sáng|xử\\s*lý\\s*nước\\s*thải\\s*sinh\\s*hoạt|vệ\\s*sinh\\s*công\\s*nghiệp)\\b',
    '\\b(?:miss\\s*global|hoa\\s*hậu\\s*hoàn\\s*vũ|vương\\s*miện\\s*danh\\s*giá|nhan\\s*sắc\\s*thăng\\s*hạng|catwalk|trình\\s*diễn\\s*bikini|phần\\s*thi\\s*ứng\\s*xử|người\\s*đẹp\\s*biển)\\b',
    '\\b(?:resort\\s*5\\s*sao|biệt\\s*thự\\s*nghỉ\\s*dưỡng\\s*luxury|hạng\\s*thương\\s*gia|du\\s*thuyền\\s*triệu\\s*đô|trải\\s*nghiệm\\s*thượng\\s*lưu|dịch\\s*vụ\\s*chuẩn\\s*quốc\\s*tế)\\b',
    '\\b(?:xe\\s*điện\\s*thông\\s*minh|trạm\\s*sạc\\s*nhanh|pin\\s*lithium|phạm\\s*vi\\s*di\\s*chuyển|xe\\s*tự\\s*lái|adas|tự\\s*động\\s*hóa|triển\\s*lãm\\s*xe\\s*vms)\\b',
    '\\b(?:văn\\s*phòng\\s*cho\\s*thuê|co-working\\s*space|khu\\s*phức\\s*hợp|tiện\\s*ích\\s*all-in-one|tòa\\s*nhà\\s*thông\\s*minh|quản\\s*lý\\s*bất\\s*động\\s*sản)\\b',
    '\\b(?:đạo\\s*đức\\s*pháp\\s*luật|văn\\s*hóa\\s*ngành\\s*y|kỷ\\s*cương\\s*hành\\s*chính|tác\\s*phong\\s*công\\s*vụ|đổi\\s*mới\\s*sáng\\s*tạo|chuyển\\s*đổi\\s*số\\s*quốc\\s*gia)\\b',
    '\\b(?:hội\\s*thảo\\s*chuyên\\s*đề|tổng\\s*kết\\s*phong\\s*trào|thi\\s*đua\\s*ngành\\s*giáo\\s*dục|trao\\s*giải\\s*thưởng\\s*sáng\\s*tạo|triển\\s*khai\\s*nhiệm\\s*vụ\\s*trọng\\s*tâm)\\b',
    '\\b(?:tin\\s*buồn|lễ\\s*viếng|vô\\s*cùng\\s*thương\\s*tiếc|hưởng\\s*thọ|lễ\\s*truy\\s*điệu|an\\s*táng|phúng\\s*viếng|chia\\s*buồn\\s*cùng\\s*gia\\s*đình)\\b',
    '\\b(?:quên\\s*mật\\s*khẩu|mã\\s*otp|lỗi\\s*chuyển\\s*tiền|hạn\\s*mức\\s*giao\\s*dịch|quản\\s*lý\\s*chi\\s*tiêu|thanh\\s*toán\\s*hóa\\s*đơn|liên\\s*kết\\s*ngân\\s*hàng)\\b',
    '\\b(?:bảo\\s*trì\\s*cáp\\s*quang|đứt\\s*cáp|gói\\s*cước\\s*data|nạp\\s*thẻ\\s*điện\\s*thoại|thuê\\s*bao\\s*di\\s*động|chất\\s*lượng\\s*đường\\s*truyền|sim\\s*số\\s*đẹp)\\b',
    '\\b(?:diện\\s*tích\\s*sử\\s*dụng|hợp\\s*đồng\\s*đặt\\s*cọc|pháp\\s*lý\\s*dự\\s*án|tiến\\s*độ\\s*bàn\\s*giao|hoa\\s*hồng\\s*môi\\s*giới|tầng\\s*thanh\\s*khoản|nhà\\s*phố\\s*liền\\s*kề)\\b',
    '\\b(?:kinh\\s*phí\\s*nghiên\\s*cứu|xếp\\s*hạng\\s*đại\\s*học|chỉ\\s*số\\s*trích\\s*dẫn|đăng\\s*báo\\s*quốc\\s*tế|quỹ\\s*phát\\s*triển\\s*khoa\\s*học|nghiên\\s*cứu\\s*sinh\\s*tiến\\s*sĩ)\\b',
    '\\b(?:bán\\s*nhà\\s*chính\\s*chủ|hạ\\s*giá\\s*hết\\s*nấc|cắt\\s*lỗ\\s*sâu|vị\\s*trí\\s*đắc\\s*địa|sổ\\s*hồng\\s*trao\\s*tay|hỗ\\s*trợ\\s*vay\\s*vốn|kinh\\s*doanh\\s*đắc\\s*lợi|chủ\\s*ngộp|thu\\s*hồi\\s*vốn)\\b',
    '\\b(?:kết\\s*thúc\\s*phiên|sắc\\s*xanh\\s*lan\\s*tỏa|sắc\\s*đỏ\\s*bao\\s*trùm|v\\s*n\\s*index\\s*quay\\s*đầu|khối\\s*ngoại\\s*bán\\s*ròng|thanh\\s*khoản\\s*sụt\\s*giảm|nhóm\\s*cổ\\s*phiếu\\s*vốn\\s*hóa)\\b',
    '\\b(?:khoe\\s*dáng|xả\\s*kho\\s*ảnh|style\\s*cực\\s*chất|nhan\\s*sắc\\s*đời\\s*thực|gây\\s*sốt\\s*với\\s*bộ\\s*ảnh|lộ\\s*diện\\s*sau\\s*khi|phong\\s*cách\\s*thời\\s*thượng|gu\\s*thời\\s*trang)\\b',
    '\\b(?:mẹo\\s*vặt\\s*cuộc\\s*sống|cách\\s*chọn\\s*mua|review\\s*chân\\s*thực|kinh\\s*nghiệm\\s*chọn|top\\s*sản\\s*phẩm\\s*đáng\\s*mua|hướng\\s*dẫn\\s*chi\\s*tiết|bí\\s*quyết\\s*làm)\\b',
    '\\b(?:định\\s*giá\\s*tài\\s*sản|kê\\s*biên\\s*tài\\s*sản|thu\\s*hồi\\s*nợ|tín\\s*dụng\\s*đen|vay\\s*tiền\\s*nhanh|lãi\\s*suất\\s*thả\\s*nổi|đảo\\s*nợ)\\b',
    '\\b(?:dinh\\s*dưỡng|thực\\s*phẩm\\s*chức\\s*năng|vitamin|khoáng\\s*chất|tăng\\s*cường\\s*sức\\s*đề\\s*kháng|miễn\\s*dịch|giảm\\s*cân|làm\\s*đẹp|spa|thẩm\\s*mỹ|da\\s*liễu|nha\\s*khoa|đông\\s*y|thuốc\\s*nam|bài\\s*thuốc|thực\\s*đơn|mon\\s*ngon|đặc\\s*sản|ẩm\\s*thực|axit\\s*uric|tiểu\\s*đường|huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|ung\\s*thư|ruột\\s*kích\\s*thích|cúm\\s*mùa|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|ngộ\\s*độc\\s*thực\\s*phẩm|tỏi\\s*đen|kim\\s*tiền\\s*thảo|nghẹt\\s*mũi|kháng\\s*sinh|sống\\s*khỏe)(?!.*(?:cho|tại|vùng|cứu\\s*trợ|bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:hội\\s*nghị\\s* thượng\\s*đỉnh|G7|G20|ASEAN|APEC|UNESCO|WHO|UNICEF|WTO|NATO|liên\\s*hợp\\s*quốc|nghị\\s*quyết\\s*chung|tuyên\\s*bố\\s*chung)\\b',
    '\\b(?:khám\\s*nghiệm\\s*tử\\s*thi|pháp\\s*y|hung\\s* khí|tang\\s*vật\\s*vụ\\s*án|hồ\\s*sơ\\s*vụ\\s* án|lệnh\\s*truy\\s*nã|nghi\\s*phạm\\s*đang\\s*bỏ\\s*trốn|chứng\\s*cứ\\s*quan\\s*trọng)\\b',
    '\\b(?:x\\s*s\\s*m\\s*b|x\\s*s\\s*m\\s*n|x\\s*s\\s*m\\s*t|mega\\s*6/45|power\\s*6/55|max\\s*3d|giải\\s*jackpot|kết\\s*quả\\s*xổ\\s*số\\s*hôm\\s*nay)\\b',
    '\\b(?:golf|mma|ufc|boxing|muay\\s*thai|billiards|bi-a|võ\\s*tự\\s*do|sàn\\s*đấu\\s*rực\\s*lửa|thu\\s*phục|hạ\\s*gục\\s*đối\\s*thủ)\\b',
    '\\b(?:bạch\\s*dương|kim\\s*ngưu|song\\s*tử|cự\\s*giải|sư\\s*tử|xử\\s*nữ|thiên\\s*bình|thiên\\s*yết|hổ\\s*cáp|nhân\\s*mã|ma\\s*kết|bảo\\s*bình|song\\s*ngư)\\b',
    '\\b(?:nhìn\\s*lại|tổng\\s*kết|toàn\\s*cảnh|dấu\\s*ấn|tiêu\\s*điểm)\\s*(?:thế\\s*giới|năm\\s*20\\d{2}|kinh\\s*tế|thị\\s*trường|quốc\\s*tế)\\b',
    '\\bvòng\\s*xoáy\\s*(?:bất\\s*ổn|xung\\s*đột|bạo\\s*lực|chiến\\s*tranh|nợ\\s*nần|khủng\\s*hoảng)\\b',
    '\\b(?:bất\\s*ổn\\s*chính\\s*trị|đảo\\s*chính|biểu\\s*tình|nội\\s*chiến|xung\\s*đột\\s*sắc\\s*tộc)\\b',
    '\\b(?:chỉ\\s*số\\s*h-index|trích\\s*dẫn\\s*khoa\\s*học|bài\\s*báo\\s*quốc\\s*tế|phản\\s*biện\\s*kín|hội\\s*đồng\\s*chức\\s*danh\\s*giáo\\s*sư|hệ\\s*số\\s*tác\\s*động|impact\\s*factor)\\b',
    '\\b(?:gia\\s*phả|nhà\\s*thờ\\s*họ|giỗ\\s*tổ|tộc\\s*ước|đại\\s*hội\\s*dòng\\s*họ|con\\s*cháu\\s*hậu\\s*duệ|phụng\\s*thờ\\s*tổ\\s*tiên|lăng\\s*mộ\\s*dòng\\s*tộc)\\b',
    '\\b(?:máy\\s*c\\s*n\\s*c|máy\\s*cắt\\s*laser|máy\\s*chấn|máy\\s*tiện|máy\\s*phay|dây\\s*chuyền\\s*tự\\s*động\\s*hóa|robot\\s*công\\s*nghiệp|vật\\s*liệu\\s*composit)\\b',
    '\\b(?:thử\\s*nghiệm\\s*lâm\\s*sàng|biện\\s*pháp\\s*can\\s*thiệp|nội\\s*soi\\s*tiêu\\s*hóa|chụp\\s*m\\s*r\\s*i|cat\\s*scan|sinh\\s*thiết|kháng\\s*sinh\\s*đồ)\\b',
    '\\b(?:đồng\\s*tiền\\s*cổ|tem\\s*phi\\s*luật|sưu\\s*tầm\\s*đồ\\s*xưa|đồ\\s*gốm\\s*sứ|giá\\s*trị\\s*thẩm\\s*mỹ|nghệ\\s*nhuật\\s*sắp\\s*đặt)\\b',
    '\\b(?:gỗ\\s*veneer|acrylic|mdf|laminate|sàn\\s*gỗ\\s*công\\s*nghiệp|đồ\\s*gỗ\\s*nội\\s*thất|phụ\\s*kiện\\s*tủ\\s*bếp|đèn\\s*led\\s*trang\\s*trí)\\b',
    '\\b(?:thủy\\s*canh|khí\\s*canh|phân\\s*bón\\s*n\\s*p\\s*k|thuốc\\s*bảo\\s*vệ\\s*thực\\s*vật|giống\\s*cây\\s*lai|nuôi\\s*cấy\\s*mô|nhà\\s*màng|nhà\\s*lưới)\\b',
    '\\b(?:vận\\s*hành\\s*quy\\s*trình|tối\\s*ưu\\s*hệ\\s*thống|tiết\\s*kiệm\\s*chi\\s*phí|năng\\s*suất\\s*lao\\s*động|quản\\s*trị\\s*chuỗi\\s*cung\\s*ứng)\\b',
    '\\b(?:bảo\\s*hiểm\\s*y\\s*tế|bhyt|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|trục\\s*lợi\\s*bảo\\s*hiểm|rút\\s*tiền\\s*bảo\\s*hiểm|thẻ\\s*bảo\\s*hiểm|khám\\s*chữa\\s*bệnh\\s*bảo\\s*hiểm)\\b',
    '\\b(?:thuốc\\s*lá\\s*(?:lậu|nhập\\s*lậu|ngoại)|bao\\s*thuốc\\s*lá|tàng\\s*trữ\\s*thuốc\\s*lá|buôn\\s*bán\\s*hàng\\s*cấm)\\b',
    '\\b(?:mại\\s*dâm|mua\\s*bán\\s*dâm|cà\\s*phê\\s*chòi|kích\\s*dục|massage\\s*kích\\s*dục|tú\\s*bà|chứa\\s*mại\\s*dâm)\\b',
    '\\b(?:hàng\\s*lậu|hàng\\s*cấm|tàng\\s*trữ\\s*trái\\s*phép|vận\\s*chuyển\\s*trái\\s*phép\\s*chất\\s*ma\\s*túy|bắt\\s*quả\\s*tang\\s*vụ)\\b',
    '\\b(?:đánh\\s*bạc|sát\\s*phạt|tụ\\s*điểm\\s*đá\\s*gà|xóc\\s*đĩa|lô\\s*đề|ghi\\s*số\\s*đề|tổ\\s*chức\\s*đánh\\s*bạc)\\b',
    '\\b(?:trộm\\s*cắp|cướp\\s*giật|móc\\s*túi|đột\\s*nhập|phá\\s*khóa|trộm\\s*xe|cướp\\s*tài\\s*sản)\\b',
    '\\b(?:giết\\s*người|phân\\s*xác|phi\\s*tang|đâm\\s*chết|mâu\\s*thuẫn\\s*tình\\s*cảm|ghen\\s*tuông|hành\\s*hung|cố\\s*ý\\s*gây\\s*thương\\s*tích)\\b',
    '\\b(?:lừa\\s*đảo\\s*chiếm\\s*đoạt|giả\\s*danh\\s*công\\s*an|lừa\\s*đảo\\s*qua\\s*mạng|tín\\s*dụng\\s*đen|cho\\s*vay\\s*lãi\\s*nặng|bảng\\s*giá\\s*đất)\\b',
    '\\b(?:mã\\s*vạch|qr\\s*code|tem\\s*truy\\s*xuất|hệ\\s*thống\\s*erp|phần\\s*mềm\\s*quản\\s*lý|số\\s*hóa\\s*doanh\\s*nghiệp)\\b',
    '\\b(?:giá\\s*heo\\s*hơi|giá\\s*cà\\s*phê|giá\\s*hồ\\s*tiêu|giá\\s*cao\\s*su|giá\\s*sầu\\s*riêng|thương\\s*lá\\s*thu\\s*mua|vào\\s*vụ\\s*thu\\s*hoạch|vựa\\s*trái\\s*cây)\\b',
    '\\b(?:xo\\s*so|xổ\\s*số|vietlott|xsmb|xsmn|xsmt|kqxs|trúng\\s*số|giải\\s*thưởng\\s*lớn|độc\\s*đắc)\\b',
    '\\b(?:casino|sòng\\s*bạc|đánh\\s*bạc|cá\\s*cược|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề)\\b',
    '\\b(?:tử\\s*vi|cung\\s*hoàng\\s*đạo|con\\s*giáp|phong\\s*thủy|bói\\s*toán|tướng\\s*số|vận\\s*mệnh)\\b',
    '\\b(?:tam\\s*tai|năm\\s*tuổi|sao\\s*kế\\s*đô|vận\\s*hạn|cúng\\s*giải\\s*hạn|hóa\\s*giải\\s*vận\\s*đen|phong\\s*thủy\\s*cải\\s*vận|tử\\s*vi\\s*trọn\\s*đời)\\b',
    '\\b(?:Man\\s*Utd|Manchester\\s*United|Premier\\s*League|La\\s*Liga|Bundesliga|Serie\\s*A|Champions\\s*League)\\b',
    "\\bBulletin\\s*d'information\\b",
    '\\b(?:vóc\\s*dáng|sắc\\s*vóc|đường\\s*cong|eo\\s*thon|bí\\s*quyết\\s*giữ\\s*dáng|thời\\s*trang\\s*thảm\\s*đỏ|vẻ\\s*đẹp\\s*không\\s*tuổi)\\b',
    '\\b(?:lời\\s*bài\\s*hát|lyrics|hợp\\s*âm\\s*guitar|tab\\s*piano|phòng\\s*thu\\s*âm|kỹ\\s*thuật\\s*thanh\\s*nhạc|nhạc\\s*cụ\\s*chính\\s*hãng|vang\\s*số|loa\\s*kéo)\\b',
    '\\b(?:kích\\s*hoạt\\s*vneid|tài\\s*khoản\\s*vneid|vssid|bhxh|bảo\\s*hiểm\\s*xã\\s*hội|định\\s*danh\\s*điện\\s*tử|nộp\\s*phạt\\s*online|dịch\\s*vụ\\s*công\\s*trực\\s*tuyến|cổng\\s*dịch\\s*vụ\\s*công)\\b',
    '\\b(?:sửa\\s*chữa\\s*điện\\s*nước|thông\\s*tắc\\s*bể\\s*phốt|hút\\s*hầm\\s*cầu|thay\\s*vòi\\s*nước|lắp\\s*đặt\\s*camera|bảo\\s*trì\\s*điều\\s*hòa|vệ\\s*sinh\\s*máy\\s*giặt)\\b',
    '\\b(?:thanh\\s*lý\\s*giá\\s*rẻ|xả\\s*kho\\s*nghỉ\\s*bán|giày\\s*si\\s*tuyển|đồ\\s*cũ\\s*giá\\s*tốt|thu\\s*mua\\s*phế\\s*liệu|đồng\\s*nát|vựa\\s*ve\\s*chai|đổi\\s*cũ\\s*lấy\\s*mới)\\b',
    '\\b(?:hội\\s*người\\s*cao\\s*tuổi|hội\\s*cựu\\s*chiến\\s*binh|đại\\s*hội\\s*chi\\s*hội|phong\\s*trào\\s*văn\\s*nghệ|khiêu\\s*vũ\\s*dưỡng\\s*sinh|câu\\s*lạc\\s*bộ\\s*hưu\\s*trí)\\b',
    '\\b(?:mật\\s*ong\\s*rừng|rau\\s*sạch\\s*nhà\\s*trồng|nấm\\s*linh\\s*chi|nhân\\s*sâm|đông\\s*trùng\\s*hạ\\s*thảo|phòng\\s*tràn\\s*lan\\s*đột\\s*biến|cây\\s*cảnh\\s*giá\\s*trị)\\b',
    '\\b(?:hướng\\s*dẫn\\s*đăng\\s*ký|thủ\\s*tục\\s*sang\\s*tên|cấp\\s*đổi\\s*số\\s*đỏ|đính\\s*chính\\s*thông\\s*tin|tra\\s*cứu\\s*quy\\s*hoạch|hồ\\s*sơ\\s*địa\\s*chính)\\b',
    '\\b(?:chống\\s*bán\\s*phá\\s*giá|thuế\\s*tự\\s*vệ|biện\\s*pháp\\s*phòng\\s*vệ\\s*thương\\s*mại|fta|evfta|cptpp|rcep|quy\\s*tắc\\s*xuất\\s*xứ|phòng\\s*thương\\s*mại)\\b',
    '\\b(?:quyết\\s*toán\\s*thuế|thuế\\s*thu\\s*nhập\\s*cá\\s*nhân|tncn|hoàn\\s*thuế\\s*gtgt|hóa\\s*đơn\\s*điện\\s*tử|kiểm\\s*toán\\s*nhà\\s*nước|vụ\\s*ngân\\s*sách|kế\\s*hoạch\\s*tài\\s*chính)\\b',
    '\\b(?:công\\s*nghệ\\s*nano|vật\\s*lý\\s*lượng\\s*tử|máy\\s*tính\\s*lượng\\s*tử|vật\\s*liệu\\s*siêu\\s*dẫn|graphene|in\\s*3d|chế\\s*tạo\\s*nhanh|vi\\s*mạch\\s*bán\\s*dẫn)\\b',
    '\\b(?:bàn\\s*phím\\s*cơ|keycap|switch|lube\\s*phím|hi-fi|dac/amp|đĩa\\s*than|bút\\s*máy|mực\\s*viết\\s*máy|sưu\\s*tầm\\s*bút|ngòi\\s*bút|viết\\s*lách)\\b',
    '\\b(?:đhđcđ|bải\\s*miễn\\s*hđqt|thành\\s*viên\\s*độc\\s*lập|nhà\\s*đầu\\s*tư\\s*chiến\\s*lược|m&a|sáp\\s*nhập\\s*doanh\\s*nghiệp)\\b',
    '\\b(?:real\\s*madrid|man\\s*utd|manchester\\s*city|liverpool|arsenal|barca|bayern\\s*munich|psg|chuyển\\s*nhượng\\s*cầu\\s*thủ|hợp\\s*đồng\\s*bom\\s*tấn|champions\\s*league|premiere\\s*league|v-league|v\\s*league|ngoại\\s*hạng\\s*anh|league\\s*1|la\\s*liga|serie\\s*a|bundesliga|công\\s*phượng|quang\\s*hải|tiến\\s*linh|văn\\s*toàn|đội\\s*tuyển\\s*bóng\\s*đá)\\b',
    '\\b(?:nhạc\\s*trẻ|k-pop|v-pop|show\\s*diễn|lưu\\s*diễn\\s*quốc\\s*tế|world\\s*tour|lightstick|comeback\\s*ấn\\s*tượng|debut\\s*thành\\s*công|bảng\\s*xếp\\s*hạng\\s*âm\\s*nhạc)\\b',
    '\\b(?:tự\\s*do\\s*tài\\s*chính|thu\\s*nhập\\s*thụ\\s*động|khai\\s*phá\\s*tiềm\\s*năng|vùng\\s*an\\s*toàn|chữa\\s*lành\\s*tâm\\s*hồn|thiền\\s*định\\s*mỗi\\s*ngày)\\b',
    '\\b(?:cắt\\s*mí|botox|trẻ\\s*hóa\\s*làn\\s*da|spa\\s*làm\\s*đẹp|viện\\s*thẩm\\s*mỹ)\\b',
    '\\b(?:sp-[\\d\\w]+|mã\\s*giảm\\s*giá|voucher|coupon|deal\\s*sốc|săn\\s*sale|livestream\\s*bán\\s*hàng|tiktok\\s*shop|shopee\\s*live|lazada\\s*sale)\\b',
    '\\b(?:bí\\s*kíp|kinh\\s*nghiệm|mẹo)\\s*(?:tìm|thuê|chọn|mua|bán)\\s*(?:phòng\\s*trọ|nhà\\s*trọ|căn\\s*hộ|chung\\s*cư|nhà\\s*đất)\\b',
    '\\b(?:tâm\\s*sự|ngoại\\s*tình|người\\s*thứ\\s*ba|đánh\\s*ghen|bí\\s*mật\\s*phòng\\s*the|chuyện\\s*thầm\\s*kín|bạn\\s*đời|ly\\s*hôn|kết\\s*hôn|hẹn\\s*hò)\\b',
    '\\b(?:review\\s*sản\\s*phẩm|đánh\\s*giá\\s*chi\\s*tiết|trên\\s*tay|mở\\s*hộp|unboxing|so\\s*sánh\\s*hiệu\\s*năng|trải\\s*nghiệm\\s*người\\s*dùng)\\b',
    '\\b(?:ra\\s*mắt\\s*iphone|samsung\\s*galaxy|macbook|ios\\s*(?:update|\\d+)|android\\s*\\d+|snapdragon|dimensity|xe\\s*điện\\s*vinfast|lãi\\s*suất\\s*kép|máy\\s*tính\\s*bảng|laptop|tai\\s*nghe\\s*bluetooth)\\b',
    '\\b(?:chứng\\s*khoán\\s*phái\\s*sinh|thị\\s*trường\\s*chứng\\s*khoán|phiên\\s*giao\\s*dịch|khớp\\s*lệnh|thanh\\s*khoản|nhà\\s*đầu\\s*tư\\s*nước\\s*ngoài)\\b',
    '\\b(?:luyện\\s*thi\\s*ielts|toeic|toefl|ngữ\\s*pháp\\s*tiếng\\s*anh|học\\s*từ\\s*vựng|phương\\s*pháp\\s*ghi\\s*nhớ|du\\s*học\\s*sinh|trao\\s*đổi\\s*sinh\\s*viên)\\b',
    '\\b(?:phát\\s*trực\\s*tiếp|kol|koc|người\\s*có\\s*sức\\s*ảnh\\s*hưởng|viral\\s*clip|drama\\s*mới|bóc\\s*phốt|hóng\\s*biến|đu\\s*trend|thử\\s*thách\\s*24h)\\b',
    '\\b(?:cryptocurrency|sàn\\s*giao\\s*dịch\\s*số|n\\s*f\\s*t|vốn\\s*hóa\\s*thị\\s*trường\\s*số|công\\s*nghệ\\s*chuỗi\\s*khối)\\b',
    '\\b(?:nghị\\s*quyết\\s*hđqt|biên\\s*bản\\s*họp|chương\\s*trình\\s*nghị\\s*sự|quy\\s*hoạch\\s*phân\\s*khu|điều\\s*chỉnh\\s*quy\\s*hoạch|chủ\\s*trương\\s*đầu\\s*tư|thẩm\\s*định\\s*giá\\s*tài\\s*sản|nghĩa\\s*vụ\\s*thuế)\\b',
    '\\b(?:định\\s*hướng\\s*phát\\s*triển|tầm\\s*nhìn\\s*2030|chiến\\s*lược\\s*phát\\s*triển|chuyển\\s*đổi\\s*số\\s*vận\\s*hành|hệ\\s*sinh\\s*thái\\s*khởi\\s*nghiệp)\\b',
    '\\b(?:tuyên\\s*truyền\\s*phổ\\s*biến|giáo\\s*dục\\s*pháp\\s*luật|hưởng\\s*ứng\\s*phong\\s*trào|tổng\\s*kết\\s*khen\\s*thưởng|khen\\s*ngợi\\s*biểu\\s*dương)(?!.*(?:cứu\\s*trợ|khắc\\s*phục|phòng\\s*chống\\s*thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:mẹ\\s*chồng\\s*nàng\\s*dâu|tiểu\\s*tam|giật\\s*chồng|sống\\s*thử|ly\\s*hôn\\s*nghìn\\s*tỷ|tranh\\s*chấp\\s*quyền\\s*nuôi\\s*con|mâu\\s*thuẫn\\s*gia\\s*đình|ngoại\\s*tình\\s*bị\\s*phát\\s*hiện)\\b',
    '\\b(?:lừa\\s*đảo\\s*chiếm\\s*đoạt|mã\\s*độc\\s*tấn\\s*công|phần\\s*mềm\\s*gián\\s*điệp|ransomware|truy\\s*cập\\s*trái\\s*phép|an\\s*toàn\\s*thông\\s*tin\\s*mạng|bảo\\s*mật\\s*đa\\s*lớp|xác\\s*thực\\s*hai\\s*yếu\\s*tố)\\b',
    '\\b(?:dịch\\s*bệnh\\s*gia\\s*súc|lở\\s*mồm\\s*long\\s*móng|tai\\s*xanh|dịch\\s*tả\\s*lợn\\s*châu\\s*phi|thuốc\\s*thú\\s*y|kháng\\s*sinh\\s*cho\\s*vật\\s*nuôi|thức\\s*ăn\\s*chăn\\s*nuôi|kỹ\\s*thuật\\s*vỗ\\s*béo)\\b',
    '\\b(?:vietgap|globalgap|haccp|chỉ\\s*dẫn\\s*địa\\s*lý|thương\\s*hiệu\\s*quốc\\s*gia|ocop|mỗi\\s*xã\\s*một\\s*sản\\s*phẩm)\\b',
    '\\b(?:đăng\\s*ký\\s*thương\\s*hiệu|sở\\s*hữu\\s*công\\s*nghiệp|kiểu\\s*dáng\\s*độc\\s*quyền|sách\\s*trắng|báo\\s*cáo\\s*thường\\s*niên|đại\\s*hội\\s*thành\\s*viên|vốn\\s*góp)\\b',
    '\\b(?:đại\\s*hội\\s*đảng|bầu\\s*cử\\s*quốc\\s*hội|hội\\s*nghị\\s*trung\\s*ương|bổ\\s*nhiệm\\s*cán\\s*bộ|luân\\s*chuyển\\s*nhân\\s*sự|kỷ\\s*luật\\s*đảng|khai\\s*trừ\\s*đảng)\\b',
    '\\b(?:trao\\s*huy\\s*hiệu\\s*đảng|huân\\s*chương\\s*lao\\s*động|cờ\\s*thi\\s*đua\\s*chính\\s*phủ|bằng\\s*khen\\s*thủ\\s*tướng|anh\\s*hùng\\s*lao\\s*động)\\b',
    '\\b(?:tiếp\\s*xúc\\s*cử\\s*tri|thảo\\s*luận\\s*tại\\s*tổ|chất\\s*vấn\\s*bộ\\s*trưởng|phiên\\s*họp\\s*thường\\s*kỳ|thông\\s*qua\\s*nghị\\s*quyết|lấy\\s*phiếu\\s*tín\\s*nhiệm)\\b',
    '\\b(?:chúc\\s*mừng\\s*năm\\s*mới|thư\\s*chúc\\s*tết|lời\\s*kêu\\s*gọi\\s*thi\\s*đua|thăm\\s*hỏi\\s*tặng\\s*quà|dâng\\s*hoa\\s*viếng|tưởng\\s*niệm\\s*các\\s*anh\\s*hùng)\\b',
    '\\b(?:đồng\\s*bào\\s*công\\s*giáo|đồng\\s*bào\\s*có\\s*đạo|chức\\s*sắc\\s*tôn\\s*giáo|cơ\\s*sở\\s*tôn\\s*giáo|khối\\s*đại\\s*đoàn\\s*kết)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|sập|tốc\\s*mái|hư\\s*hỏng|chia\\s*sẻ|ủng\\s*hộ))\\b',
    '\\b(?:hoàn\\s*thiện\\s*pháp\\s*lý|hành\\s*lang\\s*pháp\\s*lý|văn\\s*bản\\s*quy\\s*phạm|tư\\s*vấn\\s*pháp\\s*lý|trợ\\s*giúp\\s*pháp\\s*lý|cải\\s*cách\\s*tư\\s*pháp)(?!.*(?:bão|lũ))\\b',
    '\\b(?:phát\\s*triển\\s*bứt\\s*phá|tạo\\s*đà\\s*tăng\\s*trưởng|kịch\\s*bản\\s*tăng\\s*trưởng|mục\\s*tiêu\\s*tăng\\s*trưởng|nền\\s*tảng\\s*số)(?!.*(?:bão|lũ|khắc\\s*phục|phòng\\s*chống))\\b',
    '\\b(?:container\\s*nông\\s*sản|xe\\s*chở\\s*nông\\s*sản|ùn\\s*ứ\\s*cửa\\s*khẩu|thông\\s*quan\\s*hàng\\s*hóa|xuất\\s*nhập\\s*khẩu)(?!\\s*(?:do|tại)\\s*(?:bão|lũ|mưa))\\b',
    '\\b(?:chấn\\s*thương\\s*(?:cơ|gân|sụn|dây\\s*chằng|mắt\\s*cá|đầu\\s*gối)|gãy\\s*chân\\s*trong\\s*thi\\s*đấu|chấn\\s*thương\\s*khi\\s*tập\\s*luyện|phục\\s*hồi\\s*chấn\\s*thương)\\b',
    '\\b(?:mô\\s*hình\\s*sinh\\s*kế|hỗ\\s*trợ\\s*sinh\\s*kế|chuyển\\s*đổi\\s*sinh\\s*kế|sinh\\s*kế\\s*bền\\s*vững)(?!.*(?:bão|lũ|thiên\\s*tai|khôi\\s*phục|phục\\s*hồi|hậu\\s*quả|vùng\\s*un|vùng\\s*ngập))\\b',
    '\\b(?:buộc\\s*thực\\s*hiện\\s*biện\\s*pháp\\s*khắc\\s*phục\\s*hậu\\s*quả|xử\\s*phạt\\s*vi\\s*phạm\\s*hành\\s*chính|nghiệm\\s*thu\\s*công\\s*trình|khai\\s*thác\\s*khoáng\\s*sản\\s*trái\\s*phép)\\b',
    '\\b(?:hiến\\s*máu\\s*nhân\\s*đạo|hành\\s*trình\\s*đỏ|giọt\\s*máu\\s*nghĩa\\s*tình|ngân\\s*hàng\\s*máu|tình\\s*nguyện\\s*viên\\s*hiến\\s*máu)\\b',
    '\\b(?:khắc\\s*phục\\s*hậu\\s*quả\\s*vụ\\s*cháy|khắc\\s*phục\\s*hậu\\s*quả\\s*tai\\s*nạn|điều\\s*tra\\s*nguyên\\s*nhân\\s*vụ\\s*tai\\s*nạn|khám\\s*nghiệm\\s*hiện\\s*trường\\s*vụ\\s*cháy)\\b',
    '\\b(?:nghệ\\s*nhân\\s*ưu\\s*tú|nghệ\\s*nhân\\s*nhân\\s*dân|bảo\\s*tồn\\s*di\\s*sản|văn\\s*hóa\\s*phi\\s*vật\\s*thể|làng\\s*nghề\\s*truyền\\s*thống|sản\\s*phẩm\\s*ocop)\\b',
    '\\b(?:mời\\s*bạn\\s*xem\\s*thêm|tin\\s*liên\\s*quan|bài\\s*viết\\s*cùng\\s*chủ\\s*đề|xem\\s*thêm\\s*vụ\\s*việc|tin\\s*nóng\\s*trong\\s*ngày)\\b',
    '\\b(?:đăng\\s*ký\\s*tư\\s*vấn|liên\\s*hệ\\s*quảng\\s*cáo|hợp\\s*tác\\s*truyền\\s*thông|phòng\\s*kinh\\s*doanh|bản\\s*quyền\\s*thuộc\\s*về)\\b',
    '\\b(?:giải\\s*mã\\s*gen|xét\\s*nghiệm\\s*adn|công\\s*nghệ\\s*gen|di\\s*truyền\\s*học|bản\\s*đồ\\s*gen)\\b',
    '\\b(?:kỷ\\s*niệm\\s*\\d+\\s*năm\\s*thành\\s*lập|ngày\\s*truyền\\s*thống|đại\\s*hội\\s*đại\\s*biểu|văn\\s*kiện\\s*đại\\s*hội|báo\\s*cáo\\s*chính\\s*trị|lễ\\s*báo\\s*công|viếng\\s*lăng\\s*chủ\\s*tịch|dâng\\s*hương\\s*tưởng\\s*niệm)(?!.*(?:nạn\\s*nhân|người\\s*tử\\s*vong|đồng\\s*bào|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:thực\\s*tế\\s*ảo|v\\s*r|a\\s*r|metaverse|thị\\s*kính|tay\\s*cầm\\s*điều\\s*khiển|không\\s*gian\\s*số\\s*3d|mô\\s*phỏng\\s*hình\\s*ảnh|kính\\s*thông\\s*minh)\\b',
    '\\b(?:nhịn\\s*ăn\\s*gián\\s*đoạn|chế\\s*độ\\s*ăn\\s*keto|thực\\s*phẩm\\s*bảo\\s*vệ\\s*sức\\s*khỏe|vi\\s*chất\\s*dinh\\s*dưỡng|eo\\s*thon\\s*dáng\\s*đẹp)\\b',
    '\\b(?:huấn\\s*luyện\\s*chó|trại\\s*chó\\s*giống|thú\\s*cưng\\s*độc\\s*lạ|phục\\s*chế\\s*xe\\s*cổ|độ\\s*xe\\s*chuyên\\s*nghiệp|hệ\\s*thống\\s*âm\\s*thanh\\s*analog|băng\\s*cối|âm\\s*thanh\\s*trung\\s*thực)\\b',
    '\\b(?:triển\\s*khai\\s*nghị\\s*quyết|quán\\s*triệt\\s*tư\\s*tưởng|vận\\s*động\\s*quần\\s*chúng|xây\\s*dựng\\s*nông\\s*thôn\\s*mới|phong\\s*trào\\s*toàn\\s*dân|đoàn\\s*kết\\s*xây\\s*dựng\\s*đời\\s*sống)\\b',
    '\\b(?:dự\\s*án\\s*luật|thông\\s*cáo\\s*báo\\s*chí|kỳ\\s*họp\\s*thứ|họp\\s*báo\\s*thường\\s*kỳ|quốc\\s*hội\\s*khóa|đoàn\\s*đại\\s*biểu|hđnd\\s*tỉnh|ubnd\\s*tỉnh|văn\\s*phòng\\s*chính\\s*phủ)(?!.*(?:chỉ\\s*đạo|khẩn\\s*cấp|công\\s*điện|bão|lũ|thiên\\s*tai|PCTT|MARD|cứu\\s*trợ))\\b',
    '\\b(?:lấy\\s*ý\\s*kiến\\s*nhân\\s*dân|tiếp\\s*xúc\\s*cử\\s*tri|báo\\s*cáo\\s*chính\\s*trị|nghị\\s*quyết\\s*đại\\s*hội|quyết\\s*định\\s*ban\\s*hành|kế\\s*hoạch\\s*tuyên\\s*truyền)\\b',
    '\\b(?:độc\\s*lập\\s*tự\\s*do\\s*hạnh\\s*phúc|cộng\\s*hòa\\s*xã\\s*hội\\s*chủ\\s*nghĩa\\s*việt\\s*nam|số\\s*:\\s*\\d+/kh-|số\\s*:\\s*\\d+/qđ-)(?!.*(?:thiên\\s*tai|bão|lũ|sạt\\s*lở|khắc\\s*phục|hỗ\\s*trợ|kinh\\s*phí))\\b',
    '\\b(?:lễ\\s*ăn\\s*hỏi|rước\\s*dâu|tiệc\\s*cưới|mừng\\s*thọ|lễ\\s*vu\\s*lan|phật\\s*đản|phục\\s*sinh|quà\\s*tặng\\s*ý\\s*nghĩa|lời\\s*chúc\\s*hay)\\b',
    '\\b(?:sự\\s*thật\\s*ít\\s*ai\\s*biết|cảnh\\s*báo\\s*từ\\s*chuyên\\s*gia|giải\\s*quyết\\s*dứt\\s*điểm|dấu\\s*hiệu\\s*nhận\\s*biết|lời\\s*khuyên\\s*từ\\s*bác\\s*sĩ|phương\\s*pháp\\s*tự\\s*nhiên|thông\\s*tin\\s*sai\\s*lệch|kiểm\\s*chứng\\s*sự\\s*thật)\\b',
    '\\b(?:tất\\s*toán\\s*tài\\s*khoản|đáo\\s*hạn\\s*thẻ|phí\\s*duy\\s*trì|hạn\\s*mức\\s*thanh\\s*toán|bảo\\s*hiểm\\s*nhân\\s*thọ|quyền\\s*lợi\\s*bảo\\s*hiểm|người\\s*được\\s*thụ\\s*hưởng|bồi\\s*thường\\s*hợp\\s*đồng)(?!.*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:ưu\\s*đãi\\s*độc\\s*quyền|giảm\\s*giá\\s*sốc|khuyến\\s*mãi\\s*khủng|giờ\\s*vàng\\s*giá\\s*tốt|quà\\s*tặng\\s*hấp\\s*dẫn|số\\s*lượng\\s*có\\s*hạn|đặt\\s*hàng\\s*ngay|freeship)\\b',
    '\\b(?:xử\\s*phạt\\s*vi\\s*phạm\\s*hành\\s*chính|tạm\\s*giữ\\s*phương\\s*tiện|nồng\\s*độ\\s*cồn|vi\\s*phạm\\s*tốc\\s*độ|phí\\s*đường\\s*bộ)\\b',
    '\\b(?:biển\\s*số\\s*định\\s*danh|đăng\\s*ký\\s*xe|sang\\s*tên\\s*chính\\s*chủ|biển\\s*số\\s*đẹp|đấu\\s*giá\\s*biển\\s*số)\\b',
    '\\b(?:sửa\\s*bình\\s*nóng\\s*lạnh|chống\\s*thấm\\s*dột|sửa\\s*mái\\s*tôn|thông\\s*tắc\\s*cống|hút\\s*bể\\s*phốt|vệ\\s*sinh\\s*điều\\s*hòa|bảo\\s*dưỡng\\s*máy\\s*giặt|lắp\\s*mạng\\s*internet)\\b',
    '\\b(?:n\\s*b\\s*a|m\\s*l\\s*b|n\\s*f\\s*l|super\\s*bowl|grand\\s*slam|wimbledon|roland\\s*garros|u\\s*s\\s*open|australian\\s*open|giải\\s*quần\\s*vợt|bóng\\s*rổ\\s*nhà\\s*nghề)\\b',
    "\\b(?:christie's|sotheby's|nhà\\s*đấu\\s*giá\\s*danh\\s*tiếng|tranh\\s*sơn\\s*mài|khảm\\s*tam\\s*khí|gỗ\\s*thủy\\s*tùng|trầm\\s*hương\\s*tự\\s*nhiên|kỳ\\s*nam|mộc\\s*hương|đồ\\s*gỗ\\s*mỹ\\s*nghệ)\\b",
    '\\b(?:phần\\s*mềm\\s*kế\\s*toán|phần\\s*mềm\\s*nhân\\s*sự|quản\\s*lý\\s*kho\\s*hàng|tối\\s*ưu\\s*vận\\s*hành|giải\\s*pháp\\s*doanh\\s*nghiệp|năng\\s*suất\\s*vượt\\s*trội)\\b',
    '\\b(?:chương\\s*trình\\s*liên\\s*kết\\s*đào\\s*tạo|trao\\s*bằng\\s*tốt\\s*nghiệp|lễ\\s*khai\\s*giảng\\s*năm\\s*học|hiệu\\s*trưởng\\s*nhà\\s*trường|phòng\\s*giáo\\s*dục\\s*đào\\s*tạo)\\b',
    '\\b(?:lễ\\s*tân\\s*gia|vàng\\s*cưới|phong\\s*bì\\s*mừng|lễ\\s*dạm\\s*ngõ|tiệc\\s*thôi\\s*nôi|đầy\\s*tháng|kỷ\\s*niệm\\s*ngày\\s*cưới|đội\\s*bê\\s*tráp)\\b',
    '\\b(?:black\\s*friday|cyber\\s*monday|lazada\\s*birthday|shopee\\s*sale|siêu\\s*sale\\s*\\d+/\\d+|ngày\\s*hội\\s*mua\\s*sắm|mã\\s*giảm\\s*giá|hoàn\\s*tiền\\s*max)\\b',
    '\\b(?:gaslighting|mối\\s*quan\\s*hệ\\s*độc\\s*hại|trầm\\s*cảm\\s*sau\\s*sinh|rối\\s*loạn\\s*lo\\s*âu|liệu\\s*pháp\\s*tâm\\s*lý|tư\\s*vấn\\s*trị\\s*liệu)\\b',
    '\\b(?:bạo\\s*lực\\s*gia\\s*đình|bình\\s*đẳng\\s*giới|phòng\\s*chống\\s*bạo\\s*lực|tháng\\s*hành\\s*động|mít\\s*tinh\\s*hưởng\\s*ứng|ngày\\s*gia\\s*đình\\s*việt\\s*nam)\\b',
    '\\b(?:hiv/aids|thuốc\\s*arv|điều\\s*trị\\s*nghiện|cai\\s*nghiện\\s*ma\\s*túy|tệ\\s*nạn\\s*xã\\s*hội|trung\\s*tâm\\s*cai\\s*nghiện)\\b',
    '\\b(?:linh\\s*kiện\\s*máy\\s*tính|card\\s*đồ\\s*họa|r\\s*t\\s*x|g\\s*t\\s*x|r\\s*a\\s*m|s\\s*s\\s*d|ổ\\s*cứng\\s*di\\s*động|nguồn\\s*máy\\s*tính|tản\\s*nhiệt\\s*nước)\\b',
    '\\b(?:thời\\s*điểm\\s*vàng|cơ\\s*hội\\s*có\\s*một\\s*không\\s*hai|nhận\\s*ngay\\s*ưu\\s*đãi|đừng\\s*bỏ\\s*lỡ|đăng\\s*ký\\s*ngay)\\b',
    '\\b(?:du\\s*lịch\\s*tâm\\s*linh|hành\\s*hương|chùa\\s*tam\\s*chúc|bái\\s*đính|đại\\s*nam|quần\\s*thể\\s*danh\\s*thắng|di\\s*tích\\s*tâm\\s*linh|khu\\s*nghỉ\\s*dưỡng\\s*sinh\\s*thái)\\b',
    '\\b(?:rolex|patek\\s*philippe|audemars\\s*piguet|hublot|omega|thương\\s*hiệu\\s*đồng\\s*hồ|mặt\\s*số|bộ\\s*chuyển\\s*động|trữ\\s*cót|phiên\\s*bản\\s*giới\\s*hạn)\\b',
    '\\b(?:burnout|quiet\\s*quitting|work-life\\s*balance|hybrid\\s*work|chảy\\s*máu\\s*chất\\s*xám|nhân\\s*sự\\s*chủ\\s*chốt|môi\\s*trường\\s*làm\\s*việc\\s*lý\\s*tưởng)\\b',
    '\\b(?:ngành\\s*công\\s*nghiệp\\s*f&b|xu\\s*hướng\\s*tiêu\\s*dùng|chuỗi\\s*cung\\s*ứng\\s*toàn\\s*cầu|chi\\s*phí\\s*vận\\s*hành|ký\\s*kết\\s*hợp\\s*tác)\\b',
    '\\b(?:oecd|brics|asml|t\\s*s\\s*m\\s*c|nvidia|apple\\s*intelligence|openai|chatgpt|mô\\s*hình\\s*ngôn\\s*ngữ\\s*lớn|l\\s*l\\s*m)\\b',
    '\\b(?:du\\s*thuyền\\s*hạng\\s*sang|princess\\s*yachts|sunseeker|viking\\s*yachts|bến\\s*du\\s*thuyền|hàng\\s*không\\s*tư\\s*nhân|chuyên\\s*cơ\\s*riêng|gulfstream|bombardier)\\b',
    '\\b(?:đoàn\\s*luật\\s*sư|liên\\s*đoàn\\s*luật\\s*sư|quy\\s*tắc\\s*đạo\\s*đức\\s*nghề\\s*nghiệp|kỷ\\s*luật\\s*luật\\s*sư|tư\\s*vấn\\s*pháp\\s*lý\\s*doanh\\s*nghiệp|hợp\\s*quy\\s*pháp\\s*luật)\\b',
    '\\b(?:dòng\\s*vốn\\s*ngoại|chu\\s*kỳ\\s*kinh\\s*tế|điểm\\s*đảo\\s*chiều|lạm\\s*phát\\s*mục\\s*tiêu|nới\\s*lỏng\\s*tiền\\s*tệ|thắt\\s*chặt\\s*chi\\s*tiêu|ngân\\s*sách\\s*quốc\\s*gia)\\b',
    '\\b(?:phụ\\s*gia\\s*thực\\s*phẩm|chất\\s*bảo\\s*quản|tiêu\\s*chuẩn\\s*vệ\\s*sinh\\s*kỹ\\s*thuật)\\b',
    '\\b(?:mở\\s*bán|căn\\s*hộ\\s*cao\\s*cấp|shophouse|liền\\s*kề|biệt\\s*thự\\s*song\\s*lập|không\\s*gian\\s*sống\\s*đẳng\\s*cấp|vị\\s*trí\\s*vàng|sinh\\s*lời\\s*cao|sổ\\s*đỏ\\s*trao\\s*tay|nhận\\s*nhà\\s*ngay|tiến\\s*độ\\s*thanh\\s*toán|hỗ\\s*trợ\\s*lãi\\s*suất|bất\\s*động\\s*sản\\s*nghỉ\\s*dưỡng)\\b',
    '\\b(?:kèo\\s*bóng|soi\\s*kèo|tỷ\\s*lệ\\s*cược|nhà\\s*cái|ku\\s*casino|kubet|win79|go88|nhận\\s*định\\s*trận\\s*đấu|tỷ\\s*lệ\\s*kèo|soi\\s*cầu|lô\\s*đề|nổ\\s*hũ|bắn\\s*cá|game\\s*bài|tiến\\s*lên\\s*miền\\s*nam|đá\\s*gà|xóc\\s*đĩa|tài\\s*xỉu|b29|bet88)\\b',
    '\\b(?:định\\s*hướng\\s*giáo\\s*dục\\s*mầm\\s*non|phương\\s*pháp\\s*montessori|reggio\\s*emilia|steam|giáo\\s*dục\\s*trải\\s*nghiệm)\\b',
    '\\b(?:cải\\s*lương|hát\\s*tuồng|hát\\s*chèo|dân\\s*ca\\s*quan\\s*họ|đờn\\s*ca\\s*tài\\s*tử|văn\\s*hóa\\s*phi\\s*vật\\s*thể|nghệ\\s*thuật\\s*truyền\\s*thống|nghệ\\s*nhân\\s*nhân\\s*dân)\\b',
    '\\b(?:phân\\s*bón\\s*lá|kỹ\\s*thuật\\s*chiết\\s*cành|ghép\\s*mắt|cây\\s*ăn\\s*trái|vườn\\s*cây\\s*ăn\\s*quả|năng\\s*suất\\s*vụ\\s*mùa|phòng\\s*trừ\\s*sâu\\s*bệnh)\\b',
    '\\b(?:tranh\\s*chấp\\s*bản\\s*quyền|vi\\s*phạm\\s*sáng\\s*chế|kiện\\s*tụng\\s*bằng\\s*sáng\\s*chế|tác\\s*quyền\\s*âm\\s*nhạc|v\\s*c\\s*p\\s*m\\s*c|độc\\s*quyền\\s*thương\\s*hiệu)\\b',
    '\\b(?:thẩm\\s*định\\s*viên|đấu\\s*giá\\s*viên|công\\s*chứng\\s*viên|thừa\\s*phát\\s*lại|văn\\s*phòng\\s*luật|hành\\s*nghề\\s*y\\s*dược)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*ngành|quy\\s*chuẩn\\s*kỹ\\s*thuật|nghiệm\\s*thu\\s*hoàn\\s*thành|bàn\\s*giao\\s*công\\s*trình|nhà\\s*thầu\\s*phụ|liên\\s*danh\\s*nhà\\s*thầu)\\b',
    '\\b(?:blue\\s*origin|tên\\s*lửa\\s*đẩy\\s*(?!\\s*tấn\\s*công)|vệ\\s*tinh\\s*viễn\\s*thông|trạm\\s*vũ\\s*trụ|thiên\\s*văn\\s*học|kính\\s*viễn\\s*vọng)\\b',
    '\\b(?:lệnh\\s*trừng\\s*phạt|cấm\\s*vận\\s*kinh\\s*tế|phong\\s*tỏa\\s*tài\\s*sản\\s*quốc\\s*tế|trừng\\s*phạt\\s*ngoại\\s*giao|trục\\s*xuất\\s*nhà\\s*ngoại\\s*giao|quan\\s*hệ\\s*song\\s*phương)\\b',
    '\\b(?:olympic|asiad|paragames|đại\\s*hội\\s*thể\\s*thao|huấn\\s*luyện\\s*viên\\s*trưởng|đội\\s*tuyển\\s*quốc\\s*gia|liên\\s*đoàn\\s*bóng\\s*đá|v\\s*f\\s*f)\\b',
    '\\b(?:xổ\\s*số|k\\s*q\\s*x\\s*s|vietlott|lô\\s*đề|soi\\s*cầu|vé\\s*số|thưởng\\s*độc\\s*đắc|trúng\\s*giải\\s*đặc\\s*biệt)\\b',
    '\\b(?:10|5|event|sự\\s*kiện)\\s*nổi\\s*bật(?:\\s*của\\s*tỉnh|\\s*trong\\s*năm|\\s*địa\\s*phương)\\b',
    '\\b(?:thành\\s*tựu|kết\\s*quả)\\s*nổi\\s*bật\\b',
    '\\b(?:phấn\\s*đấu|mục\\s*tiêu|kế\\s*hoạch)\\s*tăng\\s*trưởng\\b',
    '\\btăng\\s*trưởng\\s*\\d+\\s*con\\s*số\\b',
    '\\b(?:đua\\s*thuyền|rowing|canoeing|đấu\\s*kiếm|fencing|cử\\s*tạ|bắn\\s*súng|thể\\s*dục\\s*dụng\\s*cụ|aerobic|điền\\s*kinh|nhảy\\s*cao|nhảy\\s*xa)\\b',
    '\\b(?:kỷ\\s*lục\\s*thế\\s*giới|kỷ\\s*lục\\s*quốc\\s*gia|huy\\s*chương\\s*vàng|huy\\s*chương\\s*bạc|huy\\s*chương\\s*đồng|bảng\\s*tổng\\s*sắp|phá\\s*kỷ\\s*lục)\\b',
    '\\b(?:chủ\\s*hộ\\s*kinh\\s*doanh|mã\\s*số\\s*thuế|giấy\\s*phép\\s*kinh\\s*doanh|thanh\\s*tra\\s*thuế|hộ\\s*kinh\\s*doanh\\s*cá\\s*thể|phí\\s*môn\\s*bài)\\b',
    '\\b(?:swift|l/c|tín\\s*dụng\\s*thư|nhờ\\s*thu\\s*chứng\\s*từ|thanh\\s*toán\\s*quốc\\s*tế|rửa\\s*tiền|trốn\\s*thuế|thiên\\s*đường\\s*thuế|kiểm\\s*toán\\s*độc\\s*lập)\\b',
    '\\b(?:vi\\s*khuẩn\\s*hp|tụ\\s*cầu\\s*vàng|liên\\s*cầu\\s*khuẩn|e\\s*coli|kháng\\s*thuốc|phòng\\s*thí\\s*nghiệm|nuôi\\s*cấy\\s*vi\\s*sinh|kỹ\\s*thuật\\s*di\\s*truyền)\\b',
    '\\b(?:hậu\\s*kỳ\\s*ảnh|lightroom|chỉnh\\s*màu\\s*cinematic|dải\\s*tương\\s*phản|dynamyc\\s*range|loa\\s*kiểm\\s*âm|tai\\s*nghe\\s*chống\\s*ồn|hi-res\\s*audio)\\b',
    '\\b(?:ban\\s*liên\\s*lạc|hội\\s*đồng\\s*ngũ|cựu\\s*giáo\\s*chức|hội\\s*khuyến\\s*học|tri\\s*ân\\s*thầy\\s*cô|kỷ\\s*niệm\\s*ngày\\s*ra\\s*trường|họp\\s*lớp)\\b',
    '\\b(?:á\\s*hậu|hoa\\s*hậu|hoa\\s*khôi|người\\s*đẹp|người\\s*mẫu|showbiz|nhan\\s*sắc|thảm\\s*đỏ|catwalk)\\b',
    '\\b(?:loài\\s*chim|thế\\s*giới\\s*động\\s*vật|bảo\\s*tồn\\s*thiên\\s*nhiên|vườn\\s*thú|sở\\s*thú|cá\\s*thể|tê\\s*tê|động\\s*vật\\s*hoang\\s*dã|thả\\s*về\\s*rừng)\\b',
    '\\b(?:j-league|k-league|nagoya\\s*grampus|kawasaki|yokohama|incheon|gangwon|buriram|pathum)\\b',
    '\\b(?:nha\\s*khoa|răng\\s*hàm\\s*mặt|niềng\\s*răng|trồng\\s*răng|bọc\\s*răng|tẩy\\s*trắng)\\b',
    '\\b(?:hoàng\\s*thành\\s*thăng\\s*long|cố\\s*đô\\s*huế|thánh\\s*địa\\s*mỹ\\s*sơn|tràng\\s*an\\s*ninh\\s*bình|di\\s*tích\\s*lịch\\s*sử\\s*cấp\\s*quốc\\s*gia|khu\\s*di\\s*tích|trùng\\s*tu\\s*di\\s*tích)\\b',
    '\\b(?:liệu\\s*pháp\\s*cbt|trị\\s*liệu\\s*tâm\\s*lý|tham\\s*vấn\\s*tâm\\s*thần|sang\\s*chấn|lo\\s*âu|rối\\s*loạn\\s*nhân\\s*cách|giải\\s*mã\\s*giấc\\s*mơ|tiềm\\s*thức)\\b',
    '\\b(?:giao\\s*hàng\\s*tiết\\s*kiệm|giao\\s*hàng\\s*nhanh|viettel\\s*post|v\\s*n\\s*post|mã\\s*vận\\s*đơn|chuyển\\s*phát\\s*nhanh|phí\\s*ship|thu\\s*hộ\\s*cod|tra\\s*cứu\\s*đơn\\s*hàng)\\b',
    '\\b(?:kết\\s*cấu\\s*thép|hệ\\s*thống\\s*m\\s*e\\s*p|tòa\\s*nhà\\s*xanh|chứng\\s*chỉ\\s*leed|thiết\\s*kế\\s*kháng\\s*chấn|vật\\s*liệu\\s*xây\\s*dựng\\s*mới|công\\s*nghệ\\s*bê\\s*tông)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*ngành\\s*y|hành\\s*nghề\\s*khám\\s*chữa\\s*bệnh|kỷ\\s*luật\\s*vi\\s*phạm|tận\\s*tâm\\s*phục\\s*vụ|thầy\\s*thuốc\\s*nhân\\s*dân)\\b',
    "\\b(?:l'oreal|estee\\s*lauder|shiseido|lancome|laneige|innisfree|sk-ii|mỹ\\s*phẩm\\s*chính\\s*hãng|son\\s*môi|kem\\s*dưỡng\\s*da|chu\\s*trình\\s*skincare)\\b",
    "\\b(?:mcdonald's|kfc|lotteria|pizza\\s*hut|starbucks|highlands\\s*coffee|phúc\\s*long|trà\\s*sữa\\s*topping|thực\\s*đơn\\s*nhanh|món\\s*mới\\s*ra\\s*mắt)\\b",
    '\\b(?:ăn\\s*dặm\\s*kiểu\\s*nhật|ăn\\s*dặm\\s*blw|rèn\\s*con\\s*tự\\s*lập|khủng\\s*hoảng\\s*tuổi\\s*lên\\s*ba|mẹ\\s*bỉm\\s*sữa|chọn\\s*bỉm\\s*sữa|sữa\\s*công\\s*thức|phát\\s*triển\\s*chiều\\s*cao)\\b',
    '\\b(?:cà\\s*phê|quán\\s*bar|pub|lounge|vũ\\s*trường|karaoke)\\s*(?:khai\\s*trương|giảm\\s*giá|check-in|chill|quẩy|nhạc\\s*sống)(?!.*(?:cháy|sập|ngập|bão|lũ))\\b',
    '\\b(?:xác\\s*pháo|pháo\\s*giấy|pháo\\s*điện|pháo\\s*hoa|đốt\\s*pháo)(?!.*(?:cháy|nổ|thương\\s*vong|cứu\\s*hộ))\\b',
    '\\b(?:giếng\\s*hoang|hố\\s*ga|cống\\s*thoát\\s*nước)\\s*(?:bỏ\\s*hoang|không\\s*nắp|nguy\\s*hiểm)(?!.*(?:ngập|lũ|mưa|bão))\\b',
    '\\b(?:hướng\\s*dẫn\\s*viên|thuyết\\s*minh\\s*viên)\\s*(?:du\\s*lịch|bảo\\s*tàng|di\\s*tích)(?!.*(?:mắc\\s*kẹt|cô\\s*lập|lũ|bão))\\b',
    '\\b(?:luật\\s*mới|luật\\s*sửa\\s*đổi|dự\\s*thảo\\s*luật|thông\\s*qua\\s*luật|hiệu\\s*lực\\s*thi\\s*hành)(?!.*(?:phòng\\s*chống\\s*thiên\\s*tai|đê\\s*điều|khẩn\\s*cấp))\\b',
    '\\b(?:món\\s*hời|áp\\s*mã\\s*giảm\\s*giá|đổ\\s*xô\\s*mua\\s*sắm|tình\\s*trạng\\s*cháy\\s*hàng|vỡ\\s*trận\\s*vì\\s*khuyến\\s*mãi)\\b',
    '\\b(?:xòe\\s*thái|cồng\\s*chiêng|tây\\s*nguyên|ca\\s*trù|hát\\s*xoan|đàn\\s*đá|trình\\s*diễn\\s*nghệ\\s*thuật)\\b',
    '\\b(?:trị\\s*bệnh\\s*cho\\s*chó\\s*mèo|tiêm\\s*phòng\\s*dại|phối\\s*giống\\s*thú\\s*cưng|thức\\s*ăn\\s*hạt|cát\\s*vệ\\s*sinh|phòng\\s*khám\\s*thú\\s*y|spa\\s*thú\\s*cưng)\\b',
    '\\b(?:điều\\s*khoản\\s*bất\\s*khả\\s*kháng|ủy\\s*quyền\\s*đại\\s*diện|phụ\\s*lục\\s*hợp\\s*đồng|thanh\\s*lý\\s*hợp\\s*đồng|phát\\s*mại\\s*tài\\s*sản|tố\\s*tụng\\s*trọng\\s*tài|tòa\\s*án\\s*kinh\\s*tế)\\b',
    '\\b(?:thẩm\\s*định\\s*giá|đấu\\s*giá\\s*tài\\s*sản|kê\\s*biên|thu\\s*về\\s*ngân\\s*sách|nghĩa\\s*vụ\\s*tài\\s*chính)\\b',
    '\\b(?:bồi\\s*dưỡng\\s*nghiệp\\s*vụ|tập\\s*huấn\\s*kỹ\\s*năng)\\b',
    '\\b(?:bát\\s*tràng|vạn\\s*phúc|sa\\s*đéc|đại\\s*bái|làng\\s*nghề|sản\\s*phẩm\\s*thủ\\s*công)\\b',
    '\\b(?:cần\\s*trục\\s*tháp|xe\\s*lu\\s*rung|máy\\s*xúc\\s*bánh\\s*xích|máy\\s*ủi|xe\\s*cẩu\\s*tự\\s*hành|vận\\s*hành\\s*máy\\s*móc|bảo\\s*trì\\s*công\\s*nghiệp)\\b',
    '\\b(?:án\\s*treo|giảm\\s*nhẹ\\s*hình\\s*phạt|hành\\s*vi\\s*phạm\\s*tội|đồng\\s*phạm|chủ\\s*mưu|tang\\s*vật|hồ\\s*sơ\\s*vụ\\s*án|phiên\\s*tòa\\s*xét\\s*xử)\\b',
    '\\b(?:quyết\\s*định\\s*khởi\\s*tố|lệnh\\s*tạm\\s*giam|phiên\\s*phúc\\s*thẩm)\\b',
    '\\b(?:số\\s*hóa|chuyển\\s*đổi\\s*số|hệ\\s*sinh\\s*thái|khởi\\s*nghiệp\\s*sáng\\s*tạo|vón\\s*đầu\\s*tư|quỹ\\s*mạo\\s*hiểm)\\b',
    '\\b(?:phong\\s*cách\\s*thời\\s*trang|mốt\\s*mới\\s*nhất|phối\\s*đồ|mix\\s*đồ|phụ\\s*kiện\\s*đi\\s*kèm|lookbook|sưu\\s*tập\\s*mùa\\s*hè|trình\\s*diễn\\s*thời\\s*trang|tuần\\s*lễ\\s*thời\\s*trang)\\b',
    '\\b(?:ùn\\s*tắc\\s*giờ\\s*cao\\s*điểm|kẹt\\s*xe\\s*cục\\s*bộ|phân\\s*luồng\\s*dịp\\s*lễ|bến\\s*xe\\s*đông\\s*nghẹt|người\\s*dân\\s*đổ\\s*về\\s*quê|đường\\s*vành\\s*đai\\s*trên\\s*cao)\\b',
    '\\b(?:lãi\\s*suất\\s*huy\\s*động|tiết\\s*kiệm\\s*tại\\s*quầy|app\\s*ngân\\s*hàng|quẹt\\s*thẻ|thanh\\s*toán\\s*không\\s*tiền\\s*mặt|voucher\\s*giảm\\s*giá)\\b',
    '\\b(?:văn\\s*bằng\\s*hai|đào\\s*tạo\\s*từ\\s*xa|chứng\\s*chỉ\\s*ngắn\\s*hạn|học\\s*phần|tín\\s*chỉ|đăng\\s*ký\\s*môn\\s*học|phòng\\s*đào\\s*tạo|khoa\\s*chuyên\\s*môn)\\b',
    '\\b(?:trao\\s*tặng\\s*kỷ\\s*niệm\\s*chương|huy\\s*hiệu\\s*đảng|khen\\s*thưởng\\s*đột\\s*xuất|phong\\s*trào\\s*thi\\s*đua|gương\\s*người\\s*tốt\\s*việc\\s*tốt|điển\\s*hình\\s*tiên\\s*tiến)\\b',
    '\\b(?:mẹo\\s*chăm\\s*sóc|bí\\s*quyết\\s*làm\\s*đẹp|tự\\s*nhiên\\s*tại\\s*nhà|cẩm\\s*nang\\s*sức\\s*khỏe|phương\\s*pháp\\s*khoa\\s*học|chế\\s*độ\\s*dinh\\s*dưỡng|bảo\\s*vệ\\s*sức\\s*khỏe|tư\\s*vấn\\s*sức\\s*khỏe|lưu\\s*ý\\s*sức\\s*khỏe|giữ\\s*ấm\\s*cơ\\s*thể|phòng\\s*bệnh\\s*mùa\\s*đông)(?!.*(?:vùng\\s*lũ|bão|thiên\\s*tai|cứu\\s*trợ))\\b',
    '\\b(?:năng\\s*lượng\\s*nhiệt\\s*hạch|fusion\\s*energy|du\\s*lịch\\s*vũ\\s*trụ|virgin\\s*galactic|thám\\s*hiểm\\s*sao\\s*hỏa|định\\s*cư\\s*vũ\\s*trụ)\\b',
    '\\b(?:crispr|chỉnh\\s*sửa\\s*gen|liệu\\s*pháp\\s*tế\\s*bào\\s*gốc|miễn\\s*dịch\\s*trị\\s*liệu|phác\\s*đồ\\s*ung\\s*thư|y\\s*học\\s*tái\\s*tạo)\\b',
    '\\b(?:sao\\s*vàng\\s*đất\\s*việt|hàng\\s*việt\\s*nam\\s*chất\\s*lượng\\s*cao|giải\\s*thưởng\\s*tạ\\s*quang\\s*bửu|giải\\s*vin\\s*future|giải\\s*thưởng\\s*nhà\\s*nước)\\b',
    '\\b(?:chương\\s*trình\\s*mục\\s*tiêu\\s*quốc\\s*gia|đô\\s*thị\\s*văn\\s*minh|gia\\s*đình\\s*văn\\s*hóa)\\b',
    '\\b(?:kiểm\\s*tra\\s*chuyên\\s*ngành|thanh\\s*tra\\s*hành\\s*chính|xử\\s*phạt\\s*vi\\s*phạm|niêm\\s*yết\\s*công\\s*khai|lấy\\s*ý\\s*kiến\\s*nhân\\s*dân)\\b',
    '\\b(?:khảm\\s*xà\\s*cừ|mây\\s*tre\\s*đan|đúc\\s*đồng|nghệ\\s*thuật\\s*chạm\\s*khắc|sản\\s*phẩm\\s*mỹ\\s*nghệ|tinh\\s*hoa\\s*di\\s*sản)\\b',
    '\\b(?:liệu\\s*pháp\\s*âm\\s*thanh|aromatherapy|trị\\s*liệu\\s*mùi\\s*hương|nước\\s*hoa\\s*niche|tầng\\s*hương|độ\\s*lưu\\s*hương|tinh\\s*dầu\\s*thiên\\s*nhiên|thư\\s*giãn\\s*tâm\\s*hồn)\\b',
    '\\b(?:chủ\\s*trương\\s*đại\\s*hội|văn\\s*kiện\\s*quy\\s*hoạch|đề\\s*án\\s*phát\\s*triển|nguồn\\s*lực\\s*số|hạ\\s*tầng\\s*viễn\\s*thông|phủ\\s*sóng\\s*5\\s*g)\\b',
    '\\b(?:xây\\s*dựng\\s*đội\\s*ngũ|nâng\\s*cao\\s*năng\\s*lực|đào\\s*tạo\\s*nguồn\\s*nhân\\s*lực|chính\\s*sách\\s*đãi\\s*ngộ|môi\\s*trường\\s*chuyên\\s*nghiệp)\\b',
    '\\b(?:mã\\s*h\\s*s|chứng\\s*nhận\\s*xuất\\s*xu|c/o|tờ\\s*khai\\s*hải\\s*quan|thông\\s*quan\\s*hàng\\s*hóa|cước\\s*vận\\s*tải\\s*biển|tàu\\s*container|logistics\\s*chuyên\\s*dụng)\\b',
    '\\b(?:tranh\\s*chấp\\s*quyền\\s*sử\\s*dụng\\s*đất|thừa\\s*kế\\s*theo\\s*pháp\\s*luật|di\\s*chúc\\s*hợp\\s*pháp|hợp\\s*đồng\\s*ủy\\s*quyền|công\\s*chứng\\s*tư\\s*pháp|thi\\s*hành\\s*án\\s*dân\\s*sự)\\b',
    '\\b(?:độc\\s*quyền\\s*phân\\s*phối|nhượng\\s*quyền\\s*thương\\s*mại|franchise|chiến\\s*dịch\\s*marketing|định\\s*vị\\s*thị\\s*trường)\\b',
    '\\b(?:phê\\s*duyệt\\s*quy\\s*hoạch|nguồn\\s*vốn\\s*o\\s*d\\s*a|giải\\s*ngân\\s*vốn\\s*đầu\\s*tư|tiến\\s*độ\\s*dự\\s*án|tổng\\s*mức\\s*đầu\\s*tư)\\b',
    '\\b(?:nhà\\s*đinh|nhà\\s*tiền\\s*lê|nhà\\s*lý|nhà\\s*trần|nhà\\s*hồ|nhà\\s*mạc|nhà\\s*tây\\s*sơn|nhà\\s*nguyễn|chế\\s*độ\\s*phong\\s*kiến|chiều\\s*đại\\s*lịch\\s*sử)\\b',
    '\\b(?:hiện\\s*vật\\s*trưng\\s*bày|bảo\\s*tàng\\s*lịch\\s*sử|khai\\s*quật\\s*di\\s*chỉ|di\\s*vật\\s*quý\\s*hiếm|trùng\\s*tu\\s*tôn\\s*tạo)\\b',
    '\\b(?:bắn\\s*cung|đua\\s*xe\\s*đạp|bowling|trượt\\s*băng|khiêu\\s*vũ\\s*thể\\s*thao|dancesport|thể\\s*dục\\s*nghệ\\s*thuật|vovinam|karatedo|taekwondo|wushu)\\b',
    '\\b(?:đăng\\s*ký\\s*thanh\\s*toán|kiểm\\s*tra\\s*số\\s*dư|biến\\s*động\\s*số\\s*dư|lịch\\s*sử\\s*giao\\s*dịch|sao\\s*kê\\s*tài\\s*khoản|chuyển\\s*tiền\\s*nhanh\\s*24/7)\\b',
    '\\b(?:xem\\s*ngày\\s*tốt|giờ\\s*hoàng\\s*đạo|hướng\\s*xuất\\s*hành|khai\\s*trương\\s*hồng\\s*phát|văn\\s*khấn\\s*cổ\\s*truyền|mâm\\s*cỗ\\s*cúng\\s*rằm)\\b',
    '\\b(?:flex\\s*đến\\s*hơi\\s*thở\\s*cuối|check-in\\s*sang\\s*chảnh|k\\s*o\\s*ls|k\\s*o\\s*cs|gen\\s*z|thế\\s*hệ\\s*alpha|slay|vibe\\s*cực\\s*chỉnh|đu\\s*idol|vô\\s*tri|thao\\s*túng\\s*tâm\\s*lý)\\b',
    '\\b(?:biên\\s*bản\\s*vi\\s*phạm\\s*hành\\s*chính|quyết\\s*định\\s*xử\\s*phạt|hình\\s*thức\\s*tăng\\s*nặng|tình\\s*tiết\\s*giảm\\s*nhẹ|cưỡng\\s*thế\\s*thi\\s*hành|khiếu\\s*nại\\s*tố\\s*cáo|tranh\\s*chấp\\s*hành\\s*chính)\\b',
    '\\b(?:hệ\\s*thống\\s*phân\\s*phối\\s*bán\\s*lẻ|chuỗi\\s*cửa\\s*hàng\\s*tiện\\s*lợi|siêu\\s*thị\\s*mini|trải\\s*nghiệm\\s*khách\\s*hàng|cơ\\s*hội\\s*hợp\\s*tác\\s*kinh\\s*doanh|phát\\s*triển\\s*đại\\s*lý)\\b',
    '\\b(?:khóa\\s*học\\s*online\\s*miễn\\s*phí|hội\\s*thảo\\s*trực\\s*tuyến|webinar|đào\\s*tạo\\s*kỹ\\s*năng\\s*mềm|chứng\\s*chỉ\\s*hoàn\\s*thành|học\\s*bổng\\s*khuyến\\s*học)\\b',
    '\\b(?:hướng\\s*dẫn\\s*thủ\\s*tục|cấp\\s*đổi\\s*giấy\\s*phép|tra\\s*cứu\\s*thông\\s*tin|dịch\\s*vụ\\s*công\\s*mức\\s*độ\\s*4|thủ\\s*tục\\s*một\\s*cửa)\\b',
    '\\b(?:lịch\\s*sử\\s*kháng\\s*chiến|tội\\s*ác\\s*chiến\\s*tranh|di\\s*tích\\s*chiến\\s*trường|tìm\\s*kiếm\\s*đồng\\s*đội|huân\\s*chương\\s*chiến\\s*công)\\b',
    '\\b(?:quân\\s*đội\\s*nhân\\s*dân|cờ\\s*đảng|huy\\s*hiệu\\s*đảng|kỷ\\s*niệm\\s*.*năm.*thành\\s*lập|vang\\s*mãi|hào\\s*khí|chiến\\s*thắng|quân\\s*lệnh\\s*số)\\b',
    '\\b(?:chuyên\\s*án|điều\\s*tra\\s*làm\\s*rõ|phá\\s*án|tội\\s*phạm\\s*ma\\s*túy|bắt\\s*giữ\\s*đối\\s*tượng|truy\\s*nã|vụ\\s*án\\s*giết\\s*người)\\b',
    '\\b(?:chương\\s*trình\\s*khuyến\\s*mãi|hành\\s*trình\\s*bay|vé\\s*máy\\s*bay\\s*giá\\s*rẻ|giờ\\s*bay|đăng\\s*ký\\s*trực\\s*tuyến|check-in\\s*online|phòng\\s*chờ\\s*hạng\\s*thương\\s*gia)\\b',
    '\\b(?:quy\\s*tắc\\s*đạo\\s*đức|hành\\s*vi\\s*ứng\\s*xử|văn\\s*hóa\\s*gia\\s*đình|giá\\s*trị\\s*cốt\\s*lõi|phẩm\\s*chất\\s*đạo\\s*đức|lối\\s*sống\\s*lành\\s*mạnh|thể\\s*dục\\s*thể\\s*thao)\\b',
    '\\b(?:mã\\s*lỗi\\s*điều\\s*hòa|lỗi\\s*e\\s*1|lỗi\\s*e\\s*2|lỗi\\s*f\\s*5|bảng\\s*mã\\s*lỗi|sửa\\s*bình\\s*nóng\\s*lạnh\\s*tại\\s*nhà|thông\\s*tắc\\s*bể\\s*phốt\\s*giá\\s*rẻ)\\b',
    '\\b(?:hội\\s*cựu\\s*thanh\\s*niên\\s*xung\\s*phong|ban\\s*liên\\s*lạc\\s*bạn\\s*chiến\\s*đấu|hội\\s*hỗ\\s*trợ\\s*gia\\s*đình\\s*liệt\\s*sĩ|quỹ\\s*nghĩa\\s*tình\\s*đồng\\s*đội|tri\\s*ân\\s*anh\\s*hùng)\\b',
    "\\b(?:quả\\s*bóng\\s*vàng|ballon\\s*d'or|chiếc\\s*giày\\s*vàng|golden\\s*boot|the\\s*best|cầu\\s*thủ\\s*xuất\\s*sắc\\s*nhất|đội\\s*hình\\s*tiêu\\s*biểu|quản\\s*lý\\s*thể\\s*thao)\\b",
    '\\b(?:dầm\\s*chuyển|cột\\s*biên|bể\\s*nước\\s*mái|hệ\\s*thống\\s*thang\\s*máy|phòng\\s*cháy\\s*chữa\\s*cháy\\s*kỹ\\s*thuật|nghiệm\\s*thu\\s*pccc)\\b',
    '\\b(?:nâng\\s*cao\\s*hiệu\\s*quả|công\\s*nghệ\\s*tiên\\s*tiến|giải\\s*pháp\\s*toàn\\s*diện|đối\\s*tác\\s*tin\\s*cậy)\\b',
    '\\b(?:lụa\\s*tơ\\s*tằm|thổ\\s*cẩm|dệt\\s*may\\s*xuất\\s*khẩu|sợi\\s*tự\\s*nhiên|ngành\\s*may\\s*mặc|thiết\\s*kế\\s*thời\\s*trang)\\b',
    '\\b(?:hàng\\s*thừa\\s*kế|phân\\s*chia\\s*tài\\s*sản|tranh\\s*chấp\\s*hôn\\s*nhân|quyền\\s*nuôi\\s*con|án\\s*phí\\s*dân\\s*sự|hòa\\s*giải\\s*cơ\\s*sở)\\b',
    '\\b(?:quy\\s*chế\\s*hoạt\\s*động|nội\\s*quy\\s*cơ\\s*quan|cải\\s*cách\\s*thủ\\s*tục|một\\s*cửa\\s*liên\\s*thông|hiện\\s*đại\\s*hóa\\s*hành\\s*chính| kỷ\\s*luật\\s*công\\s*vụ)\\b',
    '\\b(?:lò\\s*cao|luyện\\s*kim|phôi\\s*thép|cán\\s*nóng|cán\\s*nguội|hợp\\s*kim\\s*đặc\\s*biệt|ngành\\s*công\\s*nghiệp\\s*nặng|khai\\s*thác\\s*khoáng\\s*sản)\\b',
    '\\b(?:hướng\\s*dẫn\\s*áp\\s*dụng|quy\\s*định\\s*chi\\s*tiết|thông\\s*tư\\s*hướng\\s*dẫn|nghị\\s*định\\s*sửa\\s*đổi|có\\s*hiệu\\s*lực\\s*thi\\s*hành)\\b',
    '\\b(?:đại\\s*hội\\s*chi\\s*bộ|ban\\s*chấp\\s*hành|tiền\\s*phong\\s*gương\\s*mẫu|kiểm\\s*điểm\\s*tự\\s*phê\\s*bình|phát\\s*triển\\s*đảng\\s*viên|kết\\s*nạp\\s*đảng)\\b',
    '\\b(?:logistics\\s*ngược|kho\\s*thông\\s*minh|cảng\\s*cạn\\s*icd|hệ\\s*thống\\s*w\\s*m\\s*s|vận\\s*tải\\s*đa\\s*phương\\s*thức|chuỗi\\s*cung\\s*ứng\\s*bền\\s*vững|tối\\s*ưu\\s*chặng\\s*cuối)\\b',
    '\\b(?:nâng\\s*cao\\s*chất\\s*lượng|đổi\\s*mới\\s*toàn\\s*diện|phát\\s*triển\\s*bền\\s*vững|nguồn\\s*nhân\\s*lực\\s*chất\\s*lượng\\s*cao|kinh\\s*tế\\s*tri\\s*thức|công\\s*nghiệp\\s*4.0)\\b',
    '\\b(?:hỏi\\s*đáp\\s*pháp\\s*luật|tư\\s*vấn\\s*sức\\s*khỏe|chuyện\\s*lạ\\s*đó\\s*đây|tiêu\\s*điểm\\s*dư\\s*luận|góc\\s*nhìn\\s*chuyên\\s*gia|tiếng\\s*nói\\s*cử\\s*tri|báo\\s*chí\\s*điều\\s*tra|phóng\\s*sự\\s*dài\\s*kỳ)\\b',
    '\\b(?:ga\\s*ngầm|đào\\s*hầm\\s*bằng\\s*robot\\s*tbm|đốt\\s*hầm\\s*dìm|lồng\\s*hầm|phương\\s*pháp\\s*đào\\s*hở|thi\\s*công\\s*ngầm|kết\\s*cấu\\s*chịu\\s*lực|địa\\s*chất\\s*công\\s*trình)\\b',
    '\\b(?:chương\\s*trình\\s*nghị\\s*sự\\s*quốc\\s*tế|tuyên\\s*bố\\s*hành\\s*động|cam\\s*kết\\s*khí\\s*hậu|net\\s*zero|chuyển\\s*đổi\\s*năng\\s*lượng|tín\\s*chỉ\\s*carbon|phát\\s*triển\\s*xanh)\\b',
    '\\b(?:dự\\s*thảo\\s*quy\\s*tắc|lấy\\s*ý\\s*kiến\\s*phản\\s*hồi|đánh\\s*giá\\s*tác\\s*động|thẩm\\s*định\\s*độc\\s*lập|đo\\s*lường\\s*chỉ\\s*số\\s*kpi)\\b',
    '\\b(?:nâng\\s*tầm\\s*vị\\s*thế|khẳng\\s*định\\s*thương\\s*hiệu|vươn\\s*tầm\\s*thế\\s*giới|ghi\\s*danh\\s*bản\\s*đồ|kết\\s*nối\\s*toàn\\s*cầu)\\b',
    '\\b(?:taylor\\s*swift|eras\\s*tour|messi|lionel\\s*messi|ronaldo|cristiano\\s*ronaldo|mbappe|haaland|neymar|giải\\s*thưởng\\s*grammy|oscar)\\b',
    '\\b(?:putin|tập\\s*cận\\s*bình|elon\\s*musk|mark\\s*zuckerberg|bill\\s*gates|jeff\\s*bezos|tỷ\\s*phú\\s*forbes|giàu\\s*nhất\\s*thế\\s*giới)\\b',
    '\\b(?:tuyến\\s*cáp\\s*aag|apg|ia|smw3|sự\\s*cố\\s*đứt\\s*cáp|đường\\s*truyền\\s*quốc\\s*tế|bảo\\s*trì\\s*hệ\\s*thống|trạm\\s*cập\\s*bờ)\\b',
    '\\b(?:thị\\s*trường\\s*chuyển\\s*nhượng|hợp\\s*đồng\\s*kỷ\\s*lục|ngôi\\s*sao\\s*bóng\\s*đá|vòng\\s*loại\\s*world\\s*cup|champion\\s*league)\\b',
    '\\b(?:chiến\\s*dịch\\s*quảng\\s*cáo|đại\\s*sứ\\s*thương\\s*hiệu|tính\\s*năng\\s*độc\\s*đáo|cập\\s*nhật\\s*phiên\\s*bản)\\b',
    '\\b(?:liên\\s*hoan\\s*phim|l\\s*h\\s*p|cannes|venice|berlin|bông\\s*sen\\s*vàng|cánh\\s*diều\\s*vàng|đạo\\s*diễn\\s*xuất\\s*sắc|biên\\s*kịch|vai\\s*diễn|sân\\s*khấu\\s*kịch|phim\\s*mưa\\s*đỏ|bộ\\s*phim)\\b',
    '\\b(?:tranh\\s*chấp\\s*lao\\s*động|sa\\s*thải\\s*trái\\s*luật|hợp\\s*đồng\\s*lao\\s*động|bảo\\s*hiểm\\s*thất\\s*nghiệp|đình\\s*công|lương\\s*thưởng)\\b',
    '\\b(?:turbine\\s*gió|cánh\\s*quạt\\s*phong\\s*điện|điện\\s*gió\\s*ngoài\\s*khơi|móng\\s*cọc\\s*biển|năng\\s*lượng\\s*tái\\s*tạo|quy\\s*hoạch\\s*điện\\s*viii|giá\\s*feed-in\\s*tariff)\\b',
    '\\b(?:nghiên\\s*cứu\\s*độc\\s*lập|kết\\s*quả\\s*khảo\\s*sát|số\\s*liệu\\s*thống\\s*kê|độ\\s*tin\\s*cậy|phương\\s*pháp\\s*nghiên\\s*cứu|phân\\s*tích\\s*dữ\\s*liệu)\\b',
    '\\b(?:nâng\\s*cao\\s*trình\\s*độ|đào\\s*tạo\\s*chuyên\\s*sâu|kỹ\\s*năng\\s*thời\\s*đại\\s*số)\\b',
    '\\b(?:kỹ\\s*thuật\\s*nấu\\s*nướng|lên\\s*men\\s*tự\\s*nhiên|vi\\s*sinh\\s*thực\\s*phẩm|hương\\s*liệu\\s*nhân\\s*tạo|an\\s*toàn\\s*vệ\\s*sinh|chuỗi\\s*cung\\s*ứng\\s*lạnh)\\b',
    '\\b(?:gian\\s*lận\\s*thuế|quyết\\s*toán\\s*kế\\s*toán|chứng\\s*từ\\s*kế\\s*toán|nghiệp\\s*vụ\\s*tài\\s*chính|kế\\s*toán\\s*trưởng)\\b',
    '\\b(?:hồ\\s*sơ\\s*pháp\\s*lý|thủ\\s*tục\\s*hành\\s*chính|giải\\s*ngân\\s*vốn)\\b',
    '\\b(?:văn\\s*hóa\\s*đọc|ngày\\s*hội\\s*sách|ra\\s*mắt\\s*tác\\s*phẩm|độc\\s*giả|tác\\s*giả|nhà\\s*xuất\\s*bản|phê\\s*bình\\s*văn\\s*học|di\\s*sản\\s*chữ\\s*viết)\\b',
    '\\b(?:liên\\s*kết\\s*vùng|tầm\\s*nhìn\\s*quy\\s*hoạch|động\\s*lực\\s*tăng\\s*trưởng|kinh\\s*tế\\s*số|chuyển\\s*đổi\\s*xanh|bền\\s*vững)\\b',
    '\\b(?:ban\\s*lễ\\s*tang|cáo\\s*phó|gia\\s*đình\\s*báo\\s*tin|thành\\s*kính\\s*phân\\s*ưu|vòng\\s*hoa\\s*viếng|di\\s*nguyện)(?!.*(?:cứu\\s*dân|cứu\\s*hộ|hy\\s*sinh\\s*khi\\s*làm\\s*nhiệm\\s*vụ|bão|lũ|ngập|sạt\\s*lở))\\b',
    '\\b(?:gốm\\s*chu\\s*đậu|gốm\\s*phù\\s*lãng|đúc\\s*đồng\\s*ngũ\\s*xã|tranh\\s*đông\\s*hồ|tranh\\s*hàng\\s*trống|ngôi\\s*làng\\s*cổ|nghệ\\s*nhân\\s*truyền\\s*thống)\\b',
    '\\b(?:công\\s*tác\\s*xã\\s*hội|quỹ\\s*từ\\s*thiện|vận\\s*động\\s*quyên\\s*góp|nhà\\s*hảo\\s*tâm|mạnh\\s*thường\\s*quân|trao\\s*quà\\s*tình\\s*nghĩa|xóa\\s*đói\\s*giảm\\s*nghèo|lá\\s*lành\\s*đùm\\s*lá\\s*rách)(?!.*(?:bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở|đồng\\s*bào|hậu\\s*quả))\\b',
    '\\b(?:vách\\s*kính\\s*unitized|hệ\\s*stick|tấm\\s*alu|lam\\s*chắn\\s*nắng|mặt\\s*dựng|kết\\s*cấu\\s*bao\\s*che|vật\\s*liệu\\s*hoàn\\s*thiện|trang\\s*trí\\s*ngoại\\s*thất)\\b',
    '\\b(?:phấn\\s*đấu\\s*hoàn\\s*thành|vượt\\s*kế\\s*hoạch|thi\\s*đua\\s*lập\\s*thành\\s*tích|chào\\s*mừng\\s*kỷ\\s*niệm|biểu\\s*dương\\s*khen\\s*thưởng|gương\\s*sáng)(?!.*(?:khắc\\s*phục|hậu\\s*quả|thiên\\s*tai|bão|lũ|sạt\\s*lở|cứu\\s*trợ))\\b',
    '\\b(?:rầy\\s*nâu|sâu\\s*cuốn\\s*lá|ốc\\s*bươu\\s*vàng|bệnh\\s*đạo\\s*ôn|phun\\s*thuốc\\s*trừ\\s*sâu|bảo\\s*vệ\\s*mùa\\s*màng|an\\s*toàn\\s*sinh\\s*học)\\b',
    '\\b(?:lụa\\s*nha\\s*xá|thổ\\s*cẩm\\s*mỹ\\s*nghiệp|chạm\\s*bạc\\s*đồng\\s*xâm|đá\\s*mỹ\\s*nghệ\\s*non\\s*nước|tinh\\s*hoa\\s*đất\\s*nghề)\\b',
    '\\b(?:phá\\s*sản\\s*doanh\\s*nghiệp|giải\\s*thế|mở\\s*thủ\\s*tục\\s*phá\\s*sản|quản\\s*tài\\s*viên|danh\\s*sách\\s*chủ\\s*nợ|tuyên\\s*bố\\s*phá\\s*sản|nợ\\s*quá\\s*hạn)\\b',
    '\\b(?:máy\\s*xúc\\s*đào|dung\\s*tích\\s*gầu|bán\\s*kính\\s*đào|hệ\\s*thống\\s*thủy\\s*lực|bảo\\s*trì\\s*máy\\s*móc|vật\\s*tư\\s*thi\\s*công|thiết\\s*bị\\s*công\\s*trình)\\b',
    '\\b(?:tăng\\s*cường\\s*quản\\s*lý|siết\\s*chặt\\s*kỷ\\s*cương|nâng\\s*cao\\s*trách\\s*nhiệm|kiểm\\s*tra\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*vi\\s*phạm|đúng\\s*quy\\s*định)\\b',
    '\\b(?:sơn\\s*mài\\s*hạ\\s*thái|tạc\\s*tượng\\s*sơn\\s*đồng|mây\\s*tre\\s*đan\\s*phú\\s*vinh|nghệ\\s*nhân\\s*đúc\\s*đồng|triển\\s*lãm\\s*mỹ\\s*thuật)\\b',
    '\\b(?:viện\\s*kiểm\\s*sát\\s*nhân\\s*dân\\s*tối\\s*cao|tòa\\s*án\\s*nhân\\s*dân\\s*tối\\s*cao|kháng\\s* nghị|giám\\s*đốc\\s*thẩm|tái\\s*thẩm|tố\\s*tụng|án\\s*lệ)\\b',
    '\\b(?:chiến\\s*lược\\s*tăng\\s*trưởng|mô\\s*hình\\s*kinh\\s*doanh|mở\\s*rộng\\s*thị\\s*trường|huy\\s*động\\s*vốn|thị\\s*phần|doanh\\s*thu)\\b',
    '\\b(?:cách\\s*mạng\\s*công\\s*nghiệp|khởi\\s*nghiệp|quỹ\\s*đầu\\s*tư)\\b',
    '\\b(?:trận\\s*bạch\\s*đằng|chi\\s*lăng|điện\\s*biên\\s*phủ|nghệ\\s*thuật\\s*quân\\s*sự|lịch\\s*sử\\s*vẻ\\s*vang|hào\\s*khí\\s*dân\\s*tộc|truyền\\s*thống\\s*yêu\\s*nước)\\b',
    '\\b(?:súng\\s*trường|pháo\\s*tự\\s*hành|xe\\s*thiết\\s*giáp|trực\\s*thăng\\s*vũ\\s*trang|tên\\s*lửa\\s*hành\\s*trình|tác\\s*chiến\\s*không\\s*gian|an\\s*ninh\\s*quốc\\s*phòng)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn|giúp\\s*dân|vùng\\s*lũ|lũ\\s*lụt|cô\\s*lập|sơ\\s*tán))\\b',
    '\\b(?:trưng\\s*bày\\s*bảo\\s*tàng|phục\\s*chế\\s*số|hiện\\s*vật\\s*gốc|không\\s*gian\\s*triển\\s*lãm|thuyết\\s*minh\\s*viên|khách\\s*tham\\s*quan|di\\s*sản\\s*thế\\s*giới)\\b',
    '\\b(?:hệ\\s*lõi\\s*cứng|outrigger|belt\\s*truss|giằng\\s*cột|móng\\s*vây|tường\\s*vây|cọc\\s*baryte)\\b',
    '\\b(?:tuyên\\s*đương\\s*điển\\s*hình|người\\s*tốt\\s*việc\\s*tốt|huy\\s*hiệu\\s*cao\\s*quý|giải\\s*thưởng\\s*danh\\s*giá)\\b',
    '\\b(?:lặn\\s*biển\\s*sâu|tàu\\s*ngầm\\s*thám\\s*hiểm|rãnh\\s*mariana|sinh\\s*vật\\s*biển\\s*lạ|thám\\s*hiểm\\s*đáy\\s*đại\\s*dương|khoa\\s*học\\s*đại\\s*dương)\\b',
    '\\b(?:vệ\\s*tinh\\s*địa\\s*tĩnh|quỹ\\s*đạo\\s*thấp|trạm\\s*điều\\s*khiển\\s*mặt\\s*đất|băng\\s*tần\\s*viễn\\s*thông|sóng\\s*vô\\s*tuyến|truyền\\s*hình\\s*số\\s*vệ\\s*tinh)\\b',
    '\\b(?:hiến\\s*pháp|pháp\\s*lệnh|quyền\\s*con\\s*người|quyền\\s*cơ\\s*bản|bộ\\s*máy\\s*nhà\\s*nước|đạo\\s*luật\\s*chuyên\\s*ngành|nghị\\s*quyết\\s*liên\\s*tịch)\\b',
    '\\b(?:văn\\s*hóa\\s*ứng\\s*xử|tri\\s*thức\\s*nhân\\s*loại|di\\s*sản\\s*tư\\s*tưởng|triết\\s*lý\\s*giáo\\s*dục|phương\\s*pháp\\s*truyền\\s*thống)\\b',
    '\\b(?:nâng\\s*cao\\s*hiệu\\s*lực|hiệu\\s*quả\\s*quản\\s*lý|siết\\s*chặt\\s*kỷ\\s*luật|tăng\\s*cường\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*sai\\s*phạm)\\b',
    '\\b(?:đá\\s*quý\\s*lục\\s*yên|trang\\s*sức\\s*cao\\s*cấp|vàng\\s*bạc\\s*đá\\s*quý|kim\\s*cương\\s*nhân\\s*tạo|đá\\s*phong\\s*thủy|ngọc\\s*trai|p\\s*n\\s*j|d\\s*o\\s*j\\s*i|s\\s*j\\s*c)\\b',
    '\\b(?:artemis|apollo|voyager|james\\s*webb|kính\\s*viễn\\s*vọng\\s*hubble|sứ\\s*mệnh\\s*vũ\\s*trụ|đổ\\s*bộ\\s*mặt\\s*trăng|hành\\s*tinh\\s*xa\\s*xôi)\\b',
    '\\b(?:phân\\s*chia\\s*di\\s*sản|khai\\s*nhận\\s*thừa\\s*kế|hợp\\s*đồng\\s*tặng\\s*cho|quyền\\s*bề\\s*mặt|tài\\s*sản\\s*chung|phân\\s*chia\\s*hậu\\s*ly\\s*hôn|nghĩa\\s*vụ\\s*cấp\\s*dưỡng)\\b',
    '\\b(?:tải\\s*trọng\\s*gió|dao\\s*động\\s*công\\s*trình|hệ\\s*thống\\s*giảm\\s*chấn|tuned\\s*mass\\s*damper|t\\s*m\\s*d|kháng\\s*chấn|ổn\\s*định\\s*kết\\s*cấu)\\b',
    '\\b(?:chương\\s*trình\\s*hợp\\s*tác|biên\\s*bản\\s*ghi\\s*nhớ|ký\\s*kết\\s*thỏa\\s*thuận|xúc\\s*tiến\\s*thương\\s*mại)\\b',
    '\\b(?:hàng\\s*tiêu\\s*dùng\\s*nhanh|f\\s*m\\s*c\\s*g|thực\\s*phẩm\\s*đóng\\s*gói|thiết\\s*bị\\s*nhà\\s*bếp|chuỗi\\s*cửa\\s*hàng\\s*bán\\s*lẻ|hàng\\s*hóa\\s*thiết\\s*yếu)\\b',
    '\\b(?:kỹ\\s*thuật\\s*giao\\s*bóng|cú\\s*đánh\\s*trái\\s*tay|chiến\\s*thuật\\s*phối\\s*hợp|đường\\s*chuyền\\s*quyết\\s*định|tình\\s*huống\\s*cố\\s*định|việt\\s*vị|trọng\\s*tài\\s*v\\s*a\\s*r|thẻ\\s*đỏ)\\b',
    '\\b(?:quy\\s*hoạch\\s*tổng\\s*thể\\s*quốc\\s*gia|vùng\\s*kinh\\s*tế\\s*trọng\\s*điểm|liên\\s*kết\\s*tiểu\\s*vùng|phân\\s*bổ\\s*nguồn\\s*lực|tầm\\s*nhìn\\s*phát\\s*triển)\\b',
    '\\b(?:sức\\s*nâng\\s*tối\\s*đa|tầm\\s*với\\s*cần\\s*trực|cáp\\s*tải|puly|móc\\s*cẩu|tự\\s*trọng|thông\\s*số\\s*kỹ\\s*thuật\\s*máy|bảo\\s*trì\\s*định\\s*kỳ)\\b',
    '\\b(?:tinh\\s*thần\\s*đoàn\\s*kết|phát\\s*huy\\s*truyền\\s*thống|thắng\\s*lợi\\s*vẻ\\s*vang|nhiệm\\s*vụ\\s*trọng\\s*tâm|nâng\\s*cao\\s*cảnh\\s*giác|tối\\s*ưu\\s*hóa|quy\\s*trình\\s*khép\\s*kín)\\b',
    '\\b(?:sống\\s*khỏe\\s*mỗi\\s*ngày|góc\\s*tâm\\s*hồn|dành\\s*cho\\s*thiếu\\s*nhi|phụ\\s*nữ\\s*và\\s*gia\\s*đình|góc\\s*thư\\s*giãn|tâm\\s*sự\\s*thầm\\s*kín|hạnh\\s*phúc\\s*gia\\s*đình)\\b',
    '\\b(?:trang\\s*trí\\s*nhà\\s*cửa|phong\\s*thủy\\s*phòng\\s*ngủ|sắp\\s*xếp\\s*không\\s*gian|tổ\\s*ấm\\s*gia\\s*đình|nội\\s*thất\\s*tinh\\s*tế|xu\\s*hướng\\s*màu\\s*sắc|vật\\s*liệu\\s*bên\\s*vững)\\b',
    '\\b(?:hộp\\s*số\\s*turbine|hệ\\s*thống\\s*bôi\\s*trơn|cảm\\s*biến\\s*rung\\s*động|phần\\s*mềm\\s*scada|giám\\s*sát\\s*từ\\s*xa|bảo\\s*trì\\s*dự\\s*phòng|khắc\\s*phục\\s*lỗi\\s*kỹ\\s*thuật)\\b',
    '\\b(?:quy\\s*hoạch\\s*ngành\\s*du\\s*lịch|phát\\s*triển\\s*kinh\\s*tế\\s*biển|liên\\s*kết\\s*vùng\\s*kinh\\s*tế|huy\\s*động\\s*nguồn\\s*lực|xã\\s*hội\\s*hóa)\\b',
    '\\b(?:tuyên\\s*truyền\\s*vận\\s*động|phòng\\s*chống\\s*lãng\\s*phí|thực\\s*hành\\s*tiết\\s*kiệm|đẩy\\s*mạnh\\s*cải\\s*cách|hiệu\\s*quả\\s*thi\\s*hành)\\b',
    '\\b(?:vải\\s*thiều\\s*lục\\s*ngạn|nhãn\\s*lồng\\s*hưng\\s*yên|rượu\\s*cần\\s*tây\\s*nguyên|sâm\\s*ngọc\\s*linh|bưởi\\s*năm\\s*roi|xoài\\s*cát\\s*hòa\\s*lộc|thương\\s*hiệu\\s*đặc\\s*sản|vùng\\s*trồng\\s*tiêu\\s*chuẩn)\\b',
    '\\b(?:công\\s*chứng\\s*sang\\s*tên|thuế\\s*trước\\s*bạ|phí\\s*đăng\\s*ký\\s*biến\\s*động|trích\\s*lục\\s*bản\\s*đồ|giấy\\s*xác\\s*nhận\\s*tình\\s*trạng|thông\\s*tin\\s*quy\\s*hoạch)\\b',
    '\\b(?:xe\\s*bơm\\s*bê\\s*tông|cần\\s*bơm|áp\\s*suất\\s*bơm|vệ\\s*sinh\\s*đường\\s*ống|trạm\\s*trộn\\s*bê\\s*tông|phụ\\s*gia\\s*xây\\s*dựng|nghiệm\\s*thu\\s*cốt\\s*thép)\\b',
    '\\b(?:phát\\s*triển\\s*nguồn\\s*nhân\\s*lực|đào\\s*tạo\\s*kỹ\\s*năng|chứng\\s*chỉ\\s*nghề|giải\\s*quyết\\s*việc\\s*làm|an\\s*sinh\\s*xã\\s*hội|chính\\s*sách\\s*ưu\\s*đãi)\\b',
    '\\b(?:tăng\\s*cường\\s*hợp\\s*tác|thúc\\s*đẩy\\s*đầu\\s*tư|cạnh\\s*tranh\\s*sòng\\s*phẳng)\\b',
    '\\b(?:khám\\s*phá\\s*thế\\s*giới|hành\\s*trình\\s*di\\s*sản|cửa\\s*sổ\\s*tâm\\s*hồn|những\\s*tấm\\s*lòng\\s*vàng|lời\\s*hay\\s*ý\\s*đẹp|gương\\s*sáng\\s*quanh\\s*ta)\\b',
    '\\b(?:vận\\s*động\\s*tài\\s*trợ|trao\\s*tặng\\s*nhà\\s*tình\\s*nghĩa|quỹ\\s*bảo\\s*trợ|trợ\\s*giúp\\s*nhân\\s*đạo|chương\\s*trình\\s*thiện\\s*nguyện|tấm\\s*lòng\\s*hảo\\s*tâm)(?!\\s*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở))\\b',
    '\\b(?:toa\\s*quay|tay\\s*cần|khối\\s*đối\\s*trọng|dầm\\s*gốc|lồng\\s*nâng|đốt\\s*thân\\s*cần\\s*trục|hệ\\s*thống\\s*phanh\\s*hãm|vận\\s*hành\\s*an\\s*toàn)\\b',
    '\\b(?:thu\\s*hút\\s*vốn\\s*f\\s*d\\s*i|môi\\s*trường\\s*đầu\\s*tư|ưu\\s*đãi\\s*ngân\\s*sách|vốn\\s*vốn\\s*đầu\\s*tư\\s*công|giải\\s*ngân|tiến\\s*độ\\s*xây\\s*lắp)\\b',
    '\\b(?:tăng\\s*cường\\s*kiểm\\s*tra|giám\\s*sát\\s*xử\\s*lý|đúng\\s*trình\\s*tự|pháp\\s*luật\\s*hiện\\s*hành)\\b',
    '\\b(?:bánh\\s*đậu\\s*xanh|chè\\s*tân\\s*cương|kẹo\\s*cu\\s*đơ|bánh\\s*pía|mè\\s*xửng|thương\\s*hiệu\\s*truyền\\s*thống|nghệ\\s*nhân\\s*vị\\s*nguyên)\\b',
    '\\b(?:đăng\\s*ký\\s*kết\\s*hôn|xác\\s*nhận\\s*độc\\s*thân|thay\\s*đổi\\s*hộ\\s*tịch|trích\\s*lục\\s*bản\\s*sao|công\\s*dân\\s*số)\\b',
    '\\b(?:hiệu\\s*suất\\s*quang\\s*điện|i\\s*n\\s*v\\s*e\\s*r\\s*t\\s*e\\s*r|hệ\\s*thống\\s*lưu\\s*trữ|pin\\s*mặt\\s*trời|vệ\\s*sinh\\s*tấm\\s*pin|bảo\\s*trì\\s*điện\\s*mặt\\s*trời|hotspot)\\b',
    '\\b(?:chương\\s*trình\\s*liên\\s*kết|hợp\\s*tác\\s*đào\\s*tạo|nghiên\\s*cứu\\s*khoa\\s*học|công\\s*bố\\s*quốc\\s*tế)\\b',
    '\\b(?:phong\\s*trào\\s*thể\\s*thao|giải\\s*chạy\\s*marathon|phong\\s*trào\\s*cơ\\s*sở|nâng\\s*cao\\s*sức\\s*khỏe|vận\\s*động\\s*toàn\\s*dân)\\b',
    '\\b(?:hành\\s*tỏi\\s*lý\\s*sơn|quế\\s*trà\\s*bồng|hồi\\s*lạng\\s*sơn|tiêu\\s*chư\\s*sê|hạt\\s*điều\\s*bình\\s*phước|đặc\\s*sản\\s*tiêu\\s*biểu|nguyên\\s*liệu\\s*quý|vùng\\s*nguyên\\s*liệu)\\b',
    '\\b(?:nhận\\s*con\\s*nuôi|cha\\s*mẹ\\s*nuôi|thủ\\s*tục\\s*nhận\\s*nuôi|quyền\\s*và\\s*nghĩa\\s*vụ|xác\\s*nhận\\s*nuôi\\s*dưỡng|đăng\\s*ký\\s*nuôi\\s*con\\s*nuôi|pháp\\s*luật\\s*hôn\\s*nhân)\\b',
    '\\b(?:xuất\\s*khẩu\\s*chính\\s*ngạch|tiểu\\s*ngạch|ủy\\s*thác\\s*xuất\\s*khẩu|thủ\\s*tục\\s*hải\\s*quan|logistics\\s*xuất\\s*khẩu|chứng\\s*nhận\\s*kiểm\\s*dịch|quota\\s*thuế\\s*quan)\\b',
    '\\b(?:cảm\\s*biến\\s*áp\\s*suất|bộ\\s*điều\\s*khiển\\s*logic|plc|hệ\\s*thống\\s*mạng\\s*công\\s*nghiệp|truyền\\s*thông\\s*modbus|giám\\s*sát\\s*số|tối\\s*ưu\\s*quy\\s*trình)\\b',
    '\\b(?:chương\\s*trình\\s*hành\\s*động|nghị\\s*quyết\\s*đại\\s*hội|đẩy\\s*mạnh\\s*thi\\s*đua|hoàn\\s*thành\\s*xuất\\s*sắc|nhân\\s*rộng\\s*mô\\s*hình)\\b',
    '\\b(?:mực\\s*một\\s*nắng|tôm\\s*hùm\\s*bình\\s*ba|cua\\s*cà\\s*mau|sò\\s*huyết\\s*ô\\s*loan|chả\\s*mực\\s*hạ\\s*long|đặc\\s*sản\\s*biển|đánh\\s*bắt\\s*xa\\s*bờ|hải\\s*sản\\s*tươi\\s*sống)\\b',
    '\\b(?:nhập\\s*quốc\\s*tịch|thôi\\s*quốc\\s*tịch|việt\\s*kiều|thị\\s*thực\\s*điện\\s*tử|e-visa|hộ\\s*chiếu\\s*phổ\\s*thông|người\\s*nước\\s*ngoài\\s*tại\\s*việt\\s*nam|định\\s*cư)\\b',
    '\\b(?:quy\\s*tắc\\s*phòng\\s*cháy|thiết\\s*bị\\s*cứu\\s*hỏa|chuông\\s*báo\\s*cháy|vòi\\s*phun\\s*tự\\s*động|thang\\s*thoát\\s*hiểm)\\b',
    '\\b(?:tinh\\s*thần\\s*khởi\\s*nghiệp|chương\\s*trình\\s*vườn\\s*ươm\\s*tạo|hỗ\\s*trợ\\s*doanh\\s*nghiệp|đối\\s*mới\\s*sáng\\s*tạo|vốn\\s*đầu\\s*tư\\s*mạo\\s*hiểm|angel\\s*investor)\\b',
    '\\b(?:quy\\s*định\\s*pháp\\s*luật)\\b',
    '\\b(?:rượu\\s*mẫu\\s*sơn|rượu\\s*gò\\s*công|bia\\s*hơi\\s*hà\\s*nội|cà\\s*phê\\s*robusta|cà\\s*phê\\s*arabica|trà\\s*tà\\s*xùa|thương\\s*hiệu\\s*đồ\\s*uống|vùng\\s*nguyên\\s*liệu\\s*chè)\\b',
    '\\b(?:trợ\\s*giúp\\s*pháp\\s*lý|luật\\s*sư\\s*chỉ\\s*định|miễn\\s*phí\\s*dịch\\s*vụ|hỗ\\s*trợ\\s*pháp\\s*luật|tư\\s*vấn\\s*pháp\\s*lý\\s*lưu\\s*động|phổ\\s*biến\\s*giáo\\s*dục\\s*pháp\\s*luật)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*xuất\\s*khẩu|chứng\\s*chỉ\\s*chất\\s*lượng\\s*iso|rào\\s*cản\\s*kỹ\\s*thuật|thông\\s*quan\\s*hàng\\s*hóa\\s*tại\\s*cửa\\s*khẩu|chứng\\s*nhận\\s*nguồn\\s*gốc)\\b',
    '\\b(?:thang\\s*máy\\s*tốc\\s*độ\\s*cao|phòng\\s*máy\\s*thang\\s*máy|hệ\\s*thống\\s*điều\\s*khiển\\s*tầng|cửa\\s*tầng\\s*tự\\s*động)\\b',
    '\\b(?:tuyên\\s*dương\\s*điển\\s*hình|nghị\\s*quyết|quY\\s*định)\\b',
    '\\b(?:hoa\\s*đào\\s*nhật\\s*tân|hoa\\s*mai\\s*bình\\s*định|lan\\s*đột\\s*biến|trầm\\s*hương|cây\\s*cảnh\\s*bonsai|nghệ\\s*thuật\\s*tạo\\s*hình\\s*cây|triển\\s*lãm\\s*sinh\\s*vật\\s*cảnh)(?!.*(?:khôi\\s*phục|hồi\\s*sinh|lũ|bão|ngập|thiên\\s*tai))\\b',
    '\\b(?:trách\\s*nhiệm\\s*nghề\\s*nghiệp|bảo\\s*hiểm\\s*trách\\s*nhiệm|vi\\s*phạm\\s*đạo\\s*đức\\s*nghề|đình\\s*chỉ\\s*hành\\s*nghề|thu\\s*hồi\\s*thẻ\\s*luật\\s*sư|khiếu\\s*nại\\s*tố\\s*tụng)\\b',
    '\\b(?:b\\s*m\\s*s|i\\s*o\\s*t\\s*tòa\\s*nhà|điều\\s*hòa\\s*trung\\s*tâm\\s*chiller|hệ\\s*thống\\s*v\\s*r\\s*v|quản\\s*lý\\s*năng\\s*lượng|tự\\s*động\\s*hóa\\s*tòa\\s*nhà|nhà\\s*thông\\s*minh)\\b',
    '\\b(?:chương\\s*trình\\s*hợp\\s*tác\\s*quốc\\s*tế|ký\\s*kết\\s*m\\s*o\\s*u)\\b',
    '\\b(?:phấn\\s*đấu\\s*đạt\\s*chuẩn|nông\\s*thôn\\s*mới\\s*nâng\\s*cao|gương\\s*sáng\\s*tiêu\\s*biểu)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|cứu\\s*người|lũ|bão|ngập|thiên\\s*tai))\\b',
    '\\b(?:đền\\s*hùng|chùa\\s*hương|yên\\s*tử|lễ\\s*hội\\s*truyền\\s*thống|sắc\\s*phong|di\\s*tích\\s*lịch\\s*sử|trẩy\\s*hội)\\b',
    '\\b(?:thù\\s*lao\\s*luật\\s*sư|hợp\\s*đồng\\s*dịch\\s*vụ\\s*pháp\\s*lý|chi\\s*phí\\s*tố\\s*tụng|thụ\\s*lý\\s*vụ\\s*án|phân\\s*xử\\s*tranh\\s*chấp)\\b',
    '\\b(?:bhyt|chế\\s*độ\\s*thai\\s*sản)\\b',
    '\\b(?:robot\\s*lau\\s*kính|hệ\\s*thống\\s*gondola|bảo\\s*trì\\s*mặt\\s*dựng|kiểm\\s*định\\s*thiết\\s*bị|quản\\s*lý\\s*tòa\\s*nhà)\\b',
    '\\b(?:đẩy\\s*mạnh\\s*tuyên\\s*truyền|xây\\s*dựng\\s*đời\\s*sống|phong\\s*trào\\s*tiên\\s*phong|gương\\s*mẫu\\s*thực\\s*hiện|hoàn\\s*thành\\s*nhiệm\\s*vụ)\\b',
    '\\b(?:gỗ\\s*đồng\\s*kỵ|gỗ\\s*la\\s*xuyên|khảm\\s*trai\\s*chuyên\\s*mỹ|mỹ\\s*nghệ\\s*thiết\\s*kế|nghệ\\s*nhân\\s*bàn\\s*tay\\s*vàng|làng\\s*nghề\\s*tiêu\\s*biểu)\\b',
    '\\b(?:ly\\s*hôn\\s*thuận\\s*tình|phân\\s*chia\\s*tài\\s*sản\\s*chung|nhân\\s*thân|hộ\\s*khẩu)\\b',
    '\\b(?:hòa\\s*giải\\s*viên|trung\\s*tâm\\s*trọng\\s*tài|quy\\s*trình\\s*hòa\\s*giải|thỏa\\s*thuận\\s*dân\\s*sự|nhân\\s*chứng\\s*vật\\s*chứng|người\\s*có\\s*quyền\\s*lợi\\s*nghĩa\\s*vụ)\\b',
    '\\b(?:chiếu\\s*sáng\\s*mỹ\\s*thuật|hệ\\s*thống\\s*dali|đèn\\s*led\\s*pixel|hiệu\\s*ứng\\s*ánh\\s*sáng|kịch\\s*bản\\s*chiếu\\s*sáng|trang\\s*trí\\s*đô\\s*thị|ánh\\s*sáng\\s*vẻ\\s*đẹp)\\b',
    '\\b(?:tăng\\s*cường\\s*kỷ\\s*luật|siết\\s*chặt\\s*quản\\s*lý)\\b',
    '\\b(?:sóng\\s*hấp\\s*dẫn|năng\\s*lượng\\s*tối|lỗ\\s*sâu|cơ\\s*học\\s*lượng\\s*tử|vật\\s*lý\\s*hạt|gia\\s*tốc\\s*hạt)\\b',
    '\\b(?:khiếu\\s*nại\\s*hành\\s*chính|quyết\\s*định\\s*hành\\s*chính|thời\\s*hiệu\\s*khiếu\\s*nại|giải\\s*quyết\\s*tố\\s*cáo|tòa\\s*án\\s*hành\\s*chính|phán\\s*quyết\\s*cuối\\s*cùng)\\b',
    '\\b(?:hợp\\s*tác\\s*đa\\s*phương|diễn\\s*đàn\\s*an\\s*ninh|đối\\s*thoại\\s*chiến\\s*lược|biên\\s*bản\\s*thỏa\\s*thuận|quan\\s*hệ\\s*đối\\s*ngoại|vị\\s*thế\\s*quốc\\s*gia)\\b',
    '\\b(?:quy\\s*trình\\s*vận\\s*hành|ISO\\s*\\d+)\\b',
    '\\b(?:tuyên\\s*dương\\s*thành\\s*tích|huân\\s*chương\\s*lao\\s*động|bằng\\s*khen\\s*chính\\s*phủ|gương\\s*điển\\s*hình\\s*tiên\\s*tiến|phát\\s*huy\\s*sức\\s*mạnh)\\b',
    '\\b(?:hạnh\\s*phúc\\s*quanh\\s*ta|tổ\\s*ấm\\s*việt|gia\\s*đình\\s*và\\s*pháp\\s*luật|giá\\s*trị\\s*truyền\\s*thống|đạo\\s*đức\\s*lối\\s*sống|nếp\\s*sống\\s*văn\\s*minh)\\b',
    '\\b(?:phụ\\s*nữ\\s*hiện\\s*đại|nam\\s*giới\\s*bản\\s*lĩnh|giữ\\s*lửa\\s*hạnh\\s*phúc|bí\\s*quyết\\s*gia\\s*đình|mối\\s*quan\\s*hệ\\s*bền\\s*chặt|tâm\\s*lý\\s*gia\\s*đình)\\b',
    '\\b(?:hệ\\s*thống\\s*cấp\\s*thoát\\s*nước|trạm\\s*bơm\\s*tăng\\s*áp|bể\\s*xử\\s*lý\\s*nước\\s*thải|đường\\s*ống\\s*hdpe|van\\s*giảm\\s*áp|cột\\s*áp|hố\\s*ga\\s*thông\\s*minh)\\b',
    '\\b(?:chiến\\s*lược\\s*quốc\\s*gia|trọng\\s*tâm\\s*kinh\\s*tế|mục\\s*tiêu\\s*tổng\\s*quát|nhiệm\\s*vụ\\s*đột\\s*phá)\\b',
    '\\b(?:hoàn\\s*thành\\s*vượt\\s*mức)\\b',
    '\\b(?:sổ\\s*tay\\s*văn\\s*hóa|câu\\s*chuyện\\s*giáo\\s*dục|nhật\\s*ký\\s*người\\s*đi\\s*đường|văn\\s*hóa\\s*giao\\s*thông|ý\\s*thức\\s*công\\s*dân|rèn\\s*luyện\\s*nhân\\s*cách|giá\\s*trị\\s*sống)\\b',
    '\\b(?:dư\\s*luận\\s*xã\\s*hội|lên\\s*án\\s*hành\\s*vi|phản\\s*ứng\\s*cộng\\s*đồng|nghĩa\\s*vụ\\s*trách\\s*nhiệm|chuẩn\\s*mực\\s*đạo\\s*đức)\\b',
    '\\b(?:bồn\\s*trộn\\s*bê\\s*tông|cánh\\s*khuấy|hệ\\s*thống\\s*truyền\\s*động|phụ\\s*gia\\s*bê\\s*tông|lưu\\s*hóa|đúc\\s*sẵn)\\b',
    '\\b(?:nghị\\s*quyết\\s*phát\\s*triển|định\\s*hướng\\s*tầm\\s*nhìn|ưu\\s*tiên\\s*đầu\\s*tư|hạ\\s*tầng\\s*kỹ\\s*thuật|đồng\\s*bộ\\s*hiện\\s*đại)\\b',
    '\\b(?:thi\\s*đua\\s*yêu\\s*nước|kế\\s*hoạch\\s*đề\\s*ra)\\b',
    '\\b(?:quỹ\\s*thiện\\s*tâm|quỹ\\s*hy\\s*vọng|quỹ\\s*vì\\s*người\\s*nghèo|chương\\s*trình\\s*tài\\s*trợ|tấm\\s*lòng\\s*vàng|trao\\s*tặng\\s*quà)(?!\\s*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở))\\b',
    '\\b(?:công\\s*chứng\\s*số|ký\\s*số)\\b',
    '\\b(?:hội\\s*đông\\s*y|cây\\s*thuốc\\s*nam|vườn\\s*dược\\s*liệu|hải\\s*thượng\\s*lãn\\s*ông|tuệ\\s*tĩnh|y\\s*học\\s*cổ\\s*truyền|châm\\s*cứu|bấm\\s*huyệt)\\b',
    '\\b(?:đạo\\s*đức\\s*công\\s*vụ|trách\\s*nhiệm\\s*người\\s*đứng\\s*đầu|kiểm\\s*soát\\s*quyền\\s*lực|phòng\\s*chống\\s*tham\\s*nhũng|lãng\\s*phí)\\b',
    '\\b(?:kiểm\\s*tra\\s*sát\\s*hạch|đường\\s*lối\\s*chính\\s*sách|nghị\\s*quyết\\s*đảng)\\b',
    '\\b(?:niềm\\s*tin\\s*và\\s*khát\\s*vọng|góc\\s*nhìn\\s*thời\\s*đại|nhịp\\s*đập\\s*kinh\\s*tế|thế\\s*giới\\s*đó\\s*đây|chuyện\\s*của\\s*sao|bật\\s*mí\\s*bí\\s*mật|cận\\s*cảnh\\s*quy\\s*trình|khám\\s*phá\\s*thực\\s*tế)\\b',
    '\\b(?:món\\s*hời\\s*đầu\\s*tư|dòng\\s*vốn\\s*lớn|thị\\s*trường\\s*sôi\\s*động|chốt\\s*quyền\\s*nhận\\s*cổ\\s*tức|niêm\\s*yết\\s*sàn|ipo)\\b',
    '\\b(?:tư\\s*duy\\s*triệu\\s*phú|làm\\s*giàu\\s*không\\s*khó|nghỉ\\s*hưu\\s*sớm|kế\\s*hoạch\\s*chi\\s*tiêu|quản\\s*lý\\s*tài\\s*sản)\\b',
    '\\b(?:thành\\s*lập\\s*doanh\\s*nghiệp|giấy\\s*phép\\s*điều\\s*kiện|hợp\\s*quy\\s*kỹ\\s*thuật|kiểm\\s*định\\s*độc\\s*lập|chất\\s*lượng\\s*vượt\\s*trội|thương\\s*hiệu\\s*uy\\s*tín)\\b',
    '\\b(?:kết\\s*quả\\s*mong\\s*đợi)\\b',
    '\\b(?:lập\\s*vi\\s*bằng|niêm\\s*phong\\s*tài\\s*sản|kê\\s*biên\\s*phát\\s*mại|thông\\s*báo\\s*cưỡng\\s*chế|vi\\s*bằng\\s*ghi\\s*nhận)\\b',
    '\\b(?:quạt\\s*chàng\\s*sơn|giấy\\s*dó|tranh\\s*điệp|lụa\\s*vạn\\s*phúc|gốm\\s*bát\\s*tràng|di\\s*sản\\s*văn\\s*hóa\\s*phi\\s*vật\\s*thể)\\b',
    '\\b(?:thanh\\s*tra\\s*công\\s*vụ|kỷ\\s*luật\\s*hành\\s*chính|giải\\s*quyết\\s*đơn\\s*thư|tiếp\\s*công\\s*dân|đối\\s*thoại\\s*trực\\s*tiếp|tháo\\s*gỡ\\s*vướng\\s*mắc)\\b',
    '\\b(?:công\\s*nghệ\\s*tự\\s*động|phần\\s*mềm\\s*quản\\s*trị|hệ\\s*sinh\\s*thái\\s*số)\\b',
    '\\b(?:tăng\\s*cường\\s*trách\\s*nhiệm|siết\\s*chặt\\s*kỷ\\s*cương|kiểm\\s*tra\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*sai\\s*phạm|đúng\\s*quy\\s*định)\\b',
    '\\b(?:kiểu\\s*dáng\\s*công\\s*nghiệp|sở\\s*hữu\\s*trí\\s*tuệ|bảo\\s*hộ\\s*thương\\s*hiệu|đăng\\s*ký\\s*nhãn\\s*hiệu|vi\\s*phạm\\s*bản\\s*quyền|tác\\s*quyền)\\b',
    '\\b(?:hiệp\\s*hội\\s*doanh\\s*nghiệp|phòng\\s*thương\\s*mại|vcci|liên\\s*đoàn\\s*lao\\s*động|hội\\s*liên\\s*hiệp\\s*phụ\\s*nữ|đoàn\\s*thanh\\s*niên)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:đan\\s*lát|thêu\\s*ren|móc\\s*len|may\\s*vá|đồ\\s*handmade|quà\\s*tặng\\s*thủ\\s*công|trang\\s*trí\\s*bàn\\s*tiệc|tổ\\s*chức\\s*sự\\s*kiện)\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|bhyt|chế\\s*độ\\s*thai\\s*sản|hưu\\s*trí|trợ\\s*cấp\\s*thất\\s*nghiệp|an\\s*sinh\\s*xã\\s*hội)\\b',
    '\\b(?:triển\\s*khai\\s*nhiệm\\s*vụ|tổng\\s*kết\\s*công\\s*tác|phát\\s*động\\s*thi\\s*đua|khen\\s*thưởng\\s*đột\\s*xuất|huy\\s*hiệu\\s*đảng)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|phòng\\s*chống\\s*thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:bất\\s*cập|vướng\\s*mắc|kiến\\s*nghị\\s*cử\\s*tri|phản\\s*hồi\\s*dư\\s*luận|phản\\s*biện\\s*xã\\s*hội|vấn\\s*đề\\s*nóng|câu\\s*chuyện\\s*cảnh\\s*giác)\\b',
    '\\b(?:văn\\s*hóa\\s*giao\\s*thông|văn\\s*hóa\\s*đọc|văn\\s*minh\\s*đô\\s*thị|đạo\\s*đức\\s*nghề\\s*nghiệp|nhân\\s*cách|lối\\s*sống|kỹ\\s*năng\\s*mềm|tư\\s*duy\\s*tích\\s*cực)\\b',
    '\\b(?:lấn\\s*chiếm\\s*lòng\\s*lề\\s*đường|trật\\s*tự\\s*đô\\s*thị|vỉ\\s*hè\\s*thông\\s*thoáng|vệ\\s*sinh\\s*môi\\s*trường\\s*khu\\s*phố|tổ\\s*tự\\s*quản|camera\\s*an\\s*ninh\\s*phường)\\b',
    '\\b(?:ngày\\s*hội\\s*đại\\s*đoàn\\s*kết|hội\\s*thảo\\s*khoa\\s*học|diễn\\s*đàn\\s*trẻ\\s*em|đại\\s*hội\\s*hội\\s*khuyến\\s*học|clb\\s*hưu\\s*trí|sinh\\s*hoạt\\s*hè)\\b',
    '\\b(?:phí\\s*dịch\\s*vụ\\s*chung\\s*cư|ban\\s*quản\\s*trị\\s*nhà|họp\\s*dân\\s*cư|quy\\s*chế\\s*phát\\s*ngôn|thủ\\s*tục\\s*hành\\s*chính\\s*công|một\\s*cửa\\s*liên\\s*thông)\\b',
    '\\b(?:noel|giáng\\s*sinh|tết\\s*dương\\s*lịch|năm\\s*mới|chúc\\s*mừng|quà\\s*tặng|khuyến\\s*mãi|du\\s*xuân|đón\\s*xuân|vui\\s*xuân|chơi\\s*xuân|xuân\\s*về|chợ\\s*xuân|mùa\\s*xuân|cây\\s*cảnh|chơi\\s*tết|bính\\s*ngọ|mai\\s*vàng|đào\\s*phai|quất\\s*cảnh|lăng\\s*ông|cúng|thắp\\s*hương|trẩy\\s*hội|bưởi\\s*diễn|đặc\\s*sản|phố\\s*đêm|hoa\\s*hậu|người\\s*mẫu)(?!.*(?:bão|lũ|mưa|thời\\s*tiết|lạnh|rét|tuyết|rốn\\s*lũ|tái\\s*thiết|hồi\\s*sinh|khắc\\s*phục|vạn\\s*xuân))\\b',
    '\\b(?:chợ\\s*phiên|không\\s*gian\\s*văn\\s*hóa|lượng\\s*khách\\s*du\\s*lịch|điểm\\s*đến\\s*hấp\\s*dẫn|check-in|sống\\s*ảo|đồi\\s*cỏ|khu\\s*du\\s*lịch|nghỉ\\s*dưỡng|vui\\s*chơi)(?!.*(?:mắc\\s*kẹt|cô\\s*lập|lũ|bão|sạt\\s*lở|thiên\\s*tai|cuốn\\s*trôi|hư\\s*hỏng))\\b',
    '\\b(?:dâng\\s*hương|lễ\\s*hội|khai\\s*mạc|bế\\s*mạc|kỷ\\s*niệm\\s*ngày|lễ\\s*kỷ\\s*niệm|tưởng\\s*niệm|tặng\\s*bằng\\s*khen|trao\\s*bằng|ghi\\s*công|liệt\\s*sĩ)(?!.*(?:nạn\\s*nhân|bão|lũ|thiên\\s*tai|cứu\\s*hộ|hy\\s*sinh\\s*khi\\s*làm\\s*nhiệm\\s*vụ))\\b',
    '\\b(?:tuyển\\s*sinh|điểm\\s*chuẩn|học\\s*phí|tự\\s*chủ\\s*đại\\s*học|kỳ\\s*thi\\s*tốt\\s*nghiệp|học\\s*sinh\\s*giỏi|đi\\s*học\\s*thêm|làm\\s*thêm\\s*dịp\\s*hè|vào\\s*lớp\\s*1|nghỉ\\s*học)(?!.*(?:bão|lũ|mưa|thiên\\s*tai|ngập|sạt\\s*lở|giông|phòng\\s*tránh))\\b',
    '\\b(?:nghỉ\\s*hưu|lương\\s*hưu|trợ\\s*cấp\\s*xã\\s*hội|tinh\\s*giản\\s*biên\\s*chế|sắp\\s*xếp\\s*tổ\\s*chức|bảo\\s*hiểm\\s*xã\\s*hội|lương\\s*cơ\\s*bản|chính\\s*sách\\s*đối\\s*với)(?!.*(?:khắc\\s*phục|hỗ\\s*trợ\\s*bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:tăng\\s*lương|giảm\\s*lương|xếp\\s*lương|trả\\s*lương|nợ\\s*lương|lương\\s*tối\\s*thiểu|phụ\\s*cấp\\s*lương|bình\\s*ổn\\s*giá)(?!.*(?:khắc\\s*phục|hỗ\\s*trợ|thiên\\s*tai))\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|bhtn|biên\\s*chế|công\\s*chức|viên\\s*chức|sổ\\s*bhxh|chốt\\s*sổ|bảo\\s*hiểm\\s*thất\\s*nghiệp|bảo\\s*hiểm\\s*bắt\\s*buộc)\\b',
    '\\b(?:gaza|hamas|israel|ukraine|nga|tên\\s*lửa|xung\\s*đột\\s*vũ\\s*trang|chính\\s*phủ\\s*mỹ|đóng\\s*cửa|iran|trung\\s*đông|beirut|lebanon|houthi)(?!.*(?:công\\s*dân\\s*việt\\s*nam|người\\s*việt|ảnh\\s*hưởng\\s*tới\\s*việt\\s*nam|(?:hỗ\\s*trợ|cứu\\s*trợ|viện\\s*trợ)\\s*.*việt\\s*nam|sạt\\s*lở|ngập\\s*lụt|bão|lũ|thiên\\s*tai|khẩn\\s*cấp|tình\\s*huống|thảm\\s*họa))\\b',
    '\\b(?:donald\\s*trump|joe\\s*biden|nhà\\s*trắng|lầu\\s*năm\\s*góc|bầu\\s*cử\\s*mỹ|tổng\\s*thống\\s*mỹ|putin|zelensky)\\b',
    '\\b(?:động\\s*đất\\s*tại\\s*(?:nhật|đài|tư|trung|mỹ|indo|philip|nepal|thổ|maroc|nam\\s*phi|lào(?!\\s*cai)))\\b',
    '\\b(?:giải\\s*tứ\\s*hùng|v-league|bóng\\s*đá|thể\\s*thao|lượt\\s*trận|giải\\s*đấu)\\b',
    '\\b(?:đồng\\s*bộ\\s*dữ\\s*liệu|trợ\\s*lý\\s*ảo|công\\s*dân\\s*số|số\\s*hóa|chuyển\\s*đổi\\s*số|đề\\s*án\\s*nhân\\s*tài)\\b',
    '\\b(?:tìm\\s*kiếm\\s*thông\\s*tin|công\\s*cụ\\s*tìm\\s*kiếm)(?!\\s*(?:cứu\\s*nạn|nạn\\s*nhân))\\b',
    '\\b(?:rác\\s*thải|nhựa|bao\\s*bì)(?!\\s*(?:ngập|ung\\s*ứ|sau\\s*bão|do\\s*lũ))\\b',
    '\\b(?:giải\\s*cứu\\s*nạn\\s*nhân\\s*bị\\s*bắt\\s*cóc|giải\\s*cứu\\s*con\\s*tin|giải\\s*cứu\\s*người\\s*nước\\s*ngoài)(?!.*(?:bão|lũ|thiên\\s*tai|sạt\\s*lở))\\b',
    '\\b(?:tổng\\s*duyệt|hợp\\s*luyện|thực\\s*tập\\s*phương\\s*án|hội\\s*thao\\s*nghiệp\\s*vụ|huấn\\s*luyện\\s*nghiệp\\s*vụ|diễn\\s*tập\\s*phương\\s*án|trải\\s*nghiệm\\s*thực\\s*hành|tập\\s*huấn\\s*kỹ\\s*năng)(?!\\s*(?:thực\\s*tế|trong\\s*mưa\\s*bão|cứu\\s*người\\s*thật))\\b',
    '\\b(?:xóa\\s*nhà\\s*tạm|nhà\\s*dột\\s*nát|hỗ\\s*trợ\\s*nhà\\s*ở|nhà\\s*đại\\s*đoàn\\s*kết|an\\s*cư\\s*lạc\\s*nghiệp)(?!\\s*(?:vùng\\s*lũ|rốn\\s*lũ|sau\\s*bão|thiên\\s*tai|sạt\\s*lở|nguy\\s*cơ|di\\s*dời))\\b',
    '\\b(?:ngộ\\s*độc\\s*thực\\s*phẩm|bánh\\s*mì|bếp\\s*ăn\\s*tập\\s*thể|suất\\s*ăn|an\\s*toàn\\s*thực\\s*phẩm|vệ\\s*sinh\\s*thực\\s*phẩm|dịch\\s*bệnh|sốt\\s*xuất\\s*huyết|bệnh\\s*lao|sa\\s*mạc\\s*hóa)(?!.*(?:do|vì|bởi|sau)\\s*(?:bão|lũ|thiên\\s*tai|mưa|ngập))\\b',
    '\\b(?:vi\\s*phạm\\s*giao\\s*thông|phạt\\s*nguội|tước\\s*giấy\\s*phép|nồng\\s*độ\\s*cồn|biển\\s*số\\s*xe|đăng\\s*kiểm|xe\\s*xăng|xe\\s*điện|khí\\s*thải|hết\\s*xăng)(?!.*(?:đảo\\s*phú\\s*quý|cô\\s*lập))\\b',
    '\\b(?:cục\\s*thuế|ngành\\s*thuế|nợ\\s*thuế|hoàn\\s*thuế|hành\\s*chính\\s*công|trung\\s*tâm\\s*phục\\s*vụ|dịch\\s*vụ\\s*công|chuyển\\s*đổi\\s*số)\\b',
    '\\b(?:buôn\\s*lậu|gian\\s*lận\\s*thương\\s*mại|hàng\\s*giả|hàng\\s*nhái|hàng\\s*cấm|vận\\s*chuyển\\s*trái\\s*phép|hàng\\s*lậu)\\b',
    '\\b(?:phim\\s*truyện|chiếu\\s*phim|điện\\s*ảnh|liên\\s*hoan\\s*phim|tác\\s*phẩm\\s*nghệ\\s*thuật|triển\\s*lãm\\s*ảnh|ra\\s*mắt\\s*phim)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|tiết\\s*mục|hợp\\s*xướng|giải\\s*trí|phim\\s*trường|rạp\\s*chiếu\\s*phim|triển\\s*lãm|khai\\s*mạc|lễ\\s*hội|tuần\\s*lễ\\s*thời\\s*trang|sân\\s*khấu|biểu\\s*diễn|ca\\s*múa\\s*nhạc)\\b',
    '\\b(?:xả\\s*súng|nổ\\s*súng|đấu\\s*súng|thảm\\s*sát|khủng\\s*bố|đánh\\s*bom|giẫm\\s*đạp|chen\\s*lấn\\s*xô\\s*đẩy|biểu\\s*tình|bạo\\s*loạn)(?!\\s*(?:cứu\\s*trợ|hỗ\\s*trợ))\\b',
    '\\b(?:được\\s*mùa|mất\\s*giá|rớt\\s*giá|giải\\s*cứu\\s*nông\\s*sản|tiêu\\s*thụ\\s*kém|bí\\s*đầu\\s*ra|thương\\s*lái\\s*ép\\s*giá|cam\\s*sành|thanh\\s*long|dưa\\s*hấu|sầu\\s*riêng|vải\\s*thiều|thu\\s*hoạch)(?!\\s*(?:ngập|ung\\s*ứ|hư\\s*hỏng|rụng|gãy\\s*đổ|thiệt\\s*hại|mất\\s*trắng|sau|cứu|chạy)\\s*(?:do|vì|bởi|bão|lũ|thiên\\s*tai|mưa|thời\\s*tiết))\\b',
    '\\b(?:bọ\\s*xít|kiến\\s*ba\\s*khoang|ong\\s*đốt|rắn\\s*cắn|chó\\s*cắn|ngộ\\s*độc\\s*rượu|ngộ\\s*độc\\s*nấm)(?!\\s*(?:lũ|ngập|bão))\\b',
    '\\b(?:huyền\\s*sử|truyền\\s*thuyết|giai\\s*thoại|chứng\\s*nhân\\s*lịch\\s*sử|kỷ\\s*vật|hồi\\s*ký|tâm\\s*tình|tản\\s*mạn|góc\\s*nhìn|tam\\s*quốc|thục\\s*hán|lưu\\s*bị|quan\\s*vũ|tào\\s*tháo|tôn\\s*quyền|đại\\s*việt|sử\\s*ký)\\b',
    '\\b(?:dân\\s*tộc\\s*(?:mông|dao|tày|nùng|thái|lô\\s*lô)|văn\\s*hóa\\s*dân\\s*gian|làn\\s*điệu|điệu\\s*múa|then|cọi|páo\\s*dung|lễ\\s*hội|tín\\s*ngưỡng|thờ\\s*cúng|miếu|đền|chùa|di\\s*sản|phong\\s*tục|tập\\s*quán|làng\\s*nghề|nghệ\\s*nhân)(?!.*(?:sạt\\s*lở|lũ|bão|thiên\\s*tai|mưa\\s*lũ|khắc\\s*phục|thiệt\\s*hại|vỡ|chết\\s*người|thiệt\\s*mạng|tử\\s*vong|hồ\\s*chứa))\\b',
    '\\b(?:phẫu\\s*thuật|mổ|cấp\\s*cứu\\s*bệnh\\s*nhân|bệnh\\s*viện\\s*đa\\s*khoa|nguy\\s*kịch|vỡ\\s*tạng|vỡ\\s*tim|chạy\\s*thận|ecmo|lọc\\s*máu|đột\\s*quỵ|tai\\s*biến|cứu\\s*sống\\s*bệnh\\s*nhân|nhồi\\s*máu|ung\\s*thư|bàng\\s*quang|ruột\\s*thừa|sỏi\\s*thận|nhiễm\\s*nấm|ăn\\s*mòn\\s*xương|hiến\\s*tạng|ghép\\s*gan|ghép\\s*tim|thông\\s*tim|can\\s*thiệp\\s*mạch|hồi\\s*sinh\\s*sự\\s*sống|hỗ\\s*trợ\\s*chuyên\\s*môn|y\\s*khoa|tiểu\\s*ra\\s*máu|tập\\s*yoga)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|tai\\s*nạn\\s*thảm\\s*khốc|sập\\s*hầm|cháy\\s*lớn|giông\\s*bão|gặp\\s*nạn|đuối\\s*nước|ngập|mưa\\s*lũ))\\b',
    '\\b(?:phát\\s*hiện\\s*thi\\s*thể|xác\\s*chết|người\\s*đàn\\s*ông\\s*tử\\s*vong|án\\s*mạng|trọng\\s*án|truy\\s*nã|bắt\\s*giữ|ma\\s*túy|buôn\\s*lậu|vượt\\s*biên|đánh\\s*bạc|mại\\s*dâm|cướp\\s*giật|trộm\\s*cắp|đâm\\s*chém|hỗn\\s*chiến|vây\\s*ráp|nẹt\\s*pô|lạng\\s*lách|đua\\s*xe|quái\\s*xế|bốc\\s*đầu|cầm\\s*dao|đâm\\s*chết|truy\\s*sát|xả\\s*súng|mua\\s*bán\\s*người|đầu\\s*thú)\\b',
    '\\b(?:hiếp\\s*dâm|giao\\s*cấu|cưỡng\\s*bức|dâm\\s*ô|âu\\s*yếm|chuốc\\s*say|tưới\\s*xăng|phóng\\s*hỏa|án\\s*mạng|sát\\s*hại|treo\\s*cổ|dương\\s*tính|tạt\\s*sơn|đòi\\s*nợ|đập\\s*phá|xe\\s*công\\s*nghệ|gây\\s*rối\\s*trật\\s*tự|lừa\\s*đảo|mạo\\s*danh|bắt\\s*cóc\\s*online|tội\\s*phạm|phạm\\s*tội|đổi\\s*tiền\\s*mới|sổ\\s*tiết\\s*kiệm|mã\\s*độc\\s*tống\\s*tiền|con\\s*bạc|bảo\\s*vật\\s*quốc\\s*gia|cuộc\\s*gọi\\s*lạ|truy\\s*sát|tiệm\\s*tóc|chém\\s*bạn)\\b',
    '\\b(?:tín\\s*dụng\\s*đen|lừa\\s*đảo|bắt\\s*cóc\\s*online|nhảy\\s*lầu|tự\\s*sát|cầm\\s*dao|xông\\s*vào|vụ\\s*án|nhặt\\s*được\\s*tiền|trả\\s*lại\\s*người\\s*đánh\\s*rơi|pháo\\s*hoa|pháo\\s*nổ|tự\\s*chế\\s*pháo|thuốc\\s*nổ|vật\\s*liệu\\s*nổ)(?!.*(?:lũ|bão|trôi|sạt|thiên\\s*tai|mưa\\s*lũ|cuốn\\s*trôi|vùi\\s*lấp))\\b',
    '\\b(?:tai\\s*nạn\\s*lao\\s*động|sập\\s*giàn\\s*giáo|ngã\\s*giàn\\s*giáo|rơi\\s*từ\\s*tầng\\s*cao|điện\\s*giật|chập\\s*điện)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|sạt\\s*lở))\\b',
    '\\b(?:nhặt\\s*được\\s*tiền|trả\\s*lại\\s*người\\s*đánh\\s*rơi|pháo\\s*hoa|pháo\\s*nổ|tự\\s*chế\\s*pháo|thuốc\\s*nổ|vật\\s*liệu\\s*nổ)(?!.*(?:lũ|bão|trôi|sạt|thiên\\s*tai|mưa\\s*lũ|cuốn\\s*trôi|vùi\\s*lấp))\\b',
    '\\b(?:ngã\\s*vào\\s*gầm|cuốn\\s*vào\\s*gầm|kẹt\\s*trong\\s*cabin|cá\\s*ăn\\s*thịt|đuối\\s*nước\\s*thương\\s*tâm|tắm\\s*sông|tắm\\s*biển|rơi\\s*xuống\\s*sông)(?!.*(?:bão|lũ|lụt|mưa\\s*lớn|nước\\s*dâng|sạt\\s*lở))\\b',
    '\\b(?:cháy\\s*nhà|cháy\\s*xe|cháy\\s*xưởng|cháy\\s*chợ|hỏa\\s*hoạn\\s*tại)(?!.*(?:rừng|thảm\\s*thực\\s*vật|cứu\\s*hộ|thiên\\s*tai|pccc|dập\\s*lửa|trụ\\s*sở\\s*cảnh\\s*sát))\\b',
    '\\b(?:chim\\s*hồng\\s*hoàng|động\\s*vật\\s*quý\\s*hiếm|sách\\s*đỏ|thả\\s*về\\s*(?:rừng|biển|tự\\s*nhiên)|cứu\\s*hộ\\s*động\\s*vật|tê\\s*tê|rùa\\s*biển|cá\\s*thể|voọc|khỉ\\s*vàng)(?!.*(?:bão|lũ|lụt|sạt\\s*lở))\\b',
    '\\b(?:thống\\s*kê|báo\\s*cáo|tổng\\s*kết)\\s*(?:tình\\s*hình|số\\s*liệu)\\s*(?:tai\\s*nạn|giao\\s*thông|an\\s*ninh\\s*trật\\s*tự)(?!\\s*(?:do|vì|trong)\\s*(?:bão|lũ|thiên\\s*tai|mưa))\\b',
    '\\b(?:ốc\\s*thanh\\s*vân|showbiz|nghệ\\s*sĩ|hoạt\\s*động\\s*nghệ\\s*thuật|giải\\s*trí|hoa\\s*hậu|người\\s*đẹp|văn\\s*nghệ\\s*quần\\s*chúng|phong\\s*trào\\s*văn\\s*hóa|trò\\s*chuyện\\s*cùng|nhạc\\s*sĩ|tác\\s*giả|nhà\\s*thơ|tổ\\s*quốc\\s*và\\s*người\\s*lính|u22\\s*việt\\s*nam|sea\\s*games|lễ\\s*xuất\\s*quân|concert|cành\\s*cọ\\s*vàng|countdown|tượng\\s*bồ\\s*tát|hồi\\s*hương|xuất\\s*bản\\s*sách|ra\\s*mắt\\s*sách|lịch\\s*sử\\s*truyền\\s*thống|lịch\\s*sử\\s*lực\\s*lượng\\s*vũ\\s*trang)\\b',
    '\\b(?:bảo\\s*hiểm\\s*y\\s*tế|bhyt|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|thủ\\s*tục\\s*hành\\s*chính|dịch\\s*vụ\\s*công|trực\\s*tuyến|chuyển\\s*đổi\\s*số|số\\s*hóa|cổng\\s*dịch\\s*vụ\\s*công|cải\\s*cách\\s*tư\\s*pháp|thi\\s*hành\\s*án|tiếp\\s*dân|khiếu\\s*nại\\s*tố\\s*cáo|cung\\s*cầu\\s*lao\\s*động|kết\\s*nối\\s*cung\\s*cầu|ban\\s*nội\\s*chính|viện\\s*kiểm\\s*sát|tòa\\s*án|đoàn\\s*đại\\s*biểu|làm\\s*việc\\s*với|liên\\s*kết\\s*sản\\s*xuất|phê\\s*duyệt\\s*hỗ\\s*trợ)(?!.*(?:hỗ\\s*trợ|bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:chất\\s*độc\\s*da\\s*cam|nạn\\s*nhân\\s*da\\s*cam|dioxin)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|thảm\\s*họa))\\b',
    '\\b(?:thị\\s*trường|chứng\\s*khoán|cổ\\s*phiếu|vn-index|giá\\s*vàng|giá\\s*bạc|giá\\s*cà\\s*phê|tỷ\\s*giá|lãi\\s*suất|ngân\\s*hàng|tín\\s*dụng|vay\\s*vốn|doanh\\s*thu|lợi\\s*nhuận|xuất\\s*khẩu|nhập\\s*khẩu|kim\\s*ngạch|thương\\s*mại|bất\\s*động\\s*sản|đấu\\s*giá\\s*đất|sổ\\s*đỏ|thưởng\\s*tết|lì\\s*xì|phụ\\s*cấp\\s*ưu\\s*đãi|khung\\s*chính\\s*sách|chính\\s*sách\\s*thuế|nộp\\s*phạt|kích\\s*cầu|khấu\\s*trừ\\s*lương|xuất\\s*siêu|nhập\\s*siêu|kinh\\s*tế\\s*tư\\s*nhân|phong\\s*tỏa\\s*tài\\s*khoản|cưỡng\\s*chế\\s*thuế|nợ\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử)(?!.*(?:bão|lũ|thiệt\\s*hại|ủng\\s*hộ|hỗ\\s*trợ|ước\\s*tính|khắc\\s*phục|hư\\s*hỏng))\\b',
    '\\b(?:khám\\s*chữa\\s*bệnh|bệnh\\s*viện|bác\\s*sĩ|phẫu\\s*thuật|cấy\\s*ghép|nội\\s*soi|tư\\s*vấn\\s*sức\\s*khỏe|dinh\\s*dưỡng|làm\\s*đẹp|thẩm\\s*mỹ)(?!.*(?:cấp\\s*cứu|tai\\s*nạn|thương\\s*vong|sập|cháy|nổ|bão|lũ))\\b',
    '\\b(?:thưởng\\s*tết|quà\\s*tết|nghỉ\\s*tết|vé\\s*tết|hàng\\s*tết|sắm\\s*tết|chợ\\s*tết|đón\\s*tết|vui\\s*xuân|chúc\\s*tết|tết\\s*nguyên\\s*đán|lì\\s*xì|bánh\\s*chưng|mứt\\s*tết|hoa\\s*tết|du\\s*xuân|du\\s*lịch|khách\\s*sạn|resort|nghỉ\\s*dưỡng|check-in|sống\\s*ảo)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|thiên\\s*tai|bão|lũ|người\\s*nghèo|khó\\s*khăn|mắc\\s*kẹt|cô\\s*lập))\\b',
    '\\b(?:bảo\\s*dưỡng|sửa\\s*chữa|thợ\\s*sửa|lắp\\s*đặt|máy\\s*nước\\s*nóng|điều\\s*hòa|máy\\s*lạnh|tủ\\s*lạnh|máy\\s*giặt|vệ\\s*sinh\\s*máy|thợ\\s*hàn|thợ\\s*cơ\\s*khí|nhôm\\s*kính)(?!.*(?:bão|lũ|ngập|hư\\s*hại|tốc\\s*mái|sạt\\s*lở|cầu|đường|giao\\s*thông|hư\\s*hỏng))\\b',
    '\\b(?:galaxy\\s*z|iphone|ipad|macbook|logitech|samsung\\s*galaxy|oppo|xiaomi|ra\\s*mắt\\s*sản\\s*phẩm|công\\s*nghệ\\s*mới|trên\\s*tay|đập\\s*hộp|review|đánh\\s*giá\\s*xe|xe\\s*sang|siêu\\s*xe|zalo|nền\\s*tảng\\s*số|wi-fi|hao\\s*pin|công\\s*nghệ\\s*ai|hyperos|snapdragon|khung\\s*xương\\s*dephy|màn\\s*hình\\s*lili|điều\\s*chế\\s*ánh\\s*sáng|redmi|poco|ces\\s*2026|công\\s*nghiệp\\s*hỗ\\s*trợ|nội\\s*địa\\s*hóa|chuỗi\\s*giá\\s*trị|kỹ\\s*thuật\\s*số|trí\\s*tuệ\\s*nhân\\s*tạo|thử\\s*nghiệm\\s*ai|livestream|bán\\s*hàng\\s*online|thương\\s*mại\\s*điện\\s*tử|sàn\\s*tmdt|an\\s*ninh\\s*mạng|luật\\s*an\\s*ninh\\s*mạng|bluetti|charger)(?!.*(?:cứu\\s*hộ|cảnh\\s*báo|xe\\s*lội\\s*nước|cứu\\s*người|chế\\s*tạo|sáng\\s*chế|ứng\\s*phó|khẩn\\s*cấp|thiên\\s*tai))\\b',
    '\\b(?:tiền\\s*cổ|cổ\\s*vật|khảo\\s*cổ|ngôi\\s*mộ|di\\s*tích\\s*lịch\\s*sử|kho\\s*báu|đào\\s*được|phát\\s*hiện\\s*hầm|mộ\\s*cổ)(?!.*(?:sạt\\s*lở|hư\\s*hại|lũ|bão|cuốn\\s*trôi))\\b',
    '\\b(?:ứng\\s*phó|phòng\\s*chống|giảm\\s*thiểu)\\s*(?:biến\\s*đổi\\s*khí\\s*hậu|dịch\\s*bệnh|covid|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|lạm\\s*phát|suy\\s*thoái|khủng\\s*hoảng|bạo\\s*lực|xâm\\s*hại|tai\\s*nạn|thương\\s*mại|gian\\s*lận|tội\\s*phạm)(?!\\s*(?:và|với)\\s*(?:bão|lũ|thiên\\s*tai|mưa|ngập))\\b',
    '\\b(?:chuyển\\s*tiền\\s*nhầm|nhận\\s*lại\\s*tiền|giao\\s*dịch\\s*viên|tài\\s*khoản\\s*ngân\\s*hàng|sổ\\s*tiết\\s*kiệm|thẻ\\s*tín\\s*dụng|vay\\s*vốn\\s*ưu\\s*đãi|đáo\\s*hạn|sàn\\s*giao\\s*dịch\\s*vàng|tín\\s*dụng\\s*đen|đòi\\s*nợ\\s*thuê)\\b',
    '\\b(?:bảo\\s*hiểm\\s*(?:nhân\\s*thọ|phi\\s*nhân\\s*thọ|agribank|bảo\\s*việt|dai-ichi|manulife|prudential|aia|chubb|generali|hanwha|mb\\s*ageas|sun\\s*life|fw|cathay|liberty|pvi|bic|pti|vbi|mic)|mua\\s*bảo\\s*hiểm|bán\\s*bảo\\s*hiểm|tư\\s*vấn\\s*bảo\\s*hiểm|hợp\\s*đồng\\s*bảo\\s*hiểm)(?!.*(?:bồi\\s*thường\\s*thiệt\\s*hại\\s*do\\s*bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:người\\s*nộp\\s*thuế|cơ\\s*quan\\s*thuế|quyết\\s*toán\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử|chống\\s*thất\\s*thu|nợ\\s*thuế|hoàn\\s*thuế|thuế\\s*khoán|hộ\\s*kinh\\s*doanh)\\b',
    '\\b(?:từ\\s*trái\\s*tim\\s*đến\\s*trái\\s*tim|chương\\s*trình\\s*phẫu\\s*thuật|mổ\\s*tim|hở\\s*hàm\\s*ếch|nạn\\s*nhân\\s*chất\\s*độc\\s*da\\s*cam|khuyết\\s*tật|trẻ\\s*mồ\\s*côi|người\\s*cao\\s*tuổi\\s*neo\\s*đơn)\\b',
    '\\b(?:trao\\s*tặng\\s*nhà|nhà\\s*tình\\s*nghĩa|nhà\\s*đại\\s*đoàn\\s*kết|hỗ\\s*trợ\\s*sinh\\s*kế|tặng\\s*bò|trao\\s*vốn|nhặt\\s*được\\s*của\\s*rơi|trả\\s*lại\\s*tài\\s*sản|tấm\\s*lòng\\s*vàng|mạnh\\s*thường\\s*quân)(?!\\s*(?:cho|tại|vùng|người\\s*dân)\\s*(?:bão|lũ|thiên\\s*tai|sạt\\s*lở|ngập\\s*lụt|sau\\s*bão|tái\\s*thiết|khắc\\s*phục))\\b',
    '\\b(?:chương\\s*trình\\s*tình\\s*nguyện|mùa\\s*hè\\s*xanh|tiếp\\s*sức\\s*mùa\\s*thi|hiến\\s*máu\\s*tình\\s*nguyện|bát\\s*cháo\\s*tình\\s*thương|suất\\s*cơm\\s*miễn\\s*phí)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|cô\\s*lập|khắc\\s*phục|hỗ\\s*trợ\\s*bà\\s*con|sạt\\s*lở))\\b',
    '\\b(?:trao\\s*quà|tặng\\s*quà|hỗ\\s*trợ\\s*khó\\s*khăn|người\\s*nghèo|hộ\\s*nghèo|trẻ\\s*em\\s*nghèo|người\\s*khuyết\\s*tật|nạn\\s*nhân\\s*chất\\s*độc\\s*màu\\s*da\\s*cam)(?!.*(?:vùng\\s*bão|vùng\\s*lũ|rốn\\s*lũ|sau\\s*bão|bị\\s*thiệt\\s*hại|khắc\\s*phục\\s*hậu\\s*quả|triều\\s*cường|ngập|lụt|thiên\\s*tai|tốc\\s*mái|sập\\s*nhà|trôi|mưa\\s*lũ|sạt\\s*lở|chia\\s*cắt|cô\\s*lập|bị\\s*ảnh\\s*hưởng|tái\\s*thiết|ổn\\s*định|dân\\s*sinh|khẩn\\s*cấp))\\b',
    '\\b(?:bỏ\\s*nhà\\s*đi|rời\\s*khỏi\\s*nhà|tìm\\s*người\\s*thân|tìm\\s*trẻ\\s*lạc|bỏ\\s*đi\\s*không\\s*rõ|mất\\s*tích\\s*bí\\s*ẩn)\\b',
    '\\b(?:thiếu\\s*nữ\\s*mất\\s*tích|đi\\s*lạc|không\\s*thấy\\s*về|gia\\s*đình\\s*lo\\s*lắng|bỏ\\s*trốn\\s*cùng|tìm\\s*ông\\s*cụ|tìm\\s*bà\\s*cụ|rời\\s*khỏi\\s*địa\\s*phương|vắng\\s*mặt\\s*tại\\s*nơi\\s*cư\\s*trú)\\b',
    '\\b(?:hoa\\s*hậu|á\\s*hậu|người\\s*mẫu|showbiz|scandal|cát\\s*xê|thảm\\s*đỏ|sao\\s*việt|nam\\s*em|ngọc\\s*trinh|mỹ\\s*tâm|sơn\\s*tùng|hồ\\s*ngọc\\s*hà|trấn\\s*thành|trường\\s*giang|anh\\s*trai\\s*say\\s*hi|chị\\s*đẹp)\\b',
    '\\b(?:điểm\\s*chuẩn|nhập\\s*học|tốt\\s*nghiệp\\s*thpt|ôn\\s*thi|sĩ\\s*tử|trường\\s*chuyên|học\\s*bạ|xét\\s*tuyển\\s*đại\\s*học)\\b',
    '\\b(?:nghi\\s*lễ\\s*ngoại\\s*giao|quan\\s*hệ\\s*song\\s*phương|đón\\s*tiếp\\s*trọng\\s*thể|điện\\s*đàm|thư\\s*chúc\\s*mừng|quốc\\s*yến)\\b',
    '\\b(?:nâng\\s*lương|tăng\\s*lương|chuyển\\s*ngạch|xét\\s*tuyển|viên\\s*chức|công\\s*chức|thăng\\s*hạng|chức\\s*danh\\s*nghề\\s*nghiệp)\\b',
    '\\b(?:chế\\s*độ\\s*tuất|trợ\\s*cấp\\s*tuất|đóng\\s*bù\\s*bảo\\s*hiểm|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|lương\\s*cơ\\s*sở)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*trình\\s*độ|hạng\\s*CDNN|chứng\\s*chỉ\\s*hành\\s*nghề|giấy\\s*phép\\s*hành\\s*nghề)\\b',
    '\\b(?:thông\\s*báo\\s*tìm\\s*kiếm\\s*người\\s*vắng\\s*mặt|tuyên\\s*bố\\s*mất\\s*tích|tìm\\s*chủ\\s*sở\\s*hữu|niêm\\s*yết\\s*công\\s*khai)\\b',
    '\\b(?:luật\\s*đầu\\s*tư|luật\\s*việc\\s*làm|luật\\s*đất\\s*đai|luật\\s*kinh\\s*doanh|thủ\\s*tục\\s*hành\\s*chính|cải\\s*cách\\s*thể\\s*chế)\\b',
    '\\b(?:nổi\\s*lềnh\\s*bềnh|thi\\s*thể\\s*(?:nam|nữ|thanh\\s*niên)|nhảy\\s*cầu|chết\\s*đuối\\s*khi\\s*tắm|đuối\\s*nước\\s*khi\\s*tắm|tự\\s*tử|quyên\\s*sinh|nhảy\\s*lầu|uống\\s*thuốc\\s*sâu|treo\\s*cổ|đánh\\s*ghen|bạo\\s*lực\\s*học\\s*đường|xô\\s*xát|cãi\\s*vã)\\b',
    '\\b(?:thu\\s*hồi\\s*vũ\\s*khí|vật\\s*liệu\\s*nổ\\s*tự\\s*chế|công\\s*cụ\\s*hỗ\\s*trợ|giao\\s*nộp\\s*vũ\\s*khí)\\b',
    '\\b(?:súng\\s*in\\s*3d|chiêu\\s*trò\\s*lừa\\s*đảo|giả\\s*mạo\\s*tập\\s*đoàn|tuyển\\s*dụng\\s*việc\\s*làm|bóc\\s*trần\\s*thủ\\s*đoạn)\\b',
    '\\b(?:chặn\\s*đứng\\s*kế\\s*hoạch|bỏ\\s*trốn|kẻ\\s*sát\\s*nhân|truy\\s*bắt|ngừng\\s*bắn|thỏa\\s*thuận\\s*hòa\\s*bình|xung\\s*đột\\s*biên\\s*giới)\\b',
    '\\b(?:trí\\s*tuệ\\s*nhân\\s*tạo|artificial\\s*intelligence|ai\\s*generative|chatgpt|google\\s*ai|tích\\s*hợp\\s*ai|công\\s*cụ\\s*tìm\\s*kiếm|trình\\s*duyệt\\s*web|tấn\\s*công\\s*mạng|an\\s*ninh\\s*mạng|lừa\\s*đảo\\s*trực\\s*tuyến|mã\\s*độc|phần\\s*mềm\\s*gián\\s*điệp|hack|hacker|lỗ\\s*hổng\\s*bảo\\s*mật)\\b',
    '\\b(?:làm\\s*chả\\s*quế|đặc\\s*sản\\s*làng\\s*nghề|thực\\s*phẩm\\s*chức\\s*năng|orihiro|hành\\s*trình\\s*(\\d+|năm)|chăm\\s*sóc\\s*sức\\s*khỏe\\s*(?:từ|của))\\b',
    '\\b(?:kết\\s*quả\\s*tin\\s*tức\\s*cho\\s*từ\\s*khóa|tin\\s*tức\\s*tv|video\\s*nổi\\s*bật)\\b',
    '办国外文凭|QQ\\s*\\d+|fake\\s*diploma|degree|transcript|certificate\\s*online',
    '\\b(?:biên\\s*giới\\s*campuchia|biên\\s*giới\\s*thái\\s*lan|tranh\\s*chấp\\s*lãnh\\s*thổ)(?!\\s*(?:mưa|lũ|bão))\\b',
    '办\\w+\\s*假\\s*文\\s*凭|google\\s*bao\\s*ping|google\\s*rank|săn\\s*cá|nổ\\s*hũ|xổ\\s*số|quay\\s*thử|vé\\s*số|vietlott',
    '\\b(?:Fake\\s*diploma|Degree\\s*Transcript|University\\s*of\\s*.*fake|QQ\\s*\\d+|wechat\\s*id|telegram\\s*id)\\b',
    '\\b(?:8871\\.net\\.cn|54688\\.cc|56688\\.cc|57688\\.cc|237933801|QQ\\s*860)\\b',
    '\\b(?:ktv|massage|karaoke)\\s*(?:ôm|đào|tay\\s*vịn|gọi\\s*đào|nam\\s*ktv|boy\\s*bao|bao\\s*phòng)\\b',
    '\\b(?:làm\\s*bằng\\s*(?:đại\\s*học|cấp\\s*3)|chứng\\s*chỉ\\s*tiếng\\s*anh\\s*lấy\\s*ngay|bao\\s*đậu|giấy\\s*tờ\\s*giả)\\b',
    '\\b(?:giẫm\\s*đạp|đánh\\s*bom|khủng\\s*bố|xả\\s*súng|chiến\\s*sự|xung\\s*đột\\s*vũ\\s*trang)\\b',
    '\\b(?:kim\\s*cương|đá\\s*quý|trang\\s*sức|thời\\s*trang\\s*cao\\s*cấp|sàn\\s*diễn|người\\s*mẫu)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|kịch\\s*nói|phim\\s*điện\\s*ảnh|rạp\\s*phim|cà\\s*phê\\s*đường\\s*tàu|kho\\s*ảnh\\s*đẹp|website\\s*chia\\s*sẻ)\\b',
    '\\b(?:gây|tạo|cơn)\\s*bão\\s*(?:mạng|dư\\s*luận|giá|lòng|sale|khuyến\\s*mãi|chấn\\s*thương|tài\\s*chính|sa\\s*thải|truyền\\s*thông|cảm\\s*xúc|lợi\\s*nhuận|tín\\s*dụng|bất\\s*động\\s*sản|vàng|coin|crypto)\\b',
    '\\bbão\\s*(?:giá|lửa|đạn|sale|đêm)\\b',
    '\\bgây\\s*bão\\b(?!\\s*(?:lũ|lụt|diện\\s*rộng|biển|cấp|nhiệt\\s*đới))',
    '\\b(?:lá\\s*chắn|hệ\\s*thống)\\s*(?:tên\\s*lửa|phòng\\s*không|vòm\\s*sắt|tia\\s*sắt|laser)\\b',
    '\\b(?:phòng\\s*thủ|tấn\\s*công)\\s*(?:tên\\s*lửa|uav|drone)\\b',
    '\\b(?:sinh\\s*non|bệnh\\s*hiểm\\s*nghèo|ung\\s*thư|thai\\s*phụ|sản\\s*phụ|hiếm\\s*muộn|vô\\s*sinh)(?!.*(?:do|vì|bởi|tại|sau)\\s*(?:thiên\\s*tai|bão|lũ|ngập|lụt|sạt|sét|nóng|hạn|động\\s*đất|sóng\\s*thần))\\b',
    '\\b(?:thị\\s*lực|mất\\s*trí\\s*nhớ|suy\\s*tim|chẩn\\s*đoán|xét\\s*nghiệm|phẫu\\s*thuật|nội\\s*soi|siêu\\s*âm|cấy\\s*ghép|cận\\s*thị|viễn\\s*thị|loạn\\s*thị|nhồi\\s*máu|đột\\s*quỵ|cao\\s*huyết\\s*áp|tiểu\\s*đường|mỡ\\s*máu|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đậu\\s*mùa\\s*khỉ|thủy\\s*đậu|sởi|cúm\\s*a|cúm\\s*b|nâng\\s*ngực|hút\\s*mỡ|thẩm\\s*mỹ\\s*viện)(?!.*(?:nạn\\s*nhân|tử\\s*thi|do\\s*thiên\\s*tai|sau\\s*bão|ngập\\s*lụt))\\b',
    '\\b(?:nghĩa\\s*tình|nhẫn\\s*cưới|gia\\s*đình\\s*hạnh\\s*phúc|sinh\\s*kế\\s*phụ\\s*nữ|giảm\\s*nghèo\\s*bền\\s*vững|quà\\s*tết|tiết\\s*kiệm\\s*tại\\s*quầy)(?!.*(?:bão|lũ|thiên\\s*tai|tái\\s*thiết|khắc\\s*phục|hỗ\\s*trợ|ngập|sạt\\s*lở|nhà\\s*tình\\s*nghĩa|nhà\\s*đại\\s*đoàn\\s*kết))\\b',
    '\\b(?:trao\\s*bằng|tiến\\s*sĩ|thạc\\s*sĩ|đại\\s*biểu\\s*Quốc\\s*hội|30[-/]4|1[-/]5|nghỉ\\s*lễ|bầu\\s*cử|ứng\\s*cử|đắc\\s*cử)\\b',
    '\\b(?:đối\\s*tượng|truy\\s*quét|trái\\s*phép|buôn\\s*lậu|bắt\\s*giữ|khởi\\s*tố|bắt\\s*tạm\\s*giam|lừa\\s*đảo|chiếm\\s*đoạt\\s*tài\\s*sản|tham\\s*ô|ăn\\s*chặn)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|cứu\\s*trợ|hỗ\\s*trợ|thiện\\s*nguyện|khắc\\s*phục|thiên\\s*tai))\\b',
    '\\b(?:phát\\s*huy\\s*vai\\s*trò|nêu\\s*gương|điển\\s*hình|khen\\s*thưởng|thi\\s*đua|thành\\s*tích|gương\\s*sáng|học\\s*tập\\s*và\\s*làm\\s*theo)(?!.*(?:cứu\\s*dân|cứu\\s*nạn|cứu\\s*người|dũng\\s*cảm|quên\\s*mình|hy\\s*sinh|lũ\\s*dữ|thiên\\s*tai|bão|lũ))\\b',
    '^(?!.*(?:bão|lũ|mưa|thiên\\s*tai|khắc\\s*phục|cứu\\s*hộ|cứu\\s*nạn|vùng\\s*lũ|đồng\\s*bào)).*\\b(?:ra\\s*quân|lễ\\s*phát\\s*động|hưởng\\s*ứng|phong\\s*trào|dâng\\s*hương|mít\\s*tinh|kỷ\\s*niệm)\\b',
    '\\b(?:chủ\\s*công|nòng\\s*cốt|xung\\s*kích|tình\\s*nguyện|xung\\s*phong)(?!\\s*(?:cứu\\s*hộ|cứu\\s*nạn|giúp\\s*dân|khắc\\s*phục))\\b',
    '\\b(?:luyện\\s*tập|hợp\\s*luyện|thao\\s*diễn|hội\\s*thao|diễn\\s*tập\\s*khu\\s*vực|bắn\\s*đạn\\s*thật)(?!\\s*(?:thực\\s*tế|trong\\s*mưa\\s*bão))\\b',
    '\\b(?:bật\\s*mí|khả\\s*năng|săn\\s*ngầm|trực\\s*thăng\\s*săn\\s*ngầm|trực\\s*thăng\\s*ka-\\d+|vũ\\s*khí\\s*tối\\s*tân|tiêm\\s*kích)\\b',
    r'\b(?:kiện\s*toàn\s*ban\s*chỉ\s*đạo|nghiêm\s*cấm\s*lợi\s*dụng|kiểm\s*tra\s*về\s*phòng\s*cháy|thực\s*tập\s*phương\s*án|hội\s*thao\s*pccc)\b(?!.*(?:cháy\s*rừng|rừng\s*bị\s*cháy))',
    '\\b(?:giá\\s*cà\\s*phê|giá\\s*hồ\\s*tiêu|giá\\s*cao\\s*su|tạm\\s*dừng\\s*đà\\s*tăng|giá\\s*nông\\s*sản)\\b',
    '\\b(?:đại\\s*hội\\s*đảng\\s*bộ|tạm\\s*dừng\\s*tổ\\s*chức\\s*đại\\s*hội|chuẩn\\s*bị\\s*đại\\s*hội|nhân\\s*sự\\s*đại\\s*hội)\\b',
    '\\b(?:mua\\s*bán\\s*người|buôn\\s*bán\\s*người|nạn\\s*nhân\\s*mua\\s*bán|lừa\\s*bán|việc\\s*nhẹ\\s*lương\\s*cao|nạn\\s*nhân\\s*bị\\s*lừa|giải\\s*cứu\\s*nạn\\s*nhân\\s*trafficking)\\b',
    '\\b(?:di\\s*cư\\s*trái\\s*phép|vượt\\s*biên|nhập\\s*cảnh\\s*trái\\s*phép|lao\\s*động\\s*chui|trục\\s*xuất)(?!.*(?:do|vì|bởi)\\s*(?:thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:cơn)\\s*(?:địa\\s*chấn|sóng\\s*thần)\\s*(?:chính\\s*trị|tài\\s*chính|ngôn\\s*ngữ|mạng|sân\\s*cỏ|điện\\s*ảnh|showbiz)\\b',
    '\\b(?:rạp\\s*cưới|đám\\s*cưới|đám\\s*hỏi|rước\\s*dâu)(?!\\s*(?:bị\\s*lũ|trong\\s*lũ|gặp\\s*nạn|cuốn\\s*trôi))\\b',
    '\\b(?:buông\\s*hai\\s*tay|bốc\\s*đầu|nẹt\\s*pô|đua\\s*xe|lạng\\s*lách)(?!\\s*(?:gặp\\s*nạn|tai\\s*nạn))\\b',
    '\\b(?:phạt\\s*nguội|nồng\\s*độ\\s*cồn|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|đăng\\s*kiểm|biển\\s*số)\\b',
    '\\b(?:phạt\\s*nguội|nồng\\s*độ\\s*cồn|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|đăng\\s*kiểm|biển\\s*số)\\b',
    '\\b(?:đại\\s*biểu\\s*quốc\\s*hội|đbqh|hđnd|tiếp\\s*xúc\\s*cử\\s*tri|kỳ\\s*họp\\s*thứ|cử\\s*tri|thảo\\s*luận\\s*tổ|đại\\s*hội\\s*đảng|bầu\\s*cử|nhiệm\\s*kỳ|công\\s*tác\\s*cán\\s*bộ)\\b',
    '\\b(?:chủ\\s*đầu\\s*tư|nhà\\s*thầu|đấu\\s*thầu|gói\\s*thầu|định\\s*giá\\s*đất|dự\\s*án\\s*hạ\\s*tầng|đôn\\s*đốc|giải\\s*phóng\\s*mặt\\s*bằng|đền\\s*bù|quy\\s*hoạch|khởi\\s*công|khánh\\s*thành|sửa\\s*chữa\\s*đường\\s*băng|nâng\\s*cấp\\s*mở\\s*rộng|khu\\s*trung\\s*tâm\\s*hành\\s*chính|nghiên\\s*cứu\\s*quy\\s*hoạch|đô\\s*thị|lịch\\s*sử)(?!.*(?:khắc\\s*phục|sạt\\s*lở|vỡ\\s*đê|cứu\\s*hộ|thiên\\s*tai|bão|lũ|tái\\s*định\\s*cư|di\\s*dời|khẩn\\s*cấp|cầu|đường|sụt\\s*lún|giữ\\s*đất|kè\\s*chống))\\b',
    '\\b(?:tổng\\s*điều\\s*tra\\s*kinh\\s*tế|phụ\\s*cấp\\s*khu\\s*vực|xếp\\s*lương|trợ\\s*cấp\\s*bhxh|lương\\s*hưu|tăng\\s*trợ\\s*cấp|xếp\\s*hạng\\s*lương|bảo\\s*hiểm\\s*y\\s*tế\\s*giấy|thưởng\\s*tết)(?!.*(?:vùng\\s*lũ|ngập\\s*lụt|thiên\\s*tai|cứu\\s*trợ|khắc\\s*phục|hỗ\\s*trợ\\s*khẩn\\s*cấp))\\b',
    '\\b(?:thủ\\s*tướng\\s*tiếp|chủ\\s*tịch\\s*nước\\s*tiếp|ngoại\\s*giao\\s*đoàn|đại\\s*sứ\\s*quán|lãnh\\s*sự\\s*quán)(?!.*(?:hỗ\\s*trợ\\s*bão\\s*lụt|viện\\s*trợ))\\b',
    '\\b(?:ra\\s*mắt\\s*sản\\s*phẩm|ra\\s*mắt\\s*(?:xe|điện\\s*thoại|máy|laptop|ốp|sạc|phiên\\s*bản)|công\\s*nghệ\\s*mới|trải\\s*nghiệm|mở\\s*hộp)\\b',
    '\\b(?:olight|ostation|sony|playstation|steam|iphone|samsung|oppo|xiaomi|khôi\\s*phục\\s*cài\\s*đặt|bằng\\s*sáng\\s*chế|ai\\s*ghost|npc|game\\s*thủ)\\b',
    '\\b(?:kỷ\\s*niệm\\s*(?:\\d+|năm)\\s*năm|ngày\\s*thành\\s*lập|số\\s*đầu\\s*tiên|sinh\\s*nhật|mừng\\s*thọ)\\b',
    '\\b(?:đón\\s*đoàn\\s*khách|khách\\s*du\\s*lịch|tham\\s*quan|nghỉ\\s*dưỡng|check-in|sống\\s*ảo)(?!\\s*(?:mắc\\s*kẹt|cô\\s*lập))\\b',
    '\\b(?:hiv|aids|ma\\s*túy|cai\\s*nghiện|ngáo\\s*đá|bay\\s*lắc|hóa\\s*chất\\s*duỗi\\s*tóc)\\b',
    '\\b(?:giá\\s*đồng|giá\\s*vàng|chứng\\s*khoán|cổ\\s*phiếu|lập\\s*đỉnh\\s*lịch\\s*sử|vượt\\s*đỉnh)(?!\\s*(?:mực\\s*nước|lũ|triều\\s*cường))\\b',
    '\\b(?:khẩn\\s*cấp\\s*(?:chi|rót)\\s*vốn|ngân\\s*sách|đầu\\s*tư\\s*công)(?!\\s*(?:khắc\\s*phục|hỗ\\s*trợ|cứu\\s*trợ|phòng\\s*chống))\\b',
    '\\b(?:giá\\s*cao\\s*su|giá\\s*xăng|giá\\s*dầu|ron\\s*95|e5\\s*ron\\s*92|thị\\s*trường\\s*nội\\s*địa|kiều\\s*hối|tỷ\\s*giá|lãi\\s*suất|giá\\s*tôm|thương\\s*phẩm|kinh\\s*tế\\s*số|giá\\s*tiêu|thu\\s*ngân\\s*sách|tiêu\\s*dùng\\s*nội\\s*địa|sáp\\s*nhập|doanh\\s*nghiệp\\s*(?:chớp\\s*thời\\s*cơ|xuất\\s*khẩu|nhập\\s*khẩu|fdi|thành\\s*lập\\s*mới|nhỏ\\s*và\\s*vừa)|hàng\\s*việt|xuất\\s*khẩu|nhập\\s*khẩu|kim\\s*ngạch|fdi|nhập\\s*thịt|giá\\s*lợn|leo\\s*thang|thuế\\s*bất\\s*động\\s*sản|thanh\\s*tra\\s*doanh\\s*nghiệp|tài\\s*chính\\s*quốc\\s*tế)(?!.*(?:ngập|lũ))\\b',
    '\\b(?:thảm\\s*họa)\\s*(?:thẩm\\s*mỹ|thời\\s*trang|âm\\s*nhạc|dao\\s*kéo|mc|trang\\s*điểm|nấu\\s*ăn|nhan\\s*sắc)\\b',
    '\\b(?:bão)\\s*(?:sao\\s*kê|drama|tẩy\\s*chay|chỉ\\s*trích|ném\\s*đá|đòi\\s*nợ|kiện\\s*tụng|ly\\s*hôn)\\b',
    '\\b(?:sóng\\s*gió)\\s*(?:cuộc\\s*đời|tình\\s*yêu|hôn\\s*nhân|gia\\s*tộc|thương\\s*trường|hậu\\s*trường)\\b',
    '\\b(?:barca|bundesliga|la\\s*liga|man\\s*city|arsenal|odegaard|arda\\s*guler|ole\\s*gunnar|solskjaer|manchester\\s*united|jun\\s*phạm|công\\s*diễn\\s*\\d+|show\\s*ca\\s*nhạc|nhạc\\s*sĩ|cống\\s*hiến|âm\\s*nhạc|crystal\\s*palace|aston\\s*villa|thép\\s*xanh\\s*nam\\s*định|shb\\s*đà\\s*nẵng|haaland|saka|enzo\\s*maresca|ruben\\s*amorim|bóng\\s*đá\\s*malaysia|stranger\\s*things|u23|vck|asian\\s*cup|world\\s*cup|cầu\\s*thủ|huấn\\s*luyện\\s*viên|ai\\s*là\\s*triệu\\s*phú|đại\\s*gia\\s*chân\\s*đất|hết\\s*thời|ly\\s*hôn|hòa\\s*minzy|ca\\s*sĩ)\\b',
    '\\b(?:hạ\\s*cánh\\s*khẩn\\s*cấp|sự\\s*cố\\s*kỹ\\s*thuật|máy\\s*bay|sân\\s*bay|hàng\\s*không|phi\\s*công|tiếp\\s*viên|đường\\s*băng|cất\\s*cánh|hạ\\s*cánh|delay|hủy\\s*chuyến|đổi\\s*hướng|quay\\s*đầu)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|sương\\s*mù|gió\\s*giật|thời\\s*tiết\\s*xấu))\\b',
    '\\b(?:(?<!nghiêm\\s)trọng\\s*tài|kèo|xem\\s*trực\\s*tiếp|nhận\\s*định)\\b(?!.*?(?:lao\\s*cai|vùng\\s*lũ|khắc\\s*phục|cứu\\s*hộ|hỗ\\s*trợ|thiên\\s*tai))',
    '\\b(?:giải\\s*cứu)\\s*(?:thương\\s*vụ|hàng\\s*thủ|kinh\\s*tế|doanh\\s*nghiệp|bất\\s*động\\s*sản)(?!\\s*(?:lũ|bão))\\b',
    '\\b(?:lễ\\s*công\\s*bố|trao\\s*thưởng|giải\\s*báo\\s*chí|phát\\s*động\\s*cuộc\\s*thi)\\b',
    '\\b(?:bắt\\s*cóc|giải\\s*cứu\\s*nạn\\s*nhân\\s*bị\\s*bắt|truy\\s*bắt|nhóm\\s*đối\\s*tượng|truy\\s*nã|án\\s*mạng|giết\\s*người|khởi\\s*tố|bắt\\s*tạm\\s*giam|gây\\s*án|điều\\s*tra|tố\\s*cáo|chiếm\\s*đoạt|trung\\s*tâm\\s*cai\\s*nghiện)(?!.*(?:lũ|bão|thiên\\s*tai))\\b',
    '\\b(?:tin\\s*sai\\s*lệch|tin\\s*giả|thông\\s*tin\\s*thất\\s*thiệt|xử\\s*lý\\s*đối\\s*tượng\\s*đăng\\s*tin)(?!\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:lục\\s*bình|rác\\s*thải|đổ\\s*trộm|ô\\s*nhiễm|bụi\\s*mù\\s*mịt)(?!\\s*(?:sau\\s*lũ|do\\s*bão))\\b',
    '\\b(?:ăn\\s*chặn|biển\\s*thủ|trục\\s*lợi|sao\\s*kê|minh\\s*bạch)\\s*(?:từ\\s*thiện|tiền\\s*cứu\\s*trợ|quỹ|tài\\s*khoản)(?!\\s*(?:cho|về|người)\\s*(?:vùng\\s*lũ|bão))\\b',
    '\\b(?:lùm\\s*xùm|tranh\\s*cãi|tố\\s*cáo|bóc\\s*phốt)\\s*(?:kêu\\s*gọi|quyên\\s*góp|từ\\s*thiện|nghệ\\s*sĩ)\\b',
    '\\b(?:quy\\s*hoạch|đề\\s*án|chủ\\s*trương|phê\\s*duyệt|nghiên\\s*cứu|đề\\s*xuất)\\s*(?:đường\\s*sắt|sân\\s*bay|cảng\\s*biển|cao\\s*tốc|metro|tàu\\s*điện)(?!.*(?:sạt\\s*lở|lũ|bão|ngập|thiên\\s*tai|hư\\s*hỏng|sự\\s*cố))\\b',
    '\\b(?:vận\\s*hành\\s*thương\\s*mại|chạy\\s*thử|đóng\\s*điện|thông\\s*xe|khởi\\s*công|động\\s*thổ|khép\\s*kín\\s*đường|vành\\s*đai\\s*\\d+|phân\\s*luồng\\s*giao\\s*thông|xuất\\s*quân\\s*bảo\\s*vệ|duyệt\\s*đội\\s*ngũ|diễn\\s*tap\\s*bảo\\s*vệ)(?!\\s*(?:khắc\\s*phục|sửa\\s*chữa|cầu\\s*tạm|cứu\\s*hộ|thiên\\s*tai))\\b',
    '\\b(?:thống\\s*kê|báo\\s*cáo|tổng\\s*kết)\\s*(?:tình\\s*hình|số\\s*liệu)\\s*(?:tai\\s*nạn|giao\\s*thông|an\\s*ninh\\s*trật\\s*tự)(?!\\s*(?:do|vì|trong)\\s*(?:bão|lũ|thiên\\s*tai|mưa))\\b',
    '\\b(?:hàng\\s*hóa\\s*qua\\s*biên\\s*giới|vận\\s*chuyển\\s*trái\\s*phép|buôn\\s*lậu|gian\\s*lận\\s*thương\\s*mại|hàng\\s*giả|kéo\\s*xe|cửu\\s*vạn|vượt\\s*biên|xuất\\s*nhập\\s*cảnh\\s*trái\\s*phép)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|vùng\\s*lũ))\\b',
    '\\b(?:bình\\s*ổn\\s*thị\\s*trường|thóc\\s*gạo|giá\\s*đất|luật\\s*phá\\s*sản|nâng\\s*hạng\\s*thị\\s*trường|chứng\\s*khoán|xuất\\s*khẩu|nhập\\s*khẩu|giá\\s*xăng|giá\\s*dầu|giá\\s*vàng|kim\\s*ngạch|tăng\\s*trưởng|gdp|lạm\\s*phát|cpi)(?!.*(?:thiệt\\s*hại|ảnh\\s*hưởng|do|vì)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:giải\\s*thưởng\\s*khoa\\s*học|nghiên\\s*cứu\\s*khoa\\s*học|sáng\\s*tạo\\s*kỹ\\s*thuật|đổi\\s*mới\\s*sáng\\s*tạo|trao\\s*giải|vinh\\s*danh|nhà\\s*khoa\\s*học|học\\s*sinh\\s*giỏi|kỳ\\s*thi)(?!.*(?:dự\\s*báo|cảnh\\s*báo|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:bình\\s*đẳng\\s*giới|tháng\\s*hành\\s*động|phụ\\s*nữ\\s*việt\\s*nam|hội\\s*liên\\s*hiệp\\s*phụ\\s*nữ|bạo\\s*lực\\s*gia\\s*đình|trẻ\\s*em\\s*gái|quyền\\s*phụ\\s*nữ)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|vùng\\s*lũ|thiên\\s*tai))\\b',
    '\\b(?:cháy\\s*nhà|cháy\\s*ki\\s*ốt|cháy\\s*chung\\s*cư|cháy\\s*xưởng|cháy\\s*xe|hỏa\\s*hoạn\\s*tại)(?!.*(?:rừng|diện\\s*rộng|khu\\s*cong\\s*nghiệp|thảm\\s*họa|cứu\\s*hộ|thiên\\s*tai))\\b',
    '^(?:thứ\\s+\\w+,\\s+\\d{1,2}[/-]\\d{1,2}[/-]\\d{4}\\s*[|-])',
    '^(?:chương\\s*trình\\s*thời\\s*sự)',
    '^bản\\s*tin\\s*(?:sáng|trưa|tối)\\s+\\d{1,2}[/-]\\d{1,2}',
    '\\b(?:quảng\\s*cáo|facebook|sinh\\s*lời|marketing|livestream|bán\\s*hàng\\s*online|chốt\\s*đơn|doanh\\s*thu|lợi\\s*nhuận)(?!.*(?:bão|lũ|thiên\\s*tai|ủng\\s*hộ|cứu\\s*trợ))\\b',
    '\\b(?:v\\.league|cúp\\s*quốc\\s*gia|hội\\s*quân|tiền\\s*đạo|cầu\\s*thủ|becamex|slna|hagl|cahn|clb|bóng\\s*đá|futsal|seagames|aff\\s*cup|vòng\\s*\\d+|lượt\\s*trận|tỷ\\s*số)(?!.*(?:bão|lũ|thiên\\s*tai|ủng\\s*hộ))\\b',
    '\\b(?:trồng\\s*cây|vụ\\s*đông|vụ\\s*xuân|vụ\\s*mùa|được\\s*mùa|mất\\s*mùa|giá\\s*thóc|giá\\s*lúa|nông\\s*dân\\s*sản\\s*xuất|xuống\\s*giống)(?!.*(?:bão|lũ|ngập|thiệt\\s*hại|khắc\\s*phục|thiên\\s*tai|rét|lạnh|nhiệt\\s*độ))\\b',
    '\\b(?:tập\\s+\\d+|review\\s*phim|preview\\s*tập|tóm\\s*tắt\\s*phim|lịch\\s*chiếu|show\\s*truyền\\s*hình)\\b',
    '\\b(?:lằn\\s*ranh\\s*tập|nguyệt\\s*mất\\s*tích|phim\\s*truyền\\s*hình\\s*tập|kết\\s*phim|nội\\s*dung\\s*tập)\\b',
]

# 2. CONDITIONAL VETO: Noise that can co-exist with disaster (Economy, Accident, etc.)
# These will be blocked ONLY if there is NO specific hazard score or metrics.
CONDITIONAL_VETO = [
    # URBAN / INDUSTRIAL FIRE & EXPLOSION (Non-Forest)
    # Block unless caused by disaster (lightning, storm, etc.)
    r"(?:cháy|hỏa\s*hoạn|bốc\s*cháy|phát\s*hỏa)\s*(?:nhà|căn\s*hộ|chung\s*cư|phòng\s*trọ|quán|karaoke|bar|cửa\s*hàng|ki\s*ốt|xưởng|kho|trụ\s*sở|xe|ô\s*tô|xe\s*máy)(?!\s*(?:do|vì|bởi|tại)\s*(?:bão|lũ|thiên\s*tai|sét\s*đánh|chập\s*điện\s*do\s*mưa|cây\s*đổ))",
    r"(?:nổ|phát\s*nổ)\s*(?:bình\s*gas|khí\s*gas|nồi\s*hơi|lò\s*hơi|trạm\s*biến\s*áp|máy\s*biến\s*áp|pin|ắc\s*quy)(?!\s*(?:do|vì|bởi|tại)\s*(?:bão|lũ|thiên\s*tai|sét\s*đánh))",
    r"(?:PCCC|cảnh\s*sát\s*PCCC|114|đội\s*chữa\s*cháy|lực\s*lượng\s*chữa\s*cháy|dập\s*tắt\s*đám\s*cháy)(?!\s*(?:rừng|thảm\s*thực\s*vật|do\s*sét|trong\s*mưa\s*bão))",
    r"(?:nguyên\s*nhân\s*ban\s*đầu|đang\s*điều\s*tra|khám\s*nghiệm\s*hiện\s*trường|khởi\s*tố\s*vụ\s*án)\s*(?:cháy|nổ)?",
    r"lửa\s*ngùn\s*ngụt|bà\s*hỏa|chập\s*điện(?!\s*(?:do|vì)\s*(?:mưa|ngập|bão))",

    # URBAN MAINTENANCE
    r"\b(?:chặt\s*hạ|tỉa\s*cành|cắt\s*tỉa|duy\s*tu|xử\s*lý\s*cây\s*xanh)(?!\s*(?:sau|do)\s*(?:bão|lũ|lửa))\b",
    r"\b(?:quản\s*lý\s*biên\s*giới|đồn\s*biên\s*phòng|tuần\s*tra\s*biên\s*giới|vệ\s*biên|vùng\s*biên)\b",
    r"\b(?:bom\s*mìn|vật\s*nổ|rửa\s*tiền|Taliban|Hamas|Hezbollah|phiến\s*quân|phi\s*vụ|buôn\s*người)\b",

    # TRAFFIC ACCIDENTS (Vehicle specific)
    r"(?<!\w)(?:va\s*chạm\s*liên\s*hoàn|tai\s*nạn\s*liên\s*hoàn|tai\s*nạn\s*giao\s*thông|lật\s*xe|tông\s*xe|xe\s*khách|xe\s*tải|xe\s*ben|va\s*chạm|bị\s*xe\s*cán|xe\s*máy|xe\s*đạp|xe\s*điên|xe\s*tập\s*lai)(?!.*(?:do|vì|bởi|chở|của|xe|đoàn|đi|khi|trong|tại|vùng|bị)\s*(?:bão|lũ|sạt\s*lở|mưa|thiện\s*nguyện|từ\s*thiện|cứu\s*trợ|người\s*đi\s*cứu|hàng\s*cứu|cứu\s*trợ|nhân\s*đạo|ngập|nước\s*cuốn|cuốn\s*trôi|nước\s*dâng|thiên\s*tai))(?!.*(?:đoàn\s*thiện\s*nguyện|đoàn\s*từ\s*thiện|xe\s*cứu\s*trợ|hàng\s*cứu\s*trợ|hỗ\s*trợ\s*khẩn\s*cấp|từ\s*thiện|thiện\s*nguyện|lao\s*cai|yen\s*bai|lang\s*son|phu\s*tho|quang\s*ninh|hai\s*phong|thanh\s*hoa|nghe\s*an|ha\s*tinh|quang\s*tri|thua\s*thien\s*hue|da\s*nang|quang\s*nam|quang\s*ngai|binh\s*dinh|phu\s*yen|khanh\s*hoa|ninh\s*thuan|binh\s*thuan|kon\s*tum|gia\s*lai|dak\s*lak|dak\s*nong|lam\s*dong))",
    r"\b(?:tông\s*xe|tông\s*vào|xe\s*máy|xe\s*tải|lái\s*xe)(?!.*(?:bão|lũ|sạt\s*lở|cứu\s*trợ|ngập|cứu\s*nạn|tử\s*vong|thiệt\s*mạng|trôi|cuốn))\b",
    r"\b(?:tai\s*nạn\s*liên\s*hoàn|đâm\s*xe|lật\s*xe|va\s*chạm|người\s*lái\s*xe|tài\s*xế|nồng\s*độ\s*cồn|giấy\s*phép\s*lái\s*xe|sát\s*hạch|thói\s*quen|kỹ\s*năng\s*lái\s*xe|luật\s*giao\s*thông|điểm\s*đen|đường\s*sắt|đường\s*ray|tàu\s*hỏa|xe\s*đạp|xe\s*khách|xe\s*tải|xe\s*hợp\s*đồng|tông\s*xe)(?!.*(?:bão|lũ|sạt\s*lở|mưa|ngập))\b",
    r"\b(?:tai\s*nạn\s*thảm\s*khốc|thảm\s*khốc\s*9\s*người|lật\s*xe\s*khách)(?!.*(?:bão|lũ|sạt\s*lở|lũ\s*quét|sóng\s*thần|cứu\s*trợ|thiên\s*tai))\b",

    # INDIVIDUAL ACCIDENTS
    r"(?:sập|đổ)\s*(?:giàn\s*giáo|cần\s*cẩu|công\s*trình|tường|trần|mái|nhà\s*xưởng)\s*(?:đang\s*thi\s*công|khi\s*thi\s*công|tại\s*công\s*trình)(?!\s*(?:do|vì|gây)\s*(?:gió|bão|lốc|mưa|chết|tử\s*vong|thương\s*vong))",
    r"tai\s*nạn\s*lao\s*động|an\s*toàn\s*lao\s*động|phóng\s*hỏa|đốt\s*nhà",
    r"(?:rơi|ngã)\s*(?:từ\s*trên\s*cao|tầng\s*\d+|giàn\s*giáo|cần\s*cẩu|hố\s*ga|thang\s*máy)",
    r"\b(?:đuối\s*nước|tìm\s*thấy\s*thi\s*thể|tử\s*vong\s*(?:thương\s*tâm|do\s*ngạt|ở\s*sông|ở\s*biển|khi\s*tắm))(?!.*(?:bão|lũ|ngập|sạt|thiên\s*tai|tai\s*nạn|vỡ\s*đê|sóng\s*lớn))\b",
    r"\b(?:dự\s*báo\s*thời\s*tiết\s*ngày|thời\s*tiết\s*hôm\s*nay|thời\s*tiết\s*tháng|bản\s*tin\s*thời\s*tiết)(?!.*(?:mưa\s*lũ|ngập|sạt|bão|lốc|mưa\s*đá|hạn\s*mặn|triều\s*cường|rét|lạnh|nhiệt\s*độ))\b",
    r"(?:sập|tai\s*nạn)\s*(?:hầm\s*lò|mỏ\s*đá|mỏ\s*than|công\s*trường)(?!\s*(?:do|vì|bởi)\s*(?:bão|lũ|thiên\s*tai|mưa|sạt\s*lở))",

    # ECONOMY & FINANCE
    r"(?:lãi\s*suất|tín\s*dụng|tỉ\s*giá|ngoại\s*tệ|ngân\s*hàng|chứng\s*khoán|vốn\s*điều\s*lệ|lợi\s*nhuận|doanh\s*thu|vn-index)(?!\s*(?:chính\s*sách|hỗ\s*trợ|ư\s*đãi|khôi\s*phục|khắc\s*phục)\s*(?:sau|vùng|cho|người)\s*(?:bão|lũ|thiên\s*tai|ngập|sạt\s*lở))",
    r"giá\s*(?:vàng|heo|cà\s*phê|lúa|xăng|dầu|trái\s*cây|thanh\s*long|nông\s*sản|bất\s*động\s*sản|đất)",
    r"hạ\s*nhiệt\s*(?:giá|thị\s*trường)|tăng\s*trưởng\s*kinh\s*tế|gdp|oda|adb|wb|imf",

    # TECH TUTORIALS & SPAM
    r"(?:cách|hướng\s*dẫn|thủ\s*thuật|mẹo).*(?:tách|gộp|nén|chuyển|sửa).*(?:file|tệp|pdf|word|excel|ảnh|video)",
    r"(?:google|facebook|youtube|tiktok|zalo\s*pay|vneid).*(?:cập\s*nhật|tính\s*năng|ra\s*mắt|lỗi|hướng\s*dẫn)(?!.*(?:cứu\s*trợ|ủng\s*hộ|thiên\s*tai|bão|lũ|khẩn\s*cấp))",
    r"how\s*to.*(?:tutorial|template|branding|customize)",
    r"(?:sân\s*bay|hàng\s*không|hạ\s*cánh|cất\s*cánh|phi\s*công|cơ\s*trưởng)(?!.*(?:do|vì|bởi|để|ứng\s*phó)\s*(?:bão|lũ|thiên\s*tai|thời\s*tiết))",

    # SAFETY ADVISORIES & EDUCATION (Non-emergencies)
    r"\b(?:khuyến\s*cáo|nhắc\s*nhở|kỹ\s*năng|phòng\s*ngừa|tập\s*huấn)\s*(?:pccc|an\s*toàn|ngập\s*lụt|đuối\s*nước)\b",
    
    # INFRASTRUCTURE & TECHNICAL FAILURES (Non-disaster incidents)
    # INFRASTRUCTURE & TECHNICAL FAILURES (Moved to Conditional)
    # MOVED: r"\b(?:sự\s*cố|hỏng\s*hóc|bảo\s*trì|ngắt\s*điện|mất\s*điện|cắt\s*điện)\s*(?:lưới\s*điện|trạm\s*biến\s*áp|đường\s*dây|cáp\s*quang|internet|hệ\s*thống)(?!.*(?:do|vì|bởi|khắc\s*phục|xuyên\s*đêm)\s*(?:bão|lũ|thiên\s*tai|sạt\s*lở|mưa))\b",
    r"\b(?:thủng\s*xăm|hỏng\s*xe|chết\s*máy|ùn\s*tắc|kẹt\s*xe|dòng\s*người\s*chen\s*chúc)\b",
    r"\b(?:sập\s*giàn\s*giáo|tai\s*nạn\s*lao\s*động|ngộ\s*độc\s*thực\s*phẩm|cháy\s*nổ\s*bình\s*gas)\b",
    # Refined Fire Veto: Block building/car fires, allow Forest Fires (cháy rừng)
    r"\b(?:cháy\s*lớn|vụ\s*cháy|hỏa\s*hoạn|bà\s*hỏa|thiêu\s*rụi|cháy\s*rụi).*(?:nhà\s*dân|cửa\s*hàng|quán|karaoke|chung\s*cư|xưởng|nhà\s*kho|xe\s*khách|xe\s*tải|ô\s*tô|xe\s*máy|chợ|siêu\s*thị|tầng|phòng|căn\s*hộ)(?!.*(?:rừng|thảm\s*thực\s*vật|do\s*sét|trong\s*bão|mưa))",
    
    # ROUTINE URBAN NOISE
    r"\b(?:triều\s*cường\s*(?:rằm|giữa\s*tháng|hàng\s*tháng)|ngập\s*do\s*triều|đỉnh\s*triều|hố\s*ga|nắp\s*cống|vỉ\s*hè|đường\s*hầm)\b",
    r"\b(?:kiểm\s*tra\s*nồng\s*độ\s*cồn|phạt\s*nguội|xe\s*quá\s*tải|trạm\s*thu\s*phí|vào\s*cua|mất\s*lái)\b",

    # MARINE & AGRI PRODUCTION (Routine production news)
    r"\b(?:vươn\s*khơi|bám\s*biển|đánh\s*bắt|nuôi\s*trồng|tái\s*đàn|vào\s*vụ|thu\s*hoạch|giá\s*thu\s*mua|hải\s*sản|thủy\s*sản)\b",
    
    # PUBLIC HEALTH & EPIDEMICS (Medical, not natural disasters)
    r"\b(?:sốt\s*xuất\s*huyết|tay\s*chân\s*miệng|dịch\s*sởi|cúm\s*gia\s*cầm|đỉnh\s*dịch|bùng\s*phát\s*dịch|phun\s*hóa\s*chất|diệt\s*loăng\s*quăng| não\s*mô\s*cầu)\b",
    r"\b(?:bảo\s*hiểm\s*xã\s*hội|bảo\s*hiểm\s*thất\s*nghiệp|bhxh|bhtn|bhyt|chế\s*độ\s*bhxh)\b",
    
    # PUBLIC WORKS MAINTENANCE (Routine)
    r"\b(?:nạo\s*vét|khơi\s*thông|vệ\s*sinh).*(?:kênh\s*mương|cống\s*rãnh|dòng\s*chảy|rác\s*thải)\b",
    r"\b(?:phủ\s*xanh|trồng\s*cây\s*gây\s*rừng|chăm\s*sóc\s*cây\s*xanh|cắt\s*tỉa\s*cành\s*cây)\b",

    # ADMINISTRATIVE & NON-DISASTER DRILLS/MEETINGS
    r"(?:nghiệm\s*thu|bàn\s*giao)\s*(?:công\s*trình|đề\s*tài|dự\s*án)(?!.*(?:khắc\s*phục|hậu\s*quả|sạt\s*lở|khẩn\s*cấp|cứu\s*trợ|tái\s*định\s*cư|nhà\s*đại\s*đoàn\s*kết|sau\s*bão))",
    r"(?:hội\s*nghị|hội\s*thảo|tập\s*huấn)\s.*(?:khoa\s*học|kỹ\s*thuật|công\s*nghệ|chuyên\s*đề)",

    # MILITARY DRILLS & TRAINING (Non-incident)
    r"\b(?:diễn\s*tập|thực\s*binh|hiệp\s*đồng|huấn\s*luyện|tình\s*huống\s*giả\s*định|phương\s*án\s*ứng\s*phó|tập\s*huấn)\b",
    
    # FUTURE SCENARIOS & RESEARCH (Not immediate events)
    r"\b(?:kịch\s*bản\s*biến\s*đổi|tầm\s*nhìn\s*20\d{2}|dự\s*báo\s*đến\s*năm|mô\s*hình\s*mô\s*phỏng|nghiên\s*cứu\s*khoa\s*học|đề\s*tài\s*cấp\s*bộ)\b",
    
    # GENERAL WELFARE & CHARITY (Non-disaster relief)
    r"\b(?:hộ\s*nghèo|cận\s*nghèo|giảm\s*nghèo\s*bền\s*vững|quà\s*tết|hiến\s*máu|khám\s*bệnh\s*miễn\s*phí|vượt\s*khó\s*vươn\s*lên)\b",

    # HYDRO-POWER & IRRIGATION REGULATION (Routine vs Emergency)
    r"\b(?:xả\s*nước\s*đổ\s*ải|vận\s*hành\s*phát\s*điện|phát\s*điện\s*định\s*kỳ|mực\s*nước\s*chết|hồ\s*thủy\s*điện\s*xả\s*nước(?!\s*khẩn\s*cấp))\b",
    r"\b(?:tưới\s*tiêu|nguồn\s*nước\s*phục\s*vụ\s*sản\s*xuất|điều\s*tiết\s*nước\s*ruộng)\b",
    
    # ROUTINE MONITORING (Non-disaster sensors)
    r"\b(?:kết\s*quả\s*quan\s*trắc|trạm\s*đo|chỉ\s*số\s*hàng\s*ngày|độ\s*mặn\s*đo\s*được|mặn\s*xâm\s*nhập\s*nhẹ)\b",
    
    # ROAD REPAIRS & TRANSPORT (Routine)
    r"\b(?:thông\s*hầm|trải\s*nhựa|vá\s*đường|khắc\s*phục\s*ổ\s*gà|duy\s*tu|sửa\s*chữa\s*định\s*kỳ|mở\s*rộng\s*tuyến\s*đường)(?!.*(?:bão|lũ|sạt\s*lở|mưa|thiên\s*tai|khắc\s*phục|sụt\s*lún|nứt\s*toác|hư\s*hỏng))\b",

    # ROUTINE WEATHER (Non-disaster/Pleasant weather)
    r"\b(?:nắng\s*đẹp|thời\s*tiết\s*thuận\s*lợi|nắng\s*ấm|gió\s*nhẹ|mây\s*rải\s*rác|không\s*mưa|nắng\s*chan\s*hòa|bình\s*minh|hoàng\s*hôn)\b",
    
    # ACADEMIC & EXAM SEASONS (Metaphorical heat/waves)
    r"\b(?:phòng\s*thi|sức\s*nóng\s*mùa\s*thi|sĩ\s*tử|vượt\s*vũ\s*môn|đề\s*thi|nộp\s*hồ\s*sơ|điểm\s*chuẩn|nguyện\s*vọng|tuyển\s*sinh)\b",
    
    # HISTORICAL NOSTALGIA & DOCUMENTARIES (Past events)
    r"\b(?:ký\s*ức|hồi\s*tưởng|nhìn\s*lại|phim\s*tài\s*liệu|năm\s*xưa|chuyện\s*cũ|tư\s*liệu\s*quý)\b",
    
    # RECRUITMENT & JOB MARKET
    r"\b(?:thị\s*trường\s*lao\s*động|nhu\s*cầu\s*tuyển\s*dụng|cơ\s*hội\s*việc\s*làm|làn\s*sóng\s*nhảy\s*việc|nộp\s*c\s*v|phỏng\s*vấn\s*tuyển\s*dụng)\b",

    # INDUSTRY, INFRA & ADMIN (Conditional - Blocked if NO disaster context)
    r"\b(?:giấy\s*phép\s*xây\s*dựng|hoàn\s*công|bê\s*tông\s*tươi|ép\s*cọc|nền\s*móng|đấu\s*thầu\s*xây\s*lắp|nhà\s*thầu\s*chính|nghiệm\s*thu\s*dự\s*án)\b",
    r"\b(?:dây\s*chuyền\s*sản\s*xuất|khu\s*công\s*nghiệp|kcn|khu\s*chế\s*xuất|nguyên\s*liệu\s*đầu\s*vào|sản\s*lượng\s*hàng\s*năm|dệt\s*may|da\s*giày|linh\s*kiện\s*điện\s*tử)\b",
    r"\b(?:vệ\s*sinh\s*môi\s*trường|thu\s*gom\s*rác\s*thải|nhà\s*máy\s*xử\s*lý|phí\s*vệ\s*sinh|cung\s*cấp\s*nước\s*sạch|giá\s*nước\s*sinh\s*hoạt|xử\s*lý\s*(?:rác|nước\s*thải|ô\s*nhiễm|môi\s*trường|điểm\s*đen|vướng\s*mắc|sai\s*phạm|thiếu\s*sót|nghẽn|tắc|ùn\s*tắc))\b",
    r"\b(?:đẩy\s*mạnh|thúc\s*đẩy|tăng\s*tốc|phấn\s*đấu)\s*(?:giải\s*ngân|đầu\s*tư|thi\s*công|tiến\s*độ|phát\s*triển|tăng\s*trưởng)\b",
    r"\bkhắc\s*phục\s*(?:sai\s*phạm|vướng\s*mắc|thiếu\s*sót|hậu\s*quả\s*từ\s*việc|nợ|lỗ|tình\s*trạng\s*ùn\s*tắc|ô\s*nhiễm)\b",
    r"\b(?:kiểm\s*tra\s*pccc|nghiệm\s*thu\s*phòng\s*cháy|diễn\s*tập\s*phòng\s*cháy|giấy\s*chứng\s*nhận\s*vệ\s*sinh\s*an\s*toàn|đạt\s*chuẩn\s*iso|hợp\s*quy\s*hợp\s*chuẩn|kiểm\s*định\s*chất\s*lượng)\b",
    r"\b(?:vệ\s*sinh\s*môi\s*trường\s*đô\s*thị|phân\s*loại\s*rác\s*tại\s*nguồn|phát\s*động\s*tết\s*trồng\s*cây|hưởng\s*ứng\s*giờ\s*trái\s*đất)\b",
    r"\b(?:tiêu\s*chuẩn\s*tcvn|astm|iso\s*9001|hợp\s*chuẩn\s*hợp\s*quy|tiêu\s*chuẩn\s*kỹ\s*thuật|quy\s*trình\s*kiểm\s*định|giấy\s*phép\s*hoạt\s*động)\b",

    # INFRASTRUCTURE, RAILWAY & PLANNING (Conditional - Blocked if NO disaster context)
    r"\b(?:công\s*nghệ\s*hầm\s*dìm|nhịp\s*dây\s*văng|cáp\s*dự\s*ứng\s*lực|gối\s*cầu|khe\s*co\s*giãn|hầm\s*xuyên\s*núi|công\s*trình\s*trọng\s*điểm|thông\s*xe\s*kỹ\s*thuật)\b",
    r"\b(?:đường\s*ray|khổ\s*đường\s*tiêu\s*chuẩn|nhà\s*ga\s*trên\s*cao|tàu\s*điện\s*ngầm|m\s*e\s*t\s*r\s*o|vận\s*hành\s*chạy\s*thử|hệ\s*thống\s*tín\s*hiệu\s*đường\s*sắt)\b",
    r"\b(?:tàu\s*cao\s*tốc\s*bắc\s*nam|khổ\s*đường\s*1435mm|tốc\s*đế\s*thiết\s*kế\s*350km/h|siêu\s*dự\s*án|khả\s*năng\s*thông\s*qua|tải\s*trọng\s*trục|hành\s*lang\s*kinh\s*tế)\b",
    r"\b(?:cấp\s*phép\s*xây\s*dựng|quy\s*hoạch\s*chi\s*tiết\s*1/500|mật\s*độ\s*xây\s*dựng|hệ\s*số\s*sử\s*dụng\s*đất|giải\s*phóng\s*mặt\s*bằng|đền\s*bù\s*tái\s*định\s*cư)\b",

    # AVIATION & AIRPORT OPS (Conditional - Blocked if NO disaster context)
    r"\b(?:hoãn\s*chuyến|chậm\s*chuyến|hủy\s*chuyến|hành\s*lý\s*ký\s*gửi|soát\s*vé|thủ\s*tục\s*check-in|thị\s*thực|visa)(?!.*(?:bão|lũ|thiên\s*tai|thời\s*tiết|mưa|sương\s*mù))\b",
    r"\b(?:đường\s*băng|sân\s*đỗ|nhà\s*ga\s*hành\s*khách|cảng\s*hàng\s*không|phí\s*sân\s*bay|dịch\s*vụ\s*mặt\s*đất|kiểm\s*soát\s*viên\s*không\s*lưu|an\s*ninh\s*hàng\s*không)(?!.*(?:bão|lũ|thiên\s*tai|thời\s*tiết|mưa|sương\s*mù|sấm\s*sét|gió\s*giật))\b",

    # ENERGY INFRASTRUCTURE (Conditional - Blocked if NO disaster context)
    r"\b(?:đường\s*dây\s*500kv|trạm\s*biến\s*áp|điện\s*gió|điện\s*mặt\s*trời|truyền\s*tải\s*điện|lưới\s*điện|cột\s*điện|trụ\s*điện)(?!.*(?:đổ|gãy|nghiêng|sạt|do|vì|khắc\s*phục|sự\s*cố)\s*(?:bão|lũ|thiên\s*tai|mưa|đất))\b",

    # FIRE SAFETY ADMIN (Conditional - Blocked if NO fire/disaster context)
    r"\b(?:nghiệm\s*thu\s*pccc|hồ\s*sơ\s*pccc|thẩm\s*duyệt\s*pccc|chứng\s*nhận\s*pccc|giấy\s*phép\s*pccc|lắp\s*đặt\s*hệ\s*thống\s*báo\s*cháy)\b",

    # CHARITY & RELIEF (Conditional - Blocked if NO disaster context)
    r"\b(?:quỹ\s*từ\s*thiện|vận\s*động\s*quyên\s*góp|mạnh\s*thường\s*quân|trao\s*quà|hỗ\s*trợ\s*nhân\s*đạo|tấm\s*lòng\s*vàng|lá\s*lành\s*đùm\s*lá\s*rách|chung\s*tay\s*góp\s*sức|chung\s*tay\s*hỗ\s*trợ)(?!\s*(?:bão|lũ|thiên\s*tai|khắc\s*phục|cứu\s*trợ|sạt\s*lở|đồng\s*bào|hậu\s*quả))\b",
    r"\b(?:hiến\s*máu\s*nhân\s*đạo|hành\s*trình\s*đỏ|quỹ\s*khuyến\s*học|tiếp\s*sức\s*đến\s*trường|chương\s*trình\s*từ\s*thiện|ngày\s*vì\s*người\s*nghèo)\b",

    # GOVT AGENCIES & GENERIC INFRA (Conditional - Blocked if NO disaster context)
    # Changed from (?!\s*...) to (?!.*...) to allow intervening words like "về việc", "ban hành"
    r"\b(?:ubnd|hđnd|mttq|thành\s*ủy|tỉnh\s*ủy|mặt\s*trận\s*tổ\s*quốc|đoàn\s*đại\s*biểu)(?!.*(?:kêu\s*gọi|ủng\s*hộ|hỗ\s*trợ|khắc\s*phục|chỉ\s*đạo|ứng\s*phó|phòng\s*chống|công\s*điện|văn\s*bản|thiệt\s*hại|khẩn\s*cấp|kiểm\s*tra|thăm\s*hỏi|tặng\s*quà|cứu\s*trợ|tìm\s*kiếm|nạn\s*nhân))\b",
    r"\b(?:cao\s*tốc|vành\s*đai\s*\d+|nút\s*giao|hầm\s*chui|cầu\s*vượt|metro|đường\s*sắt|toa\s*tàu)(?!.*(?:sạt\s*lở|hư\s*hỏng|khắc\s*phục|mưa\s*lũ|ngập|chia\s*cắt|trôi|cuốn\s*trôi|sập|nạn|ngăn\s*lũ|nứt|gãy|đổ|sụt|lún|bão|lốc|thiên\s*tai|sự\s*cố|hồ\s*chứa|thủy\s*điện|khẩn\s*cấp))\b",
    r"\b(?:quy\s*hoạch\s*đô\s*thị|chỉnh\s*trang\s*đô\s*thị)\b",

    # F) Market, Labor, Admin & Services (Moved from Absolute)
    r"\b(?:tiểu\s*thương|sạp\s*hàng|chợ\s*đầu\s*mối|chợ\s*truyền\s*thống|ban\s*quản\s*lý\s*chợ)(?!\s*(?:cháy|ngập|lụt|tốc\s*mái|sập|hư\s*hỏng|bị\s*lũ|thiệt\s*hại|tan\s*hoang|sau\s*bão|khắc\s*phục))\b",
    r"\b(?:nghỉ\s*tết|lịch\s*nghỉ|quay\s*lại\s*làm\s*việc|ngày\s*làm\s*việc|công\s*sở|nghỉ\s*bù|đi\s*làm\s*trở\s*lại)(?!\s*(?:sau\s*bão|khắc\s*phục))\b",
    r"\b(?:nhập\s*cư|thị\s*thực|visa|hộ\s*chiếu|xuất\s*nhập\s*cảnh|di\s*trú|lãnh\s*sự|đại\s*sứ\s*quán)\b",
    r"\b(?:cây\s*ATM|rút\s*tiền|thẻ\s*ngân\s*hàng|mã\s*PIN|sổ\s*tiết\s*kiệm|đáo\s*hạn|chi\s*trả\s*lương|tiền\s*thưởng)\b",
    r"\b(?:đổi\s*tên\s*trường|thành\s*lập\s*trường|sáp\s*nhập\s*trường|công\s*bố\s*quyết\s*định|trao\s*quyết\s*định)(?!\s*(?:thành\s*lập|kiện\s*toàn)\s*(?:ban\s*chỉ\s*huy|đội|lực\s*lượng))\b",

    # Traffic Accidents (Specific Refinements)
    # Traffic Accidents (Moved to Conditional)
    # MOVED: r"\b(?:va\s*chạm|đâm\s*nhau|tự\s*gây|mất\s*lái)\s*(?:xe\s*máy|ô\s*tô|xe\s*tải)(?!\s*(?:do|vì|bởi)\s*(?:bão|lũ|mưa|gió|sạt\s*lở|trơn|ngập))",

    # === MOVED FROM ABSOLUTE VETO (JAN 2026 REFACTOR) ===
    # These are potential noise but should be allowed if the Score is high enough.
    
    # 1. CHARITY & DONATION
    r"\b(?:trao\s*tặng|tặng\s*quà|khánh\s*thành\s*nhà|nhà\s*tình\s*nghĩa|nhà\s*đại\s*đoàn\s*kết|mái\s*ấm|bò\s*giống|quỹ\s*thiện\s*nguyện|nuôi\s*em|chương\s*trình\s*từ\s*thiện|xây\s*nhà\s*cho\s*người\s*nghèo)(?!.*(?:bão|lũ|lụt|sạt\s*lở|thiên\s*tai|khẩn\s*cấp|cứu\s*trợ|khắc\s*phục|hỗ\s*trợ|tái\s*thiết|bị\s*ảnh\s*hưởng|ngập|giông|lốc))\b",
    
    # 2. ROUTINE UTILITY
    r"\b(?:công\s*ty\s*điện\s*lực|pc\s*\w+|đảm\s*bảo\s*điện|cấp\s*điện|hệ\s*thống\s*điện|cắt\s*điện)(?!.*(?:bão|lũ|sạt\s*lở|thiên\s*tai|khắc\s*phục|hư\s*hỏng|gãy|đổ|ngập|sự\s*cố|khôi\s*phục|hỗ\s*trợ))\b",
    
    # 3. TRAFFIC ACCIDENTS (Vehicle specific)
    r"\b(?:tai\s*nạn\s*giao\s*thông|xe\s*khách\s*(?:bị\s*)?lật|va\s*chạm\s*xe|tông\s*xe|xe\s*tải\s*cán|xe\s*máy\s*đấu\s*đầu|xe\s*đầu\s*kéo|va\s*chạm|đâm\s*liên\s*hoàn|xe\s*tải|xe\s*container|xe\s*buýt|lật\s*xe)(?!.*(?:do\s*bão|do\s*lũ|do\s*sạt\s*lở|do\s*mưa\s*lớn|trong\s*mưa\s*bão|bị\s*lũ\s*cuốn|trôi|ngập))\b",
    r"\b(?:va\s*chạm|đâm\s*nhau|tự\s*gây|mất\s*lái)\s*(?:xe\s*máy|ô\s*tô|xe\s*tải)(?!\s*(?:do|vì|bởi)\s*(?:bão|lũ|mưa|gió|sạt\s*lở|trơn|ngập))",
    r"(?:va\s*chạm\s*liên\s*hoàn|tai\s*nạn\s*giao\s*thông|lật\s*xe|tông\s*xe|xe\s*khách|xe\s*tải|xe\s*ben|lao\s*xuống\s*vực|lao\s*xuống\s*sông)(?!.*(?:do|vì|bởi|tại|xe|đoàn)\s*(?:bão|lũ|sạt\s*lở|mưa|đường\s*trơn|sương\s*mù|gió\s*mạnh|ngập|mưa\s*đá|thời\s*tiết|cứu\s*trợ|thiện\s*nguyện|hỗ\s*trợ))(?!.*(?:đoàn\s*thiện\s*nguyện|xe\s*cứu\s*trợ|hỗ\s*trợ\s*bão|cứu\s*nạn|không\s*qua\s*khỏi|ghe|thuyền|tàu|thủy\s*nạn|chia\s*cắt|tình\s*huống\s*khẩn\s*cấp|hư\s*hỏng\s*cầu|sập\s*cầu))",
    r"(?:xe\s*máy|ô\s*tô|xe\s*khách|xe\s*tải|xe\s*container|xe\s*đầu\s*kéo|xe\s*buýt|tàu\s*thủy|ca\s*nô|tàu\s*cá)\s*(?:lật|lao|tông|đâm|va\s*chạm|bốc\s*cháy|cháy)(?!.*(?:do|vì|bởi|tại|xe|đoàn)\s*(?:bão|lũ|sạt\s*lở|mưa|đường\s*trơn|sương\s*mù|gió\s*mạnh|ngập|mưa\s*đá|thời\s*tiết|cứu\s*trợ|thiện\s*nguyện|hỗ\s*trợ))(?!.*(?:đoàn\s*thiện\s*nguyện|xe\s*cứu\s*trợ|hỗ\s*trợ\s*bão|cứu\s*nạn|chia\s*cắt))",

    # 4. INFRASTRUCTURE INCIDENTS
    r"\b(?:sự\s*cố|hỏng\s*hóc|bảo\s*trì|ngắt\s*điện|mất\s*điện|cắt\s*điện)\s*(?:lưới\s*điện|trạm\s*biến\s*áp|đường\s*dây|cáp\s*quang|internet|hệ\s*thống)(?!.*(?:do|vì|bởi|khắc\s*phục|xuyên\s*đêm)\s*(?:bão|lũ|thiên\s*tai|sạt\s*lở|mưa))\b",

    # 5. SAFETY & WARNINGS (Ambiguous)
    r"\b(?:khuyến\s*cáo|nhắc\s*nhở|kỹ\s*năng|phòng\s*ngừa|tập\s*huấn)\s*(?:pccc|an\s*toàn|đuối\s*nước|tai\s*nạn)(?!\s*(?:ngập\s*lụt|bão|lũ|thiên\s*tai))\b",
    r"\b(?:ngã\s*vào\s*gầm|cuốn\s*vào\s*gầm|kẹt\s*trong\s*cabin|cá\s*ăn\s*thịt|đuối\s*nước\s*thương\s*tâm|tắm\s*sông|tắm\s*biển|rơi\s*xuống\s*sông)(?!.*(?:bão|lũ|lụt|mưa\s*lớn|nước\s*dâng|sạt\s*lở))\b",

    # 6. ADMINISTRATIVE DIRECTIVES (Moved from Absolute)
    r"\b(?:chỉ\s*thị|công\s*điện|lệnh\s*của\s*chủ\s*tịch\s*nước|công\s*văn|ban\s*hành\s*văn\s*bản)(?!.*(?:bão|lũ|thiên\s*tai|khắc\s*phục|hỗ\s*trợ|ứng\s*phó|khẩn\s*cấp|hỏa\s*tốc|sạt\s*lở|ngập\s*lụt|di\s*dời|sơ\s*tán|an\s*toàn|cứu\s*nạn|cứu\s*hộ|thiệt\s*hại|vỡ\s*đê|điện\s*khẩn))\b",

    # --- MOVED FROM ABSOLUTE TO CONDITIONAL (Fixing False Negatives) ---
    # Allowed if hazard signals are present (e.g. "khắc phục ngập lụt", "hỗ trợ bão lũ")
    r"\b(?:sư\s*đoàn|trung\s*đoàn|lữ\s*đoàn|tiểu\s*đoàn|quân\s*chủng|tiêm\s*kích|tàu\s*sân\s*bay|tên\s*lửa\s*đạn\s*đạo|tàu\s*ngầm|tác\s*chiến\s*điện\s*tử|chiến\s*lược\s*quân\s*sự)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|cứu\s*hộ|cứu\s*nạn|giúp\s*dân|vùng\s*lũ|bão|thiên\s*tai))",
    r"\b(?:giá\s*vàng\s*hôm\s*nay|vàng\s*miếng\s*sjc|vàng\s*nhẫn|tỷ\s*giá\s*trung\s*tâm|đồng\s*u\s*s\s*d|euro|yên\s*nhật|bảng\s*anh|ngoại\s*tệ|vàng\s*thế\s*giới)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|viện\s*trợ|cứu\s*trợ|thiên\s*tai))",
    r"\b(?:hệ\s*thống\s*pháp\s*luật|văn\s*bản\s*quy\s*phạm|luật\s*sửa\s*đổi|bổ\s*sung|quy\s*định\s*hướng\s*dẫn|nghị\s*định\s*chính\s*phủ|nghị\s*quyết\s*quốc\s*hội)\b(?!.*(?:khắc\s*phục|hỗ\s*trợ|kinh\s*phí|ngân\s*sách|thiên\s*tai|bão|lũ))",
    r"\b(?:venezuela|maduro|trump|biden|is|iraq|libya|gaza|nato|greenland|ukraine|zelensky|putin|nga\s*tấn\s*công|mỹ\s*cấm|tên\s*lửa\s*đạn\s*đạo|trung\s*tâm\s*quân\s*sự|slovakia|hong\s*kong|campuchia-thái\s*lan|liên\s*minh\s*châu\s*mỹ|trả\s*tự\s*do|bắt\s*giữ\s*tổng\s*thống|lula\s*da\s*silva|trấn\s*áp\s*biểu\s*tình|con\s*tin|tam\s*giác\s*vàng|xe\s*tăng|tên\s*lửa|s-350|starlink|vệ\s*tinh|bộ\s*ba\s*hạt\s*nhân|quan\s*hệ\s*với\s*triều\s*tiên|cuộc\s*chiến\s*nga|caracas|ngừng\s*bắn|chiến\s*sự|bụi\s*mịn|hàn\s*quốc|thái\s*lan|bangkok|ấn\s*độ|iran|sng|kherson|gaza|israel|thụy\s*sĩ|cảng\s*vụ\s*hàng\s*không|ngoại\s*trưởng|nigeria|greenland|eu|liên\s*minh\s*châu\s*âu)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|viện\s*trợ|cứu\s*trợ|đóng\s*góp|ủng\s*hộ|thiên\s*tai))",
]

# 3. SOFT NEGATIVE (RETAINED)
SOFT_NEGATIVE = [
    # A) Politics/Admin ceremony templates
    r"(?:kỳ\s*họp|phiên\s*họp|hội\s*nghị|đại\s*hội|văn\s*phòng|ubnd|hđnd|mttq)\s*(?:đảng|đảng\s*bộ|hđnd|quốc\s*hội|chi\s*bộ|cử\s*tri|toàn\s*quốc|tổng\s*kết|sơ\s*kết)",
    r"tiếp\s*xúc\s*cử\s*tri|chất\s*vấn|giải\s*trình|bầu\s*cử|ứng\s*cử",
    r"(?:bổ\s*nhiệm|miễn\s*nhiệm|điều\s*động|luân\s*chuyển|kỷ\s*luật|kiểm\s*tra|giám\s*sát)(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn|thiên\s*tai|bão|lũ|sạt\s*lở))",
    r"nghị\s*quyết|nghị\s*định|thông\s*tư|quyết\s*định|chỉ\s*thị(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn))",
    r"trợ\s*cấp\s*thất\s*nghiệp|đạt\s*chuẩn\s*nông\s*thôn\s*mới|nông\s*thôn\s*mới\s*nâng\s*cao(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn|cứu\s*người|thiên\s*tai|bão|lũ|sạt\s*lở|ngập))",

    # B) Digest formats
    r"bản\s*tin\s*(?:cuối\s*ngày|sáng|trưa|tối)|điểm\s*tin|tin\s*trong\s*nước|tin\s*quốc\s*tế",

    # C) Education and Awards
    r"(?:tốt\s*nghiệp|nhận\s*học\s*bổng|tuyển\s*sinh.*đại\s*học)(?!.*(?:sau\s*lũ|vùng\s*lũ))",
    r"giải\s*thưởng|vinh\s*danh|trao\s*huân\s*chương|cờ\s*thi\s*đua|kỷ\s*niệm|lễ\s*kỷ\s*niệm|văn\s*hóa\s*văn\s*nghệ|biểu\s*diễn",

    # D) Construction ceremony
    r"khởi\s*công|khánh\s*thành|nghiệm\s*thu(?!.*(?:kè|đê|hồ|đập|thủy\s*lợi|thoát\s*nước|chống\s*ngặp|chống\s*sạt\s*lở|thiên\s*tai|tái\s*thiết|khắc\s*phục|sửa\s*chữa|hư\s*hỏng|bão|lũ|ngập|nhà\s*tình\s*nghĩa))",

    # E) Missing persons (soft flag only if NOT clearly disaster-related)
    # r"mất\s*tích(?!.*(?:mưa\s*lũ|lũ|bão|nước\s*cuốn|sạt\s*lở|lũ\s*quét|tìm\s*kiếm\s*cứu\s*nạn))", # Removed to avoid false negatives for marine/rescue
    r"(?:thanh\s*niên|nữ\s*sinh|học\s*sinh)\s*mất\s*tích(?!.*(?:mưa\s*lũ|lũ|bão|nước\s*cuốn|rơi\s*xuống|đắm\s*thuyền|chìm\s*tàu|tìm\s*thấy\s*thi\s*thể))",

    # F) Agency/Org specific clutter (About Us, Intro, Technical Specs)
    r"về\s*agpc|giới\s*thiệu\s*chung|chức\s*năng\s*nhiệm\s*vụ|cơ\s*cấu\s*tổ\s*chức|sơ\s*đồ\s*tổ\s*chức",
    r"chống\s*sét\s*(?:cảm\s*ứng|lan\s*truyền|van|chủ\s*động)|kim\s*thu\s*sét|hệ\s*thống\s*tiếp\s*địa", # Lightning protection tech
]


# Combined Negative List for backward compatibility (used in NO_ACCENT generation)
DISASTER_NEGATIVE = ABSOLUTE_VETO + CONDITIONAL_VETO + SOFT_NEGATIVE

# Removed old compiled patterns


# Pre-compute unaccented patterns for matching against t0 (canonical text)
DISASTER_RULES_NO_ACCENT = []
for label, pats in DISASTER_RULES:
    nops = [risk_lookup.strip_accents(p) for p in pats]
    DISASTER_RULES_NO_ACCENT.append((label, nops))

DISASTER_CONTEXT_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_NEGATIVE]

# OPTIMIZATION: PRE-COMPILE REGEX
RE_FLAGS = re.IGNORECASE | re.VERBOSE | re.DOTALL

@lru_cache(maxsize=2048)
def v_safe(p: str) -> str:
    """
    Đảm bảo Regex an toàn khi dùng re.VERBOSE.
    Nếu mẫu là chuỗi đơn dòng, ta đổi khoảng trắng thành \\s+ để không bị nuốt mất.
    Nếu mẫu là chuỗi nhiều dòng (đã format), ta giữ nguyên.
    CẢNH BÁO: Không thay đổi nếu có look-behind (?<= hoặc (?<! vì sẽ gây lỗi variable-width.
    """
    if "\n" in p: return p
    if "(?<!" in p or "(?<=" in p: return p
    return p.replace(" ", r"\s+")

def build_mega_re(pats: List[str]):
    """
    Build accented mega-regex.
    """
    if not pats: return None
    pats_v = [v_safe(p) for p in pats]
    
    # Accented Mega-Regex
    try:
        mega_acc = re.compile("|".join(f"(?:{p})" for p in pats_v), RE_FLAGS)
        return mega_acc
    except:
        return None

# Pre-compute accented and unaccented patterns for high-performance matching
# Pre-compute accented patterns for high-performance matching
DISASTER_RULES_RE = []
for label, pats in DISASTER_RULES:
    pats_v = [v_safe(p) for p in pats]
    # Create accented compiled list
    compiled_acc = [re.compile(p, RE_FLAGS) for p in pats_v]
    # Attempt to also create a mega-regex for this label if possible
    try:
        mega_acc = re.compile("|".join(f"(?:{p})" for p in pats_v), RE_FLAGS)
        compiled_acc = [mega_acc]
    except: pass
    
    # Only append accented versions
    DISASTER_RULES_RE.append((label, compiled_acc))

# HIGH_PRIORITY_RE is already imported from sources
RISK_LEVEL_RE = re.compile(r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp\s*)?([1-5|I-V|V])", re.IGNORECASE)



# Define Veto Regexes as Mega-Regexes
ABSOLUTE_VETO_RE = build_mega_re(ABSOLUTE_VETO)
CONDITIONAL_VETO_RE = build_mega_re(CONDITIONAL_VETO)
SOFT_NEGATIVE_RE = build_mega_re(SOFT_NEGATIVE)

# [OPTIMIZED] Whitelist Pattern for Pre-compilation
WHITELIST_PATTERN_STR = r"(?:chiến\s*dịch\s*[\"“]?quang\s*trung[\"”]?|xả\s*lũ|xả\s*đáy|sơ\s*tán|di\s*dời\s*(?:dân|người)|cứu\s*hộ|cứu\s*nạn|khắc\s*phục\s*hậu\s*quả\s*(?:thiên\s*tai|bão|lũ|mưa|sạt\s*lở)|hỗ\s*trợ\s*khẩn\s*cấp|cấp\s*bách|nhà\s*chống\s*lũ|nhà\s*phao|hỗ\s*trợ\s*đồng\s*bào\s*vùng\s*lũ|ban\s*chỉ\s*huy\s*pctt|tìm\s*kiếm\s*cứu\s*nạn|đưa\s*thuyền\s*lên\s*bờ|tránh\s*bão|trú\s*tránh|neo\s*đậu|hố\s*tử\s*thần|sụt\s*lún|chi\s*viện|xe\s*cứu\s*trợ|hàng\s*cứu\s*trợ|tiếp\s*tế|phương\s*tiện\s*cứu\s*trợ|người\s*dân\s*vùng\s*lũ|bà\s*con\s*vùng\s*lũ|khám\s*chữa\s*bệnh.*vùng\s*lũ|tiêm.*vùng\s*lũ|vắc\s*xin.*vùng\s*lũ|ứng\s*cứu\s*viễn\s*thông|khôi\s*phục\s*liên\s*lạc|cấm\s*lưu\s*thông|phân\s*luồng|khắc\s*phục\s*sạt\s*trượt|thông\s*tuyến|khởi\s*công.*nhà.*vùng\s*lũ|xây\s*dựng.*nhà.*vùng\s*lũ|sửa\s*chữa.*nhà.*vùng\s*lũ|công\s*trình\s*cấp\s*thiết|uav.*cứu\s*trợ|trực\s*thăng.*cứu\s*trợ|tàu\s*hỏa.*cứu\s*trợ|xâm\s*thực|sạt\s*lở\s*bờ\s*sông|gặt\s*lúa\s*chạy\s*lũ|thu\s*hoạch.*chạy\s*lũ|bảo\s*vệ.*đê.*kè|sửa\s*chữa.*hư\s*hỏng.*(?:bão|lũ)|học\s*sinh.*nghỉ\s*học|cho\s*học\s*sinh.*nghỉ|trường.*ngập|sách\s*vở.*vùng\s*lũ|hỗ\s*trợ.*giáo\s*dục|vào\s*biển\s*đông|bão.*đổ\s*bộ|cấm\s*biển|lệnh\s*cấm\s*biển|cấm\s*phương\s*tiện|cấm\s*xe|cấm\s*đường|nước\s*cuốn\s*trôi|xuất\s*quân.*hỗ\s*trợ|bộ\s*đội.*vượt\s*lũ|công\s*an.*giúp\s*dân|cảnh\s*sát.*hỗ\s*trợ|cảnh\s*sát.*giúp\s*dân|cảnh\s*sát.*phòng\s*chống|chiến\s*sĩ.*hỗ\s*trợ|chiến\s*sĩ.*giúp\s*dân|tình\s*trạng\s*khẩn\s*cấp|tình\s*huống\s*khẩn\s*cấp|sơ\s*tán\s*dân|di\s*dời\s*khẩn\s*cấp|tái\s*thiết.*thiên\s*tai|khởi\s*công.*nhà.*thiên\s*tai|xây\s*dựng.*nhà.*thiên\s*tai|sửa\s*chữa.*nhà.*thiên\s*tai|khởi\s*công.*hồ|sửa\s*chữa.*hồ|bch\s*phòng\s*chống|ban\s*chỉ\s*huy|tìm\s*kiếm\s*cứu\s*nạn|tkcn|diễn\s*tập.*phòng\s*chống|diễn\s*tập.*cứu\s*nạn|sắc\s*phục\s*cand|công\s*an.*cứu\s*nạn|chiến\s*sĩ.*cứu\s*nạn|binh\s*sĩ.*cứu\s*hộ|csgt.*giải\s*cứu|cảnh\s*sát.*giải\s*cứu|cứu\s*nạn.*khẩn\s*cấp|xây\s*nhà.*sau\s*lũ|sửa\s*nhà.*sau\s*lũ|nhà.*tình\s*nghĩa.*lũ|nghỉ\s*học.*tránh\s*bão|nghỉ\s*học.*chống\s*bão|ứng\s*trực.*(?:bão|lũ)|trực\s*ban.*(?:bão|lũ)|đảm\s*bảo\s*an\s*toàn.*(?:bão|lũ|thiên\s*tai)|tạm\s*dừng.*du\s*lịch|công\s*bố.*tình\s*huống\s*khẩn\s*cấp|công\s*bố.*thiên\s*tai|viện\s*trợ.*khẩn\s*cấp|cháy\s*rừng|kêu\s*cứu\s*khẩn\s*cấp|ứng\s*dụng.*cứu\s*nạn|nâng\s*cao\s*năng\s*lực.*(?:thiên\s*tai|bão|lũ)|bị\s*cô\s*lập|khắc\s*phục.*thiên\s*tai|triển\s*khai.*ứng\s*phó|ứng\s*dụng.*mưa\s*lũ|diễn\s*tập.*ứng\s*phó|sinh\s*viên.*hỗ\s*trợ|thanh\s*niên.*xung\s*kích|an\s*toàn.*(?:hồ\s*đập|hồ\s*chứa|thủy\s*lợi)|dự\s*trữ.*nước|vneid.*cứu\s*trợ|du\s*khách.*mắc\s*kẹt|giải\s*cứu.*du\s*khách|chủ\s*động\s*ứng\s*phó|huy\s*động.*lực\s*lượng.*(?:bão|lũ)|bão\s*số\s*\d+|vận\s*chuyển.*(?:hàng)?\s*cứu\s*trợ|di\s*dời.*(?:khỏi.*chung\s*cư|tránh\s*bão|khẩn\s*trương)|nghỉ\s*học.*(?:tránh\s*bão|phòng\s*chống))"
WHITELIST_RE = re.compile(WHITELIST_PATTERN_STR, re.IGNORECASE)

# DISASTER_CONTEXT needs individual matching to identify specific context contributions
DISASTER_CONTEXT_RE = [re.compile(v_safe(p), RE_FLAGS) for p in DISASTER_CONTEXT]



# MEGA-REGEX for Source Keywords
AMBIGUOUS_KEYWORDS = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
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
RE_AGENCY = re.compile(r"""
(?ix)                                  # i: ignorecase, x: verbose
\b(
    # 1) KTTV (National Hydro-Met)
    Tổng\s*cục\s*(?:KTTV|Khí\s*tượng\s*Thủy\s*văn)
  | Trung\s*tâm\s*Dự\s*báo(?:\s*Khí\s*tượng\s*Thủy\s*văn)?(?:\s*Quốc\s*gia)?     # "Trung tâm Dự báo KTTV QG"
  | (?:Đài|Trạm)\s*(?:Khí\s*tượng\s*Thủy\s*văn|KTTV)(?:\s*khu\s*vực|\s*tỉnh|\s*địa\s*phương)?  # Đài KTTV khu vực/tỉnh
  | NCHMF                                                                               # viết tắt hay gặp

    # 2) PCTT / Đê điều (Disaster & Dyke)
  | Cục\s*Quản\s*lý\s*đê\s*điều(?:\s*và\s*(?:Phòng,\s*chống\s*thiên\s*tai|PCTT))?
  | (?:Tổng\s*cục|Cục)\s*(?:Phòng,\s*chống\s*thiên\s*tai|PCTT)
  | Ban\s*Chỉ\s*đạo\s*(?:Quốc\s*gia|Trung\s*ương)\s*về\s*Phòng,\s*chống\s*thiên\s*tai
  | Văn\s*phòng\s*thường\s*trực\s*Ban\s*Chỉ\s*đạo(?:\s*(?:Quốc\s*gia|Trung\s*ương))?\s*về\s*(?:PCTT|Phòng,\s*chống\s*thiên\s*tai)
  | Ban\s*Chỉ\s*huy\s*(?:PCTT(?:\s*&\s*TKCN)?|Phòng,\s*chống\s*thiên\s*tai(?:\s*&\s*Tìm\s*kiếm\s*cứu\s*nạn)?)

    # 3) Động đất / Sóng thần
  | Viện\s*Vật\s*lý\s*Địa\s*cầu
  | Trung\s*tâm\s*Báo\s*tin\s*động\s*đất(?:\s*và\s*cảnh\s*báo\s*sóng\s*thần)?
  | Trung\s*tâm\s*Cảnh\s*báo\s*sóng\s*thần

    # 4) Tìm kiếm cứu nạn hàng hải
  | Trung\s*tâm\s*Phối\s*hợp\s*tìm\s*kiếm\s*cứu\s*nạn\s*hàng\s*hải(?:\s*Việt\s*Nam)?
  | VMRCC
  | MRCC

    # 5) Thủy lợi / Tài nguyên nước (hay xuất hiện khi xả lũ, hồ chứa)
  | (?:Tổng\s*cục|Cục)\s*Thủy\s*lợi
  | Cục\s*Quản\s*lý\s*tài\s*nguyên\s*nước

    # 6) Lâm nghiệp / cháy rừng
  | Tổng\s*cục\s*Lâm\s*nghiệp
  | Cục\s*Kiểm\s*lâm

    # 7) Quân đội / Quốc phòng (Hỗ trợ cứu nạn) - Updated
  | Bộ\s*Quốc\s*phòng
  | Bộ\s*Tư\s*lệnh\s*(?:Thủ\s*đô|TP\.HCM|Cảnh\s*sát\s*cơ\s*động|Biên\s*phòng|Công\s*binh|Cảnh\s*sát\s*biển)
  | Quân\s*khu\s*(?:\d+|[A-Z]+)
  | Ban\s*Chỉ\s*huy\s*(?:Quân\s*sự|Phòng\s*thủ\s*dân\s*sự)
  | Bộ\s*đội\s*Biên\s*phòng
  | Cảnh\s*sát\s*cơ\s*động
  | Cảnh\s*sát\s*biển
)\b
""", re.IGNORECASE | re.VERBOSE)

WEIGHT_RULE = 5.0
WEIGHT_IMPACT = 5.0
WEIGHT_AGENCY = 2.5
WEIGHT_SOURCE = 0.5
WEIGHT_PROVINCE = 3.0


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
        # Handle Ranges (e.g. 5-7)
        nums = re.findall(r"\d+", s.replace(".", "").replace(",", ""))
        if len(nums) >= 2:
            res["min"] = int(nums[0])
            res["max"] = int(nums[1])
        elif nums:
            res["min"] = res["max"] = int(nums[0])

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
        return True, False, False, negative_matches

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

    return absolute_veto, conditional_veto, soft_negative, negative_matches

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
    
    # cấp/cap X (exclude 'khẩn cấp' and 'giật')
    # Support both accented and unaccented variations
    for m in re.finditer(r"(?<!khan\s)(?<!khẩn\s)(?<!giat\s)(?<!giật\s)(?:cấp|cap)\s*(\d{1,2})(?:\s*(?:-|,|đến|tới|den|toi)\s*(\d{1,2}))?", t):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
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
    if (title and sources.VIP_TERMS_RE.search(title)) or sources.VIP_TERMS_RE.search(text):
        is_vip = True

    # Helper 2: Negative Checks (Absolute/Conditional/Soft Vetoes)
    absolute_veto, conditional_veto, soft_negative, negative_matches = check_veto_status(
        t_acc, t_title_acc, has_hazard=(len(rule_matches) > 0)
    )

    # 2. Hazard (Rule) Match - Category identification
    hazard_found = len(rule_matches) > 0
    rule_score = WEIGHT_RULE if hazard_found else 0.0
    
    # [OPTIMIZATION] Multi-Hazard Bonus: If article mentions multiple categories (e.g. Storm + Flood)
    if len(rule_matches) >= 2:
        rule_score += 1.0
        if len(rule_matches) >= 3:
            rule_score += 0.5

    # [OPTIMIZATION] High-Priority Keyword Boost
    if HIGH_PRIORITY_RE and HIGH_PRIORITY_RE.search(t_acc):
        rule_score += 1.0 # Significant boost for dangerous event types

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
        
        if level >= 3: rule_score += 3.0 # Level 3+ is high priority
        elif level >= 1: rule_score += 1.5

    # [OPTIMIZATION] Title Boost: If hazard keyword in title, add bonus
    if title_rule_match:
        rule_score += 2.0 # Increased from 1.5

    # 2. Impact Match - Deaths, missing, or significant damage/metrics
    # REFINED: Use extracted objects to determine impact_score
    raw_details = extract_impact_details(text, t_acc=t_acc)

    # We define impact_found if any typed list in raw_details is non-empty
    impact_found = any(len(lst) > 0 for lst in raw_details.values())

    metrics = extract_disaster_metrics(text, t_acc=t_acc)
    real_metrics_found = any(k != "duration_days" for k in metrics.keys())

    # Impact score is fixed if ANY major impact sign is found after negation-filtering
    impact_score = WEIGHT_IMPACT if (impact_found or real_metrics_found) else 0.0

    # Determine event stage using impact signals for priority
    event_stage = determine_event_stage(search_text, impact_detected=impact_found)

    # [OPTIMIZATION] Stage Bonus: Help recovery/aid news reach approval
    stage_bonus = 0.0
    if event_stage == "RECOVERY":
        stage_bonus += 1.5
    elif event_stage == "FORECAST":
        stage_bonus += 1.5

    # [OPTIMIZATION] Magnitude Scaling: Bonus for extreme values
    extreme_bonus = stage_bonus
    if metrics.get("rainfall_mm", 0) >= 150: extreme_bonus += 1.5 # Lowered from 300
    if metrics.get("rainfall_mm", 0) >= 300: extreme_bonus += 1.0 # Extra bonus
    if metrics.get("wind_level", 0) >= 12: extreme_bonus += 2.0
    if metrics.get("earthquake_magnitude", 0) >= 6.0: extreme_bonus += 2.5
    
    # Note: raw_details contains dicts, need to extract max. Using d_count/m_count:
    d_count = sum(d["max"] for d in raw_details.get("deaths", []))
    m_count = sum(m["max"] for m in raw_details.get("missing", []))
    if (d_count + m_count) >= 5: extreme_bonus += 2.0
    
    impact_score += extreme_bonus

    # 3. Agency Match - Official source/agency
    agency_match = bool(RE_AGENCY.search(t_acc))
    agency_score = WEIGHT_AGENCY if agency_match else 0.0

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

    # [OPTIMIZATION] Strategic Location Boost: Bonus for dams, passes, etc.
    sensitive_bonus = 1.0 if sensitive_hits else 0.0

    # Proper Noun Boost (Strictness adjustment)
    proper_boost = 0.5 if any(h.get("is_proper") for h in prov_hits) else 0.0
    province_score = (WEIGHT_PROVINCE if location_found else 0.0) + proper_boost + sensitive_bonus

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
    
    source_score = min(4.0, float(len(non_ambiguous_hits)) * WEIGHT_SOURCE)

    # [OPTIMIZATION] Authority Boost: Scale points based on source tier
    # Level 1: Standard (0.0)
    # Level 2: Trusted (1.5)
    # Level 3: High Authority / Gov (4.0) - Replaces common 3.0+ user request
    authority_bonus = 0.0
    if not soft_negative:
        if authority_level >= 3:
            authority_bonus = 4.0
        elif authority_level == 2 or trusted_source:
            authority_bonus = 1.5

    # Context Matches (Optimized)
    context_hits = []
    # Use DISASTER_CONTEXT_RE
    for i, pat_re in enumerate(DISASTER_CONTEXT_RE):
        if pat_re.search(t_acc):
            context_hits.append(DISASTER_CONTEXT[i])



    # Sensitive Locations Check (Metadata)
    sensitive_found = []
    # Collect all findings (already combined in sensitive_hits above)
    for loc_name in sensitive_hits:
        sensitive_found.append(loc_name)
        context_hits.append(f"sensitive_loc:{loc_name}")

    context_score_val = len(context_hits)

    # UNIFIED CONFIDENCE SCORE
    # Add context bonus (0.5 per hit, max 3.0)
    context_bonus = min(3.0, context_score_val * 0.5)
    
    # [OPTIMIZATION] Gold Standard Boost (Refined for User Request):
    # Goal: Pending > 90% accuracy, Auto-Approve 100% for clear cases.
    
    gold_boost = 0.0
    
    # Regex checks for [Hazard] + [Preposition] + [Proper Noun Location OR Geographical feature]
    # Allow "sông", "suối", "đèo", "cầu" as location markers to capture "Sạt lở bờ sông Lô"
    # [FIX] Enhanced accuracy: Ensure extraction actually found a location in the title
    # old loose regex: diamond_pattern = re.search(r"...", t_title_acc, re.IGNORECASE)
    
    title_has_geo = False
    if best_prov != "unknown":
        # Check if this best_prov matches something in the title
        # best_prov comes from prov_hits which prioritizes title matches (H2: Title Match)
        if best_prov.lower() in t_title_acc:
            title_has_geo = True
            
    if rule_score > 0 and title_has_geo:
        gold_boost += 8.0 # High confidence boost for [Hazard in Title] + [Location in Title]
        
    # Condition B: TRUSTED WARNING (Official Sources emitting Warnings)
    # If it's a trusted source giving a forecast/warning -> Auto Approve
    if trusted_source and (event_stage == "FORECAST" or sources.RE_FORECAST.search(t_title_acc)):
        gold_boost += 6.0
        
    # Condition C: STANDARD GOLD (High Reliability Combo)
    # Article has Rule + Province + (Impact OR Agency/Trusted)
    if rule_score > 0 and (province_score > 0 or sensitive_bonus > 0):
        # If we have impacts OR it is from a trusted source/agency
        if (impact_found or real_metrics_found):
             if agency_match or authority_bonus > 0 or trusted_source:
                  gold_boost += 5.0 # High confidence -> Auto Approve zone
             else:
                  gold_boost += 2.5 # Good confidence -> Likely Pending/Approved
        elif trusted_source:
             # Trusted source with Rule + Location but no explicit impact stats yet (Breaking news)
             gold_boost += 3.0 # Push to Pending/Approved
             
    score = rule_score + impact_score + agency_score + source_score + province_score + authority_bonus + context_bonus + gold_boost
    
    # [CRITICAL] VIP Boost: If it's a VIP term, it must pass!
    if is_vip:
        score += 30.0 # Force pass (> 15.0)

    # [OPTIMIZATION] Title Inconsistency Penalty: 
    # If title mentions major hazard (Storm, Flood) but body lacks impact/metrics
    major_hazard_titles = ["bão", "siêu bão", "lũ ống", "lũ quét", "ngập sâu", "sạt lở"]
    if any(kh in (title or "").lower() for kh in major_hazard_titles):
        if not (impact_found or real_metrics_found):
            score -= 3.0 # Penalty for clickbait/generic routine mentions

    # [OPTIMIZATION] Penalty for No Hazard Rule Match (Accident & Noise filtering)
    # If we didn't match a specific Disaster Rule (Storm, Flood, etc.), we penalize.
    if rule_score == 0.0:
        # Check casualty count (calculated above)
        total_casualties = d_count + m_count
        if total_casualties == 0:
            # No hazard + No deaths/missing = Heavy Penalty (Likely noise, minor accident, or admin news)
            score -= 5.0
        elif total_casualties >= 5:
            # High casualties regardless of rule match -> Keep it (No penalty, maybe even boost)
            score += 2.0
        else:
            # No hazard + FEW deaths involved = Ambiguous (Could be crime, traffic, or unknown disaster)
            # We apply a smaller penalty to keep it from 'Auto-Approve' but allow 'Pending' if Score is ok
            score -= 1.0 # Reduced from 2.0
    
    # [FIX] Conditional Veto Penalty
    if conditional_veto and rule_score == 0.0:
        score -= 10.0 # Effectively kill the score if it's a conditional veto (accident/fire) with no disaster rule match
        
    # [OPTIMIZATION] International News Filter
    # If article mentions international locations (e.g. Philippines, Japan) but NO Vietnamese location/region
    # We deprioritize it heavily unless it explicitly mentions "Biển Đông" (covered by Storm rules) or "Việt Nam"
    # Note: location_found = (prov_hits OR sensitive_hits)
    if len(international_hits) > 0 and not location_found:
        # Check for explicit "Việt Nam" mention just to be safe
        if "việt nam" not in t_acc and "viet nam" not in t_acc:
             score -= 10.0
    
    if score < 0: score = 0.0
    
    # [OPTIMIZATION] Soft Negative Penalty: Significant reduction for ambiguous noise
    if soft_negative:
        score -= 4.0
        if score < 0: score = 0.0

    context_score = context_score_val


    impact_details = raw_details # Re-use already extracted details

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_found,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": rule_score,
        "hazard_counts": hazard_counts,
        "hazard_weights": hazard_weights,
        "context_score": context_score,
        "sensitive_locations": sensitive_found,
        "absolute_veto": absolute_veto,
        "conditional_veto": conditional_veto,
        "hard_negative": absolute_veto, # Legacy compat
        "soft_negative": soft_negative,
        "negative_hit": negative_matches,
        "is_vip": is_vip,
        "metrics": metrics,
        "impact_details": impact_details,
        "is_province_match": best_prov != "unknown",
        "is_agency_match": agency_match is not None,
        "is_sensitive_location": len(sensitive_found) > 0,
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
    if scores["FORECAST"] > scores["INCIDENT"]:
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
        if re.search(r"(?:động\s*đất|sóng\s*thần|rung\s*chấn|triều\s*cường|mưa\s*đá|lũ\s*quét|sạt\s*lở|lũ\s*ống|hạn\s*mặn|xâm\s*nhập\s*mặn|sụt\s*lún|gió\s*lốc|vòi\s*rồng|mưa\s*(?:lớn|lũ|to|dông|bão)|ngập(?:\s*(?:lụt|úng|nặng))?|rốn\s*lũ|lũ\s*lụt|nước\s*dâng|xả\s*lũ|vỡ\s*đê|vỡ\s*đập|vỡ\s*hồ|hồ\s*chứa\s*.*vỡ|sập\s*cầu|sập\s*nhà|sập\s*bờ\s*kè|sập\s*đê|cấm\s*biển|cấm\s*đường|mất\s*tích\s*do\s*lũ|lệnh\s*sơ\s*tán|tình\s*trạng\s*khẩn\s*cấp|khắc\s*phục\s*hậu\s*quả|hàng\s*cứu\s*trợ|tiếp\s*tế|chết\s*người\s*(?:do|vì|trong)\s*(?:lũ|bão|ngập|sạt|vỡ|thiên\s*tai)|(?:tái\s*thiết|hồi\s*sinh|khôi\s*phục|phục\s*hồi|cứu\s*trợ|viện\s*trợ).*(?:lũ|bão|thiên\s*tai|ngập|sạt\s*lở))", title_lower, re.IGNORECASE): return True
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
    # Unless it was a Definitive Event or VIP (handled above)
    if not (has_impact or (has_hazard and has_location)):
        return False

    # 2. Main Threshold Check (11.0 points to pass after bonuses - Increased from 10.0)
    if sig["score"] >= 11.0:
        return True

    # 3. Trusted Source / Verification Fallback (9.5 for official - Increased from 8.0)
    if trusted_source and sig["score"] >= 9.5:
        return True

    is_forecast = sig["stage"] == "FORECAST"
    is_planning = any(pk in full_text.lower() for pk in PLANNING_PREP_KEYWORDS)
    
    # Article Mode Thresholds:
    # Increased to 10.0 for all types as per user request to be stricter for 'Pending'
    threshold = 10.5 if is_forecast else 10.0
    
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
        reason = "Negative keyword match (Veto)"
    elif sig["conditional_veto"] and sig["hazard_score"] == 0:
        reason = "Conditional Veto (No disaster hazard match)"
    elif sig["score"] >= 15.0: 
        reason = "Passed (Approved)"
    elif sig["score"] >= 10.0:
        reason = "Passed (Pending Review)"
    elif sig.get("rule_matches"): 
        reason = f"Low Score ({sig['score']:.1f}). Met: {sig['rule_matches']}"
    
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
    # [OPTIMIZED] Whitelist / Bypass Veto
    # Specific government campaigns or critical phrases that might trigger vetoes
    # "Chiến dịch Quang Trung": Housing recovery campaign (often vetoed by military/history terms)
    # "xả lũ", "sơ tán": Critical actions that must pass
    if "Chiến dịch Quang Trung" in t or "chiến dịch Quang Trung" in t:
         pass # Skip Veto check
    elif re.search(r"(?:xả\s*lũ|xả\s*đáy|sơ\s*tán|di\s*dời\s*dân|cứu\s*hộ|cứu\s*nạn|khắc\s*phục\s*hậu\s*quả\s*(?:thiên\s*tai|bão|lũ|mưa|sạt\s*lở)|nhà\s*chống\s*lũ|nhà\s*phao|hỗ\s*trợ\s*đồng\s*bào\s*vùng\s*lũ|chằng\s*chống\s*nhà|đưa\s*thuyền\s*lên\s*bờ|tránh\s*bão|trú\s*tránh|hố\s*tử\s*thần|sụt\s*lún|chi\s*viện|xe\s*cứu\s*trợ|hàng\s*cứu\s*trợ|tiếp\s*tế|người\s*dân\s*vùng\s*lũ|bà\s*con\s*vùng\s*lũ|khám\s*chữa\s*bệnh.*vùng\s*lũ|tiêm.*vùng\s*lũ|vắc\s*xin.*vùng\s*lũ|ứng\s*cứu\s*viễn\s*thông|khôi\s*phục\s*liên\s*lạc|cấm\s*lưu\s*thông|phân\s*luồng|khắc\s*phục\s*sạt\s*trượt|thông\s*tuyến|khởi\s*công.*nhà.*vùng\s*lũ|xây\s*dựng.*nhà.*vùng\s*lũ|sửa\s*chữa.*nhà.*vùng\s*lũ|công\s*trình\s*cấp\s*thiết|uav.*cứu\s*trợ|trực\s*thăng.*cứu\s*trợ|tàu\s*hỏa.*cứu\s*trợ|xâm\s*thực|sạt\s*lở\s*bờ\s*sông|gặt\s*lúa\s*chạy\s*lũ|thu\s*hoạch.*chạy\s*lũ|bảo\s*vệ.*đê.*kè|sửa\s*chữa.*hư\s*hỏng.*(?:bão|lũ)|học\s*sinh.*nghỉ\s*học|cho\s*học\s*sinh.*nghỉ|trường.*ngập|sách\s*vở.*vùng\s*lũ|hỗ\s*trợ.*giáo\s*dục|vào\s*biển\s*đông|bão.*đổ\s*bộ|cấm\s*biển|lệnh\s*cấm\s*biển|cấm\s*phương\s*tiện|cấm\s*xe|cấm\s*đường|nước\s*cuốn\s*trôi|xuất\s*quân.*hỗ\s*trợ|bộ\s*đội.*vượt\s*lũ|công\s*an.*giúp\s*dân|cảnh\s*sát.*hỗ\s*trợ|cảnh\s*sát.*giúp\s*dân|cảnh\s*sát.*phòng\s*chống|chiến\s*sĩ.*hỗ\s*trợ|chiến\s*sĩ.*giúp\s*dân|tình\s*trạng\s*khẩn\s*cấp|tình\s*huống\s*khẩn\s*cấp|sơ\s*tán\s*dân|di\s*dời\s*khẩn\s*cấp|tái\s*thiết.*thiên\s*tai|khởi\s*công.*nhà.*thiên\s*tai|xây\s*dựng.*nhà.*thiên\s*tai|sửa\s*chữa.*nhà.*thiên\s*tai|khởi\s*công.*hồ|sửa\s*chữa.*hồ|bch\s*phòng\s*chống|ban\s*chỉ\s*huy|tìm\s*kiếm\s*cứu\s*nạn|tkcn|diễn\s*tập.*phòng\s*chống|diễn\s*tập.*cứu\s*nạn|sắc\s*phục\s*cand|công\s*an.*cứu\s*nạn|chiến\s*sĩ.*cứu\s*nạn|binh\s*sĩ.*cứu\s*hộ|csgt.*giải\s*cứu|cảnh\s*sát.*giải\s*cứu|cứu\s*nạn.*khẩn\s*cấp|xây\s*nhà.*sau\s*lũ|sửa\s*nhà.*sau\s*lũ|nhà.*tình\s*nghĩa.*lũ|nghỉ\s*học.*tránh\s*bão|nghỉ\s*học.*chống\s*bão|ứng\s*trực.*(?:bão|lũ)|trực\s*ban.*(?:bão|lũ)|đảm\s*bảo\s*an\s*toàn.*(?:bão|lũ|thiên\s*tai)|tạm\s*dừng.*du\s*lịch|công\s*bố.*tình\s*huống\s*khẩn\s*cấp|công\s*bố.*thiên\s*tai|viện\s*trợ.*khẩn\s*cấp|cháy\s*rừng|kêu\s*cứu\s*khẩn\s*cấp|ứng\s*dụng.*cứu\s*nạn|nâng\s*cao\s*năng\s*lực.*(?:thiên\s*tai|bão|lũ)|bị\s*cô\s*lập|khắc\s*phục.*thiên\s*tai|triển\s*khai.*ứng\s*phó|ứng\s*dụng.*mưa\s*lũ|diễn\s*tập.*ứng\s*phó|sinh\s*viên.*hỗ\s*trợ|thanh\s*niên.*xung\s*kích|an\s*toàn.*(?:hồ\s*đập|hồ\s*chứa|thủy\s*lợi)|dự\s*trữ.*nước|vneid.*cứu\s*trợ|du\s*khách.*mắc\s*kẹt|giải\s*cứu.*du\s*khách|chủ\s*động\s*ứng\s*phó|huy\s*động.*lực\s*lượng.*(?:bão|lũ)|bão\s*số\s*\d+|vận\s*chuyển.*(?:hàng)?\s*cứu\s*trợ|di\s*dời.*(?:khỏi.*chung\s*cư|tránh\s*bão|khẩn\s*trương)|nghỉ\s*học.*(?:tránh\s*bão|phòng\s*chống))", t, re.IGNORECASE):
         pass # Skip Veto check for critical actions
    elif ABSOLUTE_VETO_RE and ABSOLUTE_VETO_RE.search(t):
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
        forest_indicators = ["rừng", "thực bì", "khoảnh", "tiểu khu", "lâm phần", "lâm nghiệp", "diện tích", "thảm thực vật"]
        # Check both title and body (normalized)
        if not any(fi in t_title for fi in forest_indicators) and not any(fi in t_body for fi in forest_indicators):
            hazard_weights["wildfire"] -= 10

    primary = "unknown"
    if hazard_weights:
        # Sort by weight, then by priority index (Using pre-mapped dictionary for O(1) lookup)
        sorted_hazards = sorted(
            hazard_weights.items(),
            key=lambda item: (-item[1], DISASTER_PRIORITY_MAP.get(item[0], 99))
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
        for f in fused:
            # Check for significant overlap with existing fused match
            s1, e1 = cand["span"]
            s2, e2 = f["span"]
            overlap = max(0, min(e1, e2) - max(s1, s2))
            
            if overlap > 0:
                # If same type or strongly overlapping, keep the more precise one
                if cand["precision"] > f["precision"]:
                    fused.remove(f)
                    fused.append(cand)
                elif cand["precision"] == f["precision"] and (e1-s1) > (e2-s2):
                    fused.remove(f)
                    fused.append(cand)
                
                is_conflict = True
                break
        
        if not is_conflict:
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
        "needs_verification": needs_verification,
        "has_impacts": has_impacts,
        "landmark": impacts.get("landmark")
    }
