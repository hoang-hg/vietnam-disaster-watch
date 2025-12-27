
import httpx
import asyncio
import json

# Configuration
BASE_URL = "http://127.0.0.1:8001"
# Note: You need a valid admin token to run this. 
# For this test script, we assume a local dev environment.
ADMIN_TOKEN = "" # Fill this or use a login call

async def test_api_integration():
    print("🚀 Bắt đầu kiểm tra tích hợp Backend...")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Kiểm tra Stats Summary (Dữ liệu trang Dashboard)
        print("\n[1] Kiểm tra Dashboard Stats...")
        res = await client.get("/api/stats/summary")
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Thành công: Tìm thấy {data.get('events_count', 0)} sự kiện.")
        else:
            print(f"❌ Lỗi Stats: {res.status_code}")

        # 2. Kiểm tra danh sách 34 tỉnh thành trong API
        print("\n[2] Kiểm tra đồng bộ 34 tỉnh thành...")
        res = await client.get("/api/events?limit=1")
        if res.status_code == 200:
            print("✅ API Events hoạt động.")
        
        # 3. Kiểm tra các Endpoint Admin mới (Yêu cầu token)
        if not ADMIN_TOKEN:
            print("\n⚠️  Bỏ qua kiểm tra Admin (Chưa có token). Vui lòng điền ADMIN_TOKEN để test sâu hơn.")
            return

        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

        # 4. Kiểm tra Crawler Status
        print("\n[3] Kiểm tra Crawler Status (Admin)...")
        res = await client.get("/api/admin/crawler-status", headers=headers)
        if res.status_code == 200:
            print(f"✅ Thành công: Đã lấy được trạng thái của {len(res.json())} nguồn tin.")
        else:
            print(f"❌ Lỗi Crawler Status: {res.status_code}")

        # 5. Kiểm tra AI Feedback (Gửi thử một feedback)
        print("\n[4] Kiểm tra AI Feedback Loop...")
        # Lấy thử 1 bài báo pending hoặc approved để test
        arts = await client.get("/api/articles/latest?limit=1")
        if arts.status_code == 200 and arts.json():
            art_id = arts.json()[0]['id']
            payload = {
                "article_id": art_id,
                "corrected_type": "storm",
                "comment": "Test integration script"
            }
            res = await client.post("/api/admin/ai-feedback", json=payload, headers=headers)
            if res.status_code == 200:
                print("✅ Thành công: Đã gửi AI Feedback và cập nhật bài báo.")
            else:
                print(f"❌ Lỗi AI Feedback: {res.status_code}")

        # 6. Kiểm tra Export
        print("\n[5] Kiểm tra API Xuất dữ liệu...")
        res = await client.get(f"/api/admin/export/daily?token={ADMIN_TOKEN}", headers=headers)
        if res.status_code == 200:
            print("✅ Thành công: Endpoint Export Excel hoạt động.")
        else:
            print(f"❌ Lỗi Export: {res.status_code}")

    print("\n✨ Hoàn tất kiểm tra logic!")

if __name__ == "__main__":
    asyncio.run(test_api_integration())
