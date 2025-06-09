import logging
import os
from sqlite3 import Connection, Error as SQLiteError
from typing import Optional, Dict, Any, List # Added List and Dict
import time # For testing delays and unique IDs

# Database related imports
from ..database.database import get_expense_by_id, update_expense, get_db_connection, create_expense, delete_expense, DATABASE_PATH as DEFAULT_DB_PATH, get_expenses # Added get_expenses
from .config_manager import get_config, get_api_key as cm_get_api_key # cm_ for config_manager's get_api_key
from .llm_interface import get_llm_classification

# Module-level logger
logger = logging.getLogger(__name__)

def classify_single_expense(db_conn: Connection, expense_id: int) -> bool:
    """
    Classifies a single expense record using the LLM interface and updates the database.
    (Content from previous implementation - assumed to be correct and complete)
    """
    logger.info(f"Attempting to classify expense ID: {expense_id}")
    try:
        expense = get_expense_by_id(db_conn, expense_id)
        if not expense:
            logger.warning(f"Expense ID {expense_id} not found. Cannot classify.")
            return False
        if expense.get('is_confirmed_by_user') == 1:
            logger.info(f"Expense ID {expense_id} is already confirmed by user. Skipping AI classification.")
            return False
        
        description_for_ai = expense.get('description_for_ai') or expense.get('source_raw_description')
        if not description_for_ai:
            logger.warning(f"Expense ID {expense_id} has no description. Cannot classify.")
            return False
            
        amount = expense.get('amount')
        channel = expense.get('channel')
        source_provided_category = expense.get('source_provided_category')
        app_config = get_config()
        if not app_config:
            logger.error("Failed to load application configuration for single classification.")
            return False

        classification_result = get_llm_classification(
            description_for_ai=description_for_ai, config=app_config,
            amount=amount, channel=channel, source_provided_category=source_provided_category
        )
        if classification_result and classification_result.get('ai_suggestion_l1') and classification_result.get('ai_suggestion_l2'):
            update_data = {
                'ai_suggestion_l1': classification_result['ai_suggestion_l1'],
                'ai_suggestion_l2': classification_result['ai_suggestion_l2'],
                'is_classified_by_ai': 1
            }
            if update_expense(db_conn, expense_id, update_data):
                logger.info(f"Expense ID {expense_id} successfully classified and updated. L1: {update_data['ai_suggestion_l1']}, L2: {update_data['ai_suggestion_l2']}")
                return True
            else:
                logger.error(f"Expense ID {expense_id}: Classified by LLM, but failed to update database.")
                return False
        else:
            logger.warning(f"Expense ID {expense_id}: LLM classification failed or no valid suggestions returned.")
            return False
    except SQLiteError as e:
        logger.error(f"Database error during classification of expense ID {expense_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during classification of expense ID {expense_id}: {e}", exc_info=True)
        return False

def classify_batch_expenses(db_conn: Connection, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifies a batch of unclassified and unconfirmed expenses.

    Args:
        db_conn: Active SQLite database connection.
        limit: Optional integer to limit the number of expenses processed.

    Returns:
        A dictionary summarizing the batch operation.
    """
    log_prefix = f"Batch classify (limit: {limit if limit else 'None'}):"
    logger.info(f"{log_prefix} Starting process.")

    # Fetch Unclassified Expenses
    filters = {'is_classified_by_ai': 0, 'is_confirmed_by_user': 0}
    page_to_fetch = 1
    per_page_limit = limit if limit is not None and limit > 0 else 1000 # Default to a large number if no limit, or use limit
    
    try:
        # get_expenses expects page and per_page for limit.
        # We only need one "page" of results up to the limit.
        fetched_data = get_expenses(
            db_connection=db_conn,
            page=page_to_fetch,
            per_page=per_page_limit,
            filters=filters,
            sort_by='id', # Process older expenses first
            sort_order='ASC'
        )
        expenses_to_process: List[Dict[str, Any]] = fetched_data.get('expenses', [])
        total_matching_criteria = fetched_data.get('total_count', 0) # Total that could be processed over time

        if not expenses_to_process:
            logger.info(f"{log_prefix} No expenses found matching criteria for batch classification.")
            return {
                "total_matching_criteria": total_matching_criteria,
                "processed_in_this_batch": 0,
                "successfully_classified": 0,
                "failed_to_classify": 0,
                "message": "No expenses to process."
            }
        
        logger.info(f"{log_prefix} Fetched {len(expenses_to_process)} expenses to process (out of {total_matching_criteria} total matching).")

    except SQLiteError as e:
        logger.error(f"{log_prefix} Database error fetching expenses: {e}")
        return {"error": "Database error fetching expenses", "details": str(e)}
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error fetching expenses: {e}", exc_info=True)
        return {"error": "Unexpected error fetching expenses", "details": str(e)}

    # Initialize Counters
    processed_count = 0
    successfully_classified_count = 0
    failed_count = 0

    # Load Config
    app_config = get_config()
    if not app_config:
        logger.error(f"{log_prefix} Failed to load application configuration. Aborting batch.")
        return {
            "total_matching_criteria": total_matching_criteria,
            "processed_in_this_batch": 0,
            "successfully_classified": 0,
            "failed_to_classify": 0,
            "error": "Failed to load configuration."
        }
    
    # Check for placeholder API key before starting the loop
    # This prevents multiple warnings if the key is a placeholder
    api_key_for_check = cm_get_api_key() # Gets key for default service
    if not api_key_for_check or "YOUR_DEEPSEEK_API_KEY_HERE" in api_key_for_check or "ANOTHER_KEY_HERE" in api_key_for_check:
        logger.warning(f"{log_prefix} API key is a placeholder or missing. Actual LLM calls will be skipped by get_llm_classification.")
        # The loop will still run, but get_llm_classification will return None for each.

    # Iterate and Classify
    for expense in expenses_to_process:
        expense_id = expense.get('id')
        if expense_id is None:
            logger.warning(f"{log_prefix} Found expense data without an ID: {expense}. Skipping.")
            failed_count +=1 # Count as failed if ID is missing
            continue

        processed_count += 1
        logger.info(f"{log_prefix} Processing expense ID: {expense_id} ({processed_count}/{len(expenses_to_process)})")

        description_for_ai = expense.get('description_for_ai') or expense.get('source_raw_description')
        if not description_for_ai:
            logger.warning(f"{log_prefix} Expense ID {expense_id} has no description. Skipping classification.")
            failed_count += 1
            continue
            
        amount = expense.get('amount')
        channel = expense.get('channel')
        source_provided_category = expense.get('source_provided_category')

        try:
            classification_result = get_llm_classification(
                description_for_ai=description_for_ai, config=app_config,
                amount=amount, channel=channel, source_provided_category=source_provided_category
            )

            if classification_result and classification_result.get('ai_suggestion_l1') and classification_result.get('ai_suggestion_l2'):
                update_data = {
                    'ai_suggestion_l1': classification_result['ai_suggestion_l1'],
                    'ai_suggestion_l2': classification_result['ai_suggestion_l2'],
                    'is_classified_by_ai': 1
                }
                if update_expense(db_conn, expense_id, update_data):
                    successfully_classified_count += 1
                    logger.info(f"{log_prefix} Expense ID {expense_id} successfully classified and updated.")
                else:
                    failed_count += 1
                    logger.error(f"{log_prefix} Expense ID {expense_id}: Classified by LLM, but failed to update database.")
            else:
                failed_count += 1
                logger.warning(f"{log_prefix} Expense ID {expense_id}: LLM classification failed or no valid suggestions returned.")
        except Exception as e_inner: # Catch errors during individual classification/update
            failed_count += 1
            logger.error(f"{log_prefix} Error processing expense ID {expense_id}: {e_inner}", exc_info=True)
        
        # Optional delay (consider adding if rate limits are an issue)
        # time.sleep(0.5) # Example: 0.5 second delay

    logger.info(f"{log_prefix} Process complete. Total fetched: {len(expenses_to_process)}, Processed in this run: {processed_count}, Successfully classified: {successfully_classified_count}, Failed: {failed_count}")
    return {
        "total_matching_criteria": total_matching_criteria,
        "processed_in_this_batch": processed_count,
        "successfully_classified": successfully_classified_count,
        "failed_to_classify": failed_count
    }


if __name__ == '__main__':
    # Configure logging for detailed test output
    # Using module-level logger obtained by getLogger(__name__) is better than getLogger("expense_classifier_test")
    # as it reflects the module hierarchy.
    # For __main__ execution, __name__ is "__main__". For imported, it's "personal_expense_analyzer.ai_layer.expense_classifier".
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s.%(funcName)s:%(lineno)d] - %(message)s')
    # Test logger for __main__ scope
    main_logger = logging.getLogger(__name__) # This will be "__main__" logger

    db_path_to_use = DEFAULT_DB_PATH
    main_logger.info(f"Using database for test: {db_path_to_use}")

    db_conn_main = None
    test_expense_ids_main = [] # Store IDs of all created test expenses

    try:
        db_conn_main = get_db_connection()
        if not db_conn_main:
            main_logger.error("Failed to establish database connection. Aborting test.")
            exit(1)

        from ..database.database import create_tables
        create_tables(db_conn_main)
        main_logger.info("Database tables ensured.")

        # --- Test classify_single_expense (briefly, already tested before) ---
        main_logger.info("\n--- Testing classify_single_expense (brief check) ---")
        single_test_data = {
            'transaction_time': '2024-07-30T10:00:00Z', 'amount': '15.00', 'channel': 'SingleTest',
            'source_raw_description': 'Single test coffee', 'description_for_ai': 'Single test coffee for AI',
            'external_transaction_id': f'TEST_SINGLE_{int(time.time())}'
        }
        single_id = create_expense(db_conn_main, single_test_data)
        if single_id:
            test_expense_ids_main.append(single_id)
            main_logger.info(f"Created single test expense ID: {single_id}")
            classify_single_expense(db_conn_main, single_id) # Result depends on API key
        else:
            main_logger.warning("Failed to create single test expense, possibly due to unique constraint if run before.")

        # --- Test classify_batch_expenses ---
        main_logger.info("\n--- Testing classify_batch_expenses ---")
        
        # Create some unclassified, unconfirmed expenses for batch processing
        batch_test_data = [
            {'transaction_time': '2024-07-30T11:00:00Z', 'amount': '100.00', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 1 - Groceries for week', 'description_for_ai': 'Groceries for week', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 0, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_1'},
            {'transaction_time': '2024-07-30T12:00:00Z', 'amount': '25.50', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 2 - Taxi to meeting', 'description_for_ai': 'Taxi to meeting', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 0, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_2'},
            {'transaction_time': '2024-07-30T13:00:00Z', 'amount': '60.75', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 3 - Online subscription renewal', 'description_for_ai': 'Online subscription renewal', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 0, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_3'},
            {'transaction_time': '2024-07-30T14:00:00Z', 'amount': '5.00', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 4 - Office coffee', 'description_for_ai': 'Office coffee', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 0, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_4'},
            {'transaction_time': '2024-07-30T15:00:00Z', 'amount': '10.00', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 5 - Parking fee', 'description_for_ai': 'Parking fee', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 0, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_5'},
            # This one should NOT be picked up by the batch
            {'transaction_time': '2024-07-30T16:00:00Z', 'amount': '50.00', 'channel': 'BatchTest', 'source_raw_description': 'Batch item 6 - Already confirmed', 'description_for_ai': 'Already confirmed', 'is_classified_by_ai': 0, 'is_confirmed_by_user': 1, 'external_transaction_id': f'BATCH_TEST_{int(time.time())}_6'},
        ]
        
        batch_ids_created = []
        for data in batch_test_data:
            exp_id = create_expense(db_conn_main, data)
            if exp_id:
                batch_ids_created.append(exp_id)
                test_expense_ids_main.append(exp_id) # Add to overall list for cleanup
        main_logger.info(f"Created {len(batch_ids_created)} expenses for batch test. IDs: {batch_ids_created}")

        # Check API key status
        api_key_for_batch_test = cm_get_api_key()
        if not api_key_for_batch_test or "YOUR_DEEPSEEK_API_KEY_HERE" in api_key_for_batch_test or "ANOTHER_KEY_HERE" in api_key_for_batch_test:
            main_logger.warning("API key is a placeholder. Batch classification will run, but no actual LLM calls will be made (expecting all to 'fail' classification).")
        else:
            main_logger.info("Valid API key found. Batch classification will attempt real LLM calls.")

        # Call classify_batch_expenses with a limit
        batch_limit = 3
        main_logger.info(f"Calling classify_batch_expenses with limit: {batch_limit}")
        batch_summary = classify_batch_expenses(db_conn_main, limit=batch_limit)
        main_logger.info(f"Batch Classification Summary (limit {batch_limit}): {batch_summary}")

        # Verify results (example for the first few)
        if batch_ids_created:
            main_logger.info("Verifying expenses after first batch run:")
            for i, exp_id_to_check in enumerate(batch_ids_created):
                if i < batch_limit: # Only check those that should have been processed
                    expense_after_batch = get_expense_by_id(db_conn_main, exp_id_to_check)
                    if expense_after_batch:
                        main_logger.info(f"  ID {exp_id_to_check}: AI Classified: {expense_after_batch['is_classified_by_ai']}, L1: {expense_after_batch['ai_suggestion_l1']}, L2: {expense_after_batch['ai_suggestion_l2']}")
                    else:
                         main_logger.error(f"Could not retrieve expense ID {exp_id_to_check} after batch.")
                elif expense_after_batch := get_expense_by_id(db_conn_main, exp_id_to_check): # Check those beyond limit
                     if expense_after_batch['is_classified_by_ai'] == 1:
                          main_logger.warning(f"  ID {exp_id_to_check} (beyond limit) was classified. Check batch logic.")


        # Call again to process remaining (if any)
        main_logger.info("\nCalling classify_batch_expenses again (no limit, to process remaining)")
        batch_summary_2 = classify_batch_expenses(db_conn_main) # No limit
        main_logger.info(f"Batch Classification Summary (run 2): {batch_summary_2}")
        
        # Verify all applicable are processed
        main_logger.info("Verifying expenses after second batch run:")
        for exp_id_to_check in batch_ids_created:
            # Find original data to check if it should have been processed
            original_data = next((d for d in batch_test_data if d['external_transaction_id'] == get_expense_by_id(db_conn_main, exp_id_to_check).get('external_transaction_id')), None)
            if original_data and original_data['is_confirmed_by_user'] == 0: # Should have been processed
                expense_after_batch_2 = get_expense_by_id(db_conn_main, exp_id_to_check)
                if expense_after_batch_2:
                    main_logger.info(f"  ID {exp_id_to_check}: AI Classified: {expense_after_batch_2['is_classified_by_ai']}, L1: {expense_after_batch_2['ai_suggestion_l1']}, L2: {expense_after_batch_2['ai_suggestion_l2']}")
                else:
                    main_logger.error(f"Could not retrieve expense ID {exp_id_to_check} after batch 2.")

    except Exception as e_main_test:
        main_logger.error(f"An error occurred in the main test block: {e_main_test}", exc_info=True)
    finally:
        if db_conn_main and test_expense_ids_main:
            main_logger.info(f"\nCleaning up {len(test_expense_ids_main)} test expenses...")
            cleaned_count = 0
            for exp_id in test_expense_ids_main:
                if delete_expense(db_conn_main, exp_id):
                    cleaned_count +=1
            main_logger.info(f"Successfully deleted {cleaned_count} test expenses.")
        
        if db_conn_main:
            db_conn_main.close()
            main_logger.info("Database connection closed.")

    main_logger.info("\nExpense classifier test script finished.")
