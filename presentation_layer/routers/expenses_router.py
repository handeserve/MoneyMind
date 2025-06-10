import logging
from sqlite3 import Connection
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
import sqlite3

# Assuming get_db is in main.py, which is one level up from routers directory
# Adjust if get_db is moved to a dedicated db_dependencies.py
from presentation_layer.dependencies import get_db 

# Database CRUD operations and AI classifier
from database import database as db_ops
from ai_layer.expense_classifier import classify_single_expense

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
):
    filters_dict = {}
    if channel is not None: filters_dict['channel'] = channel
    if start_date is not None: filters_dict['start_date'] = start_date
    if end_date is not None: filters_dict['end_date'] = end_date
    if is_hidden is not None: filters_dict['is_hidden'] = 1 if is_hidden else 0
    if is_confirmed_by_user is not None: filters_dict['is_confirmed_by_user'] = 1 if is_confirmed_by_user else 0
    if category_l1 is not None: filters_dict['category_l1'] = category_l1
    try:
        with sqlite3.connect(db_ops.DATABASE_PATH) as db:
            db.row_factory = sqlite3.Row
            result = db_ops.get_expenses(
                db_connection=db,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order.upper(),
                filters=filters_dict
            )
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
):
    try:
        with sqlite3.connect(db_ops.DATABASE_PATH) as db:
            db.row_factory = sqlite3.Row
            expense = db_ops.get_expense_by_id(db, expense_id)
            if not expense:
                raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
            if expense.get('is_confirmed_by_user') == 1:
                raise HTTPException(status_code=400, detail=f"Expense ID {expense_id} is already confirmed by user. Cannot re-classify with AI.")
            success = classify_single_expense(db_conn=db, expense_id=expense_id)
            if success:
                updated_expense = db_ops.get_expense_by_id(db, expense_id)
                if updated_expense:
                    return updated_expense
                else:
                    logging.error(f"AI Classification reported success for {expense_id}, but failed to retrieve updated record.")
                    raise HTTPException(status_code=500, detail="Classification successful, but failed to retrieve updated record.")
            else:
                if not db_ops.get_expense_by_id(db, expense_id):
                    raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
                raise HTTPException(status_code=500, detail="AI classification failed. Check server logs.")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during AI classification for expense {expense_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during AI classification for expense {expense_id}.")

@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense_by_user(
    expense_id: int = Path(..., ge=1, description="The ID of the expense to update."),
    data: ExpenseUpdateByUser = Body(...),
):
    update_payload: Dict[str, Any] = data.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(status_code=400, detail="No update data provided.")
    if 'category_l1' in update_payload or 'category_l2' in update_payload:
        if not ('category_l1' in update_payload and 'category_l2' in update_payload and update_payload['category_l1'] and update_payload['category_l2']):
            raise HTTPException(status_code=400, detail="Both category_l1 and category_l2 must be provided and non-empty if confirming categories.")
        update_payload['is_confirmed_by_user'] = 1
    try:
        with sqlite3.connect(db_ops.DATABASE_PATH) as db:
            db.row_factory = sqlite3.Row
            existing_expense = db_ops.get_expense_by_id(db, expense_id)
            if not existing_expense:
                raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
            success = db_ops.update_expense(db_connection=db, expense_id=expense_id, update_data=update_payload)
            if success:
                updated_expense = db_ops.get_expense_by_id(db, expense_id)
                if updated_expense:
                    return updated_expense
                else:
                    logging.error(f"Update for expense {expense_id} reported success, but failed to retrieve updated record.")
                    raise HTTPException(status_code=500, detail="Update successful, but failed to retrieve updated record.")
            else:
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
):
    try:
        with sqlite3.connect(db_ops.DATABASE_PATH) as db:
            db.row_factory = sqlite3.Row
            existing_expense = db_ops.get_expense_by_id(db, expense_id)
            if not existing_expense:
                raise HTTPException(status_code=404, detail=f"Expense with ID {expense_id} not found.")
            success = db_ops.delete_expense(db_connection=db, expense_id=expense_id)
            if success:
                return {"message": f"Expense with ID {expense_id} successfully deleted."}
            else:
                if db_ops.get_expense_by_id(db, expense_id):
                    raise HTTPException(status_code=500, detail=f"Failed to delete expense {expense_id}. An unknown error occurred.")
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
