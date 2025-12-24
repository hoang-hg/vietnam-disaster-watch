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
        "beaufort", "hải lý", "km/h",
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
        "bao so", "sieu bao", "ap thap nhiet doi", "xoay thuan nhiet doi",
        "bien dong", "hoan luu bao", "tam bao", "mat bao", "do bo"
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
        "mưa như trút", "mưa xối xả", "mưa tầm tã", "lượng mưa", "tổng lượng mưa",
        "lũ lên cao", "lũ rút", "lũ đang lên", "lũ rút chậm",
        "nước sông dâng", "mực nước sông", "mực nước dâng", "mực nước tăng nhanh",
        "mực nước lên báo động", "vượt mức báo động", "trên báo động", "đạt đỉnh",
        "đỉnh lũ trên sông", "lũ dồn dập", "lũ chồng lũ", "lũ kép",
        "nước chảy xiết", "dòng chảy xiết", "dòng chảy mạnh",
        "nước đổ về", "lũ đổ về", "nước từ thượng nguồn", "thượng nguồn đổ về",
        "ngập ven sông", "ngập ven suối", "ngập vùng trũng", "ngập vùng thấp",
        "sông suối dâng cao", "suối dâng", "nước suối dâng",
        "lũ trên các sông", "lũ trên lưu vực", "lưu vực sông",
        "lưu lượng đỉnh", "lưu lượng tăng", "lưu lượng về hồ", "lưu lượng xả",
        "ngập đô thị", "ngập do mưa", "ngập do triều", "ngập do thoát nước kém",
        "ngập hầm", "ngập hầm chui", "ngập tầng hầm", "ngập chung cư",
        "ngập cống", "tắc cống", "tắc nghẽn cống", "tràn cống", "nước tràn cống",
        "tràn bờ", "nước tràn bờ", "ngập lề đường", "ngập giao lộ",
        "ngập diện rộng", "ngập trên diện rộng", "ngập nghiêm trọng",
        "biển nước", "ngập trắng", "nước ngập quá bánh xe", "ngập ngang bánh xe",
        "xả điều tiết", "điều tiết hồ chứa", "điều tiết lũ",
        "xả đáy", "xả cửa đáy", "xả cửa tràn", "mở cửa xả", "mở cửa xả lũ",
        "xả qua tràn", "xả qua đập tràn",
        "mực nước hồ", "dung tích hồ", "mực nước dâng bình thường", "mực nước chết",
        "tích nước", "cắt lũ", "cắt giảm lũ",
        "vỡ bờ", "sạt lở bờ", "sạt lở kè", "sập kè", "hư hỏng kè",
        "xói lở bờ sông", "xói lở bờ biển", 
        "sạt lở nghiêm trọng", "nguy cơ sạt lở", "cảnh báo sạt lở",
        "điểm sạt lở", "vị trí sạt lở", "điểm sụt lún",
        "sạt lở ta luy dương", "sạt lở taluy dương", "sạt lở ta luy âm", "sạt lở taluy âm",
        "trượt mái dốc", "trượt mái", "trượt dốc", "sạt mái", "sập mái taluy",
        "sạt lở vách", "sạt lở vách đá", "đá rơi", "đá lở", "đá lăn xuống đường",
        "đất đá tràn xuống", "đất đá đổ xuống", "đất đá sạt xuống",
        "sụt hố", "sụt hố sâu", "hố sụt", "hố sụt lún", "sụt nền", "nền đất yếu",
        "nứt nhà", "nứt tường", "nứt nền", "nứt mặt đường", "nứt đường",
        "đường bị cuốn trôi", "cuốn trôi đường", "sạt lở quốc lộ", "sạt lở tỉnh lộ",
        "sạt lở đường đèo", "sạt lở đèo", "tắc đường do sạt lở",
        "cầu bị cuốn trôi", "cầu bị sập", "sập cầu", "sập cống", "hư hỏng cống",
        "sạt lở gây ách tắc", "giao thông tê liệt", "đường bị chia cắt",
        "ngập cầu", "ngập đường hầm", "ngập tuyến", "tuyến đường bị chia cắt",
        "mưa vượt ngưỡng", "mưa trên 100mm", "mưa trên 150mm", "mưa trên 200mm",
        "mưa trong 1 giờ", "mưa trong 3 giờ", "mưa trong 6 giờ", "mưa trong 12 giờ", "mưa trong 24 giờ",
        "lượng mưa 24 giờ", "lượng mưa giờ", "mưa cục bộ", "mưa cường suất lớn",
        "mưa tập trung", "mưa dông", "mưa giông", "mưa rào và dông",
        "lu quet", "lu ong", "ngap lut", "ngap ung", "sat lo", "truot lo",
        "sut lun", "ho tu than", "vo de", "vo dap", "xa lu", "xa tran", "xa khan cap",
        "xoi lo", "ham ech", "nut toac", "dut duong", "mua lon", "luong mua"
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
        "dòng chảy kiệt", "mùa cạn", "kiệt nước", "mực nước xuống thấp", "độ mặn 4‰",
        "cảm giác nóng", "cảm giác nhiệt", "nhiệt độ cảm nhận",
        "chỉ số nhiệt", "heat index",
        "nắng nóng diện rộng", "nắng nóng trên diện rộng",
        "nhiệt độ vượt ngưỡng", "nhiệt độ tăng cao", "nhiệt độ ngoài trời",
        "trên 37 độ", "trên 38 độ", "trên 39 độ", "trên 40 độ",
        "ban ngày nắng nóng", "đêm nóng", "đêm oi", "nắng nóng ban đêm",
        "tia UV rất cao", "UV rất cao", "UV nguy cơ cao", "bức xạ UV",
        "thiếu nước tưới", "thiếu nước sản xuất", "thiếu nước nghiêm trọng",
        "khát nước", "cấp nước khẩn cấp", "cấp nước sinh hoạt", "cắt nước luân phiên",
        "nguồn nước suy giảm", "nguồn nước cạn", "nguồn nước kiệt",
        "mực nước hồ xuống thấp", "mực nước hồ giảm", "mực nước sông xuống thấp",
        "cạn hồ", "hồ trơ đáy", "sông cạn", "suối cạn", "kênh cạn", "ao hồ cạn",
        "khô kiệt", "kiệt dòng", "dòng chảy suy giảm", "lưu lượng suy giảm",
        "mực nước chết", "mực nước tối thiểu",
        "điều tiết nước", "xả nước", "bổ sung nước", "lấy nước ngọt",
        "mặn xâm nhập", "mặn xâm nhập sâu", "xâm nhập mặn sâu vào nội đồng",
        "nồng độ mặn", "độ mặn tăng cao", "độ mặn vượt ngưỡng",
        "ranh mặn 1g/l", "ranh mặn 2g/l", "ranh mặn 3g/l", "ranh mặn 4g/l",
        "ranh mặn 1‰", "ranh mặn 2‰", "ranh mặn 3‰", "ranh mặn 4‰",
        "nước mặn", "nước lợ", "mặn hóa", "mặn hóa đất",
        "xâm mặn", "ngọt hóa", "giữ ngọt", "trữ ngọt",
        "đóng cống ngăn mặn", "mở cống lấy nước", "vận hành cống", "đập tạm ngăn mặn",
        "bơm chống hạn", "bơm chống mặn", "bơm nước ngọt",
        "xâm nhập mặn theo sông", "mặn theo cửa sông",
        "cháy đồng", "cháy thảm thực vật", "khô hanh",
        "nguy cơ cháy", "cấp độ cháy", "cảnh báo nắng nóng",
        "cây trồng héo", "héo úa", "khô héo", "cháy lá",
        "nứt nẻ ruộng đồng", "đồng ruộng nứt nẻ",
        "giảm năng suất", "suy giảm năng suất", "thiệt hại do hạn",
        "bốc hơi mạnh", "bốc hơi tăng", "thiếu ẩm", "độ ẩm thấp",
        "sa mạc hóa", "hoang mạc hóa",
        "nang nong keo dai", "han han", "kho han", "thieu nuoc",
        "xam nhap man", "nhiem man", "do man", "ranh man",
        "cam giac nhiet", "heat index", "muc nuoc xuong thap", "song can", "ho tro day"
    ],
    "wind_fog": [
        "gió mạnh", "gió giật", "biển động", "sóng lớn", "sóng cao", "cấm biển",
        "sương mù", "sương mù dày đặc", "tầm nhìn hạn chế",
        "gió mạnh cấp", "gió giật cấp", "gió mùa đông bắc", "không khí lạnh tăng cường",
        "biển động mạnh", "biển động rất mạnh", "sóng cao từ", "độ cao sóng",
        "cấm tàu thuyền", "tàu thuyền không ra khơi", "tàu thuyền vào bờ",
        "sương mù dày", "mù dày đặc", "tầm nhìn xa dưới", "giảm tầm nhìn", "mù quang",
        "gió mạnh trên đất liền", "gió mạnh diện rộng", "gió giật mạnh", "gió giật rất mạnh",
        "gió giật cấp 6", "gió giật cấp 7", "gió giật cấp 8", "gió giật cấp 9", "gió giật cấp 10",
        "gió giật cấp 11", "gió giật cấp 12", "gió giật trên cấp 12",
        "lốc gió", "gió lốc", "gió xoáy", "gió thổi mạnh",
        "gió cấp 6", "gió cấp 7", "gió cấp 8", "gió cấp 9", "gió cấp 10", "gió cấp 11", "gió cấp 12",
        "biển động dữ dội", "biển động nguy hiểm", "biển động cấp",
        "sóng biển", "sóng biển cao", "sóng biển tăng", "sóng biển mạnh",
        "sóng cao 3-5m", "sóng cao 4-6m", "sóng cao 5-7m", "sóng cao trên 6m",
        "độ cao sóng 3-5m", "độ cao sóng 4-6m", "độ cao sóng 5-7m",
        "biển động kèm sóng lớn", "nước biển động", "biển động do gió mùa",
        "ngoài khơi", "vùng biển xa", "ven biển", "trên vùng biển",
        "khuyến cáo tàu thuyền", "cảnh báo tàu thuyền", "tàu thuyền hạn chế ra khơi",
        "tạm dừng ra khơi", "dừng ra khơi", "neo đậu", "neo đậu tránh gió",
        "vào nơi trú tránh", "trú gió", "khu neo đậu", "khu trú bão",
        "cấm phương tiện ra biển", "cấm hoạt động trên biển", "đình chỉ hoạt động khai thác",
        "cảnh báo nguy hiểm trên biển", "vùng biển nguy hiểm",
        "sương mù dày đặc kéo dài", "sương mù xuất hiện", "sương mù bao phủ",
        "mù dày", "mù dày đặc", "mù mịt", "mù mưa", "mù sương",
        "sương mù biển", "sương mù ven biển",
        "tầm nhìn giảm", "tầm nhìn kém", "tầm nhìn thấp", "tầm nhìn bị hạn chế",
        "tầm nhìn dưới 500m", "tầm nhìn dưới 200m", "tầm nhìn dưới 100m",
        "tầm nhìn xa giảm", "tầm nhìn hạn chế nghiêm trọng",
        "khói mù", "mù khói", "ô nhiễm không khí làm giảm tầm nhìn",
        "gio manh", "gio giat", "bien dong", "song lon", "song cao",
        "cam bien", "cam tau thuyen", "tau thuyen vao bo", "tau thuyen khong ra khoi",
        "suong mu", "mu day dac", "tam nhin han che", "mu quang"
    ],
    "storm_surge": [
        "triều cường", "nước dâng", "nước dâng do bão", "nước biển dâng", "đỉnh triều",
        "triều cường kết hợp", "ngập do triều cường", "nước dâng cao",
        "biển dâng", "thủy triều dâng", "đỉnh triều cường", "triều cao",
        "nước dâng do áp thấp", "triều cường kỷ lục", "dâng cao bất thường",
        "ngập ven biển", "sóng tràn", "sóng đánh tràn", "tràn qua kè", "vượt báo động triều",
        "nước dâng do gió mạnh", "nước dâng do gió mùa", "nước dâng do gió mùa đông bắc",
        "nước dâng kết hợp sóng", "nước dâng do hoàn lưu", "dâng do áp thấp nhiệt đới",
        "dâng nước", "dâng triều", "mực nước biển dâng", "mực nước dâng", "mực nước ven biển dâng",
        "kỳ triều", "kỳ triều cường", "kỳ nước lớn", "kỳ nước ròng",
        "chân triều", "đỉnh nước", "mực nước triều", "mực triều", "mực nước theo triều",
        "mực nước đạt đỉnh", "mực nước triều dâng cao", "mực nước vượt ngưỡng",
        "triều lên", "triều xuống", "triều dâng nhanh", "triều dâng cao",
        "đợt triều cường", "triều cường tháng", "triều cường cuối tháng",
        "ngập do nước dâng", "ngập do nước biển dâng", "ngập do triều",
        "ngập vùng cửa sông", "ngập vùng hạ lưu", "ngập vùng trũng ven biển",
        "nước tràn vào khu dân cư ven biển", "nước biển tràn vào",
        "xói lở bờ biển do triều", "xâm thực bờ biển", "xâm thực do sóng",
        "sóng đánh vượt kè", "sóng vượt kè", "sóng vượt đê", "sóng tràn bờ",
        "sóng đánh tràn bờ", "sóng đánh tràn đê", "sóng đánh tràn qua đê biển",
        "nước tràn qua đê", "tràn đê biển", "vỡ kè", "sạt lở kè biển",
        "ngập do sóng tràn", "sóng lớn kết hợp triều cường", "sóng lớn kèm nước dâng",
        "biển xâm thực", "biển lấn",
        "báo động triều", "mực nước báo động triều", "vượt mức báo động triều",
        "vượt báo động 1 triều", "vượt báo động 2 triều", "vượt báo động 3 triều",
        "trieu cuong", "nuoc dang", "nuoc bien dang", "dinh trieu", "trieu cao",
        "song tran", "song danh tran", "tran qua ke", "ngap ven bien", "vuot bao dong trieu"

    ],
    "extreme_other": [
        "dông", "dông lốc", "lốc", "lốc xoáy", "vòi rồng", "mưa đá", "sét", "giông sét", "giông", "mưa giông", "giông tố",
        "rét đậm", "rét hại", "không khí lạnh", "sương muối", "băng giá",
        "mưa đá to", "sét đánh",
        "giông lốc mạnh", "lốc xoáy mạnh", "tố lốc",
        "rét đậm rét hại", "rét kỷ lục", "đợt rét", "không khí lạnh mạnh",
        "băng giá phủ trắng", "sương giá", "rét buốt",
        "mưa tuyết", "tuyết rơi",
        "dông mạnh", "dông dữ dội", "dông kèm lốc", "dông kèm sét",
        "dông kèm mưa đá", "dông kèm gió giật", "dông sét mạnh",
        "mây dông", "ổ dông", "tế bào dông", "mưa rào và dông",
        "mưa rào", "mưa rào mạnh", "mưa rào cục bộ",
        "lốc cục bộ", "lốc mạnh", "lốc dữ dội",
        "lốc xoáy cục bộ", "lốc xoáy kèm mưa đá",
        "vòi rồng trên biển", "vòi rồng trên đất liền",
        "gió giật do dông", "gió giật mạnh do dông",
        "gió giật nguy hiểm", "gió giật rất mạnh",
        "gió giật cấp", "giật cấp", "gió giật trên cấp",
        "sét mạnh", "sét dữ dội", "tia sét", "sét lan truyền",
        "nguy cơ sét", "cảnh báo sét", "đánh sét",
        "sét đánh chết người", "sét đánh bị thương", "bị sét đánh",
        "sét đánh trúng", "sét đánh cháy", "cháy do sét",
        "mưa đá lớn", "mưa đá dày", "mưa đá dữ dội",
        "mưa đá kèm dông", "mưa đá kèm gió giật",
        "mưa đá đường kính", "hạt mưa đá", "mưa đá gây hư hại",
        "mưa đá làm tốc mái", "mưa đá làm vỡ kính",
        "không khí lạnh tăng cường", "không khí lạnh tràn về",
        "không khí lạnh mạnh lên", "tăng cường không khí lạnh",
        "gió mùa đông bắc", "gió mùa đông bắc mạnh",
        "nhiệt độ giảm sâu", "giảm nhiệt mạnh", "giảm nhiệt đột ngột",
        "nhiệt độ xuống thấp", "nhiệt độ thấp kỷ lục",
        "trời rét", "rét sâu", "rét kéo dài", "rét tăng cường",
        "băng tuyết", "băng tuyết phủ trắng", "băng giá xuất hiện",
        "băng bám", "đóng băng", "đóng băng mặt đường",
        "sương muối dày", "sương muối phủ trắng", "sương muối xuất hiện",
        "tuyết rơi dày", "tuyết phủ", "có tuyết", "bông tuyết",
        "dong loc", "loc xoay", "voi rong", "mua da", "set", "giong set", "mua giong",
        "ret dam", "ret hai", "khong khi lanh", "suong muoi", "bang gia", "mua tuyet", "tuyet roi"
    ],
    "wildfire": [
        "cháy rừng", "nguy cơ cháy rừng", "cấp dự báo cháy rừng", "PCCCR",
        "cháy rừng lan rộng", "đám cháy rừng", "lửa rừng", "cháy thực bì",
        "cháy rừng phòng hộ", "nguy cơ cháy rừng cấp", "cấp cháy rừng",
        "phòng cháy chữa cháy rừng", "chữa cháy rừng", "đám cháy lan",
        "nguy cơ cháy rừng rất cao", "cấp cháy rừng cấp", "trực cháy rừng",
        "cháy rừng đặc dụng", "đốt nương làm rẫy", "đốt thực bì",
        "cảnh báo cháy rừng", "báo cháy rừng", "bản tin cảnh báo cháy rừng",
        "cấp nguy hiểm cháy rừng", "cấp độ nguy hiểm cháy rừng",
        "cấp IV", "cấp V", "cấp 4", "cấp 5",  # (hay đi kèm “cấp cháy rừng”)
        "phòng cháy", "chữa cháy", "phòng cháy chữa cháy", "PCCC",
        "ban chỉ đạo PCCCR", "phương án PCCCR", "kế hoạch PCCCR",
        "điểm cháy", "điểm phát lửa", "điểm nóng cháy rừng",
        "bùng phát", "bùng cháy", "cháy bùng", "cháy dữ dội", "cháy âm ỉ",
        "cháy lan nhanh", "cháy vượt kiểm soát", "khó khống chế", "mất kiểm soát",
        "khoanh vùng", "khống chế đám cháy", "dập lửa", "dập tắt", "dập tắt hoàn toàn",
        "tàn lửa", "nguy cơ bùng phát trở lại", "cháy tái bùng phát",
        "đường băng cản lửa", "tạo đường băng cản lửa", "vành đai cản lửa",
        "đốt rác", "đốt đồng", "đốt cỏ", "đốt ong", "đốt tổ ong",
        "đốt than", "đốt lửa trại", "lửa trại", "bất cẩn dùng lửa",
        "vứt tàn thuốc", "tàn thuốc lá", "đốt vàng mã",
        "đốt nương", "đốt rẫy", "phát nương", "đốt dọn thực bì",
        "kiểm lâm", "lực lượng kiểm lâm", "cảnh sát phòng cháy chữa cháy",
        "cảnh sát PCCC", "dân quân", "dân quân tự vệ", "bộ đội", "công an",
        "huy động lực lượng", "huy động phương tiện",
        "máy bơm", "vòi rồng", "xe chữa cháy", "xe bồn", "xe téc",
        "máy thổi gió", "dao phát", "vỉ dập lửa", "bình chữa cháy",
        "trực thăng", "máy bay", "thả nước", "thả nước từ trên cao",
        "khói", "khói mù", "khói dày đặc", "mùi khét", "tro bụi", "tàn tro",
        "ô nhiễm không khí", "chất lượng không khí", "AQI",
        "lan khói", "khói lan", "tầm nhìn giảm do khói",
        "chay rung", "chay thuc bi", "pcccr", "pccc", "cap du bao chay rung",
        "dot nuong", "dot ray", "dot co", "dot rac", "kiem lam", "dap lua", "khoang vung"
    ],
    "quake_tsunami": [
        "động đất", "rung chấn", "dư chấn", "nứt đất", "đứt gãy", "sóng thần", "cảnh báo sóng thần",
        "trận động đất", "chấn động", "địa chấn", "tâm chấn", "chấn tiêu",
        "động đất mạnh", "rung chấn mạnh", "dư chấn động đất",
        "độ richter", "độ lớn", "cường độ động đất", "thang richter",
        "rung lắc", "magnitude", "viện vật lý địa cầu", "Mw", "ML", "M",
        "sự kiện động đất", "tâm động đất", "vùng tâm chấn", "tâm chấn nông", "tâm chấn sâu",
        "độ sâu chấn tiêu", "độ sâu tâm chấn", "độ sâu chấn tiêu km",
        "đứt gãy kiến tạo", "đới đứt gãy", "đứt gãy hoạt động", "đứt gãy phương", "đới kiến tạo",
        "mảng kiến tạo", "ranh giới mảng", "dịch chuyển kiến tạo",
        "địa chấn kế", "máy đo địa chấn", "trạm địa chấn",
        "gia tốc nền", "gia tốc nền cực đại", "PGA", "PGV",
        "cường độ rung lắc", "mức độ rung lắc", "rung lắc cảm nhận",
        "thang MSK", "thang Mercalli", "Mercalli", "MMI",
        "nhà rung", "cửa kính rung", "đồ đạc rung lắc", "tường rung", "rung chuyển",
        "người dân cảm nhận rung lắc", "cảm nhận rung chấn", "giật mình vì rung chấn",
        "nứt tường", "nứt nhà", "nứt nền", "sập tường", "sập nhà", "hư hỏng do rung chấn",
        "sụt lún do động đất", "nứt nẻ mặt đất", "nứt gãy mặt đất",
        "Richter", "SR", "Rs", "M5", "M6", "M7",
        "Ms", "mb", "Md", "Mw", "ML",
        "độ lớn mô men", "mô men địa chấn", "seismic moment",
        "aftershock", "foreshock", "mainshock", "earthquake",
        "cảnh báo sóng thần khẩn cấp", "nguy cơ sóng thần", "bản tin sóng thần",
        "sóng thần có thể xảy ra", "khả năng xảy ra sóng thần",
        "mực nước biển biến động", "mực nước biển bất thường",
        "nước biển rút", "triều rút bất thường", "biển rút bất thường",
        "sóng biển dâng đột ngột", "sóng cao bất thường", "sóng tràn bờ do sóng thần",
        "sơ tán ven biển", "di dời khỏi vùng ven biển",
        "trung tâm cảnh báo sóng thần", "trung tâm báo tin động đất và cảnh báo sóng thần",
        "PTWC", "Pacific Tsunami Warning Center", "NOAA", "JMA",
        "dong dat", "rung chan", "du chan", "dia chan", "tam chan", "chan tieu",
        "do richter", "thang richter", "rung lac", "song than", "canh bao song than",
        "vien vat ly dia cau", "nha rung", "nuoc bien rut", "song bien dang dot ngot"
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
    """Build Google News RSS URL as fallback.
    Uses a combination of Impact keywords and Context (Disaster Type) keywords.
    """
    # Use refined impact list for GNews
    hazards = hazard_terms or GNEWS_IMPACT_KEYWORDS
    
    def _quote(terms):
        return [f'"{t.strip()}"' if ' ' in t.strip() else t.strip() for t in terms]

    hazards = _quote(hazards)
    
    # Google has a ~32 word limit for search queries. 
    # To be safe and effective, we sample from both lists.
    import random
    
    # 1. Sample Impact terms (Hazards) - target 15 terms
    hazards = hazard_terms or GNEWS_IMPACT_KEYWORDS
    hazards = _quote(hazards)
    if len(hazards) > 15:
        hazards = random.sample(hazards, 15)

    # 2. Sample Context terms (Disaster Types) - target 15 terms
    contexts = []
    if context_terms:
        contexts = _quote(context_terms)
        if len(contexts) > 15:
            contexts = random.sample(contexts, 15)

    base = "https://news.google.com/rss/search?q="
    
    # Build query: site:domain (Impacts) (Contexts)
    query_parts = [f"site:{domain}", "(" + " OR ".join(hazards) + ")"]
    if contexts:
        query_parts.append("(" + " OR ".join(contexts) + ")")
    
    query = " ".join(query_parts)
        
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
