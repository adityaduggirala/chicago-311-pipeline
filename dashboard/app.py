"""Streamlit dashboard over the DuckDB marts.  Run: streamlit run dashboard/app.py"""
import sys
from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pipeline import config  # noqa: E402

st.set_page_config(page_title="Chicago 311 Analytics", layout="wide")
st.title("Chicago 311 Service Requests")

if not config.DB_PATH.exists():
    st.error("No warehouse found. Run `python -m pipeline.run --source sample` first.")
    st.stop()

con = duckdb.connect(str(config.DB_PATH), read_only=True)
q = lambda sql: con.execute(sql).df()

kpi = q("SELECT count(*) total, count(*) FILTER (WHERE is_open) open_, round(median(resolution_hours),1) med FROM fct_requests")
c1, c2, c3 = st.columns(3)
c1.metric("Total requests", f"{int(kpi.total[0]):,}")
c2.metric("Currently open", f"{int(kpi.open_[0]):,}")
c3.metric("Median resolution (hrs)", kpi.med[0])

trend = q("SELECT * FROM mart_volume_trend")
st.plotly_chart(px.line(trend, x="created_date", y=["requests", "rolling_7d_avg"], title="Daily volume"), width="stretch")

left, right = st.columns(2)
sla = q("SELECT * FROM mart_resolution_by_type ORDER BY median_hours DESC")
left.plotly_chart(px.bar(sla, x="sr_type", y=["median_hours", "p90_hours"], barmode="group", title="Resolution time by type"), width="stretch")
ward = q("SELECT * FROM mart_ward_backlog ORDER BY open_requests DESC LIMIT 15")
right.plotly_chart(px.bar(ward, x="ward", y="open_requests", title="Top 15 wards by open backlog"), width="stretch")
