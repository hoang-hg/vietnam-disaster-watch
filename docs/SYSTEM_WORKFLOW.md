# Quy trình Hệ thống Viet Disaster Watch

Tài liệu mô tả chi tiết luồng xử lý dữ liệu (Data Pipeline) từ nguồn tin đến người dùng cuối.

## Sơ đồ Tổng quan
[Source Web/RSS] -> [Crawler Bot] -> [NLP Filter] -> [Extractor] -> [Database] -> [Dashboard UI]

---

## 1. Thu thập dữ liệu (Crawling Strategy)
Hệ thống sử dụng module `backend/app/feed.py` để định kỳ tải tin tức.

*   **Nguồn tin (Data Sources)**: Được định nghĩa trong `backend/sources.json`.
*   **Phương thức RSS**: Với các báo lớn (VnExpress, Tuổi Trẻ...), hệ thống tải trực tiếp XML Feed. Đây là cách nhanh và ổn định nhất.
*   **Phương thức GNews Fallback**: Với các báo địa phương hoặc không có RSS chuẩn, hệ thống tạo truy vấn tìm kiếm Google News. 
    *   *Ví dụ Query*: `site:baolaocai.vn (bão OR lũ OR sạt lở OR ...)`
    *   Cách này đảm bảo lấy được tin thiên tai ngay cả khi báo đó không có RSS chuyên mục Xã hội.

## 2. Bộ lọc Thông minh (Intelligent Filtering)
Đây là "trái tim" của hệ thống, nằm tại `backend/app/nlp.py`.

### Bước 2.1: Sơ loại (Pre-screening)
*   Check trùng URL/Title trong Database.
*   Loại bỏ tin quá cũ (> 48h).

### Bước 2.2: Phân tích Nội dung (NLP Decision)
Hàm `contains_disaster_keywords(text)` quyết định xem một tin có phải là thiên tai hay không.
1.  **Hard Veto (Vòng kim cô)**: Loại bỏ ngay lập tức nếu chứa từ khóa nhạy cảm hoặc không liên quan:
    *   Bóng đá: "đội tuyển", "chung kết", "u23", "vòng loại"...
    *   Kinh tế/Xã hội: "bão giá", "bão sale", "lãi suất", "chứng khoán", "showbiz"...
    *   Ẩn dụ: "cơn sóng dư luận", "địa chấn chính trị"...
2.  **Scoring (Chấm điểm)**: Tính tổng điểm dựa trên mật độ từ khóa thiên tai ("bão số", "ngập lụt", "sạt lở"...).
3.  **Soft Veto (Vùng xám)**: Nếu chứa từ khóa như "khánh thành", "hội nghị", điểm số yêu cầu để pass sẽ cao hơn bình thường (để tránh tin khánh thành công trình phòng chống thiên tai bị nhận nhầm là thiên tai).

**Kết quả Benchmark (300 cases):**
*   Tỷ lệ báo động giả (False Positive): **0.00%**.
*   Tỷ lệ bỏ sót tin (Sensitivity): **100%**.

## 3. Trích xuất Thông tin (Extraction)
Sau khi tin được chấp nhận, hệ thống trích xuất dữ liệu chi tiết:

*   **Phân loại (Classification)**: Xác định 1 trong 8 nhóm thiên tai chính (Storm, Flood, Fire, Quake...) dựa trên độ ưu tiên.
    *   *Ví dụ*: Tin vừa có "Bão" vừa có "Mưa" -> Xếp loại là "Storm".
*   **Định vị (Geocoding)**: Quét văn bản tìm tên 63 Tỉnh/Thành phố.
    *   Sử dụng giải thuật so khớp chính xác với danh sách Alias đầy đủ (VD: "TPHCM" = "Hồ Chí Minh").
    *   Recall đạt **100%**.
*   **Đánh giá thiệt hại (Impact Assessment)**: Trích xuất số người chết/bị thương và mức độ hư hại tài sản ("sập nhà", "tốc mái").

## 4. Lưu trữ và Phục vụ (Serving)
*   Dữ liệu sạch được lưu vào bảng `Event` trong Database.
*   API `GET /api/events` cung cấp dữ liệu cho Frontend.
*   Frontend hiển thị:
    *   **Bản đồ**: Marker tại các tỉnh bị ảnh hưởng.
    *   **Danh sách**: Card tin tức với nhãn loại thiên tai và mức độ nghiêm trọng.

---
*Tài liệu được cập nhật ngày 19/12/2025.*
