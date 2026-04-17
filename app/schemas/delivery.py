"""
Pydantic schemas for delivery tracking and status updates.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.constants import DeliveryStatus, ChannelType


class DeliveryBase(BaseModel):
    """Base schema for delivery records."""
    notification_id: str
    channel: ChannelType
    destination: str
    status: DeliveryStatus = DeliveryStatus.PENDING


class DeliveryCreate(DeliveryBase):
    """Schema for creating delivery records."""
    provider_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class DeliveryUpdate(BaseModel):
    """Schema for updating delivery records."""
    status: Optional[DeliveryStatus] = None
    provider_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    retry_after: Optional[int] = None


class DeliveryResponse(DeliveryBase):
    """Schema for delivery responses."""
    id: str
    provider_id: Optional[str]
    attempt_count: int
    max_attempts: int
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    error_message: Optional[str]
    error_code: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeliveryEventBase(BaseModel):
    """Base schema for delivery events."""
    delivery_id: str
    from_status: Optional[DeliveryStatus]
    to_status: DeliveryStatus
    event_type: str = "status_change"
    details: Optional[Dict[str, Any]] = None


class DeliveryEventCreate(DeliveryEventBase):
    """Schema for creating delivery events."""
    pass


class DeliveryEventResponse(DeliveryEventBase):
    """Schema for delivery event responses."""
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DeliveryWithEventsResponse(DeliveryResponse):
    """Schema for delivery with included events."""
    events: List[DeliveryEventResponse] = []


class DeliveryListRequest(BaseModel):
    """Schema for delivery list requests."""
    notification_id: Optional[str] = None
    channel: Optional[ChannelType] = None
    status: Optional[DeliveryStatus] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class DeliveryStatsResponse(BaseModel):
    """Schema for delivery statistics."""
    total: int
    by_channel: Dict[str, Dict[str, int]]
    by_status: Dict[str, int]
    by_date: Dict[str, int]
    success_rate: float
    average_delivery_time: Optional[float] = None


class DeliveryRetryRequest(BaseModel):
    """Schema for delivery retry requests."""
    delivery_ids: Optional[List[str]] = None
    max_retries: Optional[int] = None
    force_retry: bool = False


class DeliveryRetryResponse(BaseModel):
    """Schema for delivery retry responses."""
    retryable_deliveries: int
    retried_deliveries: int
    failed_deliveries: int
    message: str


class BulkDeliveryStatus(BaseModel):
    """Schema for bulk delivery status updates."""
    deliveries: List[DeliveryUpdate]


class DeliverySearchRequest(BaseModel):
    """Schema for delivery search requests."""
    query: str = Field(..., min_length=1, max_length=100)
    channel: Optional[ChannelType] = None
    status: Optional[DeliveryStatus] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class DeliveryMetricsRequest(BaseModel):
    """Schema for delivery metrics requests."""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    channel: Optional[ChannelType] = None
    group_by: str = Field(default="day", regex="^(hour|day|week|month)$")


class DeliveryMetricsResponse(BaseModel):
    """Schema for delivery metrics responses."""
    period: str
    metrics: List[Dict[str, Any]]
    summary: Dict[str, Any]


class DeliveryHealthCheck(BaseModel):
    """Schema for delivery health checks."""
    channel: ChannelType
    is_healthy: bool
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    error_rate: float = 0.0


class DeliveryHealthResponse(BaseModel):
    """Schema for delivery health responses."""
    overall_health: str
    channels: List[DeliveryHealthCheck]
    queue_depth: Dict[str, int]
    worker_status: Dict[str, str]
