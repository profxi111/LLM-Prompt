import os
from typing import Optional


class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    DATA_DIR = os.path.join(BASE_DIR, "data")
    UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
    FAISS_INDEX_DIR = os.path.join(DATA_DIR, "faiss_index")
    FAISS_INDEX_PATH = os.path.join(FAISS_INDEX_DIR, "prompts.index")
    DATABASE_PATH = os.path.join(DATA_DIR, "prompts.db")
    
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    EMBEDDING_MODEL = "m3e-small"
    EMBEDDING_DEVICE = "cpu"
    
    RAG_TOP_K = 3
    RAG_THRESHOLD = 0.5
    
    DEFAULT_USER_ID = 1
    
    @classmethod
    def ensure_directories(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.UPLOADS_DIR, exist_ok=True)
        os.makedirs(cls.FAISS_INDEX_DIR, exist_ok=True)


config = Config()
