# app/main.py
from fastapi import FastAPI
from .routes_health import router as health_router
from .routes_supplier_health import router as supplier_health_router
from .routes_promo import router as promo_router
from .routes_price import router as price_router
from .db import get_db, load_sales_data

app = FastAPI(title="DuckIQ Data Health API")

@app.on_event("startup")
def startup_event():
    conn = get_db()
    load_sales_data(conn)  # Load Excel into DuckDB on startup

app.include_router(health_router)
app.include_router(supplier_health_router)
app.include_router(promo_router)
app.include_router(price_router)