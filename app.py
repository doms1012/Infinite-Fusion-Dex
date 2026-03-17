import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(page_title="Pokemon Fusion Sorter", layout="wide", initial_sidebar_state="expanded")

# --- 0. CUSTOM STYLING ---
st.markdown("""
<style>
    /* Gradient Title */
    h1 {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #3b82f6, #9333ea);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        padding-bottom: 0.5rem;
    }
    
    /* Dataframe rounded corners and shadow */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(156, 163, 175, 0.2);
    }
    
    /* Reduce top padding for a sleeker look */
    .block-container {
        padding-top: 2rem !important;
    }
    
    /* Sidebar Box & Overlay X Button */
    [data-testid="stSidebar"] .stButton {
        display: flex;
        justify-content: flex-end;
        margin-bottom: -20px; /* Pulls the image up underneath the button */
        position: relative;
        z-index: 10;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button {
        background-color: rgba(239, 68, 68, 0.8) !important;
        color: white !important;
        border-radius: 50% !important;
        width: 18px !important;
        height: 18px !important;
        min-height: 18px !important;
        padding: 0 !important;
        font-size: 10px !important;
        line-height: 1 !important;
        border: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background-color: rgba(239, 68, 68, 1) !important;
    }
    [data-testid="stSidebar"] [data-testid="column"] {
        padding: 0 2px !important; /* Tighter 5-column grid spacing */
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATA & CACHING ---
@st.cache_data
def load_data():
    csv_url = "https://raw.githubusercontent.com/EarthBet/Fusion-Dex/main/fusionDex.csv"
    # Force informalDex to string so "1.10" doesn't get parsed as "1.1"
    df = pd.read_csv(csv_url, dtype={'informalDex': str})
    # Clean up "Unnamed" columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    def clean_name(a): return str(a).strip().capitalize()
    df['nameHead'] = df['nameHead'].apply(clean_name)
    df['nameBody'] = df['nameBody'].apply(clean_name)
    df['type1'] = df['type1'].apply(clean_name)
    df['type2'] = df['type2'].apply(clean_name)
    
    # Generate true idHead and idBody from informalDex and names
    if 'informalDex' in df.columns and 'idHead' not in df.columns:
        # Extract potential head and body IDs (handles formats like "1.4" or "1_4")
        ids = df['informalDex'].astype(str).str.extract(r'(\d+)[^\d]+(\d+)')
        single_ids = df['informalDex'].astype(str).str.extract(r'(\d+)')[0]
        
        # Build a reliable Name -> Base ID mapping dictionary
        dex_map = {}
        for name, head_id in zip(df['nameHead'], single_ids):
            if pd.notna(head_id) and name not in dex_map:
                dex_map[name] = head_id
                
        for name, body_id in zip(df['nameBody'], ids[1]):
            if pd.notna(body_id) and name not in dex_map:
                dex_map[name] = body_id
                
        # Map the exact Base IDs back to the dataframe to prevent duplicate heads
        df['idHead'] = df['nameHead'].map(dex_map).fillna(single_ids)
        df['idBody'] = df['nameBody'].map(dex_map).fillna(df['idHead'])
        
    return df

try:
    df_original = load_data()
    all_mons = sorted(list(set(df_original['nameHead'].unique()) | set(df_original['nameBody'].unique())))
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

def find_id_column(df, keywords):
    for col in df.columns:
        # Normalize column names by removing spaces, underscores, and lowercasing
        clean_col = col.lower().replace(' ', '').replace('_', '')
        if clean_col in keywords:
            return col
    return None

head_keywords = ['idhead', 'headid', 'headdex', 'dexhead', 'id1', 'pokedex1', 'pokemon1id']
body_keywords = ['idbody', 'bodyid', 'bodydex', 'dexbody', 'id2', 'pokedex2', 'pokemon2id']

dex_head_col = find_id_column(df_original, head_keywords)
dex_body_col = find_id_column(df_original, body_keywords)

# Fallback error handling to show actual CSV column names if it fails
if not dex_head_col or not dex_body_col:
    st.error(f"**Error:** Could not automatically locate the ID columns.\n\n**Available CSV columns:** `{', '.join(df_original.columns)}`\n\nPlease check the exact header names in your CSV file and add them to `head_keywords` and `body_keywords` in `app.py`.")
    st.stop()

col_map = {'dex_head': dex_head_col, 'dex_body': dex_body_col}

def clean_id(val):
    """Cleans up float formatting and removes dataset suffixes like '-420'"""
    # Strip out any hyphens and the text after it (e.g., "17-420" -> "17")
    clean_val = str(val).split('-')[0].strip()
    try:
        return str(int(float(clean_val)))
    except (ValueError, TypeError):
        return clean_val

def get_base_sprite(dex_id):
    c_id = clean_id(dex_id)
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{c_id}.png"

def get_fusion_sprite(head_id, body_id):
    h, b = clean_id(head_id), clean_id(body_id)
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{h}.{b}.png"

# Create a mapping for Box Manager (Name -> Dex ID)
name_to_id = dict(zip(df_original['nameHead'], df_original[col_map['dex_head']]))

# --- 2. SIDEBAR / BOX MANAGER ---
st.sidebar.title("Box Manager")
st.sidebar.write("Select the Pokemon you currently own.")

# Use Streamlit's native 'key' parameter to bind directly to session state. This prevents stuttering/UI desync.
st.sidebar.multiselect(
    "Search and Add Pokemon:",
    options=all_mons,
    key="my_box",
    help="Type to search for Pokemon names"
)

def remove_from_box(mon):
    st.session_state.my_box.remove(mon)

# Display the organized box with sprites below
if st.session_state.my_box:
    st.sidebar.markdown("### 🗃️ Your Box")
    with st.sidebar.container(border=True):
        sorted_box = sorted(st.session_state.my_box)
        # 5x5 Grid pattern (rendered row by row)
        for i in range(0, len(sorted_box), 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(sorted_box):
                    mon = sorted_box[i + j]
                    with cols[j]:
                        st.button("✖", key=f"rm_{mon}", on_click=remove_from_box, args=(mon,), help=f"Remove {mon}")
                        dex_id = name_to_id.get(mon, 0)
                        st.image(get_base_sprite(dex_id), use_container_width=True)
                        st.markdown(f"<p style='text-align: center; font-size: 9px; margin-top: -5px; word-wrap: break-word; line-height: 1.1;'>{mon}</p>", unsafe_allow_html=True)

# --- 3. MAIN UI ---
st.title("Pokemon Fusion Sorter")

st.markdown("#### ⚙️ Sorting & Filtering")
# Filters and Sort Options in columns
col1, col2, col3 = st.columns(3)

with col1:
    sort_options = {
        'base_total': 'Total Stats',
        'hp': 'HP',
        'attack': 'Attack',
        'defense': 'Defense',
        'sp_attack': 'Special Attack',
        'sp_defense': 'Special Defense',
        'speed': 'Speed'
    }
    # Dynamic column mapping (handles different CSV versions)
    available_sort_cols = [c for c in sort_options.keys() if c in df_original.columns]
    sort_by_display = st.selectbox("Sort By:", options=available_sort_cols, format_func=lambda x: sort_options[x], index=0)

with col2:
    order = st.selectbox("Order:", options=["Descending", "Ascending"])

with col3:
    hide_self = st.checkbox("Hide Self-Fusions", value=True)

# --- 4. PROCESSING ---
temp_df = df_original.copy()

# Filter: Self Fusions
if hide_self:
    temp_df = temp_df[temp_df['nameHead'] != temp_df['nameBody']]

# Filter: Box (Only if box is not empty)
if st.session_state.my_box:
    temp_df = temp_df[temp_df['nameHead'].isin(st.session_state.my_box) & 
                       temp_df['nameBody'].isin(st.session_state.my_box)]
else:
    st.info("💡 Your box is empty. Showing all possible fusions. Use the sidebar to add Pokemon you own.")

# Apply Sorting
temp_df = temp_df.sort_values(by=sort_by_display, ascending=(order == "Ascending"))

# --- 5. DISPLAY RESULTS ---
# We use Streamlit's native dataframe display with image support
results_df = temp_df.head(50).copy()

# Formatting for display
friendly_names = {
    'nameHead': 'Head Name',
    'nameBody': 'Body Name',
    'type1': 'Type 1',
    'type2': 'Type 2',
    'base_total': 'Total',
    'hp': 'HP',
    'attack': 'Attack',
    'defense': 'Defense',
    'sp_attack': 'Special Attack',
    'sp_defense': 'Special Defense',
    'speed': 'Speed'
}

# Add sprite URL columns for Streamlit to render
results_df['Head Icon'] = results_df[col_map['dex_head']].apply(get_base_sprite)
results_df['Body Icon'] = results_df[col_map['dex_body']].apply(get_base_sprite)

# Generate Custom Fused Sprites
results_df['Fused Sprite'] = results_df.apply(lambda row: get_fusion_sprite(row[col_map['dex_head']], row[col_map['dex_body']]), axis=1)

# Reorder columns to put sprites next to names and Dex ID first
dex_col_candidates = [c for c in results_df.columns if c.lower() in ['informaldex', 'informal_dex']]
dex_col = dex_col_candidates[0] if dex_col_candidates else results_df.columns[0]

start_cols = [dex_col, 'Head Icon', 'nameHead', 'Body Icon', 'nameBody', 'Fused Sprite', 'type1', 'type2']

# Ensure ALL fields from the CSV are shown
remaining_cols = [c for c in results_df.columns if c not in start_cols]

final_cols = start_cols + remaining_cols

results_df = results_df[final_cols].rename(columns=friendly_names)

# Render the table
st.dataframe(
    results_df,
    column_config={
        "Head Icon": st.column_config.ImageColumn(" ", width="small"),
        "Body Icon": st.column_config.ImageColumn(" ", width="small"),
        "Fused Sprite": st.column_config.ImageColumn("Fusion", width="medium"),
    },
    hide_index=True,
    use_container_width=False
)

st.write(f"Showing {len(results_df)} of {len(temp_df)} matches.")