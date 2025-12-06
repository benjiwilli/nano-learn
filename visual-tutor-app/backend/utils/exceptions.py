"""Custom exceptions for Visual Tutor App."""

from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for API responses."""
    
    # Validation errors
    INVALID_IMAGE = "INVALID_IMAGE"
    INVALID_ANNOTATION = "INVALID_ANNOTATION"
    INVALID_REQUEST = "INVALID_REQUEST"
    
    # Service errors
    GEMINI_API_ERROR = "GEMINI_API_ERROR"
    GEMINI_RATE_LIMITED = "GEMINI_RATE_LIMITED"
    NANO_API_ERROR = "NANO_API_ERROR"
    NANO_RATE_LIMITED = "NANO_RATE_LIMITED"
    IMAGE_GENERATION_FAILED = "IMAGE_GENERATION_FAILED"
    
    # Processing errors
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    EXPLANATION_FAILED = "EXPLANATION_FAILED"
    PROMPT_GENERATION_FAILED = "PROMPT_GENERATION_FAILED"
    
    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    
    # Resource errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class VisualTutorError(Exception):
    """Base exception for Visual Tutor App."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.code.value,
            "message": self.message,
            "details": self.details
        }


class ValidationError(VisualTutorError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_REQUEST,
            details={"field": field, **(details or {})},
            status_code=400
        )


class ImageValidationError(ValidationError):
    """Raised when image validation fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message=message, field="image", details=details)
        self.code = ErrorCode.INVALID_IMAGE


class ServiceError(VisualTutorError):
    """Raised when an external service fails."""
    
    def __init__(
        self,
        message: str,
        service: str,
        code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details={"service": service, **(details or {})},
            status_code=503
        )


class GeminiError(ServiceError):
    """Raised when Gemini API fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            service="gemini",
            code=ErrorCode.GEMINI_API_ERROR,
            details=details
        )


class NanoBananaProError(ServiceError):
    """Raised when Nano Banana Pro API fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            service="nanobananapro",
            code=ErrorCode.NANO_API_ERROR,
            details=details
        )


class RateLimitError(VisualTutorError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details={"retry_after": retry_after},
            status_code=429
        )


class SessionError(VisualTutorError):
    """Raised when session operations fail."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        super().__init__(
            message=message,
            code=ErrorCode.SESSION_NOT_FOUND,
            details={"session_id": session_id},
            status_code=404
        )


class AnalysisError(VisualTutorError):
    """Raised when analysis fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code=ErrorCode.ANALYSIS_FAILED,
            details=details,
            status_code=500
        )
