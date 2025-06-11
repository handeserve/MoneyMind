from fastapi import APIRouter, Depends, HTTPException, Body
from sqlite3 import Connection
from typing import Optional, Dict, Any

# Pydantic models
from pydantic import BaseModel, Field

# DB Dependency
from presentation_layer.dependencies import get_db 

# AI Layer function
from ai_layer.expense_classifier import classify_batch_expenses, get_unclassified_expense_ids, classify_expense_by_id
from ai_layer.llm_interface import get_llm_classification
from ai_layer.config_manager import get_prompt_template, get_preset_categories
import logging # For logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Model for Request Body ---

class BatchClassifyRequest(BaseModel):
    limit: Optional[int] = Field(None, gt=0, description="Optional limit for the number of expenses to process in this batch.")
    max_workers: Optional[int] = Field(3, ge=1, le=10, description="Number of concurrent workers for parallel processing (1-10, default: 3)")

class ClassifyByIdRequest(BaseModel):
    expense_id: int = Field(..., description="The ID of the expense to classify")

# --- API Endpoints ---

@router.get("/unclassified_expense_ids", response_model=Dict[str, Any])
async def get_unclassified_ids(db: Connection = Depends(get_db)):
    """
    获取所有未分类记录的ID列表
    """
    try:
        result = get_unclassified_expense_ids(db)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unclassified expense IDs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get unclassified expense IDs")

@router.post("/classify_single_expense", response_model=Dict[str, Any])
async def classify_single_by_id(
    request: ClassifyByIdRequest,
    db: Connection = Depends(get_db)
):
    """
    根据ID分类单个记录
    """
    try:
        result = classify_expense_by_id(db, request.expense_id)
        return result
    except Exception as e:
        logger.error(f"Error classifying expense by ID {request.expense_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to classify expense: {str(e)}")

# --- API Endpoint for Batch Classification ---

@router.post("/batch_classify_expenses", response_model=Dict[str, Any])
async def trigger_batch_classify_expenses(
    # Allow request_body to be None if client sends empty JSON {} or no body for "no limit"
    # Or, make it explicit: `data: Optional[BatchClassifyRequest] = None`
    # Using Body(None) for optional body makes more sense than Optional[BatchClassifyRequest] = None
    # if we want to distinguish between no body and body with limit=null.
    # For this case, making request_body optional is fine.
    request_body: Optional[BatchClassifyRequest] = Body(None, description="Optional request body to specify a limit."), # Allows empty body for no limit
    db: Connection = Depends(get_db)
):
    """
    Triggers a batch AI classification process for unclassified expenses.
    """
    limit_value = request_body.limit if request_body and request_body.limit is not None else None
    max_workers_value = request_body.max_workers if request_body and request_body.max_workers is not None else 3
    
    logger.info(f"Received request for batch classification. Limit: {limit_value if limit_value is not None else 'None'}, Max Workers: {max_workers_value}")

    try:
        # Call the batch classification function from the AI layer
        summary = classify_batch_expenses(db, limit=limit_value, max_workers=max_workers_value)
        
        # The summary from classify_batch_expenses already contains messages and counts.
        # We can add a general API message if needed, or just return the detailed summary.
        
        # Example: if summary itself contains an "error" key from classify_batch_expenses
        if "error" in summary:
            logger.error(f"Batch classification function returned an error: {summary.get('details', summary['error'])}")
            # Determine appropriate status code based on error if possible, else 500
            raise HTTPException(status_code=500, detail=summary.get('details', summary['error']))

        # If no items matched criteria initially (handled by classify_batch_expenses returning specific summary)
        if summary.get("total_matching_criteria") == 0 and summary.get("processed_in_this_batch") == 0 :
            # This message is now part of the summary from classify_batch_expenses
            logger.info("Batch classification: No expenses found matching the criteria.")
            # Return summary as is, it should have "message": "No expenses to process."
            return summary
        
        # If some items were processed or attempted
        logger.info(f"Batch classification completed. Summary: {summary}")
        return summary

    except HTTPException: # Re-raise HTTPException if already raised (e.g. by get_db)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /batch_classify_expenses endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred during batch classification: {str(e)}")

if __name__ == "__main__":
    # This block is for context/documentation; direct execution isn't typical for routers.
    logging.basicConfig(level=logging.INFO)
    local_logger = logging.getLogger(__name__) # Use local_logger to avoid conflict with module-level logger
    local_logger.info("ai_router.py loaded. Defines batch classification endpoint.")
    local_logger.info("Pydantic model BatchClassifyRequest defined for optional limit.")
