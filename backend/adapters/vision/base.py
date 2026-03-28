from abc import ABC, abstractmethod
from typing import Dict, Any
import base64
import os


class VisionAdapter(ABC):
    @abstractmethod
    def describe(self, image_path: str) -> str:
        pass


class VisionAdapterFactory:
    _adapters = {}
    
    @classmethod
    def register(cls, vendor: str, adapter_class):
        cls._adapters[vendor] = adapter_class
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> VisionAdapter:
        vendor = config.get("vendor", "").lower()
        adapter_class = cls._adapters.get(vendor)
        if adapter_class is None:
            raise ValueError(f"不支持的视觉模型厂商: {vendor}")
        return adapter_class(config)
