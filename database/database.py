import sqlite3
import os
from datetime import datetime, timezone, date # Added timezone and date
from decimal import Decimal # Added Decimal for type hinting, though stored as TEXT

# Define the database file path in the project root
DATABASE_NAME = "personal_expenses.db"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(PROJECT_ROOT, DATABASE_NAME)

# List of valid columns for expenses table, useful for dynamic query building
EXPENSE_COLUMNS = [
    'id', 'transaction_time', 'amount', 'currency', 'channel', 
    'source_raw_description', 'description_for_ai', 'category_l1', 'category_l2',
    'ai_suggestion_l1', 'ai_suggestion_l2', 'is_classified_by_ai',
    'is_confirmed_by_user', 'is_hidden', 'notes', 'external_transaction_id',
    'external_merchant_id', 'source_provided_category', 'source_payment_method',
    'source_transaction_status', 'imported_at', 'updated_at'
]

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # Access columns by name
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_tables(conn):
    """Creates the necessary tables in the database if they don't already exist."""
    if conn is None:
        print("Database connection is not available. Cannot create tables.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_time TEXT NOT NULL, 
            amount TEXT NOT NULL, -- Storing Decimal as TEXT for precision
            currency TEXT NOT NULL DEFAULT 'CNY',
            channel TEXT, 
            source_raw_description TEXT,
            description_for_ai TEXT,
            category_l1 TEXT,
            category_l2 TEXT,
            ai_suggestion_l1 TEXT,
            ai_suggestion_l2 TEXT,
            is_classified_by_ai INTEGER NOT NULL DEFAULT 0, 
            is_confirmed_by_user INTEGER NOT NULL DEFAULT 0, 
            is_hidden INTEGER NOT NULL DEFAULT 0, 
            notes TEXT,
            external_transaction_id TEXT UNIQUE, 
            external_merchant_id TEXT,
            source_provided_category TEXT,
            source_payment_method TEXT,
            source_transaction_status TEXT,
            imported_at TEXT NOT NULL, 
            updated_at TEXT NOT NULL 
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            source_channel TEXT NOT NULL, 
            import_timestamp TEXT NOT NULL, 
            records_imported INTEGER NOT NULL,
            status TEXT 
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

# --- CRUD Operations for Expenses ---

def create_expense(db_connection, expense_data):
    """
    Creates a new expense record.
    expense_data is a dict. Ensure 'amount' is string or Decimal.
    """
    current_time_iso = datetime.now(timezone.utc).isoformat()
    
    # Fields that must be provided by expense_data (example, adapt as needed)
    # For manual creation, many fields might be optional or have defaults.
    required_fields = ['transaction_time', 'amount', 'channel', 'source_raw_description']
    for field in required_fields:
        if field not in expense_data:
            raise ValueError(f"Missing required field for creating expense: {field}")

    # Prepare data, ensuring amount is string
    expense_data['amount'] = str(expense_data['amount'])
    expense_data.setdefault('currency', 'CNY')
    expense_data.setdefault('description_for_ai', expense_data['source_raw_description'])
    expense_data.setdefault('is_classified_by_ai', 0)
    expense_data.setdefault('is_confirmed_by_user', 0)
    expense_data.setdefault('is_hidden', 0)
    expense_data['imported_at'] = expense_data.get('imported_at', current_time_iso) # Can be overridden if needed
    expense_data['updated_at'] = current_time_iso

    # Filter expense_data to only include valid columns
    valid_data = {k: v for k, v in expense_data.items() if k in EXPENSE_COLUMNS and k != 'id'}
    
    cols = ', '.join(valid_data.keys())
    placeholders = ', '.join(['?'] * len(valid_data))
    sql = f"INSERT INTO expenses ({cols}) VALUES ({placeholders})"
    
    try:
        with db_connection: # Manages commit/rollback
            cursor = db_connection.cursor()
            cursor.execute(sql, list(valid_data.values()))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error creating expense: {e}")
        # Specific check for UNIQUE constraint, e.g., on external_transaction_id
        if "UNIQUE constraint failed" in str(e) and 'external_transaction_id' in str(e):
            print(f"Potential duplicate: An expense with external_transaction_id '{expense_data.get('external_transaction_id')}' may already exist.")
        return None

def get_expense_by_id(db_connection, expense_id):
    """Fetches a single expense by its ID."""
    try:
        with db_connection:
            cursor = db_connection.cursor()
            cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching expense by ID {expense_id}: {e}")
        return None

def _build_where_clause(filters):
    """Helper function to build WHERE clause and parameters from filters."""
    where_clauses = []
    params = []

    if filters:
        for key, value in filters.items():
            if key == 'start_date':
                # Ensure value is a valid date string, append time for full day coverage
                where_clauses.append("transaction_time >= ?")
                params.append(f"{value} 00:00:00")
            elif key == 'end_date':
                where_clauses.append("transaction_time <= ?")
                params.append(f"{value} 23:59:59")
            elif key == 'category_l1_is_null' and value:
                where_clauses.append("(category_l1 IS NULL OR category_l1 = '')")
            elif key in EXPENSE_COLUMNS: # Exact match for other valid columns
                where_clauses.append(f"{key} = ?")
                params.append(value)
            else:
                print(f"Warning: Invalid filter key '{key}'. Ignoring.")

    where_query = ""
    if where_clauses:
        where_query = " WHERE " + " AND ".join(where_clauses)
    
    return where_query, params

def get_expenses(db_connection, page=1, per_page=10, sort_by=None, sort_order='ASC', filters=None):
    """
    Fetches expenses with pagination, sorting, and filtering.
    Filters dict can include 'start_date', 'end_date', and other column exact matches.
    """
    if sort_by is None:
        sort_by = 'transaction_time'
    if sort_by not in EXPENSE_COLUMNS:
        print(f"Warning: Invalid sort_by column '{sort_by}'. Defaulting to 'transaction_time'.")
        sort_by = 'transaction_time'
    
    if sort_order.upper() not in ['ASC', 'DESC']:
        print(f"Warning: Invalid sort_order '{sort_order}'. Defaulting to 'ASC'.")
        sort_order = 'ASC'

    offset = (page - 1) * per_page
    
    # Use the helper function to build WHERE clause
    where_query, params = _build_where_clause(filters)
    base_query = "FROM expenses"

    # Query for total count
    count_sql = f"SELECT COUNT(*) as total_count {base_query} {where_query}"
    
    # Query for paginated expenses
    expenses_sql = f"SELECT * {base_query} {where_query} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?"
    params_for_expenses = params + [per_page, offset]

    try:
        with db_connection:
            cursor = db_connection.cursor()
            
            cursor.execute(count_sql, params)
            total_count_row = cursor.fetchone()
            total_count = total_count_row['total_count'] if total_count_row else 0
            
            cursor.execute(expenses_sql, params_for_expenses)
            rows = cursor.fetchall()
            expenses_list = [dict(row) for row in rows]
            
            return {'expenses': expenses_list, 'total_count': total_count}
            
    except sqlite3.Error as e:
        print(f"Error fetching expenses: {e}")
        return {'expenses': [], 'total_count': 0}


def get_unclassified_expenses(db_connection, limit=None):
    """Fetches expenses not yet classified by AI or confirmed by user."""
    sql = "SELECT * FROM expenses WHERE is_classified_by_ai = 0 AND is_confirmed_by_user = 0"
    params = []
    if limit and isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    
    try:
        with db_connection:
            cursor = db_connection.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error fetching unclassified expenses: {e}")
        return []

def update_expense(db_connection, expense_id, update_data):
    """
    Updates an expense record.
    update_data is a dict of columns to update.
    'updated_at' is automatically set.
    """
    if not update_data:
        print("No data provided for update.")
        return False

    # Ensure amount is string if provided
    if 'amount' in update_data:
        update_data['amount'] = str(update_data['amount'])
        
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

    # Filter update_data to only include valid columns, exclude id and imported_at
    valid_update_data = {k: v for k, v in update_data.items() if k in EXPENSE_COLUMNS and k not in ['id', 'imported_at']}
    
    if not valid_update_data:
        print("No valid fields to update after filtering.")
        return False

    set_clauses = [f"{key} = ?" for key in valid_update_data.keys()]
    sql = f"UPDATE expenses SET {', '.join(set_clauses)} WHERE id = ?"
    
    params = list(valid_update_data.values()) + [expense_id]
    
    try:
        with db_connection:
            cursor = db_connection.cursor()
            cursor.execute(sql, params)
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating expense ID {expense_id}: {e}")
        return False

def delete_expense(db_connection, expense_id):
    """Deletes an expense by its ID."""
    try:
        with db_connection:
            cursor = db_connection.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting expense ID {expense_id}: {e}")
        return False

def batch_delete_expenses(db_connection, expense_ids: list[int]):
    """Deletes multiple expenses by a list of their IDs."""
    if not expense_ids:
        return 0
    try:
        with db_connection:
            cursor = db_connection.cursor()
            placeholders = ', '.join(['?'] * len(expense_ids))
            sql = f"DELETE FROM expenses WHERE id IN ({placeholders})"
            cursor.execute(sql, expense_ids)
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error batch deleting expenses: {e}")
        return 0

def batch_clear_categories(db_connection, expense_ids: list[int]):
    """Clears category information for multiple expenses."""
    if not expense_ids:
        return 0
    try:
        with db_connection:
            cursor = db_connection.cursor()
            placeholders = ', '.join(['?'] * len(expense_ids))
            sql = f"""
                UPDATE expenses 
                SET 
                    category_l1 = NULL, 
                    category_l2 = NULL,
                    is_classified_by_ai = 0,
                    is_confirmed_by_user = 0,
                    updated_at = ?
                WHERE id IN ({placeholders})
            """
            params = [datetime.now(timezone.utc).isoformat()] + expense_ids
            cursor.execute(sql, params)
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error batch clearing categories: {e}")
        return 0

def batch_clear_all_categories(db_connection, filters=None):
    """Clears category information for all expenses matching the given filters."""
    try:
        with db_connection:
            cursor = db_connection.cursor()
            
            # Build WHERE clause from filters
            where_clause, params = _build_where_clause(filters or {})
            
            sql = f"""
                UPDATE expenses 
                SET 
                    category_l1 = NULL, 
                    category_l2 = NULL,
                    is_classified_by_ai = 0,
                    is_confirmed_by_user = 0,
                    updated_at = ?
                {where_clause}
            """
            params = [datetime.now(timezone.utc).isoformat()] + params
            cursor.execute(sql, params)
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error batch clearing all categories: {e}")
        return 0

def batch_delete_all_expenses(db_connection, filters=None):
    """Deletes all expenses matching the given filters."""
    try:
        with db_connection:
            cursor = db_connection.cursor()
            
            # Build WHERE clause from filters
            where_clause, params = _build_where_clause(filters or {})
            
            sql = f"DELETE FROM expenses {where_clause}"
            cursor.execute(sql, params)
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error batch deleting all expenses: {e}")
        return 0

if __name__ == '__main__':
    print(f"Initializing database at: {DATABASE_PATH}")
    # For testing, delete DB if it exists for a clean run
    # if os.path.exists(DATABASE_PATH):
    #     os.remove(DATABASE_PATH)
    #     print("Deleted existing database for a clean test run.")

    conn = get_db_connection()
    if conn:
        create_tables(conn)
        print("Database tables ensured/created.")

        # --- Test CRUD Operations ---
        print("\n--- Testing CRUD Operations ---")

        # 1. Create Expense
        print("\n1. Testing Create Expense...")
        expense1_data = {
            'transaction_time': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
            'amount': Decimal("100.50"), # Use Decimal for input, will be converted to str
            'channel': 'Manual Test',
            'source_raw_description': 'Lunch at Testaurant',
            'notes': 'Team lunch',
            'external_transaction_id': 'MANUAL_TEST_001' 
        }
        expense1_id = create_expense(conn, expense1_data)
        print(f"Created expense with ID: {expense1_id}")

        expense2_data = {
            'transaction_time': datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
            'amount': "75.00", # Amount as string
            'channel': 'Manual Test',
            'source_raw_description': 'Groceries',
            'category_l1': 'Food',
            'is_confirmed_by_user': 1, # Already confirmed
            'external_transaction_id': 'MANUAL_TEST_002'
        }
        expense2_id = create_expense(conn, expense2_data)
        print(f"Created expense with ID: {expense2_id}")
        
        expense3_data = { # For unclassified test
            'transaction_time': datetime(2024, 1, 17, 14, 0, 0, tzinfo=timezone.utc).isoformat(),
            'amount': Decimal("25.00"),
            'channel': 'Other Test',
            'source_raw_description': 'Coffee',
            'external_transaction_id': 'MANUAL_TEST_003'
        }
        expense3_id = create_expense(conn, expense3_data)
        print(f"Created expense with ID: {expense3_id}")

        # Test creation with duplicate external_transaction_id
        expense_dup_data = {
            'transaction_time': datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc).isoformat(),
            'amount': Decimal("50.00"),
            'channel': 'Manual Test',
            'source_raw_description': 'Duplicate Test',
            'external_transaction_id': 'MANUAL_TEST_001' # Duplicate external_transaction_id
        }
        dup_id = create_expense(conn, expense_dup_data)
        print(f"Attempted creation with duplicate external_transaction_id, result ID: {dup_id} (expected None or error msg)")


        # 2. Get Expense by ID
        print("\n2. Testing Get Expense by ID...")
        if expense1_id:
            retrieved_expense = get_expense_by_id(conn, expense1_id)
            print(f"Retrieved expense {expense1_id}: {retrieved_expense}")
        retrieved_non_existent = get_expense_by_id(conn, 99999)
        print(f"Retrieved non-existent expense 99999: {retrieved_non_existent}")

        # 3. Get Expenses (All, Filtered, Sorted, Paginated)
        print("\n3. Testing Get Expenses...")
        all_expenses_page1 = get_expenses(conn, page=1, per_page=2)
        print(f"All expenses (Page 1, 2 per page): {all_expenses_page1['expenses']}")
        print(f"Total count: {all_expenses_page1['total_count']}")

        all_expenses_page2 = get_expenses(conn, page=2, per_page=2)
        print(f"All expenses (Page 2, 2 per page): {all_expenses_page2['expenses']}")


        filtered_expenses = get_expenses(conn, filters={'channel': 'Manual Test', 'start_date': '2024-01-15', 'end_date': '2024-01-16'})
        print(f"Filtered expenses (Channel 'Manual Test', 2024-01-15 to 2024-01-16): {filtered_expenses['expenses']}")
        print(f"Total count for filter: {filtered_expenses['total_count']}")
        
        # Test with is_hidden filter (assuming default is 0)
        hidden_expenses_filter = get_expenses(conn, filters={'is_hidden': 0})
        print(f"Filtered expenses (is_hidden=0): Count {hidden_expenses_filter['total_count']}")

        sorted_expenses = get_expenses(conn, sort_by='amount', sort_order='DESC')
        print(f"Expenses sorted by amount DESC: {[e['amount'] for e in sorted_expenses['expenses']]}")

        # 4. Get Unclassified Expenses
        print("\n4. Testing Get Unclassified Expenses...")
        unclassified = get_unclassified_expenses(conn)
        print(f"Unclassified expenses ({len(unclassified)}):")
        for ue in unclassified:
            print(f"  ID: {ue['id']}, Desc: {ue['source_raw_description']}, AI: {ue['is_classified_by_ai']}, User: {ue['is_confirmed_by_user']}")
        
        unclassified_limit1 = get_unclassified_expenses(conn, limit=1)
        print(f"Unclassified expenses (limit 1): {len(unclassified_limit1)}")


        # 5. Update Expense
        print("\n5. Testing Update Expense...")
        if expense1_id:
            update_success = update_expense(conn, expense1_id, {'notes': 'Updated team lunch notes', 'category_l1': 'Food', 'amount': Decimal("105.75")})
            print(f"Update for expense {expense1_id} successful: {update_success}")
            updated_expense = get_expense_by_id(conn, expense1_id)
            print(f"Updated expense {expense1_id} data: {updated_expense['notes']}, {updated_expense['category_l1']}, Amount: {updated_expense['amount']}, Updated_at: {updated_expense['updated_at']}")

        # 6. Delete Expense
        print("\n6. Testing Delete Expense...")
        if expense2_id:
            delete_success = delete_expense(conn, expense2_id)
            print(f"Delete for expense {expense2_id} successful: {delete_success}")
            deleted_expense_check = get_expense_by_id(conn, expense2_id)
            print(f"Check deleted expense {expense2_id}: {deleted_expense_check}")
        
        # Verify total count after deletion
        final_count_check = get_expenses(conn)
        print(f"Final total expenses after tests: {final_count_check['total_count']}")

        conn.close()
        print("\nDatabase operations test complete. Connection closed.")
    else:
        print("Database initialization failed. Cannot run tests.")
