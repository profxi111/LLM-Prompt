"""
V2 S3 — 整理优化 Agent（终端节点）
接收 S2/S4 的输出，进行中英双语整理 + 字数控制。
"""

from typing import Dict, Any, Optional
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer


S3_SYSTEM_PROMPT = """你是一个专业的提示词优化助手，擅长整理和优化 AI 图像生成提示词。

你的职责是将输入的提示词整理为：
1. **中文说明**：简要说明这张图像的核心特征（1-3句话）
2. **英文提示词**：优化后的英文提示词，保留关键元素，移除冗余

要求：
- 英文提示词使用逗号分隔的短语，简洁专业
- 保留所有重要的画面元素和风格描述
- 适当添加质量增强标签（如：masterpiece, best quality, 8k, professional）
- 负面提示词单独列出（--no 格式）

字数要求：
- 英文提示词不超过 300 词
- 中文说明不超过 100 字

输出格式：
===中文说明===
[简短中文描述]
===英文提示词===
[英文提示词]
===负面提示词===
[负面提示词]"""


class S3OrganizeAgent(BaseAgent):
    """S3 整理优化 Agent — 中英双语整理 + 字数控制（终端节点）"""

    agent_id = "S3"
    requires_llm = True

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        整理 S2/S4 的输出，生成中英双语的最终提示词。
        S3 是终端节点，输出即最终结果。
        """
        # 获取上游 Agent 的输出作为 S3 的输入
        upstream_output = self._get_upstream_output(context)
        if not upstream_output:
            upstream_output = input_text

        prompt = f"""{S3_SYSTEM_PROMPT}

原始提示词（待整理）：
{upstream_output}

请按格式整理优化："""

        result = self._call_llm_in_subagent(prompt, context)
        return result

    def _get_upstream_output(self, context: ContextContainer) -> str:
        """获取上游 Agent 的输出（S2 或 S4）"""
        # 优先取 S2（通常 S3 前是 S2）
        s2 = context.get_output("S2")
        if s2:
            return s2.output_text
        # 降级取 S4
        s4 = context.get_output("S4")
        if s4:
            return s4.output_text
        return ""

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        s2 = context.get_output("S2")
        return s2.output_text if s2 else context.user_input

    def _call_llm_in_subagent(self, prompt: str, context: ContextContainer) -> str:
        if hasattr(self, "_master_call_model") and self._master_call_model:
            return self._master_call_model(prompt, context=context)
        raise RuntimeError(
            f"S3 ({self.agent_id}) 需要 LLM 调用，但未注入 _master_call_model。"
        )
