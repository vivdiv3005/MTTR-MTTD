# ⏱️ MTTR / MTTD Tracker

Track Mean Time to Detect (MTTD) and Mean Time to Respond/Resolve (MTTR) across your SOC incidents. Built with Streamlit + Plotly.

## Features
- **Trend charts** — MTTD and MTTR over time with median, P90 band, SLA reference lines, and regression trendline
- **SLA attainment** — breach % per period, attainment by severity, MTTD vs SLA comparison table
- **Breakdown** — MTTR by category, by team, box plot distribution, analyst leaderboard
- **Incident table** — searchable, filterable, CSV download
- **Paste data tab** — drop raw CSV directly in the browser, no file upload needed
- **Adjustable SLA targets** — sidebar sliders to tune P1–P4 thresholds
- **Period-over-period KPIs** — arrow indicators showing improvement or regression vs previous period

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/mttr-mttd-tracker.git
cd mttr-mttd-tracker
pip install -r requirements.txt
python generate_sample.py
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to share.streamlit.io → New app → select repo → app.py → Deploy

## Expected CSV Columns

| Column | Required | Description |
|--------|----------|-------------|
| `incident_id` | ✅ | e.g. INC-5001 |
| `severity` | ✅ | P1 / P2 / P3 / P4 |
| `category` | ✅ | Malware, Phishing… |
| `alert_time` | ✅ | 2026-01-15 08:22:00 |
| `detect_time` | ✅ | datetime |
| `resolve_time` | ✅ | datetime |
| `team` | optional | SOC Tier 1 |
| `analyst` | optional | alice.chen |
| `mttd_min` | optional | auto-computed if absent |
| `mttr_min` | optional | auto-computed if absent |

## SOC Dashboard Series
- ✅ SOC SLA Dashboard
- ✅ Threat Intelligence Map
- ✅ Insider Threat Scorer
- ✅ MTTR / MTTD Tracker  ← you are here
- 🔜 CVE Vulnerability Scanner
- 🔜 Log Anomaly Detector

## License
MIT
