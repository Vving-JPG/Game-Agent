"""
文本渲染器 - 打字机效果输出

提供逐字显示的打字机效果，增强 RPG 游戏的沉浸感
"""

import sys
import time


class TextRenderer:
    """文本渲染器，支持打字机效果"""
    
    def __init__(self, speed=0.03):
        """
        初始化渲染器
        
        Args:
            speed: 打字速度（秒/字符），默认 0.03
        """
        self.speed = speed
    
    def show(self, text):
        """
        逐字输出文本，就像打字机一样
        
        Args:
            text: 要显示的文本
        """
        for ch in text:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(self.speed)
        print()  # 换行
    
    def show_instant(self, text):
        """
        瞬间显示文本（不需要打字机效果时使用）
        
        Args:
            text: 要显示的文本
        """
        print(text)
    
    def set_speed(self, speed):
        """
        设置打字速度
        
        Args:
            speed: 新的打字速度（秒/字符）
        """
        self.speed = speed


# 默认渲染器实例
renderer = TextRenderer()


if __name__ == "__main__":
    # 测试代码
    print("=== 打字机效果测试 ===")
    
    renderer.show("这是一段逐字显示的文本...")
    time.sleep(0.5)
    
    renderer.show_instant("这段是瞬间显示的！")
    time.sleep(0.5)
    
    # 调整速度
    renderer.set_speed(0.1)
    renderer.show("这段显示得更慢...")
    
    renderer.set_speed(0.01)
    renderer.show("这段显示得更快！！！")
