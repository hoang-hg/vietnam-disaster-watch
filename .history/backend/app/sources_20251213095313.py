from dataclasses import dataclass
from typing import Literal, List
import urllib.parse

Method = Literal["rss", "gnews"]

DISASTER_KEYWORDS = [
    # bão/áp thấp
    "bão", "bão số", "siêu bão", "hoàn lưu bão", "tâm bão", "đổ bộ",
    "áp thấp", "áp thấp nhiệt đới", "atnđ", "vùng áp thấp",

    # gió - dông - mưa cực đoan
    "gió mạnh", "gió giật", "dông", "dông lốc", "lốc", "lốc xoáy", "vòi rồng",
    "mưa", "mưa lớn", "mưa rất to", "mưa cực lớn", "mưa diện rộng",
    "mưa kéo dài", "mưa kỷ lục", "mưa cực đoan", "mưa đá", "sét", "giông sét",

    # lũ/ngập/biển
    "lũ", "lụt", "lũ lớn", "lũ lịch sử", "lũ dâng", "ngập", "ngập úng", "ngập lụt", "ngập sâu",
    "lũ quét", "lũ ống", "ngập cục bộ",
    "triều cường", "nước dâng", "nước dâng do bão", "biển động", "sóng lớn", "sóng cao",
    "sóng thần", "cảnh báo sóng thần", "cấm biển",

    # sạt lở/địa chất
    "sạt lở", "sạt lở đất", "trượt lở", "trượt đất", "taluy", "sạt taluy",
    "sạt lở bờ sông", "sạt lở bờ biển",
    "động đất", "rung chấn", "dư chấn", "nứt đất", "nứt nhà", "đứt gãy",
    "sụt lún", "hố tử thần", "sụp đường", "sụp lún",

    # khí hậu cực đoan
    "nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt", "nhiệt độ kỷ lục",
    "hạn hán", "khô hạn", "thiếu nước", "cạn kiệt",
    "rét đậm", "rét hại", "không khí lạnh", "sương muối", "băng giá",
    "xâm nhập mặn", "nhiễm mặn", "độ mặn",

    # cháy rừng
    "cháy rừng", "nguy cơ cháy rừng", "cấp dự báo cháy rừng",

    # tổng hợp/cảnh báo/thiệt hại/ứng phó
    "thiên tai", "thảm họa", "rủi ro thiên tai", "cấp độ rủi ro",
    "cảnh báo", "khuyến cáo", "cảnh báo sớm", "dự báo", "bản tin",
    "thiệt hại", "tàn phá", "tốc mái", "sập", "cuốn trôi", "chia cắt", "cô lập",
    "sơ tán", "di dời", "mất tích", "thương vong", "mất điện", "mất liên lạc",
    "vỡ đê", "xả lũ", "xả tràn", "hồ chứa", "thủy điện",
]

@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    method: Method
    url: str  # RSS URL if method=rss

def build_gnews_rss(domain: str, extra_terms: List[str] | None = None) -> str:
    terms = extra_terms or DISASTER_KEYWORDS
    q = f"site:{domain} (" + " OR ".join(terms) + ")"
    params = {"q": q, "hl": "vi", "gl": "VN", "ceid": "VN:vi"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)

SOURCES: list[Source] = [
    # Bạn có thể thay method="rss" và url="...rss" nếu có RSS chính thức
    Source("Báo Tin tức (TTXVN)", "baotintuc.vn", "gnews", ""),
    Source("SGGP", "sggp.org.vn", "gnews", ""),
    Source("VnExpress", "vnexpress.net", "gnews", ""),
    Source("VietNamNet", "vietnamnet.vn", "gnews", ""),
    Source("Dân Trí", "dantri.com.vn", "gnews", ""),
    Source("Báo Mới", "baomoi.com", "gnews", ""),
    Source("Thanh Niên", "thanhnien.vn", "gnews", ""),
    Source("VNA Net", "vnanet.vn", "gnews", ""),
    Source("Tuổi Trẻ", "tuoitre.vn", "gnews", ""),
    Source("Người Lao Động", "nld.com.vn", "gnews", ""),
    Source("Lao Động", "laodong.vn", "gnews", ""),
    Source("Quân đội Nhân dân", "qdnd.vn", "gnews", ""),
]
