import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
            else:
                logger.warning(f"Config file {self.config_path} not found. Using default configuration.")
                self.config = self._get_default_config()
                self.save_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = self._get_default_config()

    def save_config(self) -> None:
        """Save current configuration to YAML file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise

    def get_config(self) -> Dict[str, Any]:
        """Get the entire configuration."""
        return self.config

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation."""
        try:
            value = self.config
            for key in key_path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_value(self, key_path: str, value: Any) -> None:
        """Update a specific configuration value using dot notation."""
        keys = key_path.split('.')
        current = self.config
        
        # Navigate to the nested dictionary
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Update the value
        current[keys[-1]] = value
        self.save_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "database": {
                "path": "data/moneymind.db",
                "backup_path": "data/backups"
            },
            "ai_services": {
                "default": "deepseek",
                "deepseek": {
                    "api_key": "",
                    "model": "deepseek-chat",
                    "temperature": 0.7
                },
                "openai": {
                    "api_key": "",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                },
                "anthropic": {
                    "api_key": "",
                    "model": "claude-3-sonnet",
                    "temperature": 0.7
                }
            },
            "app": {
                "name": "MoneyMind",
                "version": "1.0.0",
                "debug": False,
                "host": "127.0.0.1",
                "port": 8000,
                "log_level": "INFO",
                "log_file": "logs/app.log"
            },
            "security": {
                "jwt_secret": "",
                "jwt_algorithm": "HS256",
                "jwt_expire_minutes": 1440
            },
            "import": {
                "default_currency": "CNY",
                "supported_currencies": ["CNY", "USD", "EUR", "JPY"],
                "supported_channels": ["WeChat Pay", "Alipay", "Bank Card", "Cash"]
            }
        }

# Create a singleton instance
config_manager = ConfigManager()

# Export the singleton instance
__all__ = ['config_manager'] 