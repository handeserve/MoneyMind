from fastapi import APIRouter, HTTPException, Body, status, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from ai_layer import config_manager as cm
from ai_layer.llm_interface import get_llm_classification
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---

class StandardResponse(BaseModel):
    message: str

class ValuePayload(BaseModel):
    value: Any

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)

class CategoryUpdate(BaseModel):
    new_name: str = Field(..., min_length=1)

class AllCategoriesResponse(BaseModel):
    categories: Dict[str, List[str]]

# --- Endpoints for General Settings ---

@router.get("", response_model=Dict[str, Any])
async def get_full_config():
    """Retrieves the entire current configuration."""
    logger.info("GET /settings endpoint called.")
    return cm.get_config(force_reload=True)

@router.put("/{config_path:path}", response_model=StandardResponse)
async def update_config_by_path(config_path: str, payload: ValuePayload):
    """
    Updates a specific configuration value identified by a dot-separated key path.
    Saves the configuration after updating.
    """
    try:
        logger.info(f"Attempting to update config path '{config_path}' with value: {payload.value}")
        if not cm.update_config_value(config_path, payload.value):
            # This path is less likely now with the generic update_config_value
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Update in memory failed.")
        
        if not cm.save_config():
            cm.get_config(force_reload=True) # Reload to discard in-memory changes
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration to file.")
            
        return StandardResponse(message=f"Configuration path '{config_path}' updated successfully.")
    
    except Exception as e:
        logger.error(f"Failed to update configuration for path '{config_path}'. Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update configuration for path: {config_path}. Check logs for details."
        )

# --- Endpoint for AI Connection Test ---

class TestAIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

@router.get("/test-ai", response_model=TestAIResponse)
async def test_ai_connection_endpoint():
    """
    Tests the connection to the active AI service by making a simple classification call.
    """
    logger.info("GET /test-ai endpoint called.")
    try:
        result = get_llm_classification(description="这是AI连接测试")
        
        if result is None:
            # Should not happen unless there's a catastrophic error in llm_interface
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Test failed: Received None result.")

        if "error" in result:
            logger.error(f"AI connection test failed with error: {result}")
            # Map internal error codes to user-friendly messages
            error_code = result.get("error", "UNKNOWN_ERROR")
            error_detail = result.get("detail", "No details provided.")
            
            message = "AI连接测试失败。"
            if "API_HTTP_ERROR_401" in error_code:
                message = "AI连接测试失败：API密钥无效或未授权。"
            elif "API_HTTP_ERROR" in error_code:
                message = f"AI连接测试失败：API返回HTTP错误码。详情: {error_detail}"
            elif "API_NETWORK_ERROR" in error_code:
                message = "AI连接测试失败：无法连接到AI服务，请检查网络或Base URL。"
            elif "placeholder" in error_detail:
                 message = "AI连接测试失败：API密钥似乎是一个占位符，请更新配置。"

            return TestAIResponse(success=False, message=message, data=result)

        if result.get("ai_suggestion_l1"):
            message = f"AI连接测试成功！服务返回分类: {result.get('ai_suggestion_l1')} / {result.get('ai_suggestion_l2')}"
            return TestAIResponse(success=True, message=message, data=result)
        else:
            message = "AI连接测试成功，但未能获得有效的分类结果。"
            return TestAIResponse(success=True, message=message, data=result)

    except Exception as e:
        logger.error(f"An unexpected error occurred during AI connection test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发生意外错误: {e}")


# --- Endpoints for Category Management ---

@router.get("/categories", response_model=AllCategoriesResponse)
async def get_all_categories_endpoint():
    logger.info("GET /categories endpoint called.")
    return AllCategoriesResponse(categories=cm.get_preset_categories())

@router.post("/categories/l1", status_code=201, response_model=StandardResponse)
async def create_l1_category_endpoint(category: CategoryCreate):
    logger.info(f"POST /categories/l1 with name: {category.name}.")
    if not cm.add_l1_category_config(category.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"L1 category '{category.name}' may already exist.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L1 category '{category.name}' created.")

@router.put("/categories/l1/{l1_name}", response_model=StandardResponse)
async def update_l1_category_endpoint(l1_name: str, category_update: CategoryUpdate):
    logger.info(f"PUT /categories/l1/{l1_name} to: {category_update.new_name}.")
    if not cm.update_l1_category_config(l1_name, category_update.new_name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"L1 category '{l1_name}' not found or new name is invalid.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L1 category '{l1_name}' updated to '{category_update.new_name}'.")

@router.delete("/categories/l1/{l1_name}", status_code=200, response_model=StandardResponse)
async def delete_l1_category_endpoint(l1_name: str):
    logger.info(f"DELETE /categories/l1/{l1_name}.")
    if not cm.delete_l1_category_config(l1_name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"L1 category '{l1_name}' not found.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L1 category '{l1_name}' deleted.")

@router.post("/categories/l1/{l1_name}/l2", status_code=201, response_model=StandardResponse)
async def create_l2_category_endpoint(l1_name: str, category_l2: CategoryCreate):
    logger.info(f"POST /categories/l1/{l1_name}/l2 with name: {category_l2.name}.")
    if not cm.add_l2_category_config(l1_name, category_l2.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Failed to add L2 category. L1 '{l1_name}' not found or L2 already exists.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L2 category '{category_l2.name}' added to L1 '{l1_name}'.")

@router.put("/categories/l2/{l1_name}/{l2_name}", response_model=StandardResponse)
async def update_l2_category_endpoint(l1_name: str, l2_name: str, category_l2_update: CategoryUpdate):
    logger.info(f"PUT /categories/l2/{l1_name}/{l2_name} to: {category_l2_update.new_name}.")
    if not cm.update_l2_category_config(l1_name, l2_name, category_l2_update.new_name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"L2 category '{l2_name}' under L1 '{l1_name}' not found or new name is invalid.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L2 category '{l2_name}' updated to '{category_l2_update.new_name}'.")

@router.delete("/categories/l2/{l1_name}/{l2_name}", status_code=200, response_model=StandardResponse)
async def delete_l2_category_endpoint(l1_name: str, l2_name: str):
    logger.info(f"DELETE /categories/l2/{l1_name}/{l2_name}.")
    if not cm.delete_l2_category_config(l1_name, l2_name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"L2 category '{l2_name}' under L1 '{l1_name}' not found.")
    if not cm.save_config():
        cm.get_config(force_reload=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save configuration.")
    return StandardResponse(message=f"L2 category '{l2_name}' deleted from L1 '{l1_name}'.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("settings_router.py loaded. Intended for import by main FastAPI app.")
    logger.info("Defined Pydantic models and placeholder endpoints for category and AI configuration management.")
