"""
V2 /api/knowledge — 知识库管理
GET  /api/knowledge/categories — 获取分类列表
POST /api/knowledge/classify   — 对文本进行分类（K1 流程）
POST /api/knowledge/rebuild     — 重建知识库向量索引
POST /api/knowledge/examples    — 追加示例
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/knowledge", tags=["V2_知识库"])


class ClassifyRequest(BaseModel):
    texts: List[str]


class AddExampleRequest(BaseModel):
    text: str
    category: str
    style: Optional[str] = ""
    scene: Optional[str] = ""


@router.get("/categories")
async def get_categories() -> Dict[str, Any]:
    """获取知识库分类列表"""
    try:
        from backend.services.knowledge_base import get_knowledge_base_service
        kb = get_knowledge_base_service()
        categories = kb.get_categories()
        return {
            "code": 0,
            "message": "获取成功",
            "data": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify")
async def classify_text(request: ClassifyRequest) -> Dict[str, Any]:
    """
    对多行文本进行分类（K1 流程，纯向量检索）。
    设计依据：[D-009] 零 LLM 成本
    """
    try:
        from backend.services.knowledge_base import get_knowledge_base_service
        from backend.agents.sub.k1_classifier import K1ClassifierAgent

        kb = get_knowledge_base_service()
        classifier = K1ClassifierAgent()

        results = []
        for text in request.texts:
            # 优先用 KnowledgeBaseService.search
            search_result = kb.search(text, top_k=1, threshold=0.0)
            if search_result:
                top = search_result[0]
                results.append({
                    "text": text,
                    "category": top.get("category", "general"),
                    "score": top.get("similarity", 0.0),
                    "example": top.get("text", "")[:100]
                })
            else:
                results.append({
                    "text": text,
                    "category": "general",
                    "score": 0.0,
                    "example": None
                })

        return {
            "code": 0,
            "message": "分类成功",
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild")
async def rebuild_index() -> Dict[str, Any]:
    """
    重建知识库向量索引。
    遍历 data/knowledge_base/kb_examples/*.jsonl，构建 FAISS 索引。
    """
    try:
        from backend.services.knowledge_base import get_knowledge_base_service
        kb = get_knowledge_base_service()
        result = kb.rebuild_index()

        return {
            "code": 0,
            "message": "重建成功",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/examples")
async def add_example(request: AddExampleRequest) -> Dict[str, Any]:
    """
    向知识库追加一条示例。
    """
    try:
        from backend.services.knowledge_base import get_knowledge_base_service
        kb = get_knowledge_base_service()

        success = kb.add_example({
            "text": request.text,
            "category": request.category,
            "style": request.style,
            "scene": request.scene
        })

        if success:
            return {
                "code": 0,
                "message": "追加成功",
                "data": None
            }
        else:
            return {
                "code": -1,
                "message": "追加失败",
                "data": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
