import sqlite3
import re

PROVINCE_COORDINATES = {
    "TP. Hà Nội": [21.0285, 105.8542],
    "Hà Giang": [22.8233, 104.9836],
    "Cao Bằng": [22.6667, 106.2500],
    "Bắc Kạn": [22.1470, 105.8348],
    "Tuyên Quang": [21.8228, 105.2173],
    "Lào Cai": [22.4833, 103.9667],
    "Điện Biên": [21.3852, 103.0235],
    "Lai Châu": [22.3846, 103.4641],
    "Sơn La": [21.3259, 103.9126],
    "Yên Bái": [21.7167, 104.9167],
    "Hòa Bình": [20.8133, 105.3383],
    "Thái Nguyên": [21.5928, 105.8442],
    "Lạng Sơn": [21.8548, 106.7621],
    "Quảng Ninh": [21.0063, 107.5944],
    "Bắc Giang": [21.2731, 106.1947],
    "Phú Thọ": [21.3236, 105.2111],
    "Vĩnh Phúc": [21.3083, 105.6044],
    "Bắc Ninh": [21.1833, 106.0667],
    "Hải Dương": [20.9409, 106.3330],
    "TP. Hải Phòng": [20.8449, 106.6881],
    "Hưng Yên": [20.6500, 106.0500],
    "Thái Bình": [20.4464, 106.3364],
    "Hà Nam": [20.5422, 105.9208],
    "Nam Định": [20.4283, 106.1683],
    "Ninh Bình": [20.2539, 105.9750],
    "Thanh Hóa": [19.8000, 105.7667],
    "Nghệ An": [19.1667, 104.9167],
    "Hà Tĩnh": [18.3444, 105.9056],
    "Quảng Bình": [17.4833, 106.6000],
    "Quảng Trị": [16.8256, 107.1017],
    "Thừa Thiên Huế": [16.4637, 107.5908],
    "TP. Đà Nẵng": [16.0544, 108.2022],
    "Quảng Nam": [15.5667, 107.9833],
    "Quảng Ngãi": [15.1206, 108.8042],
    "Bình Định": [13.9358, 109.1350],
    "Phú Yên": [13.0883, 109.0928],
    "Khánh Hòa": [12.2500, 109.1833],
    "Ninh Thuận": [11.5667, 108.9833],
    "Bình Thuận": [11.0833, 108.0000],
    "Kon Tum": [14.3500, 108.0000],
    "Gia Lai": [13.9833, 108.0000],
    "Đắk Lắk": [12.6667, 108.0500],
    "Đắk Nông": [12.0000, 107.6667],
    "Lâm Đồng": [11.9464, 108.4419],
    "Bình Phước": [11.7500, 106.9167],
    "Tây Ninh": [11.3000, 106.1667],
    "Bình Dương": [11.1667, 106.6000],
    "Đồng Nai": [10.9500, 106.8167],
    "Bà Rịa - Vũng Tàu": [10.4914, 107.1706],
    "TP. Hồ Chí Minh": [10.8231, 106.6297],
    "Long An": [10.5333, 106.4000],
    "Tiền Giang": [10.3500, 106.3500],
    "Bến Tre": [10.2333, 106.3833],
    "Trà Vinh": [9.9333, 106.3333],
    "Vĩnh Long": [10.2500, 105.9667],
    "Đồng Tháp": [11.6083, 105.6167],
    "An Giang": [10.3833, 105.4333],
    "Kiên Giang": [10.0167, 105.0833],
    "TP. Cần Thơ": [10.0333, 105.7833],
    "Hậu Giang": [9.7833, 105.4667],
    "Sóc Trăng": [9.6000, 105.9667],
    "Bạc Liêu": [9.2833, 105.7167],
    "Cà Mau": [9.1833, 105.1500],
    "Miền Bắc": [21.5, 105.5],
    "Bắc Bộ": [21.5, 105.5],
    "Miền Trung": [16.0, 107.5],
    "Trung Bộ": [16.0, 107.5],
    "Miền Nam": [10.5, 106.5],
    "Nam Bộ": [10.5, 106.5],
    "Tây Nguyên": [14.0, 108.0],
    "Bắc Trung Bộ": [18.5, 105.5],
    "Nam Trung Bộ": [12.5, 109.0],
    "Đồng bằng sông Cửu Long": [10.0, 105.5],
    "Biển Đông": [15.0, 114.0],
    "Vịnh Bắc Bộ": [19.5, 107.5]
}

def normalize_name(name):
    if not name: return ""
    name = name.replace("Tình ", "Tỉnh ")
    name = re.sub(r"^(Tỉnh|Thành phố)\s+", "", name, flags=re.IGNORECASE)
    if name.lower().startswith("hồ chí minh"): return "TP. Hồ Chí Minh"
    if name.lower().startswith("hà nội"): return "TP. Hà Nội"
    if name.lower().startswith("đà nẵng"): return "TP. Đà Nẵng"
    if name.lower().startswith("cần thơ"): return "TP. Cần Thơ"
    if name.lower().startswith("hải phòng"): return "TP. Hải Phòng"
    return name

def run_fix():
    conn = sqlite3.connect('backend/data/app.db')
    cur = conn.cursor()
    
    cur.execute("SELECT id, province FROM events WHERE lat IS NULL OR lon IS NULL")
    rows = cur.fetchall()
    print(f"Found {len(rows)} events to fix.")
    
    updated = 0
    for eid, province in rows:
        norm = normalize_name(province)
        coords = PROVINCE_COORDINATES.get(norm)
        if not coords:
            for k, v in PROVINCE_COORDINATES.items():
                if norm and (norm in k or k in norm):
                    coords = v
                    break
        
        if coords:
            cur.execute("UPDATE events SET lat = ?, lon = ? WHERE id = ?", (coords[0], coords[1], eid))
            updated += 1
            
    conn.commit()
    print(f"Successfully updated {updated} events.")
    conn.close()

if __name__ == "__main__":
    run_fix()
