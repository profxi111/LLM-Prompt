from typing import Dict, Any
from backend.adapters.base import ModelAdapter, ModelAdapterFactory


class MiniMaxAdapter(ModelAdapter):
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        return headers

    def _build_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = kwargs.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        return {
            "model": self.name,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "messages": messages
        }

    def _parse_response(self, response: Dict[str, Any]) -> str:
        print(f"DEBUG MiniMax _parse_response: input={response}")
        try:
            content = response.get("content", [])
            print(f"DEBUG MiniMax: content={content}")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        result = item.get("text", "")
                        print(f"DEBUG MiniMax: extracted text={result[:50]}")
                        return result
            print("DEBUG MiniMax: No text found in content")
            return ""
        except (KeyError, IndexError, TypeError) as e:
            print(f"DEBUG MiniMax: Parse error: {e}")
            raise ValueError("MiniMax API 响应格式异常")


ModelAdapterFactory.register("minimax", MiniMaxAdapter)
