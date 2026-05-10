#!/usr/bin/env python3
"""
DeepSeek 配置测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config_manager import create_config_manager


def test_deepseek_config():
    """测试 DeepSeek 配置"""
    print("=" * 60)
    print("测试 DeepSeek 配置")
    print("=" * 60)
    
    # 创建配置管理器
    config = create_config_manager()
    
    # 获取配置摘要
    print("\n配置摘要:")
    summary = config.get_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 获取 VLM 配置
    print("\nVLM 配置:")
    vlm = config.get_vlm_config()
    print(f"  Provider: {vlm.get('provider')}")
    print(f"  Model: {vlm.get('model')}")
    print(f"  API Key: {'*' * 10 if vlm.get('api_key') else '未设置'}")
    print(f"  API Base: {vlm.get('api_base')}")
    
    # 获取 Embedding 配置
    print("\nEmbedding 配置:")
    embedding = config.get_embedding_config()
    print(f"  Provider: {embedding.get('provider')}")
    print(f"  Model: {embedding.get('model')}")
    print(f"  API Key: {'*' * 10 if embedding.get('api_key') else '未设置'}")
    print(f"  API Base: {embedding.get('api_base')}")
    
    # 验证配置
    print("\n配置验证:")
    validation = config.validate()
    print(f"  有效: {validation['valid']}")
    if validation['errors']:
        print(f"  错误: {validation['errors']}")
    if validation['warnings']:
        print(f"  警告: {validation['warnings']}")
    
    print("\n✅ DeepSeek 配置测试完成!")


if __name__ == "__main__":
    test_deepseek_config()
