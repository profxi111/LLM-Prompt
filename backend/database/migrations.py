import sqlite3
import os


def init_database():
    """
    初始化 SQLite 数据库，包含 V1 核心表 + V2 新增表。
    V2 新增：sessions、agent_model_overrides、knowledge_base_meta
    """
    db_path = "data/prompts.db"
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── V1 核心表 ──────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,
            tags TEXT,
            user_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vector_synced INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'default',
            style TEXT,
            keywords TEXT,
            tone TEXT,
            default_scene TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_key_encrypted TEXT NOT NULL,
            encryption_key TEXT,
            priority INTEGER DEFAULT 1,
            scene TEXT,
            enabled INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER DEFAULT 1,
            intent_result TEXT,
            agent_used TEXT,
            model_id INTEGER,
            duration_ms INTEGER,
            success INTEGER DEFAULT 1,
            error TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_key_encrypted TEXT NOT NULL,
            encryption_key TEXT,
            enabled INTEGER DEFAULT 1
        )
    """)

    # ── V2 新增表 ──────────────────────────────────────────

    # sessions 表：存储每个会话的完整 ContextContainer JSON
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER DEFAULT 1,
            context_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # agent_model_overrides 表：指定特定 Agent 使用的模型
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_model_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            agent_id TEXT NOT NULL,
            model_id INTEGER,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 2000,
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)

    # knowledge_base_meta 表：知识库元数据
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_version TEXT,
            last_rebuild_at TEXT,
            example_count INTEGER DEFAULT 0,
            dimension INTEGER DEFAULT 768,
            embedding_model TEXT DEFAULT 'm3e-small'
        )
    """)

    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (1, 'default')")

    conn.commit()
    conn.close()

    print(f"数据库初始化完成: {db_path}")


if __name__ == "__main__":
    init_database()
