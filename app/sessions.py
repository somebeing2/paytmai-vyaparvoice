import re
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import get_settings
from .database import init_and_seed_db, release_db_lock, use_db_path

_VALID_SID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_SESSION_LOCK = threading.RLock()
_SESSION_LAST_SEEN: Dict[str, float] = {}


def sanitize_or_create_session_id(raw_sid: str = "") -> Tuple[str, bool]:
    candidate = (raw_sid or "").strip()
    if candidate and _VALID_SID_RE.match(candidate):
        return candidate, False
    return secrets.token_hex(12), True


def get_session_db_path(session_id: str) -> Path:
    settings = get_settings()
    storage_dir = settings.session_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"sess_{session_id}.db"


def _delete_session_files(storage_dir: Path, sid: str) -> bool:
    """Delete sess_<sid>.db plus any SQLite journal/WAL sidecars and release RLock."""
    db_file = storage_dir / f"sess_{sid}.db"
    removed = False
    for suffix in ("", "-journal", "-wal", "-shm"):
        candidate = Path(str(db_file) + suffix)
        if candidate.exists():
            try:
                candidate.unlink()
                if suffix == "":
                    removed = True
            except OSError:
                pass
    release_db_lock(str(db_file))
    return removed


def _sync_disk_sessions(storage_dir: Path) -> None:
    """Ensure any sess_*.db files already on disk are tracked in _SESSION_LAST_SEEN."""
    if not storage_dir.exists():
        return
    for db_file in storage_dir.glob("sess_*.db"):
        sid = db_file.stem[len("sess_"):]
        if sid and sid not in _SESSION_LAST_SEEN:
            try:
                _SESSION_LAST_SEEN[sid] = db_file.stat().st_mtime
            except OSError:
                pass


def _session_file_bytes(storage_dir: Path, sid: str) -> int:
    total = 0
    base = storage_dir / f"sess_{sid}.db"
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(str(base) + suffix)
        if p.exists():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def evict_stale_sessions(now_ts: float = None, protect_sid: str = "") -> int:
    """
    Enforces all three Render free-tier safeguards under _SESSION_LOCK:
      1. TTL expiry (now_ts - last_seen > session_ttl_seconds).
      2. Per-session SQLite size limit (file_bytes > max_session_db_bytes).
      3. Maximum active session count (LRU evict oldest when count > max_active_sessions).
      4. Total session directory disk limit (LRU evict oldest when sum(bytes) > max_total_sessions_bytes).
    """
    settings = get_settings()
    storage_dir = settings.session_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    now_val = now_ts if now_ts is not None else time.time()
    ttl = settings.session_ttl_seconds
    max_sessions = max(1, settings.max_active_sessions)
    max_db_bytes = max(65536, settings.max_session_db_bytes)
    max_total_bytes = max(max_db_bytes, settings.max_total_sessions_bytes)
    removed = 0

    with _SESSION_LOCK:
        _sync_disk_sessions(storage_dir)

        # 1. Evict TTL-expired sessions
        expired = [sid for sid, seen in list(_SESSION_LAST_SEEN.items()) if (now_val - seen) > ttl]
        for sid in expired:
            _SESSION_LAST_SEEN.pop(sid, None)
            if _delete_session_files(storage_dir, sid):
                removed += 1

        # 2. Evict any individual session DB exceeding max_session_db_bytes
        for sid in list(_SESSION_LAST_SEEN.keys()):
            if _session_file_bytes(storage_dir, sid) > max_db_bytes:
                _SESSION_LAST_SEEN.pop(sid, None)
                if _delete_session_files(storage_dir, sid):
                    removed += 1

        # 3. Evict oldest sessions (LRU) when count > max_active_sessions
        if len(_SESSION_LAST_SEEN) > max_sessions:
            ordered = sorted(
                _SESSION_LAST_SEEN.items(),
                key=lambda kv: (1 if kv[0] == protect_sid else 0, kv[1]),
            )
            excess = len(_SESSION_LAST_SEEN) - max_sessions
            for sid, _ in ordered[:excess]:
                _SESSION_LAST_SEEN.pop(sid, None)
                if _delete_session_files(storage_dir, sid):
                    removed += 1

        # 4. Evict oldest sessions (LRU) when aggregate bytes > max_total_sessions_bytes
        sizes = {sid: _session_file_bytes(storage_dir, sid) for sid in _SESSION_LAST_SEEN}
        total_bytes = sum(sizes.values())
        if total_bytes > max_total_bytes:
            ordered = sorted(
                _SESSION_LAST_SEEN.items(),
                key=lambda kv: (1 if kv[0] == protect_sid else 0, kv[1]),
            )
            for sid, _ in ordered:
                if total_bytes <= max_total_bytes:
                    break
                if sid == protect_sid and len(_SESSION_LAST_SEEN) == 1:
                    break
                _SESSION_LAST_SEEN.pop(sid, None)
                freed = sizes.get(sid, 0)
                if _delete_session_files(storage_dir, sid):
                    removed += 1
                    total_bytes -= freed

    return removed


def reset_session_tracker() -> None:
    """Test helper to clear in-memory session timestamps."""
    with _SESSION_LOCK:
        _SESSION_LAST_SEEN.clear()


def active_session_summary() -> Dict[str, object]:
    settings = get_settings()
    storage_dir = settings.session_storage_dir
    with _SESSION_LOCK:
        _sync_disk_sessions(storage_dir)
        count = len(_SESSION_LAST_SEEN)
        total_bytes = sum(_session_file_bytes(storage_dir, sid) for sid in _SESSION_LAST_SEEN)
    return {
        "isolate_visitors": settings.isolate_visitors,
        "active_sessions": count,
        "max_active_sessions": settings.max_active_sessions,
        "ttl_seconds": settings.session_ttl_seconds,
        "total_disk_bytes": total_bytes,
        "max_session_db_bytes": settings.max_session_db_bytes,
        "max_total_sessions_bytes": settings.max_total_sessions_bytes,
    }


class SessionIsolationMiddleware(BaseHTTPMiddleware):
    """
    Gives each visitor/browser tab an isolated SQLite sandbox bounded by TTL,
    maximum session count (LRU eviction), per-DB size limit, and total disk cap.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        path = request.url.path

        if path.startswith("/static") or not settings.isolate_visitors:
            return await call_next(request)

        raw_sid = (
            request.headers.get(settings.session_header_name)
            or request.cookies.get(settings.session_cookie_name)
            or ""
        )
        sid, created = sanitize_or_create_session_id(raw_sid)
        db_path = get_session_db_path(sid)

        with _SESSION_LOCK:
            evict_stale_sessions(protect_sid=sid)
            _SESSION_LAST_SEEN[sid] = time.time()
            if not db_path.exists():
                with use_db_path(str(db_path)):
                    init_and_seed_db(force_reset=False)
                evict_stale_sessions(protect_sid=sid)

        request.state.demo_session_id = sid
        with use_db_path(str(db_path)):
            response = await call_next(request)

        # Post-request guard in case a mutation grew the DB past max_session_db_bytes
        with _SESSION_LOCK:
            if _session_file_bytes(settings.session_storage_dir, sid) > settings.max_session_db_bytes:
                _delete_session_files(settings.session_storage_dir, sid)
                with use_db_path(str(db_path)):
                    init_and_seed_db(force_reset=False)

        response.headers[settings.session_header_name] = sid
        if created or request.cookies.get(settings.session_cookie_name) != sid:
            response.set_cookie(
                key=settings.session_cookie_name,
                value=sid,
                max_age=settings.session_ttl_seconds,
                httponly=True,
                samesite="lax",
            )
        return response
