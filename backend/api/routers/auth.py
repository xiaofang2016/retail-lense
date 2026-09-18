"""Sign-up, token login, refresh, logout, login history, and optional SMS 2FA."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status

from api.dependencies import get_current_user
from core.exceptions import IpBlockedForUser, IpRestricted, RegistrationConflict, TwoFactorError, UserLockedOut
from core.security.request_ip import client_ip
from core.security.tokens import create_access_token, create_refresh_token, decode_refresh_token
from core.settings import get_settings
from schema.auth import (
    BlockedIpList,
    BlockedIpOut,
    BlockIpIn,
    CredentialsRequest,
    CreateUserRegistration,
    LoginHistoryList,
    LoginHistoryOut,
    PhoneConfirmIn,
    PhoneStartIn,
    TokenResponse,
    VerifyOtpIn,
)
from schema.user import UserOut, UserRecord
from services.auth_service import AuthResult, AuthService
from services.registration import RegistrationService
from services.two_factor import TwoFactorService

router = APIRouter()


def require_admin(current_user: UserRecord) -> None:
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")



def _refresh_cookie_settings() -> dict:
    secure = get_settings().app_env not in {"local", "test"}
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": 60 * 60 * 24 * 7,
        "path": "/",
    }


def _login_payload(result: AuthResult, response: Response | None = None) -> dict:
    if result.access_token:
        if response and result.refresh_token:
            response.set_cookie(key="retaillen.refresh_token", value=result.refresh_token, **_refresh_cookie_settings())
        return TokenResponse.respond(result.access_token, result.refresh_token)
    return {"status": "otp_required", "phone_hint": result.phone_hint}


def _login_or_raise(
    username: str,
    password: str,
    remember_me: bool,
    ip: str,
    user_agent: str,
    response: Response | None = None,
) -> dict:
    try:
        return _login_payload(AuthService().authenticate(username, password, remember_me, ip, user_agent), response)
    except UserLockedOut as exc:
        raise HTTPException(status.HTTP_423_LOCKED, detail="User is locked out") from exc
    except IpBlockedForUser as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This IP is blocked for this account") from exc
    except IpRestricted as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed logins from this IP") from exc
    except TwoFactorError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc
    except LookupError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password") from exc


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_new_user(data: CreateUserRegistration) -> UserOut:
    if not get_settings().allow_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User registration is disabled")
    try:
        return RegistrationService().register_user(data)
    except RegistrationConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/token")
def get_token(
    request: Request,
    response: Response,
    username: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    remember_me: Annotated[bool, Form()] = False,
):
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    return _login_or_raise(username, password, remember_me, ip, user_agent, response)


@router.post("/signin")
def signin_json(request: Request, response: Response, data: CredentialsRequest):
    """JSON alias of POST /auth/token for non-form clients."""
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    return _login_or_raise(data.username, data.password, data.remember_me, ip, user_agent, response)


@router.post("/verify-otp")
def verify_otp(request: Request, response: Response, data: VerifyOtpIn):
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    try:
        result = AuthService().verify_login_otp(
            data.username, data.code, data.remember_me, ip, user_agent
        )
    except IpRestricted as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed logins from this IP") from exc
    except TwoFactorError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc
    if result.access_token and result.refresh_token:
        response.set_cookie(key="retaillen.refresh_token", value=result.refresh_token, **_refresh_cookie_settings())
    return TokenResponse.respond(result.access_token, result.refresh_token)


@router.post("/2fa/phone")
def start_phone_bind(body: PhoneStartIn, current_user: UserRecord = Depends(get_current_user)) -> dict[str, str]:
    try:
        hint = TwoFactorService().start_bind(current_user, body.phone)
    except TwoFactorError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc
    return {"message": "ok", "phone_hint": hint}


@router.post("/2fa/confirm", response_model=UserOut)
def confirm_phone_bind(
    body: PhoneConfirmIn, current_user: UserRecord = Depends(get_current_user)
) -> UserOut:
    try:
        user = TwoFactorService().confirm_bind(current_user, body.code)
    except TwoFactorError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc
    return UserOut.from_record(user)


@router.post("/2fa/disable", response_model=UserOut)
def disable_two_factor(current_user: UserRecord = Depends(get_current_user)) -> UserOut:
    user = TwoFactorService().disable(current_user)
    return UserOut.from_record(user)


@router.post("/refresh")
def refresh_token(request: Request, response: Response, data: dict | None = None):
    payload = data or {}
    refresh_token_value = payload.get("refresh_token") or request.cookies.get("retaillen.refresh_token")
    if not refresh_token_value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token is required")
    try:
        user_id = decode_refresh_token(refresh_token_value).get("sub")
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="retaillen.refresh_token", value=new_refresh_token, **_refresh_cookie_settings())
    return TokenResponse.respond(new_access_token, new_refresh_token)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("retaillen.access_token")
    response.delete_cookie("retaillen.refresh_token")
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
    require_admin(current_user)
    ips = AuthService().list_blocked_ips(current_user)
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in ips])


@router.post("/blocked-ips", response_model=BlockedIpList)
def block_ip(body: BlockIpIn, current_user: UserRecord = Depends(get_current_user)) -> BlockedIpList:
    require_admin(current_user)
    service = AuthService()
    try:
        user = service.block_ip(current_user, body.ip)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid IP") from exc
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in user.blocked_ips])


@router.delete("/blocked-ips", response_model=BlockedIpList)
def unblock_ip(body: BlockIpIn, current_user: UserRecord = Depends(get_current_user)) -> BlockedIpList:
    require_admin(current_user)
    service = AuthService()
    try:
        user = service.unblock_ip(current_user, body.ip)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid IP") from exc
    return BlockedIpList(items=[BlockedIpOut(ip=ip) for ip in user.blocked_ips])
