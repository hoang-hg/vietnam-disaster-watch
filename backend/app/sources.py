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
        "áp thấp", "áp thấp nhiệt đới", "atnđ", "vùng áp thấp", "vùng thấp", "rãnh áp thấp",
        "bão nhiệt đới", "siêu bão nhiệt đới", "gió bão", "vùng gió mạnh",
        "tiến vào biển đông", "đi vào biển đông", "suy yếu thành áp thấp",
        "chuyển hướng", "ảnh hưởng của bão", "hoàn lưu áp thấp",
        "tin bão", "tin áp thấp", "bản tin bão", "cảnh báo bão"
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
        "nứt đất", "sụt lún đất", "đất sụp", "hố sụt đất",
        # User requested additions (Technical terms)
        "báo động 1", "báo động 2", "báo động 3", "báo động khẩn cấp", "mực nước báo động",
        "lũ trên sông", "lũ bùn đá", "lũ bùn",
        "xói lở", "xâm thực", "sạt trượt", "trượt sườn", "đứt gãy taluy", "đá lăn"
    ],
    "heat_drought": [
        "nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt", "nhiệt độ kỷ lục",
        "hạn hán", "khô hạn", "thiếu nước", "cạn kiệt", "xâm nhập mặn", "nhiễm mặn", "độ mặn",
        "nắng nóng kéo dài", "đợt nắng nóng", "nắng như đổ lửa", "nóng đỉnh điểm",
        "nhiệt độ cao nhất", "nền nhiệt cao", "nóng bức", "oi bức",
        "hạn hán kéo dài", "hạn hán nghiêm trọng", "đất khô cằn", "đất nứt nẻ",
        "thiếu nước sinh hoạt", "thiếu nước sạch", "hạn mặn", "hạn hán và xâm nhập mặn",
        "độ mặn tăng", "nước nhiễm mặn", "mất mùa do hạn",
        # User requested additions
        "ranh mặn", "cống ngăn mặn", "độ mặn phần nghìn"
    ],
    "wind_fog": [
        "gió mạnh", "gió giật", "biển động", "sóng lớn", "sóng cao", "cấm biển",
        "sương mù", "sương mù dày đặc", "tầm nhìn hạn chế",
        "gió mạnh cấp", "gió giật cấp", "gió mùa đông bắc", "không khí lạnh tăng cường",
        "biển động mạnh", "biển động rất mạnh", "sóng cao từ", "độ cao sóng",
        "cấm tàu thuyền", "tàu thuyền không ra khơi", "tàu thuyền vào bờ",
        "sương mù dày", "mù dày đặc", "tầm nhìn xa dưới", "giảm tầm nhìn"
    ],
    "storm_surge": [
        "triều cường", "nước dâng", "nước dâng do bão", "nước biển dâng", "đỉnh triều",
        "triều cường kết hợp", "ngập do triều cường", "nước dâng cao",
        "biển dâng", "thủy triều dâng", "đỉnh triều cường", "triều cao"
    ],
    "extreme_other": [
        "dông", "dông lốc", "lốc", "lốc xoáy", "vòi rồng", "mưa lớn", "mưa rất to", 
        "mưa cực lớn", "mưa diện rộng", "mưa đá", "sét", "giông sét", "giông", "mưa giông", "giông tố",
        "rét đậm", "rét hại", "không khí lạnh", "sương muối", "băng giá",
        "mưa như trút nước", "mưa xối xả", "mưa tầm tã", "mưa kéo dài",
        "mưa lũ", "mưa lớn kéo dài", "mưa đá to", "sét đánh",
        "giông lốc mạnh", "lốc xoáy mạnh", "tố lốc",
        "rét đậm rét hại", "rét kỷ lục", "đợt rét", "không khí lạnh mạnh",
        "băng giá phủ trắng", "sương giá", "rét buốt",
        # User requested additions
        "mưa to đến rất to", "mưa đặc biệt lớn", "mưa cực đoan", "mưa kỷ lục"
    ],
    "wildfire": [
        "cháy rừng", "nguy cơ cháy rừng", "cấp dự báo cháy rừng", "PCCCR",
        "cháy rừng lan rộng", "đám cháy rừng", "lửa rừng", "cháy thực bì",
        "cháy rừng phòng hộ", "nguy cơ cháy rừng cấp", "cấp cháy rừng",
        "phòng cháy chữa cháy rừng", "chữa cháy rừng", "đám cháy lan",
        # User requested additions
        "nguy cơ cháy rừng rất cao", "cấp cháy rừng cấp"
    ],
    "quake_tsunami": [
        "động đất", "rung chấn", "dư chấn", "nứt đất", "đứt gãy", "sóng thần", "cảnh báo sóng thần",
        "trận động đất", "chấn động", "địa chấn", "tâm chấn", "chấn tiêu",
        "động đất mạnh", "rung chấn mạnh", "dư chấn động đất",
        "độ richter", "độ lớn", "cường độ động đất", "thang richter"
    ]
}

# Flat list for searching and initial filtering
DISASTER_KEYWORDS = [item for sublist in DISASTER_GROUPS.values() for item in sublist]

# Context keywords (not a disaster group, but used to refine search)
CONTEXT_KEYWORDS = [
    "thiên tai", "thảm họa", "rủi ro thiên tai", "cấp độ rủi ro",
    "thiệt hại", "tàn phá", "tốc mái", "sập", "cuốn trôi", "chia cắt", "cô lập",
    "sơ tán", "di dời", "mất tích", "thương vong", "mất điện", "mất liên lạc",
    "vỡ đê", "xả lũ", "xả tràn", "hồ chứa", "thủy điện"
]

# VIP Terms (Critical warnings/actions that bypass all filters)
VIP_TERMS = [
    r"tin\s*bão", r"bão\s*(?:số|gần\s*biển\s*đông|đổ\s*bộ)", 
    r"áp\s*thấp\s*nhiệt\s*đới", r"ATNĐ",
    r"hỗ\s*trợ\s*khẩn\s*cấp", r"viện\s*trợ.*thiên\s*tai"
]


@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    primary_rss: str | None = None  # Primary RSS URL
    backup_rss: str | None = None   # Backup RSS URL
    note: str | None = None
    trusted: bool | None = False

def build_gnews_rss(domain: str, hazard_terms: List[str] | None = None, context_terms: List[str] | None = None) -> str:
    """Build Google News RSS URL as fallback.

    If both hazard_terms and context_terms are provided, build a query that
    requires a hazard term and a context term to reduce false positives.
    Automatically quotes terms with spaces to prevent keyword splitting.
    """
    hazards = hazard_terms or DISASTER_KEYWORDS
    
    # Helper to quote terms with spaces
    def _quote(terms):
        return [f'"{t.strip()}"' if ' ' in t.strip() else t.strip() for t in terms]

    hazards = _quote(hazards)

    if context_terms:
        contexts = _quote(context_terms)
        hazard_q = " OR ".join(hazards)
        context_q = " OR ".join(contexts)
        q = f"site:{domain} (({hazard_q}) AND ({context_q}))"
    else:
        q = f"site:{domain} (" + " OR ".join(hazards) + ")"
        
    params = {"q": q, "hl": "vi", "gl": "VN", "ceid": "VN:vi"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)

def load_config_from_json() -> dict:
    """Load global config from sources.json file.
    
    Returns dict with keys: gnews_fallback, gnews_context_terms, 
    gnews_min_articles, request_timeout, max_articles_per_source
    """
    sources_file = Path(__file__).parent.parent / "sources.json"
    if not sources_file.exists():
        print(f"[WARN] sources.json not found at {sources_file}, using empty config")
        return {}
    
    try:
        with open(sources_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            "gnews_fallback": data.get("gnews_fallback", True),
            "gnews_context_terms": data.get("gnews_context_terms", []),
            "gnews_min_articles": data.get("gnews_min_articles", 1),
            "request_timeout": data.get("request_timeout", 10),
            "max_articles_per_source": data.get("max_articles_per_source", 30),
        }
    except Exception as e:
        print(f"[ERROR] failed to load config from sources.json: {e}")
        return {}

def load_sources_from_json() -> list[Source]:
    """Load sources from sources.json file."""
    sources_file = Path(__file__).parent.parent / "sources.json"
    if not sources_file.exists():
        print(f"[WARN] sources.json not found at {sources_file}, using empty list")
        return []
    
    try:
        with open(sources_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        sources = []
        for src_data in data.get("sources", []):
            source = Source(
                name=src_data["name"],
                domain=src_data["domain"],
                primary_rss=src_data.get("primary_rss"),
                backup_rss=src_data.get("backup_rss"),
                note=src_data.get("note"),
                trusted=src_data.get("trusted", False)
            )
            sources.append(source)
        
        return sources
    except Exception as e:
        print(f"[ERROR] failed to load sources.json: {e}")
        return []

# Load sources and config at module import time
SOURCES: list[Source] = load_sources_from_json()
CONFIG: dict = load_config_from_json()
# Trigger reload for source update
