from typing import Dict, Any, Optional, List
import json
import time
from cryptography.fernet import Fernet
from backend.database.db import execute_query
from backend.database.models import User, Model
from backend.services.rag import get_rag_service
from backend.services.embedding import get_embedding_service
from backend.services.vision import get_vision_service
from backend.adapters.base import ModelAdapterFactory


class MasterAgent:
    def __init__(self):
        self.rag_service = get_rag_service()
        self.embedding_service = get_embedding_service()
        self.vision_service = get_vision_service()
    
    def process_request(self, image_path: Optional[str], text: str, user_id: int = 1) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            user = self._get_user_preference(user_id)
            
            rag_context = self._get_rag_context(text)
            
            intent_result = self._identify_intent(image_path, text, user, rag_context)
            
            scene = intent_result.get("scene", "other")
            confidence = intent_result.get("confidence", 0.0)
            
            if confidence < 0.7:
                return {
                    "code": -1,
                    "message": "意图识别置信度不足，请明确您的需求类型",
                    "data": {
                        "intent_result": intent_result,
                        "suggested_scenes": ["ecommerce", "poster"]
                    }
                }
            
            model = self._select_model(scene)
            
            if scene == "ecommerce":
                from backend.agents.ecommerce import EcommerceAgent
                agent = EcommerceAgent()
            elif scene == "poster":
                from backend.agents.poster import PosterAgent
                agent = PosterAgent()
            else:
                return {
                    "code": -1,
                    "message": "暂不支持该场景",
                    "data": {"scene": scene}
                }
            
            prompt = agent.generate_prompt(image_path, text, user, rag_context)
            
            result = self._call_model(model, prompt)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self._log_request(
                user_id=user_id,
                intent_result=json.dumps(intent_result, ensure_ascii=False),
                agent_used=agent.__class__.__name__,
                model_id=model["id"],
                duration_ms=duration_ms,
                success=1
            )
            
            return {
                "code": 0,
                "message": "生成成功",
                "data": {
                    "prompt": result,
                    "scene": scene,
                    "confidence": confidence,
                    "model_used": model["name"],
                    "duration_ms": duration_ms
                }
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_request(
                user_id=user_id,
                intent_result="",
                agent_used="",
                model_id=None,
                duration_ms=duration_ms,
                success=0,
                error=str(e)
            )
            
            return {
                "code": -1,
                "message": f"处理失败: {str(e)}",
                "data": None
            }
    
    def _get_user_preference(self, user_id: int) -> User:
        row = execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        
        if row:
            return User(
                id=row["id"],
                name=row["name"],
                style=row["style"],
                keywords=row["keywords"],
                tone=row["tone"],
                default_scene=row["default_scene"]
            )
        
        return User()
    
    def _get_rag_context(self, text: str) -> List[Dict[str, Any]]:
        query_vector = self.embedding_service.embed_text(text)
        search_results = self.rag_service.search(query_vector, top_k=3, threshold=0.5)
        
        contexts = []
        for idx, score in search_results:
            row = execute_query(
                "SELECT * FROM prompts WHERE id = ?",
                (idx,),
                fetch_one=True
            )
            if row:
                contexts.append({
                    "id": row["id"],
                    "content": row["content"],
                    "category": row["category"],
                    "similarity": score
                })
        
        return contexts
    
    def _identify_intent(self, image_path: Optional[str], text: str, user: User, rag_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        image_description = ""
        if image_path:
            try:
                image_description = self.vision_service.describe(image_path)
            except Exception as e:
                print(f"视觉模型调用失败: {e}")
                image_description = ""
        
        context_text = "\n".join([f"参考{c['category']}提示词: {c['content']}" for c in rag_context])
        
        prompt = f"""你是一个意图识别助手，需要判断用户的需求属于哪个场景。

用户需求: {text}
用户偏好: 风格={user.style}, 关键词={user.keywords}, 默认场景={user.default_scene}
参考提示词: {context_text}"""
        
        if image_description:
            prompt += f"""
图片描述: {image_description}"""
        
        prompt += """
请判断用户需求属于以下哪个场景:
- ecommerce: 电商相关，如产品标题、卖点、详情页、营销文案等
- poster: 海报设计相关，如构图、色彩、光影、风格、镜头、元素搭配等
- other: 其他场景

请以JSON格式返回，包含以下字段:
{{
  "scene": "ecommerce|poster|other",
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}"""
        
        model = self._select_model("general")
        
        try:
            result = self._call_model(model, prompt)
            
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                intent_data = json.loads(json_str)
                
                if "scene" in intent_data:
                    return intent_data
        except Exception as e:
            print(f"意图识别失败: {e}")
        
        return {
            "scene": "other",
            "confidence": 0.0,
            "reason": "意图识别失败，使用默认值"
        }
    
    def _select_model(self, scene: str) -> Dict[str, Any]:
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
        
        raise Exception("没有可用的模型配置，请先在模型配置中添加第三方大模型API")
    
    def _call_model(self, model: Dict[str, Any], prompt: str) -> str:
        try:
            if model.get("encryption_key"):
                fernet = Fernet(model["encryption_key"].encode())
                decrypted_key = fernet.decrypt(model["api_key_encrypted"].encode()).decode()
            else:
                decrypted_key = model["api_key_encrypted"]
        except Exception as e:
            print(f"解密API密钥失败: {e}")
            decrypted_key = model["api_key_encrypted"]
        
        config = {
            "vendor": model["vendor"],
            "name": model["name"],
            "api_url": model["api_url"],
            "api_key": decrypted_key
        }
        
        adapter = ModelAdapterFactory.create(config)
        return adapter.call(prompt)
    
    def _log_request(self, user_id: int, intent_result: str, agent_used: str, model_id: Optional[int], duration_ms: int, success: int, error: Optional[str] = None):
        execute_query(
            """INSERT INTO logs (user_id, intent_result, agent_used, model_id, duration_ms, success, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, intent_result, agent_used, model_id, duration_ms, success, error)
        )
