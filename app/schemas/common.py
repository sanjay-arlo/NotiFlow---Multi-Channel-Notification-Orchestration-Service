"""
Common schema components used across multiple endpoints.
"""

from typing import Generic, List, TypeVar, Optional

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    items: List[T] = Field(..., description="Items in current page")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    success: bool = Field(False, description="Whether the request was successful")
    error: dict = Field(..., description="Error details")
    code: str = Field(..., description="Error code")


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    success: bool = Field(True, description="Whether the request was successful")
    data: Optional[dict] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Success message")


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    service: str = Field(..., description="Service name")
    uptime_seconds: Optional[int] = Field(None, description="Service uptime in seconds")


class ReadinessCheckResponse(BaseModel):
    """Readiness check response schema."""
    status: str = Field(..., description="Service readiness status")
    checks: dict = Field(..., description="Dependency health checks")


class QueueHealthResponse(BaseModel):
    """Queue health check response schema."""
    queues: dict = Field(..., description="Queue depth and worker information")


class RateLimitResponse(BaseModel):
    """Rate limit response schema."""
    limit: int = Field(..., description="Rate limit per window")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset: int = Field(..., description="Timestamp when rate limit resets")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")


class ValidationResponse(BaseModel):
    """Validation response schema."""
    valid: bool = Field(..., description="Whether the input is valid")
    errors: Optional[List[str]] = Field(None, description="Validation error messages")
    warnings: Optional[List[str]] = Field(None, description="Validation warnings")


class SearchResponse(BaseModel, Generic[T]):
    """Generic search response schema."""
    query: str = Field(..., description="Search query")
    total: int = Field(..., ge=0, description="Total results found")
    items: List[T] = Field(..., description="Search results")
    page: int = Field(..., ge=1, description="Current page")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")


class BulkOperationResponse(BaseModel):
    """Generic bulk operation response schema."""
    total: int = Field(..., ge=0, description="Total items processed")
    successful: int = Field(..., ge=0, description="Successful operations")
    failed: int = Field(..., ge=0, description="Failed operations")
    errors: Optional[List[dict]] = Field(None, description="Error details for failed operations")
    results: Optional[List[dict]] = Field(None, description="Operation results")


class MetricsResponse(BaseModel):
    """Metrics response schema."""
    metrics: dict = Field(..., description="Metric values")
    period: str = Field(..., description="Time period for metrics")
    generated_at: str = Field(..., description="When metrics were generated")
