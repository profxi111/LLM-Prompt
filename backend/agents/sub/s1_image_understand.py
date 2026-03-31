"""
V2 S1 — 图片理解 Agent
调用 vision_service 描述上传的图片，为 S2 提供图片语义信息。
仅在有图片上传时执行。
"""

from typing import Dict, Any, Optional
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer


class S1ImageUnderstandAgent(BaseAgent):
    """S1 图片理解 Agent — 调用视觉模型描述图片"""

    agent_id = "S1"
    requires_llm = False  # 使用视觉模型而非文本 LLM

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        调用 vision_service 描述图片。
        如果没有配置视觉模型，返回占位说明。
        """
        image_path = context.image_path
        if not image_path:
            return "（无图片）"

        try:
            from backend.services.vision import get_vision_service
            vision_service = get_vision_service()
            description = vision_service.describe(image_path)
            return description
        except Exception as e:
            return f"（视觉模型调用失败：{str(e)}）"

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        # S1 不需要文本输入，只需要图片路径
        return context.image_path or ""
