# streamlit_app/data_health_dashboard.py
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from datetime import datetime

DB_PATH = "data/duckiq.duckdb"

# Prevent set_page_config from being called twice when included in app.py
if "data_health_configured" not in st.session_state:
    st.set_page_config(page_title="DuckIQ Data Health Dashboard", layout="wide")
    st.session_state["data_health_configured"] = True

# ----------------------------------------------------------------
# WRAPPER FUNCTION (New)
# ----------------------------------------------------------------
def render_data_health_dashboard():

    # --- Sidebar ---
    st.sidebar.header("🔍 View Selection")
    view = st.sidebar.radio(
        "Select View",
        ["Overview", "Store Health", "Supplier Health"],
        help="Switch between data health summaries."
    )
    st.sidebar.caption(f"📦 Database: `{DB_PATH}`")

    # --- Helper functions ---
    @st.cache_data(ttl=60)
    def load_table(table_name: str) -> pd.DataFrame:
        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            df = con.execute(f"SELECT * FROM {table_name}").fetchdf()
        except Exception:
            df = pd.DataFrame()
        con.close()
        if "run_timestamp" in df.columns:
            df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])
        return df

    def format_score_color(score: float) -> str:
        if score >= 90:
            return "✅"
        elif score >= 80:
            return "🟡"
        else:
            return "🔴"

    # --- Layout ---
    st.title("🦆 DuckIQ — Data Health Monitoring")
    st.caption("Track and compare store & supplier data reliability over time.")

    # Load data
    store_df = load_table("store_health_scores")
    supplier_df = load_table("supplier_health_scores")

    # ----------------------------------------------------------------
    # OVERVIEW TAB
    # ----------------------------------------------------------------
    if view == "Overview":
        st.subheader("📊 Data Health Overview")

        if store_df.empty and supplier_df.empty:
            st.warning("No data found in DuckDB. Run /data_health and /supplier_health first.")
            st.stop()

        # --- Compute averages per run ---
        overview_records = []
        if not store_df.empty:
            s_avg = store_df.groupby("run_timestamp")["score"].mean().reset_index()
            s_avg["type"] = "Store"
            overview_records.append(s_avg)
        if not supplier_df.empty:
            sup_avg = supplier_df.groupby("run_timestamp")["score"].mean().reset_index()
            sup_avg["type"] = "Supplier"
            overview_records.append(sup_avg)

        if not overview_records:
            st.info("No health score data available yet.")
            st.stop()

        overview_df = pd.concat(overview_records)
        overview_df.sort_values("run_timestamp", inplace=True)

        # --- Latest snapshot cards ---
        cols = st.columns(2)
        if not store_df.empty:
            latest_store_score = store_df.sort_values("run_timestamp").groupby("store_name").tail(1)["score"].mean()
            cols[0].metric("🏬 Avg Store Health", f"{latest_store_score:.1f}", delta=None)
        if not supplier_df.empty:
            latest_sup_score = supplier_df.sort_values("run_timestamp").groupby("supplier").tail(1)["score"].mean()
            cols[1].metric("🏢 Avg Supplier Health", f"{latest_sup_score:.1f}", delta=None)

        # --- Trend chart ---
        st.markdown("### 📈 Average Health Score Over Time")
        fig = px.line(
            overview_df,
            x="run_timestamp",
            y="score",
            color="type",
            markers=True,
            title="Store vs Supplier Average Health Over Time",
            color_discrete_map={"Store": "#0078D4", "Supplier": "#FF7A00"}
        )
        fig.update_layout(
            yaxis_title="Average Health Score",
            xaxis_title="Run Timestamp",
            legend_title="Data Type",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Distribution snapshot ---
        st.markdown("### 📊 Latest Distribution of Scores")
        col1, col2 = st.columns(2)
        if not store_df.empty:
            latest_ts = store_df["run_timestamp"].max()
            latest_store = store_df[store_df["run_timestamp"] == latest_ts]
            fig_store = px.histogram(
                latest_store, x="score", nbins=20,
                title="Store Health Score Distribution",
                color_discrete_sequence=["#0078D4"]
            )
            col1.plotly_chart(fig_store, use_container_width=True)
        if not supplier_df.empty:
            latest_ts = supplier_df["run_timestamp"].max()
            latest_sup = supplier_df[supplier_df["run_timestamp"] == latest_ts]
            fig_sup = px.histogram(
                latest_sup, x="score", nbins=20,
                title="Supplier Health Score Distribution",
                color_discrete_sequence=["#FF7A00"]
            )
            col2.plotly_chart(fig_sup, use_container_width=True)

    # ----------------------------------------------------------------
    # STORE HEALTH TAB
    # ----------------------------------------------------------------
    elif view == "Store Health":
        st.subheader("🏬 Store-Level Data Health")
        if store_df.empty:
            st.warning("No store health data found. Run /data_health first.")
            st.stop()

        df_latest = store_df.sort_values("run_timestamp").groupby("store_name").tail(1)
        st.markdown("### 🧾 Latest Store Scores")
        df_latest["status"] = df_latest["score"].apply(format_score_color)
        st.dataframe(
            df_latest[["store_name", "score", "status", "missing_rrp_pct",
                       "missing_supplier_pct", "negative_qty_pct",
                       "extreme_price_pct", "notes"]],
            use_container_width=True
        )

        store_selected = st.selectbox("Select Store", sorted(store_df["store_name"].unique()))
        df_trend = store_df[store_df["store_name"] == store_selected]
        fig = px.line(
            df_trend, x="run_timestamp", y="score",
            title=f"{store_selected} — Health Score Trend",
            markers=True, color_discrete_sequence=["#0078D4"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------------------------------
    # SUPPLIER HEALTH TAB
    # ----------------------------------------------------------------
    else:
        st.subheader("🏢 Supplier-Level Data Health")
        if supplier_df.empty:
            st.warning("No supplier health data found. Run /supplier_health first.")
            st.stop()

        df_latest = supplier_df.sort_values("run_timestamp").groupby("supplier").tail(1)
        st.markdown("### 🧾 Latest Supplier Scores")
        df_latest["status"] = df_latest["score"].apply(format_score_color)
        st.dataframe(
            df_latest[["supplier", "score", "status", "missing_rrp_pct",
                       "negative_qty_pct", "extreme_price_pct",
                       "supplier_drift_flag", "notes"]]);
        
        # Drift summary
        st.markdown("### ⚠️ Supplier Drift Summary")
        drift_df = df_latest[df_latest["supplier_drift_flag"] == True]
        if drift_df.empty:
            st.success("No supplier drift detected ✅")
        else:
            st.error(f"{len(drift_df)} suppliers show drift:")
            st.dataframe(drift_df[["supplier", "notes", "score"]])

        # Trend chart
        sup_selected = st.selectbox("Select Supplier", sorted(supplier_df["supplier"].unique()))
        df_trend = supplier_df[supplier_df["supplier"] == sup_selected]
        fig = px.line(
            df_trend, x="run_timestamp", y="score",
            title=f"{sup_selected} — Health Score Trend",
            markers=True, color_discrete_sequence=["#FF7A00"]
        )
        st.plotly_chart(fig, use_container_width=True)