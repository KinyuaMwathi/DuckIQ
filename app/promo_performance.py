# app/promo_performance.py
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from .db import get_db

EAT_TZ = pytz.timezone("Africa/Nairobi")

def compute_promo_metrics():
    conn = get_db()
    df = conn.execute("SELECT * FROM sales").fetchdf()

    if df.empty:
        return {"error": "No data found in sales table."}

    # --- Clean & compute derived fields ---
    df["unit_price"] = df["Total Sales"] / df["Quantity"].replace(0, np.nan)
    df["Date Of Sale"] = pd.to_datetime(df["Date Of Sale"], errors="coerce")
    df = df.dropna(subset=["RRP", "Quantity", "Total Sales"])
    
    # Identify promo flag (price < 90% of RRP)
    df["is_promo"] = df["unit_price"] < (0.9 * df["RRP"])
    
    # Group baseline (non-promo) vs promo per SKU
    sku_groups = []
    for sku, group in df.groupby("Item_Code"):
        promo = group[group["is_promo"]]
        base = group[~group["is_promo"]]

        if len(base) == 0 or len(promo) == 0:
            continue  # skip SKUs with no variation

        # Compute metrics
        baseline_units = base["Quantity"].mean()
        promo_units = promo["Quantity"].mean()
        promo_uplift = ((promo_units - baseline_units) / baseline_units) * 100 if baseline_units > 0 else np.nan

        promo_stores = promo["Store Name"].nunique()
        total_stores = group["Store Name"].nunique()
        promo_coverage = (promo_stores / total_stores) * 100 if total_stores > 0 else 0

        promo_price_impact = (promo["unit_price"].mean() / promo["RRP"].mean()) * 100
        base_avg_price = base["unit_price"].mean()
        promo_avg_price = promo["unit_price"].mean()

        sku_groups.append({
            "Item_Code": sku,
            "Description": group["Description"].iloc[0],
            "Supplier": group["Supplier"].iloc[0],
            "Promo_Uplift_%": round(promo_uplift, 2),
            "Promo_Coverage_%": round(promo_coverage, 2),
            "Promo_Price_Impact_%": round(promo_price_impact, 2),
            "Baseline_Avg_Price": round(base_avg_price, 2),
            "Promo_Avg_Price": round(promo_avg_price, 2)
        })

    results_df = pd.DataFrame(sku_groups)
    if results_df.empty:
        return {"message": "No significant promo patterns detected."}

    # Identify top performing SKUs
    top_skus = results_df.sort_values("Promo_Uplift_%", ascending=False).head(5).to_dict(orient="records")

    # Compute summary insights for a Bidco stakeholder
    avg_uplift = results_df["Promo_Uplift_%"].mean()
    avg_coverage = results_df["Promo_Coverage_%"].mean()

    insights = [
        f"Avg Promo Uplift across SKUs: {avg_uplift:.1f}%",
        f"Avg Promo Coverage across stores: {avg_coverage:.1f}%",
        f"Top performing SKU: {top_skus[0]['Description']} ({top_skus[0]['Promo_Uplift_%']}% uplift)"
    ]

    return {
        "run_timestamp": datetime.now(EAT_TZ).isoformat(),
        "summary": {
            "avg_promo_uplift_%": round(avg_uplift, 2),
            "avg_promo_coverage_%": round(avg_coverage, 2),
            "sku_count": len(results_df)
        },
        "top_skus": top_skus,
        "insights": insights,
        "details": results_df.to_dict(orient="records")
    }