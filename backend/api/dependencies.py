"""JWT auth dependency. Signing key comes from env locally or Secrets Manager on EC2."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError

from core.security.tokens import decode_access_token
from schema.user import UserRecord
from services.user_store import get_user_store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> UserRecord:
    if token is None and "retaillen.access_token" in request.cookies:
        token = request.cookies.get("retaillen.access_token", "")
    token = token or ""

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except PyJWTError as exc:
        raise credentials_exception from exc

    user = get_user_store().get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user
