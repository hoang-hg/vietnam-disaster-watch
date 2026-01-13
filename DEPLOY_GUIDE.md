# 🚀 Hướng Dẫn Deploy Viet Disaster Watch

Tài liệu này hướng dẫn cách triển khai hệ thống Viet Disaster Watch lên môi trường Production (VPS/Server).

## 🛠 Yêu Cầu (Prerequisites)

1.  **VPS (Máy chủ ảo)**:
    *   Hệ điều hành: Ubuntu 22.04 LTS (Khuyến nghị)
    *   RAM: Tối thiểu 2GB (Khuyến nghị 4GB)
    *   CPU: 2 vCPU
    *   Ổ cứng: 20GB SSD
2.  **Domain (Tên miền)**: Đã trỏ về IP của VPS.
3.  **Docker & Docker Compose**:
    ```bash
    # Ubuntu
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    # Logout và Login lại để áp dụng group docker
    ```

---

## ⚙️ Cấu Hình Môi Trường

1.  **Clone code về Server**:
    ```bash
    git clone https://github.com/hoang-hg/viet-disaster-watch.git
    cd viet-disaster-watch
    ```

2.  **Tạo File Môi Trường (.env)**:
    Copy file mẫu và chỉnh sửa:
    ```bash
    cp .env.production.example .env
    nano .env
    ```
    *Những biến quan trọng cần sửa:*
    *   `DB_PASSWORD`: Đặt mật khẩu DB khó đoán.
    *   `SECRET_KEY`: Chuỗi ngẫu nhiên dài để mã hóa token.
    *   `DEFAULT_ADMIN_PASSWORD`: Mật khẩu admin mặc định.
    *   `VITE_API_BASE`: Để trống `VITE_API_BASE=` (Frontend sẽ tự gọi `/api` qua proxy cùng domain).

---

## 🔒 Cấu Hình SSL (Vấn đề "Con Gà và Quả Trứng")

Lần đầu tiên chạy, Nginx sẽ lỗi vì chưa có chứng chỉ SSL. Bạn cần làm theo đúng trình tự sau **một lần duy nhất**:

**Bước 1: Tắt SSL trong Nginx tạm thời**
*   Mở file `nginx/nginx.conf`.
*   Tìm block `server { listen 443 ssl; ... }` và comment lại toàn bộ (bao gồm cả dòng `listen 443 ssl`).
*   Đảm bảo chỉ còn block `server { listen 80; ... }` hoạt động.

**Bước 2: Khởi động hệ thống (Chế độ HTTP)**
```bash
docker-compose -f docker-compose.prod.yml up -d
```
*Lúc này web đã chạy được nhưng chỉ ở http://domain-cua-ban.com*

**Bước 3: Xin chứng chỉ SSL từ Let's Encrypt**
Thay `your-domain.com` bằng tên miền thật của bạn:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path /var/www/certbot -d your-domain.com
```
*Nếu thành công, nó sẽ báo "Congratulations!".*

**Bước 4: Bật lại SSL**
*   Mở lại file `nginx/nginx.conf`.
*   Bỏ comment (uncomment) block 443 đã làm ở Bước 1.
*   Sửa `server_name` thành domain thật của bạn (cả ở block 80 và 443).
*   Sửa đường dẫn chứng chỉ trong `ssl_certificate` và `ssl_certificate_key` cho đúng domain (Certbot thường lưu ở `/etc/letsencrypt/live/your-domain.com/...`).

**Bước 5: Restart Nginx**
```bash
docker-compose -f docker-compose.prod.yml restart nginx
```
*Lúc này web đã chạy HTTPS an toàn.*

---

## 🧠 Giải Thích Về Redis (Có cần thiết không?)

Trong hệ thống Viet Disaster Watch, Redis đóng 3 vai trò:

1.  **Caching (Bộ nhớ đệm - QUAN TRỌNG NHẤT):**
    *   *Tác dụng:* Lưu kết quả các tin tức mới nhất, thống kê sự kiện (những API nặng).
    *   *Lợi ích:* Giúp API trả về kết quả trong **10ms** thay vì 500ms (nhanh gấp 50 lần). Giảm tải cho Database.

2.  **Distributed Lock (Khóa phân tán):**
    *   *Tác dụng:* Khi chạy nhiều Crawler cùng lúc (Gunicorn workers), Redis đảm bảo **không có 2 worker nào quét cùng một nguồn tin cùng lúc**.
    *   *Lợi ích:* Tránh việc Database bị spam dữ liệu trùng lặp và tiết kiệm băng thông.

3.  **Rate Limiting (Giới hạn truy cập - Optional):**
    *   *Tác dụng:* Đếm số lần request từ 1 IP để chặn spam.

### ❓ Câu hỏi: Có thể bỏ Redis không?

**CÓ, NHƯNG KHÔNG NÊN.**

Code Backend đã được viết cơ chế **Fallback (Dự phòng)**:
*   Nếu `REDIS_URL` không được cung cấp hoặc Redis chết, hệ thống sẽ tự động chuyển sang dùng **Ram nội bộ (In-Memory)** của từng process Python.

**Nhược điểm nếu bỏ Redis:**
*   ❌ **Cache bị phân mảnh:** Nếu bạn chạy 4 worker (multiprocess), mỗi worker có bộ nhớ riêng. User A truy cập vào worker 1 thấy tin mới, nhưng User B vào worker 2 lại thấy tin cũ. (Trải nghiệm tệ).
*   ❌ **Mất Lock:** Có rủi ro Crawler chạy trùng lặp, gây tốn tài nguyên server.
*   ❌ **Mất Cache khi Restart:** Mỗi lần deploy lại backend, cache trong RAM mất hết, Database sẽ bị "đánh úp" (thunder herd) ngay khi khởi động.

**👉 Khuyến nghị:** Vì Redis rất nhẹ (chỉ tốn ~50-100MB RAM), bạn **NÊN GIỮ LẠI** để hệ thống chạy mượt mà và chuyên nghiệp nhất.


### 🐞 Xử lý lỗi Redis khi chạy thử (Local Development)

Nếu bạn chạy Backend trực tiếp trên máy tính (`python -m uvicorn ...`) và gặp lỗi:
> *Redis connection failed: Error 10061 ... actively refused it.*

**Nguyên nhân:** Máy tính của bạn chưa cài Redis hoặc Redis chưa chạy.
**Cách xử lý nhanh:**
1.  Mở file `backend/.env`.
2.  Tìm dòng `REDIS_URL`.
3.  Thêm dấu `#` để tắt nó: `# REDIS_URL=redis://localhost:6379/0`.
    *   Hệ thống sẽ tự động chuyển sang chế độ **In-Memory Cache** (không lỗi nữa).

---

## 🔄 Cập Nhật Ứng Dụng (Update)

Khi có code mới, chỉ cần:
```bash
git pull
docker-compose -f docker-compose.prod.yml build backend frontend
docker-compose -f docker-compose.prod.yml up -d
```
