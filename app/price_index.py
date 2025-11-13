# app/price_index.py
import pandas as pd
import numpy as np
import uuid
from datetime import datetime
import pytz
from .db import get_db

EAT_TZ = pytz.timezone("Africa/Nairobi")

def ensure_price_index_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_index_scores (
            run_id VARCHAR,
            run_timestamp TIMESTAMP,
            Store_Name VARCHAR,
            Sub_Department VARCHAR,
            Section VARCHAR,
            Bidco_Avg_Unit_Price DOUBLE,
            Competitor_Avg_Unit_Price DOUBLE,
            Price_Index DOUBLE,
            Bidco_Avg_RRP DOUBLE,
            Bidco_vs_RRP_Discount DOUBLE
        )
    """)

def compute_price_index():
    conn = get_db()
    df = conn.execute("SELECT * FROM sales").fetchdf()

    if df.empty:
        return {"error": "No data available in sales table"}

    df["unit_price"] = df["Total Sales"] / df["Quantity"].replace(0, np.nan)
    df["Date Of Sale"] = pd.to_datetime(df["Date Of Sale"], errors="coerce")
    df = df.dropna(subset=["unit_price", "RRP", "Supplier"])

    results = []
    for (store, subdept, section), group in df.groupby(["Store Name", "Sub-Department", "Section"]):
        bidco = group[group["Supplier"].str.lower().str.contains("bidco", na=False)]
        competitors = group[~group["Supplier"].str.lower().str.contains("bidco", na=False)]

        if bidco.empty or competitors.empty:
            continue

        bidco_avg_price = bidco["unit_price"].mean()
        competitor_avg_price = competitors["unit_price"].mean()
        bidco_avg_rrp = bidco["RRP"].mean()

        price_index = (bidco_avg_price / competitor_avg_price) * 100 if competitor_avg_price > 0 else np.nan
        bidco_discount = (bidco_avg_price / bidco_avg_rrp) * 100 if bidco_avg_rrp > 0 else np.nan

        results.append({
            "Store_Name": store,
            "Sub_Department": subdept,
            "Section": section,
            "Bidco_Avg_Unit_Price": round(bidco_avg_price, 2),
            "Competitor_Avg_Unit_Price": round(competitor_avg_price, 2),
            "Price_Index": round(price_index, 2),
            "Bidco_Avg_RRP": round(bidco_avg_rrp, 2),
            "Bidco_vs_RRP_Discount": round(bidco_discount, 2)
        })

    results_df = pd.DataFrame(results)
    if results_df.empty:
        return {"message": "No comparable categories found."}

    ensure_price_index_table(conn)
    run_id = str(uuid.uuid4())
    run_ts = datetime.now(EAT_TZ)

    results_df["run_id"] = run_id
    results_df["run_timestamp"] = run_ts

    conn.register("tmp_price", results_df)
    conn.execute("""
        INSERT INTO price_index_scores
        SELECT run_id, run_timestamp, Store_Name, Sub_Department, Section,
               Bidco_Avg_Unit_Price, Competitor_Avg_Unit_Price, Price_Index,
               Bidco_Avg_RRP, Bidco_vs_RRP_Discount
        FROM tmp_price
    """)
    conn.unregister("tmp_price")

    avg_index = results_df["Price_Index"].mean()
    overall_position = (
        "Premium" if avg_index > 105 else
        "Discounted" if avg_index < 95 else
        "Near-Market"
    )

    insights = [
        f"Bidco's overall price position: {overall_position} ({avg_index:.1f}%) vs competitors.",
        f"Average discount vs RRP: {results_df['Bidco_vs_RRP_Discount'].mean():.1f}%",
        f"Top store with lowest price index: {results_df.sort_values('Price_Index').iloc[0]['Store_Name']}"
    ]

    return {
        "run_id": run_id,
        "run_timestamp": run_ts.isoformat(),
        "summary": {
            "avg_price_index": round(avg_index, 2),
            "position": overall_position,
            "stores_evaluated": len(results_df)
        },
        "insights": insights,
        "details": results_df.to_dict(orient="records")
    }