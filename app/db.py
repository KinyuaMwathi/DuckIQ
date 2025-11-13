# app/db.py
import duckdb
from pathlib import Path
import pandas as pd

DB_PATH = Path("data/duckiq.duckdb")

def init_duckdb():
    conn = duckdb.connect(str(DB_PATH))
    return conn

def load_sales_data(conn, excel_path="data/Test_Data.xlsx", table_name="sales"):
    df = pd.read_excel(excel_path, engine="openpyxl")
    # Clean whitespace-only rows
    df = df.dropna(how="all")
    # Register and create table with exact column names
    conn.register("tmp_df", df)
    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM tmp_df")
    conn.unregister("tmp_df")
    print(f"Loaded {len(df)} rows into {table_name}")
    return df

# Singleton pattern
_conn = None

def get_db():
    global _conn
    if _conn is None:
        _conn = init_duckdb()
    return _conn