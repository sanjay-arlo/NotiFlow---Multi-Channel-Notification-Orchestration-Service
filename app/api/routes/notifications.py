"""
Notification API endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_tenant,
    get_notification_service,
    handle_notiflow_exceptions
)
from app.core.constants import NotificationPriority
from app.schemas.notification import (
    SendNotificationRequest,
    SendNotificationResponse,
    BatchNotificationRequest,
    BatchNotificationResponse,
    NotificationResponse,
    NotificationStatusResponse
)

router = APIRouter()


@router.post("/send", response_model=SendNotificationResponse)
@handle_notiflow_exceptions
async def send_notification(
    request: SendNotificationRequest,
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service)
) -> SendNotificationResponse:
    """Send a single notification."""
    notification = await notification_service.send_notification(
        tenant_id=str(tenant.id),
        user_external_id=request.user_id,
        title=request.title,
        body=request.body,
        requested_channels=request.channels,
        priority=request.priority or NotificationPriority.NORMAL,
        template_slug=request.template_slug,
        template_variables=request.template_variables,
        scheduled_at=request.scheduled_at,
        bypass_quiet_hours=request.bypass_quiet_hours,
        notification_metadata=request.notification_metadata
    )
    
    return SendNotificationResponse(
        id=str(notification.id),
        status=notification.status,
        resolved_channels=notification.resolved_channels,
        priority=notification.priority,
        scheduled_at=notification.scheduled_at,
        created_at=notification.created_at
    )


@router.post("/batch", response_model=BatchNotificationResponse)
@handle_notiflow_exceptions
async def send_batch_notifications(
    request: BatchNotificationRequest,
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service)
) -> BatchNotificationResponse:
    """Send notifications to multiple users."""
    result = await notification_service.send_batch_notifications(
        tenant_id=str(tenant.id),
        user_external_ids=request.user_ids,
        title=request.title,
        body=request.body,
        requested_channels=request.channels,
        priority=request.priority or NotificationPriority.NORMAL,
        notification_metadata=request.notification_metadata
    )
    
    return BatchNotificationResponse(
        batch_id=result["batch_id"],
        total=result["total"],
        queued=result["queued"],
        failed=result["failed"],
        notifications=result["notifications"]
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
@handle_notiflow_exceptions
async def get_notification(
    notification_id: str,
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service)
) -> NotificationResponse:
    """Get notification details."""
    notification = await notification_service.get_notification(
        notification_id, include_deliveries=True
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Build delivery responses
    deliveries = []
    for delivery in notification.deliveries:
        deliveries.append({
            "channel": delivery.channel,
            "status": delivery.status,
            "destination": delivery.destination,
            "provider_id": delivery.provider_id,
            "sent_at": delivery.sent_at.isoformat() if delivery.sent_at else None,
            "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            "attempts": delivery.attempt_count,
            "last_error": delivery.last_error,
            "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None
        })
    
    return NotificationResponse(
        id=str(notification.id),
        status=notification.status,
        title=notification.title,
        created_at=notification.created_at,
        completed_at=notification.completed_at.isoformat() if notification.completed_at else None,
        deliveries=deliveries
    )


@router.post("/{notification_id}/cancel")
@handle_notiflow_exceptions
async def cancel_notification(
    notification_id: str,
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service)
) -> Dict[str, str]:
    """Cancel a notification."""
    notification = await notification_service.cancel_notification(
        notification_id, str(tenant.id)
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {
        "id": str(notification.id),
        "status": notification.status,
        "message": "Notification cancelled successfully"
    }


@router.get("/")
@handle_notiflow_exceptions
async def list_notifications(
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[datetime] = Query(None, description="Filter by start date"),
    to_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> Dict[str, any]:
    """List notifications for tenant."""
    skip = (page - 1) * per_page
    
    notifications = await notification_service.notification_repo.get_by_status(
        status=status,
        tenant_id=str(tenant.id),
        skip=skip,
        limit=per_page
    )
    
    return {
        "items": [
            {
                "id": str(n.id),
                "status": n.status,
                "title": n.title,
                "priority": n.priority,
                "created_at": n.created_at,
                "completed_at": n.completed_at
            }
            for n in notifications
        ],
        "page": page,
        "per_page": per_page,
        "total": len(notifications)
    }


@router.get("/stats")
@handle_notiflow_exceptions
async def get_notification_stats(
    tenant = Depends(get_current_tenant),
    notification_service = Depends(get_notification_service),
    from_date: Optional[datetime] = Query(None, description="Start date for stats"),
    to_date: Optional[datetime] = Query(None, description="End date for stats")
) -> Dict[str, any]:
    """Get notification statistics."""
    stats = await notification_service.notification_repo.count_by_status(
        tenant_id=str(tenant.id)
    )
    
    return {
        "by_status": stats,
        "total": sum(stats.values())
    }
