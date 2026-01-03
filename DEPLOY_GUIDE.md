# Hướng dẫn Triển khai Viet Disaster Watch

Tài liệu này hướng dẫn cách chạy dự án trên máy cá nhân (Local) để lập trình và trên Server thật (Production) để ra mắt người dùng.

---

## 1. Chuẩn bị (Prerequisites)
- Đã cài đặt **Docker** và **Docker Compose**.
- (Lưu ý cho Server): Đã trỏ tên miền (Domain) về địa chỉ IP của Server.

---

## 2. Chạy trên máy cá nhân (Local Development)
Dùng để lập trình, sửa code và xem thay đổi ngay lập tức.

**Bước 1: Chuẩn bị file môi trường**
Tạo file `backend/.env` (nếu chưa có) và đảm bảo có các thông số cơ bản.

**Bước 2: Khởi động hệ thống**
Mở terminal tại thư mục gốc của dự án và chạy:
```bash
docker-compose up --build
```

**Bước 3: Truy cập**
- **Frontend:** [http://localhost](http://localhost)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Chạy trên Server thật (Production)
Dùng để ra mắt thực tế với độ bảo mật cao, Nginx và HTTPS.

### Bước 1: Thiết lập File .env
Copy file mẫu sản xuất và chỉnh sửa thông tin mật khẩu:
```bash
cp .env.production.example .env
```
*Sửa file `.env` vừa tạo: Thay đổi `DB_PASSWORD`, `SECRET_KEY` bằng những chuỗi ký tự khó đoán.*

### Bước 2: Cấu hình Tên miền
Mở file `nginx/nginx.conf`, thay thế tất cả `example.com` bằng tên miền thật của bạn (ví dụ: `thientai.vn`).

### Bước 3: Khởi chạy Docker Production
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Bước 4: Kích hoạt SSL (HTTPS) lần đầu
*(Chỉ thực hiện sau khi Server đã chạy và tên miền đã trỏ về đúng IP)*

1. Chạy lệnh cấp chứng chỉ:
```bash
docker exec viet_disaster_certbot certbot certonly --webroot -w /var/www/certbot --force-renewal --email email-cua-ban@gmail.com -d ten-mien.com -d www.ten-mien.com --agree-tos --no-eff-email
```
2. Sau khi báo thành công, bảo Nginx nạp lại cấu hình:
```bash
docker exec viet_disaster_proxy nginx -s reload
```

---

## 4. Các lệnh quản lý thông dụng

| Tác vụ | Lệnh |
| :--- | :--- |
| **Xem log Backend** | `docker logs -f viet_disaster_backend` |
| **Dừng hệ thống** | `docker-compose down` (Local) hoặc `docker-compose -f docker-compose.prod.yml down` (Prod) |
| **Cập nhật code mới** | `git pull` -> Chạy lại lệnh Khởi chạy ở trên |
| **Kiểm tra DB** | `docker exec -it viet_disaster_db psql -U postgres` |

---

## 5. Lưu ý quan trọng cho Production
- **Security:** Luôn giữ file `.env` bí mật, không đẩy lên GitHub.
- **Backup:** Dữ liệu được lưu trong các Volume `db_data`, `backend_data`. Hãy thường xuyên backup các thư mục này.
- **Proxy:** Nếu bị các báo chặn IP, hãy thêm danh sách Proxy vào biến `CRAWLER_PROXIES` trong file `.env`.
