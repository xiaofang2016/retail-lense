"""Sign-up, token login, refresh, logout, login history, and optional SMS 2FA."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status

from api.dependencies import get_current_user
from core.exceptions import IpBlockedForUser, IpRestricted, RegistrationConflict, TwoFactorError, UserLockedOut
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


def _login_payload(result: AuthResult) -> dict:
    if result.access_token:
        return TokenResponse.respond(result.access_token)
    return {"status": "otp_required", "phone_hint": result.phone_hint}


def _login_or_raise(username: str, password: str, remember_me: bool, ip: str, user_agent: str) -> dict:
    try:
        return _login_payload(AuthService().authenticate(username, password, remember_me, ip, user_agent))
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
    username: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    remember_me: Annotated[bool, Form()] = False,
):
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    return _login_or_raise(username, password, remember_me, ip, user_agent)


@router.post("/signin")
def signin_json(request: Request, data: CredentialsRequest):
    """JSON alias of POST /auth/token for non-form clients."""
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    return _login_or_raise(data.username, data.password, data.remember_me, ip, user_agent)


@router.post("/verify-otp")
def verify_otp(request: Request, data: VerifyOtpIn):
    ip = client_ip(request)
    user_agent = request.headers.get("user-agent") or ""
    try:
        token = AuthService().verify_login_otp(
            data.username, data.code, data.remember_me, ip, user_agent
        )
    except IpRestricted as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed logins from this IP") from exc
    except TwoFactorError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc
    return TokenResponse.respond(token)


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
