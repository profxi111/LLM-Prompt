from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import urllib3
import json
import certifi

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ModelAdapter(ABC):
    """
    模型适配器基类。
    所有第三方大模型 API 适配器必须继承此类。
    """

    # 默认超时配置
    DEFAULT_CONNECT_TIMEOUT = 10  # 连接超时（秒）
    DEFAULT_READ_TIMEOUT = 60     # 读取超时（秒）

    def __init__(self, vendor: str, name: str, api_url: str, api_key: str):
        self.vendor = vendor
        self.name = name
        self.api_url = api_url
        self.api_key = api_key

    @abstractmethod
    def _build_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        构建请求体。
        子类必须实现，将 prompt 转换为对应 API 的请求格式。
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Dict[str, Any]) -> str:
        """
        解析响应。
        子类必须实现，从 API 响应中提取生成的文本。
        """
        pass

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        pass

    def call(self, prompt: str, **kwargs) -> str:
        """
        使用urllib3执行HTTP调用
        """
        try:
            print(f"DEBUG adapter.call: 开始, vendor={self.vendor}, url={self.api_url}")
            headers = self._get_headers()
            payload = self._build_request(prompt, **kwargs)
            print(f"DEBUG adapter.call: headers和payload构建完成")

            timeout = urllib3.Timeout(
                connect=self.DEFAULT_CONNECT_TIMEOUT,
                read=self.DEFAULT_READ_TIMEOUT
            )
            print(f"DEBUG adapter.call: 发送POST请求, timeout={timeout}")

            # 创建PoolManager，禁用SSL验证（仅用于测试）
            http = urllib3.PoolManager(
                cert_reqs='CERT_NONE',
                timeout=timeout
            )
            
            encoded_data = json.dumps(payload).encode('utf-8')
            response = http.request(
                'POST',
                self.api_url,
                body=encoded_data,
                headers=headers
            )
            
            print(f"DEBUG adapter.call: 响应收到, status={response.status}")
            
            if response.status != 200:
                raise Exception(f"{self.vendor} API HTTP 错误：{response.status} - {response.data.decode('utf-8')}")
                
            return self._parse_response(json.loads(response.data.decode('utf-8')))

        except urllib3.exceptions.TimeoutError:
            raise Exception(
                f"{self.vendor} API 请求超时（连接 {self.DEFAULT_CONNECT_TIMEOUT}s + "
                f"读取 {self.DEFAULT_READ_TIMEOUT}s）。"
                "请检查网络连接或模型服务状态。"
            )
        except urllib3.exceptions.ConnectionError as e:
            raise Exception(
                f"{self.vendor} API 连接失败：{str(e)}。"
                "请检查 API 地址是否正确，或网络是否可达。"
            )
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
        1. 优先使用用户配置的 vendor
        2. 如果未匹配，尝试使用别名映射
        3. 如果仍未匹配，尝试使用 name 字段推断
        """
        vendor = config.get("vendor", "").lower()

        # 1. 直接匹配
        if vendor in cls._adapters:
            return cls._adapters[vendor](
                vendor=vendor,
                name=config["name"],
                api_url=config["api_url"],
                api_key=config["api_key"]
            )

        # 2. 别名映射
        canonical = cls._ALIASES.get(vendor)
        if canonical and canonical in cls._adapters:
            return cls._adapters[canonical](
                vendor=canonical,
                name=config["name"],
                api_url=config["api_url"],
                api_key=config["api_key"]
            )

        # 3. 尝试从 name 推断 vendor
        name = config.get("name", "").lower()
        for alias, canonical in cls._ALIASES.items():
            if alias in name or name in alias:
                if canonical in cls._adapters:
                    return cls._adapters[canonical](
                        vendor=canonical,
                        name=config["name"],
                        api_url=config["api_url"],
                        api_key=config["api_key"]
                    )

        raise ValueError(f"不支持的模型厂商: {vendor}，请检查配置或注册对应的适配器")
