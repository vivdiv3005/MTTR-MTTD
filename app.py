import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pathlib, io
from datetime import datetime, timedelta

st.set_page_config(
    page_title="MTTR / MTTD Tracker",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.kpi { background:#F8F9FA; border-radius:10px; padding:1rem 1.25rem; text-align:center; border:1px solid #E9ECEF; }
.kpi-val  { font-size:28px; font-weight:700; line-height:1.1; }
.kpi-lbl  { font-size:12px; color:#6C757D; margin-top:3px; }
.kpi-sub  { font-size:11px; margin-top:4px; }
.good  { color:#27500A; } .warn { color:#633806; } .bad { color:#791F1F; }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:600; }
.b-p1 { background:#FCEBEB; color:#791F1F; border:1px solid #F09595; }
.b-p2 { background:#FAEEDA; color:#633806; border:1px solid #EF9F27; }
.b-p3 { background:#E6F1FB; color:#0C447C; border:1px solid #85B7EB; }
.b-p4 { background:#EAF3DE; color:#27500A; border:1px solid #97C459; }
.b-ok { background:#EAF3DE; color:#27500A; border:1px solid #97C459; }
.b-br { background:#FCEBEB; color:#791F1F; border:1px solid #F09595; }
.trend-up   { color:#791F1F; font-weight:600; }
.trend-down { color:#27500A; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── SLA targets (minutes) ────────────────────
SLA = {
    "P1": {"detect": 5,   "respond": 30,  "resolve": 240},
    "P2": {"detect": 15,  "respond": 60,  "resolve": 480},
    "P3": {"detect": 30,  "respond": 240, "resolve": 1440},
    "P4": {"detect": 120, "respond": 480, "resolve": 4320},
}
SEV_COLORS = {"P1":"#E24B4A","P2":"#EF9F27","P3":"#378ADD","P4":"#639922"}
SAMPLE_PATH = pathlib.Path(__file__).parent / "sample_incidents.csv"

# ── helpers ──────────────────────────────────
def fmt_min(m):
    if pd.isna(m): return "—"
    m = int(m)
    if m < 60:   return f"{m}m"
    if m < 1440: return f"{m//60}h {m%60:02d}m"
    return f"{m//1440}d {(m%1440)//60}h"

def sla_color(val, target):
    if pd.isna(val): return "#888"
    r = val / target
    if r <= 1.0: return "#639922"
    if r <= 1.5: return "#EF9F27"
    return "#E24B4A"

def trend_pct(curr, prev):
    if prev == 0: return 0
    return round((curr - prev) / prev * 100, 1)

def load_data(src) -> pd.DataFrame:
    if isinstance(src, pathlib.Path):
        df = pd.read_csv(src)
    else:
        df = pd.read_csv(src)
    for col in ["alert_time","detect_time","respond_time","resolve_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "mttd_min" not in df.columns and "alert_time" in df.columns and "detect_time" in df.columns:
        df["mttd_min"] = (df["detect_time"] - df["alert_time"]).dt.total_seconds() / 60
    if "mttr_min" not in df.columns and "alert_time" in df.columns and "resolve_time" in df.columns:
        df["mttr_min"] = (df["resolve_time"] - df["alert_time"]).dt.total_seconds() / 60
    df["mttd_min"] = pd.to_numeric(df.get("mttd_min"), errors="coerce")
    df["mttr_min"] = pd.to_numeric(df.get("mttr_min"), errors="coerce")
    if "alert_time" in df.columns:
        df["week"]  = df["alert_time"].dt.to_period("W").dt.start_time
        df["month"] = df["alert_time"].dt.to_period("M").dt.start_time
    else:
        df["week"]  = pd.NaT
        df["month"] = pd.NaT
    for col in ["sla_detect_met","sla_respond_met","sla_resolve_met"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map({"true":True,"false":False}).fillna(False)
    return df

# ── sidebar ──────────────────────────────────
st.sidebar.title("⏱️ MTTR / MTTD Tracker")
st.sidebar.caption("Upload incident CSV or use built-in sample")

upload = st.sidebar.file_uploader("Upload incidents CSV", type=["csv"])

if "df" not in st.session_state:
    st.session_state.df    = load_data(SAMPLE_PATH)
    st.session_state.label = "sample_incidents.csv (built-in · 180 incidents)"

if upload:
    st.session_state.df    = load_data(upload)
    st.session_state.label = upload.name
elif st.sidebar.button("↺  Reset to sample data"):
    st.session_state.df    = load_data(SAMPLE_PATH)
    st.session_state.label = "sample_incidents.csv (built-in · 180 incidents)"

df_full = st.session_state.df.copy()

st.sidebar.divider()
st.sidebar.subheader("Filters")

sev_opts  = sorted(df_full["severity"].dropna().unique().tolist()) if "severity" in df_full.columns else []
sev_sel   = st.sidebar.multiselect("Severity", sev_opts, default=sev_opts)

cat_opts  = sorted(df_full["category"].dropna().unique().tolist()) if "category" in df_full.columns else []
cat_sel   = st.sidebar.multiselect("Category", cat_opts, default=cat_opts)

team_opts = sorted(df_full["team"].dropna().unique().tolist()) if "team" in df_full.columns else []
team_sel  = st.sidebar.multiselect("Team", team_opts, default=team_opts)

granularity = st.sidebar.radio("Trend granularity", ["Weekly","Monthly"], index=1)
time_col    = "week" if granularity == "Weekly" else "month"

st.sidebar.divider()
st.sidebar.subheader("SLA targets (minutes)")
for sev in ["P1","P2","P3"]:
    with st.sidebar.expander(f"{sev} targets"):
        SLA[sev]["detect"]  = st.number_input(f"Detect",  value=SLA[sev]["detect"],  key=f"d_{sev}", min_value=1)
        SLA[sev]["respond"] = st.number_input(f"Respond", value=SLA[sev]["respond"], key=f"r_{sev}", min_value=1)
        SLA[sev]["resolve"] = st.number_input(f"Resolve", value=SLA[sev]["resolve"], key=f"rv_{sev}",min_value=1)

# ── filter ───────────────────────────────────
df = df_full.copy()
if sev_sel  and "severity" in df.columns:  df = df[df["severity"].isin(sev_sel)]
if cat_sel  and "category" in df.columns:  df = df[df["category"].isin(cat_sel)]
if team_sel and "team"     in df.columns:  df = df[df["team"].isin(team_sel)]

# ── compute period-over-period ───────────────
periods = sorted(df[time_col].dropna().unique()) if time_col in df.columns else []
curr_df = df[df[time_col] == periods[-1]] if len(periods) >= 1 else df
prev_df = df[df[time_col] == periods[-2]] if len(periods) >= 2 else pd.DataFrame()

curr_mttd = curr_df["mttd_min"].median()
curr_mttr = curr_df["mttr_min"].median()
prev_mttd = prev_df["mttd_min"].median() if not prev_df.empty else curr_mttd
prev_mttr = prev_df["mttr_min"].median() if not prev_df.empty else curr_mttr
delta_mttd = trend_pct(curr_mttd, prev_mttd)
delta_mttr = trend_pct(curr_mttr, prev_mttr)

overall_mttd = df["mttd_min"].median()
overall_mttr = df["mttr_min"].median()

sla_det_rate  = df["sla_detect_met"].mean()  * 100 if "sla_detect_met"  in df.columns else None
sla_res_rate  = df["sla_resolve_met"].mean() * 100 if "sla_resolve_met" in df.columns else None

# ── PAGE ─────────────────────────────────────
st.title("⏱️ MTTR / MTTD Tracker")
st.caption(f"Source: {st.session_state.label}  ·  {len(df):,} incidents shown")

# ── KPI row ───────────────────────────────────
c1,c2,c3,c4,c5,c6 = st.columns(6)

def kpi_card(col, value, label, sub=None, color_class=""):
    col.markdown(
        f'<div class="kpi"><div class="kpi-val {color_class}">{value}</div>'
        f'<div class="kpi-lbl">{label}</div>'
        + (f'<div class="kpi-sub {color_class}">{sub}</div>' if sub else "")
        + "</div>",
        unsafe_allow_html=True
    )

arrow_mttd = ("▲ " if delta_mttd > 0 else "▼ ") + f"{abs(delta_mttd)}% vs prev"
arrow_mttr = ("▲ " if delta_mttr > 0 else "▼ ") + f"{abs(delta_mttr)}% vs prev"
cls_mttd   = "bad" if delta_mttd > 5 else "warn" if delta_mttd > 0 else "good"
cls_mttr   = "bad" if delta_mttr > 5 else "warn" if delta_mttr > 0 else "good"

kpi_card(c1, fmt_min(overall_mttd), "Median MTTD (all time)")
kpi_card(c2, fmt_min(overall_mttr), "Median MTTR (all time)")
kpi_card(c3, fmt_min(curr_mttd),    "MTTD (latest period)", arrow_mttd, cls_mttd)
kpi_card(c4, fmt_min(curr_mttr),    "MTTR (latest period)", arrow_mttr, cls_mttr)
kpi_card(c5, f"{sla_det_rate:.1f}%" if sla_det_rate is not None else "—",
         "Detect SLA attainment",
         color_class="good" if sla_det_rate and sla_det_rate>=95 else "warn" if sla_det_rate and sla_det_rate>=80 else "bad")
kpi_card(c6, f"{sla_res_rate:.1f}%" if sla_res_rate is not None else "—",
         "Resolve SLA attainment",
         color_class="good" if sla_res_rate and sla_res_rate>=95 else "warn" if sla_res_rate and sla_res_rate>=80 else "bad")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 Trend charts", "🎯 SLA attainment", "🔬 Breakdown", "📋 Incident table", "📥 Paste data"]
)

# ─── TAB 1 — TREND CHARTS ────────────────────
with tab1:
    if df.empty or time_col not in df.columns:
        st.warning("No data to display.")
    else:
        trend = (
            df.groupby(time_col)
              .agg(
                  mttd_median=("mttd_min","median"),
                  mttr_median=("mttr_min","median"),
                  mttd_p90   =("mttd_min", lambda x: x.quantile(0.9)),
                  mttr_p90   =("mttr_min", lambda x: x.quantile(0.9)),
                  incident_count=("mttd_min","count"),
              )
              .reset_index()
        )
        trend[time_col] = pd.to_datetime(trend[time_col])

        # MTTD trend
        fig_mttd = go.Figure()
        fig_mttd.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttd_p90"],
            name="P90", line=dict(width=0),
            fill=None, mode="lines", showlegend=False
        ))
        fig_mttd.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttd_median"],
            name="Median MTTD", mode="lines+markers",
            line=dict(color="#378ADD", width=2.5),
            fill="tonexty", fillcolor="rgba(55,138,221,0.08)",
            marker=dict(size=6),
        ))
        fig_mttd.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttd_p90"],
            name="P90 MTTD", mode="lines",
            line=dict(color="#378ADD", width=1, dash="dot"),
        ))
        # SLA reference lines
        for sev, cfg in SLA.items():
            fig_mttd.add_hline(
                y=cfg["detect"], line_dash="dash",
                line_color=SEV_COLORS[sev], opacity=0.5,
                annotation_text=f"{sev} SLA ({cfg['detect']}m)",
                annotation_position="right",
                annotation_font=dict(color=SEV_COLORS[sev], size=10),
            )
        # Trendline
        if len(trend) >= 3:
            x_num = np.arange(len(trend))
            coeffs = np.polyfit(x_num, trend["mttd_median"].ffill(), 1)
            tl = np.poly1d(coeffs)(x_num)
            fig_mttd.add_trace(go.Scatter(
                x=trend[time_col], y=tl,
                name="Trend", mode="lines",
                line=dict(color="#E24B4A", width=1.5, dash="longdash"),
            ))
        fig_mttd.update_layout(
            title="Mean Time to Detect (MTTD) over time",
            yaxis_title="Minutes", xaxis_title="",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=40,b=20,l=0,r=120), height=320,
            legend=dict(orientation="h", y=1.12, x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_mttd, use_container_width=True)

        # MTTR trend
        fig_mttr = go.Figure()
        fig_mttr.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttr_p90"],
            name="P90", line=dict(width=0),
            fill=None, mode="lines", showlegend=False,
        ))
        fig_mttr.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttr_median"],
            name="Median MTTR", mode="lines+markers",
            line=dict(color="#E24B4A", width=2.5),
            fill="tonexty", fillcolor="rgba(226,75,74,0.08)",
            marker=dict(size=6),
        ))
        fig_mttr.add_trace(go.Scatter(
            x=trend[time_col], y=trend["mttr_p90"],
            name="P90 MTTR", mode="lines",
            line=dict(color="#E24B4A", width=1, dash="dot"),
        ))
        for sev, cfg in SLA.items():
            fig_mttr.add_hline(
                y=cfg["resolve"], line_dash="dash",
                line_color=SEV_COLORS[sev], opacity=0.5,
                annotation_text=f"{sev} SLA ({fmt_min(cfg['resolve'])})",
                annotation_position="right",
                annotation_font=dict(color=SEV_COLORS[sev], size=10),
            )
        if len(trend) >= 3:
            coeffs2 = np.polyfit(x_num, trend["mttr_median"].ffill(), 1)
            tl2 = np.poly1d(coeffs2)(x_num)
            fig_mttr.add_trace(go.Scatter(
                x=trend[time_col], y=tl2,
                name="Trend", mode="lines",
                line=dict(color="#EF9F27", width=1.5, dash="longdash"),
            ))
        fig_mttr.update_layout(
            title="Mean Time to Respond/Resolve (MTTR) over time",
            yaxis_title="Minutes", xaxis_title="",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=40,b=20,l=0,r=120), height=320,
            legend=dict(orientation="h", y=1.12, x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_mttr, use_container_width=True)

        # Volume chart
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=trend[time_col], y=trend["incident_count"],
            marker_color="#EEEDFE", marker_line_color="#AFA9EC", marker_line_width=0.5,
            name="Incident count",
        ))
        fig_vol.update_layout(
            title="Incident volume",
            yaxis_title="Count", xaxis_title="",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=40,b=20,l=0,r=10), height=220,
        )
        st.plotly_chart(fig_vol, use_container_width=True)

# ─── TAB 2 — SLA ATTAINMENT ──────────────────
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("SLA attainment by severity")
        if "severity" in df.columns and "sla_resolve_met" in df.columns:
            sla_sev = (
                df.groupby("severity")
                  .agg(
                      total=("sla_resolve_met","count"),
                      met  =("sla_resolve_met","sum"),
                  )
                  .reset_index()
            )
            sla_sev["pct"]     = (sla_sev["met"] / sla_sev["total"] * 100).round(1)
            sla_sev["breached"]= sla_sev["total"] - sla_sev["met"]
            sla_sev["color"]   = sla_sev["pct"].apply(
                lambda p: "#639922" if p>=95 else "#EF9F27" if p>=80 else "#E24B4A")
            fig_sla = go.Figure(go.Bar(
                x=sla_sev["severity"], y=sla_sev["pct"],
                marker_color=sla_sev["color"],
                text=sla_sev["pct"].apply(lambda p: f"{p}%"),
                textposition="outside",
            ))
            fig_sla.add_hline(y=95, line_dash="dash", line_color="#3C3489",
                              annotation_text="95% target", annotation_position="right",
                              annotation_font_color="#3C3489")
            fig_sla.update_layout(
                yaxis=dict(range=[0,115], title="Attainment %"),
                xaxis_title="Severity",
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=10,b=10,l=0,r=80), height=300,
            )
            st.plotly_chart(fig_sla, use_container_width=True)

            st.dataframe(
                sla_sev[["severity","total","met","breached","pct"]].rename(columns={
                    "severity":"Severity","total":"Total","met":"Met","breached":"Breached","pct":"Attainment %"
                }),
                use_container_width=True, hide_index=True
            )

    with col_b:
        st.subheader("SLA breach trend")
        if time_col in df.columns and "sla_resolve_met" in df.columns:
            breach_trend = (
                df.groupby(time_col)
                  .agg(total=("sla_resolve_met","count"), met=("sla_resolve_met","sum"))
                  .reset_index()
            )
            breach_trend["breach_pct"] = ((breach_trend["total"]-breach_trend["met"])/breach_trend["total"]*100).round(1)
            breach_trend[time_col] = pd.to_datetime(breach_trend[time_col])

            fig_br = go.Figure()
            fig_br.add_trace(go.Bar(
                x=breach_trend[time_col], y=breach_trend["breach_pct"],
                marker_color=breach_trend["breach_pct"].apply(
                    lambda p: "#E24B4A" if p>20 else "#EF9F27" if p>10 else "#97C459"),
                name="Breach %",
                text=breach_trend["breach_pct"].apply(lambda p: f"{p}%"),
                textposition="outside",
            ))
            fig_br.add_hline(y=5, line_dash="dash", line_color="#639922",
                             annotation_text="Target ≤5%", annotation_position="right",
                             annotation_font_color="#639922")
            fig_br.update_layout(
                yaxis=dict(title="Breach %", range=[0, breach_trend["breach_pct"].max()*1.25+5]),
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=10,b=10,l=0,r=80), height=300,
            )
            st.plotly_chart(fig_br, use_container_width=True)

    # MTTD vs SLA comparison table
    st.subheader("MTTD / MTTR vs SLA by severity")
    if "severity" in df.columns:
        rows_sla = []
        for sev in ["P1","P2","P3","P4"]:
            sub = df[df["severity"]==sev]
            if sub.empty: continue
            med_mttd = sub["mttd_min"].median()
            med_mttr = sub["mttr_min"].median()
            sla_d    = SLA[sev]["detect"]
            sla_r    = SLA[sev]["resolve"]
            rows_sla.append({
                "Severity": sev,
                "Median MTTD": fmt_min(med_mttd),
                "MTTD SLA":    fmt_min(sla_d),
                "MTTD vs SLA": f"{'✅' if med_mttd<=sla_d else '⚠️'} {round(med_mttd/sla_d*100)}%",
                "Median MTTR": fmt_min(med_mttr),
                "MTTR SLA":    fmt_min(sla_r),
                "MTTR vs SLA": f"{'✅' if med_mttr<=sla_r else '⚠️'} {round(med_mttr/sla_r*100)}%",
                "Count": len(sub),
            })
        st.dataframe(pd.DataFrame(rows_sla), use_container_width=True, hide_index=True)

# ─── TAB 3 — BREAKDOWN ───────────────────────
with tab3:
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Median MTTR by category")
        if "category" in df.columns:
            cat_mttr = df.groupby("category")["mttr_min"].median().sort_values(ascending=True)
            fig_cat = go.Figure(go.Bar(
                x=cat_mttr.values, y=cat_mttr.index, orientation="h",
                marker_color="#E24B4A", text=cat_mttr.apply(fmt_min), textposition="outside",
            ))
            fig_cat.update_layout(
                xaxis_title="Median MTTR (minutes)", yaxis_title="",
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=10,b=10,l=0,r=60), height=340,
            )
            st.plotly_chart(fig_cat, use_container_width=True)

    with col_d:
        st.subheader("Median MTTR by team")
        if "team" in df.columns:
            team_mttr = df.groupby("team")["mttr_min"].median().sort_values(ascending=True)
            fig_team = go.Figure(go.Bar(
                x=team_mttr.values, y=team_mttr.index, orientation="h",
                marker_color="#7F77DD", text=team_mttr.apply(fmt_min), textposition="outside",
            ))
            fig_team.update_layout(
                xaxis_title="Median MTTR (minutes)", yaxis_title="",
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=10,b=10,l=0,r=60), height=340,
            )
            st.plotly_chart(fig_team, use_container_width=True)

    st.subheader("MTTD distribution — box plot by severity")
    if "severity" in df.columns:
        fig_box = px.box(
            df.dropna(subset=["mttd_min"]),
            x="severity", y="mttd_min",
            color="severity", color_discrete_map=SEV_COLORS,
            points="outliers",
            labels={"mttd_min":"MTTD (minutes)","severity":"Severity"},
            category_orders={"severity":["P1","P2","P3","P4"]},
        )
        for sev, cfg in SLA.items():
            fig_box.add_hline(
                y=cfg["detect"], line_dash="dot",
                line_color=SEV_COLORS[sev], opacity=0.6,
                annotation_text=f"{sev} target",
                annotation_font=dict(color=SEV_COLORS[sev], size=10),
            )
        fig_box.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=10,b=10,l=0,r=80), height=360,
            showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Analyst performance — median MTTR")
    if "analyst" in df.columns:
        analyst_df = (
            df.groupby("analyst")
              .agg(median_mttr=("mttr_min","median"),
                   total_incidents=("mttr_min","count"),
                   sla_rate=("sla_resolve_met","mean"))
              .reset_index()
              .sort_values("median_mttr")
        )
        analyst_df["sla_rate"] = (analyst_df["sla_rate"] * 100).round(1)
        analyst_df["median_mttr_fmt"] = analyst_df["median_mttr"].apply(fmt_min)
        st.dataframe(
            analyst_df[["analyst","total_incidents","median_mttr_fmt","sla_rate"]].rename(columns={
                "analyst":"Analyst","total_incidents":"Incidents",
                "median_mttr_fmt":"Median MTTR","sla_rate":"SLA Met %"
            }),
            use_container_width=True, hide_index=True
        )

# ─── TAB 4 — INCIDENT TABLE ──────────────────
with tab4:
    st.subheader("All incidents")

    search = st.text_input("Search by incident ID, category, or analyst", "")
    df_tbl = df.copy()
    if search:
        mask = df_tbl.apply(lambda r: search.lower() in str(r).lower(), axis=1)
        df_tbl = df_tbl[mask]

    show_cols = [c for c in [
        "incident_id","severity","category","team","analyst",
        "alert_time","mttd_min","mttr_min",
        "sla_detect_met","sla_resolve_met"
    ] if c in df_tbl.columns]

    df_show = df_tbl[show_cols].copy()
    df_show["mttd_fmt"] = df_show["mttd_min"].apply(fmt_min)
    df_show["mttr_fmt"] = df_show["mttr_min"].apply(fmt_min)
    df_show = df_show.drop(columns=["mttd_min","mttr_min"])

    def color_sev(val):
        return {
            "P1":"background-color:#FCEBEB;color:#791F1F;font-weight:600",
            "P2":"background-color:#FAEEDA;color:#633806;font-weight:600",
            "P3":"background-color:#E6F1FB;color:#0C447C;font-weight:600",
            "P4":"background-color:#EAF3DE;color:#27500A;font-weight:600",
        }.get(str(val),"")

    try:
        styled_tbl = df_show.style.map(color_sev, subset=["severity"])
    except AttributeError:
        styled_tbl = df_show.style.applymap(color_sev, subset=["severity"])

    st.dataframe(styled_tbl, use_container_width=True, hide_index=True,
        column_config={
            "incident_id":     st.column_config.TextColumn("ID"),
            "severity":        st.column_config.TextColumn("Sev"),
            "category":        st.column_config.TextColumn("Category"),
            "team":            st.column_config.TextColumn("Team"),
            "analyst":         st.column_config.TextColumn("Analyst"),
            "alert_time":      st.column_config.DatetimeColumn("Alert time", format="YYYY-MM-DD HH:mm"),
            "mttd_fmt":        st.column_config.TextColumn("MTTD"),
            "mttr_fmt":        st.column_config.TextColumn("MTTR"),
            "sla_detect_met":  st.column_config.CheckboxColumn("Detect SLA"),
            "sla_resolve_met": st.column_config.CheckboxColumn("Resolve SLA"),
        })

    csv_bytes = df_tbl.to_csv(index=False).encode()
    st.download_button("Download filtered incidents CSV", csv_bytes, "filtered_incidents.csv", "text/csv")

# ─── TAB 5 — PASTE DATA ──────────────────────
with tab5:
    st.subheader("Paste incident data")
    st.markdown("""
Paste a CSV directly into the box below — no file needed. Minimum required columns:

| Column | Example |
|--------|---------|
| `incident_id` | INC-5001 |
| `severity` | P1, P2, P3, P4 |
| `category` | Malware, Phishing… |
| `alert_time` | 2026-01-15 08:22:00 |
| `detect_time` | 2026-01-15 08:26:00 |
| `resolve_time` | 2026-01-15 11:55:00 |
| `team` *(optional)* | SOC Tier 1 |
| `analyst` *(optional)* | alice.chen |
""")

    sample_snippet = """incident_id,severity,category,alert_time,detect_time,resolve_time,team,analyst
INC-9001,P1,Ransomware,2026-06-01 02:10:00,2026-06-01 02:14:00,2026-06-01 05:45:00,IR Team,alice.chen
INC-9002,P2,Phishing,2026-06-02 09:30:00,2026-06-02 09:44:00,2026-06-02 17:10:00,SOC Tier 1,bob.martin
INC-9003,P3,Misconfiguration,2026-06-03 14:00:00,2026-06-03 14:22:00,2026-06-04 08:00:00,Cloud Security,carol.white
INC-9004,P1,Data Exfil,2026-06-04 03:14:00,2026-06-04 03:19:00,2026-06-04 07:00:00,IR Team,alice.chen
INC-9005,P2,Unauthorised Access,2026-06-05 11:00:00,2026-06-05 11:18:00,2026-06-05 19:30:00,SOC Tier 2,dave.jones"""

    pasted = st.text_area("Paste CSV here", value=sample_snippet, height=200)

    if st.button("▶  Analyse pasted data"):
        try:
            pasted_df = pd.read_csv(io.StringIO(pasted))
            st.session_state.df    = load_data(io.StringIO(pasted))
            st.session_state.label = f"Pasted data ({len(pasted_df)} incidents)"
            st.success(f"Loaded {len(pasted_df)} incidents. Switch to any tab to see the analysis.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not parse CSV: {e}")

    with st.expander("View expected CSV schema"):
        schema = pd.DataFrame([
            {"Column":"incident_id",    "Required":"✅","Type":"string", "Example":"INC-5001"},
            {"Column":"severity",       "Required":"✅","Type":"string", "Example":"P1 / P2 / P3 / P4"},
            {"Column":"category",       "Required":"✅","Type":"string", "Example":"Malware"},
            {"Column":"alert_time",     "Required":"✅","Type":"datetime","Example":"2026-01-15 08:22:00"},
            {"Column":"detect_time",    "Required":"✅","Type":"datetime","Example":"2026-01-15 08:26:00"},
            {"Column":"resolve_time",   "Required":"✅","Type":"datetime","Example":"2026-01-15 11:55:00"},
            {"Column":"respond_time",   "Required":"—", "Type":"datetime","Example":"Optional"},
            {"Column":"team",           "Required":"—", "Type":"string", "Example":"SOC Tier 1"},
            {"Column":"analyst",        "Required":"—", "Type":"string", "Example":"alice.chen"},
            {"Column":"mttd_min",       "Required":"—", "Type":"number", "Example":"4 (auto-computed if absent)"},
            {"Column":"mttr_min",       "Required":"—", "Type":"number", "Example":"225 (auto-computed if absent)"},
            {"Column":"sla_detect_met", "Required":"—", "Type":"bool",   "Example":"true/false"},
            {"Column":"sla_resolve_met","Required":"—", "Type":"bool",   "Example":"true/false"},
        ])
        st.dataframe(schema, use_container_width=True, hide_index=True)

st.divider()
st.caption("MTTR / MTTD Tracker · Built with Streamlit · Part of the SOC Dashboard Series")
