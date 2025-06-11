import sqlite3
import logging
from datetime import date, timedelta, datetime # Added timedelta for date calculations
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _format_date_for_query(d: date) -> str:
    """Format date for SQLite query."""
    return d.strftime("%Y-%m-%d")

def _format_datetime_end_of_day(d: date) -> str:
    """Formats a date object to 'YYYY-MM-DD 23:59:59' string for SQLite inclusive end date."""
    return f"{d.isoformat()} 23:59:59"

def get_summary_stats(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Calculates total expenses and average daily expenses within a date range.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_expenses,
                ABS(AVG(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as average_daily_expenses
            FROM expenses
            WHERE transaction_time BETWEEN ? AND ?
            AND is_hidden = 0
        """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        
        stats = cursor.fetchone()
        if not stats:
            return {
                "total_expenses": 0.0,
                "average_daily_expenses": 0.0,
                "start_date": start_date,
                "end_date": end_date
            }
            
        return {
            "total_expenses": float(stats['total_expenses'] or 0.0),
            "average_daily_expenses": float(stats['average_daily_expenses'] or 0.0),
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        logger.error(f"Error in get_summary_stats: {e}")
        return {
            "total_expenses": 0.0,
            "average_daily_expenses": 0.0,
            "start_date": start_date,
            "end_date": end_date
        }

def get_spending_by_channel(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Calculates total spending grouped by payment channel.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT 
                channel,
                ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
            FROM expenses
            WHERE transaction_time BETWEEN ? AND ?
            AND is_hidden = 0
            GROUP BY channel
            ORDER BY total_amount DESC
        """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        
        results = cursor.fetchall()
        if not results:
            return []
            
        return [{
            "channel": row['channel'] or "未知渠道",
            "total_amount": float(row['total_amount'] or 0.0)
        } for row in results]
    except Exception as e:
        logger.error(f"Error in get_spending_by_channel: {e}")
        return []

def get_expense_trend(db_conn: sqlite3.Connection, start_date: date, end_date: date, granularity: str = "daily") -> List[Dict[str, Any]]:
    """
    Calculates expense trends over time with daily, weekly, or monthly granularity.
    """
    try:
        cursor = db_conn.cursor()
        if granularity == "daily":
            cursor.execute("""
                SELECT 
                    DATE(transaction_time) as date_period,
                    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
                FROM expenses
                WHERE transaction_time BETWEEN ? AND ?
                AND is_hidden = 0
                GROUP BY date_period
                ORDER BY date_period
            """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        elif granularity == "weekly":
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', transaction_time) as date_period,
                    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
                FROM expenses
                WHERE transaction_time BETWEEN ? AND ?
                AND is_hidden = 0
                GROUP BY date_period
                ORDER BY date_period
            """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        elif granularity == "monthly":
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', transaction_time) as date_period,
                    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
                FROM expenses
                WHERE transaction_time BETWEEN ? AND ?
                AND is_hidden = 0
                GROUP BY date_period
                ORDER BY date_period
            """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        else:
            logger.warning(f"Invalid granularity '{granularity}' in get_expense_trend. Defaulting to daily.")
            cursor.execute("""
                SELECT 
                    DATE(transaction_time) as date_period,
                    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
                FROM expenses
                WHERE transaction_time BETWEEN ? AND ?
                AND is_hidden = 0
                GROUP BY date_period
                ORDER BY date_period
            """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
            
        results = cursor.fetchall()
        if not results:
            return []
            
        return [{
            "date_period": row['date_period'],
            "total_amount": float(row['total_amount'] or 0.0)
        } for row in results]
    except Exception as e:
        logger.error(f"Error in get_expense_trend: {e}")
        return []

def get_spending_by_l1_category(db_conn: sqlite3.Connection, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Calculates total spending grouped by L1 category for user-confirmed expenses.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT 
                category_l1,
                ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_amount
            FROM expenses
            WHERE transaction_time BETWEEN ? AND ?
            AND is_hidden = 0
            GROUP BY category_l1
            ORDER BY total_amount DESC
        """, (_format_date_for_query(start_date), _format_datetime_end_of_day(end_date)))
        
        results = cursor.fetchall()
        if not results:
            return []
            
        return [{
            "category_l1": row['category_l1'] or "未分类",
            "total_amount": float(row['total_amount'] or 0.0)
        } for row in results]
    except Exception as e:
        logger.error(f"Error in get_spending_by_l1_category: {e}")
        return []

# --- Main block for testing (Optional but Recommended) ---
if __name__ == '__main__':
    # This test block requires database.py to be in the parent directory
    # and personal_expenses.db to be in the project root.
    import os
    from .database import get_db_connection, create_tables, create_expense, delete_expense, DATABASE_PATH

    logger.info(f"Analytics Test: Using database at {DATABASE_PATH}")
    
    # Ensure a clean state or known state for testing
    # For simplicity, we'll use the existing DB but could also create a temp in-memory DB.
    conn = get_db_connection()
    if not conn:
        logger.error("Analytics Test: Failed to connect to database. Aborting.")
        exit()
    
    create_tables(conn) # Ensure tables exist

    # Sample data for testing
    sample_expenses_data = [
        {'transaction_time': (datetime.now() - timedelta(days=5)).isoformat(), 'amount': '10.00', 'channel': 'Cash', 'source_raw_description': 'Coffee', 'is_confirmed_by_user': 1, 'category_l1': 'Food & Drinks', 'category_l2': 'Coffee Shops', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_1'},
        {'transaction_time': (datetime.now() - timedelta(days=4)).isoformat(), 'amount': '25.50', 'channel': 'WeChat Pay', 'source_raw_description': 'Lunch', 'is_confirmed_by_user': 1, 'category_l1': 'Food & Drinks', 'category_l2': 'Restaurants', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_2'},
        {'transaction_time': (datetime.now() - timedelta(days=3)).isoformat(), 'amount': '50.00', 'channel': 'Alipay', 'source_raw_description': 'Groceries', 'is_confirmed_by_user': 1, 'category_l1': 'Food & Drinks', 'category_l2': 'Groceries', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_3'},
        {'transaction_time': (datetime.now() - timedelta(days=2)).isoformat(), 'amount': '30.00', 'channel': 'Cash', 'source_raw_description': 'Taxi', 'is_confirmed_by_user': 1, 'category_l1': 'Transportation', 'category_l2': 'Taxi', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_4'},
        {'transaction_time': (datetime.now() - timedelta(days=1)).isoformat(), 'amount': '120.00', 'channel': 'Credit Card', 'source_raw_description': 'Online Shopping', 'is_confirmed_by_user': 1, 'category_l1': 'Shopping & Services', 'category_l2': 'Online', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_5'},
        {'transaction_time': (datetime.now() - timedelta(days=1)).isoformat(), 'amount': '15.00', 'channel': 'Cash', 'source_raw_description': 'Hidden Coffee', 'is_confirmed_by_user': 1, 'category_l1': 'Food & Drinks', 'category_l2': 'Coffee Shops', 'is_hidden': 1, 'external_transaction_id': 'ANALYTICS_TEST_6'}, # Hidden
        {'transaction_time': (datetime.now() - timedelta(days=8)).isoformat(), 'amount': '200.00', 'channel': 'WeChat Pay', 'source_raw_description': 'Last week stuff', 'is_confirmed_by_user': 1, 'category_l1': 'Miscellaneous', 'category_l2': 'General', 'is_hidden': 0, 'external_transaction_id': 'ANALYTICS_TEST_7'},
    ]
    
    expense_ids_to_delete = []
    logger.info("Analytics Test: Inserting sample data...")
    for data in sample_expenses_data:
        # create_expense expects 'amount' as Decimal or string that can be cast to Decimal
        # It also sets imported_at and updated_at automatically.
        try:
            exp_id = create_expense(conn, data)
            if exp_id:
                expense_ids_to_delete.append(exp_id)
            else:
                logger.warning(f"Analytics Test: Failed to insert sample data: {data.get('external_transaction_id')}. It might already exist if tests were run before without cleanup.")
        except Exception as e:
             logger.warning(f"Analytics Test: Error inserting sample data {data.get('external_transaction_id')}: {e}")

    logger.info(f"Analytics Test: Sample data inserted. IDs: {expense_ids_to_delete}")

    # Define date range for tests
    test_end_date = date.today()
    test_start_date_7_days = test_end_date - timedelta(days=6) # Last 7 days
    test_start_date_30_days = test_end_date - timedelta(days=29) # Last 30 days

    logger.info(f"\n--- Testing get_summary_stats (Last 7 days: {test_start_date_7_days} to {test_end_date}) ---")
    summary = get_summary_stats(conn, test_start_date_7_days, test_end_date)
    logger.info(f"Summary Stats: {summary}")

    logger.info(f"\n--- Testing get_spending_by_channel (Last 7 days) ---")
    channels = get_spending_by_channel(conn, test_start_date_7_days, test_end_date)
    logger.info(f"Spending by Channel: {channels}")

    logger.info(f"\n--- Testing get_expense_trend (Last 7 days, daily) ---")
    trend_daily = get_expense_trend(conn, test_start_date_7_days, test_end_date, "daily")
    logger.info(f"Expense Trend (Daily): {trend_daily}")
    
    logger.info(f"\n--- Testing get_expense_trend (Last 30 days, weekly) ---")
    trend_weekly = get_expense_trend(conn, test_start_date_30_days, test_end_date, "weekly")
    logger.info(f"Expense Trend (Weekly): {trend_weekly}")

    logger.info(f"\n--- Testing get_expense_trend (Last 30 days, monthly) ---")
    trend_monthly = get_expense_trend(conn, test_start_date_30_days, test_end_date, "monthly")
    logger.info(f"Expense Trend (Monthly): {trend_monthly}")

    logger.info(f"\n--- Testing get_spending_by_l1_category (Last 7 days) ---")
    categories_l1 = get_spending_by_l1_category(conn, test_start_date_7_days, test_end_date)
    logger.info(f"Spending by L1 Category: {categories_l1}")
    
    # Test with a date range with no expenses
    logger.info(f"\n--- Testing with date range with no expenses ---")
    far_future_start = date.today() + timedelta(days=365)
    far_future_end = date.today() + timedelta(days=370)
    summary_no_data = get_summary_stats(conn, far_future_start, far_future_end)
    logger.info(f"Summary Stats (no data): {summary_no_data}")
    channels_no_data = get_spending_by_channel(conn, far_future_start, far_future_end)
    logger.info(f"Channels (no data): {channels_no_data}")


    logger.info("\nAnalytics Test: Cleaning up sample data...")
    for exp_id in expense_ids_to_delete:
        delete_expense(conn, exp_id)
    logger.info("Analytics Test: Sample data cleanup complete.")

    conn.close()
    logger.info("Analytics Test: Database connection closed.")
