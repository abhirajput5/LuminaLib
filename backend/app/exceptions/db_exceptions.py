from __future__ import annotations


class DatabaseException(Exception):
    """Base class for all database-related exceptions"""

    pass


class DatabaseConnectionError(DatabaseException):
    """Raised when DB connection fails"""

    pass


class QueryExecutionError(DatabaseException):
    """Raised when a query execution fails"""

    pass


class IntegrityError(DatabaseException):
    """Raised when a constraint is violated (e.g., unique email)"""

    pass


class RecordNotFound(DatabaseException):
    """Raised when expected DB record is not found"""

    pass


class DuplicateRecord(DatabaseException):
    """Raised when attempting to insert duplicate data"""

    pass


class TransactionError(DatabaseException):
    """Raised when transaction fails"""

    pass
