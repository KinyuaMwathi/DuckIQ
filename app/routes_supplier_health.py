# app/routes_supplier_health.py
from fastapi import APIRouter
from .supplier_health_engine import compute_supplier_health

router = APIRouter()

@router.get("/supplier_health")
def supplier_health():
    """Compute supplier-level data health scores and detect drift."""
    return compute_supplier_health()