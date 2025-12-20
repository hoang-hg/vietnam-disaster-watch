import time
import datetime
import sys
import os
from pathlib import Path

# Thêm thư mục backend vào sys.path để import được app
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

try:
    from app.crawler import process_once
except ImportError as e:
    print(f"Lỗi import: {e}")
    # Fallback nếu chạy từ thư mục khác
    try:
        from backend.app.crawler import process_once
    except ImportError:
        print("Không thể import app.crawler. Hãy chắc chắn bạn đang chạy từ thư mục gốc hoặc thư mục backend.")
        sys.exit(1)

INTERVAL_SECONDS = 60 * 60  # 60 phút

print(f"🚀 BẮT ĐẦU SCHEDULER: Chạy crawl mỗi {INTERVAL_SECONDS/60} phút")
print("==================================================")

while True:
    try:
        start_time = datetime.datetime.now()
        print(f"\n[Scheduler] Bắt đầu phiên crawl lúc: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Gọi hàm crawl (đồng bộ)
        result = process_once()
        
        end_time = datetime.datetime.now()
        elapsed = result.get('elapsed', 0)
        new_count = result.get('new_articles', 0)
        
        print(f"[Scheduler] Hoàn tất phiên crawl.")
        print(f" - Tin mới: {new_count}")
        print(f" - Thời gian chạy: {elapsed:.2f}s")
        print(f" - Thời gian kết thúc: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[Scheduler] Dừng bởi người dùng.")
        break
    except Exception as e:
        print(f"\n[Scheduler] Lỗi trong quá trình crawl: {e}")
        # Không dừng loop, chỉ log lỗi và chờ lần chạy sau
    
    # Tính thời gian chờ
    print(f"[Scheduler] Chờ {INTERVAL_SECONDS/60} phút cho phiên tiếp theo...")
    print("--------------------------------------------------")
    time.sleep(INTERVAL_SECONDS)
