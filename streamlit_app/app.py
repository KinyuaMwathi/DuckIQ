# streamlit_app/app.py

# --------------------------------------------------------------------
# 🔧 Bulletproof fix for Windows + Streamlit import issues
# Ensures the DuckIQ root folder is always on PYTHONPATH
# --------------------------------------------------------------------
import sys, os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st

# --------------------------------------------------------------------
# Page config (set once)
# --------------------------------------------------------------------
if "duckiq_home_configured" not in st.session_state:
    st.set_page_config(page_title="DuckIQ Unified Dashboard", layout="wide")
    st.session_state["duckiq_home_configured"] = True

# --------------------------------------------------------------------
# Header
# --------------------------------------------------------------------
st.title("🦆 DuckIQ — Unified Commercial Analytics Hub")
st.caption("Data Health • Promotions • Promo Trends • Pricing Index")

# --------------------------------------------------------------------
# Import dashboards (corrected import paths)
# Each dashboard now sits in the same folder as app.py
# --------------------------------------------------------------------
def safe_import(module_name, fn_name):
    try:
        module = __import__(module_name, fromlist=[fn_name])
        return getattr(module, fn_name)
    except Exception:
        return None

render_data_health_dashboard = safe_import("data_health_dashboard", "render_data_health_dashboard")
render_promo_dashboard = safe_import("promo_dashboard", "render_promo_dashboard")
render_promo_trends_dashboard = safe_import("promo_trends_dashboard", "render_promo_trends_dashboard")
render_price_index_dashboard = safe_import("price_index_dashboard", "render_price_index_dashboard")

# Optional: compact sidebar error summaries
with st.sidebar:
    if render_data_health_dashboard is None:
        st.warning("⚠ Data Health module unavailable")
    if render_promo_dashboard is None:
        st.warning("⚠ Promotions module unavailable")
    if render_promo_trends_dashboard is None:
        st.warning("⚠ Promo Trends module unavailable")
    if render_price_index_dashboard is None:
        st.warning("⚠ Price Index module unavailable")

# --------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Data Health",
    "🏷️ Promotions",
    "📈 Promo Trends",
    "💰 Pricing Index"
])

# --------------------------------------------------------------------
# Tab content
# --------------------------------------------------------------------
with tab1:
    if render_data_health_dashboard:
        render_data_health_dashboard()
    else:
        st.error("Data Health dashboard not available.")

with tab2:
    if render_promo_dashboard:
        render_promo_dashboard()
    else:
        st.error("Promotions dashboard not available.")

with tab3:
    if render_promo_trends_dashboard:
        render_promo_trends_dashboard()
    else:
        st.error("Promo Trends dashboard not available.")

with tab4:
    if render_price_index_dashboard:
        render_price_index_dashboard()
    else:
        st.error("Pricing Index dashboard not available.")

# --------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------
st.markdown("---")
st.caption("DuckIQ — All dashboards integrated in one UI.")