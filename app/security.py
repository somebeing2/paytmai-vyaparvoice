import hmac
from typing import Optional
from fastapi import Header, HTTPException, status

from .config import get_settings


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


def assert_paid_calls_permitted(provider_name: str = "external provider") -> None:
    """
    Hard safeguard ensuring public Render deployments never invoke metered APIs.
    """
    settings = get_settings()
    if settings.public_deploy:
        raise PermissionError(
            f"Live {provider_name} calls are blocked when PUBLIC_DEPLOY=true."
        )
