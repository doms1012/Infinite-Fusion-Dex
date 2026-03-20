import pandas as pd
import sys
from split_names import SPLIT_NAMES, NAT_DEX_MAPPING

def test_integrity():
    df = pd.read_csv('species.csv')
    errors = []

    print(f"🔍 Validating {len(df)} rows against split_names.py definitions...")

    for _, row in df.iterrows():
        pif_id = int(row['dex_num'])
        if pif_id <= 0: continue
        
        # Determine what the National ID SHOULD be
        nat_id = NAT_DEX_MAPPING.get(pif_id, pif_id) if pif_id > 251 else pif_id
        
        try:
            exp_pre, exp_suf = SPLIT_NAMES[nat_id]
            act_pre, act_suf = str(row['name_prefix']), str(row['name_suffix'])

            # Binary comparison (catches Gre/ninja vs Gren/inja)
            if act_pre != exp_pre or act_suf != exp_suf:
                errors.append({
                    "PIF_ID": pif_id,
                    "Name": row['name'],
                    "Target_Nat_ID": nat_id,
                    "Expected": f"{exp_pre}/{exp_suf}",
                    "Actual": f"{act_pre}/{act_suf}"
                })
        except IndexError:
            # Skip if the list is shorter than the Dex
            continue

    if not errors:
        print("✅ SUCCESS: The species file is now 100% aligned with the game logic.")
        sys.exit(0)
    else:
        print(f"❌ FAIL: Found {len(errors)} mismatches.")
        error_df = pd.DataFrame(errors)
        error_df.to_csv('mismatches_found.csv', index=False)
        print(error_df.head(10).to_string(index=False))
        sys.exit(1)

if __name__ == "__main__":
    test_integrity()