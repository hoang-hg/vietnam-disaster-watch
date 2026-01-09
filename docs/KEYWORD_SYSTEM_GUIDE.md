# Hướng Dẫn Quản Lý Từ Khóa - Viet Disaster Watch NLP System

Tài liệu này tổng hợp các danh sách từ khóa quan trọng nhất trong hệ thống NLP (`backend/app/nlp.py` và `backend/app/sources.py`). 
Sử dụng tài liệu này để tra cứu nhanh khi cần điều chỉnh độ nhạy, khả năng lọc rác, hoặc ưu tiên tin tức của hệ thống.

---

## 1. Nhóm Phân Loại & Nhận Diện (Core Identification)
Dùng để xác định bài viết có thuộc về chủ đề thiên tai hay không và thuộc loại nào.

| Tên Biến | File | Vị Trí (Line*) | Chức Năng | Khi Nào Cần Sửa? |
| :--- | :--- | :--- | :--- | :--- |
| **`DISASTER_GROUPS`** | `sources.py` | ~10 | Danh sách từ khóa sơ khởi dùng cho **Crawler**. Định dạng chuỗi đơn giản. | Khi muốn crawler tìm kiếm thêm các chủ đề mới (VD: thêm từ khóa "sạt lở bờ sông" để crawler quét sâu hơn). |
| **`DISASTER_RULES`** | `nlp.py` | ~660 | Danh sách **Regex** chi tiết dùng để **phân loại** tin vào nhóm cụ thể (Bão, Lũ, Sạt lở...). | Khi hệ thống phân loại sai loại hình thiên tai, hoặc cần bắt các cụm từ phức tạp/viết tắt. |
| **`DISASTER_CONTEXT`** | `sources.py` | ~185 | Từ khóa ngữ cảnh (khắc phục, ứng phó, chỉ đạo, khẩn trương). | Khi muốn tăng điểm cho các tin bài mang tính chất chỉ đạo/hậu quả mà có thể khan hiếm từ khóa thiên tai trực tiếp. |

---

## 2. Nhóm Lọc Rác & Trừ Điểm (Filter & Veto)
Dùng để loại bỏ tin rác, tin không liên quan, tin giả, hoặc tin về các vấn đề xã hội khác.

| Tên Biến | File | Vị Trí (Line*) | Chức Năng | Khi Nào Cần Sửa? |
| :--- | :--- | :--- | :--- | :--- |
| **`ABSOLUTE_VETO`** | `nlp.py` | ~1500 | Danh sách từ khóa **CẤM TUYỆT ĐỐI**. Tin chứa bất kỳ từ nào trong này sẽ bị **Loại Ngay** (Score = 0). (VD: xổ số, bóng đá, showbiz, game). | Khi phát hiện tin rác "lọt lưới" (VD: tin quảng cáo, tin rao vặt, tin giải trí). |
| **`CONDITIONAL_VETO`** | `nlp.py` | ~1600 | Từ khóa cấm có điều kiện (Tai nạn giao thông, Cháy nhà). Chỉ bị loại nếu **KHÔNG** có từ khóa thiên tai đi kèm. | Khi các tin về tai nạn giao thông, cháy nổ dân sự bị nhận nhầm là thiên tai. |
| **`SOFT_NEGATIVE`** | `nlp.py` | ~1700 | Từ khóa "nghi vấn" (Hội nghị, Văn nghệ, Khen thưởng). Bị **trừ điểm nhẹ** (-4.0). | Khi các tin về hội họp hành chính, văn nghệ chào mừng bị chấm điểm quá cao. |
| **`INTERNATIONAL_LOCATIONS`**| `sources.py` | ~260 | Tên các quốc gia trên thế giới. Dùng để **trừ điểm mạnh** (-10.0) nếu tin không liên quan đến VN. | Khi thấy tin tức về thiên tai ở nước ngoài (không ảnh hưởng VN) xuất hiện trên dashboard. |

---

## 3. Nhóm Ưu Tiên & Trọng Số (Boost & Scoring)
Dùng để đẩy điểm số lên cao cho các tin quan trọng, khẩn cấp, hoặc có tác động lớn.

| Tên Biến | File | Vị Trí (Line*) | Chức Năng | Khi Nào Cần Sửa? |
| :--- | :--- | :--- | :--- | :--- |
| **`VIP_TERMS`** | `sources.py` | ~280 | Từ khóa **KHẨN CẤP** (Tin bão khẩn cấp, Lệnh sơ tán, Công điện thủ tướng). Tin chứa từ này được **Duyệt Ngay (+30 điểm)**. | Khi muốn các tin chỉ đạo cực kỳ quan trọng luôn luôn được duyệt ngay lập tức, bất chấp nội dung ngắn hay thiếu số liệu. |
| **`IMPACT_KEYWORDS`** | `nlp.py` | ~2100 | Regex bắt dữ liệu thiệt hại/tác động (Chết, Bị thương, Sập nhà, Mất tích). Cộng +5.0 điểm. | Khi hệ thống không trích xuất được số liệu thương vong/thiệt hại trong bài viết. |
| **`HIGH_PRIORITY_KEYWORDS`** | `sources.py` | ~230 | Từ khóa ưu tiên cao (Xả lũ, Vỡ đê, Lũ quét). Được cộng điểm thưởng (+1.0). | Khi muốn nhấn mạnh mức độ nghiêm trọng của một sự kiện/hành động cụ thể. |
| **`SENSITIVE_LOCATIONS`** | `sources.py` | ~236 | Địa điểm nhạy cảm (Đập thủy điện, Đèo, Sân bay, Đê biển). Cộng điểm ưu tiên vị trí. | Khi muốn theo dõi đặc biệt tình hình tại các công trình trọng điểm quốc gia. |

---

## 4. Nhóm Địa Danh (Geolocation)

| Tên Biến | File | Vị Trí (Line*) | Chức Năng | Khi Nào Cần Sửa? |
| :--- | :--- | :--- | :--- | :--- |
| **`PROVINCE_MAPPING`** | `nlp.py` | ~560 | Bản đồ chuẩn hóa tên Tỉnh/Thành/Quận/Huyện và các biến thể viết tắt. | Khi có thay đổi về đơn vị hành chính, hoặc hệ thống không nhận ra tên địa phương (VD: tên huyện mới tách). |

---

## Tóm Tắt Quy Trình Chỉnh Sửa Nhanh

1.  **Muốn tìm thêm tin (Crawler):**
    *   Mở `backend/app/sources.py`
    *   Sửa `DISASTER_GROUPS`

2.  **Muốn lọc bớt rác (Filter):**
    *   Mở `backend/app/nlp.py`
    *   Sửa `ABSOLUTE_VETO` (thêm từ khóa rác mới phát hiện).

3.  **Muốn ưu tiên tin khẩn (Priority):**
    *   Mở `backend/app/sources.py`
    *   Sửa `VIP_TERMS`.

4.  **Muốn hệ thống hiểu loại thiên tai mới:**
    *   Mở `backend/app/nlp.py`
    *   Sửa `DISASTER_RULES`.

*Lưu ý: Sau khi sửa file Python, cần restart lại Backend Server để áp dụng thay đổi.*
