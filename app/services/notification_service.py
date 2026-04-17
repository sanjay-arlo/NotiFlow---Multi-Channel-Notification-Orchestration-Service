"""
Main notification orchestration service.
"""

from datetime import datetime
from typing import Dict, List, Optional

from app.core.constants import NotificationStatus, NotificationPriority
from app.core.exceptions import (
    UserNotFoundError,
    NoChannelsAvailableError,
    QuietHoursActiveError,
    TemplateNotFoundError,
    InvalidTemplateVariablesError
)
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.db.models.user import User
from app.db.models.template import Template
from app.repositories.notification_repo import NotificationRepository
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.user_repo import UserRepository
from app.repositories.tenant_repo import TenantRepository
from app.services.channel_resolver import ChannelResolver
from app.services.preference_service import PreferenceService
from app.services.template_service import TemplateService
from app.services.delivery_service import DeliveryService
from app.utils.id_utils import generate_notification_id, generate_delivery_id
from app.utils.redis_client import redis_client
from app.core.constants import REDIS_NOTIFICATION_STATUS_TTL


class NotificationService:
    """Main service for creating and managing notifications."""
    
    def __init__(
        self,
        notification_repo: NotificationRepository,
        delivery_repo: DeliveryRepository,
        user_repo: UserRepository,
        tenant_repo: TenantRepository,
        channel_resolver: ChannelResolver,
        preference_service: PreferenceService,
        template_service: TemplateService,
        delivery_service: DeliveryService
    ):
        self.notification_repo = notification_repo
        self.delivery_repo = delivery_repo
        self.user_repo = user_repo
        self.tenant_repo = tenant_repo
        self.channel_resolver = channel_resolver
        self.preference_service = preference_service
        self.template_service = template_service
        self.delivery_service = delivery_service
    
    async def send_notification(
        self,
        tenant_id: str,
        user_external_id: str,
        title: str,
        body: str,
        requested_channels: Optional[List[str]] = None,
        priority: str = NotificationPriority.NORMAL,
        template_slug: Optional[str] = None,
        template_variables: Optional[Dict[str, any]] = None,
        scheduled_at: Optional[datetime] = None,
        bypass_quiet_hours: bool = False,
        metadata: Optional[Dict[str, any]] = None
    ) -> Notification:
        """
        Create and queue a notification for delivery.
        
        Returns the created notification record.
        """
        # Get user
        user = await self.user_repo.get_by_tenant_and_external(
            tenant_id, user_external_id
        )
        if not user:
            raise UserNotFoundError(user_external_id)
        
        # Get template if specified
        template = None
        if template_slug:
            template = await self.template_service.get_template(
                tenant_id, template_slug
            )
        
        # Render template content
        if template and template_variables:
            rendered_content = await self.template_service.render_notification(
                template, template_variables, requested_channels
            )
            # Update title and body with rendered content
            if "subject" in rendered_content:
                title = rendered_content["subject"]
            if "body" in rendered_content:
                body = rendered_content["body"]
        
        # Resolve channels
        resolved_channels = await self.channel_resolver.resolve_channels(
            user, 
            Notification(title=title, body=body, priority=priority),
            requested_channels
        )
        
        if not resolved_channels:
            raise NoChannelsAvailableError(user_external_id)
        
        # Check quiet hours
        is_quiet, resume_at = await self.preference_service.check_quiet_hours(
            user, priority, bypass_quiet_hours
        )
        
        # Handle quiet hours
        if is_quiet and not bypass_quiet_hours:
            notification = await self._create_scheduled_notification(
                tenant_id=tenant_id,
                user=user,
                title=title,
                body=body,
                resolved_channels=resolved_channels,
                priority=priority,
                template=template,
                scheduled_at=resume_at,
                suppressed_by_quiet_hours=True,
                metadata=metadata
            )
            return notification
        
        # Create immediate notification
        notification = await self._create_notification(
            tenant_id=tenant_id,
            user=user,
            title=title,
            body=body,
            resolved_channels=resolved_channels,
            priority=priority,
            template=template,
            scheduled_at=scheduled_at,
            bypass_quiet_hours=bypass_quiet_hours,
            metadata=metadata
        )
        
        # Create delivery records and queue tasks
        await self._create_deliveries_and_queue(notification)
        
        return notification
    
    async def send_batch_notifications(
        self,
        tenant_id: str,
        user_external_ids: List[str],
        title: str,
        body: str,
        requested_channels: Optional[List[str]] = None,
        priority: str = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """
        Send batch notifications to multiple users.
        
        Returns dict with batch_id, total, queued, failed, notifications.
        """
        batch_id = str(generate_notification_id())
        results = {
            "batch_id": batch_id,
            "total": len(user_external_ids),
            "queued": 0,
            "failed": 0,
            "notifications": []
        }
        
        for user_external_id in user_external_ids:
            try:
                notification = await self.send_notification(
                    tenant_id=tenant_id,
                    user_external_id=user_external_id,
                    title=title,
                    body=body,
                    requested_channels=requested_channels,
                    priority=priority,
                    metadata=metadata
                )
                results["queued"] += 1
                results["notifications"].append({
                    "id": str(notification.id),
                    "status": notification.status,
                    "user_external_id": user_external_id
                })
            
            except Exception as e:
                results["failed"] += 1
                results["notifications"].append({
                    "id": None,
                    "status": "failed",
                    "user_external_id": user_external_id,
                    "error": str(e)
                })
        
        return results
    
    async def get_notification(
        self,
        notification_id: str,
        include_deliveries: bool = True
    ) -> Optional[Notification]:
        """Get notification with optional delivery details."""
        if include_deliveries:
            return await self.notification_repo.get_with_deliveries(notification_id)
        else:
            return await self.notification_repo.get(notification_id)
    
    async def cancel_notification(
        self,
        notification_id: str,
        tenant_id: str
    ) -> Optional[Notification]:
        """Cancel a notification and its pending deliveries."""
        # Get notification
        notification = await self.notification_repo.get(notification_id)
        if not notification:
            return None
        
        # Check if notification can be cancelled
        if notification.status in [NotificationStatus.DELIVERED, NotificationStatus.FAILED]:
            raise ValueError(f"Cannot cancel notification in {notification.status} status")
        
        # Update notification status
        notification = await self.notification_repo.mark_as_cancelled(notification_id)
        
        # Cancel pending deliveries
        await self.delivery_service.cancel_pending_deliveries(notification_id)
        
        # Invalidate cache
        await self._invalidate_notification_cache(notification_id)
        
        return notification
    
    async def update_notification_status(
        self,
        notification_id: str
    ) -> Optional[str]:
        """Update notification status based on delivery statuses."""
        deliveries = await self.delivery_repo.get_by_notification(notification_id)
        if not deliveries:
            return None
        
        # Aggregate delivery statuses
        delivery_statuses = [delivery.status for delivery in deliveries]
        new_status = self._aggregate_delivery_status(delivery_statuses)
        
        # Update notification if status changed
        current_notification = await self.notification_repo.get(notification_id)
        if current_notification and current_notification.status != new_status:
            await self.notification_repo.update_status(notification_id, new_status)
            
            # Set completed_at for terminal statuses
            if new_status in [NotificationStatus.DELIVERED, NotificationStatus.FAILED, NotificationStatus.CANCELLED]:
                await self.notification_repo.update_status(
                    notification_id, new_status, datetime.utcnow()
                )
        
        # Update cache
        await self._cache_notification_status(notification_id, new_status, deliveries)
        
        return new_status
    
    async def _create_notification(
        self,
        tenant_id: str,
        user: User,
        title: str,
        body: str,
        resolved_channels: List[str],
        priority: str,
        template: Optional[Template],
        scheduled_at: Optional[datetime] = None,
        bypass_quiet_hours: bool = False,
        suppressed_by_quiet_hours: bool = False,
        metadata: Optional[Dict[str, any]] = None
    ) -> Notification:
        """Create notification record."""
        # Determine primary channel
        primary_channel = self.channel_resolver.get_primary_channel(
            resolved_channels, 
            Notification(title=title, body=body, priority=priority)
        )
        
        notification_data = {
            "tenant_id": tenant_id,
            "user_id": user.id,
            "title": title,
            "body": body,
            "metadata": metadata or {},
            "template_id": template.id if template else None,
            "requested_channels": None,  # Will be set if explicitly requested
            "resolved_channels": resolved_channels,
            "primary_channel": primary_channel,
            "priority": priority,
            "scheduled_at": scheduled_at,
            "bypass_quiet_hours": bypass_quiet_hours,
            "suppressed_by_quiet_hours": suppressed_by_quiet_hours,
            "status": NotificationStatus.QUEUED
        }
        
        return await self.notification_repo.create(notification_data)
    
    async def _create_scheduled_notification(
        self,
        tenant_id: str,
        user: User,
        title: str,
        body: str,
        resolved_channels: List[str],
        priority: str,
        template: Optional[Template],
        scheduled_at: datetime,
        suppressed_by_quiet_hours: bool,
        metadata: Optional[Dict[str, any]] = None
    ) -> Notification:
        """Create scheduled notification."""
        return await self._create_notification(
            tenant_id=tenant_id,
            user=user,
            title=title,
            body=body,
            resolved_channels=resolved_channels,
            priority=priority,
            template=template,
            scheduled_at=scheduled_at,
            bypass_quiet_hours=False,  # Scheduled notifications will be re-evaluated
            suppressed_by_quiet_hours=suppressed_by_quiet_hours,
            metadata=metadata
        )
    
    async def _create_deliveries_and_queue(
        self,
        notification: Notification
    ) -> List[Delivery]:
        """Create delivery records and queue Celery tasks."""
        deliveries = []
        
        for channel in notification.resolved_channels:
            # Determine destination
            destination = self._get_destination_for_channel(
                notification.user, channel
            )
            
            if not destination:
                continue  # Skip channels without destination
            
            # Create delivery record
            delivery = await self.delivery_service.create_delivery(
                notification_id=notification.id,
                channel=channel,
                destination=destination
            )
            deliveries.append(delivery)
            
            # Queue Celery task
            await self.delivery_service.queue_delivery_task(delivery.id)
        
        # Update notification status to processing
        await self.notification_repo.mark_as_processing(notification.id)
        
        return deliveries
    
    def _get_destination_for_channel(
        self,
        user: User,
        channel: str
    ) -> Optional[str]:
        """Get destination address for channel."""
        if channel == "email":
            return user.email
        elif channel == "sms":
            return user.phone
        elif channel == "webhook":
            # Webhook destination would come from webhook config
            # For now, return None - this would need webhook config per user/tenant
            return None
        return None
    
    def _aggregate_delivery_status(
        self,
        delivery_statuses: List[str]
    ) -> str:
        """Aggregate delivery statuses into notification status."""
        from app.core.constants import STATUS_PRIORITY
        
        if not delivery_statuses:
            return NotificationStatus.FAILED
        
        # Find highest priority status
        max_status = max(
            delivery_statuses,
            key=lambda s: STATUS_PRIORITY.get(s, 0)
        )
        
        # Apply aggregation rules
        if max_status in ["pending", "processing"]:
            return max_status if max_status != "sent" else "processing"
        
        if all(status == "delivered" for status in delivery_statuses):
            return "delivered"
        
        if all(status in ["failed", "bounced", "cancelled"] for status in delivery_statuses):
            return "failed" if "failed" in delivery_statuses or "bounced" in delivery_statuses else "cancelled"
        
        return "partial"
    
    async def _cache_notification_status(
        self,
        notification_id: str,
        status: str,
        deliveries: List[Delivery]
    ) -> None:
        """Cache notification status for fast reads."""
        try:
            delivery_statuses = {}
            for delivery in deliveries:
                delivery_statuses[delivery.channel] = delivery.status
            
            cache_data = {
                "status": status,
                "deliveries": delivery_statuses
            }
            
            await redis_client.json_set(
                f"notifstatus:{notification_id}",
                cache_data,
                REDIS_NOTIFICATION_STATUS_TTL
            )
        except Exception:
            pass  # Cache failures shouldn't break functionality
    
    async def _invalidate_notification_cache(self, notification_id: str) -> None:
        """Invalidate cached notification status."""
        try:
            await redis_client.delete(f"notifstatus:{notification_id}")
        except Exception:
            pass
