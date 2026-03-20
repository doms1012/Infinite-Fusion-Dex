import streamlit as st
import pandas as pd
import math
import itertools
import requests
from pkmn_logic import calculate_effectiveness, TYPE_COLORS

# Set page configuration
st.set_page_config(page_title="Pokemon Fusion Companion", layout="wide", initial_sidebar_state="expanded")

# --- 0. STYLE (REVERTED TO CLEAN NEUTRAL THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;700&display=swap');

    /* 1. UNIVERSAL FONT OVERRIDE */
    h1, h2, h3, .stSubheader, .stat-label, [data-testid="stDataFrame"] *, 
    [data-testid="stCaption"] p, .stMarkdown p, .stMarkdown span {
        font-family: 'Oswald', sans-serif !important;
    }
            


    /* 2. THE MAIN TITLE */
    .stMarkdown h1, [data-testid="stHeader"] h1 {
        font-family: 'Oswald', sans-serif !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        text-align: center !important;
        letter-spacing: 2px !important;
        background: -webkit-linear-gradient(45deg, #3b82f6, #9333ea);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 20px;
    }

    /* 3. SIDEBAR CHIPS (Neutral Theme) */
    span[data-baseweb="tag"] {
        background-color: #262730 !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 4px !important;
    }
    span[data-baseweb="tag"] span {
        color: white !important;
        font-family: 'Oswald', sans-serif !important;
        text-transform: uppercase;
        font-size: 0.8rem;
    }
    span[data-baseweb="tag"] svg {
        fill: white !important;
    }

    /* 4. INTEGRATED SWAP BUTTON */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid rgba(59, 130, 246, 0.5);
        background-color: rgba(59, 130, 246, 0.05);
        color: #3b82f6;
        font-family: 'Oswald', sans-serif !important;
        text-transform: uppercase;
        font-weight: 400;
        font-size: 0.85rem;
        letter-spacing: 1px;
        transition: all 0.2s ease;
        margin-top: -10px; 
    }

    .stButton > button:hover {
        background: linear-gradient(45deg, #3b82f6, #9333ea) !important;
        color: white !important;
        border-color: transparent !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }

    /* 5. STAT LABELS & PROGRESS BARS */
    .stat-label {
        font-size: 0.9rem;
        font-weight: 400;
        margin-bottom: 4px; 
        margin-top: 12px;    
        text-transform: uppercase;
        display: block;
    }
    
    div[data-testid="stProgress"] > div > div > div > div {
        height: 10px !important;
    }

    /* Type Badge Styling */
    .type-badge {
        padding: 2px 10px;
        border-radius: 4px;
        color: white;
        text-transform: uppercase;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 5px;
        display: inline-block;
        font-family: 'Oswald', sans-serif;
    }
            
            /* Team Weakness Matrix Styling */
    .weakness-box {
        padding: 5px;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
        color: white;
        margin-bottom: 2px;
        font-size: 0.8rem;
    }
            
    /* 2026 Compact Matrix Styling */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        padding: 0px 4px !important;
        font-size: 0.8rem !important;
        line-height: 1 !important;
    }
    
    /* Remove the empty 'gap' above the dataframe */
    div[data-testid="stDataFrame"] > div:first-child {
        margin-top: -20px !important;
    }

    /* Tighten stat bars */
    .stat-label {
        margin-top: 4px !important;
        font-size: 0.85rem !important;
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

        prefix = str(head['name_prefix']) if 'name_prefix' in head.index else head['name'][:len(head['name'])//2]
        suffix = str(body['name_suffix']).lower() if 'name_suffix' in body.index else body['name'][len(body['name'])//2:].lower()
        
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
        response = requests.head(url, timeout=0.5)
        if response.status_code == 200:
            return url
    except:
        pass
    return POKEBALL_ICON

# --- 4. SIDEBAR & PERSISTENCE LOGIC ---
st.sidebar.title("Box Manager")

pokemon_labels = {f"#{int(idx)} {row['name']}": int(idx) for idx, row in df_base.sort_index().iterrows()}
id_to_label = {v: k for k, v in pokemon_labels.items()}

query_box = st.query_params.get("box", "")
query_team = st.query_params.get("team", "")

url_box_ids = [int(x) for x in query_box.split(",") if x.strip().isdigit()]
box_default = [id_to_label[i] for i in url_box_ids if i in id_to_label]

if "team" not in st.session_state:
    st.session_state.team = []
    url_team_pairs = [x for x in query_team.split(",") if "." in x]
    for pair in url_team_pairs:
        try:
            h, b = map(int, pair.split("."))
            if h in df_base.index and b in df_base.index:
                st.session_state.team.append(engine.get_fusion_data(h, b))
        except:
            continue

selected_labels = st.sidebar.multiselect(
    "Add to Box:", 
    options=list(pokemon_labels.keys()), 
    default=box_default, 
    key="my_box_labels"
)

current_box_ids = [pokemon_labels[label] for label in selected_labels]

new_box_string = ",".join([str(i) for i in current_box_ids])
if query_box != new_box_string:
    st.query_params["box"] = new_box_string

if current_box_ids:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Your Current Box")
    with st.sidebar.container(border=True):
        sorted_box_ids = sorted(current_box_ids)
        for i in range(0, len(sorted_box_ids), 5):
            cols = st.columns(5)
            for k in range(5):
                if i + k < len(sorted_box_ids):
                    cols[k].image(get_base_sprite(sorted_box_ids[i + k]), width="stretch")

# --- 3. DATA PROCESSING ---
st.title("Pokemon Fusion Companion")
# --- 5. TEAM DASHBOARD ---
st.header("Active Team (Max 6)")

if "team" in st.session_state and st.session_state.team:
    # 1. Team Sprite Grid
    team_cols = st.columns(6)
    for idx, member in enumerate(st.session_state.team):
        with team_cols[idx]:
            st.image(check_fusion_sprite(member['Head ID'], member['Body ID']), width="stretch")
            st.caption(f"**{member['Fusion Name']}**")
            if st.button("✖", key=f"remove_member_{idx}"):
                st.session_state.team.pop(idx)
                st.rerun()

    st.divider()
    
    # 2. SYMMETRICAL ANALYTICS ROW
    col_stats, col_matrix = st.columns([1, 1.3])

    with col_stats:
        st.markdown("##### Team Averages")
        stat_inner_1, stat_inner_2 = st.columns(2)
        stats_list = ["HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"]
        
        for i, stat in enumerate(stats_list):
            target_col = stat_inner_1 if i < 3 else stat_inner_2
            avg_val = sum(m[stat] for m in st.session_state.team) / len(st.session_state.team)
            with target_col:
                st.markdown(f"<div style='font-size:0.7rem; margin-top:5px; font-weight:bold;'>{stat}: {int(avg_val)}</div>", unsafe_allow_html=True)
                st.progress(min(avg_val / global_maxes[stat], 1.0))
        
        team_bst = sum(sum(m[s] for s in stats_list) for m in st.session_state.team) / len(st.session_state.team)
        st.markdown(f"<div style='font-size:0.8rem; margin-top:25px; text-align:center; border-top:1px solid #444; padding-top:5px;'><b>Avg Team BST: {int(team_bst)}</b></div>", unsafe_allow_html=True)

    with col_matrix:
        st.markdown("##### Type Coverage")
        all_types = list(TYPE_COLORS.keys())
        
        # Build Table Headers
        sprite_headers = "".join([f"<th style='padding:2px; width:35px; text-align:center;'><img src='{check_fusion_sprite(m['Head ID'], m['Body ID'])}' width='32'></th>" for m in st.session_state.team])
        
        rows_html = ""
        for t in all_types:
            row_cells = ""
            weak_count = 0 # Strictly counting the number of weak members
            for member in st.session_state.team:
                effs = calculate_effectiveness(member['Type'])
                m = effs.get(t, 1.0)
                
                # Logic for display values (Fractions)
                if m == 4.0: display_val = "4"; weak_count += 1
                elif m == 2.0: display_val = "2"; weak_count += 1
                elif m == 1.0: display_val = "-"
                elif m == 0.5: display_val = "½"
                elif m == 0.25: display_val = "¼"
                elif m == 0.0: display_val = "0"
                else: display_val = str(m)
                
                # Cell Coloring
                bg = "transparent"; color = "inherit"
                if m > 1: bg = "#ff4b4b"; color = "white"
                elif m < 1 and m > 0: bg = "#3b82f6"; color = "white"
                elif m == 0: bg = "#faca2b"; color = "black"
                
                row_cells += f"<td style='background-color:{bg}; color:{color}; text-align:center; font-size:0.7rem; padding:1px; border:1px solid #333;'>{display_val}</td>"
            
            # Summary cell styling: turns deeper red if 3 or more members are weak
            sum_bg = "transparent"
            if weak_count >= 3: sum_bg = "#721c24" # 50%+ of team is weak
            elif weak_count > 0: sum_bg = "#4a1216" # 1-2 members are weak
            
            row_cells += f"<td style='background-color:{sum_bg}; text-align:center; font-size:0.7rem; padding:1px; border:1px solid #333; font-weight:bold;'>{weak_count if weak_count > 0 else ''}</td>"
            
            type_color = TYPE_COLORS.get(t, "#777")
            rows_html += f"<tr><td style='font-size:0.65rem; padding:1px; font-weight:bold; color:{type_color}; white-space:nowrap;'>{t}</td>{row_cells}</tr>"

        # Table with Sigma header
        final_html = f"""
        <table style="width:100%; border-collapse:collapse; line-height:0.9; font-family:sans-serif; table-layout: fixed;">
            <thead>
                <tr>
                    <th style="text-align:left; font-size:0.65rem; padding:1px; width:65px;">Type</th>
                    {sprite_headers}
                    <th style="padding:1px; font-size:0.9rem; color:#ff4b4b; width:30px; text-align:center; font-weight:bold;">&Sigma; weak</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """
        st.markdown(final_html, unsafe_allow_html=True)

else:
    st.info("Your team is currently empty. Add members below.")

# Shared URL Sync
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# URL Sync logic
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# URL Sync logic
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# URL Sync logic
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# Shared URL Sync logic (placed at the very end of Section 5)
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# Final URL Sync (Moved outside the IF to avoid duplication)
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# URL Sync
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string

# URL Sync happens once at the end of the section
team_url_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
if st.query_params.get("team", "") != team_url_string:
    st.query_params["team"] = team_url_string
st.divider()
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
st.write(f"Generated {len(results_df)} unique fusions.")
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
    width="stretch",
    on_select="rerun", 
    selection_mode="single-cell",
    key="fusion_table"
)

# --- 7. DETAIL VIEW (FIXED NESTING) ---
if event.selection.cells:
    try:
        # 1. Identify the selected fusion
        row_idx = event.selection.cells[0][0]
        base_fusion = results_df.iloc[row_idx]
        h_id, b_id = base_fusion['Head ID'], base_fusion['Body ID']
        
        # 2. Handle Swap State Management
        if 'swap_ids' not in st.session_state or (st.session_state.swap_ids != (h_id, b_id) and st.session_state.swap_ids != (b_id, h_id)):
            st.session_state.swap_ids = (h_id, b_id)
        
        h_id, b_id = st.session_state.swap_ids
        current_fusion = engine.get_fusion_data(h_id, b_id)
        
        # 3. Header & Action Bar
        st.divider()
        st.subheader(f"{current_fusion['Fusion Name']} (#{current_fusion['Fusion Dex']})")
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🔄 Swap Head/Body", width="stretch"):
                st.session_state.swap_ids = (b_id, h_id)
                st.rerun()

        with btn_col2:
            is_on_team = any(m['Fusion Dex'] == current_fusion['Fusion Dex'] for m in st.session_state.team)
            if is_on_team:
                st.button("✅ Already on Team", disabled=True, width="stretch")
            elif len(st.session_state.team) >= 6:
                st.button("🚫 Team Full (Max 6)", disabled=True, width="stretch")
            else:
                if st.button("➕ Add to Team", width="stretch"):
                    st.session_state.team.append(current_fusion)
                    # Instant URL Sync
                    team_string = ",".join([m['Fusion Dex'] for m in st.session_state.team])
                    st.query_params["team"] = team_string
                    st.rerun()

        # 4. Visualizations: Sprites & Stats
        col_left, col_right = st.columns(2)
        with col_left:
            st.image(check_fusion_sprite(h_id, b_id), width="stretch")
            
            # Colored Type Badges logic
            type_html = ""
            for t in current_fusion['Type'].split('/'):
                color = TYPE_COLORS.get(t, "#777")
                type_html += f'<span class="type-badge" style="background-color: {color};">{t}</span>'
            
            st.markdown(f"**Type:** {type_html}", unsafe_allow_html=True)
            st.write(f"**Ability:** {current_fusion['Abilities']}")
            
            st.markdown("### Defensive Profile")
            effs = calculate_effectiveness(current_fusion['Type'])
            w1, w2, w3 = st.columns(3)
            with w1:
                st.error("Weak")
                for t, m in effs.items():
                    if m > 1: st.write(f"{t} {m}x")
            with w2:
                st.info("Resist")
                for t, m in effs.items():
                    if 0 < m < 1: st.write(f"{t} {m}x")
            with w3:
                st.warning("Immune")
                for t, m in effs.items():
                    if m == 0: st.write(t)

        with col_right:
            st.markdown("### Components")
            ch, cb = st.columns(2)
            ch.image(get_base_sprite(h_id), caption=f"Head: {current_fusion['Head']}", width="stretch")
            cb.image(get_base_sprite(b_id), caption=f"Body: {current_fusion['Body']}", width="stretch")

            st.markdown("### Base Stats")
            for stat in ["HP", "Atk", "Def", "SpAtk", "SpDef", "Speed"]:
                val = current_fusion[stat]
                st.markdown(f"<div class='stat-label'>{stat}: {val}</div>", unsafe_allow_html=True)
                st.progress(min(val / global_maxes[stat], 1.0))
            st.write(f"**BST Total:** {current_fusion['Total']}")

    except Exception as e:
        st.error(f"Error loading detail view: {e}")
        if st.button("Reset View"):
            st.rerun()

# --- FOOTER ---