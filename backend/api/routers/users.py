from fastapi import APIRouter, Depends

from api.dependencies import get_current_user
from schema.auth import ForgotPassword, ResetPassword
from schema.user import UserOut, UserRecord
from services.auth_service import AuthService
from services.password_reset import PasswordResetService

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_me(current_user: UserRecord = Depends(get_current_user)) -> UserOut:
    return AuthService().to_public(current_user)


@router.post("/forgot-password")
def forgot_password(body: ForgotPassword) -> dict[str, str]:
    """Always 200 so callers cannot probe which emails are registered."""
    PasswordResetService().send_reset_email(body.email)
    return {"message": "ok"}


@router.post("/reset-password")
def reset_password(body: ResetPassword) -> dict[str, str]:
    PasswordResetService().reset_password(body.token, body.password)
    return {"message": "ok"}
