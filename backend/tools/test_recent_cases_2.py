
import sys
from pathlib import Path
import json
import re

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import nlp

def run_recent_test_suite_2():
    test_cases = [
    # --- 1-20: Bão/ATNĐ/biển động/triều cường ---
    {"text": "Bão gây mưa to gió lớn làm 1 người chết và 3 người bị thương ở Bình Định.", "expected": {"deaths": [1], "injured": [3]}},
    {"text": "Gió giật mạnh làm tốc mái 90 căn nhà tại Phú Yên.", "expected": {"damage_count": 90}},
    {"text": "Áp thấp nhiệt đới khiến 2 tàu cá bị chìm, 4 ngư dân được cứu.", "expected": {"marine": [{"num": 2, "unit": "tàu cá"}]}},
    {"text": "Biển động làm 1 tàu cá trôi dạt, mất liên lạc với 6 thuyền viên.", "expected": {"marine": [{"num": 1, "unit": "tàu cá"}], "missing": [6]}},
    {"text": "Bão làm 2 người mất tích, đến sáng nay tìm thấy thi thể 1 người.", "expected": {"missing": [2], "deaths": [1]}},
    {"text": "Không ghi nhận thương vong do bão, nhưng tốc mái 35 căn nhà.", "expected": {"damage_count": 35}},
    {"text": "Hoàn lưu bão gây thiệt hại khoảng 18 tỷ đồng.", "expected": {"damage_billion_vnd": 18.0}},
    {"text": "Sơ tán 850 hộ dân ven biển trước khi bão vào.", "expected": {}},  # planned/before
    {"text": "Sau bão, di dời 420 người khỏi khu vực sạt lở.", "expected": {"disruption": [{"num": 420, "unit": "người"}]}},
    {"text": "Gió mạnh trên biển đánh chìm 3 phương tiện, 2 người mất tích.", "expected": {"marine": [{"num": 3, "unit": "phương tiện"}], "missing": [2]}},
    {"text": "Nước dâng do bão làm ngập 1.200 hộ dân vùng trũng.", "expected": {"damage_count": 1200}},
    {"text": "Bão khiến 1 người tử vong do điện giật và 5 người nhập viện.", "expected": {"deaths": [1], "injured": [5]}},
    {"text": "Mất liên lạc với 2 tàu hàng ngoài khơi do thời tiết xấu.", "expected": {"marine": [{"num": 2, "unit": "tàu hàng"}]}},
    {"text": "Lật 1 thuyền thúng, 1 ngư dân mất tích.", "expected": {"marine": [{"num": 1, "unit": "thuyền"}], "missing": [1]}},
    {"text": "Cứu nạn thành công 7 ngư dân trôi dạt trên biển.", "expected": {"marine": [{"num": 7, "unit": "ngư dân"}]}},
    {"text": "Bão làm sập 4 căn nhà và hư hỏng 22 căn khác.", "expected": {"damage_count": 26}},
    {"text": "Thiệt hại do bão ước 450 triệu đồng.", "expected": {"damage_billion_vnd": 0.45}},
    {"text": "Không có tàu thuyền nào bị chìm trong đợt biển động.", "expected": {}},  # negation
    {"text": "Bão làm 3 người bị thương, trong đó 1 người trọng thương.", "expected": {"injured": [3]}},
    {"text": "Bão gây đổ cột điện, 200 hộ dân mất điện diện rộng.", "expected": {"damage_count": 200}},

    # --- 21-40: Mưa lớn/lũ/ngập lụt ---
    {"text": "Mưa lớn gây ngập 800 nhà ở khu dân cư ven sông.", "expected": {"damage_count": 800}},
    {"text": "Lũ lên nhanh làm 2 người chết đuối khi qua suối.", "expected": {"deaths": [2]}},
    {"text": "Lũ quét cuốn trôi 3 người, hiện còn 2 người mất tích.", "expected": {"missing": [2]}},
    {"text": "Mưa lũ làm 6 người bị thương và sập 1 căn nhà.", "expected": {"injured": [6], "damage_count": 1}},
    {"text": "Ngập lụt gây thiệt hại 70 tỷ đồng.", "expected": {"damage_billion_vnd": 70.0}},
    {"text": "Mưa cực đoan làm cô lập 150 hộ dân.", "expected": {"damage_count": 150}},
    {"text": "Sơ tán 300 hộ dân do nước dâng cao.", "expected": {"disruption": [{"num": 300, "unit": "hộ"}]}},
    {"text": "Không ghi nhận người chết, mất tích trong đợt mưa lũ.", "expected": {}},  # negation
    {"text": "Mưa lớn làm 1 người mất tích, 4 người bị thương.", "expected": {"missing": [1], "injured": [4]}},
    {"text": "Nước lũ làm hư hỏng 40 căn nhà, tốc mái 12 căn.", "expected": {"damage_count": 52}},
    {"text": "Mưa lớn gây thiệt hại 2,8 tỷ đồng và ngập 90ha lúa.", "expected": {"damage_billion_vnd": 2.8, "agriculture": [{"num": 90, "unit": "ha"}]}},
    {"text": "Lũ làm chết 500 con gia cầm và cuốn trôi 2 cây cầu tạm.", "expected": {"agriculture": [{"num": 500, "unit": "con"}]}},
    {"text": "Ngập sâu khiến 1.600 hộ dân bị chia cắt.", "expected": {"damage_count": 1600}},
    {"text": "Mưa lớn, dự kiến sơ tán 1.000 người nếu nước tiếp tục lên.", "expected": {}},  # planned
    {"text": "Lũ bùn đá làm 1 người tử vong and 1 người mất tích.", "expected": {"deaths": [1], "missing": [1]}},
    {"text": "Tìm thấy thi thể 2 nạn nhân mất tích sau lũ.", "expected": {"deaths": [2]}},
    {"text": "Mưa lớn làm sạt lở đường, 5 người bị thương khi xe trượt.", "expected": {"injured": [5]}},
    {"text": "Nước tràn vào nhà làm 250 hộ phải di dời khẩn cấp.", "expected": {"disruption": [{"num": 250, "unit": "hộ"}]}},
    {"text": "Mưa lũ làm thiệt hại 900 triệu đồng.", "expected": {"damage_billion_vnd": 0.9}},
    {"text": "Không có thiệt hại về tài sản sau khi nước rút.", "expected": {}},  # negation

    # --- 41-55: Sạt lở/sụt lún/xói lở ---
    {"text": "Sạt lở đất làm sập 2 căn nhà, 3 người bị thương.", "expected": {"damage_count": 2, "injured": [3]}},
    {"text": "Sạt lở vùi lấp 4 người, hiện còn 1 người mất tích.", "expected": {"missing": [1]}},
    {"text": "Sạt lở khiến 1 người thiệt mạng, thiệt hại khoảng 6 tỷ đồng.", "expected": {"deaths": [1], "damage_billion_vnd": 6.0}},
    {"text": "Sụt lún làm hư hỏng 18 căn nhà tại khu dân cư.", "expected": {"damage_count": 18}},
    {"text": "Đá lăn làm 2 người bị thương nặng.", "expected": {"injured": [2]}},
    {"text": "Không ghi nhận thương vong do sạt lở, nhưng 60 hộ dân bị cô lập.", "expected": {"damage_count": 60}},
    {"text": "Di dời 500 người khỏi khu vực có nguy cơ sạt trượt.", "expected": {"disruption": [{"num": 500, "unit": "người"}]}},
    {"text": "Sạt lở làm nứt đường, ước thiệt hại 1,5 tỷ đồng.", "expected": {"damage_billion_vnd": 1.5}},
    {"text": "Sụt lún gây sập 1 căn nhà và 1 người bị thương.", "expected": {"damage_count": 1, "injured": [1]}},
    {"text": "Tìm thấy thi thể 1 nạn nhân bị vùi lấp.", "expected": {"deaths": [1]}},
    {"text": "Sạt lở bờ sông làm trôi 3 căn nhà.", "expected": {"damage_count": 3}},
    {"text": "Không phải sơ tán dân vì vết nứt đã được xử lý.", "expected": {}},  # negation
    {"text": "Sạt lở làm 2 người chết, 2 người bị thương.", "expected": {"deaths": [2], "injured": [2]}},
    {"text": "Sạt lở gây thiệt hại 250 triệu đồng.", "expected": {"damage_billion_vnd": 0.25}},
    {"text": "Đường bị chia cắt, 110 hộ dân tạm thời cô lập.", "expected": {"damage_count": 110}},

    # --- 56-65: Sét/lốc/mưa đá ---
    {"text": "Sét đánh làm 2 người tử vong tại cánh đồng.", "expected": {"deaths": [2]}},
    {"text": "Sét đánh khiến 7 người bị thương, 3 người nhập viện.", "expected": {"injured": [7]}},
    {"text": "Lốc xoáy làm tốc mái 140 căn nhà ở Sóc Trăng.", "expected": {"damage_count": 140}},
    {"text": "Vòi rồng làm lật 2 tàu du lịch trên sông, 9 người bị thương.", "expected": {"marine": [{"num": 2, "unit": "tàu du lịch"}], "injured": [9]}},
    {"text": "Mưa đá làm hư hỏng 1.500 nhà dân vùng núi.", "expected": {"damage_count": 1500}},
    {"text": "Mưa đá làm thiệt hại 60ha hoa màu.", "expected": {"agriculture": [{"num": 60, "unit": "ha"}]}},
    {"text": "Gió lốc làm sập 6 căn nhà và thiệt hại 1 tỷ đồng.", "expected": {"damage_count": 6, "damage_billion_vnd": 1.0}},
    {"text": "Không ghi nhận thiệt hại do lốc, chỉ có mưa lớn.", "expected": {}},  # negation
    {"text": "Sét đánh gây cháy, 1 nhà bị sập đổ và 2 người bị thương.", "expected": {"damage_count": 1, "injured": [2]}},
    {"text": "Lốc làm 1 người bị thương nhẹ and 20 căn nhà tốc mái.", "expected": {"injured": [1], "damage_count": 20}},

    # --- 66-78: Hạn hán/xâm nhập mặn/nắng nóng ---
    {"text": "Hạn hán làm thiệt hại 350ha lúa.", "expected": {"agriculture": [{"num": 350, "unit": "ha"}]}},
    {"text": "Xâm nhập mặn làm ảnh hưởng 2.000ha cây ăn trái.", "expected": {"agriculture": [{"num": 2000, "unit": "ha"}]}},
    {"text": "Thiếu nước sinh hoạt do hạn hán, 1.200 hộ dân bị ảnh hưởng.", "expected": {"damage_count": 1200}},
    {"text": "Nắng nóng làm 12 người nhập viện vì kiệt sức.", "expected": {"injured": [12]}},
    {"text": "Nắng nóng làm 1 người tử vong do sốc nhiệt.", "expected": {"deaths": [1]}},
    {"text": "Không ghi nhận ca nhập viện do nắng nóng.", "expected": {}},  # negation
    {"text": "Hạn mặn gây thiệt hại khoảng 40 tỷ đồng.", "expected": {"damage_billion_vnd": 40.0}},
    {"text": "Xâm nhập mặn làm chết 900 con gia cầm.", "expected": {"agriculture": [{"num": 900, "unit": "con"}]}},
    {"text": "Hạn hán khiến 2.400 con gia súc thiếu nước, ước thiệt hại 2,2 tỷ đồng.", "expected": {"agriculture": [{"num": 2400, "unit": "con"}], "damage_billion_vnd": 2.2}},
    {"text": "Di dời 180 hộ dân đến điểm cấp nước tập trung.", "expected": {"disruption": [{"num": 180, "unit": "hộ"}]}},
    {"text": "Thiếu nước kéo dài, dự kiến khoan thêm giếng cho 500 hộ.", "expected": {}},  # planned
    {"text": "Nắng nóng làm cháy 2 căn nhà và thiệt hại 600 triệu đồng.", "expected": {"damage_count": 2, "damage_billion_vnd": 0.6}},
    {"text": "Hạn hán, chưa có thống kê thiệt hại.", "expected": {}},

    # --- 79-88: Cháy rừng ---
    {"text": "Cháy rừng làm thiệt hại 80ha rừng phòng hộ.", "expected": {"agriculture": [{"num": 80, "unit": "ha"}]}},
    {"text": "Cháy rừng khiến 1 người bị thương do bỏng.", "expected": {"injured": [1]}},
    {"text": "Cháy rừng làm 2 người tử vong khi tham gia chữa cháy.", "expected": {"deaths": [2]}},
    {"text": "Cháy rừng lan rộng, sơ tán 320 hộ dân khỏi khu vực nguy hiểm.", "expected": {"disruption": [{"num": 320, "unit": "hộ"}]}},
    {"text": "Thiệt hại do cháy rừng ước 12 tỷ đồng.", "expected": {"damage_billion_vnd": 12.0}},
    {"text": "Khói cháy rừng khiến 25 người nhập viện kiểm tra.", "expected": {"injured": [25]}},
    {"text": "Đám cháy làm sập 5 căn nhà gần rừng.", "expected": {"damage_count": 5}},
    {"text": "Không có thiệt hại về người sau khi dập tắt cháy rừng.", "expected": {}},  # negation
    {"text": "Cảnh báo nguy cơ cháy rừng cấp V, chưa xảy ra cháy.", "expected": {}},  # warning only
    {"text": "Cháy rừng làm thiệt hại 150 triệu đồng.", "expected": {"damage_billion_vnd": 0.15}},

    # --- 89-94: Rét hại/sương muối/mưa đá ---
    {"text": "Rét hại làm chết 60 con trâu bò và 30ha rau màu bị hư hại.", "expected": {"agriculture": [{"num": 60, "unit": "con"}, {"num": 30, "unit": "ha"}]}},
    {"text": "Sương muối làm thiệt hại 110ha cây trồng.", "expected": {"agriculture": [{"num": 110, "unit": "ha"}]}},
    {"text": "Mưa đá kèm rét làm tốc mái 25 căn nhà.", "expected": {"damage_count": 25}},
    {"text": "Rét hại khiến 4 người nhập viện.", "expected": {"injured": [4]}},
    {"text": "Không ghi nhận thiệt hại do sương muối trong đợt này.", "expected": {}},  # negation
    {"text": "Rét đậm kéo dài, dự kiến hỗ trợ 1.000 hộ dân vùng cao.", "expected": {}},  # planned

    # --- 95-97: Động đất ---
    {"text": "Động đất làm nứt 30 căn nhà và 3 người bị thương.", "expected": {"damage_count": 30, "injured": [3]}},
    {"text": "Dư chấn khiến 1 người bị thương, không có thiệt hại khác.", "expected": {"injured": [1]}},
    {"text": "Không có thiệt hại sau trận động đất, người dân chỉ cảm nhận rung lắc.", "expected": {}},

    # --- 98-100: Nhiễu (họp/diễn tập/kế hoạch) ---
    {"text": "Ban chỉ huy họp khẩn, triển khai lực lượng ứng phó; chưa xảy ra thiệt hại.", "expected": {}},
    {"text": "Diễn tập phòng chống thiên tai với 500 người tham gia.", "expected": {}},
    {"text": "Ban hành kế hoạch ứng phó bão, chưa ghi nhận thiệt hại.", "expected": {}},
]

    print(f"--- Running {len(test_cases)} Recent Test Cases Set 2 ---")
    passed = 0
    total = len(test_cases)
    
    for i, case in enumerate(test_cases):
        text = case['text']
        expected = case['expected']
        
        results = nlp.extract_impact_details(text)
        flat = nlp.extract_impacts(text)
        
        is_pass = True
        fail_details = []

        for key, exp_val in expected.items():
            if key == "deaths" or key == "missing" or key == "injured":
                got = sorted(results.get(key, []))
                exp = sorted(exp_val)
                if got != exp:
                    is_pass = False
                    fail_details.append(f"{key}: Exp {exp}, Got {got}")
            elif key == "damage_billion_vnd":
                got = flat.get("damage_billion_vnd")
                if got != exp_val:
                    is_pass = False
                    fail_details.append(f"damage_billion_vnd: Exp {exp_val}, Got {got}")
            elif key == "damage_count":
                if isinstance(exp_val, list):
                    got_count = []
                    for item in results.get("damage", []):
                        u = (item.get("unit") or "").lower()
                        if any(x in u for x in ["nhà", "hộ", "căn", "ngôi"]):
                             got_count.append(item.get("num", 0))
                    if sorted(got_count) != sorted(exp_val):
                         is_pass = False
                         fail_details.append(f"damage_count: Exp {exp_val}, Got {got_count}")
                else:
                    # Sum for simple count
                    got_count = 0
                    for item in results.get("damage", []):
                        u = (item.get("unit") or "").lower()
                        if any(x in u for x in ["nhà", "hộ", "căn", "ngôi"]):
                             got_count += item.get("num", 0)
                    if got_count != exp_val:
                        is_pass = False
                        fail_details.append(f"damage_count: Exp {exp_val}, Got {got_count}")
            elif key in ["agriculture", "marine", "disruption"]:
                got_list = results.get(key, [])
                if not got_list:
                    is_pass = False
                    fail_details.append(f"{key}: Exp {exp_val}, Got []")
                else:
                    # Check all expected items
                    for item_exp in exp_val:
                        found_match = False
                        for item_got in got_list:
                            if item_got.get("num") == item_exp.get("num"):
                                u_exp = item_exp.get("unit", "").lower()
                                u_got = item_got.get("unit", "").lower()
                                if u_exp == 'ha' and ('héc ta' in u_got or 'hecta' in u_got): u_got = 'ha'
                                if u_exp in u_got:
                                    found_match = True
                                    break
                        if not found_match:
                            is_pass = False
                            fail_details.append(f"{key}: Could not find match for {item_exp} in {got_list}")

        # Reverse check: anything found that wasn't expected?
        if not expected and (results.get("deaths") or results.get("missing") or results.get("injured") or (flat.get("damage_billion_vnd") and flat.get("damage_billion_vnd") > 0) or results.get("damage") or results.get("agriculture") or results.get("marine") or results.get("disruption")):
             has_val = False
             if results.get("deaths"): has_val = True
             if results.get("missing"): has_val = True
             if results.get("injured"): has_val = True
             if flat.get("damage_billion_vnd") and flat.get("damage_billion_vnd") > 0: has_val = True
             if results.get("damage"): has_val = True
             if results.get("agriculture"): has_val = True
             if results.get("marine"): has_val = True
             if results.get("disruption"): 
                 for d in results.get("disruption", []):
                     if d.get("num"): has_val = True
             
             if has_val:
                 is_pass = False
                 fail_details.append(f"Unexpected data found: {results}")

        if not is_pass:
            print(f"[{i+1}] FAIL: '{text}'")
            for fd in fail_details:
                print(f"   - {fd}")
        else:
            passed += 1
            
    print(f"\nFinal Score: {passed}/{total}")

if __name__ == "__main__":
    run_recent_test_suite_2()
