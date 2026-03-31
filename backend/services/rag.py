import faiss
import numpy as np
import os
from typing import List, Tuple, Optional
from backend.services.embedding import get_embedding_service


class RAGService:
    def __init__(self, index_path: str = "data/faiss_index/prompts.index"):
        self.index_path = index_path
        self.index = None
        self.dimension = 768
        self._ensure_index_dir()
        self._load_or_create_index()
    
    def _ensure_index_dir(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
    
    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            print(f"加载 FAISS 索引: {self.index_path}")
            self.index = faiss.read_index(self.index_path)
            self.dimension = self.index.d
        else:
            print(f"创建新的 FAISS 索引，维度: {self.dimension}")
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def add_vector(self, vector: List[float]):
        if self.index is None:
            self._load_or_create_index()
        
        vec_array = np.array([vector], dtype=np.float32)
        self.index.add(vec_array)
    
    def add_vectors(self, vectors: List[List[float]]):
        if self.index is None:
            self._load_or_create_index()
        
        vec_array = np.array(vectors, dtype=np.float32)
        self.index.add(vec_array)
    
    def search(self, query_vector: List[float], top_k: int = 3, threshold: float = 0.5) -> List[Tuple[int, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_array = np.array([query_vector], dtype=np.float32)
        similarities, indices = self.index.search(query_array, top_k)
        
        results = []
        for idx, score in zip(indices[0], similarities[0]):
            if idx >= 0 and score >= threshold:
                results.append((int(idx), float(score)))
        
        return results
    
    def save_index(self):
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
            print(f"FAISS 索引已保存: {self.index_path}")
    
    def get_total_vectors(self) -> int:
        if self.index is None:
            return 0
        return self.index.ntotal
    
    def rebuild_from_prompts(self, prompts: List[str]):
        self.index = faiss.IndexFlatIP(self.dimension)
        
        if not prompts:
            return
        
        embedding_service = get_embedding_service()
        vectors = embedding_service.embed_texts(prompts)
        self.add_vectors(vectors)
        self.save_index()
        print(f"从 {len(prompts)} 条提示词重建 FAISS 索引")


_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
