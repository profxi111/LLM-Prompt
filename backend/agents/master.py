"""
V2 MasterAgent — 完全重写
支持 4 种路由：S1_S2_S3 / S2_S3 / S5_S3 / K1
支持 process_adjust 多轮调整
支持 session 管理
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet

from backend.agents.context import ContextContainer
from backend.database.db import execute_query
from backend.services.rag import get_rag_service
from backend.services.embedding import get_embedding_service
from backend.services.vision import get_vision_service
from backend.services.knowledge_base import get_knowledge_base_service
from backend.adapters.base import ModelAdapterFactory


class MasterAgent:
    """
    V2 MasterAgent — 统一调度入口。
    支持 4 种路由：
    - S1_S2_S3：有图片 + 有需求 → 图片理解 → 构图生成 → 整理优化
    - S2_S3：纯文字需求 → 构图生成 → 整理优化
    - S5_S3：视频/空镜头需求 → 视频空镜 → 整理优化
    - K1：分类请求 → 纯向量检索，无 LLM
    """

    def __init__(self):
        self.rag_service = get_rag_service()
        self.embedding_service = get_embedding_service()
        self.vision_service = get_vision_service()
        self.kb_service = get_knowledge_base_service()

    def process_request(
        self,
        image_path: Optional[str],
        text: str,
        user_id: int = 1,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        V2 统一入口。
        如果传入 session_id，则继续该会话；否则创建新会话。
        """
        start_time = time.time()

        try:
            user = self._get_user_preference(user_id)

            # 获取或创建 ContextContainer
            if session_id:
                context = self._load_session(session_id)
                if context is None:
                    context = self._new_context(session_id, user_id, image_path, text)
            else:
                context = self._new_context("", user_id, image_path, text)

            # 意图识别 + 路由决策
            route = self._decide_route(image_path, text, user)
            context.route = route

            # 根据路由执行 Agent 链
            result_prompt = self._execute_route(context, route, user)

            # 设置最终输出
            context.set_final(result_prompt)

            # 计算总耗时
            total_ms = int((time.time() - start_time) * 1000)
            context.total_duration_ms = total_ms

            # 保存 session
            self._save_session(context)

            return {
                "code": 0,
                "message": "生成成功",
                "data": {
                    "session_id": context.session_id,
                    "final_prompt": context.final_prompt,
                    "variants": context.variants,
                    "agent_chain": context.agent_chain,
                    "route": context.route,
                    "confidence": context.confidence,
                    "classified_category": context.classified_category,
                    "duration_ms": total_ms,
                }
            }

        except Exception as e:
            total_ms = int((time.time() - start_time) * 1000)
            return {
                "code": -1,
                "message": f"处理失败: {str(e)}",
                "data": None
            }

    def process_adjust(
        self,
        session_id: str,
        target_agent: str,
        user_instruction: str
    ) -> Dict[str, Any]:
        """
        V2 调整入口 — 用户对指定 Agent 的输出进行调整。
        找到该 Agent 的输出，重新生成，更新 ContextContainer。
        """
        start_time = time.time()

        try:
            context = self._load_session(session_id)
            if context is None:
                raise ValueError(f"会话不存在: {session_id}")

            user = self._get_user_preference(1)

            # 注入 master 调用方法到子 Agent
            master_call = lambda prompt, **kw: self._call_model_for_subagent(
                prompt, context=context, **kw
            )

            # 根据 target_agent 决定如何处理
            if target_agent == "S2":
                # 重新执行 S2
                from backend.agents.sub.s2_composition_gen import S2CompositionGenAgent
                agent = S2CompositionGenAgent()
                agent._master_call_model = master_call
                context.agent_outputs = [o for o in context.agent_outputs if o.agent_id != "S2"]
                context = agent.execute(context, user)
                # S2 重做 → S3 也需重做
                context.agent_outputs = [o for o in context.agent_outputs if o.agent_id != "S3"]

            elif target_agent == "S3":
                from backend.agents.sub.s3_organize import S3OrganizeAgent
                agent = S3OrganizeAgent()
                agent._master_call_model = master_call
                context.agent_outputs = [o for o in context.agent_outputs if o.agent_id != "S3"]

            elif target_agent == "S4":
                from backend.agents.sub.s4_style_extend import S4StyleExtendAgent
                agent = S4StyleExtendAgent()
                agent._master_call_model = master_call
                context.agent_outputs = [o for o in context.agent_outputs if o.agent_id != "S4"]
                context = agent.execute(context, user)
                return self._finalize_adjust(context, start_time, user_instruction)

            elif target_agent == "S1":
                from backend.agents.sub.s1_image_understand import S1ImageUnderstandAgent
                agent = S1ImageUnderstandAgent()
                context.agent_outputs = [o for o in context.agent_outputs if o.agent_id != "S1"]
                context = agent.execute(context, user)

            else:
                raise ValueError(f"不支持的 Agent: {target_agent}")

            # 继续执行 S3
            from backend.agents.sub.s3_organize import S3OrganizeAgent
            s3 = S3OrganizeAgent()
            s3._master_call_model = master_call
            context = s3.execute(context, user)

            return self._finalize_adjust(context, start_time, user_instruction)

        except Exception as e:
            return {
                "code": -1,
                "message": f"调整失败: {str(e)}",
                "data": None
            }

    def _finalize_adjust(
        self,
        context: ContextContainer,
        start_time: float,
        user_instruction: str
    ) -> Dict[str, Any]:
        """完成调整后返回"""
        total_ms = int((time.time() - start_time) * 1000)
        context.total_duration_ms = total_ms
        self._save_session(context)

        return {
            "code": 0,
            "message": "调整成功",
            "data": {
                "session_id": context.session_id,
                "final_prompt": context.final_prompt,
                "variants": context.variants,
                "agent_chain": context.agent_chain,
                "duration_ms": total_ms,
            }
        }

    # ─── 路由决策 ────────────────────────────────────────────

    def _decide_route(
        self,
        image_path: Optional[str],
        text: str,
        user: Dict[str, Any]
    ) -> str:
        """
        V2 路由决策逻辑。
        优先级：K1（分类）> S5（视频）> S1（有图）> S2（默认）
        """
        text_lower = text.lower()

        # K1：纯分类请求（高频操作，零成本）
        k1_keywords = ["分类", "归类", "属于哪种", "哪类", "category"]
        if any(kw in text for kw in k1_keywords):
            return "K1"

        # S5：视频/空镜头需求
        s5_keywords = ["视频", "空镜", "镜头", "video", "空镜头", "科技视频", "产品视频"]
        if any(kw in text_lower for kw in s5_keywords):
            return "S5_S3"

        # S1：有图片上传
        if image_path:
            return "S1_S2_S3"

        # 默认：纯文字 → S2
        return "S2_S3"

    def _execute_route(
        self,
        context: ContextContainer,
        route: str,
        user: Dict[str, Any]
    ) -> str:
        """
        根据路由执行对应的 Agent 链。
        每个子 Agent 需要注入 master 的 LLM 调用方法。
        """
        master_call = lambda prompt, **kw: self._call_model_for_subagent(
            prompt, context=context, **kw
        )

        if route == "K1":
            from backend.agents.sub.k1_classifier import K1ClassifierAgent
            agent = K1ClassifierAgent()
            context = agent.execute(context, user)
            # K1 不输出 prompt，仅分类
            return context.classified_category or "general"

        elif route == "S1_S2_S3":
            # S1 → S2 → S3
            from backend.agents.sub.s1_image_understand import S1ImageUnderstandAgent
            from backend.agents.sub.s2_composition_gen import S2CompositionGenAgent
            from backend.agents.sub.s3_organize import S3OrganizeAgent

            s1 = S1ImageUnderstandAgent()
            context = s1.execute(context, user)

            s2 = S2CompositionGenAgent()
            s2._master_call_model = master_call
            context = s2.execute(context, user)

            s3 = S3OrganizeAgent()
            s3._master_call_model = master_call
            context = s3.execute(context, user)

            s3_out = context.get_output("S3")
            return s3_out.output_text if s3_out else ""

        elif route == "S2_S3":
            from backend.agents.sub.s2_composition_gen import S2CompositionGenAgent
            from backend.agents.sub.s3_organize import S3OrganizeAgent

            s2 = S2CompositionGenAgent()
            s2._master_call_model = master_call
            context = s2.execute(context, user)

            s3 = S3OrganizeAgent()
            s3._master_call_model = master_call
            context = s3.execute(context, user)

            s3_out = context.get_output("S3")
            return s3_out.output_text if s3_out else ""

        elif route == "S5_S3":
            from backend.agents.sub.s5_video_shot import S5VideoShotAgent
            from backend.agents.sub.s3_organize import S3OrganizeAgent

            s5 = S5VideoShotAgent()
            s5._master_call_model = master_call
            context = s5.execute(context, user)

            s3 = S3OrganizeAgent()
            s3._master_call_model = master_call
            context = s3.execute(context, user)

            s3_out = context.get_output("S3")
            return s3_out.output_text if s3_out else ""

        else:
            raise ValueError(f"不支持的路由: {route}")

    # ─── LLM 调用 ────────────────────────────────────────────

    def _call_model_for_subagent(
        self,
        prompt: str,
        context: ContextContainer,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """供子 Agent 调用的 LLM 入口"""
        model = self._select_model("general")
        return self._call_model_with_config(
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def _select_model(self, scene: str) -> Dict[str, Any]:
        """从数据库选择最高优先级的可用模型"""
        rows = execute_query(
            "SELECT * FROM models WHERE enabled = 1 AND (scene = ? OR scene IS NULL) ORDER BY priority DESC LIMIT 1",
            (scene,),
            fetch_one=True
        )
        if rows:
            return dict(rows)

        rows = execute_query(
            "SELECT * FROM models WHERE enabled = 1 ORDER BY priority DESC LIMIT 1",
            fetch_one=True
        )
        if rows:
            return dict(rows)

        raise Exception("没有可用的模型配置，请先在模型配置中添加第三方大模型 API")

    def _decrypt_key(self, model: Dict[str, Any]) -> str:
        """解密 API Key"""
        try:
            if model.get("encryption_key"):
                fernet = Fernet(model["encryption_key"].encode())
                return fernet.decrypt(model["api_key_encrypted"].encode()).decode()
        except Exception:
            pass
        return model.get("api_key_encrypted", "")

    def _call_model_with_config(
        self,
        model: Dict[str, Any],
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """使用指定模型配置调用 LLM"""
        decrypted_key = self._decrypt_key(model)

        config = {
            "vendor": model["vendor"],
            "name": model["name"],
            "api_url": model["api_url"],
            "api_key": decrypted_key
        }

        adapter = ModelAdapterFactory.create(config)
        return adapter.call(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    # ─── Session 管理 ─────────────────────────────────────────

    def _new_context(
        self,
        session_id: str,
        user_id: int,
        image_path: Optional[str],
        text: str
    ) -> ContextContainer:
        ctx = ContextContainer(
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            user_input=text,
            image_path=image_path
        )
        # 获取 RAG 上下文
        ctx.rag_context = self._get_rag_context(text)
        return ctx

    def _get_rag_context(self, text: str) -> List[Dict[str, Any]]:
        if self.embedding_service._model is None:
            return []

        query_vector = self.embedding_service.embed_text(text)
        results = self.rag_service.search(query_vector, top_k=3, threshold=0.5)

        contexts = []
        for idx, score in results:
            row = execute_query(
                "SELECT * FROM prompts WHERE id = ?",
                (idx,),
                fetch_one=True
            )
            if row:
                contexts.append({
                    "id": row["id"],
                    "content": row["content"][:200],
                    "similarity": float(score)
                })
        return contexts

    def _save_session(self, context: ContextContainer):
        """保存或更新 session 到数据库"""
        # 尝试更新已有 session
        existing = execute_query(
            "SELECT id FROM sessions WHERE session_id = ?",
            (context.session_id,),
            fetch_one=True
        )
        if existing:
            execute_query(
                "UPDATE sessions SET context_json = ?, updated_at = ? WHERE session_id = ?",
                (context.serialize(), time.strftime("%Y-%m-%dT%H:%M:%S"), context.session_id)
            )
        else:
            execute_query(
                "INSERT INTO sessions (session_id, user_id, context_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (
                    context.session_id,
                    context.user_id,
                    context.serialize(),
                    context.created_at,
                    context.updated_at
                )
            )

    def _load_session(self, session_id: str) -> Optional[ContextContainer]:
        """从数据库加载 session"""
        row = execute_query(
            "SELECT context_json FROM sessions WHERE session_id = ?",
            (session_id,),
            fetch_one=True
        )
        if row:
            try:
                return ContextContainer.deserialize(row["context_json"])
            except Exception:
                return None
        return None

    def _get_user_preference(self, user_id: int) -> Dict[str, Any]:
        row = execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        if row:
            return dict(row)
        return {}
