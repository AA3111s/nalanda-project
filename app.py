import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

from real_data import get_blocks_df, HILSA_STATS, BLOCK_CENSUS, JJM_COVERAGE, MGNREGA_DATA
from classifier import classify_complaint, SCHEMA
from image_loader import hero_css_bg

try:
    from streamlit_plotly_events import plotly_events
    HAS_EVENTS = True
except ImportError:
    HAS_EVENTS = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NGIS · Nalanda", page_icon="🏛️",
                   layout="wide", initial_sidebar_state="expanded")

# ── Chart theme (Updated to Jan Samadhan Palette) ──────────────────────────────
TERRACOTTA = "#D98A73"  # Pastel Terracotta
SAGE       = "#9CAF88"  # Soft Sage Green
RED        = "#C67D6F"  # High Priority: Dusty Coral / Muted Terracotta
AMBER      = "#D1AE6C"  # Medium Priority: Muted Sand / Ochre
GREEN      = "#8EA38B"  # Low Priority: Earthy Sage
BLUE       = "#ABC4D8"  # Pale Sky Blue
CREAM      = "#F8F5F0"  # Cream Official (Background)
WHITE      = "#FFFFFF"  # Cards / Handpaper
MUTED      = "#6B7280"  # Gray for secondary text
NAVY       = "#1E3A8A"  # Deep blue for official headers
BORDER     = "#E5E7EB"  # Light border for structure

# ── FIX: Aliases to prevent breaking existing chart functions ──────────────────
GOLD   = AMBER       
GOLD_L = "#E8D898"   
SAGE_L = "#C2D2B3"

def ct(fig, title="", h=None, secondary_axes=False):
    """Apply consistent light chart theme."""
    kw = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED, family="'Plus Jakarta Sans', sans-serif", size=11),
        title=dict(text=title, font=dict(family="'Instrument Serif', serif", size=18, color=NAVY),
                   x=0, xanchor="left") if title else {},
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=BORDER,
                   tickfont=dict(size=10, color=MUTED), title_font=dict(size=11, color=MUTED)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=BORDER,
                   tickfont=dict(size=10, color=MUTED), title_font=dict(size=11, color=MUTED)),
        margin=dict(t=46 if title else 14, b=14, l=8, r=8),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor=BORDER, borderwidth=1,
                    font=dict(color=MUTED, size=11), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor=WHITE, bordercolor=BORDER,
                        font=dict(color=NAVY, family="'Plus Jakarta Sans'")),
    )
    if h:
        kw["height"] = h
    fig.update_layout(**kw)
    return fig

# ── Sparkline SVG helper ───────────────────────────────────────────────────────
def spark(values, color=GOLD, w=80, h=28):
    if len(values) < 2 or max(values) == min(values):
        return ""
    mn, mx = min(values), max(values)
    pts = " ".join(
        f"{i/(len(values)-1)*w:.1f},{h-((v-mn)/(mx-mn))*h:.1f}"
        for i, v in enumerate(values)
    )
    return (f'<svg width="{w}" height="{h}" style="overflow:visible;vertical-align:middle">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ── KPI card helper ────────────────────────────────────────────────────────────
def kpi(label, value, delta="", delta_dir="flat", sparkvals=None, accent=GOLD):
    sp = spark(sparkvals) if sparkvals else ""
    delta_color = GREEN if delta_dir=="up" else RED if delta_dir=="down" else "#5C4F42"
    arrow = "↑ " if delta_dir=="up" else "↓ " if delta_dir=="down" else ""
    return f"""
    <div class="kpi-card" style="border-top-color:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:6px;">
        <div class="kpi-delta" style="color:{delta_color}">{arrow}{delta}</div>{sp}
      </div>
    </div>"""


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

*,*::before,*::after{box-sizing:border-box}
footer{visibility:hidden}header{visibility:hidden}.stDeployButton{display:none}

/* Main Background - Cream Official */
.stApp { background: #F8F5F0 !important; }
.main .block-container { padding: 0 0 60px 0 !important; max-width: 100% !important; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; }
section[data-testid="stSidebar"] * { color: #4B5563 !important; }
.sidebar-brand { padding: 22px 18px 16px; border-bottom: 1px solid #E5E7EB; }
.sidebar-brand .wordmark { font-family: 'Instrument Serif', serif; font-size: 26px; color: #1E3A8A !important; letter-spacing: 0.02em; }
.sidebar-brand .sub { font-size: 9px; letter-spacing: 2.5px; text-transform: uppercase; color: #D98A73 !important; margin-top: 2px; }
.sidebar-brand .loc { font-size: 11px; color: #6B7280 !important; margin-top: 4px; font-family: 'Fira Code', monospace; }

/* Hero Banner */
.ngis-hero { position: relative; width: 100%; height: 180px; overflow: hidden; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.ngis-hero-bg { width: 100%; height: 100%; background-size: cover; background-position: center; filter: saturate(0.8) brightness(0.95); }
.ngis-hero-over { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(248, 245, 240, 0.95) 0%, rgba(248, 245, 240, 0.7) 50%, rgba(248, 245, 240, 0.1) 100%); display: flex; align-items: flex-end; padding: 26px 52px; }
.ngis-hero h1 { font-family: 'Instrument Serif', serif !important; font-size: 2.8rem !important; color: #1E3A8A !important; margin: 0 0 4px !important; line-height: 1.1 !important; font-weight: 600 !important; }
.ngis-hero p { color: #4B5563; font-size: 13px; margin: 0; letter-spacing: 0.5px; font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 500; }

.ngis-body { padding: 32px 52px 0; }

/* Filter bar */
.filter-bar { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 12px 18px; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; font-size: 11px; color: #6B7280; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }

/* KPI grid (Added Handloom top border & depth) */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.kpi-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 22px 20px 16px; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.04); overflow: hidden; transition: all 0.2s; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.08); }
.kpi-card::before { 
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 5px; 
    /* Bihar Handloom Fabric Pattern from Mood Board */
    background: linear-gradient(90deg, #D98A73 25%, #ABC4D8 25%, #ABC4D8 50%, #9CAF88 50%, #9CAF88 75%, #D1AE6C 75%); 
}
.kpi-label { font-size: 10px; color: #6B7280; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; margin-bottom: 8px; }
.kpi-value { font-size: 36px; font-weight: 500; color: #1E3A8A; font-family: 'Plus Jakarta Sans', sans-serif; line-height: 1; }
.kpi-delta { font-size: 11px; font-family: 'Fira Code', monospace; font-weight: 500; }

/* Section label (Added official Navy styling) */
.sec-label { font-size: 12px; color: #1E3A8A; text-transform: uppercase; letter-spacing: 2px; font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; padding-bottom: 8px; border-bottom: 2px solid #ABC4D8; margin-bottom: 20px; display: inline-block;}

/* Divider (Cultural stitching pattern instead of a plain line) */
.ngis-hr { height: 4px; background-color: transparent; background-image: repeating-linear-gradient(45deg, #D98A73, #D98A73 2px, transparent 2px, transparent 8px); margin: 36px 0; border: none; opacity: 0.5; }

/* System Brief Custom Box */
.sys-brief { background: #FFFFFF; border: 1px solid #E5E7EB; border-left: 6px solid #1E3A8A; border-radius: 8px; padding: 18px 22px; margin-bottom: 24px; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 14px; color: #4B5563; line-height: 1.7; box-shadow: 0 4px 12px rgba(0,0,0,0.04); position: relative; }
.sys-brief::after { content: '🏛️'; position: absolute; right: 24px; top: 50%; transform: translateY(-50%); font-size: 40px; opacity: 0.05; }

/* Insight / Alert blocks */
.ins-block { background: #FFFFFF; border: 1px solid #E5E7EB; border-left: 4px solid #8EA38B; border-radius: 6px; padding: 14px 18px; margin-bottom: 10px; font-size: 13.5px; line-height: 1.75; color: #4B5563; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.alrt-block { background: rgba(198, 125, 111, 0.08); border: 1px solid rgba(198, 125, 111, 0.2); border-left: 4px solid #C67D6F; border-radius: 6px; padding: 11px 16px; margin-bottom: 10px; font-size: 12px; font-family: 'Fira Code', monospace; color: #A05245; line-height: 1.6; }
.good-block { background: rgba(142, 163, 139, 0.1); border: 1px solid rgba(142, 163, 139, 0.25); border-left: 4px solid #8EA38B; border-radius: 6px; padding: 11px 16px; margin-bottom: 10px; font-size: 12px; font-family: 'Fira Code', monospace; color: #4A6348; line-height: 1.6; }
            
/* Scheme tags */
.tag { display: inline-block; font-size: 11px; font-family: 'Plus Jakarta Sans', sans-serif; padding: 3px 10px; border-radius: 4px; margin: 3px; font-weight: 500; }
.tag-g { background: rgba(217, 138, 115, 0.1); border: 1px solid rgba(217, 138, 115, 0.3); color: #B95B40; }
.tag-t { background: rgba(156, 175, 136, 0.1); border: 1px solid rgba(156, 175, 136, 0.3); color: #587340; }

/* Jurisdiction */
.jur { background: #F8F5F0; border: 1px solid #E5E7EB; border-radius: 4px; padding: 10px 14px; font-family: 'Fira Code', monospace; font-size: 11px; color: #D98A73; line-height: 1.8; }

/* Ticket result card */
.ticket-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-top: 3px solid #ABC4D8; border-radius: 8px; padding: 20px 22px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
.ticket-id { font-family: 'Instrument Serif', serif; font-size: 28px; color: #1E3A8A; font-weight: 600; }
.ticket-meta { font-size: 12px; color: #6B7280; margin-top: 4px; font-family: 'Plus Jakarta Sans', sans-serif; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 2px solid #E5E7EB !important; gap: 0 !important; }
.stTabs [data-baseweb="tab"] { color: #6B7280 !important; font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 13px !important; font-weight: 600 !important; padding: 11px 24px !important; border-bottom: 2px solid transparent !important; transition: color 0.2s !important; }
.stTabs [aria-selected="true"] { color: #1E3A8A !important; border-bottom-color: #1E3A8A !important; background: transparent !important; }

/* Buttons */
.stButton>button { background: #1E3A8A !important; color: #FFFFFF !important; font-weight: 600 !important; border-radius: 4px !important; letter-spacing: 0.5px !important; }
.stButton>button:hover { background: #152C69 !important; border-color: #152C69 !important; }

/* Inputs */
.stSelectbox>div>div, .stTextArea textarea { background: #FFFFFF !important; border-color: #E5E7EB !important; color: #1F2937 !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important; }
.stTextArea textarea::placeholder { color: #9CA3AF !important; }

/* Native metrics */
div[data-testid="metric-container"] { background: #FFFFFF !important; border: 1px solid #E5E7EB !important; border-top: 3px solid #D4AF37 !important; border-radius: 6px !important; padding: 14px 16px !important; box-shadow: 0 2px 6px rgba(0,0,0,0.02); }
[data-testid="metric-container"] label { color: #6B7280 !important; font-weight: 600 !important; }
[data-testid="metric-container"] [data-testid="metric-value"] { color: #1F2937 !important; font-weight: 500 !important; }

/* Expander */
.streamlit-expanderHeader { background: #FFFFFF !important; border: 1px solid #E5E7EB !important; color: #1F2937 !important; font-weight: 600 !important; }
.streamlit-expanderContent { background: #F8F5F0 !important; border: 1px solid #E5E7EB !important; border-top: none !important; }

/* Image Strip Carousel */
.img-strip {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    overflow-x: auto;
    padding-bottom: 12px;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
}

/* Customizing the scrollbar to match your theme */
.img-strip::-webkit-scrollbar {
    height: 6px;
}
.img-strip::-webkit-scrollbar-track {
    background: #F8F5F0; 
    border-radius: 4px;
}
.img-strip::-webkit-scrollbar-thumb {
    background: #ABC4D8; 
    border-radius: 4px;
}

/* Giving the empty divs dimensions so the background images appear */
.img-strip div {
    flex: 0 0 300px; /* Forces each image card to be exactly 300px wide */
    height: 180px;   /* Gives the card a height */
    background-size: cover;
    background-position: center;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    scroll-snap-align: start;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
}

/* Hover effect for polish */
.img-strip div:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if 'grievances' not in st.session_state:
    blocks = list(BLOCK_CENSUS.keys())
    cats   = list(SCHEMA.keys())
    depts  = [SCHEMA[c]["department"].split("(")[0].strip() for c in cats]
    n = 90
    np.random.seed(42)
    dates     = [(datetime.now()-timedelta(days=int(np.random.randint(0,45)))).strftime("%Y-%m-%d") for _ in range(n)]
    cat_idx   = np.random.choice(len(cats)-1, n)
    blk_idx   = np.random.choice(len(blocks), n)
    pris      = np.random.choice(["High","Medium","Low"], n, p=[0.22,0.48,0.30])
    stats_    = np.random.choice(["Open","In Progress","Resolved"], n, p=[0.50,0.25,0.25])
    ages      = np.random.randint(1, 35, n)
    st.session_state.grievances = pd.DataFrame({
        "ID":         [f"NLD-{i+1:03d}" for i in range(n)],
        "Date":       dates,
        "Category":   [cats[i] for i in cat_idx],
        "Department": [depts[i] for i in cat_idx],
        "Block":      [blocks[i] for i in blk_idx],
        "Priority":   pris.tolist(),
        "Status":     stats_.tolist(),
        "Days_Open":  ages.tolist(),
    })

if 'drill_block' not in st.session_state:
    st.session_state.drill_block = None
if 'global_priority' not in st.session_state:
    st.session_state.global_priority = "All"
if 'global_block' not in st.session_state:
    st.session_state.global_block = "All"

df        = st.session_state.grievances
blocks_df = get_blocks_df()
resolved  = len(df[df['Status']=='Resolved'])


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="wordmark">NGIS</div>
      <div class="sub">Nalanda Intelligence System</div>
      <div class="loc">Hilsa Sub-Division · Bihar</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Today's Brief","Analytics Suite","Field Capture"],
        icons=["grid-fill","bar-chart-fill","camera-fill"],
        default_index=0,
        styles={
            "container":         {"padding":"4px 8px","background":"transparent"},
            "icon":              {"color":"#D4823A","font-size":"14px"},
            "nav-link":          {"font-size":"13px","color":"#524840","font-family":"Plus Jakarta Sans",
                                  "padding":"9px 12px","margin-bottom":"2px","border-radius":"2px"},
            "nav-link-selected": {"background":"#1A1510","color":"#F2E8D9","font-weight":"600"},
        }
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("""<div style='height:1px;background:#1A1510;margin:0 -8px'></div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Global filters — all pages respond
    st.markdown("<div style='font-size:9px;color:#5C4F42;text-transform:uppercase;letter-spacing:2px;font-family:Plus Jakarta Sans;padding-left:4px;margin-bottom:8px'>Global Filters</div>", unsafe_allow_html=True)
    gp = st.selectbox("Priority", ["All","High","Medium","Low"], label_visibility="collapsed",
                      key="global_priority")
    gb = st.selectbox("Block", ["All"]+sorted(df['Block'].unique().tolist()),
                      label_visibility="collapsed", key="global_block")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    now = datetime.now()
    st.markdown(f"""
    <div style='font-family:Fira Code,monospace;font-size:10px;color:#3A2E22;line-height:2;padding-left:4px'>
      {now.strftime('%d %b %Y  %H:%M')}<br>
      Pop  1,97,309<br>
      Area 140 km²<br>
      Vtgs 56 · Blks 20
    </div>""", unsafe_allow_html=True)


# ── Apply global filters ───────────────────────────────────────────────────────
fdf = df.copy()
if st.session_state.global_priority != "All":
    fdf = fdf[fdf['Priority']==st.session_state.global_priority]
if st.session_state.global_block != "All":
    fdf = fdf[fdf['Block']==st.session_state.global_block]


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — TODAY'S BRIEF
# ═══════════════════════════════════════════════════════════════════
if selected == "Today's Brief":

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_n   = len(df[df['Date']==today_str])
    high_n    = len(df[df['Priority']=='High'])
    pending_n = len(df[df['Status']=='Open'])
    res_rate  = int(resolved/len(df)*100)

    # Hardcoding the default image URL directly to avoid any image_loader errors
    bg_default = "url('https://photodharma.net/India/Nalanda/images/Nalanda-Original-00016.jpg?q=80&w=2000&auto=format&fit=crop')"

    st.markdown(f"""
    <style>
    .ngis-hero-large {{
        position: relative; width: 100%; 
        height: 300px; 
        overflow: hidden; border-radius: 0 0 12px 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .ngis-hero-bg-single {{
        position: absolute; inset: 0;
        background-image: {bg_default};
        background-size: cover; background-position: center;
        filter: saturate(0.8) brightness(0.85);
    }}
    .ngis-hero-over-dark {{
        position: absolute; inset: 0;
        /* Switched to a dark gradient overlay so white text stands out */
        background: linear-gradient(90deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.5) 50%, rgba(0,0,0,0.1) 100%);
        display: flex; align-items: flex-end; padding: 32px 52px;
    }}
    .ngis-hero-over-dark h1 {{
        font-family: 'Instrument Serif', serif !important; 
        font-size: 3.5rem !important; 
        color: #FFFFFF !important; /* Changed to White */
        margin: 0 0 8px !important; 
        line-height: 1.1 !important; 
        font-weight: 600 !important;
        text-shadow: 2px 2px 6px rgba(0,0,0,0.5);
    }}
    .ngis-hero-over-dark p {{
        color: #F8F5F0 !important; /* Changed to Cream */
        font-size: 15px; margin: 0; letter-spacing: 0.5px; 
        font-family: 'Plus Jakarta Sans', sans-serif; 
        font-weight: 500;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.5);
    }}
    </style>
    
    <div class="ngis-hero-large">
      <div class="ngis-hero-bg-single"></div>
      <div class="ngis-hero-over-dark">
        <div>
          <h1>Today's Brief</h1>
          <p>Live grievance status · Nalanda District · {datetime.now().strftime("%d %B %Y, %A")}</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


    st.markdown('<div class="ngis-body">', unsafe_allow_html=True)

    # Auto-generated daily summary
    top_block = fdf['Block'].value_counts().idxmax() if len(fdf) else "—"
    top_cat   = fdf['Category'].value_counts().idxmax().split("/")[0].strip() if len(fdf) else "—"
    st.markdown(f"""
    <div class="sys-brief">
      <strong style="color:#1E3A8A; font-family:'Instrument Serif', serif; font-size: 18px; letter-spacing: 0.5px;">System Brief — </strong>
      {len(fdf)} active records in view · {today_n} filed today ·
      Highest volume block: <strong style="color:#D98A73">{top_block}</strong> ·
      Dominant category: <strong style="color:#9CAF88">{top_cat}</strong> ·
      {high_n} high-priority items requiring attention ·
      Resolution rate: <strong style="color:#4A6348">{res_rate}%</strong>
    </div>
    """, unsafe_allow_html=True)

    # KPI row with sparklines
    daily = df.groupby('Date').size().reset_index(name='c').sort_values('Date')
    spark_total = daily['c'].tolist()[-14:]
    high_daily  = df[df['Priority']=='High'].groupby('Date').size().reset_index(name='c').sort_values('Date')
    spark_high  = high_daily['c'].tolist()[-14:]

    st.markdown(
        '<div class="kpi-row">' +
        kpi("Total Grievances",   len(df),  f"{today_n} today",      "flat",  spark_total, GOLD) +
        kpi("High Priority",      high_n,   "requires action",        "down",  spark_high,  RED) +
        kpi("Pending / Open",     pending_n,f"{pending_n} in queue",  "flat",  None,        AMBER) +
        kpi("Resolution Rate",    f"{res_rate}%", "of all registered","up",   None,        GREEN) +
        '</div>', unsafe_allow_html=True
    )

    # Row: Volume bar + Funnel
    c1, c2 = st.columns([3,2], gap="large")

    with c1:
        st.markdown('<div class="sec-label">Volume by Block & Priority</div>', unsafe_allow_html=True)
        hm = fdf.groupby(['Block','Priority']).size().reset_index(name='Count')
        
        # Sort blocks by total count so the highest volume sits at the top
        block_order = hm.groupby('Block')['Count'].sum().sort_values(ascending=True).index.tolist()
        
        fig_b = px.bar(hm, x='Count', y='Block', color='Priority', 
                       orientation='h', # Flipped to horizontal
                       color_discrete_map={"High":RED,"Medium":AMBER,"Low":GREEN},
                       barmode='stack',
                       # Enforced logical sorting for priority and volume
                       category_orders={"Priority": ["High", "Medium", "Low"], "Block": block_order}, 
                       custom_data=['Priority'])
                       
        fig_b.update_traces(
            hovertemplate="<b>%{y}</b><br>Priority: %{customdata[0]}<br>Count: %{x}<extra></extra>"
        )
        
        fig_b.update_layout(
            xaxis_title="Complaints", 
            yaxis_title=None,
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1)
        )
        ct(fig_b, h=300)
        st.plotly_chart(fig_b, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-label">Resolution Pipeline</div>', unsafe_allow_html=True)
        in_prog = len(df[df['Status']=='In Progress'])
        fig_f = go.Figure(go.Funnel(
            y=["Registered","Triaged","In Progress","Resolved"],
            x=[len(df), int(len(df)*0.82), in_prog, resolved],
            textinfo="value+percent initial",
            connector=dict(line=dict(color="#221C14",width=1.5)),
            marker=dict(color=[BLUE, AMBER, SAGE, GREEN]),
        ))
        ct(fig_f, h=300)
        st.plotly_chart(fig_f, use_container_width=True)

    st.markdown('<div class="ngis-hr"></div>', unsafe_allow_html=True)

   # ── Category Status Metric Blocks ───────────────────────────────────────────────
    st.markdown('<div class="sec-label">Category Status Overview · Open vs Progress vs Done</div>', unsafe_allow_html=True)

    # Group data by Category and Status, then unstack to get columns for each status
    cat_status = fdf.groupby(['Category', 'Status']).size().unstack(fill_value=0)
    
    # Ensure all statuses exist in the dataframe to prevent KeyError
    for stat in ['Open', 'In Progress', 'Resolved']:
        if stat not in cat_status.columns:
            cat_status[stat] = 0
            
    # Calculate Total to sort the cards by highest volume first
    cat_status['Total'] = cat_status['Open'] + cat_status['In Progress'] + cat_status['Resolved']
    cat_status = cat_status.sort_values('Total', ascending=False)

    # Build the HTML grid (compressed to avoid Markdown code block triggers)
    cards = []
    for cat, row in cat_status.iterrows():
        # Using implicit string concatenation to keep the Python readable 
        # while passing a single-line string to the HTML renderer
        card = (
            f'<div style="background:#FFFFFF border:1px solid #E5E7EB; border-top:2px solid #5B8E7D; border-radius:4px; padding:16px 18px;">'
            f'<div style="font-size:13px; color:#1F2937; font-weight:600; margin-bottom:14px; font-family:\'Plus Jakarta Sans\',sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{cat}">{cat}</div>'
            f'<div style="display:flex; justify-content:space-between; font-family:\'Fira Code\',monospace; font-size:10px;">'
            f'<div style="display:flex; flex-direction:column; align-items:flex-start;"><span style="color:#5C4F42; margin-bottom:4px; letter-spacing:1px; font-weight:600;">OPEN</span><span style="color:#C67D6F; font-size:20px;">{row["Open"]}</span></div>'
            f'<div style="display:flex; flex-direction:column; align-items:center;"><span style="color:#5C4F42; margin-bottom:4px; letter-spacing:1px; font-weight:600;">PROG</span><span style="color:#D1AE6C; font-size:20px;">{row["In Progress"]}</span></div>'
            f'<div style="display:flex; flex-direction:column; align-items:flex-end;"><span style="color:#5C4F42; margin-bottom:4px; letter-spacing:1px; font-weight:600;">DONE</span><span style="color:#8EA38B; font-size:20px;">{row["Resolved"]}</span></div>'
            f'</div></div>'
        )
        cards.append(card)

    # Join all cards into the grid container on a single line
    grid_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">{"".join(cards)}</div>'

    # Render the custom HTML grid
    st.markdown(grid_html, unsafe_allow_html=True)

    st.markdown('<div class="ngis-hr"></div>', unsafe_allow_html=True)

    # Complaint register table
    st.markdown('<div class="sec-label">Complaint Register · Sort and Filter</div>', unsafe_allow_html=True)
    category_options = ["All"] + sorted(fdf['Category'].dropna().unique().tolist())
    c_cat, c_age = st.columns([2, 1], gap="medium")
    with c_cat:
        category_choice = st.selectbox("Category", category_options, label_visibility="collapsed")
    with c_age:
        age_order = st.selectbox("Age order", ["Descending", "Ascending"], index=0, label_visibility="collapsed")

    st.markdown(
        "<div class='filter-bar'>Category filter applied first · Block A to Z · Priority High to Low · Status Open to In Progress to Closed</div>",
        unsafe_allow_html=True,
    )

    table_df = fdf.copy()
    if category_choice != "All":
        table_df = table_df[table_df['Category'] == category_choice]

    if len(table_df):
        table_df = table_df.copy()
        table_df['Status_Display'] = table_df['Status'].replace({'Resolved': 'Closed'})
        priority_rank = {'High': 0, 'Medium': 1, 'Low': 2}
        status_rank = {'Open': 0, 'In Progress': 1, 'Closed': 2}
        table_df['_priority_rank'] = table_df['Priority'].map(priority_rank).fillna(99).astype(int)
        table_df['_status_rank'] = table_df['Status_Display'].map(status_rank).fillna(99).astype(int)
        table_df['_block_sort'] = table_df['Block'].astype(str).str.lower()
        table_df['_category_sort'] = table_df['Category'].astype(str).str.lower()
        table_df = table_df.sort_values(
            by=['_priority_rank', '_block_sort', '_status_rank', 'Days_Open', 'ID'],
            ascending=[True, True, True, age_order == 'Ascending', True],
        ).head(15)
    else:
        table_df = table_df.copy()

    def priority_badge(p):
        c = RED if p == "High" else AMBER if p == "Medium" else GREEN
        return f'<span style="color:{c};font-family:Fira Code,monospace;font-size:10px">● {p}</span>'

    def age_badge(d):
        c = RED if d > 20 else AMBER if d > 10 else MUTED
        return f'<span style="color:{c};font-family:Fira Code,monospace">{d}d</span>'

    rows = ""
    for _, row in table_df.iterrows():
        status_value = row.get('Status_Display', row['Status'])
        rows += f"""<tr style="border-bottom:1px solid #F3F4F6; transition: background 0.2s;" onmouseover="this.style.background='#F9FAFB';" onmouseout="this.style.background='transparent';">
            <td style="padding:12px 16px; color:#1E3A8A; font-family:'Fira Code', monospace; font-size:12px; font-weight:500;">{row['ID']}</td>
            <td style="padding:12px 16px; color:#4B5563; font-size:12px;">{row['Category'].split('/')[0].strip()}</td>
            <td style="padding:12px 16px; color:#6B7280; font-size:12px;">{row['Block']}</td>
            <td style="padding:12px 16px; font-size:12px;">{priority_badge(row['Priority'])}</td>
            <td style="padding:12px 16px;">{age_badge(row['Days_Open'])}</td>
            <td style="padding:12px 16px; color:#524840; font-size:11px; font-family:'Fira Code', monospace;">{status_value}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-radius:8px; overflow:hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr style="background-color:#F8F5F0; border-bottom:2px solid #D98A73;">
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">ID</th>
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">Category</th>
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">Block</th>
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">Priority</th>
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">Age</th>
                    <th style="padding:14px 16px; text-align:left; font-size:10px; color:#1E3A8A; text-transform:uppercase; letter-spacing:1.5px; font-family:'Plus Jakarta Sans', sans-serif; font-weight:700;">Status</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Spike detection
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    daily2 = df.groupby('Date').size().reset_index(name='c')
    if len(daily2) > 3:
        spikes = daily2[daily2['c'] > daily2['c'].mean() + 1.5*daily2['c'].std()]
        if not spikes.empty:
            st.markdown(f"<div class='alrt-block'>⚠ SPIKE — Abnormal complaint volume on {', '.join(spikes['Date'].tolist())}. Block-level investigation recommended.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='good-block'>✓ No volume spikes detected in the last 45 days. System operating within normal parameters.</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — ANALYTICS SUITE
# ═══════════════════════════════════════════════════════════════════
elif selected == "Analytics Suite":

    bg2 = hero_css_bg("rajgir")
    st.markdown(f"""
    <div class="ngis-hero">
      <div class="ngis-hero-bg" style="background-image:{bg2};position:absolute;inset:0"></div>
      <div class="ngis-hero-over">
        <div>
          <h1>Analytics Suite</h1>
          <p>Power BI-style drill-down · scheme compliance · predictive forecasting · risk intelligence</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ngis-body">', unsafe_allow_html=True)

    # Image strip with Nalanda images
    bg_n = hero_css_bg("nalanda_ruins", 400)
    bg_r = hero_css_bg("rajgir", 400)
    bg_p = hero_css_bg("pawapuri", 400)
    st.markdown(f"""
    <div class="img-strip">
      <div style="background-image:{bg_n}" title="Nalanda Mahavihara Ruins"></div>
      <div style="background-image:{bg_r}" title="Rajgir Hills"></div>
      <div style="background-image:{bg_p}" title="Pawapuri — Jal Mandir"></div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["📊  Grievance Intelligence","💧  Scheme Compliance","📈  Forecasting","🗺️  Block Drill-Down"])

    # ── TAB 1: GRIEVANCE INTELLIGENCE ──────────────────────────────
    with tabs[0]:
        c1, c2 = st.columns(2, gap="large")

        with c1:
            # Stacked bar + line overlay — total vs resolved
            bc = fdf.groupby('Block').agg(Total=('ID','count'), Resolved=('Status', lambda x: (x=='Resolved').sum())).reset_index()
            bc['Pending'] = bc['Total'] - bc['Resolved']
            bc['Res_Rate'] = (bc['Resolved']/bc['Total']*100).round(1)
            bc = bc.sort_values('Total', ascending=False)

            fig = make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_bar(x=bc['Block'], y=bc['Total'], name="Total", marker_color=BLUE, opacity=0.7, secondary_y=False)
            fig.add_bar(x=bc['Block'], y=bc['Resolved'], name="Resolved", marker_color=GREEN, opacity=0.9, secondary_y=False)
            fig.add_scatter(x=bc['Block'], y=bc['Res_Rate'], name="Res. Rate %",
                            line=dict(color=GOLD, width=2.5), mode='lines+markers',
                            marker=dict(size=6), secondary_y=True)
            fig.update_layout(barmode='overlay',
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color=MUTED, family="Plus Jakarta Sans"),
                              title=dict(text="Total vs Resolved — Resolution Rate Overlay",
                                         font=dict(family="Instrument Serif, serif", size=16, color=CREAM)),
                              xaxis=dict(gridcolor="#221C14", tickangle=-35, tickfont=dict(size=10), title=None),
                              margin=dict(t=46,b=14,l=8,r=8), height=320,
                              legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                              hoverlabel=dict(bgcolor="#1C1510", bordercolor="#3A2E22", font=dict(color=CREAM)))
            fig.update_yaxes(gridcolor="#221C14", secondary_y=False)
            fig.update_yaxes(showgrid=False, range=[0,120], ticksuffix="%", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            # Sunburst — category → priority drill
            fdf2 = fdf.copy(); fdf2['cnt']=1
            fig_s = px.sunburst(fdf2, path=['Category','Priority'], values='cnt',
                                color='Priority',
                                color_discrete_map={"High":RED,"Medium":AMBER,"Low":GREEN,"(?)":MUTED})
            fig_s.update_traces(textfont=dict(family="Plus Jakarta Sans", size=11))
            ct(fig_s, "Category → Priority Sunburst", h=320)
            fig_s.update_layout(margin=dict(t=46,b=0,l=0,r=0))
            st.plotly_chart(fig_s, use_container_width=True)

        # Heatmap matrix — Block × Department
        pivot = fdf.groupby(['Block','Department']).size().unstack(fill_value=0)
        fig_hm = px.imshow(pivot,
                           color_continuous_scale=[[0,"#0C0A07"],[0.3,"#2C1A0E"],[0.7,AMBER],[1,RED]],
                           text_auto=True, aspect="auto")
        fig_hm.update_traces(textfont=dict(size=9, color=CREAM))
        fig_hm.update_layout(coloraxis_colorbar=dict(title="Count", tickfont=dict(color=MUTED), thickness=10))
        ct(fig_hm, "Block × Department Complaint Matrix — Intensity Heatmap", h=380)
        st.plotly_chart(fig_hm, use_container_width=True)

        # Waterfall — net position
        c1b, c2b = st.columns(2, gap="large")
        with c1b:
            opened   = len(df)
            resolved_ = len(df[df['Status']=='Resolved'])
            in_prog_  = len(df[df['Status']=='In Progress'])
            backlog   = opened - resolved_
            fig_wf = go.Figure(go.Waterfall(
                name="", orientation="v",
                x=["Registered","In Progress","Resolved","Backlog"],
                y=[opened, -in_prog_, -resolved_, 0],
                measure=["absolute","relative","relative","total"],
                text=[f"{opened}",f"-{in_prog_}",f"-{resolved_}",f"{backlog}"],
                textposition="outside",
                connector=dict(line=dict(color="#221C14", width=1)),
                increasing=dict(marker=dict(color=BLUE)),
                decreasing=dict(marker=dict(color=GREEN)),
                totals=dict(marker=dict(color=RED if backlog>30 else AMBER)),
                textfont=dict(color=MUTED, size=11),
            ))
            ct(fig_wf, "Complaint Lifecycle Waterfall", h=300)
            st.plotly_chart(fig_wf, use_container_width=True)

        with c2b:
            # Department response time simulation
            dept_ages = fdf[fdf['Status']!='Resolved'].groupby('Department')['Days_Open'].mean().reset_index()
            dept_ages.columns = ['Department', 'Avg_Days']
            dept_ages = dept_ages.sort_values('Avg_Days', ascending=False)
            dept_ages['Dept_Short'] = dept_ages['Department'].apply(lambda x: x[:22]+"…" if len(x)>22 else x)
            dept_ages['color'] = dept_ages['Avg_Days'].apply(lambda x: RED if x>20 else AMBER if x>12 else GREEN)

            fig_d = go.Figure(go.Bar(
                x=dept_ages['Avg_Days'], y=dept_ages['Dept_Short'],
                orientation='h', marker_color=dept_ages['color'],
                text=dept_ages['Avg_Days'].apply(lambda x: f"{x:.0f}d"),
                textposition='outside', textfont=dict(color=MUTED, size=10),
                customdata=dept_ages['Department'],
                hovertemplate="<b>%{customdata}</b><br>Avg open: %{x:.0f} days<extra></extra>"
            ))
            fig_d.add_vline(x=15, line_dash="dot", line_color=GREEN,
                            annotation_text="15d target", annotation_font_color=GREEN)
            ct(fig_d, "Avg. Days Open by Department (unresolved)", h=300)
            fig_d.update_layout(yaxis_title=None)
            st.plotly_chart(fig_d, use_container_width=True)

    # ── TAB 2: SCHEME COMPLIANCE ────────────────────────────────────
    with tabs[1]:

        c1, c2 = st.columns([3,2], gap="large")
        with c1:
            jjm_df = pd.DataFrame([{"Block":b,**v} for b,v in JJM_COVERAGE.items()]).sort_values("coverage_pct", ascending=False)
            fig_j = px.bar(jjm_df, x="Block", y=["coverage_pct","functional_pct"], barmode='group',
                           color_discrete_map={"coverage_pct":SAGE,"functional_pct":BLUE},
                           labels={"value":"%","variable":"Metric"},
                           custom_data=[jjm_df['Block']])
            fig_j.add_hline(y=80, line_dash="dot", line_color=AMBER,
                            annotation_text="National 80%", annotation_font_color=AMBER)
            fig_j.update_layout(xaxis_title=None, yaxis_title="(%)",
                                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            ct(fig_j, "JJM Tap Coverage vs Functional Connections — All Blocks")
            st.plotly_chart(fig_j, use_container_width=True)

        with c2:
            jjm_df["gap"] = jjm_df["coverage_pct"] - jjm_df["functional_pct"]
            fig_sc = px.scatter(jjm_df, x="coverage_pct", y="functional_pct",
                                size="gap", color="functional_pct",
                                color_continuous_scale=[[0,RED],[0.5,AMBER],[1,GREEN]],
                                text="Block",
                                labels={"coverage_pct":"Coverage %","functional_pct":"Functional %"})
            fig_sc.add_shape(type="line",x0=0,y0=0,x1=100,y1=100,line=dict(color="#221C14",dash="dot"))
            fig_sc.update_traces(textposition='top center', textfont=dict(size=9, color=MUTED),
                                 marker=dict(opacity=0.8))
            fig_sc.update_layout(coloraxis_colorbar=dict(title="Func%",tickfont=dict(color=MUTED),thickness=8))
            ct(fig_sc, "Coverage vs Functionality Gap (bubble = gap size)")
            st.plotly_chart(fig_sc, use_container_width=True)

        # Gauge for Hilsa
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=JJM_COVERAGE["Hilsa"]["coverage_pct"],
                title={"text":"Hilsa JJM Coverage","font":{"color":MUTED,"family":"Plus Jakarta Sans","size":13}},
                delta={"reference":80,"suffix":"%"},
                number={"suffix":"%","font":{"color":CREAM,"size":44}},
                gauge={"axis":{"range":[0,100],"tickcolor":"#221C14"},
                       "bar":{"color":GOLD},"bgcolor":"rgba(0,0,0,0)","bordercolor":"rgba(0,0,0,0)",
                       "steps":[{"range":[0,60],"color":"#1A0B0B"},{"range":[60,100],"color":"rgba(91,142,125,.1)"}],
                       "threshold":{"line":{"color":AMBER,"width":2},"value":80}}
            ))
            fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig_g, use_container_width=True)

        with col_g2:
            mgn_df = pd.DataFrame([{"Block":b,**v} for b,v in MGNREGA_DATA.items()])
            hilsa_delay = MGNREGA_DATA["Hilsa"]["avg_delay_days"]
            fig_g2 = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=hilsa_delay,
                title={"text":"Hilsa MGNREGA Delay (days)","font":{"color":MUTED,"family":"Plus Jakarta Sans","size":13}},
                delta={"reference":15,"suffix":"d vs mandate","increasing":{"color":RED},"decreasing":{"color":GREEN}},
                number={"suffix":"d","font":{"color":CREAM,"size":44}},
                gauge={"axis":{"range":[0,60],"tickcolor":"#221C14"},
                       "bar":{"color":RED if hilsa_delay>30 else AMBER},
                       "bgcolor":"rgba(0,0,0,0)","bordercolor":"rgba(0,0,0,0)",
                       "steps":[{"range":[0,15],"color":"rgba(74,155,111,.12)"},{"range":[15,60],"color":"#1A0B0B"}],
                       "threshold":{"line":{"color":GREEN,"width":2},"value":15}}
            ))
            fig_g2.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig_g2, use_container_width=True)

        with col_g3:
            fig_g3 = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=res_rate,
                title={"text":"District Resolution Rate","font":{"color":MUTED,"family":"Plus Jakarta Sans","size":13}},
                delta={"reference":70,"suffix":"%"},
                number={"suffix":"%","font":{"color":CREAM,"size":44}},
                gauge={"axis":{"range":[0,100],"tickcolor":"#221C14"},
                       "bar":{"color":GREEN},"bgcolor":"rgba(0,0,0,0)","bordercolor":"rgba(0,0,0,0)",
                       "steps":[{"range":[0,50],"color":"#1A0B0B"},{"range":[50,100],"color":"rgba(74,155,111,.08)"}],
                       "threshold":{"line":{"color":GOLD,"width":2},"value":70}}
            ))
            fig_g3.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig_g3, use_container_width=True)

        # MGNREGA delay + Pareto
        c1m, c2m = st.columns(2, gap="large")
        with c1m:
            mgn_df = mgn_df.sort_values("avg_delay_days", ascending=False)
            mgn_df["col"] = mgn_df["avg_delay_days"].apply(lambda x: RED if x>40 else AMBER if x>25 else GREEN)
            fig_mg = go.Figure(go.Bar(
                x=mgn_df["Block"], y=mgn_df["avg_delay_days"],
                marker_color=mgn_df["col"],
                text=mgn_df["avg_delay_days"].apply(lambda x:f"{x}d"),
                textposition='outside', textfont=dict(color=MUTED, size=9),
                customdata=mgn_df[["job_cards","active_workers","pending_wages_lakh"]].values,
                hovertemplate="<b>%{x}</b><br>Delay: %{y} days<br>Job cards: %{customdata[0]:,}<br>Active workers: %{customdata[1]:,}<br>Pending wages: ₹%{customdata[2]:.1f}L<extra></extra>"
            ))
            fig_mg.add_hline(y=15, line_dash="dash", line_color=GREEN,
                             annotation_text="15-day mandate", annotation_font_color=GREEN, annotation_position="top right")
            ct(fig_mg, "MGNREGA Wage Delay by Block — Hover for Detail")
            fig_mg.update_layout(xaxis=dict(tickangle=-35, title=None))
            st.plotly_chart(fig_mg, use_container_width=True)

        with c2m:
            mgn_s = mgn_df.sort_values("pending_wages_lakh", ascending=False).copy()
            mgn_s["cum"] = mgn_s["pending_wages_lakh"].cumsum()/mgn_s["pending_wages_lakh"].sum()*100
            fig_pa = make_subplots(specs=[[{"secondary_y":True}]])
            fig_pa.add_bar(x=mgn_s["Block"], y=mgn_s["pending_wages_lakh"],
                           name="Pending ₹L", marker_color="#1E3560", secondary_y=False)
            fig_pa.add_scatter(x=mgn_s["Block"], y=mgn_s["cum"],
                               name="Cumulative %", line=dict(color=GOLD, width=2), secondary_y=True)
            fig_pa.add_hline(y=80, line_dash="dot", line_color=MUTED, secondary_y=True,
                             annotation_text="80%", annotation_font_color=MUTED)
            fig_pa.update_layout(
                title=dict(text="Pareto — Pending Wage Distribution",
                           font=dict(family="Instrument Serif, serif", size=16, color=CREAM)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=MUTED, family="Plus Jakarta Sans"),
                xaxis=dict(gridcolor="#221C14", tickangle=-35, title=None),
                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=46,b=14,l=8,r=8),
                hoverlabel=dict(bgcolor="#1C1510", bordercolor="#3A2E22", font=dict(color=CREAM))
            )
            fig_pa.update_yaxes(gridcolor="#221C14", secondary_y=False)
            fig_pa.update_yaxes(showgrid=False, range=[0,110], ticksuffix="%", secondary_y=True)
            st.plotly_chart(fig_pa, use_container_width=True)

        # Hilsa intel cards
        h = HILSA_STATS
        st.markdown('<div class="ngis-hr"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Hilsa Sub-Division — Baseline Intelligence</div>', unsafe_allow_html=True)
        for txt in [
            f"⚠ <strong>Gender Welfare</strong> — Child sex ratio 898 vs Bihar avg 935. PCPNDT enforcement and ASHA monitoring critical.",
            f"📚 <strong>Education</strong> — Female literacy 44.49% vs male 63.77%. 19-point gender gap. MDM and scholarship audits recommended in rural panchayats.",
            f"💧 <strong>JJM Last-Mile</strong> — 28% of households (~9,300 families) uncovered. 61% functional rate signals service failure, not just coverage failure.",
            f"👷 <strong>MGNREGA</strong> — 28-day avg payment delay vs 15-day mandate. ₹12.4 lakh pending for ~4,200 active workers."
        ]:
            st.markdown(f"<div class='ins-block'>{txt}</div>", unsafe_allow_html=True)

    # ── TAB 3: FORECASTING ──────────────────────────────────────────
    with tabs[2]:
        daily3 = df.groupby('Date').size().reset_index(name='count').sort_values('Date')
        daily3['date_num'] = range(len(daily3))
        x, y = daily3['date_num'].values, daily3['count'].values

        c1, c2 = st.columns([3,2], gap="large")

        with c1:
            if len(x) >= 4:
                coeffs = np.polyfit(x, y, 1)
                fx     = np.arange(len(x), len(x)+7)
                fy     = np.polyval(coeffs, fx)
                std_r  = np.std(y - np.polyval(coeffs, x))
                cu     = fy + 1.5*std_r
                cl     = np.maximum(fy - 1.5*std_r, 0)
                fdates = [(datetime.now()+timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(7)]

                fig_fc = go.Figure()
                fig_fc.add_scatter(x=daily3['Date'], y=daily3['count'], name="Actual",
                                   line=dict(color=SAGE, width=2.5), mode='lines+markers',
                                   marker=dict(size=5, color=SAGE),
                                   hovertemplate="%{x}<br>%{y} complaints<extra></extra>")
                fig_fc.add_scatter(x=fdates+fdates[::-1], y=list(cu)+list(cl[::-1]),
                                   fill='toself', fillcolor='rgba(212,130,58,.07)',
                                   line=dict(color="rgba(0,0,0,0)"), name="Confidence Band")
                fig_fc.add_scatter(x=fdates, y=fy, name="7-Day Forecast",
                                   line=dict(color=GOLD, width=2, dash="dot"), mode='lines+markers',
                                   marker=dict(size=5, color=GOLD))
                m_, s_ = np.mean(y), np.std(y)
                anom   = daily3[np.abs(y-m_)>1.8*s_]
                if not anom.empty:
                    fig_fc.add_scatter(x=anom['Date'], y=anom['count'], mode='markers',
                                       name="Anomaly", marker=dict(color=RED, size=12, symbol="x",
                                       line=dict(width=2, color=RED)))
                fig_fc.update_layout(xaxis=dict(showgrid=False), yaxis_title="Daily Complaints",
                                     legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
                ct(fig_fc, "45-Day Trend + 7-Day Forecast with Anomaly Detection", h=360)
                st.plotly_chart(fig_fc, use_container_width=True)

        with c2:
            # Category trend
            cat_d = df.groupby(['Date','Category']).size().reset_index(name='count')
            cat_d['cat_short'] = cat_d['Category'].apply(lambda x: x.split('/')[0].strip())
            fig_ct = px.line(cat_d, x='Date', y='count', color='cat_short',
                             color_discrete_sequence=[SAGE,GOLD,BLUE,RED,AMBER,GREEN,"#9B59B6","#E91E63","#795548"])
            fig_ct.update_layout(legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            ct(fig_ct, "Category-wise Volume Trends", h=360)
            st.plotly_chart(fig_ct, use_container_width=True)

        # Risk composite
        st.markdown('<div class="sec-label">Composite Block Risk Index</div>', unsafe_allow_html=True)
        risk_df = pd.DataFrame([{
            "Block": b,
            "Delay": MGNREGA_DATA.get(b,{}).get("avg_delay_days",0),
            "JJM":   100 - JJM_COVERAGE.get(b,{}).get("coverage_pct",0),
            "Grievances": len(df[df['Block']==b]),
        } for b in list(BLOCK_CENSUS.keys())])
        risk_df["Risk"] = (risk_df["Delay"]/52*40 + risk_df["JJM"]/100*30 + risk_df["Grievances"]/risk_df["Grievances"].max()*30).round(1)
        risk_df = risk_df.sort_values("Risk", ascending=False)

        fig_rk = px.bar(risk_df, x="Block", y="Risk",
                        color="Risk", color_continuous_scale=[[0,GREEN],[0.45,AMBER],[0.75,RED],[1,"#7B0000"]],
                        text="Risk", custom_data=risk_df[["Delay","JJM","Grievances"]].values)
        fig_rk.update_traces(
            texttemplate="%{text:.0f}", textposition="outside",
            textfont=dict(color=MUTED, size=9),
            hovertemplate="<b>%{x}</b><br>Risk Score: %{y:.0f}<br>MGNREGA Delay: %{customdata[0]}d<br>JJM Gap: %{customdata[1]:.0f}%<br>Grievances: %{customdata[2]}<extra></extra>"
        )
        fig_rk.update_layout(coloraxis_showscale=False, xaxis=dict(tickangle=-35, title=None), yaxis=dict(range=[0,100]))
        ct(fig_rk, "Composite Risk Score — MGNREGA Delay + JJM Gap + Grievance Volume")
        st.plotly_chart(fig_rk, use_container_width=True)

    # ── TAB 4: BLOCK DRILL-DOWN ─────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="sec-label">Select a Block to Drill Down</div>', unsafe_allow_html=True)
        drill = st.selectbox("Block", sorted(df['Block'].unique().tolist()), label_visibility="collapsed")
        bdf   = df[df['Block']==drill]
        bdata = blocks_df[blocks_df['Block']==drill].iloc[0] if len(blocks_df[blocks_df['Block']==drill]) else None

        if bdata is not None:
            st.markdown(f"""
            <div class="kpi-row">
              {kpi("Population",       f"{int(bdata['Population']):,}", "Census 2011",    "flat", None, SAGE)}
              {kpi("Literacy Rate",    f"{bdata['Literacy_%']:.1f}%",   "Census 2011",    "flat", None, BLUE)}
              {kpi("JJM Coverage",     f"{bdata['JJM_Coverage_%']:.0f}%", "vs 80% national","flat", None, GOLD)}
              {kpi("MGNREGA Delay",    f"{bdata['MGNREGA_Delay_Days']:.0f}d", "vs 15d mandate","down", None, RED)}
            </div>
            """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            cat_b = bdf.groupby('Category').size().reset_index(name='n')
            cat_b['cat_s'] = cat_b['Category'].apply(lambda x: x.split('/')[0].strip())
            fig_pb = px.pie(cat_b, values='n', names='cat_s', hole=0.52,
                            color_discrete_sequence=[SAGE,GOLD,BLUE,RED,AMBER,GREEN,"#9B59B6","#E91E63"])
            fig_pb.update_traces(textfont=dict(family="Plus Jakarta Sans", size=10), textinfo="percent+label")
            ct(fig_pb, f"{drill} — Category Mix", h=300)
            fig_pb.update_layout(showlegend=False, margin=dict(t=46,b=0,l=0,r=0))
            st.plotly_chart(fig_pb, use_container_width=True)

        with c2:
            pri_b = bdf.groupby('Priority').size().reset_index(name='n')
            fig_pr = go.Figure(go.Bar(
                x=pri_b['Priority'], y=pri_b['n'],
                marker_color=[RED if p=="High" else AMBER if p=="Medium" else GREEN for p in pri_b['Priority']],
                text=pri_b['n'], textposition='outside', textfont=dict(color=MUTED, size=11)
            ))
            ct(fig_pr, f"{drill} — Priority Breakdown", h=300)
            fig_pr.update_layout(xaxis_title=None)
            st.plotly_chart(fig_pr, use_container_width=True)

        with c3:
            # Radar for this block
            def timeliness(d): return max(0, 100-((d-15)/15)*100)
            cats_r = ["Literacy","Sex Ratio/10","JJM Cover","MGNREGA OK","Res.Rate"]
            if bdata is not None:
                vals = [bdata['Literacy_%'], bdata['Sex_Ratio']/10, bdata['JJM_Coverage_%'],
                        timeliness(bdata['MGNREGA_Delay_Days']),
                        len(bdf[bdf['Status']=='Resolved'])/max(len(bdf),1)*100]
                fig_rd = go.Figure(go.Scatterpolar(
                    r=vals+[vals[0]], theta=cats_r+[cats_r[0]],
                    fill='toself', name=drill,
                    line=dict(color=GOLD, width=2),
                    fillcolor="rgba(212,130,58,.1)"
                ))
                fig_rd.update_layout(
                    polar=dict(bgcolor="rgba(0,0,0,0)",
                               radialaxis=dict(visible=True,range=[0,100],color="#221C14",gridcolor="#221C14",tickfont=dict(size=8,color="#3A2E22")),
                               angularaxis=dict(color=MUTED,gridcolor="#221C14",tickfont=dict(color=MUTED))),
                    paper_bgcolor="rgba(0,0,0,0)",
                    title=dict(text=f"{drill} — Profile Radar", font=dict(family="Instrument Serif, serif", size=15, color=CREAM)),
                    margin=dict(t=46,b=10,l=20,r=20), height=300,
                    showlegend=False
                )
                st.plotly_chart(fig_rd, use_container_width=True)

        # Trend for this block
        btd = bdf.groupby('Date').size().reset_index(name='n')
        fig_bt = px.area(btd, x='Date', y='n',
                         color_discrete_sequence=[SAGE])
        fig_bt.update_traces(fillcolor="rgba(91,142,125,.12)", line=dict(width=2))
        fig_bt.update_layout(xaxis_title=None, yaxis_title="Daily complaints")
        ct(fig_bt, f"{drill} — Daily Complaint Trend")
        st.plotly_chart(fig_bt, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — FIELD CAPTURE
# ═══════════════════════════════════════════════════════════════════
elif selected == "Field Capture":

    bg3 = hero_css_bg("pawapuri")
    st.markdown(f"""
    <div class="ngis-hero">
      <div class="ngis-hero-bg" style="background-image:{bg3};position:absolute;inset:0"></div>
      <div class="ngis-hero-over">
        <div>
          <h1>Field Digitization Terminal</h1>
          <p>Heuristic NLP routing · jurisdiction chain · scheme mapping · auto-escalation</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ngis-body">', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1.7], gap="large")
    with c1:
        st.markdown('<div class="sec-label">Input Grievance Text</div>', unsafe_allow_html=True)
        raw = st.text_area("", height=220,
                           placeholder="हमारे गाँव में पानी की सप्लाई बंद है। हैंडपम्प खराब हो गया है...",
                           label_visibility="collapsed")
        go_btn = st.button("Classify & Route →", use_container_width=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#FFFFFFborder:1px solid #E5E7EB;border-radius:3px;padding:12px 14px;
                    font-family:'Fira Code',monospace;font-size:10px;color:#3A2E22;line-height:1.9">
          ENGINE  · Weighted bigram heuristic<br>
          LANGS   · Hindi + English<br>
          CATS    · 9 primary categories<br>
          EXTRACT · Block · Village · Name · Date<br>
          OUTPUT  · Dept · Jurisdiction · Schemes
        </div>
        """, unsafe_allow_html=True)

    with c2:
        if go_btn and raw.strip():
            with st.spinner("Running classification engine..."):
                r = classify_complaint(raw)
                new_id = f"NLD-{len(st.session_state.grievances)+1:03d}"
                st.session_state.grievances = pd.concat([
                    st.session_state.grievances,
                    pd.DataFrame([{
                        "ID": new_id, "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Category": r["category"], "Department": r["department"],
                        "Block": r["block"], "Priority": r["priority"],
                        "Status": "Open", "Days_Open": 0
                    }])
                ], ignore_index=True)

            pri_col = RED if r['priority']=="High" else AMBER if r['priority']=="Medium" else GREEN
            st.markdown(f"""
            <div class="ticket-card">
              <div style="font-size:9px;color:#5C4F42;text-transform:uppercase;letter-spacing:2px;
                          font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px">Ticket Generated</div>
              <div class="ticket-id">{new_id}</div>
              <div class="ticket-meta">
                {r['icon']} {r['category']} &nbsp;·&nbsp;
                Priority <span style="color:{pri_col};font-weight:600">{r['priority']}</span> &nbsp;·&nbsp;
                Block: {r['block']} &nbsp;·&nbsp; Confidence: {r['confidence']*100:.0f}%
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin-bottom:14px">
              <div style="font-size:9px;color:#5C4F42;text-transform:uppercase;letter-spacing:2px;
                          font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px">Department Routed</div>
              <div style="font-size:16px;font-weight:600;color:#1F2937;font-family:'Plus Jakarta Sans',sans-serif">
                {r['department']}
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin-bottom:14px">
              <div style="font-size:9px;color:#5C4F42;text-transform:uppercase;letter-spacing:2px;
                          font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px">Jurisdiction Chain</div>
              <div class="jur">{r.get('jurisdiction','—')}</div>
            </div>
            """, unsafe_allow_html=True)

            cs = r.get("central_schemes", [])
            bs = r.get("bihar_schemes", [])
            if cs or bs:
                c_tags = "".join([f'<span class="tag tag-g">{s}</span>' for s in cs])
                b_tags = "".join([f'<span class="tag tag-t">{s}</span>' for s in bs])
                st.markdown(f"""
                <div style="margin-bottom:14px">
                  <div style="font-size:9px;color:#5C4F42;text-transform:uppercase;letter-spacing:2px;
                              font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:8px">Applicable Schemes</div>
                  <div>{c_tags}{b_tags}</div>
                </div>
                """, unsafe_allow_html=True)

            esc = ("⚠ HIGH PRIORITY — Escalate to SDO within 24 hours. Flag for Collector's weekly review."
                   if r["priority"]=="High" else
                   "→ Route to department. 15-day resolution window under VB-GRAM-G applies.")
            esc_cls = "alrt-block" if r["priority"]=="High" else "good-block"
            st.markdown(f"<div class='{esc_cls}'>{esc}</div>", unsafe_allow_html=True)

            # Similar past complaints
            similar = df[df['Category']==r['category']].head(5)
            if len(similar):
                with st.expander(f"📋  {len(similar)} similar past complaints in {r['category'].split('/')[0].strip()}"):
                    st.dataframe(similar[['ID','Block','Priority','Status','Days_Open']],
                                 use_container_width=True, hide_index=True)

        elif go_btn:
            st.markdown("<div class='alrt-block'>Please enter grievance text before classifying.</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)