"""
配置管理模块

统一管理配置文件加载和 API Key 管理
支持主配置和 Key 配置的分离
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    配置管理器
    
    管理主配置 (ov.conf) 和 Key 配置 (keys.conf)
    支持环境变量注入和配置合并
    """
    
    def __init__(self, 
                 config_path: str = "config/ov.conf",
                 keys_path: str = "config/keys.conf"):
        """
        初始化配置管理器
        
        Args:
            config_path: 主配置文件路径
            keys_path: Key 配置文件路径
        """
        self.config_path = Path(config_path)
        self.keys_path = Path(keys_path)
        
        self._config: Dict[str, Any] = {}
        self._keys: Dict[str, Any] = {}
        self._merged: Dict[str, Any] = {}
        
        self._load_all()
    
    def _load_all(self):
        """加载所有配置"""
        self._config = self._load_config_file(self.config_path)
        self._keys = self._load_config_file(self.keys_path)
        self._merged = self._merge_configs()
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 配置字典
        """
        if not file_path.exists():
            print(f"配置文件不存在: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 替换环境变量
            content = self._replace_env_vars(content)
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误 {file_path}: {e}")
            return {}
        except Exception as e:
            print(f"加载配置文件失败 {file_path}: {e}")
            return {}
    
    def _replace_env_vars(self, content: str) -> str:
        """
        替换环境变量占位符
        
        Args:
            content: 原始内容
            
        Returns:
            str: 替换后的内容
        """
        import re
        
        # 匹配 ${VAR_NAME} 格式
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, content)
    
    def _merge_configs(self) -> Dict[str, Any]:
        """
        合并主配置和 Key 配置
        
        Returns:
            Dict: 合并后的配置
        """
        merged = self._config.copy()
        
        # 获取当前使用的 provider
        vlm_provider = merged.get("vlm", {}).get("provider", "volcengine")
        embedding_provider = merged.get("embedding", {}).get("dense", {}).get("provider", "volcengine")
        
        # 从 keys 中获取对应 provider 的配置
        if vlm_provider in self._keys:
            key_config = self._keys[vlm_provider]
            if "vlm" not in merged:
                merged["vlm"] = {}
            merged["vlm"]["api_key"] = key_config.get("api_key", "")
            merged["vlm"]["api_base"] = key_config.get("api_base", "")
        
        if embedding_provider in self._keys:
            key_config = self._keys[embedding_provider]
            if "embedding" not in merged:
                merged["embedding"] = {"dense": {}}
            if "dense" not in merged["embedding"]:
                merged["embedding"]["dense"] = {}
            merged["embedding"]["dense"]["api_key"] = key_config.get("api_key", "")
            merged["embedding"]["dense"]["api_base"] = key_config.get("api_base", "")
        
        return merged
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔，如 "vlm.api_key"）
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self._merged
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_vlm_config(self) -> Dict[str, Any]:
        """
        获取 VLM 配置
        
        Returns:
            Dict: VLM 配置
        """
        return self._merged.get("vlm", {})
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """
        获取 Embedding 配置
        
        Returns:
            Dict: Embedding 配置
        """
        return self._merged.get("embedding", {}).get("dense", {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """
        获取存储配置
        
        Returns:
            Dict: 存储配置
        """
        return self._merged.get("storage", {})
    
    def get_all_keys(self) -> Dict[str, Any]:
        """
        获取所有 Key 配置（不包含敏感信息）
        
        Returns:
            Dict: Key 配置列表（API Key 已脱敏）
        """
        keys_copy = {}
        for provider, config in self._keys.items():
            if provider.startswith("_"):
                continue
            keys_copy[provider] = {
                "api_base": config.get("api_base", ""),
                "has_api_key": bool(config.get("api_key", ""))
            }
        return keys_copy
    
    def set_key(self, provider: str, api_key: str, api_base: str = None):
        """
        设置 API Key
        
        Args:
            provider: 提供商名称
            api_key: API Key
            api_base: API Base URL（可选）
        """
        if provider not in self._keys:
            self._keys[provider] = {}
        
        self._keys[provider]["api_key"] = api_key
        
        if api_base:
            self._keys[provider]["api_base"] = api_base
        
        # 重新合并配置
        self._merged = self._merge_configs()
        
        # 保存到文件
        self._save_keys()
    
    def _save_keys(self):
        """保存 Key 配置到文件"""
        try:
            # 创建备份
            if self.keys_path.exists():
                backup_path = self.keys_path.with_suffix(".conf.backup")
                with open(self.keys_path, "r", encoding="utf-8") as f:
                    with open(backup_path, "w", encoding="utf-8") as bf:
                        bf.write(f.read())
            
            with open(self.keys_path, "w", encoding="utf-8") as f:
                json.dump(self._keys, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存 Key 配置失败: {e}")
    
    def reload(self):
        """重新加载配置"""
        self._load_all()
    
    def validate(self) -> Dict[str, Any]:
        """
        验证配置完整性
        
        Returns:
            Dict: 验证结果
        """
        errors = []
        warnings = []
        
        # 检查主配置
        if not self._config:
            errors.append("主配置文件加载失败")
        
        # 检查 Key 配置
        if not self._keys:
            warnings.append("Key 配置文件不存在或为空")
        
        # 检查 VLM 配置
        vlm_config = self.get_vlm_config()
        if not vlm_config.get("api_key"):
            errors.append("VLM API Key 未设置")
        if not vlm_config.get("provider"):
            errors.append("VLM Provider 未设置")
        
        # 检查 Embedding 配置
        embedding_config = self.get_embedding_config()
        if not embedding_config.get("api_key"):
            warnings.append("Embedding API Key 未设置")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要（不包含敏感信息）
        
        Returns:
            Dict: 配置摘要
        """
        vlm = self.get_vlm_config()
        embedding = self.get_embedding_config()
        storage = self.get_storage_config()
        
        return {
            "vlm_provider": vlm.get("provider", "未设置"),
            "vlm_model": vlm.get("model", "未设置"),
            "vlm_has_key": bool(vlm.get("api_key")),
            "embedding_provider": embedding.get("provider", "未设置"),
            "embedding_model": embedding.get("model", "未设置"),
            "embedding_has_key": bool(embedding.get("api_key")),
            "workspace": storage.get("workspace", "./openviking_workspace"),
            "available_providers": list(self.get_all_keys().keys())
        }


def create_config_manager(config_path: str = None, keys_path: str = None) -> ConfigManager:
    """
    创建配置管理器的便捷函数
    
    Args:
        config_path: 主配置文件路径
        keys_path: Key 配置文件路径
        
    Returns:
        ConfigManager: 配置管理器实例
    """
    # 支持环境变量指定配置路径
    if config_path is None:
        config_path = os.environ.get("OPENVIKING_CONFIG", "config/ov.conf")
    
    if keys_path is None:
        keys_path = os.environ.get("OPENVIKING_KEYS", "config/keys.conf")
    
    return ConfigManager(config_path, keys_path)
