from fastapi import APIRouter, Depends, HTTPException, Query
from sqlite3 import Connection
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel, validator
import logging

from presentation_layer.dependencies import get_db
from database import analytics as analytics_ops
from database.analytics import get_summary_stats, get_spending_by_l1_category, get_spending_by_channel, get_expense_trend
from database.db import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["财务概览"])

# --- Pydantic Models for Financial Overview Responses ---
class SummaryStats(BaseModel):
    total_expenses: float = 0.0
    average_daily_expenses: float = 0.0
    start_date: date
    end_date: date

class ChannelDistributionItem(BaseModel):
    channel: str
    total_amount: float = 0.0

class ExpenseTrendItem(BaseModel):
    date_period: str
    total_amount: float = 0.0

class CategorySpendingItem(BaseModel):
    category_l1: str
    total_amount: float = 0.0

# --- Helper for Date Validation ---
def validate_date_range(start_date: date, end_date: date):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    if (end_date - start_date).days > 365:
        raise HTTPException(status_code=400, detail="日期范围不能超过一年")

# --- Financial Overview Endpoints ---
@router.get("", response_model=Dict[str, Any])
async def get_financial_overview(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db_conn = Depends(get_db_connection)
):
    """获取完整的财务概览数据"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        # 获取概览统计
        stats = get_summary_stats(db_conn, start_date, end_date)
        
        # 计算前一个周期的统计
        period_days = (end_date - start_date).days
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days)
        prev_stats = get_summary_stats(db_conn, prev_start_date, prev_end_date)
        
        # 计算变化百分比
        def calculate_change(current, previous):
            if previous == 0:
                return 0.0
            return ((current - previous) / previous) * 100
        
        return {
            "total_expense": abs(stats["total_expenses"]),
            "avg_daily": abs(stats["average_daily_expenses"]),
            "transaction_count": 0,  # 需要从数据库获取
            "expense_change": calculate_change(abs(stats["total_expenses"]), abs(prev_stats["total_expenses"])),
            "avg_change": calculate_change(abs(stats["average_daily_expenses"]), abs(prev_stats["average_daily_expenses"])),
            "count_change": 0.0  # 需要实现
        }
    except Exception as e:
        logger.error(f"Error in financial overview endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expense-trends", response_model=Dict[str, List])
async def get_expense_trends_endpoint(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    period: str = Query("day", description="时间周期 (day/week/month)"),
    db_conn = Depends(get_db_connection)
):
    """获取支出趋势数据"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        # 映射前端期望的参数到后端
        granularity_map = {"day": "daily", "week": "weekly", "month": "monthly"}
        granularity = granularity_map.get(period, "daily")
        
        trend_data = get_expense_trend(db_conn, start_date, end_date, granularity)
        
        # 格式化为前端期望的格式
        dates = [item["date_period"] for item in trend_data]
        amounts = [abs(item["total_amount"]) for item in trend_data]
        
        return {
            "dates": dates,
            "amounts": amounts
        }
    except Exception as e:
        logger.error(f"Error in expense trends endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=SummaryStats)
async def get_summary_endpoint(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db_conn = Depends(get_db_connection)
):
    """获取指定日期范围内的支出统计摘要"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        stats = get_summary_stats(db_conn, start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"Error in /summary endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category-spending", response_model=List[CategorySpendingItem])
async def get_category_spending_endpoint(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db_conn = Depends(get_db_connection)
):
    """获取按一级类别分组的支出统计"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        category_data = get_spending_by_l1_category(db_conn, start_date, end_date)
        return category_data
    except Exception as e:
        logger.error(f"Error in /category-spending endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/channel-distribution", response_model=List[ChannelDistributionItem])
async def get_channel_spending_endpoint(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db_conn = Depends(get_db_connection)
):
    """获取按支付渠道分组的支出统计"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        channel_data = get_spending_by_channel(db_conn, start_date, end_date)
        return channel_data
    except Exception as e:
        logger.error(f"Error in /channel-distribution endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expense-trend", response_model=List[ExpenseTrendItem])
async def get_expense_trend_endpoint(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    granularity: str = Query("daily", description="时间粒度 (daily/weekly/monthly)"),
    db_conn = Depends(get_db_connection)
):
    """获取支出趋势数据"""
    try:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        validate_date_range(start_date, end_date)
        
        if granularity not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="无效的时间粒度，必须是 daily、weekly 或 monthly")
            
        trend_data = get_expense_trend(db_conn, start_date, end_date, granularity)
        return trend_data
    except Exception as e:
        logger.error(f"Error in /expense-trend endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("financial_overview_router.py loaded. Intended for import by main FastAPI app.")
