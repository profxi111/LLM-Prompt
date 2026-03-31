"""
V2 /api/sessions — Session 管理
GET /api/sessions            — 列出最近 20 条会话
GET /api/sessions/{id}       — 获取完整会话（含链路详情）
DELETE /api/sessions/{id}    — 删除会话
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api", tags=["V2_Sessions"])


@router.get("/sessions")
async def list_sessions(limit: int = 20) -> Dict[str, Any]:
    """
    列出最近的会话摘要。
    """
    try:
        from backend.database.db import execute_query

        rows = execute_query(
            "SELECT session_id, user_id, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
            fetch_all=True
        )

        sessions = [
            {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

        return {
            "code": 0,
            "message": "获取成功",
            "data": sessions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """
    获取完整会话数据，包含 ContextContainer 所有链路详情。
    """
    try:
        from backend.database.db import execute_query
        from backend.agents.context import ContextContainer

        row = execute_query(
            "SELECT context_json FROM sessions WHERE session_id = ?",
            (session_id,),
            fetch_one=True
        )

        if not row:
            raise HTTPException(status_code=404, detail="会话不存在")

        context = ContextContainer.deserialize(row["context_json"])

        return {
            "code": 0,
            "message": "获取成功",
            "data": context.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """
    删除指定会话。
    """
    try:
        from backend.database.db import execute_query

        execute_query(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,)
        )

        return {
            "code": 0,
            "message": "删除成功",
            "data": None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
