from collections import deque
from contextvars import ContextVar
import hmac
import threading
import time
from typing import Deque, Dict, Optional, Set
from fastapi import Header, HTTPException, Request, status

from .config import get_settings

_CURRENT_SESSION_ID: ContextVar[str] = ContextVar("vyaparvoice_current_sid", default="")
_UNLOCK_LOCK = threading.RLock()
_DEMO_UNLOCKED_SESSIONS: Set[str] = set()
_PIN_FAIL_LOG: Dict[str, Deque[float]] = {}
_RATE_LOG: Dict[str, Deque[float]] = {}


def set_current_request_session(session_id: str) -> None:
    _CURRENT_SESSION_ID.set((session_id or "").strip())


def get_current_request_session() -> str:
    return _CURRENT_SESSION_ID.get() or ""


def is_session_demo_unlocked(session_id: Optional[str] = None) -> bool:
    settings = get_settings()
    if settings.demo_live_flag:
        return True
    sid = (session_id if session_id is not None else get_current_request_session()).strip()
    if not sid:
        return False
    with _UNLOCK_LOCK:
        return sid in _DEMO_UNLOCKED_SESSIONS


def unlock_session_with_demo_pin(session_id: str, provided_pin: str, client_ip: str = "unknown") -> bool:
    """
    Constant-time verification of DEMO_PIN from env var.
    Never logs or echoes provided_pin or settings.demo_pin.
    Includes brute-force lockout (max 5 failed attempts per 60s per IP).
    """
    settings = get_settings()
    expected = settings.demo_pin
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo PIN unlock is unavailable because DEMO_PIN is not configured on the server.",
        )

    now = time.monotonic()
    with _UNLOCK_LOCK:
        dq = _PIN_FAIL_LOG.setdefault(client_ip, deque())
        while dq and (now - dq[0]) > 60.0:
            dq.popleft()
        if len(dq) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed PIN attempts. Wait 60 seconds before retrying.",
            )

    candidate = (provided_pin or "").strip()
    if not candidate or not hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8")):
        with _UNLOCK_LOCK:
            _PIN_FAIL_LOG.setdefault(client_ip, deque()).append(now)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid demo PIN.",
        )

    sid = (session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session identifier.")
    with _UNLOCK_LOCK:
        _DEMO_UNLOCKED_SESSIONS.add(sid)
    return True


def lock_session_demo_mode(session_id: str) -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    with _UNLOCK_LOCK:
        _DEMO_UNLOCKED_SESSIONS.discard(sid)


def reset_security_state_for_tests() -> None:
    with _UNLOCK_LOCK:
        _DEMO_UNLOCKED_SESSIONS.clear()
        _PIN_FAIL_LOG.clear()
        _RATE_LOG.clear()


def extract_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return "local"


def enforce_ip_rate_limit(request: Request, bucket: str = "credit_api") -> None:
    """
    Sliding-window per-IP rate limiter for all endpoints capable of triggering
    credit-consuming or external provider calls.
    """
    settings = get_settings()
    limit = max(1, int(settings.rate_limit_per_minute))
    ip = extract_client_ip(request)
    key = f"{bucket}:{ip}"
    now = time.monotonic()
    with _UNLOCK_LOCK:
        dq = _RATE_LOG.setdefault(key, deque())
        while dq and (now - dq[0]) > 60.0:
            dq.popleft()
        if len(dq) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests/min per IP). Served safely without provider charges.",
            )
        dq.append(now)


def verify_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> bool:
    """
    Fail-closed verification for administrative / global-state endpoints.
    If ADMIN_TOKEN is unset or mismatched, reject with 403 Forbidden.
    """
    settings = get_settings()
    expected = settings.admin_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative actions are disabled because ADMIN_TOKEN is not configured.",
        )
    provided = (x_admin_token or "").strip()
    if not provided or not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Token header.",
        )
    return True


def assert_paid_calls_permitted(provider_name: str = "external provider", demo_unlocked: Optional[bool] = None) -> None:
    """
    Hard safeguard ensuring public Render deployments only invoke metered APIs
    when explicitly unlocked via DEMO_PIN or server-side DEMO_LIVE_UNLOCKED=true.
    """
    settings = get_settings()
    unlocked = is_session_demo_unlocked() if demo_unlocked is None else bool(demo_unlocked or settings.demo_live_flag)
    if settings.public_deploy and not unlocked:
        raise PermissionError(
            f"Live {provider_name} calls are blocked when PUBLIC_DEPLOY=true (unlock Demo Mode via DEMO_PIN in Technical View to enable live calls)."
        )
