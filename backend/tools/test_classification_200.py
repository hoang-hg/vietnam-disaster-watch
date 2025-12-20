import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.nlp import compute_disaster_signals, DISASTER_RULES

# 8 Groups defined in NLP:
# 1. storm
# 2. flood_landslide
# 3. heat_drought
# 4. wind_fog
# 5. storm_surge
# 6. extreme_other
# 7. wildfire
# 8. quake_tsunami

def run_test_cases():
    test_cases = [
        # --- GROUP 1: STORM (Bão, ATNĐ) ---
        ("Bão số 1 giật cấp 12 tiến vào biển Đông", "storm"),
        ("Siêu bão Yagi đổ bộ Quảng Ninh gây thiệt hại lớn", "storm"),
        ("Áp thấp nhiệt đới trên biển Đông có khả năng mạnh lên thành bão", "storm"),
        ("Tin bão khẩn cấp: Bão số 3 cách đất liền 100km", "storm"),
        ("Hoàn lưu bão gây mưa lớn tại các tỉnh miền núi", "storm"),
        ("Vị trí tâm bão số 2 ở vào khoảng 18.5 độ Vĩ Bắc", "storm"),
        ("Công điện khẩn ứng phó với bão Noru", "storm"),
        ("Dự báo bão: Gió giật cấp 15, sóng biển cao 5m", "storm"),
        ("Bão tan, suy yếu thành vùng áp thấp", "storm"),
        ("Áp thấp nhiệt đới gây gió mạnh trên biển", "storm"),
        ("Cơn bão số 9 hướng thẳng vào Nam Trung Bộ", "storm"),
        ("Theo dõi chặt chẽ diễn biến của bão Saola", "storm"),
        ("Bão Koinu giật cấp 16 di chuyển theo hướng Tây Tây Bắc", "storm"),
        ("ATNĐ có khả năng gây mưa to ở Bắc Bộ", "storm"),
        ("Ảnh hưởng của bão, nhiều tàu thuyền phải neo đậu", "storm"),
        ("Bão số 5: Quảng Trị đến Quảng Ngãi cấm biển", "storm"),
        ("Tin áp thấp nhiệt đới khẩn cấp", "storm"),
        ("Sức gió mạnh nhất vùng gần tâm bão", "storm"),
        ("Bão giật cấp 17 tàn phá Philippines, hướng về Biển Đông", "storm"),
        ("Dự báo hướng di chuyển của bão số 4", "storm"),
        ("Mắt bão sắc nét, cường độ rất mạnh", "storm"),
        ("Bão Sonca suy yếu nhanh khi vào bờ", "storm"),
        ("Cảnh báo gió mạnh trên biển do hoàn lưu bão", "storm"),
        ("Các tỉnh ven biển chủ động phòng chống bão", "storm"),
        ("Bộ đội biên phòng bắn pháo hiệu báo bão", "storm"),

        # --- GROUP 2: FLOOD & LANDSLIDE (Lũ, Ngập, Sạt lở) ---
        ("Mưa lớn kéo dài, cảnh báo lũ quét tại Lào Cai", "flood_landslide"),
        ("Nước sông Hồng dâng cao, báo động 2 tại Hà Nội", "flood_landslide"),
        ("Ngập lụt nghiêm trọng tại TP.HCM sau cơn mưa chiều qua", "flood_landslide"),
        ("Sạt lở đất tại đèo Bảo Lộc, giao thông chia cắt", "flood_landslide"),
        ("Hàng nghìn ngôi nhà bị ngập sâu trong nước lũ", "flood_landslide"),
        ("Thủy điện xả lũ, hạ du cần đề phòng ngập úng", "flood_landslide"),
        ("Vỡ đê sông Bùi, hàng trăm hộ dân phải sơ tan", "flood_landslide"),
        ("Cảnh báo sụt lún đất tại quy hoạch khu dân cư", "flood_landslide"),
        ("Lũ ống bất ngờ quét qua bản làng, 5 người mất tích", "flood_landslide"),
        ("Mưa như trút, đường phố Hà Nội thành sông", "flood_landslide"),
        ("Sạt lở bờ sông Hậu đe dọa hàng chục hộ dân", "flood_landslide"),
        ("Nguy cơ sạt lở đất đá ở vùng núi phía Bắc", "flood_landslide"),
        ("Đường sắt Bắc Nam bị ách tắc do sạt lở", "flood_landslide"),
        ("Mưa lớn diện rộng, cảnh báo ngập úng đô thị", "flood_landslide"),
        ("Mực nước đỉnh lũ trên các sông vượt mức báo động 3", "flood_landslide"),
        ("Hố tử thần xuất hiện giữa đường sau mưa lớn", "flood_landslide"),
        ("Đất đồi sạt trượt vùi lấp nhà dân", "flood_landslide"),
        ("Triều cường kết hợp mưa lớn gây ngập lụt diện rộng", "flood_landslide"), # Could be storm_surge too, but rain often implies flood logic
        ("Lũ về nhanh, người dân không kịp di dời tài sản", "flood_landslide"),
        ("Khắc phục hậu quả bão lũ, dọn dẹp bùn đất", "flood_landslide"),
        ("Hồ chứa thủy lợi đầy nước, nguy cơ tràn đập", "flood_landslide"),
        ("Sạt lở taluy dương tại QL6", "flood_landslide"),
        ("TP.HCM chống ngập bằng máy bơm công suất lớn", "flood_landslide"),
        ("Quảng Bình: 'Rốn lũ' Tân Hóa ngập sâu 3m", "flood_landslide"),
        ("Sụt lún nghiêm trọng tại bờ biển Cửa Đại", "flood_landslide"),
        
        # --- GROUP 3: HEAT, DROUGHT, SALINITY (Nắng nóng, Hạn, Mặn) ---
        ("Hà Nội nắng nóng gay gắt, nhiệt độ trên 40 độ C", "heat_drought"),
        ("Cảnh báo chỉ số tia UV ở mức gây hại cao", "heat_drought"),
        ("Hạn hán kéo dài, hồ thủy điện cạn trơ đáy", "heat_drought"),
        ("Xâm nhập mặn sâu vào nội đồng ĐBSCL", "heat_drought"),
        ("Miền Trung đối mặt với nắng nóng đặc biệt gay gắt", "heat_drought"),
        ("Người dân miền Tây thiếu nước ngọt sinh hoạt trầm trọng", "heat_drought"),
        ("Nhiệt độ kỷ lục được ghi nhận tại Tương Dương", "heat_drought"),
        ("Đất đai nứt nẻ do khô hạn kéo dài", "heat_drought"),
        ("Độ mặn tại các cửa sông tăng cao kỷ lục", "heat_drought"),
        ("Công bố tình huống khẩn cấp về hạn hán", "heat_drought"),
        ("Thời tiết oi bức, nhu cầu điện tăng vọt", "heat_drought"),
        ("Cây trồng chết khô vì thiếu nước tưới", "heat_drought"),
        ("El Nino gây nắng nóng cực đoan trên diện rộng", "heat_drought"),
        ("Cấp nước ngọt miễn phí cho vùng hạn mặn", "heat_drought"),
        ("Cảnh báo cháy rừng do nắng nóng kéo dài", "wildfire"), # NOTE: Rule matches wildfire first usually if "cháy rừng" is explicit
        ("Hạn mặn khốc liệt đe dọa vựa lúa miền Tây", "heat_drought"),
        ("Nắng nóng diện rộng ở Bắc Bộ và Trung Bộ", "heat_drought"),
        ("Dự báo nắng nóng còn kéo dài trong nhiều ngày tới", "heat_drought"),
        ("Nguy cơ kiệt sức, đột quỵ do sốc nhiệt", "heat_drought"),
        ("Nông dân điêu đứng vì lúa chết do nhiễm mặn", "heat_drought"),

        # --- GROUP 4: WIND & FOG (Gió mạnh, Sương mù) ---
        ("Gió mùa đông bắc gây gió mạnh trên biển", "wind_fog"),
        ("Sương mù dày đặc, sân bay Nội Bài hủy chuyến", "wind_fog"),
        ("Tầm nhìn hạn chế do sương mù tại Sa Pa", "wind_fog"),
        ("Cảnh báo gió mạnh cấp 6-7 trên vùng biển Cà Mau", "wind_fog"),
        ("Biển động mạnh, tàu thuyền không được ra khơi", "wind_fog"),
        ("Sóng biển cao 3-4m đánh sập bờ kè", "wind_fog"),
        ("Không khí lạnh gây gió giật mạnh ở vùng ven biển", "wind_fog"),
        ("Sương mù bao phủ Hà Nội, chất lượng không khí kém", "wind_fog"), # 'bụi mịn' filtered, but 'sương mù' is valid
        ("Lệnh cấm biển do thời tiết xấu, gió lớn", "wind_fog"),
        ("Gió to làm bật gốc cây cổ thụ", "wind_fog"), 
        ("Mù dày đặc trên đèo, cảnh báo an toàn giao thông", "wind_fog"),
        ("Thời tiết biển diễn biến xấu, sóng to gió lớn", "wind_fog"),
        ("Gió giật mạnh làm tốc mái nhà dân", "wind_fog"), # 'tốc mái' often implies damage, but 'gió giật' is the hazard
        ("Hiện tượng sương mù bức xạ vào sáng sớm", "wind_fog"),
        ("Cảnh báo lốc xoáy và gió giật mạnh trên biển", "extreme_other"),

        # --- GROUP 5: STORM SURGE (Nước dâng, Triều cường) ---
        ("Triều cường đạt đỉnh, TP.HCM ngập nặng", "storm_surge"),
        ("Cảnh báo nước dâng do bão ven biển miền Trung", "storm_surge"),
        ("Mực nước triều tại Vũng Tàu tăng cao", "storm_surge"),
        ("Ngập lụt do triều cường vượt báo động 3", "storm_surge"),
        ("Nước biển dâng gây xâm thực bờ biển", "storm_surge"),
        ("Đê biển bị sóng lớn đánh tràn do triều cường", "storm_surge"),
        ("Triều cường rằm tháng Giêng gây ngập đường phố", "storm_surge"),
        ("Sống chung với ngập do triều ở Cần Thơ", "storm_surge"),
        ("Dự báo đỉnh triều cường lịch sử", "storm_surge"),
        ("Nước dâng kết hợp sóng lớn phá hủy kè biển", "storm_surge"),
        ("Nguy cơ ngập úng vùng trũng thấp do triều cường", "storm_surge"),
        ("Ảnh hưởng của triều cường đến sinh hoạt người dân", "storm_surge"),
        ("Giải pháp chống ngập do triều cường", "storm_surge"),
        ("Triều cường dâng cao vào sáng sớm và chiều tối", "storm_surge"),
        ("Nước sông Sài Gòn dâng cao theo con nước triều", "storm_surge"),

        # --- GROUP 6: EXTREME OTHER (Rét, Lốc, Sét, Mưa đá) ---
        # User concern: "Rét đậm rét hại" check
        ("Miền Bắc đón đợt rét đậm, rét hại mạnh nhất mùa đông", "extreme_other"),
        ("Băng giá xuất hiện trên đỉnh Fansipan", "extreme_other"),
        ("Tuyết rơi tại Y Tý, Lào Cai thu hút du khách", "extreme_other"),
        ("Cảnh báo mưa đá và dông lốc tại các tỉnh vùng núi", "extreme_other"),
        ("Sét đánh chết trâu bò tại Thanh Hóa", "extreme_other"),
        ("Dông lốc làm tốc mái hàng trăm ngôi nhà", "extreme_other"),
        ("Vòi rồng xuất hiện ngoài khơi biển Kiên Giang", "extreme_other"),
        ("Lốc xoáy tàn phá vùng tâm", "extreme_other"),
        ("Trâu bò chết rét hàng loạt do rét hại kéo dài", "extreme_other"),
        ("Học sinh được nghỉ học tránh rét đậm", "extreme_other"),
        ("Không khí lạnh tăng cường, nhiệt độ giảm sâu", "extreme_other"),
        ("Sương muối gây hại cho hoa màu", "extreme_other"),
        ("Mưa đá kích thước lớn làm thủng mái nhà", "extreme_other"),
        ("Giông sét kàm sập cây", "extreme_other"),
        ("Cảnh báo dông, lốc, sét, mưa đá", "extreme_other"),
        ("Rét hại làm ảnh hưởng sức khỏe người già", "extreme_other"),
        ("Băng tuyết phủ trắng Mẫu Sơn", "extreme_other"),
        ("Lốc xoáy kèm mưa đá gây thiệt hại nặng", "extreme_other"),
        ("Người dân đốt lửa sưởi ấm vì quá rét", "extreme_other"),
        ("Thời tiết cực đoan: Mưa đá giữa mùa hè", "extreme_other"),

        # --- GROUP 7: WILDFIRE (Cháy rừng) ---
        ("Cháy rừng nghiêm trọng tại Vườn quốc gia Hoàng Liên", "wildfire"),
        ("Huy động hàng trăm người dập lửa rừng ở Hà Tĩnh", "wildfire"),
        ("Cảnh báo cháy rừng cấp cực kỳ nguy hiểm", "wildfire"),
        ("Nắng nóng làm gia tăng nguy cơ cháy rừng", "wildfire"),
        ("Lửa rừng lan nhanh do gió lào thổi mạnh", "wildfire"),
        ("Kiểm soát đám cháy thực bì, không để lan vào rừng", "wildfire"),
        ("Rừng phòng hộ bốc cháy dữ dội trong đêm", "wildfire"),
        ("Khởi tố vụ án vi phạm quy định PCCC gây cháy rừng", "wildfire"),
        ("Diễn tập phương án chữa cháy rừng", "wildfire"),
        ("Thiệt hại hàng chục ha rừng sau vụ hỏa hoạn", "wildfire"),
        ("Dập tắt hoàn toàn đám cháy rừng ở Gia Lai", "wildfire"),
        ("Báo động nguy cơ cháy rừng cấp 5 tại Tây Nguyên", "wildfire"),
        ("Lửa thiêu rụi rừng tràm U Minh Thượng", "wildfire"),
        ("Phát hiện điểm cháy rừng qua hệ thống camera", "wildfire"),
        ("Toàn dân tham gia phòng chống cháy rừng", "wildfire"),

        # --- GROUP 8: QUAKE & TSUNAMI (Động đất, Sóng thần) ---
        ("Động đất 4.5 độ Richter rung chuyển Kon Tum", "quake_tsunami"),
        ("Người dân Hà Nội cảm nhận rung chấn động đất", "quake_tsunami"),
        ("Thủy điện sông Tranh tích nước gây động đất kích thích", "quake_tsunami"),
        ("Cảnh báo sóng thần sau động đất mạnh ở biển", "quake_tsunami"),
        ("Viện Vật lý Địa cầu thông báo tin động đất", "quake_tsunami"),
        ("Dư chấn động đất khiến người dân hoang mang", "quake_tsunami"),
        ("Đứt gãy địa chất hoạt động mạnh gây rung lắc", "quake_tsunami"),
        ("Nhà cửa bị nứt do ảnh hưởng của động đất", "quake_tsunami"),
        ("Xác định tâm chấn động đất tại độ sâu 10km", "quake_tsunami"),
        ("Trận động đất có độ lớn 5.0 gây rung lắc mạnh", "quake_tsunami"), # 'độ lớn' removed but 'động đất' matches
        ("Sóng thần có thể cao tới 10m nếu xảy ra động đất lớn", "quake_tsunami"),
        ("Tập huấn kỹ năng ứng phó động đất, sóng thần", "quake_tsunami"),
        ("Hệ thống cảnh báo sớm sóng thần được kích hoạt", "quake_tsunami"),
        ("Ghi nhận hàng loạt trận động đất nhỏ trong ngày", "quake_tsunami"),
        ("Nứt đất kéo dài sau rung chấn", "quake_tsunami"),

        # --- NEGATIVE / NOISE (Should range NO MATCH or Filtered) ---
        ("Giá vàng hôm nay tăng mạnh", "NONE"),
        ("Đội tuyển Việt Nam vô địch AFF Cup", "NONE"),
        ("Tai nạn giao thông nghiêm trọng làm 3 người chết", "NONE"),
        ("Cháy nhà dân tại quận Cầu Giấy", "NONE"), # Urban fire is filtered
        ("Bão giá càn quét thị trường bất động sản", "NONE"), # Metaphor
        ("Cơn bão sao kê của nghệ sĩ", "NONE"), # Metaphor
        ("Làn sóng đầu tư vào chứng khoán", "NONE"), # Metaphor
        ("Chất lượng không khí Hà Nội ở mức xấu", "NONE"), # Filtered now
        ("Chỉ số AQI hôm nay rất cao, bụi mịn dày đặc", "NONE"), # Filtered now
        ("Dự báo thời tiết ngày mai trời đẹp, nắng nhẹ", "NONE"), # Generic weather
        ("Khởi tố bị can vụ án tham nhũng", "NONE"),
        ("Lễ hội pháo hoa quốc tế Đà Nẵng", "NONE"),
        ("Tuyển sinh đại học năm 2024", "NONE"),
        ("Xăng dầu giảm giá liên tiếp", "NONE"),
        ("Showbiz Việt dậy sóng vì scandal", "NONE"),
        ("Cơn sốt đất nền tại vùng ven", "NONE"),
        ("Xe container lật ngang đường gây ùn tắc", "NONE"),
        ("Rác thải nhựa gây ô nhiễm môi trường biển", "NONE"), # Pollution
        ("Độ lớn của thị trường thương mại điện tử", "NONE"), # 'độ lớn' w/o earthquake keywords
        ("Sóng gió cuộc đời của nữ ca sĩ", "NONE"), # Metaphor
    ]

    correct = 0
    total = len(test_cases)
    
    print(f"{'Text Content':<60} | {'Expected':<15} | {'Predicted':<15} | {'Result'}")
    print("-" * 110)

    for text, expected in test_cases:
        res = compute_disaster_signals(text)
        
        # Determine predicted group
        # Priority: Hard Negative -> NONE
        if res["hard_negative"]:
            predicted = "NONE"
        elif not res["rule_matches"]:
            predicted = "NONE"
        else:
            # Matches return a list, take the first one or logic
            # Usually strict priority isn't enforced in return, but standard convention
            matches = res["rule_matches"]
            if "wildfire" in matches: predicted = "wildfire"
            elif "storm" in matches: predicted = "storm"
            elif "quake_tsunami" in matches: predicted = "quake_tsunami"
            elif "storm_surge" in matches: predicted = "storm_surge" # Prioritize over flood
            elif "flood_landslide" in matches: predicted = "flood_landslide"
            elif "extreme_other" in matches: predicted = "extreme_other"
            elif "heat_drought" in matches: predicted = "heat_drought"
            elif "wind_fog" in matches: predicted = "wind_fog"
            else: predicted = matches[0]

        is_correct = (predicted == expected)
        # Allow overlap flexibility? 
        # E.g. "Gió giật mạnh làm tốc mái" -> could be wind or flood_landslide (damage).
        # We'll mark Strict for now.
        
        if not is_correct:
            print(f"{text[:58]:<60} | {expected:<15} | {predicted:<15} | FAIL")

    print("-" * 110)
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {correct/total*100:.2f}%")

if __name__ == "__main__":
    run_test_cases()
