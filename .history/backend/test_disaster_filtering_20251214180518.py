#!/usr/bin/env python3
"""
Test the new disaster keyword filtering functionality.
"""

import sys
sys.path.insert(0, '.')
from app.nlp import contains_disaster_keywords

def test_filtering():
    """Test disaster keyword filtering with various article titles."""
    test_cases = [
        # Should ACCEPT (contain disaster keywords)
        ('Bão số 4 đổ bộ Hà Tĩnh - Quảng Bình, gây ngập lụt nặng', True),
        ('Động đất 5.2 độ richter tại Cao Bằng', True),
        ('Xuất hiện hố do sụt lún đường quốc lộ qua Huế', True),
        ('Lũ quét gây tàn phá nhiều nhà dân tại Quảng Trị', True),
        ('Ngành hàng không cảnh báo gió giật mạnh từ bão Kai-Tak', True),
        ('Hạn hán kéo dài ở Tây Nguyên gây thiệt hại nông nghiệp', True),
        ('Sóng thần cảnh báo tại Biển Đông', True),
        ('Cháy rừng tại tỉnh Đắk Lắk lan rộng', True),
        
        # Should SKIP (no disaster keywords)
        ('Đột nhập nhà dân trộm ô tô rồi lái đi đón bạn gái', False),
        ('Phát hiện thi thể nam giới trên sông Sài Gòn có hình xăm cá chép', False),
        ('Bắt nghi phạm đột nhập hàng loạt trường học ở Đà Nẵng trộm máy chiếu', False),
        ('Chủ tịch Trần Thanh Mẫn tiếp xúc cử tri tại Cần Thơ', False),
        ('Cuối tuần lai rai vài chai, nhiều người vi phạm nồng độ cồn bị xử lý', False),
        ('Chủ tịch cấp tỉnh được trao nhiều thẩm quyền lớn với dự án đất đai', False),
    ]
    
    print('Testing Disaster Keyword Filtering')
    print('=' * 90)
    print(f'{"Status":<12} | {"Expected":<10} | {"Title":<65}')
    print('-' * 90)
    
    passed = 0
    failed = 0
    
    for title, should_accept in test_cases:
        is_disaster = contains_disaster_keywords(title)
        status = '✓ ACCEPT' if is_disaster else '✗ SKIP'
        expected = 'ACCEPT' if should_accept else 'SKIP'
        
        # Check if result matches expectation
        is_correct = is_disaster == should_accept
        if is_correct:
            passed += 1
            check = '✓'
        else:
            failed += 1
            check = '✗ FAIL'
        
        print(f'{status:<12} | {expected:<10} | {title[:65]:<65} {check}')
    
    print('=' * 90)
    print(f'Results: {passed} passed, {failed} failed')
    
    return failed == 0

if __name__ == '__main__':
    success = test_filtering()
    sys.exit(0 if success else 1)
