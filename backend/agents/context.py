"""
V2 ContextContainer — 记录每个 Agent 的输入输出，支持序列化到 sessions 表。
设计依据：[D-010] 为什么 ContextContainer 用 JSON 序列化而非关系表
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List


@dataclass
class AgentOutput:
    """单个 Agent 的执行结果"""
    agent_id: str           # e.g. "S1", "S2", "S3"
    input_text: str          # Agent 收到的原始输入
    output_text: str        # Agent 生成的原始输出
    model_name: str         # 使用的模型名称
    duration_ms: int         # 执行耗时
    timestamp: str = ""      # ISO 格式时间戳

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextContainer:
    """
    V2 核心上下文容器 — 记录完整 Agent 链路执行过程。
    整体序列化为 JSON 存入 sessions 表，不拆分为多表关联。
    设计依据：[D-010]
    """
    session_id: str = ""
    user_id: int = 1
    user_input: str = ""
    image_path: Optional[str] = None

    # 各 Agent 输出（按执行顺序追加）
    agent_outputs: List[AgentOutput] = field(default_factory=list)

    # 最终输出（最后一步 Agent 的输出）
    final_prompt: str = ""

    # 分类结果（K1 流程）
    classified_category: Optional[str] = None

    # S4 变体
    variants: List[Dict[str, Any]] = field(default_factory=list)

    # Agent 链路 ID 列表
    agent_chain: List[str] = field(default_factory=list)

    # 路由决策
    route: str = ""         # "S1_S2_S3" | "S2_S3" | "S5_S3" | "K1"
    confidence: float = 0.0

    # RAG + 知识库上下文
    rag_context: List[Dict[str, Any]] = field(default_factory=list)
    kb_context: List[Dict[str, Any]] = field(default_factory=list)

    # 执行元信息
    total_duration_ms: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.updated_at = self.created_at

    def add_output(self, agent_id: str, input_text: str, output_text: str,
                   model_name: str, duration_ms: int):
        """追加一个 Agent 的执行结果"""
        output = AgentOutput(
            agent_id=agent_id,
            input_text=input_text,
            output_text=output_text,
            model_name=model_name,
            duration_ms=duration_ms
        )
        self.agent_outputs.append(output)
        self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 追加到链路
        if agent_id not in self.agent_chain:
            self.agent_chain.append(agent_id)

    def get_output(self, agent_id: str) -> Optional[AgentOutput]:
        """获取指定 Agent 的输出"""
        for output in self.agent_outputs:
            if output.agent_id == agent_id:
                return output
        return None

    def set_final(self, prompt: str):
        """设置最终输出"""
        self.final_prompt = prompt
        self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def serialize(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_input": self.user_input,
            "image_path": self.image_path,
            "agent_outputs": [o.to_dict() for o in self.agent_outputs],
            "final_prompt": self.final_prompt,
            "classified_category": self.classified_category,
            "variants": self.variants,
            "agent_chain": self.agent_chain,
            "route": self.route,
            "confidence": self.confidence,
            "rag_context": self.rag_context,
            "kb_context": self.kb_context,
            "total_duration_ms": self.total_duration_ms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }, ensure_ascii=False)

    @classmethod
    def deserialize(cls, data: str) -> "ContextContainer":
        """从 JSON 字符串反序列化"""
        obj = json.loads(data)
        outputs = [
            AgentOutput(**o) for o in obj.get("agent_outputs", [])
        ]
        return cls(
            session_id=obj.get("session_id", ""),
            user_id=obj.get("user_id", 1),
            user_input=obj.get("user_input", ""),
            image_path=obj.get("image_path"),
            agent_outputs=outputs,
            final_prompt=obj.get("final_prompt", ""),
            classified_category=obj.get("classified_category"),
            variants=obj.get("variants", []),
            agent_chain=obj.get("agent_chain", []),
            route=obj.get("route", ""),
            confidence=obj.get("confidence", 0.0),
            rag_context=obj.get("rag_context", []),
            kb_context=obj.get("kb_context", []),
            total_duration_ms=obj.get("total_duration_ms", 0),
            created_at=obj.get("created_at", ""),
            updated_at=obj.get("updated_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于 API 响应）"""
        return {
            "session_id": self.session_id,
            "user_input": self.user_input,
            "image_path": self.image_path,
            "final_prompt": self.final_prompt,
            "classified_category": self.classified_category,
            "variants": self.variants,
            "agent_chain": self.agent_chain,
            "route": self.route,
            "confidence": self.confidence,
            "rag_context": self.rag_context,
            "kb_context": self.kb_context,
            "total_duration_ms": self.total_duration_ms,
            "created_at": self.created_at,
            # 各 Agent 详情
            "s1_image_description": self._get_agent_output("S1"),
            "s2_draft_prompt": self._get_agent_output("S2"),
            "s3_final_prompt": self._get_agent_output("S3"),
            "s4_variants": self._get_agent_output("S4"),
        }

    def _get_agent_output(self, agent_id: str) -> Any:
        output = self.get_output(agent_id)
        if output:
            if agent_id == "S4":
                try:
                    return json.loads(output.output_text)
                except Exception:
                    return output.output_text
            return output.output_text
        return None
