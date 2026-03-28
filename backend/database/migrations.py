import sqlite3
import os


def init_database():
    db_path = "data/prompts.db"
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
    
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (1, 'default')")
    
    conn.commit()
    conn.close()
    
    print(f"数据库初始化完成: {db_path}")


if __name__ == "__main__":
    init_database()
