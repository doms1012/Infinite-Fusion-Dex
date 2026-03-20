import streamlit as st
import pandas as pd
import math
import itertools

# Set page configuration
st.set_page_config(page_title="Pokemon Fusion Sorter", layout="wide", initial_sidebar_state="expanded")

# --- 0. STYLE (THE STABLE FONT FIX) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;700&display=swap');

    /* Target specific content containers only to protect UI icons */
    h1, h2, h3, .stSubheader, .stat-label, [data-testid="stDataFrame"] * {
        font-family: 'Oswald', sans-serif !important;
    }

    h1 {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #3b82f6, #9333ea);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    [data-testid="stDataFrame"] {
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(156, 163, 175, 0.2);
    }

    .stat-label {
        font-size: 1rem;
        font-weight: 400;
        margin-bottom: 8px; 
        margin-top: 16px;    
        text-transform: uppercase;
        display: block;
        line-height: 1;
    }
    
    div[data-testid="stProgress"] > div > div > div > div {
        height: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. ENGINE ---
class FusionEngine:
    def __init__(self, df):
        self.df = df

    def _calc_stat(self, dominant, other):
        return (2 * int(dominant) // 3) + (int(other) // 3)

    def get_fusion_data(self, head_dex, body_dex):
        head = self.df.loc[head_dex]
        body = self.df.loc[body_dex]
        
        stats = {
            "HP": self._calc_stat(head['hp'], body['hp']),
            "Atk": self._calc_stat(head['atk'], body['atk']),
            "Def": self._calc_stat(head['def'], body['def']),
            "SpAtk": self._calc_stat(head['spatk'], body['spatk']),
            "SpDef": self._calc_stat(head['spdef'], body['spdef']),
            "Speed": self._calc_stat(head['speed'], body['speed'])
        }
        
        if head['internal_id'] == ':SHEDINJA' or body['internal_id'] == ':SHEDINJA': 
            stats["HP"] = 1
        
        t1 = 'Flying' if head['type1'] == 'Normal' and head['type2'] == 'Flying' else head['type1']
        t2 = body['type2'] if pd.notna(body['type2']) else body['type1']
        if t2 == t1: t2 = body['type1']

        return {
            "Fusion Dex": f"{int(head_dex)}.{int(body_dex)}",
            "Head": head['name'], "Head ID": int(head_dex),
            "Body": body['name'], "Body ID": int(body_dex),
            "Type": f"{t1}/{t2}" if t1 != t2 else t1,
            "Abilities": ", ".join(list(set([str(body['ability1']), str(head['ability1'])]))).replace('nan', ''),
            **stats, "Total": sum(stats.values())
        }

@st.cache_data
def load_base_data():
    df = pd.read_csv('species.csv')
    df_indexed = df[df['dex_num'] > 0].drop_duplicates(subset=['dex_num']).set_index('dex_num')
    maxes = {"HP": 255, "Atk": 190, "Def": 250, "SpAtk": 194, "SpDef": 250, "Speed": 200}
    return df_indexed, maxes

df_base, global_maxes = load_base_data()
engine = FusionEngine(df_base)

def get_base_sprite(dex_id): 
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(dex_id)}.png"
def get_fusion_sprite(head_id, body_id): 
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(head_id)}.{int(body_id)}.png"

# --- 2. SIDEBAR ---
st.sidebar.title("Box Manager")
pokemon_labels = {f"#{idx} {row['name']}": idx for idx, row in df_base.sort_index().iterrows()}
selected_labels = st.sidebar.multiselect("Add to Box:", options=list(pokemon_labels.keys()), key="my_box_labels")
current_box_ids = [pokemon_labels[label] for label in selected_labels]

if current_box_ids:
    st.sidebar.markdown("### Your Box")
    with st.sidebar.container(border=True):
        sorted_box_ids = sorted(current_box_ids)
        for i in range(0, len(sorted_box_ids), 5):
            cols = st.columns(5)
            for k in range(5):
                if i + k < len(sorted_box_ids):
                    cols[k].image(get_base_sprite(sorted_box_ids[i + k]), use_container_width=True)

# --- 3. DATA PROCESSING ---
st.title("Pokemon Fusion Sorter")
c1, c2, c3 = st.columns(3)
sort_by = c1.selectbox("Sort By", options=["Total", "HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"])
order = c2.selectbox("Order", options=["Descending", "Ascending"])
hide_self = c3.checkbox("Hide Self-Fusions", value=True)

if not current_box_ids:
    st.info("Add Pokemon to your Box in the sidebar.")
    st.stop()

# 1. GENERATE COMBOS
combos = list(itertools.permutations(current_box_ids, 2)) if hide_self else list(itertools.product(current_box_ids, repeat=2))

# 2. ADD SAFEGUARD (PREVENTS CRASHES)
MAX_FUSIONS = 5000 
if len(combos) > MAX_FUSIONS:
    st.error(f"Too many fusions ({len(combos):,})! Limit is {MAX_FUSIONS:,}. Please remove some Pokemon from your box.")
    st.stop()

fusion_results = [engine.get_fusion_data(h, b) for h, b in combos]

if not fusion_results:
    st.warning("No fusions possible. Add more Pokemon.")
    st.stop()

results_df = pd.DataFrame(fusion_results).sort_values(by=sort_by, ascending=(order == "Ascending"))
results_df['Fusion Sprite'] = results_df.apply(lambda r: get_fusion_sprite(r['Head ID'], r['Body ID']), axis=1)
results_df['Head Icon'] = results_df['Head ID'].apply(get_base_sprite)
results_df['Body Icon'] = results_df['Body ID'].apply(get_base_sprite)

# --- 4. TABLE ---
event = st.dataframe(
    results_df[["Fusion Dex", "Fusion Sprite", "Head", "Head Icon", "Body", "Body Icon", "Type", "Total", "HP", "Atk", "Def", "SpAtk", "SpDef", "Speed", "Abilities"]],
    column_config={
        "Fusion Sprite": st.column_config.ImageColumn("Fusion", width="small"),
        "Head Icon": st.column_config.ImageColumn("", width="small"),
        "Body Icon": st.column_config.ImageColumn("", width="small"),
        "Total": st.column_config.NumberColumn("BST", format="%d", width="small"),
    },
    hide_index=True, 
    use_container_width=True,
    on_select="rerun", 
    selection_mode="single-cell",
    key="fusion_table"
)

# --- 5. VISUALIZATION ---
if event.selection.cells:
    row_idx = event.selection.cells[0][0]
    fusion = results_df.iloc[row_idx]
    
    st.divider()
    with st.container(border=True):
        st.subheader(f"Fusion Detail: {fusion['Head']} / {fusion['Body']}")
        v1, v2, v3 = st.columns([1, 1, 1])
        v1.image(get_base_sprite(fusion['Head ID']), caption=f"Head: {fusion['Head']}")
        v2.markdown("<h2 style='text-align: center; padding-top: 20px;'>+</h2>", unsafe_allow_html=True)
        v3.image(get_base_sprite(fusion['Body ID']), caption=f"Body: {fusion['Body']}")
        st.image(get_fusion_sprite(fusion['Head ID'], fusion['Body ID']), use_container_width=True)
        
        st.write(f"**Type:** {fusion['Type']} | **BST:** {fusion['Total']} | **Abilities:** {fusion['Abilities']}")
        
        for stat in ["HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"]:
            val = fusion[stat]
            st.markdown(f"<div class='stat-label'>{stat}: {val}</div>", unsafe_allow_html=True)
            st.progress(min(val / global_maxes[stat], 1.0))
            
    if st.button("Close Detail"):
        st.rerun()

st.write(f"Generated {len(results_df)} unique fusions.")