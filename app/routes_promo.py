# app/routes_promo.py
from fastapi import APIRouter
from .promo_performance import compute_promo_metrics

router = APIRouter()

@router.get("/promo_summary")
def promo_summary():
    """Compute and summarize promotion performance metrics."""
    return compute_promo_metrics()