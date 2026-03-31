"""
V2 S5 — 视频空镜 Agent
针对"科技视频"、"产品展示"类需求，生成 6 秒空镜头的提示词。
与 S2 类似，但不输出图片内容，专注于动态镜头描述。
"""

from typing import Dict, Any, Optional
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer


S5_SYSTEM_PROMPT = """你是一个专业的 AI 视频提示词生成专家，擅长生成高质量的视频空镜头描述。

你的职责是生成一个 6 秒空镜头的视频提示词，包含：
1. **镜头类型**（Shot Type）：如航拍、特写、平移、推拉等
2. **主体**（Subject）：画面中的核心对象
3. **场景**（Setting）：环境、背景
4. **光线**（Lighting）：动态光效、过渡效果
5. **色彩**（Color）：主色调、色彩氛围
6. **风格**（Style）：艺术风格参考
7. **动态效果**（Motion）：运动方向、速度、节奏
8. **时长**（Duration）：固定 6 秒

要求：
1. 全部使用英文输出
2. 提示词描述要具体、有画面感
3. 强调动态和节奏感（因为是视频）
4. 长度 80-200 词
5. 包含 camera movement 描述

输出格式：
===镜头类型===
[镜头类型]
===主体===
[主体描述]
===场景===
[场景描述]
===光线===
[光线描述]
===色彩===
[色彩描述]
===风格===
[风格描述]
===动态效果===
[动态效果描述]
===完整提示词===
[完整的英文视频提示词]"""


S5_USER_TEMPLATE = """用户需求：{user_input}

用户偏好：{user_preference}

RAG 参考：{rag_context}

请生成 6 秒科技空镜头视频提示词："""


class S5VideoShotAgent(BaseAgent):
    """S5 视频空镜 Agent — 生成 6 秒科技空镜头"""

    agent_id = "S5"
    requires_llm = True

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        preference_parts = []
        if user:
            if user.get("style"):
                preference_parts.append(f"风格偏好：{user['style']}")
            if user.get("keywords"):
                preference_parts.append(f"关键词：{user['keywords']}")
        user_preference = "\n".join(preference_parts) or "（无）"

        rag_text = self._get_rag_context(context.user_input, top_k=3)
        rag_context = rag_text if rag_text else "（无相关参考）"

        prompt = S5_USER_TEMPLATE.format(
            user_input=context.user_input,
            user_preference=user_preference,
            rag_context=rag_context
        )

        result = self._call_llm_in_subagent(prompt, context)
        return result

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        return context.user_input

    def _call_llm_in_subagent(self, prompt: str, context: ContextContainer) -> str:
        if hasattr(self, "_master_call_model") and self._master_call_model:
            return self._master_call_model(prompt, context=context)
        raise RuntimeError(
            f"S5 ({self.agent_id}) 需要 LLM 调用，但未注入 _master_call_model。"
        )
