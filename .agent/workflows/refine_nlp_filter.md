
# Workflow: Refine NLP for Automated Disaster News Approval
# Objective: Tune veto logic and scoring to auto-approve (Score > 15) legitimate disaster news.

1. **Analyze Logs**: Identify false positives (vetoed valid news) and low-scoring valid news.
2. **Modify `nlp.py`**:
   - Update `ABSOLUTE_VETO` regexes to add exceptions for:
     - International Veto (`Nga`, `Ukraine`...): Allow if `(cứu\s*trợ|hỗ\s*trợ).*việt\s*nam`.
     - Tech Veto (if found): Allow if context is rescue/relief.
     - Construction Veto: Allow `khánh thành`, `khởi công` if `vùng bão`, `vùng lũ`, `thiên tai`.
   - Update `is_valid_disaster_news` (VIP Whitelist) to boost scores for:
     - `cứu trợ`, `tiếp tế`, `hàng cứu trợ`.
     - `khắc phục hậu quả` (already added, maybe refine).
3. **Modify `sources.py`**:
   - Add "Relief/Rescue" keywords to `HIGH_PRIORITY_KEYWORDS` to boost base score.
4. **Rescan/Test**: Verify changes with new logs or dry run.
