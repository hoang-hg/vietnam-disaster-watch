import json
from collections import Counter

def find_duplicates():
    with open("sources.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    sources = data["sources"]
    
    # 1. Exact Domain Duplicates
    domains = [s["domain"].lower().strip() for s in sources]
    domain_counts = Counter(domains)
    dup_domains = [d for d, c in domain_counts.items() if c > 1]
    
    # 2. Exact Name Duplicates
    names = [s["name"].lower().strip() for s in sources]
    name_counts = Counter(names)
    dup_names = [n for n, c in name_counts.items() if c > 1]
    
    # 3. Similar Domains (e.g. bao.vn vs www.bao.vn)
    normalized_domains = []
    for d in domains:
        if d.startswith("www."):
            normalized_domains.append(d[4:])
        else:
            normalized_domains.append(d)
    
    norm_domain_counts = Counter(normalized_domains)
    dup_norm_domains = [d for d, c in norm_domain_counts.items() if c > 1]

    print(f"Total sources: {len(sources)}")
    if dup_domains:
        print("Duplicate Domains:", dup_domains)
    else:
        print("No exact duplicate domains.")
        
    if dup_names:
        print("Duplicate Names:", dup_names)
    else:
        print("No exact duplicate names.")
        
    if len(dup_norm_domains) > len(dup_domains):
        print("Potentially overlapping domains (e.g. with/without www):", set(dup_norm_domains) - set(dup_domains))

if __name__ == "__main__":
    find_duplicates()
