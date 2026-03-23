from __future__ import annotations


class AuthException(Exception):
    """Base class for all auth-related exceptions"""

    pass


class InvalidCredentials(AuthException):
    """Raised when email/password is incorrect"""

    pass


class UserNotFound(AuthException):
    """Raised when user does not exist"""

    pass


class UserInactive(AuthException):
    """Raised when user is inactive"""

    pass


class UserAlreadyExists(AuthException):
    """Raised when trying to create a user with existing email"""

    pass


class WeakPassword(AuthException):
    """Raised when password does not meet policy"""

    pass


class InvalidToken(AuthException):
    """Raised when token is invalid"""

    pass


class TokenExpired(AuthException):
    """Raised when token is expired"""

    pass


class InvalidTokenType(AuthException):
    """Raised when wrong token type is used (access vs refresh)"""

    pass
