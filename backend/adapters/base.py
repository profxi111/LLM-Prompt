from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests


class ModelAdapter(ABC):
    """
    模型适配器基类。
    V2 Fix：所有 requests 调用使用 (connect_timeout, read_timeout) 元组超时。
    """

    # 默认连接超时 10s，读超时 60s — 防止挂起
    DEFAULT_CONNECT_TIMEOUT = 10
    DEFAULT_READ_TIMEOUT = 60

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
        """
        V2 Fix：
        1. 使用元组超时 (connect, read) 替代单值 timeout
        2. 添加更明确的错误消息
        """
        try:
            headers = self._get_headers()
            payload = self._build_request(prompt, **kwargs)

            # V2 Fix: 分离连接超时和读取超时，防止挂起
            timeout = (
                self.DEFAULT_CONNECT_TIMEOUT,
                self.DEFAULT_READ_TIMEOUT
            )

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return self._parse_response(response.json())

        except requests.exceptions.Timeout:
            raise Exception(
                f"{self.vendor} API 请求超时（连接 {self.DEFAULT_CONNECT_TIMEOUT}s + "
                f"读取 {self.DEFAULT_READ_TIMEOUT}s）。"
                "请检查网络连接或模型服务状态。"
            )
        except requests.exceptions.ConnectionError as e:
            raise Exception(
                f"{self.vendor} API 连接失败：{str(e)}。"
                "请检查 API 地址是否正确，或网络是否可达。"
            )
        except requests.exceptions.HTTPError as e:
            raise Exception(f"{self.vendor} API HTTP 错误：{e}")
        except Exception as e:
            raise Exception(f"{self.vendor} 处理失败：{str(e)}")

    def __repr__(self):
        return f"{self.__class__.__name__}(vendor={self.vendor}, name={self.name})"


class ModelAdapterFactory:
    """
    模型适配器工厂。
    V2 Fix：vendor 匹配增加别名支持，防止因用户输入的厂商名称不匹配而失败。
    """

    _adapters: Dict[str, type] = {}

    # V2 新增：厂商别名映射（兼容不同写法的 vendor 名称）
    _ALIASES: Dict[str, str] = {
        # 通义千问
        "通义千问": "qwen",
        "qwen": "qwen",
        "阿里云": "qwen",
        "aliyun": "qwen",
        # DeepSeek
        "deepseek": "deepseek",
        "ds": "deepseek",
        # MiniMax
        "minimax": "minimax",
        "abab": "minimax",
    }

    @classmethod
    def register(cls, vendor: str, adapter_class: type):
        cls._adapters[vendor.lower()] = adapter_class

    @classmethod
    def create(cls, config: Dict[str, Any]) -> ModelAdapter:
        """
        V2 Fix：
        1. 通过别名映射将不同写法的 vendor 名称映射到注册的 key
        2. 找不到时尝试返回 QwenAdapter 作为默认兜底
        """
        raw_vendor = config.get("vendor", "")
        vendor_lower = raw_vendor.lower()

        # 尝试别名映射
        mapped = cls._ALIASES.get(vendor_lower, vendor_lower)
        adapter_class = cls._adapters.get(mapped)

        if adapter_class is None:
            # 最后兜底：返回 QwenAdapter（通用 OpenAI-compatible API）
            adapter_class = cls._adapters.get("qwen")

        if adapter_class is None:
            raise ValueError(
                f"不支持的模型厂商: {raw_vendor}。"
                f"已注册的厂商: {list(cls._adapters.keys())}。"
                "请在模型配置中使用 'qwen'、'deepseek' 或 'minimax' 作为厂商名。"
            )

        return adapter_class(config)
