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
    
    # COMPLEX EXTRACTION PATTERNS (VERBOSE MODE)
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

# High-priority keywords that indicate severe events
HIGH_PRIORITY_KEYWORDS = [
    r"lũ\s*quét", r"lũ\s*ống", r"vỡ\s*đê", r"vỡ\s*đập", r"siêu\s*bão",
    r"sạt\s*lở\s*đất", r"sóng\s*thần", r"động\s*đất\s*mạnh", r"nước\s*dâng\s*do\s*bão",
    r"triều\s*cường\s*kỷ\s*lục"
]
HIGH_PRIORITY_RE = [re.compile(p, re.IGNORECASE) for p in HIGH_PRIORITY_KEYWORDS]

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
    # METAPHORICAL LANGUAGE (Financial, Social, Emotions) 
    r"cơn\s*bão\s*(?:chứng\s*khoán|chứng\s*trường|bán\s*tháo|lãi\s*suất|tỷ\s*giá|khủng\s*hoảng|suy\s*thoái|giá\s*cả|dư\s*luận|truy\s*ền\s*thông|tin\s*giả|mạng|tin\s*đồn|showbiz|tài\s*chính|ngoại\s*giao|chính\s*trị|rating|đánh\s*giá|review|hashtag|trend|viral|quà\s*tặng|lòng|tố)",
    r"bão\s*(?:bán\s*tháo|margin|call\s*margin|giải\s*chấp|chứng\s*khoán|coin|crypto|tỷ\s*giá|lãi\s*suất|phốt|drama|diss|cà\s*khịa|scandal|tin\s*đồn|thị\s*phi|tuyển\s*dụng|sa\s*thải|layoff|nghỉ\s*việc|giá|sale|like|sao\s*kê|chấn\s*thương|view|comment|order|đơn|hàng|flash\s*sale|voucher|ddos|spam|bot|an\s*ninh\s*mạng|email|tin\s*nhắn|notification|thất\s*nghiệp)",
    r"cơn\s*lốc\s*(?:giá|tăng\s*giá|giảm\s*giá|khuyến\s*mãi|sale|flash\s*sale|voucher|đầu\s*tư|đường\s*biên|màu\s*cam|sân\s*cỏ|chuyển\s*nhượng)",
    r"hạn\s*hán\s*(?:bàn\s*thắng|ghi\s*bàn|điểm\s*số|thành\s*tích|danh\s*hiệu|ý\s*tưởng|lời\s*giải)",
    r"khô\s*hạn\s*(?:bàn\s*thắng|ý\s*tưởng|nội\s*dung|tương\s*tác|vốn|tài\s*chính)",
    r"mưa\s*(?:like|view|comment|đơn\s*hàng|order|follow|sub|subscriber|deal|voucher|ưu\s*đãi|quà\s*tặng|coupon|gạch\s*đá|lời\s*khen|feedback|email|tin\s*nhắn|notification|bàn\s*thắng|huy\s*chương)",
    r"ngập\s*(?:deal|ưu\s*đãi|voucher|order|đơn|hashtag|trend|tràn\s*(?:cảm\s*xúc|hạnh\s*phúc|tình\s*yêu|niềm\s*vui))",
    r"cháy\s*(?:vé|show|concert|liveshow|tour|hàng|kho|đơn|order|slot|suất|deadline|kpi|dự\s*án|task|việc|túi|tiền|hết\s*mình|phố|team|máu|đam\s*mê|quá|rực)",
    r"bốc\s*hơi\s*(?:tài\s*khoản|vốn\s*hóa|giá\s*trị|lợi\s*nhuận|tài\s*sản)",
    r"sóng\s*thần\s*(?:sa\s*thải|layoff|bán\s*tháo|giảm\s*giá|công\s*nghệ|pháp\s*lý|lừa\s*đảo)",
    r"làn\s*sóng\s*(?:đầu\s*tư|tẩy\s*chay|sa\s*thải|viral|trend|covid|dịch\s*bệnh|công\s*nghệ|di\s*cư\s*số|di\s*chuyển)(?!\s*sóng\s*thần)",
    r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ|điện\s*ảnh|chính\s*trường|vpop)",
    r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|MXH|mạng\s*xã\s*hội|vbiz)",
    r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|Vpop|V-League|tình\s*trường|chủ\s*quyền)",
    r"cơn\s*lũ\s*(?:tin\s*giả|tội\s*phạm|rác\s*thải\s*số|lượt|fan|tin\s*nhắn|email|notification|lời\s*khen)",
    r"sạt\s*lở\s*(?:niềm\s*tin|danh\s*tiếng|hình\s*ảnh|tài\s*chính|đạo\s*đức)",
    r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm|hôn\s*nhân|gia\s*đình)",
    r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ|tài\s*sản|dự\s*án)",
    r"cơn\s*sốt\s*(?:đất|giá|vé)", r"không\s*khí\s*lạnh\s*(?:nhạt|lùng|giá)",
    r"storm\s+of|flood\s+of|tsunami\s+of", # English metaphors
    # ENTERTAINMENT, SHOWBIZ & LIFESTYLE
    r"\b(?:showbiz|vbiz|vpop|kpop|biz|drama|scandal|netizen|fandom|idol|livestream|streamer|youtuber|tiktoker|influencer|shopping\s*online)\b",
    r"\b(?:ca\s*sĩ|diễn\s*viên|người\s*mẫu|hoa\s*hậu|á\s*hậu|nghệ\s*sĩ|sao\s*Việt|sao\s*hàn|sao\s*hoa)\b",
    r"\b(?:concert|liveshow|đêm\s*nhạc|vở\s*diễn|tiết\s*mục|hợp\s*xướng|giải\s*trí|phim\s*trường|rạp\s*chiếu\s*phim|triển\s*lãm|khai\s*mạc|lễ\s*hội|tuần\s*lễ\s*thời\s*trang)\b",
    r"\b(?:album|mv|ca\s*khúc|bài\s*hát|phim\s*bộ|series|tập\s*cuối|trailer|spoiler|happening|rap\s*việt|chị\s*đẹp|anh\s*trai)\b",
    r"\b(?:đám\s*cưới|hôn\s*lễ|ly\s*hôn|ngoại\s*tình|đánh\s*ghen|hẹn\s*hò|chia\s*tay|tình\s*trường)\b",
    r"\b(?:làm\s*đẹp|skincare|mỹ\s*phẩm|trắng\s*da|giảm\s*cân|tăng\s*cân|thực\s*phẩm\s*chức\s*năng|thăng\s*hạng\s*nhan\s*sắc)\b",
    r"\b(?:noel|giáng\s*sinh|check-in|du\s*lịch|phố\s*đi\s*bộ|ẩm\s*thực|món\s*ngon|nhà\s*hàng|quán\s*ăn|đầu\s*bếp)\b",
    # SPORTS
    r"\b(?:bóng\s*đá|cầu\s*thủ|đội\s*tuyển|world\s*cup|v-league|sea\s*games|aff\s*cup|hlv|huấn\s*luyện\s*viên|trọng\s*tài|sân\s*cỏ|tỉ\s*số|ghi\s*bàn|bàn\s*thắng|vô\s*địch|huy\s*chương|hcv|hcb|hcd|marathon|giải\s*chạy|đua\s*xe|bơi\s*lội|tennis|vòng\s*loại|bán\s*kết|chung\s*kết|ăn\s*mừng|cổ\s*vũ|xuống\s*đường)\b",
    # TECHNOLOGY & GADGETS
    r"\b(?:iphone|samsung|oppo|xiaomi|smartphone|macbook|ipad|máy\s*tính\s*bảng|laptop|xe\s*điện|vinfast|tesla|chip|vi\s*xử\s*lý|hệ\s*điều\s*hành|android|ios|ứng\s*dụng|app|lộ\s*diện\s*thiết\s*kế|giá\s*bán\s*niêm\s*yết|ra\s*mắt\s*sản\s*phẩm)\b",
    r"\b(?:bitcoin|crypto|blockchain|nft|token|ví\s*điện\s*tử|sàn\s*coin|đào\s*coin|tiền\s*ảo|máy\s*đào)\b",
    r"\b(?:game|gaming|pubg|liên\s*quân|esports|nạp\s*game|skin\s*game|playstation|xbox|nintendo)\b",
    r"sóng\s*(?:wifi|wi-?fi|4g|5g|lte|di\s*động|viễn\s*thông|radio|trending|trend|viral)(?!\s*thần)",
    r"mất\s*sóng\s*(?:wifi|wi-?fi|4g|5g|lte)",
    r"bắt\s*sóng", r"phủ\s*sóng", r"vùng\s*phủ\s*sóng", r"trạm\s*phát\s*sóng", r"tần\s*số", r"băng\s*tần",

    # INTERNATIONAL WAR & CONFLICT
    r"\b(?:ukraine|dải\s*gaza|israel|hamas|venezuela|libya|đài\s*loan|nga\s*-\s*ukraine|kiev|moscow|tên\s*lửa|uav|drone|đạn\s*pháo|khai\s*hỏa|chiến\s*sự|vùng\s*kursk|hành\s*lang\s*ngũ\s*cốc)\b",
    r"(?:xung\s*đột\s*vũ\s*trang|quản\s*chế\s*tàu\s*dầu|phong\s*tỏa\s*tàu|tấn\s*công\s*bằng\s*tên\s*lửa)",

    # SOCIAL, CRIME & LAW
    r"\b(?:án\s*mạng|hành\s*hạ|ngược\s*đãi|ma\s*túy|thuốc\s*lắc|đánh\s*bạc|sới\s*bạc|cá\s*độ|mại\s*dâm|mua\s*bán\s*dâm|tú\s*bà|môi\s*giới|lừa\s*đảo|chiếm\s*đoạt|truy\s*nã|nghi\s*phạm|hung\s*thủ|sát\s*hợi|bạo\s*hành|bắt\s*cóc|trục\s*lợi|giả\s*chết|karaoke)\b",
    r"\b(?:xử\s*phạt|khởi\s*tố|truy\s*tố|xét\s*xử|phiên\s*tòa|bản\s*án|tử\s*hình|chung\s*thân|án\s*tù|bị\s*can|bị\s*cáo|tòa\s*án\s*nhân\s*dân|điều\s*tra\s*viên|tranh\s*chấp|khiếu\s*nại|tố\s*cáo)\b",
    r"\b(?:giấy\s*phép\s*lái\s*xe|phạt\s*nguội|đăng\s*kiểm|cấp\s*căn\s*cước|hộ\s*chiếu|tước\s*bằng|định\s*danh\s*điện\s*tử)\b",
    r"\b(?:xổ\s*số|vietlott|trúng\s*số|giải\s*đặc\s*biệt|vé\s*số|kết\s*quả\s*mở\s*thưởng)\b",
    r"\b(?:ung\s*thư|tiểu\s*đường|huyết\s*áp|đột\s*quỵ|ngộ\s*độc\s*lá\s*ngón|vắc\s*xin|chiến\s*dịch\s*tiêm\s*chủng|dinh\s*dưỡng|thực\s*phẩm|món\s*ăn|đặc\s*sản)\b",

    # ADMINISTRATIVE NOISE
    r"\b(?:đại\s*hội\s*đảng|ban\s*bí\s*thư|bộ\s*chính\s*trị|ủy\s*viên\s*trung\s*ương|hội\s*nghị\s*ban\s*chấp\s*hành|thành\s*ủy|tỉnh\s*ủy|ubnd|hđnd|mttq|điều\s*động\s*cán\s*bộ|bổ\s*nhiệm|luân\s*chuyển|phân\s*công|quy\s*tập\s*hài\s*cốt|liệt\s*sĩ|nghĩa\s*trang\s*liệt\s*sĩ|trao\s*huân\s*chương|cờ\s*thi\s*đua|vinh\s*danh|kỷ\s*niệm\s*ngày\s*thành\s*lập)\b",
    r"\b(?:nông\s*thôn\s*mới|quy\s*hoạch\s*đô\s*thị|vành\s*đai\s*\d+|cao\s*tốc|khởi\s*công|thông\s*xe|nghiệm\s*thu|đấu\s*giá\s*đất|sổ\s*đỏ|quyền\s*sử\s*dụng\s*đất|giao\s*đất|chuyển\s*nhượng)\b",

    # OTHERS (Spam/Noise)
    r"việc\s*nhẹ\s*lương\s*cao|bóc\s*vỏ\s*tôm|tắt\s*camera|camera\s*quay\s*lén|giải\s*cứu\s*(?:rùa|chim|động\s*vật|thú\s*quý|tôm\s*hùm|nông\s*sản)",
    r"\.docx\b|\.pdf\b|\.doc\b|AstroWind|Tailwind\s*CSS",
    r"giá\s*thanh\s*long|lên\s*kệ\s*siêu\s*thị|xuất\s*khẩu\s*nông\s*sản|vé\s*máy\s*bay\s*giá\s*rẻ|tết\s*nguyên\s*đán|thưởng\s*tết",

    # ADDED: SOCIAL & POLICY NOISE (Deep Filtering)
    r"\b(?:hành\s*trình\s*công\s*lý|đạo\s*đức\s*nghề\s*nghiệp|quy\s*tắc\s*ứng\s*xử|văn\s*hóa\s*công\s*sở)\b",
    r"\b(?:học\s*phí|điểm\s*chuẩn|quy\s*chế\s*thi|kỳ\s*thi\s*tốt\s*nghiệp|sách\s*giáo\s*khoa|kỷ\s*yếu|tự\s*chủ\s*đại\s*học)\b",
    r"\b(?:bảo\s*hiểm\s*xã\s*hội|bhxh|hưu\s*trí|lương\s*tối\s*thiểu|đóng\s*bảo\s*hiểm|trợ\s*cấp\s*thất\s*nghiệp|xuất\s*khẩu\s*lao\s*động)\b",
    r"\b(?:đấu\s*thầu\s*thuốc|vật\s*tư\s*y\s*tế|bảo\s*hiểm\s*y\s*tế|y\s*đức|quản\s*lý\s*bệnh\s*viện|khám\s*sức\s*khỏe\s*định\s*kỳ)\b",
    r"\b(?:đại\s*lễ|cầu\s*an|lễ\s*chùa|dâng\s*hương|tâm\s*linh|ngoại\s*cảm|gọi\s*hồn|vong\s*linh)\b",
    r"\b(?:biệt\s*thự\s*biển|condotel|shophouse|vinhomes|sungroup|novaland|mở\s*bán\s*giai\s*đoạn|chiết\s*khấu\s*khủng)\b",
    # ADDED: COMMERCIAL, VIRAL & LIFESTYLE NOISE (Final Precision)
    r"\b(?:siêu\s*sale|săn\s*deal|áp\s*mã|giảm\s*sâu|mở\s*bán\s*ưu\s*đãi|càn\s*quét\s*giỏ\s*hàng|đổ\s*bộ\s*thị\s*trường)\b",
    r"\b(?:clip\s*gây\s*bão|video\s*xôn\s*xao|hành\s*động\s*đẹp\s*gây\s*sốt|cư\s*dân\s*mạng\s*truy\s*tìm|phẫn\s*nộ\s*với\s*hành\s*động)\b",
    r"\b(?:cơn\s*lốc\s*tuyển\s*dụng|cơ\s*hội\s*vàng|thăng\s*tiến\s*sự\s*nghiệp|định\s*hướng\s*nghề\s*nghiệp|bí\s*quyết\s*thành\s*công)\b",
    r"\b(?:công\s*thức\s*nấu\s*ăn|mẹo\s*vặt\s*nhà\s*bếp|top\s*quán\s*ngon|review\s*ẩm\s*thực|đặc\s*sản\s*vùng\s*miền|thực\s*đơn\s*mỗi\s*ngày)\b",
    r"\b(?:đề\s*tài\s*nghiên\s*cứu|công\s*trình\s*khoa\s*học|phát\s*kiến\s*vĩ\s*đại|luận\s*văn\s*tốt\s*nghiệp|chuyên\s*đề\s*học\s*thuật)\b",

    # FINAL LAYER: CORPORATE, URBAN & GLOBAL NOISE
    r"\b(?:đại\s*hội\s*cổ\s*đông|hội\s*đồng\s*quản\s*trị|hđqt|báo\s*cáo\s*tài\s*chính|cổ\s*phiếu\s*quỹ|vốn\s*hóa\s*thị\s*trường|niêm\s*yết\s*sàn|trái\s*phiếu\s*doanh\s*nghiệp)\b",
    r"\b(?:đặt\s*tên\s*đường|chỉnh\s*trang\s*đô\s*thị|tu\s*bổ\s*di\s*tích|xây\s*dựng\s*công\s*viên|vườn\s*hoa|tượng\s*đài|chiếu\s*sáng\s*đô\s*thị)\b",
    r"\b(?:bầu\s*cử\s*mỹ|tổng\s*thống\s*mỹ|nhà\s*trắng|điện\s*kremlin|thám\s*hiểm\s*không\s*gian|nasa|spacex|vũ\s*trụ|thiên\s*văn|khảo\s*cổ)\b",
    r"\b(?:fashion\s*week|bộ\s*sưu\s*tập|thời\s*trang\s*cao\s*cấp|nhãn\s*hàng\s*xa\s*xỉ|túi\s*xách|nước\s*hoa|trang\s*sức|kim\s*cương)\b",

    # FINAL POLISH: ZODIAC, AUTOMOTIVE & LIFESTYLE MARKETING
    r"\b(?:tử\s*vi|cung\s*hoàng\s*đạo|phong\s*thủy|hợp\s*tuổi|ngày\s*tốt|giờ\s*xấu|xem\s*bói|gieo\s*quẻ|nhân\s*tướng\s*học)\b",
    r"\b(?:đánh\s*giá\s*xe|trải\s*nghiệm\s*lái|động\s*cơ\s*turbo|mã\s*lực|mô-men\s*xoắn|phụ\s*tùng\s*chính\s*hãng|lazang|lốp\s*xe|ngoại\s*thất\s*xe)\b",
    r"\b(?:phẫu\s*thuật\s*thẩm\s*mỹ|hút\s*mỡ|nâng\s*mũi|tiêm\s*filler|căng\s*chỉ|trị\s*mụn|chăm\s*sóc\s*da|spa|thẩm\s*mỹ\s*viện)\b",
    r"\b(?:hội\s*chợ\s*thương\s*mại|ngày\s*hội\s*việc\s*làm|lễ\s*hội\s*ẩm\s*thực|minigame|bốc\s*thăm\s*trúng\s*thưởng|vòng\s*quay\s*may\s*mắn)\b",

    # --- THE ULTIMATE REFINEMENT: HEALTH, PARENTING, ARTS & PETS ---
    r"\b(?:thực\s*đơn\s*giảm\s*cân|mẹo\s*sống\s*khỏe|tác\s*dụng\s*của\s*rau| yoga|gym|fitness|bài\s*tập\s*thể\s*dục|dinh\s*dưỡng\s*lành\s*mạnh)\b",
    r"\b(?:nuôi\s*dạy\s*con|sữa\s*mẹ|ăn\s*dặm|phát\s*triển\s*trí\s*não|đồ\s*chơi\s*trẻ\s*em|mẹ\s*bầu|thai\s*nhi|mầm\s*non)\b",
    r"\b(?:phê\s*bình\s*sách|tác\s*giả\s*trẻ|triển\s*lãm\s*tranh|hội\s*họa|điêu\s*khắc|giai\s*thoại\s*lịch\s*sử|nhân\s*vật\s*lịch\s*sử|thơ\s*ca)\b",
    r"\b(?:chăm\s*sóc\s*chó\s*mèo|thú\s*cưng|giống\s*chó|phụ\s*kiện\s*pet|thú\s*y|bệnh\s*viện\s*thú\s*y)\b",
    r"\b(?:báo\s*giá\s*xi\s*măng|sắt\s*thép|vật\s*liệu\s*xây\s*dựng|mẫu\s*nhà\s*đẹp|nội\s*thất\s*hiện\s*đại|thiết\s*kế\s*căn\s*hộ)\b",

    # --- ADVANCED PRECISION: TOURISM, AGRICULTURE & CREATIVE ARTS ---
    r"\b(?:voucher\s*du\s*lịch|tour\s*giá\s*rẻ|cẩm\s*nang\s*điểm\s*đến|lịch\s*trình\s*khám\s*phá|review\s*homestay|vé\s*máy\s*bay\s*khứ\s*hồi|dịch\s*vụ\s*nghỉ\s*dưỡng)\b",
    r"\b(?:kỹ\s*thuật\s*trồng|chăm\s*sóc\s*cây\s*cảnh|phong\s*lan|bonsai|phân\s*bón|thuốc\s*trừ\s*sâu|nông\s*nghiệp\s*công\s*nghệ\s*cao|giống\s*cây\s*trồng)\b",
    r"\b(?:học\s*đàn|học\s*vẽ|chụp\s*ảnh\s*chân\s*dung|ống\s*máy\s*ảnh|mirrorless|dựng\s*phim|hậu\s*kỳ|thiết\s*kế\s*đồ\s*họa|photoshop|illustrator)\b",
    r"\b(?:tiệc\s*tất\s*niên|year\s*end\s*party|teambuilding|văn\s*hóa\s*doanh\s*nghiệp|nhân\s*viên\s*tiêu\s*biểu|nghỉ\s*mát\s*hè|sinh\s*nhật\s*công\s*ty)\b",

    # --- THE FINAL-FINAL-ULTRA PRECISION: PSYCHOLOGY, TECH, SCIENCE & LEGAL ---
    r"\b(?:tâm\s*lý\s*học|trầm\s*cảm|chữa\s*lành|sang\s*chấn\s*tâm\s*lý|kỹ\s*năng\s*sống|tư\s*duy\s*tích\s*cực|phát\s*triển\s*bản\s*thân|hạnh\s*phúc\s*mỗi\s*ngày)\b",
    r"\b(?:big\s*data|machine\s*learning|trí\s*tuệ\s*nhân\s*tạo|backend|frontend|lập\s*trình\s*viên|python|java|javascript|thiết\s*kế\s*ui/ux|server|hosting|ên\s*kết\s*đào\s*tạo)\b",
    r"\b(?:hố\s*đen|thiên\s*hà|dải\s*ngân\s*hà|vật\s*chất\s*tối|gen\s*di\s*truyền|dna|tế\s*bào\s*gốc|biến\s*đổi\s*gen|vi\s*khuẩn|virus\s*(?!\s*it))\b",
    r"\b(?:viện\s*kiểm\s*sát|cơ\s*quan\s*điều\s*tra|luật\s*sư|bào\s*chữa|kháng\s*cáo|tư\s*vấn\s*pháp\s*luật|hợp\s*đồng\s*kinh\s*tế|thừa\s*kế|tranh\s*chấp\s*tài\s*sản)\b",
    r"\b(?:đón\s*tiếp\s*đoàn|nghị\s*sự|ký\s*kết\s*biên\s*bản|hợp\s*tác\s*chiến\s*lược|trao\s*đổi\s*văn\s*hóa|ngoại\s*giao\s*nhân\s*dân|thi\s*đua\s*khen\s*thưởng|công\s*tác\s*cán\s*bộ)\b",

    # --- THE "PROFESSIONAL & DAILY NOISE" LAYER ---
    r"\b(?:khám\s*xét|niêm\s*phong|cưỡng\s*chế\s*kê\s*biên|phong\s*tỏa\s*tài\s*khoản|tạm\s*đình\s*chỉ\s*công\s*tác|lệnh\s*bắt\s*tạm\s*giam|đọc\s*lệnh\s*khởi\s*tố)\b",
    r"\b(?:nghi\s*thức\s*ngoại\s*giao|lễ\s*đón|duyệt\s*đội\s*danh\s*dự|tiễn\s*đoàn|quan\s*hệ\s*đối\s*tác|vun\s*đắp\s*tình\s*hữu\s*nghị)\b",
    r"\b(?:căn\s*hộ\s*cao\s*cấp|mặt\s*bằng\s*kinh\s*doanh|thuê\s*văn\s*phòng|sang\s*nhượng\s*quán|kđt|khu\s*đô\s*thị\s*mới|quy\s*hoạch\s*chi\s*tiết)\b",
    r"\b(?:tuyển\s*dụng\s*gấp|mức\s*lương\s*thỏa\s*thuận|quyền\s*lợi\s*hấp\s*dẫn|môi\s*trường\s*làm\s*việc|nộp\s*hồ\s*sơ|phỏng\s*vấn\s*online)\b",

    # --- DEEP GLOBAL & STATE NOISE ---
    r"\b(?:trung\s*đông|hezbollah|houthi|biển\s*đỏ|eo\s*biển\s*hormuz|xung\s*đột\s*israel|thủ\s*tướng\s*netanyahu)\b",
    r"\b(?:đồi\s*capitol|lầu\s*năm\s*góc|bầu\s*cử\s*tổng\s*thống|đảng\s*dân\s*chủ|đảng\s*cộng\s*hòa|donald\s*trump|joe\s*biden|kamala\s*harris)\b",
    r"\b(?:fed|wall\s*street|dow\s*jones|nasdaq|goldman\s*sachs|jp\s*morgan|quỹ\s*tiền\s*tệ\s*quốc\s*tế|ngân\s*hàng\s*thế\s*giới|wb|imf)\b",
    r"\b(?:huân\s*chương|bằng\s*khen|danh\s*hiệu\s*cao\s*quý|kỷ\s*niệm\s*chương|nghệ\s*sĩ\s*nhân\s*dân|nsnd|nghệ\s*sĩ\s*ưu\s*tú|nsut)\b",
    r"\b(?:hội\s*nghị\s*hiệp\s*thương|kỳ\s*hợp\s*thứ|đảng\s*viên\s*mới|sinh\s*hoạt\s*chi\s*bộ|nghị\s*quyết\s*trung\s*ương|công\s*tác\s*kiểm\s*tra\s*đảng)\b",

    # --- THE FINAL-FINAL-COMPLETE LAYER: JUDICIARY, HERITAGE & TRENDING TV ---
    r"\b(?:tòa\s*án\s*tối\s*cao|viện\s*kiểm\s*sát\s*nhân\s*dân|hội\s*đồng\s*xét\s*xử|luật\s*sư\s*bào\s*chữa|tranh\s*tụng|phiên\s*tòa\s*sơ\s*thẩm|phúc\s*thẩm|đại\s*diện\s*pháp\s*luật)\b",
    r"\b(?:di\s*sản\s*văn\s*hóa|phong\s*tục\s*tập\s*quán|bảo\s*tồn\s*di\s*tích|làng\s*nghề\s*truyền\s*thống|nghệ\s*nhân\s*ưu\s*tú|di\s*vật|cổ\s*vật)\b",
    r"\b(?:miss\s*grand|miss\s*universe|miss\s*world|anh\s*trai\s*say\s*hi|anh\s*trai\s*vượt\s*ngàn\s*chông\s*gai|the\s*mask\s*singer|show\s*thực\s*tế)\b",

    # --- THE "TECHNICAL, AVIATION & INFRA" LAYER ---
    r"\b(?:trích\s*lập\s*dự\s*phòng|nợ\s*xấu|thanh\s*khoản|tái\s*cơ\s*cấu|phí\s*bảo\s*hiểm|hợp\s*đồng\s*nhân\s*thọ|quyền\s*lợi\s*khách\s*hàng)\b",
    r"\b(?:khớp\s*lệnh|dư\s*mua|dư\s*bán|chứng\s*khoán\s*phái\s*sinh|khối\s*ngoại|vốn\s*điều\s*lệ|lệnh\s*giới\s*hạn)\b",
    r"\b(?:hoãn\s*chuyến|chậm\s*chuyến|hủy\s*chuyến|hành\s*lý\s*ký\s*gửi|soát\s*vé|thủ\s*tục\s*check-in|thị\s*thực|visa)\b",
    r"\b(?:giấy\s*phép\s*xây\s*dựng|hoàn\s*công|bê\s*tông\s*tươi|ép\s*cọc|nền\s*móng|đấu\s*thầu\s*xây\s*lắp|nhà\s*thầu\s*chính|nghiệm\s*thu\s*dự\s*án)\b",
    r"\b(?:vệ\s*tinh\s*nhân\s*tạo|trạm\s*không\s*gian|mưa\s*sao\s*băng|nhật\s*thực|nguyệt\s*thực|kính\s*thiên\s*văn|tàu\s*vũ\s*trụ)\b",

    # --- THE "JOURNALISM & LIFESTYLE DIGEST" LAYER ---
    r"\b(?:bạn\s*đọc\s*viết|nhịp\s*cầu\s*độc\s*giả|thư\s*tòa\s*soạn|ký\s*sự\s*pháp\s*đình|chuyện\s*thường\s*ngày|góc\s*nhìn\s*tri\s*thức|diễn\s*đàn\s*kinh\s*tế)\b",
    r"\b(?:tư\s*vấn\s*hướng\s*nghiệp|cẩm\s*nang\s*du\s*học|xét\s*tuyển\s*học\s*bạ|chỉ\s*tiêu\s*tuyển\s*sinh|điểm\s*sàn|nguyện\s*vọng\s*1|kỳ\s*thi\s*đánh\s*giá\s*năng\s*lực)\b",
    r"\b(?:ban\s*quản\s*trị|phí\s*bảo\s*trì|họp\s*dân\s*cư|tiện\s*ích\s*nội\s*khu|vận\s*hành\s*nhà\s*máy|hệ\s*thống\s*máy\s*chủ|đường\s*truyền\s*internet)\b",
    r"\b(?:khai\s*trương\s*chi\s*nhánh|giảm\s*giá\s*khai\s*trương|voucher\s*mua\s*sắm|thẻ\s*thành\s*viên|tích\s*điểm\s*đổi\s*quà|giờ\s*vàng\s*mua\s*sắm)\b",
    r"\b(?:hạt\s*giống\s*tâm\s*hồn|châm\s*ngôn\s*sống|triết\s*lý\s*kinh\s*doanh|quà\s*tặng\s*cuộc\s*sống|nhân\s*sinh\s*quan|đắc\s*nhân\s*tâm)\b",

    # --- THE "TECHNICAL INFRA, CIVIC ADMIN & HISTORICAL RESEARCH" LAYER ---
    r"\b(?:nút\s*giao\s*thông|cầu\s*vượt\s*thép|hầm\s*chui|dải\s*phân\s*cách|lát\s*vỉ\s*hè|chỉnh\s*trang\s*hàng\s*rào|cáp\s*quang\s*biển|băng\s*thông|trạm\s*biến\s*áp\s*áp\s*cao)\b",
    r"\b(?:tổ\s*dân\s*phố|khu\s*phố\s*văn\s*hóa|gia\s*đình\s*tiêu\s*biểu|giấy\s*khai\s*sinh|thường\s*trú|tạm\s*vắng|căn\s*cước\s*công\s*dân|định\s*danh\s*mức\s*2)\b",
    r"\b(?:phân\s*tích\s*kỹ\s*thuật|ngưỡng\s*kháng\s*cự|hỗ\s*trợ\s*mạnh|mô\s*hình\s*nến|chỉ\s*số\s*rsi|etf|chứng\s*quyền|trái\s*phiếu\s*chính\s*phủ)\b",
    r"\b(?:lăng\s*tẩm|đền\s*đài|cố\s*đô|di\s*tích\s*quốc\s*gia|khảo\s*cổ\s*học|dấu\s*tích\s*cổ|hiện\s*vật|triều\s*đại|vua\s*chúa)\b",
    r"\b(?:bản\s*vá\s*lỗi|mã\s*nguồn|lỗ\s*hổng\s*bảo\s*mật|tấn\s*công\s*ddos|phần\s*mềm\s*độc\s*hại|trải\s*nghiệm\s*người\s*dùng|ux/ui|giao\s*diện\s*mới)\b",

    # --- THE "INDUSTRIAL, ENERGY & BIODIVERSITY" LAYER ---
    r"\b(?:dây\s*chuyền\s*sản\s*xuất|khu\s*công\s*nghiệp|kcn|khu\s*chế\s*xuất|nguyên\s*liệu\s*đầu\s*vào|sản\s*lượng\s*hàng\s*năm|dệt\s*may|da\s*giày|linh\s*kiện\s*điện\s*tử)\b",
    r"\b(?:điện\s*mặt\s*trời|điện\s*gió|điện\s*áp\s*mái|giá\s*mua\s*điện|truyền\s*tải\s*điện|tiết\s*kiệm\s*điện\s*năng|nguồn\s*năng\s*lượng\s*tái\s*tạo)\b",
    r"\b(?:đa\s*dạng\s*sinh\s*học|bảo\s*tồn\s*động\s*vật|cá\s*thể\s*quý\s*hiếm|sách\s*đỏ|thả\s*về\s*rừng|vườn\s*quốc\s*gia|khu\s*bảo\s*tồn|tài\s*nguyên\s*sinh\s*vật)\b",
    r"\b(?:chứng\s*chỉ\s*hành\s*nghề|đào\s*tạo\s*nghiệp\s*vụ|kỹ\s*năng\s*chuyên\s*môn|huấn\s*luyện\s*an\s*toàn|văn\s*bằng\s*quốc\s*tế|phong\s*trào\s*tay\s*nghề)\b",
    r"\b(?:vệ\s*sinh\s*môi\s*trường|thu\s*gom\s*rác\s*thải|nhà\s*máy\s*xử\s*lý|phí\s*vệ\s*sinh|cung\s*cấp\s*nước\s*sạch|giá\s*nước\s*sinh\s*hoạt)\b",

    # --- THE "STATE PROTOCOL, CORPORATE WELFARE & ACADEMIC ADMIN" LAYER ---
    r"\b(?:tiếp\s*đại\s*sứ|trình\s*quốc\s*thư|giao\s*lưu\s*hữu\s*nghị|củng\s*cố\s*quan\s*hệ|ngoại\s*giao\s*đa\s*phương|ký\s*kết\s*biên\s*bản\s*ghi\s*nhớ|MOU|đối\s*tác\s*chiến\s*lược)\b",
    r"\b(?:lương\s*tháng\s*13|thưởng\s*năng\s*suất|nội\s*quy\s*lao\s*động|công\s*đoàn\s*cơ\s*sở|khen\s*thưởng\s*định\s*kỳ|phong\s*trào\s*lao\s*động|thi\s*đua\s*ngành)\b",
    r"\b(?:bản\s*quyền\s*tác\s*giả|sở\s*hữu\s*trí\s*tuệ|bảo\s*hộ\s*thương\s*hiệu|luận\s*văn\s*thạc\s*sĩ|nghiên\s*cứu\s*sinh|hội\s*đồng\s*bảo\s*vệ|tạp\s*chí\s*khoa\s*học)\b",
    r"\b(?:điểm\s*thu\s*gom\s*rác|phí\s*dịch\s*vụ\s*chung\s*cư|đèn\s*đường|lát\s*đá\s*vỉ\s*hè|cây\s*xanh\s*đô\s*thị|phun\s*thuốc\s*muỗi|diệt\s*côn\s*trùng)\b",
    r"\b(?:trà\s*đạo|thiền\s*định|cắm\s*hoa\s*nghệ\s*thuật|sưu\s*tầm\s*đồ\s*cổ|thú\s*vui\s*tao\s*nhã|trưng\s*bày\s*sinh\s*vật\s*cảnh)\b",

    # --- THE FINAL-FINAL-ULTIMATE PRECISION: DEFENSE, CULTURE & REGULATORY ---
    r"\b(?:huấn\s*luyện\s*quân\s*sự|tuyển\s*quân|diễn\s*tập\s*phương\s*án|quân\s*khu|bộ\s*chỉ\s*huy\s*quân\s*sự|dân\s*quân\s*tự\s*vệ|phòng\s*thủ\s*dân\s*sự)\b",
    r"\b(?:lễ\s*hội\s*dân\s*gian|hội\s*làng|tín\s*ngưỡng\s*thờ\s*cúng|không\s*gian\s*văn\s*hóa|không\s*gian\s*đi\s*bộ|nghệ\s*thuật\s*đường\s*phố)\b",
    r"\b(?:quản\s*lý\s*thị\s*trường|hàng\s*giả\s*hàng\s*nhái|tiêu\s*hủy\s*tang\s*vật|vi\s*phạm\s*nhãn\s*hiệu|quản\s*lý\s*giá\s*cả|bình\s*ổn\s*thị\s*trường)\b",
    r"\b(?:lấy\s*ý\s*kiến\s*dự\s*thảo|nghị\s*định\s*hướng\s*dẫn|thông\s*tư\s*liên\s*tịch|hđnd\s*các\s*cấp|công\s*tác\s*pháp\s*chế|tuyên\s*truyền\s*pháp\s*luật)\b",
    r"\b(?:tổng\s*đài\s*cskh|đường\s*dây\s*nóng\s*khiếu\s*nại|giải\s*đáp\s*thắc\s*mắc|phản\s*hồi\s*khách\s*hàng|quy\s*trình\s*kỹ\s*thuật|hỗ\s*trợ\s*trực\s*tuyến)\b",
    # --- THE "CONSUMER TECH, DIGITAL MARKETING & NICHE HOBBIES" LAYER ---
    r"\b(?:đập\s*hộp|trên\s*tay|review\s*chi\s*tiết|đánh\s*giá\s*hiệu\s*năng|so\s*sánh\s*cấu\s*hình|benchmark|antutu|camera\s*selfie|màn\s*hình\s*amoled|tần\s*số\s*quét)\b",
    r"\b(?:tối\s*ưu\s*seo|backlink|chạy\s*quảng\s*cáo|adsense|google\s*ads|facebook\s*ads|tiktok\s*shop|tiếp\s*thị\s*liên\s*kết|affiliate\s*marketing|branding|thương\s*hiệu\s*cá\s*nhân)\b",
    r"\b(?:máy\s*ảnh\s*film|len\s*mf|lens\s*fix|ngàm\s*chuyển|phụ\s*kiện\s*studio|đèn\s*flash|chụp\s*ảnh\s*nghệ\s*thuật|quay\s*phim\s*4k)\b",
    r"\b(?:cá\s*cảnh|thủy\s*sinh|hồ\s*cá\s*koi|cây\s*không\s*khí|sen\s*đá|xương\s*rồng|đồ\s*chơi\s*mô\s*hình|lego|action\s*figure|vape|pod\s*system)\b",
    r"\b(?:mẹo\s*làm\s*bánh|nấu\s*ăn\s*ngon|nồi\s*chiên\s*không\s*dầu|máy\s*ép\s*chậm|đồ\s*gia\s*dụng\s*thông\s*minh|robot\s*hút\s*bụi|máy\s*rửa\s*bát)\b",

    # --- THE "RURAL, MARINE & PHILANTHROPY" LAYER ---
    r"\b(?:ngư\s*trường\s*khai\s*thác|xuất\s*khẩu\s*hải\s*sản|vận\s*tải\s*biển|cảng\s*nước\s*sâu|luồng\s*hàng\s*hải|tàu\s*viễn\s*dương|giàn\s*khoan\s*dầu|dầu\s*khí\s*quốc\s*gia)\b",
    r"\b(?:cánh\s*đồng\s*mẫu\s*lớn|hợp\s*tác\s*xã\s*nông\s*nghiệp|sản\s*xuất\s*giỏi|chăn\s*nuôi\s*tập\s*trung|chuỗi\s*giá\s*trị|truy\s*xuất\s*nguồn\s*gốc)\b",
    r"\b(?:hiến\s*máu\s*nhân\s*đạo|hành\s*trình\s*đỏ|quỹ\s*khuyến\s*học|mùa\s*hè\s*xanh|tiếp\s*sức\s*đến\s*trường|chương\s*trình\s*từ\s*thiện\s*thường\s*niên)\b",
    r"\b(?:đấu\s*giá\s*tác\s*phẩm|thị\s*trường\s*nghệ\s*thuật|triển\s*lãm\s*cá\s*nhân|tài\s*sản\s*văn\s*hóa|giá\s*trị\s*dân\s*gian)\b",
    r"\b(?:vệ\s*sinh\s*an\s*toàn\s*thực\s*phẩm|ngộ\s*độc\s*thực\s*phẩm\s*tại\s*trường|kiểm\s*tra\s*liên\s*ngành|xử\s*phạt\s*hành\s*chính\s*cơ\s*sở)\b",

    # --- THE "E-SPORTS, HOME IMPROVEMENT, FITNESS & ACADEMIC ADMIN" LAYER ---
    r"\b(?:giải\s*đấu\s*esports|vòng\s*bảng|vòng\s*playoff|tuyển\s*thủ\s*chuyên\s*nghiệp|binh\s*đoàn|patch\s*update|meta\s*game|tướng\s*mới|trang\s*phục\s*vĩnh\s*viễn)\b",
    r"\b(?:cải\s*tạo\s*nhà|sơn\s*nhà|lát\s*sàn|thiết\s*kế\s*nội\s*thất|đồ\s*gia\s*dụng|tủ\s*bếp|phòng\s*khách\s*đẹp|mẫu\s*rèm\s*cửa|giấy\s*dán\s*tường)\b",
    r"\b(?:tập\s*gym|bodybuilding|whey\s*protein|creatine|giảm\s*mỡ\s*bụng|cơ\s*bụng\s*6\s*múi|huấn\s*luyện\s*viên\s*cá\s*nhân|pt|chạy\s*bộ\s*mỗi\s*ngày)\b",
    r"\b(?:học\s*bổng\s*toàn\s*phần|hội\s*thảo\s*quốc\s*tế|tạp\s*chí\s*isi/scopus|công\s*bố\s*nghiên\s*cứu|hệ\s*đào\s*tạo\s*từ\s*xa|văn\s*bằng\s*2|vừa\s*học\s*vừa\s làm)\b",
    r"\b(?:phí\s*quản\s*lý\s*vận\s*hành|bảo\s*trì\s*thang\s*máy|hệ\s*thống\s*chiếu\s*sáng|xử\s*lý\s*nước\s*thải\s*sinh\s*hoạt|vệ\s*sinh\s*công\s*nghiệp)\b",

    # --- THE "BEAUTY CONTESTS, LUXURY TRAVEL & EV TECHNICALS" LAYER ---
    r"\b(?:miss\s*global|hoa\s*hậu\s*hoàn\s*vũ|vương\s*miện\s*danh\s*giá|nhan\s*sắc\s*thăng\s*hạng|catwalk|trình\s*diễn\s*bikini|phần\s*thi\s*ứng\s*xử|người\s*đẹp\s*biển)\b",
    r"\b(?:resort\s*5\s*sao|biệt\s*thự\s*nghỉ\s*dưỡng\s*luxury|hạng\s*thương\s*gia|du\s*thuyền\s*triệu\s*đô|trải\s*nghiệm\s*thượng\s*lưu|dịch\s*vụ\s*chuẩn\s*quốc\s*tế)\b",
    r"\b(?:xe\s*điện\s*thông\s*minh|trạm\s*sạc\s*nhanh|pin\s*lithium|phạm\s*vi\s*di\s*chuyển|xe\s*tự\s*lái|adas|tự\s*động\s*hóa|triển\s*lãm\s*xe\s*vms)\b",
    r"\b(?:văn\s*phòng\s*cho\s*thuê|co-working\s*space|khu\s*phức\s*hợp|tiện\s*ích\s*all-in-one|tòa\s*nhà\s*thông\s*minh|quản\s*lý\s*bất\s*động\s*sản)\b",

    # --- THE "SAFETY, COMPLIANCE & PROFESSIONAL STANDARDS" LAYER ---
    r"\b(?:kiểm\s*tra\s*pccc|nghiệm\s*thu\s*phòng\s*cháy|diễn\s*tập\s*phòng\s*cháy|giấy\s*chứng\s*nhận\s*vệ\s*sinh\s*an\s*toàn|đạt\s*chuẩn\s*iso|hợp\s*quy\s*hợp\s*chuẩn|kiểm\s*định\s*chất\s*lượng)\b",
    r"\b(?:đạo\s*đức\s*pháp\s*luật|văn\s*hóa\s*ngành\s*y|kỷ\s*cương\s*hành\s*chính|tác\s*phong\s*công\s*vụ|đổi\s*mới\s*sáng\s*tạo|chuyển\s*đổi\s*số\s*quốc\s*gia)\b",
    r"\b(?:hội\s*thảo\s*chuyên\s*đề|tổng\s*kết\s*phong\s*trào|thi\s*đua\s*ngành\s*giáo\s*dục|trao\s*giải\s*thưởng\s*sáng\s*tạo|triển\s*khai\s*nhiệm\s*vụ\s*trọng\s*tâm)\b",
    r"\b(?:vệ\s*sinh\s*môi\s*trường\s*đô\s*thị|phân\s*loại\s*rác\s*tại\s*nguồn|phát\s*động\s*tết\s*trồng\s*cây|hưởng\s*ứng\s*giờ\s*trái\s*đất)\b",

    # --- THE "BANKING, TELCO & PERSONAL LIFECYCLE" LAYER ---
    r"\b(?:tin\s*buồn|lễ\s*viếng|vô\s*cùng\s*thương\s*tiếc|hưởng\s*thọ|lễ\s*truy\s*điệu|an\s*táng|phúng\s*viếng|chia\s*buồn\s*cùng\s*gia\s*đình)\b",
    r"\b(?:quên\s*mật\s*khẩu|mã\s*otp|lỗi\s*chuyển\s*tiền|hạn\s*mức\s*giao\s*dịch|quản\s*lý\s*chi\s*tiêu|thanh\s*toán\s*hóa\s*đơn|liên\s*kết\s*ngân\s*hàng)\b",
    r"\b(?:bảo\s*trì\s*cáp\s*quang|đứt\s*cáp|gói\s*cước\s*data|nạp\s*thẻ\s*điện\s*thoại|thuê\s*bao\s*di\s*động|chất\s*lượng\s*đường\s*truyền|sim\s*số\s*đẹp)\b",
    r"\b(?:diện\s*tích\s*sử\s*dụng|hợp\s*đồng\s*đặt\s*cọc|pháp\s*lý\s*dự\s*án|tiến\s*độ\s*bàn\s*giao|hoa\s*hồng\s*môi\s*giới|tầng\s*thanh\s*khoản|nhà\s*phố\s*liền\s*kề)\b",
    r"\b(?:kinh\s*phí\s*nghiên\s*cứu|xếp\s*hạng\s*đại\s*học|chỉ\s*số\s*trích\s*dẫn|đăng\s*báo\s*quốc\s*tế|quỹ\s*phát\s*triển\s*khoa\s*học|nghiên\s*cứu\s*sinh\s*tiến\s*sĩ)\b",

    # --- THE "REAL ESTATE, STOCK MARKET & CELEBRITY SOCIAL" LAYER ---
    r"\b(?:bán\s*nhà\s*chính\s*chủ|hạ\s*giá\s*hết\s*nấc|cắt\s*lỗ\s*sâu|vị\s*trí\s*đắc\s*địa|sổ\s*hồng\s*trao\s*tay|hỗ\s*trợ\s*vay\s*vốn|kinh\s*doanh\s*đắc\s*lợi|chủ\s*ngộp|thu\s*hồi\s*vốn)\b",
    r"\b(?:kết\s*thúc\s*phiên|sắc\s*xanh\s*lan\s*tỏa|sắc\s*đỏ\s*bao\s*trùm|v\s*n\s*index\s*quay\s*đầu|khối\s*ngoại\s*bán\s*ròng|thanh\s*khoản\s*sụt\s*giảm|nhóm\s*cổ\s*phiếu\s*vốn\s*hóa)\b",
    r"\b(?:khoe\s*dáng|xả\s*kho\s*ảnh|style\s*cực\s*chất|nhan\s*sắc\s*đời\s*thực|gây\s*sốt\s*với\s*bộ\s*ảnh|lộ\s*diện\s*sau\s*khi|phong\s*cách\s*thời\s*thượng|gu\s*thời\s*trang)\b",
    r"\b(?:mẹo\s*vặt\s*cuộc\s*sống|cách\s*chọn\s*mua|review\s*chân\s*thực|kinh\s*nghiệm\s*chọn|top\s*sản\s*phẩm\s*đáng\s*mua|hướng\s*dẫn\s*chi\s*tiết|bí\s*quyết\s*làm)\b",
    r"\b(?:định\s*giá\s*tài\s*sản|kê\s*biên\s*tài\s*sản|thu\s*hồi\s*nợ|tín\s*dụng\s*đen|vay\s*tiền\s*nhanh|lãi\s*suất\s*thả\s*nổi|đảo\s*nợ)\b",

    # --- THE "GOLD, CURRENCY & HEALTH BUREAUCRACY" LAYER ---
    r"\b(?:giá\s*vàng\s*hôm\s*nay|vàng\s*miếng\s*sjc|vàng\s*nhẫn|tỷ\s*giá\s*trung\s*tâm|đồng\s*u\s*s\s*d|euro|yên\s*nhật|bảng\s*anh|ngoại\s*tệ|vàng\s*thế\s*giới)\b",
    r"\b(?:tiêm\s*chủng\s*mở\s*rộng|vắc\s*xin\s*phòng\s*bệnh|lịch\s*tiêm\s*chủng|phác\s*đồ\s*điều\s*trị|chẩn\s*đoán\s*hình\s*ảnh|xét\s*nghiệm\s*máu|điều\s*trị\s*nội\s*trú)\b",
    r"\b(?:bí\s*quyết\s*nấu\s*ăn|cách\s*làm\s*món|thực\s*đơn\s*gia\s*đình|món\s*ngon\s*cuối\s*tuần|review\s*quán\s*ăn|ẩm\s*thực\s*đường\s*phố|văn\s*hóa\s*ẩm\s*thực)\b",

    # --- THE "GLOBAL SUMMITS, DEEP INVESTIGATION & NICHE SPORTS" LAYER ---
    r"\b(?:hội\s*nghị\s* thượng\s*đỉnh|G7|G20|ASEAN|APEC|UNESCO|WHO|UNICEF|WTO|NATO|liên\s*hợp\s*quốc|nghị\s*quyết\s*chung|tuyên\s*bố\s*chung)\b",
    r"\b(?:khám\s*nghiệm\s*tử\s*thi|pháp\s*y|hung\s* khí|tang\s*vật\s*vụ\s*án|hồ\s*sơ\s*vụ\s* án|lệnh\s*truy\s*nã|nghi\s*phạm\s*đang\s*bỏ\s*trốn|chứng\s*cứ\s*quan\s*trọng)\b",
    r"\b(?:x\s*s\s*m\s*b|x\s*s\s*m\s*n|x\s*s\s*m\s*t|mega\s*6/45|power\s*6/55|max\s*3d|giải\s*jackpot|kết\s*quả\s*xổ\s*số\s*hôm\s*nay)\b",
    r"\b(?:golf|mma|ufc|boxing|muay\s*thai|billiards|bi-a|võ\s*tự\s*do|sàn\s*đấu\s*rực\s*lửa|thu\s*phục|hạ\s*gục\s*đối\s*thủ)\b",
    r"\b(?:bạch\s*dương|kim\s*ngưu|song\s*tử|cự\s*giải|sư\s*tử|xử\s*nữ|thiên\s*bình|thiên\s*yết|hổ\s*cáp|nhân\s*mã|ma\s*kết|bảo\s*bình|song\s*ngư)\b",

    # --- THE "ACADEMIC EXCELLENCE, GENEALOGY & PROFESSIONAL MACHINERY" LAYER ---
    r"\b(?:chỉ\s*số\s*h-index|trích\s*dẫn\s*khoa\s*học|bài\s*báo\s*quốc\s*tế|phản\s*biện\s*kín|hội\s*đồng\s*chức\s*danh\s*giáo\s*sư|hệ\s*số\s*tác\s*động|impact\s*factor)\b",
    r"\b(?:gia\s*phả|nhà\s*thờ\s*họ|giỗ\s*tổ|tộc\s*ước|đại\s*hội\s*dòng\s*họ|con\s*cháu\s*hậu\s*duệ|phụng\s*thờ\s*tổ\s*tiên|lăng\s*mộ\s*dòng\s*tộc)\b",
    r"\b(?:máy\s*c\s*n\s*c|máy\s*cắt\s*laser|máy\s*chấn|máy\s*tiện|máy\s*phay|dây\s*chuyền\s*tự\s*động\s*hóa|robot\s*công\s*nghiệp|vật\s*liệu\s*composit)\b",
    r"\b(?:thử\s*nghiệm\s*lâm\s*sàng|biện\s*pháp\s*can\s*thiệp|nội\s*soi\s*tiêu\s*hóa|chụp\s*m\s*r\s*i|cat\s*scan|sinh\s*thiết|kháng\s*sinh\s*đồ)\b",
    r"\b(?:đồng\s*tiền\s*cổ|tem\s*phi\s*luật|sưu\s*tầm\s*đồ\s*xưa|đồ\s*gốm\s*sứ|giá\s*trị\s*thẩm\s*mỹ|nghệ\s*nhuật\s*sắp\s*đặt)\b",

    # --- THE "INDUSTRIAL STANDARDS, SPECIALIZED INTERIOR & AGRICULTURAL TECH" LAYER ---
    r"\b(?:tiêu\s*chuẩn\s*tcvn|astm|iso\s*9001|hợp\s*chuẩn\s*hợp\s*quy|tiêu\s*chuẩn\s*kỹ\s*thuật|quy\s*trình\s*kiểm\s*định|giấy\s*phép\s*hoạt\s*động)\b",
    r"\b(?:gỗ\s*veneer|acrylic|mdf|laminate|sàn\s*gỗ\s*công\s*nghiệp|đồ\s*gỗ\s*nội\s*thất|phụ\s*kiện\s*tủ\s*bếp|đèn\s*led\s*trang\s*trí)\b",
    r"\b(?:thủy\s*canh|khí\s*canh|phân\s*bón\s*n\s*p\s*k|thuốc\s*bảo\s*vệ\s*thực\s*vật|giống\s*cây\s*lai|nuôi\s*cấy\s*mô|nhà\s*màng|nhà\s*lưới)\b",
    r"\b(?:vận\s*hành\s*quy\s*trình|tối\s*ưu\s*hệ\s*thống|tiết\s*kiệm\s*chi\s*phí|năng\s*suất\s*lao\s*động|quản\s*trị\s*chuỗi\s*cung\s*ứng)\b",
    r"\b(?:mã\s*vạch|qr\s*code|tem\s*truy\s*xuất|hệ\s*thống\s*erp|phần\s*mềm\s*quản\s*lý|số\s*hóa\s*doanh\s*nghiệp)\b",

    # --- THE DEFINITIVE FINAL LAYER: COMMODITIES, SPIRITUAL & MUSIC TECH ---
    r"\b(?:giá\s*heo\s*hơi|giá\s*cà\s*phê|giá\s*hồ\s*tiêu|giá\s*cao\s*su|giá\s*sầu\s*riêng|thương\s*lá\s*thu\s*mua|vào\s*vụ\s*thu\s*hoạch|vựa\s*trái\s*cây)\b",
    r"\b(?:tam\s*tai|năm\s*tuổi|sao\s*kế\s*đô|vận\s*hạn|cúng\s*giải\s*hạn|hóa\s*giải\s*vận\s*đen|phong\s*thủy\s*cải\s*vận|tử\s*vi\s*trọn\s*đời)\b",
    r"\b(?:vóc\s*dáng|sắc\s*vóc|đường\s*cong|eo\s*thon|bí\s*quyết\s*giữ\s*dáng|thời\s*trang\s*thảm\s*đỏ|vẻ\s*đẹp\s*không\s*tuổi)\b",
    r"\b(?:lời\s*bài\s*hát|lyrics|hợp\s*âm\s*guitar|tab\s*piano|phòng\s*thu\s*âm|kỹ\s*thuật\s*thanh\s*nhạc|nhạc\s*cụ\s*chính\s*hãng|vang\s*số|loa\s*kéo)\b",
    r"\b(?:vneid|tài\s*khoản\s*mức\s*2|nộp\s*phạt\s*online|dịch\s*vụ\s*công\s*trực\s*tuyến|cổng\s*dịch\s*vụ\s*công)\b",

    # --- THE "HOUSEHOLD UTILITIES, LOCAL TRADING & CIVIC CLUBS" LAYER ---
    r"\b(?:sửa\s*chữa\s*điện\s*nước|thông\s*tắc\s*bể\s*phốt|hút\s*hầm\s*cầu|thay\s*vòi\s*nước|lắp\s*đặt\s*camera|bảo\s*trì\s*điều\s*hòa|vệ\s*sinh\s*máy\s*giặt)\b",
    r"\b(?:thanh\s*lý\s*giá\s*rẻ|xả\s*kho\s*nghỉ\s*bán|giày\s*si\s*tuyển|đồ\s*cũ\s*giá\s*tốt|thu\s*mua\s*phế\s*liệu|đồng\s*nát|vựa\s*ve\s*chai|đổi\s*cũ\s*lấy\s*mới)\b",
    r"\b(?:hội\s*người\s*cao\s*tuổi|hội\s*cựu\s*chiến\s*binh|đại\s*hội\s*chi\s*hội|phong\s*trào\s*văn\s*nghệ|khiêu\s*vũ\s*dưỡng\s*sinh|câu\s*lạc\s*bộ\s*hưu\s*trí)\b",
    r"\b(?:mật\s*ong\s*rừng|rau\s*sạch\s*nhà\s*trồng|nấm\s*linh\s*chi|nhân\s*sâm|đông\s*trùng\s*hạ\s*thảo|phòng\s*tràn\s*lan\s*đột\s*biến|cây\s*cảnh\s*giá\s*trị)\b",
    r"\b(?:hướng\s*dẫn\s*đăng\s*ký|thủ\s*tục\s*sang\s*tên|cấp\s*đổi\s*số\s*đỏ|đính\s*chính\s*thông\s*tin|tra\s*cứu\s*quy\s*hoạch|hồ\s*sơ\s*địa\s*chính)\b",

    # --- THE "MACRO-ECONOMICS, TAX BUREAUCRACY & HIGH-TECH HOBBIES" LAYER ---
    r"\b(?:chống\s*bán\s*phá\s*giá|thuế\s*tự\s*vệ|biện\s*pháp\s*phòng\s*vệ\s*thương\s*mại|fta|evfta|cptpp|rcep|quy\s*tắc\s*xuất\s*xứ|phòng\s*thương\s*mại)\b",
    r"\b(?:quyết\s*toán\s*thuế|thuế\s*thu\s*nhập\s*cá\s*nhân|tncn|hoàn\s*thuế\s*gtgt|hóa\s*đơn\s*điện\s*tử|kiểm\s*toán\s*nhà\s*nước|vụ\s*ngân\s*sách|kế\s*hoạch\s*tài\s*chính)\b",
    r"\b(?:công\s*nghệ\s*nano|vật\s*lý\s*lượng\s*tử|máy\s*tính\s*lượng\s*tử|vật\s*liệu\s*siêu\s*dẫn|graphene|in\s*3d|chế\s*tạo\s*nhanh|vi\s*mạch\s*bán\s*dẫn)\b",
    r"\b(?:bàn\s*phím\s*cơ|keycap|switch|lube\s*phím|hi-fi|dac/amp|đĩa\s*than|bút\s*máy|mực\s*viết\s*máy|sưu\s*tầm\s*bút|ngòi\s*bút|viết\s*lách)\b",
    r"\b(?:đhđcđ|bải\s*miễn\s*hđqt|thành\s*viên\s*độc\s*lập|nhà\s*đầu\s*tư\s*chiến\s*lược|m&a|sáp\s*nhập\s*doanh\s*nghiệp)\b",

    # --- THE "GLOBAL SPORTS, FANDOMS & LIFESTYLE INSPIRATION" LAYER ---
    r"\b(?:real\s*madrid|man\s*utd|manchester\s*city|liverpool|arsenal|barca|bayern\s*munich|psg|chuyển\s*nhượng\s*cầu\s*thủ|hợp\s*đồng\s*bom\s*tấn| champions\s*league|premiere\s*league)\b",
    r"\b(?:nhạc\s*trẻ|k-pop|v-pop|show\s*diễn|lưu\s*diễn\s*quốc\s*tế|world\s*tour|lightstick|comeback\s*ấn\s*tượng|debut\s*thành\s*công|bảng\s*xếp\s*hạng\s*âm\s*nhạc)\b",
    r"\b(?:tự\s*do\s*tài\s*chính|thu\s*nhập\s*thụ\s*động|khai\s*phá\s*tiềm\s*năng|vùng\s*an\s*toàn|chữa\s*lành\s*tâm\s*hồn|thiền\s*định\s*mỗi\s*ngày)\b",
    r"\b(?:cắt\s*mí|botox|trẻ\s*hóa\s*làn\s*da|spa\s*làm\s*đẹp|viện\s*thẩm\s*mỹ)\b",
    r"\b(?:luyện\s*thi\s*ielts|toeic|toefl|ngữ\s*pháp\s*tiếng\s*anh|học\s*từ\s*vựng|phương\s*pháp\s*ghi\s*nhớ|du\s*học\s*sinh|trao\s*đổi\s*sinh\s*viên)\b",

    # --- THE "DIGITAL CONTENT, INFLUENCER MARKETING & URBAN PLANNING" LAYER ---
    r"\b(?:phát\s*trực\s*tiếp|kol|koc|người\s*có\s*sức\s*ảnh\s*hưởng|viral\s*clip|drama\s*mới|bóc\s*phốt|hóng\s*biến|đu\s*trend|thử\s*thách\s*24h)\b",
    r"\b(?:cryptocurrency|sàn\s*giao\s*dịch\s*số|n\s*f\s*t|vốn\s*hóa\s*thị\s*trường\s*số|công\s*nghệ\s*chuỗi\s*khối)\b",
    r"\b(?:nghị\s*quyết\s*hđqt|biên\s*bản\s*họp|chương\s*trình\s*nghị\s*sự|quy\s*hoạch\s*phân\s*khu|điều\s*chỉnh\s*quy\s*hoạch|chủ\s*trương\s*đầu\s*tư|thẩm\s*định\s*giá\s*tài\s*sản|nghĩa\s*vụ\s*thuế)\b",
    r"\b(?:định\s*hướng\s*phát\s*triển|tầm\s*nhìn\s*2030|chiến\s*lược\s*phát\s*triển|chuyển\s*đổi\s*số\s*vận\s*hành|hệ\s*sinh\s*thái\s*khởi\s*nghiệp)\b",
    r"\b(?:tuyên\s*truyền\s*phổ\s*biến|giáo\s*dục\s*pháp\s*luật|hưởng\s*ứng\s*phong\s*trào|tổng\s*kết\s*khen\s*thưởng|khen\s*ngợi\s*biểu\s*dương)\b",

    # --- THE "SOCIAL DRAMA, CYBER-SECURITY & QUALITY STANDARDS" LAYER ---
    r"\b(?:mẹ\s*chồng\s*nàng\s*dâu|tiểu\s*tam|giật\s*chồng|sống\s*thử|ly\s*hôn\s*nghìn\s*tỷ|tranh\s*chấp\s*quyền\s*nuôi\s*con|mâu\s*thuẫn\s*gia\s*đình|ngoại\s*tình\s*bị\s*phát\s*hiện)\b",
    r"\b(?:lừa\s*đảo\s*chiếm\s*đoạt|mã\s*độc\s*tấn\s*công|phần\s*mềm\s*gián\s*điệp|ransomware|truy\s*cập\s*trái\s*phép|an\s*toàn\s*thông\s*tin\s*mạng|bảo\s*mật\s*đa\s*lớp|xác\s*thực\s*hai\s*yếu\s*tố)\b",
    r"\b(?:dịch\s*bệnh\s*gia\s*súc|lở\s*mồm\s*long\s*móng|tai\s*xanh|dịch\s*tả\s*lợn\s*châu\s*phi|thuốc\s*thú\s*y|kháng\s*sinh\s*cho\s*vật\s*nuôi|thức\s*ăn\s*chăn\s*nuôi|kỹ\s*thuật\s*vỗ\s*béo)\b",
    r"\b(?:vietgap|globalgap|haccp|chỉ\s*dẫn\s*địa\s*lý|thương\s*hiệu\s*quốc\s*gia|ocop|mỗi\s*xã\s*một\s*sản\s*phẩm)\b",
    r"\b(?:đăng\s*ký\s*thương\s*hiệu|sở\s*hữu\s*công\s*nghiệp|kiểu\s*dáng\s*độc\s*quyền|sách\s*trắng|báo\s*cáo\s*thường\s*niên|đại\s*hội\s*thành\s*viên|vốn\s*góp)\b",

    # --- THE "STATE ANNIVERSARIES, SPECIALIZED LIFESTYLE & VR TECHNICALS" LAYER ---
    r"\b(?:kỷ\s*niệm\s*\d+\s*năm\s*thành\s*lập|ngày\s*truyền\s*thống|đại\s*hội\s*đại\s*biểu|văn\s*kiện\s*đại\s*hội|báo\s*cáo\s*chính\s*trị|lễ\s*báo\s*công|viếng\s*lăng\s*chủ\s*tịch|dâng\s*hương\s*tưởng\s*niệm)\b",
    r"\b(?:thực\s*tế\s*ảo|v\s*r|a\s*r|metaverse|thị\s*kính|tay\s*cầm\s*điều\s*khiển|không\s*gian\s*số\s*3d|mô\s*phỏng\s*hình\s*ảnh|kính\s*thông\s*minh)\b",
    r"\b(?:nhịn\s*ăn\s*gián\s*đoạn|chế\s*độ\s*ăn\s*keto|thực\s*phẩm\s*bảo\s*vệ\s*sức\s*khỏe|vi\s*chất\s*dinh\s*dưỡng|eo\s*thon\s*dáng\s*đẹp)\b",
    r"\b(?:huấn\s*luyện\s*chó|trại\s*chó\s*giống|thú\s*cưng\s*độc\s*lạ|phục\s*chế\s*xe\s*cổ|độ\s*xe\s*chuyên\s*nghiệp|hệ\s*thống\s*âm\s*thanh\s*analog|băng\s*cối|âm\s*thanh\s*trung\s*thực)\b",
    r"\b(?:triển\s*khai\s*nghị\s*quyết|quán\s*triệt\s*tư\s*tưởng|vận\s*động\s*quần\s*chúng|xây\s*dựng\s*nông\s*thôn\s*mới|phong\s*trào\s*toàn\s*dân|đoàn\s*kết\s*xây\s*dựng\s*đời\s*sống)\b",

    # --- THE "SOCIAL CEREMONIES, CLICKBAIT & PERSONAL FINANCE" LAYER ---
    r"\b(?:lễ\s*ăn\s*hỏi|rước\s*dâu|tiệc\s*cưới|mừng\s*thọ|lễ\s*vu\s*lan|phật\s*đản|phục\s*sinh|quà\s*tặng\s*ý\s*nghĩa|lời\s*chúc\s*hay)\b",
    r"\b(?:sự\s*thật\s*ít\s*ai\s*biết|cảnh\s*báo\s*từ\s*chuyên\s*gia|giải\s*quyết\s*dứt\s*điểm|dấu\s*hiệu\s*nhận\s*biết|lời\s*khuyên\s*từ\s*bác\s*sĩ|phương\s*pháp\s*tự\s*nhiên|thông\s*tin\s*sai\s*lệch|kiểm\s*chứng\s*sự\s*thật)\b",
    r"\b(?:tất\s*toán\s*tài\s*khoản|đáo\s*hạn\s*thẻ|phí\s*duy\s*trì|hạn\s*mức\s*thanh\s*toán|bảo\s*hiểm\s*nhân\s*thọ|quyền\s*lợi\s*bảo\s*hiểm|người\s*được\s*thụ\s*hưởng|bồi\s*thường\s*hợp\s*đồng)\b",
    r"\b(?:ưu\s*đãi\s*độc\s*quyền|giảm\s*giá\s*sốc|khuyến\s*mãi\s*khủng|giờ\s*vàng\s*giá\s*tốt|quà\s*tặng\s*hấp\s*dẫn|số\s*lượng\s*có\s*hạn|đặt\s*hàng\s*ngay|freeship)\b",
    r"\b(?:xử\s*phạt\s*vi\s*phạm\s*hành\s*chính|tạm\s*giữ\s*phương\s*tiện|nồng\s*độ\s*cồn|vi\s*phạm\s*tốc\s*độ|phí\s*đường\s*bộ)\b",

    # --- THE "HOUSEHOLD MAINTENANCE, INTERNATIONAL SPORTS & HIGH-END ANTIQUES" LAYER ---
    r"\b(?:sửa\s*bình\s*nóng\s*lạnh|chống\s*thấm\s*dột|sửa\s*mái\s*tôn|thông\s*tắc\s*cống|hút\s*bể\s*phốt|vệ\s*sinh\s*điều\s*hòa|bảo\s*dưỡng\s*máy\s*giặt|lắp\s*mạng\s*internet)\b",
    r"\b(?:n\s*b\s*a|m\s*l\s*b|n\s*f\s*l|super\s*bowl|grand\s*slam|wimbledon|roland\s*garros|u\s*s\s*open|australian\s*open|giải\s*quần\s*vợt|bóng\s*rổ\s*nhà\s*nghề)\b",
    r"\b(?:christie's|sotheby's|nhà\s*đấu\s*giá\s*danh\s*tiếng|tranh\s*sơn\s*mài|khảm\s*tam\s*khí|gỗ\s*thủy\s*tùng|trầm\s*hương\s*tự\s*nhiên|kỳ\s*nam|mộc\s*hương|đồ\s*gỗ\s*mỹ\s*nghệ)\b",
    r"\b(?:phần\s*mềm\s*kế\s*toán|phần\s*mềm\s*nhân\s*sự|quản\s*lý\s*kho\s*hàng|tối\s*ưu\s*vận\s*hành|giải\s*pháp\s*doanh\s*nghiệp|năng\s*suất\s*vượt\s*trội)\b",
    r"\b(?:chương\s*trình\s*liên\s*kết\s*đào\s*tạo|trao\s*bằng\s*tốt\s*nghiệp|lễ\s*khai\s*giảng\s*năm\s*học|hiệu\s*trưởng\s*nhà\s*trường|phòng\s*giáo\s*dục\s*đào\s*tạo)\b",

    # --- THE "SOCIAL CELEBRATIONS, RETAIL HOLIDAYS & PC HARDWARE" LAYER ---
    r"\b(?:lễ\s*tân\s*gia|vàng\s*cưới|phong\s*bì\s*mừng|lễ\s*dạm\s*ngõ|tiệc\s*thôi\s*nôi|đầy\s*tháng|kỷ\s*niệm\s*ngày\s*cưới|đội\s*bê\s*tráp)\b",
    r"\b(?:black\s*friday|cyber\s*monday|lazada\s*birthday|shopee\s*sale|siêu\s*sale\s*\d+/\d+|ngày\s*hội\s*mua\s*sắm|mã\s*giảm\s*giá|hoàn\s*tiền\s*max)\b",
    r"\b(?:gaslighting|mối\s*quan\s*hệ\s*độc\s*hại|trầm\s*cảm\s*sau\s*sinh|rối\s*loạn\s*lo\s*âu|liệu\s*pháp\s*tâm\s*lý|tư\s*vấn\s*trị\s*liệu)\b",
    r"\b(?:linh\s*kiện\s*máy\s*tính|card\s*đồ\s*họa|r\s*t\s*x|g\s*t\s*x|r\s*a\s*m|s\s*s\s*d|ổ\s*cứng\s*di\s*động|nguồn\s*máy\s*tính|tản\s*nhiệt\s*nước)\b",
    r"\b(?:thời\s*điểm\s*vàng|cơ\s*hội\s*có\s*một\s*không\s*hai|nhận\s*ngay\s*ưu\s*đãi|đừng\s*bỏ\s*lỡ|đăng\s*ký\s*ngay)\b",

    # --- THE "SPIRITUAL TOURISM, LUXURY WATCHES & MODERN WORK CULTURE" LAYER ---
    r"\b(?:du\s*lịch\s*tâm\s*linh|hành\s*hương|chùa\s*tam\s*chúc|bái\s*đính|đại\s*nam|quần\s*thể\s*danh\s*thắng|di\s*tích\s*tâm\s*linh|khu\s*nghỉ\s*dưỡng\s*sinh\s*thái)\b",
    r"\b(?:rolex|patek\s*philippe|audemars\s*piguet|hublot|omega|thương\s*hiệu\s*đồng\s*hồ|mặt\s*số|bộ\s*chuyển\s*động|trữ\s*cót|phiên\s*bản\s*giới\s*hạn)\b",
    r"\b(?:burnout|quiet\s*quitting|work-life\s*balance|hybrid\s*work|chảy\s*máu\s*chất\s*xám|nhân\s*sự\s*chủ\s*chốt|môi\s*trường\s*làm\s*việc\s*lý\s*tưởng)\b",
    r"\b(?:ngành\s*công\s*nghiệp\s*f&b|xu\s*hướng\s*tiêu\s*dùng|chuỗi\s*cung\s*ứng\s*toàn\s*cầu|chi\s*phí\s*vận\s*hành|ký\s*kết\s*hợp\s*tác)\b",
    r"\b(?:oecd|brics|asml|t\s*s\s*m\s*c|nvidia|apple\s*intelligence|openai|chatgpt|mô\s*hình\s*ngôn\s*ngữ\s*lớn|l\s*l\s*m)\b",

    # --- THE "LUXURY MARINE, PRIVATE AVIATION & PROFESSIONAL ETHICS" LAYER ---
    r"\b(?:du\s*thuyền\s*hạng\s*sang|princess\s*yachts|sunseeker|viking\s*yachts|bến\s*du\s*thuyền|hàng\s*không\s*tư\s*nhân|chuyên\s*cơ\s*riêng|gulfstream|bombardier)\b",
    r"\b(?:đoàn\s*luật\s*sư|liên\s*đoàn\s*luật\s*sư|quy\s*tắc\s*đạo\s*đức\s*nghề\s*nghiệp|kỷ\s*luật\s*luật\s*sư|tư\s*vấn\s*pháp\s*lý\s*doanh\s*nghiệp|hợp\s*quy\s*pháp\s*luật)\b",
    r"\b(?:dòng\s*vốn\s*ngoại|chu\s*kỳ\s*kinh\s*tế|điểm\s*đảo\s*chiều|lạm\s*phát\s*mục\s*tiêu|nới\s*lỏng\s*tiền\s*tệ|thắt\s*chặt\s*chi\s*tiêu|ngân\s*sách\s*quốc\s*gia)\b",
    r"\b(?:phụ\s*gia\s*thực\s*phẩm|chất\s*bảo\s*quản|tiêu\s*chuẩn\s*vệ\s*sinh\s*kỹ\s*thuật)\b",
    r"\b(?:định\s*hướng\s*giáo\s*dục\s*mầm\s*non|phương\s*pháp\s*montessori|reggio\s*emilia|steam|giáo\s*dục\s*trải\s*nghiệm)\b",

    # --- THE "TRADITIONAL ARTS, AGRICULTURE SCIENCE & I.P. WARS" LAYER ---
    r"\b(?:cải\s*lương|hát\s*tuồng|hát\s*chèo|dân\s*ca\s*quan\s*họ|đờn\s*ca\s*tài\s*tử|văn\s*hóa\s*phi\s*vật\s*thể|nghệ\s*thuật\s*truyền\s*thống|nghệ\s*nhân\s*nhân\s*dân)\b",
    r"\b(?:phân\s*bón\s*lá|kỹ\s*thuật\s*chiết\s*cành|ghép\s*mắt|cây\s*ăn\s*trái|vườn\s*cây\s*ăn\s*quả|năng\s*suất\s*vụ\s*mùa|phòng\s*trừ\s*sâu\s*bệnh)\b",
    r"\b(?:tranh\s*chấp\s*bản\s*quyền|vi\s*phạm\s*sáng\s*chế|kiện\s*tụng\s*bằng\s*sáng\s*chế|tác\s*quyền\s*âm\s*nhạc|v\s*c\s*p\s*m\s*c|độc\s*quyền\s*thương\s*hiệu)\b",
    r"\b(?:thẩm\s*định\s*viên|đấu\s*giá\s*viên|công\s*chứng\s*viên|thừa\s*phát\s*lại|văn\s*phòng\s*luật|hành\s*nghề\s*y\s*dược)\b",
    r"\b(?:tiêu\s*chuẩn\s*ngành|quy\s*chuẩn\s*kỹ\s*thuật|nghiệm\s*thu\s*hoàn\s*thành|bàn\s*giao\s*công\s*trình|nhà\s*thầu\s*phụ|liên\s*danh\s*nhà\s*thầu)\b",

    # --- THE "SPACE, GEOPOLITICS & OLYMPIC SPORTS" LAYER ---
    r"\b(?:blue\s*origin|tên\s*lửa\s*đẩy\s*(?!\s*tấn\s*công)|vệ\s*tinh\s*viễn\s*thông|trạm\s*vũ\s*trụ|thiên\s*văn\s*học|kính\s*viễn\s*vọng)\b",
    r"\b(?:lệnh\s*trừng\s*phạt|cấm\s*vận\s*kinh\s*tế|phong\s*tỏa\s*tài\s*sản\s*quốc\s*tế|trừng\s*phạt\s*ngoại\s*giao|trục\s*xuất\s*nhà\s*ngoại\s*giao|quan\s*hệ\s*song\s*phương)\b",
    r"\b(?:olympic|asiad|paragames|đại\s*hội\s*thể\s*thao|huấn\s*luyện\s*viên\s*trưởng|đội\s*tuyển\s*quốc\s*gia|liên\s*đoàn\s*bóng\s*đá|v\s*f\s*f)\b",
    r"\b(?:đua\s*thuyền|rowing|canoeing|đấu\s*kiếm|fencing|cử\s*tạ|bắn\s*súng|thể\s*dục\s*dụng\s*cụ|aerobic|điền\s*kinh|nhảy\s*cao|nhảy\s*xa)\b",
    r"\b(?:kỷ\s*lục\s*thế\s*giới|kỷ\s*lục\s*quốc\s*gia|huy\s*chương\s*vàng|huy\s*chương\s*bạc|huy\s*chương\s*đồng|bảng\s*tổng\s*sắp|phá\s*kỷ\s*lục)\b",

    # --- THE "SMALL BUSINESS, INTL BANKING & MICROBIAL TECH" LAYER ---
    r"\b(?:chủ\s*hộ\s*kinh\s*doanh|mã\s*số\s*thuế|giấy\s*phép\s*kinh\s*doanh|thanh\s*tra\s*thuế|hộ\s*kinh\s*doanh\s*cá\s*thể|phí\s*môn\s*bài)\b",
    r"\b(?:swift|l/c|tín\s*dụng\s*thư|nhờ\s*thu\s*chứng\s*từ|thanh\s*toán\s*quốc\s*tế|rửa\s*tiền|trốn\s*thuế|thiên\s*đường\s*thuế|kiểm\s*toán\s*độc\s*lập)\b",
    r"\b(?:vi\s*khuẩn\s*hp|tụ\s*cầu\s*vàng|liên\s*cầu\s*khuẩn|e\s*coli|kháng\s*thuốc|phòng\s*thí\s*nghiệm|nuôi\s*cấy\s*vi\s*sinh|kỹ\s*thuật\s*di\s*truyền)\b",
    r"\b(?:hậu\s*kỳ\s*ảnh|lightroom|chỉnh\s*màu\s*cinematic|dải\s*tương\s*phản|dynamyc\s*range|loa\s*kiểm\s*âm|tai\s*nghe\s*chống\s*ồn|hi-res\s*audio)\b",
    r"\b(?:ban\s*liên\s*lạc|hội\s*đồng\s*ngũ|cựu\s*giáo\s*chức|hội\s*khuyến\s*học|tri\s*ân\s*thầy\s*cô|kỷ\s*niệm\s*ngày\s*ra\s*trường|họp\s*lớp)\b",

    # --- THE "HISTORICAL HERITAGE, MENTAL HEALTH & LOGISTICS" LAYER ---
    r"\b(?:hoàng\s*thành\s*thăng\s*long|cố\s*đô\s*huế|thánh\s*địa\s*mỹ\s*sơn|vịnh\s*hạ\s*long|di\s*tích\s*lịch\s*sử\s*cấp\s*quốc\s*gia|khu\s*di\s*tích|trùng\s*tu\s*di\s*tích)\b",
    r"\b(?:liệu\s*pháp\s*cbt|trị\s*liệu\s*tâm\s*lý|tham\s*vấn\s*tâm\s*thần|sang\s*chấn|lo\s*âu|rối\s*loạn\s*nhân\s*cách|giải\s*mã\s*giấc\s*mơ|tiềm\s*thức)\b",
    r"\b(?:giao\s*hàng\s*tiết\s*kiệm|giao\s*hàng\s*nhanh|viettel\s*post|v\s*n\s*post|mã\s*vận\s*đơn|chuyển\s*phát\s*nhanh|phí\s*ship|thu\s*hộ\s*cod|tra\s*cứu\s*đơn\s*hàng)\b",
    r"\b(?:kết\s*cấu\s*thép|hệ\s*thống\s*m\s*e\s*p|tòa\s*nhà\s*xanh|chứng\s*chỉ\s*leed|thiết\s*kế\s*kháng\s*chấn|vật\s*liệu\s*xây\s*dựng\s*mới|công\s*nghệ\s*bê\s*tông)\b",
    r"\b(?:tiêu\s*chuẩn\s*ngành\s*y|hành\s*nghề\s*khám\s*chữa\s*bệnh|kỷ\s*luật\s*vi\s*phạm|tận\s*tâm\s*phục\s*vụ|thầy\s*thuốc\s*nhân\s*dân)\b",

    # --- THE "CONSUMER BRANDS, FAST FOOD & PARENTING METHODS" LAYER ---
    r"\b(?:l'oreal|estee\s*lauder|shiseido|lancome|laneige|innisfree|sk-ii|mỹ\s*phẩm\s*chính\s*hãng|son\s*môi|kem\s*dưỡng\s*da|chu\s*trình\s*skincare)\b",
    r"\b(?:mcdonald's|kfc|lotteria|pizza\s*hut|starbucks|highlands\s*coffee|phúc\s*long|trà\s*sữa\s*topping|thực\s*đơn\s*nhanh|món\s*mới\s*ra\s*mắt)\b",
    r"\b(?:ăn\s*dặm\s*kiểu\s*nhật|ăn\s*dặm\s*blw|rèn\s*con\s*tự\s*lập|khủng\s*hoảng\s*tuổi\s*lên\s*ba|mẹ\s*bỉm\s*sữa|chọn\s*bỉm\s*sữa|sữa\s*công\s*thức|phát\s*triển\s*chiều\s*cao)\b",
    r"\b(?:công\s*nghệ\s*hầm\s*dìm|nhịp\s*dây\s*văng|cáp\s*dự\s*ứng\s*lực|gối\s*cầu|khe\s*co\s*giãn|hầm\s*xuyên\s*núi|công\s*trình\s*trọng\s*điểm|thông\s*xe\s*kỹ\s*thuật)\b",
    r"\b(?:món\s*hời|áp\s*mã\s*giảm\s*giá|đổ\s*xô\s*mua\s*sắm|tình\s*trạng\s*cháy\s*hàng|vỡ\s*trận\s*vì\s*khuyến\s*mãi)\b",

    # --- THE "HERITAGE ARTS, PET CARE & LEGAL FORMALITIES" LAYER ---
    r"\b(?:xòe\s*thái|cồng\s*chiêng|tây\s*nguyên|ca\s*trù|hát\s*xoan|đàn\s*đá|trình\s*diễn\s*nghệ\s*thuật)\b",
    r"\b(?:trị\s*bệnh\s*cho\s*chó\s*mèo|tiêm\s*phòng\s*dại|phối\s*giống\s*thú\s*cưng|thức\s*ăn\s*hạt|cát\s*vệ\s*sinh|phòng\s*khám\s*thú\s*y|spa\s*thú\s*cưng)\b",
    r"\b(?:điều\s*khoản\s*bất\s*khả\s*kháng|ủy\s*quyền\s*đại\s*diện|phụ\s*lục\s*hợp\s*đồng|thanh\s*lý\s*hợp\s*đồng|phát\s*mại\s*tài\s*sản|tố\s*tụng\s*trọng\s*tài|tòa\s*án\s*kinh\s*tế)\b",
    r"\b(?:thẩm\s*định\s*giá|đấu\s*giá\s*tài\s*sản|kê\s*biên|thu\s*về\s*ngân\s*sách|nghĩa\s*vụ\s*tài\s*chính)\b",
    r"\b(?:bồi\s*dưỡng\s*nghiệp\s*vụ|tập\s*huấn\s*kỹ\s*năng)\b",

    # --- THE "CRAFT VILLAGES, HEAVY MACHINERY & CRIMINAL REFINEMENT" LAYER ---
    r"\b(?:bát\s*tràng|vạn\s*phúc|sa\s*đéc|đại\s*bái|làng\s*nghề|sản\s*phẩm\s*thủ\s*công)\b",
    r"\b(?:cần\s*trục\s*tháp|xe\s*lu\s*rung|máy\s*xúc\s*bánh\s*xích|máy\s*ủi|xe\s*cẩu\s*tự\s*hành|vận\s*hành\s*máy\s*móc|bảo\s*trì\s*công\s*nghiệp)\b",
    r"\b(?:án\s*treo|giảm\s*nhẹ\s*hình\s*phạt|hành\s*vi\s*phạm\s*tội|đồng\s*phạm|chủ\s*mưu|tang\s*vật|hồ\s*sơ\s*vụ\s*án|phiên\s*tòa\s*xét\s*xử)\b",
    r"\b(?:quyết\s*định\s*khởi\s*tố|lệnh\s*tạm\s*giam|phiên\s*phúc\s*thẩm)\b",
    r"\b(?:số\s*hóa|chuyển\s*đổi\s*số|hệ\s*sinh\s*thái|khởi\s*nghiệp\s*sáng\s*tạo|vón\s*đầu\s*tư|quỹ\s*mạo\s*hiểm)\b",

    # --- THE FINAL POLISH: FASHION, MICRO-FINANCE & EDUCATIONAL ADMIN ---
    r"\b(?:phong\s*cách\s*thời\s*trang|mốt\s*mới\s*nhất|phối\s*đồ|mix\s*đồ|phụ\s*kiện\s*đi\s*kèm|lookbook|sưu\s*tập\s*mùa\s*hè|trình\s*diễn\s*thời\s*trang)\b",
    r"\b(?:lãi\s*suất\s*huy\s*động|tiết\s*kiệm\s*tại\s*quầy|app\s*ngân\s*hàng|quẹt\s*thẻ|thanh\s*toán\s*không\s*tiền\s*mặt|voucher\s*giảm\s*giá)\b",
    r"\b(?:văn\s*bằng\s*hai|đào\s*tạo\s*từ\s*xa|chứng\s*chỉ\s*ngắn\s*hạn|học\s*phần|tín\s*chỉ|đăng\s*ký\s*môn\s*học|phòng\s*đào\s*tạo|khoa\s*chuyên\s*môn)\b",
    r"\b(?:trao\s*tặng\s*kỷ\s*niệm\s*chương|huy\s*hiệu\s*đảng|khen\s*thưởng\s*đột\s*xuất|phong\s*trào\s*thi\s*đua|gương\s*người\s*tốt\s*việc\s*tốt|điển\s*hình\s*tiên\s*tiến)\b",
    r"\b(?:mẹo\s*chăm\s*sóc|bí\s*quyết\s*làm\s*đẹp|tự\s*nhiên\s*tại\s*nhà|cẩm\s*nang\s*sức\s*khỏe|phương\s*pháp\s*khoa\s*học|chế\s*độ\s*dinh\s*dưỡng)\b",

    # --- THE "FUTURE TECH, BIO-MEDICINE & PRESTIGE AWARDS" LAYER ---
    r"\b(?:năng\s*lượng\s*nhiệt\s*hạch|fusion\s*energy|du\s*lịch\s*vũ\s*trụ|virgin\s*galactic|thám\s*hiểm\s*sao\s*hỏa|định\s*cư\s*vũ\s*trụ)\b",
    r"\b(?:crispr|chỉnh\s*sửa\s*gen|liệu\s*pháp\s*tế\s*bào\s*gốc|miễn\s*dịch\s*trị\s*liệu|phác\s*đồ\s*ung\s*thư|y\s*học\s*tái\s*tạo)\b",
    r"\b(?:sao\s*vàng\s*đất\s*việt|hàng\s*việt\s*nam\s*chất\s*lượng\s*cao|giải\s*thưởng\s*tạ\s*quang\s*bửu|giải\s*vin\s*future|giải\s*thưởng\s*nhà\s*nước)\b",
    r"\b(?:chương\s*trình\s*mục\s*tiêu\s*quốc\s*gia|đô\s*thị\s*văn\s*minh|gia\s*đình\s*văn\s*hóa)\b",
    r"\b(?:kiểm\s*tra\s*chuyên\s*ngành|thanh\s*tra\s*hành\s*chính|xử\s*phạt\s*vi\s*phạm|niêm\s*yết\s*công\s*khai|lấy\s*ý\s*kiến\s*nhân\s*dân)\b",

    # --- THE "CRAFTSMANSHIP, AROMATHERAPY & METRO ENGINEERING" LAYER ---
    r"\b(?:khảm\s*xà\s*cừ|mây\s*tre\s*đan|đúc\s*đồng|nghệ\s*thuật\s*chạm\s*khắc|sản\s*phẩm\s*mỹ\s*nghệ|tinh\s*hoa\s*di\s*sản)\b",
    r"\b(?:liệu\s*pháp\s*âm\s*thanh|aromatherapy|trị\s*liệu\s*mùi\s*hương|nước\s*hoa\s*niche|tầng\s*hương|độ\s*lưu\s*hương|tinh\s*dầu\s*thiên\s*nhiên|thư\s*giãn\s*tâm\s*hồn)\b",
    r"\b(?:đường\s*ray|khổ\s*đường\s*tiêu\s*chuẩn|nhà\s*ga\s*trên\s*cao|tàu\s*điện\s*ngầm|m\s*e\s*t\s*r\s*o|vận\s*hành\s*chạy\s*thử|hệ\s*thống\s*tín\s*hiệu\s*đường\s*sắt)\b",
    r"\b(?:chủ\s*trương\s*đại\s*hội|văn\s*kiện\s*quy\s*hoạch|đề\s*án\s*phát\s*triển|nguồn\s*lực\s*số|hạ\s*tầng\s*viễn\s*thông|phủ\s*sóng\s*5\s*g)\b",
    r"\b(?:xây\s*dựng\s*đội\s*ngũ|nâng\s*cao\s*năng\s*lực|đào\s*tạo\s*nguồn\s*nhân\s*lực|chính\s*sách\s*đãi\s*ngộ|môi\s*trường\s*chuyên\s*nghiệp)\b",

    # --- THE "CUSTOMS TECHNICALS, LAND DISPUTES & ENERGY GRID" LAYER ---
    r"\b(?:mã\s*h\s*s|chứng\s*nhận\s*xuất\s*xứ|c\s*o|tờ\s*khai\s*hải\s*quan|thông\s*quan\s*hàng\s*hóa|cước\s*vận\s*tải\s*biển|tàu\s*container|logistics\s*chuyên\s*dụng)\b",
    r"\b(?:tranh\s*chấp\s*quyền\s*sử\s*dụng\s*đất|thừa\s*kế\s*theo\s*pháp\s*luật|di\s*chúc\s*hợp\s*pháp|hợp\s*đồng\s*ủy\s*quyền|công\s*chứng\s*tư\s*pháp|thi\s*hành\s*án\s*dân\s*sự)\b",
    r"\b(?:đường\s*dây\s*500kv|trạm\s*biến\s*áp|điều\s*độ\s*hệ\s*thống\s*điện|điện\s*mặt\s*trời\s*mái\s*nhà|dppa|mua\s*bán\s*điện\s*trực\s*tiếp)\b",
    r"\b(?:độc\s*quyền\s*phân\s*phối|nhượng\s*quyền\s*thương\s*mại|franchise|chiến\s*dịch\s*marketing|định\s*vị\s*thị\s*trường)\b",
    r"\b(?:phê\s*duyệt\s*quy\s*hoạch|nguồn\s*vốn\s*o\s*d\s*a|giải\s*ngân\s*vốn\s*đầu\s*tư|tiến\s*độ\s*dự\s*án|tổng\s*mức\s*đầu\s*tư)\b",

    # --- THE OMNIBUS: HISTORICAL DYNASTIES, ARCHAEOLOGY & SPECIALIZED SPORTS ---
    r"\b(?:nhà\s*đinh|nhà\s*tiền\s*lê|nhà\s*lý|nhà\s*trần|nhà\s*hồ|nhà\s*mạc|nhà\s*tây\s*sơn|nhà\s*nguyễn|chế\s*độ\s*phong\s*kiến|chiều\s*đại\s*lịch\s*sử)\b",
    r"\b(?:hiện\s*vật\s*trưng\s*bày|bảo\s*tàng\s*lịch\s*sử|khai\s*quật\s*di\s*chỉ|di\s*vật\s*quý\s*hiếm|trùng\s*tu\s*tôn\s*tạo)\b",
    r"\b(?:bắn\s*cung|đua\s*xe\s*đạp|bowling|trượt\s*băng|khiêu\s*vũ\s*thể\s*thao|dancesport|thể\s*dục\s*nghệ\s*thuật|vovinam|karatedo|taekwondo|wushu)\b",
    r"\b(?:đăng\s*ký\s*thanh\s*toán|kiểm\s*tra\s*số\s*dư|biến\s*động\s*số\s*dư|lịch\s*sử\s*giao\s*dịch|sao\s*kê\s*tài\s*khoản|chuyển\s*tiền\s*nhanh\s*24/7)\b",
    r"\b(?:xem\s*ngày\s*tốt|giờ\s*hoàng\s*đạo|hướng\s*xuất\s*hành|khai\s*trương\s*hồng\s*phát|văn\s*khấn\s*cổ\s*truyền|mâm\s*cỗ\s*cúng\s*rằm)\b",

    # --- THE FINAL FINAL CATCH-ALL: VIRAL TRENDS, GEN Z SLANG & LEGAL ADMIN ---
    r"\b(?:flex\s*đến\s*hơi\s*thở\s*cuối|check-in\s*sang\s*chảnh|k\s*o\s*ls|k\s*o\s*cs|gen\s*z|thế\s*hệ\s*alpha|slay|vibe\s*cực\s*chỉnh|đu\s*idol|vô\s*tri|thao\s*túng\s*tâm\s*lý)\b",
    r"\b(?:biên\s*bản\s*vi\s*phạm\s*hành\s*chính|quyết\s*định\s*xử\s*phạt|hình\s*thức\s*tăng\s*nặng|tình\s*tiết\s*giảm\s*nhẹ|cưỡng\s*thế\s*thi\s*hành|khiếu\s*nại\s*tố\s*cáo|tranh\s*chấp\s*hành\s*chính)\b",
    r"\b(?:hệ\s*thống\s*phân\s*phối\s*bán\s*lẻ|chuỗi\s*cửa\s*hàng\s*tiện\s*lợi|siêu\s*thị\s*mini|trải\s*nghiệm\s*khách\s*hàng|cơ\s*hội\s*hợp\s*tác\s*kinh\s*doanh|phát\s*triển\s*đại\s*lý)\b",
    r"\b(?:khóa\s*học\s*online\s*miễn\s*phí|hội\s*thảo\s*trực\s*tuyến|webinar|đào\s*tạo\s*kỹ\s*năng\s*mềm|chứng\s*chỉ\s*hoàn\s*thành|học\s*bổng\s*khuyến\s*học)\b",
    r"\b(?:hướng\s*dẫn\s*thủ\s*tục|cấp\s*đổi\s*giấy\s*phép|tra\s*cứu\s*thông\s*tin|cổng\s*thông\s*tin\s*điện\s*tử|dịch\s*vụ\s*công\s*mức\s*độ\s*4|thủ\s*tục\s*một\s*cửa)\b",

    # --- THE "HISTORICAL WAR HISTORY, HEAVY WEAPONRY & AIRPORT TECHNICALS" LAYER ---
    r"\b(?:sư\s*đoàn|trung\s*đoàn|lữ\s*đoàn|tiểu\s*đoàn|quân\s*chủng|tiêm\s*kích|tàu\s*sân\s*bay|tên\s*lửa\s*đạn\s*đạo|tàu\s*ngầm|tác\s*chiến\s*điện\s*tử|chiến\s*lược\s*quân\s*sự)\b",
    r"\b(?:lịch\s*sử\s*kháng\s*chiến|tội\s*ác\s*chiến\s*tranh|di\s*tích\s*chiến\s*trường|tìm\s*kiếm\s*đồng\s*đội|huân\s*chương\s*chiến\s*công)\b",
    r"\b(?:đường\s*băng|sân\s*đỗ|nhà\s*ga\s*hành\s*khách|cảng\s*hàng\s*không|phí\s*sân\s*bay|dịch\s*vụ\s*mặt\s*đất|kiểm\s*soát\s*viên\s*không\s*lưu|an\s*ninh\s*hàng\s*không)\b",
    r"\b(?:chương\s*trình\s*khuyến\s*mãi|hành\s*trình\s*bay|vé\s*máy\s*bay\s*giá\s*rẻ|giờ\s*bay|đăng\s*ký\s*trực\s*tuyến|check-in\s*online|phòng\s*chờ\s*hạng\s*thương\s*gia)\b",
    r"\b(?:quy\s*tắc\s*đạo\s*đức|hành\s*vi\s*ứng\s*xử|văn\s*hóa\s*gia\s*đình|giá\s*trị\s*cốt\s*lõi|phẩm\s*chất\s*đạo\s*đức|lối\s*sống\s*lành\s*mạnh|thể\s*dục\s*thể\s*thao)\b",

    # --- THE "APPLIANCE TECHNICALS, VETERAN GROUPS & ELITE SPORTS AWARDS" LAYER ---
    r"\b(?:mã\s*lỗi\s*điều\s*hòa|lỗi\s*e\s*1|lỗi\s*e\s*2|lỗi\s*f\s*5|bảng\s*mã\s*lỗi|sửa\s*bình\s*nóng\s*lạnh\s*tại\s*nhà|thông\s*tắc\s*bể\s*phốt\s*giá\s*rẻ)\b",
    r"\b(?:hội\s*cựu\s*thanh\s*niên\s*xung\s*phong|ban\s*liên\s*lạc\s*bạn\s*chiến\s*đấu|hội\s*hỗ\s*trợ\s*gia\s*đình\s*liệt\s*sĩ|quỹ\s*nghĩa\s*tình\s*đồng\s*đội|tri\s*ân\s*anh\s*hùng)\b",
    r"\b(?:quả\s*bóng\s*vàng|ballon\s*d'or|chiếc\s*giày\s*vàng|golden\s*boot|the\s*best|cầu\s*thủ\s*xuất\s*sắc\s*nhất|đội\s*hình\s*tiêu\s*biểu|quản\s*lý\s*thể\s*thao)\b",
    r"\b(?:dầm\s*chuyển|cột\s*biên|bể\s*nước\s*mái|hệ\s*thống\s*thang\s*máy|phòng\s*cháy\s*chữa\s*cháy\s*kỹ\s*thuật|nghiệm\s*thu\s*pccc)\b",
    r"\b(?:nâng\s*cao\s*hiệu\s*quả|công\s*nghệ\s*tiên\s*tiến|giải\s*pháp\s*toàn\s*diện|đối\s*tác\s*tin\s*cậy)\b",

    # --- THE "TEXTILES, FAMILY LAW & INTERNAL GOVERNANCE" LAYER ---
    r"\b(?:lụa\s*tơ\s*tằm|thổ\s*cẩm|dệt\s*may\s*xuất\s*khẩu|sợi\s*tự\s*nhiên|ngành\s*may\s*mặc|thiết\s*kế\s*thời\s*trang)\b",
    r"\b(?:hàng\s*thừa\s*kế|phân\s*chia\s*tài\s*sản|tranh\s*chấp\s*hôn\s*nhân|quyền\s*nuôi\s*con|án\s*phí\s*dân\s*sự|hòa\s*giải\s*cơ\s*sở)\b",
    r"\b(?:quy\s*chế\s*hoạt\s*động|nội\s*quy\s*cơ\s*quan|cải\s*cách\s*thủ\s*tục|một\s*cửa\s*liên\s*thông|hiện\s*đại\s*hóa\s*hành\s*chính| kỷ\s*luật\s*công\s*vụ)\b",
    r"\b(?:lò\s*cao|luyện\s*kim|phôi\s*thép|cán\s*nóng|cán\s*nguội|hợp\s*kim\s*đặc\s*biệt|ngành\s*công\s*nghiệp\s*nặng|khai\s*thác\s*khoáng\s*sản)\b",
    r"\b(?:hướng\s*dẫn\s*áp\s*dụng|quy\s*định\s*chi\s*tiết|thông\s*tư\s*hướng\s*dẫn|nghị\s*định\s*sửa\s*đổi|có\s*hiệu\s*lực\s*thi\s*hành)\b",

    # --- THE "PARTY ADMIN, ADVANCED LOGISTICS & MEGA-PROJECT TECH" LAYER ---
    r"\b(?:đại\s*hội\s*chi\s*bộ|ban\s*chấp\s*hành|tiền\s*phong\s*gương\s*mẫu|kiểm\s*điểm\s*tự\s*phê\s*bình|phát\s*triển\s*đảng\s*viên|kết\s*nạp\s*đảng)\b",
    r"\b(?:logistics\s*ngược|kho\s*thông\s*minh|cảng\s*cạn\s*icd|hệ\s*thống\s*w\s*m\s*s|vận\s*tải\s*đa\s*phương\s*thức|chuỗi\s*cung\s*ứng\s*bền\s*vững|tối\s*ưu\s*chặng\s*cuối)\b",
    r"\b(?:tàu\s*cao\s*tốc\s*bắc\s*nam|khổ\s*đường\s*1435mm|tốc\s*đế\s*thiết\s*kế\s*350km/h|siêu\s*dự\s*án|khả\s*năng\s*thông\s*qua|tải\s*trọng\s*trục|hành\s*lang\s*kinh\s*tế)\b",
    r"\b(?:cấp\s*phép\s*xây\s*dựng|quy\s*hoạch\s*chi\s*tiết\s*1/500|mật\s*độ\s*xây\s*dựng|hệ\s*số\s*sử\s*dụng\s*đất|giải\s*phóng\s*mặt\s*bằng|đền\s*bù\s*tái\s*định\s*cư)\b",
    r"\b(?:nâng\s*cao\s*chất\s*lượng|đổi\s*mới\s*toàn\s*diện|phát\s*triển\s*bền\s*vững|nguồn\s*nhân\s*lực\s*chất\s*lượng\s*cao|kinh\s*tế\s*tri\s*thức|công\s*nghiệp\s*4.0)\b",

    # --- THE "JOURNALISM SECTIONS, EXPERT COLUMNS & METRO HUB TECH" LAYER ---
    r"\b(?:hỏi\s*đáp\s*pháp\s*luật|tư\s*vấn\s*sức\s*khỏe|chuyện\s*lạ\s*đó\s*đây|tiêu\s*điểm\s*dư\s*luận|góc\s*nhìn\s*chuyên\s*gia|tiếng\s*nói\s*cử\s*tri|báo\s*chí\s*điều\s*tra|phóng\s*sự\s*dài\s*kỳ)\b",
    r"\b(?:ga\s*ngầm|đào\s*hầm\s*bằng\s*robot\s*tbm|đốt\s*hầm\s*dìm|lồng\s*hầm|phương\s*pháp\s*đào\s*hở|thi\s*công\s*ngầm|kết\s*cấu\s*chịu\s*lực|địa\s*chất\s*công\s*trình)\b",
    r"\b(?:chương\s*trình\s*nghị\s*sự\s*quốc\s*tế|tuyên\s*bố\s*hành\s*động|cam\s*kết\s*khí\s*hậu|net\s*zero|chuyển\s*đổi\s*năng\s*lượng|tín\s*chỉ\s*carbon|phát\s*triển\s*xanh)\b",
    r"\b(?:dự\s*thảo\s*quy\s*tắc|lấy\s*ý\s*kiến\s*phản\s*hồi|đánh\s*giá\s*tác\s*động|thẩm\s*định\s*độc\s*lập|đo\s*lường\s*chỉ\s*số\s*kpi)\b",
    r"\b(?:nâng\s*tầm\s*vị\s*thế|khẳng\s*định\s*thương\s*hiệu|vươn\s*tầm\s*thế\s*giới|ghi\s*danh\s*bản\s*đồ|kết\s*nối\s*toàn\s*cầu)\b",

    # --- THE "GLOBAL ICONS, TECH TITANS & SUBMARINE CABLE TECH" LAYER ---
    r"\b(?:taylor\s*swift|eras\s*tour|messi|lionel\s*messi|ronaldo|cristiano\s*ronaldo|mbappe|haaland|neymar|giải\s*thưởng\s*grammy|oscar)\b",
    r"\b(?:putin|tập\s*cận\s*bình|elon\s*musk|mark\s*zuckerberg|bill\s*gates|jeff\s*bezos|tỷ\s*phú\s*forbes|giàu\s*nhất\s*thế\s*giới)\b",
    r"\b(?:tuyến\s*cáp\s*aag|apg|ia|smw3|sự\s*cố\s*đứt\s*cáp|đường\s*truyền\s*quốc\s*tế|bảo\s*trì\s*hệ\s*thống|trạm\s*cập\s*bờ)\b",
    r"\b(?:thị\s*trường\s*chuyển\s*nhượng|hợp\s*đồng\s*kỷ\s*lục|ngôi\s*sao\s*bóng\s*đá|vòng\s*loại\s*world\s*cup|champion\s*league)\b",
    r"\b(?:chiến\s*dịch\s*quảng\s*cáo|đại\s*sứ\s*thương\s*hiệu|tính\s*năng\s*độc\s*đáo|cập\s*nhật\s*phiên\s*bản)\b",

    # --- THE "CINEMA FESTIVALS, LABOR LAW & WIND POWER ENGINEERING" LAYER ---
    r"\b(?:liên\s*hoan\s*phim|l\s*h\s*p|cannes|venice|berlin|bông\s*sen\s*vàng|cánh\s*diều\s*vàng|đạo\s*diễn\s*xuất\s*sắc|biên\s*kịch|vai\s*diễn|sân\s*khấu\s*kịch)\b",
    r"\b(?:tranh\s*chấp\s*lao\s*động|sa\s*thải\s*trái\s*luật|hợp\s*đồng\s*lao\s*động|bảo\s*hiểm\s*thất\s*nghiệp|đình\s*công|lương\s*thưởng)\b",
    r"\b(?:turbine\s*gió|cánh\s*quạt\s*phong\s*điện|điện\s*gió\s*ngoài\s*khơi|móng\s*cọc\s*biển|năng\s*lượng\s*tái\s*tạo|quy\s*hoạch\s*điện\s*viii|giá\s*feed-in\s*tariff)\b",
    r"\b(?:nghiên\s*cứu\s*độc\s*lập|kết\s*quả\s*khảo\s*sát|số\s*liệu\s*thống\s*kê|độ\s*tin\s*cậy|phương\s*pháp\s*nghiên\s*cứu|phân\s*tích\s*dữ\s*liệu)\b",
    r"\b(?:nâng\s*cao\s*trình\s*độ|đào\s*tạo\s*chuyên\s*sâu|kỹ\s*năng\s*thời\s*đại\s*số)\b",

    # --- THE "GASTRONOMY TECH, FOOD SCIENCE & PROFESSIONAL ACCOUNTING" LAYER ---
    r"\b(?:kỹ\s*thuật\s*nấu\s*nướng|lên\s*men\s*tự\s*nhiên|vi\s*sinh\s*thực\s*phẩm|hương\s*liệu\s*nhân\s*tạo|an\s*toàn\s*vệ\s*sinh|chuỗi\s*cung\s*ứng\s*lạnh)\b",
    r"\b(?:gian\s*lận\s*thuế|quyết\s*toán\s*kế\s*toán|chứng\s*từ\s*kế\s*toán|nghiệp\s*vụ\s*tài\s*chính|kế\s*toán\s*trưởng)\b",
    r"\b(?:hồ\s*sơ\s*pháp\s*lý|thủ\s*tục\s*hành\s*chính|giải\s*ngân\s*vốn)\b",
    r"\b(?:văn\s*hóa\s*đọc|ngày\s*hội\s*sách|ra\s*mắt\s*tác\s*phẩm|độc\s*giả|tác\s*giả|nhà\s*xuất\s*bản|phê\s*bình\s*văn\s*học|di\s*sản\s*chữ\s*viết)\b",
    r"\b(?:liên\s*kết\s*vùng|tầm\s*nhìn\s*quy\s*hoạch|động\s*lực\s*tăng\s*trưởng|kinh\s*tế\s*số|chuyển\s*đổi\s*xanh|bền\s*vững)\b",

    # --- THE "FAMILY RITUALS, CRAFT VILLAGES & SOCIAL WELFARE" LAYER ---
    r"\b(?:ban\s*lễ\s*tang|cáo\s*phó|gia\s*đình\s*báo\s*tin|thành\s*kính\s*phân\s*ưu|vòng\s*hoa\s*viếng|di\s*nguyện)\b",
    r"\b(?:gốm\s*chu\s*đậu|gốm\s*phù\s*lãng|đúc\s*đồng\s*ngũ\s*xã|tranh\s*đông\s*hồ|tranh\s*hàng\s*trống|ngôi\s*làng\s*cổ|nghệ\s*nhân\s*truyền\s*thống)\b",
    r"\b(?:công\s*tác\s*xã\s*hội|quỹ\s*từ\s*thiện|vận\s*động\s*quyên\s*góp|nhà\s*hảo\s*tâm|mạnh\s*thường\s*quân|trao\s*quà\s*tình\s*nghĩa|xóa\s*đói\s*giảm\s*nghèo)\b",
    r"\b(?:vách\s*kính\s*unitized|hệ\s*stick|tấm\s*alu|lam\s*chắn\s*nắng|mặt\s*dựng|kết\s*cấu\s*bao\s*che|vật\s*liệu\s*hoàn\s*thiện|trang\s*trí\s*ngoại\s*thất)\b",
    r"\b(?:phấn\s*đấu\s*hoàn\s*thành|vượt\s*kế\s*hoạch|thi\s*đua\s*lập\s*thành\s*tích|chào\s*mừng\s*kỷ\s*niệm|biểu\s*dương\s*khen\s*thưởng|gương\s*sáng)\b",

    # --- THE "PEST MANAGEMENT, TEXTILE VILLAGES & BANKRUPTCY LAW" LAYER ---
    r"\b(?:rầy\s*nâu|sâu\s*cuốn\s*lá|ốc\s*bươu\s*vàng|bệnh\s*đạo\s*ôn|phun\s*thuốc\s*trừ\s*sâu|bảo\s*vệ\s*mùa\s*màng|an\s*toàn\s*sinh\s*học)\b",
    r"\b(?:lụa\s*nha\s*xá|thổ\s*cẩm\s*mỹ\s*nghiệp|chạm\s*bạc\s*đồng\s*xâm|đá\s*mỹ\s*nghệ\s*non\s*nước|tinh\s*hoa\s*đất\s*nghề)\b",
    r"\b(?:phá\s*sản\s*doanh\s*nghiệp|giải\s*thế|mở\s*thủ\s*tục\s*phá\s*sản|quản\s*tài\s*viên|danh\s*sách\s*chủ\s*nợ|tuyên\s*bố\s*phá\s*sản|nợ\s*quá\s*hạn)\b",
    r"\b(?:máy\s*xúc\s*đào|dung\s*tích\s*gầu|bán\s*kính\s*đào|hệ\s*thống\s*thủy\s*lực|bảo\s*trì\s*máy\s*móc|vật\s*tư\s*thi\s*công|thiết\s*bị\s*công\s*trình)\b",
    r"\b(?:tăng\s*cường\s*quản\s*lý|siết\s*chặt\s*kỷ\s*cương|nâng\s*cao\s*trách\s*nhiệm|kiểm\s*tra\s*giám\s*sát|xử\s*lý\s*nghiêm\s*vi\s*phạm|đúng\s*quy\s*định)\b",

    # --- THE "ARTISAN VILLAGES, JUDICIARY DEEP & CORPORATE STRATEGY" LAYER ---
    r"\b(?:sơn\s*mài\s*hạ\s*thái|tạc\s*tượng\s*sơn\s*đồng|mây\s*tre\s*đan\s*phú\s*vinh|nghệ\s*nhân\s*đúc\s*đồng|triển\s*lãm\s*mỹ\s*thuật)\b",
    r"\b(?:viện\s*kiểm\s*sát\s*nhân\s*dân\s*tối\s*cao|tòa\s*án\s*nhân\s*dân\s*tối\s*cao|kháng\s* nghị|giám\s*đốc\s*thẩm|tái\s*thẩm|tố\s*tụng|án\s*lệ)\b",
    r"\b(?:chiến\s*lược\s*tăng\s*trưởng|mô\s*hình\s*kinh\s*doanh|mở\s*rộng\s*thị\s*trường|huy\s*động\s*vốn|thị\s*phần|doanh\s*thu)\b",
    r"\b(?:hệ\s*thống\s*pháp\s*luật|văn\s*bản\s*quy\s*phạm|luật\s*sửa\s*đổi|bổ\s*sung|quy\s*định\s*hướng\s*dẫn|nghị\s*định\s*chính\s*phủ|nghị\s*quyết\s*quốc\s*hội)\b",
    r"\b(?:cách\s*mạng\s*công\s*nghiệp|khởi\s*nghiệp|quỹ\s*đầu\s*tư)\b",

    # --- THE "MILITARY HISTORY, MUSEUM TECH & NATIONAL TRADITIONS" LAYER ---
    r"\b(?:trận\s*bạch\s*đằng|chi\s*lăng|điện\s*biên\s*phủ|nghệ\s*thuật\s*quân\s*sự|lịch\s*sử\s*vẻ\s*vang|hào\s*khí\s*dân\s*tộc|truyền\s*thống\s*yêu\s*nước)\b",
    r"\b(?:súng\s*trường|pháo\s*tự\s*hành|xe\s*thiết\s*giáp|trực\s*thăng\s*vũ\s*trang|tên\s*lửa\s*hành\s*trình|tác\s*chiến\s*không\s*gian|an\s*ninh\s*quốc\s*phòng)\b",
    r"\b(?:trưng\s*bày\s*bảo\s*tàng|phục\s*chế\s*số|hiện\s*vật\s*gốc|không\s*gian\s*triển\s*lãm|thuyết\s*minh\s*viên|khách\s*tham\s*quan|di\s*sản\s*thế\s*giới)\b",
    r"\b(?:hệ\s*lõi\s*cứng|outrigger|belt\s*truss|giằng\s*cột|móng\s*vây|tường\s*vây|cọc\s*baryte)\b",
    r"\b(?:tuyên\s*đương\s*điển\s*hình|người\s*tốt\s*việc\s*tốt|huy\s*hiệu\s*cao\s*quý|giải\s*thưởng\s*danh\s*giá)\b",

    # --- THE "DEEP SEA, SATELLITE TECH & CONSTITUTIONAL LAW" LAYER ---
    r"\b(?:lặn\s*biển\s*sâu|tàu\s*ngầm\s*thám\s*hiểm|rãnh\s*mariana|sinh\s*vật\s*biển\s*lạ|thám\s*hiểm\s*đáy\s*đại\s*dương|khoa\s*học\s*đại\s*dương)\b",
    r"\b(?:vệ\s*tinh\s*địa\s*tĩnh|quỹ\s*đạo\s*thấp|trạm\s*điều\s*khiển\s*mặt\s*đất|băng\s*tần\s*viễn\s*thông|sóng\s*vô\s*tuyến|truyền\s*hình\s*số\s*vệ\s*tinh)\b",
    r"\b(?:hiến\s*pháp|pháp\s*lệnh|quyền\s*con\s*người|quyền\s*cơ\s*bản|bộ\s*máy\s*nhà\s*nước|đạo\s*luật\s*chuyên\s*ngành|nghị\s*quyết\s*liên\s*tịch)\b",
    r"\b(?:văn\s*hóa\s*ứng\s*xử|tri\s*thức\s*nhân\s*loại|di\s*sản\s*tư\s*tưởng|triết\s*lý\s*giáo\s*dục|phương\s*pháp\s*truyền\s*thống)\b",
    r"\b(?:nâng\s*cao\s*hiệu\s*lực|hiệu\s*quả\s*quản\s*lý|siết\s*chặt\s*kỷ\s*luật|tăng\s*cường\s*giám\s*sát|xử\s*lý\s*nghiêm\s*sai\s*phạm)\b",

    # --- THE "GEMSTONES, SPACE MISSIONS & PROPERTY LAW" LAYER ---
    r"\b(?:đá\s*quý\s*lục\s*yên|trang\s*sức\s*cao\s*cấp|vàng\s*bạc\s*đá\s*quý|kim\s*cương\s*nhân\s*tạo|đá\s*phong\s*thủy|ngọc\s*trai|p\s*n\s*j|d\s*o\s*j\s*i|s\s*j\s*c)\b",
    r"\b(?:artemis|apollo|voyager|james\s*webb|kính\s*viễn\s*vọng\s*hubble|sứ\s*mệnh\s*vũ\s*trụ|đổ\s*bộ\s*mặt\s*trăng|hành\s*tinh\s*xa\s*xôi)\b",
    r"\b(?:phân\s*chia\s*di\s*sản|khai\s*nhận\s*thừa\s*kế|hợp\s*đồng\s*tặng\s*cho|quyền\s*bề\s*mặt|tài\s*sản\s*chung|phân\s*chia\s*hậu\s*ly\s*hôn|nghĩa\s*vụ\s*cấp\s*dưỡng)\b",
    r"\b(?:tải\s*trọng\s*gió|dao\s*động\s*công\s*trình|hệ\s*thống\s*giảm\s*chấn|tuned\s*mass\s*damper|t\s*m\s*d|kháng\s*chấn|ổn\s*định\s*kết\s*cấu)\b",
    r"\b(?:chương\s*trình\s*hợp\s*tác|biên\s*bản\s*ghi\s*nhớ|ký\s*kết\s*thỏa\s*thuận|xúc\s*tiến\s*thương\s*mại)\b",

    # --- THE "CONSUMER COMMODITIES, SPORTS TECHNICALS & NATIONAL STRATEGY" LAYER ---
    r"\b(?:hàng\s*tiêu\s*dùng\s*nhanh|f\s*m\s*c\s*g|thực\s*phẩm\s*đóng\s*gói|thiết\s*bị\s*nhà\s*bếp|chuỗi\s*cửa\s*hàng\s*bán\s*lẻ|hàng\s*hóa\s*thiết\s*yếu)\b",
    r"\b(?:kỹ\s*thuật\s*giao\s*bóng|cú\s*đánh\s*trái\s*tay|chiến\s*thuật\s*phối\s*hợp|đường\s*chuyền\s*quyết\s*định|tình\s*huống\s*cố\s*định|việt\s*vị|trọng\s*tài\s*v\s*a\s*r|thẻ\s*đỏ)\b",
    r"\b(?:quy\s*hoạch\s*tổng\s*thể\s*quốc\s*gia|vùng\s*kinh\s*tế\s*trọng\s*điểm|liên\s*kết\s*tiểu\s*vùng|phân\s*bổ\s*nguồn\s*lực|tầm\s*nhìn\s*phát\s*triển)\b",
    r"\b(?:sức\s*nâng\s*tối\s*đa|tầm\s*với\s*cần\s*trực|cáp\s*tải|puly|móc\s*cẩu|tự\s*trọng|thông\s*số\s*kỹ\s*thuật\s*máy|bảo\s*trì\s*định\s*kỳ)\b",
    r"\b(?:tinh\s*thần\s*đoàn\s*kết|phát\s*huy\s*truyền\s*thống|thắng\s*lợi\s*vẻ\s*vang|nhiệm\s*vụ\s*trọng\s*tâm|nâng\s*cao\s*cảnh\s*giác|tối\s*ưu\s*hóa|quy\s*trình\s*khép\s*kín)\b",

    # --- THE "FAMILY LIFESTYLE, ZEN LIVING & TURBINE MAINTENANCE" LAYER ---
    r"\b(?:sống\s*khỏe\s*mỗi\s*ngày|góc\s*tâm\s*hồn|dành\s*cho\s*thiếu\s*nhi|phụ\s*nữ\s*và\s*gia\s*đình|góc\s*thư\s*giãn|tâm\s*sự\s*thầm\s*kín|hạnh\s*phúc\s*gia\s*đình)\b",
    r"\b(?:trang\s*trí\s*nhà\s*cửa|phong\s*thủy\s*phòng\s*ngủ|sắp\s*xếp\s*không\s*gian|tổ\s*ấm\s*gia\s*đình|nội\s*thất\s*tinh\s*tế|xu\s*hướng\s*màu\s*sắc|vật\s*liệu\s*bên\s*vững)\b",
    r"\b(?:hộp\s*số\s*turbine|hệ\s*thống\s*bôi\s*trơn|cảm\s*biến\s*rung\s*động|phần\s*mềm\s*scada|giám\s*sát\s*từ\s*xa|bảo\s*trì\s*dự\s*phòng|khắc\s*phục\s*lỗi\s*kỹ\s*thuật)\b",
    r"\b(?:quy\s*hoạch\s*ngành\s*du\s*lịch|phát\s*triển\s*kinh\s*tế\s*biển|liên\s*kết\s*vùng\s*kinh\s*tế|huy\s*động\s*nguồn\s*lực|xã\s*hội\s*hóa)\b",
    r"\b(?:tuyên\s*truyền\s*vận\s*động|phòng\s*chống\s*lãng\s*phí|thực\s*hành\s*tiết\s*kiệm|đẩy\s*mạnh\s*cải\s*cách|hiệu\s*quả\s*thi\s*hành)\b",

    # --- THE "REGIONAL SPECIALTIES, FINE PRODUCE & PROPERTY JARGON" LAYER ---
    r"\b(?:vải\s*thiều\s*lục\s*ngạn|nhãn\s*lồng\s*hưng\s*yên|rượu\s*cần\s*tây\s*nguyên|sâm\s*ngọc\s*linh|bưởi\s*năm\s*roi|xoài\s*cát\s*hòa\s*lộc|thương\s*hiệu\s*đặc\s*sản|vùng\s*trồng\s*tiêu\s*chuẩn)\b",
    r"\b(?:công\s*chứng\s*sang\s*tên|thuế\s*trước\s*bạ|phí\s*đăng\s*ký\s*biến\s*động|trích\s*lục\s*bản\s*đồ|giấy\s*xác\s*nhận\s*tình\s*trạng|thông\s*tin\s*quy\s*hoạch)\b",
    r"\b(?:xe\s*bơm\s*bê\s*tông|cần\s*bơm|áp\s*suất\s*bơm|vệ\s*sinh\s*đường\s*ống|trạm\s*trộn\s*bê\s*tông|phụ\s*gia\s*xây\s*dựng|nghiệm\s*thu\s*cốt\s*thép)\b",
    r"\b(?:phát\s*triển\s*nguồn\s*nhân\s*lực|đào\s*tạo\s*kỹ\s*năng|chứng\s*chỉ\s*nghề|giải\s*quyết\s*việc\s*làm|an\s*sinh\s*xã\s*hội|chính\s*sách\s*ưu\s*đãi)\b",
    r"\b(?:tăng\s*cường\s*hợp\s*tác|thúc\s*đẩy\s*đầu\s*tư|cạnh\s*tranh\s*sòng\s*phẳng)\b",

    # --- THE "HERITAGE MEDIA, PHILANTHROPY & CRANE ENGINEERING" LAYER ---
    r"\b(?:khám\s*phá\s*thế\s*giới|hành\s*trình\s*di\s*sản|cửa\s*sổ\s*tâm\s*hồn|những\s*tấm\s*lòng\s*vàng|lời\s*hay\s*ý\s*đẹp|gương\s*sáng\s*quanh\s*ta)\b",
    r"\b(?:vận\s*động\s*tài\s*trợ|trao\s*tặng\s*nhà\s*tình\s*nghĩa|quỹ\s*bảo\s*trợ|trợ\s*giúp\s*nhân\s*đạo|chương\s*trình\s*thiện\s*nguyện|tấm\s*lòng\s*hảo\s*tâm)\b",
    r"\b(?:toa\s*quay|tay\s*cần|khối\s*đối\s*trọng|dầm\s*gốc|lồng\s*nâng|đốt\s*thân\s*cần\s*trục|hệ\s*thống\s*phanh\s*hãm|vận\s*hành\s*an\s*toàn)\b",
    r"\b(?:thu\s*hút\s*vốn\s*f\s*d\s*i|môi\s*trường\s*đầu\s*tư|ưu\s*đãi\s*ngân\s*sách|vốn\s*vốn\s*đầu\s*tư\s*công|giải\s*ngân|tiến\s*độ\s*xây\s*lắp)\b",
    r"\b(?:tăng\s*cường\s*kiểm\s*tra|giám\s*sát\s*xử\s*lý|đúng\s*trình\s*tự|pháp\s*luật\s*hiện\s*hành)\b",

    # --- THE "REGIONAL SWEETS, CIVIL STATUS & SOLAR TECH" LAYER ---
    r"\b(?:bánh\s*đậu\s*xanh|chè\s*tân\s*cương|kẹo\s*cu\s*đơ|bánh\s*pía|mè\s*xửng|thương\s*hiệu\s*truyền\s*thống|nghệ\s*nhân\s*vị\s*nguyên)\b",
    r"\b(?:đăng\s*ký\s*kết\s*hôn|xác\s*nhận\s*độc\s*thân|thay\s*đổi\s*hộ\s*tịch|trích\s*lục\s*bản\s*sao|công\s*dân\s*số)\b",
    r"\b(?:hiệu\s*suất\s*quang\s*điện|i\s*n\s*v\s*e\s*r\s*t\s*e\s*r|hệ\s*thống\s*lưu\s*trữ|pin\s*mặt\s*trời|vệ\s*sinh\s*tấm\s*pin|bảo\s*trì\s*điện\s*mặt\s*trời|hotspot)\b",
    r"\b(?:chương\s*trình\s*liên\s*kết|hợp\s*tác\s*đào\s*tạo|nghiên\s*cứu\s*khoa\s*học|công\s*bố\s*quốc\s*tế)\b",
    r"\b(?:phong\s*trào\s*thể\s*thao|giải\s*chạy\s*marathon|phong\s*trào\s*cơ\s*sở|nâng\s*cao\s*sức\s*khỏe|vận\s*động\s*toàn\s*dân)\b",

    # --- THE "HERBAL SPECIALTIES, ADOPTION LAW & EXPORT LOGISTICS" LAYER ---
    r"\b(?:hành\s*tỏi\s*lý\s*sơn|quế\s*trà\s*bồng|hồi\s*lạng\s*sơn|tiêu\s*chư\s*sê|hạt\s*điều\s*bình\s*phước|đặc\s*sản\s*tiêu\s*biểu|nguyên\s*liệu\s*quý|vùng\s*nguyên\s*liệu)\b",
    r"\b(?:nhận\s*con\s*nuôi|cha\s*mẹ\s*nuôi|thủ\s*tục\s*nhận\s*nuôi|quyền\s*và\s*nghĩa\s*vụ|xác\s*nhận\s*nuôi\s*dưỡng|đăng\s*ký\s*nuôi\s*con\s*nuôi|pháp\s*luật\s*hôn\s*nhân)\b",
    r"\b(?:xuất\s*khẩu\s*chính\s*ngạch|tiểu\s*ngạch|ủy\s*thác\s*xuất\s*khẩu|thủ\s*tục\s*hải\s*quan|logistics\s*xuất\s*khẩu|chứng\s*nhận\s*kiểm\s*dịch|quota\s*thuế\s*quan)\b",
    r"\b(?:cảm\s*biến\s*áp\s*suất|bộ\s*điều\s*khiển\s*logic|plc|hệ\s*thống\s*mạng\s*công\s*nghiệp|truyền\s*thông\s*modbus|giám\s*sát\s*số|tối\s*ưu\s*quy\s*trình)\b",
    r"\b(?:chương\s*trình\s*hành\s*động|nghị\s*quyết\s*đại\s*hội|đẩy\s*mạnh\s*thi\s*đua|hoàn\s*thành\s*xuất\s*sắc|nhân\s*rộng\s*mô\s*hình)\b",

    # --- THE "SEAFOOD SPECIALTIES, NATIONALITY LAW & GLOBAL VISAS" LAYER ---
    r"\b(?:mực\s*một\s*nắng|tôm\s*hùm\s*bình\s*ba|cua\s*cà\s*mau|sò\s*huyết\s*ô\s*loan|chả\s*mực\s*hạ\s*long|đặc\s*sản\s*biển|đánh\s*bắt\s*xa\s*bờ|hải\s*sản\s*tươi\s*sống)\b",
    r"\b(?:nhập\s*quốc\s*tịch|thôi\s*quốc\s*tịch|việt\s*kiều|thị\s*thực\s*điện\s*tử|e-visa|hộ\s*chiếu\s*phổ\s*thông|người\s*nước\s*ngoài\s*tại\s*việt\s*nam|định\s*cư)\b",
    r"\b(?:quy\s*tắc\s*phòng\s*cháy|thiết\s*bị\s*cứu\s*hỏa|chuông\s*báo\s*cháy|vòi\s*phun\s*tự\s*động|thang\s*thoát\s*hiểm)\b",
    r"\b(?:tinh\s*thần\s*khởi\s*nghiệp|chương\s*trình\s*vườn\s*ươm\s*tạo|hỗ\s*trợ\s*doanh\s*nghiệp|đối\s*mới\s*sáng\s*tạo|vốn\s*đầu\s*tư\s*mạo\s*hiểm|angel\s*investor)\b",
    r"\b(?:quy\s*định\s*pháp\s*luật)\b",

    # --- THE "TRADITIONAL DRINKS, LEGAL AID & EXPORT STANDARDS" LAYER ---
    r"\b(?:rượu\s*mẫu\s*sơn|rượu\s*gò\s*công|bia\s*hơi\s*hà\s*nội|cà\s*phê\s*robusta|cà\s*phê\s*arabica|trà\s*tà\s*xùa|thương\s*hiệu\s*đồ\s*uống|vùng\s*nguyên\s*liệu\s*chè)\b",
    r"\b(?:trợ\s*giúp\s*pháp\s*lý|luật\s*sư\s*chỉ\s*định|miễn\s*phí\s*dịch\s*vụ|hỗ\s*trợ\s*pháp\s*luật|tư\s*vấn\s*pháp\s*lý\s*lưu\s*động|phổ\s*biến\s*giáo\s*dục\s*pháp\s*luật)\b",
    r"\b(?:tiêu\s*chuẩn\s*xuất\s*khẩu|chứng\s*chỉ\s*chất\s*lượng\s*iso|rào\s*cản\s*kỹ\s*thuật|thông\s*quan\s*hàng\s*hóa\s*tại\s*cửa\s*khẩu|chứng\s*nhận\s*nguồn\s*gốc)\b",
    r"\b(?:thang\s*máy\s*tốc\s*độ\s*cao|phòng\s*máy\s*thang\s*máy|hệ\s*thống\s*điều\s*khiển\s*tầng|cửa\s*tầng\s*tự\s*động)\b",
    r"\b(?:tuyên\s*dương\s*điển\s*hình|nghị\s*quyết|quY\s*định)\b",

    # --- THE "FLORICULTURE, LEGAL LIABILITY & SMART BUILDING" LAYER ---
    r"\b(?:hoa\s*đào\s*nhật\s*tân|hoa\s*mai\s*bình\s*định|lan\s*đột\s*biến|trầm\s*hương|cây\s*cảnh\s*bonsai|nghệ\s*thuật\s*tạo\s*hình\s*cây|triển\s*lãm\s*sinh\s*vật\s*cảnh)\b",
    r"\b(?:trách\s*nhiệm\s*nghề\s*nghiệp|bảo\s*hiểm\s*trách\s*nhiệm|vi\s*phạm\s*đạo\s*đức\s*nghề|đình\s*chỉ\s*hành\s*nghề|thu\s*hồi\s*thẻ\s*luật\s*sư|khiếu\s*nại\s*tố\s*tụng)\b",
    r"\b(?:b\s*m\s*s|i\s*o\s*t\s*tòa\s*nhà|điều\s*hòa\s*trung\s*tâm\s*chiller|hệ\s*thống\s*v\s*r\s*v|quản\s*lý\s*năng\s*lượng|tự\s*động\s*hóa\s*tòa\s*nhà|nhà\s*thông\s*minh)\b",
    r"\b(?:chương\s*trình\s*hợp\s*tác\s*quốc\s*tế|ký\s*kết\s*m\s*o\s*u)\b",
    r"\b(?:phấn\s*đấu\s*đạt\s*chuẩn|nông\s*thôn\s*mới\s*nâng\s*cao|gương\s*sáng\s*tiêu\s*biểu)\b",

    # --- THE "HISTORICAL FESTIVALS, LEGAL FEES & SOCIAL INSURANCE" LAYER ---
    r"\b(?:đền\s*hùng|chùa\s*hương|yên\s*tử|lễ\s*hội\s*truyền\s*thống|sắc\s*phong|di\s*tích\s*lịch\s*sử|trẩy\s*hội)\b",
    r"\b(?:thù\s*lao\s*luật\s*sư|hợp\s*đồng\s*dịch\s*vụ\s*pháp\s*lý|chi\s*phí\s*tố\s*tụng|thụ\s*lý\s*vụ\s*án|phân\s*xử\s*tranh\s*chấp)\b",
    r"\b(?:bhyt|chế\s*độ\s*thai\s*sản)\b",
    r"\b(?:robot\s*lau\s*kính|hệ\s*thống\s*gondola|bảo\s*trì\s*mặt\s*dựng|kiểm\s*định\s*thiết\s*bị|quản\s*lý\s*tòa\s*nhà)\b",
    r"\b(?:đẩy\s*mạnh\s*tuyên\s*truyền|xây\s*dựng\s*đời\s*sống|phong\s*trào\s*tiên\s*phong|gương\s*mẫu\s*thực\s*hiện|hoàn\s*thành\s*nhiệm\s*vụ)\b",

    # --- THE "WOODWORK VILLAGES, FAMILY LAW & MEDIATION" LAYER ---
    r"\b(?:gỗ\s*đồng\s*kỵ|gỗ\s*la\s*xuyên|khảm\s*trai\s*chuyên\s*mỹ|mỹ\s*nghệ\s*thiết\s*kế|nghệ\s*nhân\s*bàn\s*tay\s*vàng|làng\s*nghề\s*tiêu\s*biểu)\b",
    r"\b(?:ly\s*hôn\s*thuận\s*tình|phân\s*chia\s*tài\s*sản\s*chung|nhân\s*thân|hộ\s*khẩu)\b",
    r"\b(?:hòa\s*giải\s*viên|trung\s*tâm\s*trọng\s*tài|quy\s*trình\s*hòa\s*giải|thỏa\s*thuận\s*dân\s*sự|nhân\s*chứng\s*vật\s*chứng|người\s*có\s*quyền\s*lợi\s*nghĩa\s*vụ)\b",
    r"\b(?:chiếu\s*sáng\s*mỹ\s*thuật|hệ\s*thống\s*dali|đèn\s*led\s*pixel|hiệu\s*ứng\s*ánh\s*sáng|kịch\s*bản\s*chiếu\s*sáng|trang\s*trí\s*đô\s*thị|ánh\s*sáng\s*vẻ\s*đẹp)\b",
    r"\b(?:tăng\s*cường\s*kỷ\s*luật|siết\s*chặt\s*quản\s*lý)\b",

    # --- THE "QUANTUM PHYSICS, SPACE SCOPES & ADMIN LAW" LAYER ---
    r"\b(?:sóng\s*hấp\s*dẫn|năng\s*lượng\s*tối|lỗ\s*sâu|cơ\s*học\s*lượng\s*tử|vật\s*lý\s*hạt|gia\s*tốc\s*hạt)\b",
    r"\b(?:khiếu\s*nại\s*hành\s*chính|quyết\s*định\s*hành\s*chính|thời\s*hiệu\s*khiếu\s*nại|giải\s*quyết\s*tố\s*cáo|tòa\s*án\s*hành\s*chính|phán\s*quyết\s*cuối\s*cùng)\b",
    r"\b(?:hợp\s*tác\s*đa\s*phương|diễn\s*đàn\s*an\s*ninh|đối\s*thoại\s*chiến\s*lược|biên\s*bản\s*thỏa\s*thuận|quan\s*hệ\s*đối\s*ngoại|vị\s*thế\s*quốc\s*gia)\b",
    r"\b(?:quy\s*trình\s*vận\s*hành|đảm\s*bảo\s*an\s*toàn)\b",
    r"\b(?:tuyên\s*dương\s*thành\s*tích|huân\s*chương\s*lao\s*động|bằng\s*khen\s*chính\s*phủ|gương\s*điển\s*hình\s*tiên\s*tiến|phát\s*huy\s*sức\s*mạnh)\b",

    # --- THE "LIFESTYLE PHILOSOPHY, FAMILY ETHICS & PLUMBING TECH" LAYER ---
    r"\b(?:hạnh\s*phúc\s*quanh\s*ta|tổ\s*ấm\s*việt|gia\s*đình\s*và\s*pháp\s*luật|giá\s*trị\s*truyền\s*thống|đạo\s*đức\s*lối\s*sống|nếp\s*sống\s*văn\s*minh)\b",
    r"\b(?:phụ\s*nữ\s*hiện\s*đại|nam\s*giới\s*bản\s*lĩnh|giữ\s*lửa\s*hạnh\s*phúc|bí\s*quyết\s*gia\s*đình|mối\s*quan\s*hệ\s*bền\s*chặt|tâm\s*lý\s*gia\s*đình)\b",
    r"\b(?:hệ\s*thống\s*cấp\s*thoát\s*nước|trạm\s*bơm\s*tăng\s*áp|bể\s*xử\s*lý\s*nước\s*thải|đường\s*ống\s*hdpe|van\s*giảm\s*áp|cột\s*áp|hố\s*ga\s*thông\s*minh)\b",
    r"\b(?:chiến\s*lược\s*quốc\s*gia|trọng\s*tâm\s*kinh\s*tế|mục\s*tiêu\s*tổng\s*quát|nhiệm\s*vụ\s*đột\s*phá)\b",
    r"\b(?:hoàn\s*thành\s*vượt\s*mức)\b",

    # --- THE "CULTURAL LITERACY, EDUCATIONAL STORIES & PUBLIC ETHICS" LAYER ---
    r"\b(?:sổ\s*tay\s*văn\s*hóa|câu\s*chuyện\s*giáo\s*dục|nhật\s*ký\s*người\s*đi\s*đường|văn\s*hóa\s*giao\s*thông|ý\s*thức\s*công\s*dân|rèn\s*luyện\s*nhân\s*cách|giá\s*trị\s*sống)\b",
    r"\b(?:dư\s*luận\s*xã\s*hội|lên\s*án\s*hành\s*vi|phản\s*ứng\s*cộng\s*đồng|nghĩa\s*vụ\s*trách\s*nhiệm|chuẩn\s*mực\s*đạo\s*đức)\b",
    r"\b(?:bồn\s*trộn\s*bê\s*tông|cánh\s*khuấy|hệ\s*thống\s*truyền\s*động|phụ\s*gia\s*bê\s*tông|lưu\s*hóa|đúc\s*sẵn)\b",
    r"\b(?:nghị\s*quyết\s*phát\s*triển|định\s*hướng\s*tầm\s*nhìn|ưu\s*tiên\s*đầu\s*tư|hạ\s*tầng\s*kỹ\s*thuật|đồng\s*bộ\s*hiện\s*đại)\b",
    r"\b(?:thi\s*đua\s*yêu\s*nước|kế\s*hoạch\s*đề\s*ra)\b",

    # --- THE "PHILANTHROPY FOUNDATIONS, NOTARY LAW & TRADITIONAL MEDICINE" LAYER ---
    r"\b(?:quỹ\s*thiện\s*tâm|quỹ\s*hy\s*vọng|quỹ\s*vì\s*người\s*nghèo|chương\s*trình\s*tài\s*trợ|tấm\s*lòng\s*vàng|trao\s*tặng\s*quà)\b",
    r"\b(?:công\s*chứng\s*số|ký\s*số)\b",
    r"\b(?:hội\s*đông\s*y|cây\s*thuốc\s*nam|vườn\s*dược\s*liệu|hải\s*thượng\s*lãn\s*ông|tuệ\s*tĩnh|y\s*học\s*cổ\s*truyền|châm\s*cứu|bấm\s*huyệt)\b",
    r"\b(?:đạo\s*đức\s*công\s*vụ|trách\s*nhiệm\s*người\s*đứng\s*đầu|kiểm\s*soát\s*quyền\s*lực|phòng\s*chống\s*tham\s*nhũng|lãng\s*phí)\b",
    r"\b(?:kiểm\s*tra\s*sát\s*hạch|đường\s*lối\s*chính\s*sách|nghị\s*quyết\s*đảng)\b",

    # --- THE "INSPIRATIONAL MEDIA, ECONOMIC PULSE & GLOBAL CURIOSITIES" LAYER ---
    r"\b(?:niềm\s*tin\s*và\s*khát\s*vọng|góc\s*nhìn\s*thời\s*đại|nhịp\s*đập\s*kinh\s*tế|thế\s*giới\s*đó\s*đây|chuyện\s*của\s*sao|bật\s*mí\s*bí\s*mật|cận\s*cảnh\s*quy\s*trình|khám\s*phá\s*thực\s*tế)\b",
    r"\b(?:món\s*hời\s*đầu\s*tư|dòng\s*vốn\s*lớn|thị\s*trường\s*sôi\s*động|chốt\s*quyền\s*nhận\s*cổ\s*tức|niêm\s*yết\s*sàn|ipo)\b",
    r"\b(?:tư\s*duy\s*triệu\s*phú|làm\s*giàu\s*không\s*khó|nghỉ\s*hưu\s*sớm|kế\s*hoạch\s*chi\s*tiêu|quản\s*lý\s*tài\s*sản)\b",
    r"\b(?:thành\s*lập\s*doanh\s*nghiệp|giấy\s*phép\s*điều\s*kiện|hợp\s*quy\s*kỹ\s*thuật|kiểm\s*định\s*độc\s*lập|chất\s*lượng\s*vượt\s*trội|thương\s*hiệu\s*uy\s*tín)\b",
    r"\b(?:kết\s*quả\s*mong\s*đợi)\b",
    # --- THE "BAILIFF PROCEDURES, ARTISAN CRAFTS & PUBLIC SUPERVISION" LAYER ---
    r"\b(?:lập\s*vi\s*bằng|niêm\s*phong\s*tài\s*sản|kê\s*biên\s*phát\s*mại|thông\s*báo\s*cưỡng\s*chế|vi\s*bằng\s*ghi\s*nhận)\b",
    r"\b(?:quạt\s*chàng\s*sơn|giấy\s*dó|tranh\s*điệp|lụa\s*vạn\s*phúc|gốm\s*bát\s*tràng|di\s*sản\s*văn\s*hóa\s*phi\s*vật\s*thể)\b",
    r"\b(?:thanh\s*tra\s*công\s*vụ|kỷ\s*luật\s*hành\s*chính|giải\s*quyết\s*đơn\s*thư|tiếp\s*công\s*dân|đối\s*thoại\s*trực\s*tiếp|tháo\s*gỡ\s*vướng\s*mắc)\b",
    r"\b(?:công\s*nghệ\s*tự\s*động|phần\s*mềm\s*quản\s*trị|hệ\s*sinh\s*thái\s*số)\b",
    r"\b(?:tăng\s*cường\s*trách\s*nhiệm|siết\s*chặt\s*kỷ\s*cương|kiểm\s*tra\s*giám\s*sát|xử\s*lý\s*nghiêm\s*sai\s*phạm|đúng\s*quy\s*định)\b",
    # --- THE FINAL-FINAL-ULTIMATE: INTELLECTUAL PROPERTY, BUSINESS ADMIN & HOUSEHOLD CRAFTS ---
    r"\b(?:kiểu\s*dáng\s*công\s*nghiệp|sở\s*hữu\s*trí\s*tuệ|bảo\s*hộ\s*thương\s*hiệu|đăng\s*ký\s*nhãn\s*hiệu|vi\s*phạm\s*bản\s*quyền|tác\s*quyền)\b",
    r"\b(?:hiệp\s*hội\s*doanh\s*nghiệp|phòng\s*thương\s*mại|vcci|liên\s*đoàn\s*lao\s*động|hội\s*liên\s*hiệp\s*phụ\s*nữ|đoàn\s*thanh\s*niên)\b",
    r"\b(?:đan\s*lát|thêu\s*ren|móc\s*len|may\s*vá|đồ\s*handmade|quà\s*tặng\s*thủ\s*công|trang\s*trí\s*bàn\s*tiệc|tổ\s*chức\s*sự\s*kiện)\b",
    r"\b(?:bảo\s*hiểm\s*xã\s*hội|bhxh|bhyt|chế\s*độ\s*thai\s*sản|hưu\s*trí|trợ\s*cấp\s*thất\s*nghiệp|an\s*sinh\s*xã\s*hội)\b",
    r"\b(?:triển\s*khai\s*nhiệm\s*vụ|tổng\s*kết\s*công\s*tác|phát\s*động\s*thi\s*đua|khen\s*thưởng\s*đột\s*xuất|huy\s*hiệu\s*đảng)\b",
    # --- THE ULTIMATE PURITY: CIVIC GOVERNANCE, SOCIAL DISCOURSE & URBAN ORDER ---
    r"\b(?:bất\s*cập|vướng\s*mắc|kiến\s*nghị\s*cử\s*tri|phản\s*hồi\s*dư\s*luận|phản\s*biện\s*xã\s*hội|vấn\s*đề\s*nóng|câu\s*chuyện\s*cảnh\s*giác)\b",
    r"\b(?:văn\s*hóa\s*giao\s*thông|văn\s*hóa\s*đọc|văn\s*minh\s*đô\s*thị|đạo\s*đức\s*nghề\s*nghiệp|nhân\s*cách|lối\s*sống|kỹ\s*năng\s*mềm|tư\s*duy\s*tích\s*cực)\b",
    r"\b(?:lấn\s*chiếm\s*lòng\s*lề\s*đường|trật\s*tự\s*đô\s*thị|vỉ\s*hè\s*thông\s*thoáng|vệ\s*sinh\s*môi\s*trường\s*khu\s*phố|tổ\s*tự\s*quản|camera\s*an\s*ninh\s*phường)\b",
    r"\b(?:ngày\s*hội\s*đại\s*đoàn\s*kết|hội\s*thảo\s*khoa\s*học|diễn\s*đàn\s*trẻ\s*em|đại\s*hội\s*hội\s*khuyến\s*học|clb\s*hưu\s*trí|sinh\s*hoạt\s*hè)\b",
    r"\b(?:phí\s*dịch\s*vụ\s*chung\s*cư|ban\s*quản\s*trị\s*nhà|họp\s*dân\s*cư|quy\s*chế\s*phát\s*ngôn|thủ\s*tục\s*hành\s*chính\s*công|một\s*cửa\s*liên\s*thông)\b"
]

# 2. CONDITIONAL VETO: Noise that can co-exist with disaster (Economy, Accident, etc.)
# These will be blocked ONLY if there is NO specific hazard score or metrics.
CONDITIONAL_VETO = [
    # URBAN / INDUSTRIAL FIRE & EXPLOSION (Non-Forest)
    r"(?:cháy|hỏa\s*hoạn|bốc\s*cháy|phát\s*hỏa)\s*(?:nhà|căn\s*hộ|chung\s*cư|phòng\s*trọ|quán|karaoke|bar|cửa\s*hàng|ki\s*ốt|xưởng|kho|trụ\s*sở|xe|ô\s*tô|xe\s*máy)",
    r"(?:nổ|phát\s*nổ)\s*(?:bình\s*gas|khí\s*gas|nồi\s*hơi|lò\s*hơi|trạm\s*biến\s*áp|máy\s*biến\s*áp|pin|ắc\s*quy)",
    r"(?:PCCC|cảnh\s*sát\s*PCCC|114|đội\s*chữa\s*cháy|lực\s*lượng\s*chữa\s*cháy|dập\s*tắt\s*đám\s*cháy)",
    r"(?:nguyên\s*nhân\s*ban\s*đầu|đang\s*điều\s*tra|khám\s*nghiệm\s*hiện\s*trường|khởi\s*tố\s*vụ\s*án)\s*(?:cháy|nổ)?",
    r"lửa\s*ngùn\s*ngụt", r"bà\s*hỏa", r"chập\s*điện",

    # TRAFFIC ACCIDENTS (General)
    r"(?:tai\s*nạn|va\s*chạm|tông|đâm)\s*(?:giao\s*thông|liên\s*hoàn)?",
    r"(?:xe\s*máy|ô\s*tô|xe\s*khách|xe\s*tải|xe\s*container|xe\s*đầu\s*kéo|xe\s*buýt|tàu\s*hỏa|tàu\s*thủy|ca\s*nô|tàu\s*cá)\s*(?:lật|lao|tông|đâm|va\s*chạm)",
    r"(?:CSGT|cảnh\s*sát\s*giao\s*thông|khám\s*nghiệm|điều\s*tra)\s*(?:nguyên\s*nhân|vụ\s*việc)?",
    r"mất\s*thắng|mất\s*phanh|xe\s*lu|xe\s*cẩu|xe\s*ủi|xe\s*ben|xe\s*bồn",

    # INDIVIDUAL ACCIDENTS
    r"đuối\s*nước.*(?:tắm\s*sông|tắm\s*suối|tắm\s*biển|đi\s*bơi|hồ\s*bơi|bể\s*bơi)",
    r"(?:sập|đổ)\s*(?:giàn\s*giáo|cần\s*cẩu|công\s*trình|tường|trần|mái|nhà\s*xưởng)\s*(?:đang\s*thi\s*công|khi\s*thi\s*công)",
    r"tai\s*nạn\s*lao\s*động|an\s*toàn\s*lao\s*động",
    r"(?:rơi|ngã)\s*(?:từ\s*trên\s*cao|tầng\s*\d+|giàn\s*giáo|cần\s*cẩu)",

    # ECONOMY & FINANCE
    r"lãi\s*suất|tín\s*dụng|tỉ\s*giá|ngoại\s*tệ|ngân\s*hàng|chứng\s*khoán|vốn\s*điều\s*lệ|lợi\s*nhuận|doanh\s*thu|vn-index",
    r"giá\s*(?:vàng|heo|cà\s*phê|lúa|xăng|dầu|trái\s*cây|thanh\s*long|nông\s*sản|bất\s*động\s*sản|đất)",
    r"hạ\s*nhiệt\s*(?:giá|thị\s*trường)|tăng\s*trưởng\s*kinh\s*tế|gdp|oda|adb|wb|imf",

    # TECH TUTORIALS & SPAM
    r"(?:cách|hướng\s*dẫn|thủ\s*thuật|mẹo).*(?:tách|gộp|nén|chuyển|sửa).*(?:file|tệp|pdf|word|excel|ảnh|video)",
    r"(?:google|facebook|youtube|tiktok|zalo\s*pay|vneid).*(?:cập\s*nhật|tính\s*năng|ra\s*mắt|lỗi|hướng\s*dẫn)",
    r"how\s*to.*(?:tutorial|template|branding|customize)",
    r"sân\s*bay|hàng\s*không|hạ\s*cánh|cất\s*cánh|phi\s*công|cơ\s*trưởng",

    # SAFETY ADVISORIES & EDUCATION (Non-emergencies)
    r"\b(?:khuyến\s*cáo|nhắc\s*nhở|kỹ\s*năng|phòng\s*ngừa|tập\s*huấn)\s*(?:pccc|an\s*toàn|ngập\s*lụt|đuối\s*nước)\b",
    
    # INFRASTRUCTURE & TECHNICAL FAILURES (Non-disaster incidents)
    r"\b(?:sự\s*cố|hỏng\s*hóc|bảo\s*trì|ngắt\s*điện|mất\s*điện|cắt\s*điện)\s*(?:lưới\s*điện|trạm\s*biến\s*áp|đường\s*dây|cáp\s*quang|internet|hệ\s*thống)\b",
    r"\b(?:thủng\s*xăm|hỏng\s*xe|chết\s*máy|ùn\s*tắc|kẹt\s*xe|dòng\s*người\s*chen\s*chúc)\b",
    r"\b(?:sập\s*giàn\s*giáo|tai\s*nạn\s*lao\s*động|ngộ\s*độc\s*thực\s*phẩm|cháy\s*nổ\s*bình\s*gas)\b",
    
    # ROUTINE URBAN NOISE
    r"\b(?:triều\s*cường\s*rằm|ngập\s*do\s*triều|đỉnh\s*triều|hố\s*ga|nắp\s*cống|vỉ\s*hè|đường\s*hầm)\b",
    r"\b(?:kiểm\s*tra\s*nồng\s*độ\s*cồn|phạt\s*nguội|xe\s*quá\s*tải|trạm\s*thu\s*phí|vào\s*cua|mất\s*lái)\b",

    # MARINE & AGRI PRODUCTION (Routine production news)
    r"\b(?:vươn\s*khơi|bám\s*biển|đánh\s*bắt|nuôi\s*trồng|tái\s*đàn|vào\s*vụ|thu\s*hoạch|giá\s*thu\s*mua|hải\s*sản|thủy\s*sản)\b",
    
    # PUBLIC HEALTH & EPIDEMICS (Medical, not natural disasters)
    r"\b(?:sốt\s*xuất\s*huyết|tay\s*chân\s*miệng|dịch\s*sởi|cúm\s*gia\s*cầm|đỉnh\s*dịch|bùng\s*phát\s*dịch|phun\s*hóa\s*chất|diệt\s*loăng\s*quăng)\b",
    
    # PUBLIC WORKS MAINTENANCE (Routine)
    r"\b(?:nạo\s*vét|khơi\s*thông|vệ\s*sinh).*(?:kênh\s*mương|cống\s*rãnh|dòng\s*chảy|rác\s*thải)\b",
    r"\b(?:phủ\s*xanh|trồng\s*cây\s*gây\s*rừng|chăm\s*sóc\s*cây\s*xanh|cắt\s*tỉa\s*cành\s*cây)\b",

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
    r"\b(?:thông\s*hầm|trải\s*nhựa|vá\s*đường|khắc\s*phục\s*ổ\s*gà|duy\s*tu|sửa\s*chữa\s*định\s*kỳ|mở\s*rộng\s*tuyến\s*đường)\b",

    # ROUTINE WEATHER (Non-disaster/Pleasant weather)
    r"\b(?:nắng\s*đẹp|thời\s*tiết\s*thuận\s*lợi|nắng\s*ấm|gió\s*nhẹ|mây\s*rải\s*rác|không\s*mưa|nắng\s*chan\s*hòa|bình\s*minh|hoàng\s*hôn)\b",
    
    # ACADEMIC & EXAM SEASONS (Metaphorical heat/waves)
    r"\b(?:phòng\s*thi|sức\s*nóng\s*mùa\s*thi|sĩ\s*tử|vượt\s*vũ\s*môn|đề\s*thi|nộp\s*hồ\s*sơ|điểm\s*chuẩn|nguyện\s*vọng|tuyển\s*sinh)\b",
    
    # HISTORICAL NOSTALGIA & DOCUMENTARIES (Past events)
    r"\b(?:ký\s*ức|hồi\s*tưởng|nhìn\s*lại|phim\s*tài\s*liệu|lịch\s*sử|năm\s*xưa|chuyện\s*cũ|tư\s*liệu\s*quý)\b",
    
    # RECRUITMENT & JOB MARKET
    r"\b(?:thị\s*trường\s*lao\s*động|nhu\s*cầu\s*tuyển\s*dụng|cơ\s*hội\s*việc\s*làm|làn\s*sóng\s*nhảy\s*việc|nộp\s*c\s*v|phỏng\s*vấn\s*tuyển\s*dụng)\b"
]

# 3. SOFT NEGATIVE: Potential False Positive (Politics, Admin, Economy)
# Can be overridden if HAZARD SCORE is high enough.
SOFT_NEGATIVE = [
    # === A) Politics/Admin ceremony templates ===
    r"(?:kỳ\s*họp|phiên\s*họp|hội\s*nghị|đại\s*hội|văn\s*phòng|ubnd|hđnd|mttq)\s*(?:đảng|đảng\s*bộ|hđnd|quốc\s*hội|chi\s*bộ|cử\s*tri|toàn\s*quốc|tổng\s*kết|sơ\s*kết)",
    r"tiếp\s*xúc\s*cử\s*tri|chất\s*vấn|giải\s*trình|bầu\s*cử|ứng\s*cử",
    r"bổ\s*nhiệm|miễn\s*nhiệm|điều\s*động|luân\s*chuyển|kỷ\s*luật|kiểm\s*tra|giám\s*sát",
    r"nghị\s*quyết|nghị\s*định|thông\s*tư|quyết\s*định|chỉ\s*thị(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn))",
    r"trợ\s*cấp\s*thất\s*nghiệp|đạt\s*chuẩn\s*nông\s*thôn\s*mới|nông\s*thôn\s*mới\s*nâng\s*cao",

    # === B) Digest formats ===
    r"bản\s*tin\s*(?:cuối\s*ngày|sáng|trưa|tối)|điểm\s*tin|tin\s*trong\s*nước|tin\s*quốc\s*tế",

    # === C) Education and Awards ===
    r"(?:tốt\s*nghiệp|nhận\s*học\s*bổng|tuyển\s*sinh.*đại\s*học)(?!.*(?:sau\s*lũ|vùng\s*lũ))",
    r"giải\s*thưởng|vinh\s*danh|trao\s*huân\s*chương|cờ\s*thi\s*đua|kỷ\s*niệm|lễ\s*kỷ\s*niệm|văn\s*hóa\s*văn\s*nghệ|biểu\s*diễn",

    # === D) Construction ceremony ===
    r"khởi\s*công|khánh\s*thành|nghiệm\s*thu(?!.*(?:kè|đê|hồ|thoát\s*nước|chống\s*ngặp|chống\s*sạt\s*lở|thiên\s*tai))",

    # === E) Missing persons (soft flag only if NOT clearly disaster-related) ===
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
    
    # [OPTIMIZATION] Multi-Hazard Bonus: If article mentions multiple categories (e.g. Storm + Flood)
    if len(rule_matches) >= 2:
        rule_score += 1.0
        if len(rule_matches) >= 3:
            rule_score += 0.5

    # [OPTIMIZATION] High-Priority Keyword Boost
    for pat in HIGH_PRIORITY_RE:
        if pat.search(t_acc):
            rule_score += 1.0 # Significant boost for dangerous event types
            break

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

    # 2. Main Threshold Check (11.0 points to pass after bonuses - Increased from 10.0)
    if sig["score"] >= 11.0:
        return True

    # 3. Trusted Source / Verification Fallback (9.5 for official - Increased from 8.0)
    if trusted_source and sig["score"] >= 9.5:
        return True

    is_forecast = sig["stage"] == "FORECAST"
    is_planning = any(pk in full_text.lower() for pk in PLANNING_PREP_KEYWORDS)
    
    # Article Mode Thresholds:
    # Incident news passes at 8.5 (Raised from 7.0)
    # Forecast news (Bulletins) needs 9.5+ (Raised from 8.0)
    threshold = 9.5 if is_forecast else 8.5
    
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
    reason = f"Score {sig['score']:.1f} < 8.5"
    if sig["absolute_veto"]: reason = "Negative keyword match (Veto)"
    elif sig["score"] >= 8.5: reason = "Passed (Score >= 8.5)"
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
    import html
    cleaned = html.unescape(text) # [OPTIMIZATION] Standardize HTML entities for Vietnamese
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
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
