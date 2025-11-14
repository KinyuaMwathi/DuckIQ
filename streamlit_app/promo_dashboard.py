# streamlit_app/promotions_dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="DuckIQ - Promotions Dashboard", layout="wide")

st.title("🦆 DuckIQ — Promotions & Performance Dashboard")
st.caption("Understand promotional impact, uplift, and coverage across SKUs and suppliers.")

# --- Load Data from FastAPI ---
@st.cache_data(ttl=60)
def fetch_promo_data():
    try:
        response = requests.get(f"{API_BASE_URL}/promo_summary")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API returned status {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}

data = fetch_promo_data()

if not data or "details" not in data:
    st.warning("No promo data found. Run /promo_summary first.")
    st.stop()

# --- Display Summary Metrics ---
st.markdown("### 📊 Promotion Summary")
cols = st.columns(3)
cols[0].metric("Avg Promo Uplift (%)", f"{data['summary']['avg_promo_uplift_%']:.1f}")
cols[1].metric("Avg Promo Coverage (%)", f"{data['summary']['avg_promo_coverage_%']:.1f}")
cols[2].metric("SKUs Analyzed", data["summary"]["sku_count"])

st.markdown("---")

# --- Key Commercial Insights ---
st.markdown("### 💡 Key Commercial Insights")
for insight in data["insights"]:
    st.success(f"✅ {insight}")

st.markdown("---")

# --- Detailed SKU Data ---
df = pd.DataFrame(data["details"])

# Handle missing values gracefully
numeric_cols = ["Promo_Uplift_%", "Promo_Coverage_%", "Promo_Price_Impact_%"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Visualizations ---
st.subheader("📈 Promotions Performance Visualization")

col1, col2 = st.columns(2)

# Scatter Plot — Coverage vs Uplift
with col1:
    st.markdown("#### 🎯 Promo Uplift vs Coverage")
    fig1 = px.scatter(
        df,
        x="Promo_Coverage_%",
        y="Promo_Uplift_%",
        color="Supplier",
        size="Promo_Price_Impact_%",
        hover_name="Description",
        title="Promo Coverage vs Uplift (%) per SKU",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig1.update_layout(xaxis_title="Promo Coverage (%)", yaxis_title="Promo Uplift (%)")
    st.plotly_chart(fig1, use_container_width=True)

# Bar Chart — Top 10 SKUs by Uplift
with col2:
    st.markdown("#### 🏆 Top 10 SKUs by Promo Uplift")
    top_skus = df.sort_values("Promo_Uplift_%", ascending=False).head(10)
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
    fig2.update_layout(yaxis_title="SKU", xaxis_title="Uplift (%)", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# --- Data Table ---
st.markdown("### 🧾 Detailed SKU Performance")
st.dataframe(
    df[[
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
st.caption("Source: DuckIQ /promo_summary API — auto-generated from DuckDB dataset.")