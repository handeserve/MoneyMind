import yaml
import logging
import os
import shutil
from copy import deepcopy
from typing import Dict, List, Optional, Any

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
CONFIG_BACKUP_PATH = CONFIG_FILE_PATH + ".bak"

_cached_config: Optional[Dict[str, Any]] = None
logger = logging.getLogger(__name__)

def _get_default_config_structure() -> dict:
    """Returns the default configuration structure."""
    return {
        "ai_services": {
            "active_service": "deepseek",
            "classification_concurrency": 5,
            "services": {
                "deepseek": {
                    "api_key": "",
                    "base_url": "https://api.deepseek.com",
                    "model": "deepseek-chat"
                }
            }
        },
        "prompts": {
            "user_prompt_template": "请将以下支出描述分类: {description}"
        },
        "preset_categories": {
            "餐饮美食": ["日常三餐", "外卖"],
            "交通出行": ["公共交通", "打车"]
        },
        "database": {
            "database_path": "data/moneymind.db",
            "backup_path": "data/backups",
            "auto_backup": True,
            "backup_interval": 24
        },
        "app": {
            "language": "zh-CN",
            "theme": "light",
            "currency": "CNY",
            "date_format": "YYYY-MM-DD"
        },
        "import": {
            "auto_classify": True,
            "skip_duplicates": True,
            "batch_size": 100,
            "default_channel": "alipay"
        }
    }

def load_config(config_path: str = CONFIG_FILE_PATH) -> dict:
    """Loads and merges configuration from a YAML file with defaults."""
    default_config = _get_default_config_structure()
    final_config = deepcopy(default_config)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            file_config = yaml.safe_load(f)
        if not file_config:
            logger.warning(f"Config file {config_path} is empty. Using all default configurations.")
            return final_config

        logger.info(f"Configuration successfully loaded from {config_path}.")
        # Deep merge file config into final config
        for key, value in file_config.items():
            if isinstance(value, dict) and isinstance(final_config.get(key), dict):
                final_config[key] = {**final_config.get(key, {}), **value}
            else:
                final_config[key] = value

    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}. Using default configurations.")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config file {config_path}: {e}. Using default configurations.")
            
    return final_config

def get_config(force_reload: bool = False) -> Dict[str, Any]:
    """Retrieves the configuration, loading it once and caching the result."""
    global _cached_config
    if _cached_config is None or force_reload:
        logger.info("Loading configuration from disk.")
        _cached_config = load_config()
    return _cached_config

def clear_cached_config():
    """Clears the cached configuration."""
    global _cached_config
    _cached_config = None
    logger.info("Cleared cached configuration.")

def save_config() -> bool:
    """Saves the current in-memory config to file."""
    if _cached_config is None:
        logger.warning("No configuration in memory to save.")
        return False
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            shutil.copy2(CONFIG_FILE_PATH, CONFIG_BACKUP_PATH)
        except Exception as e:
            logger.error(f"Failed to create backup of config file: {e}")
            return False
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(_cached_config, f, allow_unicode=True, sort_keys=False, indent=2)
        logger.info(f"Configuration successfully saved to {CONFIG_FILE_PATH}")
        clear_cached_config() # Invalidate cache so next get is from file
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration to {CONFIG_FILE_PATH}: {e}")
        return False

def _ensure_config_loaded_for_modification():
    """Internal helper to ensure config is loaded before modification."""
    if _cached_config is None:
        get_config()
    if _cached_config is None:
        raise RuntimeError("CRITICAL: Configuration could not be loaded for modification.")

# --- Getters ---

def get_active_ai_service_name() -> Optional[str]:
    return get_config().get("ai_services", {}).get("active_service")

def get_active_ai_service_config() -> Optional[Dict[str, Any]]:
    config = get_config()
    active_service_name = config.get("ai_services", {}).get("active_service")
    if not active_service_name:
        return None
    return config.get("ai_services", {}).get("services", {}).get(active_service_name)

def get_classification_concurrency() -> int:
    return get_config().get("ai_services", {}).get("classification_concurrency", 1)

def get_prompt_template(template_name: str) -> Optional[str]:
    return get_config().get("prompts", {}).get(template_name)

def get_preset_categories() -> Dict[str, List[str]]:
    return get_config().get("preset_categories", {})

# --- Updaters ---

def update_config_value(key_path: str, value: Any) -> bool:
    """
    Updates a value in the in-memory configuration using a dot-separated path.
    Example: update_config_value('ai_services.services.deepseek.api_key', 'new_key')
    """
    _ensure_config_loaded_for_modification()
    keys = key_path.split('.')
    config_ref = _cached_config
    for key in keys[:-1]:
        config_ref = config_ref.setdefault(key, {})
    config_ref[keys[-1]] = value
    logger.info(f"Updated in-memory config at path '{key_path}'.")
    return True

# --- Category Management (unchanged logic, just confirmed compatibility) ---

def add_l1_category_config(l1_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.setdefault("preset_categories", {})
    if l1_name in categories:
        logger.warning(f"L1 category '{l1_name}' already exists.")
        return False
    categories[l1_name] = []
    logger.info(f"Added L1 category '{l1_name}' to in-memory config.")
    return True

def update_l1_category_config(old_l1_name: str, new_l1_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.get("preset_categories", {})
    if old_l1_name not in categories: return False
    if new_l1_name in categories and old_l1_name != new_l1_name: return False
    categories[new_l1_name] = categories.pop(old_l1_name)
    logger.info(f"Updated L1 category '{old_l1_name}' to '{new_l1_name}'.")
    return True

def delete_l1_category_config(l1_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.get("preset_categories", {})
    if l1_name in categories:
        del categories[l1_name]
        logger.info(f"Deleted L1 category '{l1_name}'.")
        return True
    return False

def add_l2_category_config(l1_name: str, l2_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.setdefault("preset_categories", {})
    if l1_name not in categories: return False
    l2_list = categories.setdefault(l1_name, [])
    if l2_name in l2_list: return False
    l2_list.append(l2_name)
    logger.info(f"Added L2 category '{l2_name}' to '{l1_name}'.")
    return True

def update_l2_category_config(l1_name: str, old_l2_name: str, new_l2_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories: return False
    l2_list = categories.get(l1_name, [])
    if old_l2_name not in l2_list: return False
    if new_l2_name in l2_list and old_l2_name != new_l2_name: return False
    index = l2_list.index(old_l2_name)
    l2_list[index] = new_l2_name
    logger.info(f"Updated L2 in '{l1_name}': '{old_l2_name}' to '{new_l2_name}'.")
    return True

def delete_l2_category_config(l1_name: str, l2_name: str) -> bool:
    _ensure_config_loaded_for_modification()
    categories = _cached_config.get("preset_categories", {})
    if l1_name not in categories: return False
    l2_list = categories.get(l1_name, [])
    if l2_name in l2_list:
        l2_list.remove(l2_name)
        logger.info(f"Deleted L2 category '{l2_name}' from '{l1_name}'.")
        return True
    return False
