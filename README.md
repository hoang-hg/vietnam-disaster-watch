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

## � Cài đặt và Chạy bằng Docker (Khuyên dùng)

Đây là cách nhanh nhất và ổn định nhất để chạy dự án trên bất kỳ máy tính nào mà không cần cài đặt Python hay Node.js thủ công.

### 1. Yêu cầu
-   **Docker Desktop** (đã cài đặt và đang chạy).
-   **Git** (để clone mã nguồn).

### 2. Các bước thực hiện

**Bước 1: Clone mã nguồn**
Mở terminal (PowerShell, CMD hoặc Git Bash) và chạy lệnh:
```bash
git clone <đường-dẫn-repo-của-bạn>
cd viet-disaster-watch
```

**Bước 2: Cấu hình biến môi trường**
Copy file mẫu `.env.example` thành `.env`:
```bash
# Trên Windows
copy .env.example .env

# Trên Mac/Linux
cp .env.example .env
```
*Lưu ý: Mặc định file `.env` đã được cấu hình sẵn để chạy tốt với Docker (Database PostgreSQL).*

**Bước 3: Khởi chạy ứng dụng**
Chạy lệnh sau để Docker tự động tải, build và chạy toàn bộ hệ thống (Frontend + Backend + Database):

```bash
docker compose up --build -d
```
*(Lần đầu chạy có thể mất vài phút để tải Docker Images)*

**Bước 4: Truy cập ứng dụng**
Sau khi lệnh chạy xong, mở trình duyệt và truy cập:
-   **Ứng dụng Web (Frontend)**: [http://localhost:5173](http://localhost:5173)
-   **API Tài liệu (Backend Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
-   **Quản lý Database (pgAdmin - nếu cài thêm)**: Host: `localhost`, Port: `5432`, User: `postgres`, Pass: `password`

### 3. Các lệnh thường dùng

-   **Ngừng ứng dụng**: `docker compose stop`
-   **Tắt hẳn và xóa container**: `docker compose down`
-   **Xem log (Backend)**: `docker logs -f viet-disaster-watch-backend-1`
-   **Cập nhật code mới**: Sau khi `git pull`, chạy lại `docker compose up --build -d`

## 🛠 Chạy Thủ công (Dành cho Dev/Debug)

Nếu bạn muốn chạy từng phần riêng lẻ để phát triển:

### Backend
Yêu cầu: Python 3.10+
```bash
cd backend
cd frontend
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
Yêu cầu: Node.js 18+
```bash
cd frontend
npm install
npm run dev
```

## 📂 Cấu trúc dự án

```
viet-disaster-watch/
├── backend/
│   ├── app/
│   │   ├── nlp.py           # Logic xử lý ngôn ngữ & phân loại 8 nhóm thiên tai
│   │   ├── crawler.py       # Bộ thu thập dữ liệu (kèm cơ chế DEDUP & Retry)
│   │   ├── api.py           # API Endpoints
│   │   └── sources.py       # Cấu hình nguồn tin
│   ├── data/                # Dữ liệu SQLite (Dev mode)
│   └── logs/                # Logs hệ thống crawl
├── frontend/
│   ├── src/
│   │   ├── components/      # UI Components (Map, Cards...)
│   │   ├── pages/           # Dashboard, Events...
│   │   └── api.js           # Kết nối Backend
├── docker-compose.yml       # Cấu hình triển khai Docker
└── README.md
```

## ⚖️ Lưu ý pháp lý
Ứng dụng này là một công cụ tổng hợp tin tức (News Aggregator). Toàn bộ nội dung bài viết gốc thuộc bản quyền của các tòa soạn và cơ quan phát hành. Hệ thống chỉ trích xuất siêu dữ liệu (metadata), tóm tắt và dẫn link trực tiếp về nguồn gốc để tôn trọng quyền tác giả.
