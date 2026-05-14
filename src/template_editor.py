"""
模板编辑器 — 人机协作优化提示词模板。

编写 → 体验 → 反馈 → AI 修改 → 再次体验
"""

from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.content_generator import ContentGenerator


class TemplateEditor:
    """提示词/模板编辑器 - 人机协作优化"""

    def __init__(self, content_generator: "ContentGenerator"):
        self.gen = content_generator

    def list_templates(self) -> list:
        """列出所有模板"""
        return list(self.gen._templates.keys())

    def view_template(self, name: str):
        """查看模板内容"""
        tpl = self.gen.get_template(name)
        if not tpl:
            print(f"❌ 模板 [{name}] 不存在。")
            return
        print(f"\n{'=' * 60}")
        print(f"模板: {name}")
        print(f"描述: {tpl.get('description', '')}")
        print(f"{'=' * 60}")
        print(tpl.get("content", ""))
        print(f"{'=' * 60}")

    def edit_template(self, name: str):
        """交互式编辑模板"""
        tpl = self.gen.get_template(name)
        if not tpl:
            print(f"❌ 模板 [{name}] 不存在。可编辑: {', '.join(self.list_templates())}")
            return

        print(f"\n当前模板 [{name}]:")
        print("-" * 40)
        print(tpl.get("content", ""))
        print("-" * 40)
        print("\n输入新内容（输入 END 结束，CANCEL 取消）:")

        lines = []
        try:
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                if line.strip().upper() == "CANCEL":
                    print("↩ 已取消")
                    return
                lines.append(line)
        except EOFError:
            pass

        if not lines:
            print("↩ 未输入内容，已取消。")
            return

        new_content = "\n".join(lines)
        self.gen.update_template(name, new_content)
        print(f"✅ 模板 [{name}] 已更新。")

    def test_template(self, name: str, test_input: str):
        """测试模板效果"""
        tpl = self.gen.get_template(name)
        if not tpl:
            print(f"❌ 模板 [{name}] 不存在。")
            return

        try:
            params = json.loads(test_input)
        except json.JSONDecodeError:
            params = {"test": test_input}

        rendered = self.gen.render_template(name, **params)
        if not rendered:
            print("⚠️ 模板渲染结果为空，可能缺少变量。")
            print(f"  需要的变量: {tpl.get('variables', [])}")
            return

        print(f"\n渲染后的提示词 [{name}]:")
        print("-" * 40)
        print(rendered[:500])
        if len(rendered) > 500:
            print(f"... (共 {len(rendered)} 字符)")
        print("-" * 40)

        print("\n⏳ 正在调用 LLM...")
        response = self.gen._call_llm(rendered, expect_json=False, max_tokens=512)
        print(f"\n🤖 LLM 响应:\n{response}")

    def ai_optimize(self, name: str, feedback: str):
        """根据用户反馈让 AI 优化模板"""
        tpl = self.gen.get_template(name)
        if not tpl:
            print(f"❌ 模板 [{name}] 不存在。")
            return

        optimize_prompt = f"""你是一个提示词工程专家。用户对以下提示词模板有反馈，请根据反馈优化模板。

当前模板:
{tpl.get('content', '')}

用户反馈:
{feedback}

请只输出优化后的模板内容（不要任何解释），保留原有的 {{变量}} 占位符。"""

        print("⏳ 正在让 AI 优化模板...")
        new_content = self.gen._call_llm(
            optimize_prompt, expect_json=False, temperature=0.3, max_tokens=1024
        )

        if not new_content or len(new_content) < 10:
            print("❌ AI 优化失败，返回内容为空。")
            return

        print(f"\n优化后的模板:\n{'=' * 40}")
        print(new_content)
        print(f"{'=' * 40}")

        confirm = input("\n是否应用此优化？[Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            self.gen.update_template(name, new_content)
            print(f"✅ 模板 [{name}] 已更新为 AI 优化版本。")
        else:
            print("↩ 已取消，模板未修改。")

    def start_collab_loop(self):
        """启动人机协作循环：编写 → 体验 → 反馈 → AI修改"""
        print("\n" + "=" * 60)
        print("🛠️ 模板协作模式 — 人机协作优化")
        print("=" * 60)

        while True:
            print("\n" + "-" * 40)
            print("1. 查看所有模板")
            print("2. 查看模板详情")
            print("3. 编辑模板")
            print("4. 测试模板")
            print("5. 提交反馈（AI 优化）")
            print("6. 新建模板")
            print("0. 退出")
            print("-" * 40)

            try:
                choice = input("选择 > ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "0":
                break
            elif choice == "1":
                names = self.list_templates()
                if names:
                    print(f"\n已加载模板 ({len(names)}):")
                    for n in names:
                        tpl = self.gen.get_template(n)
                        print(f"  · {n} - {tpl.get('description', '')}")
                else:
                    print("⚠️ 没有模板。")
            elif choice == "2":
                name = input("模板名: ").strip()
                self.view_template(name)
            elif choice == "3":
                name = input("模板名: ").strip()
                self.edit_template(name)
            elif choice == "4":
                name = input("模板名: ").strip()
                test_input = input("测试参数 (JSON): ").strip()
                self.test_template(name, test_input)
            elif choice == "5":
                name = input("模板名: ").strip()
                print("输入反馈（输入 END 结束）:")
                lines = []
                try:
                    while True:
                        line = input()
                        if line.strip().upper() == "END":
                            break
                        lines.append(line)
                except EOFError:
                    pass
                if lines:
                    feedback = "\n".join(lines)
                    self.ai_optimize(name, feedback)
            elif choice == "6":
                name = input("新模板名: ").strip()
                if not name:
                    continue
                if self.gen.get_template(name):
                    print(f"⚠️ 模板 [{name}] 已存在，使用编辑功能修改。")
                    continue
                print("输入模板内容（输入 END 结束）:")
                lines = []
                try:
                    while True:
                        line = input()
                        if line.strip().upper() == "END":
                            break
                        lines.append(line)
                except EOFError:
                    pass
                if lines:
                    self.gen.update_template(name, "\n".join(lines))
                    print(f"✅ 模板 [{name}] 已创建。")
            else:
                print("无效选项。")

        print("\n👋 模板协作模式结束。")
