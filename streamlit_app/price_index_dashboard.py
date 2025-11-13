# streamlit_app/price_index_dashboard.py
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from datetime import datetime
import os, tempfile, shutil

DB_PATH = "data/duckiq.duckdb"

st.set_page_config(page_title="DuckIQ - Price Index Dashboard", layout="wide")

st.title("🦆 DuckIQ — Price Index Dashboard")
st.caption("Compare Bidco’s pricing vs competitors per store, sub-department, and section.")

# --- Load Data Safely ---
def load_price_index_data():
    try:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb").name
        shutil.copy(DB_PATH, tmp_file)
        con = duckdb.connect(tmp_file, read_only=True)
        df = con.execute("SELECT * FROM price_index_scores").fetchdf()
        con.close()
        os.remove(tmp_file)
        if "run_timestamp" in df.columns:
            df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])
        return df
    except Exception as e:
        st.error(f"Error reading price_index_scores: {e}")
        return pd.DataFrame()

df = load_price_index_data()

if df.empty:
    st.warning("No price index data found. Run /price_index to generate results.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
store_filter = st.sidebar.selectbox("Select Store", ["All"] + sorted(df["Store_Name"].dropna().unique().tolist()))
subdept_filter = st.sidebar.selectbox("Select Sub-Department", ["All"] + sorted(df["Sub_Department"].dropna().unique().tolist()))

filtered_df = df.copy()
if store_filter != "All":
    filtered_df = filtered_df[filtered_df["Store_Name"] == store_filter]
if subdept_filter != "All":
    filtered_df = filtered_df[filtered_df["Sub_Department"] == subdept_filter]

# --- Summary Metrics ---
st.subheader("📊 Summary Metrics")

latest_run = filtered_df.sort_values("run_timestamp").tail(1)
avg_index = latest_run["Price_Index"].mean()
avg_discount = latest_run["Bidco_vs_RRP_Discount"].mean()

position = (
    "🟥 Premium" if avg_index > 105 else
    "🟨 Near-Market" if 95 <= avg_index <= 105 else
    "🟩 Discounted"
)

cols = st.columns(3)
cols[0].metric("Avg Price Index", f"{avg_index:.1f}")
cols[1].metric("Avg Discount vs RRP (%)", f"{avg_discount:.1f}")
cols[2].metric("Overall Position", position)

st.markdown("---")

# --- Heatmap: Store vs Price Index ---
st.subheader("🏪 Store-Level Price Index Heatmap")

heatmap_df = (
    latest_run.groupby(["Store_Name", "Sub_Department"])
    .agg({"Price_Index": "mean"})
    .reset_index()
)

if not heatmap_df.empty:
    fig = px.density_heatmap(
        heatmap_df,
        x="Sub_Department",
        y="Store_Name",
        z="Price_Index",
        color_continuous_scale=["#00B050", "#FFFF00", "#FF0000"],
        title="Bidco Price Index by Store and Sub-Department",
        nbinsx=20
    )
    fig.update_layout(
        xaxis_title="Sub-Department",
        yaxis_title="Store",
        coloraxis_colorbar=dict(title="Price Index"),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No sufficient data for store-level comparison.")

# --- Scatter: Bidco Realised Price vs RRP ---
st.subheader("💰 Bidco Realised Price vs RRP")

scatter_df = latest_run.copy()
scatter_df["Discount_Factor"] = scatter_df["Bidco_Avg_Unit_Price"] / scatter_df["Bidco_Avg_RRP"] * 100

fig2 = px.scatter(
    scatter_df,
    x="Bidco_Avg_RRP",
    y="Bidco_Avg_Unit_Price",
    color="Price_Index",
    hover_data=["Store_Name", "Sub_Department", "Section"],
    title="Bidco Realised Price vs RRP by Store/Sub-Department",
    color_continuous_scale="RdYlGn_r"
)
fig2.update_layout(
    xaxis_title="RRP (KES)",
    yaxis_title="Realised Unit Price (KES)",
    template="plotly_white"
)
st.plotly_chart(fig2, use_container_width=True)

# --- Detailed Table ---
st.markdown("### 🧾 Detailed Price Index Results")
st.dataframe(
    latest_run.sort_values("Price_Index"),
    use_container_width=True,
    height=400
)

st.markdown("---")
st.caption("Data source: DuckIQ price_index_scores (DuckDB)")