from __future__ import annotations


class BookException(Exception):
    """Base exception for Book domain"""

    pass


# ============================
# CREATE
# ============================


class BookAlreadyExists(BookException):
    """Raised when trying to create a duplicate book"""

    pass


class InvalidBookData(BookException):
    """Raised when book data is invalid"""

    pass


class BookFileUploadFailed(BookException):
    """Raised when file upload fails"""

    pass


# ============================
# GET / COMMON
# ============================


class BookNotFound(BookException):
    """Raised when book does not exist"""

    pass


# ============================
# UPDATE
# ============================


class BookUpdateConflict(BookException):
    """Raised when update causes conflict (e.g., duplicate)"""

    pass


# ============================
# BORROW
# ============================


class BookAlreadyBorrowed(BookException):
    """Raised when user already borrowed the book"""

    pass


class InvalidBorrowRequest(BookException):
    """Raised when borrow request is invalid"""

    pass


# ============================
# RETURN
# ============================


class BorrowRecordNotFound(BookException):
    """Raised when return is attempted without borrow record"""

    pass


class BookReviewConflict(BookException):
    """Raised when review submission causes conflict (e.g., duplicate)"""

    pass


class InvalidBookReview(BookException):
    """Raised when book review data is invalid"""

    pass
