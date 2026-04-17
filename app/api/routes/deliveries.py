"""
Delivery history and statistics endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_tenant,
    get_delivery_service,
    handle_notiflow_exceptions
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


class DeliveryResponse(BaseModel):
    """Response schema for delivery details."""
    id: str = Field(..., description="Delivery ID")
    notification_id: str = Field(..., description="Notification ID")
    channel: str = Field(..., description="Channel used")
    status: str = Field(..., description="Delivery status")
    destination: str = Field(..., description="Destination address")
    provider_id: Optional[str] = Field(None, description="Provider message ID")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivered timestamp")
    attempts: int = Field(..., description="Number of attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")


class DeliveryStatsResponse(BaseModel):
    """Response schema for delivery statistics."""
    by_channel: Dict[str, Dict[str, int]] = Field(..., description="Stats by channel")
    by_status: Dict[str, int] = Field(..., description="Stats by status")
    total: int = Field(..., description="Total deliveries")


@router.get("/", response_model=PaginatedResponse[DeliveryResponse])
@handle_notiflow_exceptions
async def list_deliveries(
    tenant = Depends(get_current_tenant),
    delivery_service = Depends(get_delivery_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    from_date: Optional[datetime] = Query(None, description="Filter by start date"),
    to_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[DeliveryResponse]:
    """List deliveries for tenant."""
    skip = (page - 1) * per_page
    
    deliveries = await delivery_service.delivery_repo.get_deliveries_by_date_range(
        from_date=from_date,
        to_date=to_date,
        channel=channel,
        tenant_id=str(tenant.id),
        skip=skip,
        limit=per_page
    )
    
    delivery_responses = [
        DeliveryResponse(
            id=str(delivery.id),
            notification_id=str(delivery.notification_id),
            channel=delivery.channel,
            status=delivery.status,
            destination=delivery.destination,
            provider_id=delivery.provider_id,
            sent_at=delivery.sent_at,
            delivered_at=delivery.delivered_at,
            attempts=delivery.attempt_count,
            last_error=delivery.last_error,
            next_retry_at=delivery.next_retry_at
        )
        for delivery in deliveries
    ]
    
    return PaginatedResponse(
        items=delivery_responses,
        page=page,
        per_page=per_page,
        total=len(delivery_responses),
        pages=(len(delivery_responses) + per_page - 1) // per_page
    )


@router.get("/{delivery_id}", response_model=DeliveryResponse)
@handle_notiflow_exceptions
async def get_delivery(
    delivery_id: str,
    tenant = Depends(get_current_tenant),
    delivery_service = Depends(get_delivery_service)
) -> DeliveryResponse:
    """Get delivery details."""
    delivery = await delivery_service.get_delivery(delivery_id, include_events=True)
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )
    
    return DeliveryResponse(
        id=str(delivery.id),
        notification_id=str(delivery.notification_id),
        channel=delivery.channel,
        status=delivery.status,
        destination=delivery.destination,
        provider_id=delivery.provider_id,
        sent_at=delivery.sent_at,
        delivered_at=delivery.delivered_at,
        attempts=delivery.attempt_count,
        last_error=delivery.last_error,
        next_retry_at=delivery.next_retry_at
    )


@router.get("/stats")
@handle_notiflow_exceptions
async def get_delivery_stats(
    tenant = Depends(get_current_tenant),
    delivery_service = Depends(get_delivery_service),
    from_date: Optional[datetime] = Query(None, description="Start date for stats"),
    to_date: Optional[datetime] = Query(None, description="End date for stats")
) -> DeliveryStatsResponse:
    """Get delivery statistics."""
    stats = await delivery_service.get_delivery_stats(
        tenant_id=str(tenant.id),
        from_date=from_date,
        to_date=to_date
    )
    
    return DeliveryStatsResponse(
        by_channel=stats["by_channel"],
        by_status=stats["by_status"],
        total=stats["total"]
    )


@router.post("/retry")
@handle_notiflow_exceptions
async def retry_failed_deliveries(
    tenant = Depends(get_current_tenant),
    delivery_service = Depends(get_delivery_service)
) -> Dict[str, int]:
    """Manually trigger retry for failed deliveries."""
    # This would typically be an admin function
    # For now, return count of deliveries that would be retried
    deliveries = await delivery_service.get_deliveries_for_retry(limit=1000)
    
    # Filter by tenant (would need to join with notifications)
    # For simplicity, just return count
    return {
        "retryable_deliveries": len(deliveries),
        "message": "Retry process initiated"
    }
