from typing import Dict, Any
from backend.adapters.base import ModelAdapter, ModelAdapterFactory


class DeepSeekAdapter(ModelAdapter):
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = kwargs.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": prompt}]
        
        return {
            "model": self.name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "stream": False
        }
    
    def _parse_response(self, response: Dict[str, Any]) -> str:
        try:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            return ""
        except (KeyError, IndexError):
            raise ValueError("DeepSeek API 响应格式异常")


ModelAdapterFactory.register("deepseek", DeepSeekAdapter)
ModelAdapterFactory.register("deepseek", DeepSeekAdapter)
