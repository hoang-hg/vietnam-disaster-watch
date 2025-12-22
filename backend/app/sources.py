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

# GNews Search Strategy: Tiered Anchors & Context Filters
# Fixed Anchors: Disaster types only (to ensure recall)
GNEWS_ANCHORS = [
    "bão", "áp thấp nhiệt đới", "lũ", "lũ quét", "ngập lụt", "sạt lở", 
    "cháy rừng", "động đất", "sóng thần", "triều cường", "nước dâng", 
    "xâm nhập mặn", "hạn hán", "nắng nóng", "dông lốc", "mưa đá", 
    "rét đậm", "rét hại", "mưa lớn"
]

# Contextual Filters: Signs of actual event/impact (sampled deterministicly per domain)
GNEWS_FILTERS = [
    "thiệt hại", "tổn thất", "sập nhà", "tốc mái", "cuốn trôi", "vùi lấp",
    "chia cắt", "cô lập", "sơ tán", "di dời", "cứu hộ", "cứu nạn", "tiếp tế",
    "mất tích", "thương vong", "tử vong", "thiệt mạng", "khắc phục", "hỗ trợ khẩn cấp",
    "xả lũ", "vỡ đê", "sạt lở kè", "ngập sâu", "ngập diện rộng", "cấm biển"
]

def dedup_terms(terms):
    """Clean and deduplicate keywords."""
    seen = set()
    out = []
    for t in terms:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t.strip())
    return out

def build_gnews_rss(domain: str, hazard_terms: List[str] | None = None, context_terms: List[str] | None = None) -> str:
    """Build Google News RSS URL with Tiered Search and Deterministic Sampling.
    
    Structure: site:domain (ANCHORS) (CONTEXT_FILTERS)
    This ensures we only capture actual disaster events, not generic weather talk.
    """
    import random
    
    def _quote(ts):
        return [f'"{t}"' if ' ' in t else t for t in ts]

    # 1. Prepare Anchors (Disaster Types)
    anchors = dedup_terms(hazard_terms or GNEWS_ANCHORS)
    # If list is too long for GNews (unlikely for anchors), keep top 15
    if len(anchors) > 15:
        anchors = anchors[:15]
    
    # 2. Prepare Context Filters (Impact/Action)
    filters = dedup_terms(context_terms or GNEWS_FILTERS)
    
    # 3. Deterministic Sampling for stability across runs for the same domain
    max_filters = 15 # Limit combined query length to avoid GNews rejections
    if len(filters) > max_filters:
        rnd = random.Random(domain) # Stable seed per domain
        filters = rnd.sample(filters, max_filters)

    # 4. Compose Query
    anchors_q = " OR ".join(_quote(anchors))
    filters_q = " OR ".join(_quote(filters))
    
    query = f"site:{domain} ({anchors_q}) ({filters_q})"
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
