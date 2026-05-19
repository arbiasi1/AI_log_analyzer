import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.models.schemas import AuditEvent, AuthSession, LoginRequest, UserProfile


TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "28800"))
DEFAULT_EMAIL = os.getenv("ADMIN_EMAIL", "admin@devops.local")
DEFAULT_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_NAME = os.getenv("ADMIN_NAME", "DevOps Admin")
DEFAULT_TEAM = os.getenv("ADMIN_TEAM", "Platform Engineering")
SECRET = os.getenv("AUTH_SECRET", "dev-local-change-me")

security = HTTPBearer(auto_error=False)
_audit_events: list[AuditEvent] = []


def login(request: LoginRequest) -> AuthSession:
    email = request.email.strip().lower()
    if not _valid_credentials(email, request.password):
        record_audit("anonymous", "login_failed", f"Rejected login for {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user = _default_user()
    token = _create_token(user)
    record_audit(user.email, "login", "User signed in.")
    return AuthSession(access_token=token, expires_in=TOKEN_TTL_SECONDS, user=user)


def logout(user: UserProfile) -> dict[str, str]:
    record_audit(user.email, "logout", "User signed out.")
    return {"status": "ok"}


def get_audit_events() -> list[AuditEvent]:
    return list(reversed(_audit_events[-50:]))


def record_audit(actor: str, action: str, detail: str) -> None:
    _audit_events.append(AuditEvent(actor=actor, action=action, detail=detail))
    del _audit_events[:-100]


async def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> UserProfile:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return _verify_token(credentials.credentials)


def _valid_credentials(email: str, password: str) -> bool:
    return hmac.compare_digest(email, DEFAULT_EMAIL.lower()) and hmac.compare_digest(
        password,
        DEFAULT_PASSWORD,
    )


def _default_user() -> UserProfile:
    return UserProfile(
        email=DEFAULT_EMAIL.lower(),
        name=DEFAULT_NAME,
        role="admin",
        team=DEFAULT_TEAM,
    )


def _create_token(user: UserProfile) -> str:
    payload = {
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "team": user.team,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    encoded_payload = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def _verify_token(token: str) -> UserProfile:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise _auth_error("Invalid authentication token.") from exc

    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise _auth_error("Invalid authentication token.")

    try:
        payload = json.loads(_unb64(encoded_payload).decode("utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _auth_error("Invalid authentication token.") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise _auth_error("Session expired. Please sign in again.")

    return UserProfile(
        email=payload["email"],
        name=payload["name"],
        role=payload["role"],
        team=payload["team"],
    )


def _sign(encoded_payload: str) -> str:
    digest = hmac.new(SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
