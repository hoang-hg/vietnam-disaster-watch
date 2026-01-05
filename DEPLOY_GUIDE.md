# Hướng dẫn Vận hành Hệ thống Viet Disaster Watch

Tài liệu này là cẩm nang chi tiết nhất giúp bạn **Triển khai**, **Vận hành** và **Sửa lỗi** hệ thống.

---

## MỤC LỤC
1. [Chạy bằng Docker (Khuyên dùng)](#1-chạy-bằng-docker-khuyên-dùng)
   - [Môi trường Phát triển (Dev)](#a-môi-trường-phát-triển-dev)
   - [Môi trường Thực tế (Production)](#b-môi-trường-thực-tế-production)
2. [Chạy Thủ công (Local Development)](#2-chạy-thủ-công-local-development)
3. [Các lệnh quản trị thường dùng](#3-các-lệnh-quản-trị-thường-dùng)
4. [Khắc phục sự cố (Troubleshooting)](#4-khắc-phục-sự-cố-troubleshooting)

---

## 1. Chạy bằng Docker (Khuyên dùng)

Đây là cách chuẩn nhất, đảm bảo môi trường trên máy bạn "y hệt" server thật, tránh lỗi "trên máy tôi vẫn chạy được".

### A. Môi trường Phát triển (Dev)
Dùng khi bạn code, test tính năng mới trên máy cá nhân.

1.  **Cấu hình:** Đảm bảo file `.env` (ở thư mục gốc) đã có nội dung cơ bản (có thể copy từ `.env.example`).
2.  **Khởi động:**
    ```bash
    docker-compose up --build
    ```
    *(Thêm `-d` vào cuối nếu muốn chạy ngầm)*
3.  **Truy cập:**
    *   Web: `http://localhost:5173` (hoặc cổng 8080 tùy cấu hình Nginx dev)
    *   API: `http://localhost:8000`

### B. Môi trường Thực tế (Production)
Dùng khi bạn đưa lên Server (VPS) để người dùng truy cập công khai.

1.  **Chuẩn bị file cấu hình:**
    ```bash
    cp .env.production.example backend/.env
    # Sửa file backend/.env này: thay đổi SECRET_KEY và DB_PASSWORD thật bảo mật.
    ```
2.  **Cài đặt SSL (HTTPS) & Chạy:**
    Sử dụng file cấu hình dành riêng cho Prod:
    ```bash
    docker-compose -f docker-compose.prod.yml up -d --build
    ```
3.  **Cấu hình Tên miền (Domain):**
    *   Mở file `nginx/nginx.conf`.
    *   Tìm dòng `server_name` và sửa `example.com` thành tên miền của bạn.
    *   Chạy lại lệnh ở bước 2 để Nginx cập nhật.

---

## 2. Chạy Thủ công (Local Development)

Chỉ dành cho lập trình viên muốn can thiệp sâu vào code mà không thích dùng Docker.

### Yêu cầu:
*   [Python 3.10+](https://www.python.org/)
*   [Node.js 18+](https://nodejs.org/)
*   [PostgreSQL](https://www.postgresql.org/) (Nếu không muốn cài, hãy sửa cấu hình dùng SQLite).
*   [Redis](https://redis.io/) (Tùy chọn, để tăng tốc).

### Bước 1: Chạy Backend (API & Crawler)
```bash
cd backend
python -m venv .venv                  # Tạo môi trường ảo
.\.venv\Scripts\activate              # Kích hoạt (Windows)
pip install -r requirements.txt       # Cài thư viện

# Cấu hình Database & Redis:
# Sửa file backend/.env hoặc set biến môi trường trực tiếp.

python -m uvicorn app.main:app --reload --port 8000
```
*Lần đầu chạy, hệ thống sẽ tự tạo file `backend/data/app.db` (nếu dùng SQLite) và thực hiện cào tin ngay lập tức.*

### Bước 2: Chạy Frontend (Giao diện)
```bash
cd frontend
npm install       # Cài thư viện Node
npm run dev       # Chạy chế độ Dev
```
Truy cập: `http://localhost:5173`

---

## 3. Các lệnh quản trị thường dùng

### Xem nhật ký hoạt động (Logs)
Để biết crawler đang làm gì, có lỗi gì không:
```bash
# Nếu chạy Docker
docker logs -f viet_disaster_backend

# Nếu chạy Local
# ...nhìn trực tiếp vào cửa sổ Terminal đang chạy Backend
```

### Truy cập Database (PostgreSQL trong Docker)
```bash
docker exec -it viet_disaster_db psql -U postgres -d viet_disaster_watch
```
*(Gõ lệnh SQL như `SELECT * FROM events;` để xem dữ liệu)*

### Dọn dẹp hệ thống
```bash
# Xóa sạch container cũ
docker-compose down

# Xóa sạch cả dữ liệu Database (CẨN THẬN!)
docker-compose down -v
```

---

## 4. Khắc phục sự cố (Troubleshooting)

**Q: Tại sao tôi không thấy tin mới nào?**
A:
1.  Kiểm tra log Backend xem quá trình Crawl có bị lỗi không.
2.  Kiểm tra kết nối mạng (nếu server chặn kết nối quốc tế, cần thêm Proxy vào `.env`).
3.  Hệ thống được lập trình cào 60 phút/lần (`CRAWL_INTERVAL_MINUTES=60`). Kiên nhẫn chờ hoặc khởi động lại Backend để ép cào ngay.

**Q: Lỗi "Connection refused" tới Redis?**
A:
*   Nếu dùng Docker: Đã tự động xử lý.
*   Nếu chạy Local: Bạn quên cài hoặc chưa bật `redis-server`. Hãy cài Redis hoặc xóa dòng `REDIS_URL` trong `.env` để dùng bộ nhớ RAM thường.

**Q: Dashboard không hiện dữ liệu dù Backend có tin?**
A: Kiểm tra file `frontend/.env` (hoặc biến `VITE_API_BASE`). Frontend cần biết địa chỉ Backend (thường là `http://localhost:8000`).

---
**Chúc bạn vận hành hệ thống thành công!** 🚀
