import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, Optional, Tuple

_CACHE_LOCK = threading.RLock()


class PersistentProviderCache:
    """
    Persistent SQLite cache keyed strictly by (provider, language, voice, exact_text)
    for both TTS audio clips and grounded LLM responses.
    On first initialization (or if the SQLite DB is deleted on an ephemeral Render disk),
    automatically loads any committed pre-warmed audio assets from assets/prewarmed/
    with zero API calls.
    """

    def __init__(self, db_path: Path, prewarmed_dir: Optional[Path] = None) -> None:
        self.db_path = Path(db_path)
        self.prewarmed_dir = Path(prewarmed_dir) if prewarmed_dir is not None else None
        self._initialized = False

    def _ensure_db(self) -> None:
        if self._initialized and self.db_path.exists():
            return
        with _CACHE_LOCK:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS tts_cache (
                        cache_key TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        language TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        exact_text TEXT NOT NULL,
                        audio_base64 TEXT NOT NULL,
                        mime_type TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS llm_cache (
                        cache_key TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        language TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        exact_text TEXT NOT NULL,
                        response_text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.commit()
                self._initialized = True
            finally:
                conn.close()
            if self.prewarmed_dir is not None:
                self._seed_from_dir_unlocked(self.prewarmed_dir)

    def _seed_from_dir_unlocked(self, prewarmed_dir: Path) -> Dict[str, int]:
        """Load committed fixed-phrase audio entries into SQLite cache with zero API calls."""
        index_path = prewarmed_dir / "index.json"
        if not prewarmed_dir.is_dir() or not index_path.is_file():
            return {"seeded": 0, "already_present": 0}
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"seeded": 0, "already_present": 0}

        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list) or not entries:
            return {"seeded": 0, "already_present": 0}

        base_resolved = prewarmed_dir.resolve()
        seeded = 0
        already_present = 0
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        try:
            existing_keys = {
                str(r[0]) for r in conn.execute("SELECT cache_key FROM tts_cache").fetchall()
            }
            now_str = self._now_iso()
            for item in entries:
                if not isinstance(item, dict):
                    continue
                prov = str(item.get("provider", "")).strip()
                lang = str(item.get("language", "")).strip()
                voice = str(item.get("voice", "")).strip()
                exact_text = str(item.get("exact_text", ""))
                audio_rel = str(item.get("audio_file", "")).strip()
                mime = str(item.get("mime_type", "audio/wav")).strip() or "audio/wav"
                if not (prov and lang and voice and exact_text and audio_rel):
                    continue

                key = self.make_key(prov, lang, voice, exact_text)
                if key in existing_keys:
                    already_present += 1
                    continue

                audio_fp = (prewarmed_dir / audio_rel).resolve()
                if base_resolved not in audio_fp.parents or not audio_fp.is_file():
                    continue
                audio_b64 = base64.b64encode(audio_fp.read_bytes()).decode("ascii")
                conn.execute(
                    """
                    INSERT OR IGNORE INTO tts_cache
                    (cache_key, provider, language, voice, exact_text, audio_base64, mime_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (key, prov, lang, voice, exact_text, audio_b64, mime, now_str),
                )
                existing_keys.add(key)
                seeded += 1
            if seeded > 0:
                conn.commit()
        finally:
            conn.close()
        return {"seeded": seeded, "already_present": already_present}

    def seed_from_prewarmed_dir(self, prewarmed_dir: Optional[Path] = None) -> Dict[str, int]:
        self._ensure_db()
        target = Path(prewarmed_dir) if prewarmed_dir is not None else self.prewarmed_dir
        if target is None:
            return {"seeded": 0, "already_present": 0}
        with _CACHE_LOCK:
            return self._seed_from_dir_unlocked(target)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def make_key(provider: str, language: str, voice: str, exact_text: str) -> str:
        raw = f"{provider.strip()}|{language.strip()}|{voice.strip()}|{exact_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_tts(
        self, provider: str, language: str, voice: str, exact_text: str
    ) -> Optional[Tuple[str, str]]:
        self._ensure_db()
        key = self.make_key(provider, language, voice, exact_text)
        with _CACHE_LOCK:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                row = conn.execute(
                    "SELECT audio_base64, mime_type FROM tts_cache WHERE cache_key = ?",
                    (key,),
                ).fetchone()
                if row:
                    return str(row[0]), str(row[1])
                return None
            finally:
                conn.close()

    def put_tts(
        self,
        provider: str,
        language: str,
        voice: str,
        exact_text: str,
        audio_base64: str,
        mime_type: str = "audio/wav",
    ) -> None:
        self._ensure_db()
        key = self.make_key(provider, language, voice, exact_text)
        with _CACHE_LOCK:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tts_cache
                    (cache_key, provider, language, voice, exact_text, audio_base64, mime_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        provider.strip(),
                        language.strip(),
                        voice.strip(),
                        exact_text,
                        audio_base64,
                        mime_type,
                        self._now_iso(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def get_llm(self, provider: str, language: str, voice: str, exact_text: str) -> Optional[str]:
        self._ensure_db()
        key = self.make_key(provider, language, voice, exact_text)
        with _CACHE_LOCK:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                row = conn.execute(
                    "SELECT response_text FROM llm_cache WHERE cache_key = ?",
                    (key,),
                ).fetchone()
                return str(row[0]) if row else None
            finally:
                conn.close()

    def put_llm(
        self, provider: str, language: str, voice: str, exact_text: str, response_text: str
    ) -> None:
        self._ensure_db()
        key = self.make_key(provider, language, voice, exact_text)
        with _CACHE_LOCK:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO llm_cache
                    (cache_key, provider, language, voice, exact_text, response_text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        provider.strip(),
                        language.strip(),
                        voice.strip(),
                        exact_text,
                        response_text,
                        self._now_iso(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def stats(self) -> Dict[str, int]:
        self._ensure_db()
        with _CACHE_LOCK:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                tts_cnt = int(conn.execute("SELECT COUNT(*) FROM tts_cache").fetchone()[0])
                llm_cnt = int(conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0])
                return {
                    "tts_cached_count": tts_cnt,
                    "llm_cached_count": llm_cnt,
                    "total_cached_count": tts_cnt + llm_cnt,
                }
            finally:
                conn.close()
