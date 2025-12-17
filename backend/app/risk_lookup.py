import re

# Keyword definitions based on Decision 18/2021/QD-TTg Article 42
# Normalized to lowercase for matching

# 1. Intensity Keywords
LEVEL_8_9 = [r"cấp 8", r"cấp 9", r"áp thấp nhiệt đới", "atnđ"]
LEVEL_10_11 = [r"cấp 10", r"cấp 11"]
LEVEL_12_13 = [r"cấp 12", r"cấp 13"]
LEVEL_14_15 = [r"cấp 14", r"cấp 15"]
LEVEL_16_UP = [r"cấp 16", r"cấp 17", "siêu bão"] 

# 2. Location Keywords (Groups)
LOC_BIENDONG = ["biển đông", "hoàng sa", "trường sa"]
LOC_VENBO = ["ven bờ"]
LOC_SOUTH = ["nam bộ", "miền tây", "miền đông"] # Added typical aliases if needed, but sticking to text
LOC_NORTH = ["tây bắc", "việt bắc", "đông bắc bộ", "đồng bằng bắc bộ", "hà nội", "bắc bộ"] # Expanded slightly for coverage
LOC_CENTRAL = ["bắc trung bộ", "trung trung bộ", "nam trung bộ", "tây nguyên", "miền trung"]

# Helper to check if text contains any pattern from list
def has_any(text, patterns):
    for p in patterns:
        if p in text or re.search(r"\b" + p + r"\b", text):
            return True
    return False

def check_storm_risk(text: str) -> int:
    """
    Analyzes text for Storm/Tropical Depression risk based on Article 42.
    Returns Risk Level (3, 4, 5) or 0 if no match.
    Logic is hierarchical: Check Level 5 -> 4 -> 3.
    """
    t = text.lower()
    
    # Pre-check: Must mention storm/atnd context? 
    # The function is called if disaster_type is storm usually, or generic.
    # Text usually contains "bão" or "áp thấp".
    
    # --- LEVEL 5 ---
    # 3a) Cap 12-13 at Nam Bo
    if has_any(t, LEVEL_12_13) and has_any(t, LOC_SOUTH):
        return 5
    # 3b) Cap 14-15 at Tay Bac, Viet Bac, Nam Trung Bo, Tay Nguyen, Nam Bo
    # (Basically most land except North/NorthCentral?) -> Reg says: Tay Bac, Viet Bac, Nam Trung Bo, Tay Nguyen, Nam Bo.
    # Missing: Dong Bac Bo, Dong Bang Bac Bo, Bac Trung Bo, Trung Trung Bo.
    if has_any(t, LEVEL_14_15) and (has_any(t, LOC_SOUTH) or "tây nguyên" in t or "nam trung bộ" in t or "tây bắc" in t or "việt bắc" in t):
        return 5
    # 3c) Super Storm (16+) at Ven Bo or Any Land
    if has_any(t, LEVEL_16_UP):
        # Strict reg: Ven Bo or Land. If just "Tren Bien Dong" -> usually Risk 4 (2d says 14+ on Bien Dong).
        # But 3c says "Super storm ... ven bo; dat lien".
        # If text says "Sieu bao tren bien dong" -> Risk 4 or 5?
        # Reg 2d: Storm 14+ on Bien Dong -> Risk 4.
        # So Super Storm on Bien Dong is Risk 4?
        # But "Sieu bao" generic is usually Risk 5.
        # Let's check location strictly.
        if has_any(t, LOC_VENBO) or has_any(t, LOC_NORTH) or has_any(t, LOC_CENTRAL) or has_any(t, LOC_SOUTH):
            return 5
          
    # --- LEVEL 4 ---
    # 2a) Cap 10-11 at Nam Bo
    if has_any(t, LEVEL_10_11) and has_any(t, LOC_SOUTH):
        return 4
    # 2b) Cap 12-13 at Ven Bo, Land North/Central/Highland (Excl South -> handled in 3a)
    if has_any(t, LEVEL_12_13):
        if has_any(t, LOC_VENBO) or has_any(t, LOC_NORTH) or has_any(t, LOC_CENTRAL):
            return 4
    # 2c) Cap 14-15 at Ven Bo, North/Central (Excl South/Highland -> handled in 3b)
    if has_any(t, LEVEL_14_15):
        if has_any(t, LOC_VENBO) or has_any(t, LOC_NORTH) or "bắc trung bộ" in t or "trung trung bộ" in t:
            return 4
    # 2d) Cap 14+ on Bien Dong
    if (has_any(t, LEVEL_14_15) or has_any(t, LEVEL_16_UP)) and has_any(t, LOC_BIENDONG):
        return 4

    # --- LEVEL 3 ---
    # 1a) ATND / Cap 8-9 on Bien Dong, Ven Bo, Land (Anywhere basically)
    if has_any(t, LEVEL_8_9):
        # Must appear with some location to be valid warning context?
        if has_any(t, LOC_BIENDONG) or has_any(t, LOC_VENBO) or has_any(t, LOC_NORTH) or has_any(t, LOC_CENTRAL) or has_any(t, LOC_SOUTH):
            return 3
            
    # 1b) Cap 10-11 on Bien Dong, Ven Bo, Land (Excl Nam Bo -> handled in 2a)
    if has_any(t, LEVEL_10_11):
        if has_any(t, LOC_BIENDONG) or has_any(t, LOC_VENBO) or has_any(t, LOC_NORTH) or has_any(t, LOC_CENTRAL):
            return 3
    # 1c) Cap 12-13 on Bien Dong
    if has_any(t, LEVEL_12_13) and has_any(t, LOC_BIENDONG):
        return 3

    return 0

# --- WATER SURGE (Nước dâng) - Article 43 ---

# Water Level Patterns (Strict context "nước dâng ... X m")
WL_1_2 = [r"1\s*m", r"1\s*mét", r"1,5\s*m", r"2\s*m", r"2\s*mét"]
WL_2_3 = [r"2\s*m", r"2\s*mét", r"2,5\s*m", r"3\s*m", r"3\s*mét", r"trên 2\s*m"]
WL_3_4 = [r"3\s*m", r"3\s*mét", r"3,5\s*m", r"4\s*m", r"4\s*mét", r"trên 3\s*m"]
WL_4_5 = [r"4\s*m", r"4\s*mét", r"4,5\s*m", r"5\s*m", r"5\s*mét", r"trên 4\s*m"]
WL_5_6 = [r"5\s*m", r"5\s*mét", r"5,5\s*m", r"6\s*m", r"6\s*mét", r"trên 5\s*m"]
WL_GT_6 = [r"6\s*m", r"6\s*mét", r"trên 6\s*m"]

# Location Groups for Surge
# G1: Quang Binh -> Binh Dinh
LOC_QB_BD = ["quảng bình", "quảng trị", "thừa thiên huế", "đà nẵng", "quảng nam", "quảng ngãi", "bình định"]
# G2: Ca Mau -> Kien Giang
LOC_CM_KG = ["cà mau", "kiên giang"]
# G3: Nghe An -> Ha Tinh
LOC_NA_HT = ["nghệ an", "hà tĩnh"]
# G4: Phu Yen -> Ca Mau (Large South Central + South)
LOC_PY_CM = ["phú yên", "khánh hòa", "ninh thuận", "bình thuận", "bà rịa", "vũng tàu", "tp hcm", "tiền giang", "bến tre", "trà vinh", "sóc trăng", "bạc liêu", "cà mau"]
# G5: Quang Ninh -> Thanh Hoa (North)
LOC_QN_TH = ["quảng ninh", "hải phòng", "thái bình", "nam định", "ninh bình", "thanh hóa"]
# G6: Binh Thuan -> Ca Mau
LOC_BT_CM = ["bình thuận", "bà rịa", "vũng tàu", "tp hcm", "tiền giang", "bến tre", "trà vinh", "sóc trăng", "bạc liêu", "cà mau"]
# G7: Phu Yen -> Ninh Thuan
LOC_PY_NT = ["phú yên", "khánh hòa", "ninh thuận"]
# G8: Quang Binh -> Thua Thien Hue
LOC_QB_TTH = ["quảng bình", "quảng trị", "thừa thiên huế"]
# G9: Da Nang -> Binh Dinh
LOC_DN_BD = ["đà nẵng", "quảng nam", "quảng ngãi", "bình định"]


def check_surge_risk(text: str) -> int:
    """Article 43: Storm Surge Risk"""
    t = text.lower()
    if "nước dâng" not in t and "triều cường" not in t:
        return 0

    # Determine rough max water level mentioned
    # This is a heuristic: check highest level first.
    
    # --- LEVEL 5 ---
    # 4a) >5m at QB->TTH
    if has_any(t, WL_5_6) or has_any(t, WL_GT_6):
        if has_any(t, LOC_QB_TTH): return 5
    # 4b) >6m at QN->HT
    if has_any(t, WL_GT_6):
        if has_any(t, LOC_QN_TH) or has_any(t, LOC_NA_HT): return 5
        
    # --- LEVEL 4 ---
    # 3a) 3-4m at QB->TTH
    if has_any(t, WL_3_4) and has_any(t, LOC_QB_TTH): return 4
    # 3b) 4-5m at NA->TTH (NA->HT + QB->TTH)
    if has_any(t, WL_4_5) and (has_any(t, LOC_NA_HT) or has_any(t, LOC_QB_TTH)): return 4
    # 3c) 5-6m at QN->HT
    if has_any(t, WL_5_6) and (has_any(t, LOC_QN_TH) or has_any(t, LOC_NA_HT)): return 4
    # 3d) >3m at DN->BD OR CM->KG
    if (has_any(t, WL_3_4) or has_any(t, WL_4_5) or has_any(t, WL_5_6)) and (has_any(t, LOC_DN_BD) or has_any(t, LOC_CM_KG)): return 4
    # 3dd) >4m at BT->CM
    if (has_any(t, WL_4_5) or has_any(t, WL_5_6)) and has_any(t, LOC_BT_CM): return 4
    
    # --- LEVEL 3 ---
    # 2a) 2-3m at QB->BD OR CM->KG
    if has_any(t, WL_2_3) and (has_any(t, LOC_QB_BD) or has_any(t, LOC_CM_KG)): return 3
    # 2b) 3-4m at NA->HT OR BT->CM
    if has_any(t, WL_3_4) and (has_any(t, LOC_NA_HT) or has_any(t, LOC_BT_CM)): return 3
    # 2c) 4-5m at QN->TH
    if has_any(t, WL_4_5) and has_any(t, LOC_QN_TH): return 3
    # 2d) >3m at PY->NT
    if (has_any(t, WL_3_4) or has_any(t, WL_4_5)) and has_any(t, LOC_PY_NT): return 3
    
    # --- LEVEL 2 ---
    # 1a) 1-2m at QB->BD OR CM->KG
    if has_any(t, WL_1_2) and (has_any(t, LOC_QB_BD) or has_any(t, LOC_CM_KG)): return 2
    # 1b) 2-3m at NA->HT OR PY->CM
    if has_any(t, WL_2_3) and (has_any(t, LOC_NA_HT) or has_any(t, LOC_PY_CM)): return 2
    # 1c) 3-4m at QN->TH
    if has_any(t, WL_3_4) and has_any(t, LOC_QN_TH): return 2
    
    return 0

# --- HEAVY RAIN (Mưa lớn) - Article 44 ---

# Rain Amount Patterns
# Regex looks for patterns like "100-200mm", "trên 200 mm"
RAIN_100_200 = [r"100[-\s]200\s*mm", r"50[-\s]100\s*mm"] # Combined 24h and 12h logic approx
RAIN_200_400 = [r"200[-\s]400\s*mm", r"trên 200\s*mm"]
RAIN_GT_400 = [r"trên 400\s*mm", r"400[-\s]500\s*mm", r"500\s*mm", r"lịch sử", r"kỷ lục"] # History/Record implies >400 usually

# Duration Patterns
# Simple keywords. Exact day parsing is hard, so we use buckets.
DUR_LONG = [r"trên 4 ngày", r"4[-\s]7 ngày", r"nhiều ngày", r"dài ngày"] # > 4 days
DUR_MED = [r"trên 2 ngày", r"2[-\s]4 ngày", r"3 ngày", r"4 ngày", r"kéo dài"] # 2-4 days
DUR_SHORT = [r"1[-\s]2 ngày", r"2 ngày", r"24 giờ", r"24h", r"đợt mưa"] # 1-2 days

# Terrain Context
TERRAIN_MT = ["trung du", "miền núi", "vùng núi", "tây nguyên", "tây bắc", "việt bắc"]
TERRAIN_PLAIN = ["đồng bằng", "ven biển", "hà nội", "tp hcm"] # Plain

def check_rain_risk(text: str) -> int:
    """Article 44: Heavy Rain Risk"""
    t = text.lower()
    
    # Check max rain amount
    amt = 0
    if has_any(t, RAIN_GT_400): amt = 400
    elif has_any(t, RAIN_200_400): amt = 300
    elif has_any(t, RAIN_100_200): amt = 150
    
    if amt == 0: return 0 # No rain amount mentioned
    
    # Check duration
    dur = 1
    if has_any(t, DUR_LONG): dur = 5
    elif has_any(t, DUR_MED): dur = 3
    elif has_any(t, DUR_SHORT): dur = 2
    
    # Check terrain (If mentioned "vùng núi" prioritize it)
    is_mt = has_any(t, TERRAIN_MT)
    # is_plain = has_any(t, TERRAIN_PLAIN) # default if not mountain
    
    # --- LEVEL 4 ---
    # 4a) 200-400mm, >4 days, Mountain
    if amt >= 300 and dur >= 5 and is_mt: return 4
    # 4b) >400mm, >2 days (Mt) OR >4 days (Plain)
    if amt >= 400:
        if (is_mt and dur >= 3) or (dur >= 5): return 4
        
    # --- LEVEL 3 ---
    # 3a) 100-200mm, >4 days, Mountain
    if amt >= 150 and dur >= 5 and is_mt: return 3
    # 3b) 200-400mm, 2-4 days (Mt) OR >2 days (Plain/Any)
    if amt >= 300:
        if (is_mt and dur >= 3) or (dur >= 3): return 3
    # 3c) >400mm, 1-2 days (Mt) OR 1-4 days (Plain)
    if amt >= 400: return 3 # Covers both cases roughly (Base level for >400mm is 3)

    # --- LEVEL 2 ---
    # 2a) 100-200mm, 2-4 days (Mt) OR >2 days (Plain)
    if amt >= 150:
        if (is_mt and dur >= 3) or (dur >= 3): return 2
    # 2b) 200-400mm, 1-2 days
    if amt >= 300 and dur <= 2: return 2
    
    # --- LEVEL 1 ---
    # 1) 100-200mm, 1-2 days
    if amt >= 150 and dur <= 2: return 1
    
    return 0

# --- FLOOD (Lũ, Ngập lụt) - Article 45 ---
# Note: Article 45 depends on Hydrological Zones (Zone 1-4).
# Without Zone mapping, we apply a Heuristic based on Severity keywords.
# "Báo động 3" is handled by generic NLP regex -> maps to Risk 3.
# Here we handle "Historic Flood" levels.

FLOOD_HISTORIC_EXCEED = [r"vượt lũ lịch sử", r"vượt mức lịch sử", r"vượt đỉnh lũ lịch sử"]
FLOOD_HISTORIC = [r"lũ lịch sử", r"đỉnh lũ lịch sử", r"tương đương lũ lịch sử"]
# FLOOD_ALARM_3_PLUS = [r"trên báo động 3", "vượt báo động 3"] -> Maps to 3 usually, or 4 in Zone 4. 
# We'll stick to Historic for strictly higher levels.

def check_flood_risk(text: str) -> int:
    """Article 45: Flood Risk (Historic Levels)"""
    t = text.lower()
    
    # 5. Exceed Historic Flood -> Level 5 (Art 45.5)
    if has_any(t, FLOOD_HISTORIC_EXCEED):
        return 5
        
    # 4. Historic Flood -> Level 4 (Art 45.4 "Alarm 3 + 0.3m to Historic")
    # Actually 45.4 says "to historic". 45.5 says "exceed historic".
    # So "Historic Flood" is boundary of 4/5. 
    # Safe to map "Lũ lịch sử" to 4 (Major disaster) or 5? 
    # Let's map to Level 4 to be safe, Exceed -> 5.
    if has_any(t, FLOOD_HISTORIC):
        return 4
        
    return 0

# --- FLASH FLOOD / LANDSLIDE (Lũ quét, Sạt lở) - Article 46 ---
# Zones defined in Appendix XII Table 5 (as per Prompt)

FF_R1 = ["lai châu", "sơn la", "điện biên", "hòa bình", "lào cai", "yên bái", "hà giang"]
FF_R2 = ["tuyên quang", "bắc kạn", "lạng sơn", "cao bằng", "thanh hóa", "nghệ an", "quảng ngãi"]
FF_R3 = ["phú thọ", "thái nguyên", "quảng ninh", "hà tĩnh", "quảng bình", "quảng trị", "thừa thiên huế", "đà nẵng", "quảng nam", "khánh hòa", "kon tum", "gia lai", "đắk lắk", "đắk nông", "lâm đồng"]
FF_R4 = ["vĩnh phúc", "bắc giang", "hải phòng", "bình định", "phú yên", "ninh thuận", "bình thuận"]

def check_flash_flood_risk(text: str) -> int:
    """Article 46: Flash Flood/Landslide Risk"""
    t = text.lower()
    
    # Must explicitly mention Flash Flood / Landslide keywords
    if not ("lũ quét" in t or "sạt lở" in t or "sụt lún" in t):
        return 0

    # Determine Rain Amount (Reuse Patterns)
    amt = 0
    if has_any(t, RAIN_GT_400): amt = 400
    elif has_any(t, RAIN_200_400): amt = 300
    elif has_any(t, RAIN_100_200): amt = 150
    
    # Strict Policy: If no rain amount mention, typical warnings might just be Level 1.
    if amt == 0: return 0

    # Determine Region Zone
    # Check R1 -> R2 -> R3 -> R4
    is_r1 = has_any(t, FF_R1)
    is_r2 = has_any(t, FF_R2)
    is_r3 = has_any(t, FF_R3)
    is_r4 = has_any(t, FF_R4)

    # Risk Logic (Simplified Matrix based on Max Potentials)
    # We assume "High Risk Area" within the Zone if not specified, for safety.
    
    # --- LEVEL 3 ---
    # 3a) 100-200mm, R1/R2 (Very High Zone) -> Level 3
    # 3b) >200mm, R1/R2 (High/Very High) -> Level 3
    # 3b) >200mm, R3 (Very High) -> Level 3
    # 3c) >400mm, R1/R2/R3 (High/Very High) -> Level 3
    if amt >= 300: # >200mm
        if is_r1 or is_r2 or is_r3: return 3
    if amt >= 150: # 100-200mm
        if is_r1 or is_r2: return 3 # Aggressive Safety
    
    # --- LEVEL 2 ---
    # 2a) 100-200mm, R1/R2 (High) -> Level 2
    # 2b) >200mm, R1/R2 (Med), R3 (High), R4 (Very High) -> Level 2
    if amt >= 300: # >200mm
        if is_r4: return 2
    if amt >= 150: # 100-200mm
        # If R3 (Very High Risk Zone) could be 2. Let's map R3 to 2 here.
        if is_r3: return 2
        
    # --- LEVEL 1 ---
    # 1a) 100-200mm R1/2/3/4 (Low/Med/High) -> Level 1
    if amt >= 150:
         return 1
         
    return 0

# --- HEAT / HEATWAVE (Nắng nóng) - Article 47 ---

# Temp Patterns
TEMP_35_37 = [r"35[-\s]37\s*độ", r"35[-\s]37\s*c", r"nắng nóng diện rộng"] # "Nắng nóng" implies >35
TEMP_37_39 = [r"37[-\s]39\s*độ", r"37[-\s]39\s*c", r"trên 37\s*độ", r"nắng nóng gay gắt"]
TEMP_39_41 = [r"39[-\s]41\s*độ", r"39[-\s]41\s*c", r"trên 39\s*độ", r"40\s*độ", r"nắng nóng đặc biệt gay gắt"]
TEMP_GT_41 = [r"trên 41\s*độ", r"vượt 41\s*độ", r"42\s*độ", r"43\s*độ"]

# Duration Patterns (Heat specific)
HEAT_DUR_3 = [r"3 ngày", r"trên 3 ngày", r"3[-\s]5 ngày"] # >= 3 days
HEAT_DUR_5 = [r"5 ngày", r"trên 5 ngày", r"5[-\s]10 ngày"]
HEAT_DUR_10 = [r"10 ngày", r"trên 10 ngày", r"10[-\s]25 ngày", r"dài ngày"]
HEAT_DUR_25 = [r"25 ngày", r"trên 25 ngày", r"kéo dài hàng tháng", r"đợt nắng nóng kỷ lục"]

# Heat Regions
# Group S: Tay Nguyen, Nam Bo
HEAT_LOC_S = ["tây nguyên", "nam bộ", "miền nam", "tp hcm", "đồng nai", "bình dương"]
# Group N: Bac Bo, Trung Bo
HEAT_LOC_N = ["bắc bộ", "trung bộ", "miền bắc", "miền trung", "hà nội", "nghệ an", "thanh hóa"]

def check_heat_risk(text: str) -> int:
    """Article 47: Heat Risk"""
    t = text.lower()
    
    # Check Temp Bucket
    temp = 0
    if has_any(t, TEMP_GT_41): temp = 42
    elif has_any(t, TEMP_39_41): temp = 40
    elif has_any(t, TEMP_37_39): temp = 38
    elif has_any(t, TEMP_35_37): temp = 36
    
    if temp == 0: return 0 # No heat context

    # Check Duration Bucket
    dur = 1 # default <3 days
    if has_any(t, HEAT_DUR_25): dur = 25
    elif has_any(t, HEAT_DUR_10): dur = 10
    elif has_any(t, HEAT_DUR_5): dur = 5
    elif has_any(t, HEAT_DUR_3) or "đợt nắng nóng" in t: dur = 3
    
    # Check Region
    is_s = has_any(t, HEAT_LOC_S)
    # is_n = has_any(t, HEAT_LOC_N) # default

    # --- LEVEL 4 ---
    # 4a) 39-41, >25 days (S)
    if temp >= 40 and dur >= 25 and is_s: return 4
    # 4b) >41, >10 days (S) OR >25 days (N)
    if temp >= 42:
        if (is_s and dur >= 10) or (dur >= 25): return 4

    # --- LEVEL 3 ---
    # 3a) 37-39, >25 days (S)
    if temp >= 38 and dur >= 25 and is_s: return 3
    # 3b) 39-41, 10-25 days (S) OR >25 days (N)
    if temp >= 40:
        if (is_s and dur >= 10) or (dur >= 25): return 3
    # 3c) >41, 5-10 days (S) OR 10-25 days (N)
    if temp >= 42:
        if (is_s and dur >= 5) or (dur >= 10): return 3

    # --- LEVEL 2 ---
    # 2a) 37-39, 10-25 days (S) OR >25 days (N)
    if temp >= 38:
        if (is_s and dur >= 10) or (dur >= 25): return 2
    # 2b) 39-41, 3-10 days (S) OR 5-25 days (N)
    if temp >= 40:
        if (is_s and dur >= 3) or (dur >= 5): return 2
    # 2c) >41, 3-10 days (N) OR 3-5 days (S)
    if temp >= 42:
        if (is_s and dur >= 3) or (dur >= 3): return 2

    # --- LEVEL 1 ---
    # 1a) 35-37, >3 days
    if temp >= 36 and dur >= 3: return 1
    # 1b) 37-39, 3-25 days (N) OR 3-10 days (S)
    if temp >= 38:
        if dur >= 3: return 1
    # 1c/d) >39, 3-5 days
    if temp >= 40 and dur >= 3: return 1
    
    return 0

# --- DROUGHT (Hạn hán) - Article 48 ---

# Water Shortage Patterns
SHORTAGE_20_50 = [r"20[-\s]50%", r"thiếu hụt nước", r"thiếu nước"] # Generic warning usually implies start of shortage
SHORTAGE_50_70 = [r"50[-\s]70%", r"trên 50%", r"hạn hán gay gắt"]
SHORTAGE_GT_70 = [r"trên 70%", r"cạn kiệt", r"mực nước chết", r"khô hạn khốc liệt", r"hạn hán đặc biệt gay gắt"]

# Duration (Months)
DR_DUR_2_3 = [r"2[-\s]3 tháng", r"kéo dài 2 tháng"]
DR_DUR_3_5 = [r"3[-\s]5 tháng", r"kéo dài 3 tháng", r"kéo dài 4 tháng"]
DR_DUR_GT_5 = [r"trên 5 tháng", r"5[-\s]6 tháng", r"nửa năm", r"dài ngày"] # Drought "dai ngay" usually means months

# Reuse Heat Regions (TN/NB vs BB/TB)
# HEAT_LOC_S (TN/NB) -> Higher Risk Sensitivity
# HEAT_LOC_N (BB/TB) -> Lower Risk Sensitivity

def check_drought_risk(text: str) -> int:
    """Article 48: Drought Risk"""
    t = text.lower()
    
    if not ("hạn hán" in t or "thiếu nước" in t or "khô hạn" in t or "xâm nhập mặn" in t):
        if "sạt lở" not in t and "sụt lún" not in t:
            return 0
        if "hạn hán" not in t: return 0

    # Check Shortage Bucket
    short = 0
    if has_any(t, SHORTAGE_GT_70): short = 75
    elif has_any(t, SHORTAGE_50_70): short = 60
    elif has_any(t, SHORTAGE_20_50): short = 35
    
    if short == 0: return 0

    # Check Duration
    dur_mo = 1
    if has_any(t, DR_DUR_GT_5): dur_mo = 6
    elif has_any(t, DR_DUR_3_5): dur_mo = 4
    elif has_any(t, DR_DUR_2_3) or "kéo dài" in t: dur_mo = 2
    
    # Check Region
    is_s = has_any(t, HEAT_LOC_S) # TN/NB
    # is_n = has_any(t, HEAT_LOC_N) # BB/TB

    # --- LEVEL 4 ---
    # 4a) Short >70%, >3 mo (All)
    if short >= 75 and dur_mo >= 4: return 4
    # 4b) Short 50-70%, >5 mo (S)
    if short >= 60 and dur_mo >= 6 and is_s: return 4

    # --- LEVEL 3 ---
    # 3a) Short >70%, 2-3 mo (All)
    if short >= 75 and dur_mo >= 2: return 3
    # 3b) Short 50-70%, 3-5 mo (S) OR >5 mo (N - clause 3c covers N >5mo wait. 
    # 3c says Short 50-70%, >5mo (N) -> Level 3.
    # 3b says Short 50-70%, 3-5mo (S) -> Level 3.
    if short >= 60:
        if (is_s and dur_mo >= 4) or (dur_mo >= 6): return 3
    # 3d) Short 20-50%, >5 mo (S)
    if short >= 35 and dur_mo >= 6 and is_s: return 3

    # --- LEVEL 2 ---
    # 2a) Short 50-70%, 2-3 mo (S)
    if short >= 60 and dur_mo >= 2 and is_s: return 2
    # 2b) Short 20-50%, 3-5 mo (S)
    if short >= 35 and dur_mo >= 4 and is_s: return 2
    # 2c) Short 50-70%, 3-5 mo (N - wait clause 2c says 3-5mo 50-70% BB -> L2)
    if short >= 60:
       # N (BB) 3-5 mo -> L2 (2c)
       if (not is_s and dur_mo >= 4): return 2
       # S/C 2-3 mo -> L2 (2a)
       if dur_mo >= 2: return 2 
       
    # 2d) Short 20-50%, >5 mo (N/C - clause 2d says BB, TB -> L2)
    if short >= 35 and dur_mo >= 6 and (not is_s): return 2

    # --- LEVEL 1 ---
    # Generic default 1 is reasonable if "Hạn hán" keywords present.
    return 1

# --- SALINE INTRUSION (Xâm nhập mặn) - Article 49 ---

# Salinity
SALT_1 = [r"1\s*g/l", r"1\s*gam", r"1\s*phần nghìn", r"1‰"]
SALT_4 = [r"4\s*g/l", r"4\s*gam", r"4\s*phần nghìn", r"4‰", r"mặn 4"] # "mặn 4" shorthand

# Intrusion Depth
# Looking for phrases "sâu X km", "vào X km"
DP_15_25 = [r"15[-\s]25\s*km", r"20\s*km"]
DP_25_50 = [r"25[-\s]50\s*km", r"30\s*km", r"40\s*km"]
DP_50_90 = [r"50[-\s]90\s*km", r"60\s*km", r"70\s*km", r"80\s*km"]
DP_GT_90 = [r"trên 90\s*km", r"vượt 90\s*km", r"100\s*km", r"sâu vào nội đồng"]

# Regions
# North/NorthCentral (BB, BTB): Higher sensitivity in reg
SALT_LOC_N = ["bắc bộ", "bắc trung bộ", "thanh hóa", "nghệ an", "hà tĩnh", "quảng bình", "thái bình", "nam định"]
# Central/South (TTB, NTB, NB): Lower sensitivity (Delta)
SALT_LOC_S = ["nam bộ", "đồng bằng sông cửu long", "bến tre", "trà vinh", "sóc trăng", "bạc liêu", "cà mau", "kiên giang", "tiền giang", "hậu giang"] 

def check_saline_risk(text: str) -> int:
    """Article 49: Saline Intrusion"""
    t = text.lower()
    if "xâm nhập mặn" not in t and "độ mặn" not in t and "nhiễm mặn" not in t:
        return 0

    # Check Depth Bucket
    depth = 0
    if has_any(t, DP_GT_90): depth = 100
    elif has_any(t, DP_50_90): depth = 70
    elif has_any(t, DP_25_50): depth = 35
    elif has_any(t, DP_15_25): depth = 20
    
    if depth == 0: return 0
    
    # Check Salinity Value (Default to 4‰ context if unspecified but talking about impacts? 
    # Actually 1‰ affects drinking, 4‰ affects rice. Media focuses on 4‰ usually.
    # Let's check if 1‰ explicitly mentioned. Else assume 4‰ context if depth is significant?
    # Or strict: if 1‰ -> is_1. Else -> is_4.
    is_1 = has_any(t, SALT_1)
    is_4 = has_any(t, SALT_4) # or default?

    # Check Region
    is_n = has_any(t, SALT_LOC_N)
    # is_s = has_any(t, SALT_LOC_S) # default

    # --- LEVEL 4 ---
    # 4a) 4‰, 50-90km (North)
    if (is_4 or not is_1) and depth >= 70 and is_n: return 4
    # 4b) 4‰, >90km (All)
    if (is_4 or not is_1) and depth >= 100: return 4

    # --- LEVEL 3 ---
    # 3a) 1‰, >90km (All)
    if is_1 and depth >= 100: return 3
    # 3b) 4‰, 25-50km (North)
    if (is_4 or not is_1) and depth >= 35 and is_n: return 3
    # 3c) 4‰, 50-90km (South/Central)
    if (is_4 or not is_1) and depth >= 70: return 3 # (is_n check led to 4a, so this catches is_s)

    # --- LEVEL 2 ---
    # 2a) 1‰, 50-90km (All)
    if is_1 and depth >= 70: return 2
    # 2b) 4‰, 15-25km (North) (Reg says 15-25 BB/BTB -> L2)
    if (is_4 or not is_1) and depth >= 20 and is_n: return 2
    # 2b) 4‰, 25-50km (South) 
    if (is_4 or not is_1) and depth >= 35: return 2 # (is_n check led to 3b, so this catches is_s)

    # --- LEVEL 1 ---
    # 1a) 1‰, 25-50km (All)
    if is_1 and depth >= 35: return 1
    # 1b) 4‰, 15-25km (Central South - prompt says TTB, NTB. NB is in Risk 2 for 25-50. 
    # What about NB 15-25? Not explicitly L2. Assume L1 or L2?
    # Safe to map 15-25 to L1 generally for South?
    if (is_4 or not is_1) and depth >= 20: return 1

    return 0

# --- STRONG WIND AT SEA (Gió mạnh trên biển) - Article 50 ---
# Wind Levels
LEVEL_6 = [r"cấp 6"]
LEVEL_7_8 = [r"cấp 7", r"cấp 8"]
LEVEL_9_UP = [r"cấp 9", r"cấp 10", r"cấp 11", r"cấp 12"] # 9+

def check_strong_wind_risk(text: str) -> int:
    """Article 50: Strong Wind at Sea"""
    t = text.lower()
    if "gió mạnh" not in t: return 0
    
    # Check Wind Level
    lv = 0
    if has_any(t, LEVEL_9_UP) or has_any(t, LEVEL_12_13) or has_any(t, LEVEL_14_15): lv = 9
    elif has_any(t, LEVEL_7_8): lv = 7
    elif has_any(t, LEVEL_6): lv = 6
    
    if lv == 0: return 0

    # Locations: LOC_VENBO, LOC_BIENDONG (Offshore)
    # Default to Offshore if not specified? Or Ven Bo?
    # Usually "Gió mạnh trên biển" implies offshore/biendong.
    is_venbo = has_any(t, LOC_VENBO)
    is_offshore = has_any(t, LOC_BIENDONG) or "ngoài khơi" in t or "đảo" in t or not is_venbo # Default to offshore if purely 'sea wind'
    
    # --- LEVEL 3 ---
    # 2a) >= Level 7, Ven Bo
    if lv >= 7 and is_venbo: return 3
    # 2b) >= Level 9, Offshore
    if lv >= 9 and is_offshore: return 3
    
    # --- LEVEL 2 ---
    # 1a) Level 6, Ven Bo
    if lv == 6 and is_venbo: return 2
    # 1b) Level 7-8, Offshore
    if lv >= 7 and is_offshore: return 2
    
    return 0

# --- FOG (Sương mù) - Article 51 ---
VIS_LT_50 = [r"dưới 50\s*m", r"< 50\s*m"]
VIS_GT_50 = [r"từ 50\s*m", r"trên 50\s*m", r"> 50\s*m"]
LOC_HIGHWAY_AIRPORT = ["cao tốc", "sân bay", "cảng hàng không"]
LOC_SEA_RIVER_PASS = ["trên biển", "trên sông", "đèo", "núi"]

def check_fog_risk(text: str) -> int:
    """Article 51: Fog"""
    t = text.lower()
    if "sương mù" not in t: return 0
    
    is_dense = "dày đặc" in t
    # If not dense, usually no risk warning? Reg says "Cảnh báo sương mù dày đặc".
    if not is_dense and not has_any(t, VIS_LT_50): return 0 

    is_lt_50 = has_any(t, VIS_LT_50)
    is_critical_loc = has_any(t, LOC_HIGHWAY_AIRPORT)
    
    # --- LEVEL 2 ---
    # Warning dense fog, <50m, Highway/Airport
    if is_lt_50 and is_critical_loc: return 2
    
    # --- LEVEL 1 ---
    # 1a) Dense, >50m, Highway/Airport
    if not is_lt_50 and is_critical_loc: return 1
    # 1b) Dense, <50m, Sea/River/Pass (or default location)
    if is_lt_50: return 1
    
    # Default Level 1 if "Dense Fog" explicitly warned without distance?
    return 1 if is_dense else 0

# --- LỐC, SÉT, MƯA ĐÁ (Tornado, Lightning, Hail) - Article 52 ---
SCOPE_WIDE = ["diện rộng", "hàng loạt", "nhiều nơi", "trên phạm vi toàn tỉnh"]

def check_extreme_other_risk(text: str) -> int:
    """Article 52: Tornado, Lightning, Hail"""
    t = text.lower()
    # Keywords check by caller or here
    keywords = ["lốc", "sét", "mưa đá"]
    if not any(k in t for k in keywords): return 0
    
    # --- LEVEL 2 ---
    # > 1/2 province (Wide scope)
    if has_any(t, SCOPE_WIDE): return 2
    
    # --- LEVEL 1 ---
    # < 1/2 province (Local/Default)
    # < 1/2 province (Local/Default)
    return 1

# --- COLD / FROST (Rét hại, Sương muối) - Article 53 ---

# Temp Ranges (Avg Daily)
COLD_LT_0 = [r"dưới 0\s*độ", r"âm\s*\d+\s*độ", r"-\d+\s*độ", r"sương muối", r"băng giá"] # <0Implies severe
COLD_0_4 = [r"0[-\s]4\s*độ", r"dưới 4\s*độ"]
COLD_4_8 = [r"4[-\s]8\s*độ", r"dưới 8\s*độ"]
COLD_8_13 = [r"8[-\s]13\s*độ", r"dưới 13\s*độ"]

# Duration
CD_DUR_3_5 = [r"3[-\s]5 ngày", r"trên 3 ngày"]
CD_DUR_5_10 = [r"5[-\s]10 ngày", r"trên 5 ngày"]
CD_DUR_GT_10 = [r"trên 10 ngày", r"dài ngày"]

# Regions
# Plains (DB): Dong Bang, Bac Trung Bo, Trung Trung Bo
COLD_LOC_DB = ["đồng bằng", "hà nội", "thanh hóa", "nghệ an", "hà tĩnh", "quảng bình", "thừa thiên huế", "bắc trung bộ", "trung trung bộ"]
# Mountains (MN): Vung Nui, Trung Du Bac Bo
COLD_LOC_MN = ["vùng núi", "trung du", "lạng sơn", "cao bằng", "hà giang", "lào cai", "yên bái", "sapa", "mẫu sơn", "đỉnh núi"]

def check_cold_risk(text: str) -> int:
    """Article 53: Cold/Frost Risk"""
    t = text.lower()
    if "rét" not in t and "sương muối" not in t and "băng giá" not in t and "lạnh" not in t:
        return 0

    # Determine Temp Bucket
    temp = 100
    if has_any(t, COLD_LT_0): temp = -1
    elif has_any(t, COLD_0_4): temp = 3
    elif has_any(t, COLD_4_8): temp = 7
    elif has_any(t, COLD_8_13) or "rét hại" in t: temp = 12 # Rét hại implies <13 (actually <13 is ret hai definition)
    
    if temp == 100: return 0

    # Determine Duration Bucket
    dur = 1
    if has_any(t, CD_DUR_GT_10): dur = 11
    elif has_any(t, CD_DUR_5_10): dur = 6
    elif has_any(t, CD_DUR_3_5) or "đợt rét" in t: dur = 4

    # Determine Region
    is_mn = has_any(t, COLD_LOC_MN) or "vùng núi" in t
    # is_db = has_any(t, COLD_LOC_DB) # default otherwise
    
    # --- LEVEL 3 ---
    # 3a) <=8C, >10d (DB)
    if temp <= 8 and dur >= 10 and not is_mn: return 3
    # 3b) <=4C, >10d (MN)
    if temp <= 4 and dur >= 10 and is_mn: return 3
    # 3c) <0C, 5-10d or >10d (MN)
    if temp <= -1 and dur >= 5 and is_mn: return 3

    # --- LEVEL 2 ---
    # 2a) 8-13C, >10d (DB)
    if temp <= 13 and dur >= 10 and not is_mn: return 2
    # 2b) 4-8C, >10d (MN)
    if temp <= 8 and dur >= 10 and is_mn: return 2
    # 2c) <=8C, 5-10d (DB)
    if temp <= 8 and dur >= 5 and not is_mn: return 2
    # 2d) 0-4C, 5-10d (MN)
    if temp <= 4 and dur >= 5 and is_mn: return 2
    # 2e) <0C, 3-5d (MN)
    if temp <= -1 and dur >= 3 and is_mn: return 2

    # --- LEVEL 1 ---
    # 1a) 8-13C, 3-5d or 5-10d (Only >5d mentioned in 1a for DB? 1a says >5 to 10. And >10d MN?)
    # 1a part 1: 8-13, 5-10d (DB)
    if temp <= 13 and dur >= 5 and not is_mn: return 1
    # 1a part 2: 8-13, >10d (MN)
    if temp <= 13 and dur >= 10 and is_mn: return 1
    # 1b) 4-8C, 5-10d (MN)
    if temp <= 8 and dur >= 5 and is_mn: return 1
    # 1c) 0-4C, 3-5d (MN)
    if temp <= 4 and dur >= 3 and is_mn: return 1
    # 1d) <=8C, 3-5d (DB)
    if temp <= 8 and dur >= 3 and not is_mn: return 1
    
    return 0

# --- WILDFIRE (Cháy rừng) - Article 54 ---

# Forest Zones (Based on Flammability)
# Zone 4 (Highest): Pine, Melaleuca (Tram), Dipterocarp (Khop), Bamboo (Tre/Nua), Eucalyptus (Bach dan)
# Locations: Tay Nguyen, U Minh, Da Lat, Northwest (Pine)
FIRE_Z4 = [r"rừng thông", r"rừng tràm", r"rừng khộp", r"rừng tre", r"rừng nứa", r"bạch đàn", r"u minh", "tây nguyên", "đà lạt"]
# Zone 3: Native Evergreen
FIRE_Z3 = [r"rừng tự nhiên", r"rừng mỡ", r"bồ đề"]
# Zone 2: Coastal/Evergreen
FIRE_Z2 = [r"rừng phi lao", r"rừng chắn cát", r"rừng ven biển"]
# Zone 1 (Lowest): Mangrove
FIRE_Z1 = [r"rừng ngập mặn", "cần giờ", "cà mau"]

# Explicit Levels (Often reported as "Cấp IV", "Cấp V")
FIRE_LV_5 = [r"cấp v", r"cấp 5", r"cực kỳ nguy hiểm"]
FIRE_LV_4 = [r"cấp iv", r"cấp 4", r"nguy hiểm"]
FIRE_LV_3 = [r"cấp iii", r"cấp 3", r"cao"]

def check_wildfire_risk(text: str) -> int:
    """Article 54: Wildfire Risk"""
    t = text.lower()
    if "cháy rừng" not in t: return 0

    # 1. Explicit Level Check (Highest Confidence)
    if has_any(t, FIRE_LV_5): return 5
    if has_any(t, FIRE_LV_4): return 4 # "Nguy hiểm" can be generic word, but with "cấp 4" it's solid.
    if has_any(t, FIRE_LV_3): return 3

    # 2. Inference
    # Needs Temp > 35 (Nắng nóng)
    if not ("nắng nóng" in t or "35" in t or "37" in t): return 0

    # Duration Est
    dur = 1
    if "trên 1 tháng" in t or "35 ngày" in t: dur = 36
    elif has_any(t, HEAT_DUR_25): dur = 26
    elif has_any(t, HEAT_DUR_10): dur = 11  
    
    # Zone Est
    is_z4 = has_any(t, FIRE_Z4)
    is_z3 = has_any(t, FIRE_Z3)
    
    # --- LEVEL 5 ---
    # >35C, >35 days, Z4
    if dur >= 36 and is_z4: return 5
    
    # --- LEVEL 4 ---
    # >35C, >35 days, Z3
    if dur >= 36 and is_z3: return 4
    # >35C, >25 days, Z4
    if dur >= 26 and is_z4: return 4
    
    # --- LEVEL 3 ---
    # Infers <25 days in Z4? 
    # Reg says "not exceed 25 days" for L3 Z4.
    # So if 10-25 days in Z4 -> likely L3.
    if dur >= 11 and is_z4: return 3
    
    # Default Level 1 if just "Nắng nóng + Cháy rừng"?
    if is_z4: return 1 # At least 1 for Z4 if hot

    return 0

# --- EARTHQUAKE (Động đất) - Article 55 ---
# Factors: Intensity (Cap chan dong) or Magnitude (Richter proxy), Location (Dam/Urban)

# Intensity Patterns
INT_V_VI = [r"cấp v", r"cấp vi", r"cấp 5", r"cấp 6"] # Intensity V-VI
INT_VI_VII = [r"cấp vi", r"cấp vii", r"cấp 6", r"cấp 7"]
INT_VII_VIII = [r"cấp vii", r"cấp viii", r"cấp 7", r"cấp 8"]
INT_GT_VIII = [r"cấp ix", r"cấp x", r"cấp 9", r"cấp 10", r"trên cấp 8"]

# Richter Proxy (Approx)
M_3_4 = [r"3\.\d\s*độ richter", r"4\.\d\s*độ richter"] # ~ V-VI
M_4_5 = [r"4\.\d\s*độ richter", r"5\.\d\s*độ richter"] # ~ VI-VII
M_5_6 = [r"5\.\d\s*độ richter", r"6\.\d\s*độ richter"] # ~ VII-VIII
M_GT_6 = [r"6\.\d\s*độ richter", r"7\.\d\s*độ richter"] # ~ VIII+

# Locations
LOC_DAM = [r"thủy điện", r"hồ chứa", r"đập"]
LOC_URBAN = [r"thành phố", r"đô thị", r"khu dân cư"]

def check_quake_risk(text: str) -> int:
    """Article 55: Earthquake Risk"""
    t = text.lower()
    if "động đất" not in t and "chấn động" not in t and "rung lắc" not in t:
        return 0

    # Determine Intensity / Magnitude Bucket (Max wins)
    # Using simple heuristic mapping: 
    # Lev 4 (VIII+ / M>6)
    # Lev 3 (VII-VIII / M 5-6)
    # Lev 2 (VI-VII / M 4-5)
    # Lev 1 (V-VI / M 3-4)
    
    tier = 0
    if has_any(t, INT_GT_VIII) or has_any(t, M_GT_6): tier = 4
    elif has_any(t, INT_VII_VIII) or has_any(t, M_5_6): tier = 3
    elif has_any(t, INT_VI_VII) or has_any(t, M_4_5): tier = 2
    elif has_any(t, INT_V_VI) or has_any(t, M_3_4): tier = 1
    
    # Check Location Context
    is_dam = has_any(t, LOC_DAM)
    is_urban = has_any(t, LOC_URBAN)

    # --- LEVEL 5 ---
    # Intensity > VIII (Tier 4) Anywhere
    if tier >= 4: return 5

    # --- LEVEL 4 ---
    # VII-VIII (Tier 3) + Urban/Dam
    if tier == 3 and (is_urban or is_dam): return 4
    
    # --- LEVEL 3 ---
    # VI-VII (Tier 2) + Dam
    if tier == 2 and is_dam: return 3
    # VII-VIII (Tier 3) + Rural (Default)
    if tier == 3: return 3

    # --- LEVEL 2 ---
    # VI-VII (Tier 2) Any
    if tier >= 2: return 2
    
    # --- LEVEL 1 ---
    # V-VI (Tier 1) Any
    if tier >= 1: return 1

    return 0

# --- TSUNAMI (Sóng thần) - Article 56 ---
# Wave Height
TSU_H_GT_16 = [r"trên 16\s*m", r"cao 20\s*m"]
TSU_H_8_16 = [r"8[-\s]16\s*m", r"8\s*m", r"10\s*m"]
TSU_H_4_8 = [r"4[-\s]8\s*m", r"4\s*m", r"5\s*m", r"6\s*m"]
TSU_H_2_4 = [r"2[-\s]4\s*m", r"2\s*m", r"3\s*m"]
TSU_H_LT_2 = [r"dưới 2\s*m", r"1\s*m", r"0,5\s*m"]

def check_tsunami_risk(text: str) -> int:
    """Article 56: Tsunami Risk"""
    t = text.lower()
    if "sóng thần" not in t: return 0

    # Determine Height Bucket
    h_tier = 0
    if has_any(t, TSU_H_GT_16): h_tier = 5
    elif has_any(t, TSU_H_8_16): h_tier = 4
    elif has_any(t, TSU_H_4_8): h_tier = 3
    elif has_any(t, TSU_H_2_4): h_tier = 2
    elif has_any(t, TSU_H_LT_2): h_tier = 1
    
    # Logic Map directly
    if h_tier == 5: return 5
    if h_tier == 4: return 4
    if h_tier == 3: return 3
    if h_tier == 2: return 2
    if h_tier == 1: return 1
    
    return 0
