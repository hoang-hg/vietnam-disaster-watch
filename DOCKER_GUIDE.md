# Hướng dẫn Đóng gói và Chạy Viet Disaster Watch bằng Docker

Tài liệu này hướng dẫn cách build (xây dựng) và run (chạy) ứng dụng bằng Docker.

## 1. Yêu cầu Tiên quyết
- Đã cài đặt [Docker Desktop](https://www.docker.com/products/docker-desktop/) trên Windows.
- Docker Desktop đang ở trạng thái **Running** (biểu tượng cá voi xanh ở thanh taskbar).

## 2. Cấu trúc Docker
Chúng ta có 2 services chính được định nghĩa trong `docker-compose.yml`:
- **backend**: Chạy Python FastAPI, tự động crawl tin tức 10 phút/lần.
- **frontend**: Chạy ReactJS trên Nginx (web server nhẹ).

Dữ liệu quan trọng được lưu tại thư mục `./backend_data` trên máy thật (được map vào container), giúp dữ liệu không bị mất khi tắt Docker.

## 3. Các Lệnh Thường Dùng

### A. Chạy lần đầu hoặc khi có sửa đổi Code (Build & Run)
Lệnh này sẽ đóng gói lại code mới nhất và khởi động hệ thống.
```powershell
docker-compose up --build -d
```
* `-d`: Chạy ngầm (detached mode), không chiếm dụng cửa sổ dòng lệnh.

### B. Xem Logs (Nhật ký hoạt động)
Để xem backend đang làm gì (có crawl tin không, có lỗi gì không):
```powershell
docker-compose logs -f backend
```
Để thoát xem log: Nhấn `Ctrl + C`.

### C. Dừng hệ thống
```powershell
docker-compose down
```

## 4. Kiểm thử
Sau khi chạy bước A thành công, mở trình duyệt:
- **Trang chủ:** [http://localhost](http://localhost)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 5. Xuất Docker Image (Để mang sang máy khác)
Nếu bạn muốn đóng gói thành file để gửi cho người khác (không cần build lại):
1. **Lưu Image ra file:**
   ```powershell
   docker save -o viet-disaster-backend.tar viet-disaster-watch-backend
   docker save -o viet-disaster-frontend.tar viet-disaster-watch-frontend
   ```
2. **Tại máy người nhận (Load lại):**
   ```powershell
   docker load -i viet-disaster-backend.tar
   docker load -i viet-disaster-frontend.tar
   docker-compose up -d
   ```
