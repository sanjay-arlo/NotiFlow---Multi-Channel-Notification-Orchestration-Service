"""
Notification request and response schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class SendNotificationRequest(BaseModel):
    """Request schema for sending a notification."""
    user_id: str = Field(..., description="User's external ID")
    title: str = Field(..., max_length=500, description="Notification title")
    body: str = Field(..., description="Notification body content")
    channels: Optional[List[str]] = Field(None, description="Specific channels to use")
    priority: Optional[str] = Field("normal", description="Notification priority")
    template_slug: Optional[str] = Field(None, description="Template slug to use")
    template_variables: Optional[Dict[str, Any]] = Field(None, description="Variables for template rendering")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule for future delivery")
    bypass_quiet_hours: bool = Field(False, description="Bypass quiet hours")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['critical', 'high', 'normal', 'low']
        if v and v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v
    
    @validator('channels')
    def validate_channels(cls, v):
        if v:
            valid_channels = ['email', 'sms', 'webhook']
            invalid = [c for c in v if c not in valid_channels]
            if invalid:
                raise ValueError(f"Invalid channels: {invalid}")
        return v


class SendNotificationResponse(BaseModel):
    """Response schema for sending notification."""
    id: str = Field(..., description="Notification ID")
    status: str = Field(..., description="Notification status")
    resolved_channels: List[str] = Field(..., description="Channels that will be used")
    priority: str = Field(..., description="Notification priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled delivery time")
    created_at: datetime = Field(..., description="Creation timestamp")


class BatchNotificationRequest(BaseModel):
    """Request schema for batch notifications."""
    user_ids: List[str] = Field(..., min_items=1, max_items=1000, description="List of user external IDs")
    title: str = Field(..., max_length=500, description="Notification title")
    body: str = Field(..., description="Notification body content")
    channels: Optional[List[str]] = Field(None, description="Specific channels to use")
    priority: Optional[str] = Field("normal", description="Notification priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['critical', 'high', 'normal', 'low']
        if v and v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v


class BatchNotificationResponse(BaseModel):
    """Response schema for batch notifications."""
    batch_id: str = Field(..., description="Batch ID")
    total: int = Field(..., description="Total notifications in batch")
    queued: int = Field(..., description="Successfully queued notifications")
    failed: int = Field(..., description="Failed notifications")
    notifications: List[Dict[str, Any]] = Field(..., description="Notification results")


class DeliveryInfo(BaseModel):
    """Delivery information schema."""
    channel: str = Field(..., description="Channel used")
    status: str = Field(..., description="Delivery status")
    destination: str = Field(..., description="Destination address")
    provider_id: Optional[str] = Field(None, description="Provider message ID")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivered timestamp")
    attempts: int = Field(..., description="Number of attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")


class NotificationResponse(BaseModel):
    """Response schema for notification details."""
    id: str = Field(..., description="Notification ID")
    status: str = Field(..., description="Notification status")
    title: str = Field(..., description="Notification title")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    deliveries: List[DeliveryInfo] = Field(..., description="Delivery attempts")


class NotificationStatusResponse(BaseModel):
    """Response schema for notification status update."""
    id: str = Field(..., description="Notification ID")
    status: str = Field(..., description="Updated status")
    message: str = Field(..., description="Status update message")


class NotificationListResponse(BaseModel):
    """Response schema for notification list."""
    items: List[Dict[str, Any]] = Field(..., description="Notification items")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total items")


class NotificationStatsResponse(BaseModel):
    """Response schema for notification statistics."""
    by_status: Dict[str, int] = Field(..., description="Count by status")
    total: int = Field(..., description="Total count")


class CancelNotificationRequest(BaseModel):
    """Request schema for cancelling notification."""
    reason: Optional[str] = Field(None, description="Cancellation reason")


class CancelNotificationResponse(BaseModel):
    """Response schema for cancelling notification."""
    id: str = Field(..., description="Notification ID")
    status: str = Field(..., description="New status")
    message: str = Field(..., description="Status message")
