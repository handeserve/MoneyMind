import logging
from sqlite3 import Connection
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

# Assuming get_db is in main.py, which is one level up from routers directory
# Adjust if get_db is moved to a dedicated db_dependencies.py
from ..main import get_db 

# Database CRUD operations and AI classifier
from ...database import database as db_ops # To call db_ops.get_expenses etc.
from ...ai_layer.expense_classifier import classify_single_expense

router = APIRouter()

# --- Pydantic Models ---
class ExpenseUpdateByUser(BaseModel):
    category_l1: Optional[str] = Field(None, description="User-confirmed or assigned L1 category.")
    category_l2: Optional[str] = Field(None, description="User-confirmed or assigned L2 category.")
    notes: Optional[str] = Field(None, description="Optional notes for the expense.")
    is_hidden: Optional[bool] = Field(None, description="Optional flag to hide the expense.")

class ExpenseResponse(BaseModel): # Example, can be more detailed based on db_ops.EXPENSE_COLUMNS
    id: int
    transaction_time: str
    amount: str # Stored as TEXT (string) in DB
    currency: str
    channel: Optional[str] = None
    source_raw_description: Optional[str] = None
    description_for_ai: Optional[str] = None
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    ai_suggestion_l1: Optional[str] = None
    ai_suggestion_l2: Optional[str] = None
    is_classified_by_ai: int
    is_confirmed_by_user: int
    is_hidden: int
    notes: Optional[str] = None
    external_transaction_id: Optional[str] = None
    external_merchant_id: Optional[str] = None
    source_provided_category: Optional[str] = None
    source_payment_method: Optional[str] = None
    source_transaction_status: Optional[str] = None
    imported_at: str
    updated_at: str
    
    class Config:
        orm_mode = True # For compatibility with SQLAlchemy-like objects, not strictly needed for dicts from sqlite3.Row

class PaginatedExpensesResponse(BaseModel):
    expenses: List[ExpenseResponse]
    total_count: int
    page: int
    per_page: int

# --- Router Endpoints ---

@router.get("/", response_model=PaginatedExpensesResponse)
async def list_expenses(
    db: Connection = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, 1-indexed."),
    per_page: int = Query(10, ge=1, le=100, description="Number of expenses per page."),
    sort_by: Optional[str] = Query(None, description=f"Column to sort by. Valid columns: {', '.join(db_ops.EXPENSE_COLUMNS)}."),
    sort_order: str = Query("ASC", pattern="^(ASC|DESC)$", description="Sort order: ASC or DESC."),
    channel: Optional[str] = Query(None, description="Filter by channel (e.g., 'WeChat Pay', 'Alipay')."),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD). Inclusive."),
    is_hidden: Optional[bool] = Query(None, description="Filter by hidden status (true/false)."),
    is_confirmed_by_user: Optional[bool] = Query(None, description="Filter by user confirmation status (true/false)."),
    category_l1: Optional[str] = Query(None, description="Filter by L1 category."),
    # Add more filters as needed based on db_ops.EXPENSE_COLUMNS
):
    """
    Retrieve a paginated list of expenses with optional sorting and filtering.
    """
    filters_dict = {}
    if channel is not None: filters_dict['channel'] = channel
    if start_date is not None: filters_dict['start_date'] = start_date
    if end_date is not None: filters_dict['end_date'] = end_date
    if is_hidden is not None: filters_dict['is_hidden'] = 1 if is_hidden else 0
    if is_confirmed_by_user is not None: filters_dict['is_confirmed_by_user'] = 1 if is_confirmed_by_user else 0
    if category_l1 is not None: filters_dict['category_l1'] = category_l1
    
    try:
        result = db_ops.get_expenses(
            db_connection=db,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order.upper(),
            filters=filters_dict
        )
        # Convert sqlite3.Row objects (if that's what get_expenses returns) to dicts for Pydantic
        # db_ops.get_expenses already returns list of dicts because conn.row_factory = sqlite3.Row
        return {
            "expenses": result['expenses'], 
            "total_count": result['total_count'],
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        logging.error(f"Error listing expenses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching expenses.")


@router.post("/{expense_id}/classify", response_model=ExpenseResponse)
async def trigger_ai_classification(
    expense_id: int = Path(..., ge=1, description="The ID of the expense to classify."),
    db: Connection = Depends(get_db)
):
    """
    Triggers AI classification for a single expense.
    If successful, returns the updated expense details.
    """
    try:
        # Check if expense exists first (optional, classify_single_expense also checks)
        expense = db_ops.get_expense_by_id(db, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")

        if expense.get('is_confirmed_by_user') == 1:
             raise HTTPException(status_code=400, detail=f"Expense ID {expense_id} is already confirmed by user. Cannot re-classify with AI.")

        success = classify_single_expense(db_conn=db, expense_id=expense_id)
        
        if success:
            updated_expense = db_ops.get_expense_by_id(db, expense_id)
            if updated_expense:
                return updated_expense # Pydantic will validate this dict
            else: # Should not happen if classify_single_expense succeeded and updated
                logging.error(f"AI Classification reported success for {expense_id}, but failed to retrieve updated record.")
                raise HTTPException(status_code=500, detail="Classification successful, but failed to retrieve updated record.")
        else:
            # classify_single_expense logs details, check if it was due to not found or other error
            # Re-fetch to see if it was a "not found" issue that classify_single_expense handled
            if not db_ops.get_expense_by_id(db, expense_id): # Check again, in case it was deleted mid-process
                 raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
            raise HTTPException(status_code=500, detail="AI classification failed. Check server logs.")
            
    except HTTPException: # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error during AI classification for expense {expense_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during AI classification for expense {expense_id}.")


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense_by_user(
    expense_id: int = Path(..., ge=1, description="The ID of the expense to update."),
    data: ExpenseUpdateByUser = Body(...),
    db: Connection = Depends(get_db)
):
    """
    Allows a user to manually update an expense's categories, notes, or hidden status.
    If category_l1 or category_l2 are provided, is_confirmed_by_user will be set to 1.
    """
    # Use model_dump for Pydantic V2+
    update_payload: Dict[str, Any] = data.model_dump(exclude_unset=True) 

    if not update_payload:
        raise HTTPException(status_code=400, detail="No update data provided.")

    # Conditionally set is_confirmed_by_user only if category fields are being updated
    if 'category_l1' in update_payload or 'category_l2' in update_payload:
        # Ensure both category fields are present if one is, for confirmation logic.
        # Or, the frontend should always send both if confirming.
        # For now, if either is present, we assume it's a category confirmation event.
        if not ('category_l1' in update_payload and 'category_l2' in update_payload and update_payload['category_l1'] and update_payload['category_l2']):
            raise HTTPException(status_code=400, detail="Both category_l1 and category_l2 must be provided and non-empty if confirming categories.")
        update_payload['is_confirmed_by_user'] = 1
    
    # If only 'notes' or 'is_hidden' is in update_payload, 'is_confirmed_by_user' is not set.

    try:
        # Check if expense exists
        existing_expense = db_ops.get_expense_by_id(db, expense_id)
        if not existing_expense:
            raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")

        success = db_ops.update_expense(db_connection=db, expense_id=expense_id, update_data=update_payload)
        
        if success:
            updated_expense = db_ops.get_expense_by_id(db, expense_id)
            if updated_expense:
                return updated_expense
            else: # Should not happen
                logging.error(f"Update for expense {expense_id} reported success, but failed to retrieve updated record.")
                raise HTTPException(status_code=500, detail="Update successful, but failed to retrieve updated record.")
        else:
            # update_expense logs details. If it returned False, it means rowcount was 0 (e.g. no change or ID not found)
            # Re-check if ID exists, as update_expense might not distinguish "not found" from "no change"
            if not db_ops.get_expense_by_id(db, expense_id):
                 raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found during update attempt.")
            raise HTTPException(status_code=400, detail=f"Failed to update expense {expense_id}. It might be that no data was changed or an error occurred.")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating expense {expense_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while updating expense {expense_id}.")


@router.delete("/{expense_id}", response_model=Dict[str, str])
async def delete_single_expense(
    expense_id: int = Path(..., ge=1, description="The ID of the expense to delete."),
    db: Connection = Depends(get_db)
):
    """
    Deletes a single expense by its ID.
    """
    try:
        # Check if expense exists before attempting delete for better error message
        existing_expense = db_ops.get_expense_by_id(db, expense_id)
        if not existing_expense:
            raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")

        success = db_ops.delete_expense(db_connection=db, expense_id=expense_id)
        
        if success:
            return {"message": f"Expense with ID {expense_id} successfully deleted."}
        else:
            # delete_expense logs details. If it returned False, it means rowcount was 0.
            # This could happen if the expense was deleted by another process just before this call.
            # Re-check if it exists to confirm.
            if db_ops.get_expense_by_id(db, expense_id):
                 raise HTTPException(status_code=500, detail=f"Failed to delete expense {expense_id}. An unknown error occurred.")
            # If it doesn't exist anymore, it implies a successful deletion (or it was already gone).
            # For idempotency, one might still return success, but standard is to report based on this call's action.
            # However, we already checked for existence, so if it was there and delete_expense failed, it's an issue.
            # Let's assume delete_expense returning false after existence check means an actual problem.
            raise HTTPException(status_code=500, detail=f"Failed to delete expense {expense_id}. Check server logs.")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting expense {expense_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while deleting expense {expense_id}.")

# Basic logging setup if this module is run directly (for testing, not typical)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("expenses_router.py loaded. This module is intended to be imported by main.py and run by Uvicorn.")
    logger.info(f"Valid expense columns for sorting/filtering: {db_ops.EXPENSE_COLUMNS}")
