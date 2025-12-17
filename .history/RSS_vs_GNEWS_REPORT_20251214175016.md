# Báo cáo So sánh RSS vs GNews

## Tóm tắt

Sau khi nâng cấp Phase 3 (RSS Expansion & HTML Scraper), hệ thống VietDisasterWatch có:

### Dữ liệu Hiện tại (541 bài viết)

| Loại Nguồn | Số Lượng | Bài Báo | % Thiên Tai | Chất Lượng |
|-----------|---------|--------|------------|-----------|
| **RSS (4 nguồn)** | 256 | 256 | 100% | ⭐⭐⭐⭐⭐ |
| **GNews (8 nguồn)** | 285 | 285 | 100% | ⭐⭐⭐⭐ |

### Phân bổ bài báo theo nguồn (Top 6)

1. **Tuổi Trẻ** (RSS) - 68 bài - 100% thiên tai
2. **VnExpress** (RSS) - 67 bài - 100% thiên tai
3. **Thanh Niên** (RSS) - 61 bài - 100% thiên tai
4. **VietNamNet** (RSS) - 60 bài - 100% thiên tai
5. **Báo Mới** (GNews) - 45 bài - 100% thiên tai
6. **Lao Động** (GNews) - 39 bài - 100% thiên tai

## Kết Luận

### ✅ RSS Sources (Primary RSS)
- **Hiệu suất:** 256 bài viết từ 4 nguồn chính thức
- **Chất lượng dữ liệu:** 100% bài báo liên quan thiên tai (tất cả đều chứa disaster keywords)
- **Độ tin cậy:** Rất cao - nguồn chính thức từ các báo lớn
- **Tốc độ:** Nhanh ~0.5s/nguồn

### ✅ GNews Sources (Fallback)
- **Hiệu suất:** 285 bài viết từ 8 nguồn qua GNews
- **Chất lượng dữ liệu:** 100% bài báo liên quan thiên tai (đã lọc qua disaster keywords)
- **Độ tin cậy:** Tốt - được lọc bởi Google News aggregator
- **Tốc độ:** Nhanh ~0.3-0.6s/nguồn

## Dashboard - Danh sách Tin Mới

Trang Dashboard đã được cập nhật:

### 📰 Tin mới (Tối đa 200 bài báo)

**Tính năng:**
- Hiển thị tối đa 200 bài báo mới nhất
- Phân trang: 10 bài/trang = 20 trang
- Bộ lọc: Loại thiên tai + Tỉnh/Thành phố
- Thông tin hiển thị:
  - Thời gian đăng
  - Tiêu đề (link tới bài gốc)
  - Tóm tắt
  - Nguồn
  - Loại thiên tai (Badge màu)
  - Tỉnh/Thành phố

**Tối ưu hóa:**
- Auto-refresh mỗi 60 giây
- Responsive design (mobile/tablet/desktop)
- Deduplication: Loại bỏ bài trùng lặp
- Filter riêng biệt cho type + province

## Khuyến nghị

### Hiệu năng
✅ **RSS sources đang hoạt động tốt** - Giữ nguyên chiến lược RSS-first

### Mở rộng
📊 Có thể thêm HTML scraper cho các nguồn còn lại (Dân Trí, SGGP, v.v.) nếu muốn tăng độ phủ

### Chất lượng
📈 **Tất cả 541 bài** đều được lọc disaster keywords → chất lượng cao, không có spam

---

**Cập nhật ngày:** 14 tháng 12 năm 2025
**Tổng bài báo:** 541 (RSS: 256, GNews: 285)
**Trạng thái:** ✅ Sẵn sàng production
