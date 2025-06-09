from fastapi import APIRouter, Depends, HTTPException, Query
from sqlite3 import Connection
from typing import Optional, List, Dict, Any # Maintained for general use, though specific models are used
from datetime import date # For date type hinting

# Pydantic models for response structures
from pydantic import BaseModel, validator

# Assuming get_db is in main.py, which is one level up from routers directory
from ..main import get_db 

# Import analytics functions from database layer
from ...database import analytics as db_analytics 
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

@router.get("/summary_stats", response_model=SummaryStats)
async def get_summary_stats_endpoint(
    start_date: date = Query(..., description="Start date for the statistics (YYYY-MM-DD)."), 
    end_date: date = Query(..., description="End date for the statistics (YYYY-MM-DD)."), 
    db: Connection = Depends(get_db)
):
    """
    Provides summary statistics of expenses within a given date range.
    """
    validate_date_range(start_date, end_date)
    try:
        stats_data = db_analytics.get_summary_stats(db, start_date, end_date)
        # The db_analytics.get_summary_stats already returns a dict that matches SummaryStats model
        # including handling of no data by returning 0.0 for amounts.
        return SummaryStats(**stats_data)
    except Exception as e:
        logger.error(f"Error in /summary_stats endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching summary statistics.")


@router.get("/channel_distribution", response_model=List[ChannelDistributionItem])
async def get_channel_distribution_endpoint(
    start_date: date = Query(..., description="Start date for the distribution (YYYY-MM-DD)."), 
    end_date: date = Query(..., description="End date for the distribution (YYYY-MM-DD)."), 
    db: Connection = Depends(get_db)
):
    """
    Shows the distribution of expenses across different payment channels.
    """
    validate_date_range(start_date, end_date)
    try:
        channel_data = db_analytics.get_spending_by_channel(db, start_date, end_date)
        # db_analytics.get_spending_by_channel returns a list of dicts matching ChannelDistributionItem
        return [ChannelDistributionItem(**item) for item in channel_data]
    except Exception as e:
        logger.error(f"Error in /channel_distribution endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching channel distribution.")


@router.get("/expense_trend", response_model=List[ExpenseTrendItem])
async def get_expense_trend_endpoint(
    start_date: date = Query(..., description="Start date for the trend analysis (YYYY-MM-DD)."), 
    end_date: date = Query(..., description="End date for the trend analysis (YYYY-MM-DD)."), 
    granularity: str = Query("daily", description="Granularity of the trend: 'daily', 'weekly', or 'monthly'."),
    db: Connection = Depends(get_db)
):
    """
    Provides data for expense trends over time, with selectable granularity.
    """
    validate_date_range(start_date, end_date)
    if granularity not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid granularity. Choose from 'daily', 'weekly', 'monthly'.")
    
    try:
        trend_data = db_analytics.get_expense_trend(db, start_date, end_date, granularity)
        # db_analytics.get_expense_trend returns a list of dicts matching ExpenseTrendItem
        return [ExpenseTrendItem(**item) for item in trend_data]
    except Exception as e:
        logger.error(f"Error in /expense_trend endpoint (granularity: {granularity}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching expense trend.")


@router.get("/category_spending", response_model=List[CategorySpendingItem])
async def get_category_spending_endpoint(
    start_date: date = Query(..., description="Start date for category spending analysis (YYYY-MM-DD)."), 
    end_date: date = Query(..., description="End date for category spending analysis (YYYY-MM-DD)."), 
    db: Connection = Depends(get_db)
):
    """
    Shows total spending per L1 category for user-confirmed expenses within the specified date range.
    """
    validate_date_range(start_date, end_date)
    try:
        category_data = db_analytics.get_spending_by_l1_category(db, start_date, end_date)
        # db_analytics.get_spending_by_l1_category returns a list of dicts matching CategorySpendingItem
        return [CategorySpendingItem(**item) for item in category_data]
    except Exception as e:
        logger.error(f"Error in /category_spending endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching category spending.")

if __name__ == "__main__":
    # This block is for context/documentation; direct execution isn't typical for routers.
    # For testing, one would typically run the main FastAPI application (main.py)
    # and use an HTTP client to hit the endpoints.
    logging.basicConfig(level=logging.INFO)
    local_logger = logging.getLogger(__name__)
    local_logger.info("dashboard_router.py loaded. Intended for import by main FastAPI app.")
    local_logger.info("Endpoints now use actual database analytics functions.")
