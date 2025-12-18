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
        "áp thấp", "áp thấp nhiệt đới", "atnđ", "vùng áp thấp"
    ],
    "flood_landslide": [
        "lũ", "lụt", "lũ lớn", "lũ lịch sử", "lũ dâng", "ngập", "ngập úng", "ngập lụt", "ngập sâu",
        "lũ quét", "lũ ống", "ngập cục bộ", "sạt lở", "sạt lở đất", "trượt lở", "trượt đất",
        "taluy", "sạt taluy", "sạt lở bờ sông", "sạt lở bờ biển", "sụt lún", "hố tử thần", "sụp đường"
    ],
    "heat_drought": [
        "nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt", "nhiệt độ kỷ lục",
        "hạn hán", "khô hạn", "thiếu nước", "cạn kiệt", "xâm nhập mặn", "nhiễm mặn", "độ mặn"
    ],
    "wind_fog": [
        "gió mạnh", "gió giật", "biển động", "sóng lớn", "sóng cao", "cấm biển",
        "sương mù", "sương mù dày đặc", "tầm nhìn hạn chế"
    ],
    "storm_surge": [
        "triều cường", "nước dâng", "nước dâng do bão", "nước biển dâng", "đỉnh triều"
    ],
    "extreme_other": [
        "dông", "dông lốc", "lốc", "lốc xoáy", "vòi rồng", "mưa lớn", "mưa rất to", 
        "mưa cực lớn", "mưa diện rộng", "mưa đá", "sét", "giông sét",
        "rét đậm", "rét hại", "không khí lạnh", "sương muối", "băng giá"
    ],
    "wildfire": [
        "cháy rừng", "nguy cơ cháy rừng", "cấp dự báo cháy rừng", "PCCCR"
    ],
    "quake_tsunami": [
        "động đất", "rung chấn", "dư chấn", "nứt đất", "đứt gãy", "sóng thần", "cảnh báo sóng thần"
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
    """
    hazards = hazard_terms or DISASTER_KEYWORDS
    if context_terms:
        hazard_q = " OR ".join(hazards)
        context_q = " OR ".join(context_terms)
        q = f"site:{domain} (({hazard_q}) AND ({context_q}))"
    else:
        q = f"site:{domain} (" + " OR ".join(hazards) + ")"
    params = {"q": q, "hl": "vi", "gl": "VN", "ceid": "VN:vi"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)

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

# Load sources at module import time
SOURCES: list[Source] = load_sources_from_json()
