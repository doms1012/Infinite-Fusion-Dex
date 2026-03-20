import pandas as pd
import re
import sys
import os

def parse_ruby_splits(content):
    splits = {}
    # Look for the 'case' or 'when' lines specifically
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('when'):
            continue
        
        # 1. Extract the Number after 'when'
        id_match = re.search(r'when\s+(\d+)', line)
        # 2. Extract the two strings inside [" ", " "]
        string_matches = re.findall(r'["\']([^"\']+)["\']', line)
        
        if id_match and len(string_matches) >= 2:
            splits[int(id_match.group(1))] = (string_matches[0], string_matches[1])
            
    return splits

def run_integrity_test():
    ruby_path = 'SplitNames.rb'
    csv_path = 'species.csv'

    with open(ruby_path, 'r', encoding='utf-8') as f:
        ruby_content = f.read()

    # 1. PARSE MAPPING
    mapping = {int(k): int(v) for k, v in re.findall(r'(\d+)\s*=>\s*(\d+)', ruby_content)}
    
    # 2. PARSE SPLITS
    name_splits = parse_ruby_splits(ruby_content)

    print(f"📊 SOURCE ANALYSIS (SplitNames.rb):")
    print(f"   - Found {len(mapping)} ID mappings.")
    print(f"   - Found {len(name_splits)} name-split definitions.")
    
    if len(name_splits) < 10:
        print("❌ ERROR: Parser failed to find the name list. Sample found:")
        print(list(name_splits.items())[:5])
        sys.exit(1)

    # 3. VALIDATE
    df = pd.read_csv(csv_path)
    errors = []

    for _, row in df.iterrows():
        pif_id = int(row['dex_num'])
        if pif_id <= 0: continue
        
        # Alignment Logic
        nat_id = mapping.get(pif_id, pif_id) if pif_id > 251 else pif_id
        
        expected = name_splits.get(nat_id)
        if not expected:
            errors.append({"ID": pif_id, "Name": row['name'], "Error": f"ID {nat_id} missing in Ruby", "Expected": "MISSING"})
            continue

        exp_pre, exp_suf = expected
        act_pre, act_suf = str(row['name_prefix']), str(row['name_suffix'])

        if act_pre != exp_pre or act_suf != exp_suf:
            errors.append({
                "ID": pif_id,
                "Name": row['name'],
                "Target_Nat_ID": nat_id,
                "Expected": f"{exp_pre}/{exp_suf}",
                "Actual": f"{act_pre}/{act_suf}",
                "Error": "Content Mismatch"
            })

    if not errors:
        print("✅ PASS: 100% Alignment.")
        sys.exit(0)
    else:
        print(f"❌ FAIL: Found {len(errors)} discrepancies.")
        error_df = pd.DataFrame(errors)
        error_df.to_csv('integrity_mismatches.csv', index=False)
        print(error_df[['ID', 'Name', 'Error', 'Target_Nat_ID', 'Expected', 'Actual']].head(10).to_string(index=False))


        sys.exit(1)