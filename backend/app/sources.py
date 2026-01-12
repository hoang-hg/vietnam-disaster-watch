from dataclasses import dataclass
from typing import Literal, List
from functools import lru_cache
import urllib.parse
import json
from pathlib import Path
import re
import unicodedata

# 14+2 Standardized Disaster Groups

FOREST_INDICATORS = [
    "rừng", "thực bì", "khoảnh", "tiểu khu", "lâm phần", "lâm nghiệp", 
    "diện tích", "thảm thực vật", "cháy lan", "đám cháy"
]

DISASTER_GROUPS = {
    "storm": [
        "bão", "cơn bão", "bão số", "bão có tên", "tên bão", "bão quốc tế", "bão nhiệt đới", "siêu bão", "siêu bão nhiệt đới", "xoáy thuận nhiệt đới",
        "áp thấp nhiệt đới", "atnđ", "atnd", "nhiễu động nhiệt đới", "vùng áp thấp nhiệt đới", "vùng áp thấp trên biển", "vùng áp thấp trên biển đông", "rãnh áp thấp", "dải hội tụ nhiệt đới", "hội tụ nhiệt đới",
        "rãnh thấp", "rãnh thấp có trục", "rãnh thấp xích đạo", "tâm bão", "vị trí tâm bão", "tọa độ tâm bão", "kinh độ tâm bão", "vĩ độ tâm bão", "mắt bão", "hoàn lưu bão",
        "hoàn lưu áp thấp", "hoàn lưu sau bão", "bán kính gió mạnh", "vùng gió mạnh", "vùng nguy hiểm do bão", "vùng nguy hiểm trên biển", "khu vực nguy hiểm do bão", "cường độ bão", "cấp bão", "sức gió mạnh nhất",
        "áp suất trung tâm", "hướng di chuyển của bão", "đường đi của bão", "quỹ đạo bão", "hành lang bão", "dự báo quỹ đạo", "dự báo đường đi", "chuyển hướng", "đổi hướng của bão", "di chuyển theo hướng",
        "dịch chuyển theo hướng", "tiến vào biển đông", "đi vào biển đông", "trên biển đông", "bão trên biển đông", "bão trên biển", "vịnh bắc bộ", "vịnh thái lan", "quần đảo hoàng sa", "quần đảo trường sa",
        "áp sát ven biển", "áp sát đất liền", "đi sát bờ", "đi vào đất liền", "đổ bộ", "đổ bộ vào", "đổ bộ trực tiếp", "đổ bộ vào đất liền", "bão mạnh", "bão rất mạnh",
        "bão mạnh lên", "bão tăng cấp", "mạnh lên thành bão", "áp thấp mạnh lên", "mạnh lên thành áp thấp nhiệt đới", "bão suy yếu", "suy yếu nhanh", "áp thấp suy yếu", "áp thấp tan", "suy yếu thành áp thấp",
        "bão tan dần", "tan dần trên biển", "gió bão", "gió mạnh cấp", "gió cấp", "gió giật cấp", "giật cấp", "beaufort", "thang beaufort", "mưa bão",
        "mưa do hoàn lưu", "mưa do hoàn lưu bão", "hoàn lưu gây mưa", "mưa kèm gió bão", "ảnh hưởng của bão", "ảnh hưởng trực tiếp", "ít khả năng ảnh hưởng", "khả năng ảnh hưởng", "tin bão", "tin áp thấp",
        "bản tin bão", "cảnh báo bão", "tin bão khẩn cấp", "dự báo bão", "cập nhật bão", "bản tin áp thấp nhiệt đới", "chống bão", "ứng phó bão", "phòng chống bão", "tránh trú bão",
        "neo đậu tránh trú bão", "kêu gọi tàu thuyền tránh trú", "gió giật trên cấp do bão", "bão đổi hướng", "bão chuyển hướng", "bão đi lệch hướng", "bão di chuyển nhanh", "bão di chuyển chậm", "bão áp sát", "bão áp sát bờ",
        "tăng cấp nhanh", "mạnh thêm", "bão giật cấp", "gió gần tâm bão", "vùng gần tâm bão", "vùng gần tâm áp thấp", "gió mạnh cấp 8", "gió mạnh cấp 9", "gió mạnh cấp 10", "gió mạnh cấp 11", "gió mạnh cấp 12", "gió giật cấp 10", "gió giật cấp 11",
        "gió giật cấp 12", "gió giật cấp 13", "gió giật cấp 14", "gió giật cấp 15", "áp suất giảm", "áp suất trung tâm giảm", "bão đi vào vịnh bắc bộ", "bão ảnh hưởng vịnh bắc bộ",
        "tâm áp thấp nhiệt đới", "vị trí tâm áp thấp", "tọa độ tâm áp thấp", "áp suất tối thiểu", "áp suất thấp nhất", "áp suất trung tâm thấp", "tốc độ di chuyển", "di chuyển với tốc độ", "hướng dịch chuyển",
        "bão suy yếu dần", "áp thấp suy yếu dần", "bão mạnh lên nhanh", "áp thấp mạnh lên nhanh", "tăng cấp rất nhanh", "tăng cấp liên tục", "giảm cấp nhanh", "tan trên biển", "tàn dư áp thấp", "vùng thấp suy yếu",
        "bão suy yếu thành áp thấp nhiệt đới", "suy yếu thành vùng áp thấp", "tăng cấp thành bão", "tăng cấp thành bão mạnh", "bão đổi cấp", "bão tăng cường", "áp thấp tăng cường", "bão di chuyển bất thường", "bão đổi hướng liên tục", "bão lệch quỹ đạo",
        "bán kính gió mạnh cấp 6", "bán kính gió mạnh cấp 7", "bán kính gió mạnh cấp 8", "bán kính gió mạnh cấp 10", "bán kính gió giật", "bán kính gió giật mạnh", "vùng gió mạnh cấp 6", "vùng gió mạnh cấp 7", "vùng gió mạnh cấp 8", "vùng gió mạnh cấp 10",
        "gió mạnh cấp 6", "gió mạnh cấp 7", "gió mạnh cấp 13", "gió mạnh cấp 14", "gió mạnh cấp 15", "gió giật cấp 8", "gió giật cấp 9", "gió giật cấp 16", "gió giật cấp 17", "gió duy trì",
        "gió trung bình", "tốc độ gió", "gió mạnh nhất", "gió giật mạnh nhất", "cường độ gió", "gió tăng dần", "gió mạnh dần", "gió giảm dần", "gió yếu dần", "gió gần tâm", "nước dâng do bão", 
        "rìa bão", "rìa hoàn lưu", "vùng mây đối lưu", "dải mây xoắn ốc", "dải mây bão", "mây đối lưu phát triển", "dông mạnh trong hoàn lưu", "tường mây", "mắt bão rõ", "vùng gần tâm gió mạnh",
        "đổ bộ vào khu vực", "đổ bộ vào ven biển", "đi vào vùng biển", "tiến gần đất liền", "đi ngang ven biển", "đi dọc ven biển", "áp sát khu vực ven biển", "đi qua quần đảo", "tâm bão trên biển", "tâm áp thấp trên biển",
        "vùng biển nguy hiểm", "khu vực biển nguy hiểm", "nguy hiểm trên biển do bão", "nguy hiểm ven biển do bão", "gió mạnh trên biển", "gió mạnh ngoài khơi", "gió mạnh vùng biển", "gió giật vùng biển", "mưa to do bão", "mưa rất to do bão",
        "mưa to đến rất to do bão", "mưa lớn do hoàn lưu bão", "mưa diện rộng do bão", "mưa kéo dài do bão", "mưa cực lớn do bão", "dải mưa bão", "vùng mưa bão", "tố lốc trong hoàn lưu bão", "lốc xoáy trong hoàn lưu bão", "sét trong hoàn lưu bão",
        "nước biển dâng do bão", "triều dâng do bão", "sóng tràn do bão", "sóng tràn bờ do bão", "biển động sau bão", "biển động mạnh sau bão", "sóng lớn sau bão", "sóng lớn trên biển", "sóng cao nguy hiểm", "sóng lớn kèm gió mạnh",
        "cây đổ", "đổ cây", "bật gốc", "gãy đổ cây", "cây ngã đổ", "gãy đổ",
    ],

    "flood": [
        "lũ", "lũ lụt", "lụt", "lũ sông", "lũ trên sông", "lũ thượng nguồn", "lũ hạ lưu", "lũ nội đồng", "lũ đô thị", "lũ lên",
        "lũ lên nhanh", "lũ rút", "lũ rút chậm", "lũ dâng", "ngập", "ngập lụt", "ngập úng", "ngập sâu", "ngập nặng", "ngập trên diện rộng",
        "ngập kéo dài", "ngập nghiêm trọng", "ngập cục bộ", "ngập lụt cục bộ", "ngập nhà", "ngập đường", "ngập phố", "ngập quốc lộ", "ngập hầm", "ngập tràn",
        "ngập tới nóc", "nước ngập", "nước lụt", "nước lũ", "mực nước dâng", "mực nước sông dâng", "nước sông dâng", "mực nước lên nhanh", "mực nước dâng cao", "mực nước cao bất thường",
        "mực nước vượt ngưỡng", "đỉnh lũ", "đạt đỉnh", "đỉnh lũ lịch sử", "lũ lịch sử", "lũ lớn", "lũ cao", "mực nước báo động", "vượt báo động", "vượt mức báo động",
        "mực nước trên báo động", "trên báo động 3", "báo động 1", "báo động 2", "báo động 3", "vỡ đê", "tràn đê", "tràn bờ", "nước tràn bờ", "tràn bờ sông",
        "tràn bờ kè", "thẩm lậu", "mạch đùn", "mạch sủi", "rò rỉ thân đê", "thấm qua thân đê", "vỡ đập", "sự cố đập", "sự cố hồ đập", "vỡ hồ",
        "sự cố hồ chứa", "xả lũ", "xả tràn", "xả điều tiết", "xả lũ khẩn cấp", "xả lũ điều tiết", "mở cửa xả", "mở cửa xả lũ", "xả qua tràn", "xả qua đập tràn",
        "xả qua cửa van", "điều tiết hồ chứa", "hồ chứa xả lũ", "hồ thủy điện xả lũ", "thủy điện xả lũ", "chia cắt do ngập", "bị chia cắt do ngập", "cô lập do ngập", "bị cô lập do ngập", "tê liệt giao thông do ngập",
        "cắt đứt giao thông do ngập", "cuốn trôi", "bị cuốn trôi", "nước lũ cuốn trôi", "lũ cuốn trôi", "trôi dạt do lũ", "mất tích do lũ", "mắc kẹt do lũ", "đe dọa tính mạng do lũ", "uy hiếp do lũ",
        "lật ghe do lũ", "chìm ghe do lũ", "lật thuyền do lũ", "chìm thuyền do lũ", "chìm tàu do lũ", "đắm thuyền do lũ", "đắm tàu do lũ", "sập cầu do lũ", "gãy cầu do lũ", "sập đường do ngập",
        "đứt đường do ngập", "vùng trũng thấp", "khu vực trũng thấp", "rốn lũ", "vùng rốn lũ", "vùng lũ", "đồng bào vùng lũ", "chạy lũ", "mưa lũ", "ngập lụt diện rộng",
        "nước dâng ngập", "nước lên ngập", "nước dâng gây ngập", "ngập lút", "ngập ngang ngực", "ngập quá đầu gối", "ngập quá nửa bánh xe", "ngập tràn vào nhà", "nước tràn vào nhà", "nước tràn qua đường",
        "lũ trên sông dâng nhanh", "nước sông lên nhanh", "nước sông lên cao", "ngập do nước sông dâng", "ngập do lũ sông", "đê xung yếu", "điểm xung yếu đê điều", "hộ đê", "hộ đê khẩn cấp", "bảo vệ đê",
        "cửa xả lũ", "cửa van xả lũ", "vận hành xả lũ", "vận hành hồ chứa", "ngập úng đô thị", "ngập úng cục bộ", "thoát nước quá tải", "quá tải thoát nước", "nước rút chậm do ngập", "ngập lâu ngày",
        "lũ hạ du", "lũ vùng hạ du", "lũ hạ lưu sông", "lũ thượng lưu sông", "lũ trên lưu vực", "lũ trên lưu vực sông", "lũ lan rộng", "lũ dâng cao", "lũ đạt đỉnh", "lũ vượt đỉnh",
        "lũ chồng lũ", "lũ kép", "lũ hai đỉnh", "lũ lên lại", "lũ quay trở lại", "lũ trái mùa", "lũ đầu mùa", "lũ cuối mùa", "lũ sớm", "lũ muộn",
        "lũ tiểu mãn", "lũ bất thường", "lũ bất ngờ", "lũ kéo dài", "lũ ngập sâu", "lụt nặng", "lụt diện rộng", "lụt kéo dài", "lụt nghiêm trọng", "lụt lịch sử",
        "mực nước hạ du dâng", "mực nước thượng nguồn dâng", "mực nước xuống chậm", "mực nước rút chậm", "mực nước tiếp tục lên", "mực nước tiếp tục dâng", "mực nước dao động mạnh", "mực nước biến động", "mực nước đạt đỉnh", "mực nước vượt đỉnh",
        "lưu lượng nước", "lưu lượng đỉnh", "lưu lượng tăng nhanh", "lưu lượng về hồ", "lưu lượng nước về hồ", "lưu lượng xả", "lưu lượng xả lũ", "lưu lượng qua đập", "lưu lượng qua tràn", "dòng chảy lũ",
        "dòng chảy trên sông", "dòng chảy tăng mạnh", "dòng chảy lớn", "dòng chảy bất thường", "dòng chảy hạ lưu", "dòng chảy thượng lưu", "mưa gây lũ", "mưa gây ngập", "mưa gây ngập lụt", "ngập do mưa lớn",
        "ngập do mưa kéo dài", "ngập do nước sông", "ngập do nước sông lên", "ngập do nước dâng", "ngập lan vào khu dân cư", "ngập tràn khu dân cư", "ngập lụt vùng hạ du", "ngập lụt vùng trũng", "ngập lụt vùng ven sông", "ngập lụt khu đô thị",
        "ngập úng vùng trũng", "ngập úng kéo dài", "ngập úng nghiêm trọng", "điểm ngập", "điểm ngập nặng", "điểm ngập sâu", "điểm ngập cục bộ", "điểm ngập kéo dài", "tuyến đường ngập", "đường phố ngập sâu",
        "xe chết máy do ngập", "ô tô chết máy do ngập", "xe máy chết máy do ngập", "kẹt xe do ngập", "kẹt xe vì ngập", "tắc đường do ngập", "tắc đường vì ngập", "ngập hầm chui", "ngập đường hầm", "ngập cầu vượt thấp",
        "đê bao", "vỡ đê bao", "tràn đê bao", "đê bao xung yếu", "đê bao xuống cấp", "nước tràn qua đê bao", "gia cố đê bao", "gia cố đê điều", "đê điều xung yếu", "điểm xung yếu đê bao",
        "nứt thân đê", "nứt đê", "nứt mặt đê", "thấm nước qua đê", "thẩm thấu qua đê", "rò rỉ chân đê", "sủi bọt chân đê", "lỗ rò chân đê", "sạt mái đê do lũ", "xói chân đê",
        "xói lở chân kè", "xói lở bờ kè", "xói lở ven sông do lũ", "hà bá nuốt đất", "sạt bờ sông do lũ", "sụt bờ sông do lũ", "sụt kè do lũ", "sập kè do lũ", "tràn kè", "vỡ kè",
        "điều tiết lũ", "cắt lũ", "đón lũ", "đón lũ an toàn", "xả lũ liên hồ", "xả lũ liên hồ chứa", "vận hành liên hồ", "quy trình vận hành liên hồ", "vận hành điều tiết lũ", "vận hành xả lũ theo quy trình",
        "xả lũ gia tăng", "xả lũ tăng dần", "xả lũ giảm dần", "xả lũ theo lưu lượng", "xả lũ qua tràn tự do", "xả lũ qua cửa van", "mở thêm cửa xả", "mở rộng cửa xả", "đóng bớt cửa xả", "giảm lưu lượng xả",
        "mực nước hồ dâng", "mực nước hồ lên nhanh", "mực nước hồ cao", "mực nước hồ vượt ngưỡng", "mực nước hồ gần mức dâng bình thường", "mực nước hồ gần mực nước dâng bình thường", "mực nước hồ gần mực nước kiểm tra", "mực nước hồ vượt mực nước kiểm tra", "mực nước hồ vượt mực nước thiết kế", "nguy cơ quá tải hồ chứa",
        "lũ thiết kế", "lũ kiểm tra", "lũ vượt thiết kế", "lũ vượt kiểm tra", "mực nước thiết kế", "mực nước kiểm tra", "vận hành cắt lũ", "cắt lũ cho hạ du", "giảm lũ cho hạ du", "đỉnh lũ hạ du",
        "tiêu úng", "tiêu thoát úng", "tiêu nước", "bơm tiêu", "bơm tiêu úng", "trạm bơm tiêu", "bơm chống ngập", "trạm bơm chống ngập", "bơm thoát nước", "tăng công suất bơm",
        "cống thoát nước", "cống thoát nước quá tải", "nước tràn cống", "cống bị quá tải", "cống bị nghẹt", "nghẹt cống thoát nước", "miệng cống trào nước", "hố ga trào nước", "hệ thống thoát nước quá tải", "thoát nước kém",
        "nước mấp mé", "nước dâng mép bờ", "tràn qua mặt đường",
    ],

    "flash_flood": [
        "lũ quét", "lũ ống", "lũ bùn đá", "lũ bùn", "dòng bùn đá", "dòng bùn lũ", "dòng bùn tràn xuống", "lũ quét bùn đá", "lũ ống bất ngờ", "lũ quét bất ngờ",
        "lũ ập đến", "lũ đổ về", "nước lũ đổ về", "dòng lũ cuồn cuộn", "nước lũ cuồn cuộn", "lũ cuồn cuộn", "dòng lũ chảy xiết", "dòng chảy xiết", "nước chảy xiết", "nguy cơ lũ quét",
        "cảnh báo lũ quét", "cảnh báo lũ ống", "điểm nóng lũ quét", "cuốn phăng", "quét sạch", "san phẳng", "bùn đất tràn xuống", "đất đá đổ về", "đá tảng lăn xuống", "sạt lở kèm lũ quét",
        "lũ quét kèm sạt lở", "cuốn trôi cầu", "trôi cầu", "sập cầu do lũ quét", "đứt đường do lũ quét", "cuốn trôi nhà", "lũ quét trong đêm", "lũ ống trong đêm", "lũ quét ban đêm", "lũ ống ban đêm",
        "dòng lũ bất ngờ", "nước dâng đột ngột", "lũ dâng đột ngột", "đá tảng cuốn theo dòng lũ", "bùn đá cuốn trôi", "bùn đất cuốn theo dòng lũ", "cuốn phăng nhà cửa", "cuốn phăng tài sản", "lũ quét tàn phá", "vùng có nguy cơ lũ quét",
        "khu vực nguy cơ lũ quét", "lũ quét xảy ra", "lũ ống xảy ra", "lũ quét bất ngờ ập xuống", "lũ ống bất ngờ ập xuống", "nước lũ ập xuống", "nước từ thượng nguồn đổ về", "lũ từ thượng nguồn", "lũ đổ ập xuống", "nước đổ ập", "dòng lũ ập đến",
        "khe suối dâng cao", "suối dâng đột ngột", "suối nhỏ thành lũ", "suối cạn thành lũ", "nước suối dâng nhanh", "nước khe dâng nhanh", "dòng suối cuồn cuộn", "dòng khe cuồn cuộn", "nước đục ngầu", "nước đen ngòm bùn đất",
        "bùn đá tràn ập", "bùn đất tràn ập", "bùn đá ào ạt", "bùn đất ào ạt", "đất đá ào xuống", "đất đá tràn ập xuống", "dòng bùn đá ập xuống", "dòng bùn ập xuống", "bùn đá tràn vào nhà", "bùn đất tràn vào nhà",
        "lũ quét vùi lấp", "lũ ống vùi lấp", "bùn đá vùi lấp", "bùn đất vùi lấp", "đất đá vùi lấp nhà", "đất đá vùi lấp người", "lũ quét cuốn sập nhà", "lũ ống cuốn sập nhà", "lũ quét cuốn trôi người", "lũ ống cuốn trôi người",
        "lũ quét cuốn trôi xe", "lũ ống cuốn trôi xe", "lũ quét cuốn trôi gia súc", "lũ ống cuốn trôi gia súc", "lũ quét cuốn trôi hoa màu", "lũ ống cuốn trôi hoa màu", "lũ quét phá hỏng đường", "lũ ống phá hỏng đường", "lũ quét cuốn trôi cầu tạm", "lũ ống cuốn trôi cầu tạm",
        "đường bị cuốn phăng", "cầu tạm bị cuốn", "cống bị cuốn trôi", "cống bị phá hủy", "đứt đường liên thôn", "đứt đường liên xã", "đứt đường vào bản", "đường vào bản bị chia cắt", "chia cắt hoàn toàn do lũ quét", "cô lập hoàn toàn do lũ ống",
        "lũ quét trong tích tắc", "lũ ống trong tích tắc", "lũ quét trong vài phút", "lũ ống trong vài phút", "lũ quét ập xuống ban đêm", "lũ ống ập xuống ban đêm", "mưa lớn gây lũ quét", "mưa lớn gây lũ ống", "mưa cường suất lớn", "mưa cực đoan gây lũ quét",
        "cảnh báo nguy cơ lũ quét", "cảnh báo nguy cơ lũ ống", "nguy cơ cao lũ quét", "nguy cơ cao lũ ống", "điểm nguy cơ lũ quét", "khu vực có nguy cơ lũ ống", "vùng có nguy cơ lũ ống", "sơ tán tránh lũ quét", "sơ tán tránh lũ ống", "di dời khẩn cấp tránh lũ quét",
        "bùn đá tràn qua quốc lộ", "bùn đất tràn qua đường", "dòng bùn đá tràn qua", "đất đá chắn ngang đường", "đất đá bịt kín đường", "tắc đường do bùn đá", "khe suối biến thành dòng lũ", "suối biến thành dòng lũ", "dòng lũ đục ngầu", "dòng lũ mang theo đất đá",
    ],

    "landslide": [
        "sạt lở", "sạt lở đất", "trượt lở đất", "trượt đất", "trượt sạt", "sụt trượt", "trượt dốc", "trượt mái dốc", "lở núi", "sạt lở núi",
        "sụt núi", "lở đất đá", "sập taluy", "sạt taluy", "sạt taluy dương", "sạt taluy âm", "sập ta luy", "trượt mái ta luy", "sập mái dốc", "đất đá vùi lấp",
        "vùi lấp", "bùn đất vùi lấp", "đá vùi lấp", "đất đá sạt xuống", "đất đá tràn xuống", "đá lăn", "đá rơi", "đá tảng rơi", "rơi đá", "sạt lở bờ sông",
        "sạt lở bờ biển", "sạt lở bờ suối", "sạt lở ven sông", "sạt lở ven biển", "vết nứt núi", "nứt núi", "vết nứt sườn núi", "nứt taluy", "nứt mặt dốc", "đứt gãy địa chất",
        "sụp đổ địa chất", "sập hầm", "sập cầu do sạt lở", "gãy cầu do sạt lở", "sạt lở đường", "đứt đường do sạt lở", "sập đường do sạt lở", "cảnh báo sạt lở", "nguy cơ sạt lở", "điểm sạt lở",
        "điểm sạt trượt", "sạt lở nghiêm trọng", "sạt lở nguy hiểm", "sạt lở uy hiếp nhà dân", "sạt lở vùi lấp nhà", "sạt lở vùi lấp người", "đất đá đổ ập xuống", "đất đá sạt ập xuống", "đá tảng rơi xuống đường", "đường bị sạt lở","tuyến đường bị sạt lở",
        "sạt trượt", "sạt trượt đất", "trượt lở", "trượt lở mái dốc", "trượt lở taluy", "sạt trượt taluy", "sạt trượt mái taluy", "trượt sườn núi", "sạt sườn núi", "sạt mái dốc",
        "đá đổ", "đá đổ xuống đường", "đá đổ ập xuống", "đá lăn xuống đường", "đá rơi xuống đường", "đá tảng lăn", "đá tảng rơi", "đá từ trên núi rơi xuống", "đá rơi liên tiếp", "rơi đá nguy hiểm",
        "đất đá tràn ra đường", "bùn đất tràn ra đường", "đất đá tràn mặt đường", "bùn đất tràn mặt đường", "đất đá phủ kín mặt đường", "đất đá vùi lấp mặt đường", "bùn đất vùi lấp mặt đường", "khối đất đá sạt xuống", "khối đá sạt xuống", "khối trượt",
        "vết trượt", "vệt trượt", "cung trượt", "mặt trượt", "khe nứt sườn dốc", "khe nứt mái taluy", "nứt taluy dương", "nứt taluy âm", "nứt sườn núi", "nứt sạt trượt",
        "sạt lở ta luy", "sạt lở taluy đường", "sạt lở mái taluy", "taluy dương sạt lở", "taluy âm sạt lở", "sụt sạt taluy", "sập kè do sạt lở", "sạt kè", "sạt lở bờ kè", "sạt lở kè suối",
        "sạt lở bờ sông nghiêm trọng", "sạt lở bờ biển nghiêm trọng", "sạt lở ăn sâu", "sạt lở tiến sát nhà dân", "sạt lở uy hiếp nhà cửa", "sạt lở đe dọa nhà dân", "sạt lở đe dọa công trình", "sạt lở sát mép nhà", "sạt lở sát đường", "sạt lở sát khu dân cư",
        "điểm sạt lở mới", "phát sinh điểm sạt lở", "sạt lở tái diễn", "sạt lở tiếp diễn", "nguy cơ sạt lở tiếp tục", "nguy cơ sạt trượt tiếp tục", "cảnh báo sạt trượt", "cảnh báo trượt lở", "điểm sạt trượt nguy hiểm", "khu vực có nguy cơ sạt trượt",
        "đường đèo bị sạt lở", "đèo bị sạt lở", "sạt lở trên đèo", "sạt lở trên quốc lộ", "sạt lở trên tỉnh lộ", "tắc đường do sạt lở", "ách tắc do sạt lở", "giao thông tê liệt do sạt lở", "đường bị chia cắt do sạt lở", "phong tỏa do sạt lở",
        "bùn đất tràn xuống nhà", "đất đá tràn vào nhà", "đất đá sạt vào nhà", "đất đá đổ vào nhà", "đất đá sạt xuống khu dân cư", "sạt lở vùi lấp tài sản", "sạt lở làm hư hại nhà cửa", "sạt lở làm hư hỏng công trình", "sạt lở làm hư hỏng đường", "sạt lở làm sập tường",
        "nền đất yếu gây sạt lở", "mưa lớn gây sạt lở", "mưa kéo dài gây sạt lở", "đất ngấm nước gây trượt", "đất bão hòa nước", "sạt lở do mưa kéo dài", "sạt lở do mưa lớn", "sạt lở do nước ngấm", "sạt lở do địa chất yếu", "địa hình dốc dễ sạt lở",
        "quả đồi sạt lở", "nguy cơ sạt trượt", "vết nứt kéo dài", "đất đá tràn lấp",
    ],

    "subsidence": [
        "sụt lún", "sụt lún đất", "sụp lún", "lún sụt", "lún xụt", "lún nền", "lún mặt đường", "lún đường", "hố sụt", "hố tử thần",
        "hố sụt lún", "hố sập", "hố sụt sâu", "hố sụt lớn", "sụt đường", "sập đường do sụt lún", "sụt lún hạ tầng", "sụt lún công trình", "nứt toác", "nứt đất",
        "nứt nền", "nứt mặt đường", "nứt nhà", "nứt tường", "nứt móng", "hàm ếch", "hàm ếch hóa", "lún võng", "lún cục bộ", "tách lớp mặt đường",
        "biến dạng mặt đường", "biến dạng nền", "cảnh báo sụt lún", "nguy cơ sụt lún", "hố tử thần xuất hiện", "xuất hiện hố tử thần", "hố sụt bất ngờ", "hố sụt xuất hiện", "hố sụt giữa đường", "lún nứt nhà cửa",
        "lún nứt công trình", "mặt đường lún sâu",
        "nghiêng lún", "lún nghiêng", "lún lệch", "lún không đều", "lún không đồng đều", "lún chênh", "lún chênh lệch", "lún sụt nghiêm trọng", "lún sụt cục bộ", "sụt lún nghiêm trọng",
        "sụt nền", "sụt nền đường", "sụt nền nhà", "sụt nền công trình", "sụt móng", "sụt móng nhà", "sụt móng công trình", "nền đất sụt", "nền đất bị lún", "nền đất bị sụt",
        "mặt đường võng", "mặt đường võng xuống", "mặt đường sụp", "mặt đường sập", "mặt đường sụt", "đường bị sụt", "đường bị lún", "đường bị lún sâu", "đoạn đường bị sụt", "đoạn đường bị lún",
        "hố sụt khổng lồ", "hố sụt sâu hoắm", "hố sụt rộng", "hố sụt ăn sâu", "hố sụt lan rộng", "hố sụt mở rộng", "hố sụt nuốt chửng", "hố sụt nuốt xe", "hố sụt nuốt người", "hố sụt trên mặt đường",
        "sập hố ga", "sụt hố ga", "hố ga sập", "cống ngầm sập", "sụt cống", "cống bị sụt", "cống bị lún", "hầm ngầm sụt lún", "khoang rỗng dưới đường", "rỗng nền",
        "hang ngầm", "hốc rỗng", "hốc rỗng dưới nền", "xói ngầm", "xói ngầm nền", "xói ngầm dưới đường", "rỗng hóa nền", "sụt lún do xói ngầm", "sụt lún do rỗng nền", "nền rỗng",
        "nứt lún", "nứt lún nền", "nứt lún mặt đường", "nứt lún nhà cửa", "nứt lún công trình", "nứt lún lan rộng", "nứt lún kéo dài", "khe nứt lớn", "khe nứt sâu", "khe nứt rộng",
        "tường bị nghiêng", "nhà bị nghiêng", "cột bị nghiêng", "công trình bị nghiêng", "sàn bị nghiêng", "sàn bị lún", "sập sàn", "sập nền", "sập móng", "sập nhà do lún",
        "di dời do sụt lún", "cảnh báo nguy cơ sụt lún", "khoanh vùng sụt lún", "rào chắn khu vực sụt lún", "đóng đường do sụt lún", "phong tỏa khu vực sụt lún", "lún nứt nguy hiểm", "khu vực có nguy cơ sụt lún", "điểm sụt lún", "ổ sụt lún",
        "sụt lún do mưa lớn", "sụt lún sau mưa", "sụt lún sau ngập", "sụt lún do sạt lở ngầm", "sụt lún do nền yếu", "sụt lún do địa chất yếu", "sụt lún do rò rỉ nước", "sụt lún do vỡ ống nước", "sụt lún do vỡ cống", "sụt lún do sụp cống",
    ],

    "drought": [
        "hạn hán", "khô hạn", "khô hạn gay gắt", "hạn gay gắt", "hạn kéo dài", "hạn hán kéo dài", "khô kiệt", "khô cằn", "thiếu nước", "thiếu nước ngọt",
        "thiếu nước sinh hoạt", "thiếu nước tưới", "thiếu nước tưới tiêu", "khát nước", "cạn nước", "cạn kiệt", "cạn hồ", "hồ cạn", "cạn trơ đáy", "trơ đáy hồ",
        "mực nước xuống thấp", "mực nước chết", "mực nước chết hồ chứa", "dòng chảy kiệt", "kiệt nước", "dòng chảy suy giảm", "nguồn nước suy giảm", "suy giảm nguồn nước", "mùa cạn", "đỉnh điểm mùa khô",
        "thiếu hụt mưa", "ít mưa", "không mưa kéo dài", "mưa thiếu hụt", "nứt nẻ", "đất nứt nẻ", "nứt nẻ ruộng đồng", "đồng ruộng nứt nẻ", "héo úa", "cây trồng héo úa",
        "cháy lá", "khô cháy", "mất mùa do hạn", "chống hạn", "ứng phó hạn hán", "cấp nước khẩn cấp", "cấp nước tạm thời", "chở nước cứu hạn", "cảnh báo hạn hán", "nguy cơ hạn hán",
        "tình trạng hạn hán", "hạn nghiêm trọng", "thiếu nước sản xuất", "thiếu nước tưới cây", "thiếu nước cho chăn nuôi", "cấp nước luân phiên", "hạn chế cấp nước", "cắt nước luân phiên", "giếng khoan cạn", "giếng cạn",
        "suối cạn", "sông cạn","nắng hạn", "nắng hạn kéo dài", "khô hạn kéo dài", "khô hạn nghiêm trọng", "khô hạn cực đoan", "hạn cực đoan", "hạn thiếu nước", "đại hạn", "hạn kỷ lục", "hạn chưa từng có",
        "khô hạn diện rộng", "khô hạn trên diện rộng", "khô hạn lan rộng", "khô hạn bao trùm", "mùa khô gay gắt", "mùa khô khốc liệt", "mùa khô kéo dài", "nắng kéo dài", "không mưa trong nhiều ngày", "không mưa trong nhiều tuần",
        "nguồn nước cạn kiệt", "cạn kiệt nguồn nước", "suy kiệt nguồn nước", "nguồn nước khan hiếm", "khan hiếm nguồn nước", "thiếu hụt nguồn nước", "khủng hoảng nước", "khẩn cấp về nước", "thiếu nước trầm trọng", "thiếu nước nghiêm trọng",
        "nước sinh hoạt khan hiếm", "khát nước sinh hoạt", "thiếu nước ăn uống", "thiếu nước sinh hoạt trầm trọng", "thiếu nước sạch", "khan hiếm nước sạch", "cạn nước sinh hoạt", "hết nước sinh hoạt", "mất nước sinh hoạt", "cúp nước kéo dài",
        "cấp nước bằng xe bồn", "xe bồn chở nước", "xe bồn cấp nước", "xe téc chở nước", "xe téc cấp nước", "phát nước sinh hoạt", "phát nước miễn phí", "đi lấy nước sinh hoạt", "xếp hàng lấy nước", "đi xin nước",
        "giếng đào cạn", "giếng đào khô", "giếng khoan khô", "giếng khoan không có nước", "mạch nước ngầm suy giảm", "mực nước ngầm hạ thấp", "tụt mực nước ngầm", "nước ngầm cạn", "giếng trơ đáy", "đào giếng sâu hơn",
        "ao hồ cạn", "ao hồ khô", "ao hồ trơ đáy", "kênh mương khô", "mương khô", "kênh khô", "đập khô", "hồ thủy lợi cạn", "hồ thủy lợi xuống thấp", "mực nước hồ thủy lợi xuống thấp",
        "sông suối khô cạn", "suối trơ đáy", "lòng suối trơ đáy", "lòng sông trơ đáy", "dòng sông cạn trơ", "dòng chảy cạn kiệt", "dòng chảy suy kiệt", "dòng chảy giảm mạnh", "lưu lượng suy giảm", "lưu lượng xuống thấp",
        "thiếu nước tưới trầm trọng", "thiếu nước cho cây trồng", "thiếu nước tưới lúa", "thiếu nước tưới hoa màu", "không đủ nước tưới", "không có nước tưới", "cắt giảm tưới", "ngưng tưới", "bỏ vụ do hạn", "mất trắng do hạn",
        "ruộng đồng khô nẻ", "đồng ruộng khô nẻ", "nứt nẻ mặt ruộng", "đất khô nứt toác", "đất khô nứt chân chim", "cây chết khô", "cây trồng chết khô", "cỏ cháy khô", "khô cháy đồng ruộng", "lá khô cháy xém",
        "gia súc thiếu nước", "gia súc khát nước", "thiếu nước cho gia súc", "chăn nuôi thiếu nước", "gia cầm thiếu nước", "ao nuôi cạn nước", "nuôi trồng thủy sản thiếu nước", "thiếu nước cho thủy sản", "thiệt hại nông nghiệp do hạn", "thiệt hại sản xuất do hạn",
        "cảnh báo khô hạn", "nguy cơ khô hạn", "dự báo hạn hán", "dự báo khô hạn", "kịch bản hạn hán", "kế hoạch chống hạn", "phương án chống hạn", "tưới tiết kiệm", "tưới nhỏ giọt", "tưới luân phiên",
        "tích trữ nước", "trữ nước", "tăng cường trữ nước", "đào ao trữ nước", "bể chứa nước tạm", "bồn chứa nước tạm", "đắp đập tạm", "đập tạm trữ nước", "đắp bờ giữ nước", "đóng kênh trữ nước",
    ],

    "salinity": [
        "xâm nhập mặn", "nhiễm mặn", "mặn xâm nhập", "mặn xâm nhập sâu", "mặn xâm nhập sâu nội đồng", "nhiễm mặn sâu", "hạn mặn", "đợt hạn mặn", "mặn bủa vây", "độ mặn",
        "độ mặn tăng cao", "độ mặn vượt ngưỡng", "độ mặn vượt chuẩn", "độ mặn 4‰", "độ mặn 1‰", "độ mặn phần nghìn", "ranh mặn", "ranh mặn 4 g/l", "ranh mặn 4g/l", "ranh mặn 1‰",
        "ranh mặn 4‰", "ranh mặn dịch chuyển", "nước lợ", "nước nhiễm mặn", "nước bị nhiễm mặn", "thiếu nước ngọt do mặn", "cống ngăn mặn", "đóng cống ngăn mặn", "mở cống lấy nước ngọt", "đẩy mặn",
        "ngăn mặn", "trữ ngọt", "lấy nước ngọt", "cấp nước ngọt", "độ mặn tăng đột biến", "mặn vượt ngưỡng cho phép", "nước mặn xâm nhập", "cảnh báo xâm nhập mặn", "nguy cơ xâm nhập mặn", "tình trạng xâm nhập mặn",
        "mặn hóa", "mặn hóa đất", "mặn hóa nguồn nước", "độ mặn cao", "độ mặn tăng mạnh", "độ mặn đạt đỉnh", "lấy nước khi triều thấp", "lấy nước lúc triều thấp",
        "xâm nhập mặn tăng cao", "xâm nhập mặn gay gắt", "xâm nhập mặn nghiêm trọng", "xâm nhập mặn kéo dài", "xâm nhập mặn trên diện rộng", "mặn lấn sâu", "mặn lấn sâu nội đồng", "mặn lấn sâu vào sông", "mặn lan sâu", "mặn lan rộng",
        "ranh mặn lấn sâu", "ranh mặn ăn sâu", "ranh mặn vào sâu", "ranh mặn tiến sâu", "ranh mặn xâm nhập sâu", "ranh mặn mở rộng", "ranh mặn tăng nhanh", "ranh mặn dịch vào", "ranh mặn lùi ra", "ranh mặn thay đổi",
        "độ mặn đo được", "độ mặn ghi nhận", "độ mặn tăng nhanh", "độ mặn giảm chậm", "độ mặn dao động", "độ mặn biến động", "độ mặn lên cao", "độ mặn xuống thấp", "độ mặn bất thường", "độ mặn cao đột ngột",
        "độ mặn g/l", "độ mặn mg/l", "độ mặn ppt", "chỉ số độ mặn", "nồng độ muối", "nồng độ muối tăng", "nồng độ muối cao", "nước mặn", "nước mặn vào sâu", "nước mặn lấn sâu",
        "mặn xâm nhập cửa sông", "mặn theo cửa sông", "mặn theo sông vào", "mặn theo triều", "mặn theo thủy triều", "mặn theo dòng chảy", "mặn theo kênh rạch", "mặn vào kênh rạch", "mặn vào hệ thống kênh", "mặn tràn kênh rạch",
        "ngọt hóa", "ngọt hóa nguồn nước", "ngọt hóa kênh rạch", "ngọt hóa vùng ven biển", "giữ ngọt", "giữ ngọt nội đồng", "giữ ngọt vùng sản xuất", "bảo vệ nguồn nước ngọt", "bảo vệ vùng ngọt", "bảo vệ vùng sản xuất",
        "rửa mặn", "rửa mặn ruộng", "rửa mặn đất", "xả rửa mặn", "xả nước rửa mặn", "thau chua rửa mặn", "rửa mặn cải tạo đất", "cải tạo đất nhiễm mặn", "cải tạo đất mặn", "phục hồi đất nhiễm mặn",
        "lấy nước theo triều", "lấy nước theo con nước", "lấy nước lúc triều kém", "lấy nước khi triều xuống", "canh lấy nước", "canh con nước lấy ngọt", "tranh thủ lấy nước ngọt", "trữ nước ngọt", "tích nước ngọt", "dự trữ nước ngọt",
        "đóng cống ngăn mặn khẩn cấp", "đóng cống chống mặn", "đóng cống giữ ngọt", "mở cống lấy ngọt", "mở cống đón nước ngọt", "vận hành cống ngăn mặn", "điều tiết cống ngăn mặn", "đóng mở cống theo triều", "đập ngăn mặn", "đập tạm ngăn mặn",
        "thiếu nước ngọt do xâm nhập mặn", "nước sinh hoạt bị nhiễm mặn", "nước máy bị nhiễm mặn", "nguồn nước sinh hoạt nhiễm mặn", "giếng bị nhiễm mặn", "giếng nhiễm mặn", "nước giếng nhiễm mặn", "nước tưới nhiễm mặn", "không đủ nước ngọt", "khát nước do mặn",
        "nhiễm phèn", "phèn mặn", "phèn mặn gay gắt", "đất nhiễm phèn", "nước nhiễm phèn", "phèn bùng phát", "xì phèn", "nước phèn", "rửa phèn", "thau chua",
    ],

    "extreme_weather": [
        "mưa lớn", "mưa rất to", "mưa to đến rất to", "mưa cực lớn", "mưa kỷ lục", "lượng mưa kỷ lục", "mưa lịch sử", "mưa xối xả", "mưa như trút", "mưa trút xuống",
        "mưa trắng trời", "mưa tầm tã", "mưa rào xối xả", "mưa diện rộng", "mưa cục bộ", "mưa trái mùa", "mưa dông", "mưa giông", "mưa giông diện rộng", "dông",
        "giông", "dông lốc", "giông lốc", "giông tố", "giông cực mạnh", "dông mạnh", "lốc", "lốc xoáy", "vòi rồng", "tố lốc",
        "lốc mạnh", "sét", "sét đánh", "giông sét", "phóng điện", "sét đánh trúng", "sét đánh chết người", "mưa đá", "mưa đá kèm dông lốc", "mưa đá dữ dội",
        "gió mạnh", "gió giật mạnh", "gió giật rất mạnh", "gió giật trên cấp", "gió rít", "gió lốc", "quật đổ", "tốc mái", "sập mái", "đổ cây",
        "cây đổ", "cột điện đổ", "mưa kèm lốc", "mưa kèm sét", "mưa kèm gió giật", "thời tiết cực đoan", "hiện tượng thời tiết cực đoan", "mưa cực đoan", "dông mạnh kèm lốc", "lốc kèm mưa đá",
        "mưa đá kèm gió giật", "sét đánh liên tiếp", "sét đánh trúng nhà", "sét đánh trúng người", "gió giật mạnh kèm mưa", "mưa lớn kèm gió giật",
        "mưa rào", "mưa rào và dông", "mưa rào kèm dông", "mưa rào kèm sét", "mưa rào rải rác", "mưa rào từng đợt", "mưa rào mạnh", "mưa rào lớn", "mưa lớn bất thường", "mưa lớn đột ngột",
        "mưa lớn cục bộ", "mưa rất lớn cục bộ", "mưa to cục bộ", "mưa dồn dập", "mưa nặng hạt", "mưa tạt", "mưa tạt ngang", "mưa táp", "mưa táp vào nhà", "mưa táp mạnh",
        "mưa lớn trong thời gian ngắn", "mưa lớn trong ít giờ", "mưa lớn trong vài giờ", "mưa cường suất lớn", "cường suất mưa lớn", "mưa cực lớn trong thời gian ngắn", "mưa dông kèm gió mạnh", "mưa dông kèm gió giật", "mưa dông dữ dội", "mưa dông kéo dài",
        "dông mạnh kèm sét", "dông sét nguy hiểm", "dông sét dữ dội", "sét đánh nhiều nơi", "sét đánh dồn dập", "sét đánh gây cháy", "sét đánh gây hỏa hoạn", "sét đánh cháy nhà", "sét đánh cháy rừng", "sét đánh vào cột điện",
        "sét đánh vào trạm biến áp", "sét đánh đứt dây điện", "sét đánh hư hỏng thiết bị", "sét đánh gây mất điện", "sét đánh làm hư hại", "tia sét", "tia sét liên hồi", "sét đánh trúng mái nhà", "sét đánh trúng cây", "sét đánh gây thương vong",
        "lốc giật", "lốc giật mạnh", "lốc giật cục bộ", "lốc xoáy cục bộ", "lốc xoáy bất ngờ", "lốc xoáy quét qua", "lốc xoáy tàn phá", "gió lốc giật mạnh", "gió giật mạnh cục bộ", "gió giật mạnh từng cơn",
        "gió giật mạnh bất thường", "gió giật dữ dội", "gió giật liên hồi", "gió giật tăng mạnh", "gió giật làm tốc mái", "gió giật làm đổ cây", "gió giật làm gãy cây", "gió giật làm đổ cột", "gió giật làm sập mái", "gió giật gây thiệt hại",
        "mưa đá rơi dày", "mưa đá dày đặc", "mưa đá rơi như trút", "mưa đá to", "mưa đá kích thước lớn", "mưa đá kéo dài", "mưa đá làm thủng mái", "mưa đá làm vỡ mái", "mưa đá làm vỡ kính", "mưa đá gây hư hại",
        "mưa đá làm hư hỏng nhà", "mưa đá làm hư hại hoa màu", "mưa đá làm dập nát", "mưa đá làm gãy cây", "mưa đá gây thiệt hại nặng", "mưa đá bất ngờ", "mưa đá cục bộ", "mưa đá trên diện rộng", "mưa đá kèm gió lốc", "mưa đá kèm sét",
        "đổ trụ điện", "gãy trụ điện", "đứt dây điện", "đứt dây cáp", "đổ biển quảng cáo", "bay mái tôn", "tốc mái tôn", "bung mái tôn", "thổi bay mái", "sập tường rào",
        "cây bật gốc", "cây gãy đổ", "gãy cành", "gãy nhánh", "đổ cột điện", "gãy cột điện", "đổ cột viễn thông", "gãy cột viễn thông", "đổ giàn giáo", "đổ rạp nhà tạm",
        "mưa lớn gây ngập cục bộ", "mưa lớn gây ngập nhanh", "ngập nhanh sau mưa", "nước dâng nhanh sau mưa", "nước chảy xiết sau mưa", "đường ngập sau mưa", "ngập lụt sau mưa", "sạt lở sau mưa", "sạt trượt sau mưa", "đá rơi sau mưa",
        "giông lốc mạnh", "cây xanh gãy đổ", "tôn bay", "cột điện gãy",
    ],

    "heatwave": [
        "nắng nóng", "đợt nắng nóng", "nắng nóng gay gắt", "nắng nóng đặc biệt gay gắt", "nắng nóng kéo dài", "nắng nóng diện rộng", "nắng nóng cục bộ", "nhiệt độ tăng cao", "nhiệt độ cao", "nhiệt độ kỷ lục",
        "đỉnh điểm nắng nóng", "nắng như đổ lửa", "nóng như thiêu như đốt", "nóng đỉnh điểm", "nóng rát", "chỉ số UV", "UV rất cao", "cảnh báo nắng nóng", "cấp độ rủi ro do nắng nóng", "say nắng",
        "sốc nhiệt", "kiệt sức vì nóng", "ngất xỉu vì nắng", "nắng hạn", "thiếu điện do nắng nóng", "quá tải điện do nắng nóng", "nguy cơ nắng nóng", "nắng nóng kỷ lục", "nhiệt độ vượt 40 độ", "nhiệt độ vượt 39 độ",
        "nhiệt độ vượt 38 độ", "mất nước do nắng nóng", "kiệt sức do nắng nóng",
        "nắng nóng cực đoan", "nắng nóng khốc liệt", "nắng nóng dữ dội", "nắng nóng nghiêm trọng", "nắng nóng tăng cường", "nắng nóng quay trở lại", "nắng nóng tái diễn", "nắng nóng kéo dài nhiều ngày", "đợt nóng", "đợt nóng kéo dài",
        "nhiệt độ cao nhất", "nhiệt độ cao nhất ngày", "nhiệt độ cao nhất phổ biến", "nhiệt độ cao nhất ở mức", "nhiệt độ cao nhất vượt ngưỡng", "nhiệt độ ban ngày", "nhiệt độ ban đêm cao", "đêm nóng", "đêm oi bức", "nền nhiệt cao",
        "nền nhiệt tăng", "nền nhiệt tăng mạnh", "nền nhiệt duy trì cao", "nền nhiệt cao kéo dài", "nhiệt độ trung bình cao", "nhiệt độ tăng nhanh", "nhiệt độ tăng mạnh", "nhiệt độ tăng vọt", "nhiệt độ duy trì trên cao", "nhiệt độ phổ biến",
        "cảm giác oi bức", "oi bức", "oi nóng", "nóng oi", "nóng hầm hập", "ngột ngạt", "nóng ngột ngạt", "hầm hập", "bức bối", "bốc hơi nóng",
        "cảm giác như", "nhiệt độ cảm nhận", "cảm giác nhiệt", "nhiệt độ cảm nhận cao", "cảm giác như 40 độ", "cảm giác như 42 độ", "cảm giác như 45 độ", "cảm giác như 50 độ", "nắng gắt", "nắng gắt gay gắt",
        "tia UV", "chỉ số UV cao", "chỉ số UV ở mức cao", "chỉ số UV nguy cơ cao", "UV ở mức rất cao", "UV ở mức nguy hiểm", "tia cực tím mạnh", "cảnh báo tia UV", "nguy cơ tia UV", "UV tăng cao",
        "hạn chế ra đường", "tránh ra đường giờ nắng", "khuyến cáo hạn chế ra đường", "tránh nắng giờ cao điểm", "tránh nắng", "trú nắng", "tìm nơi trú nắng", "uống đủ nước", "bổ sung nước", "bù nước",
        "mất nước", "mất nước nghiêm trọng", "say nóng", "choáng do nóng", "choáng váng do nóng", "ngất do nóng", "đột quỵ do nóng", "đột quỵ nhiệt", "tăng nguy cơ đột quỵ", "nhập viện vì nắng nóng",
        "cháy nắng", "bỏng nắng", "da bỏng rát", "rộp da do nắng", "khô rát cổ họng", "kiệt sức do nóng", "mệt lả vì nóng", "lả người vì nóng", "suy nhược do nóng", "tử vong do nắng nóng",
        "tiêu thụ điện tăng cao", "nhu cầu điện tăng vọt", "tải điện tăng cao", "lưới điện quá tải", "nguy cơ quá tải lưới điện", "cắt điện luân phiên", "mất điện do quá tải", "cúp điện do quá tải", "thiếu nước sinh hoạt do nắng nóng", "nguy cơ cháy nổ do nắng nóng",
        "cảnh báo nền nhiệt cao", "cảnh báo nóng", "cấp độ rủi ro nắng nóng", "rủi ro do nắng nóng", "nắng nóng nguy hiểm", "mức cảnh báo nắng nóng", "dự báo nắng nóng", "xu hướng nắng nóng", "đỉnh nóng", "đỉnh nóng trong ngày",
    ],

    "cold_surge": [
        "rét đậm", "rét hại", "rét đậm rét hại", "đợt rét", "đợt rét mạnh", "rét tăng cường", "không khí lạnh", "không khí lạnh tăng cường", "gió mùa đông bắc", "gió mùa đông bắc mạnh",
        "gió mùa đông bắc tăng cường", "nhiệt độ xuống thấp", "nhiệt độ giảm sâu", "giảm nhiệt mạnh", "rét buốt", "rét tê tái", "lạnh cắt da cắt thịt", "băng giá", "băng tuyết", "tuyết rơi",
        "mưa tuyết", "sương muối", "sương muối dày", "bám băng", "đóng băng", "trắng xóa băng", "băng phủ", "băng bám cây", "cảnh báo rét đậm rét hại", "nguy cơ rét hại",
        "rét kỷ lục", "lạnh kỷ lục", "nhiệt độ dưới 10 độ", "nhiệt độ dưới 5 độ", "nhiệt độ xuống 0 độ", "gia súc chết rét", "cây trồng chết rét",
        "trời rét", "trời chuyển rét", "trời rét buốt", "giá rét", "giá lạnh", "rét sâu", "rét đậm kéo dài", "rét hại kéo dài", "rét kéo dài nhiều ngày", "đợt không khí lạnh",
        "khối không khí lạnh", "khối không khí lạnh tăng cường", "không khí lạnh tràn về", "không khí lạnh tràn xuống", "không khí lạnh ảnh hưởng", "không khí lạnh bao trùm", "không khí lạnh mạnh", "không khí lạnh suy yếu", "không khí lạnh bổ sung", "không khí lạnh liên tiếp",
        "gió mùa tràn về", "gió mùa đông bắc tràn về", "gió mùa tăng mạnh", "gió mùa hoạt động mạnh", "gió mùa gây rét", "gió mùa gây lạnh", "gió mùa gây rét buốt", "gió mùa kèm mưa nhỏ", "gió mùa kèm mưa phùn", "gió mùa kèm sương mù",
        "nền nhiệt giảm", "nền nhiệt giảm sâu", "nền nhiệt giảm mạnh", "nền nhiệt xuống thấp", "nền nhiệt thấp", "nền nhiệt duy trì thấp", "nhiệt độ giảm mạnh", "nhiệt độ giảm nhanh", "nhiệt độ giảm sâu", "nhiệt độ giảm đột ngột",
        "lạnh sâu", "lạnh kéo dài", "lạnh tăng cường", "lạnh buốt", "lạnh tê tái", "lạnh giá", "lạnh rét", "lạnh dưới 10 độ", "lạnh dưới 5 độ", "lạnh dưới 0 độ",
        "sương mù dày", "sương mù", "mưa phùn", "mưa phùn gió bấc", "gió bấc", "gió bấc mạnh", "rét kèm mưa", "rét kèm mưa phùn", "ẩm lạnh", "lạnh ẩm",
        "băng giá xuất hiện", "xuất hiện băng giá", "băng giá dày", "băng giá phủ trắng", "băng giá trên đỉnh núi", "đóng băng mặt đường", "đóng băng mặt đường đèo", "đóng băng mặt nước", "đóng băng ruộng", "băng tràn",
        "tuyết phủ", "tuyết phủ trắng", "tuyết rơi dày", "tuyết rơi trắng núi", "mưa tuyết dày", "băng tuyết phủ trắng", "băng tuyết xuất hiện", "tuyết xuất hiện", "tuyết rơi trên núi", "tuyết rơi vùng cao",
        "sương muối xuất hiện", "xuất hiện sương muối", "sương muối phủ trắng", "sương muối gây hại", "sương muối làm cháy lá", "sương muối làm hư hại", "sương muối làm chết cây", "sương muối dày đặc", "sương muối trên cây", "sương muối trên ruộng",
        "vùng núi cao rét hại", "vùng núi rét đậm", "vùng núi rét sâu", "vùng cao rét buốt", "đèo rét buốt", "đỉnh núi băng giá", "vùng cao có băng giá", "vùng núi có tuyết", "vùng cao có sương muối", "khu vực vùng núi",
        "cây trồng bị rét", "cây trồng thiệt hại do rét", "hoa màu bị rét", "gia súc bị rét", "gia súc rét", "gia súc bị chết", "che chắn chuồng trại", "ủ ấm cho gia súc", "phòng chống rét", "chống rét cho cây trồng",
    ],

    "earthquake": [
        "động đất", "rung chấn", "rung lắc", "rung lắc mạnh", "dư chấn", "dư chấn mạnh", "tâm chấn", "chấn tiêu", "độ sâu chấn tiêu", "độ sâu tâm chấn",
        "thang richter", "cấp độ richter", "độ lớn động đất", "độ lớn theo thang richter", "magnitude", "độ lớn magnitude", "sóng địa chấn", "chấn phát", "dạng sóng địa chấn", "viện vật lý địa cầu",
        "trung tâm báo tin động đất", "thông báo động đất", "ghi nhận động đất", "cảnh báo động đất", "nguy cơ động đất", "người dân cảm nhận rung lắc", "rung lắc kéo dài", "rung lắc trong vài giây", "động đất kích thích",
        "địa chấn", "chấn động", "rung chuyển", "rung chuyển mạnh", "chấn động mạnh", "rung động", "rung động mạnh", "nhà cửa rung lắc", "đồ vật rung lắc", "cảm nhận động đất",
        "xảy ra động đất", "động đất xảy ra", "động đất xảy ra lúc", "ghi nhận rung chấn", "ghi nhận rung lắc", "ghi nhận dư chấn", "liên tiếp dư chấn", "dư chấn liên tiếp", "dư chấn tiếp diễn", "sau đó xảy ra dư chấn",
        "tâm chấn ở", "tâm chấn tại", "tâm chấn gần", "tâm chấn cách", "độ sâu chấn tiêu khoảng", "độ sâu tâm chấn khoảng", "chấn tiêu nông", "chấn tiêu sâu", "tâm chấn ngoài khơi", "tâm chấn trên đất liền",
        "kinh độ", "vĩ độ", "tọa độ tâm chấn", "tọa độ tâm chấn ở", "tọa độ kinh độ", "tọa độ vĩ độ", "vị trí tâm chấn", "vị trí chấn tiêu", "khu vực tâm chấn", "vùng tâm chấn",
        "độ lớn M", "độ lớn M3", "độ lớn M4", "độ lớn M5", "độ lớn M6", "động đất độ lớn", "động đất mạnh", "động đất vừa", "động đất nhỏ", "động đất trung bình",
        "cường độ động đất", "cường độ rung", "cấp độ rung", "mức độ rung lắc", "mức độ rung chấn", "cường độ theo thang", "thang cường độ", "thang Mercalli", "cấp độ Mercalli", "cường độ cảm nhận",
        "đứt gãy", "đứt gãy địa chất", "đới đứt gãy", "hoạt động đứt gãy", "trượt đứt gãy", "phát sinh địa chấn", "chuyển động kiến tạo", "mảng kiến tạo", "tái hoạt động đứt gãy", "động đất do đứt gãy",
        "gia tốc nền", "dao động nền", "rung nền", "rung nền đất", "chấn động mặt đất", "rung chấn mặt đất", "sóng P", "sóng S", "sóng mặt", "bản ghi địa chấn",
        "dân chạy ra đường", "người dân hoảng sợ", "hoảng loạn vì rung lắc", "sơ tán khỏi nhà", "chạy ra khỏi nhà", "rung lắc làm rơi đồ", "đồ đạc đổ", "tường bị nứt do rung chấn", "nhà bị nứt do động đất", "nứt tường do động đất",
        "động đất cảm nhận rõ", "cảm nhận rõ rung lắc", "rung lắc rõ rệt", "rung lắc mạnh ở tầng cao", "rung lắc ở nhà cao tầng", "rung lắc ở chung cư", "rung lắc ở nhiều khu vực", "rung lắc lan rộng", "rung lắc trên diện rộng", "cảm nhận rung lắc ở",
    ],

    "tsunami": [
        "sóng thần", "tsunami", "cảnh báo sóng thần", "tin sóng thần", "nguy cơ sóng thần", "nước biển rút bất thường", "biển rút bất thường", "mực nước biển biến động bất thường", "sóng thần cao", "sóng cao hàng chục mét",
        "sóng thần tàn phá", "thảm họa sóng thần", "sơ tán do sóng thần", "khu vực nguy cơ sóng thần", "theo dõi sóng thần", "sóng thần có thể xảy ra", "tín hiệu cảnh báo sóng thần", "hệ thống cảnh báo sóng thần",
        "sóng thần cảnh báo", "phát cảnh báo sóng thần", "ban hành cảnh báo sóng thần", "nâng cấp cảnh báo sóng thần", "hạ cấp cảnh báo sóng thần", "hủy cảnh báo sóng thần", "dỡ bỏ cảnh báo sóng thần", "cập nhật cảnh báo sóng thần", "trạng thái cảnh báo sóng thần", "cảnh báo sóng thần khẩn cấp",
        "cảnh báo sóng thần cho ven biển", "cảnh báo sóng thần dọc bờ biển", "cảnh báo sóng thần vùng ven biển", "khu vực ven biển nguy hiểm", "vùng ven biển nguy cơ", "khuyến cáo tránh xa bờ biển", "khuyến cáo rời khỏi bờ biển", "di tản khỏi vùng ven biển", "sơ tán khu vực ven biển", "rút lên cao tránh sóng thần",
        "sóng thần do động đất", "động đất dưới đáy biển", "động đất ngoài khơi", "động đất mạnh ngoài khơi", "tâm chấn ngoài biển", "động đất đáy biển", "đứt gãy dưới biển", "trượt lở đáy biển", "sạt lở đáy biển", "núi lửa dưới biển",
        "dự báo sóng thần", "bản tin sóng thần", "trung tâm cảnh báo sóng thần", "cơ quan cảnh báo sóng thần", "theo dõi diễn biến sóng thần", "giám sát sóng thần", "quan trắc sóng thần", "trạm quan trắc mực nước", "phao cảnh báo sóng thần", "cảm biến sóng thần",
        "thời gian sóng đến", "thời điểm sóng đến", "giờ sóng đến", "sóng thần có thể đến", "sóng thần sẽ đến", "sóng thần lan truyền", "sóng thần di chuyển nhanh", "sóng thần truyền qua đại dương", "sóng thần ảnh hưởng", "ảnh hưởng của sóng thần",
        "mực nước biển dâng nhanh", "mực nước biển rút nhanh", "nước biển rút sâu", "nước biển rút mạnh", "nước biển dâng đột ngột", "mực nước biển dâng bất thường", "mực nước biển rút bất thường", "biển rút sâu", "biển dâng nhanh", "biển dâng bất thường",
        "sóng thần tràn bờ", "sóng thần tràn vào", "sóng thần ập vào bờ", "nước tràn vào đất liền", "sóng tràn vào đất liền", "nước cuốn trôi", "dòng nước mạnh cuốn trôi", "sóng cuốn trôi", "sóng tràn phá", "sóng thần gây ngập",
        "chiều cao sóng thần", "độ cao sóng", "sóng cao bất thường", "sóng cao đột biến", "mực nước tăng bất thường", "mực nước biến động mạnh", "biên độ mực nước", "dao động mực nước mạnh", "mực nước dao động mạnh", "mực nước lên xuống nhanh",
        "tác động sóng thần", "thiệt hại do sóng thần", "thương vong do sóng thần", "ngập lụt do sóng thần", "sóng thần phá hủy nhà cửa", "sóng thần cuốn trôi nhà cửa", "sóng thần cuốn trôi tàu thuyền", "tàu thuyền bị cuốn trôi", "cảng biển bị ảnh hưởng", "khu vực cảng bị ảnh hưởng",
        "không xuống biển", "cấm xuống biển do sóng thần", "cấm tắm biển", "tạm dừng hoạt động ven biển", "đóng cửa bãi biển", "người dân không tụ tập ven biển", "không đứng gần mép nước", "tránh xa cửa sông", "tránh xa khu vực trũng ven biển", "sơ tán theo phương án",
    ],

    "storm_surge": [
        "nước dâng", "nước dâng do bão", "nước biển dâng", "nước dâng ven biển", "nước dâng do áp thấp", "sóng tràn", "sóng tràn bờ", "sóng đánh vào bờ", "sóng biển cao", "sóng biển dâng",
        "triều cường", "đỉnh triều", "thủy triều dâng", "triều cường vượt mức", "triều cường đạt đỉnh", "ngập do triều cường", "ngập lụt do triều", "ngập do nước dâng", "ngập ven biển do triều cường", "xâm thực do sóng",
        "xói lở do sóng", "vỡ kè biển", "tràn kè", "tràn đê biển", "cảnh báo triều cường", "cảnh báo nước dâng", "cảnh báo nước biển dâng", "nước dâng đạt đỉnh", "mực triều dâng cao", "triều dâng cao",
        "ngập ven biển do nước dâng",
        "nước biển dâng cao", "mực nước biển dâng cao", "mực nước biển lên cao", "mực nước biển tăng cao", "mực nước dâng cao", "mực nước dâng nhanh", "mực nước ven biển dâng", "mực nước vùng cửa sông dâng", "nước dâng cao bất thường", "nước dâng đột biến",
        "mực triều", "mực triều lên", "mực triều lên nhanh", "mực triều tăng", "mực triều tăng nhanh", "mực triều cao", "mực triều cao bất thường", "mực triều vượt ngưỡng", "mực triều đạt mức cao", "mực triều lên mức cao",
        "cường triều", "đợt triều cường", "đợt cường triều", "triều cường tăng mạnh", "triều cường lên nhanh", "triều cường kéo dài", "triều cường rút chậm", "triều cường bất thường", "triều cường diện rộng", "cường triều kết hợp sóng lớn",
        "triều kém", "kỳ triều kém", "kỳ triều cường", "con nước lớn", "con nước ròng", "nước lớn", "nước ròng", "triều lên", "triều xuống", "triều lên nhanh",
        "ngập vùng trũng ven biển", "ngập khu vực ven biển", "ngập sâu ven biển", "ngập đường ven biển", "ngập tuyến ven biển", "ngập khu dân cư ven biển", "ngập bãi biển", "nước tràn vào khu dân cư", "nước tràn vào nhà", "nước tràn qua đường",
        "sóng lớn kết hợp triều cường", "sóng lớn kèm triều cường", "sóng biển cao kèm triều", "sóng cao kèm nước dâng", "sóng mạnh kèm triều", "sóng mạnh đánh thẳng vào bờ", "sóng đánh mạnh", "sóng đánh liên hồi", "sóng dồn dập", "sóng xô bờ",
        "sóng vượt kè", "sóng vượt đê", "sóng tràn qua kè", "sóng tràn qua đê", "nước tràn qua kè", "nước tràn qua đê", "tràn qua kè biển", "tràn qua đê biển", "tràn qua bờ kè", "sóng đánh tràn bờ",
        "kè chắn sóng", "đê chắn sóng", "kè biển", "đê biển", "kè bị hư hỏng", "kè bị sạt", "kè bị xói", "kè bị phá hỏng", "đê biển xung yếu", "kè biển xung yếu",
        "xói lở bờ biển do sóng", "xói lở bờ do sóng", "xâm thực bờ biển do sóng", "xâm thực bờ biển", "xâm thực bờ", "sạt lở bờ biển do sóng", "sạt lở kè biển", "xói chân kè", "hở chân kè", "sạt chân kè",
        "cảnh báo triều", "cảnh báo mực triều", "cảnh báo triều dâng", "cảnh báo ngập do triều", "khuyến cáo hạn chế ra biển", "khuyến cáo tránh khu vực trũng", "đóng đường ven biển", "cấm đường ven biển", "di dời vùng trũng ven biển", "chằng chống nhà cửa ven biển",
    ],

    "wildfire": [
        "cháy rừng", "cháy rừng phòng hộ", "cháy rừng đặc dụng", "cháy rừng sản xuất", "cháy thực bì", "cháy thảm thực bì", "cháy tán", "cháy ngầm", "cháy dưới tán", "đám cháy",
        "đám cháy lan", "cháy lan nhanh", "lửa rừng", "giặc lửa", "bùng phát cháy rừng", "cột khói", "khói mù", "khói dày đặc", "điểm cháy", "ổ cháy",
        "đám cháy lớn", "dập lửa", "dập tắt đám cháy", "chữa cháy rừng", "khống chế đám cháy", "nguy cơ cháy rừng", "cảnh báo cháy rừng", "cấp dự báo cháy rừng", "PCCCR", "phòng cháy chữa cháy rừng",
        "trực PCCCR", "thiêu rụi", "cháy rụi", "tàn tro", "nguy cơ cháy rừng rất cao", "cấp cháy rừng cực kỳ nguy hiểm", "cấp dự báo cháy rừng cấp IV", "cấp dự báo cháy rừng cấp V", "bốc cháy", "bùng cháy", "cháy lan sang khu dân cư",
        "cháy rừng bùng phát trở lại", "bùng phát trở lại", "đám cháy bùng phát trở lại", "cháy tái phát", "cháy bùng phát", "cháy bùng lên", "lửa bùng lên", "bùng phát dữ dội", "bùng phát mạnh", "cháy lan rộng",
        "đám cháy lan rộng", "đám cháy vượt tầm kiểm soát", "cháy mất kiểm soát", "đám cháy bùng mạnh", "đám cháy dữ dội", "ngọn lửa bốc cao", "lửa bốc cao", "khói bốc cao", "cột khói bốc cao", "khói bốc lên nghi ngút",
        "cháy âm ỉ", "đám cháy âm ỉ", "tàn lửa", "đốm lửa", "đốm cháy", "tàn lửa âm ỉ", "lửa cháy âm ỉ", "than hồng", "tàn tro còn nóng", "nguy cơ bùng phát lại",
        "cháy trên diện rộng", "cháy hàng chục ha", "cháy hàng trăm ha", "cháy rừng trên diện rộng", "thiệt hại hàng chục ha", "thiệt hại hàng trăm ha", "rừng bị thiêu rụi", "thiêu rụi nhiều ha", "cháy trụi", "cháy trụi rừng",
        "cháy rừng tự nhiên", "cháy rừng thông", "cháy rừng keo", "cháy rừng tràm", "cháy rừng bạch đàn", "cháy rừng tre nứa", "cháy rừng ven biển", "cháy rừng trên núi", "cháy rừng đồi", "cháy rừng vùng giáp ranh",
        "đường băng cản lửa", "băng cản lửa", "đường ranh cản lửa", "mở đường băng cản lửa", "phát đường băng", "khoanh vùng đám cháy", "khoanh vùng dập lửa", "tạo vành đai cản lửa", "dọn thực bì tạo vành đai", "cắt đường lửa",
        "phun nước dập lửa", "bơm nước dập lửa", "vòi phun chữa cháy", "máy bơm chữa cháy", "bình chữa cháy dã chiến", "dập lửa xuyên đêm", "chữa cháy xuyên đêm", "dập lửa suốt đêm", "căng mình dập lửa", "khống chế hoàn toàn",
        "dập tắt hoàn toàn", "dập tắt triệt để", "không để bùng phát lại", "đề phòng cháy tái phát", "tăng cường canh gác", "túi nước chữa cháy", "xe bồn chở nước", "máy thổi gió dập lửa", "dụng cụ dập lửa", "chữa cháy tại chỗ",
        "huy động lực lượng", "huy động phương tiện", "điều động lực lượng", "điều động phương tiện", "lực lượng kiểm lâm", "lực lượng PCCCR", "dân quân tự vệ", "bộ đội tham gia chữa cháy", "công an tham gia chữa cháy", "chính quyền địa phương huy động",
        "cấm lửa trong rừng", "cấm vào rừng", "đóng cửa rừng", "tạm dừng vào rừng", "hạn chế vào rừng", "tuần tra bảo vệ rừng", "canh gác lửa rừng", "trực gác lửa", "kiểm soát nguồn lửa", "ngăn chặn nguồn lửa",
        "nguy cơ cháy lan", "nguy cơ cháy bùng phát", "nguy cơ cháy tăng cao", "nguy cơ cháy cực cao", "cảnh báo cấp V", "cảnh báo cấp IV", "cấp nguy hiểm cháy rừng", "cấp cực kỳ nguy hiểm", "cấp rất nguy hiểm", "mức cảnh báo cháy rừng",
        "khói lan vào khu dân cư", "khói bao phủ khu dân cư", "khói mù do cháy rừng", "bụi khói dày đặc", "khó thở do khói", "tầm nhìn giảm do khói", "ảnh hưởng giao thông do khói", "đóng đường vì khói", "sơ tán vì cháy rừng", "di dời vì cháy rừng",
    ],

    "erosion": [
        "xói lở", "xói lở nghiêm trọng", "xói lở tăng nhanh", "xói lở tiến sát", "xói lở bờ sông", "xói lở bờ biển", "xói lở bờ", "xói lở bãi bồi", "xói lở cửa sông", "xâm thực",
        "xâm thực biển", "xâm thực bờ biển", "xâm thực bờ sông", "xói mòn", "xói mòn đất", "mất đất do xói mòn", "rãnh xói", "mương xói", "hàm ếch bờ sông", "hàm ếch bờ biển",
        "sụt bờ", "sụt bờ sông", "sụt bờ biển", "mất bờ", "mất đất", "cảnh báo xói lở", "nguy cơ xói lở", "xói lở uy hiếp nhà dân", "xói lở ăn sâu", "sạt hàm ếch",
        "hàm ếch ăn sâu", "xói lở làm sụt nhà", "xói lở làm sụt đường",
        "xói lở ăn sát", "xói lở ăn sát nhà", "xói lở ăn sát đường", "xói lở khoét sâu", "xói lở khoét hàm ếch", "xói lở khoét chân bờ", "xói lở chân bờ", "xói chân bờ", "xói chân kè", "xói chân đê",
        "sạt lở do xói lở", "sạt lở bờ do xói", "lở bờ sông", "lở bờ biển", "lở bờ", "lở đất ven sông", "lở đất ven biển", "lở bãi bồi", "lở bờ kênh", "lở bờ rạch",
        "bờ sông bị khoét", "bờ sông bị xói", "bờ sông bị sụt", "bờ biển bị khoét", "bờ biển bị xói", "bờ biển bị sụt", "sụp mép sông", "sụp mép biển", "sụp bờ", "sập bờ",
        "nứt bờ sông", "nứt bờ biển", "nứt taluy bờ sông", "nứt taluy bờ biển", "nứt dọc bờ", "nứt nẻ bờ sông", "nứt nẻ bờ biển", "nứt đường ven sông", "nứt đường ven biển", "nứt nền ven sông",
        "xói lở làm đứt đường", "xói lở uy hiếp đường", "xói lở uy hiếp công trình", "xói lở uy hiếp trường học", "xói lở uy hiếp trạm y tế", "xói lở uy hiếp cầu", "xói lở uy hiếp tuyến đê", "xói lở uy hiếp kè", "xói lở cuốn trôi đất", "xói lở cuốn trôi cây",
        "mất đất sản xuất", "mất đất canh tác", "mất đất ven sông", "mất đất ven biển", "mất vườn tược", "mất ruộng do xói lở", "mất nhà do xói lở", "nhà bị sụt xuống sông", "nhà bị kéo xuống sông", "nhà bị cuốn xuống sông",
        "dòng chảy đổi hướng", "dòng chảy xiết", "dòng chảy mạnh", "dòng chảy khoét bờ", "dòng chảy xói bờ", "dòng chảy bẻ cua", "khúc cua sông", "bờ cong sông", "bãi bồi bị xói", "cù lao bị xói",
        "sóng biển đánh xói", "sóng biển khoét bờ", "sóng lớn khoét bờ", "sóng đánh sạt bờ", "sóng đánh làm sụt bờ", "nước chảy siết khoét bờ", "triều cường gây xói lở", "triều cường làm sạt bờ", "nước lên xuống gây xói", "mực nước dao động gây xói",
        "sạt kè", "kè bị sạt", "kè bị xói", "kè bị hư hỏng", "kè bị sập", "sập kè", "hư hỏng kè", "gia cố kè", "kè xung yếu", "điểm xung yếu bờ sông",
        "khu vực sạt lở bờ sông", "điểm sạt lở bờ sông", "điểm sạt lở bờ biển", "điểm xói lở", "điểm xói lở nghiêm trọng", "điểm xói lở nguy hiểm", "xói lở kéo dài", "xói lở tái diễn", "xói lở lan rộng", "xói lở ngày càng nặng",
        "di dời vì xói lở", "sơ tán vì sạt lở bờ", "cấm đường do sạt lở bờ", "phong tỏa do sạt lở bờ", "cắm biển cảnh báo sạt lở", "cắm biển cảnh báo xói lở", "khẩn trương gia cố bờ", "khẩn cấp xử lý xói lở", "khắc phục sạt lở bờ", "kè tạm chống xói",
    ],

    "warning_forecast": [
        "bản tin dự báo", "bản tin cảnh báo", "tin cảnh báo", "cảnh báo thiên tai", "dự báo thời tiết", "dự báo khí tượng", "dự báo khí tượng thủy văn", "KTTV", "trung tâm dự báo", "trung tâm dự báo khí tượng thủy văn",
        "đài khí tượng", "đài KTTV", "bản tin khẩn cấp", "thông báo khẩn", "cảnh báo khẩn cấp", "cảnh báo cực đoan", "tin phát đi", "bản tin cập nhật", "tin cuối cùng", "cập nhật mới nhất",
        "lệnh cấm biển", "cấm biển", "cấm tàu thuyền ra khơi", "tạm dừng ra khơi", "cấm đường", "cấm phương tiện", "đóng cửa biển", "khuyến cáo", "đề phòng", "cảnh giác",
        "thiên tai", "rủi ro thiên tai", "cấp độ rủi ro thiên tai", "cấp độ rủi ro", "cấp độ rủi ro thiên tai cấp", "khuyến cáo người dân", "đề nghị người dân", "khuyến cáo hạn chế ra đường", "theo dõi diễn biến", "theo dõi chặt chẽ",
        "cập nhật diễn biến", "ban chỉ đạo quốc gia về phòng chống thiên tai", "ban chỉ huy phòng chống thiên tai", "phương án ứng phó", "kế hoạch ứng phó", "kịch bản ứng phó", "sẵn sàng phương án", "đường dây nóng", "số điện thoại đường dây nóng",
        "tin dự báo", "tin thời tiết", "tin khí tượng", "bản tin thời tiết", "bản tin khí tượng", "bản tin khí tượng thủy văn", "dự báo KTTV", "bản tin KTTV", "tin KTTV", "thông tin KTTV",
        "trung tâm dự báo quốc gia", "trung tâm khí tượng thủy văn quốc gia", "nchmf", "tổng cục khí tượng thủy văn", "cơ quan khí tượng", "đài khí tượng thủy văn", "đài KTTV khu vực", "đài KTTV tỉnh", "trạm khí tượng", "trạm đo mưa",
        "bản đồ cảnh báo", "bản đồ dự báo", "bản đồ mưa", "bản đồ nguy cơ", "bản đồ rủi ro thiên tai", "bản đồ ngập lụt", "bản đồ sạt lở", "bản đồ lũ quét", "bản đồ gió mạnh", "vùng cảnh báo",
        "khu vực cảnh báo", "phạm vi ảnh hưởng", "khu vực chịu ảnh hưởng", "vùng nguy hiểm", "khu vực nguy hiểm", "cảnh báo khu vực nguy hiểm", "cảnh báo vùng nguy hiểm", "cảnh báo trên biển", "cảnh báo ven biển", "cảnh báo đất liền",
        "cấp độ rủi ro cấp 1", "cấp độ rủi ro cấp 2", "cấp độ rủi ro cấp 3", "cấp độ rủi ro cấp 4", "cấp độ rủi ro cấp 5", "cảnh báo cấp độ rủi ro", "nâng cấp độ rủi ro", "hạ cấp độ rủi ro", "mức rủi ro thiên tai", "cảnh báo rủi ro thiên tai",
        "cảnh báo mưa lớn", "cảnh báo mưa to", "cảnh báo mưa rất to", "cảnh báo dông lốc", "cảnh báo lốc xoáy", "cảnh báo sét", "cảnh báo mưa đá", "cảnh báo gió mạnh", "cảnh báo rét đậm", "cảnh báo nắng nóng",
        "cảnh báo lũ", "cảnh báo lũ trên sông", "cảnh báo ngập", "cảnh báo ngập úng", "cảnh báo triều cường", "cảnh báo nước dâng", "cảnh báo lũ quét", "cảnh báo lũ ống", "cảnh báo sạt lở đất", "cảnh báo trượt lở",
        "khuyến cáo phòng tránh", "khuyến cáo ứng phó", "khuyến cáo sơ tán", "khuyến cáo di dời", "khuyến cáo chằng chống", "khuyến cáo neo đậu", "khuyến cáo dự trữ", "khuyến cáo không ra ngoài", "khuyến cáo hạn chế đi lại", "khuyến cáo bảo đảm an toàn",
        "yêu cầu các địa phương", "chỉ đạo các địa phương", "chỉ đạo khẩn", "chỉ đạo ứng phó", "chỉ đạo phòng chống", "triển khai biện pháp", "triển khai phương án", "kích hoạt phương án", "kích hoạt kịch bản", "thực hiện phương châm 4 tại chỗ",
        "công điện", "công điện khẩn", "công điện hỏa tốc", "văn bản chỉ đạo", "chỉ thị", "thông báo chỉ đạo", "điện khẩn", "lệnh điều hành", "yêu cầu khẩn trương", "đề nghị khẩn trương",
        "ban chỉ huy PCTT", "ban chỉ huy PCTT và TKCN", "ban chỉ đạo PCTT", "ủy ban quốc gia ứng phó", "bộ chỉ huy quân sự", "cơ quan thường trực", "lực lượng xung kích", "tổ ứng trực", "trực ban", "trực 24/24",
        "tạm dừng hoạt động", "tạm ngừng hoạt động", "cấm tụ tập", "cấm qua lại", "phân luồng giao thông", "hạn chế phương tiện", "đóng cửa trường học", "cho học sinh nghỉ học", "tạm dừng học", "đảm bảo an toàn hồ đập",
        "diễn biến phức tạp", "chủ động ứng phó", "theo dõi chặt", "tuyệt đối không chủ quan",
    ],

    "recovery": [
        "khắc phục hậu quả", "khắc phục sự cố", "khắc phục sau thiên tai", "khắc phục sau bão", "khắc phục sau lũ", "khôi phục", "khôi phục giao thông", "khôi phục điện", "khôi phục thông tin liên lạc", "khôi phục sản xuất",
        "sau bão", "sau lũ", "sau lụt", "sau thiên tai", "sau hạn mặn", "sau sạt lở", "sau dông lốc", "chi viện",
        "thống kê thiệt hại", "đánh giá thiệt hại", "tổng hợp thiệt hại", "ước tính thiệt hại", "cứu trợ", "tiếp tế", "hàng cứu trợ", "phát quà cứu trợ", "viện trợ", "hỗ trợ khẩn cấp",
        "hỗ trợ dân sinh", "ủng hộ đồng bào", "ủng hộ người dân vùng lũ", "động viên", "thăm hỏi", "thăm hỏi nạn nhân", "ổn định đời sống", "bố trí nơi ở tạm", "nhà tạm", "tái định cư",
        "di dời tái định cư", "tái thiết", "sửa chữa nhà cửa", "gia cố nhà cửa", "khôi phục nhà cửa", "vệ sinh môi trường", "xử lý môi trường", "khử khuẩn", "phun khử khuẩn", "dọn dẹp",
        "dọn bùn đất", "nước rút", "tiêu độc khử trùng", "cấp nước sạch", "phát nước sạch", "khôi phục cấp nước", "huy động lực lượng", "huy động phương tiện", "điều động lực lượng", "xuất quân",
        "tăng cường lực lượng", "tìm kiếm", "tìm kiếm cứu nạn", "cứu hộ", "cứu nạn", "giải cứu", "trục vớt", "tìm người mất tích", "mắc kẹt", "giải tỏa ách tắc",
        "phân luồng", "thông xe", "thông tuyến", "tình trạng khẩn cấp", "công bố khẩn cấp", "lệnh khẩn cấp", "xuyên đêm", "trắng đêm", "căng mình", "nghỉ học",
        "cho học sinh nghỉ", "dừng học", "tạm dừng đến trường", "di dời", "di dời khẩn cấp", "sơ tán", "sơ tán khẩn cấp", "đưa dân đến nơi an toàn", "dọn cây đổ", "khơi thông cống rãnh",
        "khơi thông dòng chảy", "sửa chữa điện lưới", "khôi phục điện lưới", "khắc phục sự cố điện", "khôi phục thông tin", "khôi phục sóng điện thoại", "khôi phục internet", "cấp phát lương thực", "phát gạo", "phát mì tôm",
        "phát nhu yếu phẩm", "khám chữa bệnh miễn phí", "hỗ trợ y tế", "cấp thuốc", "lập chốt", "lập rào chắn", "cắm biển cảnh báo", "khử trùng nguồn nước", "lọc nước", "cấp nước uống",
        "hỗ trợ giống cây trồng", "hỗ trợ con giống", "khôi phục mùa vụ", "chăm sóc cây trồng", "phục hồi sản xuất",
        "khắc phục khẩn trương", "khẩn trương khắc phục", "khẩn cấp khắc phục", "tập trung khắc phục", "đẩy nhanh khắc phục", "đẩy nhanh tiến độ khắc phục", "khôi phục sớm", "khắc phục tạm thời", "khắc phục triệt để", "khắc phục dứt điểm",
        "cứu đói", "cứu đói khẩn cấp", "cấp phát cứu đói", "hỗ trợ lương thực", "phát lương khô", "phát suất ăn", "bếp ăn dã chiến", "nấu cơm hỗ trợ", "cấp phát nước uống", "phát bánh mì",
        "hỗ trợ tiền mặt", "hỗ trợ bằng tiền", "chi trả hỗ trợ", "cấp phát kinh phí", "tạm ứng kinh phí", "tạm ứng ngân sách", "bổ sung ngân sách", "hỗ trợ khẩn về tài chính", "gói hỗ trợ", "hỗ trợ thiệt hại",
        "thăm nắm tình hình", "kiểm tra hiện trường", "kiểm tra thiệt hại", "xác minh thiệt hại", "rà soát thiệt hại", "lập hồ sơ thiệt hại", "báo cáo nhanh thiệt hại", "báo cáo thiệt hại", "công bố số liệu thiệt hại", "cập nhật thiệt hại",
        "sửa chữa trường học", "khắc phục trường lớp", "khôi phục dạy học", "dọn vệ sinh trường học", "khử khuẩn trường học", "sửa chữa trạm y tế", "khôi phục khám chữa bệnh", "lập điểm khám lưu động", "khám bệnh lưu động", "tiêm phòng sau lũ",
        "phòng chống dịch bệnh", "ngăn dịch sau lũ", "nguy cơ dịch bệnh sau lũ", "xử lý ổ dịch", "giám sát dịch tễ", "phun thuốc khử trùng", "phun hóa chất diệt khuẩn", "diệt muỗi", "diệt lăng quăng", "khử trùng chuồng trại",
        "thu gom rác thải", "dọn rác", "vận chuyển rác thải", "xử lý rác thải", "xử lý bùn thải", "nạo vét bùn", "nạo vét kênh mương", "thông cống thoát nước", "khơi thông miệng cống", "dọn bùn non",
        "xử lý xác động vật", "thu gom xác gia súc", "tiêu hủy xác gia súc", "tiêu hủy gia súc chết", "chôn lấp xác động vật", "rắc vôi bột", "rắc vôi khử trùng", "khử trùng giếng", "súc rửa giếng", "khử nhiễm nguồn nước",
        "khôi phục thủy lợi", "sửa chữa công trình thủy lợi", "khắc phục kênh mương", "gia cố đê điều", "tu bộ đê điều", "sửa chữa đê kè", "khắc phục sạt lở kè", "gia cố taluy", "khắc phục điểm sạt lở", "xử lý điểm xung yếu",
        "lắp đặt cầu tạm", "bắc cầu tạm", "làm đường tạm", "mở đường tạm", "sửa chữa cầu đường", "khắc phục hư hỏng cầu đường", "vá ổ gà", "san gạt mặt đường", "dọn đất đá trên đường", "giải phóng đất đá",
        "khôi phục viễn thông", "khắc phục sự cố viễn thông", "sửa chữa trạm phát sóng", "khôi phục trạm BTS", "khôi phục đường truyền", "sửa cáp quang", "khắc phục đứt cáp", "khôi phục liên lạc", "khôi phục thông tin liên lạc", "phát sóng trở lại",
        "dựng lại nhà", "làm lại nhà", "sửa nhà bị tốc mái", "lợp lại mái nhà", "dựng nhà tạm", "cung cấp vật liệu lợp mái", "cấp tôn lợp mái", "cấp bạt che", "hỗ trợ sửa chữa nhà ở", "hỗ trợ xây dựng nhà",
        "hỗ trợ sinh kế", "tái lập sinh kế", "khôi phục sinh kế", "hỗ trợ vốn sản xuất", "hỗ trợ vay vốn", "khoanh nợ", "giãn nợ", "miễn giảm lãi", "ổn định sản xuất", "khôi phục sản xuất nông nghiệp",
        "khôi phục chăn nuôi", "tái đàn", "hỗ trợ tái đàn", "hỗ trợ thức ăn chăn nuôi", "hỗ trợ phân bón", "hỗ trợ thuốc bảo vệ thực vật", "hỗ trợ giống lúa", "cấp giống cây trồng", "gieo trồng lại", "khôi phục diện tích sản xuất", "hỗ trợ bà con", "chung tay ủng hộ", "tấm lòng vàng",
        "chiến dịch quang trung", "dựng lại nhà", "hỗ trợ vốn", "giảm lãi suất",
    ]
}


# Keywords that are too generic on their own and should be filtered out from fast matching
AMBIGUOUS_KEYWORDS = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}

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
  "lương thực", "nhu yếu phẩm", "dự trữ", "tại chỗ",

  "khẩn trương khắc phục hậu quả", "khẩn trương khắc phục sự cố", "khẩn trương khôi phục hạ tầng", "khẩn trương khôi phục giao thông", "khẩn trương khôi phục điện lưới", "khẩn trương khôi phục liên lạc", "khẩn trương khơi thông dòng chảy", "khẩn trương dọn bùn đất", "khẩn trương vệ sinh môi trường", "khẩn trương ổn định đời sống",
  "tập trung khắc phục hậu quả", "đẩy nhanh khắc phục hậu quả", "khắc phục khẩn cấp", "xử lý khẩn cấp sự cố", "khắc phục tạm thời", "khắc phục triệt để", "khắc phục dứt điểm", "khôi phục từng bước", "khôi phục nhanh", "khôi phục bình thường",
  "chỉ đạo khẩn trương triển khai", "chỉ đạo quyết liệt", "chỉ đạo ứng phó khẩn cấp", "chỉ đạo khắc phục hậu quả", "yêu cầu khẩn trương", "đề nghị khẩn trương", "đôn đốc thực hiện", "tăng cường chỉ đạo", "quán triệt chỉ đạo", "triển khai ngay các biện pháp",
  "công điện chỉ đạo ứng phó", "công điện về ứng phó thiên tai", "công điện về khắc phục hậu quả", "điện khẩn chỉ đạo", "văn bản chỉ đạo khẩn", "chỉ thị ứng phó thiên tai", "thông báo chỉ đạo", "lệnh điều hành khẩn", "ý kiến chỉ đạo", "chỉ đạo từ trung ương",
  "thiết lập sở chỉ huy", "sở chỉ huy tiền phương", "thiết lập chỉ huy tiền phương", "cử đoàn công tác", "đoàn công tác xuống hiện trường", "tổ công tác đặc biệt", "đoàn kiểm tra hiện trường", "kiểm tra đôn đốc", "thị sát hiện trường", "nắm tình hình tại cơ sở",
  "họp khẩn", "họp trực tuyến khẩn", "họp giao ban khẩn", "chỉ đạo tại cuộc họp", "báo cáo nhanh tình hình", "báo cáo khẩn tình hình", "cập nhật tình hình thiệt hại", "tổng hợp nhanh thiệt hại", "phân công nhiệm vụ", "phân cấp xử lý",
  "kích hoạt phương án ứng phó", "kích hoạt kịch bản ứng phó", "kích hoạt cấp độ ứng phó", "triển khai phương án ứng phó", "triển khai kế hoạch ứng phó", "chuẩn bị phương án sơ tán", "tổ chức sơ tán dân", "di dời dân khỏi vùng nguy hiểm", "đưa dân đến nơi an toàn", "bố trí nơi tránh trú",
  "huy động tối đa lực lượng", "huy động toàn bộ lực lượng", "điều động lực lượng khẩn", "bố trí lực lượng ứng trực", "tăng cường lực lượng tại chỗ", "lực lượng xung kích tại chỗ", "tổ phản ứng nhanh", "lực lượng phản ứng nhanh", "ra quân khắc phục", "phối hợp liên ngành",
  "tổ chức cứu hộ cứu nạn", "tăng cường cứu hộ", "cứu nạn khẩn cấp", "tìm kiếm người mất tích", "mở rộng phạm vi tìm kiếm", "duy trì tìm kiếm", "lập điểm tiếp nhận cứu trợ", "thiết lập điểm sơ tán", "bố trí nơi ở tạm", "hỗ trợ khẩn về y tế",
  "đảm bảo an toàn tính mạng", "ưu tiên bảo vệ tính mạng", "hạn chế thấp nhất thiệt hại", "giảm thiểu thiệt hại", "không để bị động bất ngờ", "tuyệt đối không chủ quan", "không lơ là mất cảnh giác", "chủ động phương án", "sẵn sàng mọi tình huống", "theo dõi sát diễn biến",
  "chuẩn bị vật tư dự phòng", "dự trữ nhu yếu phẩm", "dự trữ lương thực tại chỗ", "bố trí phương tiện cơ giới", "chuẩn bị máy phát điện", "chuẩn bị nước sạch", "chuẩn bị thuốc men", "cấp phát vật dụng thiết yếu", "cấp phát chăn màn", "cấp phát áo phao",
  "bảo đảm thông tin liên lạc", "bảo đảm giao thông thông suốt", "bảo đảm cấp điện an toàn", "bảo đảm cấp nước an toàn", "khắc phục sự cố viễn thông", "sửa chữa trạm phát sóng", "khắc phục đứt cáp", "khôi phục đường truyền", "khắc phục sự cố điện", "khắc phục sự cố cấp nước",
  "thông tuyến trở lại", "thông xe tạm thời", "mở lại tuyến đường", "khơi thông cống rãnh", "khơi thông kênh mương", "nạo vét bùn đất", "dọn cây gãy đổ", "dọn đất đá sạt lở", "lập rào chắn an toàn", "cắm biển cảnh báo nguy hiểm",
  "gia cố công trình xung yếu", "gia cố đê kè xung yếu", "kiểm tra an toàn hồ đập", "kiểm tra đê điều", "vận hành hồ chứa an toàn", "bảo đảm an toàn hồ chứa", "xử lý điểm xung yếu", "khắc phục điểm sạt lở", "khắc phục điểm ngập", "khắc phục điểm chia cắt",
  "tạm dừng hoạt động nguy hiểm", "đóng cửa khu vực nguy hiểm", "thiết lập vùng cấm", "phong tỏa khu vực nguy hiểm", "cấm qua lại khu vực nguy hiểm", "phân luồng giao thông", "hạn chế người dân ra đường", "tạm dừng đến trường", "đảm bảo an toàn trường học", "khôi phục hoạt động trường học",
  "hỗ trợ người dân bị ảnh hưởng", "hỗ trợ hộ bị thiệt hại", "hỗ trợ sửa chữa nhà ở", "hỗ trợ lợp lại mái nhà", "hỗ trợ khôi phục sản xuất", "hỗ trợ giống cây trồng", "hỗ trợ con giống", "hỗ trợ thức ăn chăn nuôi", "hỗ trợ tiền mặt", "tạm ứng kinh phí hỗ trợ",
  "cấp phát gạo cứu trợ", "cấp phát mì ăn liền", "cấp phát nước uống", "bếp ăn dã chiến", "cung cấp suất ăn", "tiếp tế đến khu vực cô lập", "mở điểm cứu trợ", "tiếp nhận ủng hộ", "phân phối cứu trợ", "đảm bảo an sinh xã hội",
  "vệ sinh tiêu độc khử trùng", "phun hóa chất khử khuẩn", "khử trùng nguồn nước", "súc rửa giếng nước", "thu gom rác thải", "xử lý rác thải", "thu gom xác động vật", "tiêu hủy xác gia súc", "phòng chống dịch bệnh sau thiên tai", "giám sát dịch tễ sau lũ",
  "tổng lực khắc phục", "căng mình khắc phục", "xuyên đêm khắc phục", "trắng đêm khắc phục", "khẩn trương hoàn thành", "hoàn thành khắc phục", "sớm khôi phục ổn định", "ổn định tình hình", "sớm ổn định sản xuất", "khôi phục sinh kế",
  "phương châm 4 tại chỗ", "lực lượng tại chỗ", "phương tiện tại chỗ", "hậu cần tại chỗ", "chỉ huy tại chỗ", "chủ động phòng tránh", "tăng cường phòng chống", "tăng cường kiểm tra", "tăng cường tuần tra", "tổ chức canh gác",
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
    "Hầm Hải Vân", "Hầm Đèo Cả", "Đê biển Tây", "Đê biển Gò Công",
    "Hồ chứa", "Hồ thủy lợi", "Hệ thống đê", "Hệ thống đê điều", "Đê sông", "Đê biển", "Trạm bơm",
    "Vùng rốn lũ", "Cửa sông", "Cửa biển", "Vịnh Bắc Bộ", "Vịnh Thái Lan", "Sông Cầu"
]

INTERNATIONAL_LOCATIONS = [
    # Asia
    "Afghanistan", "Armenia", "Azerbaijan", "Bahrain", "Bangladesh", "Bhutan", "Brunei", "Campuchia", "Trung Quốc", "Síp",
    "Georgia", "Ấn Độ", "Indonesia", "Iran", "Iraq", "Israel", "Nhật Bản", "Jordan", "Kazakhstan", "Kuwait", "Kyrgyzstan",
    "Lào", "Lebanon", "Malaysia", "Maldives", "Mông Cổ", "Myanmar", "Nepal", "Bắc Triều Tiên", "Oman", "Pakistan",
    "Palestine", "Philippines", "Qatar", "Nga", "Ả Rập Xê Út", "Singapore", "Hàn Quốc", "Sri Lanka", "Syria", "Đài Loan",
    "Tajikistan", "Thái Lan", "Đông Timor", "Thổ Nhĩ Kỳ", "Turkmenistan", "UAE", "Các Tiểu vương quốc Ả Rập Thống nhất",
    "Uzbekistan", "Việt Nam", "Yemen", "Nam Hàn", "Bắc Hàn", "Triều Tiên",

    # Europe
    "Albania", "Andorra", "Belarus", "Bỉ", "Bosnia và Herzegovina", "Bulgaria", "Croatia", "Séc", "Đan Mạch", "Estonia",
    "Phần Lan", "Hy Lạp", "Hungary", "Iceland", "Ireland", "Italia", "Latvia", "Liechtenstein", "Lithuania",
    "Luxembourg", "Malta", "Moldova", "Monaco", "Montenegro", "Hà Lan", "Bắc Macedonia", "Na Uy", "Ba Lan", "Bồ Đào Nha",
    "Romania", "San Marino", "Serbia", "Slovakia", "Slovenia", "Tây Ban Nha", "Thụy Điển", "Thụy Sĩ", "Ukraina", "Ukrainia",
    "Vương quốc Anh", "Vatican", "Châu Âu",

    # Key short names removed to prevent False Positives (handled via Case-Sensitive list if needed, or rely on long form)
    # Removed: "Anh" (conflicts 'anh em'), "Ý" (conflicts 'ý kiến'), "Áo" (conflicts 'quần áo'), "Pháp" ('biện pháp'), "Đức" ('đạo đức'), "Mỹ" ('mỹ thuật')
    "Hoa Kỳ", "Canada", "Mexico", "Mỹ", # 'Mỹ' kept but consider moving to case-sensitive if too noisy. Let's keep for now but monitor.
    # Wait, "Mỹ" is extremely risky with ignorecase matching "thẩm mỹ", "mỹ quan". 
    # Better to rely on "Hoa Kỳ" or "Nước Mỹ".
    # Added "Nước Mỹ", "Nước Anh", "Nước Pháp", "Nước Đức", "Nước Ý", "Nước Áo"
    "Nước Mỹ", "Nước Anh", "Nước Pháp", "Nước Đức", "Nước Ý", "Nước Áo",

    # Americas
    "Antigua và Barbuda", "Argentina", "Bahamas", "Barbados", "Belize", "Bolivia", "Brazil", "Chile", "Colombia",
    "Costa Rica", "Cuba", "Dominica", "Cộng hòa Dominica", "Ecuador", "El Salvador", "Grenada", "Guatemala", "Guyana",
    "Haiti", "Honduras", "Jamaica", "Panama", "Paraguay", "Peru", "Saint Kitts và Nevis", "Saint Lucia",
    "Saint Vincent và Grenadines", "Suriname", "Trinidad và Tobago", "Uruguay", "Venezuela",

    # Africa
    "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroon", "Cộng hòa Trung Phi",
    "Chad", "Comoros", "Cộng hòa Dân chủ Congo", "Cộng hòa Congo", "Bờ Biển Ngà", "Djibouti", "Ai Cập", "Guinea Xích đạo",
    "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Lesotho",
    "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Maroc", "Mozambique", "Namibia",
    "Niger", "Nigeria", "Rwanda", "São Tomé và Príncipe", "Senegal", "Seychelles", "Sierra Leone", "Somalia", "Nam Phi",
    "Nam Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia", "Zimbabwe",

    # Oceania
    "Úc", "Australia", "Fiji", "Kiribati", "Quần đảo Marshall", "Liên bang Micronesia", "Nauru", "New Zealand", "Palau",
    "Papua New Guinea", "Samoa", "Quần đảo Solomon", "Tonga", "Tuvalu", "Vanuatu"
]

# Countries that impact Vietnam (Upstream rivers, weather formation) -> Lower penalty
NEIGHBOR_COUNTRIES = {
    "Trung Quốc", "Lào", "Campuchia", "Cambodia", "China", "Laos", "Thái Lan", "Thailand", "Philippines"
}

# Remove duplicates and risky short words imply
# Remove duplicates and risky short words imply
RISKY_SHORT_LOCATIONS = {"Mỹ", "Anh", "Pháp", "Đức", "Ý", "Áo", "Síp", "Séc"} # Handled separately or removed
INTERNATIONAL_LOCATIONS = sorted(list(set([loc for loc in INTERNATIONAL_LOCATIONS if loc not in RISKY_SHORT_LOCATIONS])))

# Pre-compile for Case-Insensitive (General)
def _build_mega_loc_re(locations: List[str]):
    # Sort by length desc to match longest first
    locations.sort(key=len, reverse=True)
    escaped_list = [re.escape(loc).replace(r'\ ', r'\s+') for loc in locations]
    pattern = rf"\b({'|'.join(escaped_list)})(?!\w)"
    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)

# Pre-compile for Case-Sensitive (Risky short words)
# We match these ONLY if they are Capitalized (e.g. "Mỹ" matches, "mỹ" does not)
# Note: Python's re doesn't support partial case-sensitivity easily in one regex without flags.
# So we make a separate regex for them.
RISKY_LOCATIONS_CASE_SENSITIVE = ["Mỹ", "Anh", "Pháp", "Đức", "Ý", "Áo", "Síp", "Séc", "US", "UK"]

def _build_mega_loc_re_sensitive(locations: List[str]):
    locations.sort(key=len, reverse=True)
    escaped_list = [re.escape(loc).replace(r'\ ', r'\s+') for loc in locations]
    # No IGNORECASE flag here
    pattern = rf"\b({'|'.join(escaped_list)})(?!\w)"
    return re.compile(pattern, re.VERBOSE) # Case sensitive by default

SENSITIVE_LOCATIONS_RE = _build_mega_loc_re(SENSITIVE_LOCATIONS)
INTERNATIONAL_LOCATIONS_RE = _build_mega_loc_re(INTERNATIONAL_LOCATIONS)
INTERNATIONAL_LOCATIONS_CS_RE = _build_mega_loc_re_sensitive(RISKY_LOCATIONS_CASE_SENSITIVE)

# VIP Terms (Critical warnings/actions that bypass all filters)
VIP_TERMS = [
    # Storm / ATNĐ official bulletins
    r"(?:tin\s*)?bão\s*(?:khẩn\s*cấp|số\s*\d+)",
    r"tin\s*(?:khẩn|cảnh\s*báo)\s*(?:bão|áp\s*thấp\s*nhiệt\s*đới|lũ|mưa\s*lớn|gió\s*mạnh|rét\s*đậm\s*rét\s*hại|nắng\s*nóng|hạn\s*hán)",
    r"bão\s*(?:gần\s*biển\s*đông|đổ\s*bộ)",
    r"áp\s*thấp\s*nhiệt\s*đới\s*khẩn\s*cấp",
    r"\bATNĐ\b", r"\bATND\b",

    # Disaster risk level
    r"cảnh\s*báo\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)\s*\d+",

    # Command / mobilization (Authorized Disaster context)
    r"công\s*điện\s*(?:khẩn|hỏa\s*tốc|của\s*thủ\s*tướng|của\s*phó\s*thủ\s*tướng)\s*về\s*(?:bão|lũ|thiên\s*tai|ứng\s*phó|ngập|sạt\s*lở|khắc\s*phục|tìm\s*kiếm|nắng\s*nóng|rét\s*hại|hạn\s*hán|cháy\s*rừng)",
    r"chỉ\s*thị(?:\s*số\s*\d+\s*\/\s*CT[-–—]?[A-Z0-9]+)?\s*(?:của\s*(?:thủ\s*tướng|phó\s*thủ\s*tướng|bộ\s*trưởng|UBND|ban\s*chỉ\s*đạo))?.{0,120}(?:bão|ATNĐ|áp\s*thấp\s*nhiệt\s*đới|lũ|lũ\s*quét|sạt\s*lở|cháy\s*rừng|thiên\s*tai|PCTT|TKCN|khẩn\s*cấp)",
    r"lệnh\s*(?:sơ\s*tán|di\s*dời)\s*(?:khẩn|khẩn\s*cấp).*(?:bão|lũ|ngập|sạt|thiên\s*tai|vỡ\s*đê|hồ\s*đập|cháy\s*rừng)",
    r"sơ\s*tán\s*khẩn\s*cấp.*(?:bão|lũ|sạt|ngập|lụt|cháy\s*rừng|thiên\s*tai)",
    r"công\s*bố\s*tình\s*huống\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|sạt\s*lở|cháy\s*rừng)",
    r"ban\s*bố\s*tình\s*trạng\s*khẩn\s*cấp.*(?:thiên\s*tai|bão|lũ|sạt\s*lở|cháy\s*rừng|hạn\s*mặn)",
    r"cấm\s*biển\s*(?:khẩn\s*cấp|ngay)",
    r"kêu\s*gọi\s*tàu\s*thuyền\s*(?:vào\s*bờ|về\s*nơi\s*trú\s*ẩn|không\s*ra\s*khơi).*(?:bão|áp\s*thấp|gió\s*mạnh)",
    r"ban\s*chỉ\s*huy\s*PCTT(?:\s*và\s*TKCN)?\s*(?:yêu\s*cầu|chỉ\s*đạo|ra\s*công\s*điện|triển\s*khai|huy\s*động|sơ\s*tán|cấm\s*biển|ứng\s*phó|khẩn\s*cấp)",
    r"bàn\s*giao\s*nhà.*(?:bão|lũ|thiên\s*tai|hết\s*lũ|sau\s*bão|sau\s*lũ)",
    r"lệnh\s*xây\s*dựng\s*khẩn\s*cấp.*(?:kè|đê|đập|sạt\s*lở|hồ\s*chứa)",
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

    r"công\s*điện\s*số\s*\d+\s*\/\s*CĐ[-–—]TTg\b",
    r"\bCĐ[-–—]TTg\b",
    r"công\s*điện\s*số\s*\d+\s*\/\s*CĐ[-–—](?:PCTT|BNN|BTNMT|BQP|BCA|UBND)\b",
    r"(?:điện\s*khẩn|hỏa\s*tốc|văn\s*bản\s*hỏa\s*tốc).{0,120}(?:bão|ATNĐ|lũ|mưa\s*lớn|ngập|sạt\s*lở|cháy\s*rừng|rét\s*hại|nắng\s*nóng|hạn\s*hán|triều\s*cường|nước\s*dâng)",
    r"(?:thủ\s*tướng|phó\s*thủ\s*tướng).{0,80}(?:yêu\s*cầu|chỉ\s*đạo).{0,120}(?:ứng\s*phó|khắc\s*phục|khẩn\s*trương).{0,120}(?:bão|lũ|sạt\s*lở|cháy\s*rừng|thiên\s*tai|mưa\s*lớn)",

    r"(?:tuyên\s*bố|công\s*bố|ban\s*bố).{0,40}(?:tình\s*trạng|tình\s*huống)\s*khẩn\s*cấp.{0,80}(?:thiên\s*tai|bão|lũ|sạt\s*lở|cháy\s*rừng|động\s*đất|sóng\s*thần|hạn\s*mặn)",
    r"(?:thiên\s*tai|thảm\s*họa).{0,40}(?:đặc\s*biệt\s*nghiêm\s*trọng|nghiêm\s*trọng|rất\s*nghiêm\s*trọng)",
    r"thảm\s*họa\s*(?:thiên\s*tai|bão|lũ|động\s*đất|sóng\s*thần|cháy\s*rừng)",

    r"(?:lệnh|yêu\s*cầu|chỉ\s*đạo).{0,40}(?:sơ\s*tán|di\s*tản|di\s*dời).{0,40}(?:khẩn|khẩn\s*cấp|ngay).{0,120}(?:bão|lũ|ngập|sạt\s*lở|lũ\s*quét|cháy\s*rừng|nước\s*dâng|triều\s*cường)",
    r"(?:sơ\s*tán|di\s*tản|di\s*dời).{0,40}(?:hàng\s*nghìn|hàng\s*trăm|\d+)\s*(?:người|hộ\s*dân).{0,120}(?:do|vì).{0,40}(?:bão|lũ|ngập|sạt\s*lở|cháy\s*rừng|lũ\s*quét)",
    r"đưa\s*người\s*dân\s*đến\s*(?:nơi\s*an\s*toàn|khu\s*tránh\s*trú|điểm\s*sơ\s*tán).{0,120}(?:bão|lũ|sạt\s*lở|cháy\s*rừng)",

    r"(?:xả|mở)\s*lũ\s*khẩn\s*cấp",
    r"mở\s*(?:\d+)\s*cửa\s*xả\s*(?:lũ)?(?:\s*khẩn\s*cấp)?",
    r"xả\s*(?:\d+(?:[.,]\d+)?)\s*(?:m3\/s|m³\/s)\b",  
    r"vận\s*hành\s*(?:liên\s*hồ|hồ\s*chứa|hồ\s*thủy\s*điện).{0,80}(?:xả\s*lũ|cắt\s*lũ|khẩn\s*cấp)",
    r"(?:nguy\s*cơ|đe\s*dọa)\s*(?:vỡ|mất\s*an\s*toàn)\s*(?:đập|hồ\s*đập|hồ\s*chứa|đê|kè)",
    r"(?:mạch\s*đùn|mạch\s*sủi|thẩm\s*lậu|rò\s*rỉ\s*thân\s*đê).{0,80}(?:đê|đập|hồ\s*đập)",

    r"tìm\s*kiếm\s*cứu\s*nạn|cứu\s*hộ\s*cứu\s*nạn|cứu\s*nạn\s*cứu\s*hộ",
    r"\bTKCN\b|\bPCTT\b|\bCNCH\b",
    r"huy\s*động.{0,40}(?:quân\s*đội|bộ\s*đội|công\s*an|cảnh\s*sát|dân\s*quân).{0,120}(?:cứu\s*hộ|cứu\s*nạn|ứng\s*phó).{0,120}(?:bão|lũ|ngập|sạt\s*lở|cháy\s*rừng|lũ\s*quét)",
    r"khẩn\s*trương\s*(?:cứu\s*hộ|cứu\s*nạn|giải\s*cứu).{0,120}(?:bão|lũ|ngập|sạt\s*lở|lũ\s*quét|cháy\s*rừng)",

    r"(?:\d+|nhiều)\s*(?:người|nạn\s*nhân)\s*(?:tử\s*vong|thiệt\s*mạng|mất\s*tích|bị\s*thương).{0,120}(?:do|vì|trong).{0,40}(?:bão|lũ|ngập|sạt\s*lở|lũ\s*quét|lốc|sét|cháy\s*rừng|động\s*đất|sóng\s*thần)",
    r"(?:vùi\s*lấp|cuốn\s*trôi).{0,80}(?:người|nhà|xe).{0,120}(?:bão|lũ|sạt\s*lở|lũ\s*quét)",

]
VIP_TERMS_RE = re.compile("|".join(rf"(?:{p})" for p in VIP_TERMS), re.IGNORECASE | re.VERBOSE)

# Strict Priority Order for tie-breaking
DISASTER_PRIORITY_ORDER = { 
    cat: i for i, cat in enumerate([
        "tsunami", "earthquake", "storm", "flash_flood", "landslide", 
        "flood", "subsidence", "storm_surge", "wildfire", "salinity",
        "drought", "heatwave", "cold_surge", "extreme_weather", "erosion",
        "warning_forecast", "recovery"
    ]) 
}

DISASTER_PRIORITY_MAP = {
    "storm": 1, "tsunami": 1, "earthquake": 1, "storm_surge": 1,
    "flash_flood": 2, "landslide": 2, "flood": 2, "wildfire": 2,
    "extreme_weather": 3, "heatwave": 3, "cold_surge": 3, "drought": 3, "salinity": 3, "subsidence": 3, "erosion": 3,
    "warning_forecast": 4, "recovery": 5,
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

NUMBER_WORDS = {
    "không": 0, "một": 1, "mốt": 1, "1": 1, "hai": 2, "2": 2, "ba": 3, "3": 3,
    "bốn": 4, "tư": 4, "4": 4, "năm": 5, "5": 5, "sáu": 6, "6": 6, "bảy": 7, "7": 7,
    "tám": 8, "8": 8, "chín": 9, "9": 9, "mười": 10, "10": 10,
    "vài": 3, "chục": 10, "mấy chục": 30, "hàng chục": 20, "trăm": 100, "vài trăm": 300, "một trăm": 100, "hai trăm": 200, "ba trăm": 300,
    "năm trăm": 500, "nghìn": 1000, "ngàn": 1000, "một nghìn": 1000, "vạn": 10000, "hàng vạn": 20000,
    "triệu": 1000000, "tỷ": 1000000000, "tỉ": 1000000000
}

# STAGE & RISK PATTERNS
RE_WARNING_TITLE = re.compile(r"bản\s*tin(?:\s*dự\s*báo|\s*cảnh\s*báo)|dự\s*thời\s*tiết|tin\s*dự\s*báo|đón\s*thiên\s*tai", re.IGNORECASE)
RE_RECOVERY_TITLE = re.compile(r"khắc\s*phục\s*hậu\s*quả|sau\s*thiên\s*tai|tái\s*thiết|dựng\s*lại\s*nhà|xây\s*mới\s*nhà|hỗ\s*trợ\s*khẩn\s*cấp", re.IGNORECASE)
RISK_LEVEL_RE = re.compile(r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai\s*(?:cấp|mức)?\s*([1-5|I-V|V])", re.IGNORECASE)

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

HAZARD_ANCHOR = r"(?:bão|ATNĐ|áp\s*thấp|lũ|lũ\s*quét|lũ\s*ống|lũ\s*bùn|ngập|sạt\s*lở|đất\s*đá\s*trôi|nắng\s*nóng|hạn\s*hán|xâm\s*nhập\s*mặn|gió\s*mạnh|gió\s*giật|dông\s*lốc|lốc\s*xoáy|vòi\s*rồng|sét|mưa\s*đá|rét\s*hại|băng\s*giá|sương\s*muối|sương\s*mù|cháy\s*rừng|động\s*đất|sóng\s*thần|triều\s*cường|nước\s*dâng|mưa\s*lớn|mưa\s*lũ|vỡ\s*đê|vỡ\s*đập|tràn\s*đê|xả\s*lũ|chìm\s*tàu|tàu\s*cá\s*gặp\s*nạn|thuyền\s*viên\s*mất\s*tích|sự\s*cố\s*thiên\s*tai)"
PCTT_ANCHOR   = r"(?:phòng\s*chống\s*thiên\s*tai|PCTT|TKCN|tìm\s*kiếm\s*cứu\s*nạn|CNCH|cứu\s*hộ|cứu\s*nạn|Ban\s*Chỉ\s*huy|lực\s*lượng\s*xung\s*kích|bộ\s*đội\s*biên\s*phòng|chiến\s*sĩ|dân\s*quân|công\s*an|quân\s*đội)"
RECOVERY_ANCHOR = r"(?:hậu\s*quả|sau\s*(?:thiên\s*tai|bão|lũ|ngập|sạt|mưa|dông|lốc|nắng|hạn|mặn|rét|cháy|nước\s*dâng|triều\s*cường|động\s*đất|sóng\s*thần|sự\s*cố))"
DISASTER_CONTEXT = [
  # A) Cảnh báo & Rủi ro
  r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai(?:\s*cấp\s*\d+)?",
  r"cảnh\s*báo\s*(?:thiên\s*tai|rủi\s*ro\s*thiên\s*tai|nguy\s*cơ\s*thiên\s*tai)",
  r"(?:dự\s*báo|cảnh\s*báo)\s*(?:mưa\s*lớn|lũ|bão|ATNĐ|nắng\s*nóng|rét\s*hại|sương\s*muối)",
  rf"tình\s*huống\s*khẩn\s*cấp.*(?:{HAZARD_ANCHOR})",
  
  # B) Ứng phó khẩn cấp / Hành động
  rf"(?:sơ\s*tán|di\s*dời|di\s*tản)(?:\s*khẩn\s*cấp)?.*(?:{HAZARD_ANCHOR}|vùng\s*nguy\s*hiểm|người\s*dân)",
  rf"(?:cứu\s*hộ|cứu\s*nạn|giải\s*cứu).*(?:{HAZARD_ANCHOR}|người\s*dân|nạn\s*nhân|tàu\s*thuyền)",
  rf"tìm\s*kiếm\s*cứu\s*nạn.*(?:trên\s*biển|vùng\s*lũ|sạt\s*lở|{HAZARD_ANCHOR})",
  r"neo\s*đậu\s*tránh\s*trú.*(?:bão|áp\s*thấp|gió\s*mạnh)",
  rf"(?:cấm\s*ra\s*khơi|cấm\s*biển|lệnh\s*cấm\s*biển)(?:[^.\n]{{0,120}})(?:bão|áp\s*thấp|gió\s*mạnh|biển\s*động|{HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:đóng\s*đường|cấm\s*đường|cấm\s*lưu\s*thông|phân\s*luồng|chốt\s*chặn)(?:[^.\n]{{0,80}})(?:do|vì|bởi).*(?:{HAZARD_ANCHOR}|ngập|sạt\s*lở)",
  rf"phong\s*tỏa\s*khu\s*vực\s*nguy\s*hiểm.*(?:{HAZARD_ANCHOR})",
  rf"(?:huy\s*động|bố\s*trí|tăng\s*cường).*(?:lực\s*lượng|phương\s*tiện).*(?:{PCTT_ANCHOR}|ứng\s*phó|khắc\s*phục|{HAZARD_ANCHOR})",
  rf"lực\s*lượng\s*xung\s*kích.*{PCTT_ANCHOR}|trực\s*ban.*{PCTT_ANCHOR}",
  
  # C) Tác động / Thiệt hại
  rf"(?:thiệt\s*hại|tổn\s*thất)(?:[^.\n]{{0,120}})(?:do|vì|bởi)(?:[^.\n]{{0,120}})(?:thiên\s*tai|{HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:thương\s*vong|tử\s*vong|thiệt\s*mạng|chết|bị\s*thương)(?:[^.\n]{{0,160}})(?:do|vì|bởi)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:mất\s*tích|mất\s*liên\s*lạc)(?:[^.\n]{{0,80}})(?:do|trong|sau)\s*(?:{HAZARD_ANCHOR})",
  rf"(?:bị\s*thương|nhập\s*viện|cấp\s*cứu)(?:[^.\n]{{0,80}})(?:do|trong|sau)\s*(?:{HAZARD_ANCHOR}|sập\s*nhà|cây\s*đổ)",
  rf"(?:chia\s*cắt|cô\s*lập)(?:[^.\n]{{0,80}})(?:do|bởi)\s*(?:{HAZARD_ANCHOR}|ngập|lũ)",
  rf"(?:sập\s*cầu|đứt\s*đường|sạt\s*lở\s*đường|sụt\s*lún)(?:[^.\n]{{0,80}})(?:do|vì|bởi)\s*(?:{HAZARD_ANCHOR})",
  r"vỡ\s*đê|tràn\s*đê|vỡ\s*đập|sạt\s*lở\s*đê",
  rf"(?:cuốn\s*trôi|vùi\s*lấp)(?:[^.\n]{{0,80}})(?:do|bởi)\s*(?:{HAZARD_ANCHOR}|đất|nước|lũ)",
  r"hư\s*hỏng\s*nặng|tốc\s*mái\s*hoàn\s*toàn|sạt\s*lở\s*nghiêm\s*trọng|gãy\s*đổ\s*cây\s*xanh",
  r"thiệt\s*hại\s*về\s*người|thiệt\s*hại\s*tài\s*sản.*do\s*thiên\s*tai",
  rf"ước\s*tính\s*thiệt\s*hại.*do\s*(?:{HAZARD_ANCHOR})",
  
  # D) Hàng hải / Tàu thuyền
  rf"(?:tàu|ghe|thuyền|ngư\s*dân)\s*(?:gặp\s*nạn|mất\s*tích|chìm|vớt|lai\s*dắt|mắc\s*cạn|trôi\s*dạt).*(?:{HAZARD_ANCHOR}|trên\s*biển)",
  r"tín\s*hiệu\s*cầu\s*cứu|bị\s*sóng\s*đánh\s*chìm|sóng\s*lớn\s*đánh\s*chìm",
  rf"gia\s*cố\s*nhà\s*cửa|chằng\s*chống|cắt\s*tỉa\s*cây.*phòng\s*(?:{HAZARD_ANCHOR})",
  r"gia\s*cố\s*lồng\s*bè|đưa\s*tàu\s*thuyền\s*vào\s*bờ|kêu\s*gọi\s*tàu\s*thuyền",
  r"lệnh\s*cấm\s*biển",
  
  # E) Hạ tầng điện/nước/viễn thông
  rf"(?:mất\s*điện|ngừng\s*cấp\s*điện|sự\s*cố\s*lưới\s*điện)(?:[^.\n]{{0,120}})(?:do|vì|bởi).*(?:{HAZARD_ANCHOR})",
  rf"(?:ngừng\s*cấp\s*nước|gián\s*đoạn\s*cấp\s*nước)(?:[^.\n]{{0,120}})(?:do|vì|bởi).*(?:{HAZARD_ANCHOR}|thiên\s*tai)",
  rf"(?:mất\s*sóng|mất\s*liên\s*lạc|gián\s*đoạn\s*thông\s*tin)(?:[^.\n]{{0,120}})(?:do|vì|bởi).*(?:{HAZARD_ANCHOR})",

  # F) Chỉ báo thủy văn
  r"báo\s*động\s*(?:1|2|3|I|II|III)\b|vượt\s*báo\s*động",
  r"mực\s*nước\s*(?:sông|hồ)|đỉnh\s*lũ|lũ\s*lên|lũ\s*rút",
  r"lượng\s*mưa|tổng\s*lượng\s*mưa|mưa\s*lớn\s*diện\s*rộng",
  r"triều\s*cường\s*dâng\s*cao|đỉnh\s*triều|ngập\s*do\s*triều",
  r"cấp\s*gió|gió\s*giật|gió\s*mạnh\s*cấp|biển\s*động",
  r"độ\s*mặn|ranh\s*mặn|xâm\s*nhập\s*mặn",

  # G) Phục hồi & Khắc phục
  rf"khắc\s*phục\s*hậu\s*quả(?:[^.\n]{{0,120}})(?:sau\s*)?(?:{HAZARD_ANCHOR}|thiên\s*tai|sự\s*cố)",
  rf"(?:khôi\s*phục|sửa\s*chữa)(?:[^.\n]{{0,120}})(?:giao\s*thông|điện|nước|nhà\s*cửa|công\s*trình)(?:[^.\n]{{0,120}})(?:sau\s*)?(?:{HAZARD_ANCHOR})",
  rf"(?:thông\s*tuyến|khơi\s*thông|giải\s*tỏa|dọn\s*dẹp)(?:[^.\n]{{0,120}})(?:đất\s*đá|cây\s*đổ|sạt\s*lở)(?:[^.\n]{{0,120}})(?:sau\s*)?(?:{HAZARD_ANCHOR})",
  rf"(?:cứu\s*trợ|hỗ\s*trợ|tiếp\s*tế|phân\s*phát)(?:[^.\n]{{0,120}})(?:lương\s*thực|nhu\s*yếu\s*phẩm|tiền|gạo)(?:[^.\n]{{0,120}})(?:vùng\s*lũ|vùng\s*thiên\s*tai|người\s*dân\s*vùng\s*lũ|{HAZARD_ANCHOR})",
  rf"(?:tái\s*thiết|ổn\s*định\s*đời\s*sống)(?:[^.\n]{{0,120}})(?:sau\s*)?(?:{HAZARD_ANCHOR}|thiên\s*tai)",
  rf"(?:vệ\s*sinh\s*môi\s*trường|phun\s*khử\s*khuẩn|xử\s*lý\s*nguồn\s*nước)(?:[^.\n]{{0,120}})(?:sau\s*lũ|ngập\s*lụt|{HAZARD_ANCHOR})",

  # H) Chỉ đạo & Điều hành
  rf"(?:công\s*điện|hỏa\s*tốc|chỉ\s*thị)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:chỉ\s*đạo|yêu\s*cầu|đề\s*nghị|triển\s*khai)(?:[^.\n]{{0,120}})(?:ứng\s*phó|khắc\s*phục|phòng\s*chống)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:ban\s*chỉ\s*huy|ban\s*chỉ\s*đạo)(?:[^.\n]{{0,120}})({HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:kích\s*hoạt|vận\s*hành)(?:[^.\n]{{0,120}})(?:phương\s*án|kịch\s*bản)(?:[^.\n]{{0,120}})(?:ứng\s*phó|{HAZARD_ANCHOR})",
  rf"(?:thành\s*lập|thiết\s*lập)(?:[^.\n]{{0,80}})(?:sở\s*chỉ\s*huy|đoàn\s*công\s*tác)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|{PCTT_ANCHOR})",
  rf"(?:phương\s*châm)\s*4\s*tại\s*chỗ",
  rf"(?:trực\s*ban|trực\s*chiến)(?:[^.\n]{{0,40}})24\/24(?:[^.\n]{{0,120}})(?:PCTT|{HAZARD_ANCHOR})",
  rf"(?:kiểm\s*tra|rà\s*soát)(?:[^.\n]{{0,120}})(?:an\s*toàn|xung\s*yếu|hồ\s*đập|đê\s*điều)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|mùa\s*mưa\s*bão)",
]

# PRE-COMPILED STAGE DETECTORS
FORECAST_SIGS = DISASTER_GROUPS["warning_forecast"]
RECOVERY_KEYWORDS = DISASTER_GROUPS["recovery"]
INCIDENT_SIGS = [item for k, v in DISASTER_GROUPS.items() if k not in ("warning_forecast", "recovery") for item in v]

# Join patterns into a single mega-regex for performance
RE_FORECAST = re.compile("|".join(rf"(?:{p})" for p in FORECAST_SIGS), re.IGNORECASE)
RE_INCIDENT = re.compile("|".join(rf"(?:{p})" for p in INCIDENT_SIGS), re.IGNORECASE)
RE_RECOVERY = re.compile("|".join(rf"(?:{p})" for p in RECOVERY_KEYWORDS), re.IGNORECASE)

# Tiered Priority System (Restructured)
# Tier 1: Catastrophic / Severe Events (Very High Priority)
TIER1_CATASTROPHIC = [
    r"vỡ\s*(?:đập|đê|kè|hồ\s*chứa)\b",
    r"tràn\s*đê\b",
    r"(?:nguy\s*cơ\s*)?vỡ\s*(?:đập|đê|hồ\s*chứa)\b",
    r"lũ\s*quét\b",
    r"lũ\s*ống\b",
    r"lũ\s*lịch\s*sử\b",
    r"sóng\s*thần\b|tsunami\b",
    r"động\s*đất\s*(?:mạnh|trên\s*\d+(?:[.,]\d+)?)\b|rung\s*chấn\s*mạnh\b",
    r"sạt\s*lở\s*(?:đất|núi).*(?:vùi\s*lấp|chôn\s*vùi)\b",
    r"siêu\s*bão\b",
    r"bão\s*số\s*\d+\b",
    r"vượt\s*báo\s*động\s*(?:1|2|3|I|II|III)\b|trên\s*báo\s*động\b",
    r"xả\s*lũ\s*khẩn\s*cấp\b|mở\s*cửa\s*xả\s*lũ\b|xả\s*tràn\b",
    r"sạt\s*lở\s*(?:đặc\s*biệt|rất)\s*nghiêm\s*trọng\b",
    r"triều\s*cường\s*(?:kỷ\s*lục|đạt\s*đỉnh)\b|nước\s*dâng\s*(?:đột\s*biến|bất\s*thường)\b",
    r"cấp\s*dự\s*báo\s*cháy\s*rừng\s*cấp\s*V\b|cháy\s*rừng\s*(?:lớn|lan\s*rộng|nghiêm\s*trọng)\b",
]

# Tier 2: Authority / Emergency Orders
TIER2_AUTHORITY = [
    rf"(?:công\s*điện)\s*(?:khẩn|hỏa\s*tốc|số\s*\d+)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|thiên\s*tai)",
    rf"(?:ban\s*bố|công\s*bố)\s*(?:tình\s*trạng|tình\s*huống)\s*khẩn\s*cấp(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|thiên\s*tai)",
    rf"lệnh\s*(?:sơ\s*tán|di\s*dời)\s*(?:khẩn|khẩn\s*cấp)(?:[^.\n]{{0,160}})(?:{HAZARD_ANCHOR}|thiên\s*tai)",
    rf"sơ\s*tán\s*khẩn\s*cấp(?:[^.\n]{{0,160}})(?:{HAZARD_ANCHOR}|thiên\s*tai)",
    rf"(?:cấm\s*biển|cấm\s*ra\s*khơi|đóng\s*cửa\s*biển)(?:[^.\n]{{0,160}})(?:bão|áp\s*thấp|gió\s*mạnh|biển\s*động|{HAZARD_ANCHOR})",
    rf"(?:kích\s*hoạt|triển\s*khai)(?:[^.\n]{{0,120}})(?:phương\s*án|kịch\s*bản)(?:[^.\n]{{0,120}})(?:ứng\s*phó|PCTT|TKCN|{HAZARD_ANCHOR})",
    r"chiến\s*dịch\s*quang\s*trung",
]

# Tier 3: Casualties / Missing (Hazard-locked)
TIER3_CASUALTIES = [
    rf"(?:\d+|nhiều)\s*người\s*(?:chết|tử\s*vong|thiệt\s*mạng)(?:[^.\n]{{0,120}})(?:do|vì|trong)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR})",
    rf"mất\s*tích(?:[^.\n]{{0,120}})(?:do|trong|sau)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR})",
    rf"tìm\s*thấy\s*thi\s*thể(?:[^.\n]{{0,120}})(?:do|trong|sau)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR})",
    rf"thuyền\s*viên\s*mất\s*tích|tàu\s*cá\s*mất\s*tích|chìm\s*tàu(?:[^.\n]{{0,120}})(?:do|trong)(?:[^.\n]{{0,120}})(?:bão|sóng|gió|biển\s*động|áp\s*thấp)",
]

# Tier 4: Infrastructure Disruption (Hazard-locked)
TIER4_DISRUPTION = [
    rf"bị\s*(?:cô\s*lập|chia\s*cắt)(?:[^.\n]{{0,120}})(?:do|bởi)(?:[^.\n]{{0,120}})(?:lũ|ngập|sạt|{HAZARD_ANCHOR})",
    r"ngập\s*(?:sâu|nặng|lụt)\s*(?:diện\s*rộng|cục\s*bộ|nghiêm\s*trọng)?\b",
    r"(?:chia\s*cắt|cô\s*lập)\s*(?:cục\s*bộ|hoàn\s*toàn)\b",
    rf"(?:sập|đứt|sạt|lở)\s*(?:cầu|đường|quốc\s*lộ|tỉnh\s*lộ|giao\s*thông)(?:[^.\n]{{0,120}})(?:do|vì|bởi)(?:[^.\n]{{0,120}})(?:mưa|lũ|sạt|{HAZARD_ANCHOR})",
    rf"(?:mất|cắt)\s*điện(?:[^.\n]{{0,120}})(?:do|vì|bởi)(?:[^.\n]{{0,120}})(?:{HAZARD_ANCHOR}|mưa|giông|lốc)",
]

# Combinations for NLP usage
HIGH_PRIORITY_KEYWORDS = TIER1_CATASTROPHIC + TIER2_AUTHORITY + TIER3_CASUALTIES
MEDIUM_PRIORITY_KEYWORDS = TIER4_DISRUPTION + [
    r"sạt\s*lở\s*nghiêm\s*trọng", r"lũ\s*lên\s*nhanh", r"nước\s*dâng\s*cao",
    r"tàu\s*cá\s*gặp\s*nạn", r"ngư\s*dân\s*gặp\s*nạn", r"chìm\s*xuồng|lật\s*thuyền",
    r"hố\s*tử\s*thần", r"sụt\s*lún\s*đất", r"xâm\s*thực\s*biển",
    r"khẩn\s*trương\s*khắc\s*phục", r"tập\s*trung\s*ứng\s*phó"
]

HIGH_PRIORITY_RE = re.compile("|".join(rf"(?:{p})" for p in HIGH_PRIORITY_KEYWORDS), re.IGNORECASE | re.VERBOSE)
MEDIUM_PRIORITY_RE = re.compile("|".join(rf"(?:{p})" for p in MEDIUM_PRIORITY_KEYWORDS), re.IGNORECASE | re.VERBOSE)



@dataclass(frozen=True)
class Source:
    name: str
    domain: str
    primary_rss: str | None = None  # Primary RSS URL
    backup_rss: str | None = None   # Backup RSS URL
    note: str | None = None
    trusted: bool | None = False
    authority_level: int = 1         # 1: Normal, 2: Trusted, 3: High Authority (Direct Gov/VTV)
    tier: int = 2  # 1=Critical (15m), 2=Major (45m), 3=Standard (90m)

# VETO LISTS (Centralized from nlp.py)
# Strictly Non-Disaster Contexts (Metaphor, Showbiz, Game, Sport)
ABSOLUTE_VETO = [
    '(?:cách|hướng\\s*dẫn|thủ\\s*thuật|mẹo).*(?:tách|gộp|nén|chuyển|sửa).*(?:file|tệp|pdf|word|excel|ảnh|video)',
    '(?:dự\\s*án\\s*vành\\s*đai|đường\\s*vành\\s*đai|nút\\s*giao|hầm\\s*chui|cầu\\s*vượt|thông\\s*xe|khánh\\s*thành|khởi\\s*công|xây\\s*dựng\\s*tuyến\\s*đường|nâng\\s*cao\\s*độ\\s*nền)(?!.*(?:kè|đê|hồ|đập|chống|sạt\\s*lở|khắc\\s*phục|ngập))',
    '(?:google|facebook|youtube|tiktok|zalo\\s*pay|vneid).*(?:cập\\s*nhật|tính\\s*năng|ra\\s*mắt|lỗi|hướng\\s*dẫn)(?!.*(?:cứu\\s*trợ|ủng\\s*hộ|thiên\\s*tai|bão|lũ|khẩn\\s*cấp))',
    '(?:hội\\s*nghị|hội\\s*thảo|tập\\s*huấn)\\s.*(?:khoa\\s*học|kỹ\\s*thuật|công\\s*nghệ|chuyên\\s*đề)',
    '(?:khám\\s*bệnh|cấp\\s*phát\\s*thuốc|khám\\s*sức\\s*khỏe|tư\\s*vấn\\s*sức\\s*khỏe|bác\\s*sĩ|bệnh\\s*viện|bệnh\\s*xá|trạm\\s*y\\s*tế)(?!\\s*(?:cứu\\s*trợ|vùng\\s*lũ|vùng\\s*bão|thiên\\s*tai|khắc\\s*phục))',
    '(?:lãi\\\\s*suất|tín\\\\s*dụng|tỉ\\\\s*giá|ngoại\\\\s*tệ|ngân\\\\s*hàng|chứng\\\\s*khoán|vốn\\\\s*điều\\\\s*lệ|lợi\\\\s*nhuận|doanh\\\\s*thu|vn-index)(?!\\s*(?:chính\\\\s*sách|hỗ\\\\s*trợ|ư\\\\s*đãi|khôi\\\\s*phục|khắc\\\\s*phục)\\\\s*(?:sau|vùng|cho|người)\\\\s*(?:bão|lũ|thiên\\\\s*tai|ngập|sạt\\\\s*lở))',
    '(?:nghiệm\\s*thu|bàn\\s*giao)\\s*(?:công\\s*trình|đề\\s*tài|dự\\s*án)(?!.*(?:khắc\\s*phục|hậu\\s*quả|sạt\\s*lở|khẩn\\s*cấp|cứu\\s*trợ|tái\\s*định\\s*cư|nhà\\s*đại\\s*đoàn\\s*kết|sau\\s*bão))',
    '(?:sân\\s*bay|hàng\\s*không|hạ\\s*cánh|cất\\s*cánh|phi\\s*công|cơ\\s*trưởng)(?!.*(?:do|vì|bởi|để|ứng\\s*phó)\\s*(?:bão|lũ|thiên\\s*tai|thời\\s*tiết))',
    '(?:sập|tai\\s*nạn)\\s*(?:hầm\\s*lò|mỏ\\s*đá|mỏ\\s*than|công\\s*trường)(?!\\s*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai|mưa|sạt\\s*lở))',
    '(?:xung\\s*đột\\s*vũ\\s*trang|quản\\s*chế\\s*tàu\\s*dầu|phong\\s*tỏa\\s*tàu|tấn\\s*công\\s*bằng\\s*tên\\s*lửa|hội\\s*đồng\\s*bảo\\s*an|phương\\s*tây|chiến\\s*tranh|binh\\s*sĩ|quân\\s*đội|lữ\\s*đoàn)',
    'Vụ tai nạn',
    '\\.docx\\b|\\.pdf\\b|\\.doc\\b|AstroWind|Tailwind\\s*CSS',
    '\\b(?:(?<!nghiêm\\s)trọng\\s*tài|kèo|xem\\s*trực\\s*tiếp|nhận\\s*định)\\b(?!.*?(?:lao\\s*cai|vùng\\s*lũ|khắc\\s*phục|cứu\\s*hộ|hỗ\\s*trợ|thiên\\s*tai))',
    '\\b(?:10|5|event|sự\\s*kiện)\\s*nổi\\s*bật(?:\\s*của\\s*tỉnh|\\s*trong\\s*năm|\\s*địa\\s*phương)\\b',
    '\\b(?:8871\\.net\\.cn|54688\\.cc|56688\\.cc|57688\\.cc|237933801|QQ\\s*860)\\b',
    '\\b(?:Fake\\s*diploma|Degree\\s*Transcript|University\\s*of\\s*.*fake|QQ\\s*\\d+|wechat\\s*id|telegram\\s*id)\\b',
    '\\b(?:Man\\s*Utd|Manchester\\s*United|Premier\\s*League|La\\s*Liga|Bundesliga|Serie\\s*A|Champions\\s*League)\\b',
    '\\b(?:album|mv|ca\\s*khúc|bài\\s*hát|phim\\s*bộ|series|tập\\s*cuối|trailer|spoiler|happening|rap\\s*việt|chị\\s*đẹp|anh\\s*trai|anh\\s*hùng\\s*xạ\\s*điêu|phim\\s*truyền\\s*hình|phim\\s*điện\\s*ảnh)\\b',
    '\\b(?:artemis|apollo|voyager|james\\s*webb|kính\\s*viễn\\s*vọng\\s*hubble|sứ\\s*mệnh\\s*vũ\\s*trụ|đổ\\s*bộ\\s*mặt\\s*trăng|hành\\s*tinh\\s*xa\\s*xôi)\\b',
    '\\b(?:b52\\s*bomber|game\\s*b52|tải\\s*game\\s*b52|b52\\s*club|cổng\\s*game)\\b',
    '\\b(?:b\\s*m\\s*s|i\\s*o\\s*t\\s*tòa\\s*nhà|điều\\s*hòa\\s*trung\\s*tâm\\s*chiller|hệ\\s*thống\\s*v\\s*r\\s*v|quản\\s*lý\\s*năng\\s*lượng|tự\\s*động\\s*hóa\\s*tòa\\s*nhà|nhà\\s*thông\\s*minh)\\b',
    '\\b(?:ban\\s*chỉ\\s*đạo\\s*389|chống\\s*buôn\\s*lậu|hàng\\s*giả|gian\\s*lận\\s*thương\\s*mại|siết\\s*quản\\s*lý|thu\\s*ngân\\s*sách|giải\\s*ngân|đầu\\s*tư\\s*công)\\b',
    '\\b(?:ban\\s*liên\\s*lạc|hội\\s*đồng\\s*ngũ|cựu\\s*giáo\\s*chức|hội\\s*khuyến\\s*học|tri\\s*ân\\s*thầy\\s*cô|kỷ\\s*niệm\\s*ngày\\s*ra\\s*trường|họp\\s*lớp)\\b',
    '\\b(?:ban\\s*lễ\\s*tang|cáo\\s*phó|gia\\s*đình\\s*báo\\s*tin|thành\\s*kính\\s*phân\\s*ưu|vòng\\s*hoa\\s*viếng|di\\s*nguyện)(?!.*(?:cứu\\s*dân|cứu\\s*hộ|hy\\s*sinh\\s*khi\\s*làm\\s*nhiệm\\s*vụ|bão|lũ|ngập|sạt\\s*lở))\\b',
    '\\b(?:ban\\s*quản\\s*trị|phí\\s*bảo\\s*trì|họp\\s*dân\\s*cư|tiện\\s*ích\\s*nội\\s*khu|vận\\s*hành\\s*nhà\\s*máy|hệ\\s*thống\\s*máy\\s*chủ|đường\\s*truyền\\s*internet)\\b',
    '\\b(?:barca|bundesliga|la\\s*liga|man\\s*city|arsenal|odegaard|arda\\s*guler|ole\\s*gunnar|solskjaer|manchester\\s*united|jun\\s*phạm|công\\s*diễn\\s*\\d+|show\\s*ca\\s*nhạc|nhạc\\s*sĩ|cống\\s*hiến|âm\\s*nhạc|crystal\\s*palace|aston\\s*villa|thép\\s*xanh\\s*nam\\s*định|shb\\s*đà\\s*nẵng|haaland|saka|enzo\\s*maresca|ruben\\s*amorim|bóng\\s*đá\\s*malaysia|stranger\\s*things|u23|vck|asian\\s*cup|world\\s*cup|cầu\\s*thủ|huấn\\s*luyện\\s*viên|ai\\s*là\\s*triệu\\s*phú|đại\\s*gia\\s*chân\\s*đất|hết\\s*thời|ly\\s*hôn|hòa\\s*minzy|ca\\s*sĩ)\\b',
    '\\b(?:bhyt|chế\\s*độ\\s*thai\\s*sản)\\b',
    '\\b(?:big\\s*data|machine\\s*learning|trí\\s*tuệ\\s*nhân\\s*tạo|backend|frontend|lập\\s*trình\\s*viên|python|java|javascript|thiết\\s*kế\\s*ui/ux|server|hosting|ên\\s*kết\\s*đào\\s*tạo)\\b',
    '\\b(?:bitcoin|crypto|blockchain|nft|token|ví\\s*điện\\s*tử|sàn\\s*coin|đào\\s*coin|tiền\\s*ảo|máy\\s*đào)\\b',
    '\\b(?:biên\\s*bản\\s*vi\\s*phạm\\s*hành\\s*chính|quyết\\s*định\\s*xử\\s*phạt|hình\\s*thức\\s*tăng\\s*nặng|tình\\s*tiết\\s*giảm\\s*nhẹ|cưỡng\\s*thế\\s*thi\\s*hành|khiếu\\s*nại\\s*tố\\s*cáo|tranh\\s*chấp\\s*hành\\s*chính)\\b',
    '\\b(?:biên\\s*giới\\s*campuchia|biên\\s*giới\\s*thái\\s*lan|tranh\\s*chấp\\s*lãnh\\s*thổ)(?!\\s*(?:mưa|lũ|bão))\\b',
    '\\b(?:biển\\s*số\\s*định\\s*danh|đăng\\s*ký\\s*xe|sang\\s*tên\\s*chính\\s*chủ|biển\\s*số\\s*đẹp|đấu\\s*giá\\s*biển\\s*số)\\b',
    '\\b(?:biệt\\s*thự\\s*biển|condotel|shophouse|vinhomes|sun\\s*group|novaland|mở\\s*bán\\s*giai\\s*đoạn|chiết\\s*khấu\\s*khủng|ocean\\s*city|smart\\s*city|ecopark|đại\\s*đô\\s*thị|khu\\s*đô\\s*thị\\s*mới|đất\\s*nền|phân\\s*lô|bán\\s*đất)\\b',
    '\\b(?:black\\s*friday|cyber\\s*monday|lazada\\s*birthday|shopee\\s*sale|siêu\\s*sale\\s*\\d+/\\d+|ngày\\s*hội\\s*mua\\s*sắm|mã\\s*giảm\\s*giá|hoàn\\s*tiền\\s*max)\\b',
    '\\b(?:blue\\s*origin|tên\\s*lửa\\s*đẩy\\s*(?!\\s*tấn\\s*công)|vệ\\s*tinh\\s*viễn\\s*thông|trạm\\s*vũ\\s*trụ|thiên\\s*văn\\s*học|kính\\s*viễn\\s*vọng)\\b',
    '\\b(?:burnout|quiet\\s*quitting|work-life\\s*balance|hybrid\\s*work|chảy\\s*máu\\s*chất\\s*xám|nhân\\s*sự\\s*chủ\\s*chốt|môi\\s*trường\\s*làm\\s*việc\\s*lý\\s*tưởng)\\b',
    '\\b(?:buôn\\s*lậu|gian\\s*lận\\s*thương\\s*mại|hàng\\s*giả|hàng\\s*nhái|hàng\\s*cấm|vận\\s*chuyển\\s*trái\\s*phép|hàng\\s*lậu)\\b',
    '\\b(?:buông\\s*hai\\s*tay|bốc\\s*đầu|nẹt\\s*pô|đua\\s*xe|lạng\\s*lách)(?!\\s*(?:gặp\\s*nạn|tai\\s*nạn))\\b',
    '\\b(?:buông\\s*hai\\s*tay|bốc\\s*đầu|thông\\s*chốt|nẹt\\s*pô|lạng\\s*lách|đánh\\s*võng)\\b',
    '\\b(?:buộc\\s*thực\\s*hiện\\s*biện\\s*pháp\\s*khắc\\s*phục\\s*hậu\\s*quả|xử\\s*phạt\\s*vi\\s*phạm\\s*hành\\s*chính|nghiệm\\s*thu\\s*công\\s*trình|khai\\s*thác\\s*khoáng\\s*sản\\s*trái\\s*phép)\\b',
    '\\b(?:bàn\\s*phím\\s*cơ|keycap|switch|lube\\s*phím|hi-fi|dac/amp|đĩa\\s*than|bút\\s*máy|mực\\s*viết\\s*máy|sưu\\s*tầm\\s*bút|ngòi\\s*bút|viết\\s*lách)\\b',
    '\\b(?:bán\\s*nhà\\s*chính\\s*chủ|hạ\\s*giá\\s*hết\\s*nấc|cắt\\s*lỗ\\s*sâu|vị\\s*trí\\s*đắc\\s*địa|sổ\\s*hồng\\s*trao\\s*tay|hỗ\\s*trợ\\s*vay\\s*vốn|kinh\\s*doanh\\s*đắc\\s*lợi|chủ\\s*ngộp|thu\\s*hồi\\s*vốn)\\b',
    '\\b(?:bánh\\s*đậu\\s*xanh|chè\\s*tân\\s*cương|kẹo\\s*cu\\s*đơ|bánh\\s*pía|mè\\s*xửng|thương\\s*hiệu\\s*truyền\\s*thống|nghệ\\s*nhân\\s*vị\\s*nguyên)\\b',
    '\\b(?:báo\\s*giá\\s*xi\\s*măng|sắt\\s*thép|vật\\s*liệu\\s*xây\\s*dựng|mẫu\\s*nhà\\s*đẹp|nội\\s*thất\\s*hiện\\s*đại|thiết\\s*kế\\s*căn\\s*hộ)\\b',
    '\\b(?:bát\\s*tràng|vạn\\s*phúc|sa\\s*đéc|đại\\s*bái|làng\\s*nghề|sản\\s*phẩm\\s*thủ\\s*công)\\b',
    '\\b(?:bão)\\s*(?:sao\\s*kê|drama|tẩy\\s*chay|chỉ\\s*trích|ném\\s*đá|đòi\\s*nợ|kiện\\s*tụng|ly\\s*hôn)\\b',
    '\\b(?:bình\\s*đẳng\\s*giới|tháng\\s*hành\\s*động|phụ\\s*nữ\\s*việt\\s*nam|hội\\s*liên\\s*hiệp\\s*phụ\\s*nữ|bạo\\s*lực\\s*gia\\s*đình|trẻ\\s*em\\s*gái|quyền\\s*phụ\\s*nữ)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|vùng\\s*lũ|thiên\\s*tai))\\b',
    '\\b(?:bình\\s*ổn\\s*thị\\s*trường|thóc\\s*gạo|giá\\s*đất|luật\\s*phá\\s*sản|nâng\\s*hạng\\s*thị\\s*trường|chứng\\s*khoán|xuất\\s*khẩu|nhập\\s*khẩu|giá\\s*xăng|giá\\s*dầu|giá\\s*vàng|kim\\s*ngạch|tăng\\s*trưởng|gdp|lạm\\s*phát|cpi)(?!.*(?:thiệt\\s*hại|ảnh\\s*hưởng|do|vì)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:bí\\s*kíp|kinh\\s*nghiệm|mẹo)\\s*(?:tìm|thuê|chọn|mua|bán)\\s*(?:phòng\\s*trọ|nhà\\s*trọ|căn\\s*hộ|chung\\s*cư|nhà\\s*đất)\\b',
    '\\b(?:bóng\\s*đá|cầu\\s*thủ|đội\\s*tuyển|world\\s*cup|v-league|sea\\s*games|aff\\s*cup|vck|u23|u22|u21|u19|u17|premier\\s*league|serie\\s*a|la\\s*liga|bundesliga|champions\\s*league|europa\\s*league|hlv|huấn\\s*luyện\\s*viên|(?<!nghiêm\\s)trọng\\s*tài|sân\\s*cỏ|tỉ\\s*số|ghi\\s*bàn|bàn\\s*thắng|vô\\s*địch|huy\\s*chương|hcv|hcb|hcd|marathon|giải\\s*chạy|đua\\s*xe|bơi\\s*lội|tennis|vòng\\s*loại|bán\\s*kết|chung\\s*kết|ăn\\s*mừng|cổ\\s*vũ|xuống\\s*đường|nhận\\s*định|soi\\s*kèo|tỷ\\s*lệ\\s*cược|kèo\\s*nhà\\s*cái|đối\\s*đầu|trực\\s*tiếp\\s*trận)\\b',
    '\\b(?:bạch\\s*dương|kim\\s*ngưu|song\\s*tử|cự\\s*giải|sư\\s*tử|xử\\s*nữ|thiên\\s*bình|thiên\\s*yết|hổ\\s*cáp|nhân\\s*mã|ma\\s*kết|bảo\\s*bình|song\\s*ngư)\\b',
    '\\b(?:bạn\\s*đọc\\s*viết|nhịp\\s*cầu\\s*độc\\s*giả|thư\\s*tòa\\s*soạn|ký\\s*sự\\s*pháp\\s*đình|chuyện\\s*thường\\s*ngày|góc\\s*nhìn\\s*tri\\s*thức|diễn\\s*đàn\\s*kinh\\s*tế)\\b',
    '\\b(?:bạo\\s*lực\\s*gia\\s*đình|bình\\s*đẳng\\s*giới|phòng\\s*chống\\s*bạo\\s*lực|tháng\\s*hành\\s*động|mít\\s*tinh\\s*hưởng\\s*ứng|ngày\\s*gia\\s*đình\\s*việt\\s*nam)\\b',
    '\\b(?:bản\\s*quyền\\s*tác\\s*giả|sở\\s*hữu\\s*trí\\s*tuệ|bảo\\s*hộ\\s*thương\\s*hiệu|luận\\s*văn\\s*thạc\\s*sĩ|nghiên\\s*cứu\\s*sinh|hội\\s*đồng\\s*bảo\\s*vệ|tạp\\s*chí\\s*khoa\\s*học)\\b',
    '\\b(?:bản\\s*vá\\s*lỗi|mã\\s*nguồn|lỗ\\s*hổng\\s*bảo\\s*mật|tấn\\s*công\\s*ddos|phần\\s*mềm\\s*độc\\s*hại|trải\\s*nghiệm\\s*người\\s*dùng|ux/ui|giao\\s*diện\\s*mới)\\b',
    '\\b(?:bảo\\s*dưỡng|sửa\\s*chữa|thợ\\s*sửa|lắp\\s*đặt|máy\\s*nước\\s*nóng|điều\\s*hòa|máy\\s*lạnh|tủ\\s*lạnh|máy\\s*giặt|vệ\\s*sinh\\s*máy|thợ\\s*hàn|thợ\\s*cơ\\s*khí|nhôm\\s*kính)(?!.*(?:bão|lũ|ngập|hư\\s*hại|tốc\\s*mái|sạt\\s*lở|cầu|đường|giao\\s*thông|hư\\s*hỏng))\\b',
    '\\b(?:bảo\\s*hiểm\\s*(?:nhân\\s*thọ|phi\\s*nhân\\s*thọ|agribank|bảo\\s*việt|dai-ichi|manulife|prudential|aia|chubb|generali|hanwha|mb\\s*ageas|sun\\s*life|fw|cathay|liberty|pvi|bic|pti|vbi|mic)|mua\\s*bảo\\s*hiểm|bán\\s*bảo\\s*hiểm|tư\\s*vấn\\s*bảo\\s*hiểm|hợp\\s*đồng\\s*bảo\\s*hiểm)(?!.*(?:bồi\\s*thường\\s*thiệt\\s*hại\\s*do\\s*bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:bảo\\s*hiểm\\s*thất\\s*nghiệp|trợ\\s*cấp\\s*thất\\s*nghiệp|mức\\s*đóng\\s*bảo\\s*hiểm|hưởng\\s*trợ\\s*cấp|trợ\\s*cấp\\s*xã\\s*hội)\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|bhtn|biên\\s*chế|công\\s*chức|viên\\s*chức|sổ\\s*bhxh|chốt\\s*sổ|bảo\\s*hiểm\\s*thất\\s*nghiệp|bảo\\s*hiểm\\s*bắt\\s*buộc)\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|bhyt|chế\\s*độ\\s*thai\\s*sản|hưu\\s*trí|trợ\\s*cấp\\s*thất\\s*nghiệp|an\\s*sinh\\s*xã\\s*hội)\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bhxh|hưu\\s*trí|lương\\s*hưu|quỹ\\s*hưu\\s*trí|đóng\\s*bảo\\s*hiểm|trợ\\s*cấp\\s*thất\\s*nghiệp|xuất\\s*khẩu\\s*lao\\s*động)(?!.*(?:hỗ\\s*trợ\\s*đồng\\s*bào|vùng\\s*lũ|thiên\\s*tai|khắc\\s*phục))\\b',
    '\\b(?:bảo\\s*hiểm\\s*xã\\s*hội|bảo\\s*hiểm\\s*thất\\s*nghiệp|bhxh|bhtn|bhyt|chế\\s*độ\\s*bhxh)\\b',
    '\\b(?:bảo\\s*hiểm\\s*y\\s*tế|bhyt|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|thủ\\s*tục\\s*hành\\s*chính|dịch\\s*vụ\\s*công|trực\\s*tuyến|chuyển\\s*đổi\\s*số|số\\s*hóa|cổng\\s*dịch\\s*vụ\\s*công|cải\\s*cách\\s*tư\\s*pháp|thi\\s*hành\\s*án|tiếp\\s*dân|khiếu\\s*nại\\s*tố\\s*cáo|cung\\s*cầu\\s*lao\\s*động|kết\\s*nối\\s*cung\\s*cầu|ban\\s*nội\\s*chính|viện\\s*kiểm\\s*sát|tòa\\s*án|đoàn\\s*đại\\s*biểu|làm\\s*việc\\s*với|liên\\s*kết\\s*sản\\s*xuất|phê\\s*duyệt\\s*hỗ\\s*trợ)(?!.*(?:hỗ\\s*trợ|bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:bảo\\s*hiểm\\s*y\\s*tế|bhyt|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|trục\\s*lợi\\s*bảo\\s*hiểm|rút\\s*tiền\\s*bảo\\s*hiểm|thẻ\\s*bảo\\s*hiểm|khám\\s*chữa\\s*bệnh\\s*bảo\\s*hiểm)\\b',
    '\\b(?:bảo\\s*trì\\s*cáp\\s*quang|đứt\\s*cáp|gói\\s*cước\\s*data|nạp\\s*thẻ\\s*điện\\s*thoại|thuê\\s*bao\\s*di\\s*động|chất\\s*lượng\\s*đường\\s*truyền|sim\\s*số\\s*đẹp)\\b',
    '\\b(?:bảo\\s*vệ\\s*tuyệt\\s*đối|an\\s*toàn\\s*sự\\s*kiện|lễ\\s*hội|quốc\\s*khánh|ngày\\s*lễ|bảo\\s*vệ\\s*mục\\s*tiêu|diễu\\s*binh|diễu\\s*hành)\\b',
    '\\b(?:bất\\s*cập|vướng\\s*mắc|kiến\\s*nghị\\s*cử\\s*tri|phản\\s*hồi\\s*dư\\s*luận|phản\\s*biện\\s*xã\\s*hội|vấn\\s*đề\\s*nóng|câu\\s*chuyện\\s*cảnh\\s*giác)\\b',
    '\\b(?:bất\\s*ổn\\s*chính\\s*trị|đảo\\s*chính|biểu\\s*tình|nội\\s*chiến|xung\\s*đột\\s*sắc\\s*tộc)\\b',
    '\\b(?:bầu\\s*cử\\s*mỹ|tổng\\s*thống\\s*mỹ|nhà\\s*trắng|điện\\s*kremlin|thám\\s*hiểm\\s*không\\s*gian|nasa|spacex|vũ\\s*trụ|thiên\\s*văn|khảo\\s*cổ|wto|thuế\\s*quan|áp\\s*thuế|tranh\\s*chấp\\s*thương\\s*mại|đình\\s*chiến|lệnh\\s*trừng\\s*phạt|viện\\s*trợ\\s*quân\\s*sự|ngoại\\s*giao|đại\\s*sứ|giáo\\s*hoàng|vatican)\\b',
    '\\b(?:bật\\s*mí|khả\\s*năng|săn\\s*ngầm|trực\\s*thăng\\s*săn\\s*ngầm|trực\\s*thăng\\s*ka-\\d+|vũ\\s*khí\\s*tối\\s*tân|tiêm\\s*kích)\\b',
    '\\b(?:bắn\\s*cung|đua\\s*xe\\s*đạp|bowling|trượt\\s*băng|khiêu\\s*vũ\\s*thể\\s*thao|dancesport|thể\\s*dục\\s*nghệ\\s*thuật|vovinam|karatedo|taekwondo|wushu)\\b',
    '\\b(?:bắt\\s*cóc|giải\\s*cứu\\s*nạn\\s*nhân\\s*bị\\s*bắt|truy\\s*bắt|nhóm\\s*đối\\s*tượng|truy\\s*nã|án\\s*mạng|giết\\s*người|khởi\\s*tố|bắt\\s*tạm\\s*giam|gây\\s*án|điều\\s*tra|tố\\s*cáo|chiếm\\s*đoạt|trung\\s*tâm\\s*cai\\s*nghiện)(?!.*(?:lũ|bão|thiên\\s*tai))\\b',
    '\\b(?:bọ\\s*xít|kiến\\s*ba\\s*khoang|ong\\s*đốt|rắn\\s*cắn|chó\\s*cắn|ngộ\\s*độc\\s*rượu|ngộ\\s*độc\\s*nấm)(?!\\s*(?:lũ|ngập|bão))\\b',
    '\\b(?:bỏ\\s*nhà\\s*đi|rời\\s*khỏi\\s*nhà|tìm\\s*người\\s*thân|tìm\\s*trẻ\\s*lạc|bỏ\\s*đi\\s*không\\\\s*rõ|mất\\s*tích\\\\s*bí\\\\s*ẩn|thiếu\\s*nữ\\s*mất\\s*tích|đi\\s*lạc)(?!.*(?:bão|lũ|ngập|trôi|sạt|thiên\\s*tai))',
    '\\b(?:bỏ\\s*nhà\\s*đi|rời\\s*khỏi\\s*nhà|tìm\\s*người\\s*thân|tìm\\s*trẻ\\s*lạc|bỏ\\s*đi\\s*không\\s*rõ|mất\\s*tích\\s*bí\\s*ẩn)\\b',
    '\\b(?:bồi\\s*dưỡng\\s*nghiệp\\s*vụ|tập\\s*huấn\\s*kỹ\\s*năng)\\b',
    '\\b(?:bồn\\s*trộn\\s*bê\\s*tông|cánh\\s*khuấy|hệ\\s*thống\\s*truyền\\s*động|phụ\\s*gia\\s*bê\\s*tông|lưu\\s*hóa|đúc\\s*sẵn)\\b',
    '\\b(?:ca\\s*sĩ|diễn\\s*viên|người\\s*mẫu|hoa\\s*hậu|á\\s*hậu|nghệ\\s*sĩ|sao\\s*Việt|sao\\s*hàn|sao\\s*hoa)\\b',
    '\\b(?:cafe|cà\\s*phê)\\s*đường\\s*tàu\\b',
    '\\b(?:casino|sòng\\s*bạc|đánh\\s*bạc|cá\\s*cược|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề)\\b',
    '\\b(?:chim\\s*hồng\\s*hoàng|động\\s*vật\\s*quý\\s*hiếm|sách\\s*đỏ|thả\\s*về\\s*(?:rừng|biển|tự\\s*nhiên)|cứu\\s*hộ\\s*động\\s*vật|tê\\s*tê|rùa\\s*biển|cá\\s*thể|voọc|khỉ\\s*vàng)(?!.*(?:bão|lũ|lụt|sạt\\s*lở))\\b',
    '\\b(?:chim|thú|động\\s*vật)\\s*(?:quý\\s*hiếm|hoang\\s*dã|sách\\s*đỏ|bảo\\s*tồn|thả\\s*về\\s*rừng|giao\\s*nộp|bắt\\s*được)\\b',
    '\\b(?:chiến\\s*dịch\\s*quảng\\s*cáo|đại\\s*sứ\\s*thương\\s*hiệu|tính\\s*năng\\s*độc\\s*đáo|cập\\s*nhật\\s*phiên\\s*bản)\\b',
    '\\b(?:chiến\\s*lược\\s*quốc\\s*gia|trọng\\s*tâm\\s*kinh\\s*tế|mục\\s*tiêu\\s*tổng\\s*quát|nhiệm\\s*vụ\\s*đột\\s*phá)\\b',
    '\\b(?:chiến\\s*lược\\s*tăng\\s*trưởng|mô\\s*hình\\s*kinh\\s*doanh|mở\\s*rộng\\s*thị\\s*trường|huy\\s*động\\s*vốn|thị\\s*phần|doanh\\s*thu)\\b',
    '\\b(?:chiếu\\s*phim|biểu\\s*diễn|văn\\s*nghệ|cuộc\\s*thi|trực\\s*tuyến|tìm\\s*hiểu|hội\\s*diễn|liên\\s*hoan|triển\\s*lãm|hưởng\\s*ứng|phát\\s*động\\s*cuộc\\s*thi|hội\\s*thao|ngoại\\s*khóa|thực\\s*hành\\s*pccc|tìm\\s*hiểu\\s*luật|hội\\s*thi)\\b',
    '\\b(?:chiếu\\s*sáng\\s*mỹ\\s*thuật|hệ\\s*thống\\s*dali|đèn\\s*led\\s*pixel|hiệu\\s*ứng\\s*ánh\\s*sáng|kịch\\s*bản\\s*chiếu\\s*sáng|trang\\s*trí\\s*đô\\s*thị|ánh\\s*sáng\\s*vẻ\\s*đẹp)\\b',
    "\\b(?:christie's|sotheby's|nhà\\s*đấu\\s*giá\\s*danh\\s*tiếng|tranh\\s*sơn\\s*mài|khảm\\s*tam\\s*khí|gỗ\\s*thủy\\s*tùng|trầm\\s*hương\\s*tự\\s*nhiên|kỳ\\s*nam|mộc\\s*hương|đồ\\s*gỗ\\s*mỹ\\s*nghệ)\\b",
    '\\b(?:chuyên\\s*án|điều\\s*tra\\s*làm\\s*rõ|phá\\s*án|tội\\s*phạm\\s*ma\\s*túy|bắt\\s*giữ\\s*đối\\s*tượng|truy\\s*nã|vụ\\s*án\\s*giết\\s*người)\\b',
    '\\b(?:chuyến\\s*xe\\s*bão\\s*táp|phong\\s*ba\\s*bão\\s*táp|giá\\s*bão|bão\\s*lòng|bão\\s*tình|bão\\s*vây|bão\\s*sale)\\b',
    '\\b(?:chuyển\\s*tiền\\s*nhầm|nhận\\s*lại\\s*tiền|giao\\s*dịch\\s*viên|tài\\s*khoản\\s*ngân\\s*hàng|sổ\\s*tiết\\s*kiệm|thẻ\\s*tín\\s*dụng|vay\\s*vốn\\s*ưu\\s*đãi|đáo\\s*hạn|sàn\\s*giao\\s*dịch\\s*vàng|tín\\s*dụng\\s*đen|đòi\\s*nợ\\s*thuê)\\b',
    '\\b(?:cháy\\s*(?:dữ\\s*dội\\s*|lớn\\s*|ngùn\\s*ngụt\\s*)?nhà|cháy\\s*cửa\\s*hàng|cháy\\s*quán|cháy\\s*chợ|cháy\\s*gara|cháy\\s*ô\\s*tô|thiêu\\s*rụi\\s*xe|chập\\s*điện|hỏa\\s*hoạn\\s*tại|nổ\\s*bình\\s*gas)(?!.*(?:bão|lũ|thiên\\s*tai|sét\\s*đánh|rừng|cứu\\s*nạn|người\\s*chết|dập\\s*lửa|tử\\s*vong|thiệt\\s*mạng|thương\\s*vong|bé\\s*sơ\\s*sinh))\\b',
    '\\b(?:cháy\\s*lớn|vụ\\s*cháy|hỏa\\s*hoạn|bà\\s*hỏa|thiêu\\\\s*rụi|cháy\\s*rụi).*(?:nhà\\s*dân|cửa\\s*hàng|quán|karaoke|chung\\s*cư|xưởng|nhà\\s*kho|xe\\s*khách|xe\\s*tải|ô\\s*tô|xe\\s*máy|chợ|siêu\\s*thị|tầng|phòng|căn\\s*hộ)(?!.*(?:rừng|thảm\\s*thực\\s*vật|do\\s*sét|trong\\s*bão|mưa))',
    '\\b(?:cháy\\s*nhà\\s*trọ|cháy\\s*quán|cháy\\s*xưởng|cháy\\s*xe|hỏa\\s*hoạn\\s*tại\\s*nhà\\s*dân|cháy\\s*chung\\s*cư|cháy\\s*căn\\s*hộ|cháy\\s*biệt\\s*thự|cháy\\s*kho|cháy\\s*xe\\s*bồn)(?!.*(?:bão|lũ|thiên\\s*tai|sét\\s*đánh|rừng|cứu\\s*nạn|người\\s*chết|dập\\s*lửa|tử\\s*vong|thiệt\\s*mạng|thương\\s*vong))\\b',
    '\\b(?:cháy\\s*nhà|cháy\\s*ki\\s*ốt|cháy\\s*chung\\s*cư|cháy\\s*xưởng|cháy\\s*xe|hỏa\\s*hoạn\\s*tại)(?!.*(?:rừng|diện\\s*rộng|khu\\s*cong\\s*nghiệp|thảm\\s*họa|cứu\\s*hộ|thiên\\s*tai))\\b',
    '\\b(?:cháy\\s*nhà|cháy\\s*xe|cháy\\s*xưởng|cháy\\s*chợ|hỏa\\s*hoạn\\s*tại)(?!.*(?:rừng|thảm\\s*thực\\s*vật|cứu\\s*hộ|thiên\\s*tai|pccc|dập\\s*lửa|trụ\\s*sở\\s*cảnh\\s*sát))\\b',
    '\\b(?:chém|đâm|đánh\\s*hội\\s*đồng|chặn\\s*đường|hỗn\\s*chiến|mã\\s*tấu|hung\\s*khí)(?!.*(?:bão|lũ))\\b',
    '\\b(?:chê|khen|tranh\\s*cãi|bức\\s*xúc|tố\\s*cáo|lùm\\s*xùm|drama|sao\\s*kê|phốt)(?:.{0,50})(?:tiền|ủng\\s*hộ|từ\\s*thiện|cứu\\s*trợ|chuyển\\s*khoản)\\b',
    '\\b(?:chó\\s*cắn|pitbull|thú\\s*cưng|động\\s*vật\\s*tấn\\s*công|dịch\\s*tả\\s*lợn|cúm\\s*gia\\s*cầm)\\b',
    '\\b(?:chúc\\s*mừng\\s*năm\\s*mới|thư\\s*chúc\\s*tết|lời\\s*kêu\\s*gọi\\s*thi\\s*đua|thăm\\s*hỏi\\s*tặng\\s*quà|dâng\\s*hoa\\s*viếng|tưởng\\s*niệm\\s*các\\s*anh\\s*hùng)\\b',
    '\\b(?:chăm\\s*sóc\\s*chó\\s*mèo|thú\\s*cưng|giống\\s*chó|phụ\\s*kiện\\s*pet|thú\\s*y|bệnh\\s*viện\\s*thú\\s*y)\\b',
    '\\b(?:chương\\s*trình\\s*hành\\s*động|nghị\\s*quyết\\s*đại\\s*hội|đẩy\\s*mạnh\\s*thi\\s*đua|hoàn\\s*thành\\s*xuất\\s*sắc|nhân\\s*rộng\\s*mô\\s*hình)\\b',
    '\\b(?:chương\\s*trình\\s*hợp\\s*tác\\s*quốc\\s*tế|ký\\s*kết\\s*m\\s*o\\s*u)\\b',
    '\\b(?:chương\\s*trình\\s*hợp\\s*tác|biên\\s*bản\\s*ghi\\s*nhớ|ký\\s*kết\\s*thỏa\\s*thuận|xúc\\s*tiến\\s*thương\\s*mại)\\b',
    '\\b(?:chương\\s*trình\\s*khuyến\\s*mãi|hành\\s*trình\\s*bay|vé\\s*máy\\s*bay\\s*giá\\s*rẻ|giờ\\s*bay|đăng\\s*ký\\s*trực\\s*tuyến|check-in\\s*online|phòng\\s*chờ\\s*hạng\\s*thương\\s*gia)\\b',
    '\\b(?:chương\\s*trình\\s*liên\\s*kết\\s*đào\\s*tạo|trao\\s*bằng\\s*tốt\\s*nghiệp|lễ\\s*khai\\s*giảng\\s*năm\\s*học|hiệu\\s*trưởng\\s*nhà\\s*trường|phòng\\s*giáo\\s*dục\\s*đào\\s*tạo)\\b',
    '\\b(?:chương\\s*trình\\s*liên\\s*kết|hợp\\s*tác\\s*đào\\s*tạo|nghiên\\s*cứu\\s*khoa\\s*học|công\\s*bố\\s*quốc\\s*tế)\\b',
    '\\b(?:chương\\s*trình\\s*mục\\s*tiêu\\s*quốc\\s*gia|đô\\s*thị\\s*văn\\s*minh|gia\\s*đình\\s*văn\\s*hóa)\\b',
    '\\b(?:chương\\s*trình\\s*nghị\\s*sự\\s*quốc\\s*tế|tuyên\\s*bố\\s*hành\\s*động|cam\\s*kết\\s*khí\\s*hậu|net\\s*zero|chuyển\\s*đổi\\s*năng\\s*lượng|tín\\s*chỉ\\s*carbon|phát\\s*triển\\s*xanh)\\b',
    '\\b(?:chương\\s*trình\\s*tình\\s*nguyện|mùa\\s*hè\\s*xanh|tiếp\\s*sức\\s*mùa\\s*thi|hiến\\s*máu\\s*tình\\s*nguyện|bát\\s*cháo\\s*tình\\s*thương|suất\\s*cơm\\s*miễn\\s*phí)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|cô\\s*lập|khắc\\s*phục|hỗ\\s*trợ\\s*bà\\s*con|sạt\\s*lở))\\b',
    '\\b(?:chấn\\s*thương\\s*(?:cơ|gân|sụn|dây\\s*chằng|mắt\\s*cá|đầu\\s*gối)|gãy\\s*chân\\s*trong\\s*thi\\s*đấu|chấn\\s*thương\\s*khi\\s*tập\\s*luyện|phục\\s*hồi\\s*chấn\\s*thương)\\b',
    '\\b(?:chất\\s*độc\\s*da\\s*cam|nạn\\s*nhân\\s*da\\s*cam|dioxin)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|thảm\\s*họa))\\b',
    '\\b(?:chặn\\s*đứng\\s*kế\\s*hoạch|bỏ\\s*trốn|kẻ\\s*sát\\s*nhân|truy\\s*bắt|ngừng\\s*bắn|thỏa\\s*thuận\\s*hòa\\s*bình|xung\\s*đột\\s*biên\\s*giới)\\b',
    '\\b(?:chế\\s*độ\\s*tuất|trợ\\s*cấp\\s*tuất|đóng\\s*bù\\s*bảo\\s*hiểm|bảo\\s*hiểm\\s*xã\\s*hội|bhxh|lương\\s*cơ\\s*sở)\\b',
    '\\b(?:chỉ\\s*số\\s*h-index|trích\\s*dẫn\\s*khoa\\s*học|bài\\s*báo\\s*quốc\\s*tế|phản\\s*biện\\s*kín|hội\\s*đồng\\s*chức\\s*danh\\s*giáo\\s*sư|hệ\\s*số\\s*tác\\s*động|impact\\s*factor)\\b',
    '\\b(?:chỉ\\s*thị|công\\s*điện|lệnh\\s*của\\s*chủ\\s*tịch\\s*nước|công\\s*văn|ban\\s*hành\\s*văn\\s*bản)(?!.*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ|ứng\\s*phó|khẩn\\s*cấp|hỏa\\s*tốc|sạt\\s*lở|ngập|lụt|di\\s*dời|sơ\\s*tán|an\\s*toàn|cứu\\s*nạn|cứu\\s*hộ|thiệt\\s*hại|vỡ\\s*đê|điện\\s*khẩn|triều\\s*cường))',
    '\\b(?:chống\\s*bán\\s*phá\\s*giá|thuế\\s*tự\\s*vệ|biện\\s*pháp\\s*phòng\\s*vệ\\s*thương\\s*mại|fta|evfta|cptpp|rcep|quy\\s*tắc\\s*xuất\\s*xứ|phòng\\s*thương\\s*mại)\\b',
    '\\b(?:chợ\\s*phiên|không\\s*gian\\s*văn\\s*hóa|lượng\\s*khách\\s*du\\s*lịch|điểm\\s*đến\\s*hấp\\s*dẫn|check-in|sống\\s*ảo|khu\\s*du\\s*lịch|nghỉ\\s*dưỡng|vui\\s*chơi|resort|khách\\s*sạn|tour|ẩm\\s*thực)(?!.*(?:mắc\\s*kẹt|cô\\s*lập|lũ|bão|sạt\\s*lở|thiên\\s*tai|cuốn\\s*trôi|hư\\s*hỏng|mưa\\s*lớn))',
    '\\b(?:chợ\\s*phiên|không\\s*gian\\s*văn\\s*hóa|lượng\\s*khách\\s*du\\s*lịch|điểm\\s*đến\\s*hấp\\s*dẫn|check-in|sống\\s*ảo|đồi\\s*cỏ|khu\\s*du\\s*lịch|nghỉ\\s*dưỡng|vui\\s*chơi)(?!.*(?:mắc\\s*kẹt|cô\\s*lập|lũ|bão|sạt\\s*lở|thiên\\s*tai|cuốn\\s*trôi|hư\\s*hỏng))\\b',
    '\\b(?:chủ\\s*công|nòng\\s*cốt|xung\\s*kích|tình\\s*nguyện|xung\\s*phong)(?!\\s*(?:cứu\\s*hộ|cứu\\s*nạn|giúp\\s*dân|khắc\\s*phục))\\b',
    '\\b(?:chủ\\s*hộ\\s*kinh\\s*doanh|mã\\s*số\\s*thuế|giấy\\s*phép\\s*kinh\\s*doanh|thanh\\s*tra\\s*thuế|hộ\\s*kinh\\s*doanh\\s*cá\\s*thể|phí\\s*môn\\s*bài)\\b',
    '\\b(?:chủ\\s*trương\\s*đại\\s*hội|văn\\s*kiện\\s*quy\\s*hoạch|đề\\s*án\\s*phát\\s*triển|nguồn\\s*lực\\s*số|hạ\\s*tầng\\s*viễn\\s*thông|phủ\\s*sóng\\s*5\\s*g)\\b',
    '\\b(?:chủ\\s*đầu\\s*tư|nhà\\s*thầu|đấu\\s*thầu|gói\\s*thầu|định\\s*giá\\s*đất|dự\\s*án\\s*hạ\\s*tầng|đôn\\s*đốc|giải\\s*phóng\\s*mặt\\s*bằng|đền\\s*bù|quy\\s*hoạch|khởi\\s*công|khánh\\s*thành|sửa\\s*chữa\\s*đường\\s*băng|nâng\\s*cấp\\s*mở\\s*rộng|khu\\s*trung\\s*tâm\\s*hành\\s*chính|nghiên\\s*cứu\\s*quy\\s*hoạch|đô\\s*thị|lịch\\s*sử)(?!.*(?:khắc\\s*phục|sạt\\s*lở|vỡ\\s*đê|cứu\\s*hộ|thiên\\s*tai|bão|lũ|tái\\s*định\\s*cư|di\\s*dời|khẩn\\s*cấp|cầu|đường|sụt\\s*lún|giữ\\s*đất|kè\\s*chống))\\b',
    '\\b(?:chứng\\s*chỉ\\s*hành\\s*nghề|đào\\s*tạo\\s*nghiệp\\s*vụ|kỹ\\s*năng\\s*chuyên\\s*môn|huấn\\s*luyện\\s*an\\s*toàn|văn\\s*bằng\\s*quốc\\s*tế|phong\\s*trào\\s*tay\\s*nghề)\\b',
    '\\b(?:chứng\\s*khoán\\s*phái\\s*sinh|thị\\s*trường\\s*chứng\\s*khoán|phiên\\s*giao\\s*dịch|khớp\\s*lệnh|thanh\\s*khoản|nhà\\s*đầu\\s*tư\\s*nước\\s*ngoài)\\b',
    '\\b(?:clip\\s*gây\\s*bão|video\\s*xôn\\s*xao|hành\\s*động\\s*đẹp\\s*gây\\s*sốt|cư\\s*dân\\s*mạng\\s*truy\\s*tìm|phẫn\\s*nộ\\s*với\\s*hành\\s*động|bông\\s*hoa\\s*thép)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|kịch\\s*nói|phim\\s*điện\\s*ảnh|rạp\\s*phim|cà\\s*phê\\s*đường\\s*tàu|kho\\s*ảnh\\s*đẹp|website\\s*chia\\s*sẻ)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|tiết\\s*mục|hợp\\s*xướng|giải\\s*trí|phim\\s*trường|rạp\\s*chiếu\\s*phim|triển\\s*lãm|khai\\s*mạc|lễ\\s*hội|tuần\\s*lễ\\s*thời\\s*trang)\\b',
    '\\b(?:concert|liveshow|đêm\\s*nhạc|vở\\s*diễn|tiết\\s*mục|hợp\\s*xướng|giải\\s*trí|phim\\s*trường|rạp\\s*chiếu\\s*phim|triển\\s*lãm|khai\\s*mạc|lễ\\s*hội|tuần\\s*lễ\\s*thời\\s*trang|sân\\s*khấu|biểu\\s*diễn|ca\\s*múa\\s*nhạc)\\b',
    '\\b(?:container\\s*nông\\s*sản|xe\\s*chở\\s*nông\\s*sản|ùn\\s*ứ\\s*cửa\\s*khẩu|thông\\s*quan\\s*hàng\\s*hóa|xuất\\s*nhập\\s*khẩu)(?!\\s*(?:do|tại)\\s*(?:bão|lũ|mưa))\\b',
    '\\b(?:crispr|chỉnh\\s*sửa\\s*gen|liệu\\s*pháp\\s*tế\\s*bào\\s*gốc|miễn\\s*dịch\\s*trị\\s*liệu|phác\\s*đồ\\s*ung\\s*thư|y\\s*học\\s*tái\\s*tạo)\\b',
    '\\b(?:cryptocurrency|sàn\\s*giao\\s*dịch\\s*số|n\\s*f\\s*t|vốn\\s*hóa\\s*thị\\s*trường\\s*số|công\\s*nghệ\\s*chuỗi\\s*khối)\\b',
    '\\b(?:cà\\s*phê|quán\\s*bar|pub|lounge|vũ\\s*trường|karaoke)\\s*(?:khai\\s*trương|giảm\\s*giá|check-in|chill|quẩy|nhạc\\s*sống)(?!.*(?:cháy|sập|ngập|bão|lũ))\\b',
    '\\b(?:cá\\s*cảnh|thủy\\s*sinh|hồ\\s*cá\\s*koi|cây\\s*không\\s*khí|sen\\s*đá|xương\\s*rồng|đồ\\s*chơi\\s*mô\\s*hình|lego|action\\s*figure|vape|pod\\s*system)\\b',
    '\\b(?:cách\\s*mạng\\s*công\\s*nghiệp|khởi\\s*nghiệp|quỹ\\s*đầu\\s*tư)\\b',
    '\\b(?:cánh\\s*đồng\\s*mẫu\\s*lớn|hợp\\s*tác\\s*xã\\s*nông\\s*nghiệp|sản\\s*xuất\\s*giỏi|chăn\\s*nuôi\\s*tập\\s*trung|chuỗi\\s*giá\\s*trị|truy\\s*xuất\\s*nguồn\\s*gốc)\\b',
    '\\b(?:công\\s*chứng\\s*sang\\s*tên|thuế\\s*trước\\s*bạ|phí\\s*đăng\\s*ký\\s*biến\\s*động|trích\\s*lục\\s*bản\\s*đồ|giấy\\s*xác\\s*nhận\\s*tình\\s*trạng|thông\\s*tin\\s*quy\\s*hoạch)\\b',
    '\\b(?:công\\s*chứng\\s*số|ký\\s*số)\\b',
    '\\b(?:công\\s*nghệ\\s*nano|vật\\s*lý\\s*lượng\\s*tử|máy\\s*tính\\s*lượng\\s*tử|vật\\s*liệu\\s*siêu\\s*dẫn|graphene|in\\s*3d|chế\\s*tạo\\s*nhanh|vi\\s*mạch\\s*bán\\s*dẫn)\\b',
    '\\b(?:công\\s*nghệ\\s*tự\\s*động|phần\\s*mềm\\s*quản\\s*trị|hệ\\s*sinh\\s*thái\\s*số)\\b',
    '\\b(?:công\\s*thức\\s*nấu\\s*ăn|mẹo\\s*vặt\\s*nhà\\s*bếp|top\\s*quán\\s*ngon|review\\s*ẩm\\s*thực|đặc\\s*sản\\s*vùng\\s*miền|thực\\s*đơn\\s*mỗi\\s*ngày)\\b',
    '\\b(?:công\\s*ty\\s*điện\\s*lực|pc\\s*\\w+|đảm\\s*bảo\\s*điện|cấp\\s*điện|hệ\\s*thống\\s*điện|cắt\\s*điện)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|khắc\\s*phục|hư\\s*hỏng|gãy\\s*đổ|ngập|sự\\s*cố|khôi\\s*phục|hỗ\\s*trợ|mưa|giông|lốc|gió|sét))',
    '\\b(?:công\\s*tác\\s*xã\\s*hội|quỹ\\s*từ\\s*thiện|vận\\s*động\\s*quyên\\s*góp|nhà\\s*hảo\\s*tâm|mạnh\\s*thường\\s*quân|trao\\s*quà\\s*tình\\s*nghĩa|xóa\\s*đói\\s*giảm\\s*nghèo|lá\\s*lành\\s*đùm\\s*lá\\s*rách)(?!.*(?:bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở|đồng\\s*bào|hậu\\s*quả))\\b',
    '\\b(?:căn\\s*hộ\\s*cao\\s*cấp|mặt\\s*bằng\\s*kinh\\s*doanh|thuê\\s*văn\\s*phòng|sang\\s*nhượng\\s*quán|kđt|khu\\s*đô\\s*thị\\s*mới|quy\\s*hoạch\\s*chi\\s*tiết)\\b',
    '\\b(?:cơn)\\s*(?:địa\\s*chấn|sóng\\s*thần)\\s*(?:chính\\s*trị|tài\\s*chính|ngôn\\s*ngữ|mạng|sân\\s*cỏ|điện\\s*ảnh|showbiz)\\b',
    '\\b(?:cơn\\s*lốc\\s*tuyển\\s*dụng|cơ\\s*hội\\s*vàng|thăng\\s*tiến\\s*sự\\s*nghiệp|định\\s*hướng\\s*nghề\\s*nghiệp|bí\\s*quyết\\s*thành\\s*công|việc\\s*làm|tuyển\\s*dụng)\\b',
    '\\b(?:cải\\s*lương|hát\\s*tuồng|hát\\s*chèo|dân\\s*ca\\s*quan\\s*họ|đờn\\s*ca\\s*tài\\s*tử|văn\\s*hóa\\s*phi\\s*vật\\s*thể|nghệ\\s*thuật\\s*truyền\\s*thống|nghệ\\s*nhân\\s*nhân\\s*dân)\\b',
    '\\b(?:cải\\s*tạo\\s*nhà|sơn\\s*nhà|lát\\s*sàn|thiết\\s*kế\\s*nội\\s*thất|đồ\\s*gia\\s*dụng|tủ\\s*bếp|phòng\\s*khách\\s*đẹp|mẫu\\s*rèm\\s*cửa|giấy\\s*dán\\s*tường)\\b',
    '\\b(?:cảm\\s*biến\\s*áp\\s*suất|bộ\\s*điều\\s*khiển\\s*logic|plc|hệ\\s*thống\\s*mạng\\s*công\\s*nghiệp|truyền\\s*thông\\s*modbus|giám\\s*sát\\s*số|tối\\s*ưu\\s*quy\\s*trình)\\b',
    '\\b(?:cần\\s*trục\\s*tháp|xe\\s*lu\\s*rung|máy\\s*xúc\\s*bánh\\s*xích|máy\\s*ủi|xe\\s*cẩu\\s*tự\\s*hành|vận\\s*hành\\s*máy\\s*móc|bảo\\s*trì\\s*công\\s*nghiệp)\\b',
    '\\b(?:cắt\\s*mí|botox|trẻ\\s*hóa\\s*làn\\s*da|spa\\s*làm\\s*đẹp|viện\\s*thẩm\\s*mỹ)\\b',
    '\\b(?:cục\\s*thuế|ngành\\s*thuế|nợ\\s*thuế|hoàn\\s*thuế|hành\\s*chính\\s*công|trung\\s*tâm\\s*phục\\s*vụ|dịch\\s*vụ\\s*công|chuyển\\s*đổi\\s*số)\\b',
    '\\b(?:cử\\s*tri\\s*kiến\\s*nghị|thẻ\\s*căn\\s*cước|định\\s*danh\\s*điện\\s*tử|vneid|sổ\\s*hộ\\s*khẩu|trợ\\s*cấp\\s*xã\\s*hội|bảo\\s*hiểm\\s*xã\\s*hội|lương\\s*hưu|tiếp\\s*xúc\\s*cử\\s*tri|hđnd|hội\\s*đồng\\s*nhân\\s*dân|lấy\\s*phiếu\\s*tín\\s*nhiệm|chủ\\s*tịch\\s*ubnd|lãnh\\s*đạo\\s*tỉnh)(?!.*(?:bão|lũ|cứu\\s*trợ|thiên\\s*tai|khắc\\s*phục|kiểm\\s*tra|chỉ\\s*đạo|công\\s*điện|khẩn\\s*cấp|hỗ\\s*trợ|thăm|thăm\\s*hỏi|động\\s*viên|sơ\\s*tán|di\\s*dời|ứng\\s*phó))\\b',
    '\\b(?:di\\s*cư\\s*trái\\s*phép|vượt\\s*biên|nhập\\s*cảnh\\s*trái\\s*phép|lao\\s*động\\s*chui|trục\\s*xuất)(?!.*(?:do|vì|bởi)\\s*(?:thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:di\\s*sản\\s*văn\\s*hóa|phong\\s*tục\\s*tập\\s*quán|bảo\\s*tồn\\s*di\\s*tích|làng\\s*nghề\\s*truyền\\s*thống|nghệ\\s*nhân\\s*ưu\\s*tú|di\\s*vật|cổ\\s*vật)\\b',
    '\\b(?:dinh\\s*dưỡng|thực\\s*phẩm\\s*chức\\s*năng|vitamin|khoáng\\s*chất|tăng\\s*cường\\s*sức\\s*đề\\s*kháng|miễn\\s*dịch|giảm\\s*cân|làm\\s*đẹp|spa|thẩm\\s*mỹ|da\\s*liễu|nha\\s*khoa|đông\\s*y|thuốc\\s*nam|bài\\s*thuốc|thực\\s*đơn|mon\\s*ngon|đặc\\s*sản|ẩm\\s*thực|axit\\s*uric|tiểu\\s*đường|huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|ung\\s*thư|ruột\\s*kích\\s*thích|cúm\\s*mùa|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|ngộ\\s*độc\\s*thực\\s*phẩm|tỏi\\s*đen|kim\\s*tiền\\s*thảo|nghẹt\\s*mũi|kháng\\s*sinh|sống\\s*khỏe)(?!.*(?:cho|tại|vùng|cứu\\s*trợ|bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:dinh\\s*dưỡng|thực\\s*phẩm\\s*chức\\s*năng|vitamin|khoáng\\s*chất|tăng\\s*cường|sức\\s*đề\\s*kháng|miễn\\s*dịch|giảm\\s*cân|làm\\s*đẹp|spa|thẩm\\s*mỹ|da\\s*liễu|nha\\s*khoa|đông\\s*y|thuốc\\s*nam|bài\\s*thuốc|thực\\s*đơn|món\\s*ngon|đặc\\s*sản|ẩm\\s*thực|axit\\s*uric|tiểu\\s*đường|huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|ung\\s*thư|ruột\\s*kích\\s*thích|cúm\\s*mùa|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|ngộ\\s*độc\\s*thực\\s*phẩm|tỏi\\s*đen|kim\\s*tiền\\s*thảo|nghẹt\\s*mũi|kháng\\s*sinh|sống\\s*khỏe)(?!.*(?:cho|tại|vùng|cứu\\s*trợ|bão|lũ|ngập|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:thực\\s*tập|diễn\\s*tập|thực\\s*binh|hiệp\\s*đồng|huấn\\s*luyện|tình\\s*huống\\s*giả\\s*định|phương\\s*án\\s*ứng\\s*phó|tập\\s*huấn)\\b(?!.*(?:thực\\s*tế|trong\\s*mưa\\s*bão|do\\s*lũ|thiên\\s*tai|sạt\\s*lở|cứu\\s*nạn|khẩn\\s*cấp))',
    '\\b(?:diễn\\s*tập|thực\\s*chiến|an\\s*toàn\\s*thông\\s*tin|an\\s*ninh\\s*mạng|bức\\s*xạ|hạt\\s*nhân|an\\s*ninh\\s*phi\\s*truyền\\s*thống)\\b(?!.*(?:thực\\s*tế|trong\\s*mưa\\s*bão|do\\s*lũ|thiên\\s*tai|sạt\\s*lở|cứu\\s*nạn|khẩn\\s*cấp))',
    '\\b(?:diện\\s*tích\\s*sử\\s*dụng|hợp\\s*đồng\\s*đặt\\s*cọc|pháp\\s*lý\\s*dự\\s*án|tiến\\s*độ\\s*bàn\\s*giao|hoa\\s*hồng\\s*môi\\s*giới|tầng\\s*thanh\\s*khoản|nhà\\s*phố\\s*liền\\s*kề)\\b',
    '\\b(?:donald\\s*trump|biden|putin|zelensky|kim\\s*jong\\s*un|tập\\s*cận\\s*bình|netanyahu|quân\\s*đội\\s*nga|ukraine|israel|hamas|hezbollah|houthi|gaza|liban|iran|iraq|syria|yemen|triều\\s*tiên|hàn\\s*quốc|trung\\s*quốc|đài\\s*loan|biển\\s*đỏ|eo\\s*biển\\s*hormuz|boston|chicago|hoa\\s*kỳ|ấn\\s*độ|new\\s*delhi|mumbai|pakistan|bangladesh|nepal|sri\\s*lanka|sumatra|singapore|thái\\s*lan|bangkok|lào(?!\\s*cai)|campuchia|myanmar|malaysia|trạm\\s*vũ\\s*trụ|thiên\\s*châu|tàu\\s*vũ\\s*trụ|seoul|itaewon|slovakia|oman|robert\\s*fico|uranium|maroc|peru|nam\\s*phi|australia|sydney|đức|pháp|ý|italia|bồ\\s*đào\\s*nha|argentina|brazil|châu\\s*âu|eu|liên\\s*minh\\s*châu\\s*âu|đông\\s*nam\\s*á|asean|thế\\s*giới|toàn\\s*cầu|quốc\\s*tế|nước\\s*ngoài|palestine)(?!.*(?:bão|lũ|thiên\\s*tai|người\\s*việt|công\\s*dân\\s*việt\\s*nam|ảnh\\s*hưởng\\s*đến\\s*việt\\s*nam|biển\\s*đông|sạt\\s*lở|lở\\s*đất|động\\s*đất|rung\\s*chuyển|sóng\\s*thần|cháy\\s*lớn|sập|vỡ\\s*đập|thảm\\s*họa|cứu\\s*trợ|hỗ\\s*trợ|cứu\\s*hộ|cứu\\s*nạn|sơ\\s*tán|nắng\\s*nóng|hạn\\s*hán|lạnh\\s*giá|băng\\s*tuyết|rét|thiệt\\s*hại|thương\\s*vong|tử\\s*vong|mất\\s*tích))\\b',
    '\\b(?:donald\\s*trump|joe\\s*biden|nhà\\s*trắng|lầu\\s*năm\\s*góc|bầu\\s*cử\\s*mỹ|tổng\\s*thống\\s*mỹ|putin|zelensky)\\b',
    '\\b(?:du\\s*lịch\\s*tâm\\s*linh|hành\\s*hương|chùa\\s*tam\\s*chúc|bái\\s*đính|đại\\s*nam|quần\\s*thể\\s*danh\\s*thắng|di\\s*tích\\s*tâm\\s*linh|khu\\s*nghỉ\\s*dưỡng\\s*sinh\\s*thái)\\b',
    '\\b(?:du\\s*thuyền\\s*hạng\\s*sang|princess\\s*yachts|sunseeker|viking\\s*yachts|bến\\s*du\\s*thuyền|hàng\\s*không\\s*tư\\s*nhân|chuyên\\s*cơ\\s*riêng|gulfstream|bombardier)\\b',
    '\\b(?:dân\\s*tộc\\s*(?:mông|dao|tày|nùng|thái|lô\\s*lô)|văn\\s*hóa\\s*dân\\s*gian|làn\\s*điệu|điệu\\s*múa|then|cọi|páo\\s*dung|lễ\\s*hội|tín\\s*ngưỡng|thờ\\s*cúng|miếu|đền|chùa|di\\s*sản|phong\\s*tục|tập\\s*quán|làng\\s*nghề|nghệ\\s*nhân)(?!.*(?:sạt\\s*lở|lũ|bão|thiên\\s*tai|mưa\\s*lũ|khắc\\s*phục|thiệt\\s*hại|vỡ|chết\\s*người|thiệt\\s*mạng|tử\\s*vong|hồ\\s*chứa))\\b',
    '\\b(?:dâng\\s*hương|lễ\\s*hội|khai\\s*mạc|bế\\s*mạc|kỷ\\s*niệm\\s*ngày|lễ\\s*kỷ\\s*niệm|tưởng\\s*niệm|tặng\\s*bằng\\s*khen|trao\\s*bằng|ghi\\s*công|liệt\\s*sĩ)(?!.*(?:nạn\\s*nhân|bão|lũ|thiên\\s*tai|cứu\\s*hộ|hy\\s*sinh\\s*khi\\s*làm\\s*nhiệm\\s*vụ))\\b',
    '\\b(?:dòng\\s*vốn\\s*ngoại|chu\\s*kỳ\\s*kinh\\s*tế|điểm\\s*đảo\\s*chiều|lạm\\s*phát\\s*mục\\s*tiêu|nới\\s*lỏng\\s*tiền\\s*tệ|thắt\\s*chặt\\s*chi\\s*tiêu|ngân\\s*sách\\s*quốc\\s*gia)\\b',
    '\\b(?:dùng\\s*dao|cầm\\s*dao|đâm\\s*loạn\\s*xạ|chém\\s*tử\\s*vong|án\\s*mạng|trọng\\s*án|khám\\s*nghiệm\\s*tử\\s*thi)\\b',
    '\\b(?:dư\\s*luận\\s*xã\\s*hội|lên\\s*án\\s*hành\\s*vi|phản\\s*ứng\\s*cộng\\s*đồng|nghĩa\\s*vụ\\s*trách\\s*nhiệm|chuẩn\\s*mực\\s*đạo\\s*đức)\\b',
    '\\b(?:dư\\s*nợ\\s*tín\\s*dụng|tăng\\s*trưởng\\s*kinh\\s*tế|phấn\\s*đấu\\s*đạt|vượt\\s*dự\\s*báo|kinh\\s*tế\\s*vĩ\\s*mô|bội\\s*chi\\s*ngân\\s*sách|gdp|chỉ\\s*số\\s*giá|lạm\\s*phát)(?!.*(?:thiệt\\s*hại|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:dầm\\s*chuyển|cột\\s*biên|bể\\s*nước\\s*mái|hệ\\s*thống\\s*thang\\s*máy|phòng\\s*cháy\\s*chữa\\s*cháy\\s*kỹ\\s*thuật|nghiệm\\s*thu\\s*pccc)\\b',
    '\\b(?:dịch\\s*bệnh\\s*gia\\s*súc|lở\\s*mồm\\s*long\\s*móng|tai\\s*xanh|dịch\\s*tả\\s*lợn\\s*châu\\s*phi|thuốc\\s*thú\\s*y|kháng\\s*sinh\\s*cho\\s*vật\\s*nuôi|thức\\s*ăn\\s*chăn\\s*nuôi|kỹ\\s*thuật\\s*vỗ\\s*béo)\\b',
    '\\b(?:dự\\s*thảo\\s*quy\\s*tắc|lấy\\s*ý\\s*kiến\\s*phản\\s*hồi|đánh\\s*giá\\s*tác\\s*động|thẩm\\s*định\\s*độc\\s*lập|đo\\s*lường\\s*chỉ\\s*số\\s*kpi)\\b',
    '\\b(?:dự\\s*án\\s*luật|thông\\s*cáo\\s*báo\\s*chí|kỳ\\s*họp\\s*thứ|họp\\s*báo\\s*thường\\s*kỳ|quốc\\s*hội\\s*khóa|đoàn\\s*đại\\s*biểu|hđnd\\s*tỉnh|ubnd\\s*tỉnh|văn\\s*phòng\\s*chính\\s*phủ)(?!.*(?:chỉ\\s*đạo|khẩn\\s*cấp|công\\s*điện|bão|lũ|thiên\\s*tai|PCTT|MARD|cứu\\s*trợ))\\b',
    '\\b(?:fashion\\s*week|bộ\\s*sưu\\s*tập|thời\\s*trang\\s*cao\\s*cấp|nhãn\\s*hàng\\s*xa\\s*xỉ|túi\\s*xách|nước\\s*hoa|trang\\s*sức|kim\\s*cương)\\b',
    '\\b(?:fed|wall\\s*street|dow\\s*jones|nasdaq|goldman\\s*sachs|jp\\s*morgan|quỹ\\s*tiền\\s*tệ\\s*quốc\\s*tế|ngân\\s*hàng\\s*thế\\s*giới|wb|imf)\\b',
    '\\b(?:flex\\s*đến\\s*hơi\\s*thở\\s*cuối|check-in\\s*sang\\s*chảnh|k\\s*o\\s*ls|k\\s*o\\s*cs|gen\\s*z|thế\\s*hệ\\s*alpha|slay|vibe\\s*cực\\s*chỉnh|đu\\s*idol|vô\\s*tri|thao\\s*túng\\s*tâm\\s*lý)\\b',
    '\\b(?:ga\\s*ngầm|đào\\s*hầm\\s*bằng\\s*robot\\s*tbm|đốt\\s*hầm\\s*dìm|lồng\\s*hầm|phương\\s*pháp\\s*đào\\s*hở|thi\\s*công\\s*ngầm|kết\\s*cấu\\s*chịu\\s*lực|địa\\s*chất\\s*công\\s*trình)\\b',
    '\\b(?:galaxy\\s*z|iphone|ipad|macbook|logitech|samsung\\s*galaxy|oppo|xiaomi|ra\\s*mắt\\s*sản\\s*phẩm|công\\s*nghệ\\s*mới|trên\\s*tay|đập\\s*hộp|review|đánh\\s*giá\\s*xe|xe\\s*sang|siêu\\s*xe|zalo|nền\\s*tảng\\s*số|wi-fi|hao\\s*pin|công\\s*nghệ\\s*ai|hyperos|snapdragon|khung\\s*xương\\s*dephy|màn\\s*hình\\s*lili|điều\\s*chế\\s*ánh\\s*sáng|redmi|poco|ces\\s*2026|công\\s*nghiệp\\s*hỗ\\s*trợ|nội\\s*địa\\s*hóa|chuỗi\\s*giá\\s*trị|kỹ\\s*thuật\\s*số|trí\\s*tuệ\\s*nhân\\s*tạo|thử\\s*nghiệm\\s*ai|livestream|bán\\s*hàng\\s*online|thương\\s*mại\\s*điện\\s*tử|sàn\\s*tmdt|an\\s*ninh\\s*mạng|luật\\s*an\\s*ninh\\s*mạng|bluetti|charger)(?!.*(?:cứu\\s*hộ|cảnh\\s*báo|xe\\s*lội\\s*nước|cứu\\s*người|chế\\s*tạo|sáng\\s*chế|ứng\\s*phó|khẩn\\s*cấp|thiên\\s*tai|bão|lũ|lụt|hỗ\\s*trợ|cứu\\s*trợ|đồng\\s*bào|quyên\\s*góp))\\b',
    '\\b(?:game|casino|nổ\\s*hũ|bắn\\s*cá|đá\\s*gà|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề|xổ\\s*số|vietlott|jackpot|bet|cược|kèo|nhà\\s*cái|đại\\s*lý|đăng\\s*ký\\s*tặng|khuyến\\s*mãi|nạp\\s*đầu|hoàn\\s*trả|code|giftcode|apk|ios|android|app\\s*store|ch\\s*play|version|v\\d+\\.\\d+|tải\\s*app|tải\\s*game|link\\s*tải|trang\\s*chủ|đăng\\s*nhập)\\b',
    '\\b(?:game|gaming|pubg|liên\\s*quân|esports|nạp\\s*game|skin\\s*game|playstation|xbox|nintendo)\\b',
    '\\b(?:gaslighting|mối\\s*quan\\s*hệ\\s*độc\\s*hại|trầm\\s*cảm\\s*sau\\s*sinh|rối\\s*loạn\\s*lo\\s*âu|liệu\\s*pháp\\s*tâm\\s*lý|tư\\s*vấn\\s*trị\\s*liệu)\\b',
    '\\b(?:gaza|hamas|israel|ukraine|nga|tên\\s*lửa|xung\\s*đột\\s*vũ\\s*trang|chính\\s*phủ\\s*mỹ|đóng\\s*cửa|iran|trung\\s*đông|beirut|lebanon|houthi)(?!.*(?:công\\s*dân\\s*việt\\s*nam|người\\s*việt|ảnh\\s*hưởng\\s*tới\\s*việt\\s*nam|(?:hỗ\\s*trợ|cứu\\s*trợ|viện\\s*trợ)\\s*.*việt\\s*nam|sạt\\s*lở|ngập\\s*lụt|bão|lũ|thiên\\s*tai|khẩn\\s*cấp|tình\\s*huống|thảm\\s*họa))\\b',
    '\\b(?:gia\\s*phả|nhà\\s*thờ\\s*họ|giỗ\\s*tổ|tộc\\s*ước|đại\\s*hội\\s*dòng\\s*họ|con\\s*cháu\\s*hậu\\s*duệ|phụng\\s*thờ\\s*tổ\\s*tiên|lăng\\s*mộ\\s*dòng\\s*tộc)\\b',
    '\\b(?:gian\\s*lận\\s*thuế|quyết\\s*toán\\s*kế\\s*toán|chứng\\s*từ\\s*kế\\s*toán|nghiệp\\s*vụ\\s*tài\\s*chính|kế\\s*toán\\s*trưởng)\\b',
    '\\b(?:giao\\s*hàng\\s*tiết\\s*kiệm|giao\\s*hàng\\s*nhanh|viettel\\s*post|v\\s*n\\s*post|mã\\s*vận\\s*đơn|chuyển\\s*phát\\s*nhanh|phí\\s*ship|thu\\s*hộ\\s*cod|tra\\s*cứu\\s*đơn\\s*hàng)\\b',
    '\\b(?:giao\\s*lưu\\s*nghệ\\s*thuật|tôn\\s*vinh|chương\\s*trình\\s*ca\\s*nhạc|biểu\\s*diễn|lễ\\s*phát\\s*động|khai\\s*mạc|bế\\s*mạc)(?!.*(?:hỗ\\s*trợ|cứu\\s*trợ|quyên\\s*góp|từ\\s*thiện))\\b',
    '\\b(?:giao\\s*lưu\\s*nghệ\\s*thuật|tôn\\s*vinh|chương\\s*trình\\s*ca\\s*nhạc|biểu\\s*diễn|lễ\\s*phát\\s*động|khai\\s*mạc|bế\\s*mạc|tri\\s*ân\\s*khách\\s*hàng|tháng\\s*tri\\s*ân|lan\\s*tỏa\\s*yêu\\s*thương)(?!.*(?:hỗ\\s*trợ|cứu\\s*trợ|quyên\\s*góp|từ\\s*thiện|vùng\\s*lũ|bão|thiên\\s*tai))\\b',
    '\\b(?:giá\\s*cao\\s*su|giá\\s*xăng|giá\\s*dầu|ron\\s*95|e5\\s*ron\\s*92|thị\\s*trường\\s*nội\\s*địa|kiều\\s*hối|tỷ\\s*giá|lãi\\s*suất|giá\\s*tôm|thương\\s*phẩm|kinh\\s*tế\\s*số|giá\\s*tiêu|thu\\s*ngân\\s*sách|tiêu\\s*dùng\\s*nội\\s*địa|sáp\\s*nhập|doanh\\s*nghiệp\\s*(?:chớp\\s*thời\\s*cơ|xuất\\s*khẩu|nhập\\s*khẩu|fdi|thành\\s*lập\\s*mới|nhỏ\\s*và\\s*vừa)|hàng\\s*việt|xuất\\s*khẩu|nhập\\s*khẩu|kim\\s*ngạch|fdi|nhập\\s*thịt|giá\\s*lợn|leo\\s*thang|thuế\\s*bất\\s*động\\s*sản|thanh\\s*tra\\s*doanh\\s*nghiệp|tài\\s*chính\\s*quốc\\s*tế)(?!.*(?:ngập|lũ))\\b',
    '\\b(?:giá\\s*cà\\s*phê|giá\\s*hồ\\s*tiêu|giá\\s*cao\\s*su|tạm\\s*dừng\\s*đà\\s*tăng|giá\\s*nông\\s*sản)\\b',
    '\\b(?:giá\\s*heo\\s*hơi|giá\\s*cà\\s*phê|giá\\s*hồ\\s*tiêu|giá\\s*cao\\s*su|giá\\s*sầu\\s*riêng|thương\\s*lá\\s*thu\\s*mua|vào\\s*vụ\\s*thu\\s*hoạch|vựa\\s*trái\\s*cây)\\b',
    '\\b(?:giá\\s*lợn\\s*hơi|giá\\s*heo\\s*hơi|thống\\s*kê\\s*giá\\s*cả)\\b',
    '\\b(?:giá\\s*đồng|giá\\s*vàng|chứng\\s*khoán|cổ\\s*phiếu|lập\\s*đỉnh\\s*lịch\\s*sử|vượt\\s*đỉnh)(?!\\s*(?:mực\\s*nước|lũ|triều\\s*cường))\\b',
    '\\b(?:giải\\s*cứu)\\s*(?:thương\\s*vụ|hàng\\s*thủ|kinh\\s*tế|doanh\\s*nghiệp|bất\\s*động\\s*sản)(?!\\s*(?:lũ|bão))\\b',
    '\\b(?:giải\\s*cứu\\s*nạn\\s*nhân\\s*bị\\s*bắt\\s*cóc|giải\\s*cứu\\s*con\\s*tin|giải\\s*cứu\\s*người\\s*nước\\s*ngoài)(?!.*(?:bão|lũ|thiên\\s*tai|sạt\\s*lở))\\b',
    '\\b(?:giải\\s*mã\\s*gen|xét\\s*nghiệm\\s*adn|công\\s*nghệ\\s*gen|di\\s*truyền\\s*học|bản\\s*đồ\\s*gen)\\b',
    '\\b(?:giải\\s*thưởng\\s*khoa\\s*học|nghiên\\s*cứu\\s*khoa\\s*học|sáng\\s*tạo\\s*kỹ\\s*thuật|đổi\\s*mới\\s*sáng\\s*tạo|trao\\s*giải|vinh\\s*danh|nhà\\s*khoa\\s*học|học\\s*sinh\\s*giỏi|kỳ\\s*thi)(?!.*(?:dự\\s*báo|cảnh\\s*báo|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:giải\\s*tứ\\s*hùng|v-league|bóng\\s*đá|thể\\s*thao|lượt\\s*trận|giải\\s*đấu)\\b',
    '\\b(?:giải\\s*đấu\\s*esports|vòng\\s*bảng|vòng\\s*playoff|tuyển\\s*thủ\\s*chuyên\\s*nghiệp|binh\\s*đoàn|patch\\s*update|meta\\s*game|tướng\\s*mới|trang\\s*phục\\s*vĩnh\\s*viễn)\\b',
    '\\b(?:giấy\\s*phép\\s*lái\\s*xe|phạt\\s*nguội|đăng\\s*kiểm|cấp\\s*căn\\s*cước|hộ\\s*chiếu|tước\\s*bằng|định\\s*danh\\s*điện\\s*tử|trốn\\s*truy\\s*nã|đào\\s*tẩu)\\b',
    '\\b(?:giấy\\s*phép\\s*xây\\s*dựng|phân\\s*cấp|ủy\\s*quyền|thủ\\s*tục\\s*hành\\s*chính|cải\\s*cách)(?!.*(?:khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:giẫm\\s*đạp|đánh\\s*bom|khủng\\s*bố|xả\\s*súng|chiến\\s*sự|xung\\s*đột\\s*vũ\\s*trang)\\b',
    '\\b(?:giếng\\s*hoang|hố\\s*ga|cống\\s*thoát\\s*nước)\\s*(?:bỏ\\s*hoang|không\\s*nắp|nguy\\s*hiểm)(?!.*(?:ngập|lũ|mưa|bão))\\b',
    '\\b(?:giết\\s*người|phân\\s*xác|phi\\s*tang|đâm\\s*chết|mâu\\s*thuẫn\\s*tình\\s*cảm|ghen\\s*tuông|hành\\s*hung|cố\\s*ý\\s*gây\\s*thương\\s*tích)\\b',
    '\\b(?:giữ\\s*chức|bổ\\s*nhiệm|phê\\s*chuẩn|miễn\\s*nhiệm|trao\\s*quyết\\s*định|chức\\s*vụ|tân\\s*chủ\\s*tịch|tân\\s*bộ\\s*trưởng|nhân\\s*sự\\s*mới)(?!.*(?:chỉ\\s*đạo|kiểm\\s*tra|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:golf|mma|ufc|boxing|muay\\s*thai|billiards|bi-a|võ\\s*tự\\s*do|sàn\\s*đấu\\s*rực\\s*lửa|thu\\s*phục|hạ\\s*gục\\s*đối\\s*thủ)\\b',
    '\\b(?:gây|tạo|cơn)\\s*bão\\s*(?:mạng|dư\\s*luận|giá|lòng|sale|khuyến\\s*mãi|chấn\\s*thương|tài\\s*chính|sa\\s*thải|truyền\\s*thông|cảm\\s*xúc|lợi\\s*nhuận|tín\\s*dụng|bất\\s*động\\s*sản|vàng|coin|crypto)\\b',
    '\\b(?:gốm\\s*chu\\s*đậu|gốm\\s*phù\\s*lãng|đúc\\s*đồng\\s*ngũ\\s*xã|tranh\\s*đông\\s*hồ|tranh\\s*hàng\\s*trống|ngôi\\s*làng\\s*cổ|nghệ\\s*nhân\\s*truyền\\s*thống)\\b',
    '\\b(?:gỗ\\s*veneer|acrylic|mdf|laminate|sàn\\s*gỗ\\s*công\\s*nghiệp|đồ\\s*gỗ\\s*nội\\s*thất|phụ\\s*kiện\\s*tủ\\s*bếp|đèn\\s*led\\s*trang\\s*trí)\\b',
    '\\b(?:gỗ\\s*đồng\\s*kỵ|gỗ\\s*la\\s*xuyên|khảm\\s*trai\\s*chuyên\\s*mỹ|mỹ\\s*nghệ\\s*thiết\\s*kế|nghệ\\s*nhân\\s*bàn\\s*tay\\s*vàng|làng\\s*nghề\\s*tiêu\\s*biểu)\\b',
    '\\b(?:hiv/aids|thuốc\\s*arv|điều\\s*trị\\s*nghiện|cai\\s*nghiện\\s*ma\\s*túy|tệ\\s*nạn\\s*xã\\s*hội|trung\\s*tâm\\s*cai\\s*nghiện)\\b',
    '\\b(?:hiv|aids|ma\\s*túy|cai\\s*nghiện|ngáo\\s*đá|bay\\s*lắc|hóa\\s*chất\\s*duỗi\\s*tóc)\\b',
    '\\b(?:hiến\\s*máu\\s*nhân\\s*đạo|hành\\s*trình\\s*đỏ|giọt\\s*máu\\s*nghĩa\\s*tình|ngân\\s*hàng\\s*máu|tình\\s*nguyện\\s*viên\\s*hiến\\s*máu)\\b',
    '\\b(?:hiến\\s*pháp|pháp\\s*lệnh|quyền\\s*con\\s*người|quyền\\s*cơ\\s*bản|bộ\\s*máy\\s*nhà\\s*nước|đạo\\s*luật\\s*chuyên\\s*ngành|nghị\\s*quyết\\s*liên\\s*tịch)\\b',
    '\\b(?:hiếp\\s*dâm|giao\\s*cấu|cưỡng\\s*bức|dâm\\s*ô|âu\\s*yếm|chuốc\\s*say|tưới\\s*xăng|phóng\\s*hỏa|án\\s*mạng|sát\\s*hại|treo\\s*cổ|dương\\s*tính|tạt\\s*sơn|đòi\\s*nợ|đập\\s*phá|xe\\s*công\\s*nghệ|gây\\s*rối\\s*trật\\s*tự|lừa\\s*đảo|mạo\\s*danh|bắt\\s*cóc\\s*online|tội\\s*phạm|phạm\\s*tội|đổi\\s*tiền\\s*mới|sổ\\s*tiết\\s*kiệm|mã\\s*độc\\s*tống\\s*tiền|con\\s*bạc|bảo\\s*vật\\s*quốc\\s*gia|cuộc\\s*gọi\\s*lạ|truy\\s*sát|tiệm\\s*tóc|chém\\s*bạn)\\b',
    '\\b(?:hiếp\\s*dâm|giao\\s*cấu|cưỡng\\s*bức|dâm\\s*ô|đánh\\s*ghen|xô\\s*xát|tự\\s*tử|nhảy\\s*cầu|treo\\s*cổ)(?!.*(?:lũ|bão|sập|trôi|thiên\\s*tai))',
    '\\b(?:hiện\\s*vật\\s*trưng\\s*bày|bảo\\s*tàng\\s*lịch\\s*sử|khai\\s*quật\\s*di\\s*chỉ|di\\s*vật\\s*quý\\s*hiếm|trùng\\s*tu\\s*tôn\\s*tạo)\\b',
    '\\b(?:hiệp\\s*hội\\s*doanh\\s*nghiệp|phòng\\s*thương\\s*mại|vcci|liên\\s*đoàn\\s*lao\\s*động|hội\\s*liên\\s*hiệp\\s*phụ\\s*nữ|đoàn\\s*thanh\\s*niên)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|khắc\\s*phục|bão|lũ))\\b',
    '\\b(?:hiệu\\s*suất\\s*quang\\s*điện|i\\s*n\\s*v\\s*e\\s*r\\s*t\\s*e\\s*r|hệ\\s*thống\\s*lưu\\s*trữ|pin\\s*mặt\\s*trời|vệ\\s*sinh\\s*tấm\\s*pin|bảo\\s*trì\\s*điện\\s*mặt\\s*trời|hotspot)\\b',
    '\\b(?:hoa\\s*hậu|á\\s*hậu|người\\s*mẫu|showbiz|scandal|cát\\s*xê|thảm\\s*đỏ|sao\\s*việt|nam\\s*em|ngọc\\s*trinh|mỹ\\s*tâm|sơn\\s*tùng|hồ\\s*ngọc\\s*hà|trấn\\s*thành|trường\\s*giang|anh\\s*trai\\s*say\\s*hi|chị\\s*đẹp)\\b',
    '\\b(?:hoa\\s*đào\\s*nhật\\s*tân|hoa\\s*mai\\s*bình\\s*định|lan\\s*đột\\s*biến|trầm\\s*hương|cây\\s*cảnh\\s*bonsai|nghệ\\s*thuật\\s*tạo\\s*hình\\s*cây|triển\\s*lãm\\s*sinh\\s*vật\\s*cảnh)(?!.*(?:khôi\\s*phục|hồi\\s*sinh|lũ|bão|ngập|thiên\\s*tai))\\b',
    '\\b(?:hoàn\\s*thiện\\s*pháp\\s*lý|hành\\s*lang\\s*pháp\\s*lý|văn\\s*bản\\s*quy\\s*phạm|tư\\s*vấn\\s*pháp\\s*lý|trợ\\s*giúp\\s*pháp\\s*lý|cải\\s*cách\\s*tư\\s*pháp)(?!.*(?:bão|lũ))\\b',
    '\\b(?:hoàn\\s*thành\\s*vượt\\s*mức)\\b',
    '\\b(?:hoàng\\s*thành\\s*thăng\\s*long|cố\\s*đô\\s*huế|thánh\\s*địa\\s*mỹ\\s*sơn|tràng\\s*an\\s*ninh\\s*bình|di\\s*tích\\s*lịch\\s*sử\\s*cấp\\s*quốc\\s*gia|khu\\s*di\\s*tích|trùng\\s*tu\\s*di\\s*tích)\\b',
    '\\b(?:huyết\\s*áp|tim\\s*mạch|đột\\s*quỵ|tai\\s*biến|ung\\s*thư|phẫu\\s*thuật|cấy\\s*ghép)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:huyền\\s*sử|truyền\\s*thuyết|giai\\s*thoại|chứng\\s*nhân\\s*lịch\\s*sử|kỷ\\s*vật|hồi\\s*ký|tâm\\s*tình|tản\\s*mạn|góc\\s*nhìn|tam\\s*quốc|thục\\s*hán|lưu\\s*bị|quan\\s*vũ|tào\\s*tháo|tôn\\s*quyền|đại\\s*việt|sử\\s*ký)\\b',
    '\\b(?:huân\\s*chương|bằng\\s*khen|danh\\s*hiệu\\s*cao\\s*quý|kỷ\\s*niệm\\s*chương|nghệ\\s*sĩ\\s*nhân\\s*dân|nsnd|nghệ\\s*sĩ\\s*ưu\\s*tú|nsut)\\b',
    '\\b(?:huấn\\s*luyện\\s*chó|trại\\s*chó\\s*giống|thú\\s*cưng\\s*độc\\s*lạ|phục\\s*chế\\s*xe\\s*cổ|độ\\s*xe\\s*chuyên\\s*nghiệp|hệ\\s*thống\\s*âm\\s*thanh\\s*analog|băng\\s*cối|âm\\s*thanh\\s*trung\\s*thực)\\b',
    '\\b(?:huấn\\s*luyện\\s*quân\\s*sự|tuyển\\s*quân|nhập\\s*ngũ|giao\\s*nhận\\s*quân|khám\\s*tuyển|hội\\s*thao\\s*quốc\\s*phòng)\\b',
    '\\b(?:hyundai|toyota|honda|kia|mazda|ford|mitsubishi|nissan|suzuki|vinfast|mercedes|bmw|audi|lexus|porsche|land\\s*rover|peugeot|volvo|subaru|volkswagen|xe\\s*hơi|ô\\s*tô|xe\\s*máy|xe\\s*điện|ra\\s*mắt|phiên\\s*bản|thế\\s*hệ|nâng\\s*cấp|trang\\s*bị|động\\s*cơ|công\\s*suất|momen\\s*xoắn|tiêu\\s*thụ|nhiên\\s*liệu|giá\\s*bán|niêm\\s*yết|lăn\\s*bánh|trả\\s*góp|lãi\\s*suất|vay\\s*vốn|ngân\\s*hàng|uav|drone|máy\\s*bay\\s*không\\s*người\\s*lái|dk\\s*việt\\s*nhật)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn|tìm\\s*kiếm|bão|lũ|ngập|lụt|trôi|sạt|thiên\\s*tai|hư\\s*hỏng))\\b',
    '\\b(?:hàng\\s*hóa\\s*qua\\s*biên\\s*giới|vận\\s*chuyển\\s*trái\\s*phép|buôn\\s*lậu|gian\\s*lận\\s*thương\\s*mại|hàng\\s*giả|kéo\\s*xe|cửu\\s*vạn|vượt\\s*biên|xuất\\s*nhập\\s*cảnh\\s*trái\\s*phép)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|vùng\\s*lũ))\\b',
    '\\b(?:hàng\\s*lậu|hàng\\s*cấm|tàng\\s*trữ\\s*trái\\s*phép|vận\\s*chuyển\\s*trái\\s*phép\\s*chất\\s*ma\\s*túy|bắt\\s*quả\\s*tang\\s*vụ)\\b',
    '\\b(?:hàng\\s*thừa\\s*kế|phân\\s*chia\\s*tài\\s*sản|tranh\\s*chấp\\s*hôn\\s*nhân|quyền\\s*nuôi\\s*con|án\\s*phí\\s*dân\\s*sự|hòa\\s*giải\\s*cơ\\s*sở)\\b',
    '\\b(?:hàng\\s*tiêu\\s*dùng\\s*nhanh|f\\s*m\\s*c\\s*g|thực\\s*phẩm\\s*đóng\\s*gói|thiết\\s*bị\\s*nhà\\s*bếp|chuỗi\\s*cửa\\s*hàng\\s*bán\\s*lẻ|hàng\\s*hóa\\s*thiết\\s*yếu)\\b',
    '\\b(?:hàng\\s*tết|bình\\s*ổn\\s*giá|dự\\s*trữ\\s*hàng|quà\\s*tết|bánh\\s*kẹo|mứt\\s*tết|hoa\\s*tết|chợ\\s*hoa|lễ\\s*hội\\s*xuân|đường\\s*hoa)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|sạt\\s*lở|ách\\s*tắc))\\b',
    '\\b(?:hành\\s*trình\\s*công\\s*lý|đạo\\s*đức\\s*nghề\\s*nghiệp|quy\\s*tắc\\s*ứng\\s*xử|văn\\s*hóa\\s*công\\s*sở|nghỉ\\s*(?:tết|lễ)\\s*\\d+\\s*ngày|đề\\s*xuất\\s*nghỉ)\\b',
    '\\b(?:hành\\s*tỏi\\s*lý\\s*sơn|quế\\s*trà\\s*bồng|hồi\\s*lạng\\s*sơn|tiêu\\s*chư\\s*sê|hạt\\s*điều\\s*bình\\s*phước|đặc\\s*sản\\s*tiêu\\s*biểu|nguyên\\s*liệu\\s*quý|vùng\\s*nguyên\\s*liệu)\\b',
    '\\b(?:hòa\\s*giải\\s*viên|trung\\s*tâm\\s*trọng\\s*tài|quy\\s*trình\\s*hòa\\s*giải|thỏa\\s*thuận\\s*dân\\s*sự|nhân\\s*chứng\\s*vật\\s*chứng|người\\s*có\\s*quyền\\s*lợi\\s*nghĩa\\s*vụ)\\b',
    '\\b(?:hướng\\s*dẫn\\s*thủ\\s*tục|cấp\\s*đổi\\s*giấy\\s*phép|tra\\s*cứu\\s*thông\\s*tin|dịch\\s*vụ\\s*công\\s*mức\\s*độ\\s*4|thủ\\s*tục\\s*một\\s*cửa)\\b',
    '\\b(?:hướng\\s*dẫn\\s*viên|thuyết\\s*minh\\s*viên)\\s*(?:du\\s*lịch|bảo\\s*tàng|di\\s*tích)(?!.*(?:mắc\\s*kẹt|cô\\s*lập|lũ|bão))\\b',
    '\\b(?:hướng\\s*dẫn\\s*áp\\s*dụng|quy\\s*định\\s*chi\\s*tiết|thông\\s*tư\\s*hướng\\s*dẫn|nghị\\s*định\\s*sửa\\s*đổi|có\\s*hiệu\\s*lực\\s*thi\\s*hành)\\b',
    '\\b(?:hướng\\s*dẫn\\s*đăng\\s*ký|thủ\\s*tục\\s*sang\\s*tên|cấp\\s*đổi\\s*số\\s*đỏ|đính\\s*chính\\s*thông\\s*tin|tra\\s*cứu\\s*quy\\s*hoạch|hồ\\s*sơ\\s*địa\\s*chính)\\b',
    '\\b(?:hạ\\s*cánh\\s*khẩn\\s*cấp|sự\\s*cố\\s*kỹ\\s*thuật|máy\\s*bay|sân\\s*bay|hàng\\s*không|phi\\s*công|tiếp\\s*viên|đường\\s*băng|cất\\s*cánh|hạ\\s*cánh|delay|hủy\\s*chuyến|đổi\\s*hướng|quay\\s*đầu)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|sương\\s*mù|gió\\s*giật|thời\\s*tiết\\s*xấu))\\b',
    '\\b(?:hạnh\\s*phúc\\s*quanh\\s*ta|tổ\\s*ấm\\s*việt|gia\\s*đình\\s*và\\s*pháp\\s*luật|giá\\s*trị\\s*truyền\\s*thống|đạo\\s*đức\\s*lối\\s*sống|nếp\\s*sống\\s*văn\\s*minh)\\b',
    '\\b(?:hạt\\s*giống\\s*tâm\\s*hồn|châm\\s*ngôn\\s*sống|triết\\s*lý\\s*kinh\\s*doanh|quà\\s*tặng\\s*cuộc\\s*sống|nhân\\s*sinh\\s*quan|đắc\\s*nhân\\s*tâm)\\b',
    '\\b(?:hậu\\s*kỳ\\s*ảnh|lightroom|chỉnh\\s*màu\\s*cinematic|dải\\s*tương\\s*phản|dynamyc\\s*range|loa\\s*kiểm\\s*âm|tai\\s*nghe\\s*chống\\s*ồn|hi-res\\s*audio)\\b',
    '\\b(?:hệ\\s*lõi\\s*cứng|outrigger|belt\\s*truss|giằng\\s*cột|móng\\s*vây|tường\\s*vây|cọc\\s*baryte)\\b',
    '\\b(?:hệ\\s*thống\\s*cấp\\s*thoát\\s*nước|trạm\\s*bơm\\s*tăng\\s*áp|bể\\s*xử\\s*lý\\s*nước\\s*thải|đường\\s*ống\\s*hdpe|van\\s*giảm\\s*áp|cột\\s*áp|hố\\s*ga\\s*thông\\s*minh)\\b',
    '\\b(?:hệ\\s*thống\\s*phân\\s*phối\\s*bán\\s*lẻ|chuỗi\\s*cửa\\s*hàng\\s*tiện\\s*lợi|siêu\\s*thị\\s*mini|trải\\s*nghiệm\\s*khách\\s*hàng|cơ\\s*hội\\s*hợp\\s*tác\\s*kinh\\s*doanh|phát\\s*triển\\s*đại\\s*lý)\\b',
    '\\b(?:học\\s*bổng\\s*toàn\\s*phần|hội\\s*thảo\\s*quốc\\s*tế|tạp\\s*chí\\s*isi/scopus|công\\s*bố\\s*nghiên\\s*cứu|hệ\\s*đào\\s*tạo\\s*từ\\s*xa|văn\\s*bằng\\s*2|vừa\\s*học\\s*vừa\\s làm)\\b',
    '\\b(?:học\\s*phí|điểm\\s*chuẩn|quy\\s*chế\\s*thi|kỳ\\s*thi\\s*tốt\\s*nghiệp|sách\\s*giáo\\s*khoa|kỷ\\s*yếu|tự\\s*chủ\\s*đại\\s*học|dạy\\s*thêm|học\\s*thêm|ôn\\s*thi|luyện\\s*thi|sĩ\\s*tử|điểm\\s*thi|tra\\s*cứu\\s*điểm|khai\\s*giảng|năm\\s*học\\s*mới|tuyển\\s*sinh|giáo\\s*viên\\s*chủ\\s*nhiệm|đề\\s*án\\s*ngoại\\s*ngữ|tiếng\\s*anh|lịch\\s*nghỉ\\s*tết|nghỉ\\s*học|lịch\\s*học|tựu\\s*trường|tặng\\s*sách|trao\\s*tặng\\s*sách|tủ\\s*sách|phân\\s*hiệu|thư\\s*viện)(?!.*(?:vùng\\s*lũ|bão|thiên\\s*tai|hỗ\\s*trợ|khắc\\s*phục|sạt\\s*lở|mưa\\s*lũ|rét|ngập))\\b',
    '\\b(?:học\\s*đàn|học\\s*vẽ|chụp\\s*ảnh\\s*chân\\s*dung|ống\\s*máy\\s*ảnh|mirrorless|dựng\\s*phim|hậu\\s*kỳ|thiết\\s*kế\\s*đồ\\s*họa|photoshop|illustrator)\\b',
    '\\b(?:hỏi\\s*đáp\\s*pháp\\s*luật|tư\\s*vấn\\s*sức\\s*khỏe|chuyện\\s*lạ\\s*đó\\s*đây|tiêu\\s*điểm\\s*dư\\s*luận|góc\\s*nhìn\\s*chuyên\\s*gia|tiếng\\s*nói\\s*cử\\s*tri|báo\\s*chí\\s*điều\\s*tra|phóng\\s*sự\\s*dài\\s*kỳ)\\b',
    '\\b(?:hố\\s*ga|giếng\\s*hoang|hố\\s*công\\s*trình)(?!.*(?:ngập|lũ|bão|sạt|mưa|triều\\s*cường))\\b',
    '\\b(?:hố\\s*đen|thiên\\s*hà|dải\\s*ngân\\s*hà|vật\\s*chất\\s*tối|gen\\s*di\\s*truyền|dna|tế\\s*bào\\s*gốc|biến\\s*đổi\\s*gen|vi\\s*khuẩn|virus\\s*(?!\\s*it))\\b',
    '\\b(?:hồ\\s*sơ\\s*pháp\\s*lý|thủ\\s*tục\\s*hành\\s*chính|giải\\s*ngân\\s*vốn)\\b',
    '\\b(?:hộ\\s*nghèo|cận\\s*nghèo|giảm\\s*nghèo\\s*bền\\s*vững|quà\\s*tết|hiến\\s*máu|khám\\s*bệnh\\s*miễn\\s*phí|vượt\\s*khó\\s*vươn\\s*lên)\\b',
    '\\b(?:hội\\s*chợ\\s*thương\\s*mại|ngày\\s*hội\\s*việc\\s*làm|lễ\\s*hội\\s*ẩm\\s*thực|minigame|bốc\\s*thăm\\s*trúng\\s*thưởng|vòng\\s*quay\\s*may\\s*mắn)\\b',
    '\\b(?:hội\\s*cựu\\s*thanh\\s*niên\\s*xung\\s*phong|ban\\s*liên\\s*lạc\\s*bạn\\s*chiến\\s*đấu|hội\\s*hỗ\\s*trợ\\s*gia\\s*đình\\s*liệt\\s*sĩ|quỹ\\s*nghĩa\\s*tình\\s*đồng\\s*đội|tri\\s*ân\\s*anh\\s*hùng)\\b',
    '\\b(?:hội\\s*nghị\\s* thượng\\s*đỉnh|G7|G20|ASEAN|APEC|UNESCO|WHO|UNICEF|WTO|NATO|liên\\s*hợp\\s*quốc|nghị\\s*quyết\\s*chung|tuyên\\s*bố\\s*chung)\\b',
    '\\b(?:hội\\s*nghị\\s*hiệp\\s*thương|kỳ\\s*hợp\\s*thứ|đảng\\s*viên\\s*mới|sinh\\s*hoạt\\s*chi\\s*bộ|nghị\\s*quyết\\s*trung\\s*ương|công\\s*tác\\s*kiểm\\s*tra\\s*đảng)\\b',
    '\\b(?:hội\\s*người\\s*cao\\s*tuổi|hội\\s*cựu\\s*chiến\\s*binh|đại\\s*hội\\s*chi\\s*hội|phong\\s*trào\\s*văn\\s*nghệ|khiêu\\s*vũ\\s*dưỡng\\s*sinh|câu\\s*lạc\\s*bộ\\s*hưu\\s*trí)\\b',
    '\\b(?:hội\\s*thảo\\s*chuyên\\s*đề|tổng\\s*kết\\s*phong\\s*trào|thi\\s*đua\\s*ngành\\s*giáo\\s*dục|trao\\s*giải\\s*thưởng\\s*sáng\\s*tạo|triển\\s*khai\\s*nhiệm\\s*vụ\\s*trọng\\s*tâm)\\b',
    '\\b(?:hội\\s*đông\\s*y|cây\\s*thuốc\\s*nam|vườn\\s*dược\\s*liệu|hải\\s*thượng\\s*lãn\\s*ông|tuệ\\s*tĩnh|y\\s*học\\s*cổ\\s*truyền|châm\\s*cứu|bấm\\s*huyệt)\\b',
    '\\b(?:hộp\\s*số\\s*turbine|hệ\\s*thống\\s*bôi\\s*trơn|cảm\\s*biến\\s*rung\\s*động|phần\\s*mềm\\s*scada|giám\\s*sát\\s*từ\\s*xa|bảo\\s*trì\\s*dự\\s*phòng|khắc\\s*phục\\s*lỗi\\s*kỹ\\s*thuật)\\b',
    '\\b(?:hợp\\s*tác\\s*đa\\s*phương|diễn\\s*đàn\\s*an\\s*ninh|đối\\s*thoại\\s*chiến\\s*lược|biên\\s*bản\\s*thỏa\\s*thuận|quan\\s*hệ\\s*đối\\s*ngoại|vị\\s*thế\\s*quốc\\s*gia)\\b',
    '\\b(?:iphone|samsung|oppo|xiaomi|smartphone|macbook|ipad|galaxy|máy\\s*tính\\s*bảng|laptop|xe\\s*điện|vinfast|tesla|chip|vi\\s*xử\\s*lý|hệ\\s*điều\\s*hành|android|ios|ứng\\s*dụng|app|lộ\\s*diện\\s*thiết\\s*kế|giá\\s*bán\\s*niêm\\s*yết|ra\\s*mắt\\s*sản\\s*phẩm|deepfake|giả\\s*giọng|test\\s*de\\s*torture|résistance|trifold)\\b',
    '\\b(?:j-league|k-league|nagoya\\s*grampus|kawasaki|yokohama|incheon|gangwon|buriram|pathum)\\b',
    '\\b(?:khai\\s*trương\\s*chi\\s*nhánh|giảm\\s*giá\\s*khai\\s*trương|voucher\\s*mua\\s*sắm|thẻ\\s*thành\\s*viên|tích\\s*điểm\\s*đổi\\s*quà|giờ\\s*vàng\\s*mua\\s*sắm)\\b',
    '\\b(?:khiếu\\s*nại\\s*hành\\s*chính|quyết\\s*định\\s*hành\\s*chính|thời\\s*hiệu\\s*khiếu\\s*nại|giải\\s*quyết\\s*tố\\s*cáo|tòa\\s*án\\s*hành\\s*chính|phán\\s*quyết\\s*cuối\\s*cùng)\\b',
    '\\b(?:khoe\\s*dáng|xả\\s*kho\\s*ảnh|style\\s*cực\\s*chất|nhan\\s*sắc\\s*đời\\s*thực|gây\\s*sốt\\s*với\\s*bộ\\s*ảnh|lộ\\s*diện\\s*sau\\s*khi|phong\\s*cách\\s*thời\\s*thượng|gu\\s*thời\\s*trang)\\b',
    '\\b(?:khuyến\\s*cáo|nhắc\\s*nhở|kỹ\\s*năng|phòng\\s*ngừa|tập\\s*huấn)\\s*(?:pccc|an\\s*toàn|ngập\\s*lụt|đuối\\s*nước)\\b',
    '\\b(?:khách\\s*du\\s*lịch|lượng\\s*khách|ngành\\s*du\\s*lịch|doanh\\s*thu\\s*du\\s*lịch|kích\\s*cầu\\s*du\\s*lịch|vui\\s*xuân|đón\\s*tết|du\\s*xuân|nghỉ\\s*lễ|dịp\\s*lễ|vé\\s*máy\\s*bay|chặng\\s*bay|đường\\s*bay|hàng\\s*không|vietjet|vietnam\\s*airlines|bamboo\\s*airways|vietravel|check-in|sống\\s*ảo|điểm\\s*đến|khám\\s*phá|trải\\s*nghiệm|tour|combo|voucher|homestay|resort|tham\\s*quan|nghỉ\\s*dưỡng|săn\\s*mây|săn\\s*tuyết|mùa\\s*vàng|mùa\\s*lúa|hoa\\s*tam\\s*giác\\s*mạch|hoa\\s*đỗ\\s*quyên)(?!.*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ|mắc\\s*kẹt|cô\\s*lập|khắc\\s*phục|thiệt\\s*hại|bão|lũ|thiên\\s*tai|cháy|chìm))\\b',
    '\\b(?:khám\\s*chữa\\s*bệnh|bệnh\\s*viện|bác\\s*sĩ|phẫu\\s*thuật|cấy\\s*ghép|nội\\s*soi|tư\\s*vấn\\s*sức\\s*khỏe|dinh\\s*dưỡng|làm\\s*đẹp|thẩm\\s*mỹ)(?!.*(?:cấp\\s*cứu|tai\\s*nạn|thương\\s*vong|sập|cháy|nổ|bão|lũ))\\b',
    '\\b(?:khám\\s*nghiệm\\s*tử\\s*thi|pháp\\s*y|hung\\s* khí|tang\\s*vật\\s*vụ\\s*án|hồ\\s*sơ\\s*vụ\\s* án|lệnh\\s*truy\\s*nã|nghi\\s*phạm\\s*đang\\s*bỏ\\s*trốn|chứng\\s*cứ\\s*quan\\s*trọng)\\b',
    '\\b(?:khám\\s*phá\\s*thế\\s*giới|hành\\s*trình\\s*di\\s*sản|cửa\\s*sổ\\s*tâm\\s*hồn|những\\s*tấm\\s*lòng\\s*vàng|lời\\s*hay\\s*ý\\s*đẹp|gương\\s*sáng\\s*quanh\\s*ta)\\b',
    '\\b(?:khám\\s*xét|niêm\\s*phong|cưỡng\\s*chế\\s*kê\\s*biên|phong\\s*tỏa\\s*tài\\s*khoản|tạm\\s*đình\\s*chỉ\\s*công\\s*tác|lệnh\\s*bắt\\s*tạm\\s*giam|đọc\\s*lệnh\\s*khởi\\s*tố)\\b',
    '\\b(?:khóa\\s*học\\s*online\\s*miễn\\s*phí|hội\\s*thảo\\s*trực\\s*tuyến|webinar|đào\\s*tạo\\s*kỹ\\s*năng\\s*mềm|chứng\\s*chỉ\\s*hoàn\\s*thành|học\\s*bổng\\s*khuyến\\s*học)\\b',
    '\\b(?:khảm\\s*xà\\s*cừ|mây\\s*tre\\s*đan|đúc\\s*đồng|nghệ\\s*thuật\\s*chạm\\s*khắc|sản\\s*phẩm\\s*mỹ\\s*nghệ|tinh\\s*hoa\\s*di\\s*sản)\\b',
    '\\b(?:khẩn\\s*cấp\\s*(?:chi|rót)\\s*vốn|ngân\\s*sách|đầu\\s*tư\\s*công)(?!\\s*(?:khắc\\s*phục|hỗ\\s*trợ|cứu\\s*trợ|phòng\\s*chống))\\b',
    '\\b(?:khắc\\s*phục\\s*hậu\\s*quả\\s*vụ\\s*cháy|khắc\\s*phục\\s*hậu\\s*quả\\s*tai\\s*nạn|điều\\s*tra\\s*nguyên\\s*nhân\\s*vụ\\s*tai\\s*nạn|khám\\s*nghiệm\\s*hiện\\s*trường\\s*vụ\\s*cháy)\\b',
    '\\b(?:khớp\\s*lệnh|dư\\s*mua|dư\\s*bán|chứng\\s*khoán\\s*phái\\s*sinh|khối\\s*ngoại|vốn\\s*điều\\s*lệ|lệnh\\s*giới\\s*hạn)\\b',
    '\\b(?:kim\\s*cương|đá\\s*quý|trang\\s*sức|thời\\s*trang\\s*cao\\s*cấp|sàn\\s*diễn|người\\s*mẫu)\\b',
    '\\b(?:kinh\\s*phí\\s*nghiên\\s*cứu|xếp\\s*hạng\\s*đại\\s*học|chỉ\\s*số\\s*trích\\s*dẫn|đăng\\s*báo\\s*quốc\\s*tế|quỹ\\s*phát\\s*triển\\s*khoa\\s*học|nghiên\\s*cứu\\s*sinh\\s*tiến\\s*sĩ)\\b',
    '\\b(?:kiểm\\s*tra\\s*chuyên\\s*ngành|thanh\\s*tra\\s*hành\\s*chính|xử\\s*phạt\\s*vi\\s*phạm|niêm\\s*yết\\s*công\\s*khai|lấy\\s*ý\\s*kiến\\s*nhân\\s*dân)\\b',
    '\\b(?:kiểm\\s*tra\\s*nồng\\s*độ\\s*cồn|phạt\\s*nguội|xe\\s*quá\\s*tải|trạm\\s*thu\\s*phí|vào\\s*cua|mất\\s*lái)\\b',
    '\\b(?:kiểm\\s*tra\\s*sát\\s*hạch|đường\\s*lối\\s*chính\\s*sách|nghị\\s*quyết\\s*đảng)\\b',
    '\\b(?:kiểu\\s*dáng\\s*công\\s*nghiệp|sở\\s*hữu\\s*trí\\s*tuệ|bảo\\s*hộ\\s*thương\\s*hiệu|đăng\\s*ký\\s*nhãn\\s*hiệu|vi\\s*phạm\\s*bản\\s*quyền|tác\\s*quyền)\\b',
    '\\b(?:kiện\\s*toàn\\s*ban\\s*chỉ\\s*đạo|nghiêm\\s*cấm\\s*lợi\\s*dụng|kiểm\\s*tra\\s*về\\s*phòng\\s*cháy|thực\\s*tập|hội\\s*thao\\s*pccc)\\b(?!.*(?:cháy\\s*rừng|rừng\\s*bị\\s*cháy))',
    '\\b(?:ktv|massage|karaoke)\\s*(?:ôm|đào|tay\\s*vịn|gọi\\s*đào|nam\\s*ktv|boy\\s*bao|bao\\s*phòng)\\b',
    '\\b(?:kubet|thabet|sunwin|go88|b52|789club|rikvip|manclub|jun88|new88|hi88|shbet|789bet|f8bet|188bet|w88|fb88|fun88|bk8|m88|v9bet|12bet|dafabet|happyluke|k8|letou|cmd368|sv388|s128|ae888|v68|vi68|kuwin|okvip|nhatvip|tk88|ww88|cwin|88clb|ai88bet|88vin|saba|f168|77king88|bong88ag|mibet|bj88|vn8k|cuocbanh88|net88|s666|on59|388bet|sv388|lc88|789win|ee88|98win|may88|eubet|abc8|tv88|tt88|nk88|win55|88go|b5|vt999|vip8888|q88|bet88|cá\\s*cược|nhà\\s*cái)(?!.*(?:bão|lũ))\\b',
    '\\b(?:kèo\\s*bóng|soi\\s*kèo|tỷ\\s*lệ\\s*cược|nhà\\s*cái|ku\\s*casino|kubet|win79|go88|nhận\\s*định\\s*trận\\s*đấu|tỷ\\s*lệ\\s*kèo|soi\\s*cầu|lô\\s*đề|nổ\\s*hũ|bắn\\s*cá|game\\s*bài|tiến\\s*lên\\s*miền\\s*nam|đá\\s*gà|xóc\\s*đĩa|tài\\s*xỉu|b29|bet88)\\b',
    '\\b(?:kích\\s*hoạt\\s*vneid|tài\\s*khoản\\s*vneid|vssid|bhxh|bảo\\s*hiểm\\s*xã\\s*hội|định\\s*danh\\s*điện\\s*tử|nộp\\s*phạt\\s*online|dịch\\s*vụ\\s*công\\s*trực\\s*tuyến|cổng\\s*dịch\\s*vụ\\s*công)\\b',
    '\\b(?:ký\\s*ức|hồi\\s*tưởng|nhìn\\s*lại|phim\\s*tài\\s*liệu|năm\\s*xưa|chuyện\\s*cũ|tư\\s*liệu\\s*quý)\\b',
    '\\b(?:kết\\s*cấu\\s*thép|hệ\\s*thống\\s*m\\s*e\\s*p|tòa\\s*nhà\\s*xanh|chứng\\s*chỉ\\s*leed|thiết\\s*kế\\s*kháng\\s*chấn|vật\\s*liệu\\s*xây\\s*dựng\\s*mới|công\\s*nghệ\\s*bê\\s*tông)\\b',
    '\\b(?:kết\\s*quả\\s*mong\\s*đợi)\\b',
    '\\b(?:kết\\s*quả\\s*quan\\s*trắc|trạm\\s*đo|chỉ\\s*số\\s*hàng\\s*ngày|độ\\s*mặn\\s*đo\\s*được|mặn\\s*xâm\\s*nhập\\s*nhẹ)\\b',
    '\\b(?:kết\\s*quả\\s*tin\\s*tức\\s*cho\\s*từ\\s*khóa|tin\\s*tức\\s*tv|video\\s*nổi\\s*bật)\\b',
    '\\b(?:kết\\s*thúc\\s*phiên|sắc\\s*xanh\\s*lan\\s*tỏa|sắc\\s*đỏ\\s*bao\\s*trùm|v\\s*n\\s*index\\s*quay\\s*đầu|khối\\s*ngoại\\s*bán\\s*ròng|thanh\\s*khoản\\s*sụt\\s*giảm|nhóm\\s*cổ\\s*phiếu\\s*vốn\\s*hóa)\\b',
    '\\b(?:kịch\\s*bản\\s*biến\\s*đổi|tầm\\s*nhìn\\s*20\\d{2}|dự\\s*báo\\s*đến\\s*năm|mô\\s*hình\\s*mô\\s*phỏng|nghiên\\s*cứu\\s*khoa\\s*học|đề\\s*tài\\s*cấp\\s*bộ)\\b',
    '\\b(?:kỷ\\s*lục\\s*thế\\s*giới|kỷ\\s*lục\\s*quốc\\s*gia|huy\\s*chương\\s*vàng|huy\\s*chương\\s*bạc|huy\\s*chương\\s*đồng|bảng\\s*tổng\\s*sắp|phá\\s*kỷ\\s*lục)\\b',
    '\\b(?:kỷ\\s*niệm\\s*(?:\\d+|năm)\\s*năm|ngày\\s*thành\\s*lập|số\\s*đầu\\s*tiên|sinh\\s*nhật|mừng\\s*thọ)\\b',
    '\\b(?:kỷ\\s*niệm\\s*\\d+\\s*năm\\s*thành\\s*lập|ngày\\s*truyền\\s*thống|đại\\s*hội\\s*đại\\s*biểu|văn\\s*kiện\\s*đại\\s*hội|báo\\s*cáo\\s*chính\\s*trị|lễ\\s*báo\\s*công|viếng\\s*lăng\\s*chủ\\s*tịch|dâng\\s*hương\\s*tưởng\\s*niệm)(?!.*(?:nạn\\s*nhân|người\\s*tử\\s*vong|đồng\\s*bào|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:kỹ\\s*thuật\\s*giao\\s*bóng|cú\\s*đánh\\s*trái\\s*tay|chiến\\s*thuật\\s*phối\\s*hợp|đường\\s*chuyền\\s*quyết\\s*định|tình\\s*huống\\s*cố\\s*định|việt\\s*vị|trọng\\s*tài\\s*v\\s*a\\s*r|thẻ\\s*đỏ)\\b',
    '\\b(?:kỹ\\s*thuật\\s*nấu\\s*nướng|lên\\s*men\\s*tự\\s*nhiên|vi\\s*sinh\\s*thực\\s*phẩm|hương\\s*liệu\\s*nhân\\s*tạo|an\\s*toàn\\s*vệ\\s*sinh|chuỗi\\s*cung\\s*ứng\\s*lạnh)\\b',
    '\\b(?:kỹ\\s*thuật\\s*trồng|chăm\\s*sóc\\s*cây\\s*cảnh|phong\\s*lan|bonsai|phân\\s*bón|thuốc\\s*trừ\\s*sâu|nông\\s*nghiệp\\s*công\\s*nghệ\\s*cao|giống\\s*cây\\s*trồng)\\b',
    "\\b(?:l'oreal|estee\\s*lauder|shiseido|lancome|laneige|innisfree|sk-ii|mỹ\\s*phẩm\\s*chính\\s*hãng|son\\s*môi|kem\\s*dưỡng\\s*da|chu\\s*trình\\s*skincare)\\b",
    '\\b(?:lan\\s*can|vỉa\\s*hè|bờ\\s*kè|cây\\s*xanh|công\\s*viên|ghế\\s*đá).*(?:hư\\s*hỏng|gãy|đổ)(?!.*(?:sạt\\s*lở|lũ|bão|cuốn\\s*trôi|thiên\\s*tai))',
    '\\b(?:lao\\s*động\\s*chui|vượt\\s*biên|nhập\\s*cảnh\\s*trái\\s*phép|tổ\\s*chức\\s*đưa\\s*người|người\\s*rơm|container\\s*đông\\s*lạnh)(?!.*(?:cứu\\s*trợ|bão|lũ|sạt\\s*lở))\\b',
    '\\b(?:linh\\s*kiện\\s*máy\\s*tính|card\\s*đồ\\s*họa|r\\s*t\\s*x|g\\s*t\\s*x|r\\s*a\\s*m|s\\s*s\\s*d|ổ\\s*cứng\\s*di\\s*động|nguồn\\s*máy\\s*tính|tản\\s*nhiệt\\s*nước)\\b',
    '\\b(?:liên\\s*hoan\\s*phim|l\\s*h\\s*p|cannes|venice|berlin|bông\\s*sen\\s*vàng|cánh\\s*diều\\s*vàng|đạo\\s*diễn\\s*xuất\\s*sắc|biên\\s*kịch|vai\\s*diễn|sân\\s*khấu\\s*kịch|phim\\s*mưa\\s*đỏ|bộ\\s*phim)\\b',
    '\\b(?:liên\\s*hợp\\s*quốc|liên\\s*minh|hội\\s*đồng\\s*bảo\\s*an|nato|g7|g20|cop\\d+)(?!.*(?:hỗ\\s*trợ\\s*việt\\s*nam|bão|lũ|thiên\\s*tai\\s*tại\\s*việt\\s*nam|khẩn\\s*cấp))\\b',
    '\\b(?:liên\\s*kết\\s*vùng|tầm\\s*nhìn\\s*quy\\s*hoạch|động\\s*lực\\s*tăng\\s*trưởng|kinh\\s*tế\\s*số|chuyển\\s*đổi\\s*xanh|bền\\s*vững)\\b',
    '\\b(?:liệu\\s*pháp\\s*cbt|trị\\s*liệu\\s*tâm\\s*lý|tham\\s*vấn\\s*tâm\\s*thần|sang\\s*chấn|lo\\s*âu|rối\\s*loạn\\s*nhân\\s*cách|giải\\s*mã\\s*giấc\\s*mơ|tiềm\\s*thức)\\b',
    '\\b(?:liệu\\s*pháp\\s*âm\\s*thanh|aromatherapy|trị\\s*liệu\\s*mùi\\s*hương|nước\\s*hoa\\s*niche|tầng\\s*hương|độ\\s*lưu\\s*hương|tinh\\s*dầu\\s*thiên\\s*nhiên|thư\\s*giãn\\s*tâm\\s*hồn)\\b',
    '\\b(?:logistics\\s*ngược|kho\\s*thông\\s*minh|cảng\\s*cạn\\s*icd|hệ\\s*thống\\s*w\\s*m\\s*s|vận\\s*tải\\s*đa\\s*phương\\s*thức|chuỗi\\s*cung\\s*ứng\\s*bền\\s*vững|tối\\s*ưu\\s*chặng\\s*cuối)\\b',
    '\\b(?:loài\\s*chim|thế\\s*giới\\s*động\\s*vật|bảo\\s*tồn\\s*thiên\\s*nhiên|vườn\\s*thú|sở\\s*thú|cá\\s*thể|tê\\s*tê|động\\s*vật\\s*hoang\\s*dã|thả\\s*về\\s*rừng)\\b',
    '\\b(?:luyện\\s*thi\\s*ielts|toeic|toefl|ngữ\\s*pháp\\s*tiếng\\s*anh|học\\s*từ\\s*vựng|phương\\s*pháp\\s*ghi\\s*nhớ|du\\s*học\\s*sinh|trao\\s*đổi\\s*sinh\\s*viên)\\b',
    '\\b(?:luyện\\s*tập|hợp\\s*luyện|thao\\s*diễn|hội\\s*thao|diễn\\s*tập\\s*khu\\s*vực|bắn\\s*đạn\\s*thật)(?!\\s*(?:thực\\s*tế|trong\\s*mưa\\s*bão))\\b',
    '\\b(?:luật\\s*mới|luật\\s*sửa\\s*đổi|dự\\s*thảo\\s*luật|thông\\s*qua\\s*luật|hiệu\\s*lực\\s*thi\\s*hành)(?!.*(?:phòng\\s*chống\\s*thiên\\s*tai|đê\\s*điều|khẩn\\s*cấp))\\b',
    '\\b(?:luật\\s*đầu\\s*tư|luật\\s*việc\\s*làm|luật\\s*đất\\s*đai|luật\\s*kinh\\s*doanh|thủ\\s*tục\\s*hành\\s*chính|cải\\s*cách\\s*thể\\s*chế)\\b',
    '\\b(?:ly\\s*hôn\\s*thuận\\s*tình|phân\\s*chia\\s*tài\\s*sản\\s*chung|nhân\\s*thân|hộ\\s*khẩu)\\b',
    '\\b(?:làm\\s*bằng\\s*(?:đại\\s*học|cấp\\s*3)|chứng\\s*chỉ\\s*tiếng\\s*anh\\s*lấy\\s*ngay|bao\\s*đậu|giấy\\s*tờ\\s*giả)\\b',
    '\\b(?:làm\\s*chả\\s*quế|đặc\\s*sản\\s*làng\\s*nghề|thực\\s*phẩm\\s*chức\\s*năng|orihiro|hành\\s*trình\\s*(\\d+|năm)|chăm\\s*sóc\\s*sức\\s*khỏe\\s*(?:từ|của))\\b',
    '\\b(?:làm\\s*đẹp|skincare|mỹ\\s*phẩm|trắng\\s*da|giảm\\s*cân|tăng\\s*cân|thực\\s*phẩm\\s*chức\\s*năng|thăng\\s*hạng\\s*nhan\\s*sắc)\\b',
    '\\b(?:lá\\s*chắn|hệ\\s*thống)\\s*(?:tên\\s*lửa|phòng\\s*không|vòm\\s*sắt|tia\\s*sắt|laser)\\b',
    '\\b(?:lãi\\s*suất\\s*huy\\s*động|tiết\\s*kiệm\\s*tại\\s*quầy|app\\s*ngân\\s*hàng|quẹt\\s*thẻ|thanh\\s*toán\\s*không\\s*tiền\\s*mặt|voucher\\s*giảm\\s*giá)\\b',
    '\\b(?:lò\\s*cao|luyện\\s*kim|phôi\\s*thép|cán\\s*nóng|cán\\s*nguội|hợp\\s*kim\\s*đặc\\s*biệt|ngành\\s*công\\s*nghiệp\\s*nặng|khai\\s*thác\\s*khoáng\\s*sản)\\b',
    '\\b(?:lùm\\s*xùm|tranh\\s*cãi|tố\\s*cáo|bóc\\s*phốt)\\s*(?:kêu\\s*gọi|quyên\\s*góp|từ\\s*thiện|nghệ\\s*sĩ)\\b',
    '\\b(?:lăng\\s*mộ|nhà\\s*rường|hoàng\\s*thái\\s*hậu|cung\\s*đình|hoàng\\s*cung)\\b',
    '\\b(?:lăng\\s*tẩm|đền\\s*đài|cố\\s*đô|di\\s*tích\\s*quốc\\s*gia|khảo\\s*cổ\\s*học|dấu\\s*tích\\s*cổ|hiện\\s*vật|triều\\s*đại|vua\\s*chúa)\\b',
    '\\b(?:lương\\s*hưu|tăng\\s*lương|cải\\s*cách\\s*tiền\\s*lương|chế\\s*độ\\s*hưu\\s*trí|tuổi\\s*nghỉ\\s*hưu|điều\\s*chỉnh\\s*lương)\\b',
    '\\b(?:lương\\s*tháng\\s*13|thưởng\\s*năng\\s*suất|nội\\s*quy\\s*lao\\s*động|công\\s*đoàn\\s*cơ\\s*sở|khen\\s*thưởng\\s*định\\s*kỳ|phong\\s*trào\\s*lao\\s*động|thi\\s*đua\\s*ngành)\\b',
    '\\b(?:lấn\\s*chiếm\\s*lòng\\s*lề\\s*đường|trật\\s*tự\\s*đô\\s*thị|vỉ\\s*hè\\s*thông\\s*thoáng|vệ\\s*sinh\\s*môi\\s*trường\\s*khu\\s*phố|tổ\\s*tự\\s*quản|camera\\s*an\\s*ninh\\s*phường)\\b',
    '\\b(?:lấy\\s*ý\\s*kiến\\s*dự\\s*thảo|nghị\\s*định\\s*hướng\\s*dẫn|thông\\s*tư\\s*liên\\s*tịch|hđnd\\s*các\\s*cấp|công\\s*tác\\s*pháp\\s*chế|tuyên\\s*truyền\\s*pháp\\s*luật)\\b',
    '\\b(?:lấy\\s*ý\\s*kiến\\s*nhân\\s*dân|tiếp\\s*xúc\\s*cử\\s*tri|báo\\s*cáo\\s*chính\\s*trị|nghị\\s*quyết\\s*đại\\s*hội|quyết\\s*định\\s*ban\\s*hành|kế\\s*hoạch\\s*tuyên\\s*truyền)\\b',
    '\\b(?:lập\\s*vi\\s*bằng|niêm\\s*phong\\s*tài\\s*sản|kê\\s*biên\\s*phát\\s*mại|thông\\s*báo\\s*cưỡng\\s*chế|vi\\s*bằng\\s*ghi\\s*nhận)\\b',
    '\\b(?:lằn\\s*ranh\\s*tập|nguyệt\\s*mất\\s*tích|phim\\s*truyền\\s*hình\\s*tập|kết\\s*phim|nội\\s*dung\\s*tập)\\b',
    '\\b(?:lặn\\s*biển\\s*sâu|tàu\\s*ngầm\\s*thám\\s*hiểm|rãnh\\s*mariana|sinh\\s*vật\\s*biển\\s*lạ|thám\\s*hiểm\\s*đáy\\s*đại\\s*dương|khoa\\s*học\\s*đại\\s*dương)\\b',
    '\\b(?:lễ\\s*công\\s*bố|trao\\s*thưởng|giải\\s*báo\\s*chí|phát\\s*động\\s*cuộc\\s*thi)\\b',
    '\\b(?:lễ\\s*hội\\s*dân\\s*gian|hội\\s*làng|tín\\s*ngưỡng\\s*thờ\\s*cúng|không\\s*gian\\s*văn\\s*hóa|không\\s*gian\\s*đi\\s*bộ|nghệ\\s*thuật\\s*đường\\s*phố)\\b',
    '\\b(?:lễ\\s*tân\\s*gia|vàng\\s*cưới|phong\\s*bì\\s*mừng|lễ\\s*dạm\\s*ngõ|tiệc\\s*thôi\\s*nôi|đầy\\s*tháng|kỷ\\s*niệm\\s*ngày\\s*cưới|đội\\s*bê\\s*tráp)\\b',
    '\\b(?:lễ\\s*ăn\\s*hỏi|rước\\s*dâu|tiệc\\s*cưới|mừng\\s*thọ|lễ\\s*vu\\s*lan|phật\\s*đản|phục\\s*sinh|quà\\s*tặng\\s*ý\\s*nghĩa|lời\\s*chúc\\s*hay)\\b',
    '\\b(?:lệnh\\s*trừng\\s*phạt|cấm\\s*vận\\s*kinh\\s*tế|phong\\s*tỏa\\s*tài\\s*sản\\s*quốc\\s*tế|trừng\\s*phạt\\s*ngoại\\s*giao|trục\\s*xuất\\s*nhà\\s*ngoại\\s*giao|quan\\s*hệ\\s*song\\s*phương)\\b',
    '\\b(?:lịch\\s*sử\\s*kháng\\s*chiến|tội\\s*ác\\s*chiến\\s*tranh|di\\s*tích\\s*chiến\\s*trường|tìm\\s*kiếm\\s*đồng\\s*đội|huân\\s*chương\\s*chiến\\s*công)\\b',
    '\\b(?:lời\\s*bài\\s*hát|lyrics|hợp\\s*âm\\s*guitar|tab\\s*piano|phòng\\s*thu\\s*âm|kỹ\\s*thuật\\s*thanh\\s*nhạc|nhạc\\s*cụ\\s*chính\\s*hãng|vang\\s*số|loa\\s*kéo)\\b',
    '\\b(?:lụa\\s*nha\\s*xá|thổ\\s*cẩm\\s*mỹ\\s*nghiệp|chạm\\s*bạc\\s*đồng\\s*xâm|đá\\s*mỹ\\s*nghệ\\s*non\\s*nước|tinh\\s*hoa\\s*đất\\s*nghề)\\b',
    '\\b(?:lụa\\s*tơ\\s*tằm|thổ\\s*cẩm|dệt\\s*may\\s*xuất\\s*khẩu|sợi\\s*tự\\s*nhiên|ngành\\s*may\\s*mặc|thiết\\s*kế\\s*thời\\s*trang)\\b',
    '\\b(?:lục\\s*bình|rác\\s*thải|đổ\\s*trộm|ô\\s*nhiễm|bụi\\s*mù\\s*mịt)(?!\\s*(?:sau\\s*lũ|do\\s*bão))\\b',
    '\\b(?:lừa\\s*đảo\\s*chiếm\\s*đoạt|giả\\s*danh\\s*công\\s*an|lừa\\s*đảo\\s*qua\\s*mạng|tín\\s*dụng\\s*đen|cho\\s*vay\\s*lãi\\s*nặng|bảng\\s*giá\\s*đất)\\b',
    '\\b(?:lừa\\s*đảo\\s*chiếm\\s*đoạt|mã\\s*độc\\s*tấn\\s*công|phần\\s*mềm\\s*gián\\s*điệp|ransomware|truy\\s*cập\\s*trái\\s*phép|an\\s*toàn\\s*thông\\s*tin\\s*mạng|bảo\\s*mật\\s*đa\\s*lớp|xác\\s*thực\\s*hai\\s*yếu\\s*tố)\\b',
    '\\b(?:man\\s*city|chelsea|benfica|man\\s*utd|mu\\s*vs|liverpool|arsenal|barca|real\\s*madrid|tiền\\s*đạo|hậu\\s*vệ|thủ\\s*môn|hlv|huấn\\s*luyện\\s*viên|đội\\s*tuyển|u22|u23|u19|u17|đt\\s*việt\\s*nam|v-league|premier\\s*league|la\\s*liga|serie\\s*a|bundesliga|champions\\s*league|europa\\s*league|sea\\s*games|aff\\s*cup|asian\\s*cup|world\\s*cup|euro\\s*20\\d{2}|vòng\\s*loại|bảng\\s*xếp\\s*hạng|lịch\\s*thi\\s*đấu|trực\\s*tiếp\\s*bóng\\s*đá|nhận\\s*định\\s*bóng\\s*đá|soi\\s*kèo|marathon|giải\\s*chạy|điền\\s*kinh|đua\\s*xe|f1|bóng\\s*đá|thể\\s*thao|hội\\s*thi\\s*thể\\s*thao|giải\\s*đấu|tranh\\s*tài|vận\\s*động\\s*viên|huy\\s*chương|quần\\s*vợt|tennis|masters|grand\\s*slam|atp|wta|nhận\\s*định\\s*vs|vs\\s*|cagliari|pisa|girona|atletico|fulham|nottingham|estoril|alverca|mainz|st\\.\\s*pauli|lecce|como|aston\\s*villa)(?!.*(?:quyên\\s*góp|ủng\\s*hộ|từ\\s*thiện))\\b',
    "\\b(?:mcdonald's|kfc|lotteria|pizza\\s*hut|starbucks|highlands\\s*coffee|phúc\\s*long|trà\\s*sữa\\s*topping|thực\\s*đơn\\s*nhanh|món\\s*mới\\s*ra\\s*mắt)\\b",
    '\\b(?:miss\\s*global|hoa\\s*hậu\\s*hoàn\\s*vũ|vương\\s*miện\\s*danh\\s*giá|nhan\\s*sắc\\s*thăng\\s*hạng|catwalk|trình\\s*diễn\\s*bikini|phần\\s*thi\\s*ứng\\s*xử|người\\s*đẹp\\s*biển)\\b',
    '\\b(?:miss\\s*grand|miss\\s*universe|miss\\s*world|anh\\s*trai\\s*say\\s*hi|anh\\s*trai\\s*vượt\\s*ngàn\\s*chông\\s*gai|the\\s*mask\\s*singer|show\\s*thực\\s*tế)\\b',
    '\\b(?:mua\\s*bán\\s*người|buôn\\s*bán\\s*người|nạn\\s*nhân\\s*mua\\s*bán|lừa\\s*bán|việc\\s*nhẹ\\s*lương\\s*cao|nạn\\s*nhân\\s*bị\\s*lừa|giải\\s*cứu\\s*nạn\\s*nhân\\s*trafficking)\\b',
    '\\b(?:mua\\s*bán\\s*người|buôn\\s*người|di\\s*cư\\s*trái\\s*phép|nạn\\s*nhân\\s*mua\\s*bán|tội\\s*phạm\\s*mua\\s*bán|giải\\s*cứu\\s*nạn\\s*nhân\\s*mua\\s*bán|đường\\s*dây\\s*mua\\s*bán|môi\\s*giới\\s*hôn\\s*nhân|lấy\\s*chồng\\s*hàn|lấy\\s*chồng\\s*đài)\\b',
    '\\b(?:máy\\s*c\\s*n\\s*c|máy\\s*cắt\\s*laser|máy\\s*chấn|máy\\s*tiện|máy\\s*phay|dây\\s*chuyền\\s*tự\\s*động\\s*hóa|robot\\s*công\\s*nghiệp|vật\\s*liệu\\s*composit)\\b',
    '\\b(?:máy\\s*xúc\\s*đào|dung\\s*tích\\s*gầu|bán\\s*kính\\s*đào|hệ\\s*thống\\s*thủy\\s*lực|bảo\\s*trì\\s*máy\\s*móc|vật\\s*tư\\s*thi\\s*công|thiết\\s*bị\\s*công\\s*trình)\\b',
    '\\b(?:máy\\s*ảnh\\s*film|len\\s*mf|lens\\s*fix|ngàm\\s*chuyển|phụ\\s*kiện\\s*studio|đèn\\s*flash|chụp\\s*ảnh\\s*nghệ\\s*thuật|quay\\s*phim\\s*4k)\\b',
    '\\b(?:mã\\s*h\\s*s|chứng\\s*nhận\\s*xuất\\s*xu|c/o|tờ\\s*khai\\s*hải\\s*quan|thông\\s*quan\\s*hàng\\s*hóa|cước\\s*vận\\s*tải\\s*biển|tàu\\s*container|logistics\\s*chuyên\\s*dụng)\\b',
    '\\b(?:mã\\s*lỗi\\s*điều\\s*hòa|lỗi\\s*e\\s*1|lỗi\\s*e\\s*2|lỗi\\s*f\\s*5|bảng\\s*mã\\s*lỗi|sửa\\s*bình\\s*nóng\\s*lạnh\\s*tại\\s*nhà|thông\\s*tắc\\s*bể\\s*phốt\\s*giá\\s*rẻ)\\b',
    '\\b(?:mã\\s*vạch|qr\\s*code|tem\\s*truy\\s*xuất|hệ\\s*thống\\s*erp|phần\\s*mềm\\s*quản\\s*lý|số\\s*hóa\\s*doanh\\s*nghiệp)\\b',
    '\\b(?:món\\s*hời\\s*đầu\\s*tư|dòng\\s*vốn\\s*lớn|thị\\s*trường\\s*sôi\\s*động|chốt\\s*quyền\\s*nhận\\s*cổ\\s*tức|niêm\\s*yết\\s*sàn|ipo)\\b',
    '\\b(?:món\\s*hời|áp\\s*mã\\s*giảm\\s*giá|đổ\\s*xô\\s*mua\\s*sắm|tình\\s*trạng\\s*cháy\\s*hàng|vỡ\\s*trận\\s*vì\\s*khuyến\\s*mãi)\\b',
    '\\b(?:mô\\s*hình\\s*sinh\\s*kế|hỗ\\s*trợ\\s*sinh\\s*kế|chuyển\\s*đổi\\s*sinh\\s*kế|sinh\\s*kế\\s*bền\\s*vững)(?!.*(?:bão|lũ|thiên\\s*tai|khôi\\s*phục|phục\\s*hồi|hậu\\s*quả|vùng\\s*un|vùng\\s*ngập))\\b',
    '\\b(?:mại\\s*dâm|mua\\s*bán\\s*dâm|cà\\s*phê\\s*chòi|kích\\s*dục|massage\\s*kích\\s*dục|tú\\s*bà|chứa\\s*mại\\s*dâm)\\b',
    '\\b(?:mất\\s*mùa|được\\s*giá|mất\\s*giá|rớt\\s*giá|xuống\\s*giá|giá\\s*bán|thương\\s*lái|thu\\s*mua|nông\\s*dân\\s*khóc\\s*ròng|tiêu\\s*điều)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:mất\\s*trí\\s*nhớ|alzheimer|sa\\s*sút\\s*trí\\s*tuệ|thần\\s*kinh|tâm\\s*thần\\s*phân\\s*liệt|trầm\\s*cảm)(?!.*(?:bão|lũ))\\b',
    '\\b(?:mật\\s*ong\\s*rừng|rau\\s*sạch\\s*nhà\\s*trồng|nấm\\s*linh\\s*chi|nhân\\s*sâm|đông\\s*trùng\\s*hạ\\s*thảo|phòng\\s*tràn\\s*lan\\s*đột\\s*biến|cây\\s*cảnh\\s*giá\\s*trị)\\b',
    '\\b(?:mẹ\\s*chồng\\s*nàng\\s*dâu|tiểu\\s*tam|giật\\s*chồng|sống\\s*thử|ly\\s*hôn\\s*nghìn\\s*tỷ|tranh\\s*chấp\\s*quyền\\s*nuôi\\s*con|mâu\\s*thuẫn\\s*gia\\s*đình|ngoại\\s*tình\\s*bị\\s*phát\\s*hiện)\\b',
    '\\b(?:mẹo\\s*chăm\\s*sóc|bí\\s*quyết\\s*làm\\s*đẹp|tự\\s*nhiên\\s*tại\\s*nhà|cẩm\\s*nang\\s*sức\\s*khỏe|phương\\s*pháp\\s*khoa\\s*học|chế\\s*độ\\s*dinh\\s*dưỡng|bảo\\s*vệ\\s*sức\\s*khỏe|tư\\s*vấn\\s*sức\\s*khỏe|lưu\\s*ý\\s*sức\\s*khỏe|giữ\\s*ấm\\s*cơ\\s*thể|phòng\\s*bệnh\\s*mùa\\s*đông)(?!.*(?:vùng\\s*lũ|bão|thiên\\s*tai|cứu\\s*trợ|rét|lạnh|thời\\s*tiết|nắng\\s*nóng|ngập))\\b',
    '\\b(?:mẹo\\s*làm\\s*bánh|nấu\\s*ăn\\s*ngon|nồi\\s*chiên\\s*không\\s*dầu|máy\\s*ép\\s*chậm|đồ\\s*gia\\s*dụng\\s*thông\\s*minh|robot\\s*hút\\s*bụi|máy\\s*rửa\\s*bát)\\b',
    '\\b(?:mẹo\\s*vặt\\s*cuộc\\s*sống|cách\\s*chọn\\s*mua|review\\s*chân\\s*thực|kinh\\s*nghiệm\\s*chọn|top\\s*sản\\s*phẩm\\s*đáng\\s*mua|hướng\\s*dẫn\\s*chi\\s*tiết|bí\\s*quyết\\s*làm)\\b',
    '\\b(?:mời\\s*bạn\\s*xem\\s*thêm|tin\\s*liên\\s*quan|bài\\s*viết\\s*cùng\\s*chủ\\s*đề|xem\\s*thêm\\s*vụ\\s*việc|tin\\s*nóng\\s*trong\\s*ngày)\\b',
    '\\b(?:mở\\s*bán|căn\\s*hộ\\s*cao\\s*cấp|shophouse|liền\\s*kề|biệt\\s*thự\\s*song\\s*lập|không\\s*gian\\s*sống\\s*đẳng\\s*cấp|vị\\s*trí\\s*vàng|sinh\\s*lời\\s*cao|sổ\\s*đỏ\\s*trao\\s*tay|nhận\\s*nhà\\s*ngay|tiến\\s*độ\\s*thanh\\s*toán|hỗ\\s*trợ\\s*lãi\\s*suất|bất\\s*động\\s*sản\\s*nghỉ\\s*dưỡng)\\b',
    '\\b(?:mực\\s*một\\s*nắng|tôm\\s*hùm\\s*bình\\s*ba|cua\\s*cà\\s*mau|sò\\s*huyết\\s*ô\\s*loan|chả\\s*mực\\s*hạ\\s*long|đặc\\s*sản\\s*biển|đánh\\s*bắt\\s*xa\\s*bờ|hải\\s*sản\\s*tươi\\s*sống)\\b',
    '\\b(?:n\\s*b\\s*a|m\\s*l\\s*b|n\\s*f\\s*l|super\\s*bowl|grand\\s*slam|wimbledon|roland\\s*garros|u\\s*s\\s*open|australian\\s*open|giải\\s*quần\\s*vợt|bóng\\s*rổ\\s*nhà\\s*nghề)\\b',
    '\\b(?:nam\\s*sinh|nữ\\s*sinh|sinh\\s*viên|cụ\\s*bà|cụ\\s*ông).*(?:tử\\s*vong|thi\\s*thể|mất\\s*tích)(?!\\s*(?:do|vì|bởi)\\s*(?:mưa|lũ|bão|sạt|thiên\\s*tai))',
    '\\b(?:nghi\\s*lễ\\s*ngoại\\s*giao|quan\\s*hệ\\s*song\\s*phương|đón\\s*tiếp\\s*trọng\\s*thể|điện\\s*đàm|thư\\s*chúc\\s*mừng|quốc\\s*yến)\\b',
    '\\b(?:nghi\\s*thức\\s*ngoại\\s*giao|lễ\\s*đón|duyệt\\s*đội\\s*danh\\s*dự|tiễn\\s*đoàn|quan\\s*hệ\\s*đối\\s*tác|vun\\s*đắp\\s*tình\\s*hữu\\s*nghị)\\b',
    '\\b(?:nghiên\\s*cứu\\s*độc\\s*lập|kết\\s*quả\\s*khảo\\s*sát|số\\s*liệu\\s*thống\\s*kê|độ\\s*tin\\s*cậy|phương\\s*pháp\\s*nghiên\\s*cứu|phân\\s*tích\\s*dữ\\s*liệu)\\b',
    '\\b(?:nghĩa\\s*tình|nhẫn\\s*cưới|gia\\s*đình\\s*hạnh\\s*phúc|sinh\\s*kế\\s*phụ\\s*nữ|giảm\\s*nghèo\\s*bền\\s*vững|quà\\s*tết|tiết\\s*kiệm\\s*tại\\s*quầy)(?!.*(?:bão|lũ|thiên\\s*tai|tái\\s*thiết|khắc\\s*phục|hỗ\\s*trợ|ngập|sạt\\s*lở|nhà\\s*tình\\s*nghĩa|nhà\\s*đại\\s*đoàn\\s*kết))\\b',
    '\\b(?:nghĩa\\s*vụ\\s*quân\\s*sự|nghĩa\\s*vụ\\s*công\\s*an|tuyển\\s*quân|nhập\\s*ngũ|giao\\s*nhận\\s*quân|khám\\s*tuyển|công\\s*dân\\s*thực\\s*hiện\\s*nghĩa\\s*vụ|tuyển\\s*sinh\\s*công\\s*an|tuyển\\s*sinh\\s*quân\\s*đội|quân\\s*khu|bộ\\s*chỉ\\s*huy|ban\\s*chỉ\\s*huy|bộ\\s*tư\\s*lệnh)(?!.*(?:sơ\\s*tán|di\\s*dời|cứu\\s*hộ|cứu\\s*nạn|bão|lũ|ngập|thiên\\s*tai|khẩn\\s*cấp|hỗ\\s*trợ\\s*dân|giúp\\s*dân|tái\\s*thiết|làm\\s*nhà|hải\\s*văn|sóng\\s*lớn|biển\\s*động|gió\\s*mạnh))\\b',
    '\\b(?:nghĩa\\s*vụ\\s*quân\\s*sự|nhập\\s*ngũ|tuyển\\s*quân|giao\\s*nhận\\s*quân|lên\\s*đường\\s*nhập\\s*ngũ|khám\\s*tuyển|hội\\s*đồng\\s*nhân\\s*dân|tiếp\\s*xúc\\s*cử\\s*tri)\\b',
    '\\b(?:nghệ\\s*nhân\\s*ưu\\s*tú|nghệ\\s*nhân\\s*nhân\\s*dân|bảo\\s*tồn\\s*di\\s*sản|văn\\s*hóa\\s*phi\\s*vật\\s*thể|làng\\s*nghề\\s*truyền\\s*thống|sản\\s*phẩm\\s*ocop)\\b',
    '\\b(?:nghỉ\\s*hưu|lương\\s*hưu|trợ\\s*cấp\\s*xã\\s*hội|tinh\\s*giản\\s*biên\\s*chế|sắp\\s*xếp\\s*tổ\\s*chức|bảo\\s*hiểm\\s*xã\\s*hội|lương\\s*cơ\\s*bản|chính\\s*sách\\s*đối\\s*với)(?!.*(?:khắc\\s*phục|hỗ\\s*trợ\\s*bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:nghị\\s*quyết\\s*hđqt|biên\\s*bản\\s*họp|chương\\s*trình\\s*nghị\\s*sự|quy\\s*hoạch\\s*phân\\s*khu|điều\\s*chỉnh\\s*quy\\s*hoạch|chủ\\s*trương\\s*đầu\\s*tư|thẩm\\s*định\\s*giá\\s*tài\\s*sản|nghĩa\\s*vụ\\s*thuế)\\b',
    '\\b(?:nghị\\s*quyết\\s*phát\\s*triển|định\\s*hướng\\s*tầm\\s*nhìn|ưu\\s*tiên\\s*đầu\\s*tư|hạ\\s*tầng\\s*kỹ\\s*thuật|đồng\\s*bộ\\s*hiện\\s*đại)\\b',
    '\\b(?:ngành\\s*công\\s*nghiệp\\s*f&b|xu\\s*hướng\\s*tiêu\\s*dùng|chuỗi\\s*cung\\s*ứng\\s*toàn\\s*cầu|chi\\s*phí\\s*vận\\s*hành|ký\\s*kết\\s*hợp\\s*tác)\\b',
    '\\b(?:ngày\\s*hội\\s*đại\\s*đoàn\\s*kết|hội\\s*thảo\\s*khoa\\s*học|diễn\\s*đàn\\s*trẻ\\s*em|đại\\s*hội\\s*hội\\s*khuyến\\s*học|clb\\s*hưu\\s*trí|sinh\\s*hoạt\\s*hè)\\b',
    '\\b(?:ngã\\s*vào\\s*gầm|cuốn\\s*vào\\s*gầm|kẹt\\s*trong\\s*cabin|cá\\s*ăn\\s*thịt|đuối\\s*nước\\s*thương\\s*tâm|tắm\\s*sông|tắm\\s*biển|rơi\\s*xuống\\s*sông)(?!.*(?:bão|lũ|lụt|mưa\\s*lớn|nước\\s*dâng|sạt\\s*lở))\\b',
    '\\b(?:ngã\\s*vào\\s*gầm|cuốn\\s*vào\\s*gầm|kẹt\\s*trong\\s*cabin|cá\\s*ăn\\s*thịt|đuối\\s*nước\\s*thương\\s*tâm|tắm\\s*sông|tắm\\s*biển|rơi\\s*xuống\\s*sông)(?!.*(?:bão|lũ|lụt|mưa\\s*lớn|nước\\s*dâng|sạt\\s*lở|lũ\\s*quét))',
    '\\b(?:ngư\\s*trường\\s*khai\\s*thác|xuất\\s*khẩu\\s*hải\\s*sản|vận\\s*tải\\s*biển|cảng\\s*nước\\s*sâu|luồng\\s*hàng\\s*hải|tàu\\s*viễn\\s*dương|giàn\\s*khoan\\s*dầu|dầu\\s*khí\\s*quốc\\s*gia)\\b',
    '\\b(?:người\\s*chết|thi\\s*thể|tử\\s*vong)\\s*(?:bất\\s*thường|trong\\s*nhà|nhà\\s*nghỉ|quán|cháy)\\b',
    '\\b(?:người\\s*nộp\\s*thuế|cơ\\s*quan\\s*thuế|quyết\\s*toán\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử|chống\\s*thất\\s*thu|nợ\\s*thuế|hoàn\\s*thuế|thuế\\s*khoán|hộ\\s*kinh\\s*doanh)\\b',
    '\\b(?:ngồi|đứng|nằm|chụp\\s*ảnh|check-in)\\s*(?:trên|tại|giữa)\\s*đường\\s*ray',
    '\\b(?:ngộ\\s*độc\\s*thực\\s*phẩm|bánh\\s*mì|bếp\\s*ăn\\s*tập\\s*thể|suất\\s*ăn|an\\s*toàn\\s*thực\\s*phẩm|vệ\\s*sinh\\s*thực\\s*phẩm|dịch\\s*bệnh|sốt\\s*xuất\\s*huyết|bệnh\\s*lao|sa\\s*mạc\\s*hóa)(?!.*(?:do|vì|bởi|sau)\\s*(?:bão|lũ|thiên\\s*tai|mưa|ngập))\\b',
    '\\b(?:nha\\s*cai|da\\s*ga|bong\\s*da|tai\\s*xiu|xoc\\s*dia|lo\\s*de|soi\\s*keo|nhan\\s*dinh|truc\\s*tiep|ket\\s*qua|xo\\s*so|khuyen\\s*mai|nap\\s*dau|hoan\\s*tra|ty\\s*le|keo\\s*nha\\s*cai|huawei\\s*store|aptoide|uptodown)\\b',
    '\\b(?:nha\\s*khoa|răng\\s*hàm\\s*mặt|niềng\\s*răng|trồng\\s*răng|bọc\\s*răng|tẩy\\s*trắng)\\b',
    '\\b(?:nhà\\s*đinh|nhà\\s*tiền\\s*lê|nhà\\s*lý|nhà\\s*trần|nhà\\s*hồ|nhà\\s*mạc|nhà\\s*tây\\s*sơn|nhà\\s*nguyễn|chế\\s*độ\\s*phong\\s*kiến|chiều\\s*đại\\s*lịch\\s*sử)\\b',
    '\\b(?:nhà\\s*ở\\s*xã\\s*hội|mua\\s*nhà|bất\\s*động\\s*sản|thị\\s*trường\\s*nhà\\s*đất|sổ\\s*hồng|phát\\s*hành\\s*tiền|tiền\\s*kỹ\\s*thuật\\s*số|ngân\\s*hàng\\s*trung\\s*ương)\\b',
    '\\b(?:nhà\\s*ở\\s*xã\\s*hội|mua\\s*nhà|bất\\s*động\\s*sản|thị\\s*trường\\s*nhà\\s*đất|sổ\\s*hồng|phát\\s*hành\\s*tiền|tiền\\s*kỹ\\s*thuật\\s*số|ngân\\s*hàng\\s*trung\\s*ương|izumi\\s*city|căn\\s*hộ|mở\\s*bán|khu\\s*đô\\s*thị|quy\\s*hoạch\\s*không\\s*gian|đô\\s*thị\\s*văn\\s*minh)(?!.*(?:ngập|sạt\\s*lở|hư\\s*hỏng|bão|lũ))\\b',
    '\\b(?:nhìn\\s*lại|tổng\\s*kết|toàn\\s*cảnh|dấu\\s*ấn|tiêu\\s*điểm)\\s*(?:thế\\s*giới|năm\\s*20\\d{2}|kinh\\s*tế|thị\\s*trường|quốc\\s*tế)\\b',
    '\\b(?:nhạc\\s*trẻ|k-pop|v-pop|show\\s*diễn|lưu\\s*diễn\\s*quốc\\s*tế|world\\s*tour|lightstick|comeback\\s*ấn\\s*tượng|debut\\s*thành\\s*công|bảng\\s*xếp\\s*hạng\\s*âm\\s*nhạc)\\b',
    '\\b(?:nhảy\\s*cầu|treo\\s*cổ|tự\\s*thiêu|rơi\\s*lầu|rơi\\s*chung\\s*cư|ngã\\s*từ\\s*tầng)(?!.*(?:sập|đổ|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:nhận\\s*con\\s*nuôi|cha\\s*mẹ\\s*nuôi|thủ\\s*tục\\s*nhận\\s*nuôi|quyền\\s*và\\s*nghĩa\\s*vụ|xác\\s*nhận\\s*nuôi\\s*dưỡng|đăng\\s*ký\\s*nuôi\\s*con\\s*nuôi|pháp\\s*luật\\s*hôn\\s*nhân)\\b',
    '\\b(?:nhập\\s*cư|thẻ\\s*xanh|visa|thị\\s*thực|hồ\\s*sơ\\s*xin|lãnh\\s*sự\\s*quán|đại\\s*sứ\\s*quán)(?!.*(?:cứu\\s*trợ|bão|lũ|sơ\\s*tán|người\\s*việt))\\b',
    '\\b(?:nhập\\s*quốc\\s*tịch|thôi\\s*quốc\\s*tịch|việt\\s*kiều|thị\\s*thực\\s*điện\\s*tử|e-visa|hộ\\s*chiếu\\s*phổ\\s*thông|người\\s*nước\\s*ngoài\\s*tại\\s*việt\\s*nam|định\\s*cư)\\b',
    '\\b(?:nhặt\\s*được\\s*tiền|trả\\s*lại\\s*người\\s*đánh\\s*rơi|pháo\\s*hoa|pháo\\s*nổ|tự\\s*chế\\s*pháo|thuốc\\s*nổ|vật\\s*liệu\\s*nổ)(?!.*(?:lũ|bão|trôi|sạt|thiên\\s*tai|mưa\\s*lũ|cuốn\\s*trôi|vùi\\s*lấp))\\b',
    '\\b(?:nhịn\\s*ăn\\s*gián\\s*đoạn|chế\\s*độ\\s*ăn\\s*keto|thực\\s*phẩm\\s*bảo\\s*vệ\\s*sức\\s*khỏe|vi\\s*chất\\s*dinh\\s*dưỡng|eo\\s*thon\\s*dáng\\s*đẹp)\\b',
    '\\b(?:nhồi\\s*máu\\s*cơ\\s*tim|đột\\s*quỵ|tai\\s*biến|dấu\\s*hiệu\\s*cảnh\\s*báo|triệu\\s*chứng\\s*bệnh|căn\\s*bệnh|bác\\s*sĩ\\s*khuyến\\s*cáo|tư\\s*vấn\\s*tâm\\s*lý|sức\\s*khỏe\\s*tâm\\s*thần|đuối\\s*nước\\s*khi\\s*tắm|tắm\\s*biển|tắm\\s*sông|ao\\s*nhà|bể\\s*bơi|hồ\\s*bơi|đá\\s*bóng|đá\\s*banh|vận\\s*động\\s*viên|bác\\s*sĩ\\s*tư\\s*vấn|chăm\\s*sóc\\s*sức\\s*khỏe|tuyệt\\s*thực|bỏ\\s*đói|ung\\s*thư|thalassemia|vô\\s*sinh)(?!.*(?:bão|lũ|ngập|sạt|thiên\\s*tai|tai\\s*nạn))\\b',
    '\\b(?:niềm\\s*tin\\s*và\\s*khát\\s*vọng|góc\\s*nhìn\\s*thời\\s*đại|nhịp\\s*đập\\s*kinh\\s*tế|thế\\s*giới\\s*đó\\s*đây|chuyện\\s*của\\s*sao|bật\\s*mí\\s*bí\\s*mật|cận\\s*cảnh\\s*quy\\s*trình|khám\\s*phá\\s*thực\\s*tế)\\b',
    '\\b(?:noel|giáng\\s*sinh|check-in|phố\\s*đi\\s*bộ|ẩm\\s*thực|món\\s*ngon|nhà\\s*hàng|quán\\s*ăn|đầu\\s*bếp)(?!\\s*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ))\\b',
    '\\b(?:noel|giáng\\s*sinh|tết\\s*dương\\s*lịch|năm\\s*mới|chúc\\s*mừng|quà\\s*tặng|khuyến\\s*mãi|du\\s*xuân|đón\\s*xuân|vui\\s*xuân|chơi\\s*xuân|xuân\\s*về|chợ\\s*xuân|mùa\\s*xuân|cây\\s*cảnh|chơi\\s*tết|bính\\s*ngọ|mai\\s*vàng|đào\\s*phai|quất\\s*cảnh|lăng\\s*ông|cúng|thắp\\s*hương|trẩy\\s*hội|bưởi\\s*diễn|đặc\\s*sản|phố\\s*đêm|hoa\\s*hậu|người\\s*mẫu)(?!.*(?:bão|lũ|mưa|thời\\s*tiết|lạnh|rét|tuyết|rốn\\s*lũ|tái\\s*thiết|hồi\\s*sinh|khắc\\s*phục|vạn\\s*xuân))\\b',
    '\\b(?:noel|giáng\\s*sinh|tết\\s*dương\\s*lịch|năm\\s*mới|chúc\\s*mừng|quà\\s*tặng|khuyến\\s*mãi|du\\s*xuân|đón\\s*xuân|vui\\s*xuân|chơi\\s*xuân|xuân\\s*về|chợ\\s*xuân|mùa\\s*xuân|cây\\s*cảnh|chơi\\s*tết|mai\\s*vàng|đào\\s*phai|quất\\\\s*cảnh|thắp\\s*hương|trẩy\\s*hội|đặc\\s*sản|phố\\s*đêm)(?!.*(?:bão|lũ|mưa|thời\\s*tiết|lạnh|rét|tuyết|rốn\\s*lũ|tái\\s*thiết|hồi\\s*sinh|khắc\\s*phục))',
    '\\b(?:noel|giáng\\s*sinh|tết\\s*dương\\s*lịch|năm\\s*mới|chúc\\s*mừng|quà\\s*tặng|khuyến\\s*mãi|giảm\\s*giá|ưu\\s*đãi|khai\\s*trương)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|rink|ngập))\\b',
    '\\b(?:nuôi\\s*dạy\\s*con|sữa\\s*mẹ|ăn\\s*dặm|phát\\s*triển\\s*trí\\s*não|đồ\\s*chơi\\s*trẻ\\s*em|mẹ\\s*bầu|thai\\s*nhi|mầm\\s*non)\\b',
    '\\b(?:nâng\\s*cao\\s*chất\\s*lượng|đổi\\s*mới\\s*toàn\\s*diện|phát\\s*triển\\s*bền\\s*vững|nguồn\\s*nhân\\s*lực\\s*chất\\s*lượng\\s*cao|kinh\\s*tế\\s*tri\\s*thức|công\\s*nghiệp\\s*4.0)\\b',
    '\\b(?:nâng\\s*cao\\s*hiệu\\s*lực|hiệu\\s*quả\\s*quản\\s*lý|siết\\s*chặt\\s*kỷ\\s*luật|tăng\\s*cường\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*sai\\s*phạm)\\b',
    '\\b(?:nâng\\s*cao\\s*hiệu\\s*quả|công\\s*nghệ\\s*tiên\\s*tiến|giải\\s*pháp\\s*toàn\\s*diện|đối\\s*tác\\s*tin\\s*cậy)\\b',
    '\\b(?:nâng\\s*cao\\s*trình\\s*độ|đào\\s*tạo\\s*chuyên\\s*sâu|kỹ\\s*năng\\s*thời\\s*đại\\s*số)\\b',
    '\\b(?:nâng\\s*lương|tăng\\s*lương|chuyển\\s*ngạch|xét\\s*tuyển|viên\\s*chức|công\\s*chức|thăng\\s*hạng|chức\\s*danh\\s*nghề\\s*nghiệp)\\b',
    '\\b(?:nâng\\s*tầm\\s*vị\\s*thế|khẳng\\s*định\\s*thương\\s*hiệu|vươn\\s*tầm\\s*thế\\s*giới|ghi\\s*danh\\s*bản\\s*đồ|kết\\s*nối\\s*toàn\\s*cầu)\\b',
    '\\b(?:nông\\s*thôn\\s*mới|quy\\s*hoạch\\s*đô\\s*thị|vành\\s*đai\\s*\\d+|cao\\s*tốc|khởi\\s*công|thông\\s*xe|nghiệm\\s*thu|đấu\\s*giá\\s*đất|sổ\\s*đỏ|quyền\\s*sử\\s*dụng\\s*đất|giao\\s*đất|chuyển\\s*nhượng|xuất\\s*quân|lễ\\s*ra\\s*quân|hội\\s*thi|tuyên\\s*truyền|tập\\s*huấn|nhà\\s*đại\\s*đoàn\\s*kết|nhà\\s*tình\\s*nghĩa|nhà\\s*tình\\s*thương|nhà\\s*nhân\\s*ái|khai\\s*trương|ra\\s*mắt)(?!.*(?:gặp\\s*nạn|tai\\s*nạn|lật|chết|tử\\s*vong|thương\\s*vong|mất\\s*tích|cứu\\s*hộ|ứng\\s*phó|phòng\\s*chống|cứu\\s*trợ|hỗ\\s*trợ|sơ\\s*tán|khắc\\s*phục|sự\\s*cố|hư\\s*hỏng|bão|lũ))\\b',
    '\\b(?:nút\\s*giao\\s*thông|cầu\\s*vượt\\s*thép|hầm\\s*chui|dải\\s*phân\\s*cách|lát\\s*vỉ\\s*hè|chỉnh\\s*trang\\s*hàng\\s*rào|cáp\\s*quang\\s*biển|băng\\s*thông|trạm\\s*biến\\s*áp\\s*áp\\s*cao)\\b',
    '\\b(?:năng\\s*lượng\\s*nhiệt\\s*hạch|fusion\\s*energy|du\\s*lịch\\s*vũ\\s*trụ|virgin\\s*galactic|thám\\s*hiểm\\s*sao\\s*hỏa|định\\s*cư\\s*vũ\\s*trụ)\\b',
    '\\b(?:nạo\\s*vét|khơi\\s*thông|vệ\\s*sinh).*(?:kênh\\s*mương|cống\\s*rãnh|dòng\\s*chảy|rác\\s*thải)\\b',
    '\\b(?:nắng\\s*đẹp|thời\\s*tiết\\s*thuận\\s*lợi|nắng\\s*ấm|gió\\s*nhẹ|mây\\s*rải\\s*rác|không\\s*mưa|nắng\\s*chan\\s*hòa|bình\\s*minh|hoàng\\s*hôn)\\b',
    '\\b(?:nổi\\s*lềnh\\s*bềnh|thi\\s*thể\\s*(?:nam|nữ|thanh\\s*niên)|nhảy\\s*cầu|chết\\s*đuối\\s*khi\\s*tắm|đuối\\s*nước\\s*khi\\s*tắm|tự\\s*tử|quyên\\s*sinh|nhảy\\s*lầu|uống\\s*thuốc\\s*sâu|treo\\s*cổ|đánh\\s*ghen|bạo\\s*lực\\s*học\\s*đường|xô\\s*xát|cãi\\s*vã)\\b',
    '\\b(?:oecd|brics|asml|t\\s*s\\s*m\\s*c|nvidia|apple\\s*intelligence|openai|chatgpt|mô\\s*hình\\s*ngôn\\s*ngữ\\s*lớn|l\\s*l\\s*m)\\b',
    '\\b(?:olight|ostation|sony|playstation|steam|iphone|samsung|oppo|xiaomi|khôi\\s*phục\\s*cài\\s*đặt|bằng\\s*sáng\\s*chế|ai\\s*ghost|npc|game\\s*thủ)\\b',
    '\\b(?:olympic|asiad|paragames|đại\\s*hội\\s*thể\\s*thao|huấn\\s*luyện\\s*viên\\s*trưởng|đội\\s*tuyển\\s*quốc\\s*gia|liên\\s*đoàn\\s*bóng\\s*đá|v\\s*f\\s*f)\\b',
    '\\b(?:oppo|iphone|samsung|xiaomi|smartphone|laptop|tablet|công\\s*nghệ\\s*số|chuyển\\s*đổi\\s*số|nền\\s*tảng\\s*số|dịch\\s*vụ\\s*số|chatgpt|gemini|ai\\s*vision|trí\\s*tuệ\\s*nhân\\s*tạo|ios|android|windows|macos|linux|phần\\s*mềm|ứng\\s*dụng|app\\s*store|ch\\s*play|google\\s*play|bảo\\s*mật|an\\s*ninh\\s*mạng|hacker|tấn\\s*công\\s*mạng|lừa\\s*đảo\\s*trực\\s*tuyến|mã\\s*độc|virus\\s*máy\\s*tính|asus|rtx|oled|màn\\s*hình|notepad|virtual|workspaces|lenovo|yoga|tab)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn))\\b',
    '\\b(?:phim\\s*truyện|chiếu\\s*phim|điện\\s*ảnh|liên\\s*hoan\\s*phim|tác\\s*phẩm\\s*nghệ\\s*thuật|triển\\s*lãm\\s*ảnh|ra\\s*mắt\\s*phim)\\b',
    '\\b(?:phong\\s*cách\\s*thời\\s*trang|mốt\\s*mới\\s*nhất|phối\\s*đồ|mix\\s*đồ|phụ\\s*kiện\\s*đi\\s*kèm|lookbook|sưu\\s*tập\\s*mùa\\s*hè|trình\\s*diễn\\s*thời\\s*trang|tuần\\s*lễ\\s*thời\\s*trang)\\b',
    '\\b(?:phong\\s*trào\\s*thể\\s*thao|giải\\s*chạy\\s*marathon|phong\\s*trào\\s*cơ\\s*sở|nâng\\s*cao\\s*sức\\s*khỏe|vận\\s*động\\s*toàn\\s*dân)\\b',
    '\\b(?:phá\\s*sản\\s*doanh\\s*nghiệp|giải\\s*thế|mở\\s*thủ\\s*tục\\s*phá\\s*sản|quản\\s*tài\\s*viên|danh\\s*sách\\s*chủ\\s*nợ|tuyên\\s*bố\\s*phá\\s*sản|nợ\\s*quá\\s*hạn)\\b',
    '\\b(?:phát\\s*hiện\\s*thi\\s*thể|xác\\s*chết|người\\s*đàn\\s*ông\\s*tử\\s*vong|án\\s*mạng|trọng\\s*án|truy\\s*nã|bắt\\s*giữ|ma\\s*túy|buôn\\s*lậu|vượt\\s*biên|đánh\\s*bạc|mại\\s*dâm|cướp\\s*giật|trộm\\s*cắp|đâm\\s*chém|hỗn\\s*chiến|vây\\s*ráp|nẹt\\s*pô|lạng\\s*lách|đua\\s*xe|quái\\s*xế|bốc\\s*đầu|cầm\\s*dao|đâm\\s*chết|truy\\s*sát|xả\\s*súng|mua\\s*bán\\s*người|đầu\\s*thú)\\b',
    '\\b(?:phát\\s*huy\\s*vai\\s*trò|nêu\\s*gương|điển\\s*hình|khen\\s*thưởng|thi\\s*đua|thành\\s*tích|gương\\s*sáng|học\\s*tập\\s*và\\s*làm\\s*theo)(?!.*(?:cứu\\s*dân|cứu\\s*nạn|cứu\\s*người|dũng\\s*cảm|quên\\s*mình|hy\\s*sinh|lũ\\s*dữ|thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:phát\\s*triển\\s*bứt\\s*phá|tạo\\s*đà\\s*tăng\\s*trưởng|kịch\\s*bản\\s*tăng\\s*trưởng|mục\\s*tiêu\\s*tăng\\s*trưởng|nền\\s*tảng\\s*số)(?!.*(?:bão|lũ|khắc\\s*phục|phòng\\s*chống))\\b',
    '\\b(?:phát\\s*triển\\s*nguồn\\s*nhân\\s*lực|đào\\s*tạo\\s*kỹ\\s*năng|chứng\\s*chỉ\\s*nghề|giải\\s*quyết\\s*việc\\s*làm|an\\s*sinh\\s*xã\\s*hội|chính\\s*sách\\s*ưu\\s*đãi)\\b',
    '\\b(?:phát\\s*trực\\s*tiếp|kol|koc|người\\s*có\\s*sức\\s*ảnh\\s*hưởng|viral\\s*clip|drama\\s*mới|bóc\\s*phốt|hóng\\s*biến|đu\\s*trend|thử\\s*thách\\s*24h)\\b',
    '\\b(?:phân\\s*bón\\s*lá|kỹ\\s*thuật\\s*chiết\\s*cành|ghép\\s*mắt|cây\\s*ăn\\s*trái|vườn\\s*cây\\s*ăn\\s*quả|năng\\s*suất\\s*vụ\\s*mùa|phòng\\s*trừ\\s*sâu\\s*bệnh)\\b',
    '\\b(?:phân\\s*chia\\s*di\\s*sản|khai\\s*nhận\\s*thừa\\s*kế|hợp\\s*đồng\\s*tặng\\s*cho|quyền\\s*bề\\s*mặt|tài\\s*sản\\s*chung|phân\\s*chia\\s*hậu\\s*ly\\s*hôn|nghĩa\\s*vụ\\s*cấp\\s*dưỡng)\\b',
    '\\b(?:phân\\s*tích\\s*kỹ\\s*thuật|ngưỡng\\s*kháng\\s*cự|hỗ\\s*trợ\\s*mạnh|mô\\s*hình\\s*nến|chỉ\\s*số\\s*rsi|etf|chứng\\s*quyền|trái\\s*phiếu\\s*chính\\s*phủ)\\b',
    '\\b(?:phê\\s*bình\\s*sách|tác\\s*giả\\s*trẻ|triển\\s*lãm\\s*tranh|hội\\s*họa|điêu\\s*khắc|giai\\s*thoại\\s*lịch\\s*sử|nhân\\s*vật\\s*lịch\\s*sử|thơ\\s*ca|quân\\s*địch|nghi\\s*binh|chiến\\s*tranh|kháng\\s*chiến|đánh\\s*thắng|giải\\s*phóng\\s*miền\\s*nam|quân\\s*ta|quân\\s*ngụy)\\b',
    '\\b(?:phê\\s*duyệt\\s*quy\\s*hoạch|nguồn\\s*vốn\\s*o\\s*d\\s*a|giải\\s*ngân\\s*vốn\\s*đầu\\s*tư|tiến\\s*độ\\s*dự\\s*án|tổng\\s*mức\\s*đầu\\s*tư)\\b',
    '\\b(?:phí\\s*dịch\\s*vụ\\s*chung\\s*cư|ban\\s*quản\\s*trị\\s*nhà|họp\\s*dân\\s*cư|quy\\s*chế\\s*phát\\s*ngôn|thủ\\s*tục\\s*hành\\s*chính\\s*công|một\\s*cửa\\s*liên\\s*thông)\\b',
    '\\b(?:phí\\s*quản\\s*lý\\s*vận\\s*hành|bảo\\s*trì\\s*thang\\s*máy|hệ\\s*thống\\s*chiếu\\s*sáng|xử\\s*lý\\s*nước\\s*thải\\s*sinh\\s*hoạt|vệ\\s*sinh\\s*công\\s*nghiệp)\\b',
    '\\b(?:phòng\\s*thi|sức\\s*nóng\\s*mùa\\s*thi|sĩ\\s*tử|vượt\\s*vũ\\s*môn|đề\\s*thi|nộp\\s*hồ\\s*sơ|điểm\\s*chuẩn|nguyện\\s*vọng|tuyển\\s*sinh)\\b',
    '\\b(?:phòng\\s*thủ|tấn\\s*công)\\s*(?:tên\\s*lửa|uav|drone)\\b',
    '\\b(?:phạt\\s*nguội|nồng\\s*độ\\s*cồn|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|đăng\\s*kiểm|biển\\s*số)\\b',
    '\\b(?:phấn\\s*đấu\\s*hoàn\\s*thành|vượt\\s*kế\\s*hoạch|thi\\s*đua\\s*lập\\s*thành\\s*tích|chào\\s*mừng\\s*kỷ\\s*niệm|biểu\\s*dương\\s*khen\\s*thưởng|gương\\s*sáng)(?!.*(?:khắc\\s*phục|hậu\\s*quả|thiên\\s*tai|bão|lũ|sạt\\s*lở|cứu\\s*trợ))\\b',
    '\\b(?:phấn\\s*đấu\\s*đạt\\s*chuẩn|nông\\s*thôn\\s*mới\\s*nâng\\s*cao|gương\\s*sáng\\s*tiêu\\s*biểu)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|cứu\\s*người|lũ|bão|ngập|thiên\\s*tai))\\b',
    '\\b(?:phấn\\s*đấu|mục\\s*tiêu|kế\\s*hoạch)\\s*tăng\\s*trưởng\\b',
    '\\b(?:phần\\s*mềm\\s*kế\\s*toán|phần\\s*mềm\\s*nhân\\s*sự|quản\\s*lý\\s*kho\\s*hàng|tối\\s*ưu\\s*vận\\s*hành|giải\\s*pháp\\s*doanh\\s*nghiệp|năng\\s*suất\\s*vượt\\s*trội)\\b',
    '\\b(?:phẫu\\s*thuật\\s*thẩm\\s*mỹ|hút\\s*mỡ|nâng\\s*mũi|tiêm\\s*filler|căng\\s*chỉ|trị\\s*mụn|chăm\\s*sóc\\s*da|spa|thẩm\\s*mỹ\\s*viện)\\b',
    '\\b(?:phẫu\\s*thuật|ca\\s*mổ|bệnh\\s*lý|sản\\s*phụ|thai\\s*kỳ|tử\\s*cung|hiếm\\s*muộn|vô\\s*sinh|nội\\s*soi|ghép\\s*tạng|thẩm\\s*mỹ|cấy\\s*ghép|ghép\\s*gan|ghép\\s*tim|ghép\\s*thận|tai\\s*máy|trợ\\s*thính)\\b',
    '\\b(?:phẫu\\s*thuật|mổ|cấp\\s*cứu\\s*bệnh\\s*nhân|bệnh\\s*viện\\s*đa\\s*khoa|nguy\\s*kịch|vỡ\\s*tạng|chạy\\s*thận|đột\\s*quỵ|tai\\s*biến|cứu\\s*sống\\s*bệnh\\s*nhân|nhồi\\s*máu|ung\\s*thư|sỏi\\s*thận|ghép\\s*tạng|thông\\s*tim|can\\s*thiệp\\s*mạch|hồi\\s*sinh\\s*sự\\s*sống|y\\s*khoa)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|tai\\s*nạn\\s*thảm\\s*khốc|sập\\s*hầm|cháy\\s*lớn|giông\\s*bão|gặp\\s*nạn|đuối\\s*nước|ngập|mưa\\s*lũ))',
    '\\b(?:phẫu\\s*thuật|mổ|cấp\\s*cứu\\s*bệnh\\s*nhân|bệnh\\s*viện\\s*đa\\s*khoa|nguy\\s*kịch|vỡ\\s*tạng|vỡ\\s*tim|chạy\\s*thận|ecmo|lọc\\s*máu|đột\\s*quỵ|tai\\s*biến|cứu\\s*sống\\s*bệnh\\s*nhân|nhồi\\s*máu|ung\\s*thư|bàng\\s*quang|ruột\\s*thừa|sỏi\\s*thận|nhiễm\\s*nấm|ăn\\s*mòn\\s*xương|hiến\\s*tạng|ghép\\s*gan|ghép\\s*tim|thông\\s*tim|can\\s*thiệp\\s*mạch|hồi\\s*sinh\\s*sự\\s*sống|hỗ\\s*trợ\\s*chuyên\\s*môn|y\\s*khoa|tiểu\\s*ra\\s*máu|tập\\s*yoga)(?!.*(?:bão|lũ|sạt\\s*lở|thiên\\s*tai|tai\\s*nạn\\s*thảm\\s*khốc|sập\\s*hầm|cháy\\s*lớn|giông\\s*bão|gặp\\s*nạn|đuối\\s*nước|ngập|mưa\\s*lũ))\\b',
    '\\b(?:phụ\\s*gia\\s*thực\\s*phẩm|chất\\s*bảo\\s*quản|tiêu\\s*chuẩn\\s*vệ\\s*sinh\\s*kỹ\\s*thuật)\\b',
    '\\b(?:phụ\\s*nữ\\s*hiện\\s*đại|nam\\s*giới\\s*bản\\s*lĩnh|giữ\\s*lửa\\s*hạnh\\s*phúc|bí\\s*quyết\\s*gia\\s*đình|mối\\s*quan\\s*hệ\\s*bền\\s*chặt|tâm\\s*lý\\s*gia\\s*đình)\\b',
    '\\b(?:phủ\\s*xanh|trồng\\s*cây\\s*gây\\s*rừng|chăm\\s*sóc\\s*cây\\s*xanh|cắt\\s*tỉa\\s*cành\\s*cây)\\b',
    '\\b(?:poker|blackjack|roulette|baccarat|sicbo|keno|number\\s*game|kết\\s*quả\\s*xổ\\s*số|kqxs|quay\\s*số|trúng\\s*thưởng|vé\\s*số|đổi\\s*thưởng|nạp\\s*rút|uy\\s*tín|xanh\\s*chín|cổng\\s*game|bài\\s*đổi\\s*thưởng|chẵn\\s*lẻ|tài\\s*xỉu|xóc\\s*đĩa|lô\\s*đề|nổ\\s*hũ|bắn\\s*cá|đá\\s*gà|xí\\s*ngầu|cầu\\s*dây)\\b',
    '\\b(?:putin|tập\\s*cận\\s*bình|elon\\s*musk|mark\\s*zuckerberg|bill\\s*gates|jeff\\s*bezos|tỷ\\s*phú\\s*forbes|giàu\\s*nhất\\s*thế\\s*giới)\\b',
    '\\b(?:quy\\s*chế\\s*hoạt\\s*động|nội\\s*quy\\s*cơ\\s*quan|cải\\s*cách\\s*thủ\\s*tục|một\\s*cửa\\s*liên\\s*thông|hiện\\s*đại\\s*hóa\\s*hành\\s*chính| kỷ\\s*luật\\s*công\\s*vụ)\\b',
    '\\b(?:quy\\s*hoạch\\s*ngành\\s*du\\s*lịch|phát\\s*triển\\s*kinh\\s*tế\\s*biển|liên\\s*kết\\s*vùng\\s*kinh\\s*tế|huy\\s*động\\s*nguồn\\s*lực|xã\\s*hội\\s*hóa)\\b',
    '\\b(?:quy\\s*hoạch\\s*tổng\\s*thể\\s*quốc\\s*gia|vùng\\s*kinh\\s*tế\\s*trọng\\s*điểm|liên\\s*kết\\s*tiểu\\s*vùng|phân\\s*bổ\\s*nguồn\\s*lực|tầm\\s*nhìn\\s*phát\\s*triển)\\b',
    '\\b(?:quy\\s*hoạch|đề\\s*án|chủ\\s*trương|phê\\s*duyệt|nghiên\\s*cứu|đề\\s*xuất)\\s*(?:đường\\s*sắt|sân\\s*bay|cảng\\s*biển|cao\\s*tốc|metro|tàu\\s*điện)(?!.*(?:sạt\\s*lở|lũ|bão|ngập|thiên\\s*tai|hư\\s*hỏng|sự\\s*cố))\\b',
    '\\b(?:quy\\s*trình\\s*vận\\s*hành|ISO\\s*\\d+)\\b',
    '\\b(?:quy\\s*tắc\\s*phòng\\s*cháy|thiết\\s*bị\\s*cứu\\s*hỏa|chuông\\s*báo\\s*cháy|vòi\\s*phun\\s*tự\\s*động|thang\\s*thoát\\s*hiểm)\\b',
    '\\b(?:quy\\s*tắc\\s*đạo\\s*đức|hành\\s*vi\\s*ứng\\s*xử|văn\\s*hóa\\s*gia\\s*đình|giá\\s*trị\\s*cốt\\s*lõi|phẩm\\s*chất\\s*đạo\\s*đức|lối\\s*sống\\s*lành\\s*mạnh|thể\\s*dục\\s*thể\\s*thao)\\b',
    '\\b(?:quy\\s*định\\s*pháp\\s*luật)\\b',
    '\\b(?:quyết\\s*toán\\s*thuế|thuế\\s*thu\\s*nhập\\s*cá\\s*nhân|tncn|hoàn\\s*thuế\\s*gtgt|hóa\\s*đơn\\s*điện\\s*tử|kiểm\\s*toán\\s*nhà\\s*nước|vụ\\s*ngân\\s*sách|kế\\s*hoạch\\s*tài\\s*chính)\\b',
    '\\b(?:quyết\\s*định\\s*khởi\\s*tố|lệnh\\s*tạm\\s*giam|phiên\\s*phúc\\s*thẩm)\\b',
    '\\b(?:quán\\s*bar|pub|nhạc\\s*sống|phòng\\s*trà|vũ\\s*trường|karaoke|massage|bida)\\b',
    '\\b(?:quân\\s*đội\\s*nhân\\s*dân|cờ\\s*đảng|huy\\s*hiệu\\s*đảng|kỷ\\s*niệm\\s*.*năm.*thành\\s*lập|vang\\s*mãi|hào\\s*khí|chiến\\s*thắng|quân\\s*lệnh\\s*số)\\b',
    '\\b(?:quên\\s*mật\\s*khẩu|mã\\s*otp|lỗi\\s*chuyển\\s*tiền|hạn\\s*mức\\s*giao\\s*dịch|quản\\s*lý\\s*chi\\s*tiêu|thanh\\s*toán\\s*hóa\\s*đơn|liên\\s*kết\\s*ngân\\s*hàng)\\b',
    '\\b(?:quạt\\s*chàng\\s*sơn|giấy\\s*dó|tranh\\s*điệp|lụa\\s*vạn\\s*phúc|gốm\\s*bát\\s*tràng|di\\s*sản\\s*văn\\s*hóa\\s*phi\\s*vật\\s*thể)\\b',
    r"\b(?:quả\s*bóng\s*vàng|ballon\s*d'or|chiếc\s*giày\s*vàng|golden\s*boot|the\s*best|cầu\s*thủ(?:(?!\s*mất\s*tích|\s*gặp\s*nạn|\s*trong\s*lũ))|đội\s*hình\s*tiêu\s*biểu|quản\s*lý\s*thể\s*thao)\b",
    '\\b(?:quản\\s*lý\\s*thị\\s*trường|hàng\\s*giả\\s*hàng\\s*nhái|tiêu\\s*hủy\\s*tang\\s*vật|vi\\s*phạm\\s*nhãn\\s*hiệu|quản\\s*lý\\s*giá\\s*cả|bình\\s*ổn\\s*thị\\s*trường)\\b',
    '\\b(?:quảng\\s*cáo|facebook|sinh\\s*lời|marketing|livestream|bán\\s*hàng\\s*online|chốt\\s*đơn|doanh\\s*thu|lợi\\s*nhuận)(?!.*(?:bão|lũ|thiên\\s*tai|ủng\\s*hộ|cứu\\s*trợ))\\b',
    '\\b(?:quốc\\s*hội\\s*mỹ|hạ\\s*viện\\s*mỹ|thượng\\s*viện\\s*mỹ|tổng\\s*thống\\s*mỹ|bầu\\s*cử\\s*mỹ|nhà\\s*trắng|lầu\\s*năm\\s*góc)(?!\\s*(?:viện\\s*trợ|hỗ\\s*trợ)\\s*(?:bão|lũ|việt\\s*nam))\\b',
    '\\b(?:quỹ\\s*thiện\\s*tâm|quỹ\\s*hy\\s*vọng|quỹ\\s*vì\\s*người\\s*nghèo|chương\\s*trình\\s*tài\\s*trợ|tấm\\s*lòng\\s*vàng|trao\\s*tặng\\s*quà)(?!\\s*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở))\\b',
    '\\b(?:ra\\s*mắt\\s*iphone|samsung\\s*galaxy|macbook|ios\\s*(?:update|\\d+)|android\\s*\\d+|snapdragon|dimensity|xe\\s*điện\\s*vinfast|lãi\\s*suất\\s*kép|máy\\s*tính\\s*bảng|laptop|tai\\s*nghe\\s*bluetooth)\\b',
    '\\b(?:ra\\s*mắt\\s*sản\\s*phẩm|ra\\s*mắt\\s*(?:xe|điện\\s*thoại|máy|laptop|ốp|sạc|phiên\\s*bản)|công\\s*nghệ\\s*mới|trải\\s*nghiệm|mở\\s*hộp)\\b',
    '\\b(?:real\\s*madrid|man\\s*utd|manchester\\s*city|liverpool|arsenal|barca|bayern\\s*munich|psg|chuyển\\s*nhượng\\s*cầu\\s*thủ|hợp\\s*đồng\\s*bom\\s*tấn|champions\\s*league|premiere\\s*league|v-league|v\\s*league|ngoại\\s*hạng\\s*anh|league\\s*1|la\\s*liga|serie\\s*a|bundesliga|công\\s*phượng|quang\\s*hải|tiến\\s*linh|văn\\s*toàn|đội\\s*tuyển\\s*bóng\\s*đá)\\b',
    '\\b(?:resort\\s*5\\s*sao|biệt\\s*thự\\s*nghỉ\\s*dưỡng\\s*luxury|hạng\\s*thương\\s*gia|du\\s*thuyền\\s*triệu\\s*đô|trải\\s*nghiệm\\s*thượng\\s*lưu|dịch\\s*vụ\\s*chuẩn\\s*quốc\\s*tế)\\b',
    '\\b(?:review\\s*sản\\s*phẩm|đánh\\s*giá\\s*chi\\s*tiết|trên\\s*tay|mở\\s*hộp|unboxing|so\\s*sánh\\s*hiệu\\s*năng|trải\\s*nghiệm\\s*người\\s*dùng)\\b',
    '\\b(?:robot\\s*lau\\s*kính|hệ\\s*thống\\s*gondola|bảo\\s*trì\\s*mặt\\s*dựng|kiểm\\s*định\\s*thiết\\s*bị|quản\\s*lý\\s*tòa\\s*nhà)\\b',
    '\\b(?:rolex|patek\\s*philippe|audemars\\s*piguet|hublot|omega|thương\\s*hiệu\\s*đồng\\s*hồ|mặt\\s*số|bộ\\s*chuyển\\s*động|trữ\\s*cót|phiên\\s*bản\\s*giới\\s*hạn)\\b',
    '\\b(?:rule\\s*of|earning\\s*app|in\\s*chẵn\\s*lẻ|canon\\s*2900|baccarat\\s*live|vivu88|88\\s*clb|tặng\\s*bạn|ưu\\s*đãi\\s*tân\\s*thủ)\\b',
    '\\b(?:rác\\s*thải|nhựa|bao\\s*bì)(?!\\s*(?:ngập|ung\\s*ứ|sau\\s*bão|do\\s*lũ))\\b',
    '\\b(?:rượu\\s*mẫu\\s*sơn|rượu\\s*gò\\s*công|bia\\s*hơi\\s*hà\\s*nội|cà\\s*phê\\s*robusta|cà\\s*phê\\s*arabica|trà\\s*tà\\s*xùa|thương\\s*hiệu\\s*đồ\\s*uống|vùng\\s*nguyên\\s*liệu\\s*chè)\\b',
    '\\b(?:rạp\\s*cưới|đám\\s*cưới|đám\\s*hỏi|rước\\s*dâu)(?!\\s*(?:bị\\s*lũ|trong\\s*lũ|gặp\\s*nạn|cuốn\\s*trôi))\\b',
    '\\b(?:rầy\\s*nâu|sâu\\s*cuốn\\s*lá|ốc\\s*bươu\\s*vàng|bệnh\\s*đạo\\s*ôn|phun\\s*thuốc\\s*trừ\\s*sâu|bảo\\s*vệ\\s*mùa\\s*màng|an\\s*toàn\\s*sinh\\s*học)\\b',
    '\\b(?:sao\\s*vàng\\s*đất\\s*việt|hàng\\s*việt\\s*nam\\s*chất\\s*lượng\\s*cao|giải\\s*thưởng\\s*tạ\\s*quang\\s*bửu|giải\\s*vin\\s*future|giải\\s*thưởng\\s*nhà\\s*nước)\\b',
    '\\b(?:showbiz|vbiz|vpop|kpop|biz|drama|scandal|netizen|fandom|idol|livestream|streamer|youtuber|tiktoker|influencer|shopping\\s*online)\\b',
    '\\b(?:sinh\\s*hoạt\\s*chi\\s*bộ|tự\\s*soi\\s*tự\\s*sửa|phê\\s*bình|kiểm\\s*điểm|đảng\\s*viên|kỷ\\s*luật\\s*đảng|cán\\s*bộ\\s*đảng\\s*viên|tinh\\s*gọn\\s*bộ\\s*máy|sắp\\s*xếp\\s*tổ\\s*chức|công\\s*đoàn|đề\\s*án|kiện\\s*toàn|thanh\\s*tra|kết\\s*luận\\s*thanh\\s*tra|sai\\s*phạm|xử\\s*lý\\s*vi\\s*phạm|sắp\\s*xếp\\s*cơ\\s*quan|quy\\s*hoạch\\s*cán\\s*bộ|quản\\s*trị\\s*quốc\\s*gia|kỷ\\s*nguyên\\s*mới|đội\\s*ngũ\\s*cán\\s*bộ|người\\s*đứng\\s*đầu)\\b',
    '\\b(?:sinh\\s*non|bệnh\\s*hiểm\\s*nghèo|ung\\s*thư|thai\\s*phụ|sản\\s*phụ|hiếm\\s*muộn|vô\\s*sinh)(?!.*(?:do|vì|bởi|tại|sau)\\s*(?:thiên\\s*tai|bão|lũ|ngập|lụt|sạt|sét|nóng|hạn|động\\s*đất|sóng\\s*thần))\\b',
    '\\b(?:siêu\\s*sale|săn\\s*deal|áp\\s*mã|giảm\\s*sâu|mở\\s*bán\\s*ưu\\s*đãi|càn\\s*quét\\s*giỏ\\s*hàng|đổ\\s*bộ\\s*thị\\s*trường)\\b',
    '\\b(?:southampton|wolves|everton|nottingham|forest|leicester|fulham|brentford|bournemouth|crystal\\s*palace|brighton|aston\\s*villa|newcastle|west\\s*ham|tottenham|wales|ghana|senegal|ecuador|qatar|iran|saudi\\s*arabia|morocco|tunisia|c\\s*r\\s*7|ronaldo|messi|neymar|mbappe)\\b',
    '\\b(?:sp-[\\d\\w]+|mã\\s*giảm\\s*giá|voucher|coupon|deal\\s*sốc|săn\\s*sale|livestream\\s*bán\\s*hàng|tiktok\\s*shop|shopee\\s*live|lazada\\s*sale)\\b',
    '\\b(?:suy\\s*giảm\\s*thị\\s*lực|mờ\\s*mắt|nhãn\\s*khoa|thủy\\s*tinh\\s*thể|đục\\s*thủy\\s*tinh\\s*thể|mù\\s*lòa|cận\\s*thị|loạn\\s*thị)(?!.*(?:bão|lũ))\\b',
    '\\b(?:suy\\s*tim|nhồi\\s*máu|cơ\\s*tim|hở\\s*van\\s*tim|đặt\\s*stent|mạch\\s*vành|suy\\s*thận|chạy\\s*thận)(?!.*(?:bão|lũ|cứu\\s*trợ|sơ\\s*tán))\\b',
    '\\b(?:swift|l/c|tín\\s*dụng\\s*thư|nhờ\\s*thu\\s*chứng\\s*từ|thanh\\s*toán\\s*quốc\\s*tế|rửa\\s*tiền|trốn\\s*thuế|thiên\\s*đường\\s*thuế|kiểm\\s*toán\\s*độc\\s*lập)\\b',
    '\\b(?:sân\\s*bay|cảng\\s*hàng\\s*không).*(?:tạm\\s*đóng\\s*cửa|nâng\\s*cấp|sửa\\s*chữa|bảo\\s*trì)(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thời\\s*tiết|thiên\\s*tai))',
    '\\b(?:sóng\\s*gió)\\s*(?:cuộc\\s*đời|tình\\s*yêu|hôn\\s*nhân|gia\\s*tộc|thương\\s*trường|hậu\\s*trường)\\b',
    '\\b(?:sóng\\s*gió\\s*(?:cuộc\\s*đời|hý\\s*viện|showbiz|tình\\s*trường)|phong\\s*ba\\s*bão\\s*táp)\\b',
    '\\b(?:sóng\\s*hấp\\s*dẫn|năng\\s*lượng\\s*tối|lỗ\\s*sâu|cơ\\s*học\\s*lượng\\s*tử|vật\\s*lý\\s*hạt|gia\\s*tốc\\s*hạt)\\b',
    '\\b(?:súng\\s*in\\s*3d|chiêu\\s*trò\\s*lừa\\s*đảo|giả\\s*mạo\\s*tập\\s*đoàn|tuyển\\s*dụng\\s*việc\\s*làm|bóc\\s*trần\\s*thủ\\s*đoạn)\\b',
    '\\b(?:súng\\s*trường|pháo\\s*tự\\s*hành|xe\\s*thiết\\s*giáp|trực\\s*thăng\\s*vũ\\s*trang|tên\\s*lửa\\s*hành\\s*trình|tác\\s*chiến\\s*không\\s*gian|an\\s*ninh\\s*quốc\\s*phòng)(?!.*(?:cứu\\s*hộ|cứu\\s*nạn|giúp\\s*dân|vùng\\s*lũ|lũ\\s*lụt|cô\\s*lập|sơ\\s*tán))\\b',
    '\\b(?:sơn\\s*mài\\s*hạ\\s*thái|tạc\\s*tượng\\s*sơn\\s*đồng|mây\\s*tre\\s*đan\\s*phú\\s*vinh|nghệ\\s*nhân\\s*đúc\\s*đồng|triển\\s*lãm\\s*mỹ\\s*thuật)\\b',
    '\\b(?:sập\\s*giàn\\s*giáo|tai\\s*nạn\\s*lao\\s*động|ngộ\\s*độc\\s*thực\\s*phẩm|cháy\\s*nổ\\s*bình\\s*gas)\\b',
    '\\b(?:sắp\\s*xếp\\s*đơn\\s*vị\\s*hành\\s*chính|tổ\\s*chức\\s*lại|bộ\\s*máy|tập\\s*huấn|bồi\\s*dưỡng|nghiệp\\s*vụ|giải\\s*báo\\s*chí|thể\\s*lệ|cuộc\\s*thi|bầu\\s*cử|đại\\s*hội\\s*đảng|tạm\\s*dừng\\s*điều\\s*động|bổ\\s*nhiệm|miễn\\s*nhiệm|luân\\s*chuyển|kỷ\\s*luật|khai\\s*trừ)(?!\\s*(?:ứng\\s*phó|phòng\\s*chống|cứu\\s*hộ|cứu\\s*nạn|thiên\\s*tai|tìm\\s*kiếm|chó\\s*nghiệp\\s*vụ))\\b',
    '\\b(?:số\\s*hóa|chuyển\\s*đổi\\s*số|hệ\\s*sinh\\s*thái|khởi\\s*nghiệp\\s*sáng\\s*tạo|vón\\s*đầu\\s*tư|quỹ\\s*mạo\\s*hiểm)\\b',
    '\\b(?:sống\\s*khỏe\\s*mỗi\\s*ngày|góc\\s*tâm\\s*hồn|dành\\s*cho\\s*thiếu\\s*nhi|phụ\\s*nữ\\s*và\\s*gia\\s*đình|góc\\s*thư\\s*giãn|tâm\\s*sự\\s*thầm\\s*kín|hạnh\\s*phúc\\s*gia\\s*đình)\\b',
    '\\b(?:sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|dịch\\s*sởi|cúm\\s*gia\\s*cầm|đỉnh\\s*dịch|bùng\\s*phát\\s*dịch|phun\\s*hóa\\s*chất|diệt\\s*loăng\\s*quăng| não\\s*mô\\s*cầu)\\b',
    '\\b(?:sổ\\s*tay\\s*văn\\s*hóa|câu\\s*chuyện\\s*giáo\\s*dục|nhật\\s*ký\\s*người\\s*đi\\s*đường|văn\\s*hóa\\s*giao\\s*thông|ý\\s*thức\\s*công\\s*dân|rèn\\s*luyện\\s*nhân\\s*cách|giá\\s*trị\\s*sống)\\b',
    '\\b(?:sổ\\s*đỏ|giấy\\s*chứng\\s*nhận|bản\\s*đồ\\s*địa\\s*chính|tranh\\s*chấp\\s*đất|đền\\s*bù\\s*giải\\s*phóng|cấp\\s*sổ|đo\\s*đạc)(?!.*(?:sạt\\s*lở|tái\\s*định\\s*cư|vùng\\s*lũ|trôi))\\b',
    '\\b(?:sởi|rubella|thủy\\s*đậu|quai\\s*bị|tay\\s*chân\\s*miệng|sốt\\s*phát\\s*ban|cúm\\s*gia\\s*cầm|h5n1)(?!.*(?:bão|lũ|vùng\\s*lũ))\\b',
    '\\b(?:sức\\s*nâng\\s*tối\\s*đa|tầm\\s*với\\s*cần\\s*trực|cáp\\s*tải|puly|móc\\s*cẩu|tự\\s*trọng|thông\\s*số\\s*kỹ\\s*thuật\\s*máy|bảo\\s*trì\\s*định\\s*kỳ)\\b',
    '\\b(?:sửa\\s*bình\\s*nóng\\s*lạnh|chống\\s*thấm\\s*dột|sửa\\s*mái\\s*tôn|thông\\s*tắc\\s*cống|hút\\s*bể\\s*phốt|vệ\\s*sinh\\s*điều\\s*hòa|bảo\\s*dưỡng\\s*máy\\s*giặt|lắp\\s*mạng\\s*internet)\\b',
    '\\b(?:sửa\\s*chữa\\s*điện\\s*nước|thông\\s*tắc\\s*bể\\s*phốt|hút\\s*hầm\\s*cầu|thay\\s*vòi\\s*nước|lắp\\s*đặt\\s*camera|bảo\\s*trì\\s*điều\\s*hòa|vệ\\s*sinh\\s*máy\\s*giặt)\\b',
    '\\b(?:sự\\s*thật\\s*ít\\s*ai\\s*biết|cảnh\\s*báo\\s*từ\\s*chuyên\\s*gia|giải\\s*quyết\\s*dứt\\s*điểm|dấu\\s*hiệu\\s*nhận\\s*biết|lời\\s*khuyên\\s*từ\\s*bác\\s*sĩ|phương\\s*pháp\\s*tự\\s*nhiên|thông\\s*tin\\s*sai\\s*lệch|kiểm\\s*chứng\\s*sự\\s*thật)\\b',
    '\\b(?:tai\\s*nạn\\s*giao\\s*thông|xe\\s*khách|xe\\s*tải|xe\\s*container|tông\\s*xe|va\\s*chạm\\s*xe|lật\\s*xe)(?!.*(?:sạt\\s*lở|lũ|ngập|bão|thiên\\s*tai|mưa\\s*lớn|trôi|mất\\s*tích|cứu\\s*hộ|cứu\\s*nạn))\\b',
    '\\b(?:tai\\s*nạn\\s*lao\\s*động|sập\\s*giàn\\s*giáo|ngã\\s*giàn\\s*giáo|rơi\\s*từ\\s*tầng\\s*cao|điện\\s*giật|chập\\s*điện)(?!.*(?:bão|lũ|thiên\\s*tai|mưa\\s*lớn|sạt\\s*lở))\\b',
    '\\b(?:tam\\s*tai|năm\\s*tuổi|sao\\s*kế\\s*đô|vận\\s*hạn|cúng\\s*giải\\s*hạn|hóa\\s*giải\\s*vận\\s*đen|phong\\s*thủy\\s*cải\\s*vận|tử\\s*vi\\s*trọn\\s*đời)\\b',
    '\\b(?:taylor\\s*swift|eras\\s*tour|messi|lionel\\s*messi|ronaldo|cristiano\\s*ronaldo|mbappe|haaland|neymar|giải\\s*thưởng\\s*grammy|oscar)\\b',
    '\\b(?:thang\\s*máy\\s*tốc\\s*độ\\s*cao|phòng\\s*máy\\s*thang\\s*máy|hệ\\s*thống\\s*điều\\s*khiển\\s*tầng|cửa\\s*tầng\\s*tự\\s*động)\\b',
    '\\b(?:thanh\\s*lý\\s*giá\\s*rẻ|xả\\s*kho\\s*nghỉ\\s*bán|giày\\s*si\\s*tuyển|đồ\\s*cũ\\s*giá\\s*tốt|thu\\s*mua\\s*phế\\s*liệu|đồng\\s*nát|vựa\\s*ve\\s*chai|đổi\\s*cũ\\s*lấy\\s*mới)\\b',
    '\\b(?:thanh\\s*tra\\s*công\\s*vụ|kỷ\\s*luật\\s*hành\\s*chính|giải\\s*quyết\\s*đơn\\s*thư|tiếp\\s*công\\s*dân|đối\\s*thoại\\s*trực\\s*tiếp|tháo\\s*gỡ\\s*vướng\\s*mắc)\\b',
    '\\b(?:thi\\s*đua\\s*yêu\\s*nước|kế\\s*hoạch\\s*đề\\s*ra)\\b',
    '\\b(?:thiết\\s*bị\\s*báo\\s*cháy|hệ\\s*thống\\s*báo\\s*cháy|tập\\s*huấn\\s*pccc|nghiệm\\s*thu\\s*pccc)\\b',
    '\\b(?:thiếu\\s*nữ\\s*mất\\s*tích|đi\\s*lạc|không\\s*thấy\\s*về|gia\\s*đình\\s*lo\\s*lắng|bỏ\\s*trốn\\s*cùng|tìm\\s*ông\\s*cụ|tìm\\s*bà\\s*cụ|rời\\s*khỏi\\s*địa\\s*phương|vắng\\s*mặt\\s*tại\\s*nơi\\s*cư\\s*trú)\\b',
    '\\b(?:thu\\s*hoạch|được\\s*mùa|trúng\\s*mùa|năng\\s*suất|sản\\s*lượng|xuất\\s*khẩu|nông\\s*sản|vụ\\s*mùa|trồng\\s*trọt|chăn\\s*nuôi|ốc\\s*hương|tôm\\s*hùm|lồng\\s*bè|container|ách\\s*tắc\\s*tại\\s*cảng|thông\\s*quan)(?!.*(?:thiệt\\s*hại|mất\\s*trắng|ngập|bão|lũ|sạt\\s*lở|hư\\s*hỏng|cuốn\\s*trôi|thiên\\s*tai))\\b',
    '\\b(?:thu\\s*hút\\s*vốn\\s*f\\s*d\\s*i|môi\\s*trường\\s*đầu\\s*tư|ưu\\s*đãi\\s*ngân\\s*sách|vốn\\s*vốn\\s*đầu\\s*tư\\s*công|giải\\s*ngân|tiến\\s*độ\\s*xây\\s*lắp)\\b',
    '\\b(?:thu\\s*hồi\\s*vũ\\s*khí|vật\\s*liệu\\s*nổ\\s*tự\\s*chế|công\\s*cụ\\s*hỗ\\s*trợ|giao\\s*nộp\\s*vũ\\s*khí)\\b',
    '\\b(?:thuốc\\s*lá\\s*(?:lậu|nhập\\s*lậu|ngoại)|bao\\s*thuốc\\s*lá|tàng\\s*trữ\\s*thuốc\\s*lá|buôn\\s*bán\\s*hàng\\s*cấm)\\b',
    '\\b(?:thành\\s*lập\\s*doanh\\s*nghiệp|giấy\\s*phép\\s*điều\\s*kiện|hợp\\s*quy\\s*kỹ\\s*thuật|kiểm\\s*định\\s*độc\\s*lập|chất\\s*lượng\\s*vượt\\s*trội|thương\\s*hiệu\\s*uy\\s*tín)\\b',
    '\\b(?:thành\\s*tựu|kết\\s*quả)\\s*nổi\\s*bật\\b',
    '\\b(?:tháng\\s*hành\\s*động\\s*vì\\s*bình\\s*đẳng\\s*giới|tháng\\s*hành\\s*động\\s*quốc\\s*gia|công\\s*bố\\s*quyết\\s*định|trao\\s*quyết\\s*định)\\b',
    '\\b(?:thông\\s*báo\\s*tìm\\s*kiếm\\s*người\\s*vắng\\s*mặt|tuyên\\s*bố\\s*mất\\s*tích|tìm\\s*chủ\\s*sở\\s*hữu|niêm\\s*yết\\s*công\\s*khai)\\b',
    '\\b(?:thông\\s*hầm|trải\\s*nhựa|vá\\s*đường|khắc\\s*phục\\s*ổ\\s*gà|duy\\s*tu|sửa\\s*chữa\\s*định\\s*kỳ|mở\\s*rộng\\s*tuyến\\s*đường)(?!.*(?:bão|lũ|sạt\\s*lở|mưa|thiên\\s*tai|khắc\\s*phục|sụt\\s*lún|nứt\\s*toác|hư\\s*hỏng))\\b',
    '\\b(?:thù\\s*lao\\s*luật\\s*sư|hợp\\s*đồng\\s*dịch\\s*vụ\\s*pháp\\s*lý|chi\\s*phí\\s*tố\\s*tụng|thụ\\s*lý\\s*vụ\\s*án|phân\\s*xử\\s*tranh\\s*chấp)\\b',
    '\\b(?:thăm\\s*và\\s*làm\\s*việc|làm\\s*việc\\s*tại|kiểm\\s*tra\\s*công\\s*tác|chỉ\\s*đạo\\s*hội\\s*nghị|phát\\s*biểu\\s*chỉ\\s*đạo|tham\\s*dự\\s*hội\\s*nghị|tiếp\\s*xúc\\s*cử\\s*tri)(?!\\s*(?:phòng[\\s,]+chống|ứng\\s*phó|cứu\\s*trợ|khắc\\s*phục|bão|lũ|thiên\\s*tai|thăm|thăm\\s*hỏi|động\\s*viên|chia\\s*sẻ))\\b',
    '\\b(?:thưởng\\s*tết|quà\\s*tết|nghỉ\\s*tết|vé\\s*tết|hàng\\s*tết|sắm\\s*tết|chợ\\s*tết|đón\\s*tết|vui\\s*xuân|chúc\\s*tết|tết\\s*nguyên\\s*đán|lì\\s*xì|bánh\\s*chưng|mứt\\s*tết|hoa\\s*tết|du\\s*xuân|du\\s*lịch|khách\\s*sạn|resort|nghỉ\\s*dưỡng|check-in|sống\\s*ảo)(?!.*(?:cứu\\s*trợ|hỗ\\s*trợ|thiên\\s*tai|bão|lũ|người\\s*nghèo|khó\\s*khăn|mắc\\s*kẹt|cô\\s*lập))\\b',
    '\\b(?:thảm\\s*họa)\\s*(?:thẩm\\s*mỹ|thời\\s*trang|âm\\s*nhạc|dao\\s*kéo|mc|trang\\s*điểm|nấu\\s*ăn|nhan\\s*sắc)\\b',
    '\\b(?:thẩm\\s*định\\s*giá|đấu\\s*giá\\s*tài\\s*sản|kê\\s*biên|thu\\s*về\\s*ngân\\s*sách|nghĩa\\s*vụ\\s*tài\\s*chính)\\b',
    '\\b(?:thẩm\\s*định\\s*viên|đấu\\s*giá\\s*viên|công\\s*chứng\\s*viên|thừa\\s*phát\\s*lại|văn\\s*phòng\\s*luật|hành\\s*nghề\\s*y\\s*dược)\\b',
    '\\b(?:thị\\s*lực|mất\\s*trí\\s*nhớ|suy\\s*tim|chẩn\\s*đoán|xét\\s*nghiệm|phẫu\\s*thuật|nội\\s*soi|siêu\\s*âm|cấy\\s*ghép|cận\\s*thị|viễn\\s*thị|loạn\\s*thị|nhồi\\s*máu|đột\\s*quỵ|cao\\s*huyết\\s*áp|tiểu\\s*đường|mỡ\\s*máu|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|đậu\\s*mùa\\s*khỉ|thủy\\s*đậu|sởi|cúm\\s*a|cúm\\s*b|nâng\\s*ngực|hút\\s*mỡ|thẩm\\s*mỹ\\s*viện)(?!.*(?:nạn\\s*nhân|tử\\s*thi|do\\s*thiên\\s*tai|sau\\s*bão|ngập\\s*lụt))\\b',
    '\\b(?:thị\\s*trường\\s*chuyển\\s*nhượng|hợp\\s*đồng\\s*kỷ\\s*lục|ngôi\\s*sao\\s*bóng\\s*đá|vòng\\s*loại\\s*world\\s*cup|champion\\s*league)\\b',
    '\\b(?:thị\\s*trường\\s*lao\\s*động|nhu\\s*cầu\\s*tuy\\s*dụng|cơ\\s*hội\\s*việc\\s*làm|làn\\s*sóng\\s*nhảy\\s*việc|nộp\\s*c\\s*v|phỏng\\s*vấn\\s*tuy\\s*dụng)\\b',
    '\\b(?:thị\\s*trường|chứng\\s*khoán|cổ\\s*phiếu|vn-index|giá\\s*vàng|giá\\s*bạc|giá\\s*cà\\s*phê|tỷ\\s*giá|lãi\\s*suất|ngân\\s*hàng|tín\\s*dụng|vay\\s*vốn|doanh\\s*thu|lợi\\s*nhuận|xuất\\s*khẩu|nhập\\s*khẩu|kim\\s*ngạch|thương\\s*mại|bất\\s*động\\s*sản|đấu\\s*giá\\s*đất|sổ\\s*đỏ|thưởng\\s*tết|lì\\s*xì|phụ\\s*cấp\\s*ưu\\s*đãi|khung\\s*chính\\s*sách|chính\\s*sách\\s*thuế|nộp\\s*phạt|kích\\s*cầu|khấu\\s*trừ\\s*lương|xuất\\s*siêu|nhập\\s*siêu|kinh\\s*tế\\s*tư\\s*nhân|phong\\s*tỏa\\s*tài\\s*khoản|cưỡng\\s*chế\\s*thuế|nợ\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử)(?!.*(?:bão|lũ|thiệt\\s*hại|ủng\\s*hộ|hỗ\\s*trợ|ước\\s*tính|khắc\\s*phục|hư\\s*hỏng))\\b',
    '\\b(?:thịt\\s*(?:bò|heo|lợn|gà|vịt)|thực\\s*phẩm\\s*(?:bẩn|hư\\s*hỏng)|ngộ\\s*độc\\s*thực\\s*phẩm|an\\s*toàn\\s*thực\\s*phẩm|hàng\\s*giả|hàng\\s*nhái)(?!.*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:thống\\s*kê|báo\\s*cáo|tổng\\s*kết)\\s*(?:tình\\s*hình|số\\s*liệu)\\s*(?:tai\\s*nạn|giao\\s*thông|an\\s*ninh\\s*trật\\s*tự)(?!\\s*(?:do|vì|trong)\\s*(?:bão|lũ|thiên\\s*tai|mưa))\\b',
    '\\b(?:thời\\s*điểm\\s*vàng|cơ\\s*hội\\s*có\\s*một\\s*không\\s*hai|nhận\\s*ngay\\s*ưu\\s*đãi|đừng\\s*bỏ\\s*lỡ|đăng\\s*ký\\s*ngay)\\b',
    '\\b(?:thủ\\s*tướng\\s*tiếp|chủ\\s*tịch\\s*nước\\s*tiếp|ngoại\\s*giao\\s*đoàn|đại\\s*sứ\\s*quán|lãnh\\s*sự\\s*quán)(?!.*(?:hỗ\\s*trợ\\s*bão\\s*lụt|viện\\s*trợ))\\b',
    '\\b(?:thủng\\s*xăm|hỏng\\s*xe|chết\\s*máy|ùn\\s*tắc|kẹt\\s*xe|dòng\\s*người\\s*chen\\s*chúc)\\b',
    '\\b(?:thủy\\s*canh|khí\\s*canh|phân\\s*bón\\s*n\\s*p\\s*k|thuốc\\s*bảo\\s*vệ\\s*thực\\s*vật|giống\\s*cây\\s*lai|nuôi\\s*cấy\\s*mô|nhà\\s*màng|nhà\\s*lưới)\\b',
    '\\b(?:thử\\s*nghiệm\\s*lâm\\s*sàng|biện\\s*pháp\\s*can\\s*thiệp|nội\\s*soi\\s*tiêu\\s*hóa|chụp\\s*m\\s*r\\s*i|cat\\s*scan|sinh\\s*thiết|kháng\\s*sinh\\s*đồ)\\b',
    '\\b(?:thực\\s*tập\\s*phương\\s*án|diễn\\s*tập\\s*khu\\s*vực|luyện\\s*tập\\s*chuyển\\s*trạng\\s*thái|hợp\\s*luyện|thao\\s*trường|bắn\\s*đạn\\s*thật)(?!.*(?:trong\\s*mưa\\s*bão|thực\\s*tế|cứu\\s*dân|lũ\\s*lụt|thiên\\s*tai|sạt\\s*lở))\\b',
    '\\b(?:thực\\s*tế\\s*ảo|v\\s*r|a\\s*r|metaverse|thị\\s*kính|tay\\s*cầm\\s*điều\\s*khiển|không\\s*gian\\s*số\\s*3d|mô\\s*phỏng\\s*hình\\s*ảnh|kính\\s*thông\\s*minh)\\b',
    '\\b(?:thực\\s*đơn\\s*giảm\\s*cân|mẹo\\s*sống\\s*khỏe|tác\\s*dụng\\s*của\\s*rau| yoga|gym|fitness|bài\\s*tập\\s*thể\\s*dục|dinh\\s*dưỡng\\s*lành\\s*mạnh)\\b',
    '\\b(?:tin\\s*buồn|lễ\\s*viếng|vô\\s*cùng\\s*thương\\s*tiếc|hưởng\\s*thọ|lễ\\s*truy\\s*điệu|an\\s*táng|phúng\\s*viếng|chia\\s*buồn\\s*cùng\\s*gia\\s*đình)\\b',
    '\\b(?:tin\\s*sai\\s*lệch|tin\\s*giả|thông\\s*tin\\s*thất\\s*thiệt|xử\\s*lý\\s*đối\\s*tượng\\s*đăng\\s*tin)(?!\\s*(?:bão|lũ|thiên\\s*tai))\\b',
    '\\b(?:tinh\\s*thần\\s*khởi\\s*nghiệp|chương\\s*trình\\s*vườn\\s*ươm\\s*tạo|hỗ\\s*trợ\\s*doanh\\s*nghiệp|đối\\s*mới\\s*sáng\\s*tạo|vốn\\s*đầu\\s*tư\\s*mạo\\s*hiểm|angel\\s*investor)\\b',
    '\\b(?:tinh\\s*thần\\s*đoàn\\s*kết|phát\\s*huy\\s*truyền\\s*thống|thắng\\s*lợi\\s*vẻ\\s*vang|nhiệm\\s*vụ\\s*trọng\\s*tâm|nâng\\s*cao\\s*cảnh\\s*giác|tối\\s*ưu\\s*hóa|quy\\s*trình\\s*khép\\s*kín)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*ngành\\s*y|hành\\s*nghề\\s*khám\\s*chữa\\s*bệnh|kỷ\\s*luật\\s*vi\\s*phạm|tận\\s*tâm\\s*phục\\s*vụ|thầy\\s*thuốc\\s*nhân\\s*dân)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*ngành|quy\\s*chuẩn\\s*kỹ\\s*thuật|nghiệm\\s*thu\\s*hoàn\\s*thành|bàn\\s*giao\\s*công\\s*trình|nhà\\s*thầu\\s*phụ|liên\\s*danh\\s*nhà\\s*thầu)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*trình\\s*độ|hạng\\s*CDNN|chứng\\s*chỉ\\s*hành\\s*nghề|giấy\\s*phép\\s*hành\\s*nghề)\\b',
    '\\b(?:tiêu\\s*chuẩn\\s*xuất\\s*khẩu|chứng\\s*chỉ\\s*chất\\s*lượng\\s*iso|rào\\s*cản\\s*kỹ\\s*thuật|thông\\s*quan\\s*hàng\\s*hóa\\s*tại\\s*cửa\\s*khẩu|chứng\\s*nhận\\s*nguồn\\s*gốc)\\b',
    '\\b(?:tiếp\\s*xúc\\s*cử\\s*tri|thảo\\s*luận\\s*tại\\s*tổ|chất\\s*vấn\\s*bộ\\s*trưởng|phiên\\s*họp\\s*thường\\s*kỳ|thông\\s*qua\\s*nghị\\s*quyết|lấy\\s*phiếu\\s*tín\\s*nhiệm)\\b',
    '\\b(?:tiếp\\s*đại\\s*sứ|trình\\s*quốc\\s*thư|giao\\s*lưu\\s*hữu\\s*nghị|củng\\s*cố\\s*quan\\s*hệ|ngoại\\s*giao\\s*đa\\s*phương|ký\\s*kết\\s*biên\\s*bản\\s*ghi\\s*nhớ|MOU|đối\\s*tác\\s*chiến\\s*lược)\\b',
    '\\b(?:tiền\\s*cổ|cổ\\s*vật|khảo\\s*cổ|ngôi\\s*mộ|di\\s*tích\\s*lịch\\s*sử|kho\\s*báu|đào\\s*được|phát\\s*hiện\\s*hầm|mộ\\s*cổ)(?!.*(?:sạt\\s*lở|hư\\s*hại|lũ|bão|cuốn\\s*trôi))\\b',
    '\\b(?:tiệc\\s*tất\\s*niên|year\\s*end\\s*party|teambuilding|văn\\s*hóa\\s*doanh\\s*nghiệp|nhân\\s*viên\\s*tiêu\\s*biểu|nghỉ\\s*mát\\s*hè|sinh\\s*nhật\\s*công\\s*ty)\\b',
    '\\b(?:toa\\s*quay|tay\\s*cần|khối\\s*đối\\s*trọng|dầm\\s*gốc|lồng\\s*nâng|đốt\\s*thân\\s*cần\\s*trục|hệ\\s*thống\\s*phanh\\s*hãm|vận\\s*hành\\s*an\\s*toàn)\\b',
    '\\b(?:trang\\s*trí\\s*nhà\\s*cửa|phong\\s*thủy\\s*phòng\\s*ngủ|sắp\\s*xếp\\s*không\\s*gian|tổ\\s*ấm\\s*gia\\s*đình|nội\\s*thất\\s*tinh\\s*tế|xu\\s*hướng\\s*màu\\s*sắc|vật\\s*liệu\\s*bên\\s*vững)\\b',
    '\\b(?:tranh\\s*chấp\\s*bản\\s*quyền|vi\\s*phạm\\s*sáng\\s*chế|kiện\\s*tụng\\s*bằng\\s*sáng\\s*chế|tác\\s*quyền\\s*âm\\s*nhạc|v\\s*c\\s*p\\s*m\\s*c|độc\\s*quyền\\s*thương\\s*hiệu)\\b',
    '\\b(?:tranh\\s*chấp\\s*lao\\s*động|sa\\s*thải\\s*trái\\s*luật|hợp\\s*đồng\\s*lao\\s*động|bảo\\s*hiểm\\s*thất\\s*nghiệp|đình\\s*công|lương\\s*thưởng)\\b',
    '\\b(?:tranh\\s*chấp\\s*quyền\\s*sử\\s*dụng\\s*đất|thừa\\s*kế\\s*theo\\s*pháp\\s*luật|di\\s*chúc\\s*hợp\\s*pháp|hợp\\s*đồng\\s*ủy\\s*quyền|công\\s*chứng\\s*tư\\s*pháp|thi\\s*hành\\s*án\\s*dân\\s*sự)\\b',
    '\\b(?:tranh\\s*chấp|mâu\\s*thuẫn|xô\\s*xát|đâm\\s*chém|sát\\s*hại|giết\\s*người|án\\s*mạng|trọng\\s*án)(?!.*(?:bão|lũ))\\b',
    '\\b(?:trao\\s*bằng|tiến\\s*sĩ|thạc\\s*sĩ|đại\\s*biểu\\s*Quốc\\s*hội|30[-/]4|1[-/]5|nghỉ\\s*lễ|bầu\\s*cử|ứng\\s*cử|đắc\\s*cử)\\b',
    '\\b(?:trao\\s*huy\\s*hiệu\\s*đảng|huân\\s*chương\\s*lao\\s*động|cờ\\s*thi\\s*đua\\s*chính\\s*phủ|bằng\\s*khen\\s*thủ\\s*tướng|anh\\s*hùng\\s*lao\\s*động)\\b',
    '\\b(?:trao\\s*quà|tặng\\s*quà|hỗ\\s*trợ\\s*khó\\s*khăn|người\\s*nghèo|hộ\\s*nghèo|trẻ\\s*em\\s*nghèo|người\\s*khuyết\\s*tật|nạn\\s*nhân\\s*chất\\s*độc\\s*màu\\s*da\\s*cam)(?!.*(?:vùng\\s*bão|vùng\\s*lũ|rốn\\s*lũ|sau\\s*bão|bị\\s*thiệt\\s*hại|khắc\\s*phục\\s*hậu\\s*quả|triều\\s*cường|ngập|lụt|thiên\\s*tai|tốc\\s*mái|sập\\s*nhà|trôi|mưa\\s*lũ|sạt\\s*lở|chia\\s*cắt|cô\\s*lập|bị\\s*ảnh\\s*hưởng|tái\\s*thiết|ổn\\s*định|dân\\s*sinh|khẩn\\s*cấp))\\b',
    '\\b(?:trao\\s*tặng\\s*kỷ\\s*niệm\\s*chương|huy\\s*hiệu\\s*đảng|khen\\s*thưởng\\s*đột\\s*xuất|phong\\s*trào\\s*thi\\s*đua|gương\\s*người\\s*tốt\\s*việc\\s*tốt|điển\\s*hình\\s*tiên\\s*tiến)\\b',
    '\\b(?:trao\\s*tặng\\s*nhà|nhà\\s*tình\\s*nghĩa|nhà\\s*đại\\s*đoàn\\s*kết|hỗ\\s*trợ\\s*sinh\\s*kế|tặng\\s*bò|trao\\s*vốn|nhặt\\s*được\\s*của\\s*rơi|trả\\s*lại\\s*tài\\s*sản|tấm\\s*lòng\\s*vàng|mạnh\\s*thường\\s*quân)(?!\\s*(?:cho|tại|vùng|người\\s*dân)\\s*(?:bão|lũ|thiên\\s*tai|sạt\\s*lở|ngập\\s*lụt|sau\\s*bão|tái\\s*thiết|khắc\\s*phục))\\b',
    '\\b(?:triều\\s*cường\\s*(?:rằm|giữa\\s*tháng|hàng\\s*tháng)|ngập\\s*do\\s*triều|đỉnh\\s*triều|hố\\s*ga|nắp\\s*cống|vỉ\\s*hè|đường\\s*hầm)\\b',
    '\\b(?:triển\\s*khai\\s*nghị\\s*quyết|quán\\s*triệt\\s*tư\\s*tưởng|vận\\s*động\\s*quần\\s*chúng|xây\\s*dựng\\s*nông\\s*thôn\\s*mới|phong\\s*trào\\s*toàn\\s*dân|đoàn\\s*kết\\s*xây\\s*dựng\\s*đời\\s*sống)\\b',
    '\\b(?:triển\\s*khai\\s*nhiệm\\s*vụ|tổng\\s*kết\\s*công\\s*tác|phát\\s*động\\s*thi\\s*đua|khen\\s*thưởng\\s*đột\\s*xuất|huy\\s*hiệu\\s*đảng)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|phòng\\s*chống\\s*thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:trung\\s*đông|hezbollah|houthi|biển\\s*đỏ|eo\\s*biển\\s*hormuz|xung\\s*đột\\s*israel|thủ\\s*tướng\\s*netanyahu)\\b',
    '\\b(?:trà\\s*đạo|thiền\\s*định|cắm\\s*hoa\\s*nghệ\\s*thuật|sưu\\s*tầm\\s*đồ\\s*cổ|thú\\s*vui\\s*tao\\s*nhã|trưng\\s*bày\\s*sinh\\s*vật\\s*cảnh)\\b',
    '\\b(?:trách\\s*nhiệm\\s*nghề\\s*nghiệp|bảo\\s*hiểm\\s*trách\\s*nhiệm|vi\\s*phạm\\s*đạo\\s*đức\\s*nghề|đình\\s*chỉ\\s*hành\\s*nghề|thu\\s*hồi\\s*thẻ\\s*luật\\s*sư|khiếu\\s*nại\\s*tố\\s*tụng)\\b',
    '\\b(?:trí\\s*tuệ\\s*nhân\\s*tạo|artificial\\s*intelligence|ai\\s*generative|chatgpt|google\\s*ai|tích\\s*hợp\\s*ai|công\\s*cụ\\s*tìm\\s*kiếm|trình\\s*duyệt\\s*web|tấn\\s*công\\s*mạng|an\\s*ninh\\s*mạng|lừa\\s*đảo\\s*trực\\s*tuyến|mã\\s*độc|phần\\s*mềm\\s*gián\\s*điệp|hack|hacker|lỗ\\s*hổng\\s*bảo\\s*mật)\\b',
    '\\b(?:trích\\s*lập\\s*dự\\s*phòng|nợ\\s*xấu|thanh\\s*khoản|tái\\s*cơ\\s*cấu|phí\\s*bảo\\s*hiểm|hợp\\s*đồng\\s*nhân\\s*thọ|quyền\\s*lợi\\s*khách\\s*hàng)\\b',
    '\\b(?:trưng\\s*bày\\s*bảo\\s*tàng|phục\\s*chế\\s*số|hiện\\s*vật\\s*gốc|không\\s*gian\\s*triển\\s*lãm|thuyết\\s*minh\\s*viên|khách\\s*tham\\s*quan|di\\s*sản\\s*thế\\s*giới)\\b',
    '\\b(?:trận\\s*bạch\\s*đằng|chi\\s*lăng|điện\\s*biên\\s*phủ|nghệ\\s*thuật\\s*quân\\s*sự|lịch\\s*sử\\s*vẻ\\s*vang|hào\\s*khí\\s*dân\\s*tộc|truyền\\s*thống\\s*yêu\\s*nước)\\b',
    '\\b(?:trị\\s*bệnh\\s*cho\\s*chó\\s*mèo|tiêm\\s*phòng\\s*dại|phối\\s*giống\\s*thú\\s*cưng|thức\\s*ăn\\s*hạt|cát\\s*vệ\\s*sinh|phòng\\s*khám\\s*thú\\s*y|spa\\s*thú\\s*cưng)\\b',
    '\\b(?:trồng\\s*cây|vụ\\s*đông|vụ\\s*xuân|vụ\\s*mùa|được\\s*mùa|mất\\s*mùa|giá\\s*thóc|giá\\s*lúa|nông\\s*dân\\s*sản\\s*xuất|xuống\\s*giống)(?!.*(?:bão|lũ|ngập|thiệt\\s*hại|khắc\\s*phục|thiên\\s*tai|rét|lạnh|nhiệt\\s*độ))\\b',
    '\\b(?:trộm\\s*cắp|cướp\\s*giật|móc\\s*túi|đột\\s*nhập|phá\\s*khóa|trộm\\s*xe|cướp\\s*tài\\s*sản)\\b',
    '\\b(?:trở\\s*lại\\s*làm\\s*việc|ngày\\s*làm\\s*việc\\s*đầu\\s*tiên|khai\\s*xuân|du\\s*xuân|nghỉ\\s*tết|lịch\\s*nghỉ|nghỉ\\s*lễ|nghỉ\\s*bù|đi\\s*làm\\s*lại)(?!.*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục))\\b',
    '\\b(?:trợ\\s*giúp\\s*pháp\\s*lý|luật\\s*sư\\s*chỉ\\s*định|miễn\\s*phí\\s*dịch\\s*vụ|hỗ\\s*trợ\\s*pháp\\s*luật|tư\\s*vấn\\s*pháp\\s*lý\\s*lưu\\s*động|phổ\\s*biến\\s*giáo\\s*dục\\s*pháp\\s*luật)\\b',
    '\\b(?:turbine\\s*gió|cánh\\s*quạt\\s*phong\\s*điện|điện\\s*gió\\s*ngoài\\s*khơi|móng\\s*cọc\\s*biển|năng\\s*lượng\\s*tái\\s*tạo|quy\\s*hoạch\\s*điện\\s*viii|giá\\s*feed-in\\s*tariff)\\b',
    '\\b(?:tuyên\\s*dương\\s*thành\\s*tích|huân\\s*chương\\s*lao\\s*động|bằng\\s*khen\\s*chính\\s*phủ|gương\\s*điển\\s*hình\\s*tiên\\s*tiến|phát\\s*huy\\s*sức\\s*mạnh)\\b',
    '\\b(?:tuyên\\s*dương\\s*điển\\s*hình|nghị\\s*quyết|quY\\s*định)\\b',
    '\\b(?:tuyên\\s*truyền\\s*phổ\\s*biến|giáo\\s*dục\\s*pháp\\s*luật|hưởng\\s*ứng\\s*phong\\s*trào|tổng\\s*kết\\s*khen\\s*thưởng|khen\\s*ngợi\\s*biểu\\s*dương)(?!.*(?:cứu\\s*trợ|khắc\\s*phục|phòng\\s*chống\\s*thiên\\s*tai|bão|lũ))\\b',
    '\\b(?:tuyên\\s*truyền\\s*vận\\s*động|phòng\\s*chống\\s*lãng\\s*phí|thực\\s*hành\\s*tiết\\s*kiệm|đẩy\\s*mạnh\\s*cải\\s*cách|hiệu\\s*quả\\s*thi\\s*hành)\\b',
    '\\b(?:tuyên\\s*đương\\s*điển\\s*hình|người\\s*tốt\\s*việc\\s*tốt|huy\\s*hiệu\\s*cao\\s*quý|giải\\s*thưởng\\s*danh\\s*giá)\\b',
    '\\b(?:tuyến\\s*cáp\\s*aag|apg|ia|smw3|sự\\s*cố\\s*đứt\\s*cáp|đường\\s*truyền\\s*quốc\\s*tế|bảo\\s*trì\\s*hệ\\s*thống|trạm\\s*cập\\s*bờ)\\b',
    '\\b(?:tuyến\\s*metro|đường\\s*sắt\\s*đô\\s*thị|tàu\\s*điện\\s*ngầm|đường\\s*sắt\\s*trên\\s*cao|ga\\s*ngầm)(?!.*(?:ngập|lũ|sạt\\s*lở))\\b',
    '\\b(?:tuyển\\s*dụng\\s*gấp|mức\\s*lương\\s*thỏa\\s*thuận|quyền\\s*lợi\\s*hấp\\s*dẫn|môi\\s*trường\\s*làm\\s*việc|nộp\\s*hồ\\s*sơ|phỏng\\s*vấn\\s*online)\\b',
    '\\b(?:tuyển\\s*dụng|tuyển\\s*lao\\s*động|việc\\s*làm|nhân\\s*sự|chiêu\\s*mộ|thuê\\s*đất|miễn\\s*tiền\\s*thuê|khởi\\s*nghiệp|làm\\s*kinh\\s*tế|phụ\\s*nữ\\s*làm\\s*kinh\\s*tế|thoát\\s*nghèo|vay\\s*vốn|ngân\\s*hàng\\s*chính\\s*sách)\\b',
    '\\b(?:tuyển\\s*sinh|điểm\\s*chuẩn|học\\s*phí|tự\\s*chủ\\s*đại\\s*học|kỳ\\s*thi\\s*tốt\\s*nghiệp|học\\s*sinh\\s*giỏi|đi\\s*học\\s*thêm|làm\\s*thêm\\s*dịp\\s*hè|vào\\s*lớp\\s*1|nghỉ\\s*học)(?!.*(?:bão|lũ|mưa|thiên\\s*tai|ngập|sạt\\s*lở|giông|phòng\\s*tránh))\\b',
    '\\b(?:tuần\\s*tra|kiểm\\s*soát|tràn\\s*lan|trấn\\s*áp|tội\\s*phạm|tệ\\s*nạn|ma\\s*túy|cờ\\s*bạc|mại\\s*dâm|pháo\\s*nổ|vũ\\s*khí|vật\\s*liệu\\s*nổ|súng\\s*tự\\s*chế|an\\s*ninh\\s*trật\\s*tự|antt|trật\\s*tự\\s*an\\s*toàn\\s*giao\\s*thông|ttatgt|đảm\\s*bảo\\s*trật\\s*tự|giữ\\s*vững\\s*an\\s*ninh|an\\s*ninh\\s*kinh\\s*tế|an\\s*ninh\\s*chính\\s*trị|an\\s*ninh\\s*quốc\\s*gia|an\\s*ninh\\s*an\\s*toàn)\\b',
    '\\b(?:tâm\\s*lý\\s*học|trầm\\s*cảm|chữa\\s*lành|sang\\s*chấn\\s*tâm\\s*lý|kỹ\\s*năng\\s*sống|tư\\s*duy\\s*tích\\s*cực|phát\\s*triển\\s*bản\\s*thân|hạnh\\s*phúc\\s*mỗi\\s*ngày)\\b',
    '\\b(?:tâm\\s*sự|ngoại\\s*tình|người\\s*thứ\\s*ba|đánh\\s*ghen|bí\\s*mật\\s*phòng\\s*the|chuyện\\s*thầm\\s*kín|bạn\\s*đời|ly\\s*hôn|kết\\s*hôn|hẹn\\s*hò)\\b',
    '\\b(?:té\\s*xe|tự\\s*gây\\s*tai\\s*nạn|tử\\s*vong\\s*tại\\s*chỗ|tử\\s*vong\\s*trong\\s*cửa\\s*hàng|tử\\s*vong\\s*tại\\s*quán|lọt\\s*hố|rơi\\s*xuống\\s*hố)(?!.*(?:sụt\\s*lún|hố\\s*tử\\s*thần|sạt\\s*lở|lũ|bão))\\b',
    '\\b(?:tìm\\s*kiếm\\s*thông\\s*tin|công\\s*cụ\\s*tìm\\s*kiếm)(?!\\s*(?:cứu\\s*nạn|nạn\\s*nhân))\\b',
    '\\b(?:tín\\s*dụng\\s*đen|lừa\\s*đảo|bắt\\s*cóc\\s*online|nhảy\\s*lầu|tự\\s*sát|cầm\\s*dao|xông\\s*vào|vụ\\s*án|nhặt\\s*được\\s*tiền|trả\\s*lại\\s*người\\s*đánh\\s*rơi|pháo\\s*hoa|pháo\\s*nổ|tự\\s*chế\\s*pháo|thuốc\\s*nổ|vật\\s*liệu\\s*nổ)(?!.*(?:lũ|bão|trôi|sạt|thiên\\s*tai|mưa\\s*lũ|cuốn\\s*trôi|vùi\\s*lấp))\\b',
    '\\b(?:tòa\\s*án\\s*tối\\s*cao|viện\\s*kiểm\\s*sát\\s*nhân\\s*dân|hội\\s*đồng\\s*xét\\s*xử|luật\\s*sư\\s*bào\\s*chữa|tranh\\s*tụng|phiên\\s*tòa\\s*sơ\\s*thẩm|phúc\\s*thẩm|đại\\s*diện\\s*pháp\\s*luật)\\b',
    '\\b(?:tăng\\s*cường\\s*hợp\\s*tác|thúc\\s*đẩy\\s*đầu\\s*tư|cạnh\\s*tranh\\s*sòng\\s*phẳng)\\b',
    '\\b(?:tăng\\s*cường\\s*kiểm\\s*tra|giám\\s*sát\\s*xử\\s*lý|đúng\\s*trình\\s*tự|pháp\\s*luật\\s*hiện\\s*hành)\\b',
    '\\b(?:tăng\\s*cường\\s*kỷ\\s*luật|siết\\s*chặt\\s*quản\\s*lý)\\b',
    '\\b(?:tăng\\s*cường\\s*quản\\s*lý|siết\\s*chặt\\s*kỷ\\s*cương|nâng\\s*cao\\s*trách\\s*nhiệm|kiểm\\s*tra\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*vi\\s*phạm|đúng\\s*quy\\s*định)\\b',
    '\\b(?:tăng\\s*cường\\s*trách\\s*nhiệm|siết\\s*chặt\\s*kỷ\\s*cương|kiểm\\s*tra\\s*giám\\s*sát|xử\\s*lý\\s*nghiêm\\s*sai\\s*phạm|đúng\\s*quy\\s*định)\\b',
    '\\b(?:tăng\\s*huyết\\s*áp|thuốc\\s*lá|tân\\s*dược|phục\\s*hồi\\s*chức\\s*năng|nối\\s*chi|phẫu\\s*thuật|cấp\\s*cứu\\s*tích\\s*cực|nhìn\\s*mờ|bệnh\\s*lý|lây\\s*lan|đại\\s*dịch|covid|khẩu\\s*trang|tiêm\\s*chủng|vắc\\s*xin)\\b',
    '\\b(?:tăng\\s*lương|giảm\\s*lương|xếp\\s*lương|trả\\s*lương|nợ\\s*lương|lương\\s*tối\\s*thiểu|phụ\\s*cấp\\s*lương|bình\\s*ổn\\s*giá)(?!.*(?:khắc\\s*phục|hỗ\\s*trợ|thiên\\s*tai))\\b',
    '\\b(?:tư\\s*duy\\s*triệu\\s*phú|làm\\s*giàu\\s*không\\s*khó|nghỉ\\s*hưu\\s*sớm|kế\\s*hoạch\\s*chi\\s*tiêu|quản\\s*lý\\s*tài\\s*sản)\\b',
    '\\b(?:tư\\s*vấn\\s*hướng\\s*nghiệp|cẩm\\s*nang\\s*du\\s*học|xét\\s*tuyển\\s*học\\s*bạ|chỉ\\s*tiêu\\s*tuyển\\s*sinh|điểm\\s*sàn|nguyện\\s*vọng\\s*1|kỳ\\s*thi\\s*đánh\\s*giá\\s*năng\\s*lực)\\b',
    '\\b(?:tưới\\s*tiêu|nguồn\\s*nước\\s*phục\\s*vụ\\s*sản\\s*xuất|điều\\s*tiết\\s*nước\\s*ruộng)\\b',
    '\\b(?:tạm\\s*dừng\\s*ứng\\s*dụng|hệ\\s*thống\\s*thuế|nâng\\s*cấp\\s*hệ\\s*thống|bảo\\s*trì\\s*hệ\\s*thống|cập\\s*nhật\\s*thông\\s*tin|ngành\\s*thuế|hóa\\s*đơn\\s*điện\\s*tử|cổng\\s*dịch\\s*vụ\\s*công)\\b',
    '\\b(?:tải\\s*trọng\\s*gió|dao\\s*động\\s*công\\s*trình|hệ\\s*thống\\s*giảm\\s*chấn|tuned\\s*mass\\s*damper|t\\s*m\\s*d|kháng\\s*chấn|ổn\\s*định\\s*kết\\s*cấu)\\b',
    '\\b(?:tất\\s*toán\\s*tài\\s*khoản|đáo\\s*hạn\\s*thẻ|phí\\s*duy\\s*trì|hạn\\s*mức\\s*thanh\\s*toán|bảo\\s*hiểm\\s*nhân\\s*thọ|quyền\\s*lợi\\s*bảo\\s*hiểm|người\\s*được\\s*thụ\\s*hưởng|bồi\\s*thường\\s*hợp\\s*đồng)(?!.*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|hỗ\\s*trợ))\\b',
    '\\b(?:tập\\s*gym|bodybuilding|whey\\s*protein|creatine|giảm\\s*mỡ\\s*bụng|cơ\\s*bụng\\s*6\\s*múi|huấn\\s*luyện\\s*viên\\s*cá\\s*nhân|pt|chạy\\s*bộ\\s*mỗi\\s*ngày)\\b',
    '\\b(?:tập\\s+\\d+|review\\s*phim|preview\\s*tập|tóm\\s*tắt\\s*phim|lịch\\s*chiếu|show\\s*truyền\\s*hình)\\b',
    '\\b(?:tối\\s*ưu\\s*seo|backlink|chạy\\s*quảng\\s*cáo|adsense|google\\s*ads|facebook\\s*ads|tiktok\\s*shop|tiếp\\s*thị\\s*liên\\s*kết|affiliate\\s*marketing|branding|thương\\s*hiệu\\s*cá\\s*nhân)\\b',
    '\\b(?:tổ\\s*dân\\s*phố|khu\\s*phố\\s*văn\\s*hóa|gia\\s*đình\\s*tiêu\\s*biểu|giấy\\s*khai\\s*sinh|thường\\s*trú|tạm\\s*vắng|căn\\s*cước\\s*công\\s*dân|định\\s*danh\\s*mức\\s*2)\\b',
    '\\b(?:tổng\\s*duyệt|hợp\\s*luyện|thực\\s*tập\\s*phương\\s*án|hội\\s*thao\\s*nghiệp\\s*vụ|huấn\\s*luyện\\s*nghiệp\\s*vụ|diễn\\s*tập\\s*phương\\s*án|trải\\s*nghiệm\\s*thực\\s*hành|tập\\s*huấn\\s*kỹ\\s*năng)(?!\\s*(?:thực\\s*tế|trong\\s*mưa\\s*bão|cứu\\s*người\\s*thật))\\b',
    '\\b(?:tổng\\s*điều\\s*tra\\s*kinh\\s*tế|phụ\\s*cấp\\s*khu\\s*vực|xếp\\s*lương|trợ\\s*cấp\\s*bhxh|lương\\s*hưu|tăng\\s*trợ\\s*cấp|xếp\\s*hạng\\s*lương|bảo\\s*hiểm\\s*y\\s*tế\\s*giấy|thưởng\\s*tết)(?!.*(?:vùng\\s*lũ|ngập\\s*lụt|thiên\\s*tai|cứu\\s*trợ|khắc\\s*phục|hỗ\\s*trợ\\s*khẩn\\s*cấp))\\b',
    '\\b(?:tổng\\s*đài\\s*cskh|đường\\s*dây\\s*nóng\\s*khiếu\\s*nại|giải\\s*đáp\\s*thắc\\s*mắc|phản\\s*hồi\\s*khách\\s*hàng|quy\\s*trình\\s*kỹ\\s*thuật|hỗ\\s*trợ\\s*trực\\s*tuyến)\\b',
    '\\b(?:từ\\s*trái\\s*tim\\s*đến\\s*trái\\s*tim|chương\\s*trình\\s*phẫu\\s*thuật|mổ\\s*tim|hở\\s*hàm\\s*ếch|nạn\\s*nhân\\s*chất\\s*độc\\s*da\\s*cam|khuyết\\s*tật|trẻ\\s*mồ\\s*côi|người\\s*cao\\s*tuổi\\s*neo\\s*đơn)\\b',
    '\\b(?:tử\\s*vi|cung\\s*hoàng\\s*đạo|con\\s*giáp|phong\\s*thủy|bói\\s*toán|tướng\\s*số|vận\\s*mệnh)\\b',
    '\\b(?:tử\\s*vi|cung\\s*hoàng\\s*đạo|phong\\s*thủy|hợp\\s*tuổi|ngày\\s*tốt|giờ\\s*xấu|xem\\s*bói|gieo\\s*quẻ|nhân\\s*tướng\\s*học|nhân\\s*mã|xử\\s*nữ|bạch\\s*dương|kim\\s*ngưu|song\\s*tử|cự\\s*giải|sư\\s*tử|thiên\\s*bình|bọ\\s*cạp|ma\\s*kết|bảo\\s*bình|song\\s*ngư)\\b',
    '\\b(?:tự\\s*do\\s*tài\\s*chính|thu\\s*nhập\\s*thụ\\s*động|khai\\s*phá\\s*tiềm\\s*năng|vùng\\s*an\\s*toàn|chữa\\s*lành\\s*tâm\\s*hồn|thiền\\s*định\\s*mỗi\\s*ngày)\\b',
    '\\b(?:tự\\s*hào|truyền\\s*thống|kỷ\\s*niệm|chào\\s*mừng|thành\\s*lập|ra\\s*mắt|khánh\\s*thành|khởi\\s*công|động\\s*thổ|bế\\s*mạc|khai\\s*mạc|hội\\s*thi|hội\\s*diễn|liên\\s*hoan|giao\\s*lưu|gặp\\s*mặt|tọa\\s*đàm|hội\\s*thảo|tập\\s*huấn|bồi\\s*dưỡng|nhiệm\\s*kỳ|văn\\s*kiện|nghị\\s*quyết|chỉ\\s*thị|kế\\s*hoạch|đề\\s*án|dự\\s*án|quy\\s*hoạch|chiến\\s*lược|tầm\\s*nhìn)(?!.*(?:bão|lũ|lụt|ngập|thiên\\s*tai|khẩn\\s*cấp|ứng\\s*phó|cứu\\s*hộ|sạt\\s*lở|rét\\s*đậm|hạn\\s*mặn|vỡ\\s*đê|thăm\\s*hỏi|hỗ\\s*trợ|PCTT|MARD|phòng\\s*chống\\s*thiên\\s*tai|sơ\\s*tán|di\\s*dời|khắc\\s*phục\\s*hậu\\s*quả))\\b',
    '\\b(?:tự\\s*tử|nhảy\\s*cầu|bị\\s*trói|bỏ\\s*bao|nghi\\s*phạm|hung\\s*thủ|bạn\\s*trai|ghen\\s*tuông|mâu\\s*thuẫn|xả\\s*súng|nổ\\s*súng|bắn\\s*chết|đâm\\s*chết|chém|truy\\s*sát|thảm\\s*sát|án\\s*mạng|giết\\s*người|cố\\s*ý\\s*gây\\s*thương\\s*tích|bắt\\s*giữ|quả\\s*tang|đánh\\s*bạc|sới\\s*bạc|trộm\\s*cắp|cướp\\s*giật|truy\\s*nã|tội\\s*phạm|buôn\\s*lậu|ma\\s*túy|pháo\\s*nổ|xô\\s*xát|đầu\\s*thú|giả\\s*chết|trục\\s*lợi|tạm\\s*giữ\\s*hình\\s*sự|hỗn\\s*chiến|đánh\\s*nhau|hành\\s*hung|trộm|cướp|đốt\\s*nhà|phá\\s*hoại\\s*tài\\s*sản|tấn\\s*công|ngáo\\s*đá)\\b',
    '\\b(?:tự\\s*tử|quyên\\s*sinh|nhảy\\s*cầu|treo\\s*cổ|tự\\s*thiêu|trong\\s*nhà|phòng\\s*trọ|nhà\\s*nghỉ|khách\\s*sạn|chung\\s*cư|bạo\\s*lực\\s*gia\\s*đình)\\b',
    '\\b(?:uav|drone)(?!\\s*(?:cứu\\s*trợ|tìm\\s*kiếm|lũ|bão|ngập|sạt|tiếp\\s*tế))\\b',
    '\\b(?:ukraine|dải\\s*gaza|israel|hamas|venezuela|libya|đài\\s*loan|nga\\s*-\\s*ukraine|kiev|moscow|tên\\s*lửa|đạn\\s*pháo|khai\\s*hỏa|chiến\\s*sự|vùng\\s*kursk|hành\\s*lang\\s*ngũ\\s*cốc|châu\\s*âu|thượng\\s*đỉnh|g7|\\bg20\\b)\\b',
    '\\b(?:ung\\s*thư|tiểu\\s*đường|huyết\\s*áp|đột\\s*quỵ|ngộ\\s*độc|lá\\s*ngón|vắc\\s*xin|chiến\\s*dịch\\s*tiêm\\s*chủng|dinh\\s*dưỡng|thực\\s*phẩm|món\\s*ăn|đặc\\s*sản|bệnh\\s*dại|thủy\\s*đậu|dịch\\s*tả|cúm|sốt\\s*xuất\\s*huyết|chikungunya|đậu\\s*mùa\\s*(?:khỉ)?|sởi|bạch\\s*hầu|ho\\s*gà|uốn\\s*ván|não\\s*mô\\s*cầu|viêm\\s*não|bệnh\\s* truyền\\s*nhiễm|tay\\s*chân\\s*miệng|đau\\s*mắt\\s*đỏ|sốt\\s*rét|viêm\\s*gan|viêm\\s*phổi|nhiễm\\s*trùng|vi\\s*khuẩn|liên\\s*cầu\\s*khuẩn)(?!.*(?:tiếp\\s*tế|cứu\\s*trợ|cô\\s*lập|vùng\\s*lũ|ngập|lụt|hỗ\\s*trợ|khắc\\s*phục|mưa\\s*lũ))\\b',
    '\\b(?:v\\.league|cúp\\s*quốc\\s*gia|hội\\s*quân|tiền\\s*đạo|cầu\\s*thủ|becamex|slna|hagl|cahn|clb|bóng\\s*đá|futsal|seagames|aff\\s*cup|vòng\\s*\\d+|lượt\\s*trận|tỷ\\s*số)(?!.*(?:bão|lũ|thiên\\s*tai|ủng\\s*hộ))\\b',
    '\\b(?:vi\\s*khuẩn\\s*hp|tụ\\s*cầu\\s*vàng|liên\\s*cầu\\s*khuẩn|e\\s*coli|kháng\\s*thuốc|phòng\\s*thí\\s*nghiệm|nuôi\\s*cấy\\s*vi\\s*sinh|kỹ\\s*thuật\\s*di\\s*truyền)\\b',
    '\\b(?:vi\\s*phạm\\s*giao\\s*thông|phạt\\s*nguội|tước\\s*giấy\\s*phép|nồng\\s*độ\\s*cồn|biển\\s*số\\s*xe|đăng\\s*kiểm|xe\\s*xăng|xe\\s*điện|khí\\s*thải|hết\\s*xăng)(?!.*(?:đảo\\s*phú\\s*quý|cô\\s*lập))\\b',
    '\\b(?:vi\\s*phạm\\s*hành\\s*chính|xử\\s*phạt\\s*vi\\s*phạm|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|nồng\\s*độ\\s*cồn|phạt\\s*nguội|tạm\\s*giữ\\s*phương\\s*tiện|xe\\s*quá\\s*khổ|quá\\s*tải)\\b',
    '\\b(?:vietgap|globalgap|haccp|chỉ\\s*dẫn\\s*địa\\s*lý|thương\\s*hiệu\\s*quốc\\s*gia|ocop|mỗi\\s*xã\\s*một\\s*sản\\s*phẩm)\\b',
    '\\b(?:vinfast|bảo\\s*dưỡng|sửa\\s*chữa\\s*xe|khách\\s*hàng|dịch\\s*vụ|hậu\\s*mãi|bảo\\s*hành|tri\\s*ân|khuyến\\s*mại|giảm\\s*giá|voucher|siêu\\s*thị|mua\\s*sắm|cửa\\s*hàng|showroom|đại\\s*lý|phân\\s*phối|bán\\s*lẻ|thương\\s*mại\\s*điện\\s*tử|sàn\\s*giao\\s*dịch|chốt\\s*đơn|livestream\\s*bán\\s*hàng)\\b',
    '\\b(?:việc\\s*nhẹ\\s*lương\\s*cao|lừa\\s*bán|campuchia|casino|biên\\s*giới\\s*tây\\s*nam|xuất\\s*cảnh\\s*trái\\s*phép|người\\s*di\\s*cư|di\\s*cư\\s*bất\\s*hợp\\s*pháp)(?!.*(?:bão|lũ))\\b',
    '\\b(?:viện\\s*kiểm\\s*sát\\s*nhân\\s*dân\\s*tối\\s*cao|tòa\\s*án\\s*nhân\\s*dân\\s*tối\\s*cao|kháng\\s* nghị|giám\\s*đốc\\s*thẩm|tái\\s*thẩm|tố\\s*tụng|án\\s*lệ)\\b',
    '\\b(?:viện\\s*kiểm\\s*sát|cơ\\s*quan\\s*điều\\s*tra|luật\\s*sư|bào\\s*chữa|kháng\\s*cáo|tư\\s*vấn\\s*pháp\\s*luật|hợp\\s*đồng\\s*kinh\\s*tế|thừa\\s*kế|tranh\\s*chấp\\s*tài\\s*sản)\\b',
    '\\b(?:voucher\\s*du\\s*lịch|tour\\s*giá\\s*rẻ|cẩm\\s*nang\\s*điểm\\s*đến|lịch\\s*trình\\s*khám\\s*phá|review\\s*homestay|vé\\s*máy\\s*bay\\s*khứ\\s*hồi|dịch\\s*vụ\\s*nghỉ\\s*dưỡng)\\b',
    '\\b(?:vpn|mã\\s*độc|dữ\\s*liệu\\s*cá\\s*nhân|bảo\\s*mật\\s*thông\\s*tin|lừa\\s*đảo\\s*trực\\s*tuyến|không\\s*gian\\s*mạng|tài\\s*khoản\\s*ngân\\s*hàng|chiếm\\s*đoạt|giả\\s*danh|mạo\\s*danh|đòi\\s*nợ\\s*thuê|tín\\s*dụng\\s*đen|shark\\s*thủy|trương\\s*mỹ\\s*lan|vạn\\s*thịnh\\s*phát|tân\\s*hoàng\\s*minh|scb|flc|thao\\s*túng|chứng\\s*khoán|tiền\\s*ảo|bitcoin|tiền\\s*kỹ\\s*thuật\\s*số)\\b',
    '\\b(?:vách\\s*kính\\s*unitized|hệ\\s*stick|tấm\\s*alu|lam\\s*chắn\\s*nắng|mặt\\s*dựng|kết\\s*cấu\\s*bao\\s*che|vật\\s*liệu\\s*hoàn\\s*thiện|trang\\s*trí\\s*ngoại\\s*thất)\\b',
    '\\b(?:vóc\\s*dáng|sắc\\s*vóc|đường\\s*cong|eo\\s*thon|bí\\s*quyết\\s*giữ\\s*dáng|thời\\s*trang\\s*thảm\\s*đỏ|vẻ\\s*đẹp\\s*không\\s*tuổi)\\b',
    '\\b(?:văn\\s*bằng\\s*hai|đào\\s*tạo\\s*từ\\s*xa|chứng\\s*chỉ\\s*ngắn\\s*hạn|học\\s*phần|tín\\s*chỉ|đăng\\s*ký\\s*môn\\s*học|phòng\\s*đào\\s*tạo|khoa\\s*chuyên\\s*môn)\\b',
    '\\b(?:văn\\s*hóa\\s*giao\\s*thông|văn\\s*hóa\\s*đọc|văn\\s*minh\\s*đô\\s*thị|đạo\\s*đức\\s*nghề\\s*nghiệp|nhân\\s*cách|lối\\s*sống|kỹ\\s*năng\\s*mềm|tư\\s*duy\\s*tích\\s*cực)\\b',
    '\\b(?:văn\\s*hóa\\s*đọc|ngày\\s*hội\\s*sách|ra\\s*mắt\\s*tác\\s*phẩm|độc\\s*giả|tác\\s*giả|nhà\\s*xuất\\s*bản|phê\\s*bình\\s*văn\\s*học|di\\s*sản\\s*chữ\\s*viết)\\b',
    '\\b(?:văn\\s*hóa\\s*ứng\\s*xử|tri\\s*thức\\s*nhân\\s*loại|di\\s*sản\\s*tư\\s*tưởng|triết\\s*lý\\s*giáo\\s*dục|phương\\s*pháp\\s*truyền\\s*thống)\\b',
    '\\b(?:văn\\s*phòng\\s*cho\\s*thuê|co-working\\s*space|khu\\s*phức\\s*hợp|tiện\\s*ích\\s*all-in-one|tòa\\s*nhà\\s*thông\\s*minh|quản\\s*lý\\s*bất\\s*động\\s*sản)\\b',
    '\\b(?:vươn\\s*khơi|bám\\s*biển|đánh\\s*bắt|nuôi\\s*trồng|tái\\s*đàn|vào\\s*vụ|thu\\s*hoạch|giá\\s*thu\\s*mua|hải\\s*sản|thủy\\s*sản)\\b',
    '\\b(?:vải\\s*thiều\\s*lục\\s*ngạn|nhãn\\s*lồng\\s*hưng\\s*yên|rượu\\s*cần\\s*tây\\s*nguyên|sâm\\s*ngọc\\s*linh|bưởi\\s*năm\\s*roi|xoài\\s*cát\\s*hòa\\s*lộc|thương\\s*hiệu\\s*đặc\\s*sản|vùng\\s*trồng\\s*tiêu\\s*chuẩn)\\b',
    '\\b(?:vận\\s*hành\\s*quy\\s*trình|tối\\s*ưu\\s*hệ\\s*thống|tiết\\s*kiệm\\s*chi\\s*phí|năng\\s*suất\\s*lao\\s*động|quản\\s*trị\\s*chuỗi\\s*cung\\s*ứng)\\b',
    '\\b(?:vận\\s*hành\\s*thương\\s*mại|chạy\\s*thử|đóng\\s*điện|thông\\s*xe|khởi\\s*công|động\\s*thổ|khép\\s*kín\\s*đường|vành\\s*đai\\s*\\d+|phân\\s*luồng\\s*giao\\s*thông|xuất\\s*quân\\s*bảo\\s*vệ|duyệt\\s*đội\\s*ngũ|diễn\\s*tập\\s*bảo\\s*vệ)(?!\\s*(?:khắc\\s*phục|sửa\\s*chữa|cầu\\s*tạm|cứu\\s*hộ|thiên\\s*tai))\\b',
    '\\b(?:vận\\s*động\\s*tài\\s*trợ|trao\\s*tặng\\s*nhà\\s*tình\\s*nghĩa|quỹ\\s*bảo\\s*trợ|trợ\\s*giúp\\s*nhân\\s*đạo|chương\\s*trình\\s*thiện\\s*nguyện|tấm\\s*lòng\\s*hảo\\s*tâm)(?!\\s*(?:bão|lũ|thiên\\s*tai|khắc\\s*phục|cứu\\s*trợ|sạt\\s*lở))\\b',
    '\\b(?:vệ\\s*tinh\\s*nhân\\s*tạo|trạm\\s*không\\s*gian|mưa\\s*sao\\s*băng|nhật\\s*thực|nguyệt\\s*thực|kính\\s*thiên\\s*văn|tàu\\s*vũ\\s*trụ)\\b',
    '\\b(?:vệ\\s*tinh\\s*địa\\s*tĩnh|quỹ\\s*đạo\\s*thấp|trạm\\s*điều\\s*khiển\\s*mặt\\s*đất|băng\\s*tần\\s*viễn\\s*thông|sóng\\s*vô\\s*tuyến|truyền\\s*hình\\s*số\\s*vệ\\s*tinh)\\b',
    '\\b(?:vụ|bị)\\s*tai\\s*nạn(?:\\s*nghiêm\\s*trọng)?\\b(?!.*(?:do|vì|bởi)\\s*(?:bão|lũ|thiên\\s*tai|sạt|ngập|mưa))',
    '\\b(?:x\\s*s\\s*m\\s*b|x\\s*s\\s*m\\s*n|x\\s*s\\s*m\\s*t|mega\\s*6/45|power\\s*6/55|max\\s*3d|giải\\s*jackpot|kết\\s*quả\\s*xổ\\s*số\\s*hôm\\s*nay)\\b',
    '\\b(?:xe\\s*bơm\\s*bê\\s*tông|cần\\s*bơm|áp\\s*suất\\s*bơm|vệ\\s*sinh\\s*đường\\s*ống|trạm\\s*trộn\\s*bê\\s*tông|phụ\\s*gia\\s*xây\\s*dựng|nghiệm\\s*thu\\s*cốt\\s*thép)\\b',
    '\\b(?:xe\\s*bồn|xe\\s*tải|đổ\\s*bê\\s*tông|chắn\\s*đường|phế\\s*liệu|mất\\s*an\\s*toàn\\s*giao\\s*thông|vi\\s*phạm\\s*nồng\\s*độ\\s*cồn|tước\\s*bằng\\s*lái|phạt\\s*nguội|xe\\s*đưa\\s*đón|xe\\s*học\\s*sinh)\\b',
    '\\b(?:xe\\s*điện\\s*thông\\s*minh|trạm\\s*sạc\\s*nhanh|pin\\s*lithium|phạm\\s*vi\\s*di\\s*chuyển|xe\\s*tự\\s*lái|adas|tự\\s*động\\s*hóa|triển\\s*lãm\\s*xe\\s*vms)\\b',
    '\\b(?:xem\\s*ngày\\s*tốt|giờ\\s*hoàng\\s*đạo|hướng\\s*xuất\\s*hành|khai\\s*trương\\s*hồng\\s*phát|văn\\s*khấn\\s*cổ\\s*truyền|mâm\\s*cỗ\\s*cúng\\s*rằm)\\b',
    '\\b(?:xo\\s*so|xổ\\s*số|vietlott|xsmb|xsmn|xsmt|kqxs|trúng\\s*số|giải\\s*thưởng\\s*lớn|độc\\s*đắc)\\b',
    '\\b(?:xuất\\s*khẩu\\s*chính\\s*ngạch|tiểu\\s*ngạch|ủy\\s*thác\\s*xuất\\s*khẩu|thủ\\s*tục\\s*hải\\s*quan|logistics\\s*xuất\\s*khẩu|chứng\\s*nhận\\s*kiểm\\s*dịch|quota\\s*thuế\\s*quan)\\b',
    '\\b(?:xác\\s*pháo|pháo\\s*giấy|pháo\\s*điện|pháo\\s*hoa|đốt\\s*pháo)(?!.*(?:cháy|nổ|thương\\s*vong|cứu\\s*hộ))\\b',
    '\\b(?:xác\\s*pháo|pháo\\s*hoa|bắn\\s*pháo\\s*hoa|lễ\\s*hội\\s*pháo\\s*hoa|pháo\\s*tết)\\b',
    '\\b(?:xây\\s*dựng\\s*lại\\s*chợ|quy\\s*hoạch\\s*chợ|tiểu\\s*thương\\s*chợ|ban\\s*quản\\s*lý\\s*chợ|sạp\\s*hàng|ki-ốt|chợ\\s*đầu\\s*mối)(?!.*(?:cháy|hỏa\\s*hoạn|ngập|lũ|bão|tốc\\s*mái|sập|tiếp\\s*tế))\\b',
    '\\b(?:xây\\s*dựng\\s*và\\s*phát\\s*triển|thi\\s*đua\\s*yêu\\s*nước|học\\s*tập\\s*và\\s*làm\\s*theo|dân\\s*vận\\s*khéo|nông\\s*thôn\\s*mới|đô\\s*thị\\s*văn\\s*minh|toàn\\s*dân\\s*đoàn\\s*kết|khắc\\s*phục\\s*khó\\s*khăn|vượt\\s*khó|bứt\\s*phá|tăng\\s*tốc|về\\s*đích|dấu\\s*ấn)(?!.*(?:sau\\s*bão|sau\\s*lũ|thiên\\s*tai|sạt\\s*lở|mưa\\s*lũ|khắc\\s*phục\\s*hậu\\s*quả))\\b',
    '\\b(?:xây\\s*dựng\\s*đội\\s*ngũ|nâng\\s*cao\\s*năng\\s*lực|đào\\s*tạo\\s*nguồn\\s*nhân\\s*lực|chính\\s*sách\\s*đãi\\s*ngộ|môi\\s*trường\\s*chuyên\\s*nghiệp)\\b',
    '\\b(?:xòe\\s*thái|cồng\\s*chiêng|tây\\s*nguyên|ca\\s*trù|hát\\s*xoan|đàn\\s*đá|trình\\s*diễn\\s*nghệ\\s*thuật)\\b',
    '\\b(?:xóa\\s*nhà\\s*tạm|nhà\\s*dột\\s*nát|hỗ\\s*trợ\\s*nhà\\s*ở|nhà\\s*đại\\s*đoàn\\s*kết|an\\s*cư\\s*lạc\\s*nghiệp)(?!\\s*(?:vùng\\s*lũ|rốn\\s*lũ|sau\\s*bão|thiên\\s*tai|sạt\\s*lở|nguy\\s*cơ|di\\s*dời))\\b',
    '\\b(?:xả\\s*nước\\s*đổ\\s*ải|vận\\s*hành\\s*phát\\s*điện|phát\\s*điện\\s*định\\s*kỳ|mực\\s*nước\\s*chết|hồ\\s*thủy\\s*điện\\s*xả\\s*nước(?!\\s*khẩn\\s*cấp))\\b',
    '\\b(?:xả\\s*súng|nổ\\s*súng|đấu\\s*súng|thảm\\s*sát|khủng\\s*bố|đánh\\s*bom|giẫm\\s*đạp|chen\\s*lấn\\s*xô\\s*đẩy|biểu\\s*tình|bạo\\s*loạn)(?!\\s*(?:cứu\\s*trợ|hỗ\\s*trợ))\\b',
    '\\b(?:xổ\\s*số|k\\s*q\\s*x\\s*s|vietlott|lô\\s*đề|soi\\s*cầu|vé\\s*số|thưởng\\s*độc\\s*đắc|trúng\\s*giải\\s*đặc\\s*biệt)\\b',
    '\\b(?:xổ\\s*số|vietlott|trúng\\s*số|giải\\s*đặc\\s*biệt|vé\\s*số|kết\\s*quả\\s*mở\\s*thưởng)\\b',
    '\\b(?:xử\\s*phạt\\s*vi\\s*phạm\\s*hành\\s*chính|tạm\\s*giữ\\s*phương\\s*tiện|nồng\\s*độ\\s*cồn|vi\\s*phạm\\s*tốc\\s*độ|phí\\s*đường\\s*bộ)\\b',
    '\\b(?:xử\\s*phạt|khởi\\s*tố|truy\\s*tố|xét\\s*xử|phiên\\s*tòa|bản\\s*án|tử\\s*hình|chung\\s*thân|án\\s*tù|bị\\s*can|bị\\s*cáo|tòa\\s*án\\s*nhân\\s*dân|điều\\s*tra\\s*viên|tranh\\s*chấp|khiếu\\s*nại|tố\\s*cáo)\\b',
    '\\b(?:á\\s*hậu|hoa\\s*hậu|hoa\\s*khôi|người\\s*đẹp|người\\s*mẫu|showbiz|nhan\\s*sắc|thảm\\s*đỏ|catwalk)\\b',
    '\\b(?:án\\s*mạng|hành\\s*hạ|ngược\\s*đãi|ma\\s*túy|thuốc\\s*lắc|đánh\\s*bạc|sới\\s*bạc|casino|cá\\s*độ|đá\\s*gà|mại\\s*dâm|buôn\\s*lậu|hàng\\s*lậu|hàng\\s*cấm|tàng\\s*trữ|hàng\\s*giả|lừa\\s*đảo|chiếm\\s*đoạt|truy\\s*nã|nghi\\s*phạm|hung\\s*thủ|sát\\s*hại|bạo\\s*hành|bắt\\s*cóc|trục\\s*lợi|giả\\s*chết|karaoke)\\b',
    '\\b(?:án\\s*mạng|trọng\\s*án|truy\\s*nã|bắt\\s*giữ|ma\\s*túy|buôn\\s*lậu|đánh\\s*bạc|mại\\s*dâm|cướp\\s*giật|trộm\\s*cắp|đâm\\s*chém|hỗn\\s*chiến|đua\\s*xe|xả\\s*súng|mua\\s*bán\\s*người|giết\\s*người|hung\\s*thủ|nghi\\s*phạm|khởi\\s*tố|bắt\\s*tạm\\s*giam|điều\\s*tra|tố\\s*cáo|chiếm\\s*đoạt)(?!.*(?:lũ|bão|thiên\\s*tai|cứu\\s*nạn))',
    '\\b(?:án\\s*treo|giảm\\s*nhẹ\\s*hình\\s*phạt|hành\\s*vi\\s*phạm\\s*tội|đồng\\s*phạm|chủ\\s*mưu|tang\\s*vật|hồ\\s*sơ\\s*vụ\\s*án|phiên\\s*tòa\\s*xét\\s*xử)\\b',
    '\\b(?:âm\\s*dương\\s*lịch|lịch\\s*vạn\\s*niên|xem\\s*ngày\\s*tốt|tử\\s*vi|hoàng\\s*đạo|con\\s*giáp|vận\\s*may|tài\\s*lộc)\\b',
    '\\b(?:ùn\\s*tắc\\s*giờ\\s*cao\\s*điểm|kẹt\\s*xe\\s*cục\\s*bộ|phân\\s*luồng\\s*dịp\\s*lễ|bến\\s*xe\\s*đông\\s*nghẹt|người\\s*dân\\s*đổ\\s*về\\s*quê|đường\\s*vành\\s*đai\\s*trên\\s*cao)\\b',
    '\\b(?:ăn\\s*chặn|biển\\s*thủ|trục\\s*lợi|sao\\s*kê|minh\\s*bạch)\\s*(?:từ\\s*thiện|tiền\\s*cứu\\s*trợ|quỹ|tài\\s*khoản)(?!\\s*(?:cho|về|người)\\s*(?:vùng\\s*lũ|bão))\\b',
    '\\b(?:ăn\\s*dặm\\s*kiểu\\s*nhật|ăn\\s*dặm\\s*blw|rèn\\s*con\\s*tự\\s*lập|khủng\\s*hoảng\\s*tuổi\\s*lên\\s*ba|mẹ\\s*bỉm\\s*sữa|chọn\\s*bỉm\\s*sữa|sữa\\s*công\\s*thức|phát\\s*triển\\s*chiều\\s*cao)\\b',
    '\\b(?:đa\\s*dạng\\s*sinh\\s*học|bảo\\s*tồn\\s*động\\s*vật|cá\\s*thể\\s*quý\\s*hiếm|sách\\s*đỏ|thả\\s*về\\s*rừng|vườn\\s*quốc\\s*gia|khu\\s*bảo\\s*tồn|tài\\s*nguyên\\s*sinh\\s*vật)\\b',
    '\\b(?:đan\\s*lát|thêu\\s*ren|móc\\s*len|may\\s*vá|đồ\\s*handmade|quà\\s*tặng\\s*thủ\\s*công|trang\\s*trí\\s*bàn\\s*tiệc|tổ\\s*chức\\s*sự\\s*kiện)\\b',
    '\\b(?:đhđcđ|bải\\s*miễn\\s*hđqt|thành\\s*viên\\s*độc\\s*lập|nhà\\s*đầu\\s*tư\\s*chiến\\s*lược|m&a|sáp\\s*nhập\\s*doanh\\s*nghiệp)\\b',
    '\\b(?:điều\\s*khoản\\s*bất\\s*khả\\s*kháng|ủy\\s*quyền\\s*đại\\s*diện|phụ\\s*lục\\s*hợp\\s*đồng|thanh\\s*lý\\s*hợp\\s*đồng|phát\\s*mại\\s*tài\\s*sản|tố\\s*tụng\\s*trọng\\s*tài|tòa\\s*án\\s*kinh\\s*tế)\\b',
    '\\b(?:điểm\\s*chuẩn|nhập\\s*học|tốt\\s*nghiệp\\s*thpt|ôn\\s*thi|sĩ\\s*tử|trường\\s*chuyên|học\\s*bạ|xét\\s*tuyển\\s*đại\\s*học)\\b',
    '\\b(?:điểm\\s*thu\\s*gom\\s*rác|phí\\s*dịch\\s*vụ\\s*chung\\s*cư|đèn\\s*đường|lát\\s*đá\\s*vỉ\\s*hè|cây\\s*xanh\\s*đô\\s*thị|phun\\s*thuốc\\s*muỗi|diệt\\s*côn\\s*trùng)\\b',
    '\\b(?:đoàn\\s*luật\\s*sư|liên\\s*đoàn\\s*luật\\s*sư|quy\\s*tắc\\s*đạo\\s*đức\\s*nghề\\s*nghiệp|kỷ\\s*luật\\s*luật\\s*sư|tư\\s*vấn\\s*pháp\\s*lý\\s*doanh\\s*nghiệp|hợp\\s*quy\\s*pháp\\s*luật)\\b',
    '\\b(?:đua\\s*ngựa|đua\\s*chó|đua\\s*thuyền\\s*rồng|lễ\\s*hội\\s*đua\\s*thuyền)\\b',
    '\\b(?:đua\\s*thuyền|rowing|canoeing|đấu\\s*kiếm|fencing|cử\\s*tạ|bắn\\s*súng|thể\\s*dục\\s*dụng\\s*cụ|aerobic|điền\\s*kinh|nhảy\\s*cao|nhảy\\s*xa)\\b',
    '\\b(?:đuối\\s*nước|chết\\s*đuối|tắm\\s*suối|tắm\\s*hồ|hồ\\s*bơi|bể\\s*bơi|công\\s*viên\\s*nước|tắm\\s*biển)(?!.*(?:bão|lũ|mưa\\s*lũ|ngập|lũ\\s*quét|sóng\\s*thần|cứu\\s*nạn|mất\\s*tích|vùng\\s*lũ))\\b',
    '\\b(?:đá\\s*quý\\s*lục\\s*yên|trang\\s*sức\\s*cao\\s*cấp|vàng\\s*bạc\\s*đá\\s*quý|kim\\s*cương\\s*nhân\\s*tạo|đá\\s*phong\\s*thủy|ngọc\\s*trai|p\\s*n\\s*j|d\\s*o\\s*j\\s*i|s\\s*j\\s*c)\\b',
    '\\b(?:đám\\s*cưới|hôn\\s*lễ|ly\\s*hôn|ngoại\\s*tình|đánh\\s*ghen|hẹn\\s*hò|chia\\s*tay|tình\\s*trường)\\b',
    '\\b(?:đánh\\s*bạc|sát\\s*phạt|tụ\\s*điểm\\s*đá\\s*gà|xóc\\s*đĩa|lô\\s*đề|ghi\\s*số\\s*đề|tổ\\s*chức\\s*đánh\\s*bạc)\\b',
    '\\b(?:đánh\\s*giá\\s*xe|trải\\s*nghiệm\\s*lái|động\\s*cơ\\s*turbo|mã\\s*lực|mô-men\\s*xoắn|phụ\\s*tùng\\s*chính\\s*hãng|lazang|lốp\\s*xe|ngoại\\s*thất\\s*xe)\\b',
    '\\b(?:đón\\s*tiếp\\s*đoàn|nghị\\s*sự|ký\\s*kết\\s*biên\\s*bản|hợp\\s*tác\\s*chiến\\s*lược|trao\\s*đổi\\s*văn\\s*hóa|ngoại\\s*giao\\s*nhân\\s*dân|thi\\s*đua\\s*khen\\s*thưởng|công\\s*tác\\s*cán\\s*bộ)\\b',
    '\\b(?:đón\\s*đoàn\\s*khách|khách\\s*du\\s*lịch|tham\\s*quan|nghỉ\\s*dưỡng|check-in|sống\\s*ảo)(?!\\s*(?:mắc\\s*kẹt|cô\\s*lập))\\b',
    '\\b(?:đăng\\s*ký\\s*kết\\s*hôn|xác\\s*nhận\\s*độc\\s*thân|thay\\s*đổi\\s*hộ\\s*tịch|trích\\s*lục\\s*bản\\s*sao|công\\s*dân\\s*số)\\b',
    '\\b(?:đăng\\s*ký\\s*thanh\\s*toán|kiểm\\s*tra\\s*số\\s*dư|biến\\s*động\\s*số\\s*dư|lịch\\s*sử\\s*giao\\s*dịch|sao\\s*kê\\s*tài\\s*khoản|chuyển\\s*tiền\\s*nhanh\\s*24/7)\\b',
    '\\b(?:đăng\\s*ký\\s*thương\\s*hiệu|sở\\s*hữu\\s*công\\s*nghiệp|kiểu\\s*dáng\\s*độc\\s*quyền|sách\\s*trắng|báo\\s*cáo\\s*thường\\s*niên|đại\\s*hội\\s*thành\\s*viên|vốn\\s*góp)\\b',
    '\\b(?:đăng\\s*ký\\s*tư\\s*vấn|liên\\s*hệ\\s*quảng\\s*cáo|hợp\\s*tác\\s*truyền\\s*thông|phòng\\s*kinh\\s*doanh|bản\\s*quyền\\s*thuộc\\s*về)\\b',
    '\\b(?:đường\\s*sắt\\s*tốc\\s*độ\\s*cao|cao\\s*tốc\\s*bắc\\s*nam|dự\\s*án\\s*trọng\\s*điểm)(?!.*(?:sạt\\s*lở|ngập|hư\\s*hỏng|thiên\\s*tai))\\b',
    '\\b(?:được\\s*mùa|mất\\s*giá|rớt\\s*giá|giải\\s*cứu\\s*nông\\s*sản|tiêu\\s*thụ\\s*kém|bí\\s*đầu\\s*ra|thương\\s*lái\\s*ép\\s*giá|cam\\s*sành|thanh\\s*long|dưa\\s*hấu|sầu\\s*riêng|vải\\s*thiều|thu\\s*hoạch)(?!\\s*(?:ngập|ung\\s*ứ|hư\\s*hỏng|rụng|gãy\\s*đổ|thiệt\\s*hại|mất\\s*trắng|sau|cứu|chạy)\\s*(?:do|vì|bởi|bão|lũ|thiên\\s*tai|mưa|thời\\s*tiết))\\b',
    '\\b(?:được\\s*mùa|mất\\s*giá|rớt\\s*giá|giải\\s*cứu\\s*nông\\s*sản|tiêu\\s*thụ\\s*kém|bí\\s*đầu\\s*ra|thương\\s*lái\\s*ép\\s*giá|thu\\s*hoạch)(?!.*(?:ngập|ung\\s*ứ|hư\\s*hỏng|rụng|gãy\\s*đổ|thiệt\\s*hại|mất\\s*trắng|sau|cứu|chạy)\\s*(?:do|vì|bởi|bão|lũ|thiên\\s*tai|mưa|thời\\s*tiết))',
    '\\b(?:đại\\s*biểu\\s*quốc\\s*hội|đbqh|hđnd|tiếp\\s*xúc\\s*cử\\s*tri|kỳ\\s*họp\\s*thứ|cử\\s*tri|thảo\\s*luận\\s*tổ|đại\\s*hội\\s*đảng|bầu\\s*cử|nhiệm\\s*kỳ|công\\s*tác\\s*cán\\s*bộ)\\b',
    '\\b(?:đại\\s*hội\\s*chi\\s*bộ|ban\\s*chấp\\s*hành|tiền\\s*phong\\s*gương\\s*mẫu|kiểm\\s*điểm\\s*tự\\s*phê\\s*bình|phát\\s*triển\\s*đảng\\s*viên|kết\\s*nạp\\s*đảng)\\b',
    '\\b(?:đại\\s*hội\\s*cổ\\s*đông|hội\\s*đồng\\s*quản\\s*trị|hđqt|báo\\s*cáo\\s*tài\\s*chính|cổ\\s*phiếu\\s*quỹ|vốn\\s*hóa\\s*thị\\s*trường|niêm\\s*yết\\s*sàn|trái\\s*phiếu\\s*doanh\\s*nghiệp|chốt\\s*quyền\\s*trả\\s*cổ\\s*tức|chi\\s*trả\\s*cổ\\s*tức)\\b',
    '\\b(?:đại\\s*hội\\s*đại\\s*biểu|thường\\s*trực|tiếp\\s*xúc\\s*cử\\s*tri|bầu\\s*cử|ứng\\s*cử|đắc\\s*cử|bổ\\s*nhiệm|miễn\\s*nhiệm|luân\\s*chuyển\\s*cán\\s*bộ|kỷ\\s*luật\\s*đảng|khai\\s*trừ|cách\\s*chức|nghỉ\\s*hưu|về\\s*hưu|hưởng\\s*chế\\s*độ|trao\\s*tặng\\s*huy\\s*hiệu|trao\\s*bằng\\s*khen|tuyên\\s*dương|gương\\s*điển\\s*hình)(?!.*(?:cứu\\s*trợ|ủng\\s*hộ|khắc\\s*phục|bão|lũ|lụt|ngập|sạt\\s*lở|thiên\\s*tai|thăm\\s*hỏi|PCTT|MARD))\\b',
    '\\b(?:đại\\s*hội\\s*đảng\\s*bộ|tạm\\s*dừng\\s*tổ\\s*chức\\s*đại\\s*hội|chuẩn\\s*bị\\s*đại\\s*hội|nhân\\s*sự\\s*đại\\s*hội)\\b',
    '\\b(?:đại\\s*hội\\s*đảng|ban\\s*bí\\s*thư|bộ\\s*chính\\s*trị|ủy\\s*viên\\s*trung\\s*ương|hội\\s*nghị\\s*ban\\s*chấp\\s*hành|điều\\s*động\\s*cán\\s*bộ|bổ\\s*nhiệm|luân\\s*chuyển|phân\\s*công|quy\\s*tập\\s*hài\\s*cốt|nghĩa\\s*trang\\s*liệt\\s*sĩ|trao\\s*huân\\s*chương|cờ\\s*thi\\s*đua|vinh\\s*danh|kỷ\\s*niệm\\s*ngày\\s*thành\\s*lập|quỹ\\s*hưu\\s*trí|bảo\\s*hiểm\\s*hưu\\s*trí)(?!.*(?:ứng\\s*phó|phòng\\s*chống|cứu\\s*hộ|cứu\\s*nạn|thiên\\s*tai|bão|lũ|ngập|sạt\\s*lở|khẩn\\s*cấp|chỉ\\s*đạo|hỗ\\s*trợ|khắc\\s*phục|cứu\\s*trợ|tiếp\\s*nhận|trao\\s*tặng|quyên\\s*góp|sơ\\s*tán|di\\s*dời|công\\s*điện|áp\\s*thấp|mưa\\s*lũ|kết\\s*luận|hậu\\s*quả))\\b',
    '\\b(?:đại\\s*hội\\s*đảng|bầu\\s*cử\\s*quốc\\s*hội|hội\\s*nghị\\s*trung\\s*ương|bổ\\s*nhiệm\\s*cán\\s*bộ|luân\\s*chuyển\\s*nhân\\s*sự|kỷ\\s*luật\\s*đảng|khai\\s*trừ\\s*đảng)\\b',
    '\\b(?:đại\\s*lễ|cầu\\s*an|lễ\\s*chùa|dâng\\s*hương|tâm\\s*linh|ngoại\\s*cảm|gọi\\s*hồn|vong\\s*linh|chất\\s*độc\\s*da\\s*cam|dioxin|truy\\s*tìm\\s*người)\\b',
    '\\b(?:đạo\\s*đức\\s*công\\s*vụ|trách\\s*nhiệm\\s*người\\s*đứng\\s*đầu|kiểm\\s*soát\\s*quyền\\s*lực|phòng\\s*chống\\s*tham\\s*nhũng|lãng\\s*phí)\\b',
    '\\b(?:đạo\\s*đức\\s*pháp\\s*luật|văn\\s*hóa\\s*ngành\\s*y|kỷ\\s*cương\\s*hành\\s*chính|tác\\s*phong\\s*công\\s*vụ|đổi\\s*mới\\s*sáng\\s*tạo|chuyển\\s*đổi\\s*số\\s*quốc\\s*gia)\\b',
    '\\b(?:đấu\\s*thầu\\s*thuốc|vật\\s*tư\\s*y\\s*tế|bảo\\s*hiểm\\s*y\\s*tế|y\\s*đức|quản\\s*lý\\s*bệnh\\s*viện|khám\\s*sức\\s*khỏe\\s*định\\s*kỳ|chăm\\s*sóc\\s*sức\\s*khỏe|đông\\s*y|tây\\s*y|nhiễm\\s*khuẩn)\\b',
    '\\b(?:đẩy\\s*mạnh\\s*tuyên\\s*truyền|xây\\s*dựng\\s*đời\\s*sống|phong\\s*trào\\s*tiên\\s*phong|gương\\s*mẫu\\s*thực\\s*hiện|hoàn\\s*thành\\s*nhiệm\\s*vụ)\\b',
    '\\b(?:đập\\s*hộp|trên\\s*tay|review\\s*chi\\s*tiết|đánh\\s*giá\\s*hiệu\\s*năng|so\\s*sánh\\s*cấu\\s*hình|benchmark|antutu|camera\\s*selfie|màn\\s*hình\\s*amoled|tần\\s*số\\s*quét)\\b',
    '\\b(?:đặt\\s*tên\\s*đường|chỉnh\\s*trang\\s*đô\\s*thị|tu\\s*bổ\\s*di\\s*tích|xây\\s*dựng\\s*công\\s*viên|vườn\\s*hoa|tượng\\s*đài|chiếu\\s*sáng\\s*đô\\s*thị)\\b',
    '\\b(?:đề\\s*tài\\s*nghiên\\s*cứu|công\\s*trình\\s*khoa\\s*học|phát\\s*kiến\\s*vĩ\\s*đại|luận\\s*văn\\s*tốt\\s*nghiệp|chuyên\\s*đề\\s*học\\s*thuật)\\b',
    '\\b(?:đền\\s*hùng|chùa\\s*hương|yên\\s*tử|lễ\\s*hội\\s*truyền\\s*thống|sắc\\s*phong|di\\s*tích\\s*lịch\\s*sử|trẩy\\s*hội)\\b',
    '\\b(?:định\\s*giá\\s*tài\\s*sản|kê\\s*biên\\s*tài\\s*sản|thu\\s*hồi\\s*nợ|tín\\s*dụng\\s*đen|vay\\s*tiền\\s*nhanh|lãi\\s*suất\\s*thả\\s*nổi|đảo\\s*nợ)\\b',
    '\\b(?:định\\s*hướng\\s*giáo\\s*dục\\s*mầm\\s*non|phương\\s*pháp\\s*montessori|reggio\\s*emilia|steam|giáo\\s*dục\\s*trải\\s*nghiệm)\\b',
    '\\b(?:định\\s*hướng\\s*phát\\s*triển|tầm\\s*nhìn\\s*2030|chiến\\s*lược\\s*phát\\s*triển|chuyển\\s*đổi\\s*số\\s*vận\\s*hành|hệ\\s*sinh\\s*thái\\s*khởi\\s*nghiệp)\\b',
    '\\b(?:đối\\s*tượng|truy\\s*quét|trái\\s*phép|buôn\\s*lậu|bắt\\s*giữ|khởi\\s*tố|bắt\\s*tạm\\s*giam|lừa\\s*đảo|chiếm\\s*đoạt\\s*tài\\s*sản|tham\\s*ô|ăn\\s*chặn)(?!.*(?:cứu\\s*nạn|cứu\\s*hộ|cứu\\s*trợ|hỗ\\s*trợ|thiện\\s*nguyện|khắc\\s*phục|thiên\\s*tai))\\b',
    '\\b(?:đồi\\s*capitol|lầu\\s*năm\\s*góc|bầu\\s*cử\\s*tổng\\s*thống|đảng\\s*dân\\s*chủ|đảng\\s*cộng\\s*hòa|donald\\s*trump|joe\\s*biden|kamala\\s*harris)\\b',
    '\\b(?:đồng\\s*bào\\s*công\\s*giáo|đồng\\s*bào\\s*có\\s*đạo|chức\\s*sắc\\s*tôn\\s*giáo|cơ\\s*sở\\s*tôn\\s*giáo|khối\\s*đại\\s*đoàn\\s*kết)(?!.*(?:bão|lũ|thiên\\s*tai|ngập|sập|tốc\\s*mái|hư\\s*hỏng|chia\\s*sẻ|ủng\\s*hộ))\\b',
    '\\b(?:đồng\\s*bộ\\s*dữ\\s*liệu|trợ\\s*lý\\s*ảo|công\\s*dân\\s*số|số\\s*hóa|chuyển\\s*đổi\\s*số|đề\\s*án\\s*nhân\\s*tài)\\b',
    '\\b(?:đồng\\s*tiền\\s*cổ|tem\\s*phi\\s*luật|sưu\\s*tầm\\s*đồ\\s*xưa|đồ\\s*gốm\\s*sứ|giá\\s*trị\\s*thẩm\\s*mỹ|nghệ\\s*nhuật\\s*sắp\\s*đặt)\\b',
    '\\b(?:đổi\\s*tên\\s*trường|thành\\s*lập\\s*trường|sáp\\s*nhập\\s*trường|giải\\s*thể\\s*trường|công\\s*bố\\s*quyết\\s*định)(?!.*(?:bão|lũ|sạt\\s*lở))\\b',
    '\\b(?:đỗ\\s*xe|dừng\\s*xe|lấn\\s*làn|vi\\s*phạm\\s*giao\\s*thông|tước\\s*bằng|giấy\\s*phép\\s*lái\\s*xe|gplx|đăng\\s*kiểm|phạt\\s*nguội|camera\\s*phạt|biển\\s*báo|tín\\s*hiệu\\s*đèn|csgt|cảnh\\s*sát\\s*giao\\s*thông\\s*xử\\s*lý|thổi\\s*nồng\\s*độ\\s*cồn)\\b',
    '\\b(?:độc\\s*lập\\s*tự\\s*do\\s*hạnh\\s*phúc|cộng\\s*hòa\\s*xã\\s*hội\\s*chủ\\s*nghĩa\\s*việt\\s*nam|số\\s*:\\s*\\d+/kh-|số\\s*:\\s*\\d+/qđ-)(?!.*(?:thiên\\s*tai|bão|lũ|sạt\\s*lở|khắc\\s*phục|hỗ\\s*trợ|kinh\\s*phí))\\b',
    '\\b(?:độc\\s*quyền\\s*phân\\s*phối|nhượng\\s*quyền\\s*thương\\s*mại|franchise|chiến\\s*dịch\\s*marketing|định\\s*vị\\s*thị\\s*trường)\\b',
    '\\b(?:động\\s*đất\\s*tại\\s*(?:nhật|đài|tư|trung|mỹ|indo|philip|nepal|thổ|maroc|nam\\s*phi|lào(?!\\s*cai)))\\b',
    '\\b(?:ưu\\s*đãi\\s*độc\\s*quyền|giảm\\s*giá\\s*sốc|khuyến\\s*mãi\\s*khủng|giờ\\s*vàng\\s*giá\\s*tốt|quà\\s*tặng\\s*hấp\\s*dẫn|số\\s*lượng\\s*có\\s*hạn|đặt\\s*hàng\\s*ngay|freeship)\\b',
    '\\b(?:ốc\\s*thanh\\s*vân|showbiz|nghệ\\s*sĩ|hoạt\\s*động\\s*nghệ\\s*thuật|giải\\s*trí|hoa\\s*hậu|người\\s*đẹp|văn\\s*nghệ\\s*quần\\s*chúng|phong\\s*trào\\s*văn\\s*hóa|trò\\s*chuyện\\s*cùng|nhạc\\s*sĩ|tác\\s*giả|nhà\\s*thơ|tổ\\s*quốc\\s*và\\s*người\\s*lính|u22\\s*việt\\s*nam|sea\\s*games|lễ\\s*xuất\\s*quân|concert|cành\\s*cọ\\s*vàng|countdown|tượng\\s*bồ\\s*tát|hồi\\s*hương|xuất\\s*bản\\s*sách|ra\\s*mắt\\s*sách|lịch\\s*sử\\s*truyền\\s*thống|lịch\\s*sử\\s*lực\\s*lượng\\s*vũ\\s*trang)\\b',
    '\\b(?:ứng\\s*phó|phòng\\s*chống|giảm\\s*thiểu)\\s*(?:biến\\s*đổi\\s*khí\\s*hậu|dịch\\s*bệnh|covid|sốt\\s*xuất\\s*huyết|tay\\s*chân\\s*miệng|lạm\\s*phát|suy\\s*thoái|khủng\\s*hoảng|bạo\\s*lực|xâm\\s*hại|tai\\s*nạn|thương\\s*mại|gian\\s*lận|tội\\s*phạm)(?!\\s*(?:và|với)\\s*(?:bão|lũ|thiên\\s*tai|mưa|ngập))\\b', "\\bBulletin\\s*d'information\\b",
    '\\bbão\\s*(?:giá|lửa|đạn|sale|đêm)\\b','\\bchiến\\s*dịch\\s*quang\\s*trung\\b(?!.*(?:nhà|mái\\s*ấm|dựng\\s*lại|lũ|bão|hỗ\\s*trợ|khắc\\s*phục|tái\\s*thiết|ủng\\s*hộ))',
    '\\bgây\\s*bão\\b(?!\\s*(?:lũ|lụt|diện\\s*rộng|biển|cấp|nhiệt\\s*đới))', '\\btăng\\s*trưởng\\s*\\d+\\s*con\\s*số\\b',
    '\\bvòng\\s*xoáy\\s*(?:bất\\s*ổn|xung\\s*đột|bạo\\s*lực|chiến\\s*tranh|nợ\\s*nần|khủng\\s*hoảng)\\b',
    '^(?!.*(?:bão|lũ|mưa|thiên\\s*tai|khắc\\s*phục|cứu\\s*hộ|cứu\\s*nạn|vùng\\s*lũ|đồng\\s*bào)).*\\b(?:ra\\s*quân|lễ\\s*phát\\s*động|hưởng\\s*ứng|phong\\s*trào|dâng\\s*hương|mít\\s*tinh|kỷ\\s*niệm)\\b',
    '^(?:chương\\s*trình\\s*thời\\s*sự)', '^(?:thứ\\s+\\w+,\\s+\\d{1,2}[/-]\\d{1,2}[/-]\\d{4}\\s*[|-])',
    '^(?:tin|thời\\s*sự)\\s*(?:thế\\s*giới|quốc\\s*tế)\\b(?!.*(?:động\\s*đất|sóng\\s*thần|bão|lũ|thiên\\s*tai|thảm\\s*họa|vỡ\\s*đập|cháy|sập|tai\\s*nạn|cứu\\s*hộ|cứu\\s*nạn|cứu\\s*trợ))',
    '^bản\\s*tin\\s*(?:sáng|trưa|tối)\\s+\\d{1,2}[/-]\\d{1,2}',
    'bão\\s*(?:bán\\s*tháo|margin|call\\s*margin|giải\\s*chấp|chứng\\s*khoán|coin|crypto|tỷ\\s*giá|lãi\\s*suất|phốt|drama|diss|cà\\s*khịa|scandal|tin\\s*đồn|thị\\s*phi|tuyển\\s*dụng|sa\\s*thải|layoff|nghỉ\\s*việc|giá|sale|like|sao\\s*kê|chấn\\s*thương|view|comment|order|đơn|hàng|flash\\s*sale|voucher|ddos|spam|bot|an\\s*ninh\\s*mạng|email|tin\\s*nhắn|notification|thất\\s*nghiệp|táp)', 'băng\\s*tần',
    'bắt\\s*sóng', 'bốc\\s*hơi\\s*(?:tài\\s*khoản|vốn\\s*hóa|giá\\s*trị|lợi\\s*nhuận|tài\\s*sản)',
    'cháy\\s*(?:vé|show|concert|liveshow|tour|hàng|kho|đơn|order|slot|suất|deadline|kpi|dự\\s*án|task|việc|túi|tiền|hết\\s*mình|phố|team|máu|đam\\s*mê|quá|rực)',
    'chấn\\s*thương(?:\\s*chỉnh\\s*hình|\\s*thể\\s*thao|\\s*tâm\\s*lý)|giãn\\s*dây\\s*chằng|đứt\\s*dây\\s*chằng',
    'chấn\\s*động\\s*(?:dư\\s*luận|showbiz|làng\\s*giải\\s*trí|MXH|mạng\\s*xã\\s*hội|vbiz)',
    'cú\\s*sốc(?:\\s*thị\\s*trường|\\s*tình\\s*cảm|\\s*giá|\\s*vpop|\\s*showbiz|\\s*giải\\s*trí)',
    'cơn\\s*bão\\s*(?:chứng\\s*khoán|chứng\\s*trường|bán\\s*tháo|lãi\\s*suất|tỷ\\s*giá|khủng\\s*hoảng|suy\\s*thoái|giá\\s*cả|dư\\s*luận|truy\\s*ền\\s*thông|tin\\s*giả|mạng|tin\\s*đồn|showbiz|tài\\s*chính|ngoại\\s*giao|chính\\s*trị|rating|đánh\\s*giá|review|hashtag|trend|viral|quà\\s*tặng|lòng|tố|tát)',
    'cơn\\s*lũ\\s*(?:tin\\s*giả|tội\\s*phạm|rác\\s*thải\\s*số|lượt|fan|tin\\s*nhắn|email|notification|lời\\s*khen|quà|rác)',
    'cơn\\s*lốc\\s*(?:giá|tăng\\s*giá|giảm\\s*giá|khuyến\\s*mãi|sale|flash\\s*sale|voucher|đầu\\s*tư|đường\\s*biên|màu\\s*cam|sân\\s*cỏ|chuyển\\s*nhượng)','cơn\\s*sốt\\s*(?:đất|giá|vé)',
    'dông\\s*bão\\s*(?:cuộc\\s*đời|tình\\s*cảm|nội\\s*tâm|hôn\\s*nhân|gia\\s*đình)',
    'giá\\s*(?:vàng|heo|cà\\s*phê|lúa|xăng|dầu|trái\\s*cây|thanh\\s*long|nông\\s*sản|bất\\s*động\\s*sản|đất|bạc|bạch\\s*kim)',
    r"tâm\s*bão\s*(?:giá|thị\s*trường|tài\s*chính|ngân\s*hàng|bê\s*bối|truyền\s*thông|dư\s*luận|scandal)",
    'giá\\s*thanh\\s*long|lên\\s*kệ\\s*siêu\\s*thị|xuất\\s*khẩu\\s*nông\\s*sản|vé\\s*máy\\s*bay\\s*giá\\s*rẻ|tết\\s*nguyên\\s*đán|thưởng\\s*tết|được\\s*mùa|được\\s*giá|năng\\s*suất\\s*cao', 'how\\s*to.*(?:tutorial|template|branding|customize)',
    'hạ\\s*nhiệt\\s*(?:giá|thị\\s*trường)|tăng\\s*trưởng\\s*kinh\\s*tế|gdp|oda|adb|wb|imf',
    'hạn\\s*hán\\s*(?:bàn\\s*thắng| ghi\\s*bàn|điểm\\s*số|thành\\s*tích|danh\\s*hiệu|ý\\s*tưởng|lời\\s*giải)',
    'khô\\s*hạn\\s*(?:bàn\\s*thắng|ý\\s*tưởng|nội\\s*dung|tương\\s*tác|vốn|tài\\s*chính)', 'không\\s*khí\\s*lạnh\\s*(?:nhạt|lùng|giá)',
    'làn\\s*sóng\\s*(?:đầu\\s*tư|tẩy\\s*chay|sa\\s*thải|viral|trend|covid|dịch\\s*bệnh|công\\s*nghệ|di\\s*cư\\s*số|di\\s*chuyển)(?!\\s*sóng\\s*thần)',
    'lửa\\s*ngùn\\s*ngụt|bà\\s*hỏa|chập\\s*điện(?!\\s*(?:do|vì)\\s*(?:mưa|ngập|bão))',
    'mưa\\s*(?:like|view|comment|đơn\\s*hàng|order|follow|sub|subscriber|deal|voucher|ưu\\s*đãi|quà\\s*tặng|coupon|gạch\\s*đá|lời\\s*khen|feedback|email|tin\\s*nhắn|notification|bàn\\s*thắng|huy\\s*chương)','mất\\s*sóng\\s*(?:wifi|wi-?fi|4g|5g|lte)',
    'ngập\\s*(?:deal|ưu\\s*đãi|voucher|order|đơn|hashtag|trend|quà|rác|nợ|hoa|tràn\\s*(?:cảm\\s*xúc|hạnh\\s*phúc|tình\\s*yêu|niềm\\s*vui))','phủ\\s*sóng',
    'rung\\s*chấn\\s*(?:dư\\s*luận|thị\\s*trường|sân\\s*cỏ|điện\\s*ảnh|chính\\s*trường|vpop)', 'storm\\s+of|flood\\s+of|tsunami\\s+of',
    'sóng\\s*(?:wifi|wi-?fi|4g|5g|lte|di\\s*động|viễn\\s*thông|radio|trending|trend|viral)(?!\\s*thần)',
    'sóng\\s*thần\\s*(?:sa\\s*thải|layoff|bán\\s*tháo|giảm\\s*giá|công\\s*nghệ|pháp\\s*lý|lừa\\s*đảo)',
    'sạt\\s*lở\\s*(?:niềm\\s*tin|danh\\s*tiếng|hình\\s*ảnh|tài\\s*chính|đạo\\s*đức|thị\\s*trường|cổ\\s*phiếu)','sức\\s*mạnh\\s*nội\\s*sinh',
    'trào\\s*lưu\\s*(?:đi\\s*cà\\s*phê|quẩy|sống\\s*ảo|check-in|hot|mới|tik\\s*tok)|trend\\s*(?:mới|hot)', 'trạm\\s*phát\\s*sóng', 'tần\\s*số',
    'việc\\s*nhẹ\\s*lương\\s*cao|bóc\\s*vỏ\\s*tôm|tắt\\s*camera|camera\\s*quay\\s*lén|giải\\s*cứu\\s*(?:rùa|chim|động\\s*vật|thú\\s*quý|tôm\\s*hùm|nông\\s*sản)','vùng\\s*phủ\\s*sóng',
    'vận\\s*hành\\s*chính\\s*quyền\\s*địa\\s*phương\\s*2\\s*cấp|cải\\s*cách\\s*hành\\s*chính|chuyển\\s*đổi\\s*số',
    'đóng\\s*băng\\s*(?:thị\\s*trường|tài\\s*khoản|quan\\s*hệ|tài\\s*sản|dự\\s*án|giá\\s*(?:lợn|heo)|giao\\s*thông|đường|kẹt\\s*xe|cửa\\s*ngõ)',
    'địa\\s*chấn\\s*(?:showbiz|làng\\s*giải\\s*trí|Vpop|V-League|tình\\s*trường|chủ\\s*quyền)',
    'ưu\\s*đãi\\s*khủng|sale\\s*sập\\s*sàn|giá\\s*sốc|khuyến\\s*mãi\\s*khủng|mua\\s*1\\s*tặng\\s*1',
    '办\\w+\\s*假\\s*文\\s*凭|google\\s*bao\\s*ping|google\\s*rank|săn\\s*cá|nổ\\s*hũ|xổ\\s*số|quay\\s*thử|vé\\s*số|vietlott',
    '办国外文凭|QQ\\s*\\d+|fake\\s*diploma|degree|transcript|certificate\\s*online',
    'sập\\s*bẫy\\s*(?:lừa|tín\\s*dụng|đa\\s*cấp)|lừa\\s*đảo|chiếm\\s*đoạt\\s*tài\\s*sản|tội\\s*phạm\\s*công\\s*nghệ',
    'tự\\s*tử|nhảy\\s*cầu|nhảy\\s*lầu|treo\\s*cổ|uống\\s*thuốc\\s*sâu',
    'máy\\s*bay\\s*rơi|rơi\\s*máy\\s*bay|tai\\s*nạn\\s*hàng\\s*không',
    'đình\\s*công|biểu\\s*tình|bạo\\s*loạn|xung\\s*đột',
    r"\b(?:rà\s*soát\s*hộ\s*nghèo|hộ\s*cận\s*nghèo|giải\s*ngân\s*vốn|đầu\s*tư\s*công|đốt\s*pháo|tết\s*nguyên\s*đán|an\s*toàn\s*giao\s*thông|lý\s*lịch\s*tư\s*pháp|thả\s*động\s*vật|an\s*toàn\s*lao\s*động|kháng\s*chiến|lịch\s*sử\s*truyền\s*thống|kỷ\s*niệm|chào\s*tân\s*binh|tân\s*binh|thả\s*cá|phóng\s*sinh|thanh\s*niên\s*xung\s*phong)\b",
    r"\b(?:kỷ\s*luật|khai\s*trừ|cảnh\s*cáo|khiển\s*trách|đảng\s*viên|ban\s*thường\s*vụ|ủy\s*ban\s*kiểm\s*tra|bầu\s*cử|đại\s*biểu|quốc\s*hội|hđnd|ubnd)\b(?!.*(?:khắc\s*phục|hỗ\s*trợ|chỉ\s*đạo|kiểm\s*tra\s*công\s*tác\s*bão|lũ))",
    r"\b(?:dịch\s*bệnh|virus|lây\s*nhiễm|bùng\s*phát\s*dịch|cúm|sốt\s*xuất\s*huyết|tay\s*chân\s*miệng|đậu\s*mùa|covid|legionnaire)\b",
    r"\b(?:an\s*ninh\s*lương\s*thực|xói\s*mòn\s*(?:trật\s*tự|niềm\s*tin|đạo\s*đức|quan\s*hệ)|lương\s*thực\s*toàn\s*cầu)\b",
    r"^bản\s*tin\s*dự\s*báo\s*(?:thủy\s*triều|dòng\s*chảy|sóng|nguồn\s*nước)\s*(?:10\s*ngày|hạn\s*ngắn|hạn\s*dài|tuần\s*tới)(?!\s*.*(?:khẩn\s*cấp|bão|áp\s*thấp))",
    r"\b(?:núi\s*rác|bãi\s*rác|sập\s*núi\s*rác)\b",
    r"\b(?:ngắm|chiêm\s*ngưỡng|tận\s*hưởng|check-in|chụp\s*ảnh|du\s*lịch\s*trải\s*nghiệm|vẻ\s*đẹp|thơ\s*mộng|tựa\s*như|phủ\s*kín)\s*(?:tuyết|hoa|cảnh|mây|băng|sương)\b",
    r"\b(?:tạo|gây)\s*(?:địa\s*chấn|cơn\s*sốt|bão|sóng)\s*(?:tại|trong|trên)\s*(?:giải|vòng|bóng\s*đá|thể\s*thao|sân\s*cỏ|bảng\s*xếp\s*hạng)\b",
    r"\b(?:lịch\s*cấm\s*đường|phân\s*luồng\s*giao\s*thông|hạn\s*chế\s*phương\s*tiện)\s*(?:phục\s*vụ|tại|trong|dịp)\s*(?:lễ|hội|đại\s*hội|diễu\s*binh|diễu\s*hành|A\d+|sự\s*kiện|tết|quốc\s*khánh|SEA\s*Games)\b",
    r"\b(?:thực\s*tập|diễn\s*tập)\s*(?:phương\s*án|kế\s*hoạch)\s*(?:chữa\s*cháy|cứu\s*nạn|cứu\s*hộ|PCCC)\b",
    r"\b(?:tổ\s*liên\s*gia|điểm\s*chữa\s*cháy|mô\s*hình\s*an\s*toàn)\s*(?:PCCC|phòng\s*cháy)\b",
    r"\bbão\s*(?:mùa\s*đông|tuyết)\s*(?:càn\s*quét|tấn\s*công|đổ\s*bộ)\s*(?:châu|mỹ|âu|úc|canada|nhật|hàn|trung)\b",
    r"(?<!\bgiảm\s)(?:lãi\s*hợp\s*nhất|lợi\s*nhuận\s*trước\s*thuế|huy\s*động\s*vốn|tiền\s*gửi\s*tiết\s*kiệm|tổng\s*tài\s*sản\s*(?:vượt|đạt)|dư\s*nợ|nợ\s*xấu)(?!.*(?:thiệt\s*hại|bão|lũ))",
    r"\b(?:hội\s*chợ|triển\s*lãm|trưng\s*bày|xúc\s*tiến\s*thương\s*mại|ra\s*mắt\s*sản\s*phẩm|khai\s*trương|khánh\s*thành)(?!\s*.*(?:cứu\s*trợ|ủng\s*hộ|tái\s*thiết|khắc\s*phục))\b",
    r"\b(?:thực\s*tập|diễn\s*tập)\s*(?:phương\s*án|kế\s*hoạch|chiến\s*đấu|bắn\s*đạn\s*thật|quân\s*sự|phòng\s*thủ|an\s*ninh|tình\s*huống|phòng\s*chống\s*thiên\s*tai|tìm\s*kiếm\s*cứu\s*nạn)(?!\s*.*(?:ứng\s*phó\s*bão|lũ|thiên\s*tai))\b",
    r"\b(?:an\s*toàn\s*giao\s*thông|trật\s*tự\s*giao\s*thông|vi\s*phạm\s*giao\s*thông|ùn\s*tắc\s*giao\s*thông)(?!.*(?:bão|lũ|ngập|sạt|thiên\s*tai))\b",
    r"\b(?:sập|đổ)\s*(?:giàn\s*giáo|cần\s*cẩu|công\s*trình|tường\s*rào|cổng\s*trường)(?!\s*do\s*(?:bão|lũ|giông|lốc|thiên\s*tai))\b",
    r"\b(?:vụ\s*sập\s*cầu|sập\s*cầu)(?!\s*(?:do|vì|trong)\s*(?:bão|lũ|nước\s*chảy|thiên\s*tai))\b",
    r"\bmất\s*liên\s*lạc\s*(?:bí\s*ẩn|với\s*gia\s*đình|bỏ\s*nhà|đi\s*lạc)\b",
    r"\b(?:giải\s*ngân|vốn\s*đầu\s*tư|đầu\s*tư\s*công|giải\s*phóng\s*mặt\s*bằng|đền\s*bù|tái\s*định\s*cư|dự\s*án\s*PPP|CAO\s*TỐC)(?!\s*.*(?:khắc\s*phục|sạt\s*lở|hư\s*hỏng|do\s*bão|do\s*lũ|ứng\s*phó|thiên\s*tai))\b",
    r"\b(?:lịch\s*sử\s*đảng|đảng\s*bộ|tự\s*hào|truyền\s*thống|kỷ\s*niệm|ngày\s*thành\s*lập)(?!\s*.*(?:khắc\s*phục|hỗ\s*trợ|cứu\s*trợ|thiên\s*tai))\b",
]

# Noise contexts that are blocked UNLESS hazard rules are met
CONDITIONAL_VETO = [
    # URBAN / INDUSTRIAL FIRE & EXPLOSION (Non-Forest)
    # Block unless caused by disaster (lightning, storm, etc.)
    r"(?:cháy|hỏa\s*hoạn|bốc\s*cháy|phát\s*hỏa)\s*(?:nhà|căn\s*hộ|chung\s*cư|phòng\s*trọ|quán|karaoke|bar|cửa\s*hàng|ki\s*ốt|xưởng|kho|trụ\s*sở|xe|ô\s*tô|xe\s*máy)(?!\s*(?:do|vì|bởi|tại)\s*(?:bão|lũ|thiên\s*tai|sét\s*đánh|chập\s*điện\s*do\s*mưa|cây\s*đổ|giông\s*lốc))",
    r"(?:nổ|phát\s*nổ)\s*(?:bình\s*gas|khí\s*gas|nồi\s*hơi|lò\s*hơi|trạm\s*biến\s*áp|máy\s*biến\s*áp|pin|ắc\s*quy)(?!\s*(?:do|vì|bởi|tại)\s*(?:bão|lũ|thiên\s*tai|sét\s*đánh))",
    r"(?:PCCC|cảnh\s*sát\s*PCCC|114|đội\s*chữa\s*cháy|lực\s*lượng\s*chữa\s*cháy|dập\s*tắt\s*đám\s*cháy)(?!\s*(?:rừng|thảm\s*thực\s*vật|do\s*sét|trong\s*mưa\s*bão))",
    r"(?:nguyên\s*nhân\s*ban\s*đầu|đang\s*điều\s*tra|khám\s*nghiệm\s*hiện\s*trường|khởi\s*tố\s*vụ\s*án)\s*(?:cháy|nổ)?",
    # REMOVED DUPLICATE: r"lửa\s*ngùn\s*ngụt|bà\s*hỏa|chập\s*điện(?!\s*(?:do|vì)\s*(?:mưa|ngập|bão))",

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
    r"\b(?:đuối\s*nước|tìm\s*thấy\s*thi\s*thể|tử\s*vong\s*(?:thương\s*tâm|do\s*ngạt|ở\s*sông|ở\s*biển|khi\s*tắm))(?!.*(?:bão|lũ|ngập|sạt|thiên\s*tai|tai\s*nạn|vỡ\s*đê|sóng\s*lớn|sét\s*đánh|mưa\s*lũ))\b",
    r"\b(?:tìm\s*kiếm|mất\s*tích)\s*(?:bé\s*trai|bé\s*gái|nam\s*sinh|nữ\s*sinh|thanh\s*niên|người\s*thân)(?!\s*(?:do|vì|trong)\s*(?:lũ|bão|thiên\s*tai|sạt\s*lở|nước\s*cuốn))\b",
    r"\b(?:dự\s*báo\s*thời\s*tiết\s*ngày|thời\s*tiết\s*hôm\s*nay|thời\s*tiết\s*tháng|bản\s*tin\s*thời\s*tiết)(?!.*(?:mưa\s*lũ|ngập|sạt|bão|lốc|mưa\s*đá|hạn\s*mặn|triều\s*cường|rét|lạnh|nhiệt\s*độ))\b",
    # REMOVED DUPLICATE: r"(?:sập|tai\s*nạn)\s*(?:hầm\s*lò|mỏ\s*đá|mỏ\s*than|công\s*trường)(?!\s*(?:do|vì|bởi)\s*(?:bão|lũ|thiên\s*tai|mưa|sạt\s*lở))",

    # ECONOMY & FINANCE
    r"(?<!\bgiảm\s)(?:lãi\s*suất|tín\s*dụng|tỉ\s*giá|ngoại\s*tệ|ngân\s*hàng|chứng\s*khoán|vốn\s*điều\s*lệ|lợi\s*nhuận|doanh\s*thu|vn-index)(?!.*(?:chính\s*sách|hỗ\s*trợ|ưu\s*đãi|khôi\s*phục|khắc\s*phục|giảm|miễn|khoanh\s*nợ|cơ\s*cấu)\s*(?:sau|vùng|cho|người|khách\s*hàng)\s*(?:bão|lũ|thiên\s*tai|ngập|sạt\s*lở|thiệt\s*hại))",
      r"\b(?:cháy\s*lớn|vụ\s*cháy|hỏa\s*hoạn|bà\s*hỏa|thiêu\s*rụi|cháy\s*rụi).*(?:nhà\s*dân|cửa\s*hàng|quán|karaoke|chung\s*cư|xưởng|nhà\s*kho|xe\s*khách|xe\s*tải|ô\s*tô|xe\s*máy|chợ|siêu\s*thị|tầng|phòng|căn\s*hộ)(?!.*(?:rừng|thảm\s*thực\s*vật|do\s*sét|trong\s*bão|mưa))",
    
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
    r"\b(?:trao\s*tặng|tặng\s*quà|khánh\s*thành\s*nhà|nhà\s*tình\s*nghĩa|nhà\s*đại\s*đoàn\s*kết|mái\s*ấm|bò\s*giống|quỹ\s*thiện\s*nguyện|nuôi\s*em|chương\s*trình\s*từ\s*thiện|xây\s*nhà\s*cho\s*người\s*nghèo)(?!.*(?:bão|lũ|lụt|sạt\s*lở|thiên\s*tai|khẩn\s*cấp|cứu\s*trợ|khắc\s*phục|hỗ\s*trợ|tái\s*thiết|bị\s*ảnh\s*hưởng|ngập|giông|lốc))\b",
    r"\b(?:công\s*ty\s*điện\s*lực|pc\s*\w+|đảm\s*bảo\s*điện|cấp\s*điện|hệ\s*thống\s*điện|cắt\s*điện)(?!.*(?:bão|lũ|sạt\s*lở|thiên\s*tai|khắc\s*phục|hư\s*hỏng|gãy|đổ|ngập|sự\s*cố|khôi\s*phục|hỗ\s*trợ))\b",
    r"\b(?:tai\s*nạn\s*giao\s*thông|xe\s*khách\s*(?:bị\s*)?lật|va\s*chạm\s*xe|tông\s*xe|xe\s*tải\s*cán|xe\s*máy\s*đấu\s*đầu|xe\s*đầu\s*kéo|va\s*chạm|đâm\s*liên\s*hoàn|xe\s*tải|xe\s*container|xe\s*buýt|lật\s*xe)(?!.*(?:do\s*bão|do\s*lũ|do\s*sạt\s*lở|do\s*mưa\s*lớn|trong\s*mưa\s*bão|bị\s*lũ\s*cuốn|trôi|ngập))\b",
    r"\b(?:va\s*chạm|đâm\s*nhau|tự\s*gây|mất\s*lái)\s*(?:xe\s*máy|ô\s*tô|xe\s*tải)(?!\s*(?:do|vì|bởi)\s*(?:bão|lũ|mưa|gió|sạt\s*lở|trơn|ngập))",
    r"(?:va\s*chạm\s*liên\s*hoàn|tai\s*nạn\s*giao\s*thông|lật\s*xe|tông\s*xe|xe\s*khách|xe\s*tải|xe\s*ben|lao\s*xuống\s*vực|lao\s*xuống\s*sông)(?!.*(?:do|vì|bởi|tại|xe|đoàn)\s*(?:bão|lũ|sạt\s*lở|mưa|đường\s*trơn|sương\s*mù|gió\s*mạnh|ngập|mưa\s*đá|thời\s*tiết|cứu\s*trợ|thiện\s*nguyện|hỗ\s*trợ))(?!.*(?:đoàn\s*thiện\s*nguyện|xe\s*cứu\s*trợ|hỗ\s*trợ\s*bão|cứu\s*nạn|không\s*qua\s*khỏi|ghe|thuyền|tàu|thủy\s*nạn|chia\s*cắt|tình\s*huống\s*khẩn\s*cấp|hư\s*hỏng\s*cầu|sập\s*cầu))",
    r"(?:xe\s*máy|ô\s*tô|xe\s*khách|xe\s*tải|xe\s*container|xe\s*đầu\s*kéo|xe\s*buýt|tàu\s*thủy|ca\s*nô|tàu\s*cá)\s*(?:lật|lao|tông|đâm|va\s*chạm|bốc\s*cháy|cháy)(?!.*(?:do|vì|bởi|tại|xe|đoàn)\s*(?:bão|lũ|sạt\s*lở|mưa|đường\s*trơn|sương\s*mù|gió\s*mạnh|ngập|mưa\s*đá|thời\s*tiết|cứu\s*trợ|thiện\s*nguyện|hỗ\s*trợ))(?!.*(?:đoàn\s*thiện\s*nguyện|xe\s*cứu\s*trợ|hỗ\s*trợ\s*bão|cứu\s*nạn|chia\s*cắt))",
    r"\b(?:sự\s*cố|hỏng\s*hóc|bảo\s*trì|ngắt\s*điện|mất\s*điện|cắt\s*điện)\s*(?:lưới\s*điện|trạm\s*biến\s*áp|đường\s*dây|cáp\s*quang|internet|hệ\s*thống)(?!.*(?:do|vì|bởi|khắc\s*phục|xuyên\s*đêm)\s*(?:bão|lũ|thiên\s*tai|sạt\s*lở|mưa))\b",
    r"\b(?:khuyến\s*cáo|nhắc\s*nhở|kỹ\s*năng|phòng\s*ngừa|tập\s*huấn)\s*(?:pccc|an\s*toàn|đuối\s*nước|tai\s*nạn)(?!\s*(?:ngập\s*lụt|bão|lũ|thiên\s*tai))\b",
    r"\b(?:chỉ\s*thị|công\s*điện|lệnh\s*của\s*chủ\s*tịch\s*nước|công\s*văn|ban\s*hành\s*văn\s*bản)(?!.*(?:bão|lũ|thiên\s*tai|khắc\s*phục|hỗ\s*trợ|ứng\s*phó|khẩn\s*cấp|hỏa\s*tốc|sạt\s*lở|ngập|lụt|di\s*dời|sơ\s*tán|an\s*toàn|cứu\s*nạn|cứu\s*hộ|thiệt\s*hại|vỡ\s*đê|điện\s*khẩn|triều\s*cường))\b",
    r"\b(?:nuôi\s*tôm|nuôi\s*cá|thủy\s*hải\s*sản|nuôi\s*trồng|trồng\s*trọt|vụ\s*đông\s*xuân|thủy\s*lợi|kênh\s*mương|nạo\s*vét)(?!.*(?:thiệt\s*hại|khắc\s*phục|hỗ\s*trợ|ngập|lũ|hạn|mặn|thiên\s*tai|bão|sạt\s*lở|triều\s*cường|ngập\s*úng|cứu\s*trợ))\b",
    r"\b(?:sư\s*đoàn|trung\s*đoàn|lữ\s*đoàn|tiểu\s*đoàn|quân\s*chủng|tiêm\s*kích|tàu\s*sân\s*bay|tên\s*lửa\s*đạn\s*đạo|tàu\s*ngầm|tác\s*chiến\s*điện\s*tử|chiến\s*lược\s*quân\s*sự)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|cứu\s*hộ|cứu\s*nạn|giúp\s*dân|vùng\s*lũ|bão|thiên\s*tai))",
    r"\b(?:giá\s*vàng\s*hôm\s*nay|vàng\s*miếng\s*sjc|vàng\s*nhẫn|tỷ\s*giá\s*trung\s*tâm|đồng\s*u\s*s\s*d|euro|yên\s*nhật|bảng\s*anh|ngoại\s*tệ|vàng\s*thế\s*giới)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|viện\s*trợ|cứu\s*trợ|thiên\s*tai))",
    r"\b(?:hệ\s*thống\s*pháp\s*luật|văn\s*bản\s*quy\s*phạm|luật\s*sửa\s*đổi|bổ\s*sung|quy\s*định\s*hướng\s*dẫn|nghị\s*định\s*chính\s*phủ|nghị\s*quyết\s*quốc\s*hội)\b(?!.*(?:khắc\s*phục|hỗ\s*trợ|kinh\s*phí|ngân\s*sách|thiên\s*tai|bão|lũ))",
    r"\b(?:venezuela|maduro|trump|biden|is|iraq|libya|gaza|nato|greenland|ukraine|zelensky|putin|nga\s*tấn\s*công|mỹ\s*cấm|tên\s*lửa|đạn\s*đạo|trung\s*tâm\s*quân\s*sự|slovakia|hong\s*kong|campuchia-thái\s*lan|liên\s*minh\s*châu\s*mỹ|trả\s*tự\s*do|bắt\s*giữ\s*tổng\s*thống|lula\s*da\s*silva|trấn\s*áp\s*biểu\s*tình|con\s*tin|tam\s*giác\s*vàng|xe\s*tăng|tên\s*lửa|s-350|starlink|vệ\s*tinh|bộ\s*ba\s*hạt\s*nhân|quan\s*hệ\s*với\s*triều\s*tiên|cuộc\s*chiến\s*nga|caracas|ngừng\s*bắn|chiến\s*sự|bụi\s*mịn|hàn\s*quốc|thái\s*lan|bangkok|ấn\s*độ|iran|sng|kherson|gaza|israel|thụy\s*sĩ|cảng\s*vụ\s*hàng\s*không|ngoại\s*trưởng|nigeria|greenland|eu|liên\s*minh\s*châu\s*âu|australia|mexico|syria|philippines|nhật\s*bản|hàn\s*quốc|trung\s*quốc)(?!\b\sBản\s*tin\s*quốc\s*tế)\b(?!.*(?:hỗ\s*trợ|khắc\s*phục|viện\s*trợ|cứu\s*trợ|đóng\s*góp|ủng\s*hộ|thiên\s*tai|bão|lũ|sạt|ngập|triều\s*cường|biển\s*đông|bão\s*số))",
    r"\b(?:va\s*chạm\s*với\s*đoàn\s*tàu|va\s*chạm\s*tàu\s*hỏa|ô\s*tô\s*lao\s*vào\s*nhà|xe\s*tải\s*lao\s*vào\s*nhà|xe\s*tải\s*đâm\s*nhà|xe\s*khách\s*lao\s*xuống\s*vực)(?!.*(?:do|vì|bởi)\s*(?:bão|lũ|sạt\s*lở|mưa|ngập))",
    r"\b(?:giảm\s*mạnh|giảm\s*sâu)\b(?!.*(?:nhiệt\s*độ|áp\s*suất|mực\s*nước|khí\s*quyển))",
    r"\b(?:chất\s*độc\s*da\s*cam|nạn\s*nhân\s*da\s*cam|dioxin)",
    r"\b(?:hiến\s*máu|giọt\s*máu\s*hồng|ngân\s*hàng\s*máu)(?!.*(?:trong\s*lũ|giúp\s*dân\s*lũ|cứu\s*trợ\s*thiên\s*tai))",
    r"\b(?:bom\s*mìn|vật\s*liệu\s*nổ|ra\s*phá\s*bom)(?!.*(?:lũ|sạt|trôi|lộ\s*thiên|phát\s*hiện\s*sau))",
    r"\b(?:lao\s*ô\s*tô|tông\s*xe|va\s*chạm\s*xe)(?!.*(?:bão|lũ|sạt|trôi|ngập|thiên\s*tai))",
    r"\b(?:mâu\s*thuẫn\s*cá\s*nhân|xô\s*xát|đánh\s*nhau|hỗn\s*chiến)",
    r"\b(?:đại\s*dương\s*hấp\s*thụ\s*nhiệt|biến\s*đổi\s*khí\s*hậu\s*toàn\s*cầu)(?!.*(?:bão|lũ|việt\s*nam|ảnh\s*hưởng|nguy\s*cơ))",
    r"\b(?:kết\s*quả\s*xổ\s*số|xsmb|xsmn|xsmt|vietlott|quay\s*số|trúng\s*thưởng|giải\s*đặc\s*biệt)(?!.*(?:ủng\s*hộ|cứu\s*trợ))",
    r"\b(?:ngộ\s*độc\s*thực\s*phẩm|an\s*toàn\s*vệ\s*sinh|rối\s*loạn\s*tiêu\s*hóa|ngộ\s*độc\s*rượu)",
    r"\b(?:lebanon|beirut|hezbollah|israel|gaza|tel\s*aviv|iran|tehran|trung\s*đông|xung\s*đột\s*vũ\s*trang|iraq|syria|yemen|kabul|afghanistan|ukraine|kiev|moscow|nga)(?!.*(?:công\s*dân\s*việt\s*nam|bảo\s*hộ\s*công\s*dân|viện\s*trợ|cứu\s*trợ))",
    r"\b(?:bến\s*phà|hoạt\s*động\s*bến\s*phà|phà\s*ngang\s*sông)(?!.*(?:do|vì|bởi|khắc\s*phục|tạm\s*dừng)\s*(?:bão|lũ|thiên\s*tai|sạt\s*lở|mưa|nước\s*dâng))\b",
    r"\b(?:tung\s*gói|gói)\s*(?:hỗ\s*trợ|khuyến\s*mãi|kích\s*cầu)\s*(?:khách\s*hàng|dịch\s*vụ|du\s*lịch|xe|vay|tín\s*dụng)\b",
    r"\b(?:tai\s*nạn|va\s*chạm|tông\s*xe|lật\s*xe|đâm\s*xe)\s*(?:giao\s*thông|liên\s*hoàn|trên\s*cao\s*tốc|xe\s*máy|xe\s*khách|xe\s*tải)(?!.*(?:do|vì|trong|bởi)\s*(?:bão|lũ|mưa|sạt\s*lở|thiên\s*tai|ngập))",
    r"\b(?:kỳ\s*nghỉ|dịp\s*lễ|nghỉ\s*lễ)\s*(?:30\/4|1\/5|2\/9|tết)\b",
    r"\b(?:thủ\s*tục|hồ\s*sơ|quy\s*trình)\s*(?:cấp\s*phép|đăng\s*ký|phê\s*duyệt|nghiệm\s*thu)(?!.*(?:khắc\s*phục|hỗ\s*trợ|cứu\s*trợ))\b",
    r"\b(?:lễ|ký\s*kết)\s*(?:văn\s*bản|quy\s*chế|hợp\s*tác|hiệp\s*định|hiệp\s*đồng)(?!.*(?:hỗ\s*trợ|khắc\s*phục|cứu\s*trợ))\b",
]

# JUNK PATTERNS (For is_junk_title in nlp.py)
JUNK_TITLE_PATTERNS = [
    r"kết quả tin tức cho từ khóa",
    r"trang chủ - ",
    r"tìm kiếm - ",
    r"kết quả tìm kiếm",
    r"search results for",
    r"news results for",
    r"từ khóa:",
    r"^từ khóa\s*:",
    r"^dự\s*báo\s*thời\s*tiết\s*ngày\s*\d+\/\d+\s*-\s*vtc\s*news$",
    r"^thời\s*tiết\s*ngày\s*\d+\s*tháng\s*\d+$",
]

RE_FLAGS = re.IGNORECASE | re.VERBOSE | re.DOTALL

@lru_cache(maxsize=128)
def v_safe(p: str) -> str:
    """
    Ensure Regex is safe for re.VERBOSE.
    If single-line, replaces spaces with \\s+ to avoid being ignored.
    If multi-line, keeps as is.
    Bypass look-behind/look-ahead to avoid variable-width errors.
    """
    if "\n" in p: return p
    if "(?<!" in p or "(?<=" in p: return p
    return p.replace(" ", r"\s+")

def build_mega_re(pats: List[str]):
    """
    Build accented mega-regex from a list of patterns.
    """
    if not pats: return None
    pats_v = [v_safe(p) for p in pats]
    try:
        return re.compile("|".join(f"(?:{p})" for p in pats_v), RE_FLAGS)
    except Exception:
        return None

# Compile Veto and Junk Regexes once
ABSOLUTE_VETO_RE = build_mega_re(ABSOLUTE_VETO)
CONDITIONAL_VETO_RE = build_mega_re(CONDITIONAL_VETO)
JUNK_TITLE_RE = build_mega_re(JUNK_TITLE_PATTERNS)

# Weak noise indicators that penalize score but don't force veto
SOFT_NEGATIVE = [
    r"(?:kỳ\s*họp|phiên\s*họp|hội\s*nghị|đại\s*hội|văn\s*phòng|ubnd|hđnd|mttq)\s*(?:đảng|đảng\s*bộ|hđnd|quốc\s*hội|chi\s*bộ|cử\s*tri|toàn\s*quốc|tổng\s*kết|sơ\s*tết)",
    r"tiếp\s*xúc\s*cử\s*tri|chất\s*vấn|giải\s*trình|bầu\s*cử|ứng\s*cử",
    r"(?:bổ\s*nhiệm|miễn\s*nhiệm|điều\s*động|luân\s*chuyển|kỷ\s*luật|kiểm\s*tra|giám\s*sát)(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn|thiên\s*tai|bão|lũ|sạt\s*lở))",
    r"nghị\s*quyết|nghị\s*định|thông\s*tư|quyết\s*định|chỉ\s*thị(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn))",
    r"trợ\s*cấp\s*thất\s*nghiệp|đạt\s*chuẩn\s*nông\s*thôn\s*mới|nông\s*thôn\s*mới\s*nâng\s*cao(?!.*(?:ứng\s*phó|phòng\s*chống|cứu\s*hộ|cứu\s*nạn|cứu\s*người|thiên\s*tai|bão|lũ|sạt\s*lở|ngập))",
    r"bản\s*tin\s*(?:cuối\s*ngày|sáng|trưa|tối)|điểm\s*tin|tin\s*trong\s*nước|tin\s*quốc\s*tế",
    r"(?:tốt\s*nghiệp|nhận\s*học\s*bổng|tuyển\s*sinh.*đại\s*học)(?!.*(?:sau\s*lũ|vùng\s*lũ))",
    r"giải\s*thưởng|vinh\s*danh|trao\s*huân\s*chương|cờ\s*thi\s*đua|kỷ\s*niệm|lễ\s*kỷ\s*niệm|văn\s*hóa\s*văn\s*nghệ|biểu\s*diễn",
    r"khởi\s*công|khánh\s*thành|nghiệm\s*thu(?!.*(?:kè|đê|hồ|đập|thủy\s*lợi|thoát\s*nước|chống\s*ngặp|chống\s*sạt\s*lở|thiên\s*tai|tái\s*thiết|khắc\s*phục|sửa\s*chữa|hư\s*hỏng|bão|lũ|ngập|nhà\s*tình\s*nghĩa))",
    r"(?:thanh\s*niên|nữ\s*sinh|học\s*sinh)\s*mất\s*tích(?!.*(?:mưa\s*lũ|lũ|bão|nước\s*cuốn|rơi\s*xuống|đắm\s*thuyền|chìm\s*tàu|tìm\s*thấy\s*thi\s*thể))",
    r"về\s*agpc|giới\s*thiệu\s*chung|chức\s*năng\s*nhiệm\s*vụ|cơ\s*cấu\s*tổ\s*chức|sơ\s*đồ\s*tổ\s*chức",
    r"chống\s*sét\s*(?:cảm\s*ứng|lan\s*truyền|van|chủ\s*động)|kim\s*thu\s*sét|hệ\s*thống\s*tiếp\s*địa",
    r"luyện\s*tập\s*phương\s*án\s*cứu\s*hộ|diễn\s*tập\s*thực\s*binh|hội\s*thao\s*nghiệp\s*vụ",
    r"thành\s*tích\s*xuất\s*sắc|thi\s*đua\s*lập\s*thành\s*tích|phát\s*động\s*phong\s*trào|khen\s*thưởng|tuyên\s*dương",
    r"tin\s*thế\s*giới|thế\s*giới\s*24h|tin\s*nhanh\s*quốc\s*tế|tiêu\s*điểm\s*quốc\s*tế",
    r"\b(?:tập\s*huấn|diễn\s*tập|hội\s*nghị|triển\s*khai\s*nhiệm\s*vụ|quán\s*triệt|phổ\s*biến\s*kiến\s*thức|trải\s*nghiệm|tuyên\s*truyền|thực\s*tập\s*phương\s*án|hội\s*thao|tổng\s*duyệt|giải\s*việt\s*dã|giải\s*chạy)\b",
    r"\bjiải\s*bài\s*toán\s*(?:hạn|mặn|lũ|ngập|ách\s*tắc)\b",
    r"\bchấm\s*dứt\s*(?:nắng\s*nóng|rét|mưa\s*lớn|đợt\s*lạnh)\b",
    r"\b(?:phê\s*duyệt|ban\s*hành|điều\s*chỉnh|thông\s*qua)\s*(?:phương\s*án|kế\s*hoạch|chương\s*trình|luật)\s*(?:ứng\s*phó|phòng\s*chống|giảm\s*nhẹ|tình\s*trạng)\b",
    r"\b(?:điểm\s*tin|tin\s*tức|tổng\s*hợp)\s*(?:tuần|tháng|ngày)\b",
    r"\b(?:hướng\s*dẫn|kỹ\s*năng)\s*(?:lái\s*xe|tham\s*gia\s*giao\s*thông|an\s*toàn|sơ\s*cấp\s*cứu|bơi\s*lội|phòng\s*cháy)\b",
    r"\b(?:tổng\s*đài|hotline)\s*(?:111|112|113|114|115|cskh)\b",
    r"\b(?:văn\s*hóa|an\s*toàn)\s*giao\s*thông\b",
]
SOFT_NEGATIVE_RE = build_mega_re(SOFT_NEGATIVE)

# PLANNING & PREPARATION
# Keywords used to identify preparedness activities (early signals or drills)
PLANNING_PREP_KEYWORDS = [
    r"chuẩn\s*bị", r"phương\s*án", r"kế\s*hoạch", r"kịch\s*bản", r"ứng\s*phó", 
    r"sẵn\s*sàng", r"chủ\s*động", r"phòng\s*ngừa", r"phòng\s*chống", r"triển\s*khai",
    r"đối\s*phó", r"tình\s*huống", r"giả\s*định", r"diễn\s*tập", r"huấn\s*luyện"
]
RE_PLANNING = re.compile("|".join(rf"(?:{v_safe(p)})" for p in PLANNING_PREP_KEYWORDS), re.IGNORECASE)




SCORING_WEIGHTS = {
    "vip_boost": 30.0,            # Force pass (> 15.0)
    "whitelist_boost": 10.0,      # Boost for critical whitelisted actions (xả lũ, sơ tán)
    "high_priority_boost": 1.2,    # Tier 1-3
    "medium_priority_boost": 0.6,  # Tier 4 / Disruption
    "multi_hazard_bonus": 1.0,     # Mentioning 2+ hazards
    "triple_hazard_bonus": 0.5,    # Mentioning 3+ hazards
    "title_hazard_boost": 2.0,     # Hazard found in title
    "stage_recovery_bonus": 2.5,
    "stage_forecast_bonus": 2.5,
    "context_hit_weight": 0.5,     # Points per context keyword match
    "context_max_bonus": 3.0,
    "gold_title_geo_boost": 8.0,   # [Hazard in Title] + [Location in Title]
    "gold_trusted_warning": 6.0,   # Trusted source + Forecast/Warning
    "gold_standard_high": 5.0,     # Rule + Location + (Impact OR Agency)
    "gold_standard_med": 2.5,
    "gold_trusted_breaking": 3.0,  # Trusted + Rule + Location (No stats yet)
    "risk_level_high_boost": 3.0,  # Warning Level 3+
    "risk_level_low_boost": 1.5,   # Warning Level 1-2
    "extreme_rainfall_150_bonus": 1.5,
    "extreme_rainfall_300_bonus": 1.0,
    "extreme_wind_bonus": 2.0,
    "extreme_quake_bonus": 2.5,
    "high_casualty_threshold_boost": 2.0, # 5+ deaths/missing
    "silent_hazard_title_boost": 3.5, # Impact words in title without hazard
    "title_action_boost": 4.0,     # Localized evacuation/aid in title
    "penalty_no_hazard": -10.0,     # No hazard + No casualty
    "high_casualty_boost": 2.0,    # 5+ deaths/missing regardless of rule
    "penalty_ambiguous": -5.0,     # No hazard + few deaths
    "penalty_cond_veto": -50.0,    # Accident/Fire with no hazard rule - KILL IT
    "penalty_title_clickbait": -5.0, # Major hazard title but no body impact
    "authority_level_high_bonus": 4.0, # Level 3 (Gov/Official)
    "authority_level_med_bonus": 1.5,  # Level 2 (Trusted/Verified)
    "penalty_international": -15.0,    # International news with no VN location
    "penalty_neighbor_country": -4.0, # Neighboring countries (Lào, Cam, China, Thai) - milder penalty
    "penalty_drill_exercise": -20.0,    # Training, drills, sports -> High penalty to avoid noise
    "penalty_soft_negative": -10.0,     # General noise/ambiguous context
    "weight_rule": 5.0,               # Base score for disaster rule match
    "weight_impact": 5.0,             # Base score for impact/metrics
    "weight_agency": 2.5,             # Base score for official agency mention
    "weight_source": 0.5,             # Multiplier for source keyword hits
    "weight_source_max": 4.0,         # Cap for source keyword score
    "weight_province": 3.0,           # Base score for location/province match
    "threshold_approve_strict": 12.0, # Higher bar for generic titles
    "threshold_approve_strong": 10.0, # Lower bar for strong titles (VIP/Hazard-in-title)
    "threshold_pass": 11.0,           # Threshold for automatic approval
    "threshold_official": 9.5,        # Lower threshold for official/trusted sources
    "threshold_pending": 10.0,        # Threshold for 'Pending Review' status
    "threshold_forecast": 10.5        # Threshold for Forecast/Warning 'Pending'
}

# CRITICAL ACTIONS WHITELIST
# Phrases that bypass certain vetoes (e.g. accidents) because they are definitely disaster-related
WHITELIST_TERMS = (
    r"(?:xả\s*lũ|xả\s*đáy|sơ\s*tán\s*dân|di\s*dời\s*dân|di\s*dời\s*khẩn\s*cấp|"
    r"(?:cứu\s*hộ|cứu\s*nạn)\s*(?:thiên\s*tai|bão|lũ|mưa|sạt\s*lở|ngập|lụt|trôi|quét|cháy\s*rừng|hạn\s*mặn|sóng\s*thần)|"
    r"khắc\s*phục\s*hậu\s*quả\s*(?:thiên\s*tai|bão|lũ|mưa|sạt\s*lở)|"
    r"hỗ\s*trợ\s*khẩn\s*cấp\s*(?:vùng\s*lũ|thiên\s*tai|bão\s*lụt)|nhà\s*chống\s*lũ|nhà\s*phao|hỗ\s*trợ\s*đồng\s*bào\s*vùng\s*lũ|"
    r"ban\s*chỉ\s*huy\s*pctt|tìm\s*kiếm\s*cứu\s*nạn\s*(?:người\s*mất\s*tích|nạn\s*nhân\s*do\s*lũ|trên\s*biển)|"
    r"đưa\s*thuyền\s*lên\s*bờ|trú\s*tránh\s*bão|neo\s*đậu\s*tàu\s*thuyền|"
    r"chi\s*viện\s*(?:vùng\s*lũ|chống\s*bão)|xe\s*cứu\s*trợ\s*(?:bão|lũ)|hàng\s*cứu\s*trợ|tiếp\s*tế\s*vùng\s*lũ|phương\s*tiện\s*cứu\s*trợ|"
    r"người\s*dân\s*vùng\s*lũ|bà\s*con\s*vùng\s*lũ|khám\s*chữa\s*bệnh\s*vùng\s*lũ|tiêm\s*chủng\s*vùng\s*lũ|vắc\s*xin\s*vùng\s*lũ|"
    r"ứng\s*cứu\s*viễn\s*thông\s*bão\s*lũ|khôi\s*phục\s*liên\s*lạc\s*sau\s*bão|khôi\s*phục\s*sản\s*xuất\s*sau\s*lũ|"
    r"cấm\s*lưu\s*thông\s*do\s*ngập|cấm\s*lưu\s*thông\s*do\s*sạt|phân\s*luồng\s*giao\s*thông\s*do\s*ngập|"
    r"khắc\s*phục\s*sạt\s*trượt|thông\s*tuyến\s*sau\s*sạt|khởi\s*công\s*nhà\s*vùng\s*lũ|xây\s*dựng\s*nhà\s*vùng\s*lũ|sửa\s*chữa\s*nhà\s*vùng\s*lũ|"
    r"công\s*trình\s*cấp\s*thiết\s*phòng\s*chống|uav\s*cứu\s*trợ|trực\s*thăng\s*cứu\s*trợ|tàu\s*hỏa\s*cứu\s*trợ|"
    r"xâm\s*thực\s*bờ\s*biển|sạt\s*lở\s*bờ\s*sông|sạt\s*lở\s*bờ\s*biển|"
    r"gặt\s*lúa\s*chạy\s*lũ|thu\s*hoạch\s*chạy\s*lũ|bảo\s*vệ\s*đê\s*kè|sửa\s*chữa\s*hư\s*hỏng\s*do\s*bão|"
    r"học\s*sinh\s*nghỉ\s*học\s*tránh\s*bão|cho\s*học\s*sinh\s*nghỉ\s*tránh\s*lũ|trường\s*ngập\s*lụt|"
    r"sách\s*vở\s*cho\s*vùng\s*lũ|hỗ\s*trợ\s*giáo\s*dục\s*vùng\s*lũ|bão\s*vào\s*biển\s*đông|bão\s*đổ\s*bộ|"
    r"cấm\s*biển|lệnh\s*cấm\s*biển|cấm\s*phương\s*tiện\s*ra\s*khơi|nước\s*cuốn\s*trôi\s*người|"
    r"xuất\s*quân\s*hỗ\s*trợ\s*nhân\s*dân|bộ\s*đội\s*vượt\s*lũ|công\s*an\s*giúp\s*dân\s*chống\s*bão|"
    r"cảnh\s*sát\s*hỗ\s*trợ\s*người\s*dân|cảnh\s*sát\s*giúp\s*dân\s*trong\s*lũ|cảnh\s*sát\s*phòng\s*chống\s*thiên\s*tai|"
    r"chiến\s*dịch\s*quang\s*trung|hỗ\s*trợ\s*.*thiên\s*tai|khắc\s*phục\s*.*thiên\s*tai|"
    r"thiệt\s*hại\s*do\s*thiên\s*tai|tình\s*nguyện\s*viên\s*.*vùng\s*lũ|hỗ\s*trợ\s*.*vùng\s*lũ|người\s*dân\s*.*vùng\s*lũ|"
    r"cứu\s*trợ\s*.*vùng\s*lũ|tìm\s*kiếm\s*.*mất\s*tích|tìm\s*kiếm\s*.*nạn\s*nhân|"
    r"thi\s*thể\s*.*trôi\s*dạt|mất\s*tích\s*.*trên\s*biển|tàu\s*cá\s*.*mất\s*tích|ngư\s*dân\s*.*mất\s*tích|"
    r"cứu\s*nạn\s*.*trên\s*biển|lũ\s*quét\s*.*sạt\s*lở|sạt\s*lở\s*.*vùi\s*lấp|"
    r"di\s*dời\s*.*khẩn\s*cấp|sơ\s*tán\s*.*dân|công\s*điện\s*.*khẩn|"
    r"hoàn\s*lưu\s*.*bão|ảnh\s*hưởng\s*.*bão|chủ\s*động\s*ứng\s*phó|thủy\s*điện\s*.*xả\s*lũ|"
    r"ứng\s*phó\s*bão\s*số|ứng\s*phó\s*áp\s*thấp|khẩn\s*cấp\s*ứng\s*phó|"
    r"chiến\s*sĩ\s*hỗ\s*trợ\s*đồng\s*bào|chiến\s*sĩ\s*giúp\s*dân\s*gặt\s*lúa|"
    r"tình\s*(?:trạng|huống)\s*khẩn\s*cấp\s*về\s*(?:thiên\s*tai|bão|lũ|sạt|ngập|lụt|hạn|mặn|cháy\s*rừng)|"
    r"di\s*dời\s*khẩn\s*cấp\s*dân|tái\s*thiết\s*sau\s*thiên\s*tai|khởi\s*công\s*nhà\s*tình\s*nghĩa\s*vùng\s*lũ|"
    r"sửa\s*chữa\s*hồ\s*đập|bch\s*phòng\s*chống|ban\s*chỉ\s*huy\s*tkcn|"
    r"diễn\s*tập\s*phòng\s*chống\s*thiên\s*tai\s*quy\s*mô\s*lớn|"
    r"công\s*an\s*cứu\s*nạn\s*trong\s*lũ|chiến\s*sĩ\s*cứu\s*nạn|binh\s*sĩ\s*cứu\s*hộ|csgt\s*giúp\s*dân\s*trong\s*mưa\s*bão|"
    r"xây\s*nhà\s*sau\s*lũ|sửa\s*nhà\s*sau\s*lũ|nhà\s*tình\s*nghĩa\s*cho\s*vùng\s*lũ|"
    r"nghỉ\s*học\s*tránh\s*bão|nghỉ\s*học\s*chống\s*bão|nghỉ\s*học\s*do\s*mưa\s*lũ|"
    r"ứng\s*trực\s*bão\s*lũ|trực\s*ban\s*thiên\s*tai|đảm\s*bảo\s*an\s*toàn\s*hồ\s*đập|"
    r"tạm\s*dừng\s*du\s*lịch\s*do\s*bão|công\s*bố\s*tình\s*huống\s*khẩn\s*cấp|viện\s*trợ\s*khẩn\s*cấp\s*thiên\s*tai|"
    r"kêu\s*cứu\s*khẩn\s*cấp\s*trong\s*lũ|ứng\s*dụng\s*cứu\s*nạn|nâng\s*cao\s*năng\s*lực\s*phòng\s*chống\s*thiên\s*tai|"
    r"bị\s*cô\s*lập\s*do\s*lũ|khắc\s*phục\s*hậu\s*quả\s*thiên\s*tai|triển\s*khai\s*ứng\s*phó\s*bão|"
    r"an\s*toàn\s*hồ\s*chứa|dự\s*trữ\s*nước\s*chống\s*hạn|"
    r"du\s*khách\s*mắc\s*kẹt\s*do\s*mưa\s*lũ|giải\s*cứu\s*du\s*khách\s*mắc\s*kẹt|"
    r"chủ\s*động\s*ứng\s*phó\s*mưa\s*lũ|huy\s*động\s*lực\s*lượng\s*chống\s*bão|"
    r"bão\s*số\s*\d+|vận\s*chuyển\s*hàng\s*cứu\s*trợ|di\s*dời\s*dân\s*tránh\s*bão|"
    r"mái\s*ấm\s*tình\s*thương\s*vùng\s*lũ|dựng\s*nhà\s*cho\s*đồng\s*bào\s*lũ\s*lụt|"
    r"vùng\s*bị\s*thiệt\s*hại\s*do\s*lũ|chiến\s*dịch\s*quang\s*trung|thư\s*kêu\s*gọi\s*ủng\s*hộ\s*bão\s*lụt|"
    r"(?:ngân\s*hàng|tổ\s*chức\s*tín\s*dụng)\s*(?:giảm|miễn|hỗ\s*trợ)\s*(?:lãi\s*suất|nợ)\s*(?:cho|với)\s*(?:người\s*dân|khách\s*hàng)\s*(?:bị|vùng)\s*(?:thiên\s*tai|bão|lũ|sạt\s*lở)|"
    r"bom\s*(?:mìn)?\s*(?:lộ\s*thiên|phát\s*hiện)\s*(?:sau|do)\s*(?:mưa|lũ|sạt\s*lở)|"
    r"sét\s*đánh\s*(?:chết|tử\s*vong)\s*người|"
    r"tin\s*dự\s*báo\s*thời\s*tiết\s*nguy\s*hiểm|dự\s*báo\s*mưa\s*lũ|có\s*khả\s*năng\s*xảy\s*ra\s*lũ\s*quét|"
    r"đợt\s*mưa\s*lũ\s*mới|xây\s*mới\s*nhà\s*cho\s*vùng\s*sạt\s*lở|tái\s*định\s*cư\s*vùng\s*thiên\s*tai|"
    r"di\s*dời\s*.*hộ\s*dân\s*.*vùng\s*thiên\s*tai|tái\s*định\s*cư\s*.*vùng\s*sạt\s*lở|"
    r"xây\s*dựng\s*lại\s*nhà\s*.*vùng\s*bão\s*lũ|dựng\s*mái\s*ấm\s*.*vùng\s*sạt\s*lở|"
    r"hỗ\s*trợ\s*người\s*dân\s*sau\s*bão|xe\s*.*bị\s*cuốn\s*trôi\s*.*lũ|"
    r"người\s*.*bị\s*lũ\s*cuốn|nạn\s*nhân\s*.*mất\s*tích\s*do\s*lũ|"
    r"thiệt\s*hại\s*.*do\s*mưa\s*lũ|khắc\s*phục\s*hậu\s*quả\s*.*mưa\s*lũ|"
    r"mất\s*trắng\s*(?:do|sau|vì|bởi|trong)\s*(?:bão|lũ|thiên\s*tai|ngập|sạt|hạn|mặn)|"
    r"mất\s*trắng\s*(?:hoa\s*màu|lúa|tôm|cá|tài\s*sản)\s*do\s*thiên\s*tai|"
    r"rét\s*đậm|rét\s*hại|băng\s*giá|mưa\s*tuyết|không\s*khí\s*lạnh\s*tăng\s*cường|băng\s*tuyết|nắng\s*nóng\s*gay\s*gắt|hạn\s*hán\s*nghiêm\s*trọng|"
    r"nhà\s*giàn\s*dk\d+|cấp\s*cứu\s*ngư\s*dân|gặp\s*nạn\s*trên\s*biển|tàu\s*cá\s*gặp\s*nạn|"
    r"chiến\s*dịch\s*quang\s*trung|khắc\s*phục\s*sạt\s*lở|"
    r"ban\s*chỉ\s*huy\s*quân\s*sự.*(?:đắp\s*đê|gia\s*cố)|quyên\s*góp\s*ủng\s*hộ|ủng\s*hộ\s*đồng\s*bào|"
    r"hỗ\s*trợ\s*(?:ti\s*vi|tủ\s*lạnh|vật\s*dụng|đồ\s*dùng|nhu\s*yếu\s*phẩm|làm\s*nhà|xây\s*sửa\s*nhà|học\s*sinh|trường\s*học|giáo\s*viên)\s*(?:cho|tới)?\s*(?:bà\s*con|người\s*dân|hộ\s*dân|vùng\s*thiên\s*tai|vùng\s*lũ)|"
    r"(?:cấp\s*lại|cấp\s*đổi)\s*(?:sổ\s*đỏ|giấy\s*tờ|giấy\s*chứng\s*nhận)\s*(?:bị\s*)?(?:mất|hư\s*hỏng|trôi)\s*(?:do|vì|trong)\s*(?:bão|lũ|thiên\s*tai)|"
    r"(?:khôi\s*phục|ổn\s*định)\s*(?:sản\s*xuất|đời\s*sống|sinh\s*hoạt)\s*(?:sau|vùng)\s*(?:bão|lũ|thiên\s*tai)|"
    r"xuất\s*quân\s*hỗ\s*trợ\s*.*(?:bão|lũ|thiên\s*tai)|"
    r"chiến\s*dịch\s*quang\s*trung|thông\s*báo\s*khẩn\s*.*nghỉ\s*học|"
    r"(?:cho\s*)?(?:học\s*sinh|sinh\s*viên)\s*(?:nghỉ|tạm\s*ngừng)\s*học(?!\s*.*(?:tết|lễ|hè|nghỉ\s*mát))|"
    r"(?:sơ\s*tán|di\s*dời)\s*(?:dân|hộ\s*dân|người\s*dân)\s*(?:khẩn\s*cấp|an\s*toàn|khỏi\s*vùng\s*nguy\s*hiểm)|"
    r"vỡ\s*hồ\s*chứa|vỡ\s*đập\s*thủy\s*điện|sự\s*cố\s*hồ\s*đập|sự\s*cố\s*thủy\s*điện|"
    r"bão\s*số\s*\d+|áp\s*thấp\s*nhiệt\s*đới|tin\s*bão\s*khẩn\s*cấp)"
)
CRITICAL_RESCUE_ACTIONS = WHITELIST_TERMS
RE_CRITICAL_ACTIONS = re.compile(CRITICAL_RESCUE_ACTIONS, re.IGNORECASE)

GNEWS_IMPACT_KEYWORDS = [ 
    "thiệt hại","tổn thất", "đổ nhà","đổ tường", "hư hỏng","cuốn trôi", "trôi nhà","ngập nhà","vỡ đê","tràn đê",
    "vỡ bờ","chia cắt", "cô lập","mất mùa", "mất trắng","chết đuối","bị vùi lấp","người chết","tử vong","thiệt mạng", 
    "thi thể","nạn nhân","thương vong","bị thương", "trọng thương", "mất tích","mất liên lạc","tìm kiếm","sơ tán",
    "di dời","tránh trú","vào bờ", "lên bờ","về bến","cứu hộ","cứu nạn","cứu trợ","tiếp tế", 
    "hỗ trợ","trợ cấp","cứu sinh","giải cứu","tìm kiếm cứu nạn", "huy động lực lượng","xuất quân","triển khai lực lượng",
    "ứng phó","khắc phục","xử lý sự cố","sửa chữa","tu bộ","phục hồi", "tái thiết", "đánh giá thiệt hại", 
    "cảnh báo khẩn", "tin khẩn","công điện", "tình trạng khẩn cấp","tình huống khẩn cấp", "khẩn trương","gấp rút",
    "hỏa tốc","cấp bách","nguy hiểm","nguy cấp","nguy kịch", "mất an toàn","đe dọa","đe dọa nghiêm trọng","rủi ro cao",
    "nguy cơ cao", "cấm đường","cấm biển","cấm tàu thuyền","đóng cửa trường","cho nghỉ học", "nghỉ học","tạm dừng",
    "tạm ngưng","phong tỏa","cấm lưu thông","cách ly","họp khẩn", "trực ban","trực 24/24","túc trực", "ứng trực",
    "mực nước báo động", "xâm thực","sạt trượt","đứt gãy taluy","đá lăn", "tốc mái", "sập nhà", "thời tiết nguy hiểm",
    "tin dự báo", "tin cảnh báo", "tin khẩn", "sau bão", "sau lũ", "sau thiên tai", 
    "mưa cực lớn", "lũ quét", "siêu bão", "chiến dịch quang trung", "vỡ hồ chứa", "vỡ đập", "sập cầu", "sập giàn giáo",
    "ứng phó khẩn cấp", "khắc phục hậu quả", "di dời dân", "bão số", "áp thấp nhiệt đới"
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


# REGEX BASE COMPONENTS
_NUM_HARD = r"(?:\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*(?:[–-]|đến)\s*\d+)?)"
_NUM_SOFT = r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|hàng\s*chục|hàng\s*trăm|hàng\s*nghìn|hàng\s*ngàn|hàng\s*vạn|nhiều)"
_QUAL = r"(?:ít\s*nhất|tối\s*thiểu|khoảng|ước\s*tính|trên|hơn|gần)"
_UNIT = r"(?:người|nạn\s*nhân|em|cháu|trẻ\s*em|học\s*sinh|công\s*nhân|thuyền\s*viên|ngư\s*dân|hành\s*khách|tài\s*xế|lái\s*xe|cư\s*dân|du\s*khách|chiến\s*sĩ|phụ\s*nữ|thai\s*phụ|sản\s*phụ|cụ\s*ông|cụ\s*bà)"

NUM_HARD = rf"(?P<num>{_NUM_HARD})"
NUM_SOFT = rf"(?P<num_soft>{_NUM_SOFT})"
QUAL = rf"(?P<qualifier>{_QUAL})?"
UNIT = rf"(?P<unit>{_UNIT})?"

DEATH_WORD = r"(?:chết|tử\s*vong|thiệt\s*mạng|tử\s*nạn|tử\s*thương|không\s*qua\s*khỏi)"
INJ_WORD = r"(?:bị\s*thương|trọng\s*thương|bị\s*thương\s*nặng|đa\s*chấn\s*thương|thương\s*tích|chấn\s*thương|bỏng|bị\s*bỏng|bất\s*tỉnh|ngất\s*xỉu|nguy\s*kịch)"
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
CROP = r"(?:lúa|mạ|hoa\s*màu|rau\s*màu|cây\s*trồng|cây\s*ăn\s*quả|vườn\s*cây|mía|sắn|ngô|bắp|khoai|đậu|lạc|cà\s*phê|cao\s*su|hồ\s*tiêu|điều|chè|chuối|thanh\s*long|xoài|sầu\s*riêng|mít|cam|quýt|bưởi)"
CROP_STATUS = r"(?:bị\s*)?(?:ngập(?:\s*úng|\s*sâu|\s*lụt)?|hư\s*hại|hư\s*hỏng|thiệt\s*hại|mất\s*trắng|đổ\s*ngã|dập\s*nát|gãy\s*đổ|rụng\s*quả)"
LIVESTOCK = r"(?:trâu|bò|lợn|heo|dê|cừu|gà|vịt|ngan|ngỗng|gia\s*súc|gia\s*cầm)"
LIVE_STATUS = r"(?:bị\s*)?(?:chết|cuốn\s*trôi|trôi|mất|thiệt\s*hại)"
AQUA_OBJ = r"(?:ao|đầm|lồng\s*bè|lồng|bè)"
AQUA = r"(?:tôm|cá|thủy\s*sản)"
AQUA_STATUS = r"(?:bị\s*)?(?:trôi|cuốn\s*trôi|vỡ|tràn|thiệt\s*hại|mất\s*trắng|thất\s*thoát|cá\s*chết|tôm\s*chết)"

# IMPACT EXTRACTION KEYWORDS
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
        ],
        "regex": [
            r"\b(?P<qualifier>ít nhất|tối thiểu|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh|chiến sĩ)\s*(?:mất\s*tích|thất\s*lạc)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{MISS_WORD}\b",
            rf"\b(?:mất\s*tích|mất\s*liên\s*lạc)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b(?:mất\s*tích|mất\s*liên\s*lạc)\s*thêm\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*)?(?:cuốn\s*trôi|cuốn\s*đi|vùi\s*lấp|vùi\s*trong\s*lũ)\b",
            rf"\b(?:chia\s*cắt|cô\s*lập)\s*{QUAL}\s*{NUM_HARD}\s*(?:hộ\s*dân|người|nhân\s*khẩu)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*)?(?:mắc\s*kẹt|mắc\s*kẹt\s*trong\s*lũ|mắc\s*kẹt\s*trong\s*đám\s*cháy)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:vẫn\s*)?{MISS_WORD}\b",
            rf"\b{QUAL}\s*{NUM_SOFT}\s*{UNIT}\s*{MISS_WORD}\b",
        ]
    },

    "injured": {
        "terms": [
            "bị thương", "trọng thương", "bị thương nặng", "đa chấn thương", "thương tích", "nhập viện", "cấp cứu", "phải nhập viện", "đưa đi cấp cứu",
            "thương vong", "tổn thương", "gãy tay", "gãy chân", "chấn thương sọ não", "bị bỏng", "bỏng nặng", "bất tỉnh", "nguy kịch",
        ],
        "regex": [
            r"\b(?P<qualifier>ít nhất|tối thiểu|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:\s*[–-]\s*\d+)?)\s*(?P<unit>người|nạn nhân|em|cháu|học sinh|chiến sĩ)\s*(?:bị\s*thương|trọng\s*thương|nhập\s*viện|cấp\s*cứu|thương\s*vong)\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{INJ_WORD}\b",
            rf"\b{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*{CARE_WORD}\b",
            rf"\b(?:làm|khiến)\s*{QUAL}\s*{NUM_HARD}\s*{UNIT}\s*(?:bị\s*thương|trọng\s*thương|phải\s*cấp\s*cứu|nhập\s*viện)\b",
            rf"\b(?:ghi\s*nhận|có)\s*{QUAL}\s*{NUM_HARD}\s*(?:ca|trường\s*hợp)\s*(?:bị\s*thương|trọng\s*thương|thương\s*vong)\b",
            rf"\b{QUAL}\s*{NUM_SOFT}\s*{UNIT}\s*{INJ_WORD}\b",
        ]
    },

    "damage": {
        "terms": ["thiệt hại", "hư hỏng", "sập", "tốc mái", "cuốn trôi", "ngập", "ước tính", "mất trắng", "sập cầu", "cuốn trôi cầu", "hư hỏng nặng", "trôi tài sản", "sụt lún đường", "cháy rụi", "thiêu rụi", "bật gốc", "gãy đổ", "ngập úng nặng", "mất mát", "bùn lầy", "gượng dậy", "vùi lấp hoàn toàn", "bị cô lập", "vỡ hồ", "vỡ đập", "sạt lở đê", "gãy trắng", "hàm ếch"],
        "regex": [
            # Financial Damage (Billion/Million VND)
            r"\b(?:ước\s*tính|thiệt\s*hại)?\s*(?:khoảng|trên|hơn|gần)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)\s*(?P<unit>tỷ|tỉ|triệu|nghìn|ngàn)\s*đồng\b",
            r"\b(?:thiệt\s*hại|tổng\s*thiệt\s*hại)\s*(?:ước\s*tính)?\s*(?:lên\s*tới|khoảng|trên|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)\s*(?P<unit>tỷ|tỉ|triệu)\b",
            
            # Housing Damage
            r"\b(?P<qualifier>ít nhất|khoảng|hơn)?\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>nhà|căn|hộ|công\s*trình)\s*(?:bị\s*)?(?P<type>sập|đổ|tốc\s*mái|hư\s*hỏng|cuốn\s*trôi|ngập)\b",
            r"\b(?:làm|khiến)\s*(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?P<unit>nhà|căn|hộ)\s*(?:bị\s*)?(?P<type>sập|tốc\s*mái|ngập)\b",
            
            # Agriculture
            r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)\s*(?P<unit>ha|hecta|héc\s*ta)\s*(?:lúa|hoa\s*màu|cây\s*trồng)\s*(?:bị\s*)?(?:ngập|hư\s*hại|mất\s*trắng)\b"
        ]
    }
}




def load_sources_from_json(file_path: str) -> List[Source]:
    path = Path(file_path)
    if not path.exists():
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    sources = []
    for s in data.get("sources", []):
        # Auto-determine tier if not explicit
        # Tier 1: Authority Level 3 (Govt) or Explicitly Trusted High Frequency
        # Tier 2: Trusted Newspapers
        # Tier 3: General Blogs/Aggregators
        level = s.get("authority_level", 1)
        is_trusted = s.get("trusted", False)
        
        default_tier = 2
        if level >= 3: default_tier = 1
        elif is_trusted: default_tier = 1 # Bump trusted papers to Tier 1 for now (User request context)
        
        sources.append(Source(
            name=s.get("name", "Unknown"),
            domain=s.get("domain", ""),
            primary_rss=s.get("primary_rss"),
            backup_rss=s.get("backup_rss"),
            note=s.get("note"),
            trusted=is_trusted,
            authority_level=level,
            tier=s.get("tier", default_tier)
        ))
    return sources

CONFIG_FILE = Path(__file__).parent.parent / "sources.json"
CONFIG = {}
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {}

SOURCES = []
for s in CONFIG.get("sources", []):
    level = s.get("authority_level", 1)
    is_trusted = s.get("trusted", False)
    
    # Intelligent Tiering Algorithm
    # Tier 1: Critical Sources (Govt, National Weather, Major Dailies)
    if level >= 3 or "kttv" in s.get("domain", "") or is_trusted:
        default_tier = 1
    else:
        default_tier = 2

    SOURCES.append(Source(
        name=s.get("name", "Unknown"),
        domain=s.get("domain", ""),
        primary_rss=s.get("primary_rss"),
        backup_rss=s.get("backup_rss"),
        note=s.get("note"),
        trusted=is_trusted,
        authority_level=level,
        tier=s.get("tier", default_tier)
    ))

DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới (Storm/Tropical Cyclone)
    ("storm", [
        rf"\b(?<!báo\s)(?<!tin\s)(?<!thông\stin\s)(?<!tình\shình\s)(?<!đi\s)(?<!dự\s)(?<!tờ\s)(?<!đọc\s)(?<!thông\s)(?<!cảnh\s)(?<!tình\s)(?<!khai\s)(?<!đảm\s)(?<!nhà\s)(?<!đăng\s)(?<!viết\s)(?<!bài\s)(?<!gây\s)(?<!tâm\s)bão(?!\sgiá)(?!\smạng)(?!\slòng)(?!\stài\s)(?!\stín\s)(?!\ssale)(?!\skhuyến\s)(?!\schấn\s)(?!\ssa\s)(?!\struyền\s)(?!\s*chí)(?!\s*cáo)(?!\s*hiểm)(?!\s*vệ)(?!\s*đảm)(?!\s*tàng)(?!\s*toàn)(?!\s*quản)(?!\s*trì)(?!\s*hành)(?!\s*mật)(?!\s*gồm)(?!\s*phủ)(?!\s*quát)(?!\s*trọn)(?!\s*bì)(?!\s*vây)(?!\s*nhiêu)(?!\s*lâu)(?!\s*xa)(?!\s*giờ)(?!\s*lao\s*động)(?!\s*thanh\s*niên)(?!\s*tiền\s*phong)(?!\s*tin\s*tức)(?!\s*công\s*an)(?!\s*phụ\s*nữ)(?!\s*đầu\s*tư)(?!\s*pháp\s*luật)(?!\s*giáo\s*dục)(?!\s*nhân\s*dân)(?!\s*điện\s*tử)(?!\s*vietnamnet)(?!\s*dân\s*trí)(?!\s*vnexpress)(?!\s*công\s*lý)(?!\s*văn\s*hóa)(?!\s*quốc\s*tế)(?!\s*thù)(?!\s*đáp)(?!\s*công)(?!\s*hại)(?!\s*bệnh)(?!\s*lửa)(?!\s*dư\s*luận)(?!\s*chấn\s*thương)(?!\s*đơn)(?!\s*deal)(?!\s*like)(?!\s*view)(?!\s*cấp(?!\s*\d))\b",
        r"bão\s*số\s*\d+", r"siêu\s*bão", r"tâm\s*bão", r"mắt\s*bão", r"hoàn\s*lưu\s*bão",
        r"áp\s*thấp\s*nhiệt\s*đới", r"vùng\s*áp\s*thấp", r"ATNĐ", r"ATND", r"xoáy\s*thuận\s*nhiệt\s*đới",
        r"nhiễu\s*động\s*nhiệt\s*đới", r"cường\s*độ\s*bão", r"cấp\s*bão", r"gió\s*bão", r"bão\s*khẩn\s*cấp",
        r"đổ\s*bộ", r"tiến\s*vào\s*biển\s*đông", r"tin\s*bão",
        # Named Storms: Stricter, and we'll manually ensure this doesn't pass safe_no_accent if it's too risky
        r"\bbão\s+[A-ZĐ][a-zà-ỹ]{3,}\b",
        r"vùng\s*tâm\s*bão", r"áp\s*sát\s*ven\s*biển", r"hoàn\s*lưu\s*sau\s*bão", r"gió\s*xoáy", r"phong\s*ba", r"mưa\s*lũ", r"mưa\s*bão",
        r"bão\s*tăng\s*tốc", r"thần\s*tốc\s*tiến\s*vào", r"hồi\s*sức\s*sau\s*bão",
        r"\bbão\s*số\s*\d{1,2}\b",
        r"\b(?:siêu\s*bão|bão\s*rất\s*mạnh|bão\s*mạnh|bão\s*nhiệt\s*đới|siêu\s*bão\s*nhiệt\s*đới)\b",

        r"\báp\s*thấp\s*nhiệt\s*đới\b",
        r"\b(?:atnđ|atnd|a\.?\s*t\.?\s*n\.?\s*đ)\b",
        r"\b(?:xoáy\s*thuận\s*nhiệt\s*đới|nhiễu\s*động\s*nhiệt\s*đới)\b",

        r"\b(?:tâm|mắt)\s*bão\b",
        r"\bhoàn\s*lưu\s*bão\b",
        r"\bbán\s*kính\s*gió\s*mạnh\b",
        r"\bvùng\s*gió\s*mạnh\b",

        r"\b(?:beaufort|thang\s*beaufort)\b",

        r"\báp\s*suất\s*(?:trung\s*tâm|tối\s*thiểu|thấp\s*nhất)(?:\s*giảm)?\b",

        r"\b(?:đổ\s*bộ|đổ\s*bộ\s*trực\s*tiếp|áp\s*sát\s*ven\s*biển|tiến\s*gần\s*đất\s*liền)\b",
        r"\b(?:tiến\s*vào|đi\s*vào)\s*biển\s*đông\b",
        r"\b(?:vịnh\s*bắc\s*bộ|vịnh\s*thái\s*lan|quần\s*đảo\s*hoàng\s*sa|quần\s*đảo\s*trường\s*sa)\b",

        # Bão có tên: hỗ trợ cả TitleCase và ALLCAPS (YAGI, NORU, MOLAVE...)
        r"\bbão\s+(?:[A-ZĐ][a-zà-ỹ]{2,}|[A-Z]{3,})\b",

        r"\b(?:tin\s*bão|bản\s*tin\s*bão|cảnh\s*báo\s*bão|tin\s*bão\s*khẩn\s*cấp|dự\s*báo\s*bão|cập\s*nhật\s*bão)\b",
        r"\b(?:tin\s*áp\s*thấp|bản\s*tin\s*áp\s*thấp\s*nhiệt\s*đới)\b",
        r"\b(?:hướng\s*di\s*chuyển|quỹ\s*đạo\s*bão|đường\s*đi\s*của\s*bão|hành\s*lang\s*bão)\b",
        r"\b(?:tọa\s*độ\s*tâm\s*bão|kinh\s*độ\s*tâm\s*bão|vĩ\s*độ\s*tâm\s*bão|tọa\s*độ\s*tâm\s*áp\s*thấp)\b",
        r"\b(?:mưa\s*do\s*hoàn\s*lưu|mưa\s*do\s*hoàn\s*lưu\s*bão|mưa\s*to\s*do\s*bão|mưa\s*rất\s*to\s*do\s*bão)\b",
        r"\b(?:nước\s*biển\s*dâng\s*do\s*bão|nước\s*dâng\s*do\s*bão|triều\s*dâng\s*do\s*bão|sóng\s*tràn\s*do\s*bão)\b",
    ]),

  # 2) Lũ lụt (Flood)
  ("flood", [
    r"lũ\s*lụt", r"ngập\s*lụt", r"ngập\s*úng", r"xả\s*lũ",
    r"lũ\s*lên", r"lũ\s*xuống", r"lũ\s*về", r"nước\s*lũ",
    r"đỉnh\s*lũ", r"mực\s*nước\s*vượt\s*báo\s*động", r"lưu\s*lượng\s*về\s*hồ",
    r"lũ\s*trên\s*các\s*sông", r"vỡ\s*đê", r"tràn\s*đê", r"vỡ\s*đập", r"vỡ\s*hồ", r"hồ\s*chứa\s*(?:(?!\.).)*\s*vỡ", r"sự\s*cố\s*hồ", r"xả\s*tràn",
    r"tin\s*lũ", r"báo\s*động\s*(?:1|2|3|I|II|III)",
    r"lũ\s*lịch\s*sử", r"ngập\s*lụt\s*cục\s*bộ", r"ngập\s*sâu", r"vùng\s*trũng\s*thấp", r"\blũ(?!\s*trẻ)\b", r"vùng\s*lũ", r"rốn\s*lũ", r"chạy\s*lũ",
    r"điều\s*tiết\s*lũ", r"thủy\s*điện\s*(?:xả|điều\s*tiết)\s*lũ", r"vượt\s*lũ\s*lịch\s*sử", r"đợt\s*lũ\s*mới", r"lũ\s*chồng\s*lũ",
    # Core flood terms (high precision)
    r"\b(?:lũ\s*lụt|ngập\s*lụt|ngập\s*úng|lụt\s*nặng|lụt\s*diện\s*rộng|lụt\s*lịch\s*sử)\b",
    r"\b(?:lũ\s*lịch\s*sử|đỉnh\s*lũ\s*lịch\s*sử|đỉnh\s*lũ|lũ\s*đạt\s*đỉnh|lũ\s*vượt\s*đỉnh)\b",

    # Water level / alert levels
    r"\bmực\s*nước(?:\s*(?:sông|hồ|hạ\s*du|thượng\s*nguồn))?\s*(?:dâng|lên|tăng|đạt\s*đỉnh|vượt\s*ngưỡng|biến\s*động)\b",
    r"\b(?:mực\s*nước\s*báo\s*động|vượt\s*(?:mức\s*)?báo\s*động|trên\s*báo\s*động\s*3)\b",
    r"\bbáo\s*động\s*(?:1|2|3|I|II|III)\b",

    # Dike/dam incidents
    r"\b(?:vỡ|tràn)\s*(?:đê|đê\s*bao|kè|bờ|bờ\s*sông)\b",
    r"\b(?:vỡ|sự\s*cố)\s*(?:đập|hồ|hồ\s*đập|hồ\s*chứa)\b",
    r"\b(?:thẩm\s*lậu|mạch\s*đùn|mạch\s*sủi|rò\s*rỉ\s*(?:thân|chân)\s*đê|nứt\s*(?:đê|thân\s*đê|mặt\s*đê))\b",

    # Reservoir operation / discharge
    r"\bxả\s*(?:lũ|tràn|điều\s*tiết)\b",
    r"\bmở\s*cửa\s*xả(?:\s*lũ)?\b",
    r"\b(?:vận\s*hành|điều\s*tiết)\s*(?:hồ\s*chứa|liên\s*hồ(?:\s*chứa)?)\b",
    r"\blưu\s*lượng\s*(?:về\s*hồ|nước\s*về\s*hồ|xả(?:\s*lũ)?|qua\s*(?:đập|tràn))\b",

  # Urban drainage overload (very characteristic in news)
    r"\b(?:thoát\s*nước\s*quá\s*tải|hệ\s*thống\s*thoát\s*nước\s*quá\s*tải|cống\s*(?:nghẹt|bị\s*nghẹt|quá\s*tải)|hố\s*ga\s*trào\s*nước|miệng\s*cống\s*trào\s*nước)\b",
    r"\b(?:tiêu\s*úng|tiêu\s*thoát\s*úng|bơm\s*chống\s*ngập|trạm\s*bơm\s*chống\s*ngập|bơm\s*tiêu\s*úng)\b",
    # Inundation phrases (anchor "ngập" vào đối tượng cụ thể để giảm nhiễu)
    r"\bngập\s*(?:nhà|đường|phố|quốc\s*lộ|khu\s*dân\s*cư|hầm|hầm\s*chui|đường\s*hầm|cầu\s*vượt\s*thấp)\b",
    r"\bngập\s*(?:sâu|nặng|diện\s*rộng|cục\s*bộ|kéo\s*dài|nghiêm\s*trọng|tới\s*nóc|lút|ngang\s*ngực|quá\s*đầu\s*gối)\b",
    r"\b(?:ngập\s*tràn\s*vào\s*nhà|nước\s*tràn\s*vào\s*nhà|nước\s*tràn\s*qua\s*đường)\b",

    # Isolation / transport failure due to inundation
    r"\b(?:chia\s*cắt|cô\s*lập|tê\s*liệt\s*giao\s*thông)(?:\s*do\s*ngập)?\b",
    r"\b(?:xe\s*(?:chết\s*máy|tắt\s*máy)|ô\s*tô\s*chết\s*máy|xe\s*máy\s*chết\s*máy)\s*(?:do|vì)\s*ngập\b",
    r"\b(?:kẹt\s*xe|tắc\s*đường)\s*(?:do|vì)\s*ngập\b",

    # “lũ” đã có ngữ cảnh thủy văn (không phải lũ người/lũ bạn)
    r"\blũ\s*(?:sông|trên\s*sông|thượng\s*nguồn|thượng\s*lưu|hạ\s*lưu|hạ\s*du|nội\s*đồng|đô\s*thị|lưu\s*vực)\b",
    r"\blũ\s*(?:lên|lên\s*nhanh|rút|rút\s*chậm|dâng|dâng\s*cao|kéo\s*dài|bất\s*thường|trái\s*mùa|kép|chồng\s*lũ|hai\s*đỉnh)\b",
    r"\bmưa\s*(?:gây\s*lũ|gây\s*ngập|gây\s*ngập\s*lụt)\b",
  ]),

  # 3) Lũ quét/Lũ ống (Flash Flood)
  ("flash_flood", [
    r"lũ\s*quét", r"lũ\s*ống", r"lũ\s*bùn(?:\s*đá)?", r"lũ\s*đá", r"nghẽn\s*dòng",
    r"tin\s*cảnh\s*báo\s*lũ\s*quét", r"nguy\s*cơ\s*lũ\s*quét", r"lũ\s*dữ",
    r"lũ\s*cuồn\s*cuộn", r"dòng\s*lũ\s*chảy\s*xiết", r"đất\s*đá\s*đổ\s*về", r"trôi\s*cầu",
    # Direct identifiers
    r"\blũ\s*quét\b",
    r"\blũ\s*ống\b",
    r"\blũ\s*bùn(?:\s*đá)?\b",
    r"\blũ\s*quét\s*bùn\s*đá\b",

    # Strong official phrasing
    r"\b(?:cảnh\s*báo|tin\s*cảnh\s*báo|cảnh\s*báo\s*nguy\s*cơ)\s*(?:lũ\s*quét|lũ\s*ống)\b",
    r"\b(?:nguy\s*cơ|nguy\s*cơ\s*cao|điểm\s*nguy\s*cơ|khu\s*vực|vùng)\s*(?:có\s*)?nguy\s*cơ\s*(?:lũ\s*quét|lũ\s*ống)\b",
    # Sudden onset / kinetics (anchor bằng "lũ" hoặc "dòng lũ")
    r"\b(?:lũ|dòng\s*lũ|nước\s*lũ)\s*(?:ập\s*(?:đến|xuống)|đổ\s*ập\s*xuống|đổ\s*về|dâng\s*đột\s*ngột|dâng\s*nhanh|cuồn\s*cuộn)\b",
    r"\b(?:trong\s*tích\s*tắc|trong\s*vài\s*phút|bất\s*ngờ)\s*(?:xảy\s*ra|ập\s*xuống|ập\s*đến)\b",

    # “Dòng chảy xiết” but anchored to flood context
    r"\b(?:dòng\s*lũ\s*chảy\s*xiết|dòng\s*lũ\s*xiết|nước\s*lũ\s*chảy\s*xiết)\b",
    r"\b(?:dòng\s*chảy\s*xiết|nước\s*chảy\s*xiết)(?:(?=[^\.\n]{0,60}\b(?:khe\s*suối|suối|thượng\s*nguồn|bùn\s*đá|đất\s*đá|bản|làng)\b))\b",

    # Terrain signals: khe suối/suối dâng nhanh -> often used in flash flood narratives
    r"\b(?:khe\s*suối|khe|suối)\s*(?:dâng\s*cao|dâng\s*nhanh|dâng\s*đột\s*ngột|biến\s*thành\s*dòng\s*lũ)\b",
    r"\b(?:suối\s*nhỏ\s*thành\s*lũ|suối\s*cạn\s*thành\s*lũ|khe\s*suối\s*biến\s*thành\s*dòng\s*lũ)\b",
    r"\bnước\s*(?:từ\s*)?thượng\s*nguồn\s*đổ\s*về\b",

    # Mud/rock/debris flow phrases
    r"\b(?:dòng\s*bùn(?:\s*đá)?|bùn(?:\s*đá)?|đất\s*đá)\s*(?:ập\s*xuống|tràn\s*ập|ào\s*ạt|đổ\s*về|tràn\s*vào\s*nhà|mang\s*theo)\b",
    r"\b(?:đất\s*đá\s*chắn\s*ngang\s*đường|đất\s*đá\s*bịt\s*kín\s*đường)\b",

    # Damage / isolation typical of flash floods (anchored)
    r"\b(?:lũ\s*quét|lũ\s*ống|nước\s*lũ)\s*(?:cuốn\s*trôi|cuốn\s*phăng|cuốn\s*sập|vùi\s*lấp|tàn\s*phá)\b",
    r"\b(?:đứt\s*đường|trôi\s*cầu|cuốn\s*trôi\s*cầu|cầu\s*tạm\s*bị\s*cuốn)(?:(?=[^\.\n]{0,60}\b(?:lũ\s*quét|lũ\s*ống|nước\s*lũ|bùn\s*đá)\b))\b",
  ]),

  # 4) Sạt lở (Landslide)
  ("landslide", [
    r"sạt\s*lở(?!\s*bờ\s*(?:sông|biển|kè))", r"trượt\s*lở(?!\s*bờ\s*(?:sông|biển|kè))", r"lở\s*núi", r"sập\s*taluy",
    r"đá\s*đổ", r"đá\s*lăn", r"đá\s*rơi", r"sụt\s*trượt", r"vết\s*nứt(?!\s*(?:tường|nhà))",
    r"đất\s*đá\s*vùi\s*lấp", r"đứt\s*gãy", r"sụp\s*đổ\s*địa\s*chất", r"sạt\s*taluy",
    r"\bsạt\s*lở(?!\s*bờ\s*(?:sông|biển|kè))\b",
    r"\bsạt\s*lở\s*(?:đất|núi)\b",
    r"\blở\s*núi\b",
    r"\b(?:trượt\s*lở\s*đất|trượt\s*đất|trượt\s*lở)(?!\s*bờ\s*(?:sông|biển|kè))\b",
    r"\b(?:sạt\s*trượt|trượt\s*sạt|sụt\s*trượt)\s*(?:đất|sườn\s*núi|mái\s*dốc)?\b",

    # Taluy / ta luy (biến thể chính tả)
    r"\b(?:sập|sạt)\s*(?:ta[-\s]*luy|taluy)\b",
    r"\b(?:sạt\s*lở|sạt\s*trượt|trượt\s*lở)\s*(?:ta[-\s]*luy|taluy)\b",
    r"\b(?:ta[-\s]*luy|taluy)\s*(?:dương|âm)\s*(?:bị\s*)?(?:sạt|sập|trượt|lở)\b",

    # Cảnh báo / nguy cơ / điểm sạt lở
    r"\b(?:cảnh\s*báo|nguy\s*cơ)\s*(?:sạt\s*lở|sạt\s*trượt|trượt\s*lở)\b",
    r"\bđiểm\s*(?:sạt\s*lở|sạt\s*trượt|trượt\s*lở)\b",
    r"\b(?:phát\s*sinh|xuất\s*hiện)\s*điểm\s*(?:sạt\s*lở|sạt\s*trượt)\b",

    # Đường bị sạt lở (hạ tầng)
    r"\bsạt\s*lở\s*đường\b",
    r"\b(?:đường|tuyến\s*đường|quốc\s*lộ|tỉnh\s*lộ|đèo)\s*(?:bị\s*)?sạt\s*lở\b",
    r"\b(?:đứt|sập)\s*đường\s*do\s*sạt\s*lở\b",
    r"\b(?:tắc\s*đường|ách\s*tắc|phong\s*tỏa|chia\s*cắt)\s*(?:do\s*)?sạt\s*lở\b",
    # Đất đá/bùn đất vùi lấp/tràn xuống
    r"\b(?:đất\s*đá|bùn\s*đất)\s*(?:vùi\s*lấp|đổ\s*ập\s*xuống|sạt\s*xuống|tràn\s*xuống|tràn\s*ra\s*đường)\b",
    r"\b(?:đất\s*đá|bùn\s*đất)\s*(?:phủ\s*kín|vùi\s*lấp)\s*(?:mặt\s*đường|đường)\b",

    # Đá rơi/đá lăn/đá đổ: chỉ nhận khi có hậu quả gần kề (≤ 60 ký tự)
    r"\b(?:đá\s*(?:rơi|lăn|đổ)|rơi\s*đá)(?=(?:[^\.\n]{0,60}\b(?:xuống\s*đường|vào\s*nhà|liên\s*tiếp|nguy\s*hiểm|vùi\s*lấp|tắc\s*đường|ách\s*tắc)\b))\b",

    # Nứt: chỉ nhận khi gắn với núi/sườn dốc/taluy (loại nứt nhà/tường)
    r"\b(?:vết\s*nứt|khe\s*nứt)\s*(?:núi|sườn\s*núi|sườn\s*dốc|mái\s*dốc|mặt\s*dốc|(?:ta[-\s]*luy|taluy))\b",
    r"\bvết\s*nứt(?!\s*(?:tường|nhà|móng|công\s*trình))\b(?=(?:[^\.\n]{0,60}\b(?:sườn\s*núi|mái\s*dốc|taluy|ta\s*luy)\b))",

    # Thuật ngữ kỹ thuật trượt
    r"\b(?:khối\s*trượt|mặt\s*trượt|cung\s*trượt|vết\s*trượt|vệt\s*trượt)\b",

    # Nguyên nhân hay xuất hiện trong báo (tuỳ chọn)
    r"\bmưa\s*(?:lớn|kéo\s*dài)\s*gây\s*(?:sạt\s*lở|sạt\s*trượt|trượt\s*lở)\b",
  ]),

  # 5) Sụt lún đất (Land Subsidence)
  ("subsidence", [
    r"sụt\s*lún(?:\s*đất)?", r"sụp\s*lún", r"hố\s*sụt", r"hố\s*tử\s*thần", r"nghiêng\s*lún", r"sập\s*đổ",
    r"nứt\s*toác", r"sụt\s*lún\s*hạ\s*tầng", r"biến\s*dạng\s*mặt\s*đường", r"lún\s*xụt",
    r"sập\s*hầm\s*lò", r"sập\s*mỏ",
    # STRONG: match là rất chắc
    r"\bsụt\s*lún(?:\s*đất)?\b",
    r"\bsụp\s*lún\b",
    r"\b(?:lún\s*sụt|lún\s*xụt)\b",
    r"\bsụt\s*nền(?:\s*(?:đường|nhà|công\s*trình))?\b",
    r"\bsụt\s*đường\b",
    r"\b(?:đường|mặt\s*đường|nền\s*đường)\s*(?:bị\s*)?(?:lún|sụt|võng|sụp)\b",
    r"\b(?:mặt\s*đường)\s*(?:lún\s*sâu|võng\s*xuống|sụt\s*xuống|sụp\s*xuống)\b",

    # Sinkhole terms
    r"\bhố\s*sụt(?:\s*lún)?\b",
    r"\bhố\s*tử\s*thần\b",
    r"\bhố\s*sập\b",
    r"\bhố\s*sụt\s*(?:khổng\s*lồ|giữa\s*đường|trên\s*mặt\s*đường|lan\s*rộng|mở\s*rộng|nuốt\s*chửng)\b",

    # Infrastructure-specific failures strongly associated with subsidence
    r"\b(?:sập|sụt)\s*hố\s*ga\b",
    r"\bhố\s*ga\s*(?:sập|sụt|lún)\b",
    r"\b(?:cống\s*ngầm|cống|hầm\s*ngầm)\s*(?:sập|sụt|lún)\b",
    r"\bsụt\s*lún\s*(?:hạ\s*tầng|công\s*trình)\b",
    r"\bbiến\s*dạng\s*(?:mặt\s*đường|nền)\b",
    r"\btách\s*lớp\s*mặt\s*đường\b",
    # Nghiêng/lún lệch: chỉ nhận nếu có "lún/sụt/nền/móng" trong phạm vi gần
    r"\b(?:nghiêng\s*lún|lún\s*nghiêng|lún\s*lệch|lún\s*chênh(?:\s*lệch)?|lún\s*không\s*(?:đều|đồng\s*đều))\b",
    r"\b(?:nhà|tường|cột|công\s*trình|sàn)\s*(?:bị\s*)?nghiêng\b(?=(?:[^\.\n]{0,80}\b(?:lún|sụt|móng|nền|hố\s*sụt)\b))",

    # Nứt: chỉ nhận nếu có neo "lún/sụt/móng/nền/mặt đường" gần đó
    r"\bnứt\s*toác\b(?=(?:[^\.\n]{0,80}\b(?:lún|sụt|nền|móng|mặt\s*đường|hố\s*sụt)\b))",
    r"\b(?:nứt\s*(?:đất|nền|mặt\s*đường|móng|tường|nhà))\b(?=(?:[^\.\n]{0,80}\b(?:lún|sụt|sụt\s*lún|hố\s*sụt)\b))",
    r"\bnứt\s*lún(?:\s*(?:nền|mặt\s*đường|nhà\s*cửa|công\s*trình))?\b",

    # "hàm ếch": chỉ nhận nếu đi với đường/nền/mặt đường (không ăn bờ sông)
    r"\bhàm\s*ếch(?:\s*hóa)?\b(?=(?:[^\.\n]{0,60}\b(?:mặt\s*đường|đường|nền|nền\s*đường)\b))",

    # Cơ chế ngầm thường được mô tả
    r"\b(?:khoang\s*rỗng\s*dưới\s*đường|hốc\s*rỗng|rỗng\s*nền|nền\s*rỗng|rỗng\s*hóa\s*nền)\b",
    r"\bxói\s*ngầm(?:\s*(?:nền|dưới\s*đường|nền\s*đường))?\b",
    r"\bsụt\s*lún\s*do\s*(?:xói\s*ngầm|rỗng\s*nền|nền\s*yếu|địa\s*chất\s*yếu|rò\s*rỉ\s*nước|vỡ\s*ống\s*nước|vỡ\s*cống|sụp\s*cống)\b",

    # Warning / zoning / closures
    r"\b(?:cảnh\s*báo|nguy\s*cơ)\s*sụt\s*lún\b",
    r"\b(?:khoanh\s*vùng|rào\s*chắn|phong\s*tỏa|đóng\s*đường)\s*(?:khu\s*vực\s*)?sụt\s*lún\b",
    r"\b(?:điểm|ổ)\s*sụt\s*lún\b",
  ]),

  # 6) Hạn hán (Drought) - User Cat 6
  ("drought", [
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước(?:\s*sinh\s*hoạt)?", r"đất\s*nứt\s*nẻ", r"khô\s*cằn", r"cạn\s*trơ", r"cây\s*héo",
    r"hạn\s*mặn", r"thiếu\s*hụt\s*nguồn\s*nước", r"dòng\s*chảy\s*kiệt", r"mùa\s*cạn",
    r"vùng\s*hạn", r"chống\s*hạn", r"thiếu\s*hụt\s*mưa", r"mực\s*nước\s*chết",
    # STRONG: Neo hạn/khô hạn (rất chắc)
    r"\bhạn\s*hán(?:\s*(?:kéo\s*dài|nghiêm\s*trọng|gay\s*gắt|cực\s*đoan|kỷ\s*lục|chưa\s*từng\s*có))?\b",
    r"\bkhô\s*hạn(?:\s*(?:kéo\s*dài|nghiêm\s*trọng|gay\s*gắt|cực\s*đoan|diện\s*rộng|trên\s*diện\s*rộng))?\b",
    r"\bnắng\s*hạn(?:\s*kéo\s*dài)?\b",
    r"\b(?:đại\s*hạn|hạn\s*cực\s*đoan|hạn\s*kỷ\s*lục)\b",
    r"\bhạn\s*mặn\b",  # nếu bạn muốn drought cũng “bắt” hạn mặn (hoặc để salinity bắt riêng)

    # Thiếu mưa / mùa khô
    r"\b(?:thiếu\s*hụt\s*mưa|mưa\s*thiếu\s*hụt|ít\s*mưa|không\s*mưa\s*kéo\s*dài|không\s*mưa\s*trong\s*nhiều\s*(?:ngày|tuần))\b",
    r"\b(?:mùa\s*khô|mùa\s*cạn)(?:\s*(?:gay\s*gắt|khốc\s*liệt|kéo\s*dài))?\b",

    # STRONG: Thủy văn kiệt (rất đặc trưng hạn)
    r"\b(?:dòng\s*chảy|lưu\s*lượng)\s*(?:kiệt|cạn\s*kiệt|suy\s*kiệt|giảm\s*mạnh|xuống\s*thấp)\b",
    r"\bmực\s*nước\s*(?:chết|xuống\s*thấp|hạ\s*thấp|giảm\s*sâu|tụt\s*thấp)\b",
    r"\b(?:hồ|ao|đập|kênh|mương|sông|suối|lòng\s*sông|lòng\s*suối)\s*(?:cạn|khô|trơ\s*đáy|cạn\s*trơ)\b",
    r"\b(?:nguồn\s*nước|mạch\s*nước\s*ngầm|nước\s*ngầm)\s*(?:suy\s*giảm|cạn|tụt|hạ\s*thấp|khan\s*hiếm)\b",
    r"\b(?:giếng\s*(?:khoan|đào)?\s*(?:cạn|khô|trơ\s*đáy)|tụt\s*mực\s*nước\s*ngầm|mực\s*nước\s*ngầm\s*hạ\s*thấp)\b",
    # STRONG: Nông nghiệp & sinh kế (đặc trưng hạn)
    r"\b(?:đất|ruộng|đồng\s*ruộng)\s*(?:nứt\s*nẻ|khô\s*nẻ|nứt\s*toác|nứt\s*chân\s*chim)\b",
    r"\b(?:cây|cây\s*trồng)\s*(?:héo\s*úa|héo|chết\s*khô)\b",
    r"\b(?:cháy\s*lá|lá\s*khô\s*cháy\s*xém|cỏ\s*cháy\s*khô|khô\s*cháy\s*đồng\s*ruộng)\b",
    r"\b(?:bỏ\s*vụ\s*do\s*hạn|mất\s*mùa\s*do\s*hạn|mất\s*trắng\s*do\s*hạn)\b",
    r"\b(?:thiếu\s*nước\s*tưới|không\s*(?:đủ|có)\s*nước\s*tưới|ngưng\s*tưới|cắt\s*giảm\s*tưới)\b",

    # CONDITIONAL: Thiếu nước sinh hoạt / xe bồn / cúp nước (dễ nhiễu)
    # => chỉ match khi có “neo hạn” trong phạm vi gần
    r"\b(?:thiếu\s*nước\s*(?:sinh\s*hoạt|ăn\s*uống|sạch)?|nước\s*sinh\s*hoạt\s*khan\s*hiếm|khủng\s*hoảng\s*nước|khẩn\s*cấp\s*về\s*nước)\b"
    r"(?=(?:[^\.\n]{0,120}\b(?:hạn|khô\s*hạn|thiếu\s*mưa|mùa\s*khô|mùa\s*cạn|dòng\s*chảy\s*kiệt|mực\s*nước\s*chết)\b))",

    r"\b(?:cúp\s*nước(?:\s*kéo\s*dài)?|mất\s*nước\s*sinh\s*hoạt|hết\s*nước\s*sinh\s*hoạt)\b"
    r"(?=(?:[^\.\n]{0,120}\b(?:hạn|khô\s*hạn|thiếu\s*mưa|mùa\s*khô|mùa\s*cạn)\b))",

    r"\b(?:xe\s*(?:bồn|téc)\s*(?:chở|cấp)\s*nước|cấp\s*nước\s*bằng\s*xe\s*(?:bồn|téc)|phát\s*nước(?:\s*miễn\s*phí)?|xếp\s*hàng\s*lấy\s*nước|đi\s*lấy\s*nước\s*sinh\s*hoạt)\b"
    r"(?=(?:[^\.\n]{0,160}\b(?:hạn|khô\s*hạn|thiếu\s*mưa|mùa\s*khô|mùa\s*cạn)\b))",

    # Ứng phó / chống hạn (khá an toàn)
    r"\b(?:chống\s*hạn|ứng\s*phó\s*hạn\s*hán|kế\s*hoạch\s*chống\s*hạn|phương\s*án\s*chống\s*hạn|tích\s*trữ\s*nước|trữ\s*nước|tưới\s*(?:tiết\s*kiệm|nhỏ\s*giọt|luân\s*phiên))\b",
  ]),

  # 7) Xâm nhập mặn (Salinity Intrusion) - User Cat 7
  ("salinity", [
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*phèn", r"nhiễm\s*mặn", r"ngăn\s*mặn", r"ranh\s*mặn", r"độ\s*mặn\s*cao", r"hạn\s*mặn",
    r"cống\s*ngăn\s*mặn", r"đẩy\s*mặn", r"nước\s*nhiễm\s*mặn", r"\d+(?:[.,]\d+)?\s*(?:‰|%o|g\/l)\b",
    r"nước\s*lợ", r"độ\s*mặn\s*vượt\s*ngưỡng", r"mặn\s*bủa\s*vây",
    # STRONG: Neo xâm nhập mặn (cực chắc)
    r"\bxâm\s*nhập\s*mặn(?:\s*(?:tăng\s*cao|gay\s*gắt|nghiêm\s*trọng|kéo\s*dài|diện\s*rộng|trên\s*diện\s*rộng))?\b",
    r"\b(?:hạn\s*mặn|đợt\s*hạn\s*mặn)\b",
    r"\b(?:mặn\s*xâm\s*nhập|nước\s*mặn\s*xâm\s*nhập)\b",
    r"\b(?:mặn\s*lấn\s*sâu|mặn\s*lan\s*sâu|mặn\s*lan\s*rộng|mặn\s*vào\s*sâu)\b",

    # Ranh mặn
    r"\branh\s*mặn(?:\s*(?:lấn\s*sâu|ăn\s*sâu|tiến\s*sâu|vào\s*sâu|dịch\s*chuyển|mở\s*rộng|tăng\s*nhanh|thay\s*đổi))?\b",

    # STRONG: Độ mặn / nồng độ muối (có ngữ cảnh)
    r"\bđộ\s*mặn(?:\s*(?:tăng\s*cao|tăng\s*mạnh|tăng\s*nhanh|đạt\s*đỉnh|vượt\s*ngưỡng|vượt\s*chuẩn|đột\s*biến|bất\s*thường|dao\s*động|biến\s*động))?\b",
    r"\b(?:nồng\s*độ\s*muối|chỉ\s*số\s*độ\s*mặn)(?:\s*(?:tăng|cao|vượt\s*ngưỡng))?\b",

    # Số liệu độ mặn có đơn vị — phải “gần” từ khóa mặn/độ mặn/ranh mặn để tránh nhiễu
    # Ví dụ: "độ mặn 4‰", "ranh mặn 4 g/l", "độ mặn đo được 1.2 ppt"
    r"(?:(?:độ\s*mặn\s)|(?:ranh\s*mặn\s)|(?:nước\s*mặn\s))"
    r"\d+(?:[.,]\d+)?\s*(?:‰|%o|ppt|g\/l|g\/L|mg\/l|mg\/L)\b",

    # Hoặc: số liệu + đơn vị nằm trước, rồi sau đó có “độ mặn/ranh mặn” trong phạm vi gần
    r"\d+(?:[.,]\d+)?\s*(?:‰|%o|ppt|g\/l|g\/L|mg\/l|mg\/L)\b"
    r"(?=(?:[^\.\n]{0,60}\b(?:độ\s*mặn|ranh\s*mặn|nước\s*mặn)\b))",
    # STRONG: Nước lợ / nước nhiễm mặn
    r"\bnước\s*lợ\b",
    r"\b(?:nước\s*(?:nhiễm|bị)\s*mặn|nguồn\s*nước\s*(?:sinh\s*hoạt\s*)?nhiễm\s*mặn|nước\s*máy\s*bị\s*nhiễm\s*mặn)\b",
    r"\b(?:giếng\s*(?:bị\s*)?nhiễm\s*mặn|nước\s*giếng\s*nhiễm\s*mặn)\b",

    # STRONG: Biện pháp/ vận hành công trình (rất đặc trưng ĐBSCL)
    r"\b(?:cống\s*ngăn\s*mặn|đập\s*ngăn\s*mặn|đập\s*tạm\s*ngăn\s*mặn)\b",
    r"\b(?:đóng\s*cống\s*(?:ngăn\s*mặn|chống\s*mặn|giữ\s*ngọt)(?:\s*khẩn\s*cấp)?|mở\s*cống\s*(?:lấy|đón)\s*(?:nước\s*)?ngọt)\b",
    r"\b(?:ngăn\s*mặn|đẩy\s*mặn|trữ\s*ngọt|giữ\s*ngọt|bảo\s*vệ\s*(?:nguồn\s*nước\s*)?ngọt)\b",
    r"\b(?:lấy\s*nước\s*(?:khi|lúc)\s*triều\s*thấp|lấy\s*nước\s*theo\s*triều|đóng\s*mở\s*cống\s*theo\s*triều|canh\s*con\s*nước\s*lấy\s*ngọt)\b",

    # Rửa mặn / thau chua
    r"\b(?:rửa\s*mặn(?:\s*(?:đất|ruộng))?|xả\s*rửa\s*mặn|thau\s*chua\s*rửa\s*mặn|cải\s*tạo\s*đất\s*(?:nhiễm\s*)?mặn)\b",

    # CONDITIONAL: Phèn/mặn-phèn (phèn đơn lẻ dễ lệch)
    # Bắt “phèn mặn” chắc; còn “nhiễm phèn” chỉ tính nếu gần neo mặn/xâm nhập mặn/độ mặn
    r"\b(?:phèn\s*mặn|xì\s*phèn)\b",
    r"\b(?:nhiễm\s*phèn|đất\s*nhiễm\s*phèn|nước\s*nhiễm\s*phèn|phèn\s*bùng\s*phát|nước\s*phèn|rửa\s*phèn|thau\s*chua)\b"
    r"(?=(?:[^\.\n]{0,120}\b(?:mặn|xâm\s*nhập\s*mặn|độ\s*mặn|ranh\s*mặn|hạn\s*mặn)\b))",
  ]),

  # 8) Mưa lớn/Mưa đá/Lốc/Sét (Rain/Hail/Tornado/Lightning) - User Cat 8
  # Renamed back to 'extreme_weather' to match Frontend theme.js
  ("extreme_weather", [
    # Rain
    r"mưa\s*lớn", r"mưa\s*xối\s*xả", r"mưa\s*trắng\s*trời", r"mưa\s*to", r"mưa\s*rất\s*to", r"lượng\s*mưa", r"mưa\s*kỷ\s*lục", r"mưa\s*trái\s*mùa",
    # Hail/Tornado/Lightning/Wind
    r"mưa\s*đá", r"lốc(?!\s*xoáy)", r"sấm\s*sét", r"sét\s*đánh", r"phóng\s*điện", r"dông", r"giông", r"lốc\s*xoáy", r"gió\s*mạnh", r"quật\s*đổ", r"tốc\s*mái", r"vòi\s*rồng",
    r"tố\s*lốc", r"giông\s*sét", r"tia\s*sét",
    r"giông\s*cực\s*mạnh", r"gió\s*rít", r"gió\s*giật", r"gió\s*lốc", r"đợt\s*mưa\s*mới",
    # RAIN: mưa lớn/cực đoan (neo chắc)
    r"\bmưa\s*(?:rất\s*to|to\s*đến\s*rất\s*to|cực\s*lớn|kỷ\s*lục|lịch\s*sử)\b",
    r"\bmưa\s*(?:xối\s*xả|như\s*trút|trắng\s*trời|tầm\s*tã|dồn\s*dập|nặng\s*hạt)\b",
    r"\b(?:mưa\s*diện\s*rộng|mưa\s*cục\s*bộ|mưa\s*trái\s*mùa|mưa\s*cực\s*đoan)\b",

    # “mưa lớn trong thời gian ngắn / cường suất lớn” — rất đặc trưng bản tin KTTV
    r"\bmưa\s*lớn\s*(?:trong\s*(?:thời\s*gian\s*)?ngắn|trong\s*(?:ít|vài)\s*giờ)\b",
    r"\b(?:mưa\s*cường\s*suất\s*lớn|cường\s*suất\s*mưa\s*lớn)\b",

    # “mưa rào và dông/giông” (cụm forecast hay dùng)
    r"\bmưa\s*rào(?:\s*(?:và|kèm)\s*(?:dông|giông)(?:\s*sét)?)?\b",
    r"\bmưa\s*(?:dông|giông)(?:\s*diện\s*rộng)?\b",

    # THUNDERSTORM / LIGHTNING
    r"\b(?:dông|giông)(?:\s*(?:lốc|tố|cực\s*mạnh|mạnh))?\b",
    r"\b(?:sét|tia\s*sét|giông\s*sét|dông\s*sét|phóng\s*điện)\b",
    r"\bsét\s*đánh(?:\s*(?:trúng|liên\s*tiếp|dồn\s*dập|gây\s*(?:cháy|hỏa\s*hoạn|mất\s*điện|thương\s*vong)))?\b",

    # HAIL
    r"\bmưa\s*đá(?:\s*(?:dữ\s*dội|dày\s*đặc|bất\s*ngờ|cục\s*bộ|trên\s*diện\s*rộng|kèm\s*(?:dông\s*lốc|gió\s*lốc|sét)))?\b",
    r"\bmưa\s*đá\s*(?:kích\s*thước\s*lớn|to|rơi\s*dày|kéo\s*dài)\b",
    # TORNADO / SQUALL / WIND GUST
    # Lốc: tránh “lốc cốc / lốc xoáy” tuỳ bạn muốn. Ở đây: cho bắt cả “lốc”, “lốc xoáy”, “tố lốc”, “vòi rồng”
    r"\b(?:tố\s*lốc|vòi\s*rồng|lốc\s*xoáy)\b",
    # “lốc” đơn: chặn một số nhiễu phổ biến (bạn có thể mở rộng blacklist theo corpus)
    r"\blốc(?!\s*cốc)(?!\s*xoáy)\b",

    r"\bgió\s*(?:giật(?:\s*(?:mạnh|rất\s*mạnh|dữ\s*dội|liên\s*hồi|từng\s*cơn|cục\s*bộ))?|mạnh|lốc|rít)\b",

    # IMPACT words (hậu quả do mưa dông/lốc/sét)
    r"\b(?:tốc\s*mái(?:\s*tôn)?|bay\s*mái\s*tôn|bung\s*mái\s*tôn|sập\s*mái|sập\s*tường\s*rào)\b",
    r"\b(?:đổ\s*cây|cây\s*đổ|cây\s*bật\s*gốc|cây\s*gãy\s*đổ|gãy\s*cành|gãy\s*nhánh)\b",
    r"\b(?:đổ\s*cột\s*điện|gãy\s*cột\s*điện|đứt\s*dây\s*điện|đứt\s*dây\s*cáp|đổ\s*trụ\s*điện|gãy\s*trụ\s*điện)\b",
    r"\b(?:đổ\s*biển\s*quảng\s*cáo|đổ\s*giàn\s*giáo|đổ\s*rạp\s*nhà\s*tạm)\b",

    # Secondary: mưa gây hệ quả nhanh (ngập/sạt sau mưa)
    r"\b(?:mưa\s*lớn\s*gây\s*ngập(?:\s*cục\s*bộ|\s*nhanh)?|ngập\s*nhanh\s*sau\s*mưa|đường\s*ngập\s*sau\s*mưa)\b",
    r"\b(?:sạt\s*lở\s*sau\s*mưa|sạt\s*trượt\s*sau\s*mưa|đá\s*rơi\s*sau\s*mưa)\b",
  ]),

  # 9) Nắng nóng (Heatwave) - User Cat 9
  ("heatwave", [
    r"nắng\s*nóng", r"thiêu\s*đốt", r"nhiệt\s*độ\s*cao", r"sốc\s*nhiệt", r"trú\s*nóng",
    r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt\s*gay\s*gắt", r"nhiệt\s*độ\s*kỷ\s*lục",
    r"chỉ\s*số\s*tia\s*cực\s*tím", r"chỉ\s*số\s*UV", r"đợt\s*nắng\s*nóng", r"nhiệt\s*độ\s*cao\s*nhất",
    r"nắng\s*cháy\s*da", r"nóng\s*rát", r"nắng\s*hạn",
    # CORE HEATWAVE PHRASES (neo chắc)
    r"\b(?:nắng\s*nóng|đợt\s*nắng\s*nóng|đợt\s*nóng)\b",
    r"\bnắng\s*nóng\s*(?:gay\s*gắt|đặc\s*biệt\s*gay\s*gắt|kéo\s*dài|diện\s*rộng|cục\s*bộ|cực\s*đoan|khốc\s*liệt|dữ\s*dội|nghiêm\s*trọng|tăng\s*cường|tái\s*diễn|quay\s*trở\s*lại)\b",

    # “nắng như đổ lửa / thiêu đốt”
    r"\b(?:nắng\s*như\s*đổ\s*lửa|nóng\s*như\s*thiêu(?:\s*như\s*đốt)?|thiêu\s*đốt)\b",
    # TEMPERATURE / BASELINE HEAT (định lượng + cụm KTTV
    # Nhiệt độ cao nhất / nền nhiệt / duy trì cao
    r"\b(?:nhiệt\s*độ\s*cao\s*nhất|nền\s*nhiệt(?:\s*(?:tăng|cao|duy\s*trì\s*cao|cao\s*kéo\s*dài))?)\b",
    r"\b(?:nhiệt\s*độ\s*(?:tăng\s*(?:nhanh|mạnh|vọt)|duy\s*trì\s*trên\s*cao|phổ\s*biến))\b",
    r"\b(?:đêm\s*nóng|đêm\s*oi\s*bức|nhiệt\s*độ\s*ban\s*đêm\s*cao)\b",

    # Nhiệt độ vượt ngưỡng “38/39/40 độ”, “trên 40 độ”
    r"\bnhiệt\s*độ\s*vượt\s*(?:38|39|40)\s*độ\b",
    r"\b(?:trên|xấp\s*xỉ|khoảng)\s*(?:38|39|40|41|42|43|44|45)\s*độ(?:\s*C)?\b",

    # Pattern số + °C / độ C (bắt tin dạng “37-39°C”, “40°C”)
    r"\b\d{2}(?:\s*[-–]\s*\d{2})?\s*(?:°\s*C|°C|độ\s*C|độ\s*c)\b",

    # “cảm giác như 40 độ / nhiệt độ cảm nhận / cảm giác nhiệt”
    r"\b(?:nhiệt\s*độ\s*cảm\s*nhận|cảm\s*giác\s*nhiệt|cảm\s*giác\s*như)\s*(?:\d{2}\s*(?:°\s*C|°C|độ))?\b",
    r"\bcảm\s*giác\s*như\s*(?:40|41|42|43|44|45|46|47|48|49|50)\s*độ(?:\s*C)?\b",
    # UV / HEAT RISK WARNING
    r"\b(?:chỉ\s*số\s*UV|UV)(?:\s*(?:rất\s*cao|cao|nguy\s*hiểm|tăng\s*cao|ở\s*mức\s*(?:rất\s*cao|nguy\s*hiểm)))?\b",
    r"\b(?:tia\s*UV|tia\s*cực\s*tím|tia\s*cực\s*tím\s*mạnh)\b",

    # “cảnh báo nắng nóng / cấp độ rủi ro / mức cảnh báo”
    r"\b(?:cảnh\s*báo|dự\s*báo|khuyến\s*cáo)\s*(?:nắng\s*nóng|nóng|nền\s*nhiệt\s*cao)\b",
    r"\b(?:cấp\s*độ\s*rủi\s*ro(?:\s*do)?\s*nắng\s*nóng|rủi\s*ro\s*do\s*nắng\s*nóng|mức\s*cảnh\s*báo\s*nắng\s*nóng)\b",
    # HEALTH / IMPACT SIGNALS (neo hậu quả
    r"\b(?:say\s*nắng|say\s*nóng|sốc\s*nhiệt|đột\s*quỵ\s*(?:do\s*nóng|nhiệt)|kiệt\s*sức\s*(?:do|vì)\s*(?:nóng|nắng\s*nóng)|mất\s*nước(?:\s*do\s*nắng\s*nóng)?)\b",
    r"\b(?:ngất(?:\s*xỉu)?\s*(?:do\s*nóng|vì\s*nắng)|nhập\s*viện\s*vì\s*nắng\s*nóng|tử\s*vong\s*do\s*nắng\s*nóng)\b",
    r"\b(?:cháy\s*nắng|bỏng\s*nắng|da\s*bỏng\s*rát|rộp\s*da\s*do\s*nắng)\b",
    # POWER/WATER STRESS (hay xuất hiện trong tin nắng nóng
    r"\b(?:quá\s*tải\s*điện|lưới\s*điện\s*quá\s*tải|tải\s*điện\s*tăng\s*cao|nhu\s*cầu\s*điện\s*tăng\s*vọt|cắt\s*điện\s*luân\s*phiên|cúp\s*điện\s*do\s*quá\s*tải)\b",
    r"\b(?:thiếu\s*nước\s*sinh\s*hoạt\s*do\s*nắng\s*nóng|khuyến\s*cáo\s*uống\s*đủ\s*nước|bổ\s*sung\s*nước|bù\s*nước)\b",
  ]),

  # 10) Rét hại/Sương muối (Cold/Frost) - User Cat 10
  ("cold_surge", [
    r"trời\s*rét", r"rét\s*hại", r"rét\s*đậm", r"rét\s*khô", r"rét\s*tê\s*tái", r"sương\s*muối", r"băng\s*giá", r"đóng\s*băng", r"tuyết\s*rơi", r"tuyết\s*phủ",
    r"rét\s*đậm\s*rét\s*hại", r"nhiệt\s*độ\s*xuống\s*dưới\s*0",
    r"rét\s*buốt", r"mưa\s*tuyết",
    r"không\s*khí\s*lạnh\s*tăng\s*cường", r"gió\s*mùa\s*đông\s*bắc",
    r"(?:sưởi\s*ấm|đốt\s*lửa|quấn\s*chăn|chống\s*rét).*(?:vật\s*nuôi|gia\s*súc|đàn\s*bò|đàn\s*trâu|đàn\s*lợn)",
    # CORE “RÉT” PHRASES (neo chắc
    r"\b(?:rét\s*đậm|rét\s*hại|rét\s*đậm\s*rét\s*hại)\b",
    r"\b(?:đợt\s*rét|đợt\s*rét\s*mạnh|rét\s*tăng\s*cường|rét\s*kỷ\s*lục|lạnh\s*kỷ\s*lục)\b",
    r"\b(?:rét\s*buốt|rét\s*tê\s*tái|lạnh\s*cắt\s*da\s*cắt\s*thịt|giá\s*rét|rét\s*sâu)\b",
    r"\b(?:trời\s*rét|trời\s*chuyển\s*rét|trời\s*rét\s*buốt)\b",
    # COLD AIR / MONSOON (văn phong KTTV
    r"\b(?:không\s*khí\s*lạnh|đợt\s*không\s*khí\s*lạnh|khối\s*không\s*khí\s*lạnh)(?:\s*(?:tăng\s*cường|mạnh|bổ\s*sung|liên\s*tiếp|tràn\s*về|tràn\s*xuống|ảnh\s*hưởng|bao\s*trùm|suy\s*yếu))?\b",
    r"\b(?:gió\s*mùa\s*đông\s*bắc|gió\s*mùa|gió\s*bấc)(?:\s*(?:mạnh|tăng\s*cường|tràn\s*về|hoạt\s*động\s*mạnh))?\b",
    r"\b(?:mưa\s*phùn|mưa\s*nhỏ|mưa\s*phùn\s*gió\s*bấc|ẩm\s*lạnh|lạnh\s*ẩm|sương\s*mù(?:\s*dày)?)\b",
    # FROST / ICE / SNOW ANCHOR
    r"\b(?:sương\s*muối(?:\s*(?:dày|dày\s*đặc|phủ\s*trắng|xuất\s*hiện|gây\s*hại))?)\b",
    r"\b(?:băng\s*giá(?:\s*(?:dày|phủ\s*trắng|xuất\s*hiện))?|bám\s*băng|đóng\s*băng|băng\s*phủ)\b",
    r"\b(?:tuyết\s*rơi(?:\s*dày)?|tuyết\s*phủ(?:\s*trắng)?|mưa\s*tuyết)\b",
    # TEMPERATURE THRESHOLDS / QUANT (rất quan trọng
    # “nhiệt độ dưới 10/5/0 độ”, “xuống 0 độ”, “âm 1-2 độ”, “-2°C”
    r"\bnhiệt\s*độ\s*(?:xuống|giảm|dưới)\s*(?:10|5|0)\s*độ(?:\s*C)?\b",
    r"\b(?:dưới|xuống)\s*(?:10|5|0)\s*độ(?:\s*C)?\b",
    r"\b(?:âm|-\s*)\d{1,2}\s*(?:°\s*C|°C|độ\s*C|độ)\b",
    # dạng “3-6°C”, “0-2°C”
    r"\b\d{1,2}\s*[-–]\s*\d{1,2}\s*(?:°\s*C|°C|độ\s*C|độ)\b",
    # IMPACT / AGRI-LIVESTOCK SIGNALS (neo hậu quả
    r"\b(?:gia\s*súc|vật\s*nuôi|đàn\s*trâu|đàn\s*bò|đàn\s*lợn|gia\s*cầm)\s*(?:chết\s*rét|bị\s*rét|thiệt\s*hại\s*do\s*rét)\b",
    r"\b(?:cây\s*trồng|hoa\s*màu)\s*(?:chết\s*rét|bị\s*rét|thiệt\s*hại\s*do\s*rét|cháy\s*lá|hư\s*hại)\b",
    r"\b(?:ủ\s*ấm|che\s*chắn\s*chuồng\s*trại|phòng\s*chống\s*rét|chống\s*rét\s*cho\s*(?:cây\s*trồng|gia\s*súc))\b",
    # OPTIONAL: “nền nhiệt xuống thấp/duy trì thấp” (KTTV hay dùng
    r"\b(?:nền\s*nhiệt)\s*(?:giảm\s*(?:sâu|mạnh)?|xuống\s*thấp|duy\s*trì\s*thấp|thấp)\b",
  ]),

  # 11) Động đất (Earthquake) - User Cat 11
  ("earthquake", [
    r"\bđộng\s*đất\b",
    r"\b(?:địa\s*chấn|rung\s*chấn|dư\s*chấn|tâm\s*chấn|chấn\s*tiêu)\b",
    r"\b(?:rung\s*lắc|rung\s*chuyển|chấn\s*động|rung\s*động)(?:\s*mạnh)?\b",
    # MEASUREMENT / SCALE ANCHORS (giảm nhiễu mạnh
    # Richter / Magnitude / M5.2 / độ lớn 4.3
    r"\b(?:thang\s*)?richter\b",
    r"\bmagnitude\b",
    r"\bđộ\s*lớn(?:\s*động\s*đất)?\s*(?:m\s*)?\d+(?:[.,]\d+)?\b",
    r"\bM\s*\d+(?:[.,]\d+)?\b",        # M5, M 5.2
    r"\bM\d+(?:[.,]\d+)?\b",           # M5.2 (liền)

    # Mercalli
    r"\b(?:thang\s*)?mercalli\b",

    # Depth: "độ sâu chấn tiêu 10 km", "sâu khoảng 15km"
    r"\bđộ\s*sâu\s*(?:tâm\s*chấn|chấn\s*tiêu)\s*(?:khoảng|ước|tầm)?\s*\d+(?:[.,]\d+)?\s*km\b",
    r"\b(?:chấn\s*tiêu\s*(?:nông|sâu)|tâm\s*chấn\s*(?:nông|sâu))\b",
    r"\b\d+(?:[.,]\d+)?\s*km\s*(?:dưới\s*mặt\s*đất|độ\s*sâu)\b",

    # Coordinates: vĩ độ / kinh độ / tọa độ
    r"\b(?:vĩ\s*độ|kinh\s*độ|tọa\s*độ)\b",
    # dạng số độ thập phân "21.34N 105.82E" hoặc "21.34, 105.82"
    r"\b\d{1,2}(?:[.,]\d+)?\s*[°]?\s*(?:N|B)\b.*?\d{1,3}(?:[.,]\d+)?\s*[°]?\s*(?:E|Đ)\b",
    r"\b\d{1,2}(?:[.,]\d+)?\s*[,/;]\s*\d{1,3}(?:[.,]\d+)?\b",
    # INSTITUTION / REPORTIN
    r"\bviện\s*vật\s*lý\s*địa\s*cầu\b",
    r"\btrung\s*tâm\s*báo\s*tin\s*động\s*đất\b",
    r"\b(?:thông\s*báo|ghi\s*nhận|cảnh\s*báo)\s*động\s*đất\b",
    # GEOLOGICAL CONTEXT (tăng recall nhưng vẫn đúng lĩnh vực
    r"\b(?:đứt\s*gãy|đới\s*đứt\s*gãy|hoạt\s*động\s*đứt\s*gãy|mảng\s*kiến\s*tạo|chuyển\s*động\s*kiến\s*tạo)\b",
    r"\b(?:sóng\s*P|sóng\s*S|sóng\s*mặt|sóng\s*địa\s*chấn|bản\s*ghi\s*địa\s*chấn)\b",
    # HUMAN IMPACT / FEELING REPORTS (hữu ích cho báo chí
    r"\b(?:người\s*dân\s*cảm\s*nhận|cảm\s*nhận\s*rung\s*lắc|cảm\s*nhận\s*động\s*đất)\b",
    r"\b(?:nhà\s*cửa|chung\s*cư|nhà\s*cao\s*tầng|đồ\s*vật)\s*(?:rung\s*lắc|rung\s*chuyển)\b",
]),

  # 12) Sóng thần (Tsunami) - User Cat 12
  ("tsunami", [
    r"sóng\s*thần", r"sóng\s*lớn", r"động\s*đất\s*dưới\s*biển",
    r"tsunami", r"cấp\s*báo\s*động\s*sóng\s*thần", r"tin\s*cảnh\s*báo\s*sóng\s*thần",
    r"sóng\s*cao\s*hàng\s*chục\s*mét", r"thảm\s*họa\s*sóng\s*thần",
    # CORE (neo chắc
    r"\bsóng\s*thần\b",
    r"\btsunami\b",
    # WARNING / BULLETIN / STATUS CHANG
    r"\b(?:cảnh\s*báo|tin\s*cảnh\s*báo|bản\s*tin|dự\s*báo)\s*sóng\s*thần\b",
    r"\b(?:phát|ban\s*hành|cập\s*nhật|nâng\s*cấp|hạ\s*cấp|hủy|dỡ\s*bỏ)\s*cảnh\s*báo\s*sóng\s*thần\b",
    r"\b(?:trạng\s*thái|mức|cấp)\s*(?:cảnh\s*báo\s*)?sóng\s*thần\b",
    r"\bcấp\s*báo\s*động\s*sóng\s*thần\b",
    # NATURAL SIGNALS (rất đặc thù
    r"\b(?:nước\s*biển|biển)\s*rút\s*(?:bất\s*thường|nhanh|mạnh|sâu)\b",
    r"\bmực\s*nước\s*biển\s*(?:dâng|rút)\s*(?:bất\s*thường|nhanh|đột\s*ngột)\b",
    r"\b(?:dao\s*động|biến\s*động)\s*mực\s*nước(?:\s*biển)?\s*(?:mạnh|bất\s*thường)\b",
    r"\b(?:biển)\s*(?:dâng|rút)\s*(?:bất\s*thường|nhanh)\b",
    # SOURCE / CAUSE (offshore quake / seabed
    r"\bđộng\s*đất\s*(?:dưới\s*biển|ngoài\s*khơi|dưới\s*đáy\s*biển|đáy\s*biển)\b",
    r"\b(?:tâm\s*chấn)\s*(?:ngoài\s*khơi|ngoài\s*biển|trên\s*biển)\b",
    r"\b(?:trượt\s*lở|sạt\s*lở)\s*đáy\s*biển\b",
    r"\bnúi\s*lửa\s*dưới\s*biển\b",
    # EVACUATION / PUBLIC ADVIC
    r"\b(?:sơ\s*tán|di\s*tản)\s*(?:do|tránh|ứng\s*phó)\s*sóng\s*thần\b",
    r"\brút\s*lên\s*cao\s*(?:tránh|để\s*tránh)\s*sóng\s*thần\b",
    r"\b(?:khuyến\s*cáo|yêu\s*cầu)\s*(?:tránh\s*xa|rời\s*khỏi)\s*(?:bờ\s*biển|vùng\s*ven\s*biển)\b",
    r"\b(?:đóng\s*cửa|tạm\s*dừng)\s*(?:bãi\s*biển|hoạt\s*động\s*ven\s*biển)\b",
    r"\bcấm\s*(?:xuống\s*biển|tắm\s*biển)(?:\s*do\s*sóng\s*thần)?\b",
    # MONITORING / INSTRUMENTATIO
    r"\btrung\s*tâm\s*(?:cảnh\s*báo|báo\s*tin)\s*sóng\s*thần\b",
    r"\b(?:giám\s*sát|quan\s*trắc|theo\s*dõi)\s*(?:diễn\s*biến\s*)?sóng\s*thần\b",
    r"\b(?:phao|cảm\s*biến|trạm)\s*(?:cảnh\s*báo\s*)?sóng\s*thần\b",
    r"\btrạm\s*quan\s*trắc\s*mực\s*nước\b",
    # ARRIVAL TIME / WAVE HEIGHT (định lượng
    r"\b(?:thời\s*gian|thời\s*điểm|giờ)\s*sóng\s*đến\b",
    r"\b(?:chiều\s*cao\s*sóng\s*thần|độ\s*cao\s*sóng)\b",
    r"\bsóng\s*cao\s*hàng\s*chục\s*mét\b",
    # DAMAGE / INUNDATION (bổ trợ
    r"\b(?:sóng\s*thần)\s*(?:tàn\s*phá|gây\s*ngập|phá\s*hủy|cuốn\s*trôi)\b",
    r"\bngập\s*lụt\s*do\s*sóng\s*thần\b",
  ]),

  # 13) Nước dâng (Storm Surge) - User Cat 13
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"sóng\s*tràn",
    r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng", r"ngập\s*lụt\s*do\s*triều",
    # CORE ANCHORS (đặc thù
    r"\btriều\s*cường\b",
    r"\b(?:triều\s*dâng|thủy\s*triều\s*dâng|mực\s*triều)\b",
    r"\b(?:nước\s*dâng|nước\s*biển\s*dâng)\b",
    r"\bsóng\s*tràn(?:\s*bờ)?\b",
    # SEA/COAST/ESTUARY CONTEXT (gating
    r"\b(?:ven\s*biển|bờ\s*biển|khu\s*vực\s*ven\s*biển|dải\s*ven\s*biển)\b",
    r"\b(?:cửa\s*sông|vùng\s*cửa\s*sông|cửa\s*biển)\b",
    r"\b(?:ngoài\s*khơi|trên\s*biển|biển\s*động|biển\s*động\s*mạnh)\b",
    # OVERTOPPING / DEFENSE STRUCTURE
    r"\b(?:vượt|tràn\s*qua)\s*(?:kè|đê)\s*biển\b",
    r"\b(?:sóng\s*vượt|sóng\s*tràn\s*qua)\s*(?:kè|đê)\b",
    r"\b(?:tràn\s*kè|vỡ\s*kè\s*biển|tràn\s*đê\s*biển)\b",
    r"\b(?:kè\s*biển|đê\s*biển|kè\s*chắn\s*sóng|đê\s*chắn\s*sóng)\b",
    # LEVEL / PEAK phrasin
    r"\b(?:đỉnh\s*triều|mực\s*triều\s*(?:dâng\s*cao|vượt\s*ngưỡng|đạt\s*đỉnh))\b",
    r"\btriều\s*cường\s*(?:đạt\s*đỉnh|vượt\s*mức|tăng\s*mạnh|bất\s*thường)\b",
    r"\bnước\s*dâng\s*(?:đạt\s*đỉnh|cao\s*bất\s*thường|đột\s*biến)\b",
    # IMPACT / COASTAL FLOODIN
    r"\bngập(?:\s*sâu)?\s*(?:ven\s*biển|khu\s*dân\s*cư\s*ven\s*biển|đường\s*ven\s*biển)\b",
    r"\bngập\s*lụt\s*do\s*triều(?:\s*cường)?\b",
    r"\bngập\s*do\s*nước\s*dâng\b",
    # EROSION / SCOUR (coastal
    r"\b(?:xâm\s*thực|xói\s*lở)\s*(?:bờ\s*biển|do\s*sóng)\b",
    r"\b(?:xói\s*chân\s*kè|hở\s*chân\s*kè|sạt\s*chân\s*kè)\b",
    # WARNING / ADVIC
    r"\bcảnh\s*báo\s*(?:triều\s*cường|nước\s*dâng|triều\s*dâng|mực\s*triều)\b",
    r"\b(?:đóng\s*đường|cấm\s*đường)\s*ven\s*biển\b",
  ]),

  # 14) Cháy rừng (Wildfire) - User Cat 14
  ("wildfire", [
    r"cháy\s*rừng", r"cháy\s*tán", r"cháy\s*ngầm", r"cháy\s*thực\s*bì", r"lửa\s*rừng", 
    r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng", r"PCCCR", 
    r"giặc\s*lửa\s*rừng", r"dập\s*lửa\s*rừng", r"chữa\s*cháy\s*rừng",
    r"đám\s*cháy\s*(?:lớn|lan)\s*(?:tại|ở|trong)\s*rừng",
    r"huy\s*động\s*dập\s*lửa\s*rừng", r"đốt\s*thực\s*bì",
    # CORE: explicit wildfire term
    r"\bcháy\s*rừng(?:\s*(?:phòng\s*hộ|đặc\s*dụng|sản\s*xuất))?\b",
    r"\bcháy\s*(?:thực\s*bì|thảm\s*thực\s*bì)\b",
    r"\b(?:cháy\s*dưới\s*tán|cháy\s*tán|cháy\s*ngầm)\b",
    r"\blửa\s*rừng\b",
    r"\bgiặc\s*lửa\b",
    # FORESTRY org / wildfire prevention lexico
    r"\bPCCCR\b",
    r"\bphòng\s*cháy\s*chữa\s*cháy\s*rừng\b",
    r"\bcấp\s*dự\s*báo\s*cháy\s*rừng(?:\s*cấp\s*(?:IV|V|4|5))?\b",
    r"\bcảnh\s*báo\s*cháy\s*rừng(?:\s*cấp\s*(?:IV|V|4|5))?\b",
    r"\bkiểm\s*lâm\b",
    # FIRELINE / containment techniques (very specific
    r"\b(?:đường\s*băng|băng|đường\s*ranh)\s*cản\s*lửa\b",
    r"\b(?:cắt\s*đường\s*lửa|tạo\s*vành\s*đai\s*cản\s*lửa|khoanh\s*vùng\s*đám\s*cháy)\b",
    r"\b(?:khống\s*chế|dập\s*tắt|dập\s*lửa|chữa\s*cháy)\s*(?:cháy\s*rừng|đám\s*cháy\s*rừng)?\b",
    # AREA / SCALE markers (hectares
    r"\b(?:cháy|thiêu\s*rụi)\s*(?:hàng\s*chục|hàng\s*trăm|\d{1,4})\s*ha\b",
    r"\b\d{1,4}\s*ha\s*(?:rừng|thực\s*bì)\s*(?:bị\s*)?(?:cháy|thiêu\s*rụi)\b",
    # SMOKE / impact but with forest contex
    r"\b(?:cột\s*khói|khói\s*mù|khói\s*dày\s*đặc)\b(?=(?:[^\.\n]{0,60}\b(?:rừng|khu\s*rừng|thực\s*bì|đồi|núi|kiểm\s*lâm|PCCCR)\b))",
  ]),

  # 15) Xói lở (Erosion) - User Cat 15
  ("erosion", [
    r"xói\s*lở", r"sạt\s*lở\s*bờ\s*(?:sông|biển)", r"hàm\s*ếch", r"mương\s*xói", r"rãnh\s*xói", r"xâm\s*thực", r"xói\s*mòn",
    r"sập\s*bờ\s*kè", r"vỡ\s*bờ\s*kè", r"vỡ\s*kè",
    # Core erosion words
    r"\bxói\s*lở\b",
    r"\bxói\s*mòn(?:\s*đất)?\b",
    r"\bxâm\s*thực(?:\s*(?:biển|bờ\s*biển|bờ\s*sông))?\b",

    # Bank/coast specific (strong discriminator vs landslide)
    r"\b(?:xói\s*lở|sạt\s*lở|lở)\s*bờ\s*(?:sông|biển|kè|rạch|kênh|suối)\b",
    r"\bxói\s*lở\s*(?:cửa\s*sông|bãi\s*bồi|cù\s*lao)\b",
    r"\b(?:lở|sụt)\s*bờ(?:\s*(?:sông|biển))?\b",
    r"\bhàm\s*ếch(?:\s*bờ\s*(?:sông|biển))?\b",

    # Undercutting / toe erosion
    r"\b(?:khoét|xói)\s*(?:chân\s*)?(?:bờ|kè|đê)\b",
    r"\bxói\s*lở\s*(?:ăn\s*sâu|tiến\s*sát|khoét\s*sâu|ăn\s*sát)\b",

    # Levee/embankment revetment failures (erosion-like in reports)
    r"\b(?:sạt|sập|vỡ)\s*kè\b",
    r"\bkè\s*(?:bị\s*)?(?:sạt|xói|sập|hư\s*hỏng)\b",
    r"\b(?:gia\s*cố|xử\s*lý|khẩn\s*cấp\s*xử\s*lý)\s*(?:bờ|kè|đê)\b",
    r"\b(?:kè\s*tạm|kè\s*tạm\s*chống\s*xói|chống\s*xói)\b",

    # Erosion features
    r"\b(?:mương\s*xói|rãnh\s*xói)\b",

    # Warnings / risk
    r"\b(?:cảnh\s*báo|nguy\s*cơ)\s*xói\s*lở\b",
    # "dòng chảy xiết/mạnh" -> chỉ tính erosion nếu có bờ/kè/khúc cua...
    r"\bdòng\s*chảy\s*(?:xiết|mạnh|khoét\s*bờ|xói\s*bờ)\b"
    r"(?=(?:[^\.\n]{0,80}\b(?:bờ|kè|ven\s*sông|ven\s*biển|cửa\s*sông|bãi\s*bồi|khúc\s*cua)\b))",

    # "triều cường/sóng" -> chỉ tính erosion nếu có xói/lở/khoét hoặc bờ/kè gần đó
    r"\b(?:triều\s*cường|sóng\s*(?:biển|lớn))\b"
    r"(?=(?:[^\.\n]{0,80}\b(?:xói\s*lở|xâm\s*thực|khoét\s*bờ|bờ\s*biển|kè|bờ\s*sông)\b))",

    # "mất đất" -> chỉ tính erosion nếu có ven sông/ven biển/bờ/kè
    r"\bmất\s*đất\b"
    r"(?=(?:[^\.\n]{0,80}\b(?:ven\s*sông|ven\s*biển|bờ\s*sông|bờ\s*biển|bãi\s*bồi|cù\s*lao|kè)\b))",
  ]),


  # 16) Tin cảnh báo, dự báo (Warning/Forecast)
  ("warning_forecast", [
    r"bản\s*tin\s*dự\s*báo", r"tin\s*cảnh\s*báo", r"dự\s*báo\s*thời\s*tiết", r"cảnh\s*báo\s*thiên\s*tai",
    r"bản\s*tin\s*khẩn\s*cấp", r"thông\s*báo\s*khẩn", r"đài\s*khí\s*tượng", r"cảnh\s*báo\s*cực\s*đoan",
    # A) BULLETINS / FORECASTS (high precision)
    r"\bbản\s*tin\s*(?:dự\s*báo|cảnh\s*báo|thời\s*tiết|khí\s*tượng|KTTV|khí\s*tượng\s*thủy\s*văn)\b",
    r"\btin\s*(?:dự\s*báo|cảnh\s*báo|KTTV|khí\s*tượng|thời\s*tiết)\b",
    r"\b(?:dự\s*báo|cảnh\s*báo)\s*(?:khí\s*tượng|thời\s*tiết|KTTV|khí\s*tượng\s*thủy\s*văn)\b",
    r"\bcảnh\s*báo\s*thiên\s*tai\b",
    r"\b(?:bản\s*tin|tin)\s*khẩn\s*cấp\b",
    r"\b(?:thông\s*báo|cảnh\s*báo)\s*khẩn(?:\s*cấp)?\b",

    # B) MET AGENCIES / AUTHORITIES (anchors)
    r"\b(?:đài|trung\s*tâm)\s*(?:khí\s*tượng|KTTV|khí\s*tượng\s*thủy\s*văn)\b",
    r"\btrung\s*tâm\s*dự\s*báo\s*(?:khí\s*tượng\s*thủy\s*văn)?\s*quốc\s*gia\b",
    r"\btrung\s*tâm\s*khí\s*tượng\s*thủy\s*văn\s*quốc\s*gia\b",
    r"\bNCHMF\b",
    r"\btổng\s*cục\s*khí\s*tượng\s*thủy\s*văn\b",
    r"\bcơ\s*quan\s*khí\s*tượng\b",
    r"\b(?:đài\s*KTTV\s*khu\s*vực|đài\s*KTTV\s*tỉnh|trạm\s*khí\s*tượng|trạm\s*đo\s*mưa)\b",

    # C) RISK LEVEL / MAP / AFFECTED AREA (very characteristic)
    r"\bcấp\s*độ\s*rủi\s*ro\s*thiên\s*tai(?:\s*cấp)?\s*(?:1|2|3|4|5|I|II|III|IV|V)\b",
    r"\b(?:mức|cấp)\s*rủi\s*ro\s*thiên\s*tai\b",
    r"\b(?:bản\s*đồ|vùng|khu\s*vực)\s*(?:cảnh\s*báo|dự\s*báo|nguy\s*cơ|rủi\s*ro)\b",
    r"\b(?:phạm\s*vi\s*ảnh\s*hưởng|khu\s*vực\s*chịu\s*ảnh\s*hưởng|vùng\s*nguy\s*hiểm|khu\s*vực\s*nguy\s*hiểm)\b",
    r"\bcảnh\s*báo\s*(?:vùng|khu\s*vực)\s*nguy\s*hiểm\b",
    r"\bcảnh\s*báo\s*(?:trên\s*biển|ven\s*biển|đất\s*liền)\b",

    # D) RESTRICTIONS / ADVISORIES (still fairly precise)
    r"\b(?:lệnh\s*)?cấm\s*biển\b",
    r"\bcấm\s*tàu\s*thuyền\s*ra\s*khơi\b",
    r"\btạm\s*dừng\s*ra\s*khơi\b",
    r"\b(?:cấm|đóng)\s*cửa\s*biển\b",
    r"\b(?:cấm\s*đường|đóng\s*đường|cấm\s*phương\s*tiện|hạn\s*chế\s*phương\s*tiện|phân\s*luồng\s*giao\s*thông)\b",
    r"\b(?:đóng\s*cửa\s*trường\s*học|cho\s*học\s*sinh\s*nghỉ\s*học|tạm\s*dừng\s*học)\b",
    r"\bđường\s*dây\s*nóng|số\s*điện\s*thoại\s*đường\s*dây\s*nóng\b",

    # E) DIRECTIVES / OFFICIAL DISPATCHES (needs anchoring but often decisive)
    r"\bcông\s*điện(?:\s*(?:khẩn|hỏa\s*tốc))?\b",
    r"\b(?:điện\s*khẩn|văn\s*bản\s*chỉ\s*đạo|chỉ\s*thị|lệnh\s*điều\s*hành|thông\s*báo\s*chỉ\s*đạo)\b",
    r"\b(?:ban\s*chỉ\s*đạo|ban\s*chỉ\s*huy)\s*(?:PCTT|phòng\s*chống\s*thiên\s*tai|PCTT\s*và\s*TKCN|PCTT\s*&\s*TKCN|TKCN)\b",
    r"\bphương\s*án\s*(?:ứng\s*phó|sơ\s*tán)|kịch\s*bản\s*ứng\s*phó|kế\s*hoạch\s*ứng\s*phó\b",
    r"\bphương\s*châm\s*4\s*tại\s*chỗ\b",
    # Khuyến cáo / đề nghị / cảnh giác ... chỉ tính nếu gần thiên tai/KTTV
    r"\b(?:khuyến\s*cáo|đề\s*nghị|đề\s*phòng|cảnh\s*giác)\b"
    r"(?=(?:[^\.\n]{0,120}\b(?:thiên\s*tai|KTTV|khí\s*tượng|mưa\s*lũ|bão|lũ|triều\s*cường|nắng\s*nóng|rét\s*hại)\b))",

    # Chỉ đạo khẩn / yêu cầu khẩn trương ... chỉ tính nếu gần PCTT/TKCN/thiên tai
    r"\b(?:chỉ\s*đạo\s*khẩn|yêu\s*cầu\s*khẩn\s*trương|đề\s*nghị\s*khẩn\s*trương)\b"
    r"(?=(?:[^\.\n]{0,160}\b(?:PCTT|TKCN|thiên\s*tai|bão|lũ|mưa\s*lớn|sạt\s*lở|lũ\s*quét)\b))",
  ]),

  # 17) Khắc phục hậu quả (Recovery)
  ("recovery", [
    r"khắc\s*phục\s*hậu\s*quả\s*thiên\s*tai", r"khắc\s*phục\s*sự\s*cố\s*đê\s*điều", r"khôi\s*phục\s*giao\s*thông\s*sau\s*lũ",
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
    r"khắc\s*phục\s*hư\s*hỏng\s*cầu\s*do\s*lũ", r"sạt\s*lở.*thiệt\s*mạng",
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
    r"tìm\s*kiếm\s*cứu\s*nạn", r"tìm\s*kiếm\s*người\s*mất\s*tích", r"truy\s*tìm\s*nạn\s*nhân", r"trục\s*vớt\s*tàu", r"hỗ\s*trợ\s*nạn\s*nhân"
  ]),
]
