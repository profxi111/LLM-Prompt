from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests


class ModelAdapter(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_url = config.get("api_url", "")
        self.api_key = config.get("api_key", "")
        self.vendor = config.get("vendor", "")
        self.name = config.get("name", "")
    
    @abstractmethod
    def _build_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def _parse_response(self, response: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        pass
    
    def call(self, prompt: str, **kwargs) -> str:
        try:
            print(f"DEBUG MiniMax: Calling {self.vendor} at {self.api_url}")
            headers = self._get_headers()
            payload = self._build_request(prompt, **kwargs)
            print(f"DEBUG MiniMax: Payload built, sending request...")

            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
            except requests.exceptions.Timeout:
                print(f"DEBUG MiniMax: Request TIMED OUT!")
                raise Exception(f"{self.vendor} API 请求超时")
            except requests.exceptions.RequestException as e:
                print(f"DEBUG MiniMax: RequestException: {e}")
                raise
            print(f"DEBUG MiniMax: Response received, status={response.status_code}")
            response.raise_for_status()

            result = self._parse_response(response.json())
            print(f"DEBUG MiniMax: Response parsed successfully")
            return result

        except requests.exceptions.RequestException as e:
            print(f"DEBUG MiniMax: RequestException: {e}")
            raise Exception(f"{self.vendor} API 调用失败: {str(e)}")
        except Exception as e:
            print(f"DEBUG MiniMax: Exception: {e}")
            raise Exception(f"{self.vendor} 处理响应失败: {str(e)}")
    
    def __repr__(self):
        return f"{self.__class__.__name__}(vendor={self.vendor}, name={self.name})"


class ModelAdapterFactory:
    _adapters = {}
    
    @classmethod
    def register(cls, vendor: str, adapter_class):
        cls._adapters[vendor] = adapter_class
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> ModelAdapter:
        vendor = config.get("vendor", "").lower()
        print(f"DEBUG ModelAdapterFactory.create: vendor={vendor}, available={list(cls._adapters.keys())}")
        adapter_class = cls._adapters.get(vendor)

        if adapter_class is None:
            raise ValueError(f"不支持的模型厂商: {vendor}")

        return adapter_class(config)
