"""
V2 KnowledgeBaseService — 知识库服务单例
支持 search / classify / add_example / rebuild_index
设计依据：[D-009] 为什么知识库采用纯向量检索而非 LLM 分类
"""

import json
import os
import time
import faiss
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from backend.services.embedding import get_embedding_service
from backend.database.db import execute_query


class KnowledgeBaseService:
    """
    知识库服务 — 单例。
    基于 FAISS 向量检索，存储 kb_examples/ 中的分类示例。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.embedding_service = get_embedding_service()
        self.dimension = 768
        self.examples_dir = "data/knowledge_base/kb_examples"
        self.index_path = "data/knowledge_base/kb_vectors/examples.index"
        self.meta_path = "data/knowledge_base/kb_vectors/examples_meta.jsonl"
        self.vectors_dir = "data/knowledge_base/kb_vectors"

        self.index: Optional[faiss.Index] = None
        self.meta: List[Dict[str, Any]] = []

        os.makedirs(self.vectors_dir, exist_ok=True)
        self._load_index()

    def _load_index(self):
        """加载或创建 FAISS 索引"""
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.meta = [json.loads(line) for line in f if line.strip()]
                print(f"知识库索引加载完成: {self.index.ntotal} 条")
                return
            except Exception as e:
                print(f"加载知识库索引失败: {e}，将重建")

        self.index = faiss.IndexFlatIP(self.dimension)
        self.meta = []
        print("创建新的知识库索引")

    def search(
        self,
        query_text: str,
        top_k: int = 3,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        在知识库中检索与 query_text 最相似的示例。
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = self.embedding_service.embed_text(query_text)
        query_array = np.array([query_vector], dtype=np.float32)

        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(query_array, k)

        results = []
        for idx, score in zip(indices[0], similarities[0]):
            if idx < 0 or idx >= len(self.meta):
                continue
            if score >= threshold:
                item = self.meta[int(idx)]
                item["similarity"] = float(score)
                results.append(item)

        return results

    def classify(self, text: str) -> Dict[str, Any]:
        """
        对文本进行分类（K1 流程）。
        使用向量检索找到最相似的示例，返回其分类。
        """
        results = self.search(text, top_k=1, threshold=0.0)

        if not results:
            return {"category": "general", "score": 0.0, "example": None}

        top = results[0]
        return {
            "category": top.get("category", "general"),
            "score": top.get("similarity", 0.0),
            "example": top
        }

    def add_example(self, example: Dict[str, Any]) -> bool:
        """
        向知识库追加一条示例，自动重新索引。
        """
        try:
            text = example.get("text", example.get("prompt", ""))
            if not text:
                return False

            vector = self.embedding_service.embed_text(text)

            if self.index is None:
                self.index = faiss.IndexFlatIP(self.dimension)

            vec_array = np.array([vector], dtype=np.float32)
            self.index.add(vec_array)

            meta_item = {
                "text": text,
                "category": example.get("category", "general"),
                "style": example.get("style", ""),
                "scene": example.get("scene", ""),
            }
            self.meta.append(meta_item)

            self._save_index()
            return True

        except Exception as e:
            print(f"追加知识库示例失败: {e}")
            return False

    def rebuild_index(self) -> Dict[str, Any]:
        """
        从 kb_examples/ 目录重建整个知识库索引。
        """
        start_time = time.time()

        self.index = faiss.IndexFlatIP(self.dimension)
        self.meta = []

        if not os.path.exists(self.examples_dir):
            os.makedirs(self.examples_dir, exist_ok=True)
            # 创建默认分类文件
            default_data = {
                "科技风": [
                    {"text": "High-tech circuit board, blue neon lighting, futuristic cyberpunk style", "category": "科技风", "style": "cyberpunk"},
                    {"text": "Sleek smartphone device, floating holographic interface, dark background", "category": "科技风", "style": "minimal"},
                ],
                "复古风": [
                    {"text": "Vintage film camera, warm golden hour lighting, retro aesthetic", "category": "复古风", "style": "vintage"},
                    {"text": "Classic 1950s diner, neon signs, nostalgic Americana atmosphere", "category": "复古风", "style": "retro"},
                ],
            }
            for cat, examples in default_data.items():
                jsonl_path = os.path.join(self.examples_dir, f"{cat}.jsonl")
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    for ex in examples:
                        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        total = 0
        for filename in os.listdir(self.examples_dir):
            if not filename.endswith(".jsonl"):
                continue
            category = filename.replace(".jsonl", "")
            filepath = os.path.join(self.examples_dir, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            text = obj.get("text", obj.get("prompt", ""))
                            if not text:
                                continue
                            vector = self.embedding_service.embed_text(text)
                            vec_array = np.array([vector], dtype=np.float32)
                            self.index.add(vec_array)

                            meta_item = {
                                "text": text,
                                "category": obj.get("category", category),
                                "style": obj.get("style", ""),
                                "scene": obj.get("scene", ""),
                            }
                            self.meta.append(meta_item)
                            total += 1
                        except Exception:
                            continue
            except Exception as e:
                print(f"读取 {filepath} 失败: {e}")
                continue

        self._save_index()

        # 更新数据库元数据
        rebuild_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        execute_query(
            """INSERT OR REPLACE INTO knowledge_base_meta
               (id, kb_version, last_rebuild_at, example_count, dimension, embedding_model)
               VALUES (1, 'v2.0', ?, ?, ?, 'm3e-small')""",
            (rebuild_at, total, self.dimension)
        )

        elapsed = int((time.time() - start_time) * 1000)
        print(f"知识库索引重建完成: {total} 条，耗时 {elapsed}ms")

        return {
            "total": total,
            "dimension": self.dimension,
            "rebuild_at": rebuild_at,
            "elapsed_ms": elapsed
        }

    def _save_index(self):
        """保存索引和元数据到磁盘"""
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)

        with open(self.meta_path, "w", encoding="utf-8") as f:
            for item in self.meta:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def get_categories(self) -> List[Dict[str, Any]]:
        """获取知识库分类列表"""
        categories = {}
        for item in self.meta:
            cat = item.get("category", "general")
            if cat not in categories:
                categories[cat] = {"name": cat, "count": 0}
            categories[cat]["count"] += 1

        return list(categories.values())


_kb_service: Optional[KnowledgeBaseService] = None


def get_knowledge_base_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService()
    return _kb_service
