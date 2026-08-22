class UserLockedOut(Exception):
    """Raised when a user exceeds max login attempts or is still inside the lockout window."""


class IpRestricted(Exception):
    """Raised when an IP has too many failed login attempts in the configured window."""


class IpBlockedForUser(Exception):
    """Raised when this account has blocked the caller IP."""
