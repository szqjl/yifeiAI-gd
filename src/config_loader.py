# -*- coding: utf-8 -*-
"""
配置文件加载器
支持从YAML配置文件加载配置
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径，如果为None，则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """加载配置文件"""
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
        获取配置值（支持点号分隔的嵌套键）
        
        Args:
            key: 配置键，支持 "decision.max_decision_time" 格式
            default: 默认值
        
        Returns:
            配置值
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
        """获取决策配置"""
        return self.config.get("decision", {})
    
    def get_evaluation_weights(self) -> Dict[str, float]:
        """获取评估权重配置"""
        return self.config.get("evaluation", {}).get("weights", {})
    
    def get_cooperation_config(self) -> Dict[str, Any]:
        """获取配合策略配置"""
        return self.config.get("cooperation", {})
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """获取WebSocket配置"""
        return self.config.get("websocket", {})


# 全局配置实例
_global_config: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    获取全局配置实例
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置加载器实例
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader(config_path)
    return _global_config

