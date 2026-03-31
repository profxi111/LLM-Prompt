"""
V2 /api/adjust — 用户对指定 Agent 的输出进行调整
POST /api/adjust
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["V2_调整"])


class AdjustRequest(BaseModel):
    session_id: str
    target_agent: str   # "S1" | "S2" | "S3" | "S4"
    user_instruction: Optional[str] = ""


@router.post("/adjust")
async def adjust_prompt(request: AdjustRequest):
    """
    对指定 Agent 的输出进行重新处理。
    目标 Agent 输出被清除后重跑，后续 Agent 依次执行。
    """
    try:
        from backend.agents.master import MasterAgent
        master = MasterAgent()
        result = master.process_adjust(
            session_id=request.session_id,
            target_agent=request.target_agent,
            user_instruction=request.user_instruction
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
