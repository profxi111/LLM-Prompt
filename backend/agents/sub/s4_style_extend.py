"""
V2 S4 — 风格延展 Agent
在 S3 整理后，生成 3 个不同风格的变体，供用户选择。
"""

import json
from typing import Dict, Any, Optional, List
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer


S4_SYSTEM_PROMPT = """你是一个专业的 AI 图像风格专家，擅长在同一构图基础上生成多个风格变体。

给定一个基础提示词，请生成 3 个不同风格的变体，每个变体包括：
1. **风格名称**（style）：简洁的风格名称，如"赛博朋克"、"水墨古风"、"极简主义"
2. **变体提示词**（prompt）：在原提示词基础上融合该风格的描述
3. **适用场景**（scene）：该风格的典型使用场景

要求：
1. 3 个变体风格差异要明显
2. 每个变体的英文提示词 80-200 词
3. 保留原提示词的核心构图元素，只改变风格
4. 全部使用英文输出（prompt 字段）

输出格式（JSON 数组）：
```json
[
  {
    "style": "风格名称1",
    "prompt": "融合风格1的完整英文提示词...",
    "scene": "适用场景描述"
  },
  {
    "style": "风格名称2",
    "prompt": "融合风格2的完整英文提示词...",
    "scene": "适用场景描述"
  },
  {
    "style": "风格名称3",
    "prompt": "融合风格3的完整英文提示词...",
    "scene": "适用场景描述"
  }
]
```"""


class S4StyleExtendAgent(BaseAgent):
    """S4 风格延展 Agent — 生成 3 个风格变体"""

    agent_id = "S4"
    requires_llm = True

    def execute(self, context: ContextContainer, user: Optional[Dict[str, Any]] = None) -> ContextContainer:
        """
        S4 执行后，结果存入 context.variants。
        """
        context = super().execute(context, user)

        # 尝试解析 output_text 为 JSON 变体列表
        s4_output = context.get_output("S4")
        if s4_output:
            try:
                # 提取 JSON 部分
                text = s4_output.output_text
                json_start = text.find("[")
                json_end = text.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    variants = json.loads(text[json_start:json_end])
                    context.variants = variants
            except Exception:
                # 解析失败，不影响流程
                pass

        return context

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        基于 S3 的整理后结果（或 S2 草稿）生成 3 个风格变体。
        """
        # 获取 S3 或 S2 的输出
        s3 = context.get_output("S3")
        s2 = context.get_output("S2")
        source_prompt = s3.output_text if s3 else (s2.output_text if s2 else input_text)

        prompt = f"""{S4_SYSTEM_PROMPT}

基础提示词：
{source_prompt}

请生成 3 个风格变体（JSON 格式）："""

        result = self._call_llm_in_subagent(prompt, context)
        return result

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        return context.user_input

    def _call_llm_in_subagent(self, prompt: str, context: ContextContainer) -> str:
        if hasattr(self, "_master_call_model") and self._master_call_model:
            return self._master_call_model(prompt, context=context)
        raise RuntimeError(
            f"S4 ({self.agent_id}) 需要 LLM 调用，但未注入 _master_call_model。"
        )
