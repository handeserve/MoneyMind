import yaml # Requires PyYAML
import logging
import os
import shutil # For file backup
from copy import deepcopy # For merging configurations
from typing import Dict, List, Optional, Any # For type hinting

# Expects config.yaml in project root (personal_expense_analyzer/config.yaml)
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
CONFIG_BACKUP_PATH = CONFIG_FILE_PATH + ".bak"

_cached_config: Optional[Dict[str, Any]] = None

logger = logging.getLogger(__name__) # Use module-level logger

def _get_default_config_structure() -> dict:
    """Returns a comprehensive default configuration structure with the new llm_services grouping."""
    return {
        "default_llm_service": "deepseek",
        "llm_services": {
            "deepseek": {
                "api_key": "YOUR_DEEPSEEK_API_KEY_HERE_IN_DEFAULT_CONFIG",
                "model_params": {"model_name": "deepseek-chat", "temperature": 0.7, "max_tokens": 150}
            },
            "another_service": {
                "api_key": "ANOTHER_KEY_HERE_IN_DEFAULT_CONFIG",
                "model_params": {"model_name": "other-model", "temperature": 0.5, "max_tokens": 100}
            }
        },
        "prompts": {
            "classification_prompt_template": (
                "请分析以下支出描述，并将其归类到一个主要类别和一个次要类别。\n"
                "支出描述: \"{description_for_ai}\"\n"
                "金额: {amount} (可选)\n"
                "渠道: {channel} (可选)\n"
                "原始分类: {source_provided_category} (可选)\n\n"
                "请从此列表中选择一个主要类别: {available_categories_l1_list_str}\n\n"
                "然后，根据您选择的主要类别，从相关选项中选择一个次要类别。\n"
                "可用的主要和次要类别结构如下:\n{full_category_structure_str}\n\n"
                "请严格按照以下格式回复:\n"
                "L1 Category: <选择的主要类别名称>\n"
                "L2 Category: <选择的次要类别名称>"
            ),
            "another_prompt": "This is another default prompt template."
        },
        "preset_categories": {
            "Food & Drinks": ["Groceries", "Restaurants & Dining", "Coffee Shops", "Food Delivery", "Snacks & Beverages"],
            "Transportation": ["Public Transport (Bus/Metro)", "Taxi & Ride-sharing", "Fuel / Gas", "Vehicle Maintenance & Repairs", "Parking Fees", "Travel (Flights, Trains)"],
            "Housing & Utilities": ["Rent / Mortgage", "Electricity Bill", "Water Bill", "Gas Bill", "Internet & Phone Bill", "Home Maintenance & Repairs"],
            "Shopping & Services": ["Clothing & Accessories", "Electronics & Gadgets", "Home Goods & Furniture", "Personal Care & Cosmetics", "Gifts", "Subscription Services (Netflix, Spotify etc.)", "Professional Services (Legal, Consulting)"],
            "Health & Wellness": ["Doctor Visits & Medical Fees", "Pharmacy & Medication", "Health Insurance", "Gym & Fitness"],
            "Entertainment & Leisure": ["Movies, Concerts & Events", "Books, Music & Games", "Hobbies & Activities", "Vacations & Travel (non-transport)"],
            "Education": ["Tuition Fees", "Courses & Workshops", "Books & Supplies"],
            "Family & Dependents": ["Childcare", "Pet Care", "Allowances"],
            "Financial": ["Bank Fees", "Taxes", "Insurance (Non-Health)", "Investments"],
            "Miscellaneous": ["Charity & Donations", "General & Uncategorized", "Stationery & Office Supplies"]
        }
    }

def load_config(config_path: str = CONFIG_FILE_PATH) -> dict:
    """
    Loads configuration from a YAML file.

    It merges the loaded configuration with a default structure. If the config file
    is not found, is empty, or if specific top-level sections are missing from the
    file, the values from the default structure are used for those sections.
    If a top-level key (e.g., 'llm_services', 'preset_categories') exists in the 
    config file, its value will completely replace the default value for that key,
    even if the file's section is only partial (e.g., defines only one LLM service).
    A more granular, deep merge for nested dictionaries is not currently implemented.

    Logs the source (file or default) for each primary configuration section.
    """
    default_config = _get_default_config_structure()
    # Start with a deep copy of defaults, so if file is missing/empty, defaults are used.
    # If file exists, its content will override these defaults on a per-key basis.
    final_config = deepcopy(default_config)

    try:
        with open(config_path, 'r', encoding='utf-8') as f: 
            file_config = yaml.safe_load(f)
        
        if file_config is None: 
            logger.warning(f"Config file {config_path} is empty or invalid YAML. Using all default configurations.")
            file_config = {} 
        else:
            logger.info(f"Configuration successfully loaded from {config_path}.")

        # Merge file_config into final_config.
        for key, value in file_config.items():
            if value is not None: 
                final_config[key] = value
                logger.info(f"Loaded section '{key}' from config file: {config_path}")
            else: 
                 logger.info(f"Section '{key}' is null in config file {config_path}, default or existing value will be used if applicable (or it will be null).")

        # Log which sections ended up using defaults vs. file values
        for key in default_config.keys():
            if key not in file_config or file_config.get(key) is None: # Check if key was in file_config at all or if it was null
                logger.info(f"Using default for section '{key}' as it was missing or null in config file: {config_path}")
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found at: {config_path}. Using all default configurations.")
        # final_config is already a deepcopy of default_config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {config_path}: {e}. Using all default configurations.")
            
    return final_config

def get_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Retrieves the configuration, loading it once and caching the result.
    Can force a reload from disk.
    """
    global _cached_config
    if _cached_config is None or force_reload:
        if force_reload:
            logger.info("Forcing reload of configuration from disk.")
        _cached_config = load_config()
    return _cached_config

def clear_cached_config():
    """Clears the cached configuration, forcing a reload on next get_config() call."""
    global _cached_config
    _cached_config = None
    logger.info("Cleared cached configuration.")

def save_config() -> bool:
    """Saves the current in-memory _cached_config to CONFIG_FILE_PATH."""
    global _cached_config
    if _cached_config is None:
        logger.warning("No configuration loaded in memory to save.")
        return False

    # Backup existing config file
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            shutil.copy2(CONFIG_FILE_PATH, CONFIG_BACKUP_PATH)
            logger.info(f"Backed up existing config to {CONFIG_BACKUP_PATH}")
        except Exception as e:
            logger.error(f"Failed to create backup of config file: {e}")
            return False # Optionally proceed without backup, or fail here

    # Write current _cached_config to file
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(_cached_config, f, allow_unicode=True, sort_keys=False, indent=2)
        logger.info(f"Configuration successfully saved to {CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration to {CONFIG_FILE_PATH}: {e}")
        return False

# --- Helper Functions (Updated for new structure) ---

def get_default_llm_service() -> Optional[str]:
    config = get_config()
    return config.get("default_llm_service")

def get_api_key(service_name: Optional[str] = None) -> Optional[str]:
    config = get_config()
    if service_name is None:
        service_name = get_default_llm_service()
        if not service_name:
            logger.warning("Cannot determine API key: No service name provided and default_llm_service is not set.")
            return None
    
    key = config.get("llm_services", {}).get(service_name, {}).get("api_key")
    if not key:
        logger.warning(f"API key for service '{service_name}' not found in configuration.")
        return None
    # Check for default placeholder values
    if "YOUR_DEEPSEEK_API_KEY_HERE" in key or "ANOTHER_KEY_HERE" in key:
        logger.warning(f"API key for service '{service_name}' appears to be a placeholder. Please update config.yaml.")
    return key

def get_model_params(service_name: Optional[str] = None) -> Dict[str, Any]:
    config = get_config()
    if service_name is None:
        service_name = get_default_llm_service()
        if not service_name:
            logger.warning("Cannot determine model params: No service name provided and default_llm_service is not set.")
            return {}
            
    params = config.get("llm_services", {}).get(service_name, {}).get("model_params", {})
    if not params:
        logger.warning(f"Model parameters for service '{service_name}' not found in configuration.")
        return {}
    return params

def get_prompt_template(template_name: str = 'classification_prompt_template') -> Optional[str]:
    config = get_config()
    return config.get("prompts", {}).get(template_name)

def get_preset_categories() -> Dict[str, List[str]]:
    config = get_config()
    return config.get("preset_categories", {})

def get_l1_categories() -> List[str]:
    return list(get_preset_categories().keys())

def get_l2_categories(l1_category_name: str) -> List[str]:
    return get_preset_categories().get(l1_category_name, [])

# --- In-Memory Modification Functions ---

def _ensure_config_loaded_for_modification() -> bool:
    """Ensures _cached_config is loaded, returns False if not."""
    if _cached_config is None:
        get_config() # Load it
    if _cached_config is None: # Still None after trying to load
        logger.error("CRITICAL: Configuration could not be loaded for modification.")
        return False
    return True

def add_l1_category_config(l1_name: str) -> bool:
    """Adds a new L1 category to the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    # Ensure _cached_config is not None before proceeding
    assert _cached_config is not None 
    categories = _cached_config.setdefault("preset_categories", {})
    if l1_name in categories:
        logger.warning(f"L1 category '{l1_name}' already exists.")
        return False
    categories[l1_name] = []
    logger.info(f"Added L1 category '{l1_name}' to in-memory config.")
    return True

def update_l1_category_config(old_l1_name: str, new_l1_name: str) -> bool:
    """Updates an existing L1 category's name in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    categories = _cached_config.get("preset_categories", {})
    if old_l1_name not in categories:
        logger.warning(f"L1 category '{old_l1_name}' not found for update.")
        return False
    if new_l1_name in categories and old_l1_name != new_l1_name: # Check if new name conflicts
        logger.warning(f"New L1 category name '{new_l1_name}' already exists.")
        return False
    # Preserve L2 categories by popping and reassigning
    l2_list = categories.pop(old_l1_name)
    categories[new_l1_name] = l2_list
    logger.info(f"Updated L1 category '{old_l1_name}' to '{new_l1_name}' in in-memory config.")
    return True

def delete_l1_category_config(l1_name: str) -> bool:
    """Deletes an L1 category and its L2 subcategories from the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories:
        logger.warning(f"L1 category '{l1_name}' not found for deletion.")
        return False
    del categories[l1_name]
    logger.info(f"Deleted L1 category '{l1_name}' from in-memory config.")
    return True

def add_l2_category_config(l1_name: str, l2_name: str) -> bool:
    """Adds a new L2 category under an L1 category in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories:
        logger.warning(f"L1 category '{l1_name}' not found when adding L2 '{l2_name}'.")
        return False
    if l2_name in categories[l1_name]: # Check if L2 already exists in this L1
        logger.warning(f"L2 category '{l2_name}' already exists under L1 '{l1_name}'.")
        return False
    categories[l1_name].append(l2_name)
    logger.info(f"Added L2 category '{l2_name}' to L1 '{l1_name}' in in-memory config.")
    return True

def update_l2_category_config(l1_name: str, old_l2_name: str, new_l2_name: str) -> bool:
    """Updates an L2 category's name under an L1 category in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories:
        logger.warning(f"L1 category '{l1_name}' not found for L2 update.")
        return False
    if old_l2_name not in categories[l1_name]:
        logger.warning(f"Old L2 category '{old_l2_name}' not found under L1 '{l1_name}'.")
        return False
    if new_l2_name in categories[l1_name] and old_l2_name != new_l2_name: # Check for conflict within same L1
        logger.warning(f"New L2 category name '{new_l2_name}' already exists under L1 '{l1_name}'.")
        return False
    try:
        index = categories[l1_name].index(old_l2_name)
        categories[l1_name][index] = new_l2_name
        logger.info(f"Updated L2 category '{old_l2_name}' to '{new_l2_name}' under L1 '{l1_name}' in in-memory config.")
        return True
    except ValueError: # Should be caught by 'not in' check, but as safeguard
        logger.warning(f"L2 category '{old_l2_name}' not found (index error) under L1 '{l1_name}'.")
        return False


def delete_l2_category_config(l1_name: str, l2_name: str) -> bool:
    """Deletes an L2 category from an L1 category in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories:
        logger.warning(f"L1 category '{l1_name}' not found for L2 deletion.")
        return False
    if l2_name not in categories[l1_name]: # Check if L2 exists before trying to remove
        logger.warning(f"L2 category '{l2_name}' not found under L1 '{l1_name}' for deletion.")
        return False
    categories[l1_name].remove(l2_name)
    logger.info(f"Deleted L2 category '{l2_name}' from L1 '{l1_name}' in in-memory config.")
    return True

def update_default_llm_service_config(service_name: str) -> bool:
    """Updates the default LLM service name in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    # Validate if service_name exists in llm_services to prevent setting an invalid default
    if service_name not in _cached_config.get("llm_services", {}):
        logger.warning(f"Cannot set default LLM service to '{service_name}': service not configured in 'llm_services'.")
        return False
    _cached_config["default_llm_service"] = service_name
    logger.info(f"Updated default LLM service to '{service_name}' in in-memory config.")
    return True

def update_llm_service_api_key_config(service_name: str, new_api_key: str) -> bool:
    """Updates the API key for a given LLM service in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    services = _cached_config.setdefault("llm_services", {})
    service_config = services.setdefault(service_name, {}) # Ensure service_name entry exists
    service_config["api_key"] = new_api_key
    service_config.setdefault("model_params", {}) # Ensure model_params sub-dictionary exists
    logger.info(f"Updated API key for service '{service_name}' in in-memory config.")
    return True

def update_llm_service_model_params_config(service_name: str, model_params_update: dict) -> bool:
    """Updates model parameters for a given LLM service in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    services = _cached_config.setdefault("llm_services", {})
    service_config = services.setdefault(service_name, {}) # Ensure service_name entry exists
    current_params = service_config.setdefault("model_params", {}) # Ensure model_params sub-dict exists
    current_params.update(model_params_update) # Merge: updates existing, adds new from model_params_update
    logger.info(f"Updated model parameters for service '{service_name}' in in-memory config with: {model_params_update}")
    return True

def update_prompt_template_config(template_name: str, new_content: str) -> bool:
    """Updates a specific prompt template in the in-memory configuration."""
    if not _ensure_config_loaded_for_modification(): return False
    assert _cached_config is not None
    prompts = _cached_config.setdefault("prompts", {}) # Ensure prompts section exists
    prompts[template_name] = new_content
    logger.info(f"Updated prompt template '{template_name}' in in-memory config.")
    return True


if __name__ == '__main__':
    # Setup logging for detailed test output
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')

    # Use a temporary config file path for this test run to avoid altering the actual config.yaml
    original_real_config_file_path = CONFIG_FILE_PATH
    test_dir = os.path.join(os.path.dirname(original_real_config_file_path), "test_config_temp")
    os.makedirs(test_dir, exist_ok=True)
    
    TEST_CONFIG_FILE = os.path.join(test_dir, "temp_test_config.yaml")
    TEST_CONFIG_BACKUP_FILE = TEST_CONFIG_FILE + ".bak"

    # Set global CONFIG_FILE_PATH to the temporary test file for this test run
    globals()['CONFIG_FILE_PATH'] = TEST_CONFIG_FILE
    globals()['CONFIG_BACKUP_PATH'] = TEST_CONFIG_BACKUP_FILE # Update backup path too

    logger.info(f"--- Test Run: Using temporary config file: {TEST_CONFIG_FILE} ---")

    # Ensure clean state for test config file
    if os.path.exists(TEST_CONFIG_FILE): os.remove(TEST_CONFIG_FILE)
    if os.path.exists(TEST_CONFIG_BACKUP_FILE): os.remove(TEST_CONFIG_BACKUP_FILE)
    
    # Test 1: Load default config when file doesn't exist, then save it
    logger.info("\n[Test 1: Load default and save]")
    clear_cached_config() # Ensure it loads from (non-existent) file
    cfg = get_config()
    assert cfg["default_llm_service"] == "deepseek", "Default service not loaded correctly."
    save_success = save_config()
    assert save_success, "Failed to save initial default config."
    assert os.path.exists(TEST_CONFIG_FILE), "Config file was not created on save."
    
    # Test 2: Load from the saved file and verify structure
    logger.info("\n[Test 2: Reload saved config and verify structure]")
    clear_cached_config()
    cfg_reloaded = get_config()
    assert cfg_reloaded["default_llm_service"] == "deepseek", "Reloaded default service mismatch."
    assert "deepseek" in cfg_reloaded.get("llm_services", {}), "LLM services structure error."
    assert "api_key" in cfg_reloaded.get("llm_services", {}).get("deepseek", {}), "api_key missing in reloaded."
    assert "model_params" in cfg_reloaded.get("llm_services", {}).get("deepseek", {}), "model_params missing."
    assert "model_name" in cfg_reloaded.get("llm_services", {}).get("deepseek", {}).get("model_params",{}), "model_name missing."

    # Test 3: Category Modifications
    logger.info("\n[Test 3: Category Modifications]")
    clear_cached_config() # Start fresh for modification tests on loaded config
    get_config() # Load into _cached_config

    assert add_l1_category_config("NewL1"), "Failed to add NewL1"
    assert "NewL1" in get_preset_categories(), "NewL1 not found after add."
    assert add_l2_category_config("NewL1", "NewL2_under_NewL1"), "Failed to add NewL2"
    assert "NewL2_under_NewL1" in get_l2_categories("NewL1"), "NewL2 not found after add."
    assert update_l1_category_config("NewL1", "UpdatedNewL1"), "Failed to update NewL1"
    assert "UpdatedNewL1" in get_preset_categories(), "UpdatedNewL1 not found."
    assert "NewL1" not in get_preset_categories(), "Old NewL1 still exists."
    assert "NewL2_under_NewL1" in get_l2_categories("UpdatedNewL1"), "L2 list not carried over."
    assert update_l2_category_config("UpdatedNewL1", "NewL2_under_NewL1", "UpdatedNewL2"), "Failed to update NewL2"
    assert "UpdatedNewL2" in get_l2_categories("UpdatedNewL1"), "UpdatedNewL2 not found."
    assert delete_l2_category_config("UpdatedNewL1", "UpdatedNewL2"), "Failed to delete NewL2"
    assert "UpdatedNewL2" not in get_l2_categories("UpdatedNewL1"), "UpdatedNewL2 still exists."
    assert delete_l1_category_config("UpdatedNewL1"), "Failed to delete UpdatedNewL1"
    assert "UpdatedNewL1" not in get_preset_categories(), "UpdatedNewL1 still exists."

    # Test 4: AI Configuration Modifications
    logger.info("\n[Test 4: AI Configuration Modifications]")
    assert update_default_llm_service_config("another_service"), "Failed to update default LLM service."
    assert get_default_llm_service() == "another_service", "Default LLM service not updated."
    assert update_llm_service_api_key_config("deepseek", "NEW_KEY_FOR_DEEPSEEK"), "Failed to update API key."
    assert get_api_key("deepseek") == "NEW_KEY_FOR_DEEPSEEK", "API key not updated."
    new_params = {"temperature": 0.99, "model_name": "deepseek-chat-updated"}
    assert update_llm_service_model_params_config("deepseek", new_params), "Failed to update model params."
    current_deepseek_params = get_model_params("deepseek")
    assert current_deepseek_params["temperature"] == 0.99, "Model param temperature not updated."
    assert current_deepseek_params["model_name"] == "deepseek-chat-updated", "Model param model_name not updated."
    # Test adding a new service via model_params update
    assert update_llm_service_model_params_config("new_test_service", {"model_name": "test_model"}), "Failed to add new service via model_params."
    assert "new_test_service" in get_config().get("llm_services",{}), "New service not created in llm_services."
    assert get_model_params("new_test_service").get("model_name") == "test_model", "New service model_name incorrect."

    assert update_prompt_template_config("classification_prompt_template", "New Prompt Content"), "Failed to update prompt."
    assert get_prompt_template("classification_prompt_template") == "New Prompt Content", "Prompt not updated."

    # Test 5: Save all modifications and verify backup
    logger.info("\n[Test 5: Save all modifications and verify backup]")
    assert save_config(), "Failed to save modified config."
    assert os.path.exists(TEST_CONFIG_BACKUP_FILE), "Backup file was not created."

    # Test 6: Reload and verify one change from each section
    logger.info("\n[Test 6: Reload and verify changes from file]")
    clear_cached_config()
    cfg_final_check = get_config()
    assert "Food & Drinks" in cfg_final_check.get("preset_categories", {}), "Original categories lost after mods." # Assuming original test didn't delete this
    assert cfg_final_check.get("default_llm_service") == "another_service", "Default LLM service change not persisted."
    assert cfg_final_check.get("llm_services",{}).get("deepseek",{}).get("api_key") == "NEW_KEY_FOR_DEEPSEEK", "API key change not persisted."
    assert cfg_final_check.get("llm_services",{}).get("deepseek",{}).get("model_params",{}).get("temperature") == 0.99, "Model param change not persisted."
    assert cfg_final_check.get("prompts",{}).get("classification_prompt_template") == "New Prompt Content", "Prompt change not persisted."

    logger.info("\nAll config_manager tests passed successfully.")

    # Clean up test directory and files
    try:
        shutil.rmtree(test_dir)
        logger.info(f"Cleaned up temporary test directory: {test_dir}")
    except Exception as e:
        logger.error(f"Error cleaning up test directory {test_dir}: {e}")

    # Restore original CONFIG_FILE_PATH for any subsequent tool calls in a session (though not typical)
    globals()['CONFIG_FILE_PATH'] = original_real_config_file_path
    globals()['CONFIG_BACKUP_PATH'] = original_real_config_file_path + ".bak"
    clear_cached_config() # Ensure no test config is cached for other potential operations

    logger.info("--- Test Run Complete ---")
