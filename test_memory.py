#!/usr/bin/env python3
"""测试对话记忆功能"""

import sys
sys.path.insert(0, 'src')
from rpg_generator import RPGGenerator

print("=== 测试对话自动记录功能 ===\n")

# 初始化生成器
gen = RPGGenerator()

print("1. 第一次对话...")
resp1 = gen.chat("你好，请介绍一下你能做什么")
print(f"用户: 你好，请介绍一下你能做什么")
print(f"AI: {resp1[:80]}...\n")

print("2. 第二次对话...")
resp2 = gen.chat("/list_files .")
print(f"用户: /list_files .")
print(f"AI: {resp2[:80]}...\n")

print("3. 第三次对话...")
resp3 = gen.chat("生成一个魔法道具")
print(f"用户: 生成一个魔法道具")
print(f"AI: {resp3[:80]}...\n")

print("=== 查看对话记录摘要 ===")
print(gen.get_conversation_summary())

print("\n=== 验证记忆文件是否保存 ===")
import os
memory_dir = "d:/Game-Agent/openviking_workspace/viking/default/user/default/memories/conversations"
if os.path.exists(memory_dir):
    files = os.listdir(memory_dir)
    print(f"记忆目录: {memory_dir}")
    print(f"文件数量: {len(files)}")
    for f in files:
        print(f"  - {f}")
else:
    print(f"目录不存在: {memory_dir}")

print("\n=== 测试完成 ===")
