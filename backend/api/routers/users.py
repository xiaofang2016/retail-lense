from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user
from schema.auth import ForgotPassword, ResetPassword
from schema.user import AnalysisNotificationsIn, UserOut, UserRecord
from services.analysis_notifications import AnalysisNotificationError, set_email_notifications
from services.auth_service import AuthService
from services.password_reset import PasswordResetService

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_me(current_user: UserRecord = Depends(get_current_user)) -> UserOut:
    return AuthService().to_public(current_user)


@router.put("/me/analysis-notifications", response_model=UserOut)
def update_analysis_notifications(
    body: AnalysisNotificationsIn,
    current_user: UserRecord = Depends(get_current_user),
) -> UserOut:
    try:
        user = set_email_notifications(current_user, body.email)
    except AnalysisNotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return UserOut.from_record(user)


@router.post("/forgot-password")
def forgot_password(body: ForgotPassword) -> dict[str, str]:
    """Always 200 so callers cannot probe which emails are registered."""
    PasswordResetService().send_reset_email(body.email)
    return {"message": "ok"}


@router.post("/reset-password")
def reset_password(body: ResetPassword) -> dict[str, str]:
    PasswordResetService().reset_password(body.token, body.password)
    return {"message": "ok"}
