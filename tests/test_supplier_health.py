# tests/test_supplier_health.py
from app.supplier_health_engine import compute_supplier_health
from app.db import get_db, load_sales_data

def test_supplier_health_scoring():
    conn = get_db()
    load_sales_data(conn)
    result = compute_supplier_health()
    assert "run_id" in result
    assert "supplier_health" in result
    assert result["summary"]["total_suppliers"] > 0