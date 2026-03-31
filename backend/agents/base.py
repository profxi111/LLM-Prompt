"""
V2 BaseAgent — 所有专项 Agent 的抽象基类。
设计依据：[D-008] 为什么用管道编排而非单一 Agent
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
from backend.agents.context import ContextContainer
from backend.database.db import execute_query
from backend.services.rag import get_rag_service
from backend.services.embedding import get_embedding_service


class BaseAgent(ABC):
    """
    专项 Agent 基类，遵循职责单一原则。
    每个 Agent 只做一件事，边界清晰，可独立测试。
    """

    # 子类必须设置自己的 Agent ID
    agent_id: str = "BASE"

    # 是否需要调用 LLM（K1 为纯向量检索，不需要）
    requires_llm: bool = True

    def __init__(self):
        self.rag_service = get_rag_service()
        self.embedding_service = get_embedding_service()

    def execute(self, context: ContextContainer, user: Optional[Dict[str, Any]] = None) -> ContextContainer:
        """
        执行 Agent 的标准入口。
        子类通过覆写 _do_process() 实现具体逻辑。
        """
        start = time.time()

        # 构建输入
        input_text = self._build_input(context, user)

        # 执行处理
        output_text = self._do_process(input_text, context, user)

        # 记录耗时
        duration_ms = int((time.time() - start) * 1000)

        # 获取当前使用的模型
        model_name = self._get_model_name()

        # 追加到 ContextContainer
        context.add_output(
            agent_id=self.agent_id,
            input_text=input_text,
            output_text=output_text,
            model_name=model_name,
            duration_ms=duration_ms
        )

        return context

    @abstractmethod
    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        子类实现具体处理逻辑。
        返回值：Agent 的文本输出。
        """
        pass

    def _build_input(self, context: ContextContainer,
                     user: Optional[Dict[str, Any]]) -> str:
        """
        子类可覆写，构建发送给 LLM 的 prompt。
        默认返回 user_input。
        """
        return context.user_input

    def _get_model_name(self) -> str:
        """获取当前使用的模型名称（子类可覆写）"""
        return "default"

    def _call_llm(self, prompt: str, temperature: float = 0.7,
                  max_tokens: int = 2000) -> str:
        """调用 LLM 的便捷方法（子类通过 MasterAgent 获取模型）"""
        # 由 MasterAgent 在调用链中注入实际的模型调用
        raise NotImplementedError("请通过 MasterAgent._call_model() 调用")

    def _get_rag_context(self, text: str, top_k: int = 3) -> str:
        """获取 RAG 检索上下文"""
        if self.embedding_service._model is None:
            return ""

        query_vector = self.embedding_service.embed_text(text)
        results = self.rag_service.search(query_vector, top_k=top_k, threshold=0.5)

        if not results:
            return ""

        lines = []
        for idx, score in results:
            row = execute_query(
                "SELECT content FROM prompts WHERE id = ?",
                (idx,),
                fetch_one=True
            )
            if row:
                lines.append(f"[相似度 {score:.2f}] {row['content'][:200]}")

        return "\n".join(lines)
