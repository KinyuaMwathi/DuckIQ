# streamlit_app/dashboard.py
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from datetime import datetime

DB_PATH = "data/duckiq.duckdb"

st.set_page_config(page_title="DuckIQ Data Health Dashboard", layout="wide")

# --- Sidebar ---
st.sidebar.header("🔍 Filters")
view = st.sidebar.radio("View Type", ["Store Health", "Supplier Health"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Database: `{DB_PATH}`")

# --- Helper functions ---
@st.cache_data(ttl=60)
def load_table(table_name: str) -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(f"SELECT * FROM {table_name}").fetchdf()
    con.close()
    if "run_timestamp" in df.columns:
        df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])
    return df

def format_score_color(score):
    if score >= 90:
        return "✅"
    elif score >= 80:
        return "🟡"
    else:
        return "🔴"

# --- Layout ---
st.title("🦆 DuckIQ — Data Health Monitoring")
st.caption("Track data reliability over time for stores and suppliers.")

if view == "Store Health":
    st.subheader("🏬 Store-Level Data Health")

    df = load_table("store_health_scores")
    if df.empty:
        st.warning("No store health data found. Run /data_health API first.")
        st.stop()

    # Latest scores per store
    df_latest = df.sort_values("run_timestamp").groupby("store_name").tail(1)

    st.markdown("### 📊 Latest Store Scores")
    df_latest_display = df_latest[["store_name", "score", "missing_rrp_pct", "missing_supplier_pct",
                                   "negative_qty_pct", "extreme_price_pct", "notes"]]
    df_latest_display["status"] = df_latest_display["score"].apply(format_score_color)
    st.dataframe(df_latest_display.sort_values("score", ascending=False), use_container_width=True)

    # Trend chart
    st.markdown("### 📈 Score Trend Over Time")
    store_selected = st.selectbox("Select Store", sorted(df["store_name"].unique()))
    df_trend = df[df["store_name"] == store_selected]
    fig = px.line(df_trend, x="run_timestamp", y="score", title=f"{store_selected} — Data Health Trend",
                  markers=True, color_discrete_sequence=["#0078D4"])
    fig.update_layout(yaxis_title="Health Score", xaxis_title="Run Timestamp")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.subheader("🏢 Supplier-Level Data Health")

    df = load_table("supplier_health_scores")
    if df.empty:
        st.warning("No supplier health data found. Run /supplier_health API first.")
        st.stop()

    df_latest = df.sort_values("run_timestamp").groupby("supplier").tail(1)

    st.markdown("### 📊 Latest Supplier Scores")
    df_latest_display = df_latest[["supplier", "score", "missing_rrp_pct", "negative_qty_pct",
                                   "extreme_price_pct", "supplier_drift_flag", "notes"]]
    df_latest_display["status"] = df_latest_display["score"].apply(format_score_color)
    st.dataframe(df_latest_display.sort_values("score", ascending=False), use_container_width=True)

    # Drift summary
    st.markdown("### ⚠️ Supplier Drift Summary")
    drift_df = df_latest[df_latest["supplier_drift_flag"] == True]
    if drift_df.empty:
        st.success("No supplier drift detected ✅")
    else:
        st.error(f"{len(drift_df)} suppliers show drift:")
        st.dataframe(drift_df[["supplier", "notes", "score"]])

    # Trend chart
    st.markdown("### 📈 Score Trend Over Time")
    sup_selected = st.selectbox("Select Supplier", sorted(df["supplier"].unique()))
    df_trend = df[df["supplier"] == sup_selected]
    fig = px.line(df_trend, x="run_timestamp", y="score", title=f"{sup_selected} — Data Health Trend",
                  markers=True, color_discrete_sequence=["#FF7A00"])
    fig.update_layout(yaxis_title="Health Score", xaxis_title="Run Timestamp")
    st.plotly_chart(fig, use_container_width=True)