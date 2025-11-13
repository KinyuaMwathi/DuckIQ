# app/supplier_health_engine.py
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
import pytz
from .db import get_db

EAT_TZ = pytz.timezone("Africa/Nairobi")

def ensure_supplier_health_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS supplier_health_scores (
            run_id VARCHAR,
            run_timestamp TIMESTAMP,
            supplier VARCHAR,
            score DOUBLE,
            missing_rrp_pct DOUBLE,
            missing_supplier_pct DOUBLE,
            negative_qty_pct DOUBLE,
            extreme_price_pct DOUBLE,
            supplier_drift_flag BOOLEAN,
            notes VARCHAR
        )
    """)

def compute_supplier_drift(df: pd.DataFrame):
    # A product having multiple suppliers indicates drift
    drift_summary = (
        df.groupby("Item_Code")["Supplier"]
        .nunique()
        .reset_index(name="unique_suppliers")
    )
    drift_items = drift_summary[drift_summary["unique_suppliers"] > 1]["Item_Code"].tolist()
    df["drift_flag"] = df["Item_Code"].isin(drift_items)
    return df

def compute_supplier_health():
    conn = get_db()
    df = conn.execute("SELECT * FROM sales").fetchdf()

    if df.empty:
        return {"error": "No data found in sales table."}

    # Compute unit price
    df["unit_price"] = df["Total Sales"] / df["Quantity"].replace(0, np.nan)
    df = compute_supplier_drift(df)

    suppliers = df["Supplier"].dropna().unique().tolist()
    results = []
    run_id = str(uuid.uuid4())
    run_ts = datetime.now(EAT_TZ)

    for supplier in suppliers:
        subset = df[df["Supplier"] == supplier]
        n = len(subset)
        if n == 0:
            continue

        # Missing %
        miss_rrp = subset["RRP"].isna().mean()
        miss_sup = subset["Supplier"].isna().mean()

        # Negative quantities
        neg_qty = (subset["Quantity"] < 0).mean()

        # Price outliers (IQR)
        q1 = subset["unit_price"].quantile(0.25)
        q3 = subset["unit_price"].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_pct = ((subset["unit_price"] < lower) | (subset["unit_price"] > upper)).mean()

        # Supplier drift
        drift_flag = bool(subset["drift_flag"].any())

        # Penalties
        missing_pen = min(20, (miss_rrp + miss_sup) * 100 * 0.2)
        negative_pen = min(20, neg_qty * 100 * 0.2)
        outlier_pen = min(20, outlier_pct * 100 * 0.2)
        drift_pen = 10 if drift_flag else 0

        score = max(0, 100 - (missing_pen + negative_pen + outlier_pen + drift_pen))

        notes = []
        if miss_rrp > 0.1: notes.append("RRP missing >10%")
        if neg_qty > 0: notes.append("Negative quantity present")
        if outlier_pct > 0.05: notes.append("High price variance")
        if drift_flag: notes.append("Supplier drift detected")

        results.append({
            "run_id": run_id,
            "run_timestamp": run_ts.isoformat(),
            "supplier": supplier,
            "score": round(score, 2),
            "missing_rrp_pct": round(miss_rrp * 100, 2),
            "missing_supplier_pct": round(miss_sup * 100, 2),
            "negative_qty_pct": round(neg_qty * 100, 2),
            "extreme_price_pct": round(outlier_pct * 100, 2),
            "supplier_drift_flag": drift_flag,
            "notes": "; ".join(notes)
        })

    ensure_supplier_health_table(conn)
    insert_df = pd.DataFrame(results)
    conn.register("tmp_sup_health", insert_df)
    conn.execute("""
        INSERT INTO supplier_health_scores
        SELECT run_id, run_timestamp, supplier, score,
               missing_rrp_pct, missing_supplier_pct,
               negative_qty_pct, extreme_price_pct,
               supplier_drift_flag, notes
        FROM tmp_sup_health
    """)
    conn.unregister("tmp_sup_health")

    avg_score = insert_df["score"].mean()
    return {
        "run_id": run_id,
        "run_timestamp": run_ts.isoformat(),
        "summary": {"avg_score": round(avg_score, 2), "total_suppliers": len(results)},
        "supplier_health": results
    }