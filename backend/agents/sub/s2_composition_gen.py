"""
V2 S2 — 构图生成 Agent（核心节点）
接收用户需求 + 图片描述（可选），生成提示词草稿。
不做整理/翻译/字数控制 — 这是 S3 的职责。
"""

from typing import Dict, Any, Optional
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer


S2_SYSTEM_PROMPT = """你是一个专业的 AI 图像提示词生成专家，擅长生成高质量的英文图像描述提示词。

你的职责是根据用户需求，生成一个详细、专业的英文图像提示词，包含以下元素：
- 主体（Subject）：画面中的主要对象
- 场景（Setting）：环境、背景
- 构图（Composition）：视角、景别、取景方式
- 光线（Lighting）：光源类型、光影效果
- 色彩（Color）：主色调、配色方案
- 风格（Style）：艺术风格、参考风格
- 氛围（Mood）：情绪、氛围描述
- 质量标签（Quality）：高分辨率、专业摄影等

要求：
1. 全部使用英文输出
2. 提示词要专业、详细、有画面感
3. 适当使用逗号分隔的短语，避免完整句子
4. 可以包含负面提示词（Negative Prompt）
5. 长度适中（100-300词）

格式示例：
A sleek [product name], floating on a minimalist white background, centered composition, soft studio lighting from the upper left, clean gradient backdrop transitioning from pale gray to white, professional product photography style, high-end luxury feel, shot with Canon EOS R5, 85mm lens, f/2.8 aperture, ultra-sharp focus on the product, reflections on glossy surfaces, high resolution, 8k --no blurry, low quality, cluttered background"""

S2_USER_TEMPLATE = """用户需求：{user_input}

图片描述（参考）：{image_description}

用户偏好：{user_preference}

RAG 参考：{rag_context}

请根据以上信息生成图像提示词："""


class S2CompositionGenAgent(BaseAgent):
    """S2 构图生成 Agent — 生成提示词草稿（核心节点）"""

    agent_id = "S2"
    requires_llm = True

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        构建 prompt 并调用 LLM 生成构图提示词。
        S2 输出是 S3/S4 的输入，S2 不做整理。
        """
        print("DEBUG S2: _do_process 开始")
        # 构建用户偏好字符串
        preference_parts = []
        if user:
            if user.get("style"):
                preference_parts.append(f"风格偏好：{user['style']}")
            if user.get("keywords"):
                preference_parts.append(f"关键词：{user['keywords']}")
            if user.get("tone"):
                preference_parts.append(f"语气：{user['tone']}")
        user_preference = "\n".join(preference_parts) or "（无）"
        print(f"DEBUG S2: 用户偏好构建完成")

        # 获取图片描述（S1 输出）
        s1_output = context.get_output("S1")
        image_description = s1_output.output_text if s1_output else "（无图片）"
        print(f"DEBUG S2: 图片描述获取完成")

        # 获取 RAG 上下文
        print("DEBUG S2: 获取RAG上下文...")
        rag_text = self._get_rag_context(context.user_input, top_k=3)
        rag_context = rag_text if rag_text else "（无相关参考）"
        print(f"DEBUG S2: RAG上下文获取完成")

        prompt = S2_USER_TEMPLATE.format(
            user_input=context.user_input,
            image_description=image_description,
            user_preference=user_preference,
            rag_context=rag_context
        )
        print(f"DEBUG S2: prompt构建完成, 长度={len(prompt)}")

        # 调用 LLM（由 MasterAgent 注入）
        print("DEBUG S2: 调用LLM...")
        result = self._call_llm_in_subagent(prompt, context)
        print(f"DEBUG S2: LLM调用完成, 结果长度={len(result) if result else 0}")
        return result

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        return context.user_input

    def _call_llm_in_subagent(self, prompt: str, context: ContextContainer) -> str:
        """
        在子 Agent 中调用 LLM。
        子 Agent 的 LLM 调用统一通过 MasterAgent 路由。
        """
        if hasattr(self, "_master_call_model") and self._master_call_model:
            return self._master_call_model(prompt)

        raise RuntimeError(
            f"S2 ({self.agent_id}) 需要 LLM 调用，但未注入 _master_call_model。"
            " 请通过 MasterAgent 调用子 Agent。"
        )
