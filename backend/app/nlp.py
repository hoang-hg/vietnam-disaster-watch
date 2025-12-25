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
_UNIT = r"(?:người|nạn\s*nhân|em|cháu|trẻ\s*em|học\s*sinh|công\s*nhân|thuyền\s*viên|ngư\s*dân|hành\s*khách|tài\s*xế|lái\s*xe|cư\s*dân|du\s*khách|chiến\s*sĩ)"

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
            r"\b(?P<qualifier>ít nhất|tối thiểu|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh|công nhân|chiến sĩ)\s*(chết|tử vong|thiệt mạng|tử nạn|tử thương|thương vong)\b",
            r"\b(làm|khiến)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)\s*(chết|tử vong|thiệt mạng|thương vong)\b",
            r"\b(tìm thấy|phát hiện)\s*(thi thể|xác)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh)?\b",
            r"\b(cướp đi sinh mạng|tước đi sinh mạng)\s*(của)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{DEATH_WORD}\b",
            rf"\b(?:làm|khiến|cướp\s*đi|tước\s*đi)\s*(?:thiệt\s*mạng|tử\s*vong|chết)?\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:{DEATH_WORD})?\b",
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
            "mat tich", "mat lien lac", "khong ro tung tich", "chua tim thay",
            "troi dat", "chim tau", "lat thuyen", "roi xuong bien",
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
            "du khách", "cư dân", "học sinh", "công nhân", "chiến sĩ",
            "bi thuong", "nhap vien", "cap cuu", "chan thuong", "da chan thuong", "bong", "gay xuong",
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

    "marine": {
        "terms": [
            "chìm tàu", "tàu chìm", "đắm tàu", "tàu đắm", "lật tàu", "lật thuyền", "trôi dạt", "dạt vào bờ", "mất tín hiệu", "mất liên lạc", "không liên lạc được", "gặp nạn trên biển", "gặp nạn", 
            "tai nạn đường thủy", "đánh chìm", "chìm", "đắm", "lật", "trôi", "tàu cá", "tàu hàng", "tàu du lịch", "sà lan", "thuyền", "cano", "ghe", "ghe chài", "ngư dân", "thuyền viên", "cứu nạn trên biển", 
            "tìm kiếm trên biển", "lai dắt", "kéo về bờ", "cứu nạn", "cứu hộ",
            "sự cố trên biển", "sự cố hàng hải", "tai nạn hàng hải", "tai nạn trên biển",
            "sự cố đường thủy", "tai nạn đường thủy nội địa",
            "gặp nạn trên biển", "gặp sự cố", "bị nạn", "cứu nạn hàng hải",
            "va chạm", "đâm va", "tông", "đâm vào đá ngầm", "mắc cạn",
            "chết máy", "hỏng máy", "hỏng động cơ", "mất lái", "mất điều khiển",
            "vỡ mạn", "thủng thân", "nước tràn vào", "ngập nước", "rò rỉ", "chập điện",
            "cháy tàu", "bốc cháy trên tàu", "nổ trên tàu",
            "trôi dạt", "dạt bờ", "dạt vào bờ", "dạt vào đảo", "lênh đênh",
            "mất tín hiệu", "mất liên lạc", "không liên lạc được", "mất sóng",
            "tàu cá", "tàu vận tải", "tàu hàng", "tàu du lịch", "tàu chở khách", "tàu cao tốc",
            "tàu kéo", "tàu container", "tàu dầu", "tàu dịch vụ", "tàu cứu hộ",
            "ca nô", "cano", "xuồng", "xuồng máy", "thuyền thúng", "thuyền nan",
            "sà lan", "phà", "đò", "tàu", "thuyền", "phương tiện thủy",
            "ngoài khơi", "trên vùng biển", "vùng biển", "cửa biển", "cửa sông", "luồng lạch",
            "vịnh", "eo biển", "khu neo đậu", "khu tránh trú bão",
            "tọa độ", "hải lý", "cách bờ", "cách đất liền",
            "lai dắt", "lai kéo", "cứu kéo", "kéo về bờ", "đưa vào bờ", "hộ tống",
            "Trung tâm Phối hợp tìm kiếm cứu nạn hàng hải", "MRCC",
            "Cảnh sát biển", "CSB", "Bộ đội Biên phòng", "BĐBP",
            "kiểm ngư", "tìm kiếm cứu nạn", "tìm kiếm cứu hộ", "cứu hộ", "cứu nạn",
            "đắm", "chìm", "lật", "lật úp", "lật nghiêng",
            "chim tau", "dam tau", "lat tau", "lat thuyen", "troi dat", "mat lien lac",
            "mac can", "hong may", "chet may", "lai dat", "cuu nan", "cuu ho",
            "tau ca", "tau cho khach", "phuong tien thuy",
        ],
        "regex": [
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\s*(bị|đã)?\s*(chìm|đắm|lật|trôi dạt|mất liên lạc|hư hỏng|mất tích|gặp nạn)\b",
            r"\b(chìm|đắm|lật|trôi dạt|đánh chìm|lai dắt|cứu hộ|cứu nạn)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|thuyền viên|ngư dân|thuyền|phương tiện|sà lan)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>ngư dân|thuyền viên)(?:[^0-9]{0,20})?\s*(bị|đã)?\s*(mất liên lạc|mất tích|trôi dạt|gặp nạn)\b",
            r"\b(mất liên lạc|cứu hộ|cứu nạn|liên lạc được)\s*(với|cho|with)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tàu cá|tàu hàng|tàu du lịch|tàu|ghe chài|ghe|thuyền thúng|ngư dân|thuyền viên|thuyền|phương tiện|sà lan)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{VESSEL}\s*(?:bị|đã)?\s*{INCIDENT}\b",
            rf"\b{INCIDENT}\s*{QUAL}\s*{NUM_HARD}\s*{VESSEL}\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{CREW}(?:[^0-9]{{0,25}})?\s*(?:bị|đã)?\s*(?:mất\s*liên\s*lạc|mất\s*tích|trôi\s*dạt|rơi\s*xuống\s*biển|gặp\s*nạn)\b",
            rf"\b(?:mất\s*liên\s*lạc|không\s*liên\s*lạc\s*được|không\s*bắt\s*được\s*liên\s*lạc)\s*(?:với)?(?:[^0-9]{{0,20}})?\s*{QUAL}\s*{NUM_HARD}\s*{VESSEL}\b",
            r"\btrôi\s*dạt\b(?:[^.\n]{0,60})?\b(?:cách\s*bờ|cách\s*đất\s*liền)\s*\d+(?:[.,]\d+)?\s*(?:hải\s*lý|hl|km)\b",
            r"\b(?:tọa\s*độ|toạ\s*độ)\b(?:[^.\n]{0,60})?\b(?:vĩ\s*độ|kinh\s*độ)\b",
            rf"\b(?:lai\s*dắt|lai\s*kéo|cứu\s*kéo|kéo\s*về\s*bờ|đưa\s*vào\s*bờ|hộ\s*tống)\b(?:[^0-9]{{0,40}})?\s*{QUAL}\s*{NUM_HARD}\s*{VESSEL}\b",
            # 4) Cứu nạn / Cứu hộ / Biên phòng
            r"(?:Trung\s*tâm\s*Phối\s*hợp\s*)?tìm\s*kiếm\s*cứu\s*nạn",
            r"VMRCC|MRCC",
            r"Cảnh\s*sát\s*biển|\bCSB\b",
            r"Bộ\s*đội\s*biên\s*phòng|\bBĐBP\b",
            r"Lực\s*lượng\s*cứu\s*nạn\s*cứu\s*hộ",
            r"Cảnh\s*sát\s*Phòng\s*cháy\s*chữa\s*cháy|\b(?:PCCC\s*&\s*CNCH|PCCC)\b",
            r"kiểm\s*ngư", r"\b(?:chim\s*tau|dam\s*tau|lat\s*tau|lat\s*thuyen|troi\s*dat|mac\s*can|hong\s*may|chet\s*may|lai\s*dat|cuu\s*nan|cuu\s*ho)\b",
        ]
    },

    "damage": {
        "terms": [
            "thiệt hại", "tổn thất", "ước tính thiệt hại", "thiệt hại về tài sản",
            "thiệt hại nặng", "thiệt hại nghiêm trọng", "tàn phá", "trắng tay", "mất trắng", "trôi sạch",
            "hư hỏng", "hư hại", "hư hỏng nặng", "hư hại nặng", "tổng giá trị thiệt hại", "con số thiệt hại",
            "sập", "đổ sập", "sập đổ", "đổ", "nứt", "tốc mái", 
            "sập nhà", "đổ tường", "nứt tường", "nứt nhà",
            "bay mái", "tốc mái hàng loạt", "xiêu vẹo", "đổ sập hoàn toàn",
            "ngập", "ngập nhà", "ngập sâu", "ngập lút", "ngập úng",
            "cuốn trôi", "trôi nhà", "trôi xe", "lũ cuốn",
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
            "thiet hai", "ton that", "uoc tinh", "toc mai", "sap", "hu hong",
            "sat lo", "sut lun", "xoi lo", "mat dien", "mat nuoc", "dut cap quang",
            "hoa mau", "cay trong", "gia suc", "gia cam", "long be", "be ca",
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
            rf"\b(?:mất\s*điện|cúp\s*điện|mất\s*nước|mất\s*sóng|gián\s*đoạn\s*thông\s*tin|đứt\s*cáp(?:\s*quang)?)\b(?:[^0-9]{{0,30}})?\b{QUAL}\s*(?P<num>\d{{1,3}}(?:[.,]\d{{3}})*|\d+)\s*(?P<unit>hộ|khách\s*hàng|thuê\s*bao|trạm\s*BTS)\b",
            r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta)\b(?:[^.\n]{0,30})?\b(?:lúa|mạ|hoa\s*màu|rau\s*màu|cây\s*trồng|vườn\s*cây|rừng|diện\s*tích)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:ngập(?:\s*úng|\s*sâu)?|hư\s*hại|hư\s*hỏng|thiệt\s*hại|mất\s*trắng|dập\s*nát|gãy\s*đổ)\b",
            r"\b(?:mất\s*trắng|thiệt\s*hại|hư\s*hại)\b(?:[^0-9]{0,25})?\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>con)\s*(?:trâu|bò|lợn|heo|dê|ngựa|gà|vịt|gia\s*súc|gia\s*cầm)\b(?:[^.\n]{0,25})?\b(?:bị\s*)?(?:chết|cuốn\s*trôi|thiệt\s*hại|mất)\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>lồng\s*bè|bè|ao|đầm)\b(?:[^.\n]{0,30})?\b(?:nuôi|thủy\s*sản|cá)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:hư\s*hỏng|cuốn\s*trôi|thiệt\s*hại|vỡ|trôi)\b",
            r"\b(?:cá|thủy\s*sản)\s*(?:chết|thiệt\s*hại)\b(?:[^0-9]{0,25})?\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>tấn|kg|con)?\b",
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>xe|ô\s*tô|xe\s*máy|phương\s*tiện)\b(?:[^.\n]{0,30})?\b(?:bị\s*)?(?:cuốn\s*trôi|ngập|hư\s*hỏng|trôi)\b",
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
            "gián đoạn thông tin", "gián đoạn viễn thông", "đứt cáp quang",
            "so tan", "di doi", "di tan", "cam duong", "dong duong", "phan luong",
            "cam bien", "cam ra khoi", "neo dau", "mat dien", "mat nuoc", "mat song", "dut cap quang",
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
            r"\b(?:đóng\s*cửa\s*trường|tạm\s*đóng\s*cửa\s*trường|cho\s*học\s*sinh\s*nghỉ|nghỉ\s*học|tạm\s*nghỉ\s*học)\b",
            r"\b(?:hoãn|dời|điều\s*chỉnh)\s*lịch\s*thi|hoãn\s*thi|dời\s*lịch\s*thi\b",
            r"\b(?:cấm\s*biển|cấm\s*ra\s*khơi|không\s*ra\s*khơi|tàu\s*thuyền\s*không\s*ra\s*khơi)\b",
            r"\b(?:kêu\s*gọi|yêu\s*cầu)\s*(?:tàu\s*thuyền|ngư\s*dân)\s*(?:vào\s*bờ|neo\s*đậu|trú\s*bão)\b",
            r"\bneo\s*đậu\s*tránh\s*trú|khu\s*neo\s*đậu|khu\s*tránh\s*trú\s*bão\b",
            r"\b(?:mất\s*điện|cúp\s*điện|cắt\s*điện|ngừng\s*cấp\s*điện)\b",
            r"\b(?:mất\s*nước|ngừng\s*cấp\s*nước|gián\s*đoạn\s*cấp\s*nước)\b",
            r"\b(?:mất\s*sóng|mất\s*mạng|mất\s*internet|gián\s*đoạn\s*thông\s*tin|đứt\s*cáp(?:\s*quang)?)\b",
            rf"\b{QUAL}\s*{NUM}\s*(?P<unit>hộ|khách\s*hàng|thuê\s*bao|trạm\s*BTS)\b(?:[^.\n]{{0,25}})?\b(?:mất\s*điện|mất\s*nước|mất\s*sóng|gián\s*đoạn)\b",
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
            "trôi lồng bè", "vỡ ao", "tràn ao", "thất thoát thủy sản", "cá chết", "tôm chết",
            "hoa mau", "cay trong", "lua", "ngo", "bap", "mia", "san", "rau mau",
            "gia suc", "gia cam", "trau", "bo", "lon", "heo", "ga", "vit",
            "thuy san", "tom", "ca", "ao nuoi", "dam nuoi", "long be", "be ca",
            "mat trang", "mat mua", "ngap ung", "hu hai", "thiet hai",
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

# Deduplicate impact terms to avoid biased scoring and reduce CPU overhead
for k, v in IMPACT_KEYWORDS.items():
    if "terms" in v:
        v["terms"] = dedupe_keep_order(v["terms"])

# Boilerplate tokens
BOILERPLATE_TOKENS = [
    r"\bvideo\b", r"\bảnh\b", r"\bclip\b", r"\bphóng\s*sự\b", r"\btrực\s*tiếp\b",
    r"\blive\b", r"\bhtv\b", r"\bphoto\b", r"\bupdate\b"
]

NEGATION_TERMS = {
    "deaths": ["không có người chết", "không có thương vong", "chưa ghi nhận thương vong", "không ghi nhận thiệt hại về người", "không có nạn nhân"],
    "missing": ["không có người mất tích", "không ai mất tích", "chưa ghi nhận mất tích", "không mất tích"],
    "injured": ["không ai bị thương", "không có người bị thương", "không ghi nhận thương vong", "không bị thương"],
    "damage": ["không gây thiệt hại", "chưa có thiệt hại", "không có thiệt hại về tài sản", "không ghi nhận thiệt hại", "không có thiệt hại đáng kể", "không ảnh hưởng đến", "không hư hỏng"],
    "general": ["bác bỏ", "tin đồn", "phi lý", "sai sự thật", "không chính xác"]
}

PLANNING_PREP_KEYWORDS = [
    "dự kiến", "kịch bản", "giả định", "diễn tập", "phương án", "chuẩn bị", "ứng phó", "trước khi", 
    "chống chịu", "nâng cao năng lực", "kế hoạch", "tổng kết", "hội thảo"
]

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
    # I. Units kept as is (11 units)
    "Hà Nội": ["Hà Nội", "HN", "Ha Noi", "Thủ đô Hà Nội"],
    "Huế": ["Huế", "Thành phố Huế", "TP Huế", "Thừa Thiên Huế", "TT Huế", "Thua Thien Hue"],
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

# Deduplicate province variants
for k, v in PROVINCE_MAPPING.items():
    PROVINCE_MAPPING[k] = dedupe_keep_order(v)
# List of valid (new) province names
PROVINCES = list(PROVINCE_MAPPING.keys())

# Geographic coordinates for the 34 provinces (Approximate Center)
PROVINCE_COORDINATES = {
    "Hà Nội": [21.0285, 105.8542],
    "Huế": [16.4637, 107.5908],
    "Lai Châu": [22.3846, 103.4641],
    "Điện Biên": [21.3852, 103.0235],
    "Sơn La": [21.3259, 103.9126],
    "Lạng Sơn": [21.8548, 106.7621],
    "Quảng Ninh": [21.0063, 107.5944],
    "Thanh Hóa": [20.0000, 105.5000],
    "Nghệ An": [19.0000, 105.0000],
    "Hà Tĩnh": [18.3444, 105.9056],
    "Cao Bằng": [22.6667, 106.2500],
    "Tuyên Quang": [22.0000, 105.2500], # Merged Tuyen Quang/Ha Giang
    "Lào Cai": [22.4833, 103.9667],    # Merged Lao Cai/Yen Bai
    "Thái Nguyên": [21.5928, 105.8442], # Merged Thai Nguyen/Bac Kan
    "Phú Thọ": [21.3236, 105.2111],    # Merged Phu Tho/Vinh Phuc/Hoa Binh
    "Bắc Ninh": [21.1833, 106.0667],    # Merged Bac Ninh/Bac Giang
    "Hưng Yên": [20.6500, 106.0500],    # Merged Hung Yen/Thai Binh
    "Hải Phòng": [20.8449, 106.6881],   # Merged Hai Phong/Hai Duong
    "Ninh Bình": [20.2539, 105.9750],   # Merged Ninh Binh/Ha Nam/Nam Dinh
    "Quảng Trị": [16.7500, 107.1667],   # Merged Quang Tri/Quang Binh
    "Đà Nẵng": [16.0544, 108.2022],    # Merged Da Nang/Quang Nam
    "Quảng Ngãi": [15.1206, 108.8042],  # Merged Quang Ngai/Kon Tum
    "Gia Lai": [14.0000, 108.0000],     # Merged Gia Lai/Binh Dinh
    "Khánh Hòa": [12.2500, 109.1833],   # Merged Khanh Hoa/Ninh Thuan
    "Lâm Đồng": [11.9464, 108.4419],   # Merged Lam Dong/Dak Nong/Binh Thuan
    "TP Hồ Chí Minh": [10.8231, 106.6297], # Merged HCMC/BRVT/Binh Duong
    "Đồng Nai": [11.0000, 107.0000],    # Merged Dong Nai/Binh Phuoc
    "Long An": [10.5333, 106.4167],     # Merged Long An/Tay Ninh
    "An Giang": [10.3833, 105.4333],    # Merged An Giang/Kien Giang
    "Cần Thơ": [10.0333, 105.7833],     # Merged Can Tho/Hau Giang/Soc Trang
    "Tiền Giang": [10.4167, 106.3667],  # Merged Tien Giang/Ben Tre
    "Vĩnh Long": [10.2500, 105.9667],   # Merged Vinh Long/Dong Thap
    "Bạc Liêu": [9.2833, 105.7167],     # Merged Bac Lieu/Ca Mau
    "Trà Vinh": [9.9500, 106.3333]
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
    "Ven biển", "Hải đảo", "Biên giới",

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
    r"xoáy\s*thuận", r"vùng\s*xoáy", r"áp\s*cao\s*cận\s*nhiệt", r"rãnh\s*thấp", r"tổ\s*hợp\s*thời\s*tiết\s*xấu",
    r"bao\s*so\s*3", r"ap\s*thap\s*nhiet\s*doi", r"bản\s*tin\s*dự\s*báo\s*bão", r"cập\s*nhật\s*bão",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*:?\s*cấp\s*(?:1|2|3|4|5)",
    r"rủi\s*ro\s*thiên\s*tai\s*(?:cấp\s*độ\s*)?(?:1|2|3|4|5)",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
    r"bảng\s*2:\s*cấp\s*độ\s*rủi\s*ro.*áp\s*thấp\s*nhiệt\s*đới.*bão",
    r"bão\s*mạnh\s*cấp\s*(?:10|11)",
    r"bão\s*rất\s*mạnh\s*cấp\s*(?:12|13|14|15)",
    r"siêu\s*bão|bão\s*siêu\s*mạnh",
    r"áp\s*thấp\s*nhiệt\s*đới.*cấp\s*(?:6|7)",
    r"bão.*cấp\s*(?:8|9|10|11|12|13|14|15|16|17)",
    r"tin\s*áp\s*thấp\s*nhiệt\s*đới\s*gần\s*biển\s*đông",
    r"tin\s*áp\s*thấp\s*nhiệt\s*đới\s*trên\s*biển\s*đông",
    r"tin\s*áp\s*thấp\s*nhiệt\s*đới\s*khẩn\s*cấp",
    r"tin\s*áp\s*thấp\s*nhiệt\s*đới\s*trên\s*đất\s*liền",
    r"tin\s*cuối\s*cùng\s*về\s*áp\s*thấp\s*nhiệt\s*đới",
    r"tin\s*nhanh\s*về\s*áp\s*thấp\s*nhiệt\s*đới",
    r"tin\s*bão\s*gần\s*biển\s*đông",
    r"tin\s*bão\s*trên\s*biển\s*đông",
    r"tin\s*bão\s*khẩn\s*cấp",
    r"tin\s*bão\s*trên\s*đất\s*liền",
    r"tin\s*cuối\s*cùng\s*về\s*bão",
    r"tốc\s*độ\s*di\s*chuyển\s*:?\s*\d{1,3}\s*(?:km/?h|km/giờ)",
    r"di\s*chuyển\s*theo\s*hướng\s*(?:bắc|nam|đông|tây)(?:\s*(?:đông|tây))?",
    r"di\s*chuyển\s*theo\s*hướng\s*(?:bắc\s*đông\s*bắc|đông\s*bắc|đông\s*đông\s*bắc|đông\s*đông\s*nam|đông\s*nam|nam\s*đông\s*nam|nam\s*tây\s*nam|tây\s*nam|tây\s*tây\s*nam|tây\s*tây\s*bắc|tây\s*bắc|bắc\s*tây\s*bắc)",
    r"vĩ\s*(?:bắc|độ\s*vĩ\s*bắc)\s*\d{1,2}(?:[.,]\d+)?",
    r"kinh\s*(?:đông|độ\s*kinh\s*đông)\s*\d{1,3}(?:[.,]\d+)?",
    r"\d{1,2}(?:[.,]\d+)?\s*độ\s*vĩ\s*bắc",
    r"\d{1,3}(?:[.,]\d+)?\s*độ\s*kinh\s*đông",
    r"bán\s*kính\s*gió\s*mạnh",
    r"vùng\s*nguy\s*hiểm\s*(?:trong\s*)?(?:24|48|72)\s*giờ",
    r"vòng\s*tròn\s*xác\s*suất\s*70%\s*(?:tâm\s*)?(?:áp\s*thấp\s*nhiệt\s*đới|bão)?",
    r"bô[\s-]*pho|bo[\s-]*pho|beaufort",
    r"cấp\s*\d{1,2}\s*[-–]\s*\d{1,2}\s*,?\s*giật\s*cấp\s*\d{1,2}\s*[-–]\s*\d{1,2}",
    r"gió\s*(?:mạnh\s*)?cấp\s*\d{1,2}(?:\s*[-–]\s*\d{1,2})?",
    r"giật\s*cấp\s*\d{1,2}(?:\s*[-–]\s*\d{1,2})?",
    r"sức\s*gió\s*(?:mạnh\s*nhất\s*)?(?:vùng\s*gần\s*tâm\s*)?(?:cấp\s*)?\d{1,2}",
    r"tin\s*sóng\s*lớn\s*,?\s*nước\s*dâng\s*do\s*bão",
    r"nước\s*dâng\s*do\s*bão",
    r"sóng\s*(?:biển\s*)?cao\s*\d+(?:[.,]\d+)?\s*(?:m|mét)",
    r"biển\s*động\s*mạnh|biển\s*động",
    r"bão\s*[A-Za-z][A-Za-z0-9-]{2,}",
    r"cơn\s*bão\s*[A-Za-z][A-Za-z0-9-]{2,}",
    r"gió\s*(?:mạnh\s*)?cấp\s*\d+(?:\s*[–-]\s*\d+)?",
    r"gió\s*giật\s*(?:mạnh\s*)?cấp\s*\d+(?:\s*[–-]\s*\d+)?",
    r"bão\s*số\s*\d+"
  ]),


  # 2) Nước dâng, Triều cường (Storm Surge / Tidal Flood - Decision 18 Art 3.5)
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"nước\s*dâng\s*do\s*(?:bão|áp\s*thấp\s*nhiệt\s*đới|gió\s*mạnh)", 
    r"nước\s*biển\s*dâng", r"đỉnh\s*triều", r"ngập\s*do\s*triều", r"sóng\s*lớn\s*đánh\s*tràn",
    r"dâng\s*cao\s*bất\s*thường", r"ngập\s*ven\s*biển", r"tràn\s*qua\s*kè", r"sóng\s*tràn",
    r"kỳ\s*triều\s*cường", r"triều\s*cao", r"đỉnh\s*triều\s*kỷ\s*lục", r"vượt\s*báo\s*động\s*triều",
    r"độ\s*cao\s*nước\s*dâng",
    r"đỉnh\s*nước\s*dâng",
    r"nước\s*dâng\s*kết\s*hợp\s*(?:với\s*)?thủy\s*triều",
    r"mực\s*nước\s*tổng\s*cộng",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*(?:sóng\s*lớn\s*,?\s*)?nước\s*dâng",
    r"bản\s*tin\s*(?:dự\s*báo|cảnh\s*báo)\s*nước\s*dâng\s*do\s*bão",
    r"nước\s*dâng\s*do\s*gió\s*mạnh\s*trên\s*biển",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*gió\s*mạnh\s*trên\s*biển\s*,?\s*sóng\s*lớn\s*,?\s*nước\s*dâng",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*nước\s*dâng\s*:?\s*cấp\s*(?:1|2|3|4|5)",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*nước\s*dâng",
    r"mực\s*nước\s*tổng\s*cộng\s*(?:cao|lớn)\s*(?:từ|trên)\s*\d+(?:[.,]\d+)?\s*m",
    r"độ\s*cao\s*nước\s*dâng\s*(?:từ|trên)\s*\d+(?:[.,]\d+)?\s*m",
    r"tin\s*triều\s*cường",
    r"đợt\s*triều\s*cường",
    r"triều\s*cường\s*(?:cao|lớn)\s*(?:nhất|bất\s*thường)?",
    r"thủy\s*triều\s*dâng|thuỷ\s*triều\s*dâng",
    r"mực\s*nước\s*triều|mực\s*nước\s*thủy\s*triều|mực\s*nước\s*thuỷ\s*triều",
    r"mực\s*nước\s*đỉnh\s*triều|đỉnh\s*triều\s*(?:cao\s*nhất|lớn\s*nhất|kỷ\s*lục)?",
    r"(?:vượt|trên)\s*(?:mức\s*)?báo\s*động\s*(?:I|II|III|1|2|3)",
    r"\bBĐ\s*[1-3]\b",
    r"ngập\s*(?:lụt|úng)?\s*do\s*triều|ngập\s*do\s*triều\s*cường",
    r"ngập\s*ven\s*sông\s*do\s*triều|ngập\s*ven\s*biển\s*do\s*triều",
    r"storm\s*surge|tidal\s*surge|high\s*tide",
    r"trieu\s*cuong|nuoc\s*dang|nuoc\s*bien\s*dang",
    r"mực\s*nước(?:\s*triều)?\s*(?:đạt|lên|tới|trên|vượt)?\s*\d+(?:[.,]\d+)?\s*m",
    r"vượt\s*(?:mức\s*)?báo\s*động\s*(?:1|2|3|I|II|III)"
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
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"lượng\s*mưa", r"tổng\s*lượng\s*mưa",
    r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài", r"mưa\s*trên\s*\d+\s*mm", r"mưa\s*vượt\s*\d+\s*mm",
    r"mưa\s*kỷ\s*lục", r"mưa\s*như\s*trút", r"mưa\s*xối\s*xả", r"mưa\s*tầm\s*tã",
    r"lũ\s*trên\s*các\s*sông", r"lũ\s*hạ\s*lưu", r"lũ\s*thượng\s*nguồn", r"lũ\s*lên\s*nhanh",
    r"vỡ\s*đập", r"sự\s*cố\s*hồ\s*đập", r"xả\s*tràn", r"xả\s*khẩn\s*cấp",
    r"sạt\s*lở\s*kè", r"hố\s*sụt", r"nứt\s*nhà",
    r"tin\s*cảnh\s*báo\s*mưa\s*lớn",
    r"tin\s*dự\s*báo\s*mưa\s*lớn",
    r"tin\s*cảnh\s*báo\s*lũ(?!\s*quét)",          # tránh đè lên “lũ quét”
    r"tin\s*lũ(?:\s*khẩn\s*cấp)?",               # “Tin lũ”, “Tin lũ khẩn cấp”
    r"tin\s*cảnh\s*báo\s*ngập\s*lụt",
    r"tin\s*cảnh\s*báo\s*lũ\s*quét\s*,?\s*sạt\s*lở\s*đất(?:\s*,?\s*sụt\s*lún\s*đất)?",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*(?:mưa\s*lớn|lũ|ngập\s*lụt|lũ\s*quét|sạt\s*lở\s*đất|sụt\s*lún\s*đất)",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*(?:mưa\s*lớn|lũ|ngập\s*lụt|lũ\s*quét|sạt\s*lở\s*đất|sụt\s*lún\s*đất)",               # bắt “Cấp 2-3”, “Cấp 1”, ... (thường đi kèm dòng trên)
    r"mưa\s*(?:vừa|to|rất\s*to)(?:\s*đến\s*rất\s*to)?",
    r"mưa\s*đặc\s*biệt\s*lớn",
    r"mưa\s*lớn\s*diện\s*rộng",
    r"mưa\s*có\s*cường\s*độ\s*lớn",
    r"lượng\s*mưa\s*(?:tích\s*lũy|lũy\s*tích|phổ\s*biến)",
    r"tổng\s*lượng\s*mưa\s*(?:tích\s*lũy|lũy\s*tích)?",
    r"trong\s*(?:0?\d+)\s*-\s*(?:0?\d+)\s*giờ\s*tới",   # “03-06 giờ tới”
    r"trong\s*\d+\s*giờ\s*(?:qua|tới)",
    r"\b\d+(?:[.,]\d+)?\s*mm\s*/\s*\d+\s*h\b",          # “200mm/3h”, “60mm/3h”
    r">\s*\d+(?:[.,]\d+)?\s*mm\s*/\s*\d+\s*h",          # “(>200mm/3h)”
    r"đỉnh\s*lũ(?:\s*dự\s*kiến)?",
    r"lệnh\s*báo\s*động\s*lũ",
    r"(?:báo\s*động|BĐ)\s*(?:1|2|3|I|II|III)",
    r"(?:trên|dưới)\s*(?:báo\s*động|BĐ)\s*(?:1|2|3|I|II|III)",
    r"vượt\s*(?:báo\s*động|BĐ)\s*(?:1|2|3|I|II|III)",
    r"lũ\s*(?:lớn|rất\s*lớn|đặc\s*biệt\s*lớn|bất\s*thường)",
    r"lũ\s*(?:đang\s*)?(?:lên|rút|dao\s*động|biến\s*đổi\s*chậm)",
    r"lũ\s*khẩn\s*cấp", r"dòng\s*chảy", r"ngập\s*úng", r"úng\s*ngập", r"ngập\s*nước",
    r"vùng\s*trũng\s*,?\s*thấp", r"khu\s*đô\s*thị", r"khu\s*công\s*nghiệp",
    r"khu\s*tập\s*trung\s*dân\s*cư", r"độ\s*sâu\s*ngập", r"ngập\s*diện\s*rộng",
    r"nguy\s*cơ\s*(?:cao\s*)?(?:xảy\s*ra\s*)?lũ\s*quét", r"(?:sông|suối)\s*nhỏ",
    r"sườn\s*dốc", r"độ\s*ẩm\s*đất", r"bão\s*hòa", r"điểm\s*nghẽn\s*dòng", r"sạt\s*lở\s*đất\s*đá", r"lở\s*đất\s*đá", r"đá\s*lăn",
    r"sụt\s*lún\s*đất", r"lượng\s*mưa(?:\s*trong\s*\d+\s*(?:giờ|h|tiếng)|\s*24\s*giờ)?\s*(?:đạt|tới|trên|vượt)?\s*\d+\s*mm",
    r"\b\d+\s*mm(?:\/\s*24h|\/\s*24\s*giờ)?\b"
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
    r"lấy\s*nước\s*ngọt", r"vận\s*hành\s*cống\s*ngăn\s*mặn",
    r"tin\s*cảnh\s*báo\s*nắng\s*nóng", r"tin\s*dự\s*báo\s*nắng\s*nóng",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*hạn\s*hán",
    r"tin\s*cảnh\s*báo\s*xâm\s*nhập\s*mặn", r"tin\s*dự\s*báo\s*xâm\s*nhập\s*mặn",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*hạn\s*hán\s*và\s*sạt\s*lở\s*đất\s*,?\s*sụt\s*lún\s*đất",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*nắng\s*nóng",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*hạn\s*hán",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*xâm\s*nhập\s*mặn",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
    r"nhiệt\s*độ\s*cao\s*nhất", r"độ\s*ẩm\s*tương\s*đối\s*thấp\s*nhất",
    r"thời\s*gian\s*nắng\s*nóng\s*trong\s*ngày",
    r"tiếp\s*diễn\s*nắng\s*nóng", r"kết\s*thúc\s*nắng\s*nóng",
    r"nắng\s*nóng\s*diện\s*rộng", r"đợt\s*nắng\s*nóng",
    r"nhiệt\s*độ\s*cảm\s*nhận", r"chỉ\s*số\s*nhiệt", r"heat\s*index",
    r"(?:nhiệt\s*độ\s*cao\s*nhất|nắng\s*nóng)[^.\n]{0,40}\b\d{2}\s*°?\s*[cC]\b",
    r"(?:nhiệt\s*độ\s*cao\s*nhất|nắng\s*nóng)[^.\n]{0,40}\b\d{2}\s*(?:độ|do)\b",
    r"tổng\s*lượng\s*nước\s*mặt",
    r"thiếu\s*hụt\s*tổng\s*lượng\s*mưa", r"thiếu\s*hụt\s*tổng\s*lượng\s*nước\s*mặt",
    r"tỷ\s*lệ\s*phần\s*trăm\s*\(\s*%\s*\)\s*thiếu\s*hụt", r"thiếu\s*hụt\s*\d+\s*%",
    r"giá\s*trị\s*trung\s*bình\s*nhiều\s*năm", r"trung\s*bình\s*nhiều\s*năm", r"TBNN",
    r"cùng\s*thời\s*kỳ", r"năm\s*trước(?:\s*đó)?",
    r"cạn\s*kiệt\s*nguồn\s*nước", r"không\s*có\s*mưa", r"thiếu\s*nước\s*nghiêm\s*trọng",
    r"lưu\s*vực\s*sông", r"cửa\s*sông", r"nội\s*đồng", r"thủy\s*triều",
    r"ranh\s*giới\s*độ\s*mặn", r"ranh\s*mặn",
    r"(?:1|4)\s*‰", r"(?:1|4)\s*phần\s*nghìn", r"(?:1|4)\s*ppt",
    r"độ\s*mặn\s*(?:cao\s*nhất|max)", r"độ\s*mặn\s*1\s*‰", r"độ\s*mặn\s*4\s*‰",
    r"khoảng\s*cách\s*(?:chịu\s*ảnh\s*hưởng|xâm\s*nhập)", r"\b\d+\s*km\b",
    r"xâm\s*nhập\s*mặn\s*sâu", r"đỉnh\s*mặn", r"đợt\s*xâm\s*nhập\s*mặn",
    r"nang\s*nong", r"han\s*han", r"xam\s*nhap\s*man", r"do\s*man", r"ranh\s*man",
    r"han\s*man", r"dot\s*han\s*man", r"han\s*man\s*lich\s*su", 
    r"\b\d{2}(?:[–-]\d{2})?\s*(?:°c|độ\s*c|độ)\b", r"\b\d+(?:[.,]\d+)?\s*(?:‰|%o|g\/l)\b"
  ]),

  # 5) Gió mạnh trên biển, Sương mù (Wind & Fog - Decision 18 Art 3.4)
  ("wind_fog", [
    r"gió\s*mạnh\s*trên\s*biển", r"gió\s*giật\s*mạnh", r"sóng\s*cao\s*\d+\s*mét",
    r"biển\s*động\s*mạnh", r"cấm\s*biển", r"cấm\s*tàu\s*thuyền", r"sóng\s*to\s*vây\s*quanh",
    r"sương\s*mù\s*dày\s*đặc", r"mù\s*quang", r"tầm\s*nhìn\s*xa\s*dưới\s*1km",
    r"không\s*khí\s*lạnh\s*tăng\s*cường", r"gió\s*mùa\s*đông\s*bắc",
    r"gió\s*cấp\s*Beaufort", r"gió\s*giật\s*cấp\s*\d+",
    r"tầm\s*nhìn\s*xa\s*hạn\s*chế", r"biển\s*động\s*rất\s*mạnh",
    r"biển\s*động", r"biển\s*động\s*mạnh", r"biển\s*động\s*rất\s*mạnh",
    r"tin\s*cảnh\s*báo\s*gió\s*mạnh\s*trên\s*biển",
    r"tin\s*dự\s*báo\s*gió\s*mạnh\s*trên\s*biển",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*gió\s*mạnh\s*trên\s*biển\s*,?\s*sóng\s*lớn\s*,?\s*nước\s*dâng",
    r"tin\s*cảnh\s*báo\s*sương\s*mù",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*gió\s*mạnh\s*trên\s*biển",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*sương\s*mù",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
    r"gió\s*mạnh\s*trên\s*biển\s*là\s*gió\s*(?:với\s*tốc\s*độ\s*)?từ\s*cấp\s*6\s*trở\s*lên",
    r"gió\s*(?:mạnh\s*)?(?:từ\s*)?cấp\s*6\s*trở\s*lên",
    r"gió\s*(?:mạnh\s*)?cấp\s*\d+\s*(?:đến|[-–])\s*cấp\s*\d+",
    r"gió\s*(?:mạnh\s*)?cấp\s*\d+",
    r"giật\s*cấp\s*\d+\s*(?:đến|[-–])\s*cấp\s*\d+",
    r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*gió\s*bô[-\s]*pho", r"cấp\s*gió\s*Beaufort", r"thang\s*bô[-\s]*pho",
    r"sóng\s*lớn", r"độ\s*cao\s*sóng", r"độ\s*cao\s*nước\s*dâng",
    r"sóng\s*(?:cao|lớn)\s*(?:từ\s*)?2\s*m\s*trở\s*lên",
    r"sóng\s*cao\s*\d+(?:[.,]\d+)?\s*m",
    r"sóng\s*cao\s*\d+(?:[.,]\d+)?\s*(?:đến|[-–])\s*\d+(?:[.,]\d+)?\s*m",
    r"nước\s*dâng\s*do\s*gió\s*mạnh\s*trên\s*biển",
    r"nước\s*biển\s*dâng\s*do\s*gió\s*mạnh",
    r"tình\s*trạng\s*biển", r"biển\s*động\s*(?:mạnh|rất\s*mạnh)?",
    r"vùng\s*biển", r"vùng\s*biển\s*ven\s*bờ", r"ngoài\s*khơi", r"vùng\s*biển\s*xa",
    r"bắc\s*biển\s*đông", r"giữa\s*biển\s*đông", r"nam\s*biển\s*đông",
    r"vịnh\s*bắc\s*bộ", r"hoàng\s*sa", r"trường\s*sa",
    r"không\s*khí\s*lạnh\s*(?:tăng\s*cường|tràn\s*về)?",
    r"gió\s*mùa\s*đông\s*bắc\s*(?:mạnh|tăng\s*cường)?",
    r"gió\s*đông\s*bắc\s*(?:mạnh|tăng\s*cường)?",
    r"gió\s*tây\s*nam\s*(?:mạnh|tăng\s*cường)?",
    r"sương\s*mù", r"sương\s*mù\s*dày\s*đặc", r"sương\s*mù\s*dày",
    r"tầm\s*nhìn\s*ngang", r"tầm\s*nhìn\s*ngang\s*dưới\s*1\s*km",
    r"tầm\s*nhìn\s*(?:xa|ngang)\s*(?:giảm|hạn\s*chế|còn|dưới)\s*\d+(?:[.,]\d+)?\s*(?:m|km)",
    r"tầm\s*nhìn\s*xa\s*(?:từ\s*)?50\s*m\s*trở\s*lên",
    r"tầm\s*nhìn\s*xa\s*dưới\s*50\s*m",
    r"gây\s*nguy\s*hiểm\s*cho\s*các\s*phương\s*tiện\s*giao\s*thông",
    r"đường\s*cao\s*tốc", r"khu\s*vực\s*sân\s*bay",
    r"trên\s*biển", r"trên\s*sông", r"đường\s*đèo\s*núi",
    r"gio\s*manh\s*tren\s*bien", r"suong\s*mu", r"tam\s*nhin\s*(?:xa|ngang)",
    r"bien\s*dong", r"song\s*lon", r"nuoc\s*dang",
    r"tầm\s*nhìn(?:\s*xa)?\s*(?:dưới|giảm\s*còn|chỉ\s*còn)?\s*\d+(?:\s*[–-]\s*\d+)?\s*(?:m|km)",
    r"sóng\s*cao\s*(?:từ)?\s*\d+(?:[.,]\d+)?\s*(?:đến|[-–])\s*\d+(?:[.,]\d+)?\s*m"
  ]),
  # 6) Thời tiết cực đoan (Lốc, Sét, Mưa đá, Rét hại - Decision 18 Art 3.6)
  ("extreme_other", [
    r"dông\s*lốc", r"lốc\s*xoáy", r"vòi\s*rồng", r"tố\s*lốc", r"mưa\s*đá", r"mưa\s*đá\s*trắng\s*trời",
    r"sét\s*đánh", r"giông\s*sét", r"mưa\s*to\s*kèm\s*theo\s*dông\s*lốc",
    r"rét\s*đậm\s*rét\s*hại", r"rét\s*hại", r"băng\s*giá", r"sương\s*muối", r"nhiệt\s*độ\s*xuống\s*dưới\s*0",
    r"rét\s*buốt", r"băng\s*giá\s*phủ\s*trắng", r"không\s*khí\s*lạnh",
    r"mưa\s*tuyết", r"tuyết\s*rơi",
    r"tin\s*cảnh\s*báo\s*(?:dông\s*|giông\s*)?(?:lốc|sét|mưa\s*đá)",
    r"tin\s*dự\s*báo(?:,\s*)?\s*cảnh\s*báo\s*(?:rét\s*hại|sương\s*muối)",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*(?:lốc|sét|mưa\s*đá|rét\s*hại|sương\s*muối)",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",
    r"gió\s*lốc",
    r"giông\s*lốc|dông\s*lốc",
    r"lốc\s*xoáy\s*(?:cục\s*bộ|mạnh|dữ\s*dội)?",
    r"lốc\s*cuốn\s*(?:bay|tốc\s*mái|sập|đổ)",
    r"lốc\s*(?:tàn\s*phá|quật\s*đổ|thổi\s*bay)",
    r"vòi\s*rồng\s*(?:trên\s*biển|trên\s*sông|xuất\s*hiện)?",  # bạn đã có, thêm biến thể
    r"(?:tia\s*)?sét\s*(?:đánh|giáng|đánh\s*trúng|đánh\s*trúng\s*liên\s*tiếp)",
    r"bị\s*sét\s*đánh",
    r"sét\s*đánh\s*chết|tử\s*vong\s*do\s*sét",
    r"giông\s*sét|dông\s*sét",
    r"phóng\s*điện\s*(?:trong\s*đám\s*mây|giữa\s*các\s*đám\s*mây|mây\s*-\s*đất)",
    r"hạt\s*mưa\s*đá|cục\s*mưa\s*đá",
    r"mưa\s*đá\s*(?:kèm|cùng)\s*(?:mưa\s*rào|gió\s*mạnh|gió\s*giật)",
    r"mưa\s*đá\s*(?:to|rất\s*to|dày\s*đặc|trắng\s*trời)",
    r"mưa\s*đá\s*(?:đường\s*kính|kích\s*thước)\s*\d+(?:[.,]\d+)?\s*(?:cm|mm)",
    r"thiệt\s*hại\s*do\s*mưa\s*đá|mái\s*tôn\s*bị\s*thủng|vỡ\s*kính\s*do\s*mưa\s*đá",
    r"rét\s*hại\s*(?:diện\s*rộng|kéo\s*dài|tăng\s*cường|cường\s*độ\s*mạnh)?",
    r"đợt\s*rét\s*hại",
    r"sương\s*muối\s*(?:xuất\s*hiện|bao\s*phủ|phủ\s*trắng)?",
    r"băng\s*giá|đóng\s*băng|băng\s*phủ",      # hay đi kèm rét hại/sương muối trong tin tức
    r"nhiệt\s*độ\s*(?:giảm|xuống|hạ)\s*(?:dưới|còn)\s*\d+(?:[.,]\d+)?\s*°?\s*c",
    r"rét\s*đậm\s*(?:rét\s*hại)?",
    r"\bloc\b|\bset\b|\bmua\s*da\b|\bret\s*hai\b|\bsuong\s*muoi\b",
  ]),
  # 7) Cháy rừng (Wildfire - Decision 18 Art 3.7)
  ("wildfire", [
    r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"PCCCR", r"cháy\s*thực\s*bì", r"lửa\s*rừng", r"cháy\s*lan\s*rộng",
    r"quy\s*chế\s*phòng\s*cháy\s*chữa\s*cháy\s*rừng", r"trực\s*cháy\s*rừng",
    r"cấp\s*cháy\s*rừng\s*cấp\s*(?:IV|V|4|5)", r"nguy\s*cơ\s*cháy\s*rừng\s*rất\s*cao",
    r"cháy\s*rừng\s*(?:phòng\s*hộ|đặc\s*dụng|sản\s*xuất)", r"đốt\s*thực\s*bì", r"đốt\s*nương",
    r"đám\s*cháy\s*rừng", r"điểm\s*cháy\s*rừng", r"lửa\s*rừng",
    r"tin\s*(?:dự\s*báo|cảnh\s*báo)\s*cháy\s*rừng(?:\s*do\s*tự\s*nhiên)?",
    r"cảnh\s*báo\s*cháy\s*rừng(?:\s*do\s*tự\s*nhiên)?",
    r"cấp\s*cảnh\s*báo\s*cháy\s*rừng\s*(?:đạt\s*)?(?:cấp\s*)?(?:4|5|IV|V)",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*cháy\s*rừng(?:\s*do\s*tự\s*nhiên)?",
    r"cấp\s*dự\s*báo\s*cháy\s*rừng\s*(?:cấp\s*)?(?:I|II|III|IV|V|1|2|3|4|5)",
    r"cấp\s*cháy\s*rừng\s*(?:cấp\s*)?(?:I|II|III|IV|V|1|2|3|4|5)",
    r"bảng\s*tra\s*cấp\s*(?:dự\s*báo\s*)?cháy\s*rừng",
    r"phòng\s*cháy\s*(?:,?\s*chữa\s*cháy)?\s*rừng",
    r"chữa\s*cháy\s*rừng", r"PCCCR", r"PCCC\s*rừng", r"Ban\s*Chỉ\s*huy\s*PCCCR",
    r"kiểm\s*lâm", r"hạt\s*kiểm\s*lâm", r"chi\s*cục\s*kiểm\s*lâm",
    r"huy\s*động\s*lực\s*lượng\s*chữa\s*cháy\s*rừng",
    r"trực\s*phòng\s*cháy\s*(?:và\s*)?chữa\s*cháy\s*rừng",
    r"canh\s*phòng\s*(?:cháy\s*rừng|lửa\s*rừng)",
    r"biển\s*báo\s*hiệu\s*cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"biển\s*cấm\s*lửa",
    r"đường\s*băng\s*cản\s*lửa|đường\s*ranh\s*cản\s*lửa",
    r"chòi\s*quan\s*sát\s*phát\s*hiện\s*cháy\s*rừng|chòi\s*canh\s*lửa",
    r"tháp\s*quan\s*trắc\s*lửa\s*rừng",
    r"hệ\s*thống\s*(?:dự\s*báo|cảnh\s*báo)\s*cháy\s*rừng",
    r"sử\s*dụng\s*lửa\s*trong\s*(?:sản\s*xuất|sinh\s*hoạt|canh\s*tác)",
    r"đốt\s*(?:xử\s*lý\s*)?thực\s*bì",
    r"đốt\s*nương|đốt\s*rẫy",
    r"cấm\s*lửa|cấm\s*đốt",
    r"bùng\s*phát\s*cháy\s*rừng",
    r"lan\s*rộng|lan\s*nhanh",
    r"khoanh\s*vùng|khống\s*chế|dập\s*tắt",
    r"diện\s*tích\s*cháy|thiệt\s*hại\s*rừng",
    r"chay\s*rung",
    r"pcccr|pccc\s*rung",
    r"cap\s*(?:du\s*bao|canh\s*bao)\s*chay\s*rung",
  ]),
  # 8) Động đất, Sóng thần (Quake & Tsunami - Decision 18 Art 3.8-10)
  ("quake_tsunami", [
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn", r"sóng\s*thần", r"richter",
    r"tâm\s*chấn", r"chấn\s*tiêu", r"đất\s*rung\s*lắc", r"viện\s*vật\s*lý\s*địa\s*cầu",
    r"magnitude", r"rung\s*lắc\s*mạnh", r"thang\s*richter", r"cấp\s*báo\s*động\s*sóng\s*thần",
    r"\b(?:m|mw|ml)\s*[=:]?\s*\d+(?:[.,]\d+)?", r"độ\s*lớn\s*\d+(?:[.,]\d+)?", r"\d+(?:[.,]\d+)?\s*độ\s*richter",
    r"bản\s*tin\s*động\s*đất",
    r"tin\s*động\s*đất",
    r"báo\s*tin\s*động\s*đất",
    r"bản\s*tin\s*cảnh\s*báo\s*sóng\s*thần",
    r"tin\s*cảnh\s*báo\s*sóng\s*thần",
    r"tin\s*hủy\s*cảnh\s*báo\s*sóng\s*thần|tin\s*huỷ\s*cảnh\s*báo\s*sóng\s*thần",
    r"tin\s*cuối\s*cùng\s*về\s*sóng\s*thần",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*động\s*đất",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*do\s*sóng\s*thần",
    r"cảnh\s*báo\s*cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
    r"giờ\s*GMT",
    r"giờ\s*Hà\s*Nội|giờ\s*Việt\s*Nam",
    r"địa\s*điểm\s*xảy\s*ra\s*động\s*đất",
    r"tọa\s*độ\s*chấn\s*tâm|toạ\s*độ\s*chấn\s*tâm",
    r"chấn\s*tâm|tâm\s*chấn",
    r"độ\s*sâu\s*chấn\s*tiêu|chấn\s*tiêu",
    r"cường\s*độ\s*chấn\s*động",
    r"thang\s*MSK[-\s]*64|\bMSK[-\s]*64\b",
    r"hậu\s*quả\s*có\s*thể\s*xảy\s*ra\s*do\s*động\s*đất",
    r"độ\s*lớn\s*động\s*đất\s*\(M\)|độ\s*lớn\s*\(M\)",
    r"thang\s*độ\s*mô\s*men|độ\s*mô\s*men",
    r"(?:động\s*đất|magnitude|độ\s*lớn)[^.\n]{0,40}\b\d+(?:[.,]\d+)?\b",
    r"(?:động\s*đất|magnitude|độ\s*lớn)[^.\n]{0,40}\bM\s*[=:]?\s*\d+(?:[.,]\d+)?\b",
    r"tin\s*cảnh\s*báo\s*sóng\s*thần\s*mức\s*1",
    r"tin\s*cảnh\s*báo\s*sóng\s*thần\s*mức\s*2",
    r"tin\s*cảnh\s*báo\s*sóng\s*thần\s*mức\s*3",
    r"khả\s*năng\s*xảy\s*ra\s*sóng\s*thần",
    r"mức\s*độ\s*nguy\s*hiểm",
    r"khu\s*vực\s*có\s*thể\s*bị\s*ảnh\s*hưởng\s*trực\s*tiếp",
    r"độ\s*cao\s*sóng\s*thần|chiều\s*cao\s*sóng\s*thần",
    r"thời\s*gian\s*sẽ\s*ảnh\s*hưởng|thời\s*gian\s*ảnh\s*hưởng|thời\s*gian\s*đến",
    r"khuyến\s*cáo\s*sẵn\s*sàng\s*sơ\s*tán",
    r"sơ\s*tán\s*ngay\s*lập\s*tức",
    r"(?:vĩ\s*độ|lat(?:itude)?)\s*[=:]?\s*[-+]?\d+(?:[.,]\d+)?",
    r"(?:kinh\s*độ|lon(?:gitude)?)\s*[=:]?\s*[-+]?\d+(?:[.,]\d+)?",
    r"(?:độ\s*sâu|depth)[^.\n]{0,20}\b\d+(?:[.,]\d+)?\s*km\b",
    r"viện\s*vật\s*lý\s*địa\s*cầu",
    r"trung\s*tâm\s*báo\s*tin\s*động\s*đất\s*và\s*cảnh\s*báo\s*sóng\s*thần",
    r"dong\s*dat|rung\s*chan|du\s*chan|chan\s*tam|chan\s*tieu",
    r"song\s*than|tsunami|earthquake",
    
    # --- COMPLEX EXTRACTION PATTERNS (VERBOSE MODE) ---
    r"""
        \b (?: độ\s*lớn | magnitude ) \s*                        # Nhãn 'độ lớn'
        (?: \(? \s* (?: Mw | MW | ML | Ms | mb | Md | M ) \s* \)? )? \s* # Loại thang đo (tùy chọn)
        [=:]? \s*                                               # Ký tự phân cách
        (?P<num> \d+ (?: [.,]\d+ )? )                            # Con số (vắt cả 5.4 hoặc 5,4)
        \b
    """,
    r"""
        (?-i:                                                   # Tắt ignore-case cho cụm này
            \b M (?: w | W | L | l | s | b | d )? \s*            # Chữ M viết hoa đặc thù
            [=:]? \s* 
            (?P<num> \d+ (?: [.,]\d+ )? ) 
        ) \b
    """,
    r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?:độ\s*)?richter\b",
    r"\bthang\s*richter\s*[=:]?\s*(?P<num>\d+(?:[.,]\d+)?)\b",
    r"""
        \b (?: độ\s*sâu | sâu | độ\s*sâu\s*chấn\s*tiêu | chấn\s*tiêu | hypocenter\s*depth | depth ) \s* 
        (?: khoảng | tầm | ước\s*tính | xấp\s*xỉ | ~ )? \s*    # Ước lượng
        (?P<depth> \d+ (?: [.,]\d+ )? ) \s*                     # Độ sâu
        (?: km | ki\s*lô\s*mét ) \b
    """,
    r"""
        \b (?: tâm\s*chấn | tâm\s*động\s*đất | epicenter )      # Nhãn vị trí
        (?: [^.\n]{0,60} )? \b                                  # Ngữ cảnh ở giữa
        (?: cách | ở\s*cách ) \s*
        (?P<dist> \d+ (?: [.,]\d+ )? ) \s* km \b                # Khoảng cách
    """,
    r"""
        \b (?P<lat> \d+ (?: [.,]\d+ )? ) \s* °? \s* (?: N | B ) \s* # Vĩ độ (N hoặc B)
        (?P<lon> \d+ (?: [.,]\d+ )? ) \s* °? \s* (?: E | Đ ) \b     # Kinh độ (E hoặc Đ)
    """,
    r"""
        \b (?: tọa\s*độ | toạ\s*độ | tâm\s*chấn | epicenter ) 
        (?: [^0-9]{0,30} )?                                     # Ngữ cảnh
        (?P<lat> \d+ (?: [.,]\d+ )? ) \s* [,;/] \s*             # Lat
        (?P<lon> \d+ (?: [.,]\d+ )? ) \b                        # Lon
    """,
    r"\b(?:Mercalli|MMI|MSK)\s*(?:cấp|độ)?\s*(?P<intensity>[IVX]{1,8}|\d{1,2})\b",
    r"""
        \b (?: cường\s*độ | mức\s*độ ) \s*                      # Cường độ
        (?: rung\s*lắc | động\s*đất )? (?: [^.\n]{0,30} )? \b
        (?: theo\s* )? (?: thang\s* )? (?: Mercalli | MMI | MSK ) \b # Thang đo
        (?: [^A-Za-z0-9]{0,10} )? 
        (?P<intensity> [IVX]{1,8} | \d{1,2} ) \b               # Chỉ số
    """,
    r"\b(?:tiền\s*chấn|dư\s*chấn|aftershock|foreshock|mainshock)\b",
    r"""
        \b (?: sóng\s*thần | tsunami ) (?: [^0-9]{0,50} )?      # Sóng thần
        (?P<wave> 
            \d+ (?: [.,]\d+ )? 
            (?: \s* [–-] \s* \d+ (?: [.,]\d+ )? )?              # Khoảng chiều cao
        ) \s* (?: m | cm ) \b
    """,
    r"""
        \b (?: sóng\s*thần | tsunami ) (?: [^.\n]{0,100} )? \b
        (?: mực\s*nước\s*biển | mực\s*nước ) (?: [^0-9]{0,30} )?
        (?: dâng | tăng | giảm | biến\s*động ) (?: [^0-9]{0,10} )?
        (?P<delta> \d+ (?: [.,]\d+ )? ) \s* (?: m | cm ) \b
    """,
    r"\b(?:phát\s*(?:đi|tin)|ban\s*hành|ra)\s*(?:bản\s*tin|thông\s*báo)\s*(?:cảnh\s*báo\s*)?(?:sóng\s*thần|tsunami)\b",
  ])
]

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
  r"cuốn\s*trôi|vùi\s*lấp",
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
  r"\b(?:canh\s*bao|khuyen\s*cao|so\s*tan|di\s*doi|cuu\s*ho|cuu\s*nan|thiet\s*hai|thuong\s*vong|tu\s*vong|mat\s*tich|chia\s*cat|co\s*lap|mat\s*dien|mat\s*lien\s*lac)\b"
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
]

# 1. ABSOLUTE VETO: Strictly Non-Disaster Contexts (Metaphor, Showbiz, Game, Sport)
# These will be blocked even if they contain "bão", "lũ", "sạt lở" keywords.
ABSOLUTE_VETO = [
    r"cơn\s*bão\s*(?:chứng\s*khoán|chứng\s*trường|bán\s*tháo|lãi\s*suất|tỷ\s*giá|khủng\s*hoảng|suy\s*thoái|giá\s*cả)",
    r"bão\s*(?:bán\s*tháo|margin|call\s*margin|giải\s*chấp|chứng\s*khoán|coin|crypto|tỷ\s*giá|lãi\s*suất)",
    r"bão\s*(?:phốt|drama|diss|cà\s*khịa|scandal|tin\s*đồn|thị\s*phi)",
    r"cơn\s*lốc\s*(?:giá|tăng\s*giá|giảm\s*giá|khuyến\s*mãi|sale|flash\s*sale|voucher|đầu\s*tư)",
    r"bão\s*(?:tuyển\s*dụng|sa\s*thải|layoff|nghỉ\s*việc)",
    r"hạn\s*hán\s*(?:bàn\s*thắng|ghi\s*bàn|điểm\s*số|thành\s*tích|danh\s*hiệu)",
    r"khô\s*hạn\s*(?:bàn\s*thắng|ý\s*tưởng|nội\s*dung|tương\s*tác)",
    r"mưa\s*(?:like|view|comment|đơn|order|follow|subscriber)",
    r"mưa\s*(?:deal|voucher|ưu\s*đãi|quà\s*tặng|coupon)",
    r"ngập\s*deal", r"ngập\s*ưu\s*đãi", r"ngập\s*voucher",
    r"cháy\s*(?:vé|show|concert|liveshow|tour)",
    r"cháy\s*(?:hàng|kho|đơn|order|slot|suất)",
    r"cháy\s*(?:deadline|kpi|dự\s*án|task|việc)",
    r"cháy\s*(?:túi|tiền)",
    r"bốc\s*hơi\s*(?:tài\s*khoản|vốn\s*hóa|giá\s*trị|lợi\s*nhuận)",
    r"sóng\s*thần\s*(?:sa\s*thải|layoff|bán\s*tháo|giảm\s*giá)",
    r"làn\s*sóng\s*(?:đầu\s*tư|tẩy\s*chay|sa\s*thải|viral|trend)(?!\s*sóng\s*thần)",
    r"sóng\s*(?:wifi|wi-fi|4g|5g|3g|lte|di\s*động|điện\s*thoại|viễn\s*thông|radio)",
    r"mất\s*sóng\s*(?:wifi|wi-fi|4g|5g|3g|lte)",
    r"bắt\s*sóng", r"phủ\s*sóng", r"vùng\s*phủ\s*sóng", r"trạm\s*phát\s*sóng",
    r"tần\s*số", r"băng\s*tần",
    r"động\s*đất\s*(?:showbiz|giải\s*trí|mxh|thị\s*trường|chứng\s*khoán)",
    r"earthquake\s*(?:showbiz|entertainment|market)",
    r"cháy\s*(?:deadline|kpi|dự\s*án|task|việc)",
    r"cháy\s*(?:túi|tiền)",
    r"bốc\s*hơi\s*(?:tài\s*khoản|vốn\s*hóa|giá\s*trị|lợi\s*nhuận)",
    r"sóng\s*thần\s*(?:sa\s*thải|layoff|bán\s*tháo|giảm\s*giá)",
    r"làn\s*sóng\s*(?:đầu\s*tư|tẩy\s*chay|sa\s*thải|viral|trend)(?!\s*sóng\s*thần)",
    r"sóng\s*(?:wifi|wi-fi|4g|5g|3g|lte|di\s*động|điện\s*thoại|viễn\s*thông|radio)",
    r"mất\s*sóng\s*(?:wifi|wi-fi|4g|5g|3g|lte)",
    r"bắt\s*sóng", r"phủ\s*sóng", r"vùng\s*phủ\s*sóng", r"trạm\s*phát\s*sóng",
    r"tần\s*số", r"băng\s*tần",
    r"động\s*đất\s*(?:showbiz|giải\s*trí|mxh|thị\s*trường|chứng\s*khoán)",
    r"earthquake\s*(?:showbiz|entertainment|market)",
    r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng|tin\s*đồn|showbiz)(?!\w)",
    r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
    r"bão\s*sao\s*kê", r"bão\s*(?:chấn\s*thương|sa\s*thải|thất\s*nghiệp)(?!\w)",
    r"(?<!thiên\s)bão\s*lòng", r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm)",
    r"siêu\s*bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu|quà\s*tặng)",
    r"bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu)", r"cơn\s*bão\s*(?:chứng\s*khoán|giá|tỷ\s*giá|lãi\s*suất)",
    r"bão\s*view", r"bão\s*comment", r"bão\s*order", r"bão\s*đơn", r"bão\s*(?:margin|call\s*margin|giải\s*chấp)",
    r"bão\s*hàng", r"bão\s*flash\s*sale", r"bão\s*voucher", r"siêu\s*xe",
    r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ|điện\s*ảnh)",
    r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|MXH)",
    r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|V-pop|V-League|tình\s*trường)",
    r"cơn\s*lũ\s*(?:tin\s*giả|tội\s*phạm|rác\s*thải\s*số)",
    r"làn\s*sóng\s*(?:tẩy\s*chay|di\s*cư\s*số|công\s*nghệ)",
    r"bóng\s*đá", r"cầu\s*thủ", r"đội\s*tuyển", r"World\s*Cup", r"V-League", r"Sea\s*Games",
    r"AFF\s*Cup", r"huấn\s*luyện\s*viên", r"bàn\s*thắng", r"ghi\s*bàn", r"vô\s*địch",
    r"huy\s*chương", r"HCV", r"HCB", r"HCD",
    r"showbiz", r"hoa\s*hậu", r"người\s*mẫu", r"ca\s*sĩ", r"diễn\s*viên", r"liveshow",
    r"scandal", r"drama", r"sao\s*Việt", r"khánh\s*thành", r"khai\s*trương", r"kỷ\s*niệm\s*ngày",
    r"kỷ\s*niệm\s*\d+\s*năm", r"chương\s*trình\s*nghệ\s*thuật", r"đêm\s*nhạc", r"đêm\s*diễn",
    r"tiết\s*mục", r"hợp\s*xướng", r"giao\s*lưu\s*nghệ\s*thuật", r"(?:phát|truyền)\s*hình\s*trực\s*tiếp\s*chương\s*trình",
    r"tuần\s*lễ\s*thời\s*trang", r"triển\s*lãm\s*nghệ\s*thuật",
    r"giấy\s*chứng\s*nhận", r"sổ\s*đỏ", r"quyền\s*sử\s*dụng\s*đất", r"giao\s*đất", r"chuyển\s*nhượng",
    r"công\s*chức", r"viên\s*chức", r"biên\s*chế", r"thẩm\s*quyền", r"hành\s*chính",
    r"quốc\s*phòng\s*toàn\s*dân", r"an\s*ninh\s*quốc\s*phòng", r"quân\s*sự", r"binh\s*sĩ",
    r"vụ\s*án", r"tranh\s*chấp", r"khiếu\s*nại", r"tố\s*cáo", r"điều\s*tra\s*viên", r"bị\s*can",
    r"kháng\s*chiến", r"đại\s*biểu\s*quốc\s*hội", r"tổng\s*tuyển\s*cử", r"chính\s*trị",
    r"phân\s*công\s*công\s*tác", r"nhân\s*sự", r"bầu\s*cử", r"nhiệm\s*kỳ",
    r"đại\s*học", r"cao\s*đẳng", r"tuyển\s*sinh", r"học\s*bổng",
    r"tốt\s*nghiệp", r"thạc\s*sĩ", r"tiến\s*sĩ",
    r"ung\s*thư", r"tế\s*bào", r"tiểu\s*đường", r"huyết\s*áp", r"đột\s*quỵ",
    r"dinh\s*dưỡng", r"thực\s*phẩm", r"món\s*ăn", r"đặc\s*sản", r"giảm\s*cân", r"làm\s*đẹp",
    r"ngăn\s*ngừa\s*bệnh", r"sức\s*khỏe\s*sinh\s*sản",
    r"tra\s*từ", r"từ\s*điển", r"bài\s*hát", r"ca\s*khúc", r"MV", r"triệu\s*view", r"top\s*trending",
    r"văn\s*hóa", r"nghệ\s*thuật", r"triển\s*lãm", r"khai\s*mạc", r"lễ\s*hội",
    r"tình\s*yêu\s*lan\s*tỏa", r"đánh\s*thức\s*những\s*lãng\s*quên",
    r"bão\s*tố\s*cuộc\s*đời", r"sóng\s*gió\s*cuộc\s*đời", r"bão\s*tố\s*tình\s*yêu",
    r"bão\s*lòng", r"gây\s*bão\s*(?:dư\s*luận|mxh|mạng\s*xã\s*hội|cộng\s*đồng\s*mạng|truyền\s*thông)",
    r"(?:clip|video|bức\s*ảnh|phát\s*ngôn).*(?:gây\s*bão|gây\s*sóng\s*gió)",
    r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng|order)",
    r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam|sân\s*cỏ|chuyển\s*nhượng|giảm\s*giá)",
    r"sóng\s*gió\s*(?:cuộc\s*đời|hôn\s*nhân)",
    r"mưa\s*(?:đơn\s*hàng|order|follow|sub|subscriber|view|like|comment|tin\s*nhắn|notification)",
    r"lũ\s*(?:tin\s*nhắn|email|notification|comment|đơn\s*hàng|order)",
    r"ngập\s*(?:đơn|order|voucher|deal|ưu\s*đãi|hashtag|trend)",
    r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|tẩy\s*chay|sa\s*thải)",
    r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)",
    r"cơn\s*sốt\s*(?:đất|giá|vé)", r"storm\s+of\s+(?:criticism|controversy|comments|tweets)", r"flood\s+of\s+(?:orders|messages|emails|comments)",
    r"tsunami\s+of\s+(?:layoffs|sales|price\s+cuts)", r"không\s*khí\s*lạnh\s*(?:nhạt|lùng|giá)",
    r"flash\s*sale", r"deal\s*sốc", r"siêu\s*sale", r"mega\s*sale",
    r"live\s*stream\s*bán\s*hàng", r"shopping\s*online",
    r"(?:đi|về)\s*bão", r"ăn\s*mừng", r"cổ\s*vũ", r"xuống\s*đường",
    r"bóng\s*đá", r"U\d+", r"đội\s*tuyển", r"SEA\s*Games", r"AFF\s*Cup",
    r"vô\s*địch", r"huy\s*chương", r"bàn\s*thắng", r"ghi\s*bàn", r"HLV", r"sân\s*cỏ",
    r"tỉ\s*số", r"chung\s*kết", r"ngược\s*dòng",
    r"sốt\s*(?:MXH|mạng\s*xã\s*hội)", r"viral", r"trend", r"trending",
    r"livestream", r"streamer", r"youtuber", r"tiktoker", r"influencer",
    r"follow", r"subscriber", r"sub\s*kênh", r"idol", r"fandom",
    r"bitcoin", r"crypto", r"blockchain", r"NFT", r"token",
    r"ví\s*điện\s*tử", r"ví\s*crypto", r"sàn\s*coin", r"đào\s*coin",
    r"game", r"gaming", r"PUBG", r"Liên\s*Quân", r"esports",
    r"streamer\s*game", r"nạp\s*game", r"skin\s*game",
    r"hẹn\s*hò", r"tình\s*trường", r"chia\s*tay", r"tan\s*vỡ",
    r"yêu\s*đương", r"tình\s*yêu\s*sét\s*đánh",
    r"Netflix", r"phim\s*bộ", r"series", r"tập\s*cuối", r"ending",
    r"VinFast", r"xe\s*điện", r"iPhone", r"Samsung", r"ra\s*mắt\s*sản\s*phẩm",
    r"nhà\s*thông\s*minh", r"smart\s*home",
    r"combo\s*du\s*lịch", r"săn\s*vé\s*máy\s*bay",
    r"mỹ\s*phẩm", r"skincare", r"làm\s*đẹp\s*da", r"review\s*mỹ\s*phẩm",
    r"làn\s*sóng\s*(?:COVID|covid|dịch)\s*thứ",
    r"bão\s*COVID", r"bão\s*F0",
    r"nhặt\s*được", r"rơi\s*(?:ví|tiền|vàng)", r"trả\s*lại\s*(?:tiền|tài\s*sản)", r"giao\s*nộp.*công\s*an",
    r"thang\s*máy", r"mắc\s*kẹt.*thang\s*máy", r"móc\s*túi", r"trộm\s*cắp", r"cướp\s*giật",
    r"check-in", r"giáng\s*sinh", r"noel", r"nhà\s*thờ", r"phố\s*đi\s*bộ",
    r"biển\s*người", r"chen\s*chân", r"liveshow", r"scandal", r"drama",
    r"du\s*lịch", r"lễ\s*hội", r"văn\s*hóa", r"nghệ\s*thuật", r"trưng\s*bày", r"triển\s*lãm",
    r"làng\s*hoa", r"cây\s*kiểng", r"sinh\s*vật\s*cảnh", r"khai\s*hội", r"tour", r"lữ\s*hành",
    r"ẩm\s*thực", r"món\s*ngon", r"đặc\s*sản", r"nấu\s*ăn", r"đầu\s*bếp", r"nhà\s*hàng",
    r"thi\s*bơi", r"đua\s*thuyền.*(hội|lễ)", r"bơi\s*lội.*(thi|giải)",
    r"thông\s*xe", r"cao\s*tốc", r"ùn\s*ứ.*(?:lễ|tết|cuối\s*tuần)", r"bến\s*xe",
    r"xe\s*tải", r"xe\s*khách", r"va\s*chạm\s*xe",
    r"tông\s*chết", r"không\s*có\s*vùng\s*cấm",
    r"phạt\s*nguội", r"giấy\s*phép\s*lái\s*xe", r"đăng\s*kiểm",
    r"cơ\s*trưởng", r"phi\s*công",
    r"tiếp\s*xúc\s*cử\s*tri", r"bổ\s*nhiệm",
    r"ngoại\s*giao", r"hội\s*kiến", r"tiếp\s*kiến", r"đối\s*ngoại", r"quyết\s*sách",
    r"giảm\s*nghèo", r"xây\s*dựng\s*nông\s*thôn\s*mới", r"chỉ\s*số\s*giá\s*tiêu\s*dùng",
    r"bất\s*động\s*sản", r"giá\s*đất",
    r"lương\s*cơ\s*bản", r"tăng\s*lương", r"lương\s*hưu", r"nghỉ\s*hưu", r"lộ\s*trình\s*lương",
    r"hiến\s*máu", r"giọt\s*máu", r" runner", r"giải\s*chạy",
    r"hóa\s*đơn", r"đấu\s*giá",
    r"bạo\s*hành", r"đánh\s*đập", r"hành\s*hung", r"bắt\s*giữ", r"vụ\s*án", r"điều\s*tra",
    r"khởi\s*tố", r"truy\s*tố", r"xét\s*xử", r"bị\s*cáo", r"tử\s*hình", r"chung\s*thân",
    r"bắt\s*cóc", r"lừa\s*đảo", r"trục\s*lợi", r"giả\s*chết", r"karaoke", r"ma\s*túy", r"tội\s*phạm",
    r"lãnh\s*đạo\s*tỉnh", r"thanh\s*tra", r"kiến\s*nghị\s*xử\s*lý", r"sai\s*phạm",
    r"quân\s*đội.*biểu\s*diễn", r"tàu\s*ngầm", r"phi\s*đội", r"phi\s*trường", r"vé\s*máy\s*bay",
    r"CSGT", r"cảnh\s*sát\s*giao\s*thông", r"tổ\s*công\s*tác", r"quái\s*xế",
    r"kinh\s*tế\s*cửa\s*khẩu",
    r"AstroWind", r"Tailwind\s*CSS", r"\.docx\b", r"\.pdf\b", r"\.doc\b", r"hồ\s*bơi",
    r"xe\s*lu", r"xe\s*cẩu", r"xe\s*ủi", r"xe\s*ben", r"mất\s*thắng", r"mất\s*phanh",
    r"khai\s*thác\s*đá", r"hoàng\s*thành", r"di\s*tích", r"di\s*sản", r"trùng\s*tu",
    r"không\s*tiền\s*mặt", r"khoáng\s*sản", r"ăn\s*gian", r"bền\s*vững", r"đô\s*thị\s*bền\s*vững",
    r"ngoại\s*giao", r"hội\s*đàm", r"hợp\s*tác\s*quốc\s*tế",
    r"lao\s*động\s*giỏi", r"ăn\s*mừng",
    r"thâu\s*tóm", r"đất\s*vàng", r"thùng\s*rượu", r"phát\s*triển\s*đô\s*thị",
    r"câu\s*cá", r"câu\s*trúng",
    r"được\s*nhận\s*nuôi", r"nhận\s*nuôi", r"bỏ\s*rơi", r"trẻ\s*sơ\s*sinh", r"bé\s*sơ\s*sinh",
    r"tắm\s*sông", r"tắm\s*suối", r"tắm\s*biển", r"đi\s*bơi",
    r"lan\s*tỏa(?!\s*lâm\s*nguy)",
    r"lan\s*tỏa(?!\s*lâm\s*nguy)",
    r"xổ\s*số", r"vietlott", r"trúng\s*số", r"giải\s*đặc\s*biệt", r"vé\s*số",
    r"ngoại\s*tình", r"đánh\s*ghen", r"ly\s*hôn", r"ly\s*thân", r"tiểu\s*tam",
    r"tước\s*bằng\s*lái", r"tước\s*giấy\s*phép", r"phạt\s*nguội", r"đăng\s*kiểm",
    r"giảm\s*cân", r"tăng\s*cân", r"thực\s*phẩm\s*chức\s*năng", r"làm\s*đẹp", r"trắng\s*da",
    r"pháp\s*ban\s*bố", r"nhật\s*bản\s*ban\s*bố", r"trung\s*quốc\s*ban\s*bố",
    r"mưa\s*gạch\s*đá", r"mưa\s*lời\s*khen", r"mưa\s*feedback",
    r"bão\s*(?:rating|đánh\s*giá|review|hashtag|trend|viral)",
    r"cơn\s*bão\s*(?:hashtag|trend|viral|từ\s*khóa)",
    r"lũ\s*(?:comment|tin\s*nhắn|email|notification)",
    r"sóng\s*(?:trending|trend|viral)(?!\s*thần)",
    r"cháy\s*hết\s*mình", r"cháy\s*phố", r"cháy\s*team",
    r"cháy\s*máu", r"cháy\s*đam\s*mê", r"cháy\s*quá",
    r"sạt\s*lở\s*(?:niềm\s*tin|danh\s*tiếng|hình\s*ảnh|tài\s*chính)",
    r"ngập\s*tràn\s*(?:cảm\s*xúc|hạnh\s*phúc|tình\s*yêu|view|like|đơn\s*hàng|order|voucher|ưu\s*đãi|quà\s*tặng)",
    r"bão\s*(?:ddos|spam|bot|tấn\s*công\s*mạng|an\s*ninh\s*mạng)",
    r"(?:bão|mưa)\s*(?:email|tin\s*nhắn|notification)",
    r"sóng\s*(?:wifi|wi-?fi|4g|5g|lte|di\s*động|viễn\s*thông|radio)",
    r"mất\s*sóng\s*(?:wifi|wi-?fi|4g|5g|lte)",
    r"mại\s*dâm", r"mua\s*bán\s*dâm", r"gái\s*bán\s*dâm", r"khách\s*mua\s*dâm",
    r"chứa\s*chấp", r"môi\s*giới\s*mại\s*dâm", r"tú\s*bà", r"động\s*lắc",
    r"đánh\s*bạc", r"sát\s*phạt", r"sới\s*bạc", r"cá\s*độ",
    r"ma\s*túy", r"thuốc\s*lắc", r"pay\s*lak", r"bay\s*lắc",
    r"án\s*mạng", r"giết\s*người", r"cướp\s*giật", r"trộm\s*cắp", r"cát\s*tặc", r"khai\s*thác\s*cát",
    r"hung\s*thủ", r"nghi\s*phạm",
    r"truy\s*nã", r"đối\s*tượng\s*lừa\s*đảo", r"đối\s*tượng\s*ma\s*túy", r"đối\s*tượng\s*truy\s*nã",
    r"bắt\s*giữ", r"bị\s*can", r"xử\s*phạt", r"xét\s*xử", r"phiên\s*tòa",
    r"tử\s*hình", r"án\s*tù", r"tội\s*phạm",
    r"thiết\s*kế\s*nội\s*thất", r"trần\s*thạch\s*cao", r"la\s*phông", r"tấm\s*ốp",
    r"trang\s*trí\s*nhà", r"nhà\s*đẹp", r"căn\s*hộ\s*mẫu", r"chung\s*cư\s*cao\s*cấp", r"biệt\s*thự",
    # Administrative / Political Noise
    r"đại\s*hội\s*(?:đảng|công\s*đoàn|phụ\s*nữ|đoàn|thanh\s*niên|nhiệm\s*kỳ)",
    r"hội\s*nghị\s*ban\s*chấp\s*hành", r"thành\s*ủy", r"tỉnh\s*ủy", r"ubnd", r"hđnd",
    r"điều\s*động\s*cán\s*bộ", r"bổ\s*nhiệm", r"luân\s*chuyển", r"phân\s*công\s*lãnh\s*đạo",
    r"trao\s*huân\s*chương", r"cờ\s*thi\s*đua", r"vinh\s*danh", r"kỷ\s*niệm\s*ngày\s*thành\s*lập",
    r"nữ\s*sinh", r"nữ\s*giới", r"phụ\s*nữ", r"vẻ\s*đẹp", r"thanh\s*niên\s*tình\s*nguyện",
    r"nổ\s*pô", r"lạng\s*lách", r"đánh\s*võng", r"vây\s*ráp", r"bắt\s*giữ\s*đối\s*tượng",
    r"tết\s*nguyên\s*đán", r"thưởng\s*tết", r"nghỉ\s*tết", r"nghỉ\s*tết\s*dương\s*lịch",
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
  r"thủ\s*tục", r"trao\s*quyền", r"tai\s*nạn\s*giao\s*thông", r"tông\s*xe", r"đuối\s*nước",
  # Tech / Internet / AI (Moved from Absolute Veto)
  r"Google", r"Facebook", r"Youtube", r"TikTok", r"Zalo\s*Pay", r"tính\s*năng", r"cập\s*nhật",
  r"công\s*nghệ\s*số", r"dữ\s*liệu", r"\bAI\b", r"trí\s*tuệ\s*nhân\s*tạo",
   # Traffic Accidents (Distinguish from Disaster)
  r"tai\s*nạn\s*giao\s*thông", r"va\s*chạm\s*xe", r"tông\s*xe", r"tông\s*chết",
  r"xe\s*tải", r"xe\s*khách", r"xe\s*đầu\s*kéo", r"xe\s*container", r"xe\s*buýt",
  r"hướng\s*dẫn", r"bí\s*quyết", r"cách\s*xử\s*lý", r"quy\s*trình(?!\s*xả\s*lũ)", r"mẹo\s*hay",
  r"biện\s*pháp(?!\s*khẩn\s*cấp)", r"kỹ\s*năng(?!\s*cứu\s*hộ)", r"phòng\s*tránh",
  r"(?<!thiên\s)tai\s*nạn\s*liên\s*hoàn", r"vi\s*phạm\s*nồng\s*độ\s*cồn",

# Construction / Maintenance
  r"giàn\s*giáo", r"sập\s*giàn\s*giáo", r"tai\s*nạn\s*lao\s*động", r"an\s*toàn\s*lao\s*động",
  # Fire / Explosion (Urban/Industrial - Not Forest)
  r"lửa\s*ngùn\s*ngụt",
  r"bà\s*hỏa", r"chập\s*điện", r"nổ\s*bình\s*gas",
  r"cháy\s*nhà", r"nhà\s*bốc\s*cháy", r"hỏa\s*hoạn\s*nhà\s*dân",
  r"cháy.*quán", r"cháy.*xưởng", r"cháy.*xe",
    r"cháy\s*nhà", r"cháy\s*xưởng", r"cháy\s*quán", r"cháy\s*xe", r"chập\s*điện", r"nổ\s*bình\s*gas",
  r"bom\s*mìn", r"vật\s*liệu\s*nổ", r"thuốc\s*nổ", r"đạn\s*pháo", r"chiến\s*tranh", r"thời\s*chiến",

  # Pollution / Environment
  r"quan\s*trắc\s*môi\s*trường", r"rác\s*thải",
  r"chất\s*lượng\s*không\s*khí", r"(?<!\w)AQI(?!\w)", r"bụi\s*mịn", r"chỉ\s*số\s*không\s*khí",

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
  # Political / Diplomatic (Metaphorical)
  r"bão\s*(?:ngoại\s*giao|chính\s*trị)",
  r"rung\s*chấn\s*chính\s*trường",

  # Military Sports / Ceremonies (Distinguish from Rescue)
  r"liên\s*đoàn\s*võ\s*thuật", r"võ\s*thuật\s*quân\s*đội",
  r"đại\s*hội\s*nhiệm\s*kỳ", r"đại\s*hội\s*thể\s*dục\s*thể\s*thao",
  r"hội\s*thao", r"hội\s*thi\s*quân\s*sự", r"giải\s*đấu",
  r"vovinam", r"karate", r"taekwondo", r"võ\s*cổ\s*truyền", r"judo", r"sambo",

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

  r"(?:cháy|hỏa\s*hoạn|bốc\s*cháy|phát\s*hỏa)\s*(?:nhà|căn\s*hộ|chung\s*cư|phòng\s*trọ|quán|karaoke|bar|cửa\s*hàng|ki\s*ốt|xưởng|kho|trụ\s*sở|xe|ô\s*tô|xe\s*máy)",
  r"(?:nổ|phát\s*nổ)\s*(?:bình\s*gas|khí\s*gas|nồi\s*hơi|lò\s*hơi|trạm\s*biến\s*áp|máy\s*biến\s*áp|pin|ắc\s*quy)",
  r"(?:PCCC|cảnh\s*sát\s*PCCC|114|đội\s*chữa\s*cháy|lực\s*lượng\s*chữa\s*cháy|dập\s*tắt\s*đám\s*cháy)",
  r"(?:nguyên\s*nhân\s*ban\s*đầu|đang\s*điều\s*tra|khám\s*nghiệm\s*hiện\s*trường|khởi\s*tố\s*vụ\s*án)\s*(?:cháy|nổ)?",
  r"(?:tai\s*nạn|va\s*chạm|tông|đâm)\s*(?:giao\s*thông|liên\s*hoàn)?",
  r"(?:xe\s*máy|ô\s*tô|xe\s*khách|xe\s*tải|xe\s*container|xe\s*đầu\s*kéo|xe\s*buýt|tàu\s*hỏa|tàu\s*thủy|ca\s*nô|tàu\s*cá)\s*(?:lật|lao|tông|đâm|va\s*chạm)",
  r"(?:CSGT|công\s*an|đội\s*Cảnh\s*sát\s*giao\s*thông|khám\s*nghiệm|điều\s*tra)\s*(?:nguyên\s*nhân|vụ\s*việc)?",
  r"đuối\s*nước.*(?:tắm\s*sông|tắm\s*suối|tắm\s*biển|đi\s*bơi|hồ\s*bơi|bể\s*bơi)",
  r"(?:sập|đổ)\s*(?:giàn\s*giáo|cần\s*cẩu|công\s*trình|tường|trần|mái|nhà\s*xưởng)\s*(?:đang\s*thi\s*công|khi\s*thi\s*công)",
  r"tai\s*nạn\s*lao\s*động|an\s*toàn\s*lao\s*động",
  r"(?:rơi|ngã)\s*(?:từ\s*trên\s*cao|tầng\s*\d+|giàn\s*giáo|cần\s*cẩu)",
  r"(?:khởi\s*tố|bắt\s*giữ|tạm\s*giam|truy\s*tố|xét\s*xử|phiên\s*tòa|bản\s*án|tử\s*hình|chung\s*thân)",
  r"(?:án\s*mạng|giết\s*người|cướp|trộm|lừa\s*đảo|ma\s*túy|đánh\s*bạc|mại\s*dâm)",
  r"(?:VN-Index|chứng\s*khoán|cổ\s*phiếu|trái\s*phiếu|lãi\s*suất|tỉ\s*giá|ngân\s*hàng|tín\s*dụng|GDP|tăng\s*trưởng\s*kinh\s*tế)",
  r"(?:giá\s*(?:vàng|xăng|dầu|đô\s*la|usd)|thị\s*trường\s*(?:vàng|chứng\s*khoán|bất\s*động\s*sản))",
   r"(?:cách|hướng\s*dẫn|thủ\s*thuật|mẹo).*(?:tách|gộp|nén|chuyển|sửa).*(?:file|tệp|PDF|Word|Excel|ảnh|video)",
  r"how\s*to.*(?:tutorial|template|branding|customize)",
  r"(?:Google|Facebook|Youtube|TikTok|Zalo\s*Pay).*(?:cập\s*nhật|tính\s*năng|ra\s*mắt|lỗi|hướng\s*dẫn)",
  r"(?:hoa\s*hậu|showbiz|scandal|drama|MV|album|Netflix|series|tập\s*cuối)",
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
  # === A) Politics/Admin ceremony templates (non-disaster by default) ===
  r"(?:kỳ\s*họp|phiên\s*họp|hội\s*nghị|đại\s*hội)\s*(?:đảng|đảng\s*bộ|hđnd|quốc\s*hội|chi\s*bộ|cử\s*tri|toàn\s*quốc|tổng\s*kết|sơ\s*kết)",
  r"tiếp\s*xúc\s*cử\s*tri|chất\s*vấn|giải\s*trình|bầu\s*cử|ứng\s*cử",
  r"bổ\s*nhiệm|miễn\s*nhiệm|điều\s*động|luân\s*chuyển|kỷ\s*luật|kiểm\s*tra|giám\s*sát",
  r"nghị\s*quyết|nghị\s*định|thông\s*tư|quyết\s*định|chỉ\s*thị(?!.*(?:ứng\s*phó|phòng\s*chống\s*thiên\s*tai|pccc|cứu\s*hộ|cứu\s*nạn))",

  # === B) “Daily bulletin / digest” formats ===
  r"bản\s*tin\s*(?:cuối\s*ngày|sáng|trưa|tối)|điểm\s*tin|tin\s*trong\s*nước|tin\s*quốc\s*tế",

  # === C) Tech/business press releases (non-disaster by default) ===
  r"(?:ra\s*mắt|giới\s*thiệu)\s*(?:sản\s*phẩm|tính\s*năng|ứng\s*dụng|nền\s*tảng)",
  r"startup|gọi\s*vốn|vòng\s*gọi\s*vốn|mở\s*rộng\s*thị\s*trường",

  # === D) Awards/culture/commemoration ===
  r"giải\s*thưởng|vinh\s*danh|trao\s*tặng|kỷ\s*niệm|lễ\s*kỷ\s*niệm|văn\s*hóa\s*văn\s*nghệ|biểu\s*diễn|đêm\s*nhạc",
  # === E) Construction ceremony (soft negative unless it’s disaster-prevention infrastructure) ===
  r"khởi\s*công|khánh\s*thành|nghiệm\s*thu(?!.*(?:kè|đê|hồ\s*chứa|cống|thoát\s*nước|chống\s*ngập|chống\s*sạt\s*lở|phòng\s*chống\s*thiên\s*tai|giảm\s*ngập))",

  # === F) Urban fire/traffic – only “soft” because can be caused by storm/flood ===
  r"tai\s*nạn\s*giao\s*thông|xe\s*container|xe\s*khách|xe\s*tải|lật\s*xe|va\s*chạm",
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng)|cháy\s*(?:nhà|xưởng|quán|xe)(?!.*cháy\s*rừng)",

  # === G) Missing persons (soft flag only if NOT clearly disaster-related) ===
  r"mất\s*tích(?!.*(?:mưa\s*lũ|lũ|bão|nước\s*cuốn|sạt\s*lở|lũ\s*quét|tìm\s*kiếm\s*cứu\s*nạn))",
  r"(?:thanh\s*niên|nữ\s*sinh|học\s*sinh)\s*mất\s*tích(?!.*(?:mưa\s*lũ|lũ|bão|nước\s*cuốn))",
]

# Combined Negative List for backward compatibility (used in NO_ACCENT generation)
DISASTER_NEGATIVE = ABSOLUTE_VETO + CONDITIONAL_VETO + SOFT_NEGATIVE

# Removed old compiled patterns
POLLUTION_TERMS = [
    # Tổng quát
    r"ô\s*nhiễm(?:\s+môi\s*trường|\s+không\s*khí|\s+nguồn\s*nước|\s+nước|\s+đất)?",
    r"ô\s*nhiễm\s+môi\s*trường",
    r"môi\s*trường\s*bị\s*ô\s*nhiễm",

    # Không khí / bụi / AQI
    r"(?:chỉ\s*số\s*)?AQI",
    r"(?:air\s*quality\s*index)",
    r"chất\s*lượng\s*không\s*khí",
    r"PM\s*2\.5|PM2\.5",
    r"PM\s*10|PM10",
    r"bụi\s*mịn",
    r"bụi\s*lơ\s*lửng",
    r"\bTSP\b",
    r"\bSO2\b|\bNO2\b|\bCO\b|\bO3\b|\bH2S\b|\bNH3\b",
    r"khói\s*mù|mù\s*khói|smog",
    r"sương\s*mù\s*quang\s*hóa",

    # Liên quan thiên tai: cháy rừng/nóng hạn → khói/tro/bụi
    r"khói\s*cháy\s*rừng|cháy\s*rừng.*khói|khói.*cháy\s*rừng",
    r"tro\s*bụi|bụi\s*tro|mưa\s*tro",

    # Nước/đất: lũ/ngập/sạt lở → ô nhiễm nguồn nước, nước thải
    r"ô\s*nhiễm\s*nước|ô\s*nhiễm\s*nguồn\s*nước",
    r"nguồn\s*nước\s*bị\s*ô\s*nhiễm",
    r"nước\s*bẩn|nước\s*đen|nước\s*đục|bốc\s*mùi",
    r"nước\s*thải|xả\s*thải|thải\s*trực\s*tiếp",
    r"rác\s*thải|rác\s*tràn\s*lan|bãi\s*rác.*tràn",

    # Sự cố môi trường do thiên tai: tràn dầu / hóa chất / khí độc
    r"tràn\s*dầu|dầu\s*loang|vệt\s*dầu|loang\s*dầu",
    r"rò\s*rỉ\s*hóa\s*chất|rò\s*rỉ|rò\s*khí|xì\s*khí",
    r"khí\s*độc|hơi\s*độc",
    r"hóa\s*chất\s*độc|chất\s*độc|độc\s*hại",

    # Hậu quả sinh thái thường được báo chí dùng
    r"cá\s*chết\s*hàng\s*loạt|thủy\s*sản\s*chết",
    r"tảo\s*nở\s*hoa|phú\s*dưỡng",
    r"kim\s*loại\s*nặng|thủy\s*ngân|asen|cadmi(?:um)?|chì",
]

# Pre-compute unaccented patterns for matching against t0 (canonical text)
DISASTER_RULES_NO_ACCENT = []
for label, pats in DISASTER_RULES:
    nops = [risk_lookup.strip_accents(p) for p in pats]
    DISASTER_RULES_NO_ACCENT.append((label, nops))

DISASTER_CONTEXT_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_NEGATIVE]

# === OPTIMIZATION: PRE-COMPILE REGEX ===
RE_FLAGS = re.IGNORECASE | re.VERBOSE

def v_safe(p: str) -> str:
    """
    Đảm bảo Regex an toàn khi dùng re.VERBOSE.
    Nếu mẫu là chuỗi đơn dòng, ta đổi khoảng trắng thành \\s+ để không bị nuốt mất.
    Nếu mẫu là chuỗi nhiều dòng (đã format), ta giữ nguyên.
    """
    if "\n" in p: return p
    return p.replace(" ", r"\s+")

# Pre-compute accented and unaccented patterns for high-performance matching
DISASTER_RULES_RE = []
for label, pats in DISASTER_RULES:
    # 1. Accented/Strict channel
    pats_v = [v_safe(p) for p in pats]
    compiled_acc = [re.compile(p, RE_FLAGS) for p in pats_v]
    try:
        mega_acc = re.compile("|".join(f"(?:{p})" for p in pats_v), RE_FLAGS)
        compiled_acc = [mega_acc]
    except: pass

    # 2. Unaccented channel
    safe_pats = [p for p in pats if safe_no_accent(p) and len(p) > 15]
    compiled_no = []
    if safe_pats:
        safe_pats_v = [v_safe(risk_lookup.strip_accents(p)) for p in safe_pats]
        try:
            mega_no = re.compile("|".join(f"(?:{p})" for p in safe_pats_v), RE_FLAGS)
            compiled_no = [mega_no]
        except:
            compiled_no = [re.compile(p, RE_FLAGS) for p in safe_pats_v]

    DISASTER_RULES_RE.append((label, compiled_acc, compiled_no))

def build_two_channel_re(pats: List[str]):
    """
    Build accented and safe-unaccented regex lists.
    The unaccented list stores (original_index, compiled_re) for safe patterns.
    """
    re_acc = [re.compile(v_safe(p), RE_FLAGS) for p in pats]
    re_no = [(i, re.compile(v_safe(risk_lookup.strip_accents(p)), RE_FLAGS)) 
             for i, p in enumerate(pats) if safe_no_accent(p)]
    return re_acc, re_no

ABSOLUTE_VETO_RE, ABSOLUTE_VETO_NO_RE = build_two_channel_re(ABSOLUTE_VETO)
CONDITIONAL_VETO_RE, CONDITIONAL_VETO_NO_RE = build_two_channel_re(CONDITIONAL_VETO)
SOFT_NEGATIVE_RE, SOFT_NEGATIVE_NO_RE = build_two_channel_re(SOFT_NEGATIVE)
DISASTER_CONTEXT_RE, DISASTER_CONTEXT_NO_RE = build_two_channel_re(DISASTER_CONTEXT)

POLLUTION_TERMS_RE = [re.compile(v_safe(p), RE_FLAGS) for p in POLLUTION_TERMS]

# MEGA-REGEX for Source Keywords (Two-Channel Optimized)
AMBIGUOUS_KEYWORDS = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
CLEAN_SOURCE_KEYWORDS = [kw.lower() for kw in SOURCE_DISASTER_KEYWORDS if kw.lower() not in AMBIGUOUS_KEYWORDS]

# Channel 1: Accented (All keywords)
CLEAN_SOURCE_KEYWORDS.sort(key=len, reverse=True)
SOURCE_KEYWORDS_ACC_RE = re.compile("|".join(re.escape(k) for k in CLEAN_SOURCE_KEYWORDS), RE_FLAGS)

# Channel 2: Unaccented (Only very safe/long keywords)
SAFE_SOURCE_KEYWORDS = [k for k in CLEAN_SOURCE_KEYWORDS if safe_no_accent(k) and len(k) > 15]
SAFE_SOURCE_KEYWORDS.sort(key=len, reverse=True)
SOURCE_KEYWORDS_NO_RE = None
if SAFE_SOURCE_KEYWORDS:
    SOURCE_KEYWORDS_NO_RE = re.compile("|".join(re.escape(risk_lookup.strip_accents(k)) for k in SAFE_SOURCE_KEYWORDS), RE_FLAGS)

# Sensitive Locations compiled list (Accented)
SENSITIVE_LOCATIONS_RE = sources.SENSITIVE_LOCATIONS_RE

# Two-Channel: Unaccented (Only for reasonably unique/long names)
SENSITIVE_LOCATIONS_NO_RE = []
for i, loc in enumerate(sources.SENSITIVE_LOCATIONS):
    if safe_no_accent(loc) or len(loc) >= 10:
        stripped = risk_lookup.strip_accents(loc)
        p_re = re.compile(v_safe(rf"(?<!\w){re.escape(stripped)}(?!\w)"), RE_FLAGS)
        SENSITIVE_LOCATIONS_NO_RE.append((i, p_re))

# Weight configuration (Externalize? No, keep here for simplicity)
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
                p_acc = re.compile(v_safe(r_str), RE_FLAGS)
                patterns_acc[impact_type].append(p_acc)

                # Unaccented version (if safe)
                if safe_no_accent(r_str):
                    r_no = risk_lookup.strip_accents(r_str)
                    patterns_no[impact_type].append(re.compile(v_safe(r_no), RE_FLAGS))
            except re.error as e:
                print(f"Error compiling regex for {impact_type}: {r_str} -> {e}")

    return patterns_acc, patterns_no

IMPACT_PATTERNS, IMPACT_PATTERNS_NO = _build_impact_patterns()
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
)\b
""", re.IGNORECASE | re.VERBOSE)

WEIGHT_RULE = 4.0
WEIGHT_IMPACT = 3.0
WEIGHT_AGENCY = 1.5
WEIGHT_SOURCE = 0.5
WEIGHT_PROVINCE = 2.5


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

# Helper functions removed (using risk_lookup)

# CORE LOGIC

def extract_provinces(text: str, title: str = "", impact_spans: List[tuple] = None) -> List[dict]:
    """
    EXTRACT FOCUS PROVINCES (Heuristic Logic)
    1. If impacts exist, prioritize provinces in ±1 sentence window.
    2. If broadcast/forecast, prioritize title locations or high frequency.
    """
    if not text: return []

    # Unicode Normalization
    t_orig = unicodedata.normalize('NFC', text)
    t_title_orig = unicodedata.normalize('NFC', title)
    t, t0 = risk_lookup.canon(t_orig)

    # 1. Raw Extraction
    raw_hits = []
    for item in PROVINCE_REGEXES:
        found_iter = list(item["re_acc"].finditer(t))
        if not found_iter:
            found_iter = list(item["re_no"].finditer(t0))
        for m in found_iter:
            # Case-sensitive check for Proper Noun
            original_segment = t_orig[m.start():m.end()]
            is_proper = original_segment[0].isupper() if original_segment else False
            raw_hits.append({
                "name": item["name"],
                "type": item["type"],
                "span": m.span(),
                "is_proper": is_proper
            })

    if not raw_hits: return []

    # 2. Heuristic: Sentence Splitting
    # Split text into sentences and map spans to sentence index
    sentences = re.split(r'(?<=[.?!;])\s+', t_orig)
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
    title_locations = []
    if t_title_orig:
        t_tit, t_tit0 = risk_lookup.canon(t_title_orig)
        for item in PROVINCE_REGEXES:
             if item["re_acc"].search(t_tit) or item["re_no"].search(t_tit0):
                 title_locations.append(item["name"])

    # If we found focus provinces via impact, or we have title locations
    if focus_provinces or title_locations:
        # Combine impact focus + title locations
        final_names = set(title_locations)
        final_names.update([p["name"] for p in focus_provinces])
        # Return unique filtered list
        return [h for h in raw_hits if h["name"] in final_names]

    # H3: Frequency (Top-3) - Fallback for Forecasts
    freq = {}
    for h in raw_hits:
        freq[h["name"]] = freq.get(h["name"], 0) + (2 if h["is_proper"] else 1)

    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    top_3 = [name for name, count in sorted_freq[:3]]

    return [h for h in raw_hits if h["name"] in top_3]

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

def compute_disaster_signals(text: str, title: str = "", trusted_source: bool = False) -> dict:
    # 1. Standardize Normalization using risk_lookup.canon (Provides Two Channels)
    # Combine title for search if not already in text
    search_text = f"{title}\n{text}" if title and title not in text else text
    t_acc, t_no = risk_lookup.canon(search_text or "")

    rule_matches = []
    hazard_counts = {}
    # Check Rules using Two-Channel Strategy
    title_rule_match = False
    t_title_acc, t_title_no = risk_lookup.canon(title or "")

    for i, (label, compiled_acc, compiled_no) in enumerate(DISASTER_RULES_RE):
        count = 0
        matched_label = False
        # 1.1 Match Accented on t_acc (Always safe)
        for pat_re in compiled_acc:
            if pat_re.search(t_acc):
                count += 1
                matched_label = True
                if title and pat_re.search(t_title_acc):
                    title_rule_match = True

        # 1.2 Match Unaccented on t_no (Only for pre-filtered safe patterns)
        if not matched_label and compiled_no:
            for pat_re in compiled_no:
                if pat_re.search(t_no):
                    count += 1
                    matched_label = True
                    if title and pat_re.search(t_title_no):
                        title_rule_match = True

        if matched_label:
            rule_matches.append(label)
            hazard_counts[label] = count

    # 1. Hazard (Rule) Match - Category identification
    hazard_found = len(rule_matches) > 0
    rule_score = WEIGHT_RULE if hazard_found else 0.0
    
    # [OPTIMIZATION] Title Boost: If hazard keyword in title, add bonus
    if title_rule_match:
        rule_score += 1.5

    # 2. Impact Match - Deaths, missing, or significant damage/metrics
    # REFINED: Use extracted objects to determine impact_score
    raw_details = extract_impact_details(text)

    # We define impact_found if any typed list in raw_details is non-empty
    impact_found = any(len(lst) > 0 for lst in raw_details.values())

    metrics = extract_disaster_metrics(text)
    real_metrics_found = any(k != "duration_days" for k in metrics.keys())

    # Impact score is fixed if ANY major impact sign is found after negation-filtering
    impact_score = WEIGHT_IMPACT if (impact_found or real_metrics_found) else 0.0

    # [OPTIMIZATION] Magnitude Scaling: Bonus for extreme values
    extreme_bonus = 0.0
    if metrics.get("rainfall_mm", 0) >= 300: extreme_bonus += 1.5
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

    prov_hits = extract_provinces(text, title=title, impact_spans=all_impact_spans)

    # Location Score: 2.0 base + 0.5 bonus if it's a Proper Noun (Uppercase)
    location_found = len(prov_hits) > 0
    sensitive_hits = [sources.SENSITIVE_LOCATIONS[i] for i, pat_re in enumerate(SENSITIVE_LOCATIONS_RE) if pat_re.search(t_acc)]
    
    # Matching unaccented sensitive locations (Two-Channel)
    if SENSITIVE_LOCATIONS_NO_RE:
        matched_indices = {i for i, _ in enumerate(SENSITIVE_LOCATIONS_RE) if any(h for h in sensitive_hits if h == sources.SENSITIVE_LOCATIONS[i])}
        for orig_idx, pat_re in SENSITIVE_LOCATIONS_NO_RE:
            if orig_idx not in matched_indices:
                if pat_re.search(t_no):
                    sensitive_hits.append(sources.SENSITIVE_LOCATIONS[orig_idx])
                    matched_indices.add(orig_idx)

    location_found = location_found or len(sensitive_hits) > 0

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
    if SOURCE_KEYWORDS_NO_RE:
        non_ambiguous_hits.update(SOURCE_KEYWORDS_NO_RE.findall(t_no))

    source_score = min(4.0, float(len(non_ambiguous_hits)) * WEIGHT_SOURCE)

    # [OPTIMIZATION] Trusted Source Boost: Absolute points for official papers
    trusted_bonus = 1.5 if trusted_source else 0.0

    # UNIFIED CONFIDENCE SCORE
    score = rule_score + impact_score + agency_score + source_score + province_score + trusted_bonus
    # Context Matches (Optimized)
    context_hits = []
    # Use DISASTER_CONTEXT_RE
    for i, pat_re in enumerate(DISASTER_CONTEXT_RE):
        if pat_re.search(t_acc):
            context_hits.append(DISASTER_CONTEXT[i])

    # Unaccented Check for Context (Safe patterns only) - Separate loop for clarity
    already_matched = set(context_hits)
    for orig_idx, pat_re in DISASTER_CONTEXT_NO_RE:
        name = DISASTER_CONTEXT[orig_idx]
        if name not in already_matched:
            if pat_re.search(t_no):
                context_hits.append(name)
                already_matched.add(name)

    # Pollution Terms (Optimized)
    for pat_re in POLLUTION_TERMS_RE:
        if pat_re.search(t_acc): context_hits.append("pollution_term") # Just marker

    # Sensitive Locations Check (Metadata)
    sensitive_found = []
    # Collect all findings (already combined in sensitive_hits above)
    for loc_name in sensitive_hits:
        sensitive_found.append(loc_name)
        context_hits.append(f"sensitive_loc:{loc_name}")

    context_score = len(context_hits)

    # NEGATIVE CHECKS (Split & Optimized)
    # 1. Absolute Veto
    absolute_veto = False
    negative_matches = []
    # Channel 1: Accented
    for pat_re in ABSOLUTE_VETO_RE:
        if pat_re.search(t_acc):
            absolute_veto = True
            negative_matches.append(pat_re.pattern)
            break
    # Channel 2: Unaccented (Safe patterns only)
    if not absolute_veto:
        for _, pat_re in ABSOLUTE_VETO_NO_RE:
            if pat_re.search(t_no):
                absolute_veto = True
                negative_matches.append(pat_re.pattern)
                break

    # 2. Conditional Veto
    conditional_veto = False
    if not absolute_veto:
        for pat_re in CONDITIONAL_VETO_RE:
             if pat_re.search(t_acc):
                 conditional_veto = True
                 negative_matches.append(pat_re.pattern)
                 break
        if not conditional_veto:
            for _, pat_re in CONDITIONAL_VETO_NO_RE:
                if pat_re.search(t_no):
                    conditional_veto = True
                    negative_matches.append(pat_re.pattern)
                    break

    # Soft Negative (Optimized)
    soft_negative = False
    if not absolute_veto and not conditional_veto:
        for pat_re in SOFT_NEGATIVE_RE:
            if pat_re.search(t_acc):
                soft_negative = True
                negative_matches.append(pat_re.pattern)
                break
        if not soft_negative:
            for _, pat_re in SOFT_NEGATIVE_NO_RE:
                if pat_re.search(t_no):
                    soft_negative = True
                    negative_matches.append(pat_re.pattern)
                    break

    metrics = extract_disaster_metrics(text)
    impact_details = extract_impact_details(text)

    # Determine event stage
    event_stage = determine_event_stage(text)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_found,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": rule_score,
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
        "is_sensitive_location": len(sensitive_found) > 0,
        "stage": event_stage # Add the detected stage
    }

def determine_event_stage(text: str) -> str:
    """
    Classify event stage: FORECAST, INCIDENT, or RECOVERY.
    Uses keyword density/scoring for robustness.
    """
    t_lower = (text or "").lower()
    scores = {"FORECAST": 0, "INCIDENT": 0, "RECOVERY": 0}

    # 1. Check Recovery (High weight for specific terms)
    for kw in RECOVERY_KEYWORDS:
        if re.search(kw, t_lower): scores["RECOVERY"] += 2

    # 2. Check Forecast/Warning
    for kw in FORECAST_SIGS:
        if re.search(kw, t_lower): scores["FORECAST"] += 2

    # 3. Check Incident (Happening/Happened)
    for kw in INCIDENT_SIGS:
        if re.search(kw, t_lower): scores["INCIDENT"] += 2

    # Tie-break logic:
    # If it's a "Bản tin dự báo" but mentions "đã gây thiệt hại", it's likely still a FORECAST
    # bulletin analyzing past impact, but for filtering we treat INCIDENT as higher priority
    # IF impact data is present.

    # Selection
    max_score = max(scores.values())
    if max_score == 0: return "INCIDENT" # Default to incident if matches are vague

    # Final decision
    if scores["RECOVERY"] >= 2 and scores["RECOVERY"] >= scores["INCIDENT"]:
        return "RECOVERY"
    if scores["FORECAST"] > scores["INCIDENT"]:
        return "FORECAST"

    return "INCIDENT"


def contains_disaster_keywords(text: str, title: str = "", trusted_source: bool = False) -> bool:
    """
    Stricter Filtering (v4):
    - Separate Title and Body context.
    - Block diplomatic/admin noise.
    - Veto metaphors and social news aggressively.
    """
    # Use full text for signal detection but remember title importance
    full_text = f"{title}\n{text}" if title else text
    t, t0 = risk_lookup.canon(full_text)
    title_lower = title.lower() if title else ""
    
    # 0. VIP Whitelist (Critical Warnings/Aid that bypass ALL filters)
    for vip_re in sources.VIP_TERMS_RE:
        if title and vip_re.search(title): return True
        if vip_re.search(text): return True

    # 0.1. DEFINITIVE EVENTS PASS (Strong Identifiers in Title)
    if title:
        # Named Storms, Quakes, Tsunamis, Surges
        if re.search(r"(?:bão|áp thấp).*?(?:số\s*\d+|[A-ZĐ][a-zà-ỹ]+)", title_lower, re.IGNORECASE): return True
        if re.search(r"(?:động đất|sóng thần|rung chấn|triều cường|mưa đá|lũ quét|sạt lở đất|lũ ống)", title_lower, re.IGNORECASE): return True
        # Official Bulletins
        if re.search(r"^(?:bản)?\s*tin\s*(?:dự\s*báo|cảnh\s*báo|khí\s*tượng|thủy\s*văn)", title_lower, re.IGNORECASE): return True
        if "đài khí tượng" in title_lower or "trung tâm dự báo" in title_lower: return True

    # 1. ABSOLUTE VETO (Metaphors, Showbiz, etc.) - Priority reject (EARLY EXIT)
    # Check both channels for maximum safety
    for pat_re in ABSOLUTE_VETO_RE:
        if pat_re.search(t):
            return False
    # Check safe unaccented channel for vetoes
    for _, pat_re in ABSOLUTE_VETO_NO_RE:
        if pat_re.search(t0):
            return False

    # Calculate final signals and score
    sig = compute_disaster_signals(text, title=title, trusted_source=trusted_source)
    
    if sig["absolute_veto"]:
        return False

    # 2. Main Threshold Check (10.0 points to pass after bonuses)
    if sig["score"] >= 10.0:
        return True

    # 3. Trusted Source / Verification Fallback (8.0 for official)
    if trusted_source and sig["score"] >= 8.0:
        return True

    is_forecast = sig["stage"] == "FORECAST"
    is_planning = any(pk in full_text.lower() for pk in PLANNING_PREP_KEYWORDS)
    
    # Article Mode Thresholds:
    # Incident news passes at 7.0 (Strict social news filter)
    # Forecast news (Bulletins) needs 8.0+
    threshold = 8.0 if is_forecast else 7.0
    
    if sig["score"] >= threshold:
        # Check if title is actually relevant or just mentions location
        if title_lower and not title_contains_disaster_keyword(title_lower):
            # If title is generic (no disaster word) and score is marginal, reject
            return False
        return True
        
    # Special bypass for high-priority Forecast titles
    if is_forecast and title_lower and nlp.title_contains_disaster_keyword(title_lower):
        return True
        
    return False


def diagnose(text: str, title: str = "") -> dict:
    sig = compute_disaster_signals(text, title=title)
    reason = f"Score {sig['score']:.1f} < 8.0"
    if sig["absolute_veto"]: reason = "Negative keyword match (Veto)"
    elif sig["score"] >= 8.0: reason = "Passed (Score >= 8.0)"
    elif sig.get("rule_matches"): reason = f"Score too low. Met: {sig['rule_matches']}"
    
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
        elif any(vip_re.search(rel_text) for vip_re in sources.VIP_TERMS_RE):
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


def summarize(text: str, max_len: int = 220, title: str = "") -> str:
    if not text:
        return "Nội dung chi tiết đang được cập nhật..."
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if title and (cleaned.lower() == title.lower() or len(cleaned) < 20):
        return "Đang tổng hợp dữ liệu từ bài báo gốc. Vui lòng bấm vào tiêu đề bài báo bên dưới để xem chi tiết."
    if len(cleaned) <= max_len: return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"


# IMPACT EXTRACTION LOGIC


def extract_impact_details(text: str) -> dict:
    """
    UNIFIED IMPACT EXTRACTION (Fusion Strategy)
    Extracts, standardizes, and de-conflicts disaster impact metrics.
    """
    results = {k: [] for k in IMPACT_KEYWORDS.keys()}
    t_acc, t_no = risk_lookup.canon(text or "")
    
    # 1. Collect all raw candidates
    candidates = []
    
    for impact_type in IMPACT_KEYWORDS.keys():
        passes = [
            (t_acc, IMPACT_PATTERNS.get(impact_type, [])),
            (t_no, IMPACT_PATTERNS_NO.get(impact_type, []))
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
                    
                    # Specific typed negations + only the most critical general negs
                    negs = NEGATION_TERMS.get(impact_type, []) + NEGATION_TERMS.get("general", [])
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

def extract_impacts(text: str) -> dict:
    """
    Wrapper for extract_impact_details for backward compatibility.
    """
    details = extract_impact_details(text)
    res = {
        "deaths": None,
        "missing": None,
        "injured": None,
        "damage_billion_vnd": 0.0,
        "agency": None
    }
    
    for k in ["deaths", "missing", "injured"]:
        if k in details and details[k]:
            res[k] = [item["max"] for item in details[k]]
            
    # damage_billion_vnd calculation
    damage_items = details.get("damage", [])
    total_billion = 0.0
    for item in damage_items:
        v = float(item["max"])
        u = (item.get("unit") or "").lower()
        if "tỷ" in u or "tỉ" in u:
            total_billion += v
        elif "triệu" in u or "trieu" in u:
            total_billion += v / 1000.0
            
    res["damage_billion_vnd"] = total_billion
    return res

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
