import sqlite3
import os
import logging
import hashlib

logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self, db_path="translations.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        id TEXT PRIMARY KEY,
                        en_text TEXT,
                        fr_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_en_text ON cache(en_text)")
        except Exception as e:
            logger.error("Failed to initialize SQLite cache: %s", e)

    def get(self, text: str) -> str:
        text = text.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT fr_text FROM cache WHERE en_text = ?", (text,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error("Cache get error: %s", e)
            return None

    def set(self, en_text: str, fr_text: str):
        en_text = en_text.strip().lower()
        # On utilise un hash pour l'ID unique
        entry_id = hashlib.md5(en_text.encode()).hexdigest()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (id, en_text, fr_text) VALUES (?, ?, ?)",
                    (entry_id, en_text, fr_text)
                )
        except Exception as e:
            logger.error("Cache set error: %s", e)

# Singleton global instance
db_file = os.path.join(os.getcwd(), "translations_cache.db")
translation_cache = TranslationCache(db_file)
