# -*- coding: utf-8 -*-
"""
Configuration Loader
Load configuration from YAML file
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Configuration Loader"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Configuration file path, if None, use default path
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
                self.config = {}
        else:
            print(f"Warning: Config file not found: {self.config_path}")
            self.config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value (supports dot-separated nested keys)
        
        Args:
            key: Configuration key, supports "decision.max_decision_time" format
            default: Default value
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_decision_config(self) -> Dict[str, Any]:
        """Get decision configuration"""
        return self.config.get("decision", {})
    
    def get_evaluation_weights(self) -> Dict[str, float]:
        """Get evaluation weights configuration"""
        return self.config.get("evaluation", {}).get("weights", {})
    
    def get_cooperation_config(self) -> Dict[str, Any]:
        """Get cooperation strategy configuration"""
        return self.config.get("cooperation", {})
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket configuration"""
        return self.config.get("websocket", {})


# Global configuration instance
_global_config: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Get global configuration instance
    
    Args:
        config_path: Configuration file path
    
    Returns:
        Configuration loader instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader(config_path)
    return _global_config

