# app/main.py
from fastapi import FastAPI
import duckdb
import pandas as pd
import tempfile, shutil, os

DB_PATH = "data/duckiq.duckdb"

app = FastAPI(title="DuckIQ API", version="1.0")

# ---------------------------------------------------------
# Safe DuckDB loader — avoids Windows file locking
# ---------------------------------------------------------
def load_table(table_name: str) -> pd.DataFrame:
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb").name
        shutil.copy(DB_PATH, tmp)

        con = duckdb.connect(tmp, read_only=True)
        df = con.execute(f"SELECT * FROM {table_name}").fetchdf()
        con.close()

        os.remove(tmp)
        return df

    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------
# Root + Health Check
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"message": "DuckIQ API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------
# DATA QUALITY ENDPOINT
# ---------------------------------------------------------
@app.get("/data_quality")
def data_quality():
    store_df = load_table("store_health_scores")
    supplier_df = load_table("supplier_health_scores")

    if store_df.empty and supplier_df.empty:
        return {"error": "No data available"}

    return {
        "store_health": store_df.to_dict(orient="records"),
        "supplier_health": supplier_df.to_dict(orient="records")
    }


# ---------------------------------------------------------
# PROMOTION SUMMARY ENDPOINT
# ---------------------------------------------------------
@app.get("/promo_summary")
def promo_summary():
    df = load_table("promo_summary_scores")

    if df.empty:
        return {"error": "No promo data available"}

    return {
        "latest_run": str(df["run_timestamp"].max()),
        "summary": {
            "avg_uplift": df["Promo_Uplift_%"].mean(),
            "avg_coverage": df["Promo_Coverage_%"].mean(),
            "avg_price_impact": df["Promo_Price_Impact_%"].mean(),
            "sku_count": df["Item_Code"].nunique()
        },
        "details": df.to_dict(orient="records")
    }


# ---------------------------------------------------------
# PRICE INDEX ENDPOINT
# ---------------------------------------------------------
@app.get("/price_index")
def price_index():
    df = load_table("price_index_scores")

    if df.empty:
        return {"error": "No price index data available"}

    return {
        "latest_run": str(df["run_timestamp"].max()),
        "summary": {
            "avg_index": df["Price_Index"].mean(),
            "avg_discount": df["Bidco_vs_RRP_Discount"].mean(),
            "store_count": df["Store_Name"].nunique()
        },
        "details": df.to_dict(orient="records")
    }