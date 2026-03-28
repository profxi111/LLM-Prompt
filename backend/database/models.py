from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Prompt:
    id: Optional[int] = None
    content: str = ""
    category: Optional[str] = None
    tags: Optional[str] = None
    user_id: int = 1
    created_at: Optional[datetime] = None
    vector_synced: int = 0


@dataclass
class User:
    id: int = 1
    name: str = "default"
    style: Optional[str] = None
    keywords: Optional[str] = None
    tone: Optional[str] = None
    default_scene: Optional[str] = None


@dataclass
class Model:
    id: Optional[int] = None
    vendor: str = ""
    name: str = ""
    api_url: str = ""
    api_key_encrypted: str = ""
    priority: int = 1
    scene: Optional[str] = None
    enabled: int = 1


@dataclass
class Log:
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    user_id: int = 1
    intent_result: Optional[str] = None
    agent_used: Optional[str] = None
    model_id: Optional[int] = None
    duration_ms: Optional[int] = None
    success: int = 1
    error: Optional[str] = None
