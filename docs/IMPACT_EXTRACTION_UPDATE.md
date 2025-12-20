# Expanded Impact Extraction Summary

## 1. NLP Module Updates (`backend/app/nlp.py`)

### New Categories in `IMPACT_KEYWORDS`
*   **`homes`**: Added specific keywords for housing damage:
    *   *sập nhà, tốc mái, ngập nhà, cuốn trôi, hư hỏng nhà...*
*   **`agriculture`**: Added keywords for crop/livestock loss:
    *   *hoa màu, lúa, ruộng, ha lúa, gia súc, gia cầm, trâu bò, lồng bè...*
*   **`marine`**: Added keywords for maritime incidents:
    *   *chìm tàu, đắm tàu, tàu cá, ngư dân...*

### Enhanced Extraction Logic (`_build_impact_patterns`)
Implemented specialized Regex patterns to extract unit-based metrics for the new categories:
*   **People** (Existing): Extracts numbers for deaths, missing, injured.
*   **Money** (Existing): Extracts financial damage (billion/million VND).
*   **Homes** (New): Extracts `NUMBER` + unit (*nhà, căn, hộ*) associated with damage keywords.
    *   *Example: "sập 10 căn nhà" -> `{"homes": [{"num": 10}]}`*
*   **Agriculture** (New): Extracts `NUMBER` + unit (*ha, tấn, con*) associated with agricultural keywords.
    *   *Example: "ngập 500ha lúa", "trôi 200 con gia cầm" -> `{"agriculture": [{"num": 500, "unit": "ha"}, {"num": 200, "unit": "con"}]}`*
*   **Marine** (New): Extracts `NUMBER` + unit (*tàu, thuyền, chiếc*) associated with marine keywords.
    *   *Example: "chìm 3 tàu cá" -> `{"marine": [{"num": 3}]}`*

## 2. Crawler & Database Updates

### Database Schema (`backend/app/models.py`)
*   Added `impact_details` column (Type: `JSON`) to the `articles` table.
*   Running `ALTER TABLE articles ADD COLUMN IF NOT EXISTS impact_details JSON` (handled via migration script/command).

### Crawler Logic (`backend/app/crawler.py`)
*   Modified `Article` creation to populate `impact_details` using `nlp.extract_impact_details()`.
*   This applies to both RSS feed processing and the HTML scraper fallback.

## 3. Usage
The system will now automatically populate the `impact_details` field in the database with structured JSON data (e.g., `{"agriculture": [{"num": 50, "unit": "ha"}]}`). This data allows for more granular reporting and UI display of disaster impacts beyond just human casualties.
