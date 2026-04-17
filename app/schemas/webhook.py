"""
Pydantic schemas for webhook configuration management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator

from app.core.constants import WebhookStatus


class WebhookConfigBase(BaseModel):
    """Base schema for webhook configuration."""
    name: str = Field(..., min_length=1, max_length=100)
    url: HttpUrl
    secret: Optional[str] = Field(None, min_length=8, max_length=256)
    headers: Dict[str, str] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=10, ge=1, le=300)
    is_active: bool = True

    @validator('headers')
    def validate_headers(cls, v):
        """Validate webhook headers."""
        # Convert header keys to lowercase for consistency
        if v:
            return {k.lower(): v for k, v in v.items()}
        return v


class WebhookConfigCreate(WebhookConfigBase):
    """Schema for creating webhook configurations."""
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_items=10)


class WebhookConfigUpdate(BaseModel):
    """Schema for updating webhook configurations."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[HttpUrl] = None
    secret: Optional[str] = Field(None, min_length=8, max_length=256)
    headers: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class WebhookConfigResponse(WebhookConfigBase):
    """Schema for webhook configuration responses."""
    id: str
    tenant_id: str
    description: Optional[str]
    status: WebhookStatus
    failure_count: int
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    last_error: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookTestRequest(BaseModel):
    """Schema for webhook test requests."""
    webhook_id: str
    test_payload: Optional[Dict[str, Any]] = None
    test_headers: Optional[Dict[str, str]] = None
    dry_run: bool = True


class WebhookTestResponse(BaseModel):
    """Schema for webhook test responses."""
    webhook_id: str
    success: bool
    status_code: Optional[int]
    response_time_ms: Optional[float]
    response_body: Optional[str]
    error_message: Optional[str]
    headers_sent: Dict[str, str]
    headers_received: Dict[str, str]


class WebhookHealthCheck(BaseModel):
    """Schema for webhook health check results."""
    webhook_id: str
    webhook_name: str
    is_healthy: bool
    status: WebhookStatus
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    consecutive_failures: int
    error_rate: float
    average_response_time: Optional[float]
    uptime_percentage: float


class WebhookHealthResponse(BaseModel):
    """Schema for webhook health summary."""
    total_webhooks: int
    healthy_webhooks: int
    unhealthy_webhooks: int
    disabled_webhooks: int
    overall_health: str
    webhooks: List[WebhookHealthCheck]


class WebhookListRequest(BaseModel):
    """Schema for webhook list requests."""
    status: Optional[WebhookStatus] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class WebhookUsageStats(BaseModel):
    """Schema for webhook usage statistics."""
    webhook_id: str
    webhook_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    average_response_time: Optional[float]
    last_used: Optional[datetime]


class WebhookSignatureVerification(BaseModel):
    """Schema for webhook signature verification."""
    payload: str
    signature: str
    secret: str
    timestamp: Optional[str] = None


class WebhookSignatureResponse(BaseModel):
    """Schema for webhook signature verification response."""
    is_valid: bool
    error_message: Optional[str]
    computed_signature: Optional[str]


class WebhookBatchUpdate(BaseModel):
    """Schema for bulk webhook updates."""
    webhook_ids: List[str]
    updates: WebhookConfigUpdate


class WebhookExportRequest(BaseModel):
    """Schema for webhook export requests."""
    webhook_ids: Optional[List[str]] = None
    include_secrets: bool = False
    format: str = Field(default="json", regex="^(json|yaml|csv)$")


class WebhookImportRequest(BaseModel):
    """Schema for webhook import requests."""
    webhooks: List[WebhookConfigCreate]
    overwrite_existing: bool = False
    validate_only: bool = False
    generate_secrets: bool = False


class WebhookImportResponse(BaseModel):
    """Schema for webhook import responses."""
    imported: int
    updated: int
    failed: int
    errors: List[str] = []
    generated_secrets: Dict[str, str] = {}


class WebhookEvent(BaseModel):
    """Schema for webhook event tracking."""
    webhook_id: str
    event_type: str
    status_code: Optional[int]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    payload_size: int
    timestamp: datetime


class WebhookAnalytics(BaseModel):
    """Schema for webhook analytics."""
    webhook_id: str
    period: str
    metrics: Dict[str, Any]
    events: List[WebhookEvent]


class WebhookRetryPolicy(BaseModel):
    """Schema for webhook retry policy configuration."""
    webhook_id: str
    max_retries: int = Field(ge=0, le=10)
    retry_intervals: List[int] = Field(default=[60, 300, 900, 3600, 7200])
    retry_on_status_codes: List[int] = Field(default=[429, 500, 502, 503, 504])
    exponential_backoff: bool = True
    jitter: bool = True


class WebhookSecurityConfig(BaseModel):
    """Schema for webhook security configuration."""
    webhook_id: str
    signature_enabled: bool = True
    signature_algorithm: str = Field(default="sha256", regex="^(sha256|sha384|sha512)$")
    timestamp_validation: bool = True
    max_timestamp_age: int = Field(default=300, ge=60)  # 5 minutes max
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None


class WebhookDeliveryReport(BaseModel):
    """Schema for webhook delivery reports."""
    webhook_id: str
    webhook_name: str
    period_start: datetime
    period_end: datetime
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_response_time: float
    errors_by_type: Dict[str, int]
    response_time_distribution: Dict[str, int]
