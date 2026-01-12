# -*- coding: utf-8 -*-
import sys
import os
import re
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

print("Starting Veto Check...")

try:
    from app import sources
    print("SUCCESS: Imported app.sources")
except ImportError as e:
    print(f"ERROR: Could not import app.sources: {e}")
    # Try alternate path
    sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))
    try:
        import sources
        print("SUCCESS: Imported sources directly")
    except ImportError as e2:
        print(f"FATAL: Could not import sources: {e2}")
        sys.exit(1)

def check_veto():
    print("-" * 30)
    print(f"ABSOLUTE_VETO List Size: {len(sources.ABSOLUTE_VETO)}")
    print(f"First item: {sources.ABSOLUTE_VETO[0]}")
    # Print a middle item to check
    mid = len(sources.ABSOLUTE_VETO)//2
    print(f"Middle item: {sources.ABSOLUTE_VETO[mid]}")
    print(f"Last item: {sources.ABSOLUTE_VETO[-1]}")
    
    if hasattr(sources, 'ABSOLUTE_VETO_RE') and sources.ABSOLUTE_VETO_RE:
        print("ABSOLUTE_VETO_RE is compiled and available.")
        # print(f"Pattern type: {type(sources.ABSOLUTE_VETO_RE)}")
    else:
        print("ERROR: ABSOLUTE_VETO_RE is missing or None!")
        # Attempt minimal compilation manually to see if it works
        try:
            print("Attempting manual compilation of ABSOLUTE_VETO...")
            re.compile("|".join(sources.ABSOLUTE_VETO), re.IGNORECASE)
            print("Manual compilation SUCCESS.")
        except Exception as ce:
            print(f"Manual compilation FAILED: {ce}")
        return

    # Test Cases
    test_cases = [
        ("Bão số 3 gây thiệt hại nặng", False), # Genuine
        ("Lũ quét tại Lào Cai", False), # Genuine
        ("Tuyển dụng nhân viên kinh doanh lương cao", True), # Veto: tuyển dụng
        ("Bắn cá đổi thưởng online cực hot", True), # Veto: bắn cá
        ("Khuyến mãi khủng mua 1 tặng 1", True), # Veto: khuyến mãi
        ("Điều trị ung thư giai đoạn cuối", True), # Veto: ung thư (unless context)
        ("Xổ số miền bắc hôm nay", True), # Veto: xổ số
        ("Check-in sang chảnh tại Đà Lạt", True), # Veto: check-in
        ("Chiến dịch Quang Trung hỗ trợ vùng lũ", False), # Whitelist keyword with disaster context
        ("Trực tiếp bóng đá Ngoại hạng Anh", True), # Veto: bóng đá
        ("Giá heo hơi hôm nay tăng nhẹ", True), # Veto: giá heo
        ("Tai nạn giao thông nghiêm trọng", True), # Veto: tai nạn (Conditional? No, might be Absolute if in list)
        # Note: 'tai nạn giao thông' is in ABSOLUTE_VETO with lookahead (?!...)
        # "Tai nạn giao thông nghiêm trọng" -> matches "tai nạn giao thông"
        # The lookahead (?!.*(?:sạt lở|lũ...)) checks if disaster terms are AFTER.
        # "Tai nạn giao thông nghiêm trọng" does NOT have disaster terms. So lookahead succeeds (it's negative).
        # So it SHOULD match veto (Veto=True).
        ("Tai nạn giao thông do sạt lở đất", False), # Disaster context -> Veto should Fail (False)
        ("Cháy nhà dân tại Hà Nội", True), # Veto: cháy nhà (conditional/absolute with lookahead)
        ("Cháy rừng lan rộng do nắng nóng", False), # Disaster context -> Veto False
    ]

    print("\n--- Running Regex Tests ---")
    failures = 0
    for text, should_veto in test_cases:
        t_acc = text.lower()
        match = sources.ABSOLUTE_VETO_RE.search(t_acc)
        is_vetoed = match is not None
        
        status = "PASS" if is_vetoed == should_veto else "FAIL"
        if status == "FAIL": failures += 1
        
        print(f"[{status}] Text: '{text}' -> Vetoed: {is_vetoed} (Expected: {should_veto})")
        if match:
            print(f"   Matches: {match.group()}")

    if failures == 0:
        print("\nALL TESTS PASSED.")
    else:
        print(f"\n{failures} TESTS FAILED.")

if __name__ == "__main__":
    check_veto()
