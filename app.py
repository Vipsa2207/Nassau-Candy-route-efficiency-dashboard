import base64
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk

sys.path.insert(0, "src")
from geo_lookup import STATE_COORDS, US_STATE_ABBREV, REGION_COORDS
# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Nassau Candy | Route Performance Report",
    page_icon="assets/nassau_candy_logo.webp",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MIN_SHIPMENTS_FOR_RANKING = 5

# Brand palette (pulled from the Nassau Candy logo)
ESPRESSO = "#2B2118"
GOLD = "#A67C52"
CREAM = "#FAF7F2"
CARD = "#FFFFFF"
BORDER = "#E7DFD2"
MUTED = "#8A7F6E"
TERRACOTTA = "#A6472F"   # bad / delayed
SAGE = "#6B7A55"         # good / efficient

# =====================================================================
# THEME / CSS
# =====================================================================
CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;1,600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

.stApp {{ background-color: {CREAM}; }}
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {ESPRESSO}; }}
h1, h2, h3 {{ font-family: 'Playfair Display', serif !important; color: {ESPRESSO}; font-weight: 700; }}
[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; }}
[data-testid="stHeader"] {{ background-color: {CREAM}; }}

/* ---------- MASTHEAD ---------- */
.masthead {{ text-align: center; padding: 8px 0 4px 0; }}
.masthead-row {{
    display: flex; align-items: center; justify-content: center;
    gap: 22px; margin-bottom: 4px;
}}
.masthead-row img {{ height: 150px; }}
.masthead-text {{ text-align: left; }}
.report-title {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-style: italic;
    font-size: 2.5rem;
    color: {ESPRESSO};
    margin: 0;
    line-height: 1.15;
}}
.report-subtitle {{
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {MUTED};
    margin-top: 6px;
}}
.brand-rule {{
    display: flex; align-items: center; justify-content: center;
    gap: 16px; max-width: 460px; margin: 14px auto 18px auto;
}}
.brand-rule::before, .brand-rule::after {{
    content: ""; flex: 1; height: 1px; background: {GOLD};
}}
.brand-rule span {{
    font-family: 'Playfair Display', serif; font-style: italic;
    color: {GOLD}; font-size: 1.3rem;
}}

/* ---------- FILTER BAR ---------- */
.filter-label {{
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: {ESPRESSO}; font-weight: 700; margin-bottom: 4px;
    display: flex; align-items: center; gap: 6px;
}}
[data-testid="stContainer"] {{ border-color: {BORDER} !important; }}

/* ---------- SECTION NAV (replaces st.tabs) ---------- */
.section-nav [data-testid="stSegmentedControl"] button {{
    font-weight: 500;
}}

/* ---------- KPI CARDS ---------- */
.kpi-card {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-top: 3px solid {GOLD};
    border-radius: 6px;
    padding: 14px 18px;
    min-height: 96px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.kpi-card.warn {{ border-top-color: {TERRACOTTA}; }}
.kpi-card.good {{ border-top-color: {SAGE}; }}
.kpi-label {{
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: {ESPRESSO}; font-weight: 700;
}}
.kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem; font-weight: 600; color: {ESPRESSO};
}}
.kpi-value.warn {{ color: {TERRACOTTA}; }}
.kpi-value.good {{ color: {SAGE}; }}
.kpi-sub {{ font-size: 0.72rem; color: {MUTED}; min-height: 1.1em; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=CARD,
    plot_bgcolor=CARD,
    font_color=ESPRESSO,
    margin=dict(l=10, r=10, t=40, b=10),
)

# =====================================================================
# ICONS (simple line-icons, not emoji -- rendered as inline SVG)
# =====================================================================
ICONS = {
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "truck": '<path d="M10 17h4V5H2v12h3"/><path d="M20 17h2v-3.34a4 4 0 0 0-1.17-2.83L19 9h-5v8h1"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
    "trophy": '<path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0V4z"/><path d="M17 5h2.5a2 2 0 0 1 0 4H17"/><path d="M7 5H4.5a2 2 0 0 0 0 4H7"/>',
    "map": '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>',
    "package": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.73z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "lightbulb": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.4 1 1.1 1 1.8V17h6v-.5c0-.7.4-1.4 1-1.8A7 7 0 0 0 12 2z"/>',
    "factory": '<path d="M2 20h20"/><path d="M4 20V10l5 3V10l5 3V10l5 3v7"/><path d="M4 10V6h3v2"/>',
    "trend": '<polyline points="3 17 9 11 13 15 21 6"/><polyline points="14 6 21 6 21 13"/>',
}


def icon_html(name, color, size=18):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;">{ICONS[name]}</svg>'
    )


def heading_html(icon_name, text, level="h3"):
    return (
        f'<{level} style="display:flex; align-items:center; gap:10px; margin:0;">'
        f'{icon_html(icon_name, ESPRESSO, 22)}<span>{text}</span></{level}>'
    )

@st.cache_data
def get_logo_base64():
    with open("assets/nassau_candy_logo.webp", "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_b64 = get_logo_base64()

# =====================================================================
# DATA LOADING
# =====================================================================
@st.cache_data
def load_data():
    orders = pd.read_csv("data/nassau_candy_features.csv")
    orders["Order Date"] = pd.to_datetime(orders["Order Date"])
    orders["Ship Date"] = pd.to_datetime(orders["Ship Date"])
    return orders

orders = load_data()

# =====================================================================
# MASTHEAD
# =====================================================================
st.markdown(
    f"""
    <div class="masthead">
        <div class="masthead-row">
            <img src="data:image/webp;base64,{logo_b64}" />
            <div class="masthead-text">
                <h1 class="report-title">Route Performance Report</h1>
                <p class="report-subtitle">Factory-to-Customer Shipping Analytics</p>
            </div>
        </div>
        <div class="brand-rule"><span>&#38;</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# FILTER BAR
# =====================================================================
with st.container(border=True):
    frow1_col1, frow1_col2 = st.columns([1, 1])

    with frow1_col1:
        st.markdown(f'<div class="filter-label">{icon_html("pin", GOLD, 15)}Region</div>', unsafe_allow_html=True)
        regions = sorted(orders["Region"].unique())
        selected_regions = st.segmented_control(
            "Region", regions, selection_mode="multi", default=regions,
            label_visibility="collapsed",
        )

    with frow1_col2:
        st.markdown(f'<div class="filter-label">{icon_html("truck", GOLD, 15)}Ship Mode</div>', unsafe_allow_html=True)
        ship_modes = sorted(orders["Ship Mode"].unique())
        selected_modes = st.segmented_control(
            "Ship Mode", ship_modes, selection_mode="multi", default=ship_modes,
            label_visibility="collapsed",
        )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    frow2_col1, frow2_col2 = st.columns([1, 1])

    with frow2_col1:
        st.markdown(f'<div class="filter-label">{icon_html("calendar", GOLD, 15)}Order Month Range</div>', unsafe_allow_html=True)
        month_periods = pd.period_range(
            orders["Order Date"].min(), orders["Order Date"].max(), freq="M"
        )
        month_labels = [p.strftime("%b %Y") for p in month_periods]
        start_label, end_label = st.select_slider(
            "Order month range",
            options=month_labels,
            value=(month_labels[0], month_labels[-1]),
            label_visibility="collapsed",
        )

    with frow2_col2:
        st.markdown(f'<div class="filter-label">{icon_html("clock", GOLD, 15)}Delay Threshold (days)</div>', unsafe_allow_html=True)
        delay_threshold = st.slider(
            "Delay threshold (days)",
            min_value=int(orders["Shipping Lead Time (Days)"].min()),
            max_value=int(orders["Shipping Lead Time (Days)"].max()),
            value=18, label_visibility="collapsed",
            help="Shipments slower than this are flagged as 'delayed' throughout the report.",
        )
        st.caption(
            f"Range reflects actual shipping lead times in the data "
            f"({int(orders['Shipping Lead Time (Days)'].min())}\u2013"
            f"{int(orders['Shipping Lead Time (Days)'].max())} days)."
        )

st.caption(
    f"Routes need {MIN_SHIPMENTS_FOR_RANKING}+ shipments to appear in efficiency rankings "
    "(avoids small-sample noise)."
)

# =====================================================================
# APPLY FILTERS
# =====================================================================
start = pd.Period(start_label, freq="M").start_time
end = pd.Period(end_label, freq="M").end_time
mask_date = (orders["Order Date"] >= start) & (orders["Order Date"] <= end)

active_regions = selected_regions if selected_regions else regions
active_modes = selected_modes if selected_modes else ship_modes

filtered = orders[
    mask_date
    & orders["Region"].isin(active_regions)
    & orders["Ship Mode"].isin(active_modes)
].copy()

filtered["Is Delayed"] = (filtered["Shipping Lead Time (Days)"] > delay_threshold).astype(int)

if filtered.empty:
    st.warning("No shipments match the current filters. Widen your filters above.")
    st.stop()

# =====================================================================
# LIVE ROUTE SUMMARY (recomputed from whatever is currently filtered)
# =====================================================================
def scale_inverse(s):
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(100.0, index=s.index)
    return 100 * (1 - (s - lo) / (hi - lo))


def compute_route_summary(df):
    summary = (
        df.groupby(["Factory", "State/Province", "Region", "Route"])
        .agg(
            Total_Shipments=("Row ID", "count"),
            Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
            Lead_Time_Std=("Shipping Lead Time (Days)", "std"),
            Delay_Rate=("Is Delayed", "mean"),
            Total_Sales=("Sales", "sum"),
        )
        .reset_index()
    )
    summary["Lead_Time_Std"] = summary["Lead_Time_Std"].fillna(0)
    summary["Speed_Score"] = scale_inverse(summary["Avg_Lead_Time"])
    summary["Consistency_Score"] = scale_inverse(summary["Lead_Time_Std"])
    summary["Reliability_Score"] = scale_inverse(summary["Delay_Rate"])
    summary["Efficiency_Score"] = (
        0.5 * summary["Speed_Score"]
        + 0.3 * summary["Consistency_Score"]
        + 0.2 * summary["Reliability_Score"]
    ).round(1)
    return summary


route_summary = compute_route_summary(filtered)
reliable_routes = route_summary[route_summary["Total_Shipments"] >= MIN_SHIPMENTS_FOR_RANKING]

EFFICIENCY_COLORSCALE = [[0, TERRACOTTA], [0.5, GOLD], [1, SAGE]]


def compute_state_summary(df):
    """Aggregates across all factories serving each customer state/province."""
    summary = (
        df.groupby(["State/Province", "Region", "Country/Region"])
        .agg(
            Total_Shipments=("Row ID", "count"),
            Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
            Lead_Time_Std=("Shipping Lead Time (Days)", "std"),
            Delay_Rate=("Is Delayed", "mean"),
        )
        .reset_index()
    )
    summary["Lead_Time_Std"] = summary["Lead_Time_Std"].fillna(0)
    summary["Speed_Score"] = scale_inverse(summary["Avg_Lead_Time"])
    summary["Consistency_Score"] = scale_inverse(summary["Lead_Time_Std"])
    summary["Reliability_Score"] = scale_inverse(summary["Delay_Rate"])
    summary["Efficiency_Score"] = (
        0.5 * summary["Speed_Score"]
        + 0.3 * summary["Consistency_Score"]
        + 0.2 * summary["Reliability_Score"]
    ).round(1)
    return summary


state_summary = compute_state_summary(filtered)
def generate_findings(df, reliable_routes_df, min_group_size=30):
    """Computes genuine, data-driven findings from whatever is currently filtered."""
    findings = []
    overall_delay = df["Is Delayed"].mean()

    mode_stats = df.groupby("Ship Mode").agg(Delay_Rate=("Is Delayed", "mean")).reset_index()
    region_stats = df.groupby("Region").agg(Delay_Rate=("Is Delayed", "mean")).reset_index()

    if len(mode_stats) >= 2:
        best_mode = mode_stats.loc[mode_stats["Delay_Rate"].idxmin()]
        worst_mode = mode_stats.loc[mode_stats["Delay_Rate"].idxmax()]
        if worst_mode["Delay_Rate"] - best_mode["Delay_Rate"] > 0.05:
            findings.append((
                "risk", f"{worst_mode['Ship Mode']} shipments delay far more often",
                f"{worst_mode['Ship Mode']} has a {worst_mode['Delay_Rate']*100:.1f}% delay rate, "
                f"versus just {best_mode['Delay_Rate']*100:.1f}% for {best_mode['Ship Mode']}.",
            ))

    state_stats = df.groupby("State/Province").agg(
        Shipments=("Row ID", "count"), Delay_Rate=("Is Delayed", "mean")
    ).reset_index()
    big_states = state_stats[state_stats["Shipments"] >= min_group_size]
    if not big_states.empty:
        worst_state = big_states.loc[big_states["Delay_Rate"].idxmax()]
        if worst_state["Delay_Rate"] > overall_delay * 1.3 and worst_state["Delay_Rate"] > 0.05:
            findings.append((
                "risk", f"{worst_state['State/Province']} is a geographic bottleneck",
                f"Among locations with {min_group_size}+ shipments, {worst_state['State/Province']} has "
                f"the highest delay rate at {worst_state['Delay_Rate']*100:.1f}%, based on "
                f"{int(worst_state['Shipments'])} shipments.",
            ))

    if len(region_stats) >= 2 and len(mode_stats) >= 2:
        region_spread = region_stats["Delay_Rate"].max() - region_stats["Delay_Rate"].min()
        mode_spread = mode_stats["Delay_Rate"].max() - mode_stats["Delay_Rate"].min()
        if mode_spread > region_spread * 2 and mode_spread > 0.05:
            findings.append((
                "neutral", "Ship mode predicts delay better than geography",
                f"Delay rates vary {mode_spread*100:.1f} percentage points across ship modes, but only "
                f"{region_spread*100:.1f} points across regions.",
            ))

    if not reliable_routes_df.empty:
        best_route = reliable_routes_df.loc[reliable_routes_df["Efficiency_Score"].idxmax()]
        findings.append((
            "good", f"{best_route['Route']} leads all qualifying routes",
            f"Scoring {best_route['Efficiency_Score']:.1f}/100 across "
            f"{int(best_route['Total_Shipments'])} shipments.",
        ))

    factory_stats = df.groupby("Factory").agg(
        Shipments=("Row ID", "count"), Delay_Rate=("Is Delayed", "mean")
    ).reset_index()
    reliable_factories = factory_stats[factory_stats["Shipments"] >= min_group_size]
    if len(reliable_factories) >= 2:
        best_f = reliable_factories.loc[reliable_factories["Delay_Rate"].idxmin()]
        worst_f = reliable_factories.loc[reliable_factories["Delay_Rate"].idxmax()]
        if worst_f["Factory"] != best_f["Factory"] and worst_f["Delay_Rate"] - best_f["Delay_Rate"] > 0.03:
            findings.append((
                "risk", f"{worst_f['Factory']} lags behind other factories",
                f"{worst_f['Factory']} shows a {worst_f['Delay_Rate']*100:.1f}% delay rate versus "
                f"{best_f['Delay_Rate']*100:.1f}% for {best_f['Factory']}.",
            ))

    snapshot_tone = "warn" if overall_delay > 0.25 else ("good" if overall_delay < 0.15 else "neutral")
    findings.append((
        snapshot_tone, "Overall delay snapshot",
        f"{overall_delay*100:.1f}% of shipments in the current selection exceed the delay "
        f"threshold ({len(df):,} shipments analyzed).",
    ))

    tone_order = {"risk": 0, "warn": 0, "neutral": 1, "good": 2}
    findings.sort(key=lambda f: tone_order.get(f[0], 1))
    return findings

def compute_factory_region_summary(df):
    """Aggregates by Factory -> Region (only 4 regions, keeps the map readable)."""
    summary = (
        df.groupby(["Factory", "Region"])
        .agg(
            Total_Shipments=("Row ID", "count"),
            Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
            Lead_Time_Std=("Shipping Lead Time (Days)", "std"),
            Delay_Rate=("Is Delayed", "mean"),
        )
        .reset_index()
    )
    summary["Lead_Time_Std"] = summary["Lead_Time_Std"].fillna(0)
    summary["Speed_Score"] = scale_inverse(summary["Avg_Lead_Time"])
    summary["Consistency_Score"] = scale_inverse(summary["Lead_Time_Std"])
    summary["Reliability_Score"] = scale_inverse(summary["Delay_Rate"])
    summary["Efficiency_Score"] = (
        0.5 * summary["Speed_Score"]
        + 0.3 * summary["Consistency_Score"]
        + 0.2 * summary["Reliability_Score"]
    ).round(1)
    summary["Flow"] = summary["Factory"] + " -> " + summary["Region"]
    return summary


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]


def efficiency_to_color(score):
    t_rgb, g_rgb, s_rgb = hex_to_rgb(TERRACOTTA), hex_to_rgb(GOLD), hex_to_rgb(SAGE)
    score = max(0, min(100, score))
    if score <= 50:
        ratio = score / 50
        return [int(t_rgb[i] + (g_rgb[i] - t_rgb[i]) * ratio) for i in range(3)]
    ratio = (score - 50) / 50
    return [int(g_rgb[i] + (s_rgb[i] - g_rgb[i]) * ratio) for i in range(3)]


def build_flow_arcs(df):
    fr = compute_factory_region_summary(df)
    fr["Region_Lat"] = fr["Region"].map(lambda r: REGION_COORDS[r][0])
    fr["Region_Lon"] = fr["Region"].map(lambda r: REGION_COORDS[r][1])

    factory_coords = df[["Factory", "Factory Lat", "Factory Lon"]].drop_duplicates().set_index("Factory")
    fr["Factory Lat"] = fr["Factory"].map(factory_coords["Factory Lat"])
    fr["Factory Lon"] = fr["Factory"].map(factory_coords["Factory Lon"])
    fr["color"] = fr["Efficiency_Score"].apply(efficiency_to_color)

    max_ship = fr["Total_Shipments"].max()
    fr["arc_height"] = 0.1 + 0.4 * (fr["Total_Shipments"] / max_ship)
    fr["arc_width"] = 2 + 8 * (fr["Total_Shipments"] / max_ship)
    return fr
# =====================================================================
# KPI ROW
# =====================================================================
total_shipments = len(filtered)
avg_lead = filtered["Shipping Lead Time (Days)"].mean()
delay_rate = filtered["Is Delayed"].mean() * 100
total_sales = filtered["Sales"].sum()
n_routes = filtered["Route"].nunique()

delay_css = "warn" if delay_rate > 25 else ("good" if delay_rate < 15 else "")

kpi_specs = [
    ("TOTAL SHIPMENTS", f"{total_shipments:,}", "", ""),
    ("AVG LEAD TIME", f"{avg_lead:.1f}d", "", ""),
    ("DELAY RATE", f"{delay_rate:.1f}%", f"threshold {delay_threshold}d", delay_css),
    ("ACTIVE ROUTES", f"{n_routes}", "", ""),
    ("TOTAL SALES", f"${total_sales:,.0f}", "", ""),
]
cols = st.columns(5)
for col, (label, value, sub, css_class) in zip(cols, kpi_specs):
    sub_html = sub if sub else "&nbsp;"
    col.markdown(
        f"""<div class="kpi-card {css_class}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value {css_class}">{value}</div>
                <div class="kpi-sub">{sub_html}</div>
            </div>""",
        unsafe_allow_html=True,
    )

st.write("")

# =====================================================================
# SECTION NAV (pill-style, not a tab bar -- content added in later steps)
# =====================================================================
SECTIONS = ["Overview", "Route Map", "Ship Modes", "Drill-Down", "Findings"]

st.markdown('<div class="section-nav">', unsafe_allow_html=True)
active_section = st.segmented_control(
    "Section", SECTIONS, selection_mode="single", default="Overview",
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

if not active_section:
    active_section = "Overview"

st.write("")

if active_section == "Overview":
    st.markdown(heading_html("trophy", "Route Efficiency Leaderboard"), unsafe_allow_html=True)

    if reliable_routes.empty:
        st.warning(
            f"No routes have {MIN_SHIPMENTS_FOR_RANKING}+ shipments under the current filters. "
            "Widen your filters to see rankings."
        )
    else:
        best = reliable_routes.loc[reliable_routes["Efficiency_Score"].idxmax()]
        st.caption(
            f"{len(reliable_routes)} of {len(route_summary)} routes qualify for ranking "
            f"(5+ shipments). Top performer: **{best['Route']}** at {best['Efficiency_Score']:.1f}/100."
        )

        col1, col2 = st.columns(2)

        with col1:
            top10 = reliable_routes.nlargest(10, "Efficiency_Score").sort_values("Efficiency_Score")
            fig_top = px.bar(
                top10, x="Efficiency_Score", y="Route", orientation="h",
                color="Efficiency_Score", range_color=[0, 100],
                color_continuous_scale=EFFICIENCY_COLORSCALE,
                title="Top 10 Most Efficient Routes",
                labels={"Efficiency_Score": "Efficiency Score"},
            )
            fig_top.update_layout(**PLOTLY_LAYOUT, coloraxis_showscale=False, height=380)
            fig_top.update_xaxes(range=[0, 100])
            st.plotly_chart(fig_top, use_container_width=True)

        with col2:
            bottom10 = reliable_routes.nsmallest(10, "Efficiency_Score").sort_values(
                "Efficiency_Score", ascending=False
            )
            fig_bottom = px.bar(
                bottom10, x="Efficiency_Score", y="Route", orientation="h",
                color="Efficiency_Score", range_color=[0, 100],
                color_continuous_scale=EFFICIENCY_COLORSCALE,
                title="Bottom 10 Least Efficient Routes",
                labels={"Efficiency_Score": "Efficiency Score"},
            )
            fig_bottom.update_layout(**PLOTLY_LAYOUT, coloraxis_showscale=False, height=380)
            fig_bottom.update_xaxes(range=[0, 100])
            st.plotly_chart(fig_bottom, use_container_width=True)
    

elif active_section == "Route Map":
    st.markdown(heading_html("map", "Factory-to-Region Shipping Flow"), unsafe_allow_html=True)   

    flow_arcs = build_flow_arcs(filtered)

    if flow_arcs.empty:
        st.warning("No shipping flows under the current filters.")
    else:
        st.caption(
            f"Showing {len(flow_arcs)} factory-to-region flows. Arc color reflects Efficiency "
            "Score: terracotta (low) &rarr; gold &rarr; sage (high). Arc thickness reflects "
            "shipment volume on that flow. Squares mark the 5 Nassau Candy factories.",
            unsafe_allow_html=True,
        )

        arc_layer = pdk.Layer(
            "ArcLayer",
            data=flow_arcs,
            get_source_position=["Factory Lon", "Factory Lat"],
            get_target_position=["Region_Lon", "Region_Lat"],
            get_source_color=[139, 111, 78, 160],
            get_target_color="color",
            get_width="arc_width",
            get_height="arc_height",
            pickable=True,
            auto_highlight=True,
        )

        factory_points = filtered[["Factory", "Factory Lat", "Factory Lon"]].drop_duplicates()
        factory_layer = pdk.Layer(
            "ScatterplotLayer",
            data=factory_points,
            get_position=["Factory Lon", "Factory Lat"],
            get_fill_color=[43, 33, 24, 220],
            get_radius=50000,
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=39, longitude=-96, zoom=3.9, pitch=0)

        deck = pdk.Deck(
            layers=[arc_layer, factory_layer],
            initial_view_state=view_state,
            map_provider="carto",
            map_style="light",
            tooltip={
                "html": "<b>{Flow}</b><br/>Efficiency: {Efficiency_Score}<br/>Shipments: {Total_Shipments}",
                "style": {"backgroundColor": ESPRESSO, "color": "white"},
            },
        )
        st.pydeck_chart(deck, use_container_width=True, height=520)
        st.caption("Map requires an internet connection to load the base map tiles.")

        legend_html = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="width:14px;height:14px;background:{color};border-radius:3px;"></div>'
            f'<span style="font-size:0.85rem;color:{MUTED};">{label}</span></div>'
            for label, color in [
                ("Low Efficiency", TERRACOTTA),
                ("Medium", GOLD),
                ("High Efficiency", SAGE),
            ]
        )
        st.markdown(
            f'<div style="display:flex;gap:32px;margin-top:8px;">{legend_html}</div>',
            unsafe_allow_html=True,
        )

    st.write("")
    with st.expander("View state-level efficiency heatmap"):
        us_states = state_summary[state_summary["Country/Region"] == "United States"].copy()
        us_states["Abbrev"] = us_states["State/Province"].map(US_STATE_ABBREV)
        us_states = us_states.dropna(subset=["Abbrev"])

        if us_states.empty:
            st.warning("No US states to map under the current filters.")
        else:
            fig_map = px.choropleth(
                us_states,
                locations="Abbrev",
                locationmode="USA-states",
                color="Efficiency_Score",
                scope="usa",
                color_continuous_scale=EFFICIENCY_COLORSCALE,
                range_color=[0, 100],
                hover_name="State/Province",
                hover_data={
                    "Abbrev": False,
                    "Total_Shipments": True,
                    "Avg_Lead_Time": ":.1f",
                    "Delay_Rate": ":.1%",
                },
                labels={"Avg_Lead_Time": "Avg Lead Time", "Delay_Rate": "Delay Rate"},
            )
            fig_map.update_layout(
                paper_bgcolor=CARD,
                plot_bgcolor=CARD,
                geo=dict(
                    bgcolor=CARD, lakecolor=CREAM, showlakes=True,
                    landcolor="#EFE9DD", subunitcolor="#D8CFC0",
                ),
                margin=dict(l=0, r=0, t=10, b=0),
                height=460,
                coloraxis_colorbar=dict(title="Efficiency"),
            )
            st.plotly_chart(fig_map, use_container_width=True)

        canada = state_summary[state_summary["Country/Region"] == "Canada"]
        if not canada.empty:
            st.caption(f"Canadian provinces ({int(canada['Total_Shipments'].sum())} shipments, not shown on map above):")
            st.dataframe(
                canada[["State/Province", "Total_Shipments", "Avg_Lead_Time", "Delay_Rate", "Efficiency_Score"]]
                .sort_values("Efficiency_Score", ascending=False)
                .rename(columns={
                    "State/Province": "Province", "Total_Shipments": "Shipments",
                    "Avg_Lead_Time": "Avg Lead Time (d)", "Delay_Rate": "Delay Rate",
                })
                .style.format({"Avg Lead Time (d)": "{:.1f}", "Delay Rate": "{:.1%}"}),
                use_container_width=True, hide_index=True,
            )

elif active_section == "Ship Modes":
    st.markdown(heading_html("package", "Ship Mode Comparison"), unsafe_allow_html=True)

    SHIP_MODE_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"]
    mode_summary = (
        filtered.groupby("Ship Mode")
        .agg(
            Shipments=("Row ID", "count"),
            Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
            Delay_Rate=("Is Delayed", "mean"),
            Avg_Sales=("Sales", "mean"),
            Avg_Gross_Profit=("Gross Profit", "mean"),
        )
        .reset_index()
    )
    mode_summary["Margin_Pct"] = mode_summary["Avg_Gross_Profit"] / mode_summary["Avg_Sales"] * 100
    mode_summary["Ship Mode"] = pd.Categorical(mode_summary["Ship Mode"], categories=SHIP_MODE_ORDER, ordered=True)
    mode_summary = mode_summary.sort_values("Ship Mode")

    if mode_summary.empty:
        st.warning("No shipments match the current filters.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            fig_lead = px.bar(
                mode_summary, x="Ship Mode", y="Avg_Lead_Time",
                color="Avg_Lead_Time", color_continuous_scale=[[0, SAGE], [1, TERRACOTTA]],
                title="Average Lead Time by Ship Mode",
                labels={"Avg_Lead_Time": "Avg Lead Time (days)"},
                text_auto=".1f",
            )
            fig_lead.update_layout(**PLOTLY_LAYOUT, coloraxis_showscale=False, height=380)
            st.plotly_chart(fig_lead, use_container_width=True)

        with col2:
            present_modes = [m for m in SHIP_MODE_ORDER if m in filtered["Ship Mode"].unique()]
            fig_box = px.box(
                filtered, x="Ship Mode", y="Shipping Lead Time (Days)",
                category_orders={"Ship Mode": present_modes},
                color="Ship Mode",
                color_discrete_sequence=[GOLD, SAGE, TERRACOTTA, ESPRESSO],
                title="Lead Time Distribution by Ship Mode",
            )
            fig_box.update_layout(**PLOTLY_LAYOUT, showlegend=False, height=380)
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown(heading_html("trend", "Cost-Time Tradeoff (Descriptive)", level="h4"), unsafe_allow_html=True)
        display_tbl = mode_summary[
            ["Ship Mode", "Shipments", "Avg_Lead_Time", "Delay_Rate", "Avg_Sales", "Margin_Pct"]
        ].rename(columns={
            "Avg_Lead_Time": "Avg Lead Time (d)", "Delay_Rate": "Delay Rate",
            "Avg_Sales": "Avg Order Value ($)", "Margin_Pct": "Avg Margin (%)",
        })
        st.dataframe(
            display_tbl.style.format({
                "Avg Lead Time (d)": "{:.1f}", "Delay Rate": "{:.1%}",
                "Avg Order Value ($)": "${:.2f}", "Avg Margin (%)": "{:.1f}%",
            }),
            use_container_width=True, hide_index=True,
        )

        margin_spread = mode_summary["Margin_Pct"].max() - mode_summary["Margin_Pct"].min()
        st.caption(
            f"Average order value and profit margin vary by less than {margin_spread:.1f} "
            "percentage points across ship modes in this filtered selection \u2014 faster shipping "
            "does not appear to be reserved for higher-value orders in this dataset."
        )

elif active_section == "Drill-Down":
    st.markdown(heading_html("search", "Route Drill-Down"), unsafe_allow_html=True)

    available_states = sorted(filtered["State/Province"].unique())
    if not available_states:
        st.warning("No states available under the current filters.")
    else:
        state_shipment_counts = filtered["State/Province"].value_counts()
        default_state = state_shipment_counts.idxmax()
        selected_state = st.selectbox(
            "Select a state / province to drill into",
            available_states,
            index=available_states.index(default_state),
        )

        state_df = filtered[filtered["State/Province"] == selected_state]
        state_row = state_summary[state_summary["State/Province"] == selected_state]

        if state_df.empty or state_row.empty:
            st.warning("No shipments for this state under the current filters.")
        else:
            state_row = state_row.iloc[0]
            n_states_ranked = len(state_summary)
            rank = int((state_summary["Efficiency_Score"] > state_row["Efficiency_Score"]).sum() + 1)

            kcol1, kcol2, kcol3, kcol4 = st.columns(4)
            kcol1.metric("Shipments", f"{int(state_row['Total_Shipments']):,}")
            kcol2.metric("Avg Lead Time", f"{state_row['Avg_Lead_Time']:.1f}d")
            kcol3.metric("Delay Rate", f"{state_row['Delay_Rate']*100:.1f}%")
            kcol4.metric(
                "Efficiency Score",
                f"{state_row['Efficiency_Score']:.1f}/100",
                help=f"Rank {rank} of {n_states_ranked} states/provinces in the current filter selection.",
            )

            st.markdown(heading_html("factory", "Factories Serving This State", level="h4"), unsafe_allow_html=True)
            factory_breakdown = (
                state_df.groupby("Factory")
                .agg(
                    Shipments=("Row ID", "count"),
                    Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
                    Delay_Rate=("Is Delayed", "mean"),
                )
                .reset_index()
                .sort_values("Shipments", ascending=False)
            )
            st.dataframe(
                factory_breakdown.rename(columns={
                    "Avg_Lead_Time": "Avg Lead Time (d)", "Delay_Rate": "Delay Rate",
                }).style.format({"Avg Lead Time (d)": "{:.1f}", "Delay Rate": "{:.1%}"}),
                use_container_width=True, hide_index=True,
            )

            st.markdown(heading_html("trend", "Monthly Trend", level="h4"), unsafe_allow_html=True)
            st.caption(
                f"Average shipping lead time to {selected_state}, by month. "
                "The dashed line marks your current delay threshold."
            )

            monthly = state_df.copy()
            monthly["Month"] = monthly["Order Date"].dt.to_period("M").dt.to_timestamp()
            monthly = (
                monthly.groupby("Month")
                .agg(Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"), Shipments=("Row ID", "count"))
                .reset_index()
            )

            fig_trend = px.line(
                monthly, x="Month", y="Avg_Lead_Time", markers=True,
                labels={"Avg_Lead_Time": "Avg Lead Time (days)"},
            )
            fig_trend.update_traces(line_color=GOLD, marker=dict(color=ESPRESSO, size=7))
            fig_trend.add_hline(
                y=delay_threshold, line_dash="dash", line_color=TERRACOTTA,
                annotation_text="Delay threshold", annotation_position="top left",
            )
            fig_trend.update_layout(**PLOTLY_LAYOUT, height=320)
            st.plotly_chart(fig_trend, use_container_width=True)

            fig_volume = px.bar(
                monthly, x="Month", y="Shipments",
                labels={"Shipments": "Shipments per Month"},
            )
            fig_volume.update_traces(marker_color=GOLD)
            fig_volume.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig_volume, use_container_width=True)

elif active_section == "Findings":
    st.markdown(heading_html("lightbulb", "Key Findings"), unsafe_allow_html=True)

    findings = generate_findings(filtered, reliable_routes)

    if not findings:
        st.info("Not enough data in the current selection to generate findings. Try widening your filters.")
    else:
        tone_config = {
            "risk": (TERRACOTTA, "!", "RISK"),
            "warn": (TERRACOTTA, "!", "RISK"),
            "neutral": (GOLD, "i", "CONTEXT"),
            "good": (SAGE, "\u2713", "STRENGTH"),
        }
        for tone, title, detail in findings:
            color, icon, label = tone_config.get(tone, (GOLD, "i", "CONTEXT"))
            r, g, b = hex_to_rgb(color)
            tint = f"rgba({r},{g},{b},0.08)"
            st.markdown(
                f"""<div style="display:flex; align-items:flex-start; gap:14px;
                    background-color:{tint}; border:1px solid {color}33;
                    border-radius:8px; padding:16px 20px; margin-bottom:14px;">
                    <div style="flex-shrink:0; width:32px; height:32px; border-radius:50%;
                        background-color:{color}; color:white; font-family:'Playfair Display',serif;
                        font-weight:700; font-size:1.05rem; display:flex; align-items:center;
                        justify-content:center;">{icon}</div>
                    <div>
                        <div style="font-size:0.65rem; letter-spacing:0.08em; font-weight:700;
                            color:{color}; margin-bottom:3px;">{label}</div>
                        <div style="font-weight:700; color:{ESPRESSO}; font-size:1.02rem;
                            margin-bottom:4px;">{title}</div>
                        <div style="font-size:0.92rem; color:{MUTED}; line-height:1.5;">{detail}</div>
                    </div>
                    </div>""",
                unsafe_allow_html=True,
            )
# =====================================================================
# FOOTER
# =====================================================================
st.divider()