import re
import csv
import os

def parse_split_names(rb_path):
    with open(rb_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to find the SPLIT_NAMES array pairs: ["Prefix", "Suffix"]
    pattern = r'\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
    matches = re.findall(pattern, content)
    
    # Create a mapping where index matches the game's internal ID
    # Index 0 is typically empty in the Ruby file
    return {i: {"pre": m[0], "suf": m[1]} for i, m in enumerate(matches)}

def update_species_csv(csv_path, name_map):
    # Read existing data
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        # Add columns if they don't exist
        if 'name_prefix' not in fieldnames:
            fieldnames += ['name_prefix', 'name_suffix']
        rows = list(reader)

    # Write back to the same file
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            # Match dex_num to the index in the SplitNames array
            dex_id = int(row['dex_num'])
            if dex_id in name_map:
                row['name_prefix'] = name_map[dex_id]['pre']
                row['name_suffix'] = name_map[dex_id]['suf']
            else:
                row['name_prefix'] = row['name'][:4] # Fallback
                row['name_suffix'] = row['name'][4:] # Fallback
            writer.writerow(row)

if __name__ == "__main__":
    if os.path.exists('SplitNames.rb') and os.path.exists('species.csv'):
        names = parse_split_names('SplitNames.rb')
        update_species_csv('species.csv', names)
        print(f"Successfully updated species.csv with {len(names)} name pairs.")
    else:
        print("Error: Ensure both SplitNames.rb and species.csv are in this folder.")