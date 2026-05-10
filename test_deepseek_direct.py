#!/usr/bin/env python3
"""直接测试 DeepSeek API 连接和可用模型"""

import sys
from pathlib import Path

def test_deepseek_api():
    """直接测试 DeepSeek API"""
    print("直接测试 DeepSeek API 连接\n")
    print("="*60)

    try:
        from openai import OpenAI

        print("1. 初始化 OpenAI 客户端...")
        client = OpenAI(
            api_key="sk-fea502e13b1247b188308dd404dcc8e1",
            base_url="https://api.deepseek.com/v1"
        )
        print("   ✅ 客户端初始化成功")

        print("\n2. 测试 API 连接...")
        try:
            models = client.models.list()
            print(f"   ✅ API 连接成功")
            print(f"   可用模型数量: {len(models.data)}")

            print("\n3. 可用的 Embedding 模型:")
            for model in models.data:
                if 'embedding' in model.id.lower() or 'embed' in model.id.lower():
                    print(f"   📦 {model.id}")

            print("\n4. 可用的 Chat 模型:")
            for model in models.data:
                if 'chat' in model.id.lower() or 'deepseek' in model.id.lower():
                    print(f"   📦 {model.id}")

            print("\n5. 测试简单的 Chat Completion...")
            chat_response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "user", "content": "你好，请简单介绍一下自己"}
                ],
                max_tokens=100
            )
            print(f"   ✅ Chat Completion 测试成功")
            print(f"   响应: {chat_response.choices[0].message.content[:100]}...")

            print("\n6. 测试 Embedding...")
            try:
                embedding_response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input="测试文本"
                )
                print(f"   ✅ Embedding 测试成功")
                print(f"   向量维度: {len(embedding_response.data[0].embedding)}")
            except Exception as e:
                print(f"   ❌ Embedding 测试失败: {e}")
                print("   建议: 检查 embedding 模型名称")

            print("\n" + "="*60)
            print("🎉 DeepSeek API 测试完成！")
            print("="*60)
            return True

        except Exception as e:
            print(f"   ❌ API 调用失败: {e}")
            error_str = str(e)

            if "401" in error_str or "Authentication" in error_str:
                print("\n   ⚠️  认证失败 - API Key 可能无效或已过期")
            elif "404" in error_str:
                print("\n   ⚠️  端点未找到 - 检查模型名称是否正确")
            elif "403" in error_str:
                print("\n   ⚠️  访问被拒绝 - 检查 API Key 权限")
            else:
                print(f"\n   ⚠️  未知错误: {type(e).__name__}")

            return False

    except ImportError:
        print("❌ 未安装 openai 库")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = test_deepseek_api()
    sys.exit(0 if success else 1)
