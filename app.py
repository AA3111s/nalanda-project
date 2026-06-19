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
            f'<div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-top: 3px solid #ABC4D8; border-radius: 8px; padding: 18px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">'
            f'<div style="font-size:13px; color:#1E3A8A; font-weight:600; margin-bottom:14px; font-family:\'Plus Jakarta Sans\',sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{cat}">{cat}</div>'
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

    # Heatmap & Drill-down for Hilsa Sub-division
    st.markdown("""<h3 style="font-family: 'Instrument Serif', serif; font-size: 28px; color: #1E3A8A; margin-bottom: 20px;">Hilsa Sub-division Grievance Heatmap</h3>""", unsafe_allow_html=True)

    hilsa_blocks = ['Hilsa', 'Chandi', 'Ekangarsarai', 'Islampur', 'Karai Parsurai', 'Parbalpur', 'Tharthari']
    
    # Filter for Hilsa sub-division
    hilsa_fdf = fdf[fdf['Block'].isin(hilsa_blocks)].copy()
    
    # Load boundaries
    import json
    try:
        with open("hilsa_boundaries.geojson", "r") as f:
            geojson_data = json.load(f)
    except:
        geojson_data = {}

    # Aggregate
    if not hilsa_fdf.empty:
        agg_df = hilsa_fdf.groupby('Block').agg(
            Total_Reports=('ID', 'count'),
            High_Priority=('Priority', lambda x: (x == 'High').sum())
        ).reset_index()
        
        fig = px.choropleth_mapbox(
            agg_df, 
            geojson=geojson_data,
            locations="Block", 
            featureidkey="properties.Block",
            color="High_Priority",
            color_continuous_scale="Reds",
            mapbox_style="white-bg", # Hides underlying base map tiles for a clean look
            zoom=9.5,
            center={"lat": 25.25, "lon": 85.35},
            hover_name="Block",
            hover_data={"Total_Reports": True, "High_Priority": True},
            title="Hilsa Sub-division Static Boundaries"
        )
        fig.update_layout(
            margin={"r":0,"t":40,"l":0,"b":0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            dragmode=False # Disables panning and zooming to make it "static"
        )
        
        st.markdown("<p style='color: #6B7280; font-size: 14px; margin-bottom: 10px;'>Click on a political boundary below to view detailed grievances.</p>", unsafe_allow_html=True)
        
        # We use on_select to capture clicks
        selection = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        
        selected_block = None
        if selection and 'selection' in selection and 'points' in selection['selection']:
            points = selection['selection']['points']
            if len(points) > 0:
                point_index = points[0]['point_index']
                if point_index < len(agg_df):
                    selected_block = agg_df.iloc[point_index]['Block']
        
        if selected_block:
            st.markdown(f"---")
            st.markdown(f"<h4 style='color: #1E3A8A; font-family: \"Instrument Serif\", serif;'>Detailed Problems for {selected_block}</h4>", unsafe_allow_html=True)
            block_data = hilsa_fdf[hilsa_fdf['Block'] == selected_block].copy()
            # Sort by priority High to Low
            block_data['Priority_Rank'] = block_data['Priority'].map({'High': 0, 'Normal': 1})
            block_data = block_data.sort_values(by=['Priority_Rank', 'Days_Open'], ascending=[True, False]).drop(columns=['Priority_Rank'])
            
            st.dataframe(block_data[['ID', 'Category', 'Priority', 'Days_Open', 'Status']], use_container_width=True, hide_index=True)
            
    else:
        st.info("No reports found for Hilsa sub-division.")

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