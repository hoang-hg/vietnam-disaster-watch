
import unittest
from unittest.mock import MagicMock
import sys
import re

# Mock dependencies before importing app modules
sys.modules['app.cache'] = MagicMock()
sys.modules['app.broadcast'] = MagicMock()
sys.modules['app.ws'] = MagicMock()
sys.modules['app.notifications'] = MagicMock()

# Now import the logic
from app.event_matcher import _get_tokens, _calculate_similarity, _find_best_match
# We don't import models inside test methods usually, need to mock the db session objects 
# if we were testing _find_best_match comprehensively, but here we focus on similarity math.

class TestEventMatchingQuality(unittest.TestCase):
    
    def calculate_score(self, title1, title2):
        tok1 = _get_tokens(title1)
        tok2 = _get_tokens(title2)
        return _calculate_similarity(tok1, tok2)

    def test_storm_yagi_matching(self):
        """Test matching 'Bão số 3' with 'Bão Yagi'"""
        t1 = "Bão số 3 đổ bộ vào Quảng Ninh"
        t2 = "Bão Yagi (bão số 3) giật cấp 15 tại Quảng Ninh"
        score = self.calculate_score(t1, t2)
        print(f"Bão Yagi Score: {score}")
        self.assertGreater(score, 0.30, "Should match Typhoon Yagi variations")

    def test_flood_ha_giang_matching(self):
        """Test matching Flood in Ha Giang with different phrasing"""
        t1 = "Mưa lớn gây ngập lụt tại Hà Giang"
        t2 = "Hà Giang: Mưa lớn khiến nhiều nơi bị ngập sâu"
        score = self.calculate_score(t1, t2)
        print(f"Hà Giang Flood Score: {score}")
        self.assertGreater(score, 0.30, "Should match Ha Giang flood events")

    def test_different_locations_mismatch(self):
        """Test that different locations do NOT match"""
        t1 = "Sạt lở đất tại Lào Cai khiến 2 người chết"
        t2 = "Sạt lở đất nghiêm trọng tại Yên Bái, 1 người mất tích"
        score = self.calculate_score(t1, t2)
        print(f"Diff Location Score: {score}")
        self.assertLess(score, 0.30, "Should NOT match different locations")

    def test_different_disaster_same_location(self):
        """Test that different disaster types in same location do NOT match"""
        t1 = "Cháy lớn tại chợ Đồng Xuân, Hà Nội"
        t2 = "Hà Nội: Mưa giông gây ngập úng cục bộ"
        score = self.calculate_score(t1, t2)
        print(f"Diff Disaster Score: {score}")
        self.assertLess(score, 0.30, "Should NOT match different disaster types")

    def test_stopwords_effectiveness(self):
        """Verify common words are filtered"""
        text = "bị tại người nhiều khiến gây"
        u, b = _get_tokens(text)
        # All these should be stopwords now
        self.assertEqual(len(u), 0, f"Stopwords leaked: {u}")

if __name__ == '__main__':
    unittest.main()
