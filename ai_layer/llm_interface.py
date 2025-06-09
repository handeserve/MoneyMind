import logging
import requests
import re
import time
import json # For formatting the category structure string neatly if needed

# Import from local config_manager
# cm_get_api_key is not directly used here anymore, config dict is passed.
# get_config is used in the __main__ block for testing.
from .config_manager import get_config

# API URL - For now, this remains specific. Future enhancement could make this part of service_config.
# For this task, we assume the default service is DeepSeek-compatible.
LLM_API_URL_TEMPLATE = "{base_url}/v1/chat/completions" # Example, might need adjustment if base_url varies
DEEPSEEK_BASE_URL = "https://api.deepseek.com" # Default, could be part of service_config later

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 15

logger = logging.getLogger(__name__) # Use module-level logger

def get_llm_classification(
    description_for_ai: str,
    config: dict, # Full config dict from config_manager.get_config()
    amount: float | str | None = None,
    channel: str | None = None,
    source_provided_category: str | None = None
) -> dict | None:
    """
    Calls the configured default LLM API to get expense classification.
    Currently assumes a DeepSeek-compatible API structure.
    """
    logger.info(f"Attempting LLM classification for: '{description_for_ai}' using configured default service.")

    # 1. Retrieve Default Service and its Configuration
    default_service_name = config.get('default_llm_service')
    if not default_service_name:
        logger.error("Default LLM service is not defined in configuration. Aborting classification.")
        return None
    logger.info(f"Using default LLM service: {default_service_name}")

    service_config = config.get('llm_services', {}).get(default_service_name)
    if not service_config:
        logger.error(f"Configuration for LLM service '{default_service_name}' not found. Aborting classification.")
        return None
    
    api_key = service_config.get('api_key')
    model_cfg = service_config.get('model_params', {})
    
    llm_model_name = model_cfg.get('model_name')
    temperature = model_cfg.get('temperature', 0.7) # Default if not in config
    # max_tokens = model_cfg.get('max_tokens') # Optional

    # API URL construction (still assumes DeepSeek for now)
    # Future: base_url could come from service_config if supporting other APIs
    api_url = LLM_API_URL_TEMPLATE.format(base_url=DEEPSEEK_BASE_URL)


    # 2. Error Handling for Essential Config
    # Placeholder check (generic, config_manager's get_api_key has more specific default checks)
    if not api_key or "YOUR_" in api_key.upper() or "_API_KEY_HERE" in api_key.upper():
        logger.error(f"API key for service '{default_service_name}' is missing or appears to be a placeholder. Aborting classification.")
        return None # Or return dummy for testing as per example, but for real use, None is better.
        # return {"ai_suggestion_l1": "DummyL1 (No API Key)", "ai_suggestion_l2": "DummyL2"}


    if not llm_model_name:
        logger.error(f"Model name for service '{default_service_name}' is not configured. Aborting classification.")
        return None

    prompt_template = config.get('prompts', {}).get('classification_prompt_template')
    preset_categories = config.get('preset_categories', {})

    if not prompt_template:
        logger.error("Classification prompt template is missing in configuration. Cannot proceed.")
        return None
    if not preset_categories:
        logger.error("Preset categories are missing in configuration. Cannot proceed.")
        return None

    # 3. Prepare Prompt
    available_categories_l1_list = list(preset_categories.keys())
    available_categories_l1_list_str = ", ".join(available_categories_l1_list)

    full_category_structure_parts = []
    for l1, l2_list in preset_categories.items():
        full_category_structure_parts.append(f"{l1}: {', '.join(l2_list)}")
    full_category_structure_str = "; ".join(full_category_structure_parts)
    
    amount_str = str(amount) if amount is not None else "N/A"
    channel_str = str(channel) if channel is not None else "N/A"
    source_provided_category_str = str(source_provided_category) if source_provided_category is not None else "N/A"

    try:
        prompt = prompt_template.format(
            description_for_ai=description_for_ai,
            amount=amount_str,
            channel=channel_str,
            source_provided_category=source_provided_category_str,
            available_categories_l1_list_str=available_categories_l1_list_str, # Corrected placeholder name
            full_category_structure_str=full_category_structure_str           # Corrected placeholder name
        )
    except KeyError as e:
        logger.error(f"Error formatting prompt template. Missing key: {e}. Check prompt template and available variables.")
        return None
    
    logger.debug(f"Formatted prompt for LLM ({default_service_name} - {llm_model_name}):\n{prompt}")

    # 4. Make API Call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": llm_model_name,
        "messages": [
            {"role": "system", "content": "You are an expert expense classification assistant. Respond strictly in the requested format."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        # if max_tokens: payload["max_tokens"] = max_tokens # Add if using max_tokens
    }

    response_json = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            response_json = response.json()
            break 
        except requests.exceptions.Timeout:
            logger.warning(f"Request to {default_service_name} timed out on attempt {attempt + 1}/{MAX_RETRIES}.")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error with {default_service_name} on attempt {attempt + 1}/{MAX_RETRIES}.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from {default_service_name} on attempt {attempt + 1}/{MAX_RETRIES}: {e.response.status_code} - {e.response.text}")
            if e.response.status_code < 500: 
                return None 
        except Exception as e: 
            logger.error(f"An unexpected error occurred during API call to {default_service_name} attempt {attempt + 1}/{MAX_RETRIES}: {e}")
        
        if attempt < MAX_RETRIES - 1:
            sleep_time = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
            logger.info(f"Retrying {default_service_name} call in {sleep_time} seconds...")
            time.sleep(sleep_time)
        else:
            logger.error(f"Max retries reached. Failed to call {default_service_name} API.")
            return None

    if not response_json:
        logger.error(f"No JSON response received from {default_service_name} API after retries.")
        return None

    # 5. Parse Response
    try:
        content = response_json['choices'][0]['message']['content']
        logger.debug(f"LLM ({default_service_name}) raw response content: {content}")

        l1_match = re.search(r"L1 Category:\s*(.*)", content, re.IGNORECASE | re.DOTALL)
        l2_match = re.search(r"L2 Category:\s*(.*)", content, re.IGNORECASE | re.DOTALL)

        extracted_l1 = l1_match.group(1).strip() if l1_match else None
        extracted_l2 = l2_match.group(1).strip() if l2_match else None

        if not extracted_l1 or not extracted_l2:
            logger.warning(f"Could not parse L1/L2 categories from LLM response ({default_service_name}): '{content}'. L1: {extracted_l1}, L2: {extracted_l2}")
            return None
        
        if extracted_l1 not in preset_categories:
            logger.warning(f"LLM ({default_service_name}) suggested L1 category '{extracted_l1}' which is not in presets. Storing it anyway.")
        elif extracted_l2 not in preset_categories.get(extracted_l1, []):
            logger.warning(f"LLM ({default_service_name}) suggested L2 category '{extracted_l2}' for L1 '{extracted_l1}', which is not in presets for that L1. Storing it anyway.")

        logger.info(f"LLM ({default_service_name}) classification successful: L1='{extracted_l1}', L2='{extracted_l2}'")
        return {"ai_suggestion_l1": extracted_l1, "ai_suggestion_l2": extracted_l2}

    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parsing JSON response from {default_service_name} API: {e}. Response: {response_json}")
        return None
    except Exception as e: 
        logger.error(f"An unexpected error occurred during response parsing from {default_service_name}: {e}")
        return None


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s.%(funcName)s:%(lineno)d] - %(message)s')
    main_logger = logging.getLogger(__name__) # Logger for this __main__ block

    main_logger.info("--- Testing LLM Classification with Dynamic Default Service ---")
    
    # Load full application configuration
    # This uses the actual config.yaml or defaults if not found/parsable.
    app_config = get_config() 
    if not app_config:
        main_logger.error("Failed to load application configuration for testing. Aborting.")
        exit()

    default_service_to_test = app_config.get('default_llm_service')
    if not default_service_to_test:
        main_logger.error("No default_llm_service configured. Cannot run test.")
        exit()
    
    main_logger.info(f"Configured default LLM service for testing: '{default_service_to_test}'")

    # Check API key for the default service
    # This uses the updated get_api_key from config_manager which checks the llm_services structure
    # We need to import it from config_manager to use it here if it's not already.
    # For this test, we'll rely on the check within get_llm_classification itself.
    
    # The get_llm_classification function will now perform its own internal check
    # for placeholder API keys based on the dynamically selected service.
    
    main_logger.info("\nTesting pre-API call logic (placeholder key check is inside get_llm_classification):")
    test_result_placeholder_check = get_llm_classification(
        description_for_ai="Test coffee shop with dynamic service",
        config=app_config, # Pass the full config
        amount="5.00",
        channel="Credit Card"
    )
    # The outcome depends on whether the actual key for 'default_service_to_test' in config.yaml is a placeholder.
    # If it's a placeholder, get_llm_classification should return None and log an error.
    # If it's a real key, it will attempt an API call.
    main_logger.info(f"Result of dynamic service test: {test_result_placeholder_check}")
    if test_result_placeholder_check is None:
         main_logger.info("(If API key for the default service is a placeholder, this 'None' result is expected.)")
    else:
         main_logger.info("(If API key for the default service is valid, an actual API call was attempted.)")


    # To more thoroughly test, one might have a dedicated test_config.yaml
    # and switch CONFIG_FILE_PATH in config_manager temporarily, or mock get_config().
    # For now, this test relies on the actual config.yaml.
    
    # Example of a real call attempt (if key is valid)
    # This part is similar to before, but now it uses the default service from config
    main_logger.info(f"\nAttempting REAL API call if API key for '{default_service_to_test}' is valid...")
    
    sample_expenses_for_dynamic_test = [
        {"desc": "Dynamically routed Starbucks coffee", "amt": "6.50", "chan": "Credit Card", "src_cat": "Food"},
        {"desc": "Dynamically routed Uber to work", "amt": "15.20", "chan": "Alipay", "src_cat": "Travel"},
    ]

    # Check if API key is placeholder before attempting loop
    # This check is a bit more explicit for the __main__ block
    _llm_services = app_config.get('llm_services', {})
    _service_config_for_test = _llm_services.get(default_service_to_test, {})
    _api_key_for_test = _service_config_for_test.get('api_key')

    if not _api_key_for_test or "YOUR_" in _api_key_for_test.upper() or "_API_KEY_HERE" in _api_key_for_test.upper():
        main_logger.warning(f"API key for default service '{default_service_to_test}' is a placeholder. Skipping live API call loop.")
    else:
        for expense in sample_expenses_for_dynamic_test:
            main_logger.info(f"\nClassifying (dynamic service '{default_service_to_test}'): '{expense['desc']}'")
            result = get_llm_classification(
                description_for_ai=expense["desc"],
                config=app_config,
                amount=expense["amt"],
                channel=expense["chan"],
                source_provided_category=expense["src_cat"]
            )
            main_logger.info(f"Classification for '{expense['desc']}': {result}")
            if result:
                 main_logger.info(f"  -> L1: {result.get('ai_suggestion_l1')}, L2: {result.get('ai_suggestion_l2')}")
            time.sleep(1) 

    main_logger.info("\n--- LLM Classification Test with Dynamic Service Complete ---")
    main_logger.info("Note: PyYAML and Requests libraries are required (pip install PyYAML requests).")
