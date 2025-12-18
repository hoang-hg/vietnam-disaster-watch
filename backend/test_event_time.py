# Test cases for enhanced extract_event_time()

from datetime import datetime
from backend.app import nlp

# Mock published_at: 2024-12-18 14:30:00
published_at = datetime(2024, 12, 18, 14, 30, 0)

test_cases = [
    # Relative time - Today
    ("Sáng nay, bão số 5 đổ bộ vào Quảng Nam", "2024-12-18 12:00"),
    ("Chiều nay mưa lớn tại Hà Nội", "2024-12-18 12:00"),
    ("Hôm nay phát hiện 3 người mất tích", "2024-12-18 12:00"),
    
    # Relative time - Yesterday
    ("Đêm qua xảy ra động đất cấp 4", "2024-12-17 22:00"),
    ("Tối qua lũ quét cuốn trôi 2 nhà", "2024-12-17 22:00"),
    ("Hôm qua mực nước lên cao", "2024-12-17 12:00"),
    
    # Relative time - Early morning
    ("Rạng sáng, lũ ống tràn vào làng", "2024-12-18 05:00"),
    ("Đêm qua rạng sáng nay xảy ra sạt lở", "2024-12-18 05:00"),
    
    # Relative time - Days ago
    ("2 ngày trước bão đổ bộ", "2024-12-16 12:00"),
    ("3 ngày qua mưa liên tục", "2024-12-15 12:00"),
    ("Tuần trước xảy ra lũ lớn", "2024-12-11 12:00"),
    
    # Vietnamese date format
    ("Ngày 15 tháng 12 xảy ra động đất", "2024-12-15 12:00"),
    ("15 tháng 12 năm 2024 bão số 3", "2024-12-15 12:00"),
    ("Vào 10 tháng 11, lũ cuốn trôi cầu", "2024-11-10 12:00"),
    
    # Absolute date format
    ("Vào ngày 12/12/2024 xảy ra sạt lở", "2024-12-12"),
    ("15-11-2024: Bão số 2 đổ bộ", "2024-11-15"),
    ("5/12 phát hiện vết nứt đất", "2024-12-05"),
]

print("=== Test extract_event_time() ===\n")
print(f"Published at: {published_at.strftime('%Y-%m-%d %H:%M')}\n")

for text, expected in test_cases:
    result = nlp.extract_event_time(published_at, text)
    status = "✅" if result else "❌"
    
    if result:
        result_str = result.strftime('%Y-%m-%d %H:%M')
        match = "✓" if result_str.startswith(expected[:10]) else "✗"
        print(f"{status} {match} | {text[:50]:50s} → {result_str}")
    else:
        print(f"{status}   | {text[:50]:50s} → None")

print("\n=== Use case: Event deduplication ===\n")

# Scenario: Same event reported by different sources
events = [
    {
        "source": "VnExpress",
        "published": datetime(2024, 12, 18, 8, 0),
        "text": "Sáng nay xảy ra lũ quét tại Lào Cai"
    },
    {
        "source": "Tuổi Trẻ",
        "published": datetime(2024, 12, 18, 9, 30),
        "text": "Hôm nay phát hiện lũ ống tại Lào Cai"
    },
    {
        "source": "Thanh Niên",
        "published": datetime(2024, 12, 18, 10, 15),
        "text": "18/12/2024: Lũ quét nghiêm trọng ở Lào Cai"
    },
]

print("Events from different sources:")
event_times = {}

for e in events:
    event_time = nlp.extract_event_time(e["published"], e["text"])
    event_date = event_time.date() if event_time else None
    
    print(f"  [{e['source']:12s}] Published: {e['published'].strftime('%H:%M')}, "
          f"Event: {event_date if event_date else 'Unknown'}")
    
    if event_date:
        if event_date not in event_times:
            event_times[event_date] = []
        event_times[event_date].append(e)

print(f"\nGrouped by event date:")
for date, group in event_times.items():
    print(f"  {date}: {len(group)} reports (can be deduplicated)")

print("\n=== Use case: Timeline construction ===\n")

disaster_timeline = [
    ("Ngày 10 tháng 12: Bắt đầu mưa lớn", datetime(2024, 12, 15, 10, 0)),
    ("2 ngày trước xuất hiện lũ quét", datetime(2024, 12, 15, 10, 0)),
    ("Hôm qua mực nước lên đỉnh", datetime(2024, 12, 15, 10, 0)),
    ("Sáng nay lũ bắt đầu rút", datetime(2024, 12, 15, 10, 0)),
]

print("Constructing timeline from relative references:")
timeline = []
for text, pub_date in disaster_timeline:
    event_time = nlp.extract_event_time(pub_date, text)
    if event_time:
        timeline.append((event_time, text))

timeline.sort()
print("\nSorted timeline:")
for t, text in timeline:
    print(f"  {t.strftime('%Y-%m-%d')}: {text}")
