# app/routes_price.py
from fastapi import APIRouter
from .price_index import compute_price_index

router = APIRouter()

@router.get("/price_index")
def price_index_summary():
    return compute_price_index()