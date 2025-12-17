# Viet Disaster Watch (12 báo chính thống) — Full-stack starter

Hệ thống tổng hợp tin **thiên tai** từ 12 nguồn báo điện tử Việt Nam, phân loại (bão/lũ/động đất/sạt lở/...), trích xuất nhanh (địa điểm/thời gian/thiệt hại), nhóm thành **Sự kiện (Event)**, hiển thị dashboard bản đồ + bảng tin.

> Lưu ý pháp lý/đạo đức:
> - Ưu tiên **RSS/nguồn công khai**; nếu phải scraping, hãy tuân thủ robots.txt/ToS và hạn chế tần suất.
> - Website này **không đăng lại toàn văn** bài báo; chỉ lưu metadata/tóm tắt trích xuất và link về nguồn gốc.

## 1) Chạy nhanh bằng Docker

```bash
cd viet-disaster-watch
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/docs

Backend sẽ tự chạy crawler theo lịch (mặc định 10 phút/lần). Bạn cũng có thể trigger thủ công:

```bash
docker compose exec backend python -m app.crawler --once
```

## 2) Chạy thủ công (không Docker)

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 3) Cấu hình nguồn dữ liệu (12 báo)
Danh sách nguồn nằm ở `backend/app/sources.py`.

Thiết kế:
- Nếu có RSS chính thức, dùng `method="rss"`.
- Nếu không rõ RSS, dùng `method="gnews"` để lấy RSS truy vấn Google News theo domain (site:... + từ khóa thiên tai).

Bạn có thể chỉnh từ khóa, hoặc thay RSS bằng đường dẫn chính thức nếu có.

## 4) Dữ liệu & mô hình
- Lưu trong SQLite: `backend/data/app.db`.
- NLP hiện tại dùng **rule-based** (regex + từ khóa) để:
  - phân loại thiên tai
  - trích xuất địa điểm (tỉnh/thành)
  - trích xuất thiệt hại (người chết/mất tích/bị thương; thiệt hại kinh tế)
- Có sẵn hook để nâng cấp sang PhoBERT/VnCoreNLP trong `app/nlp.py`.

## 5) API chính
- `GET /api/health`
- `GET /api/articles/latest?limit=50&type=&province=`
- `GET /api/events?limit=50&type=&province=&q=`
- `GET /api/events/{event_id}`
- `GET /api/stats/summary`
