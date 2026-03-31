from typing import Dict, Any, Optional
from backend.database.db import execute_query
from backend.adapters.vision.base import VisionAdapterFactory


class VisionService:
    def __init__(self):
        self.adapter = self._load_vision_adapter()
    
    def describe(self, image_path: str) -> str:
        if not image_path:
            return ""
        
        if not self.adapter:
            raise Exception("没有配置视觉模型，请先在视觉模型配置中添加")
        
        return self.adapter.describe(image_path)
    
    def _load_vision_adapter(self) -> Optional[VisionAdapter]:
        row = execute_query(
            "SELECT * FROM vision_models WHERE enabled = 1 ORDER BY id DESC LIMIT 1",
            fetch_one=True
        )
        
        if row:
            config = {
                "vendor": row["vendor"],
                "name": row["name"],
                "api_url": row["api_url"],
                "api_key": row["api_key_encrypted"]
            }
            return VisionAdapterFactory.create(config)
        
        return None


_vision_service_instance = None

def get_vision_service() -> VisionService:
    global _vision_service_instance
    if _vision_service_instance is None:
        _vision_service_instance = VisionService()
    return _vision_service_instance
