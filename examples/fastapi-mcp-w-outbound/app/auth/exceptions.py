from fastapi import status, HTTPException

class UnauthenticatedException(HTTPException):
    """Raised when a request is missing valid authentication credentials."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class UnauthorizedException(HTTPException):
    """Raised when an authenticated user lacks necessary permissions."""
    def __init__(self, detail: str = "You are not authorized to access this resource"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)