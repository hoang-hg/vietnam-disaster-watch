
import sys
import os
sys.path.append(os.getcwd())
from app import nlp

test_cases = [
    # 1. Metaphors (Should FAIL)
    "Cơn bão giá quét qua thị trường bất động sản",
    "Bão sao kê càn quét showbiz Việt",
    "Siêu bão giảm giá đổ bộ Shopee",
    "Tạo nên cơn địa chấn trên sân cỏ",
    
    # 2. Accidents/Fire (Should FAIL or be CONDITIONAL VETO)
    "Cháy lớn tại quán karaoke ở Bình Dương làm 32 người chết",
    "Tai nạn thảm khốc trên cao tốc: 2 người tử vong",
    "Xe tải mất lái lao xuống vực, tài xế nguy kịch",
    "Nổ bình gas tại hộ gia đình, 1 người bị bỏng",

    # 3. Politics/Admin (Should FAIL)
    "Hội nghị tổng kết công tác phòng chống thiên tai năm 2025",
    "Thủ tướng chỉ đạo khắc phục hậu quả bão số 3 (Relevant but might be admin noise?)",
    "Lễ phát động tết trồng cây đời đời nhớ ơn Bác",
    "Đại hội đảng bộ tỉnh nhiệm kỳ mới",

    # 4. Genuine Disasters (Should PASS)
    "Bão số 1 giật cấp 12 đang tiến vào biển Đông",
    "Mưa lũ gây ngập lụt nghiêm trọng tại Huế",
    "Sạt lở đất vùi lấp 3 ngôi nhà tại Lào Cai, 5 người mất tích",
    "Động đất 5.3 độ richter rung chuyển Kon Tum",
    "Hạn hán khốc liệt khiến lúa chết khô tại miền Tây",
    "Triều cường đạt đỉnh, TP.HCM ngập sâu diện rộng",

    # 5. Ambiguous/Tricky (Check behavior)
    "Hàng trăm chiến sĩ giúp dân gặt lúa chạy lũ",
    "Khắc phục hậu quả sau mưa bão: Điện lực ra quân",
    "Mang Tết ấm đến với đồng bào vùng lũ",
    "Thanh niên tử vong do bị nước cuốn khi tắm sông"
]

with open("refinement_results.txt", "w", encoding="utf-8") as f:
    f.write(f"{'TITLE':<80} | {'SCORE':<5} | {'RESULT':<10} | {'REASON'}\n")
    f.write("-" * 120 + "\n")

    for title in test_cases:
        # Use diagnos to get full signal details
        res = nlp.diagnose(title, title)
        score = res["score"]
        signals = res["signals"]
        
        # Determine status classification
        if signals["absolute_veto"]: 
            status = "VETO"
        elif signals["conditional_veto"] and signals["hazard_score"] == 0:
            status = "COND_VETO"
        elif score >= 15.0:
            status = "PASS_AUTO"
        elif score >= 10.0:
            status = "PASS_PEND" 
        else:
            status = "FAIL"
        
        # Check for specific veto matches
        negative_hits = signals.get("negative_hit", [])
        
        f.write(f"{title[:80]:<80} | {score:<5.1f} | {status:<10} | {negative_hits} / Haz: {signals['hazard_score']}\n")

print("Results written to refinement_results.txt")
