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
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATA & CACHING ---
@st.cache_data
def load_data():
    csv_url = "https://raw.githubusercontent.com/EarthBet/Fusion-Dex/main/fusionDex.csv"
    df = pd.read_csv(csv_url)
    # Clean up "Unnamed" columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    def clean_name(a): return str(a).strip().capitalize()
    df['nameHead'] = df['nameHead'].apply(clean_name)
    df['nameBody'] = df['nameBody'].apply(clean_name)
    df['type1'] = df['type1'].apply(clean_name)
    df['type2'] = df['type2'].apply(clean_name)
    return df

try:
    df_original = load_data()
    all_mons = sorted(list(set(df_original['nameHead'].unique()) | set(df_original['nameBody'].unique())))
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- 2. SIDEBAR / BOX MANAGER ---
st.sidebar.title("📦 Box Manager")
st.sidebar.write("Select the Pokemon you currently own.")

# Use a multi-select for the box (much cleaner than the click-to-move in Streamlit)
if 'my_box' not in st.session_state:
    st.session_state.my_box = []

selected_mons = st.sidebar.multiselect(
    "Search and Add Pokemon:",
    options=all_mons,
    default=st.session_state.my_box,
    help="Type to search for Pokemon names"
)
st.session_state.my_box = selected_mons

# --- 3. MAIN UI ---
st.title("🧬 Pokemon Fusion Sorter")

st.markdown("#### ⚙️ Sorting & Filtering")
# Filters and Sort Options in columns
col1, col2, col3 = st.columns(3)

with col1:
    sort_options = {
        'base_total': 'Total Stats',
        'base_hp': 'HP',
        'base_atk': 'Attack',
        'base_def': 'Defense',
        'base_spa': 'Special Attack',
        'base_spd': 'Special Defense',
        'base_spe': 'Speed'
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
def get_sprite_url(name):
    fmt = name.lower().replace(' ', '-').replace('.', '').replace("'", "")
    return f"https://img.pokemondb.net/sprites/home/normal/{fmt}.png"

# We use Streamlit's native dataframe display with image support
results_df = temp_df.head(50).copy()

# Formatting for display
friendly_names = {
    'nameHead': 'Head Name',
    'nameBody': 'Body Name',
    'type1': 'Type 1',
    'type2': 'Type 2',
    'base_total': 'Total',
    'base_hp': 'HP',
    'base_atk': 'Attack',
    'base_def': 'Defense',
    'base_spa': 'Special Attack',
    'base_spd': 'Special Defense',
    'base_spe': 'Speed'
}

# Add sprite URL columns for Streamlit to render
results_df['Head Sprite'] = results_df['nameHead'].apply(get_sprite_url)
results_df['Body Sprite'] = results_df['nameBody'].apply(get_sprite_url)

# Reorder columns to put sprites next to names and Dex ID first
# (Assuming 'informal_dex' exists, adjust if named differently)
dex_col = 'informal_dex' if 'informal_dex' in results_df.columns else results_df.columns[0]

final_cols = [dex_col, 'Head Sprite', 'nameHead', 'Body Sprite', 'nameBody', 'type1', 'type2'] + \
             [c for c in available_sort_cols if c not in ['nameHead', 'nameBody']]

results_df = results_df[final_cols].rename(columns=friendly_names)

# Render the table
st.dataframe(
    results_df,
    column_config={
        "Head Sprite": st.column_config.ImageColumn(" ", width="small"),
        "Body Sprite": st.column_config.ImageColumn(" ", width="small"),
    },
    hide_index=True,
    use_container_width=True
)

st.write(f"Showing {len(results_df)} of {len(temp_df)} matches.")