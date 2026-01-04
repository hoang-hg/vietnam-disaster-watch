from dataclasses import dataclass
from typing import Literal, List
import urllib.parse
import json
from pathlib import Path
import re
Method = Literal["rss", "gnews"]

# 14+2 Standardized Disaster Groups
DISASTER_GROUPS = {
    # 1) Bão & áp thấp nhiệt đới (Storm/Tropical Cyclone)
    "storm": [
        "bão", "bão số", "siêu bão", "hoàn lưu bão", "tâm bão", "đổ bộ",
        "áp thấp", "áp thấp nhiệt đới", "atnđ", "atnd", "vùng áp thấp", "vùng thấp", "rãnh áp thấp",
        "bão nhiệt đới", "siêu bão nhiệt đới", "gió bão", "vùng gió mạnh", "mắt bão",
        "tiến vào biển đông", "đi vào biển đông", "suy yếu thành áp thấp",
        "chuyển hướng", "ảnh hưởng của bão", "hoàn lưu áp thấp",
        "tin bão", "tin áp thấp", "bản tin bão", "cảnh báo bão",
        "xoáy thuận nhiệt đới", "nhiễu động nhiệt đới", "cường độ bão", "cấp bão",
        "bán kính gió mạnh", "vùng nguy hiểm", "tọa độ tâm bão", "kinh độ tâm bão", "vĩ độ tâm bão",
        "dự báo bão", "hướng di chuyển của bão", "vị trí tâm bão", "sức gió mạnh nhất",
        "tin bão khẩn cấp", "hành lang bão", "bão mạnh lên", "áp thấp mạnh lên", "tan dần",
        "cập nhật bão", "mưa do hoàn lưu", 
        "bão rất mạnh", "bão mạnh", "cơn bão", "bão trên biển đông", "bão trên biển",
        "áp thấp suy yếu", "áp thấp tan", "xoáy thuận", "tổ hợp thời tiết xấu",
        "dải hội tụ nhiệt đới", "hội tụ nhiệt đới", "vùng hội tụ", "dải hội tụ",
        "rãnh thấp", "rãnh thấp có trục", "rãnh thấp xích đạo",
        "gió đông bắc", "gió mùa tây nam", "gió mùa", "không khí lạnh tương tác",
        "nước dâng do bão", "nước biển dâng do bão", "sóng lớn do bão", "biển động do bão",
        "gió mạnh cấp", "gió cấp", "gió giật cấp", "giật cấp",
        "gió giật mạnh", "gió giật rất mạnh", "gió giật trên cấp",
        "cấp 8", "cấp 9", "cấp 10", "cấp 11", "cấp 12", "cấp 13", "cấp 14", "cấp 15", "cấp 16", "cấp 17",
        "cấp 6-7", "cấp 7-8", "cấp 8-9", "cấp 9-10", "cấp 10-11", "cấp 11-12", "cấp 12-13",
        "beaufort", "gió cấp 6", "gió cấp 7",
        "đổi hướng", "đi lệch", "quỹ đạo", "đường đi của bão",
        "di chuyển nhanh", "di chuyển chậm", "di chuyển theo hướng",
        "dịch chuyển", "tăng cấp", "mạnh thêm", "suy yếu", "suy yếu nhanh",
        "mạnh lên thành bão", "mạnh lên thành áp thấp nhiệt đới",
        "đi vào đất liền", "đổ bộ vào", "đi sát bờ", "áp sát đất liền",
        "gây mưa lớn", "gây gió mạnh", "ảnh hưởng trực tiếp", "ít khả năng ảnh hưởng",
        "vùng ảnh hưởng", "hoàn lưu gây mưa", "mưa rất to", "mưa to đến rất to",
        "giữa biển đông", "bắc biển đông", "nam biển đông", "tây bắc biển đông",
        "quần đảo hoàng sa", "quần đảo trường sa",
        "vịnh bắc bộ", "vịnh thái lan",
        "biển đông", "ngoài khơi", "trên biển",
        "tên bão", "bão có tên", "bão quốc tế",
        "vùng tâm bão", "áp sát ven biển", "hoàn lưu sau bão", "gió xoáy", "phong ba"
    ],

    # 2) Lũ lụt (Flood)
    "flood": [
        "lũ lụt", "ngập lụt", "ngập úng", "lũ dâng", "đỉnh lũ", "mực nước báo động",
        "vỡ đê", "tràn đê", "xả lũ", "hồ chứa", "thủy điện", "xả tràn", "nước sông dâng",
        "ngập sâu", "ngập nhà", "ngập phố", "chia cắt", "cô lập", "vỡ đập", "sự cố đập",
        "vượt báo động", "đạt đỉnh", "nước lụt", "triều cường kết hợp", "ngập triều cường",
        "mực nước trên báo động", "lũ báo động 3", "lũ lịch sử", "ngập lụt cục bộ", "vùng trũng thấp"
    ],

    # 3) Lũ quét/Lũ ống (Flash Flood)
    "flash_flood": [
        "lũ quét", "lũ ống", "lũ bùn đá", "lũ nhanh", "lũ dữ", "lũ đổ về",
        "nguy cơ lũ quét", "cảnh báo lũ quét", "quét sạch", "nước lũ cuồn cuộn",
        "lũ cuồn cuộn", "dòng lũ chảy siết", "đất đá đổ về", "trôi cầu"
    ],

    # 4) Sạt lở (Landslide)
    "landslide": [
        "sạt lở", "sạt lở đất", "trượt lở đất", "lở núi", "sập taluy", "đất đá vùi lấp",
        "sạt lở bờ sông", "sạt lở bờ biển", "trượt mái đê", "đá lăn", "sạt lở núi",
        "đất đá sạt xuống", "trượt mái dốc",
        "đứt gãy", "trượt sạt", "vết nứt núi", "nứt núi", "sụp đổ địa chất", "sạt taluy dương", "sạt taluy âm",
        "sập cầu", "gãy cầu", "sập hầm"
    ],

    # 5) Sụt lún đất (Land Subsidence)
    "subsidence": [
        "sụt lún", "sụp lún", "hố tử thần", "nứt toác", "hàm ếch", "nứt đất", "hố sụt", "sụt lún đất",
        "sụt lún hạ tầng", "biến dạng mặt đường", "lún xụt"
    ],

    # 6) Hạn hán (Drought)
    "drought": [
        "hạn hán", "khô hạn", "thiếu nước ngọt", "nứt nẻ", "khô cằn", "cạn hồ", "dòng chảy kiệt", "mùa cạn",
        "thiếu nước sinh hoạt", "héo úa", "cháy lá", "hạn hán kéo dài",
        "vùng hạn", "chống hạn", "thiếu hụt mưa", "mực nước chết", "nứt nẻ ruộng đồng"
    ],

    # 7) Xâm nhập mặn (Salinity Intrusion)
    "salinity": [
        "xâm nhập mặn", "nhiễm mặn", "độ mặn", "ranh mặn", "mặn xâm nhập sâu", "cống ngăn mặn", "đẩy mặn",
        "độ mặn phần nghìn", "hạn mặn",
        "nước lợ", "độ mặn vượt ngưỡng", "mặn bủa vây", "ranh mặn 4 g/l", "nhiễm mặn sâu"
    ],

    # 8) Mưa lớn/Mưa đá/Lốc/Sét (Extreme Weather)
    "extreme_weather": [
        "mưa lớn", "mưa xối xả", "mưa trắng trời", "mưa đá", "lốc", "sét", "phóng điện", "dông", "giông", "lốc xoáy", "gió mạnh", "quật đổ", "tốc mái", "vòi rồng",
        "mưa rất to", "dông lốc", "tố lốc", "sét đánh", "giông sét", "lượng mưa kỷ lục", "mưa trút xuống", "mưa như trút",
        "mưa diện rộng", "mưa cục bộ", "gió giật mạnh", "giông tố", "giông cực mạnh", "gió rít", "trắng trời"
    ],

    # 9) Nắng nóng (Heatwave)
    "heatwave": [
        "nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt gay gắt", "nhiệt độ kỷ lục",
        "đợt nắng nóng", "nhiệt độ tăng cao", "chỉ số UV", "nắng như đổ lửa", "nóng đỉnh điểm",
        "nắng cháy da", "nóng rát", "nắng hạn", "nóng như thiêu như đốt"
    ],

    # 10) Rét hại/Sương muối (Cold/Frost)
    "cold_surge": [
        "rét đậm rét hại", "rét hại", "băng giá", "sương muối", "nhiệt độ xuống thấp",
        "rét buốt", "mưa tuyết", "tuyết rơi", "không khí lạnh", "rét đậm",
        "không khí lạnh tăng cường", "gió mùa đông bắc", "rét tê tái", "tráng xóa băng", "đợt rét mạnh"
    ],

    # 11) Động đất (Earthquake)
    "earthquake": [
        "động đất", "rung chấn", "dư chấn", "richter", "tâm chấn", "chấn tiêu",
        "độ lớn động đất", "magnitude", "rung lắc mạnh", "viện vật lý địa cầu",
        "sóng địa chấn", "cấp độ Richter", "rung chấn mạnh", "chấn phát"
    ],

    # 12) Sóng thần (Tsunami)
    "tsunami": [
        "sóng thần", "tsunami", "cảnh báo sóng thần", "tin sóng thần", "nước biển rút bất thường",
        "sóng cao hàng chục mét", "thảm họa sóng thần", "sóng thần tàn phá"
    ],

    # 13) Nước dâng (Storm Surge)
    "storm_surge": [
        "nước dâng", "nước dâng do bão", "nước biển dâng", "sóng tràn", "nước dâng ven biển",
        "triều cường", "đỉnh triều", "ngập do triều cường", "thủy triều dâng",
        "triều cường vượt mức", "ngập lụt do triều", "sóng biển cao", "sóng đánh vào bờ"
    ],

    # 14) Cháy rừng (Wildfire)
    "wildfire": [
        "cháy rừng", "cháy tán", "cháy ngầm", "cột khói", "dập lửa",
        "nguy cơ cháy rừng", "cấp dự báo cháy rừng", "PCCCR", "cháy thực bì", "lửa rừng",
        "cháy rừng phòng hộ", "chữa cháy rừng", "đám cháy lan",
        "giặc lửa", "điểm cháy", "khói mù", "thiêu rụi"
    ],

    # 15) Xói lở (Erosion)
    "erosion": [
        "xói lở", "sạt lở bờ sông", "sạt lở bờ biển", "hàm ếch", "mương xói", "rãnh xói", "xâm thực", "xói mòn"
    ],

    # 16) Tin cảnh báo, dự báo (Warning/Forecast)
    "warning_forecast": [
        "bản tin dự báo", "tin cảnh báo", "dự báo thời tiết", "cảnh báo thiên tai",
        "tin cuối cùng", "tin phát đi", "bản tin cập nhật", "dự báo khí tượng",
        "trung tâm dự báo", "bản tin khẩn cấp",
        "thông báo khẩn", "điểm tin thiên tai", "đài khí tượng", "dự báo khí hậu", "cảnh báo cực đoan"
    ],

    # 17) Khắc phục hậu quả (Recovery)
    "recovery": [
        "khắc phục hậu quả", "khắc phục sự cố", "khôi phục giao thông", "thống kê thiệt hại",
        "ủng hộ đồng bào", "cứu trợ", "tiếp tế", "dọn dẹp sau bão", "viện trợ", "hỗ trợ khẩn cấp"
    ],

    # 18) Tai nạn hàng hải (Marine Incidents)
    "marine": [
        "chìm tàu", "đắm tàu", "lật tàu", "trôi dạt", "mất tích trên biển",
        "tàu cá gặp nạn", "thuyền viên mất tích", "cứu nạn hàng hải", "tàu gặp sự cố",
        "hỗ trợ lai dắt", "tàu hỏng máy", "tàu phá nước", "ngư dân gặp nạn",
        "sự cố trên biển", "tai nạn đường thủy", "thuyền thúng lật", "ghe chìm",
        "mất liên lạc", "mất tín hiệu", "tàu mắc cạn", "va chạm trên biển",
        "mất tích trên vùng biển"
    ]
}

# Flat list for searching and initial filtering
DISASTER_KEYWORDS = [item for sublist in DISASTER_GROUPS.values() for item in sublist]

# Context keywords (not a disaster group, but used to refine search and increase confidence)
CONTEXT_KEYWORDS = [
  # Core disaster-event framing
  "thiên tai", "thảm họa", "rủi ro thiên tai", "cấp độ rủi ro", "cấp độ rủi ro thiên tai",
  "cảnh báo rủi ro", "mức rủi ro", "báo động", "tình huống khẩn cấp",

  # Impact / damage
  "thiệt hại", "tổn thất", "hư hỏng", "hư hại", "tàn phá",
  "tốc mái", "sập", "sập nhà", "sập công trình", "đổ tường", "đổ sập",
  "cuốn trôi", "bị cuốn trôi", "trôi nhà", "vùi lấp", "bị vùi lấp",
  "ngập lụt", "ngập", "ngập nhà", "ngập đường", "ngập phố", "ngập sâu", "ngập diện rộng",
  "chia cắt", "cô lập", "tê liệt", "gián đoạn", "đình trệ",
  "mất điện", "mất nước", "mất sóng", "mất liên lạc",

  # Casualty / SAR
  "tử vong", "thiệt mạng", "thương vong", "bị thương", "trọng thương",
  "mất tích", "mất liên lạc", "mắc kẹt", "bị kẹt",
  "tìm kiếm", "tìm kiếm cứu nạn", "cứu nạn", "cứu hộ", "giải cứu",

  # Response / command
  "sơ tán", "sơ tán khẩn cấp", "di dời", "di dời khẩn cấp", "lánh nạn", "tránh trú",
  "cứu trợ", "cứu tế", "tiếp tế", "hỗ trợ", "hỗ trợ khẩn cấp",
  "khắc phục", "khắc phục hậu quả", "xử lý sự cố", "phục hồi", "tái thiết",
  "ứng phó", "ứng phó khẩn cấp", "ban chỉ huy", "ban chỉ đạo", "PCTT", "TKCN",
  "trực ban", "trực 24/24", "túc trực",
  "công điện", "công điện khẩn", "hỏa tốc", "chỉ đạo", "chỉ thị", "yêu cầu",

  # Infrastructure / hydrology / transport restrictions
  "vỡ đê", "tràn đê", "vỡ kè", "sạt lở kè", "xói lở",
  "vỡ đập", "sự cố đập", "sự cố hồ đập", "mất an toàn hồ đập",
  "xả lũ", "xả tràn", "xả điều tiết", "xả khẩn cấp", "điều tiết hồ",
  "hồ chứa", "thủy điện", "thủy lợi", "hồ thủy lợi",
  "đóng đường", "cấm đường", "cấm biển", "dừng lưu thông", "tạm dừng",
  "sạt taluy", "sập taluy", "nứt đường", "sập cầu",
  "độ mặn", "phần nghìn", "nhiệt độ kỷ lục", "Richter", "dư chấn", "băng giá", "tuyết rơi", "hố sụt", "biến dạng địa hình",

  # Coastal flooding signals
  "nước dâng", "triều cường", "sóng tràn",

  # Community / public services
  "đóng cửa trường", "cho nghỉ học", "nghỉ học",
]


# Sensitive Geographical Locations (Critical infrastructure/terrain)
SENSITIVE_LOCATIONS = [
    # Dams/Hydropower/Reservoirs
    "Sơn La", "Hòa Bình", "Lai Châu", "Trị An", "Thác Bà", "Yaly", "Bản Chát", 
    "Hồ Kẻ Gỗ", "Dầu Tiếng", "Bản Vẽ", "Sông Tranh", "Đa Nhim", "Hàm Thuận - Đa Mi",
    "Cửa Đạt", "Ngàn Trươi", "Tả Trạch", "Phú Ninh", "Nước Trong", "Cấm Sơn", 
    "Định Bình", "Bản Mồng", "Huội Quảng", "Nậm Chiến", "Tuyên Quang", "Hương Điền",
    "Sông Bung", "Plei Krông", "Thác Mơ", "Đồng Nai 3", "Đồng Nai 4",
    # Major Mountain Passes (Landslide & Accident prone)
    "Đèo Hải Vân", "Đèo Cả", "Đèo Ngang", "Đèo Pha Đin", "Đèo Khau Phạ", 
    "Đèo Ô Quy Hồ", "Đèo Mã Pì Lèng", "Đèo Bảo Lộc", "Đèo Prenn", "Đèo Chuối",
    "Đèo Lò Xo", "Đèo Cù Mông", "Đèo Ngoạn Mục", "Đèo Sông Pha", "Đèo Phượng Hoàng",
    "Đèo Măng Đen", "Đèo Keo Nưa", "Đèo Đá Đẽo", "Đèo Tam Điệp",
    # Islands & Disaster-prone Districts
    "Lý Sơn", "Phú Quý", "Bạch Long Vĩ", "Cồn Cỏ", "Thổ Chu", "Quần đảo Hoàng Sa", "Quần đảo Trường Sa",
    "Mù Cang Chải", "Sa Pa", "Mường La", "Kỳ Sơn", "Nam Trà My", "Bắc Trà My",
    "Mai Châu", "Ngọc Linh", "Đèo Thung Khe", "Hoàng Su Phì", "Bát Xát"
]
# Pre-compile for Case-Insensitive and Verbose matching
SENSITIVE_LOCATIONS_RE = [
    re.compile(rf"(?<!\w){re.escape(loc).replace(r'\ ', r'\s+')}(?!\w)", re.IGNORECASE | re.VERBOSE) 
    for loc in SENSITIVE_LOCATIONS
]

# VIP Terms (Critical warnings/actions that bypass all filters)
VIP_TERMS = [
    # Storm / ATNĐ official bulletins
    r"tin\s*bão\s*(?:khẩn\s*cấp|số\s*\d+)",
    r"tin\s*(?:khẩn|cảnh\s*báo)\s*(?:bão|áp\s*thấp\s*nhiệt\s*đới|lũ|mưa\s*lớn|gió\s*mạnh|rét\s*đậm\s*rét\s*hại)",
    r"bão\s*(?:gần\s*biển\s*đông|đổ\s*bộ)",
    r"áp\s*thấp\s*nhiệt\s*đới\s*khẩn\s*cấp",
    r"\bATNĐ\b", r"\bATND\b",

    # Disaster risk level
    r"cảnh\s*báo\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",

    # Command / mobilization
    r"công\s*điện\s*(?:khẩn|hỏa\s*tốc|của\s*thủ\s*tướng|của\s*phó\s*thủ\s*tướng|chỉ\s*đạo|ứng\s*phó)",
    r"công\s*điện.*(?:bão|lũ|thiên\s*tai|ứng\s*phó|khẩn\s*cấp)",
    r"chỉ\s*thị.*(?:bão|lũ|thiên\s*tai|ứng\s*phó|khẩn\s*cấp)",
    r"lệnh\s*(?:sơ\s*tán|di\s*dời)\s*(?:khẩn|khẩn\s*cấp)",
    r"sơ\s*tán\s*khẩn\s*cấp",
    r"cấm\s*biển\s*khẩn\s*cấp",
    r"kêu\s*gọi\s*tàu\s*thuyền\s*(?:vào\s*bờ|về\s*nơi\s*trú\s*ẩn|không\s*ra\s*khơi)",
    r"Ban\s*chỉ\s*huy\s*PCTT\s*(?:và\s*TKCN)?",
    r"trực\s*ban\s*(?:PCTT|24\/24|phòng\s*chống\s*thiên\s*tai)",

    # Severe incident signatures
    r"vỡ\s*(?:đê|đập)(?:\s*(?:nghiêm\s*trọng|khẩn\s*cấp))?",
    r"sự\s*cố\s*(?:đê\s*điều|hồ\s*đập|đập|kè)\s*(?:nghiêm\s*trọng|khẩn\s*cấp)",
    r"cảnh\s*báo\s*lũ\s*khẩn\s*cấp",
    r"nguy\s*cơ\s*sạt\s*lở\s*(?:rất\s*cao|đặc\s*biệt\s*cao)",
    r"phát\s*hiện\s*thi\s*thể.*(?:bão|lũ|sạt\s*lở|trôi|sông|suối)",
    r"tìm\s*thấy\s*thi\s*thể.*(?:bão|lũ|sạt\s*lở|trôi|sông|suối)",
    r"cháy\s*rừng\s*(?:nghiêm\s*trọng|lan\s*rộng)|cấp\s*cháy\s*rừng\s*cấp\s*V",
    r"cảnh\s*báo\s*sóng\s*thần|báo\s*động\s*sóng\s*thần",

    # Aid / relief
    r"hỗ\s*trợ\s*khẩn\s*cấp\s*thiên\s*tai",
    r"viện\s*trợ.*thiên\s*tai",
    r"ủng\s*hộ\s*đồng\s*bào.*(?:bão|lũ|thiên\s*tai)",
    r"(?:tiếp\s*nhận|trao\s*tặng).*hỗ\s*trợ.*(?:bão|lũ|thiên\s*tai)",
    r"khắc\s*phục\s*hậu\s*quả\s*(?:thiên\s*tai|bão|lũ|ngập|sạt\s*lở)",
    r"sạt\s*lở\s*(?:nghiêm\s*trọng|gây\s*tắc|chia\s*cắt|núi)",
    r"cấm\s*(?:đường|phương\s*tiện)\s*(?:do|vì)\s*(?:sạt\s*lở|mưa\s*lũ|bão)",
    r"tàu\s*cá.*mất\s*liên\s*lạc",
    r"gặp\s*nạn\s*trên\s*biển",
    r"thương\s*vong\s*(?:lớn|nặng\s*nề|nghiêm\s*trọng)",
    r"tai\s*nạn\s*(?:thảm\s*khốc|liên\s*hoàn\s*nghiêm\s*trọng)",
    r"đoàn\s*thiện\s*nguyện\s*gặp\s*nạn",
    r"xe\s*cứu\s*trợ\s*gặp\s*nạn",
    r"xe\s*chở\s*đoàn\s*.*gặp\s*nạn",
    r"khẩn\s*trương\s*cứu\s*hộ",
    r"tàu\s*.*mắc\s*cạn",
    r"tìm\s*kiếm\s*(?:ngư\s*dân|nạn\s*nhân|người|thi\s*thể).*mất\s*tích",
    r"hỗ\s*trợ.*khắc\s*phục.*(?:thiên\s*tai|bão|lũ)",

    # Severe Risk & Priority
    r"rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*[45IV]",
    r"lũ\s*quét\s*đặc\s*biệt\s*nghiêm\s*trọng",
]
VIP_TERMS_RE = [
    re.compile(p.replace(" ", r"\s+"), re.IGNORECASE | re.VERBOSE) 
    for p in VIP_TERMS
]


@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    primary_rss: str | None = None  # Primary RSS URL
    backup_rss: str | None = None   # Backup RSS URL
    note: str | None = None
    trusted: bool | None = False
    authority_level: int = 1         # 1: Normal, 2: Trusted, 3: High Authority (Direct Gov/VTV)

GNEWS_IMPACT_KEYWORDS = [ 
    "thiệt hại","tổn thất", "đổ nhà","đổ tường", "hư hỏng","cuốn trôi", "trôi nhà","ngập nhà","vỡ đê","tràn đê",
    "vỡ bờ","chia cắt", "cô lập","mất mùa", "mất trắng","chết đuối","bị vùi lấp","người chết","tử vong","thiệt mạng", 
    "thi thể","nạn nhân","thương vong","bị thương", "trọng thương", "mất tích","mất liên lạc","tìm kiếm","sơ tán",
    "di dời","tránh trú","vào bờ", "lên bờ","về bến","cứu hộ","cứu nạn","cứu trợ","tiếp tế", 
    "hỗ trợ","trợ cấp","cứu sinh","giải cứu","tìm kiếm cứu nạn", "huy động lực lượng","xuất quân","triển khai lực lượng",
    "ứng phó","khắc phục","xử lý sự cố","sửa chữa","tu bổ","phục hồi", "tái thiết", "đánh giá thiệt hại", 
    "cảnh báo khẩn", "tin khẩn","công điện", "tình trạng khẩn cấp","tình huống khẩn cấp", "khẩn trương","gấp rút",
    "hỏa tốc","cấp bách","nguy hiểm","nguy cấp","nguy kịch", "mất an toàn","đe dọa","đe dọa nghiêm trọng","rủi ro cao",
    "nguy cơ cao", "cấm đường","cấm biển","cấm tàu thuyền","đóng cửa trường","cho nghỉ học", "nghỉ học","tạm dừng",
    "tạm ngưng","phong tỏa","cấm lưu thông","cách ly","họp khẩn", "trực ban","trực 24/24","túc trực", "ứng trực",
    "mực nước báo động", "xâm thực","sạt trượt","đứt gãy taluy","đá lăn", "tốc mái", "sập nhà", "thời tiết nguy hiểm",
    "tin dự báo", "tin cảnh báo", "tin khẩn"
]


def build_gnews_rss(domain: str, hazard_terms: List[str] | None = None, context_terms: List[str] | None = None) -> str:
    """Build Google News RSS URL as fallback."""
    hazards = hazard_terms or GNEWS_IMPACT_KEYWORDS
    
    def _quote(terms):
        return [f'"{t.strip()}"' if ' ' in t.strip() else t.strip() for t in terms]

    import random
    
    hazards = _quote(hazards)
    if len(hazards) > 15:
        hazards = random.sample(hazards, 15)

    query_parts = [f"site:{domain}", "(" + " OR ".join(hazards) + ")"]
    
    context_source = context_terms if context_terms else CONTEXT_KEYWORDS
    if context_source:
        contexts = _quote(context_source)
        if len(contexts) > 20:
            contexts = random.sample(contexts, 20)
        query_parts.append("(" + " OR ".join(contexts) + ")")
    
    query = " ".join(query_parts)
    base = "https://news.google.com/rss/search?q="
    return base + urllib.parse.quote(query) + "&hl=vi&gl=VN&ceid=VN:vi"


def load_sources_from_json(file_path: str) -> List[Source]:
    path = Path(file_path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sources = []
    for s in data.get("sources", []):
        sources.append(Source(
            name=s["name"],
            domain=s["domain"],
            primary_rss=s.get("primary_rss"),
            backup_rss=s.get("backup_rss"),
            note=s.get("note"),
            trusted=s.get("trusted", False),
            authority_level=s.get("authority_level", 2 if s.get("trusted") else 1)
        ))
    return sources

CONFIG_FILE = Path(__file__).parent.parent / "sources.json"
SOURCES = load_sources_from_json(str(CONFIG_FILE))
CONFIG = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
