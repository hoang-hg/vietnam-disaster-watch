from dataclasses import dataclass
from typing import Literal, List
import urllib.parse
import json
from pathlib import Path

Method = Literal["rss", "gnews"]

# 8 Standardized Disaster Groups (Decision 18/2021/QD-TTg & common usage)
DISASTER_GROUPS = {
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
        "cập nhật bão", "mưa do hoàn lưu"
    ],
    "flood_landslide": [
        "lũ", "lụt", "lũ lớn", "lũ lịch sử", "lũ dâng", "ngập", "ngập úng", "ngập lụt", "ngập sâu",
        "ngập nước", "chia cắt", "cô lập", "vỡ đê", "tràn đê", "xả lũ", "hồ chứa",
        "lũ quét", "lũ ống", "ngập cục bộ", "sạt lở", "sạt lở đất", "trượt lở", "trượt đất",
        "taluy", "sạt taluy", "sạt lở bờ sông", "sạt lở bờ biển", "sụt lún", "hố tử thần", "sụp đường",
        "ngập đường", "ngập úng cục bộ", "tràn vào nhà", "nước lũ", "nước dâng cao",
        "lũ về", "đỉnh lũ", "mực nước lũ", "lũ lụt lớn", "lũ chảy xiết",
        "sạt lở núi", "sạt lở taluy", "đất đá sạt lở", "vách núi sạt lở",
        "sụp lở", "sập taluy", "trượt ta-luy", "đất đá vùi lấp",
        "nứt đất", "sụt lún đất", "đất sụp", "hố sụt đất", "vách đá lăn",
        "báo động 1", "báo động 2", "báo động 3", "báo động khẩn cấp", "mực nước báo động",
        "lũ trên sông", "lũ hạ lưu", "lũ thượng nguồn", "lũ dâng cao", "lên nhanh",
        "lưu lượng", "vỡ đập", "sự cố đập", "sự cố hồ đập", "xả tràn", "xả khẩn cấp",
        "xói lở", "xâm thực", "sạt trượt", "trượt sườn", "đứt gãy taluy", "đá lăn",
        "hàm ếch", "nứt toác", "trôi cầu", "đứt đường", "ngập phố", "ngập lút",
        "mưa lớn", "mưa rất to", "mưa cực lớn", "mưa diện rộng", "mưa kéo dài",
        "mưa to đến rất to", "mưa đặc biệt lớn", "mưa cực đoan", "mưa kỷ lục",
        "mưa như trút", "mưa xối xả", "mưa tầm tã", "lượng mưa", "tổng lượng mưa"
    ],
    "heat_drought": [
        "nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt", "nhiệt độ kỷ lục",
        "hạn hán", "khô hạn", "thiếu nước", "cạn kiệt", "xâm nhập mặn", "nhiễm mặn", "độ mặn",
        "nắng nóng kéo dài", "đợt nắng nóng", "nắng như đổ lửa", "nóng đỉnh điểm",
        "nhiệt độ cao nhất", "nền nhiệt cao", "nóng bức", "oi bức",
        "hạn hán kéo dài", "hạn hán nghiêm trọng", "đất khô cằn", "đất nứt nẻ",
        "thiếu nước sinh hoạt", "thiếu nước sạch", "hạn mặn", "hạn hán và xâm nhập mặn",
        "độ mặn tăng", "nước nhiễm mặn", "mất mùa do hạn",
        "ranh mặn", "cống ngăn mặn", "độ mặn phần nghìn", "đẩy mặn", "chi viện nước ngọt",
        "dòng chảy kiệt", "mùa cạn", "kiệt nước", "mực nước xuống thấp", "độ mặn 4‰"
    ],
    "wind_fog": [
        "gió mạnh", "gió giật", "biển động", "sóng lớn", "sóng cao", "cấm biển",
        "sương mù", "sương mù dày đặc", "tầm nhìn hạn chế",
        "gió mạnh cấp", "gió giật cấp", "gió mùa đông bắc", "không khí lạnh tăng cường",
        "biển động mạnh", "biển động rất mạnh", "sóng cao từ", "độ cao sóng",
        "cấm tàu thuyền", "tàu thuyền không ra khơi", "tàu thuyền vào bờ",
        "sương mù dày", "mù dày đặc", "tầm nhìn xa dưới", "giảm tầm nhìn", "mù quang"
    ],
    "storm_surge": [
        "triều cường", "nước dâng", "nước dâng do bão", "nước biển dâng", "đỉnh triều",
        "triều cường kết hợp", "ngập do triều cường", "nước dâng cao",
        "biển dâng", "thủy triều dâng", "đỉnh triều cường", "triều cao",
        "nước dâng do áp thấp", "triều cường kỷ lục", "dâng cao bất thường",
        "ngập ven biển", "sóng tràn", "sóng đánh tràn", "tràn qua kè", "vượt báo động triều"
    ],
    "extreme_other": [
        "dông", "dông lốc", "lốc", "lốc xoáy", "vòi rồng", "mưa đá", "sét", "giông sét", "giông", "mưa giông", "giông tố",
        "rét đậm", "rét hại", "không khí lạnh", "sương muối", "băng giá",
        "mưa đá to", "sét đánh",
        "giông lốc mạnh", "lốc xoáy mạnh", "tố lốc",
        "rét đậm rét hại", "rét kỷ lục", "đợt rét", "không khí lạnh mạnh",
        "băng giá phủ trắng", "sương giá", "rét buốt",
        "mưa tuyết", "tuyết rơi"
    ],
    "wildfire": [
        "cháy rừng", "nguy cơ cháy rừng", "cấp dự báo cháy rừng", "PCCCR",
        "cháy rừng lan rộng", "đám cháy rừng", "lửa rừng", "cháy thực bì",
        "cháy rừng phòng hộ", "nguy cơ cháy rừng cấp", "cấp cháy rừng",
        "phòng cháy chữa cháy rừng", "chữa cháy rừng", "đám cháy lan",
        "nguy cơ cháy rừng rất cao", "cấp cháy rừng cấp", "trực cháy rừng",
        "cháy rừng đặc dụng", "đốt nương làm rẫy", "đốt thực bì"
    ],
    "quake_tsunami": [
        "động đất", "rung chấn", "dư chấn", "nứt đất", "đứt gãy", "sóng thần", "cảnh báo sóng thần",
        "trận động đất", "chấn động", "địa chấn", "tâm chấn", "chấn tiêu",
        "động đất mạnh", "rung chấn mạnh", "dư chấn động đất",
        "độ richter", "độ lớn", "cường độ động đất", "thang richter",
        "rung lắc", "magnitude", "viện vật lý địa cầu", "Mw", "ML", "M"
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
    "Đèo Măng Đen", "Đèo Keo Nưa", "Đèo Đá Đẽo", "Đèo Tam Điệp"
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
    r"công\s*điện\s*(?:khẩn|hỏa\s*tốc)",
    r"công\s*điện\s*số\s*\d+\/CĐ\-(?:TTg|[A-Z]+)",
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
    r"nguy\s*cơ\s*sạt\s*lở\s*rất\s*cao",
    r"cháy\s*rừng\s*(?:nghiêm\s*trọng|lan\s*rộng)|cấp\s*cháy\s*rừng\s*cấp\s*V",
    r"cảnh\s*báo\s*sóng\s*thần|báo\s*động\s*sóng\s*thần",

    # Aid / relief
    r"hỗ\s*trợ\s*khẩn\s*cấp\s*thiên\s*tai",
    r"viện\s*trợ.*thiên\s*tai",
]


@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    primary_rss: str | None = None  # Primary RSS URL
    backup_rss: str | None = None   # Backup RSS URL
    note: str | None = None
    trusted: bool | None = False

GNEWS_HAZARD_KEYWORDS = [ "thiệt hại","tổn thất", "đổ nhà","đổ tường", "hư hỏng","cuốn trôi",
"trôi nhà","ngập nhà","vỡ đê","tràn đê","vỡ bờ","chia cắt", "cô lập","mất mùa", "mất trắng","chết đuối","bị vùi lấp","người chết","tử vong","thiệt mạng", 
"thi thể","nạn nhân","thương vong","bị thương", "trọng thương", "mất tích","mất liên lạc","tìm kiếm","sơ tán",
"di dời","tránh trú","vào bờ", "lên bờ","về bến","cứu hộ","cứu nạn","cứu trợ","tiếp tế", 
"hỗ trợ","trợ cấp","cứu sinh","giải cứu","tìm kiếm cứu nạn", "huy động lực lượng","xuất quân","triển khai lực lượng",
"ứng phó","khắc phục","xử lý sự cố","sửa chữa","tu bổ","phục hồi", "tái thiết","thiệt hại",
"đánh giá thiệt hại", "cảnh báo","cảnh báo khẩn","dự báo", "tin khẩn","công điện", "tình trạng khẩn cấp","tình huống khẩn cấp","trạng thái khẩn cấp","khẩn cấp", "khẩn trương","gấp rút",
"hỏa tốc","cấp bách","nguy hiểm","nguy cấp","nguy kịch", "mất an toàn","đe dọa","đe dọa nghiêm trọng","rủi ro cao","nguy cơ cao","cấm", "cấm đường","cấm biển","cấm tàu thuyền","đóng cửa","đóng cửa trường","cho nghỉ học", 
"nghỉ học","tạm dừng","tạm ngưng","phong tỏa","cấm lưu thông","cách ly","họp khẩn", "cuộc họp khẩn","ban chỉ huy","ban chỉ đạo","trực ban","trực 24/24","túc trực", "ứng trực","mưa to đến rất to","mưa đặc biệt lớn","mưa cực đoan",
"mưa kỷ lục", "báo động","mực nước báo động", "lũ trên sông","lũ bùn đá","lũ bùn","xói lở","xâm thực","sạt trượt","trượt sườn", "đứt gãy taluy","đá lăn","ranh mặn","cống ngăn mặn","độ mặn phần nghìn", 
"bão", "siêu bão", "áp thấp nhiệt đới", "lũ quét", "ngập lụt", "xả lũ",
"sạt lở", "sụt lún", "đất đá vùi lấp", "lũ ống", "nắng nóng", "hạn hán", "xâm nhập mặn", "triều cường", "nước dâng", "mưa lớn", "lốc xoáy", "mưa đá", "cảnh báo mưa", "dự báo thời tiết nguy hiểm", "rét đậm", "rét hại", "băng giá", "sương muối", "cháy rừng", 
"động đất", "sóng thần", "rung chấn", "tốc mái", "sập nhà", "cảnh báo thiên tai", "dự báo thời tiết", "mưa lũ", "sóng lớn", "mưa dông",
"tin cảnh báo", "tin dự báo", "công điện", "ATNĐ", "gió mạnh", "biển động", "sương mù", "dông lốc", "sét đánh", "rét đậm rét hại"
]


def build_gnews_rss(domain: str, hazard_terms: List[str] | None = None, context_terms: List[str] | None = None) -> str:
    """Build Google News RSS URL as fallback.

    If both hazard_terms and context_terms are provided, build a query that
    requires a hazard term and a context term to reduce false positives.
    Automatically quotes terms with spaces to prevent keyword splitting.
    """
    # Use condensed list for GNews if no specific hazards provided to keep URL short
    hazards = hazard_terms or GNEWS_HAZARD_KEYWORDS
    
    # Helper to quote terms with spaces
    def _quote(terms):
        return [f'"{t.strip()}"' if ' ' in t.strip() else t.strip() for t in terms]

    hazards = _quote(hazards)
    
    # Randomly sample if list is too huge to avoid URL length issues (optional, but good for safety)
    import random
    if len(hazards) > 50:
        hazards = random.sample(hazards, 50)

    base = "https://news.google.com/rss/search?q="
    
    # Build query
    query = f"site:{domain} (" + " OR ".join(hazards) + ")"
    
    if context_terms:
        contexts = _quote(context_terms)
        query += " (" + " OR ".join(contexts) + ")"
        
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
            trusted=s.get("trusted", False)
        ))
    return sources

# Example Global Source Access
CONFIG_FILE = Path(__file__).parent.parent / "sources.json"
SOURCES = load_sources_from_json(str(CONFIG_FILE))
CONFIG = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
