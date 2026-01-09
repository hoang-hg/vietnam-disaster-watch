from dataclasses import dataclass
from typing import Literal, List
import urllib.parse
import json
from pathlib import Path
import re
import unicodedata

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
        "đổi hướng", "đi lệch", "quỹ đạo bão", "đường đi của bão",
        "di chuyển nhanh", "di chuyển chậm", "di chuyển theo hướng",
        "dịch chuyển", "bão tăng cấp", "mạnh thêm", "bão suy yếu", "áp thấp suy yếu", "suy yếu nhanh",
        "mạnh lên thành bão", "mạnh lên thành áp thấp nhiệt đới",
        "đi vào đất liền", "đổ bộ vào", "đi sát bờ", "áp sát đất liền",
        "gây mưa lớn", "gây gió mạnh", "ảnh hưởng trực tiếp", "ít khả năng ảnh hưởng",
        "vùng ảnh hưởng", "hoàn lưu gây mưa", "mưa rất to", "mưa to đến rất to",
        "giữa biển đông", "bắc biển đông", "nam biển đông", "tây bắc biển đông",
        "vịnh bắc bộ", "vịnh thái lan",
        "tên bão", "bão có tên", "bão quốc tế",
        "vùng tâm bão", "áp sát ven biển", "hoàn lưu sau bão", "gió xoáy", "phong ba",
        "chống bão", "ứng phó bão", "phòng chống bão", "chạy bão", "tránh trú bão", "mưa bão"
    ],

    # 2) Lũ lụt (Flood)
    "flood": [
        "lũ lụt", "ngập lụt", "ngập úng", "lũ dâng", "đỉnh lũ", "mực nước báo động",
        "vỡ đê", "tràn đê", "xả lũ", "hồ chứa", "thủy điện", "xả tràn", "nước sông dâng",
        "ngập sâu", "ngập nhà", "ngập phố", "chia cắt", "cô lập", "vỡ đập", "sự cố đập", "vỡ hồ", "sự cố hồ chứa",
        "vượt báo động", "đạt đỉnh", "nước lụt", "triều cường kết hợp", "ngập triều cường",
        "mực nước trên báo động", "lũ báo động 3", "lũ lịch sử", "ngập lụt cục bộ", "vùng trũng thấp",
        "nước dâng", "triều cường",
        "lũ quét", "lũ ống", "nước lũ", "lũ lớn", "lũ dữ", "lũ cao", "rốn lũ",
        "lật ghe", "chìm ghe", "lật thuyền", "chìm thuyền", "chìm tàu", "trôi dạt",
        "di dời", "sơ tán", "phong tỏa", "uy hiếp",
        "sập bờ kè", "sập cầu", "cuốn trôi",
        "mạch đùn", "mạch sủi", "vùng rốn lũ", "lũ", "vùng lũ", "chạy lũ", "đồng bào vùng lũ"
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
        "mưa diện rộng", "mưa cục bộ", "gió giật mạnh", "giông tố", "giông cực mạnh", "gió rít", "trắng trời",
        "tốc mái", "mưa trái mùa"
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
        "xói lở", "sạt lở bờ sông", "sạt lở bờ biển", "hàm ếch", "mương xói", "rãnh xói", "xâm thực", "xói mòn",
        "sạt lở đê", "sạt lở kè", "sạt lở bờ"
    ],

    # 16) Tin cảnh báo, dự báo (Warning/Forecast)
    "warning_forecast": [
        "bản tin dự báo", "tin cảnh báo", "dự báo thời tiết", "cảnh báo thiên tai",
        "tin cuối cùng", "tin phát đi", "bản tin cập nhật", "dự báo khí tượng",
        "trung tâm dự báo", "bản tin khẩn cấp", "thiên tai",
        "thông báo khẩn", "điểm tin thiên tai", "đài khí tượng", "dự báo khí hậu", "cảnh báo cực đoan",
        "cảnh báo lũ", "cảnh báo sạt lở", "cảnh báo ngập lụt", "tin bão khẩn cấp",
        "lệnh cấm biển", "cấm biển", "cấm đường", "cấm phương tiện", "tiến sát đất liền", "đề phòng"
    ],

    "recovery": [
        "khắc phục hậu quả", "khắc phục sự cố", "khôi phục giao thông", "thống kê thiệt hại",
        "ủng hộ đồng bào", "cứu trợ", "tiếp tế", "dọn dẹp sau bão", "viện trợ", "hỗ trợ khẩn cấp",
        "ổn định đời sống", "khôi phục sản xuất", "tái thiết", "hỗ trợ dân sinh", "bình ổn thị trường", "hồi sinh",
        "xử lý môi trường", "vệ sinh sau bão", "nước rút",
        "huy động lực lượng", "xuyên đêm", "trắng đêm", "căng mình",
        "tiếp tế", "khẩn trương", "thị sát", "phân luồng", "thông xe",
        "nghỉ học", "cho học sinh nghỉ", "dừng học",
        "tình trạng khẩn cấp", "công bố khẩn cấp", "lệnh khẩn cấp",
        "tìm kiếm", "cứu nạn", "cứu hộ", "mất tích", "xuất quân", "điều động", "tái định cư",
        "giải cứu", "mắc kẹt", "huy động", "hàng cứu trợ", "tìm kiếm cứu nạn", "trục vớt",
        "giúp dân", "chiến sĩ", "gặt lúa", "chạy lũ", "vùng lũ", "đồng bào", "trắng đêm", "xuyên đêm"
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
  "tử vong", "thiệt mạng", "thương vong", "bị thương", "trọng thương", "chết người",
  "mất tích", "mất liên lạc", "mắc kẹt", "bị kẹt",
  "tìm kiếm", "tìm kiếm cứu nạn", "cứu nạn", "cứu hộ", "giải cứu", "giúp dân", "chiến sĩ", "gặt lúa", "chạy lũ", "vùng lũ", "đồng bào",

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
  
  # DIRECTIVES / PREPAREDNESS (Added)
  "công điện", "chỉ thị", "văn bản hỏa tốc", "ý kiến chỉ đạo", "thông báo khẩn",
  "huy động", "triển khai", "bố trí", "xung kích", "ứng trực", "trực ban", "ra quân", "xuất quân",
  "đảm bảo an toàn", "tuyệt đối an toàn", "chủ động ứng phó", "phương án", "kịch bản",
  "hồ đập", "thủy lợi", "đê điều", "kè", "xung yếu",
  "lương thực", "nhu yếu phẩm", "dự trữ", "tại chỗ"
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
    "Mai Châu", "Ngọc Linh", "Đèo Thung Khe", "Hoàng Su Phì", "Bát Xát",
    # Additional Infrastructure
    "Thủy điện Trị An", "Thủy điện Sơn La", "Thủy điện Hòa Bình", "Thủy điện Thác Bà",
    "Thủy điện Yaly", "Thủy điện Bản Vẽ", "Cầu Bãi Cháy", "Cầu Tân Vũ", "Cầu Cần Thơ",
    "Cảng Lạch Huyện", "Cảng Cái Mép", "Sân bay Vân Đồn", "Sân bay Long Thành",
    "Hầm Hải Vân", "Hầm Đèo Cả", "Đê biển Tây", "Đê biển Gò Công"
]

INTERNATIONAL_LOCATIONS = [
    "Nhật Bản", "Hàn Quốc", "Trung Quốc", "Đài Loan", "Philippines", "Thái Lan", "Lào", "Campuchia", "Myanmar", "Malaysia", 
    "Singapore", "Indonesia", "Mỹ", "Hoa Kỳ", "Nga", "Đức", "Pháp", "Anh", "Ý", "Italia", "Tây Ban Nha", "Úc", "Australia", 
    "Canada", "Ấn Độ", "Thổ Nhĩ Kỳ", "Maroc", "Nepal", "Pakistan", "Afghanistan", "Iran", "Iraq", "Israel", "Palestine", 
    "Ukraina", "Ukrainia", "Thụy Sĩ", "Thụy Điển", "Na Uy", "Phần Lan", "Đan Mạch", "Hà Lan", "Bỉ", "Áo", "Hy Lạp", "Bồ Đào Nha", 
    "Bắc Triều Tiên", "Mông Cổ", "Kazakhstan", "Uzbekistan", "Ả Rập Xê Út", "UAE", "Ai Cập", "Nam Phi", "Nigeria", "Kenya", 
    "Ethiopia", "Brazil", "Argentina", "Mexico", "Colombia", "Chile", "New Zealand"
]

# Pre-compile for Case-Insensitive and Verbose matching
def _build_mega_loc_re(locations: List[str]):
    escaped_list = [re.escape(loc).replace(r'\ ', r'\s+') for loc in locations]
    # Use capturing group ( ) instead of (?: ) for findall support
    pattern = rf"(?<!\w)({'|'.join(escaped_list)})(?!\w)"
    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)

SENSITIVE_LOCATIONS_RE = _build_mega_loc_re(SENSITIVE_LOCATIONS)
INTERNATIONAL_LOCATIONS_RE = _build_mega_loc_re(INTERNATIONAL_LOCATIONS)

# VIP Terms (Critical warnings/actions that bypass all filters)
VIP_TERMS = [
    # Storm / ATNĐ official bulletins
    r"tin\s*bão\s*(?:khẩn\s*cấp|số\s*\d+)",
    r"tin\s*(?:khẩn|cảnh\s*báo)\s*(?:bão|áp\s*thấp\s*nhiệt\s*đới|lũ|mưa\s*lớn|gió\s*mạnh|rét\s*đậm\s*rét\s*hại|nắng\s*nóng|hạn\s*hán)",
    r"bão\s*(?:gần\s*biển\s*đông|đổ\s*bộ)",
    r"áp\s*thấp\s*nhiệt\s*đới\s*khẩn\s*cấp",
    r"\bATNĐ\b", r"\bATND\b",

    # Disaster risk level
    r"cảnh\s*báo\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",

    # Command / mobilization (Authorized Disaster context)
    r"công\s*điện\s*(?:khẩn|hỏa\s*tốc|của\s*thủ\s*tướng|của\s*phó\s*thủ\s*tướng)\s*về\s*(?:bão|lũ|thiên\s*tai|ứng\s*phó|ngập|sạt\s*lở|khắc\s*phục|tìm\s*kiếm|nắng\s*nóng|rét\s*hại|hạn\s*hán|cháy\s*rừng)",
    r"chỉ\s*thị.*(?:bão|lũ|thiên\s*tai|ứng\s*phó|khẩn\s*cấp)",
    r"lệnh\s*(?:sơ\s*tán|di\s*dời)\s*(?:khẩn|khẩn\s*cấp).*(?:bão|lũ|ngập|sạt|thiên\s*tai|vỡ\s*đê|hồ\s*đập|cháy\s*rừng)",
    r"sơ\s*tán\s*khẩn\s*cấp.*(?:bão|lũ|sạt|ngập|lụt|cháy\s*rừng|thiên\s*tai)",
    r"công\s*bố\s*tình\s*huống\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|sạt\s*lở|cháy\s*rừng)",
    r"ban\s*bố\s*tình\s*trạng\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|sạt\s*lở|cháy\s*rừng|hạn\s*mặn)",
    r"cấm\s*biển\s*(?:khẩn\s*cấp|ngay)",
    r"kêu\s*gọi\s*tàu\s*thuyền\s*(?:vào\s*bờ|về\s*nơi\s*trú\s*ẩn|không\s*ra\s*khơi).*(?:bão|áp\s*thấp|gió\s*mạnh)",
    r"Ban\s*chỉ\s*huy\s*PCTT\s*(?:và\s*TKCN)?",
    r"trực\s*ban\s*(?:PCTT|phòng\s*chống\s*thiên\s*tai)",
    r"trực\s*ban\s*24\/24.*(?:bão|lũ|thiên\s*tai|áp\s*thấp|mưa\s*lớn|ngập\s*lụt)",

    # Severe incident signatures (Must be disaster related)
    r"vỡ\s*(?:đê|đập|hồ\s*chứa|kè)(?:\s*(?:nghiêm\s*trọng|khẩn\s*cấp|do\s*mưa\s*lũ))?",
    r"hồ\s*chứa\s*(?:(?!\.).)*\s*(?:vỡ|xả\s*lũ\s*khẩn\s*cấp)",
    r"sự\s*cố\s*(?:đê\s*điều|hồ\s*đập|đập|hồ|kè)\s*(?:nghiêm\s*trọng|khẩn\s*cấp|do\s*mưa\s*lũ)",
    r"sự\s*cố\s*cống\s*(?:nghiêm\s*trọng|khẩn\s*cấp).*do\s*(?:mưa|lũ|triều\s*cường)",
    r"cảnh\s*báo\s*(?:lũ|lũ\s*quét|sạt\s*lở)\s*khẩn\s*cấp",
    r"nguy\s*cơ\s*sạt\s*lở\s*(?:rất\s*cao|đặc\s*biệt\s*cao|đất|núi)",
    r"phát\s*hiện\s*thi\s*thể.*(?:bão|lũ|sạt\s*lở|vùi\s*lấp|lũ\s*quét)",
    r"tìm\s*thấy\s*thi\s*thể.*(?:bão|lũ|sạt\s*lở|vùi\s*lấp|lũ\s*quét)",
    r"cháy\s*rừng\s*(?:nghiêm\s*trọng|lan\s*rộng|lớn)|cấp\s*cháy\s*rừng\s*cấp\s*V",
    r"cảnh\s*báo\s*sóng\s*thần|báo\s*động\s*sóng\s*thần|sóng\s*thần\s*tấn\s*công",

    # Aid / relief (Explicit disaster context)
    r"hỗ\s*trợ\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|ngập|sạt|hạn\s*mặn|rét\s*hại|cháy\s*rừng)",
    r"viện\s*trợ.*(?:thiên\s*tai|bão|lũ|sạt|hạn\s*hán)",
    r"ủng\s*hộ\s*đồng\s*bào.*(?:bão|lũ|thiên\s*tai|vùng\s*sạt|bị\s*thiệt\s*hại)",
    r"(?:tiếp\s*nhận|trao\s*tặng).*hỗ\s*trợ.*(?:bão|lũ|thiên\s*tai|sạt\s*lở)",
    r"khắc\s*phục\s*hậu\s*quả\s*(?:sau\s*)?(?:thiên\s*tai|bão|lũ|mưa\s*bão|ngập|sạt\s*lở|dông\s*lốc|cháy\s*rừng|hạn\s*mặn)",
    r"sạt\s*lở\s*(?:nghiêm\s*trọng|gây\s*tắc|chia\s*cắt|núi|đất|bờ\s*sông|bờ\s*biển)",
    r"cấm\s*(?:đường|phương\s*tiện)\s*(?:do|vì)\s*(?:sạt\s*lở|mưa\s*lũ|bão|ngập\s*sâu|tuyết|băng\s*giá|cháy\s*rừng)",
    r"tàu\s*cá.*mất\s*liên\s*lạc.*(?:bão|gió|sóng|biển\s*động|áp\s*thấp)",
    r"gặp\s*nạn\s*trên\s*biển.*(?:do|trong)\s*(?:bão|sóng|gió|áp\s*thấp)",
    r"thương\s*vong\s*(?:lớn|nặng\s*nề|nghiêm\s*trọng).*(?:do|vì)\s*(?:thiên\s*tai|bão|lũ|sạt|lốc|mưa\s*đá)",
    r"đoàn\s*thiện\s*nguyện\s*gặp\s*nạn.*(?:vùng\s*lũ|đường\s*sạt)",
    r"lũ\s*lịch\s*sử|lũ\s*đặc\s*biệt\s*lớn",
    r"sập\s*hầm\s*lò.*(?:do|vì)\s*(?:mưa|lũ|sạt)",
    r"sạt\s*lở.*vùi\s*lấp",
    r"xe\s*cứu\s*trợ\s*gặp\s*nạn.*(?:vùng\s*lũ|do\s*thiên\s*tai)",
    r"chết\s*người\s*(?:do|vì|trong)\s*(?:lũ|bão|ngập|sạt|vỡ|thiên\s*tai|lốc|sét|rét\s*đậm)",
    r"(?:làm|khiến)\s*(?:\d+|nhiều)\s*người\s*(?:chết|tử\s*vong|thiệt\s*mạng).*(?:do|vì|trong)\s*(?:bão|lũ|sạt|thiên\s*tai|ngập|lốc|sét|vỡ)",
    r"xe\s*chở\s*đoàn\s*.*gặp\s*nạn.*(?:vùng\s*lũ|đi\s*cứu\s*trợ)",
    r"khẩn\s*trương\s*cứu\s*hộ.*(?:nạn\s*nhân|người\s*dân).*(?:bão|lũ|sạt|ngập|thiên\s*tai)",
    r"tàu\s*.*mắc\s*cạn.*(?:do|trong)\s*(?:bão|sóng|gió|áp\s*thấp)",
    r"tìm\s*kiếm\s*(?:ngư\s*dân|nạn\s*nhân|người|thi\s*thể).*mất\s*tích.*(?:do|trong|sau)\s*(?:bão|lũ|sạt|lốc|sóng|mưa\s*lũ)",
    r"hỗ\s*trợ.*khắc\s*phục.*(?:thiên\s*tai|bão|lũ|sạt|ngập|hạn\s*mặn|cháy\s*rừng)",

    # Severe Risk & Priority
    r"rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*[45IV]",
    r"lũ\s*quét\s*đặc\s*biệt\s*nghiêm\s*trọng",
]
VIP_TERMS_RE = re.compile("|".join(rf"(?:{p})" for p in VIP_TERMS), re.IGNORECASE | re.VERBOSE)


# Red Alert (High-danger warning) keywords
DANGER_SIGS = [
    r"khẩn\s*cấp", r"đặc\s*biệt\s*nguy\s*hiểm", r"cực\s*kỳ\s*nguy\s*hiểm",
    r"siêu\s*bão", r"lũ\s*lịch\s*sử", r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)?\s*[345]",
    r"đặc\s*biệt\s*lớn", r"nguy\s*hiểm\s*cao", r"báo\s*động\s*đỏ", r"cảnh\s*báo\s*đỏ",
    r"khốc\s*liệt", r"dữ\s*dội", r"thảm\s*khốc", r"tang\s*thương", r"trắng\s*trời"
]
DANGER_RE = re.compile("|".join(rf"(?:{p})" for p in DANGER_SIGS), re.IGNORECASE | re.VERBOSE)
# High Priority Keywords indicative of high-impact events

HAZARD_ANCHOR = r"(?:bão|áp\s*thấp|lũ|ngập|sạt\s*lở|nắng\s*nóng|hạn\s*hán|xâm\s*nhập\s*mặn|gió\s*mạnh|sương\s*mù|cháy\s*rừng|động\s*đất|sóng\s*thần|triều\s*cường|nước\s*dâng|mưa\s*lớn|chìm\s*tàu|tài\s*cá\s*gặp\s*nạn|thuyền\s*viên|mất\s*tích)"
PCTT_ANCHOR   = r"(?:phòng\s*chống\s*thiên\s*tai|PCTT|TKCN|tìm\s*kiếm\s*cứu\s*nạn)"

DISASTER_CONTEXT = [
  r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai(?:\s*cấp\s*\d+)?",
  r"cảnh\s*báo\s*(?:thiên\s*tai|rủi\s*ro\s*thiên\s*tai)",
  r"tình\s*huống\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|sạt\s*lở)",
  # B) Ứng phó khẩn cấp (đặc thù)
  r"sơ\s*tán(?:\s*khẩn\s*cấp)?.*(?:bão|lũ|sạt|ngập|lụt|thiên\s*tai|cháy\s*rừng)",
  r"di\s*dời(?:\s*khẩn\s*cấp)?.*(?:bão|lũ|sạt|ngập|vùng\s*thiên\s*tai)",
  r"cứu\s*hộ.*(?:thiên\s*tai|bão|lũ|sạt|ngập)", r"cứu\s*nạn.*(?:thiên\s*tai|bão|lũ|sạt|ngập)",
  r"tìm\s*kiếm\s*cứu\s*nạn.*(?:trên\s*biển|vùng\s*lũ|sạt\s*lở)",
  r"neo\s*đậu\s*tránh\s*trú.*(?:bão|áp\s*thấp)",
  r"cấm\s*ra\s*khơi|cấm\s*biển.*(?:bão|áp\s*thấp|gió\s*mạnh)",
  r"đóng\s*đường|cấm\s*đường|cấm\s*lưu\s*thông|phân\s*luồng.*(?:do|vì)\s*(?:bão|lũ|sạt|ngập)",
  r"phong\s*tỏa\s*khu\s*vực\s*nguy\s*hiểm.*(?:sạt\s*lở|lũ|ngập)",
  r"lực\s*lượng\s*xung\s*kích.*phòng\s*chống\s*thiên\s*tai|trực\s*ban.*PCTT",
  # C) Tác động/thiệt hại (đặc thù)
  r"thiệt\s*hại|tổn\s*thất.*do\s*thiên\s*tai",
  r"thương\s*vong|tử\s*vong|thiệt\s*mạng.*(?:do|vì)\s*(?:bão|lũ|sạt|thiên\s*tai|lốc|sét)",
  r"mất\s*tích|mất\s*liên\s*lạc.*(?:do|trong)\s*(?:bão|lũ|sạt|lốc)",
  r"bị\s*thương|nhập\s*viện|cấp\s*cứu.*(?:do|trong)\s*(?:bão|lũ|sạt|lốc|sập\s*nhà)",
  r"chia\s*cắt|cô\s*lập.*(?:do|bởi)\s*(?:lũ|ngập|sạt)",
  r"sập\s*cầu|đứt\s*đường|sạt\s*lở\s*đường.*(?:do|vì)\s*(?:mưa|lũ|sạt)",
  r"vỡ\s*đê|tràn\s*đê|vỡ\s*đập",
  r"cuốn\s*trôi|vùi\s*lấp.*(?:do|bởi)\s*(?:lũ|sạt|đất|nước)",
  r"hư\s*hỏng\s*nặng|tốc\s*mái\s*hoàn\s*toàn|sạt\s*lở\s*nghiêm\s*trọng",
  r"thiệt\s*hại\s*về\s*người|thiệt\s*hại\s*tài\s*sản.*do\s*thiên\s*tai",
  r"ước\s*tính\s*thiệt\s*hại.*do\s*bão",
  r"tàu\s*gặp\s*nạn|thuyền\s*viên\s*mất\s*tích|hỗ\s*trợ\s*lai\s*dắt.*(?:do|trong)\s*(?:bão|sóng|gió)",
  r"tín\s*hiệu\s*cầu\s*cứu|bị\s*sóng\s*đánh\s*chìm",
  r"gia\s*cố\s*nhà\s*cửa|chằng\s*chống|cắt\s*tỉa\s*cây.*phòng\s*bão",
  r"gia\s*cố\s*lồng\s*bè|đưa\s*tàu\s*thuyền\s*vào\s*bờ",
  r"lệnh\s*cấm\s*biển",
  r"mất\s*điện\s*diện\s*rộng|ngừng\s*cấp\s*điện.*do\s*bão",
  r"ngừng\s*cấp\s*nước|gián\s*đoạn\s*cấp\s*nước.*do\s*thiên\s*tai",
  # D) Chỉ báo thủy văn/khí tượng mang tính “bản tin thiên tai”
  r"báo\s*động\s*(?:1|2|3|I|II|III)|vượt\s*báo\s*động",
  r"mực\s*nước|đỉnh\s*lũ|lũ\s*lên|lũ\s*rút",
  r"lượng\s*mưa|tổng\s*lượng\s*mưa|mưa\s*lớn\s*diện\s*rộng",
  r"triều\s*cường|đỉnh\s*triều",
  r"cấp\s*gió|gió\s*giật|beaufort",
  r"độ\s*mặn|ranh\s*mặn|độ\s*mặn\s*\d+\s*(?:‰|%o|g\/l)",
  # E) Từ khóa phục hồi sau thiên tai (recovery – đặc thù)
  r"khắc\s*phục\s*hậu\s*quả|khẩn\s*trương\s*khắc\s*phục.*(?:bão|lũ|thiên\s*tai|sạt)",
  r"khôi\s*phục\s*(?:giao\s*thông|cấp\s*điện|cấp\s*nước|liên\s*lạc).*sau\s*bão",
  r"thông\s*tuyến|khơi\s*thông|giải\s*tỏa|dọn\s*dẹp|thu\s*dọn|nạo\s*vét.*sau\s*mưa\s*lũ",
  r"cứu\s*trợ|tiếp\s*tế|cấp\s*phát|phát\s*lương\s*thực|nhu\s*yếu\s*phẩm.*vùng\s*lũ",
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

# PRE-COMPILED STAGE DETECTORS
FORECAST_SIGS = DISASTER_GROUPS["warning_forecast"]
RECOVERY_KEYWORDS = DISASTER_GROUPS["recovery"]
INCIDENT_SIGS = [item for k, v in DISASTER_GROUPS.items() if k not in ("warning_forecast", "recovery") for item in v]

# Join patterns into a single mega-regex for performance
RE_FORECAST = re.compile("|".join(rf"(?:{p})" for p in FORECAST_SIGS), re.IGNORECASE)
RE_INCIDENT = re.compile("|".join(rf"(?:{p})" for p in INCIDENT_SIGS), re.IGNORECASE)
RE_RECOVERY = re.compile("|".join(rf"(?:{p})" for p in RECOVERY_KEYWORDS), re.IGNORECASE)

# High-priority keywords that indicate severe events
HIGH_PRIORITY_KEYWORDS = [
    r"lũ\s*quét", r"lũ\s*ống", r"vỡ\s*đê", r"vỡ\s*đập", r"siêu\s*bão",
    r"sạt\s*lở\s*đất", r"sóng\s*thần", r"động\s*đất\s*mạnh", r"nước\s*dâng\s*do\s*bão",
    r"triều\s*cường\s*kỷ\s*lục", r"công\s*điện\s*(?:khẩn|hỏa\s*tốc|chỉ\s*đạo|ứng\s*phó|số).*thiên\s*tai",
    r"ngập\s*lụt\s*nghiêm\s*trọng", r"sạt\s*lở\s*đất\s*vùi\s*lấp", r"mưa\s*lũ\s*gây\s*ngập",
    r"lệnh\s*sơ\s*tán.*(?:bão|lũ|sạt)", r"tình\s*trạng\s*khẩn\s*cấp.*thiên\s*tai", r"chỉ\s*thị\s*khẩn.*ứng\s*phó",
    r"bị\s*cô\s*lập.*(?:do|bởi)\s*(?:lũ|ngập|sạt)", r"bị\s*chia\s*cắt.*(?:do|bởi)\s*(?:lũ|ngập|sạt)", 
    r"phong\s*tỏa\s*khẩn\s*cấp.*khu\s*vực\s*(?:sạt|lũ|ngập)",
    r"(?:thủ\s*tướng|phó\s*thủ\s*tướng)\s*(?:chỉ\s*đạo|yêu\s*cầu|ký\s*công\s*điện).*thiên\s*tai",
    r"khẩn\s*trương\s*ứng\s*phó.*(?:bão|lũ|sạt|ngập|thiên\s*tai)", 
    r"thuyền\s*viên\s*mất\s*tích.*(?:do|trong)\s*(?:bão|sóng)", 
    r"tàu\s*cá\s*mất\s*tích.*(?:do|trong)\s*(?:bão|sóng)", 
    r"chìm\s*tàu\s*trên\s*biển.*(?:do|trong)\s*(?:bão|sóng|gió)", 
    r"sụt\s*lún\s*nghiêm\s*trọng", r"nguy\s*cơ\s*mất\s*an\s*toàn.*hồ\s*đập",
    r"di\s*dời\s*khẩn\s*cấp.*khỏi\s*vùng\s*(?:sạt|lũ|nguy\s*hiểm)", 
    r"cô\s*lập\s*hoàn\s*toàn.*(?:do|bởi)\s*(?:lũ|ngập|sạt)", r"phong\s*tỏa\s*hiện\s*trường.*sạt\s*lở", 
    r"chia\s*cắt\s*giao\s*thông.*(?:do|bởi)\s*(?:lũ|ngập|sạt)", 
    r"huy\s*động\s*lực\s*lượng\s*cứu\s*hộ.*thiên\s*tai",
    r"sạt\s*lở\s*nghiêm\s*trọng", r"lũ\s*lên\s*nhanh", r"ngập\s*sâu\s*diện\s*rộng",
    r"nước\s*dâng\s*cao", r"hỗ\s*trợ\s*khẩn\s*cấp.*vùng\s*lũ", r"khắc\s*phục\s*hậu\s*quả.*thiên\s*tai", 
    r"cứu\s*trợ\s*khẩn\s*cấp.*vùng\s*lũ", r"nhu\s*yếu\s*phẩm.*vùng\s*lũ", r"dự\s*báo\s*bão",
    r"cấm\s*biển", r"lệnh\s*cấm\s*biển", r"cấm\s*đường", r"cấm\s*phương\s*tiện", 
    r"giải\s*cứu\s*thành\s*công.*khỏi\s*vùng\s*lũ", r"người\s*mắc\s*kẹt.*trong\s*lũ", r"nạn\s*nhân\s*mắc\s*kẹt.*sạt\s*lở", 
    r"ủng\s*hộ\s*đồng\s*bào.*lũ\s*lụt", r"thiệt\s*hại\s*do\s*bão", r"điều\s*tiết\s*hồ", r"xả\s*lũ", 
    r"mắc\s*cạn.*do\s*bão", r"tàu\s*gặp\s*nạn.*do\s*bão", r"tái\s*thiết.*(?:thiên\s*tai|bão|lũ)",
    r"sạt\s*lở\s*núi", r"tin\s*bão", r"tin\s*lũ", r"tin\s*mưa\s*lớn", r"mưa\s*lũ",
    r"xé\s*đường.*do\s*lũ", r"hàm\s*ếch.*sạt\s*lở", r"cứu\s*\d+\s*người.*trong\s*lũ", r"rốn\s*lũ", r"dựng\s*lại\s*nhà.*sau\s*bão", 
    r"cứu\s*dân.*vùng\s*lũ", r"cứu\s*người.*trong\s*lũ", r"vùng\s*tâm\s*bão", r"lưu\s*thông\s*trở\s*lại.*sau\s*bão",
    r"sơ\s*tán\s*(?:người\s*)?dân", r"di\s*dời\s*(?:người\s*)?dân", r"xả\s*lũ\s*khẩn\s*cấp", r"vận\s*hành\s*xả\s*lũ",
    r"chiến\s*dịch\s*quang\s*trung", r"hỗ\s*trợ\s*nhà\s*ở.*sau\s*bão", r"nhà\s*chống\s*lũ", r"nhà\s*phao",
    r"ban\s*chỉ\s*huy\s*pctt", r"hỗ\s*trợ\s*đồng\s*bào\s*vùng\s*lũ",
    r"công\s*bố\s*tình\s*huống.*khẩn\s*cấp", r"thông\s*tuyến|tìm\s*kiếm.*mất\s*tích.*do\s*lũ", r"hồi\s*sinh.*vùng\s*lũ", 
    r"ngập\s*lụt\s*đặc\s*biệt\s*nguy\s*hiểm", r"sập\s*(?:nhà|cầu|cống|đê|kè|tường).*(?:do|trong)\s*(?:bão|lũ|sạt)", 
    r"tốc\s*mái", r"vùi\s*lấp", r"cuốn\s*trôi", r"mất\s*tích.*do\s*lũ", r"người\s*chết.*do\s*bão", 
    r"tử\s*vong.*do\s*thiên\s*tai", r"ngập\s*úng", r"thiệt\s*hại\s*nặng.*do\s*bão", r"họp\s*khẩn.*chỉ\s*đạo\s*bão", 
    r"ban\s*bố\s*tình\s*trạng\s*khẩn\s*cấp.*thiên\s*tai", r"mưa\s*trái\s*mùa", r"lật\s*(?:ghe|thuyền|xuồng).*(?:do|trong)\s*lũ", 
    r"chìm\s*(?:ghe|thuyền|xuồng|tàu).*(?:do|trong)\s*bão", r"tai\s*nạn\s*trên\s*biển.*do\s*bão", r"lũ\s*cuốn", 
    r"sạt\s*lở\s*đất\s*vùi\s*lấp", r"cô\s*lập\s*do\s*mưa\s*lũ", r"chia\s*cắt\s*giao\s*thông.*do\s*lũ",
    r"hư\s*hỏng\s*nghiêm\s*trọng\s*(?:đê|kè|hồ|đập|cầu|cống)",
    r"thủng\s*(?:thân|đáy)\s*tàu.*do\s*sóng", r"tàu\s*cá\s*gặp\s*nạn.*do\s*bão", r"chống\s*rét\s*cho\s*(?:gia\s*súc|vật\s*nuôi)",
    r"băng\s*giá\s*phủ\s*trắng", r"mưa\s*to\s*ngập\s*úng",
    r"người\s*dân\s*bị\s*cô\s*lập", r"chia\s*cắt\s*do\s*mưa\s*lũ", r"học\s*sinh\s*nghỉ\s*học.*tránh\s*bão",
    r"tàu\s*cá\s*(?:chìm|mất\s*tích|dạt).*do\s*bão", r"thi\s*thể\s*ngư\s*dân.*sau\s*bão", r"thông\s*tuyến\s*sạt\s*lở",
    r"di\s*dời.*tái\s*định\s*cư", r"axit\s*bị\s*lũ\s*cuốn", r"người\s*chết\s*do\s*mưa\s*lũ",
    r"nghĩa\s*tình\s*(?:vùng|nơi)\s*lũ", r"cứu\s*trợ\s*người\s*dân\s*bị\s*cô\s*lập",
    r"xây\s*nhà\s*.*vùng\s*lũ", r"thi\s*thể\s*.*đã\s*được\s*tìm\s*thấy.*trong\s*lũ", r"khắc\s*phục\s*.*sạt\s*lở",
    r"cô\s*lập\s*.*hộ\s*dân", r"gãy\s*đôi\s*cầu.*do\s*lũ", r"mất\s*tích\s*trên\s*biển.*do\s*bão",
    r"lũ\s*tràn\s*qua\s*đập", r"hư\s*hỏng\s*mặt\s*đường.*do\s*mưa\s*lũ",
    r"xe\s*máy\s*hư\s*hỏng.*do\s*ngập", r"hàng\s*nghìn\s*xe.*ngập\s*nước", 
    r"ô\s*tô\s*hư\s*hỏng.*do\s*ngập", r"phương\s*tiện\s*hư\s*hỏng.*do\s*thiên\s*tai",
    # GENUINE DISASTER RECOVERY & INCIDENTS (Boosted)
    r"nứt\s*toác.*di\s*dời", r"lũ.*cô\s*lập.*cứu\s*dân",
    r"cuộc\s*gọi\s*cầu\s*cứu.*trong\s*lũ", r"tiếp\s*tế\s*thực\s*phẩm.*cô\s*lập",
    r"mưa\s*ngập\s*lịch\s*sử", r"giải\s*cứu.*mắc\s*kẹt.*lũ",
    r"xuyên\s*đêm.*cứu.*dân.*vùng\s*lũ", r"thiệt\s*hại.*do\s*thiên\s*tai",
    r"khắc\s*phục.*hư\s*hỏng.*cầu.*do\s*lũ", r"sạt\s*lở.*thiệt\s*mạng",
    r"bờ\s*kè.*đổ\s*sập", r"ngập\s*cầu.*ách\s*tắc",
    r"sạt\s*lở.*cô\s*lập", r"tìm\s*thấy.*thi\s*thể.*đuối\s*nước.*trong\s*lũ",
    r"trao\s*quà\s*.*thiệt\s*hại\s*.*(?:mưa|lũ|bão)", r"trường\s*học\s*.*thiệt\s*hại\s*.*(?:vùng|do)\s*lũ",
    r"lốc\s*xoáy\s*.*thiệt\s*hại", r"khắc\s*phục\s*.*khẩn\s*cấp\s*.*kè",
    r"tìm\s*kiếm\s*.*mất\s*tích\s*.*tàu\s*cá.*do\s*bão", r"điểm\s*tiếp\s*nhận\s*.*hàng\s*cứu\s*trợ.*bão",
    r"tái\s*thiết\s*.*khu\s*tái\s*định\s*cư", r"đảm\s*bảo\s*.*giao\s*thông\s*.*(?:mưa|lũ)",
    r"hỗ\s*trợ\s*.*người\s*dân\s*.*bị\s*thiệt\s*hại.*do\s*thiên\s*tai", r"chủ\s*động\s*ứng\s*phó\s*.*mưa\s*lũ",
    # ADDITIONAL BOOSTED RECOVERY PHRASES
    r"thiên\s*tai.*gây\s*thiệt\s*hại.*tỷ\s*đồng", r"khắc\s*phục.*hồ\s*đập.*hư\s*hỏng",
    r"chốt\s*chặn.*khu\s*vực.*xung\s*yếu", r"tổng\s*đài.*tiếp\s*nhận.*thiên\s*tai",
    r"hỗ\s*trợ.*người\s*dân.*vùng\s*lũ",
    r"bị\s*cô\s*lập.*do\s*lũ", r"chia\s*cắt\s*giao\s*thông.*do\s*sạt", r"rốn\s*lũ",
    r"tiếp\s*tế\s*lương\s*thực.*vùng\s*lũ", r"khẩn\s*cấp\s*ứng\s*phó.*bão",
    r"tin\s*bão", r"cảnh\s*báo\s*ngập\s*lụt", r"nối\s*lại\s*giao\s*thông.*sau\s*bão",
    r"mưa\s*lớn\s*gây\s*ngập", r"ngập\s*sâu.*cô\s*lập",
    r"hàng\s*ngàn\s*hộ\s*dân.*cô\s*lập.*do\s*lũ", r"xuyên\s*đêm.*cứu.*hộ",
    r"áp\s*thấp\s*nhiệt\s*đới", r"gió\s*mùa\s*đông\s*bắc",
    # JAN 7 - PART 3 (LOG ANALYSIS BOOSTS)
    r"di\s*dời\s*dân.*sạt\s*lở", r"khắc\s*phục\s*sạt\s*lở",
    r"khắc\s*phục\s*thủy\s*lợi", r"mất\s*nhà\s*do\s*thiên\s*tai",
    # JAN 9 - REFINEMENT (User Request)
    r"hối\s*hả\s*tránh\s*bão", r"đưa\s*thuyền\s*lên\s*bờ", r"neo\s*đậu\s*tàu\s*thuyền", r"trú\s*tránh\s*bão",
    r"hố\s*tử\s*thần", r"sụt\s*lún\s*đất", r"sụt\s*lún\s*nghiêm\s*trọng",
    r"chi\s*viện\s*.*(?:bão|lũ|thiên\s*tai|vùng\s*lũ)", r"xe\s*chở\s*hàng\s*cứu\s*trợ", r"xe\s*cứu\s*trợ",
    r"hàng\s*cứu\s*trợ", r"thiệt\s*hại\s*do\s*sạt\s*lở", r"sạt\s*lở\s*gây\s*ách\s*tắc",
    r"khẩn\s*trương\s*khắc\s*phục", r"dốc\s*toàn\s*lực",
    r"ngập\s*lụt\s*cục\s*bộ", r"mưa\s*lớn\s*diện\s*rộng",
    r"hỗ\s*trợ\s*giống.*vùng\s*lũ", r"tặng\s*cano.*vùng\s*lũ",
    r"bão.*quần\s*thảo", r"lũ.*vượt\s*mốc",
    r"chủ\s*động\s*ứng\s*phó.*rét",
    r"khắc\s*phục.*sạt\s*lở", r"xử\s*lý.*sự\s*cố.*sạt\s*lở",
    r"vỡ\s*kênh\s*mương", r"xây\s*dựng\s*lại\s*nhà.*sau\s*bão",
    r"tìm\s*kiếm.*người.*mất\s*tích.*lũ", r"khẩn\s*trương\s*ứng\s*phó.*mưa\s*lũ",
    r"hướng\s*về.*đồng\s*bào.*vùng\s*lũ", r"tặng.*suất\s*quà.*vùng\s*lũ",
    r"hỗ\s*trợ.*đồng\s*bào.*thiên\s*tai", r"chuyển\s*hàng\s*cứu\s*trợ.*vùng\s*lũ",
    r"khẩn\s*trương\s*cứu\s*nạn.*do\s*lũ", r"y\s*tế.*ứng\s*phó.*bão",
    r"sơ\s*tán.*dân.*tránh\s*lũ", r"gia\s*cố.*nhà.*chống\s*bão",
    r"kích\s*hoạt.*phương\s*án.*ứng\s*phó.*bão", r"lịch\s*trực.*phòng\s*chống.*bão",
    # JAN 7 - PART 5: BOOSTED DIRECTIVES & RECOVERY (Fixing Low Scores)
    r"ban\s*hành.*công\s*điện.*bão", r"công\s*điện.*khẩn.*ứng\s*phó",
    r"khắc\s*phục.*hậu\s*quả.*thiên\s*tai", r"công\s*tác.*khắc\s*phục.*sau\s*bão",
    r"sự\s*cố.*lưới\s*điện.*bão", r"sự\s*cố.*lưới\s*điện.*mưa\s*lũ",
    r"tìm\s*thấy.*thi\s*thể.*do\s*lũ", r"nạn\s*nhân.*mất\s*tích.*do\s*lũ",
    r"dân.*bỏ\s*nhà.*sạt\s*lở", r"hỗ\s*trợ.*bị\s*ảnh\s*hưởng.*bởi\s*thiên\s*tai",
    r"họp\s*khẩn.*chỉ\s*đạo.*ứng\s*phó",
    r"bão\s*số\s*\d+", r"cơn\s*bão\s*số",
    r"di\s*dời\s*khẩn.*tránh\s*lũ", r"sơ\s*tán\s*khẩn.*tránh\s*bão",
    r"sạt\s*lở\s*đất", r"nguy\s*cơ\s*sạt\s*lở",
    r"mưa\s*lớn\s*kéo\s*dài", r"ngập\s*lụt\s*nghiêm\s*trọng",
    r"thiệt\s*hại\s*do\s*thiên\s*tai", r"khắc\s*phục\s*hậu\s*quả",
    r"xuyên\s*đêm.*cứu", r"xuyên\s*đêm.*khắc\s*phục.*hậu\s*quả",
    r"thị\s*sát.*chỉ\s*đạo.*phòng\s*chống\s*bão", r"kiểm\s*tra.*khắc\s*phục.*hậu\s*quả",
    r"lãnh\s*đạo.*thăm.*hỏi.*vùng\s*lũ", r"ứng\s*phó.*sự\s*cố.*thiên\s*tai",
    r"khẩn\s*trương.*khắc\s*phục.*hậu\s*quả", r"khẩn\s*trương.*hỗ\s*trợ.*người\s*dân",
    r"sự\s*cố.*đê.*điều", r"sự\s*cố.*hồ.*đập",
    r"vượt\s*lũ.*cứu", r"xẻ.*lũ",
    r"ảnh\s*hưởng.*bão\s*số", r"ảnh\s*hưởng.*áp\s*thấp",
    r"hỗ\s*trợ.*đồng\s*bào.*bão", r"hỗ\s*trợ.*đồng\s*bào.*lũ",
    r"rét\s*đậm", r"rét\s*hại", r"băng\s*giá", r"tuyết\s*rơi",
    r"kè\s*chống\s*sạt\s*lở", r"di\s*dời\s*khẩn\s*cấp.*khỏi\s*vùng\s*sạt", 
    r"chạy\s*lũ", r"sơ\s*tán\s*dân.*tránh\s*trú", r"cứu\s*hộ.*thiên\s*tai", r"cứu\s*nạn.*thiên\s*tai",
    r"giữ\s*đất.*giữ\s*nhà.*trong\s*lũ", r"sạt\s*trượt",
    r"xuyên\s*đêm\s*cứu\s*hộ", r"trắng\s*đêm\s*cứu\s*nạn",
    r"khẩn\s*trương\s*chạy\s*lũ", r"nguy\s*cơ\s*sạt\s*lở\s*đất",
    r"ngập\s*sâu", r"chìm\s*(?:ghe|thuyền|xuồng|tàu)", r"hỗ\s*trợ\s*khẩn\s*cấp",
    # JAN 2026: NEW BOOSTS FOR DIRECTIVES & INFRASTRUCTURE
    r"công\s*điện\s*số", r"chỉ\s*thị\s*số", r"an\s*toàn\s*hồ\s*đập", r"an\s*toàn\s*công\s*trình\s*thủy\s*lợi",
    r"vận\s*hành\s*xả\s*lũ", r"huy\s*động\s*lực\s*lượng", r"ứng\s*trực", r"trực\s*chiến",
    r"bố\s*trí\s*lực\s*lượng", r"xung\s*kích", r"phương\s*án\s*ứng\s*phó",
    r"bảo\s*đảm\s*an\s*toàn", r"tuyệt\s*đối\s*an\s*toàn", r"không\s*để\s*bị\s*động",
    r"di\s*biến\s*động\s*dân\s*cư", r"kiên\s*quyết\s*sơ\s*tán", r"cưỡng\s*chế\s*di\s*dời",
    r"xuất\s*quân\s*hỗ\s*trợ", r"trao\s*hỗ\s*trợ.*đồng\s*bào", r"kỹ\s*thuật\s*phòng\s*tránh", r"hướng\s*dẫn\s*ứng\s*phó",
    r"nước\s*cuốn\s*trôi", r"bị\s*nước\s*cuốn", r"lũ\s*cuốn\s*trôi",
    r"chỉ\s*đạo\s*di\s*dời", r"kiểm\s*tra\s*công\s*tác\s*ứng\s*phó", r"khẩn\s*trương\s*tìm\s*kiếm",
    # JAN 7 - PART 6: WARNINGS & DYKE SAFETY
    r"mực\s*nước.*đạt\s*đỉnh", r"mực\s*nước.*lên\s*nhanh", r"trên\s*báo\s*động",
    r"nguy\s*cơ\s*vỡ\s*đê", r"sự\s*cố\s*đê", r"tràn\s*đê", r"hộ\s*đê", r"an\s*toàn\s*đê\s*điều",
    r"xả\s*lũ", r"xả\s*đáy", r"mở\s*cửa\s*xả", r"lệnh\s*xả", r"thủy\s*điện\s*xả",
    r"công\s*điện\s*khẩn", r"lệnh\s*báo\s*động",
    # JAN 7 - PART 7: RAINFALL & RECOVERY
    r"mưa.*\d+\s*mm", r"lượng\s*mưa.*mm",
    r"tìm\s*thấy\s*nạn\s*nhân", r"tìm\s*thấy\s*thi\s*thể",
    r"di\s*dời\s*khẩn\s*cấp", r"công\s*điện",
    # UPDATE JAN 9 - REFINEMENT (User Request)
    r"ứng\s*cứu\s*viễn\s*thông", r"khôi\s*phục\s*liên\s*lạc", r"khắc\s*phục\s*sự\s*cố.*lưới\s*điện",
    r"sạt\s*trượt.*gây\s*ách\s*tắc", r"cấm\s*lưu\s*thông.*khu\s*vực\s*sạt",
    r"tiêm\s*vắc\s*xin.*vùng\s*lũ", r"khám\s*chữa\s*bệnh.*vùng\s*lũ",
    r"cấp\s*phát\s*thuốc.*vùng\s*lũ", r"phun\s*khử\s*khuẩn.*vùng\s*lũ",
    r"khởi\s*công.*nhà.*vùng\s*lũ", r"tái\s*thiết.*sau\s*bão",
    r"chiến\s*dịch\s*quang\s*trung", 
    r"tàu\s*hỏa.*chở\s*nhu\s*yếu\s*phẩm", r"hàng\s*không.*vận\s*chuyển.*cứu\s*trợ",
    r"uav.*tiếp\s*tế", r"trực\s*thăng.*cứu\s*trợ",
    # JAN 9 - PART 2: EROSION & CROP RESCUE
    r"xâm\s*thực\s*biển", r"sạt\s*lở\s*bờ\s*sông", r"triều\s*cường\s*dâng\s*cao",
    r"gặt\s*lúa\s*chạy\s*lũ", r"thu\s*hoạch.*chạy\s*lũ", r"sơ\s*tán.*gia\s*súc",
    r"sửa\s*chữa.*hư\s*hỏng.*bão", r"sửa\s*chữa.*hư\s*hỏng.*lũ",
    r"khẩn\s*cấp\s*khắc\s*phục.*sạt\s*lở", r"hư\s*hỏng.*công\s*trình.*thủy\s*lợi",
    # JAN 9 - PART 3: EDUCATION & STORM TRACKING
    r"học\s*sinh.*nghỉ\s*học", r"cho\s*học\s*sinh.*nghỉ",
    r"trường.*ngập", r"sách\s*vở.*vùng\s*lũ",
    r"hỗ\s*trợ.*học\s*sinh.*vùng\s*lũ", r"khắc\s*phục.*ngành.*giáo\s*dục",
    r"vào\s*biển\s*đông", r"bão.*đổ\s*bộ", r"áp\s*thấp.*mạnh\s*lên",
    # JAN 9 - PART 4: MARITIME BANS & SAFETY
    r"cấm\s*biển", r"lệnh\s*cấm\s*biển", r"ngừng\s*cấp\s*phép.*tàu",
    r"cấm\s*phương\s*tiện.*qua\s*đèo", r"sạt\s*lở.*đèo", r"cấm\s*đường",
    r"nước\s*cuốn\s*trôi", r"bị\s*lũ\s*cuốn", r"bị\s*nước\s*cuốn",
    r"hiểm\s*họa\s*sạt\s*lở", r"nguy\s*cơ\s*sạt\s*lở\s*cao",
    # JAN 9 - PART 5: MILITARY & POLICE ASSISTANCE
    r"bộ\s*đội.*giúp\s*dân", r"công\s*an.*giúp\s*dân",
    r"xuất\s*quân.*hỗ\s*trợ", r"quân\s*khu.*hỗ\s*trợ",
    r"đi\s*từng\s*nhà.*rà\s*từng\s*hộ", r"xuyên\s*đêm.*di\s*dời",
    r"cảnh\s*sát.*hỗ\s*trợ", r"cảnh\s*sát.*giúp\s*dân",
    r"chiến\s*sĩ.*hỗ\s*trợ", r"chiến\s*sĩ.*giúp\s*dân",
    r"tình\s*trạng\s*khẩn\s*cấp", r"tình\s*huống\s*khẩn\s*cấp",
    r"công\s*bố.*tình\s*huống\s*khẩn\s*cấp", r"công\s*bố.*thiên\s*tai",
    r"sơ\s*tán\s*dân", r"di\s*dời\s*khẩn\s*cấp", r"bảo\s*vệ\s*đê\s*điều",
    # JAN 9 - PART 6: PREPAREDNESS & RESCUE
    r"ứng\s*trực\s*24/24", r"trực\s*bão", r"nghỉ\s*học.*tránh\s*bão",
    r"sắc\s*phục\s*cand.*giúp\s*dân", r"công\s*an.*cứu\s*nạn", r"công\s*an.*cứu\s*hộ",
    r"chiến\s*sĩ.*cứu\s*nạn", r"binh\s*sĩ.*cứu\s*hộ",
    r"csgt.*giải\s*cứu", r"cảnh\s*sát.*giải\s*cứu",
    r"giải\s*cứu\s*thành\s*công", r"bị\s*cô\s*lập", r"cô\s*lập.*do.*lũ",
    r"an\s*toàn.*hồ\s*đập", r"hồ\s*chứa.*thủy\s*lợi",
    r"chủ\s*động\s*ứng\s*phó", r"huy\s*động\s*lực\s*lượng.*(?:bão|lũ|thiên\s*tai)",
    r"khẩn\s*trương\s*di\s*dời", r"khẩn\s*cấp\s*di\s*dời", r"cấm\s*biển",
    r"nghỉ\s*học.*(?:bão|lũ|thiên\s*tai|tránh\s*bão)", r"vận\s*chuyển.*(?:hàng)?\s*cứu\s*trợ",
    r"nứt\s*đất", r"sụt\s*lún\s*đất", r"tin\s*cảnh\s*báo.*(?:bão|lũ|thiên\s*tai|thủy\s*văn)",
    r"tin\s*dự\s*báo.*(?:bão|lũ|thiên\s*tai|thủy\s*văn)",
    r"lũ\s*lịch\s*sử", r"ngập\s*sâu(?!\s*diện\s*rộng)", r"ngập\s*úng", r"áp\s*thấp\s*nhiệt\s*đới", r"bão\s*số", r"cháy\s*rừng\s*cấp"
]
HIGH_PRIORITY_RE = re.compile("|".join(rf"(?:{p})" for p in HIGH_PRIORITY_KEYWORDS), re.IGNORECASE | re.VERBOSE)


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
    
    # [OPTIMIZATION] Deterministic sampling for consistent testing if needed, or stick to random.
    # Sticking to random for variability but adding check for empty list
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
    
    # [OPTIMIZATION] Better error handling for JSON decoding
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    sources = []
    for s in data.get("sources", []):
        sources.append(Source(
            name=s.get("name", "Unknown"),
            domain=s.get("domain", ""),
            primary_rss=s.get("primary_rss"),
            backup_rss=s.get("backup_rss"),
            note=s.get("note"),
            trusted=s.get("trusted", False),
            authority_level=s.get("authority_level", 2 if s.get("trusted") else 1)
        ))
    return sources

CONFIG_FILE = Path(__file__).parent.parent / "sources.json"

# Load raw config for global settings
CONFIG = {}
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {}

# Parse sources list
SOURCES = []
for s in CONFIG.get("sources", []):
    SOURCES.append(Source(
        name=s.get("name", "Unknown"),
        domain=s.get("domain", ""),
        primary_rss=s.get("primary_rss"),
        backup_rss=s.get("backup_rss"),
        note=s.get("note"),
        trusted=s.get("trusted", False),
        authority_level=s.get("authority_level", 2 if s.get("trusted") else 1)
    ))

