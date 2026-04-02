import os
import hashlib
from typing import List

SKIP_EMBEDDING_MODEL = os.environ.get('SKIP_EMBEDDING_MODEL', '1') == '1'
HAS_SENTENCE_TRANSFORMERS = None
SentenceTransformer = None

# 预先设置为False，避免导入sentence_transformers
HAS_SENTENCE_TRANSFORMERS = False


def _check_sentence_transformers():
    global HAS_SENTENCE_TRANSFORMERS, SentenceTransformer
    if HAS_SENTENCE_TRANSFORMERS is not None:
        return HAS_SENTENCE_TRANSFORMERS
    
    if SKIP_EMBEDDING_MODEL:
        HAS_SENTENCE_TRANSFORMERS = False
        return False
    
    try:
        from sentence_transformers import SentenceTransformer as ST
        SentenceTransformer = ST
        HAS_SENTENCE_TRANSFORMERS = True
    except ImportError:
        HAS_SENTENCE_TRANSFORMERS = False
        print("警告: sentence-transformers 未安装，将使用简单文本哈希作为向量")
    
    return HAS_SENTENCE_TRANSFORMERS


class EmbeddingService:
    _instance = None
    _model = None
    _model_load_attempted = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._model_load_attempted:
            self._model_load_attempted = True
            self._load_model()
    
    def _load_model(self):
        if SKIP_EMBEDDING_MODEL:
            print("嵌入模型加载已跳过（设置 SKIP_EMBEDDING_MODEL=0 启用），使用简单文本哈希作为向量")
            self._model = None
            return
        
        if _check_sentence_transformers():
            model_name = 'm3e-small'
            device = 'cpu'

            try:
                print(f"正在加载嵌入模型: {model_name} (设备: {device})")
                self._model = SentenceTransformer(model_name, device=device)
                print(f"嵌入模型加载完成，向量维度: {self._model.get_sentence_embedding_dimension()}")
            except Exception as e:
                print(f"嵌入模型加载失败: {e}，将使用简单文本哈希作为向量")
                self._model = None
        else:
            print("使用简单文本哈希作为向量")
    
    def embed_text(self, text: str) -> List[float]:
        if HAS_SENTENCE_TRANSFORMERS and self._model is not None:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        else:
            return self._simple_hash_vector(text)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if HAS_SENTENCE_TRANSFORMERS and self._model is not None:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            return [self._simple_hash_vector(text) for text in texts]
    
    def _simple_hash_vector(self, text: str) -> List[float]:
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        vector = [float(b) / 255.0 for b in hash_bytes]
        while len(vector) < 768:
            vector.extend(vector)
        return vector[:768]
    
    @property
    def dimension(self) -> int:
        return 768


_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
