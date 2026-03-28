# 提示词智能调度与生成工具

局域网专属的提示词智能生成与调度工具，支持图片+文字双输入，主Agent智能分发至电商/海报专项子Agent，全程无本地大模型、无显卡依赖，纯CPU+外部API运行。

## 功能特性

- 智能调度：主Agent自动识别用户意图，分发至对应专项子Agent
- 专项Agent：电商Agent（产品标题、卖点、详情页、营销文案）+ 海报Agent（构图、色彩、光影、风格、镜头、元素搭配）
- RAG检索：基于FAISS的语义向量检索，支持历史提示词复用
- 多模型支持：通义千问、DeepSeek、MiniMax等第三方大模型API
- 局域网部署：支持同一局域网内多设备访问
- 无显卡依赖：纯CPU运行，普通办公电脑即可使用

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3. 访问应用

- 本地访问：http://localhost:8000
- 局域网访问：http://[本机IP]:8000

## 使用说明

### 首次使用

1. 配置模型API：在"模型配置"页面添加第三方大模型API
   - 厂商：选择通义千问/DeepSeek/MiniMax
   - 模型名称：如 qwen-turbo
   - API地址：厂商提供的API端点
   - API Key：您的API密钥
   - 优先级：数字越大越优先

2. 设置个人偏好（可选）：在"个人偏好设置"页面配置常用风格、关键词等

### 生成提示词

1. 上传参考图片（可选）
2. 输入文字需求
3. 点击"生成提示词"
4. 查看生成结果，可复制或收藏

### RAG检索

- 在"RAG检索"页面输入关键词
- 系统会返回相似度最高的历史提示词

### 收藏管理

- 在生成结果页面点击"收藏"
- 在"我的收藏"页面查看所有收藏
- 支持删除收藏

## 项目结构

```
prompt-scheduler/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── adapters/            # 模型适配层
│   │   ├── base.py          # ModelAdapter 基类
│   │   ├── qwen.py         # 通义千问适配
│   │   ├── deepseek.py     # DeepSeek 适配
│   │   └── minimax.py      # MiniMax 适配
│   ├── agents/             # Agent 层
│   │   ├── master.py       # 主Agent
│   │   ├── ecommerce.py    # 电商专项Agent
│   │   └── poster.py       # 海报专项Agent
│   ├── services/           # 业务服务层
│   │   ├── rag.py          # RAG 检索服务
│   │   └── embedding.py    # 向量嵌入服务
│   ├── database/           # 数据层
│   │   ├── db.py           # SQLite 连接管理
│   │   ├── models.py       # ORM 模型定义
│   │   └── migrations.py   # 数据库初始化脚本
│   └── utils/
│       └── config.py       # 配置管理
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   ├── prompts.db          # SQLite 数据库文件
│   └── faiss_index/        # FAISS 向量库目录
├── uploads/                # 用户上传图片存储目录
└── requirements.txt
```

## API 接口

### 生成提示词
- POST /api/generate
- 参数：{ "image_path": "uploads/xxx.jpg", "text": "用户需求" }

### 上传图片
- POST /api/upload
- 参数：multipart/form-data file

### 收藏提示词
- POST /api/favorite
- 参数：{ "content": "提示词内容", "category": "ecommerce/poster" }

### 获取收藏列表
- GET /api/favorites

### 删除收藏
- DELETE /api/favorite/{id}

### RAG检索
- GET /api/search?q=关键词

### 用户偏好
- GET /api/user/preference
- PUT /api/user/preference

### 模型管理
- GET /api/models
- POST /api/models
- DELETE /api/models/{id}

## 技术栈

- 后端：Python + FastAPI
- 数据库：SQLite
- 向量库：FAISS-CPU
- 嵌入模型：sentence-transformers (m3e-small)
- 前端：原生HTML + CSS + JavaScript

## 系统要求

- Python 3.10+
- 4GB+ 内存
- 无显卡要求
- Windows/Linux/macOS

## 注意事项

1. 首次使用需要配置第三方大模型API
2. RAG检索需要先收藏一些提示词才能生效
3. sentence-transformers未安装时会使用简单哈希作为向量（功能可用但效果较差）
4. 建议安装sentence-transformers以获得更好的语义检索效果

## 许可证

MIT License
