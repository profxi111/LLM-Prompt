"""
V2 K1 — 提示词分类 Agent
纯向量检索，无 LLM 调用，零成本。
设计依据：[D-009] 为什么知识库采用纯向量检索而非 LLM 分类
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from backend.agents.base import BaseAgent
from backend.agents.context import ContextContainer
from backend.services.embedding import get_embedding_service


class K1ClassifierAgent(BaseAgent):
    """
    K1 提示词分类 Agent — 纯 FAISS 向量检索，零 LLM 成本。
    设计依据：[D-009]
    """

    agent_id = "K1"
    requires_llm = False  # 纯向量检索，不需要 LLM

    # 分类标签定义
    CATEGORIES = {
        "科技风": "tech",
        "复古风": "retro",
        "国潮风": "guochao",
        "视频空镜头": "video_shot",
        "电商标题": "ecommerce",
        "通用": "general"
    }

    def __init__(self):
        super().__init__()
        self._kb_examples: Dict[str, List[Tuple[str, List[float]]]] = {}
        self._embedding_service = get_embedding_service()
        self._load_kb_examples()

    def _load_kb_examples(self):
        """从 kb_examples/ 目录加载 JSONL 示例"""
        kb_dir = "data/knowledge_base/kb_examples"
        if not os.path.exists(kb_dir):
            return

        for filename in os.listdir(kb_dir):
            if not filename.endswith(".jsonl"):
                continue
            category = filename.replace(".jsonl", "")
            examples = []
            filepath = os.path.join(kb_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            text = obj.get("text", obj.get("prompt", ""))
                            if text:
                                vector = self._embedding_service.embed_text(text)
                                examples.append((text, vector))
                        except Exception:
                            continue
                self._kb_examples[category] = examples
            except Exception:
                pass

    def _do_process(self, input_text: str, context: ContextContainer,
                    user: Optional[Dict[str, Any]]) -> str:
        """
        纯向量检索：找到与输入最相似的示例，返回其分类。
        """
        if not self._kb_examples:
            return "general"

        query_vector = self._embedding_service.embed_text(input_text)

        best_score = -1.0
        best_category = "general"

        for category, examples in self._kb_examples.items():
            for text, vector in examples:
                score = self._cosine_similarity(query_vector, vector)
                if score > best_score:
                    best_score = score
                    best_category = category

        context.classified_category = best_category
        return best_category

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def classify(self, text: str) -> Dict[str, Any]:
        """
        对单条文本进行分类。
        返回：{ "category": "科技风", "score": 0.95, "top_examples": [...] }
        """
        query_vector = self._embedding_service.embed_text(text)

        results = []
        for category, examples in self._kb_examples.items():
            best_score = -1.0
            best_example = None
            for text_ex, vector in examples:
                score = self._cosine_similarity(query_vector, vector)
                if score > best_score:
                    best_score = score
                    best_example = text_ex
            results.append({
                "category": category,
                "score": best_score,
                "top_example": best_example or ""
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        top = results[0] if results else {"category": "general", "score": 0.0}

        return {
            "category": top["category"],
            "score": top["score"],
            "all_scores": results
        }
