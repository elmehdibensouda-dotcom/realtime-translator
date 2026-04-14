import sqlite3
import os
import logging
import hashlib

logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self, db_path="translations.db"):
        self.db_path = db_path
        self._memory_cache = {}  # In-memory hot cache
        self._max_mem_size = 1000
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
                # Optimization for SQLite speed
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
        except Exception as e:
            logger.error("Failed to initialize SQLite cache: %s", e)

    def get(self, text: str) -> str:
        text = text.strip().lower()
        
        # 1. Very fast memory lookup
        if text in self._memory_cache:
            return self._memory_cache[text]

        # 2. SQLite lookup
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT fr_text FROM cache WHERE en_text = ?", (text,))
                row = cursor.fetchone()
                if row:
                    res = row[0]
                    # Update memory cache
                    if len(self._memory_cache) < self._max_mem_size:
                        self._memory_cache[text] = res
                    return res
        except Exception as e:
            logger.error("Cache get error: %s", e)
        return None

    def set(self, en_text: str, fr_text: str):
        en_text = en_text.strip().lower()
        if not en_text or not fr_text: return

        # Update memory cache immediately
        self._memory_cache[en_text] = fr_text
        if len(self._memory_cache) > self._max_mem_size:
             # Very simple eviction
             self._memory_cache.pop(next(iter(self._memory_cache)))

        # Persistent update
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
