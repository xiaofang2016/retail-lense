class UserLockedOut(Exception):
    """Raised when a user exceeds max login attempts or is still inside the lockout window."""


class IpRestricted(Exception):
    """Raised when an IP has too many failed login attempts in the configured window."""


class IpBlockedForUser(Exception):
    """Raised when this account has blocked the caller IP."""


class RegistrationConflict(Exception):
    """Raised when a sign-up username or email already exists."""


class TwoFactorError(Exception):
    """SMS 2FA bind / verify failures."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)
