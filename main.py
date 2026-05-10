#!/usr/bin/env python3
"""
OpenViking Agent 入口程序

基于火山引擎 OpenViking 的智能体应用
"""

import sys
import argparse
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent


def print_banner():
    """打印欢迎信息"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   OpenViking Agent                           ║
║          基于火山引擎 OpenViking 的智能体框架                 ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def interactive_mode(agent: Agent):
    """交互式对话模式"""
    print_banner()
    print("智能体已启动！输入 /help 查看可用命令，输入 exit 退出。\n")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("你 > ").strip()
            
            # 空输入跳过
            if not user_input:
                continue
            
            # 退出命令
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("\n感谢使用，再见！")
                break
            
            # 发送消息给智能体
            response = agent.chat(user_input)
            
            # 显示回复
            print(f"\n助手 > {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n检测到中断，正在退出...")
            break
        except Exception as e:
            print(f"\n错误: {e}\n")


def single_mode(agent: Agent, message: str):
    """单次对话模式"""
    response = agent.chat(message)
    print(response)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="OpenViking Agent - 智能体应用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 启动交互式对话
  python main.py -m "你好"          # 单次对话模式
  python main.py -c config/ov.conf  # 指定配置文件
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config/ov.conf",
        help="配置文件路径 (默认: config/ov.conf)"
    )
    
    parser.add_argument(
        "-m", "--message",
        help="单次对话模式，直接传入消息内容"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示智能体统计信息"
    )
    
    args = parser.parse_args()
    
    try:
        # 初始化智能体
        agent = Agent(config_path=args.config)
        
        # 显示统计信息
        if args.stats:
            stats = agent.get_stats()
            print("智能体统计信息:")
            print(f"  工作空间: {stats['workspace']}")
            print(f"  对话轮数: {stats['conversation_turns']}")
            print(f"  工具数量: {stats['tools_count']}")
            print("  记忆统计:")
            for category, count in stats['memory_stats'].items():
                print(f"    {category}: {count}")
            return
        
        # 单次对话模式
        if args.message:
            single_mode(agent, args.message)
            return
        
        # 交互式模式
        interactive_mode(agent)
        
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
