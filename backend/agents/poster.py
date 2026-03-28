from typing import Dict, Any, Optional, List
from backend.database.models import User


class PosterAgent:
    def generate_prompt(self, image_path: Optional[str], text: str, user: User, rag_context: List[Dict[str, Any]]) -> str:
        rag_examples = self._build_rag_examples(rag_context)
        
        image_hint = ""
        if image_path:
            image_hint = f"\n参考图片: {image_path}"
        
        prompt = f"""你是一个专业的海报设计提示词生成专家，擅长创作构图、色彩、光影、风格、镜头、元素搭配等设计类提示词。

用户需求: {text}{image_hint}
用户偏好: 风格={user.style}, 关键词={user.keywords}, 语气={user.tone}
参考示例:
{rag_examples}

请根据用户需求和偏好，生成专业的海报设计提示词，要求：
1. 构图清晰，层次分明
2. 色彩搭配和谐，符合主题氛围
3. 光影效果自然，增强视觉冲击力
4. 风格统一，符合设计美学
5. 镜头语言专业，突出重点
6. 元素搭配合理，不显杂乱

请按以下格式输出：

【主体描述】
...

【色彩建议】
...

【构图方式】
...

【光影氛围】
...

【风格定位】
...

【镜头语言】
...

【元素搭配】
..."""

        return prompt
    
    def _build_rag_examples(self, rag_context: List[Dict[str, Any]]) -> str:
        if not rag_context:
            return "暂无参考示例"
        
        examples = []
        for ctx in rag_context:
            examples.append(f"示例{ctx['id']} (相似度:{ctx['similarity']:.2f}): {ctx['content']}")
        
        return "\n".join(examples)
