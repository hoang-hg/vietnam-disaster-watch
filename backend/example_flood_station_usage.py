# Ví dụ sử dụng detect_flood_station()

from backend.app import nlp

# Case 1: Bài báo có tên trạm cụ thể
text1 = """
Mực nước tại trạm Đồng Hới (sông Nhật Lệ, Quảng Bình) 
lên mức báo động 2, vượt 0.5m. Dự báo tiếp tục lên.
"""

result1 = nlp.detect_flood_station(text1)
print("Case 1: Có tên trạm")
print(f"  Has station: {result1['has_station']}")
print(f"  Primary region: {result1['primary_region']}")  # => 2
print(f"  Stations: {result1['stations']}")
# Output: {"name": "Đồng Hới", "region": 2, "confidence": 0.9}

# Case 2: Chỉ có sông + tỉnh (không tên trạm)
text2 = """
Sông Hồng tại Hà Nội đang lên mức báo động 3.
Nguy cơ ngập úng khu vực thấp trũng.
"""

result2 = nlp.detect_flood_station(text2)
print("\nCase 2: Sông + Tỉnh")
print(f"  Has station: {result2['has_station']}")
# Có thể match được do "Hồng" + "Hà Nội" trong data

# Case 3: Bài chung chung (không có trạm)
text3 = """
Mưa lớn gây ngập lụt tại nhiều khu vực miền Trung.
"""

result3 = nlp.detect_flood_station(text3)
print("\nCase 3: Không có trạm")
print(f"  Has station: {result3['has_station']}")  # => False
print(f"  Primary region: {result3['primary_region']}")  # => None

# Ứng dụng trong phân loại
def enhanced_flood_classification(text, title=""):
    # 1. Detect station
    station_info = nlp.detect_flood_station(text)
    
    # 2. Classify disaster
    classification = nlp.classify_disaster(text, title)
    
    # 3. Enhance confidence if station detected
    is_flood = "flood" in classification["primary_type"]
    
    if station_info["has_station"] and is_flood:
        confidence_boost = "HIGH"  # Có evidence cụ thể (trạm)
        region = station_info["primary_region"]
        print(f"  ✅ Confirmed flood at station (Region {region})")
    elif is_flood:
        confidence_boost = "MEDIUM"  # Chỉ có từ khóa
        print(f"  ⚠️ General flood news (no specific station)")
    else:
        confidence_boost = "N/A"
    
    return {
        **classification,
        "station_info": station_info,
        "confidence": confidence_boost
    }

# Test
text_test = """
Trạm Thạch Hãn (Quảng Trị) báo cáo mực nước vượt báo động 2.
Cảnh báo nguy cơ lũ quét vùng thượng nguồn.
"""

result = enhanced_flood_classification(text_test)
print(f"\n=== Enhanced Classification ===")
print(f"Primary type: {result['primary_type']}")
print(f"Primary level: {result['primary_level']}")
print(f"Confidence: {result['confidence']}")
print(f"Station: {result['station_info']['stations'][0]['name'] if result['station_info']['has_station'] else 'N/A'}")
