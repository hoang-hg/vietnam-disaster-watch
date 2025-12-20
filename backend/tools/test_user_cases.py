
import sys
from pathlib import Path
import json
import re

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import nlp

def run_user_test_suite():
    test_cases = [
        # =========================
        # --- DEATHS (1-20) ---
        # =========================
        {"text": "Mưa lũ làm 3 người chết tại Yên Bái.", "expected": {"deaths": [3]}},
        {"text": "Tìm thấy thi thể 2 nạn nhân bị lũ cuốn.", "expected": {"deaths": [2]}},
        {"text": "Có ít nhất 5 người tử vong do sạt lở đất.", "expected": {"deaths": [5]}},
        {"text": "Vụ việc khiến 1 người thiệt mạng và 2 người bị thương.", "expected": {"deaths": [1], "injured": [2]}},
        {"text": "Đã có 4 nạn nhân tử vong sau khi đưa đi cấp cứu.", "expected": {"deaths": [4]}},
        {"text": "Lũ quét cướp đi sinh mạng của 3 cháu nhỏ.", "expected": {"deaths": [3]}},
        {"text": "Phát hiện 1 người chết đuối trên sông.", "expected": {"deaths": [1]}},
        {"text": "Hậu quả làm 2 người tử nạn tại chỗ.", "expected": {"deaths": [2]}},
        {"text": "Danh tính 3 nạn nhân thiệt mạng đã được xác định.", "expected": {"deaths": [3]}},
        {"text": "Khoảng 10 người chết trong trận động đất.", "expected": {"deaths": [10]}},
        {"text": "Không có người chết trong vụ cháy rừng.", "expected": {}},  # Negation
        {"text": "Chưa ghi nhận trường hợp tử vong nào.", "expected": {}},  # Negation
        {"text": "Sập cầu khiến 2 người chết, 3 người mất tích.", "expected": {"deaths": [2], "missing": [3]}},
        {"text": "Mưa lớn làm 1 người chết do sét đánh.", "expected": {"deaths": [1]}},
        {"text": "Trận bão khiến hơn 5 người thiệt mạng.", "expected": {"deaths": [5]}},  # lower-bound
        {"text": "Tai nạn do lũ ống khiến 6 nạn nhân tử vong.", "expected": {"deaths": [6]}},
        {"text": "Ngạt khí trong hầm làm 2 người tử vong.", "expected": {"deaths": [2]}},
        {"text": "Không loại trừ khả năng có người chết, đang xác minh.", "expected": {}},  # uncertain
        {"text": "Số người chết hiện là 0.", "expected": {}},  # zero
        {"text": "Thiên tai làm 3-5 người tử vong (thống kê ban đầu).", "expected": {"deaths": [3, 5]}},  # range

        # =========================
        # --- MISSING (21-35) ---
        # =========================
        {"text": "Hiện vẫn còn 3 người mất tích.", "expected": {"missing": [3]}},
        {"text": "Gia đình chưa tìm thấy 2 nạn nhân bị cuốn trôi.", "expected": {"missing": [2]}},
        {"text": "Lực lượng chức năng đang tìm kiếm 5 người mất liên lạc.", "expected": {"missing": [5]}},
        {"text": "Xác định danh tính 1 người bị nước cuốn trôi, chưa rõ tung tích.", "expected": {"missing": [1]}},
        {"text": "Bão số 3 làm 4 thuyền viên mất tích trên biển.", "expected": {"missing": [4], "marine": [{"num": 4, "unit": "thuyền viên"}]}},
        {"text": "Không có ai mất tích.", "expected": {}},  # Negation
        {"text": "Vẫn chưa liên lạc được với 2 người trong vùng lũ.", "expected": {"missing": [2]}},
        {"text": "Tìm kiếm 1 công nhân bị vùi lấp trong bùn đất.", "expected": {"missing": [1]}},  # entity != 'người' still intended
        {"text": "3 ngư dân mất tích trên vùng biển Quảng Ngãi.", "expected": {"missing": [3], "marine": [{"num": 3, "unit": "ngư dân"}]}},
        {"text": "Lũ ống cuốn trôi 2 người, hiện chưa tìm thấy.", "expected": {"missing": [2]}},
        {"text": "Chưa xác định tung tích 7 nạn nhân sau vụ sạt lở.", "expected": {"missing": [7]}},
        {"text": "Mất liên lạc with 1 nhóm phượt thủ, đang tìm kiếm.", "expected": {"missing": [1]}},
        {"text": "Không còn trường hợp nào mất liên lạc.", "expected": {}},  # Negation
        {"text": "Người dân báo có 2 người bị mắc kẹt trong khu vực ngập sâu.", "expected": {"missing": [2]}},
        {"text": "Đang rà soát, chưa rõ có ai mất tích hay không.", "expected": {}},  # uncertain

        # =========================
        # --- INJURED (36-50) ---
        # =========================
        {"text": "Vụ sạt lở làm 5 người bị thương.", "expected": {"injured": [5]}},
        {"text": "Đưa 10 nạn nhân đi cấp cứu.", "expected": {"injured": [10]}},
        {"text": "Có 3 người bị thương nặng đang điều trị.", "expected": {"injured": [3]}},
        {"text": "Sét đánh làm 2 người bị thương nhẹ.", "expected": {"injured": [2]}},
        {"text": "Hơn 20 người nhập viện sau bão.", "expected": {"injured": [20]}},
        {"text": "Không ghi nhận người bị thương.", "expected": {}},  # Negation
        {"text": "Chăm sóc y tế cho 5 người gặp nạn (không nêu bị thương).", "expected": {}},  # vague
        {"text": "Cứu sống 3 người bị thương trong đống đổ nát.", "expected": {"injured": [3]}},
        {"text": "Bệnh viện tiếp nhận 50 ca đa chấn thương.", "expected": {"injured": [50]}},
        {"text": "Sơ cứu cho 4 người bị xây xát.", "expected": {"injured": [4]}},
        {"text": "Vụ việc khiến 1 người thiệt mạng, không ai bị thương.", "expected": {"deaths": [1]}},  # injured negation
        {"text": "Có 6 nạn nhân bị bỏng, đang điều trị tại bệnh viện.", "expected": {"injured": [6]}},
        {"text": "Đưa đi bệnh viện 12 người do chấn thương.", "expected": {"injured": [12]}},
        {"text": "Ghi nhận 2 người bất tỉnh và 1 người gãy xương.", "expected": {"injured": [2, 1]}},  # multiple mentions
        {"text": "Chưa có thống kê số người bị thương.", "expected": {}},  # no number

        # =========================
        # --- DAMAGE MONEY (51-62) ---
        # =========================
        {"text": "Ước tính thiệt hại khoảng 500 tỷ đồng.", "expected": {"damage_billion_vnd": 500.0}},
        {"text": "Thiệt hại ban đầu lên tới 200 triệu đồng.", "expected": {"damage_billion_vnd": 0.2}},
        {"text": "Tổng thiệt hại hơn 1.000 tỷ VND.", "expected": {"damage_billion_vnd": 1000.0}},
        {"text": "Thiệt hại kinh tế ước tính 50 tỷ đồng.", "expected": {"damage_billion_vnd": 50.0}},
        {"text": "Gây tổn thất 2,5 tỷ đồng.", "expected": {"damage_billion_vnd": 2.5}},
        {"text": "Thiệt hại ước khoảng 1.2 tỷ đồng.", "expected": {"damage_billion_vnd": 1.2}},
        {"text": "Không có thiệt hại về tài sản.", "expected": {}},  # Negation
        {"text": "Thiệt hại lúa và hoa màu khoảng 10 tỷ đồng.", "expected": {"damage_billion_vnd": 10.0}},
        {"text": "Tổn thất dự kiến khoảng 30 tỷ đồng (đang cập nhật).", "expected": {"damage_billion_vnd": 30.0}},
        {"text": "Thiệt hại 700.000.000 đồng.", "expected": {}},  # regex may not cover raw VND
        {"text": "Tổng thiệt hại lên tới hàng trăm tỷ đồng.", "expected": {}},  # number words (optional feature)
        {"text": "Thiệt hại 500.000 đồng (rất nhỏ).", "expected": {}},  # too small / no triệu-tỷ

        # =========================
        # --- DAMAGE COUNT (63-75) ---
        # =========================
        {"text": "Bão làm tốc mái 50 căn nhà.", "expected": {"damage_count": 50}},
        {"text": "Sập 20 nhà dân.", "expected": {"damage_count": 20}},
        {"text": "Mưa lũ gây ngập 100 hộ dân.", "expected": {"damage_count": 100}},
        {"text": "Có 5 nhà bị sập hoàn toàn.", "expected": {"damage_count": 5}},
        {"text": "Hư hỏng 15 căn nhà.", "expected": {"damage_count": 15}},
        {"text": "300 nhà bị ngập sâu trong nước.", "expected": {"damage_count": 300}},
        {"text": "Vùi lấp 2 căn nhà trong đợt sạt lở.", "expected": {"damage_count": 2}},
        {"text": "Sập cầu khiến giao thông chia cắt, 1 căn nhà bị đổ sập.", "expected": {"damage_count": 1}},
        {"text": "Tốc mái trường học và 3 nhà văn hóa.", "expected": {"damage_count": 3}},
        {"text": "Không có nhà nào bị sập.", "expected": {}},  # Negation
        {"text": "Sửa chữa 10 căn nhà hư hỏng.", "expected": {"damage_count": 10}},
        {"text": "Ngập lụt làm 12 hộ phải sửa nhà.", "expected": {"damage_count": 12}},
        {"text": "Gió lốc làm tốc mái một ngôi nhà.", "expected": {"damage_count": 1}},  # number words: "một"

        # =========================
        # --- AGRICULTURE (76-85) ---
        # =========================
        {"text": "Mưa lớn làm ngập 500ha lúa.", "expected": {"agriculture": [{"num": 500, "unit": "ha"}]}},
        {"text": "Thiệt hại 20 ha hoa màu.", "expected": {"agriculture": [{"num": 20, "unit": "ha"}]}},
        {"text": "Cuốn trôi 1.000 con gia cầm.", "expected": {"agriculture": [{"num": 1000, "unit": "con"}]}},
        {"text": "Chết 50 con trâu bò.", "expected": {"agriculture": [{"num": 50, "unit": "con"}]}},
        {"text": "Ngập úng 5 héc ta rau màu.", "expected": {"agriculture": [{"num": 5, "unit": "ha"}]}},  # normalize hecta
        {"text": "Mất trắng 2 ha ao nuôi tôm.", "expected": {"agriculture": [{"num": 2, "unit": "ha"}]}},
        {"text": "Thiệt hại 10 tấn lúa sau mưa lũ.", "expected": {"agriculture": [{"num": 10, "unit": "tấn"}]}},  # requires unit support
        {"text": "Khoảng 5 sào ruộng bị vùi lấp.", "expected": {"agriculture": [{"num": 5, "unit": "sào"}]}},  # requires unit support
        {"text": "Hư hỏng 3 lồng bè nuôi cá.", "expected": {"agriculture": [{"num": 3, "unit": "lồng bè"}]}},  # requires unit support
        {"text": "Không ảnh hưởng đến sản xuất nông nghiệp.", "expected": {}},  # Negation/vague

        # =========================
        # --- MARINE (86-93) ---
        # =========================
        {"text": "Sóng lớn đánh chìm 3 tàu cá.", "expected": {"marine": [{"num": 3, "unit": "tàu cá"}]}},
        {"text": "2 thuyền viên trên tàu cá bị mất tích.", "expected": {"missing": [2], "marine": [{"num": 2, "unit": "thuyền viên"}]}},
        {"text": "Tìm thấy 1 tàu trôi dạt.", "expected": {"marine": [{"num": 1, "unit": "tàu"}]}},
        {"text": "Cứu hộ 5 ngư dân gặp nạn trên biển.", "expected": {"marine": [{"num": 5, "unit": "ngư dân"}]}},
        {"text": "Lật 1 ghe chài khi biển động.", "expected": {"marine": [{"num": 1, "unit": "ghe"}]}},  # requires 'ghe' support
        {"text": "Chìm 2 sà lan trên sông.", "expected": {"marine": [{"num": 2, "unit": "sà lan"}]}},
        {"text": "Mất liên lạc với 4 tàu đang hoạt động ngoài khơi.", "expected": {"marine": [{"num": 4, "unit": "tàu"}]}},
        {"text": "Không có tàu thuyền nào bị thiệt hại.", "expected": {}},  # Negation

        # =========================
        # --- DISRUPTION (94-100) ---
        # =========================
        {"text": "Sơ tán 300 hộ dân ra khỏi vùng nguy hiểm.", "expected": {"disruption": [{"num": 300, "unit": "hộ"}]}},
        {"text": "Di dời khẩn cấp 1.200 người.", "expected": {"disruption": [{"num": 1200, "unit": "người"}]}},
        {"text": "Sơ tán 50 hộ ở vùng thấp trũng.", "expected": {"disruption": [{"num": 50, "unit": "hộ"}]}},
        {"text": "Di dời 5 hộ do nguy cơ sạt lở.", "expected": {"disruption": [{"num": 5, "unit": "hộ"}]}},
        {"text": "Không phải sơ tán dân.", "expected": {}},  # Negation
        {"text": "Dự kiến sơ tán 1.000 hộ dân nếu bão đổ bộ.", "expected": {}},  # planned/forecast -> should be ignored
        {"text": "Cấm biển, tàu thuyền không ra khơi trong 24 giờ tới.", "expected": {}},  # boolean disruption (no numeric evac)
    ]

    print(f"--- Running {len(test_cases)} User-Provided Test Cases ---")
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
                # Find sum of 'nhà'/'hộ' in damage details
                got_count = 0
                for item in results.get("damage", []):
                    u = (item.get("unit") or "").lower()
                    if any(x in u for x in ["nhà", "hộ", "căn", "ngôi"]):
                         got_count += item.get("num", 0)
                if got_count != exp_val:
                    is_pass = False
                    fail_details.append(f"damage_count: Exp {exp_val}, Got {got_count}")
            elif key in ["agriculture", "marine", "disruption"]:
                # Check first item num & unit prefix
                got_list = results.get(key, [])
                if not got_list:
                    is_pass = False
                    fail_details.append(f"{key}: Exp {exp_val}, Got []")
                else:
                    item_exp = exp_val[0]
                    item_got = got_list[0]
                    if item_got.get("num") != item_exp.get("num"):
                        is_pass = False
                        fail_details.append(f"{key}.num: Exp {item_exp.get('num')}, Got {item_got.get('num')}")
                    
                    # Fuzzy unit check
                    u_exp = item_exp.get("unit", "").lower()
                    u_got = item_got.get("unit", "").lower()
                    
                    # Normalize 'héc ta' / 'ha'
                    if u_exp == 'ha' and 'héc ta' in u_got: u_got = 'ha'
                    if u_exp == 'ha' and 'hecta' in u_got: u_got = 'ha'
                    
                    if u_exp and u_exp not in u_got:
                         is_pass = False
                         fail_details.append(f"{key}.unit: Exp containing '{u_exp}', Got '{u_got}'")

        # Reverse check: anything found that wasn't expected?
        # Only if expected is empty {}.
        if not expected and (results.get("deaths") or results.get("missing") or results.get("injured") or flat.get("damage_billion_vnd") or results.get("damage") or results.get("agriculture") or results.get("marine") or results.get("disruption")):
             # But some might be booleans/tags we don't care about in this exact test
             # Let's check specifically for numeric values
             has_val = False
             if results.get("deaths"): has_val = True
             if results.get("missing"): has_val = True
             if results.get("injured"): has_val = True
             if flat.get("damage_billion_vnd") and flat.get("damage_billion_vnd") > 0: has_val = True
             if results.get("damage"): has_val = True
             if results.get("agriculture"): has_val = True
             if results.get("marine"): has_val = True
             if results.get("disruption"): 
                 # Check if numeric
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
    run_user_test_suite()
