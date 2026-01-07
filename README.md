# 🇻🇳 VietNam Disaster Watch - Hệ thống Giám sát Thiên tai Việt Nam

Hệ thống theo dõi, tổng hợp và phân tích tin tức thiên tai tự động từ 38 nguồn chính thống tại Việt Nam.

Ứng dụng sử dụng công nghệ NLP (Xử lý Ngôn ngữ Tự nhiên) để phân loại sự kiện theo cơ sở dữ liệu quốc gia (Quyết định 18/2021/QĐ-TTg) và đánh giá mức độ rủi ro theo thời gian thực (Real-time).

---

## 🎯 Hệ thống hoạt động như thế nào?

Hệ thống hoạt động theo chu trình khép kín 4 bước tự động hóa hoàn toàn:

1.  **Thu thập (Crawl):** Đều đặn quét tin tức mới nhất từ 38 nguồn báo chí (VnExpress, Tuổi Trẻ, Web Chính phủ, Đài Khí tượng...) qua RSS và Google News.
2.  **Phân tích (Analyze):** Dùng AI đọc hiểu nội dung để:
    *   Loại bỏ tin rác (xổ số, tai nạn giao thông đơn lẻ...).
    *   Phân loại vào 8 nhóm thiên tai chính (Bão, Lũ, Sạt lở...).
    *   Trích xuất địa điểm, thời gian và thống kê thiệt hại (Người/Tài sản).
3.  **Lưu trữ & Ghép sự kiện (Event Matching):** Tự động gom các bài báo nói về cùng 1 sự kiện ở cùng 1 địa phương lại với nhau để tạo thành "Dòng sự kiện".
4.  **Hiển thị (Dashboard):** Đưa dữ liệu lên bản đồ trực quan với cảnh báo nóng, thống kê thiệt hại và biểu đồ xu hướng.

---

## 🚀 Hướng dẫn Cài đặt & Chạy (Quick Start)

Bạn có 2 cách để chạy hệ thống này. Hãy chọn cách phù hợp nhất với bạn:

### ✅ Cách 1: Sử dụng Docker (Khuyên dùng - Nhanh nhất)
Cách này không yêu cầu bạn phải cài Python, Node.js hay Database thủ công. Mọi thứ đã được đóng gói sẵn.

1.  **Cài đặt:** Tải và cài [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2.  **Khởi động:** Mở terminal tại thư mục dự án và chạy:
    ```bash
    docker-compose up --build -d
    ```
3.  **Sử dụng:**
    *   Web Dashboard: [http://localhost](http://localhost)
    *   API Backend: [http://localhost:8000/docs](http://localhost:8000/docs)

👉 *Xem chi tiết tại file [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md#3-chạy-trên-server-thật-production)*.

---

### 🛠 Cách 2: Chạy Thủ công (Dành cho Lập trình viên Phát triển)
Cách này giúp bạn tự do sửa code và debug chi tiết từng phần.

**1. Backend (Python):**
```bash
cd backend
python -m venv .venvactivate
.\.venv\Scripts\  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**2. Frontend (Node.js):**
```bash
cd frontend
npm install
npm run dev
```

👉 *Xem hướng dẫn chi tiết từng bước tại file [LOCAL_DEV_GUIDE.md](LOCAL_DEV_GUIDE.md) (đang cập nhật)*.

---

## 🛠 Công nghệ sử dụng
*   **Backend:** Python 3.10, FastAPI, SQLAlchemy, APScheduler (Cronjob).
*   **Database:** PostgreSQL (Production) hoặc SQLite (Dev), Redis (Caching).
*   **Frontend:** ReactJS, Vite, TailwindCSS, Chart.js/Recharts, Leaflet Map.
*   **DevOps:** Docker, Nginx, GitHub Actions.

## 📂 Ý nghĩa các thư mục chính
*   `backend/`: Chứa mã nguồn xử lý logic, cào tin và API.
*   `frontend/`: Chứa mã nguồn giao diện website.
*   `docker-compose.yml`: File cấu hình chạy thử nghiệm (Dev).
*   `docker-compose.prod.yml`: File cấu hình chạy thật (Production) có HTTPS.
*   `nginx/`: Cấu hình máy chủ web chịu tải.

---
© 2024 - Dự án Cộng đồng giám sát Thiên tai Việt Nam.
