from app.database import SessionLocal, engine
from app import models
from sqlalchemy.orm import Session

# Ensure table exists
models.Base.metadata.create_all(bind=engine)

PROVINCE_HOTLINES = [
    { "province": "TP. Hà Nội", "phone": "0243.3824.507", "agency": "Ban CM PCTT & TKCN" },
    { "province": "TP. Hồ Chí Minh", "phone": "0283.8293.134", "agency": "Ban CM PCTT & TKCN" },
    { "province": "TP. Đà Nẵng", "phone": "0236.3822.131", "agency": "Ban CM PCTT & TKCN" },
    { "province": "TP. Cần Thơ", "phone": "0292.3820.536", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Quảng Ninh", "phone": "0203.3835.549", "agency": "Ban CM PCTT & TKCN" },
    { "province": "TP. Hải Phòng", "phone": "0225.3842.124", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Thanh Hóa", "phone": "0237.3852.126", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Nghệ An", "phone": "0238.3844.755", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Hà Tĩnh", "phone": "0239.3855.514", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Quảng Trị", "phone": "0233.3852.144", "agency": "Ban CM PCTT & TKCN" },
    { "province": "TP. Huế", "phone": "0234.3823.116", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Quảng Ngãi", "phone": "0255.3822.124", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Gia Lai", "phone": "0269.3824.134", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Khánh Hòa", "phone": "0258.3822.131", "agency": "Ban CM PCTT & TKCN" },
    { "province": "Lào Cai", "phone": "0214.3820.124", "agency": "Ban CM PCTT" },
    { "province": "Sơn La", "phone": "0212.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Thái Nguyên", "phone": "0208.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Lạng Sơn", "phone": "0205.3870.124", "agency": "Ban CM PCTT" },
    { "province": "Tuyên Quang", "phone": "0207.3822.124", "agency": "Ban CM PCTT" },
    { "province": "Lai Châu", "phone": "0213.3876.124", "agency": "Ban CM PCTT" },
    { "province": "Điện Biên", "phone": "0215.3824.124", "agency": "Ban CM PCTT" },
    { "province": "Lâm Đồng", "phone": "0263.3822.134", "agency": "Ban CM PCTT" },
    { "province": "Đắk Lắk", "phone": "0262.3852.134", "agency": "Ban CM PCTT" },
    { "province": "Cà Mau", "phone": "0290.3831.134", "agency": "Ban CM PCTT" },
    { "province": "Cao Bằng", "phone": "0206.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Phú Thọ", "phone": "0210.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Bắc Ninh", "phone": "0222.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Hưng Yên", "phone": "0221.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Ninh Bình", "phone": "0229.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Tây Ninh", "phone": "0276.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Đồng Tháp", "phone": "0277.3852.124", "agency": "Ban CM PCTT" },
    { "province": "An Giang", "phone": "0296.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Vĩnh Long", "phone": "0270.3852.124", "agency": "Ban CM PCTT" },
    { "province": "Đồng Nai", "phone": "0251.3852.124", "agency": "Ban CM PCTT" }
]

def init_data():
    db = SessionLocal()
    # Check if data exists
    count = db.query(models.RescueHotline).count()
    if count > 0:
        print("Rescue data already exists. Skipping.")
        return

    print("Initializing Rescue data...")
    for item in PROVINCE_HOTLINES:
        hotline = models.RescueHotline(
            province=item["province"],
            phone=item["phone"],
            agency=item["agency"],
            address=f"Trụ sở {item['agency']} - {item['province']}" # Default address
        )
        db.add(hotline)
    
    db.commit()
    print("Rescue data initialized successfully.")

if __name__ == "__main__":
    init_data()
