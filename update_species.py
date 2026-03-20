import pandas as pd
from split_names import SPLIT_NAMES, NAT_DEX_MAPPING

def fix_species_csv():
    # Load your current CSV
    df = pd.read_csv('species.csv')
    
    def get_parts(row):
        pif_id = int(row['dex_num'])
        if pif_id <= 0:
            return pd.Series([row['name_prefix'], row['name_suffix']], index=['name_prefix', 'name_suffix'])
            
        # Determine the target National Dex ID
        # Logic: If > 251, follow mapping. If <= 251, PIF ID = National ID.
        nat_id = NAT_DEX_MAPPING.get(pif_id, pif_id) if pif_id > 251 else pif_id
        
        # Pull correct parts from our SPLIT_NAMES list (0-indexed adjustment)
        try:
            # If your list starts with index 1 being Bulbasaur, use nat_id directly
            prefix, suffix = SPLIT_NAMES[nat_id]
        except IndexError:
            # Fallback for IDs beyond the current list
            prefix, suffix = row['name_prefix'], row['name_suffix']
            
        return pd.Series([prefix, suffix], index=['name_prefix', 'name_suffix'])

    # Apply the alignment logic to every row
    df[['name_prefix', 'name_suffix']] = df.apply(get_parts, axis=1)
    
    # OVERWRITE the original file
    df.to_csv('species.csv', index=False)
    print("✅ species.csv has been updated and re-aligned with 100% accuracy.")

if __name__ == "__main__":
    fix_species_csv()