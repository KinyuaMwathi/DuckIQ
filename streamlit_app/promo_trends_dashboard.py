# streamlit_app/promo_trends_dashboard.py
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from datetime import datetime

DB_PATH = "data/duckiq.duckdb"

st.set_page_config(page_title="DuckIQ - Promo Trends Dashboard", layout="wide")

st.title("🦆 DuckIQ — Promo Trends Dashboard")
st.caption("Monitor the evolution of promotional performance metrics over time.")

# --- Load Data ---
def load_promo_history():
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        df = con.execute("SELECT * FROM promo_summary_scores").fetchdf()
        con.close()
    except Exception as e:
        st.error(f"Error reading promo_summary_scores: {e}")
        return pd.DataFrame()

    if "run_timestamp" in df.columns:
        df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])

    return df


df = load_promo_history()

if df.empty:
    st.warning("No promo data found. Run /promo_summary a few times to generate historical runs.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
supplier_filter = st.sidebar.selectbox(
    "Select Supplier",
    options=["All"] + sorted(df["Supplier"].dropna().unique().tolist())
)
sku_filter = st.sidebar.selectbox(
    "Select SKU",
    options=["All"] + sorted(df["Description"].dropna().unique().tolist())
)

filtered_df = df.copy()
if supplier_filter != "All":
    filtered_df = filtered_df[filtered_df["Supplier"] == supplier_filter]
if sku_filter != "All":
    filtered_df = filtered_df[filtered_df["Description"] == sku_filter]

# --- Aggregate per run ---
trend_df = (
    filtered_df.groupby("run_timestamp")
    .agg({
        "Promo_Uplift_%": "mean",
        "Promo_Coverage_%": "mean",
        "Promo_Price_Impact_%": "mean"
    })
    .reset_index()
    .rename(columns={
        "Promo_Uplift_%": "Avg_Uplift_%", 
        "Promo_Coverage_%": "Avg_Coverage_%", 
        "Promo_Price_Impact_%": "Avg_Price_Impact_%"
    })
)

# --- Overview Metrics ---
st.subheader("📊 Current Averages")
latest_run = trend_df.sort_values("run_timestamp").tail(1)
cols = st.columns(3)
cols[0].metric("Avg Promo Uplift (%)", f"{latest_run['Avg_Uplift_%'].iloc[0]:.1f}")
cols[1].metric("Avg Promo Coverage (%)", f"{latest_run['Avg_Coverage_%'].iloc[0]:.1f}")
cols[2].metric("Avg Promo Price Impact (%)", f"{latest_run['Avg_Price_Impact_%'].iloc[0]:.1f}")

st.markdown("---")

# --- Trend Line Chart ---
st.subheader("📈 Promo Performance Over Time")

fig = px.line(
    trend_df,
    x="run_timestamp",
    y=["Avg_Uplift_%", "Avg_Coverage_%", "Avg_Price_Impact_%"],
    markers=True,
    title="Promo KPI Trends Over Time",
    color_discrete_map={
        "Avg_Uplift_%": "#0078D4",
        "Avg_Coverage_%": "#00B050",
        "Avg_Price_Impact_%": "#FF7A00"
    }
)
fig.update_layout(
    yaxis_title="Metric Value (%)",
    xaxis_title="Run Timestamp",
    legend_title="Metric",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# --- Historical Summary Table ---
st.markdown("### 🧾 Historical Promo Summary")
trend_df_display = trend_df.sort_values("run_timestamp", ascending=False)
st.dataframe(trend_df_display, use_container_width=True, height=400)

st.markdown("---")
st.caption("Data source: DuckIQ promo_summary_scores (DuckDB)")