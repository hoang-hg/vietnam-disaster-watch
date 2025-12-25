#!/usr/bin/env python3
"""
Test the new disaster keyword filtering functionality and metric extraction.
"""

import sys
import json
import io

# Force UTF-8 for Windows console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, '.')
from app.nlp import contains_disaster_keywords, extract_disaster_metrics, classify_disaster

def test_filtering():
    """Test disaster keyword filtering with real-world article titles and snippets."""
    
    # Format: (Text, Expected_Is_Disaster, Expected_Category[optional], Reason/Description)
    test_cases = [
        # --- POSITIVE CASES (True) ---
        
        # 1. Bão / ATNĐ
        ('[Tin bão khẩn cấp] Bão số 4 đổ bộ Quảng Bình vói sức gió mạnh cấp 10, giật cấp 12', 
         True, 'storm', 'Typical Storm Warning'),
         
        ('Áp thấp nhiệt đới trên Biển Đông suy yếu thành vùng áp thấp', 
         True, 'storm', 'Tropical Depression weakening'),

        # 2. Mưa lớn / Lũ lụt
        ('Mưa lớn kéo dài 3 ngày, lượng mưa phổ biến 150-200mm, gây ngập úng cục bộ', 
         True, 'flood_landslide', 'Heavy Rain with quantitative mm'),
         
        ('Lũ lịch sử tại Hà Tĩnh, mực nước sông Ngàn Sâu vượt báo động 3', 
         True, 'flood_landslide', 'Historic Flood'),
         
        ('Thủy điện xả lũ, hạ du nguy cơ ngập lụt diện rộng', 
         True, 'flood_landslide', 'Dam release & flooding'),

        # 3. Sạt lở / Sụt lún
        ('Sạt lở đất kinh hoàng tại Hòa Bình vùi lấp 3 hộ dân', 
         True, 'flood_landslide', 'Landslide with impact'),
         
        ('Hố tử thần xuất hiện giữa đường phố Sài Gòn sau mưa lớn', 
         True, 'flood_landslide', 'Sinkhole (Hố tử thần)'),

        # 4. Hạn hán / Mặn
        ('Xâm nhập mặn sâu vào nội đồng, độ mặn đạt 4‰ tại Bến Tre', 
         True, 'heat_drought', 'Salinity intrusion'),
         
        ('Nắng nóng gay gắt 40 độ C, nguy cơ cháy rừng cấp 5', 
         True, 'heat_drought', 'Extreme Heat & Wildfire Risk'),

        # 5. Động đất / Sóng thần
        ('Động đất 5.2 độ richter rung chuyển Cao Bằng', 
         True, 'quake_tsunami', 'Earthquake M>3.5'),
         
        ('Cảnh báo sóng thần sau động đất lớn ngoài khơi Philippines', 
         True, 'quake_tsunami', 'Tsunami Warning'),

        # 6. Gió mạnh / Biển
        ('Cảnh báo gió mạnh cấp 6-7 trên vùng biển Cà Mau', 
         True, 'wind_fog', 'Strong wind at sea'),

        # --- NEGATIVE CASES (False) - "Bẫy" ngữ nghĩa ---
        
        # Bão
        ('Thị trường vàng trong cơn bão giá chưa từng có', 
         False, None, 'Metaphor: Bão giá'),
         
        ('Cơn lốc sale 11/11 càn quét các sàn thương mại điện tử', 
         False, None, 'Metaphor: Lốc sale'),
         
        ('Bão sao kê: Loạt nghệ sĩ vướng ồn ào từ thiện', 
         False, None, 'Metaphor: Bão scandal'),

        # Động đất / Rung chấn
        ('Cú sốc địa chấn tại World Cup: Ả Rập Xê Út thắng Argentina', 
         False, None, 'Sports Metaphor: Địa chấn'),
         
        ('Rung chấn thị trường bất động sản sau vụ bắt giữ chủ tịch tập đoàn', 
         False, None, 'Market Metaphor: Rung chấn'),

        # Lũ
        ('Lũ lượt người đổ về AEON Mall ngày khai trương', 
         False, None, 'Common Speech: Lũ lượt'),
         
        ('Ngập tràn tiếng cười trong lễ hội xuân', 
         False, None, 'Metaphor: Ngập'),

        # Others
        ('Xe container gây tai nạn liên hoàn trên cao tốc', 
         False, None, 'Traffic Accident (Not natural disaster)'),
         
        ('Quy hoạch đô thị ven sông Hồng được phê duyệt', 
         False, None, 'Policy/Planning'),
    ]
    
    print('Testing Disaster Keyword Filtering & Classification')
    print('=' * 100)
    print(f'{"Result":<10} | {"Exp":<8} | {"Cat":<15} | {"Text Snippet":<50}')
    print('-' * 100)
    
    passed = 0
    failed = 0
    
    for text, should_accept, exp_cat, reason in test_cases:
        is_disaster = contains_disaster_keywords(text)
        category_dict = classify_disaster(text) if is_disaster else None
        category = category_dict["primary_type"] if category_dict else "N/A"
        
        status = 'MATCH' if is_disaster == should_accept else 'FAIL'
        
        # Verify category if it's a positive match
        cat_match = True
        if should_accept and exp_cat and category != exp_cat:
            cat_match = False
            status = 'WRONG_CAT'

        row = f'{status:<10} | {str(should_accept):<8} | {category:<15} | {text[:45]}...'
        print(row)
        
        if status == 'MATCH':
            passed += 1
        else:
            failed += 1
            print(f"   >>> [FAILED] Reason: {reason}")
    
    print('=' * 100)
    print(f'Results: {passed} passed, {failed} failed')
    
    # --- METRIC EXTRACTION TEST ---
    print('\nTesting Metric Extraction')
    print('-' * 100)
    metric_texts = [
        ("Mưa to 150mm gây ngập", {"rainfall_mm": 150.0}),
        ("Gió mạnh cấp 10, giật cấp 12", {"wind_level": 10, "wind_gust": 12}),
        ("Nhiệt độ cao nhất 40.5°C", {"temperature_c": 40.5}),
        ("Độ mặn 4‰ xâm nhập sâu", {"salinity_per_mille": 4.0}),
        ("Động đất M 5.3 tại Kon Tum", {"earthquake_magnitude": 5.3}),
    ]
    
    m_passed = 0
    for txt, expected in metric_texts:
        extracted = extract_disaster_metrics(txt)
        # Check subset
        is_ok = True
        for k, v in expected.items():
            if extracted.get(k) != v:
                is_ok = False
        
        if is_ok:
            print(f"MATCH | {txt:<40} -> {extracted}")
            m_passed += 1
        else:
            print(f"FAIL  | {txt:<40} -> Got {extracted}, Exp {expected}")

    print(f"Metrics Results: {m_passed}/{len(metric_texts)} passed")

    return failed == 0 and m_passed == len(metric_texts)

if __name__ == '__main__':
    success = test_filtering()
    sys.exit(0 if success else 1)
