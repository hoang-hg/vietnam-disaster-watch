from app.database import SessionLocal
from app import models

NATIONAL_DATA = [
    { "province": "Toàn quốc", "phone": "112", "agency": "Tìm kiếm cứu nạn khẩn cấp" },
    { "province": "Toàn quốc", "phone": "113", "agency": "An ninh trật tự" },
    { "province": "Toàn quốc", "phone": "114", "agency": "PCCC & Cứu nạn" },
    { "province": "Toàn quốc", "phone": "115", "agency": "Cấp cứu y tế" },
]

def update_data():
    db = SessionLocal()
    print("Updating National Rescue data...")
    
    for item in NATIONAL_DATA:
        # Check if exists
        exists = db.query(models.RescueHotline).filter(
            models.RescueHotline.province == item["province"],
            models.RescueHotline.phone == item["phone"]
        ).first()
        
        if not exists:
            hotline = models.RescueHotline(
                province=item["province"],
                phone=item["phone"],
                agency=item["agency"],
                address="Trực ban toàn quốc"
            )
            db.add(hotline)
            print(f"Added {item['phone']}")
    
    db.commit()
    print("National data update complete.")

if __name__ == "__main__":
    update_data()
