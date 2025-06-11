import logging
import requests
import re
import json
from . import config_manager as cm
from .prompts import generate_system_prompt

# Constants
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)

def get_llm_classification(description: str) -> dict | None:
    """
    Calls the configured active LLM API to get expense classification.
    It uses the global config via config_manager and expects a JSON response.
    """
    logger.info(f"Attempting LLM classification for: '{description}'")

    service_config = cm.get_active_ai_service_config()
    if not service_config:
        logger.error("No active AI service configured or configuration is incomplete. Aborting.")
        return None

    api_key = service_config.get('api_key')
    base_url = service_config.get('base_url')
    model = service_config.get('model')

    if not all([api_key, base_url, model]):
        logger.error(f"API key, base URL, or model is missing for the active service. Check config.")
        return None
    
    if "YOUR_" in api_key.upper() or "API_KEY" in api_key.upper():
        logger.error("API key appears to be a placeholder. Please update your configuration.")
        return None

    api_url = f"{base_url.rstrip('/')}/v1/chat/completions"

    # Dynamically generate system prompt from categories
    system_prompt = generate_system_prompt()
    user_prompt_template = cm.get_prompt_template('user_prompt_template')
    
    if not system_prompt or not user_prompt_template:
        logger.error("System prompt or user prompt template could not be generated/found.")
        return None
        
    user_prompt = user_prompt_template.format(description=description)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    logger.debug(f"Sending payload to {api_url}: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        response_json = response.json()
        
        content_str = response_json['choices'][0]['message']['content']
        
        # Robust JSON parsing from the response string
        try:
            # The ideal case: the whole string is a valid JSON object
            data = json.loads(content_str)
        except json.JSONDecodeError:
            # If not, try to find a JSON block wrapped in ```json ... ```
            json_match = re.search(r'```json\s*({.*?})\s*```', content_str, re.DOTALL)
            if json_match:
                content_str_extracted = json_match.group(1)
            else:
                # If no markdown block, find the first '{' and last '}'
                start = content_str.find('{')
                end = content_str.rfind('}')
                if start != -1 and end != -1 and end > start:
                    content_str_extracted = content_str[start:end+1]
                else:
                    logger.error(f"Failed to parse JSON and no clear JSON block found in response: {content_str}")
                    return None
            
            try:
                data = json.loads(content_str_extracted)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse extracted JSON block: {content_str_extracted}")
                return None
            
        logger.info(f"LLM classification successful: {data}")
        
        # Standardize the output keys
        return {
            "ai_suggestion_l1": data.get("category_l1"),
            "ai_suggestion_l2": data.get("category_l2")
        }

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_text = e.response.text
        logger.error(f"HTTP error from LLM API: {status_code} - {error_text}")
        # Pass detailed error info back for specific handling in the future
        return {"error": f"API_HTTP_ERROR_{status_code}", "detail": error_text}
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LLM API call: {e}")
        return {"error": "API_NETWORK_ERROR", "detail": str(e)}
    except (KeyError, IndexError, TypeError) as e:
        response_data = response.text if 'response' in locals() else "No response object"
        logger.error(f"Error parsing response from LLM API: {e}. Response: {response_data}")
        return {"error": "API_RESPONSE_PARSE_ERROR", "detail": str(e)}
    except Exception as e:
        logger.error(f"An unexpected error occurred during LLM API call: {e}", exc_info=True)
        return {"error": "UNEXPECTED_ERROR", "detail": str(e)}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s.%(funcName)s:%(lineno)d] - %(message)s')
    main_logger = logging.getLogger(__name__) # Logger for this __main__ block

    main_logger.info("--- Testing LLM Classification with Dynamic Default Service ---")
    
    # Load full application configuration
    # This uses the actual config.yaml or defaults if not found/parsable.
    app_config = cm.get_config() 
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
        description="Test coffee shop with dynamic service",
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
                description=expense["desc"],
            )
            main_logger.info(f"Classification for '{expense['desc']}': {result}")
            if result:
                 main_logger.info(f"  -> L1: {result.get('ai_suggestion_l1')}, L2: {result.get('ai_suggestion_l2')}")
            time.sleep(1) 

    main_logger.info("\n--- LLM Classification Test with Dynamic Service Complete ---")
    main_logger.info("Note: PyYAML and Requests libraries are required (pip install PyYAML requests).")
