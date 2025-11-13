# app/promo_performance.py
import pandas as pd
import numpy as np
import uuid
from datetime import datetime
import pytz
from .db import get_db

EAT_TZ = pytz.timezone("Africa/Nairobi")

def ensure_promo_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS promo_summary_scores (
            run_id VARCHAR,
            run_timestamp TIMESTAMP,
            Item_Code VARCHAR,
            Description VARCHAR,
            Supplier VARCHAR,
            "Promo_Uplift_%" DOUBLE,
            "Promo_Coverage_%" DOUBLE,
            "Promo_Price_Impact_%" DOUBLE,
            Baseline_Avg_Price DOUBLE,
            Promo_Avg_Price DOUBLE
        )
    """)

def compute_promo_metrics():
    conn = get_db()
    df = conn.execute("SELECT * FROM sales").fetchdf()

    if df.empty:
        return {"error": "No data found in sales table."}

    # Derived fields
    df["unit_price"] = df["Total Sales"] / df["Quantity"].replace(0, np.nan)
    df["Date Of Sale"] = pd.to_datetime(df["Date Of Sale"], errors="coerce")
    df = df.dropna(subset=["RRP", "Quantity", "Total Sales"])
    df["is_promo"] = df["unit_price"] < (0.9 * df["RRP"])

    sku_groups = []
    for sku, group in df.groupby("Item_Code"):
        promo = group[group["is_promo"]]
        base = group[~group["is_promo"]]

        if len(base) == 0 or len(promo) == 0:
            continue

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

    # Persist results to DuckDB
    ensure_promo_table(conn)
    run_id = str(uuid.uuid4())
    run_ts = datetime.now(EAT_TZ)

    results_df["run_id"] = run_id
    results_df["run_timestamp"] = run_ts

    conn.register("tmp_promo", results_df)
    conn.execute("""
        INSERT INTO promo_summary_scores
        SELECT run_id, run_timestamp, Item_Code, Description, Supplier,
               Promo_Uplift_%, Promo_Coverage_%, Promo_Price_Impact_%,
               Baseline_Avg_Price, Promo_Avg_Price
        FROM tmp_promo
    """)
    conn.unregister("tmp_promo")

    # Compute summary insights
    top_skus = results_df.sort_values("Promo_Uplift_%", ascending=False).head(5).to_dict(orient="records")
    avg_uplift = results_df["Promo_Uplift_%"].mean()
    avg_coverage = results_df["Promo_Coverage_%"].mean()

    insights = [
        f"Avg Promo Uplift across SKUs: {avg_uplift:.1f}%",
        f"Avg Promo Coverage across stores: {avg_coverage:.1f}%",
        f"Top performing SKU: {top_skus[0]['Description']} ({top_skus[0]['Promo_Uplift_%']}% uplift)"
    ]

    return {
        "run_id": run_id,
        "run_timestamp": run_ts.isoformat(),
        "summary": {
            "avg_promo_uplift_%": round(avg_uplift, 2),
            "avg_promo_coverage_%": round(avg_coverage, 2),
            "sku_count": len(results_df)
        },
        "top_skus": top_skus,
        "insights": insights,
        "details": results_df.to_dict(orient="records")
    }