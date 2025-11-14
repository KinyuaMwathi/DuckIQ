# streamlit_app/promo_dashboard.py
import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import os, tempfile, shutil

DB_PATH = "data/duckiq.duckdb"

# Prevent double config in unified mode
if "promo_configured" not in st.session_state:
    st.set_page_config(page_title="DuckIQ - Promotions Dashboard", layout="wide")
    st.session_state["promo_configured"] = True

# ---------------------------------------------------------
# WRAPPER FUNCTION
# ---------------------------------------------------------
def render_promo_dashboard():

    st.title("🦆 DuckIQ — Promotions & Performance Dashboard")
    st.caption("Understand promotional impact, uplift, and coverage across SKUs and suppliers.")

    # ---------------------------------------------------------
    # Load promo summary results directly from DuckDB
    # ---------------------------------------------------------
    @st.cache_data(ttl=60)
    def load_promo_data():
        """Safe load from DuckDB with Windows file-lock avoidance."""
        try:
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb").name
            shutil.copy(DB_PATH, tmp_file)

            con = duckdb.connect(tmp_file, read_only=True)
            df = con.execute("SELECT * FROM promo_summary_scores").fetchdf()
            con.close()
            os.remove(tmp_file)

            if "run_timestamp" in df.columns:
                df["run_timestamp"] = pd.to_datetime(df["run_timestamp"])

            return df

        except Exception as e:
            st.error(f"Error loading promo_summary_scores: {e}")
            return pd.DataFrame()

    df = load_promo_data()

    if df.empty:
        st.warning("No promo data found. Run /promo_summary to generate metrics.")
        st.stop()

    # Always show latest run (consistent with other dashboards)
    latest_ts = df["run_timestamp"].max()
    latest_df = df[df["run_timestamp"] == latest_ts].copy()

    # ---------------------------------------------------------
    # Summary Metrics
    # ---------------------------------------------------------
    st.markdown("### 📊 Promotion Summary")

    avg_uplift = latest_df["Promo_Uplift_%"].mean()
    avg_coverage = latest_df["Promo_Coverage_%"].mean()
    sku_count = latest_df["Item_Code"].nunique()

    cols = st.columns(3)
    cols[0].metric("Avg Promo Uplift (%)", f"{avg_uplift:.1f}")
    cols[1].metric("Avg Promo Coverage (%)", f"{avg_coverage:.1f}")
    cols[2].metric("SKUs Analyzed", sku_count)

    st.markdown("---")

    # ---------------------------------------------------------
    # Generate Insights (mirrors FastAPI logic)
    # ---------------------------------------------------------
    st.markdown("### 💡 Key Commercial Insights")

    insights = []

    # Top SKU uplift
    top_sku = latest_df.sort_values("Promo_Uplift_%", ascending=False).head(1)
    if not top_sku.empty:
        insights.append(
            f"Top performing SKU: **{top_sku['Description'].iloc[0]}** "
            f"with uplift **{top_sku['Promo_Uplift_%'].iloc[0]:.1f}%**."
        )

    # Low coverage
    if avg_coverage < 30:
        insights.append("Low promo coverage — consider expanding store participation.")

    # Weak discounting
    if latest_df["Promo_Price_Impact_%"].mean() < 5:
        insights.append("Discount depth appears shallow — promos may not be compelling enough.")

    if not insights:
        insights.append("Promotions look stable with no major issues.")

    for i in insights:
        st.success(f"✅ {i}")

    st.markdown("---")

    # ---------------------------------------------------------
    # Data cleanup
    # ---------------------------------------------------------
    numeric_cols = ["Promo_Uplift_%", "Promo_Coverage_%", "Promo_Price_Impact_%"]
    for col in numeric_cols:
        latest_df[col] = pd.to_numeric(latest_df[col], errors="coerce")

    # ---------------------------------------------------------
    # Visualizations
    # ---------------------------------------------------------
    st.subheader("📈 Promotions Performance Visualization")

    col1, col2 = st.columns(2)

    # Scatter: Coverage vs Uplift
    with col1:
        st.markdown("#### 🎯 Promo Uplift vs Coverage")
        fig1 = px.scatter(
            latest_df,
            x="Promo_Coverage_%",
            y="Promo_Uplift_%",
            color="Supplier",
            size="Promo_Price_Impact_%",
            hover_name="Description",
            title=f"Promo Coverage vs Uplift (%) — Latest Run ({latest_ts})",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig1.update_layout(
            xaxis_title="Promo Coverage (%)",
            yaxis_title="Promo Uplift (%)"
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Top 10 uplift bar chart
    with col2:
        st.markdown("#### 🏆 Top 10 SKUs by Promo Uplift")
        top_skus = latest_df.sort_values("Promo_Uplift_%", ascending=False).head(10)
        fig2 = px.bar(
            top_skus,
            x="Promo_Uplift_%",
            y="Description",
            orientation="h",
            color="Supplier",
            text="Promo_Uplift_%",
            color_discrete_sequence=px.colors.qualitative.Vivid,
            title="Top Performing SKUs by Uplift (%)"
        )
        fig2.update_layout(
            yaxis_title="SKU",
            xaxis_title="Uplift (%)",
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ---------------------------------------------------------
    # Data table
    # ---------------------------------------------------------
    st.markdown("### 🧾 Detailed SKU Performance")

    st.dataframe(
        latest_df[[ 
            "Item_Code",
            "Description",
            "Supplier",
            "Promo_Uplift_%",
            "Promo_Coverage_%",
            "Promo_Price_Impact_%",
            "Baseline_Avg_Price",
            "Promo_Avg_Price"
        ]].sort_values("Promo_Uplift_%", ascending=False),
        use_container_width=True,
        height=500
    )

    st.markdown("---")
    st.caption(f"Source: DuckDB promo_summary_scores — Latest Run: {latest_ts}")