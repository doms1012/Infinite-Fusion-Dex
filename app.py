import streamlit as st
import pandas as pd
import math
import itertools
import requests
from pkmn_logic import calculate_effectiveness, TYPE_COLORS

# Set page configuration
st.set_page_config(page_title="Pokemon Fusion Sorter", layout="wide", initial_sidebar_state="expanded")

# --- 0. STYLE (CLEAN OSWALD & INTEGRATED BUTTONS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;700&display=swap');

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

    /* REVERSE BUTTON STYLING */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid rgba(59, 130, 246, 0.5);
        background-color: rgba(59, 130, 246, 0.05);
        color: #3b82f6;
        font-family: 'Oswald', sans-serif !important;
        text-transform: uppercase;
        font-weight: 400;
        font-size: 0.8rem;
        letter-spacing: 1px;
        transition: all 0.2s ease;
        margin-top: -10px;
    }

    .stButton > button:hover {
        background: linear-gradient(45deg, #3b82f6, #9333ea);
        color: white;
        border-color: transparent;
        transform: translateY(-1px);
    }

    .stat-label {
        font-size: 0.9rem;
        font-weight: 400;
        margin-bottom: 4px; 
        margin-top: 12px;    
        text-transform: uppercase;
        display: block;
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

        prefix = str(head['name_prefix'])
        suffix = str(body['name_suffix']).lower()
        fusion_name = (prefix + suffix).capitalize()

        return {
            "Fusion Dex": f"{int(head_dex)}.{int(body_dex)}",
            "Fusion Name": fusion_name,
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

POKEBALL_ICON = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png"

def get_base_sprite(dex_id): 
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(dex_id)}.png"

@st.cache_data
def check_fusion_sprite(head_id, body_id):
    url = f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(head_id)}.{int(body_id)}.png"
    try:
        # Pings the URL to see if it exists without downloading the whole image
        response = requests.head(url, timeout=0.5)
        if response.status_code == 200:
            return url
    except:
        pass
    return POKEBALL_ICON

# --- 2. SIDEBAR ---
st.sidebar.title("Box Manager")
pokemon_labels = {f"#{idx} {row['name']}": idx for idx, row in df_base.sort_index().iterrows()}
selected_labels = st.sidebar.multiselect("Add to Box:", options=list(pokemon_labels.keys()), key="my_box_labels")
current_box_ids = [pokemon_labels[label] for label in selected_labels]

# --- 3. DATA PROCESSING ---
st.title("Pokemon Fusion Sorter")
c1, c2, c3 = st.columns(3)
sort_by = c1.selectbox("Sort By", options=["Total", "HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"])
order = c2.selectbox("Order", options=["Descending", "Ascending"])
hide_self = c3.checkbox("Hide Self-Fusions", value=True)

if not current_box_ids:
    st.info("Add Pokemon to your Box in the sidebar.")
    st.stop()

combos = list(itertools.permutations(current_box_ids, 2)) if hide_self else list(itertools.product(current_box_ids, repeat=2))

if not combos:
    st.warning("Add at least 2 Pokemon for fusions.")
    st.stop()

fusion_results = [engine.get_fusion_data(h, b) for h, b in combos]
results_df = pd.DataFrame(fusion_results).sort_values(by=sort_by, ascending=(order == "Ascending"))

# Prepare table visuals
results_df['Fusion Sprite'] = results_df.apply(lambda r: f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(r['Head ID'])}.{int(r['Body ID'])}.png", axis=1)
results_df['Head Icon'] = results_df['Head ID'].apply(get_base_sprite)
results_df['Body Icon'] = results_df['Body ID'].apply(get_base_sprite)

# --- 4. TABLE ---
event = st.dataframe(
    results_df[["Fusion Dex", "Fusion Name", "Fusion Sprite", "Head Icon", "Body Icon", "Type", "Total", "HP", "Atk", "Def", "SpAtk", "SpDef", "Speed", "Abilities"]],
    column_config={
        "Fusion Sprite": st.column_config.ImageColumn("Fusion", width="small"),
        "Head Icon": st.column_config.ImageColumn("Head Sprite", width="small"),
        "Body Icon": st.column_config.ImageColumn("Body Sprite", width="small"),
    },
    hide_index=True, 
    use_container_width=True,
    on_select="rerun", 
    selection_mode="single-cell",
    key="fusion_table"
)

# --- 5. VISUALIZATION ---
if event.selection.cells:
    try:
        row_idx = event.selection.cells[0][0]
        base_fusion = results_df.iloc[row_idx]
        new_selection = (base_fusion['Head ID'], base_fusion['Body ID'])
        
        if 'swap_ids' not in st.session_state or (
            st.session_state.swap_ids != new_selection and 
            st.session_state.swap_ids != (new_selection[1], new_selection[0])
        ):
            st.session_state.swap_ids = new_selection

        h_id, b_id = st.session_state.swap_ids
        current_fusion = engine.get_fusion_data(h_id, b_id)
        
        st.divider()
        
        # Header Area
        st.subheader(f"{current_fusion['Fusion Name']} (#{current_fusion['Fusion Dex']})")
        if st.button("Swap Head and Body", use_container_width=False):
            st.session_state.swap_ids = (b_id, h_id)
            st.rerun()

        col_left, col_right = st.columns(2)

        with col_left:
            # Main Fusion Image with Existence Check for Placeholder
            img_url = check_fusion_sprite(h_id, b_id)
            st.image(img_url, use_container_width=True)
            if img_url == POKEBALL_ICON:
                st.caption("Custom sprite does not exist.")
            
            st.write(f"**Type:** {current_fusion['Type']} | **Ability:** {current_fusion['Abilities']}")
            
            st.markdown("### Defensive Type Effectiveness")
            effs = calculate_effectiveness(current_fusion['Type'])
            w1, w2, w3 = st.columns(3)
            with w1:
                st.error("Weak")
                for t, m in effs.items():
                    if m > 1: st.markdown(f"<span style='color:{TYPE_COLORS.get(t, '#777')};'>{t}</span> {m}x", unsafe_allow_html=True)
            with w2:
                st.info("Resist")
                for t, m in effs.items():
                    if 0 < m < 1: st.markdown(f"<span style='color:{TYPE_COLORS.get(t, '#777')};'>{t}</span> {m}x", unsafe_allow_html=True)
            with w3:
                st.warning("Immune")
                for t, m in effs.items():
                    if m == 0: st.markdown(f"<span style='color:{TYPE_COLORS.get(t, '#777')};'>{t}</span>", unsafe_allow_html=True)

        with col_right:
            st.markdown("### Fusion Components")
            comp_head, comp_body = st.columns(2)
            comp_head.image(get_base_sprite(h_id), caption=f"Head: {current_fusion['Head']}")
            comp_body.image(get_base_sprite(b_id), caption=f"Body: {current_fusion['Body']}")

            st.markdown("### Base Stats")
            for stat in ["HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"]:
                val = current_fusion[stat]
                st.markdown(f"<div class='stat-label'>{stat}: {val}</div>", unsafe_allow_html=True)
                st.progress(min(val / global_maxes[stat], 1.0))
            st.write(f"**Total BST:** {current_fusion['Total']}")

    except (IndexError, KeyError):
        st.rerun()