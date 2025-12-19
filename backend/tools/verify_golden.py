import sys
import json
import re
from pathlib import Path

# Setup Path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

try:
    from app import nlp
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def normalize_prov(name):
    """Normalize province name for comparison."""
    name = name.lower().replace("thành phố", "").replace("tỉnh", "").strip()
    name = name.replace("tp.", "").replace("t.p.", "").strip()
    name = name.replace("hcm", "hồ chí minh").replace("tphcm", "hồ chí minh")
    name = name.replace("hà nội", "hà nội") # no change
    return name

def run_verification():
    file_path = "backend/tools/golden_dataset_fixed.json"
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases = data.get("cases", [])
    except json.JSONDecodeError:
        print("Invalid JSON format.")
        return

    print(f"Verifying {len(cases)} cases from Golden Dataset...")
    
    metrics = {
        "decision": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "province": {"found": 0, "expected": 0},
        "impact": {"damage_acc": 0, "total": 0},
        "classification": {"correct": 0, "total": 0} # Only for TP
    }
    
    failures = []

    for case in cases:
        title = case["title"]
        content = case.get("content", "")
        # Normalize text: Title + Content
        full_text = f"{title}\n{content}"
        
        # Expected
        exp = case["expected"]
        exp_is_disaster = exp["is_disaster"]
        exp_hazards = set(exp.get("hazards", []))
        exp_provs = [normalize_prov(p) for p in exp.get("provinces", [])]
        exp_impact = exp.get("impacts", {})

        # Actual Run
        # 1. Decision
        act_is_disaster = nlp.contains_disaster_keywords(full_text, trusted_source=False)
        
        # Decision Metric
        if exp_is_disaster:
            if act_is_disaster:
                metrics["decision"]["tp"] += 1
                
                # Check Classification (Only if TP)
                cls_res = nlp.classify_disaster(full_text)
                act_primary = cls_res["primary_type"]
                
                # Check if act_primary is in expected_hazards OR matches logic
                # Golden dataset hazards might be list e.g. ["storm"].
                if act_primary in exp_hazards:
                    metrics["classification"]["correct"] += 1
                else:
                    # Mismatch
                    failures.append(f"[Class] {case['id']}: Exp {exp_hazards}, Act {act_primary}")
                
                metrics["classification"]["total"] += 1
                
            else:
                metrics["decision"]["fn"] += 1
                failures.append(f"[FN] {case['id']}: Exp True, Act False ('{title}')")
        else:
            if act_is_disaster:
                metrics["decision"]["fp"] += 1
                failures.append(f"[FP] {case['id']}: Exp False, Act True ('{title}')")
            else:
                metrics["decision"]["tn"] += 1
        
        # 2. Extraction (Provinces)
        # Using extraction based on full text
        extracted_provs = nlp.extract_provinces(full_text)
        act_prov_names = [normalize_prov(p["name"]) for p in extracted_provs]
        
        # Recall Check
        for ep in exp_provs:
            # Flexible match
            if any(ep in ap or ap in ep for ap in act_prov_names):
                metrics["province"]["found"] += 1
        metrics["province"]["expected"] += len(exp_provs)
        
        # 3. Impact Extraction (Check Damage Hit)
        # Using compute_disaster_signals
        sig = nlp.compute_disaster_signals(full_text)
        act_damage = bool(sig["impact_hits"])
        exp_damage = exp_impact.get("damage_hit", False)
        
        # Just simple diff? Or detailed? Use simple acc for now.
        if act_damage == exp_damage:
            metrics["impact"]["damage_acc"] += 1
        metrics["impact"]["total"] += 1

    # Report
    dec = metrics["decision"]
    total_dec = sum(dec.values())
    acc = (dec["tp"] + dec["tn"]) / total_dec * 100 if total_dec else 0
    fpr = dec["fp"] / (dec["fp"] + dec["tn"]) * 100 if (dec["fp"] + dec["tn"]) else 0
    fnr = dec["fn"] / (dec["fn"] + dec["tp"]) * 100 if (dec["fn"] + dec["tp"]) else 0
    
    prov_recall = metrics["province"]["found"] / metrics["province"]["expected"] * 100 if metrics["province"]["expected"] else 0
    
    cls_acc = metrics["classification"]["correct"] / metrics["classification"]["total"] * 100 if metrics["classification"]["total"] else 0
    
    print("\n=== VERIFICATION REPORT ===")
    print(f"Cases: {len(cases)}")
    print(f"1. Decision Accuracy: {acc:.2f}% (TP={dec['tp']}, TN={dec['tn']}, FP={dec['fp']}, FN={dec['fn']})")
    print(f"   - FP Rate: {fpr:.2f}% (Target < 3%)")
    print(f"   - FN Rate: {fnr:.2f}% (Target < 10%)")
    print(f"2. Province Recall:   {prov_recall:.2f}% ({metrics['province']['found']}/{metrics['province']['expected']})")
    print(f"3. Classification Acc:{cls_acc:.2f}%")
    
    if failures:
        print("\n[Failures Sample]:")
        for f in failures[:15]:
            print(f)

if __name__ == "__main__":
    run_verification()
