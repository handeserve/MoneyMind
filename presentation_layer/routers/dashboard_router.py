from fastapi import APIRouter, Depends, HTTPException, Query
from sqlite3 import Connection
from typing import Optional, List, Dict, Any # Maintained for general use, though specific models are used
from datetime import date, datetime # For date type hinting

# Pydantic models for response structures
from pydantic import BaseModel, validator

# Assuming get_db is in main.py, which is one level up from routers directory
from presentation_layer.dependencies import get_db 

# Import analytics functions from database layer
from database import analytics as analytics_ops
from database.analytics import get_summary_stats, get_spending_by_l1_category, get_spending_by_channel, get_expense_trend
from database.db import get_db_connection
import logging # For logging within the router

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Pydantic Models for Dashboard Responses ---

class SummaryStats(BaseModel):
    total_expenses: float
    average_daily_expenses: float
    start_date: date
    end_date: date

class ChannelDistributionItem(BaseModel):
    channel: str
    total_amount: float

class ExpenseTrendItem(BaseModel):
    date_period: str 
    total_amount: float

class CategorySpendingItem(BaseModel):
    category_l1: str
    total_amount: float

# --- Helper for Date Validation ---
def validate_date_range(start_date: date, end_date: date):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

# --- Dashboard Endpoints ---

@router.get("/summary")
async def get_summary_endpoint(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    db_conn = Depends(get_db_connection)
):
    """
    Get summary statistics for the specified date range.
    """
    try:
        stats = get_summary_stats(db_conn, start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"Error in /summary endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category_spending")
async def get_category_spending_endpoint(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    db_conn = Depends(get_db_connection)
):
    """
    Get spending breakdown by L1 category for the specified date range.
    """
    try:
        category_data = get_spending_by_l1_category(db_conn, start_date, end_date)
        return category_data
    except Exception as e:
        logger.error(f"Error in /category_spending endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/channel_spending")
async def get_channel_spending_endpoint(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    db_conn = Depends(get_db_connection)
):
    """
    Get spending breakdown by payment channel for the specified date range.
    """
    try:
        channel_data = get_spending_by_channel(db_conn, start_date, end_date)
        return channel_data
    except Exception as e:
        logger.error(f"Error in /channel_spending endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expense_trend")
async def get_expense_trend_endpoint(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    granularity: str = Query("daily", description="Time granularity (daily/weekly/monthly)"),
    db_conn = Depends(get_db_connection)
):
    """
    Get expense trend over time with specified granularity.
    """
    try:
        trend_data = get_expense_trend(db_conn, start_date, end_date, granularity)
        return trend_data
    except Exception as e:
        logger.error(f"Error in /expense_trend endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # This block is for context/documentation; direct execution isn't typical for routers.
    # For testing, one would typically run the main FastAPI application (main.py)
    # and use an HTTP client to hit the endpoints.
    logging.basicConfig(level=logging.INFO)
    local_logger = logging.getLogger(__name__)
    local_logger.info("dashboard_router.py loaded. Intended for import by main FastAPI app.")
    local_logger.info("Endpoints now use actual database analytics functions.")
