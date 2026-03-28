from typing import Dict, Any, Optional, List
from backend.database.models import User


class EcommerceAgent:
    def generate_prompt(self, image_path: Optional[str], text: str, user: User, rag_context: List[Dict[str, Any]]) -> str:
        rag_examples = self._build_rag_examples(rag_context)
        
        prompt = f"""你是一个专业的电商提示词生成专家，擅长创作产品标题、卖点、详情页描述和营销文案。

用户需求: {text}
用户偏好: 风格={user.style}, 关键词={user.keywords}, 语气={user.tone}
参考示例:
{rag_examples}

请根据用户需求和偏好，生成专业的电商提示词，要求：
1. 标题简洁有力，突出产品核心卖点
2. 卖点提炼精准，直击用户痛点
3. 详情页描述详细，增强购买欲望
4. 营销文案有吸引力，促进转化

请按以下格式输出：

【产品标题】
...

【核心卖点】
1. ...
2. ...
3. ...

【详情页描述】
...

【营销文案】
..."""

        return prompt
    
    def _build_rag_examples(self, rag_context: List[Dict[str, Any]]) -> str:
        if not rag_context:
            return "暂无参考示例"
        
        examples = []
        for ctx in rag_context:
            examples.append(f"示例{ctx['id']} (相似度:{ctx['similarity']:.2f}): {ctx['content']}")
        
        return "\n".join(examples)
