# tests/test_data_health.py
from app.health_engine import compute_store_health
from app.db import get_db, load_sales_data

def test_data_health_runs():
    conn = get_db()
    load_sales_data(conn)
    result = compute_store_health()
    assert "run_id" in result
    assert "store_health" in result
    assert result["summary"]["total_stores"] > 0