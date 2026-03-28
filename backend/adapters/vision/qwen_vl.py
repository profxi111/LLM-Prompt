from typing import Dict, Any
import base64
import requests
from backend.adapters.vision.base import VisionAdapter


class QwenVLAdapter(VisionAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.api_url = config["api_url"]
        self.api_key = config["api_key"]
    
    def describe(self, image_path: str) -> str:
        full_path = os.path.join(os.getcwd(), image_path)
        
        with open(full_path, "rb") as f:
            image_data = f.read()
        
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "qwen-vl-max",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{image_base64}"
                            },
                            {
                                "type": "text",
                                "text": "请用中文详细描述这张图片的内容，包括主要元素、颜色、风格、构图等信息。"
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(self.api_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", [{}])[0].get("text", "")
            return content
        else:
            raise Exception(f"视觉模型调用失败: {response.status_code}, {response.text}")
