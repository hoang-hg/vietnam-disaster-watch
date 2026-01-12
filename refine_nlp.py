
import re

file_path = r"d:\viet-disaster-watch\backend\app\nlp.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new ABSOLUTE_VETO list
new_veto_list = r"""ABSOLUTE_VETO = [
    # =========================================================================
    # 1. METAPHORS & IDIOMS (Figurative use of disaster terms)
    # =========================================================================
    r"(?i)cơn\s*bão\s*(?:chứng\s*khoán|tài\s*chính|giá\s*cả|lạm\s*phát|dư\s*luận|truyền\s*thông|tin\s*đồn|cảm\s*xúc|lòng|tình|hạnh\s*phúc|sale|quà\s*tặng|ưu\s*đãi|diss|drama)",
    r"(?i)bão\s*(?:giá|sale|đơn|khuyến\s*mãi|lòng|tình|chứng\s*khoán|coin|crypto|sao\s*kê|drama|scandal|comment|like|view|tương\s*tác)",
    r"(?i)\b(?:gây\s*bão|tạo\s*bão)\s*(?:mạng|cộng\s*đồng|dư\s*luận|sân\s*khấu|phòng\s*vé)\b",
    r"(?i)cơn\s*lốc\s*(?:quà\s*tặng|khuyến\s*mãi|giảm\s*giá|tài\s*chính|sân\s*cỏ|đường\s*biên|chuyển\s*nhượng|vàng|bạc|sân\s*khấu)",
    r"(?i)sóng\s*thần\s*(?:tài\s*chính|công\s*nghệ|sa\s*thải|nhân\s*sự|pháp\s*lý|dư\s*luận|biểu\s*tình)",
    r"(?i)làn\s*sóng\s*(?:đầu\s*tư|tẩy\s*chay|di\s*cư|covid|lây\s*nhiễm|sa\s*thải|nhập\s*cư|công\s*nghệ|hàn\s*lưu|văn\s*hóa)(?!.*(?:sóng\s*thần|triều\s*cường))",
    r"(?i)hạn\s*hán\s*(?:bàn\s*thắng|ý\s*tưởng|lời\s*khen|tài\s*chính|vốn|nhân\s*tài|cảm\s*xúc)",
    r"(?i)khô\s*hạn\s*(?:bàn\s*thắng|vốn|ý\s*tưởng|tình\s*cảm|lời\s*nói)",
    r"(?i)mưa\s*(?:bàn\s*thắng|lời\s*khen|gạch\s*đá|bom|đạn|voucher|deal|quà|ưu\s*đãi|đơn\s*hàng|tin\s*nhắn|góp\s*ý)",
    r"(?i)ngập\s*(?:tràn\s*hạnh\s*phúc|tràn\s*niềm\s*vui|đơn|deal|quà|lời\s*chúc|drama|tin\s*nhắn|thính)",
    r"(?i)cháy\s*(?:vé|hàng|show|phòng|kệ|mạng|máy|phố|hết\s*mình|giáo\s*án|deadline|túi|tài\s*khoản|phanh|nắng)",
    r"(?i)đóng\s*băng\s*(?:tài\s*khoản|thị\s*trường|bất\s*động\s*sản|giao\s*dịch|quan\s*hệ|tài\s*sản|dự\s*án|hoạt\s*động)(?!.*(?:mưa|rét|lạnh|tuyết))",
    r"(?i)bốc\s*hơi\s*(?:tài\s*khoản|vốn|giá\s*trị|lợi\s*nhuận|con\s*người|khỏi\s*thị\s*trường)(?!.*(?:nước|nắng|nóng))",
    r"(?i)sạt\s*lở\s*(?:niềm\s*tin|uy\s*tín|đạo\s*đức|nhân\s*cách|giá\s*cổ\s*phiếu)",
    r"(?i)rung\s*chấn\s*(?:thị\s*trường|sân\s*cỏ|nhà\s*trắng|điện\s*kremlin|cung\s*điện|showbiz|giới\s*giải\s*trí)",
    r"(?i)chấn\s*động\s*(?:dư\s*luận|thế\s*giới|showbiz|cầu\s*trường|giới\s*trẻ|mạng\s*xã\s*hội)",
    r"(?i)địa\s*chấn\s*(?:sân\s*cỏ|tại\s*qatar|tại\s*world\s*cup|lang\s*túc\s*cầu)",
    r"(?i)cú\s*sốc\s*(?:tâm\s*lý|đầu\s*đời|thị\s*trường|tài\s*chính|văn\s*hóa|giá|tỷ\s*giá)",
    r"(?i)không\s*khí\s*lạnh\s*(?:nhạt|lùng|giá|trong\s*quan\s*hệ)",
    r"(?i)giải\s*nhiệt\s*(?:thị\s*trường|mùa\s*hè|cơn\s*khát|cuộc\s*sống)(?!.*(?:nắng|nóng|hạn))",
    r"(?i)thổi\s*bay\s*(?:tài\s*khoản|thành\s*quả|lợi\s*nhuận|bay\s*nóc\s*nhà\s*(?:theo\s*nghĩa\s*bóng)|mỡ\s*thừa)",

    # =========================================================================
    # 2. SPORTS & GAMES (Racing, Matches, Scores, Tournaments)
    # =========================================================================
    r"(?i)\b(?:bóng\s*đá|cầu\s*thủ|sân\s*cỏ|thủ\s*môn|tiền\s*đạo|hậu\s*vệ|trọng\s*tài|huấn\s*luyện\s*viên|hlv|var)\b",
    r"(?i)\b(?:v-league|premier\s*league|la\s*liga|serie\s*a|bundesliga|champions\s*league|europa|world\s*cup|euro\s*20\d{2}|asian\s*cup|aff\s*cup|sea\s*games)\b",
    r"(?i)\b(?:ghi\s*bàn|bàn\s*thắng|tỉ\s*số|kết\s*quả\s*trận|trực\s*tiếp\s*bóng\s*đá|nhận\s*định|soi\s*kèo|tỷ\s*lệ\s*cược|kèo\s*nhà\s*cái)\b",
    r"(?i)\b(?:tennis|quần\s*vợt|cầu\s*lông|bóng\s*chuyền|bóng\s*rổ|điền\s*kinh|bơi\s*lội|đua\s*xe|f1|marathon)\b",
    r"(?i)\b(?:esports|liên\s*quân|liên\s*minh\s*huyền\s*thoại|pubg|free\s*fire|game\s*thủ|tướng|skin|rank|leo\s*rank)\b",
    r"(?i)\b(?:man\s*utd|man\s*city|liverpool|arsenal|chelsea|real\s*madrid|barca|bayern|psg|việt\s*nam\s*vs)\b",
    r"(?i)\b(?:đặt\s*cược|cá\s*độ|bet|nhà\s*cái|kèo|tài\s*xỉu|xóc\s*đĩa|bắn\s*cá|nổ\s*hũ|game\s*bài|đổi\s*thưởng)\b",

    # =========================================================================
    # 3. ENTERTAINMENT & SHOWBIZ (Music, Movies, Celebs)
    # =========================================================================
    r"(?i)\b(?:showbiz|vbiz|kbiz|cbiz|US-UK|kpop|vpop|idol|thần\s*tượng|fandom|fan\s*meeting)\b",
    r"(?i)\b(?:hoa\s*hậu|á\s*hậu|người\s*đẹp|siêu\s*mẫu|ca\s*sĩ|diễn\s*viên|nghệ\s*sĩ|mc|tiểu\s*vy|thùy\s*tiên|sơn\s*tùng|trấn\s*thành)\b",
    r"(?i)\b(?:mv|album|single|ca\s*khúc|bài\s*hát|top\s*trending|nhạc\s*số|concert|liveshow|hòa\s*nhạc|phòng\s*thu)\b",
    r"(?i)\b(?:phim|bom\s*tấn|rạp\s*chiếu|doanh\s*thu\s*phòng\s*vé|trailer|teaser|tập\s*mới|series|netflix|điện\s*ảnh)\b",
    r"(?i)\b(?:drama|scandal|bóc\s*phốt|sao\s*kê|người\s*thứ\s*ba|trà\s*xanh|tiểu\s*tam|ly\s*hôn|chia\s*tay|hẹn\s*hò|đám\s*cưới)\b",
    r"(?i)\b(?:gameshow|truyền\s*hình\s*thực\s*tế|táo\s*quân|gặp\s*nhau\s*cuối\s*năm|chương\s*trình\s*giải\s*trí)\b",

    # =========================================================================
    # 4. FINANCE, ECONOMY & MARKET (Stocks, Crypto, Real Estate)
    # =========================================================================
    r"(?i)\b(?:chứng\s*khoán|cổ\s*phiếu|vn-index|hnx|upcom|thanh\s*khoản|khớp\s*lệnh|sàn\s*giao\s*dịch|bảng\s*điện)\b",
    r"(?i)\b(?:bitcoin|crypto|blockchain|nft|tiền\s*ảo|tiền\s*kỹ\s*thuật\s*số|eth|bnb|usdt|ví\s*điện\s*tử)\b",
    r"(?i)\b(?:ngân\s*hàng|lãi\s*suất|tín\s*dụng|vay\s*vốn|nợ\s*xấu|đáo\s*hạn|giải\s*ngân|tỷ\s*giá|ngoại\s*tệ|vàng|sjc|doji)\b",
    r"(?i)\b(?:bất\s*động\s*sản|nhà\s*đất|đất\s*nền|căn\s*hộ|chung\s*cư|biệt\s*thự|shophouse|mở\s*bán|sổ\s*đỏ|quy\s*hoạch)(?!.*(?:sạt\s*lở|ngập|lũ|bão))\b",
    r"(?i)\b(?:marketing|thương\s*hiệu|quảng\s*cáo|doanh\s*số|doanh\s*thu|lợi\s*nhuận|cổ\s*tức|đại\s*hội\s*cổ\s*đông)\b",

    # =========================================================================
    # 5. MARKETING, SHOPPING & LIFESTYLE (Sales, Tech, Food)
    # =========================================================================
    r"(?i)\b(?:khuyến\s*mãi|giảm\s*giá|sale|voucher|coupon|deal|quà\s*tặng|trúng\s*thưởng|xổ\s*số|vietlott)\b",
    r"(?i)\b(?:iphone|samsung|xiaomi|oppo|macbook|laptop|smartphone|review|đập\s*hộp|trên\s*tay|cấu\s*hình|camera)\b",
    r"(?i)\b(?:spa|thẩm\s*mỹ|làm\s*đẹp|skincare|nâng\s*mũi|gọt\s*cằm|tắm\s*trắng|giảm\s*cân|gym|yoga)\b",
    r"(?i)\b(?:du\s*lịch|tour|resort|homestay|check-in|sống\s*ảo|ẩm\s*thực|món\s*ngon|quán\s*ăn|nhà\s*hàng|cafe|trà\s*sữa)(?!.*(?:mắc\s*kẹt|cô\s*lập|lũ|bão|sạt))\b",
    r"(?i)\b(?:tử\s*vi|cung\s*hoàng\s*đạo|con\s*giáp|phong\s*thủy|xem\s*ngày|bói|vận\s*hạn|tâm\s*linh)(?!.*(?:dự\s*báo\s*thời\s*tiết))\b",

    # =========================================================================
    # 6. POLITICS, ADMIN & ROUTINE (Unless Disaster Related)
    # =========================================================================
    # These effectively screen out routine political news.
    # IMPORTANT: Negative lookaheads ensure we don't block leaders directing disaster response.
    r"(?i)\b(?:đại\s*hội\s*đảng|hội\s*nghị|phiên\s*họp|kỳ\s*họp|quốc\s*hội|hđnd|tiếp\s*xúc\s*cử\s*tri)(?!.*(?:phòng\s*chống|thiên\s*tai|bão|lũ|khẩn\s*cấp|khắc\s*phục|hỗ\s*trợ))\b",
    r"(?i)\b(?:bầu\s*cử|ứng\s*cử|bổ\s*nhiệm|miễn\s*nhiệm|luân\s*chuyển|kỷ\s*luật|khai\s*trừ|trao\s*quyết\s*định)(?!.*(?:ban\s*chỉ\s*huy|pctt))\b",
    r"(?i)\b(?:thăm\s*và\s*làm\s*việc|chúc\s*tết|dâng\s*hương|kỷ\s*niệm|lễ\s*khai\s*mạc|bế\s*mạc|khánh\s*thành|khởi\s*công)(?!.*(?:khắc\s*phục|hậu\s*quả|bão|lũ|sạt|công\s*trình\s*phòng\s*chống))\b",
    r"(?i)\b(?:ngoại\s*giao|đón\s*tiếp|nguyên\s*thủ|tổng\s*thống|thủ\s*tướng\s*(?:nước\s*ngoài)|đại\s*sứ|ký\s*kết|hợp\s*tác)(?!.*(?:viện\s*trợ|cứu\s*trợ|bão|lũ))\b",
    r"(?i)\b(?:ukraine|nga|putin|zelensky|biden|trump|nato|g7|g20|liên\s*hợp\s*quốc|trung\s*đông|gaza|israel)(?!.*(?:bão|lũ|động\s*đất|sóng\s*thần|tại\s*việt\s*nam))\b",

    # =========================================================================
    # 7. CRIME, ACCIDENTS & SOCIAL (Non-Disaster)
    # =========================================================================
    # Block redundant accidents unless weather-related.
    r"(?i)\b(?:tai\s*nạn\s*giao\s*thông|tngt|xe\s*khách|xe\s*tải|tông\s*xe|lật\s*xe)(?!.*(?:bão|lũ|mưa|ngập|sạt|trôi|thiên\s*tai))\b",
    r"(?i)\b(?:án\s*mạng|giết\s*người|hung\s*thủ|nghi\s*phạm|truy\s*nã|ma\s*túy|đánh\s*bạc|mại\s*dâm|buôn\s*lậu|trộm\s*cắp|cướp)\b",
    r"(?i)\b(?:đánh\s*ghen|xô\s*xát|hỗn\s*chiến|mâu\s*thuẫn|tự\s*tử|nhảy\s*cầu|treo\s*cổ)(?!.*(?:lũ|bão|sập|trôi))\b",
    r"(?i)\b(?:cháy\s*nhà|hỏa\s*hoạn|chập\s*điện|nổ\s*bình\s*gas)(?!.*(?:sét\s*đánh|bão|lũ|rừng|cứu\s*hộ|thiên\s*tai))\b",
    # Administrative procedures
    r"(?i)\b(?:căn\s*cước|định\s*danh|vneid|hộ\s*chiếu|giấy\s*phép|thủ\s*tục|đăng\s*ký|bảo\s*hiểm|thuế|phạt\s*nguội|nồng\s*độ\s*cồn)\b",

    # =========================================================================
    # 8. MISC NOISE (Specific phrases found in logs)
    # =========================================================================
    r"(?i)\b(?:bánh\s*đậu\s*xanh|trà\s*thái\s*nguyên|cà\s*phê\s*trung\s*nguyên|bia\s*hơi|nhậu|quán\s*nhậu)\b",
    r"(?i)\b(?:tuyển\s*dụng|tìm\s*việc|việc\s*làm|nhân\s*sự|lương|thưởng|tết)\b",
    r"(?i)\b(?:kết\s*quả\s*xổ\s*số|kqxs|xsmb|xsmn|xsmt)\b",
    r"(?i)\b(?:review|đánh\s*giá|trải\s*nghiệm|mở\s*hộp|hướng\s*dẫn\s*sử\s*dụng)\b",
]"""

# Update the file content
# Find start of ABSOLUTE_VETO
start_marker = "ABSOLUTE_VETO = ["
end_marker = "CONDITIONAL_VETO = ["

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    # Find the closing bracket of ABSOLUTE_VETO before CONDITIONAL_VETO
    # Look backwards from end_marker
    pre_conditional = content[:end_idx]
    last_bracket = pre_conditional.rfind("]")
    
    if last_bracket > start_idx:
        # Construct new content
        new_content = content[:start_idx] + new_veto_list + "\n\n" + content[end_idx:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated ABSOLUTE_VETO in nlp.py")
    else:
        print("Could not find closing bracket for ABSOLUTE_VETO")
else:
    print("Could not find ABSOLUTE_VETO or CONDITIONAL_VETO markers")
