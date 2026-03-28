from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import shutil
from cryptography.fernet import Fernet
from backend.database.migrations import init_database
from backend.database.db import execute_query
from backend.agents.master import MasterAgent
from backend.services.rag import get_rag_service
from backend.services.embedding import get_embedding_service

app = FastAPI(
    title="提示词智能调度与生成工具",
    description="局域网专属的提示词智能生成与调度工具",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("data/faiss_index", exist_ok=True)

init_database()

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    from fastapi.responses import HTMLResponse
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    return {
        "code": 0,
        "message": "服务运行正常",
        "data": {"status": "healthy"}
    }


class GenerateRequest(BaseModel):
    image_path: Optional[str] = None
    text: str


class FavoriteRequest(BaseModel):
    content: str
    category: Optional[str] = None


class UserPreferenceRequest(BaseModel):
    style: Optional[str] = None
    keywords: Optional[str] = None
    tone: Optional[str] = None
    default_scene: Optional[str] = None


class ModelRequest(BaseModel):
    vendor: str
    name: str
    api_url: str
    api_key: str
    priority: int = 1
    scene: Optional[str] = None


class VisionModelRequest(BaseModel):
    vendor: str
    name: str
    api_url: str
    api_key: str


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    file_extension = file.filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("uploads", new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "path": f"uploads/{new_filename}",
            "filename": new_filename
        }
    }


@app.post("/api/generate")
async def generate_prompt(request: GenerateRequest):
    try:
        master_agent = MasterAgent()
        result = master_agent.process_request(request.image_path, request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/favorite")
async def add_favorite(request: FavoriteRequest):
    try:
        prompt_id = execute_query(
            "INSERT INTO prompts (content, category, user_id) VALUES (?, ?, ?)",
            (request.content, request.category, 1)
        )
        
        embedding_service = get_embedding_service()
        vector = embedding_service.embed_text(request.content)
        
        rag_service = get_rag_service()
        rag_service.add_vector(vector)
        rag_service.save_index()
        
        execute_query(
            "UPDATE prompts SET vector_synced = 1 WHERE id = ?",
            (prompt_id,)
        )
        
        return {
            "code": 0,
            "message": "收藏成功",
            "data": {"id": prompt_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/favorites")
async def get_favorites():
    try:
        rows = execute_query(
            "SELECT * FROM prompts ORDER BY created_at DESC LIMIT 100",
            fetch_all=True
        )
        
        favorites = [
            {
                "id": row["id"],
                "content": row["content"],
                "category": row["category"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": favorites
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/favorite/{favorite_id}")
async def delete_favorite(favorite_id: int):
    try:
        execute_query(
            "DELETE FROM prompts WHERE id = ?",
            (favorite_id,)
        )
        
        rag_service = get_rag_service()
        
        rows = execute_query(
            "SELECT content FROM prompts WHERE vector_synced = 1",
            fetch_all=True
        )
        
        if rows:
            prompts = [row["content"] for row in rows]
            rag_service.rebuild_from_prompts(prompts)
        
        return {
            "code": 0,
            "message": "删除成功",
            "data": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_prompts(q: str):
    try:
        embedding_service = get_embedding_service()
        rag_service = get_rag_service()
        
        query_vector = embedding_service.embed_text(q)
        search_results = rag_service.search(query_vector, top_k=5, threshold=0.3)
        
        results = []
        for idx, score in search_results:
            row = execute_query(
                "SELECT * FROM prompts WHERE id = ?",
                (idx,),
                fetch_one=True
            )
            if row:
                results.append({
                    "id": row["id"],
                    "content": row["content"],
                    "category": row["category"],
                    "similarity": score,
                    "created_at": row["created_at"]
                })
        
        return {
            "code": 0,
            "message": "搜索成功",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/preference")
async def get_user_preference():
    try:
        row = execute_query(
            "SELECT * FROM users WHERE id = 1",
            fetch_one=True
        )
        
        if row:
            preference = {
                "style": row["style"],
                "keywords": row["keywords"],
                "tone": row["tone"],
                "default_scene": row["default_scene"]
            }
        else:
            preference = {
                "style": None,
                "keywords": None,
                "tone": None,
                "default_scene": None
            }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": preference
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/user/preference")
async def update_user_preference(request: UserPreferenceRequest):
    try:
        execute_query(
            """UPDATE users SET style = ?, keywords = ?, tone = ?, default_scene = ? WHERE id = 1""",
            (request.style, request.keywords, request.tone, request.default_scene)
        )
        
        return {
            "code": 0,
            "message": "保存成功",
            "data": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models")
async def get_models():
    try:
        rows = execute_query(
            "SELECT id, vendor, name, priority, scene, enabled FROM models ORDER BY priority DESC",
            fetch_all=True
        )
        
        models = [
            {
                "id": row["id"],
                "vendor": row["vendor"],
                "name": row["name"],
                "priority": row["priority"],
                "scene": row["scene"],
                "enabled": row["enabled"]
            }
            for row in rows
        ]
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": models
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models")
async def add_model(request: ModelRequest):
    try:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted_key = fernet.encrypt(request.api_key.encode()).decode()
        
        model_id = execute_query(
            """INSERT INTO models (vendor, name, api_url, api_key_encrypted, encryption_key, priority, scene, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (request.vendor, request.name, request.api_url, encrypted_key, key.decode(), request.priority, request.scene)
        )
        
        return {
            "code": 0,
            "message": "添加成功",
            "data": {"id": model_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int):
    try:
        execute_query(
            "DELETE FROM models WHERE id = ?",
            (model_id,)
        )
        
        return {
            "code": 0,
            "message": "删除成功",
            "data": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vision-models")
async def get_vision_models():
    try:
        rows = execute_query(
            "SELECT id, vendor, name, enabled FROM vision_models ORDER BY id DESC",
            fetch_all=True
        )
        
        models = [
            {
                "id": row["id"],
                "vendor": row["vendor"],
                "name": row["name"],
                "enabled": row["enabled"]
            }
            for row in rows
        ]
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": models
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vision-models")
async def add_vision_model(request: VisionModelRequest):
    try:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted_key = fernet.encrypt(request.api_key.encode()).decode()
        
        model_id = execute_query(
            """INSERT INTO vision_models (vendor, name, api_url, api_key_encrypted, encryption_key, enabled)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (request.vendor, request.name, request.api_url, encrypted_key, key.decode())
        )
        
        return {
            "code": 0,
            "message": "添加成功",
            "data": {"id": model_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/vision-models/{model_id}")
async def delete_vision_model(model_id: int):
    try:
        execute_query(
            "DELETE FROM vision_models WHERE id = ?",
            (model_id,)
        )
        
        return {
            "code": 0,
            "message": "删除成功",
            "data": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
