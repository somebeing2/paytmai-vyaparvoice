import os
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
from .database import init_and_seed_db, use_db_path

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


def evict_stale_sessions(now_ts: float = None) -> int:
    settings = get_settings()
    now_val = now_ts if now_ts is not None else time.time()
    ttl = settings.session_ttl_seconds
    max_sessions = settings.max_active_sessions
    removed = 0

    with _SESSION_LOCK:
        expired = [sid for sid, seen in _SESSION_LAST_SEEN.items() if (now_val - seen) > ttl]
        for sid in expired:
            _SESSION_LAST_SEEN.pop(sid, None)
            db_file = settings.session_storage_dir / f"sess_{sid}.db"
            if db_file.exists():
                try:
                    db_file.unlink()
                    removed += 1
                except OSError:
                    pass

        if len(_SESSION_LAST_SEEN) > max_sessions:
            oldest = sorted(_SESSION_LAST_SEEN.items(), key=lambda kv: kv[1])[
                : len(_SESSION_LAST_SEEN) - max_sessions
            ]
            for sid, _ in oldest:
                _SESSION_LAST_SEEN.pop(sid, None)
                db_file = settings.session_storage_dir / f"sess_{sid}.db"
                if db_file.exists():
                    try:
                        db_file.unlink()
                        removed += 1
                    except OSError:
                        pass
    return removed


def active_session_summary() -> Dict[str, object]:
    settings = get_settings()
    with _SESSION_LOCK:
        count = len(_SESSION_LAST_SEEN)
    return {
        "isolate_visitors": settings.isolate_visitors,
        "active_sessions": count,
        "max_active_sessions": settings.max_active_sessions,
        "ttl_seconds": settings.session_ttl_seconds,
    }


class SessionIsolationMiddleware(BaseHTTPMiddleware):
    """
    Gives each visitor/browser tab an isolated SQLite sandbox so concurrent
    judges or public Render visitors never overwrite one another's demo state.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        path = request.url.path

        # Static assets do not touch SQLite
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
            evict_stale_sessions()
            _SESSION_LAST_SEEN[sid] = time.time()
            needs_init = not db_path.exists()
            if needs_init:
                with use_db_path(str(db_path)):
                    init_and_seed_db(force_reset=False)

        request.state.demo_session_id = sid
        with use_db_path(str(db_path)):
            response = await call_next(request)

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
