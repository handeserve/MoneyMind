import logging
from sqlite3 import Connection
from typing import Optional, Dict, Any, List
import asyncio
import concurrent.futures
from functools import partial

# Database related imports
from database.database import get_expense_by_id, update_expense, get_db_connection, get_expenses
# Use the aliased config_manager
from ai_layer import config_manager as cm
from ai_layer.llm_interface import get_llm_classification

# Module-level logger
logger = logging.getLogger(__name__)

def classify_single_expense(db_conn: Connection, expense_id: int) -> dict | None:
    """
    Classifies a single expense, gets suggestions, and updates the database.
    This now uses the refactored llm_interface and config_manager.
    Returns the updated expense object on success, None on failure.
    """
    logger.info(f"Attempting to classify expense ID: {expense_id}")
    try:
        expense = get_expense_by_id(db_conn, expense_id)
        if not expense:
            logger.error(f"Expense with ID {expense_id} not found.")
            return None
        
        # Try to get description for AI, fallback to raw description
        description = expense.get('description_for_ai') or expense.get('source_raw_description')
        if not description:
            logger.error(f"Expense {expense_id} has no description (neither description_for_ai nor source_raw_description) for classification.")
            return None

        # llm_interface now handles its own configuration via the new config_manager
        classification_result = get_llm_classification(description=description)

        if classification_result and not classification_result.get("error"):
            # 从LLM返回结果中获取分类信息
            category_l1 = classification_result.get('ai_suggestion_l1') or classification_result.get('category_l1')
            category_l2 = classification_result.get('ai_suggestion_l2') or classification_result.get('category_l2')
            
            update_data = {
                'category_l1': category_l1,
                'category_l2': category_l2,
                'ai_suggestion_l1': category_l1,
                'ai_suggestion_l2': category_l2,
                'is_classified_by_ai': 1,
                'is_confirmed_by_user': 1  # 自动确认分类
            }
            if update_expense(db_conn, expense_id, update_data):
                logger.info(f"Expense ID {expense_id} successfully classified and updated.")
                return get_expense_by_id(db_conn, expense_id) # Return updated expense
            else:
                logger.error(f"Failed to update database for expense ID {expense_id}.")
                return None
        else:
            error_info = classification_result.get("detail") if classification_result else "No details"
            logger.warning(f"LLM classification failed for expense ID {expense_id}. Details: {error_info}")
            return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during classification of expense ID {expense_id}: {e}", exc_info=True)
        return None

def classify_single_expense_sync(expense: Dict[str, Any], db_conn: Connection) -> Dict[str, Any]:
    """
    Synchronous wrapper for classifying a single expense for use in concurrent processing.
    Returns a result dict with success status and details.
    """
    expense_id = expense.get('id')
    
    try:
        # Try to get description for AI, fallback to raw description
        description = expense.get('description_for_ai') or expense.get('source_raw_description')
        if not description:
            return {
                'expense_id': expense_id,
                'success': False,
                'error': 'No description available'
            }

        # Get classification from LLM
        classification_result = get_llm_classification(description=description)

        if classification_result and not classification_result.get("error"):
            # 从LLM返回结果中获取分类信息
            category_l1 = classification_result.get('ai_suggestion_l1') or classification_result.get('category_l1')
            category_l2 = classification_result.get('ai_suggestion_l2') or classification_result.get('category_l2')
            
            update_data = {
                'category_l1': category_l1,
                'category_l2': category_l2,
                'ai_suggestion_l1': category_l1,
                'ai_suggestion_l2': category_l2,
                'is_classified_by_ai': 1,
                'is_confirmed_by_user': 1  # 自动确认分类
            }
            if update_expense(db_conn, expense_id, update_data):
                return {
                    'expense_id': expense_id,
                    'success': True,
                    'classification': classification_result
                }
            else:
                return {
                    'expense_id': expense_id,
                    'success': False,
                    'error': 'Failed to update database'
                }
        else:
            error_info = classification_result.get("detail") if classification_result else "LLM classification failed"
            return {
                'expense_id': expense_id,
                'success': False,
                'error': error_info
            }
    except Exception as e:
        return {
            'expense_id': expense_id,
            'success': False,
            'error': str(e)
        }

def classify_batch_expenses(db_conn: Connection, limit: Optional[int] = None, max_workers: int = 3) -> Dict[str, Any]:
    """
    Classifies a batch of unclassified expenses using the new config and interface.
    """
    log_prefix = f"Batch classify (limit: {limit if limit else 'None'}):"
    logger.info(f"{log_prefix} Starting process.")

    # Check for placeholder API key once before starting the loop.
    # This prevents multiple warnings if the key is a placeholder.
    active_service_config = cm.get_active_ai_service_config()
    if not active_service_config or "YOUR_" in active_service_config.get("api_key", "").upper():
         logger.warning(f"{log_prefix} Active AI service API key is a placeholder or missing. LLM calls will fail.")
         # We can choose to abort early
         # return {"error": "API key is a placeholder.", "message": "Batch process aborted."}
    
    # Fetch Unclassified Expenses (no category_l1)
    filters = {'category_l1_is_null': True}
    try:
        # Fetch all matching expenses up to a reasonable maximum if no limit is set
        fetched_data = get_expenses(
            db_connection=db_conn,
            page=1,
            per_page=limit or 500, # Use limit or a default batch size
            filters=filters,
            sort_by='id',
            sort_order='ASC'
        )
        expenses_to_process: List[Dict[str, Any]] = fetched_data.get('expenses', [])
        total_matching_criteria = fetched_data.get('total_count', 0)

        if not expenses_to_process:
            logger.info(f"{log_prefix} No unclassified expenses found.")
            return {"message": "No expenses to process."}
        
        logger.info(f"{log_prefix} Fetched {len(expenses_to_process)} expenses to process.")

    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error fetching expenses: {e}", exc_info=True)
        return {"error": "Unexpected error fetching expenses", "details": str(e)}

    # Initialize Counters
    successfully_classified_count = 0
    failed_count = 0

    # Use concurrent processing for better performance
    logger.info(f"{log_prefix} Using concurrent processing with {max_workers} workers.")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a partial function with the database connection pre-filled
        classify_func = partial(classify_single_expense_sync, db_conn=db_conn)
        
        # Submit all classification tasks
        future_to_expense = {
            executor.submit(classify_func, expense): expense 
            for expense in expenses_to_process
        }
        
        # Process completed tasks as they finish
        for i, future in enumerate(concurrent.futures.as_completed(future_to_expense)):
            expense = future_to_expense[future]
            expense_id = expense.get('id')
            
            logger.info(f"{log_prefix} Processing expense ID: {expense_id} ({i+1}/{len(expenses_to_process)})")
            
            try:
                result = future.result()
                if result['success']:
                    successfully_classified_count += 1
                    logger.info(f"{log_prefix} Expense ID {expense_id}: Successfully classified.")
                else:
                    failed_count += 1
                    logger.warning(f"{log_prefix} Expense ID {expense_id}: Failed - {result.get('error', 'Unknown error')}")
                    
            except Exception as e_inner:
                failed_count += 1
                logger.error(f"{log_prefix} Error processing expense ID {expense_id}: {e_inner}", exc_info=True)

    summary_message = (
        f"Batch process complete. Processed: {len(expenses_to_process)}, "
        f"Succeeded: {successfully_classified_count}, Failed: {failed_count}"
    )
    logger.info(f"{log_prefix} {summary_message}")
    
    return {
        "total_matching_criteria": total_matching_criteria,
        "processed_in_this_batch": len(expenses_to_process),
        "successfully_classified": successfully_classified_count,
        "failed_to_classify": failed_count,
        "message": summary_message
    }

def get_unclassified_expense_ids(db_conn: Connection) -> Dict[str, Any]:
    """
    获取所有未分类记录的ID列表
    """
    try:
        filters = {'category_l1_is_null': True}
        fetched_data = get_expenses(
            db_connection=db_conn,
            page=1,
            per_page=10000,  # 获取大量记录
            filters=filters,
            sort_by='id',
            sort_order='ASC'
        )
        
        expenses = fetched_data.get('expenses', [])
        expense_ids = [expense['id'] for expense in expenses]
        
        return {
            "expense_ids": expense_ids,
            "total_count": len(expense_ids)
        }
    except Exception as e:
        logger.error(f"Failed to get unclassified expense IDs: {e}", exc_info=True)
        return {"error": "Failed to get unclassified expense IDs", "details": str(e)}

def classify_expense_by_id(db_conn: Connection, expense_id: int) -> Dict[str, Any]:
    """
    根据ID分类单个记录，返回结果状态
    """
    try:
        # 获取记录详情
        expense = get_expense_by_id(db_conn, expense_id)
        if not expense:
            return {
                'expense_id': expense_id,
                'success': False,
                'error': 'Expense not found'
            }
        
        # 调用已有的同步分类函数
        result = classify_single_expense_sync(expense, db_conn)
        return result
        
    except Exception as e:
        return {
            'expense_id': expense_id,
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    # Simplified test runner for the new structure
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s.%(funcName)s:%(lineno)d] - %(message)s')
    main_logger = logging.getLogger(__name__)

    db_conn_main = None
    try:
        db_conn_main = get_db_connection()
        if not db_conn_main:
            main_logger.error("Failed to establish database connection. Aborting test.")
            exit(1)

        # Find one unclassified expense to test single classification
        unclassified_expenses = get_expenses(db_conn_main, 1, 1, {'is_classified_by_ai': 0, 'is_confirmed_by_user': 0}).get('expenses', [])
        
        if unclassified_expenses:
            test_id = unclassified_expenses[0]['id']
            main_logger.info(f"\n--- Testing classify_single_expense on existing ID: {test_id} ---")
            result = classify_single_expense(db_conn_main, test_id)
            main_logger.info(f"Single classification result: {result}")
        else:
            main_logger.info("\n--- No unclassified expenses found to test classify_single_expense ---")
            
        main_logger.info("\n--- Testing classify_batch_expenses ---")
        batch_result = classify_batch_expenses(db_conn_main, limit=5) # Test with a small limit
        main_logger.info(f"Batch classification result: {batch_result}")

    except Exception as e:
        main_logger.error(f"An error occurred during the test run: {e}", exc_info=True)
    finally:
        if db_conn_main:
            db_conn_main.close()
            main_logger.info("Database connection closed.")
