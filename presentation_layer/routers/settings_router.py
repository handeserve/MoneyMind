from fastapi import APIRouter, Depends, HTTPException, Body
from sqlite3 import Connection # For type hinting, though not used by these specific endpoints
from typing import List, Dict, Optional, Any

# Pydantic models
from pydantic import BaseModel, Field

# Assuming get_db is in main.py, which is one level up from routers directory
# It's included for consistency, though category management might not directly use the DB here.
from presentation_layer.dependencies import get_db 

# Import config_manager from ai_layer. We'll use its functions later.
from ai_layer import config_manager as cm 
import logging # For logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models for Category Management ---

class CategoryL2(BaseModel): # Not directly used in request/response but represents structure
    name: str

class CategoryL1(BaseModel): # Not directly used in request/response but represents structure
    name: str
    l2_categories: List[CategoryL2] = []

class CategoryL1Create(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the new L1 category.")

class CategoryL1Update(BaseModel):
    new_name: str = Field(..., min_length=1, description="New name for the L1 category.")

class CategoryL2Create(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the new L2 category.")

class CategoryL2Update(BaseModel):
    new_name: str = Field(..., min_length=1, description="New name for the L2 category.")

class AllCategoriesResponse(BaseModel):
    categories: Dict[str, List[str]] # L1 name -> List of L2 names (strings)

class ResponseMessage(BaseModel):
    message: str

# --- Endpoints for Category Management ---

@router.get("/categories", response_model=AllCategoriesResponse)
async def get_all_categories_endpoint():
    """
    Retrieves the current category hierarchy (L1 and L2 categories).
    """
    logger.info("GET /categories endpoint called.")
    preset_cats = cm.get_preset_categories()
    if preset_cats is None: # Should not happen if get_preset_categories returns {} on fail
        logger.error("Failed to load categories from configuration in GET /categories.")
        raise HTTPException(status_code=500, detail="Failed to load categories from configuration.")
    return AllCategoriesResponse(categories=preset_cats)

@router.post("/categories/l1", status_code=201, response_model=ResponseMessage)
async def create_l1_category_endpoint(category: CategoryL1Create):
    """
    Creates a new L1 category.
    """
    logger.info(f"POST /categories/l1 called with L1 name: {category.name}.")
    if not cm.add_l1_category_config(category.name):
        raise HTTPException(status_code=400, detail=f"L1 category '{category.name}' may already exist or is invalid.")
    if not cm.save_config():
        cm.clear_cached_config() # Attempt to revert in-memory change on failed save
        cm.get_config(force_reload=True) # Reload original state
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after adding L1 category.")
    return ResponseMessage(message=f"L1 category '{category.name}' added and configuration saved.")

@router.put("/categories/l1/{l1_name}", response_model=ResponseMessage)
async def update_l1_category_endpoint(l1_name: str, category_update: CategoryL1Update):
    """
    Updates the name of an existing L1 category.
    """
    logger.info(f"PUT /categories/l1/{l1_name} called to update to: {category_update.new_name}.")
    if not cm.update_l1_category_config(l1_name, category_update.new_name):
        raise HTTPException(status_code=404, detail=f"L1 category '{l1_name}' not found or new name '{category_update.new_name}' is invalid/duplicate.")
    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after updating L1 category.")
    return ResponseMessage(message=f"L1 category '{l1_name}' updated to '{category_update.new_name}' and configuration saved.")

@router.delete("/categories/l1/{l1_name}", status_code=200, response_model=ResponseMessage)
async def delete_l1_category_endpoint(l1_name: str):
    """
    Deletes an L1 category and all its L2 subcategories.
    """
    logger.info(f"DELETE /categories/l1/{l1_name} called.")
    if not cm.delete_l1_category_config(l1_name):
        raise HTTPException(status_code=404, detail=f"L1 category '{l1_name}' not found.")
    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after deleting L1 category.")
    return ResponseMessage(message=f"L1 category '{l1_name}' and its L2 categories deleted. Configuration saved.")

@router.post("/categories/l1/{l1_name}/l2", status_code=201, response_model=ResponseMessage)
async def create_l2_category_endpoint(l1_name: str, category_l2: CategoryL2Create):
    """
    Creates a new L2 category under a specified L1 category.
    """
    logger.info(f"POST /categories/l1/{l1_name}/l2 called with L2 name: {category_l2.name}.")
    if not cm.add_l2_category_config(l1_name, category_l2.name):
        raise HTTPException(status_code=400, detail=f"Failed to add L2 category '{category_l2.name}'. L1 '{l1_name}' might not exist, or L2 already exists/is invalid.")
    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after adding L2 category.")
    return ResponseMessage(message=f"L2 category '{category_l2.name}' added under L1 '{l1_name}'. Configuration saved.")

@router.put("/categories/l2/{l1_name}/{l2_name}", response_model=ResponseMessage)
async def update_l2_category_endpoint(l1_name: str, l2_name: str, category_l2_update: CategoryL2Update):
    """
    Updates the name of an existing L2 category under a specified L1 category.
    """
    logger.info(f"PUT /categories/l2/{l1_name}/{l2_name} called to update to: {category_l2_update.new_name}.")
    if not cm.update_l2_category_config(l1_name, l2_name, category_l2_update.new_name):
        raise HTTPException(status_code=404, detail=f"L2 category '{l2_name}' under L1 '{l1_name}' not found, or new name '{category_l2_update.new_name}' is invalid/duplicate.")
    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after updating L2 category.")
    return ResponseMessage(message=f"L2 category '{l2_name}' under L1 '{l1_name}' updated to '{category_l2_update.new_name}'. Configuration saved.")

@router.delete("/categories/l2/{l1_name}/{l2_name}", status_code=200, response_model=ResponseMessage)
async def delete_l2_category_endpoint(l1_name: str, l2_name: str):
    """
    Deletes an L2 category from under a specified L1 category.
    """
    logger.info(f"DELETE /categories/l2/{l1_name}/{l2_name} called.")
    if not cm.delete_l2_category_config(l1_name, l2_name):
        raise HTTPException(status_code=404, detail=f"L2 category '{l2_name}' under L1 '{l1_name}' not found.")
    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration to file after deleting L2 category.")
    return ResponseMessage(message=f"L2 category '{l2_name}' deleted from L1 '{l1_name}'. Configuration saved.")


# --- Pydantic Models for AI Configuration ---

class AIModelParams(BaseModel):
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0) # Temperature can sometimes go up to 2.0
    max_tokens: Optional[int] = Field(None, gt=0)
    model_name: Optional[str] = Field(None, min_length=1)

class AIServiceConfig(BaseModel):
    api_key: Optional[str] = Field(None, description="API Key. Omitted in GET responses. Provide for updates.")
    model_params: Optional[AIModelParams] = None

class AIPromptTemplate(BaseModel):
    name: str = Field(..., description="Logical name of the prompt template, e.g., 'classification_prompt_template'.")
    content: str = Field(..., description="The content of the prompt template.")

class AIConfigResponse(BaseModel):
    default_llm_service: Optional[str] = None
    llm_services: Dict[str, AIServiceConfig] = Field(default_factory=dict, description="Configuration for each LLM service. API keys will be masked.")
    prompt_templates: List[AIPromptTemplate] = Field(default_factory=list)

class AIConfigUpdate(BaseModel):
    default_llm_service: Optional[str] = None
    llm_services_update: Optional[Dict[str, AIServiceConfig]] = Field(None, description="Update specific LLM service configurations. Include api_key or model_params to update.")
    prompt_templates_update: Optional[List[AIPromptTemplate]] = Field(None, description="Update specific prompt templates. Identified by name.")


# --- Endpoints for AI Configuration Management ---

def _build_ai_config_response() -> AIConfigResponse:
    """Helper to build the AIConfigResponse, masking API keys."""
    config = cm.get_config() # Get current config (potentially modified in-memory, then reloaded if saved)
    services_config_response = {}
    
    # Use the new llm_services structure from config_manager
    for service_name, service_data in config.get('llm_services', {}).items():
        # Ensure model_params is a dict, even if empty, to pass to AIModelParams
        model_params_data = service_data.get('model_params', {})
        services_config_response[service_name] = AIServiceConfig(
            api_key="********" if service_data.get('api_key') else None, # Mask API key
            model_params=AIModelParams(**model_params_data) if model_params_data else None
        )
    
    prompts_list_response = []
    for name, content in config.get('prompts', {}).items():
        prompts_list_response.append(AIPromptTemplate(name=name, content=content))

    return AIConfigResponse(
        default_llm_service=config.get('default_llm_service'),
        llm_services=services_config_response,
        prompt_templates=prompts_list_response
    )

@router.get("/ai_config", response_model=AIConfigResponse)
async def get_ai_config_endpoint():
    """
    Retrieves the current AI configuration (default service, service details, prompts).
    API keys for LLM services will be masked.
    """
    logger.info("GET /ai_config endpoint called.")
    try:
        # Ensure config is loaded if not already
        cm.get_config() # This loads or uses cached
        return _build_ai_config_response()
    except Exception as e:
        logger.error(f"Error retrieving AI config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve AI configuration.")


@router.put("/ai_config", response_model=ResponseMessage) # Changed response model for simplicity
async def update_ai_config_endpoint(config_update: AIConfigUpdate):
    """
    Updates AI configurations. This will save changes to config.yaml.
    Provide only the fields that need to be updated.
    """
    logger.info(f"PUT /ai_config called with data: {config_update.dict(exclude_none=True)}.")
    
    # Ensure config is loaded into memory first to apply changes
    cm.get_config(force_reload=True) # Get a fresh copy before applying updates

    any_update_failed = False

    if config_update.default_llm_service is not None:
        if not cm.update_default_llm_service_config(config_update.default_llm_service):
            any_update_failed = True
            logger.warning(f"Failed to update default_llm_service to {config_update.default_llm_service}")

    if config_update.llm_services_update:
        for service_name, service_config_data in config_update.llm_services_update.items():
            if service_config_data.api_key is not None:
                if not cm.update_llm_service_api_key_config(service_name, service_config_data.api_key):
                    any_update_failed = True
                    logger.warning(f"Failed to update api_key for {service_name}")
            
            if service_config_data.model_params is not None:
                # Pass model_params as dict, exclude Nones to avoid overwriting with None
                params_to_update = service_config_data.model_params.dict(exclude_none=True)
                if not cm.update_llm_service_model_params_config(service_name, params_to_update):
                    any_update_failed = True
                    logger.warning(f"Failed to update model_params for {service_name} with {params_to_update}")

    if config_update.prompt_templates_update:
        for prompt_data in config_update.prompt_templates_update:
            if not cm.update_prompt_template_config(prompt_data.name, prompt_data.content):
                any_update_failed = True
                logger.warning(f"Failed to update prompt template {prompt_data.name}")
    
    if any_update_failed:
        # It's tricky to roll back in-memory changes perfectly if only some succeed.
        # For now, if any part fails, we don't save and rely on next GET to reload original.
        # A more robust solution might involve a temporary config object for updates.
        cm.clear_cached_config() # Clear potentially partially modified cache
        cm.get_config(force_reload=True) # Reload original state
        raise HTTPException(status_code=400, detail="One or more AI configuration updates failed. No changes were saved.")

    if not cm.save_config():
        cm.clear_cached_config()
        cm.get_config(force_reload=True)
        raise HTTPException(status_code=500, detail="Failed to save AI configuration updates to file.")
    
    cm.clear_cached_config() # Ensure next GET fetches the saved version
    # Instead of returning the whole config, return a success message.
    # The client can then re-fetch with GET /ai_config if needed.
    return ResponseMessage(message="AI configuration updated successfully and saved.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("settings_router.py loaded. Intended for import by main FastAPI app.")
    logger.info("Defined Pydantic models and placeholder endpoints for category and AI configuration management.")
