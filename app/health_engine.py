# app/health_engine.py
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
import pytz
from .db import get_db

EAT_TZ = pytz.timezone("Africa/Nairobi")

def ensure_health_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS store_health_scores (
            run_id VARCHAR,
            run_timestamp TIMESTAMP,
            store_name VARCHAR,
            score DOUBLE,
            missing_rrp_pct DOUBLE,
            missing_supplier_pct DOUBLE,
            negative_qty_pct DOUBLE,
            extreme_price_pct DOUBLE,
            notes VARCHAR
        )
    """)

def compute_store_health():
    conn = get_db()
    df = conn.execute("SELECT * FROM sales").fetchdf()

    if df.empty:
        return {"error": "No data available in sales table."}

    # Normalize column names to direct references
    col = {
        "store": "Store Name",
        "qty": "Quantity",
        "sales": "Total Sales",
        "rrp": "RRP",
        "supplier": "Supplier"
    }

    # Compute derived metrics
    df["unit_price"] = df[col["sales"]] / df[col["qty"]].replace(0, np.nan)
    stores = df[col["store"]].dropna().unique().tolist()

    results = []
    run_id = str(uuid.uuid4())
    run_ts = datetime.now(EAT_TZ)

    for store in stores:
        subset = df[df[col["store"]] == store]
        n = len(subset)
        if n == 0:
            continue

        # Missing %s
        miss_rrp = subset[col["rrp"]].isna().mean()
        miss_sup = subset[col["supplier"]].isna().mean()

        # Negative or zero quantities
        neg_qty = (subset[col["qty"]] < 0).mean()

        # Extreme price detection (IQR method)
        q1 = subset["unit_price"].quantile(0.25)
        q3 = subset["unit_price"].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_pct = ((subset["unit_price"] < lower) | (subset["unit_price"] > upper)).mean()

        # Penalties and score
        missing_pen = min(20, miss_rrp * 100 * 0.2 + miss_sup * 100 * 0.2)
        negative_pen = min(20, neg_qty * 100 * 0.2)
        outlier_pen = min(20, outlier_pct * 100 * 0.2)

        score = max(0, 100 - (missing_pen + negative_pen + outlier_pen))

        # Notes
        notes = []
        if miss_rrp > 0.1: notes.append("RRP missing >10%")
        if miss_sup > 0.1: notes.append("Supplier missing >10%")
        if neg_qty > 0: notes.append("Negative quantity present")
        if outlier_pct > 0.05: notes.append("High price variance")

        results.append({
            "run_id": run_id,
            "run_timestamp": run_ts.isoformat(),
            "store_name": store,
            "score": round(score, 2),
            "missing_rrp_pct": round(miss_rrp * 100, 2),
            "missing_supplier_pct": round(miss_sup * 100, 2),
            "negative_qty_pct": round(neg_qty * 100, 2),
            "extreme_price_pct": round(outlier_pct * 100, 2),
            "notes": "; ".join(notes)
        })

    # Persist results
    ensure_health_table(conn)
    insert_df = pd.DataFrame(results)
    conn.register("tmp_health", insert_df)
    conn.execute("""
        INSERT INTO store_health_scores
        SELECT run_id, run_timestamp, store_name, score,
               missing_rrp_pct, missing_supplier_pct,
               negative_qty_pct, extreme_price_pct, notes
        FROM tmp_health
    """)
    conn.unregister("tmp_health")

    avg_score = insert_df["score"].mean()
    return {
        "run_id": run_id,
        "run_timestamp": run_ts.isoformat(),
        "summary": {"avg_score": round(avg_score, 2), "total_stores": len(results)},
        "store_health": results
    }