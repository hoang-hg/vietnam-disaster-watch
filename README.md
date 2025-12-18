# 🇻🇳 VietNam Disaster Watch - Hệ thống Giám sát Thiên tai Việt Nam

Hệ thống theo dõi, tổng hợp và phân tích tin tức thiên tai tự động từ 38 nguồn chính thống tại Việt Nam. Ứng dụng sử dụng kỹ thuật NLP để phân loại sự kiện theo quy định của Chính phủ (Quyết định 18/2021/QĐ-TTg) và đánh giá mức độ rủi ro theo thời gian thực.

## 🚀 Tính năng nổi bật

-   **Đa nguồn tin cậy**: Tự động thu thập từ **38 nguồn** bao gồm các cơ quan chính phủ (NCHMF, MARD, Sở ban ngành) và các báo điện tử uy tín (VnExpress, Tuổi Trẻ, Thanh Niên...).
-   **Phân loại chuẩn hóa**: Nhận diện và phân loại tự động **8 nhóm thiên tai** theo quy định pháp luật:
    1.  Bão / Áp thấp nhiệt đới
    2.  Mưa lớn / Lũ lụt / Sạt lở
    3.  Nắng nóng / Hạn hán / Xâm nhập mặn
    4.  Gió mạnh / Sương mù
    5.  Nước dâng
    6.  Cháy rừng
    7.  Động đất / Sóng thần
    8.  Thiên tai cực đoan khác (Lốc, sét, mưa đá...)
-   **Đánh giá rủi ro**: Chấm điểm rủi ro (Risk Score) dựa trên từ khóa tác động (thương vong, thiệt hại vật chất) và quy mô sự kiện.
-   **Giao diện trực quan**:
    -   **Dashboard**: Thống kê tổng quan, biểu đồ xu hướng.
    -   **Bản đồ rủi ro**: Hiển thị vị trí sự kiện trên bản đồ tương tác (Leaflet).
    -   **Tra cứu nâng cao**: Lọc theo loại hình, địa phương, thời gian và mức độ nghiêm trọng.

## 🛠 Công nghệ sử dụng

### Backend (Python)
-   **Framework**: FastAPI (High performance).
-   **NLP Engine**: Custom Rule-based System + Regex (tối ưu cho tiếng Việt chuyên ngành thiên tai).
-   **Database**: PostgreSQL (Production) hoặc SQLite (Dev) - Tích hợp `psycopg2` & SQLAlchemy ORM.
-   **Crawler**: `feedparser` cho RSS và `BeautifulSoup` & `Google News` cho fallback.

### Frontend (React)
-   **Core**: React 18 + Vite.
-   **Styling**: TailwindCSS + Lucide Icons.
-   **Charts**: Recharts.
-   **Map**: React-Leaflet.

## 📦 Cài đặt và Chạy ứng dụng

### 1. Yêu cầu hệ thống
-   Python 3.10+
-   Node.js 18+

### 2. Khởi chạy Backend
```bash
cd backend

# Tạo môi trường ảo (khuyến nghị)
python -m venv .venv

# Kích hoạt môi trường (Windows)
.\.venv\Scripts\activate
# Hoặc MacOS/Linux: source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Chạy server
npm run dev 
# Hoặc: python -m uvicorn app.main:app --reload --port 8000
```
Backend sẽ chạy tại: `http://localhost:8000`

### 3. Cấu hình Database (PostgreSQL)
Nếu bạn muốn sử dụng PostgreSQL thay vì SQLite mặc định:

1.  **Cài đặt PostgreSQL**: Đảm bảo máy của bạn đã cài đặt Postgres hoặc sử dụng Docker (xem phần dưới).
2.  **Tạo File `.env`**: Sao chép file ví dụ:
    ```bash
    cp .env.example .env
    ```
3.  **Cấu hình URL**: Mở `.env` và cập nhật `APP_DB_URL`:
    ```env
    APP_DB_URL=postgresql://user:password@localhost:5432/db_name
    ```
4.  **Chạy Migrations**: Để khởi tạo các bảng trong database:
    ```bash
    cd backend
    alembic upgrade head
    ```

### 4. Khởi chạy bằng Docker (Nhanh nhất)
Dự án đã có sẵn cấu hình Docker Compose để khởi chạy toàn bộ Backend, Frontend và Database PostgreSQL chỉ với 1 lệnh duy nhất:

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Database: `localhost:5432`

### 5. Khởi chạy Frontend (Manual)
```bash
cd frontend

# Cài đặt thư viện
npm install

# Chạy dev server
npm run dev
```
Frontend sẽ chạy tại: `http://localhost:5173`

## 📂 Cấu trúc dự án

```
viet-disaster-watch/
├── backend/
│   ├── app/
│   │   ├── nlp.py           # Logic xử lý ngôn ngữ & phân loại
│   │   ├── crawler.py       # Bộ thu thập dữ liệu
│   │   ├── api.py           # API Endpoints
│   │   └── sources.py       # Cấu hình 38 nguồn tin
│   ├── data/                # Chứa DB SQLite
│   └── logs/                # Logs hệ thống
├── frontend/
│   ├── src/
│   │   ├── components/      # UI Components (Map, Cards, Badges...)
│   │   ├── pages/           # Dashboard, Events, EventDetail
│   │   └── api.js           # Kết nối Backend
└── README.md
```

## ⚖️ Lưu ý pháp lý
Ứng dụng này là một công cụ tổng hợp tin tức (News Aggregator). Toàn bộ nội dung bài viết gốc thuộc bản quyền của các tòa soạn và cơ quan phát hành. Hệ thống chỉ trích xuất siêu dữ liệu (metadata), tóm tắt và dẫn link trực tiếp về nguồn gốc để tôn trọng quyền tác giả.
