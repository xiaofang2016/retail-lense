"""Sign-up, token login, refresh, logout, and login history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status

from api.dependencies import get_current_user
from core.exceptions import IpBlockedForUser, IpRestricted, UserLockedOut
from core.security.request_ip import client_ip
from core.security.tokens import create_access_token
from core.settings import get_settings
from schema.auth import (
    BlockedIpList,
    BlockedIpOut,
    BlockIpIn,
    CredentialsRequest,
    CreateUserRegistration,
    LoginHistoryList,
    LoginHistoryOut,
    TokenResponse,
)
from schema.user import UserOut, UserRecord
from services.auth_service import AuthService
from services.registration import RegistrationService

router = APIRouter()


def _token_or_raise(username: str, password: str, remember_me: bool, ip: str, user_agent: str) -> str:
    try:
        return AuthService().authenticate(username, password, remember_me, ip, user_agent)
    except UserLockedOut as exc:
        raise HTTPException(status.HTTP_423_LOCKED, detail="User is locked out") from exc
    except IpBlockedForUser as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This IP is blocked for this account") from exc
    except IpRestricted as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed logins from this IP") from exc
    except LookupError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password") from exc


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_new_user(data: CreateUserRegistration) -> UserOut:
    if not get_settings().allow_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User registration is disabled")
    return RegistrationService().register_user(data)


@router.post("/token")
def get_token(
    request: Request,
    username: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    remember_me: Annotated[bool, Form()] = False,
):
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    token = _token_or_raise(username, password, remember_me, ip, user_agent)
    return TokenResponse.respond(token)


@router.post("/signin")
def signin_json(request: Request, data: CredentialsRequest):
    """JSON alias of POST /auth/token for non-form clients."""
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    token = _token_or_raise(data.username, data.password, data.remember_me, ip, user_agent)
    return TokenResponse.respond(token)


@router.post("/refresh")
def refresh_token(current_user: UserRecord = Depends(get_current_user)):
    return TokenResponse.respond(create_access_token(current_user.user_id))


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("retaillen.access_token")
    return {"message": "logged out"}


@router.get("/login-history", response_model=LoginHistoryList)
def login_history(
    current_user: UserRecord = Depends(get_current_user),
    limit: int = 50,
) -> LoginHistoryList:
    events = AuthService().list_history(current_user.user_id, limit=limit)
    return LoginHistoryList(items=[LoginHistoryOut.model_validate(event.model_dump()) for event in events])


@router.get("/blocked-ips", response_model=BlockedIpList)
def list_blocked_ips(current_user: UserRecord = Depends(get_current_user)) -> BlockedIpList:
    ips = AuthService().list_blocked_ips(current_user)
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in ips])


@router.post("/blocked-ips", response_model=BlockedIpList)
def block_ip(body: BlockIpIn, current_user: UserRecord = Depends(get_current_user)) -> BlockedIpList:
    service = AuthService()
    try:
        user = service.block_ip(current_user, body.ip)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid IP") from exc
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in user.blocked_ips])


@router.delete("/blocked-ips", response_model=BlockedIpList)
def unblock_ip(body: BlockIpIn, current_user: UserRecord = Depends(get_current_user)) -> BlockedIpList:
    service = AuthService()
    try:
        user = service.unblock_ip(current_user, body.ip)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid IP") from exc
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in user.blocked_ips])
