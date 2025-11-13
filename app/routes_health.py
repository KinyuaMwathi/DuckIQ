# app/routes_health.py
from fastapi import APIRouter
from .health_engine import compute_store_health

router = APIRouter()

@router.get("/data_health")
def data_health():
    """Compute store-level data health and persist results."""
    result = compute_store_health()
    return result