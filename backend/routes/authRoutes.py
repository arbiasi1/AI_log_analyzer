from fastapi import APIRouter, Depends

from backend.models.schemas import AuditEvent, AuthSession, LoginRequest, UserProfile
from backend.services.authService import get_audit_events, login, logout, require_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthSession)
async def login_route(request: LoginRequest):
    return login(request)


@router.get("/me", response_model=UserProfile)
async def me_route(user: UserProfile = Depends(require_user)):
    return user


@router.post("/logout")
async def logout_route(user: UserProfile = Depends(require_user)):
    return logout(user)


@router.get("/audit", response_model=list[AuditEvent])
async def audit_route(_: UserProfile = Depends(require_user)):
    return get_audit_events()
